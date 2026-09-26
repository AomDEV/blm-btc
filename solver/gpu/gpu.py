"""GPU (OpenCL / Apple M1) checker for the BLM puzzle.

Reuses the secp256k1 + BIP32 OpenCL kernels from johncantrell97/bip39-solver-gpu
and adds blm.cl, which takes word-index tuples of ANY BIP39 length and checks
m/44'/0'/0'/0/i for i < n_addr against the target hash160.

Apple's cl2Metal silently KILLS long or small-work-group launches and returns
zeros, so every launch carries an embedded canary (a known mnemonic checked
against its own address in the same pass). A launch whose canaries do not all
report is rejected, never counted as a negative.
"""
import os, sys, time
import numpy as np
import pyopencl as cl

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import blm

# The 11 base kernels are vendored in gpu/cl/ (from johncantrell97/bip39-solver-gpu) so a clone of
# this repo builds with no external checkout. BLM_CL_DIR overrides for experiments.
KERNEL_DIR = os.environ.get("BLM_CL_DIR", os.path.join(HERE, "cl"))
BASE = ["common", "ripemd", "sha2", "mnemonic_constants", "secp256k1_common",
        "secp256k1_scalar", "secp256k1_field", "secp256k1_group", "secp256k1_prec",
        "secp256k1", "address"]
CANARY_FLAG = 0x80000000
UNC_FLAG = 0x40000000        # kernel: the hash160 of the UNCOMPRESSED (04||x||y) pubkey matched
PATH_MASK = 0x3fffffff

def hit_name(paths, v):
    """result word -> path string, plus ' key=uncompressed' when the 04-form hash matched"""
    v = int(v)
    return paths[(v & PATH_MASK) - 1] + (" key=uncompressed" if v & UNC_FLAG else "")

def _wide_paths():
    P=[]
    P+=[f"m/44h/0h/0h/0/{i}" for i in range(20)]; P+=[f"m/44h/0h/0h/1/{i}" for i in range(10)]
    P+=[f"m/44h/0h/1h/0/{i}" for i in range(10)];  P+=[f"m/44h/0h/1h/1/{i}" for i in range(10)]
    P+=[f"m/0h/0/{i}" for i in range(10)];         P+=[f"m/0h/1/{i}" for i in range(10)]
    P+=[f"m/0/{i}" for i in range(10)];            P+=[f"m/1/{i}" for i in range(10)]
    P+=[f"m/0h/0h/{i}h" for i in range(10)];       P+=["m"]
    P+=[f"m/44h/0h/0h/0/{i}" for i in range(20,32)]   # ids 101..112
    return P
WIDE_PATHS = _wide_paths()   # 113 paths, identical to solve.py WIDE_TREE


def words_to_tuple(words):
    return np.array([blm.WIDX[w] for w in words], dtype=np.uint16)


class GPUKilled(RuntimeError):
    pass


