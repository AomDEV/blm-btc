#!/usr/bin/env python3
"""End-to-end tests for the GPU path and the cgpu driver.

  1. gpu.py selftest     positive controls on 5 mnemonic shapes + negative control (kernel maths)
  2. passphrase          a planted hit found WITH a passphrase, and missed without it
  3. plain run           TEMPLATE with no passfile - the README's default command
  4. cgpu sweep          TEMPLATE@PASSFILE: hit in the GPU's parts is found by the GPU and tagged
  5. coverage            derivations == survivors x passphrases, counted across both engines
  6. fault fallback      BLM_CGPU_FAULT: the GPU's parts are re-run on the CPU, hit still found

Needs pyopencl and a GPU; skips cleanly (exit 0) if the GPU is unavailable.
"""
import os, sys, re, random, subprocess, itertools, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); SOLVER = os.path.dirname(HERE)
sys.path.insert(0, SOLVER); sys.path.insert(0, HERE)
import blm, solve
H = blm.HARD
TMP = tempfile.mkdtemp(prefix="cgpu_test_")
fails = 0

def report(name, ok, extra=""):
    global fails; fails += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  ' + extra) if extra else ''}")

try:
    import pyopencl as cl
    cl.Context(dev_type=cl.device_type.GPU)
except Exception as e:
    print(f"[cgpu-test] no usable OpenCL GPU ({e!r}) - skipping"); sys.exit(0)

KNOWN = "legal winner thank year wave sausage worth useful legal winner thank yellow".split()
PW = "secretX"

def build_case():
    """A 12-word frame whose winning combo is index 0, so it lands in the GPU's parts."""
    random.seed(9)
    first = lambda w, n: [w] + random.sample([x for x in blm.WORDLIST if x != w], n - 1)
    tmpl = " ".join(KNOWN[:9] + ["{" + "|".join(first("winner", 24)) + "}", KNOWN[10],
                                 "{" + "|".join(first("yellow", 24)) + "}"])
    t = f"{TMP}/t.txt"; open(t, "w").write(tmpl)
    p = f"{TMP}/p.txt"; open(p, "w").write("alpha\nTUESDAY\n" + PW + "\n")
    tgt = blm.h160s(blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(KNOWN), PW)),
                               (44 | H, 0 | H, 0 | H, 0, 1)))[0].hex()
    nvalid = sum(blm.mnemonic_checksum_ok(list(c)) for c in itertools.product(*solve.parse_template(tmpl)))
    return t, p, tgt, nvalid

def test_gpu_selftest():
    r = subprocess.run([sys.executable, f"{HERE}/gpu.py", "selftest"], capture_output=True, text=True)
    report("gpu.py selftest (kernel maths, 5 shapes + negative control)",
           "SELFTEST PASSED" in r.stdout, [l for l in r.stdout.split("\n") if "bench" in l][-1:] and
           [l for l in r.stdout.split("\n") if "bench" in l][-1].strip() or "")

def test_passphrase_kernel():
    import numpy as np
    from gpu import GPU
    g = GPU(n_addr=2, verbose=False, passphrase=PW)
    row = np.array([[blm.WIDX[w] for w in KNOWN]], dtype=np.uint16)
    node = blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(KNOWN), PW)), (44 | H, 0 | H, 0 | H, 0, 1))
    g.set_target(blm.h160s(node)[0])
    hit = int(g.check(row)[0])
    g.set_passphrase("")                      # same row, no passphrase: must now miss
    miss = int(g.check(row)[0])
    report("kernel passphrase: hit with it, miss without", hit == 2 and miss == 0, f"hit={hit} miss={miss}")

def test_uncompressed_kernel():
    """Target = hash160 of the UNCOMPRESSED pubkey: the kernel must hit with the UNC flag; a
    compressed target must hit without it; the same row against an unrelated target must miss."""
    import numpy as np
    from gpu import GPU, UNC_FLAG, PATH_MASK, hit_name
    g = GPU(n_addr=2, verbose=False)
    row = np.array([[blm.WIDX[w] for w in KNOWN]], dtype=np.uint16)
    node = blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(KNOWN))), (44 | H, 0 | H, 0 | H, 0, 1))
    c, u = blm.h160s(node)
    g.set_target(u); r_u = int(g.check(row)[0])
    g.set_target(c); r_c = int(g.check(row)[0])
    g.set_target(bytes(20)); r_0 = int(g.check(row)[0])
    ok = (r_u == (UNC_FLAG | 2) and r_c == 2 and r_0 == 0
          and hit_name(g.paths, r_u) == "m/44h/0h/0h/0/1 key=uncompressed" and hit_name(g.paths, r_c) == "m/44h/0h/0h/0/1")
    report("kernel: uncompressed-key hit flagged, compressed hit plain, unrelated target misses", ok,
           f"unc={r_u:#x} comp={r_c} none={r_0}")

def run_cgpu(t, p, tgt, share, fault=False, extra=""):
    """BLM_HIT_FILE keeps planted test hits out of solver/HIT.txt - that file is the one artifact
    this project exists to produce, and the README tells people to run this suite during setup."""
    hitf = f"{TMP}/HIT.txt"
    env = dict(os.environ, BLM_TARGET_H160=tgt, BLM_GPU_SHARE=str(share), BLM_THREADS="2",
               BLM_HIT_FILE=hitf, BLM_BLMC_ARGS=extra)
    if fault: env["BLM_CGPU_FAULT"] = "1"
    if os.path.exists(hitf): os.remove(hitf)
    arg = f"{t}@{p}" if p else t
    r = subprocess.run([sys.executable, f"{HERE}/cgpu.py", arg], capture_output=True, text=True, env=env, cwd=SOLVER)
    hits = open(hitf).read() if os.path.exists(hitf) else ""
    if os.path.exists(hitf): os.remove(hitf)
    return r.stdout + r.stderr, hits

