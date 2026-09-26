"""C engine + GPU: run ONE template with blmc on the CPU cores and the OpenCL kernel on the GPU.

The combo space is split into PARTS equal parts. The GPU takes the first GPU_PARTS of them,
the C engine (blmc) the rest, both on m/44'/0'/0'/0/{0,1} (the n2 decision).

  GPU side:  `blmc --list-bin --part 0..g-1/PARTS` enumerates checksum-valid mnemonics (one C
             thread) and streams them here as raw uint16 word indices - no text formatting on the
             C side and no parsing here, just np.frombuffer. Slices of SLICE rows go to the
             process-isolated GPU worker (GPUProc: canary-verified launches, hang detection,
             restart + re-submit).
  CPU side:  `blmc --part g..PARTS-1/PARTS --threads T` runs on its own.

If the GPU side fails for any reason, its parts are re-run on the CPU afterwards, so coverage is
complete either way. Hits go to ../HIT.txt tagged [gpu-n2] / [blmc].

  python3 cgpu.py TEMPLATE             env: BLM_GPU_SHARE (default 0.46), BLM_THREADS (default 8)
  python3 cgpu.py TEMPLATE@PASSFILE    passphrase sweep on both engines

BLM_GPU_SHARE is the fraction of the combo space given to the GPU and it is machine-specific: on
an M3 (8-core CPU / 10-core GPU) the two engines are close to equal and ~0.46 balances them. The
end-of-run line reports which side finished first and the share that would have balanced it, so a
new machine needs one run to tune. Too high is worse than too low - the GPU then gates the run.
"""
import os, sys, time, subprocess, threading, re
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); SOLVER = os.path.dirname(HERE)
sys.path.insert(0, SOLVER); sys.path.insert(0, HERE)
os.environ.setdefault("BLM_PATHS", "n2")
import blm, solve
from gpu_proc import GPUProc

BLMC = os.path.join(SOLVER, "c", "blmc"); WORDLIST = os.path.join(SOLVER, "c", "english.txt")
SLICE = 4096; GPU_INFLIGHT = 3; PARTS = 100
TARGET = blm.TARGET_H160.hex()            # BLM_TARGET_H160 overrides (tests); the GPU kernel reads the same value


def nwords(tmpl_path):
    return len(open(tmpl_path).read().split())


