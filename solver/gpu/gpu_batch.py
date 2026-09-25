"""Run a template file on the GPU: CPU workers enumerate + checksum-filter, the
GPU derives. Same template syntax as solve.py (word | ? | {a|b|c}). Hits go to
../HIT.txt tagged [gpu]. Every launch is canary-verified (see gpu.py)."""
import sys, os, time, itertools
import numpy as np
from multiprocessing import Pool, cpu_count
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import blm, solve

_S = None; _SPLIT = 0; _REST = None
def _init(slots, split):
    global _S, _SPLIT, _REST
    _S = slots; _SPLIT = split; _REST = [i for i in range(len(slots)) if i != split]

def _chunk(val):
    """Enumerate one chunk, return checksum-valid word-index tuples as uint16 (k, NW)."""
    words = [p[0] for p in _S]; words[_SPLIT] = val
    ok = []
    for combo in itertools.product(*[_S[i] for i in _REST]):
        for i, w in zip(_REST, combo): words[i] = w
        if blm.mnemonic_checksum_ok(words):
            ok.append([blm.WIDX[w] for w in words])
    return np.array(ok, dtype=np.uint16).reshape(-1, len(_S))

def run(tmpl, n_addr=20):
    from gpu_proc import GPUProc
    slots = solve.parse_template(tmpl)
    total = 1
    for p in slots: total *= len(p)
    split = max(range(len(slots)), key=lambda i: len(slots[i]))
    g = GPUProc(mode="narrow", n_addr=n_addr)
    print(f"[gpu-batch] {len(slots)} words, {total:,} combos, splitting over slot {split} ({len(slots[split])} chunks)")
    t0 = time.time(); done = 0; seeds = 0; hits = 0
    buf = []; nbuf = 0
    def flush():
        nonlocal buf, nbuf, seeds, hits
        if not nbuf: return
        arr = np.vstack(buf); buf = []; nbuf = 0
        res = g.check(arr); seeds += len(arr)
        for j in np.nonzero(res)[0]:
            mn = " ".join(blm.WORDLIST[i] for i in arr[j])
            solve.record(mn, g.paths[int(res[j])-1], f"[gpu-{g.mode}]"); hits += 1
    with Pool(cpu_count(), _init, (slots, split)) as pool:
        for arr in pool.imap_unordered(_chunk, slots[split], chunksize=1):
            done += total // len(slots[split])
            if len(arr):
                buf.append(arr); nbuf += len(arr)
            if nbuf >= g.MAX_BATCH * 4:          # amortise the ~0.35 s per-launch overhead
                flush()
            el = time.time() - t0
            sys.stderr.write(f"\r[gpu-batch] {done:,}/{total:,} combos  {seeds:,} seeds derived  {seeds/max(el,1e-9):,.0f} seeds/s  batch={g.batch} kills={g.kills}   ")
        flush()
    print(f"\n[gpu-batch] done in {time.time()-t0:.1f}s: {seeds:,} seeds, {hits} hits, {g.kills} driver kills recovered")

if __name__ == "__main__":
    run(open(sys.argv[1]).read().strip() if os.path.exists(sys.argv[1]) else sys.argv[1],
        n_addr=int(os.environ.get("BLM_NADDR", "2")))
