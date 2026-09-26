"""Process-isolated GPU checker with a hard deadline per launch.

Apple's OpenCL->Metal layer has THREE failure modes for this kernel:
  1. returns all zeros, fast            -> caught by the embedded canary (gpu.py)
  2. kills the launch when it runs long -> caught by the canary, batch halves
  3. NEVER RETURNS (queue.finish() blocks forever in C)  -> nothing in-process can
     catch this: no timeout API, and a blocked C call cannot be interrupted.
So the GPU lives in a child process. The parent waits on a result queue with a
deadline; on timeout it kills the child, halves the batch, restarts, and re-submits.
Same .check() interface as gpu.GPU, so drivers can swap it in unchanged.
"""
import os, sys, time
import numpy as np
import multiprocessing as mp

HERE = os.path.dirname(os.path.abspath(__file__))


def _worker(mode, n_addr, passphrase, inq, outq):
    sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
    import gpu as G
    g = G.GPU(n_addr=n_addr, mode=mode, verbose=False, passphrase=passphrase)
    outq.put(("ready", g.paths, g.batch))
    while True:
        item = inq.get()
        if item is None:
            return
        if item[0] == "passphrase":              # swaps the salt buffer; no program rebuild
            g.set_passphrase(item[1]); outq.put(("passok", item[1])); continue
        job_id, tuples, batch = item
        g.batch = batch
        try:
            res = g.check(tuples)
            outq.put(("ok", job_id, res, g.batch, g.kills))
        except Exception as e:                       # includes GPUKilled after it bottoms out
            outq.put(("err", job_id, repr(e), g.batch, g.kills))