class GPU:
    LOCAL = 32        # Apple SIMD-group width; smaller work-groups get the kernel killed
    MAX_BATCH = 4096  # ~1.4 s per launch at 20 addrs; the driver kills launches near ~3 s

    MAX_PASS = 99      # kernel `joined` budget: 8 + len + 4 <= 111 so the salt is one or two blocks

    @staticmethod
    def _salt_block(passphrase: str) -> np.ndarray:
        """PBKDF2 salt "mnemonic"||passphrase||INT(1) as ONE padded SHA-512 block, 16 big-endian
        words. The kernel compresses it onto the ipad midstate, so the message being padded for is
        128 (ipad) + len(salt) bytes. Fixed 16 words means no kernel constant and no rebuild when
        the passphrase changes - a sweep switches passphrase by swapping this buffer."""
        b = passphrase.encode()
        if len(b) > GPU.MAX_PASS:
            raise ValueError(f"passphrase {len(b)} B > {GPU.MAX_PASS} B: too long for the GPU kernel")
        msg = b"mnemonic" + b + b"\x00\x00\x00\x01"
        buf = bytearray(128)
        buf[:len(msg)] = msg
        buf[len(msg)] = 0x80
        buf[-8:] = ((128 + len(msg)) * 8).to_bytes(8, "big")
        return np.array([int.from_bytes(buf[8*i:8*i+8], "big") for i in range(16)], dtype=np.uint64)

    def set_passphrase(self, passphrase: str):
        """Swap the salt buffer. Also drops the canaries: they are CPU-derived with the passphrase
        in force, and a stale one would make every launch look driver-killed."""
        if passphrase == self.passphrase:
            return
        self.passphrase = passphrase
        self.sbuf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                              hostbuf=self._salt_block(passphrase))
        self._canaries = {}

    def __init__(self, n_addr=20, verbose=True, mode="narrow", passphrase=""):
        self.ctx = cl.Context(dev_type=cl.device_type.GPU)
        self.dev = self.ctx.devices[0]
        self.q = cl.CommandQueue(self.ctx)
        self.n_addr = n_addr
        self.mode = mode
        src = "\n".join(open(os.path.join(KERNEL_DIR, f + ".cl")).read() for f in BASE)
        src += "\n" + open(os.path.join(HERE, "blm.cl")).read()
        t = time.time()
        self.prg = cl.Program(self.ctx, src).build(options=[])
        dt = time.time() - t
        self.kern = self.prg.blm_check if mode == "narrow" else self.prg.blm_check_wide
        self.passphrase = None
        self._canaries = {}
        self.set_passphrase(passphrase)
        if verbose:
            print(f"[gpu] {self.dev.name}: kernels built in {dt:.1f}s, mode={mode}, "
                  f"{'m/44h/0h/0h/0/0..%d'%(n_addr-1) if mode=='narrow' else '101 wide paths'}, wg {self.LOCAL}"
                  + (f", passphrase {passphrase!r}" if passphrase else ""))
        self.batch = self.MAX_BATCH if mode == "narrow" else 1024   # wide does ~5x the EC work per seed
        self.kills = 0
        self.paths = ([f"m/44h/0h/0h/0/{i}" for i in range(n_addr)] if mode == "narrow" else WIDE_PATHS)
        self.set_target(blm.TARGET_H160)

    def set_target(self, h160: bytes):
        self.target = np.frombuffer(h160, dtype=np.uint8)
        self.tbuf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                              hostbuf=self.target)

    def _canary(self, nw):
        """A known mnemonic of length nw and its address at a fixed index."""
        if nw not in self._canaries:
            ws = ["zoo"] * nw          # distinct from every control mnemonic; index 2047 edge-tests the word table
            idx = min(3, self.n_addr - 1)
            node = blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(ws), self.passphrase)),
                              (44 | blm.HARD, 0 | blm.HARD, 0 | blm.HARD, 0, idx))
            h = blm.h160s(node)[0]
            self._canaries[nw] = {
                "tuple": words_to_tuple(ws), "idx": idx,
                "buf": cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                 hostbuf=np.frombuffer(h, dtype=np.uint8)),
            }
        return self._canaries[nw]

    def check(self, tuples: np.ndarray) -> np.ndarray:
        """tuples: (N, NW) uint16 word indices -> (N,) uint32: i+1 on a hit, else 0.
        Raises GPUKilled if the driver killed a launch (results are then discarded)."""
        tuples = np.ascontiguousarray(tuples, dtype=np.uint16)
        n, nw = tuples.shape
        out = np.zeros(n, dtype=np.uint32)
        s = 0
        while s < n:
            chunk = tuples[s:s + self.batch]
            try:
                out[s:s + len(chunk)] = self._launch(chunk)
                s += len(chunk)
            except GPUKilled:
                # the driver killed a launch that ran too long: halve the batch and redo it
                if self.batch <= 256:
                    raise
                self.batch //= 2
                self.kills += 1
        return out

    def _launch(self, chunk):
        n, nw = chunk.shape
        c = self._canary(nw)
        # append at least one canary row, then pad to a multiple of LOCAL with more canaries
        n_can = 1 + ((-(n + 1)) % self.LOCAL)
        work = np.vstack([chunk, np.repeat(c["tuple"][None, :], n_can, axis=0)])
        ibuf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                         hostbuf=np.ascontiguousarray(work))
        res = np.zeros(len(work), dtype=np.uint32)
        obuf = cl.Buffer(self.ctx, cl.mem_flags.WRITE_ONLY, res.nbytes)
        self.kern(self.q, (len(work),), (self.LOCAL,), ibuf, np.uint32(nw),
                  np.uint32(self.n_addr), self.tbuf, c["buf"], self.sbuf, obuf)
        cl.enqueue_copy(self.q, res, obuf)
        self.q.finish()
        expect = CANARY_FLAG | (c["idx"] + 1)
        if not np.all(res[n:] == expect):
            raise GPUKilled(f"GPU launch killed by driver: {int(np.sum(res[n:] != expect))}/{n_can} "
                            f"canary rows failed - batch discarded, not counted")
        real = res[:n].copy()
        real[real & CANARY_FLAG != 0] = 0   # a real row that is the canary tuple: ignore
        return real


def _control(gpu, words, k, label, path=None):
    """Plant the CPU-derived address at `path` (default m/44'/0'/0'/0/k) and confirm recovery."""
    mn = " ".join(words)
    path = path or (44 | blm.HARD, 0 | blm.HARD, 0 | blm.HARD, 0, k)
    node = blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(mn)), path)
    gpu.set_target(blm.h160s(node)[0])
    res = gpu.check(words_to_tuple(words)[None, :])
    got = hit_name(gpu.paths, res[0]) if res[0] else "none"
    want = solve_pname(path)
    ok = got == want
    print(f"   {label:34s} len={len(mn):3d}B  planted {want:18s} -> gpu {got:18s} {'OK' if ok else 'FAIL'}")
    return ok

