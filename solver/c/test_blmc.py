#!/usr/bin/env python3
"""Differential tests for blmc against the Python reference (../blm.py, ../solve.py).
Runs every check on both builds (blmc_asan first). Exit code 0 only if everything passes.
  1. --selftest        hardware SHA-256/SHA-512/HMAC/PBKDF2 vs OpenSSL
  2. --derive          seed, master key/chain, 3 addresses vs blm.py (12..24 words)
  3. --list / --count  checksum-survivor set equality vs the Python enumerator
  4. search            planted hits: partial batches (8 threads) and full 4-way batches (1 thread)
"""
import os, sys, random, subprocess, itertools, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import blm, solve
H = blm.HARD
TMP = tempfile.mkdtemp(prefix="blmc_test_")
fails = 0
def report(name, ok, extra=""):
    global fails; fails += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  ' + extra) if extra else ''}")

def run(b, args, **kw):
    return subprocess.run([f"{HERE}/{b}", "--wordlist", f"{HERE}/english.txt"] + args, capture_output=True, text=True, **kw)

def test_selftest(b):
    r = run(b, ["--selftest"])
    report("selftest", r.returncode == 0 and "MISMATCH" not in r.stdout, r.stdout.strip().split("\n")[-1])

def test_derive(b):
    random.seed(11)
    mn = [" ".join(random.choice(blm.WORDLIST) for _ in range(n)) for n in (12, 15, 18, 21, 24) for _ in range(40)]
    mn += [" ".join(["abstract"] * 24), "legal winner thank year wave sausage worth useful legal winner thank yellow"]
    r = run(b, ["--derive", "--naddr", "3"], input="\n".join(mn) + "\n")
    blocks = [x for x in r.stdout.split("end\n") if x.strip()]
    bad = 0
    for m, blk in zip(mn, blocks):
        kv = {}
        for l in blk.strip().split("\n"):
            t = l.split(" "); kv[" ".join(t[:-1])] = t[-1]
        seed = blm.mnemonic_to_seed(m); mk = blm.master_from_seed(seed)
        ok = kv["seed"] == seed.hex() and kv["master_k"] == mk.k.hex() and kv["master_c"] == mk.c.hex()
        for i in range(3): ok &= kv[f"addr {i}"] == blm.h160s(blm.derive(mk, (44 | H, 0 | H, 0 | H, 0, i)))[0].hex()
        bad += not ok
    report("derive vs blm.py", len(blocks) == len(mn) and bad == 0 and "ERROR" not in r.stderr, f"{len(mn) - bad}/{len(mn)} identical")

def test_passphrase(b):
    random.seed(7)
    mn = [" ".join(random.choice(blm.WORDLIST) for _ in range(n)) for n in (12, 21, 24) for _ in range(4)]
    bad = 0
    for pw in ("TUESDAY", "I can't BREATHE", "y" * 150):
        r = run(b, ["--derive", "--naddr", "2", "--passphrase", pw], input="\n".join(mn) + "\n")
        for m, blk in zip(mn, [x for x in r.stdout.split("end\n") if x.strip()]):
            kv = {}
            for l in blk.strip().split("\n"):
                t = l.split(" "); kv[" ".join(t[:-1])] = t[-1]
            seed = blm.mnemonic_to_seed(m, pw); mk = blm.master_from_seed(seed)
            bad += not (kv["seed"] == seed.hex() and kv["addr 1"] == blm.h160s(blm.derive(mk, (44 | H, 0 | H, 0 | H, 0, 1)))[0].hex())
        bad += "ERROR" in r.stderr
    report("derive with --passphrase (short / spaces / 150-byte) vs blm.py", bad == 0)

def test_list(b):
    random.seed(2)
    words = "legal winner thank year wave sausage worth useful legal winner thank yellow".split()
    tmpl = " ".join(words[:9] + ["{" + "|".join(random.sample(blm.WORDLIST, 22)) + "}"] * 3)
    path = f"{TMP}/t_small.txt"; open(path, "w").write(tmpl)
    slots = solve.parse_template(tmpl)
    ref = set(" ".join(c) for c in itertools.product(*slots) if blm.mnemonic_checksum_ok(list(c)))
    out = run(b, ["--template", path, "--list", "--threads", "8"]).stdout
    got = set(l for l in out.split("\n") if l and not l.startswith(("blmc", "total")))
    report("list == python enumerator", got == ref, f"{len(got)} survivors")
    cnt = run(b, ["--template", path, "--count", "--threads", "8"]).stdout.strip()
    report("count", cnt == f"total {22**3} valid {len(ref)}", cnt)

def test_plant(b):
    random.seed(3)
    known = "legal winner thank year wave sausage worth useful legal winner thank yellow".split()
    def pool(w, n, first):
        r = random.sample([x for x in blm.WORDLIST if x != w], n - 1); return [w] + r if first else r + [w]
    tgt = blm.h160s(blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(known))), (44 | H, 0 | H, 0 | H, 0, 1)))[0].hex()
    A = " ".join(known[:9] + ["{" + "|".join(pool("winner", 16, False)) + "}", known[10], "{" + "|".join(pool("yellow", 16, True)) + "}"])
    B = " ".join(known[:8] + ["{" + "|".join(pool("legal", 16, False)) + "}", "{" + "|".join(pool("winner", 16, False)) + "}", known[10], "{" + "|".join(pool("yellow", 16, False)) + "}"])
    for name, tmpl, thr in (("planted hit, 256 combos, 8 threads", A, 8), ("planted hit, 4096 combos, 1 thread (full 4-way batches)", B, 1)):
        path = f"{TMP}/{name[:11]}.txt"; open(path, "w").write(tmpl)
        hitf = f"{TMP}/HIT.txt"
        if os.path.exists(hitf): os.remove(hitf)
        r = run(b, ["--template", path, "--target", tgt, "--threads", str(thr), "--naddr", "2"], cwd=TMP)
        hits = [l for l in r.stdout.split("\n") if "HIT" in l]
        ok = len(hits) == 1 and "'" + " ".join(known) + "'" in hits[0] and "path=m/44h/0h/0h/0/1" in hits[0] and os.path.exists(hitf) and "ERROR" not in r.stderr
        report(name, ok)
    # negative control: same template, a target that is not there
    r = run(b, ["--template", path, "--target", "00" * 20, "--threads", "8", "--naddr", "2"], cwd=TMP)
    report("no false hit on absent target", "HIT" not in r.stdout)

for b in ("blmc_asan", "blmc"):
    print(f"[{b}]")
    for t in (test_selftest, test_derive, test_passphrase, test_list, test_plant): t(b)
print("ALL PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)