def run(tmpl_path, passphrase=""):
    share = float(os.environ.get("BLM_GPU_SHARE", "0.46")); threads = int(os.environ.get("BLM_THREADS", "8"))
    g_parts = max(1, min(PARTS - 1, int(round(share * PARTS))))
    gpu_part = f"0..{g_parts - 1}/{PARTS}"; cpu_part = f"{g_parts}..{PARTS - 1}/{PARTS}"
    print(f"[cgpu] gpu parts {gpu_part}  cpu parts {cpu_part}  cpu threads {threads}", flush=True)
    t0 = time.time()

    # ---- CPU side: blmc search on its parts (stderr progress -> our stderr) ----
    cpu_args = ["--passphrase", passphrase] if passphrase else []
    cpu = subprocess.Popen([BLMC, "--wordlist", WORDLIST, "--template", tmpl_path, "--part", cpu_part,
                            "--threads", str(threads), "--naddr", "2", "--target", TARGET] + cpu_args,
                           cwd=SOLVER, stderr=subprocess.PIPE, text=True)
    cpu_stat = {"line": ""}
    def cpu_reader():
        buf = ""
        for ch in iter(lambda: cpu.stderr.read(1), ""):
            if ch in "\r\n":
                if buf.startswith("blmc:") and "seeds/s" in buf: cpu_stat["line"] = buf
                elif buf.strip(): print(buf, flush=True)
                buf = ""
            else: buf += ch
    threading.Thread(target=cpu_reader, daemon=True).start()

    # ---- GPU side: stream survivors from blmc --list into the GPU worker ----
    gpu_seeds = 0; gpu_fed = 0; hits = 0; gpu_err = None; gpu_done_at = None
    g = None
    try:
        g = GPUProc(mode="narrow", n_addr=2, passphrase=passphrase)
        lister = subprocess.Popen([BLMC, "--wordlist", WORDLIST, "--template", tmpl_path, "--list-bin",
                                   "--part", gpu_part, "--threads", "1"], stdout=subprocess.PIPE, bufsize=1 << 20)
        jobs = {}
        def reap(block=False):
            nonlocal gpu_seeds, hits
            for jid, res in g.collect(timeout=0.05 if block else 0):
                arr = jobs.pop(jid); gpu_seeds += len(arr)
                for j in np.nonzero(res)[0]:
                    tag = f"[gpu-n2]{' passphrase=' + repr(passphrase) if passphrase else ''}"
                    solve.record(" ".join(blm.WORDLIST[i] for i in arr[j]), g.paths[int(res[j]) - 1], tag); hits += 1
        def status():
            el = max(time.time() - t0, 1e-9)
            c = re.search(r"(\d+) seeds\s+(\d+) seeds/s", cpu_stat["line"])
            cs = int(c.group(1)) if c else 0
            sys.stderr.write(f"\r[cgpu] gpu {gpu_seeds:,} ({gpu_seeds / el:,.0f}/s, fed {gpu_fed:,}, inflight {len(jobs)}, batch {g.batch}, "
                             f"kills {g.kills} hangs {g.hangs})  cpu {cs:,} ({cs / el:,.0f}/s)  total {(gpu_seeds + cs) / el:,.0f} seeds/s   ")
        last = 0
        if os.environ.get("BLM_CGPU_FAULT"): raise RuntimeError("injected fault (BLM_CGPU_FAULT)")   # exercises the CPU fallback
        nw = nwords(tmpl_path); rec = 2 * nw; buf = b""
        while True:
            chunk = lister.stdout.read(rec * SLICE)
            if not chunk: break
            buf += chunk
            n = len(buf) // rec
            if n:
                arr = np.frombuffer(buf[:n * rec], dtype="<u2").reshape(n, nw)
                buf = buf[n * rec:]
                gpu_fed += n
                while len(jobs) >= GPU_INFLIGHT: reap(block=True)
                jobs[g.submit(arr)] = arr
                reap()
            if time.time() - last > 2: status(); last = time.time()
        if buf: raise RuntimeError(f"blmc --list-bin ended mid-record ({len(buf)} of {rec} bytes)")
        while jobs: reap(block=True); status()
        lister.wait()
        if lister.returncode != 0: raise RuntimeError(f"blmc --list-bin exited {lister.returncode}")
        if gpu_seeds != gpu_fed: raise RuntimeError(f"gpu processed {gpu_seeds} of {gpu_fed} fed")
        gpu_done_at = time.time() - t0         # the GPU is idle from here until the CPU catches up
    except Exception as e:                     # any GPU-side failure: the CPU redoes those parts
        gpu_err = e; print(f"\n[cgpu] GPU side failed ({e!r}); parts {gpu_part} will be re-run on the CPU", flush=True)
    finally:
        if g: g.close()

    # wait for the CPU side, then show its progress line while it finishes
    while cpu.poll() is None:
        time.sleep(2)
        el = max(time.time() - t0, 1e-9)
        sys.stderr.write(f"\r[cgpu] gpu done {gpu_seeds:,}  |  {cpu_stat['line']}  |  {el:.0f}s   ")
    cpu_line = cpu_stat["line"]
    if cpu.returncode != 0: raise SystemExit(f"[cgpu] blmc (cpu) exited {cpu.returncode}")
    c = re.search(r"(\d+) seeds", cpu_line); cpu_seeds = int(c.group(1)) if c else 0
    if gpu_err is not None:
        r = subprocess.run([BLMC, "--wordlist", WORDLIST, "--template", tmpl_path, "--part", gpu_part,
                            "--threads", str(threads), "--naddr", "2", "--target", TARGET] + cpu_args,
                           cwd=SOLVER, stderr=subprocess.PIPE, text=True)
        m = re.search(r"done in [\d.]+s: \d+ combos, (\d+) seeds", r.stderr); cpu_seeds += int(m.group(1)) if m else 0
        print(r.stderr.strip().split("\n")[-1], flush=True)
    el = time.time() - t0
    total = gpu_seeds + cpu_seeds
    print(f"\n[cgpu] done in {el:.0f}s: {total:,} seeds ({gpu_seeds:,} gpu / {cpu_seeds:,} cpu), "
          f"{total / el:,.0f} seeds/s overall{'  (gpu fell back to cpu)' if gpu_err else ''}", flush=True)
    if not gpu_err and gpu_done_at and total:
        # whichever side finished first was idle for the rest of the run: report the share that
        # would have balanced them, so tuning BLM_GPU_SHARE on a new machine takes one run
        grate = gpu_seeds / max(gpu_done_at, 1e-9); crate = cpu_seeds / max(el, 1e-9)
        best = grate / (grate + crate)
        print(f"[cgpu] gpu finished at {gpu_done_at:.0f}s of {el:.0f}s "
              f"({grate:,.0f} gpu seeds/s vs {crate:,.0f} cpu seeds/s) -> BLM_GPU_SHARE={best:.2f} balances them",
              flush=True)
    hit_file = os.environ.get("BLM_HIT_FILE") or os.path.join(SOLVER, "HIT.txt")
    if os.path.exists(hit_file): print("[cgpu] HIT.txt:\n" + open(hit_file).read())