class GPUProc:
    """Drop-in for gpu.GPU: .check(tuples) -> uint32 array, .paths, .mode, .batch, .kills"""
    def __init__(self, mode="narrow", n_addr=32, batch=4096, deadline=None, verbose=True, passphrase=""):
        self.mode, self.n_addr, self.passphrase = mode, n_addr, passphrase
        self.batch = batch if mode == "narrow" else min(batch, 1024)
        self.kills = 0; self.hangs = 0
        self._next = 0; self.inflight = {}
        # deadline: generous multiple of the expected launch time; wide does ~5x the EC work
        self.deadline = deadline or (60 if mode == "narrow" else 120)
        self.verbose = verbose
        self._start()

    def _start(self):
        ctx = mp.get_context("spawn")
        self.inq, self.outq = ctx.Queue(), ctx.Queue()
        self.proc = ctx.Process(target=_worker, args=(self.mode, self.n_addr, self.passphrase, self.inq, self.outq), daemon=True)
        self.proc.start()
        tag, paths, batch = self.outq.get(timeout=180)
        assert tag == "ready"                    # a restart re-creates the worker with self.passphrase
        self.paths = paths
        if self.verbose:
            print(f"[gpu-proc] worker pid {self.proc.pid} ready: mode={self.mode}, {len(self.paths)} paths, batch {self.batch}, deadline {self.deadline}s/launch")

    def _restart(self, why):
        self.hangs += 1
        try:
            self.proc.kill(); self.proc.join(5)
        except Exception:
            pass
        self.batch = max(256, self.batch // 2)
        if self.verbose:
            print(f"\n[gpu-proc] {why}: killed worker, batch -> {self.batch}, restarting; re-submitting {len(self.inflight)} in-flight jobs")
        self._start()
        self._resubmit_all()

    def set_passphrase(self, passphrase):
        """Switch the salt. Caller must have drained every in-flight job first: results already in
        flight were computed with the previous salt."""
        assert not self.inflight, "set_passphrase with jobs in flight"
        self.passphrase = passphrase
        self.inq.put(("passphrase", passphrase))
        tag, got = self.outq.get(timeout=180)
        assert tag == "passok" and got == passphrase

    # ---- non-blocking interface: submit() / collect() ----
    def submit(self, tuples):
        """Queue a tuple array on the GPU worker; returns a job id. Does not block."""
        tuples = np.ascontiguousarray(tuples, dtype=np.uint16)
        self._next += 1; jid = self._next
        self.inflight[jid] = (tuples, time.time())
        self.inq.put((jid, tuples, self.batch))
        return jid

    def collect(self, timeout=0):
        """Return [(job_id, result_array)] for jobs that have finished. Waits up to `timeout`
        seconds for at least one. Detects hung workers by in-flight age and restarts them,
        re-submitting every job that was in flight (a killed worker loses its queue)."""
        out = []
        deadline_at = time.time() + timeout
        while True:
            try:
                msg = self.outq.get(timeout=max(0.0, deadline_at - time.time()) if timeout else 0)
            except Exception:
                msg = None
            if msg is not None:
                tag = msg[0]
                if tag == "ok":
                    _, jid, res, b, k = msg
                    if jid in self.inflight:                # ignore replies from a killed worker
                        self.inflight.pop(jid); out.append((jid, res))
                        self.batch = b; self.kills = k
                elif tag == "err":
                    _, jid, err, b, k = msg
                    self.kills = k
                    self._restart(f"worker error {err}")   # re-submits everything in flight
                if not timeout:
                    continue                               # drain whatever else is ready
            # hang check on the oldest in-flight job
            if self.inflight:
                oldest = min(t for _, t in self.inflight.values())
                if time.time() - oldest > self.deadline * max(1, len(self.inflight)):
                    self._restart(f"oldest launch exceeded {self.deadline}s x {len(self.inflight)} in flight (hung GPU call)")
            if msg is None or timeout == 0 or out:
                break
        return out

    def _resubmit_all(self):
        pending = list(self.inflight.items()); self.inflight = {}
        for _, (tuples, _t) in pending:
            self.submit(tuples)

    def check(self, tuples):
        """Blocking convenience: submit in batch-sized chunks and wait for all."""
        tuples = np.ascontiguousarray(tuples, dtype=np.uint16)
        n = len(tuples); out = np.zeros(n, dtype=np.uint32)
        pos = {}; s = 0
        while s < n:
            jid = self.submit(tuples[s:s + self.batch]); pos[jid] = (s, min(s + self.batch, n)); s += self.batch
        while pos:
            for jid, res in self.collect(timeout=1.0):
                if jid in pos:
                    a, b = pos.pop(jid); out[a:b] = res
            # after a restart the ids changed: map by tuple identity is overkill; instead re-check ordering
            if not pos: break
            missing = [j for j in pos if j not in self.inflight]
            if missing:                                    # jobs re-submitted under new ids
                # rebuild: any job not in flight and not collected must have been re-submitted; re-run remaining
                todo = [pos.pop(j) for j in missing]
                for a, b in todo:
                    jid = self.submit(tuples[a:b]); pos[jid] = (a, b)
        return out

    def close(self):
        try:
            self.inq.put(None); self.proc.join(5)
        except Exception:
            pass
        if self.proc.is_alive():
            self.proc.kill()


if __name__ == "__main__":
    sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
    import blm
    from gpu import words_to_tuple
    mode = os.environ.get("BLM_GPU_MODE", "narrow")
    g = GPUProc(mode=mode, n_addr=32)
    H = blm.HARD
    words = "legal winner thank year wave sausage worth useful legal winner thank yellow".split()
    tests = [((44|H,0|H,0|H,0,7), "m/44h/0h/0h/0/7"), ((44|H,0|H,0|H,0,21), "m/44h/0h/0h/0/21"), ((44|H,0|H,0|H,0,31), "m/44h/0h/0h/0/31")]
    if mode == "wide":
        tests += [((44|H,0|H,1|H,0,3), "m/44h/0h/1h/0/3"), ((0|H,0|H,5|H), "m/0h/0h/5h"), ((0|H,1,8), "m/0h/1/8"), ((1,2), "m/1/2"), ((), "m")]
    ok = True
    for path, name in tests:
        node = blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(words))), path)
        h = blm.h160s(node)[0]
        # set target inside the worker: simplest is an env override before start -> instead plant via a fresh worker per test
        os.environ["BLM_TARGET_H160"] = h.hex()
        g.close(); g = GPUProc(mode=mode, n_addr=32, verbose=False)
        res = g.check(words_to_tuple(words)[None, :])
        got = G.hit_name(g.paths, res[0]) if res[0] else "none"
        print(f"   planted {name:18s} -> {got:18s} {'OK' if got == name else 'FAIL'}")
        ok &= got == name
    g.close()
    print("[gpu-proc] SELFTEST", "PASSED" if ok else "FAILED")
