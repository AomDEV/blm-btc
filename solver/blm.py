"""Core BIP39/BIP32 machinery for the BLM 0.2 BTC puzzle.

Target: 1KfZGvwZxsvSmemoCmEV75uqcNzYBHjkHZ  (hash160 ccbd031e...)
"""
import hashlib, hmac, itertools, os, unicodedata
from coincurve import PrivateKey, PublicKey

TARGET_ADDR = "1KfZGvwZxsvSmemoCmEV75uqcNzYBHjkHZ"
TARGET_H160 = bytes.fromhex(os.environ.get("BLM_TARGET_H160",
                                          "ccbd031e54cde2a3189fd59bc49f731367a1779e"))
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
HARD = 0x80000000

_here = os.path.dirname(os.path.abspath(__file__))
_wl = os.path.join(_here, "english.txt")
if not os.path.exists(_wl):
    _wl = os.path.join(_here, "..", "BLM_0.2BTC", "python_script", "english.txt")
WORDLIST = [w.strip() for w in open(_wl) if w.strip()]
assert len(WORDLIST) == 2048
WIDX = {w: i for i, w in enumerate(WORDLIST)}


# ---------- hashing helpers ----------
def sha256(b): return hashlib.sha256(b).digest()

def hash160(b):
    h = hashlib.new("ripemd160"); h.update(hashlib.sha256(b).digest()); return h.digest()

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def b58check(payload: bytes) -> str:
    raw = payload + sha256(sha256(payload))[:4]
    n = int.from_bytes(raw, "big"); out = ""
    while n: n, r = divmod(n, 58); out = _B58[r] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\x00"))) + out

def h160_to_addr(h, ver=b"\x00"): return b58check(ver + h)


# ---------- BIP39 ----------
def mnemonic_checksum_ok(words) -> bool:
    """True if the word sequence is a valid BIP39 mnemonic (length + checksum)."""
    n = len(words)
    if n % 3 or not (3 <= n <= 24):
        return False
    bits = 0
    for w in words:
        i = WIDX.get(w)
        if i is None: return False
        bits = (bits << 11) | i
    total = n * 11
    cs_len = total // 33
    ent_len = total - cs_len
    ent = bits >> cs_len
    cs = bits & ((1 << cs_len) - 1)
    eb = ent.to_bytes(ent_len // 8, "big")
    return (sha256(eb)[0] >> (8 - cs_len)) == cs

def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    m = unicodedata.normalize("NFKD", mnemonic).encode()
    s = unicodedata.normalize("NFKD", "mnemonic" + passphrase).encode()
    return hashlib.pbkdf2_hmac("sha512", m, s, 2048, 64)


# ---------- BIP32 ----------
class Node:
    __slots__ = ("k", "c", "_pub")
    def __init__(self, k, c): self.k = k; self.c = c; self._pub = None
    @property
    def pub(self):
        if self._pub is None:
            self._pub = PublicKey.from_valid_secret(self.k).format(True)
        return self._pub
    def ckd(self, i):
        data = (b"\x00" + self.k if i & HARD else self.pub) + i.to_bytes(4, "big")
        I = hmac.new(self.c, data, hashlib.sha512).digest()
        k = (int.from_bytes(I[:32], "big") + int.from_bytes(self.k, "big")) % N
        return Node(k.to_bytes(32, "big"), I[32:])

def master_from_seed(seed: bytes) -> Node:
    I = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    return Node(I[:32], I[32:])

def derive(node: Node, path):
    for i in path: node = node.ckd(i)
    return node


# ---------- address forms ----------
def h160s(node: Node):
    """hash160 of compressed AND uncompressed pubkey for this node."""
    pk = PublicKey.from_valid_secret(node.k)
    return hash160(pk.format(True)), hash160(pk.format(False))


# Derivation paths worth trying for a legacy 1... address.
ACCOUNT_PATHS = [
    (44 | HARD, 0 | HARD, 0 | HARD),   # BIP44 account 0
    (44 | HARD, 0 | HARD, 1 | HARD),
    (0 | HARD,),                        # Bitcoin Core / old style
    (),                                 # bare master
    (0 | HARD, 0 | HARD),
]
CHAINS = [(0,), (1,), ()]

def scan_seed(seed: bytes, gap: int = 20):
    """Yield (path_str, addr) for a broad set of legacy derivations."""
    m = master_from_seed(seed)
    # master itself
    for c, u in [h160s(m)]:
        yield "m", c, u
    for acct in ACCOUNT_PATHS:
        try: base = derive(m, acct)
        except Exception: continue
        for ch in CHAINS:
            try: node = derive(base, ch)
            except Exception: continue
            for i in range(gap):
                try: leaf = node.ckd(i)
                except Exception: continue
                c, u = h160s(leaf)
                yield f"m/{'/'.join(str(x & 0x7fffffff) + ('h' if x & HARD else '') for x in acct + ch + (i,))}", c, u

def check_seed(seed: bytes, gap: int = 20):
    for path, c, u in scan_seed(seed, gap):
        if c == TARGET_H160: return (path, "compressed")
        if u == TARGET_H160: return (path, "uncompressed")
    return None

def check_mnemonic(mnemonic: str, passphrase: str = "", gap: int = 20):
    return check_seed(mnemonic_to_seed(mnemonic, passphrase), gap)