def run_passphrases(tmpl_path, passfile):
    """TEMPLATE@PASSFILE: sweep every passphrase against every checksum-valid mnemonic.

    Both engines participate, and neither re-enumerates per passphrase:
      CPU parts: one `blmc --passfile` process - a single enumeration pass over its parts, each
                 survivor derived once per passphrase, lanes packed with (mnemonic, passphrase).
      GPU parts: enumerated ONCE into memory (the survivor set does not depend on the passphrase),
                 then replayed for each passphrase by swapping the kernel's salt buffer.
    Passphrases longer than GPU.MAX_PASS bytes are left to the CPU, which has no such limit."""
    share = float(os.environ.get("BLM_GPU_SHARE", "0.46")); threads = int(os.environ.get("BLM_THREADS", "8"))
    pws = [l.rstrip("\n") for l in open(passfile, encoding="utf-8") if l.strip()]
    g_parts = max(1, min(PARTS - 1, int(round(share * PARTS))))
    gpu_part = f"0..{g_parts - 1}/{PARTS}"; cpu_part = f"{g_parts}..{PARTS - 1}/{PARTS}"
    print(f"[cgpu] passphrase sweep: {len(pws)} passphrases x {os.path.basename(tmpl_path)}  "
          f"gpu parts {gpu_part}  cpu parts {cpu_part}  cpu threads {threads}", flush=True)
    t0 = time.time()

    # ---- CPU side: one process for the whole sweep ----
    cpu = subprocess.Popen([BLMC, "--wordlist", WORDLIST, "--template", tmpl_path, "--part", cpu_part,
                            "--threads", str(threads), "--naddr", "2", "--target", TARGET,
                            "--passfile", passfile], cwd=SOLVER, stderr=subprocess.PIPE, text=True)
    cpu_stat = {"line": ""}
    def cpu_reader():
        buf = ""
        for ch in iter(lambda: cpu.stderr.read(1), ""):
            if ch in "\r\n":
                if buf.startswith("blmc:") and "seeds/s" in buf: cpu_stat["line"] = buf
                elif buf.strip(): print(buf, flush=True)
                buf = ""
            else: buf += ch
    threading.Thread(target=cpu_reader, daemon=True).start()

    # ---- GPU side ----
    gpu_seeds = 0; hits = 0; gpu_err = None; g = None; gpu_done = []
    try:
        import gpu as _gpu
        long_pw = [p for p in pws if len(p.encode()) > _gpu.GPU.MAX_PASS]
        gpu_pws = [p for p in pws if len(p.encode()) <= _gpu.GPU.MAX_PASS]
        if long_pw:
            print(f"[cgpu] {len(long_pw)} passphrase(s) over {_gpu.GPU.MAX_PASS} B stay on the CPU "
                  f"(kernel salt is one block): {long_pw[0]!r}...", flush=True)
        # enumerate the GPU's parts once - the survivor set is passphrase-independent
        nw = nwords(tmpl_path)
        r = subprocess.run([BLMC, "--wordlist", WORDLIST, "--template", tmpl_path, "--list-bin",
                            "--part", gpu_part, "--threads", "1"], stdout=subprocess.PIPE, check=True)
        if len(r.stdout) % (2 * nw): raise RuntimeError("blmc --list-bin ended mid-record")
        survivors = np.frombuffer(r.stdout, dtype="<u2").reshape(-1, nw)
        print(f"[cgpu] gpu parts enumerated once: {len(survivors):,} survivors "
              f"({len(survivors) * len(gpu_pws):,} derivations to do) in {time.time()-t0:.0f}s", flush=True)
        if os.environ.get("BLM_CGPU_FAULT"): raise RuntimeError("injected fault (BLM_CGPU_FAULT)")  # exercises the CPU fallback
        g = GPUProc(mode="narrow", n_addr=2)
        jobs = {}
        def reap(block=False):
            nonlocal gpu_seeds, hits
            for jid, res in g.collect(timeout=0.05 if block else 0):
                arr, pw = jobs.pop(jid); gpu_seeds += len(arr)
                for j in np.nonzero(res)[0]:
                    solve.record(" ".join(blm.WORDLIST[i] for i in arr[j]), g.paths[int(res[j]) - 1],
                                 f"[gpu-n2] passphrase={pw!r}"); hits += 1
        for pi, pw in enumerate(gpu_pws, 1):
            while jobs: reap(block=True)            # drain before the salt changes
            g.set_passphrase(pw)
            for s0 in range(0, len(survivors), SLICE):
                arr = survivors[s0:s0 + SLICE]
                while len(jobs) >= GPU_INFLIGHT: reap(block=True)
                jobs[g.submit(arr)] = (arr, pw)
                reap()
                el = max(time.time() - t0, 1e-9)
                sys.stderr.write(f"\r[cgpu] pw {pi}/{len(gpu_pws)} {pw!r}  gpu {gpu_seeds:,} "
                                 f"({gpu_seeds/el:,.0f}/s, kills {g.kills} hangs {g.hangs})  "
                                 f"| {cpu_stat['line'][:70]}   ")
        while jobs: reap(block=True)
        gpu_done.append(time.time() - t0)
    except Exception as e:
        gpu_err = e
        print(f"\n[cgpu] GPU side failed ({e!r}); parts {gpu_part} will be re-run on the CPU", flush=True)
    finally:
        if g: g.close()

    while cpu.poll() is None:
        time.sleep(2)
        sys.stderr.write(f"\r[cgpu] gpu done {gpu_seeds:,}  |  {cpu_stat['line']}  |  {time.time()-t0:.0f}s   ")
    if cpu.returncode != 0: raise SystemExit(f"[cgpu] blmc (cpu) exited {cpu.returncode}")
    c = re.search(r"(\d+) seeds", cpu_stat["line"]); cpu_seeds = int(c.group(1)) if c else 0
    if gpu_err is not None:                       # coverage guarantee: the CPU redoes the GPU parts
        r = subprocess.run([BLMC, "--wordlist", WORDLIST, "--template", tmpl_path, "--part", gpu_part,
                            "--threads", str(threads), "--naddr", "2", "--target", TARGET,
                            "--passfile", passfile], cwd=SOLVER, stderr=subprocess.PIPE, text=True)
        m = re.search(r"done in [\d.]+s: \d+ combos, (\d+) seeds", r.stderr); cpu_seeds += int(m.group(1)) if m else 0
        print(r.stderr.strip().split("\n")[-1], flush=True)
    el = time.time() - t0; total = gpu_seeds + cpu_seeds
    print(f"\n[cgpu] passphrase sweep done in {el:.0f}s: {total:,} derivations over {len(pws)} passphrases "
          f"({gpu_seeds:,} gpu / {cpu_seeds:,} cpu), {total/el:,.0f} seeds/s overall"
          f"{'  (gpu fell back to cpu)' if gpu_err else ''}", flush=True)
    if not gpu_err and gpu_done and total:
        grate = gpu_seeds / max(gpu_done[0], 1e-9); crate = cpu_seeds / max(el, 1e-9)
        print(f"[cgpu] gpu finished at {gpu_done[0]:.0f}s of {el:.0f}s "
              f"({grate:,.0f} vs {crate:,.0f} cpu seeds/s) -> BLM_GPU_SHARE={grate/(grate+crate):.2f} balances them",
              flush=True)
    hit_file = os.environ.get("BLM_HIT_FILE") or os.path.join(SOLVER, "HIT.txt")
    if os.path.exists(hit_file): print("[cgpu] HIT.txt:\n" + open(hit_file).read())


if __name__ == "__main__":
    a = sys.argv[1]
    if "@" in a:
        t, pf = a.split("@", 1); run_passphrases(os.path.abspath(t), os.path.abspath(pf))
    else:
        run(os.path.abspath(a))
