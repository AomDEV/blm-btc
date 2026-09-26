#!/usr/bin/env python3
"""Differential tests for blmc against the Python reference (../blm.py, ../solve.py).
Runs every check on both builds (blmc_asan first). Exit code 0 only if everything passes.
  1. --selftest        hardware SHA-256/SHA-512/HMAC/PBKDF2 vs OpenSSL
  2. --derive          seed, master key/chain, 3 addresses vs blm.py (12..24 words)
  3. --list / --count  checksum-survivor set equality vs the Python enumerator
  4. search            planted hits: partial batches (8 threads) and full N-way batches (1 thread)
  5. --passfile        planted hit at a non-first passphrase; seeds == survivors x passphrases
"""
import os, sys, re, random, subprocess, itertools, tempfile
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
        for i in range(3):
            c, u = blm.h160s(blm.derive(mk, (44 | H, 0 | H, 0 | H, 0, i)))
            ok &= kv[f"addr {i}"] == c.hex() and kv[f"uaddr {i}"] == u.hex()
        bad += not ok
    report("derive vs blm.py (compressed + uncompressed hash160)", len(blocks) == len(mn) and bad == 0 and "ERROR" not in r.stderr, f"{len(mn) - bad}/{len(mn)} identical")

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

def test_passfile(b):
    """--passfile: one enumeration pass, every survivor x every passphrase.
    Plants the hit at a NON-first passphrase so a bug that only ever applies the first salt,
    or that mislabels which lane a hit came from, cannot pass."""
    random.seed(5)
    known = "legal winner thank year wave sausage worth useful legal winner thank yellow".split()
    pool = lambda w, n: random.sample([x for x in blm.WORDLIST if x != w], n - 1) + [w]
    tmpl = " ".join(known[:9] + ["{" + "|".join(pool("winner", 12)) + "}", known[10],
                                 "{" + "|".join(pool("yellow", 12)) + "}"])
    path = f"{TMP}/t_pass.txt"; open(path, "w").write(tmpl)
    slots = solve.parse_template(tmpl)
    nvalid = sum(blm.mnemonic_checksum_ok(list(c)) for c in itertools.product(*slots))
    others = ["", "TUESDAY", "blm", "I can't BREATHE", "y" * 150, "05.25.20", "CHaRLy", "1865"]
    ok_all = True; detail = []
    # several list lengths and hit positions, so the winning pair lands in both interleave lanes
    for npass, idx in ((7, 4), (6, 3), (5, 1)):
        pw = f"secret{idx}"
        lines = others[:idx] + [pw] + others[idx:npass - 1]
        pf = f"{TMP}/pf_{npass}_{idx}.txt"; open(pf, "w").write("\n".join(lines) + "\n")
        tgt = blm.h160s(blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(known), pw)),
                                   (44 | H, 0 | H, 0 | H, 0, 1)))[0].hex()
        for thr in ("1", "8"):
            hitf = f"{TMP}/HIT.txt"
            if os.path.exists(hitf): os.remove(hitf)
            r = run(b, ["--template", path, "--passfile", pf, "--target", tgt, "--threads", thr, "--naddr", "2"], cwd=TMP)
            hits = [l for l in r.stdout.split("\n") if "HIT" in l]
            good = (len(hits) == 1 and "'" + " ".join(known) + "'" in hits[0]
                    and "path=m/44h/0h/0h/0/1" in hits[0] and f"passphrase='{pw}'" in hits[0]
                    and os.path.exists(hitf) and f"passphrase='{pw}'" in open(hitf).read()
                    and "ERROR" not in r.stderr)
            if not good: ok_all = False; detail.append(f"npass={npass} idx={idx} thr={thr}: {hits}")
    report("planted hit at a non-first passphrase (3 list positions x 1 and 8 threads)", ok_all, "; ".join(detail))
    # arithmetic: every survivor must be tried against every passphrase, exactly once.
    # blmc skips blank lines (a trailing newline must not add an empty-passphrase pass), so count
    # the same way it does - and check below that it really did skip the blank one.
    pf = f"{TMP}/pf_7_4.txt"; lines = [l for l in open(pf).read().split("\n") if l.strip()]
    npass = len(lines)
    r = run(b, ["--template", path, "--passfile", pf, "--target", "00" * 20, "--threads", "8", "--naddr", "2"], cwd=TMP)
    m = re.search(r"done in [\d.]+s: \d+ combos, (\d+) seeds", r.stderr)
    got = int(m.group(1)) if m else -1
    report("seeds == survivors x passphrases (blank lines skipped)", got == nvalid * npass,
           f"{got} vs {nvalid} x {npass}")
    report("no false hit across the whole sweep", "HIT" not in r.stdout)
    # blank/whitespace lines are skipped, so a trailing newline cannot silently double work
    pf2 = f"{TMP}/pf_blank.txt"; open(pf2, "w").write("\n\nTUESDAY\n\n   \nblm\n\n")
    r = run(b, ["--template", path, "--passfile", pf2, "--target", "00" * 20, "--threads", "4", "--naddr", "2"], cwd=TMP)
    m = re.search(r"done in [\d.]+s: \d+ combos, (\d+) seeds", r.stderr)
    got = int(m.group(1)) if m else -1
    report("blank lines in a passfile are skipped", got == nvalid * 2, f"{got} vs {nvalid} x 2")