def test_sweep(t, p, tgt, nvalid):
    out, hits = run_cgpu(t, p, tgt, 0.60)
    m = re.search(r"done in \d+s: ([\d,]+) derivations over (\d+) passphrases \(([\d,]+) gpu / ([\d,]+) cpu\)", out)
    tot = int(m.group(1).replace(",", "")) if m else -1
    report("sweep: hit found by the GPU and tagged with the passphrase",
           f"passphrase='{PW}'" in hits and "[gpu-n2]" in hits, hits.strip()[:90])
    report("sweep: derivations == survivors x passphrases", tot == nvalid * 3,
           f"{tot} vs {nvalid} x 3" + (f" (gpu {m.group(3)} / cpu {m.group(4)})" if m else ""))

def test_plain_run(t, tgt):
    """The README's default command (no passfile) goes through run(), whose GPU rows are now
    read-only numpy views over the binary feed. A search that finds nothing never executes the
    reap path, so the hit branch needs its own case."""
    tgt0 = blm.h160s(blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(KNOWN))),
                                (44 | H, 0 | H, 0 | H, 0, 1)))[0].hex()   # no passphrase here
    out, hits = run_cgpu(t, None, tgt0, 0.60)
    report("plain run (no passfile): hit found by the GPU over the binary feed",
           "[gpu-n2]" in hits and " ".join(KNOWN) in hits, hits.strip()[:90] or out.strip()[-90:])

def test_plain_run_uncompressed(t):
    """End to end through cgpu.py: the winning combo sits in the GPU's parts and the target is the
    uncompressed-key hash160 - HIT.txt must carry the label from the GPU path."""
    tgt = blm.h160s(blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(KNOWN))),
                               (44 | H, 0 | H, 0 | H, 0, 0)))[1].hex()
    out, hits = run_cgpu(t, None, tgt, 0.60)
    report("plain run: uncompressed-key hit found by the GPU and labelled",
           "[gpu-n2]" in hits and " ".join(KNOWN) in hits and "key=uncompressed" in hits, hits.strip()[:100] or out.strip()[-90:])

def test_nochecksum_run():
    """BLM_BLMC_ARGS=--nochecksum: the feed streams every combo and the kernel derives them all.
    The planted phrase has an INVALID checksum and sits at combo 0 (GPU parts): the default run
    must not find it, the --nochecksum run must, on the GPU side."""
    random.seed(21)
    bad_last = next(w for w in blm.WORDLIST if w != "yellow" and not blm.mnemonic_checksum_ok(KNOWN[:11] + [w]))
    known = KNOWN[:11] + [bad_last]
    first = lambda w, n: [w] + random.sample([x for x in blm.WORDLIST if x != w], n - 1)
    tmpl = " ".join(known[:9] + ["{" + "|".join(first("winner", 12)) + "}", known[10], "{" + "|".join(first(bad_last, 12)) + "}"])
    t = f"{TMP}/t_nochk.txt"; open(t, "w").write(tmpl)
    tgt = blm.h160s(blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(known))), (44 | H, 0 | H, 0 | H, 0, 1)))[0].hex()
    out0, hits0 = run_cgpu(t, None, tgt, 0.60)
    out1, hits1 = run_cgpu(t, None, tgt, 0.60, extra="--nochecksum")
    m = re.search(r"done in \d+s: ([\d,]+) seeds", out1); tot = int(m.group(1).replace(",", "")) if m else -1
    report("--nochecksum via cgpu: invisible by default, found by the GPU with the flag, seeds == combos",
           hits0 == "" and "[gpu-n2]" in hits1 and " ".join(known) in hits1 and tot == 12 * 12,
           f"default={hits0.strip()[:40]!r} flag={hits1.strip()[:60]!r} seeds={tot}")

def test_ext_run(t):
    """BLM_BLMC_ARGS='--paths ext': the GPU is switched off (kernel is std) and blmc takes all
    parts. Target at m/0'/0/0 (uncompressed) must be found and labelled by [blmc]."""
    tgt = blm.h160s(blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(KNOWN))), (0 | H, 0, 0)))[1].hex()
    out0, hits0 = run_cgpu(t, None, tgt, 0.60)
    out1, hits1 = run_cgpu(t, None, tgt, 0.60, extra="--paths ext")
    report("--paths ext via cgpu: GPU off, blmc covers all parts, m/0h/0/0 uncompressed hit labelled",
           hits0 == "" and "[blmc]" in hits1 and "path=m/0h/0/0 key=uncompressed" in hits1 and "GPU off" in out1
           and "gpu parts none" in out1, hits1.strip()[:100] or out1.strip()[-120:])

def test_fault(t, p, tgt, nvalid):
    out, hits = run_cgpu(t, p, tgt, 0.60, fault=True)
    report("injected GPU fault: parts re-run on the CPU, hit still found",
           "GPU side failed" in out and f"passphrase='{PW}'" in hits and "[blmc]" in hits)

t, p, tgt, nvalid = build_case()
print(f"[cgpu-test] frame has {nvalid} checksum-valid mnemonics, 3 passphrases, hit at {PW!r}")
test_gpu_selftest(); test_passphrase_kernel(); test_uncompressed_kernel(); test_plain_run(t, tgt); test_plain_run_uncompressed(t)
test_sweep(t, p, tgt, nvalid); test_fault(t, p, tgt, nvalid); test_nochecksum_run(); test_ext_run(t)
print("ALL PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)
