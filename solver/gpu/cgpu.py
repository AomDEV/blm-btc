"""C engine + GPU: run ONE template with blmc on the CPU cores and the OpenCL kernel on the GPU.

The combo space is split into PARTS equal parts. The GPU takes the first GPU_PARTS of them,
the C engine (blmc) the rest, both on m/44'/0'/0'/0/{0,1} (the n2 decision).

  GPU side:  `blmc --list --part 0..g-1/PARTS` enumerates checksum-valid mnemonics (one C thread,
             ~2M combos/s) and streams them here; slices of SLICE rows go to the process-isolated
             GPU worker (GPUProc: canary-verified launches, hang detection, restart + re-submit).
  CPU side:  `blmc --part g..PARTS-1/PARTS --threads T` runs on its own.

If the GPU side fails for any reason, its parts are re-run on the CPU afterwards, so coverage is
complete either way. Hits go to ../HIT.txt tagged [gpu-n2] / [blmc].

  python3 cgpu.py TEMPLATE            env: BLM_GPU_SHARE (default 0.15), BLM_THREADS (default 8)
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


def run(tmpl_path):
    share = float(os.environ.get("BLM_GPU_SHARE", "0.15")); threads = int(os.environ.get("BLM_THREADS", "8"))
    g_parts = max(1, min(PARTS - 1, int(round(share * PARTS))))
    gpu_part = f"0..{g_parts - 1}/{PARTS}"; cpu_part = f"{g_parts}..{PARTS - 1}/{PARTS}"
    print(f"[cgpu] gpu parts {gpu_part}  cpu parts {cpu_part}  cpu threads {threads}", flush=True)
    t0 = time.time()

    # ---- CPU side: blmc search on its parts (stderr progress -> our stderr) ----
    cpu = subprocess.Popen([BLMC, "--wordlist", WORDLIST, "--template", tmpl_path, "--part", cpu_part,
                            "--threads", str(threads), "--naddr", "2", "--target", TARGET], cwd=SOLVER, stderr=subprocess.PIPE, text=True)
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
    gpu_seeds = 0; gpu_fed = 0; hits = 0; gpu_err = None
    g = None
    try:
        g = GPUProc(mode="narrow", n_addr=2)
        lister = subprocess.Popen([BLMC, "--wordlist", WORDLIST, "--template", tmpl_path, "--list", "--part", gpu_part,
                                   "--threads", "1"], stdout=subprocess.PIPE, text=True, bufsize=1 << 16)
        jobs = {}
        def reap(block=False):
            nonlocal gpu_seeds, hits
            for jid, res in g.collect(timeout=0.05 if block else 0):
                arr = jobs.pop(jid); gpu_seeds += len(arr)
                for j in np.nonzero(res)[0]:
                    solve.record(" ".join(blm.WORDLIST[i] for i in arr[j]), g.paths[int(res[j]) - 1], "[gpu-n2]"); hits += 1
        def status():
            el = max(time.time() - t0, 1e-9)
            c = re.search(r"(\d+) seeds\s+(\d+) seeds/s", cpu_stat["line"])
            cs = int(c.group(1)) if c else 0
            sys.stderr.write(f"\r[cgpu] gpu {gpu_seeds:,} ({gpu_seeds / el:,.0f}/s, fed {gpu_fed:,}, inflight {len(jobs)}, batch {g.batch}, "
                             f"kills {g.kills} hangs {g.hangs})  cpu {cs:,} ({cs / el:,.0f}/s)  total {(gpu_seeds + cs) / el:,.0f} seeds/s   ")
        rows = []; last = 0
        if os.environ.get("BLM_CGPU_FAULT"): raise RuntimeError("injected fault (BLM_CGPU_FAULT)")   # exercises the CPU fallback
        for line in lister.stdout:
            w = line.split()
            if not w: continue
            rows.append([blm.WIDX[x] for x in w]); gpu_fed += 1
            if len(rows) >= SLICE:
                while len(jobs) >= GPU_INFLIGHT: reap(block=True)
                arr = np.array(rows, dtype=np.uint16); jobs[g.submit(arr)] = arr; rows = []
                reap()
            if time.time() - last > 2: status(); last = time.time()
        if rows:
            while len(jobs) >= GPU_INFLIGHT: reap(block=True)
            arr = np.array(rows, dtype=np.uint16); jobs[g.submit(arr)] = arr
        while jobs: reap(block=True); status()
        lister.wait()
        if lister.returncode != 0: raise RuntimeError(f"blmc --list exited {lister.returncode}")
        if gpu_seeds != gpu_fed: raise RuntimeError(f"gpu processed {gpu_seeds} of {gpu_fed} fed")
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
                            "--threads", str(threads), "--naddr", "2", "--target", TARGET], cwd=SOLVER, stderr=subprocess.PIPE, text=True)
        m = re.search(r"done in [\d.]+s: \d+ combos, (\d+) seeds", r.stderr); cpu_seeds += int(m.group(1)) if m else 0
        print(r.stderr.strip().split("\n")[-1], flush=True)
    el = time.time() - t0
    print(f"\n[cgpu] done in {el:.0f}s: {gpu_seeds + cpu_seeds:,} seeds ({gpu_seeds:,} gpu / {cpu_seeds:,} cpu), "
          f"{(gpu_seeds + cpu_seeds) / el:,.0f} seeds/s overall{'  (gpu fell back to cpu)' if gpu_err else ''}", flush=True)
    hit_file = os.path.join(SOLVER, "HIT.txt")
    if os.path.exists(hit_file): print("[cgpu] HIT.txt:\n" + open(hit_file).read())


def run_passphrases(tmpl_path, passfile):
    """TEMPLATE@PASSFILE: run the template once per passphrase line, C engine only (the GPU
    kernel has the empty-passphrase salt hard-coded). Hits are tagged with the passphrase."""
    threads = int(os.environ.get("BLM_THREADS", "8")); t0 = time.time(); total = 0
    lines = [l.rstrip("\n") for l in open(passfile, encoding="utf-8") if l.strip()]
    print(f"[cgpu] passphrase mode: {len(lines)} passphrases x {os.path.basename(tmpl_path)}, C only, {threads} threads", flush=True)
    for i, pw in enumerate(lines, 1):
        r = subprocess.run([BLMC, "--wordlist", WORDLIST, "--template", tmpl_path, "--threads", str(threads), "--naddr", "2",
                            "--target", TARGET, "--passphrase", pw], cwd=SOLVER, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        m = re.search(r"done in ([\d.]+)s: \d+ combos, (\d+) seeds, (\d+) hits", r.stderr)
        seeds = int(m.group(2)) if m else 0; hits = int(m.group(3)) if m else -1; total += seeds
        print(f"[cgpu] {i}/{len(lines)} passphrase {pw!r}: {seeds:,} seeds, {hits} hits, {float(m.group(1)) if m else 0:.0f}s", flush=True)
        if hits:
            with open(os.path.join(SOLVER, "HIT.txt"), "a") as f: f.write(f"    (passphrase {pw!r})\n")
            print(r.stdout, flush=True)
    print(f"\n[cgpu] passphrase sweep done in {time.time() - t0:.0f}s: {total:,} seeds over {len(lines)} passphrases", flush=True)


if __name__ == "__main__":
    a = sys.argv[1]
    if "@" in a:
        t, pf = a.split("@", 1); run_passphrases(os.path.abspath(t), os.path.abspath(pf))
    else:
        run(os.path.abspath(a))