def solve_pname(path):
    H = blm.HARD
    return "m/" + "/".join(str(x & 0x7fffffff) + ("h" if x & H else "") for x in path) if path else "m"


def selftest(gpu):
    print("[gpu] positive controls (CPU-derived address planted, GPU must recover the index):")
    ok = True
    ok &= _control(gpu, "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about".split(), 0, "12 words, index 0")
    ok &= _control(gpu, "legal winner thank year wave sausage worth useful legal winner thank yellow".split(), 7, "12 words, index 7")
    ok &= _control(gpu, ["abstract"] * 21, 3, "21 words (188 B, >128 => prehash)")
    ok &= _control(gpu, ["abstract"] * 24, 19, "24 words (215 B), index 19")
    ok &= _control(gpu, "subject camera tower mask police flag liberty black eye order pyramid vote moon peace real rifle gold world glove second food".split(), 12, "21 words, real candidate shape")
    gpu.set_target(bytes.fromhex("ccbd031e54cde2a3189fd59bc49f731367a1779e"))
    res = gpu.check(words_to_tuple("abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about".split())[None, :])
    print(f"   {'negative control (must be 0)':34s} -> {int(res[0])}   {'OK' if res[0]==0 else 'FAIL'}")
    ok &= res[0] == 0
    # planted hit at the LAST row of a full batch, with every launch canary-verified
    rng = np.random.default_rng(9)
    t = rng.integers(0, 2048, size=(gpu.MAX_BATCH * 2, 12), dtype=np.uint16)
    words = "legal winner thank year wave sausage worth useful legal winner thank yellow".split()
    t[-1] = words_to_tuple(words)
    node = blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(words))),
                      (44 | blm.HARD, 0 | blm.HARD, 0 | blm.HARD, 0, 7))
    gpu.set_target(blm.h160s(node)[0])
    res = gpu.check(t)
    ok2 = (int(res[-1]) & PATH_MASK) == 8 and int(res[-1]) & UNC_FLAG == 0 and np.count_nonzero(res[:-1]) == 0
    print(f"   {'planted at last row of 2 full batches':34s} -> last={(int(res[-1]) & PATH_MASK)-1}, other nonzero={int(np.count_nonzero(res[:-1]))}   {'OK' if ok2 else 'FAIL'}")
    ok &= ok2
    if gpu.mode == "wide":
        print("[gpu] wide-only paths (invisible to the narrow kernel):")
        H = blm.HARD; w = "legal winner thank year wave sausage worth useful legal winner thank yellow".split()
        for path, label in [((44|H,0|H,1|H,0,3), "m/44'/0'/1'/0/3"), ((0|H,0|H,5|H), "m/0'/0'/5' (all-hardened)"),
                            ((0|H,1,8), "m/0'/1/8"), ((1,2), "m/1/2"), ((), "bare master"),
                            ((44|H,0|H,0|H,1,9), "m/44'/0'/0'/1/9 (change)"),
                            ((44|H,0|H,0|H,0,20), "m/44'/0'/0'/0/20 (XX)"), ((44|H,0|H,0|H,0,21), "m/44'/0'/0'/0/21 (third hand)"),
                            ((44|H,0|H,0|H,0,31), "m/44'/0'/0'/0/31 (last)")]:
            ok &= _control(gpu, w, 0, label, path)
    print("[gpu] SELFTEST", "PASSED" if ok else "FAILED")
    return ok


def bench(gpu, nw=21, n=None):
    n = n or gpu.MAX_BATCH * 2
    rng = np.random.default_rng(1)
    tuples = rng.integers(0, 2048, size=(n, nw), dtype=np.uint16)
    gpu.check(tuples[:256])
    t = time.time(); gpu.check(tuples); dt = time.time() - t
    rate = n / dt
    print(f"[gpu] bench: {n} x {nw}-word seeds, {gpu.n_addr} addrs each: {dt:.2f}s -> "
          f"{rate:,.0f} seeds/s ({rate*gpu.n_addr:,.0f} addresses/s)  [batch settled at {gpu.batch}, kills={gpu.kills}]")
    return rate


if __name__ == "__main__":
    mode = os.environ.get("BLM_GPU_MODE", "narrow")
    g = GPU(n_addr=int(os.environ.get("BLM_NADDR", "20")), mode=mode)
    if selftest(g):
        bench(g, nw=21, n=g.batch * 2)