def test_uncompressed(b):
    """The target is the hash160 of the UNCOMPRESSED pubkey (04||x||y). Default run must find it and
    label it; --compressed-only must miss it (proves the label is not decorative)."""
    random.seed(13)
    known = "legal winner thank year wave sausage worth useful legal winner thank yellow".split()
    pool = lambda w, n: random.sample([x for x in blm.WORDLIST if x != w], n - 1) + [w]
    tmpl = " ".join(known[:9] + ["{" + "|".join(pool("winner", 16)) + "}", known[10], "{" + "|".join(pool("yellow", 16)) + "}"])
    path = f"{TMP}/t_unc.txt"; open(path, "w").write(tmpl)
    tgt = blm.h160s(blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(known))), (44 | H, 0 | H, 0 | H, 0, 0)))[1].hex()
    ok_all = True; detail = []
    for thr in ("1", "8"):
        hitf = f"{TMP}/HIT.txt"
        if os.path.exists(hitf): os.remove(hitf)
        r = run(b, ["--template", path, "--target", tgt, "--threads", thr, "--naddr", "2"], cwd=TMP)
        hits = [l for l in r.stdout.split("\n") if "HIT" in l]
        good = (len(hits) == 1 and "'" + " ".join(known) + "'" in hits[0] and "path=m/44h/0h/0h/0/0" in hits[0]
                and "key=uncompressed" in hits[0] and os.path.exists(hitf) and "key=uncompressed" in open(hitf).read()
                and "ERROR" not in r.stderr)
        if not good: ok_all = False; detail.append(f"thr={thr}: {hits}")
    report("planted UNCOMPRESSED-key hit found and labelled (1 and 8 threads)", ok_all, "; ".join(detail))
    r = run(b, ["--template", path, "--target", tgt, "--threads", "8", "--naddr", "2", "--compressed-only"], cwd=TMP)
    report("--compressed-only misses the uncompressed target", "HIT" not in r.stdout and "compressed-only" in r.stderr)
    # and a compressed target is never reported as uncompressed
    tgt = blm.h160s(blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(known))), (44 | H, 0 | H, 0 | H, 0, 1)))[0].hex()
    r = run(b, ["--template", path, "--target", tgt, "--threads", "8", "--naddr", "2"], cwd=TMP)
    hits = [l for l in r.stdout.split("\n") if "HIT" in l]
    report("compressed hit carries no uncompressed label", len(hits) == 1 and "key=uncompressed" not in hits[0])

def test_nochecksum(b):
    """--nochecksum: every combo is derived. Plant a phrase whose BIP39 checksum is INVALID: the
    default run must not even try it, the --nochecksum run must find it, and --count must equal
    the full space."""
    random.seed(17)
    base = "legal winner thank year wave sausage worth useful legal winner thank yellow".split()
    bad_last = next(w for w in blm.WORDLIST if w != "yellow" and not blm.mnemonic_checksum_ok(base[:11] + [w]))
    known = base[:11] + [bad_last]
    assert not blm.mnemonic_checksum_ok(known)
    pool = lambda w, n: random.sample([x for x in blm.WORDLIST if x != w], n - 1) + [w]
    tmpl = " ".join(known[:9] + ["{" + "|".join(pool("winner", 12)) + "}", known[10], "{" + "|".join(pool(bad_last, 12)) + "}"])
    path = f"{TMP}/t_nochk.txt"; open(path, "w").write(tmpl)
    tgt = blm.h160s(blm.derive(blm.master_from_seed(blm.mnemonic_to_seed(" ".join(known))), (44 | H, 0 | H, 0 | H, 0, 1)))[0].hex()
    r0 = run(b, ["--template", path, "--target", tgt, "--threads", "8", "--naddr", "2"], cwd=TMP)
    report("checksum-invalid phrase is invisible to the default run", "HIT" not in r0.stdout)
    ok_all = True; detail = []
    for thr in ("1", "8"):
        r = run(b, ["--template", path, "--target", tgt, "--threads", thr, "--naddr", "2", "--nochecksum"], cwd=TMP)
        hits = [l for l in r.stdout.split("\n") if "HIT" in l]
        m = re.search(r"done in [\d.]+s: \d+ combos, (\d+) seeds", r.stderr)
        good = (len(hits) == 1 and "'" + " ".join(known) + "'" in hits[0] and "path=m/44h/0h/0h/0/1" in hits[0]
                and "IGNORED" in r.stderr and "ERROR" not in r.stderr)
        if not good: ok_all = False; detail.append(f"thr={thr}: {hits}")
    report("--nochecksum finds it (1 and 8 threads)", ok_all, "; ".join(detail))
    r = run(b, ["--template", path, "--target", "00" * 20, "--threads", "8", "--naddr", "2", "--nochecksum"], cwd=TMP)
    m = re.search(r"done in [\d.]+s: (\d+) combos, (\d+) seeds", r.stderr)
    report("--nochecksum derives every combo (seeds == combos)", m is not None and m.group(1) == m.group(2) == str(12 * 12) and "HIT" not in r.stdout,
           m.group(0) if m else r.stderr[-200:])
    cnt = run(b, ["--template", path, "--count", "--nochecksum", "--threads", "8"]).stdout.strip()
    report("--count --nochecksum == full space", cnt == f"total {12 * 12} valid {12 * 12}", cnt)


