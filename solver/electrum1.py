"""Old-Electrum (v1) seed derivation: 1626-word list, 100k-round SHA-256 stretch."""
import hashlib
from coincurve import PrivateKey, PublicKey
import blm

WORDS = [w.strip() for w in open(__file__.rsplit("/", 1)[0] + "/electrum_words.txt") if w.strip()]
assert len(WORDS) == 1626
IDX = {w: i for i, w in enumerate(WORDS)}
N = blm.N
_n = 1626


def mn_decode(words):
    """12 old-Electrum words -> 32-char hex seed string."""
    out = ""
    for i in range(len(words) // 3):
        w1, w2, w3 = words[3 * i: 3 * i + 3]
        a, b, c = IDX[w1], IDX[w2], IDX[w3]
        x = a + _n * ((b - a) % _n) + _n * _n * ((c - b) % _n)
        out += "%08x" % x
    return out


def stretch(seed_hex: str) -> int:
    """Electrum v1 key stretching: 100,000 rounds of sha256(x + seed)."""
    seed = seed_hex.encode("ascii")
    x = seed
    for _ in range(100000):
        x = hashlib.sha256(x + seed).digest()
    return int.from_bytes(x, "big")


def mpk_from_secexp(secexp: int) -> bytes:
    """Master public key = uncompressed pubkey without the 0x04 prefix (64 bytes)."""
    return PublicKey.from_valid_secret(secexp.to_bytes(32, "big")).format(False)[1:]


def sequence(mpk: bytes, for_change: int, n: int) -> int:
    h = hashlib.sha256(hashlib.sha256(("%d:%d:" % (n, for_change)).encode("ascii") + mpk).digest()).digest()
    return int.from_bytes(h, "big")


def addresses(words, n_index=5, changes=(0, 1)):
    """Yield (change, index, hash160_uncompressed, hash160_compressed)."""
    secexp = stretch(mn_decode(words))
    mpk = mpk_from_secexp(secexp)
    for c in changes:
        for i in range(n_index):
            k = (secexp + sequence(mpk, c, i)) % N
            pk = PublicKey.from_valid_secret(k.to_bytes(32, "big"))
            yield c, i, blm.hash160(pk.format(False)), blm.hash160(pk.format(True))


def check(words, n_index=5, changes=(0, 1)):
    T = blm.TARGET_H160
    for c, i, u, comp in addresses(words, n_index, changes):
        if u == T: return f"electrum1 change={c} index={i} uncompressed"
        if comp == T: return f"electrum1 change={c} index={i} compressed"
    return None


if __name__ == "__main__":
    # Positive control: Electrum's own published v1 test vector
    # (tests/test_wallet_vertical.py :: test_electrum_seed_old)
    m = "powerful random nobody notice nothing important anyway look away hidden message over".split()
    seed = mn_decode(m)
    assert seed == "acb740e454c3134901d7c8f16497cc1c", f"mn_decode FAILED: {seed}"
    print("seed hex  OK :", seed)
    secexp = stretch(seed)
    mpk = mpk_from_secexp(secexp).hex()
    exp = ("e9d4b7866dd1e91c862aebf62a49548c7dbf7bcc6e4b7b8c9da820c7737968df"
           "9c09d5a3e271dc814a29981f81b3faaf2737b551ef5dcc6189cf0f8252c442b3")
    assert mpk == exp, f"stretch/MPK FAILED: {mpk}"
    print("mpk       OK :", mpk[:24], "...")
    got = {}
    for c, i, u, comp in addresses(m, 1, (0, 1)):
        got[c] = blm.h160_to_addr(u)
    assert got[0] == "1FJEEB8ihPMbzs2SkLmr37dHyRFzakqUmo", got[0]
    assert got[1] == "1KRW8pH6HFHZh889VDq6fEKvmrsmApwNfe", got[1]
    print("recv addr OK :", got[0])
    print("chng addr OK :", got[1])
    print("\nOK: old-Electrum v1 reproduces the official Electrum test vector end-to-end.")

    # Negative control: the target must NOT match this vector.
    assert check(m) is None
    print("negative control OK (official vector does not match the escrow)")

    import time
    t = time.time(); stretch(seed); print("\nstretch cost: %.1f ms/seed" % ((time.time()-t)*1000))
