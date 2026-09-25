"""Run ONE template on GPU + CPU concurrently, same path set on both.
  BLM_PATHS=n2   (default) m/44'/0'/0'/0/{0,1} on both  - user decision: fastest, no wide scan
  BLM_PATHS=n32            m/44'/0'/0'/0/0..31 on both
  BLM_PATHS=wide           113 paths (wide GPU kernel is NOT production-ready: hangs/crashes)

Design (v2): everything is asynchronous with bounded in-flight work on each sink.
  enumeration pool  -> checksum-valid tuple arrays
  main loop         -> slices of SLICE rows go to whichever sink has capacity:
                       GPU sink  = the process-isolated worker (submit / collect, non-blocking)
                       CPU sink  = a derivation pool (apply_async)
Backpressure balances the split by itself; there is no share tuner. Hits ->
../HIT.txt tagged [gpu-*] / [cpu-*]. Every GPU launch is canary-verified."""
import os, sys, time, itertools
import numpy as np
from multiprocessing import Pool, cpu_count
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("BLM_PATHS", "n2")
import blm, solve

SLICE = 4096

# ---- enumeration workers (checksum filter) ----
# Fast path: the mnemonic's 11-bit-per-word bit-string is precomputed for the FIXED
# words; each combo only ORs in the free slots. The checksum test is then one
# SHA-256 of the entropy bytes. ~5-8x faster than calling mnemonic_checksum_ok().
import hashlib
_S = None; _SPLIT = 0; _FREE = None; _FIXED = 0; _NW = 0; _CS = 0; _ENTB = 0; _MASK = 0
def _einit(slots, split):
    global _S, _SPLIT, _FREE, _FIXED, _NW, _CS, _ENTB, _MASK
    _S = slots; _SPLIT = split; _NW = len(slots)
    total = _NW * 11; _CS = total // 33; _ENTB = (total - _CS) // 8; _MASK = (1 << _CS) - 1
    _FREE = [i for i in range(_NW) if len(slots[i]) > 1 and i != split]
    _FIXED = 0
    for i, p in enumerate(slots):
        if len(p) == 1:
            _FIXED |= blm.WIDX[p[0]] << (11 * (_NW - 1 - i))
def _enum(val):
    base = _FIXED | (blm.WIDX[val] << (11 * (_NW - 1 - _SPLIT)))
    shifts = [11 * (_NW - 1 - i) for i in _FREE]
    pools = [[blm.WIDX[w] for w in _S[i]] for i in _FREE]
    sha = hashlib.sha256; cs = _CS; entb = _ENTB; mask = _MASK; nw = _NW
    ok = []
    for combo in itertools.product(*pools):
        bits = base
        for c, sh in zip(combo, shifts): bits |= c << sh
        ent = bits >> cs
        if (sha(ent.to_bytes(entb, "big")).digest()[0] >> (8 - cs)) == (bits & mask):
            ok.append([(bits >> (11 * (nw - 1 - i))) & 2047 for i in range(nw)])
    return np.array(ok, dtype=np.uint16).reshape(-1, nw)

# ---- CPU derivation workers ----
def _derive(arr):
    hits = []
    for row in arr:
        mn = " ".join(blm.WORDLIST[i] for i in row)
        p = solve.bulk_check(blm.mnemonic_to_seed(mn))
        if p: hits.append((mn, p))
    return len(arr), hits


def run(tmpl):
    from gpu_proc import GPUProc
    mode = os.environ["BLM_PATHS"]
    NADDR = {"n2": 2, "n32": 32}
    g = GPUProc(mode="narrow", n_addr=NADDR[mode]) if mode in NADDR else GPUProc(mode="wide")
    slots = solve.parse_template(tmpl)
    total = 1
    for p in slots: total *= len(p)
    split = max(range(len(slots)), key=lambda i: len(slots[i]))
    n_enum = int(os.environ.get('BLM_ENUM', '2')); n_cpu = max(1, int(os.environ.get('BLM_DERIVE', str(cpu_count() - n_enum - 1))))
    GPU_INFLIGHT = 3; CPU_INFLIGHT = n_cpu * 2
    print(f"[hybrid] paths={mode}  {len(slots)} words, {total:,} combos, {len(slots[split])} enum chunks, "
          f"{n_enum} enum + {n_cpu} CPU-derive workers, GPU in-flight {GPU_INFLIGHT}, CPU in-flight {CPU_INFLIGHT}")
    t0 = time.time(); seeds_gpu = seeds_cpu = 0; hits = 0; done = 0
    gpu_jobs = {}      # job_id -> tuples
    cpu_jobs = []      # (AsyncResult, tuples)

    def reap(block=False):
        nonlocal seeds_gpu, seeds_cpu, hits
        for jid, res in g.collect(timeout=0.05 if block else 0):
            arr = gpu_jobs.pop(jid); seeds_gpu += len(arr)
            for j in np.nonzero(res)[0]:
                solve.record(" ".join(blm.WORDLIST[i] for i in arr[j]), g.paths[int(res[j]) - 1], f"[gpu-{mode}]"); hits += 1
        keep = []
        for r, arr in cpu_jobs:
            if r.ready():
                n, h = r.get(); seeds_cpu += n
                for mn, p in h: solve.record(mn, p, f"[cpu-{mode}]"); hits += 1
            else:
                keep.append((r, arr))
        cpu_jobs[:] = keep

    def dispatch(sl, cpool):
        """Give one slice to whichever sink has capacity; wait (reaping) if both are full."""
        while True:
            if len(gpu_jobs) < GPU_INFLIGHT:
                gpu_jobs[g.submit(sl)] = sl; return
            if len(cpu_jobs) < CPU_INFLIGHT:
                cpu_jobs.append((cpool.apply_async(_derive, (sl,)), sl)); return
            reap(block=True)

    def status():
        el = max(time.time() - t0, 1e-9)
        sys.stderr.write(f"\r[hybrid] {done:,}/{total:,}  gpu {seeds_gpu:,}  cpu {seeds_cpu:,}  "
                         f"total {(seeds_gpu + seeds_cpu) / el:,.0f} seeds/s  gpu-inflight {len(gpu_jobs)} cpu-inflight {len(cpu_jobs)}  "
                         f"gpu-batch {g.batch} kills {g.kills} hangs {g.hangs}   ")

    with Pool(n_enum, _einit, (slots, split)) as epool, Pool(n_cpu) as cpool:
        for arr in epool.imap_unordered(_enum, slots[split], chunksize=1):
            done += total // len(slots[split])
            for k in range(0, len(arr), SLICE):
                dispatch(arr[k:k + SLICE], cpool)
                reap()
            status()
        while gpu_jobs or cpu_jobs:
            reap(block=True); status()
    g.close()
    el = time.time() - t0
    print(f"\n[hybrid] done in {el:.0f}s: {seeds_gpu + seeds_cpu:,} seeds ({seeds_gpu:,} gpu / {seeds_cpu:,} cpu), "
          f"{hits} hits, {(seeds_gpu + seeds_cpu) / el:,.0f} seeds/s overall, {g.kills} gpu kills, {g.hangs} gpu restarts")


if __name__ == "__main__":
    a = sys.argv[1]
    run(open(a).read().strip() if os.path.exists(a) else a)