def _ppath(s):
    return tuple((int(x[:-1]) | H) if x.endswith("h") else int(x) for x in s.split("/")[1:])

def test_ext(b):
    """--paths ext: every extra derivation vs blm.py (compressed + uncompressed), then a planted hit at
    EACH extra path that the default run must miss and the ext run must find with the right label."""
    random.seed(19)
    mn = [" ".join(random.choice(blm.WORDLIST) for _ in range(n)) for n in (12, 21, 24) for _ in range(6)]
    r = run(b, ["--derive", "--naddr", "2", "--paths", "ext"], input="\n".join(mn) + "\n")
    blocks = [x for x in r.stdout.split("end\n") if x.strip()]
    want = ["m/44h/0h/0h/1/0", "m/44h/0h/0h/1/1", "m/44h/0h/1h/0/0", "m/44h/0h/1h/0/1", "m/0h/0/0", "m/0h/0/1",
            "m/0/0", "m/0/1", "m", "m/0h/0h/0h"]
    bad = 0; n_ext = 0
    for m, blk in zip(mn, blocks):
        mk = blm.master_from_seed(blm.mnemonic_to_seed(m))
        ext = {l.split()[1]: (l.split()[2], l.split()[3]) for l in blk.split("\n") if l.startswith("ext ")}
        if sorted(ext) != sorted(want): bad += 1; continue
        for p, (c, u) in ext.items():
            rc, ru = blm.h160s(blm.derive(mk, _ppath(p)))
            bad += not (c == rc.hex() and u == ru.hex()); n_ext += 1
    report("derive --paths ext vs blm.py (10 extra paths x compressed/uncompressed)", len(blocks) == len(mn) and bad == 0, f"{n_ext} addresses")
    known = "legal winner thank year wave sausage worth useful legal winner thank yellow".split()
    pool = lambda w, n: random.sample([x for x in blm.WORDLIST if x != w], n - 1) + [w]
    tmpl = " ".join(known[:9] + ["{" + "|".join(pool("winner", 12)) + "}", known[10], "{" + "|".join(pool("yellow", 12)) + "}"])
    path = f"{TMP}/t_ext.txt"; open(path, "w").write(tmpl)
    mk = blm.master_from_seed(blm.mnemonic_to_seed(" ".join(known)))
    ok_all = True; detail = []
    for k, p in enumerate(want):
        unc = k % 2 == 1                                  # alternate compressed / uncompressed targets
        tgt = blm.h160s(blm.derive(mk, _ppath(p)))[unc].hex()
        r0 = run(b, ["--template", path, "--target", tgt, "--threads", "4", "--naddr", "2"], cwd=TMP)
        r1 = run(b, ["--template", path, "--target", tgt, "--threads", "4", "--naddr", "2", "--paths", "ext"], cwd=TMP)
        hits = [l for l in r1.stdout.split("\n") if "HIT" in l]
        good = ("HIT" not in r0.stdout and len(hits) == 1 and f"path={p} " in hits[0] + " "
                and (("key=uncompressed" in hits[0]) == unc) and "ERROR" not in r1.stderr)
        if not good: ok_all = False; detail.append(f"{p}: std={'HIT' in r0.stdout} ext={hits}")
    report("planted hit at each ext path: missed by std, found + labelled by --paths ext", ok_all, "; ".join(detail))


for b in ("blmc_asan", "blmc"):
    print(f"[{b}]")
    for t in (test_selftest, test_derive, test_passphrase, test_list, test_plant, test_passfile, test_uncompressed, test_nochecksum, test_ext): t(b)
print("ALL PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)
