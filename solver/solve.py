#!/usr/bin/env python3
"""BLM 0.2 BTC puzzle search engine.

Subcommands:
  phrases  <file>            test explicit phrases (wide derivation scan + passphrases)
  template "a b ? d ?"       brute-force '?' slots over the 2048-word list
  permute  "w1 w2 ... wN"    test every ordering of the given words
  subsets  "pool..." -n 12   every N-subset of the pool, every ordering  (big!)
"""
import argparse, itertools, os, sys, time
from multiprocessing import Pool, cpu_count
import blm

# Narrow scan used for bulk work: the paths a puzzle maker realistically uses.
# Structured as (account_prefix, [chains], n_leaves) so shared prefixes derive once.
H = blm.HARD
BULK_TREE = [
    ((44 | H, 0 | H, 0 | H), [(0,), (1,)], 4),   # BIP44 account 0
    ((0 | H,),               [(0,), (1,)], 4),   # Bitcoin-Core style m/0'/0/i
    ((),                     [(0,), (1,)], 4),   # m/0/i
]
BULK_PATHS = [a + c + (i,) for a, cs, n in BULK_TREE for c in cs for i in range(n)]


def _pname(p):
    return "m/" + "/".join(str(x & 0x7fffffff) + ("h" if x & H else "") for x in p) if p else "m"


def bulk_check(seed):
    """Derive the bulk path tree, reusing shared prefixes. Returns path name or None."""
    T = blm.TARGET_H160
    m = blm.master_from_seed(seed)
    c, u = blm.h160s(m)
    if c == T or u == T:
        return "m"
    for acct, chains, nleaf in BULK_TREE:
        node = m
        try:
            for i in acct:
                node = node.ckd(i)
        except Exception:
            continue
        for ch in chains:
            try:
                cn = node
                for i in ch:
                    cn = cn.ckd(i)
            except Exception:
                continue
            for i in range(nleaf):
                try:
                    leaf = cn.ckd(i)
                except Exception:
                    continue
                c, u = blm.h160s(leaf)
                if c == T or u == T:
                    return _pname(acct + ch + (i,))
    return None




# ---- WIDE path set (select with BLM_WIDE=1): closes the derivation-path gaps ----
# iancoleman.io/bip39 shows the first 20 BIP44 addresses; older wallets used m/0'/i and m/0/i;
# Bitcoin-Core style is all-hardened m/0'/0'/i'. Master itself is included.
WIDE_TREE = [
    ((44 | H, 0 | H, 0 | H), [(0,)], 32),        # BIP44 acct 0 receive, i 0..31 (covers the image's 20, 21, 24)
    ((44 | H, 0 | H, 0 | H), [(1,)], 10),        # BIP44 acct 0 change
    ((44 | H, 0 | H, 1 | H), [(0,), (1,)], 10),  # BIP44 acct 1
    ((0 | H,),               [(0,), (1,)], 10),  # m/0'/c/i
    ((),                     [(0,), (1,)], 10),  # m/c/i
]
WIDE_HARD = ((0 | H, 0 | H), 10)                 # m/0'/0'/i'  all-hardened

def bulk_check_wide(seed):
    T = blm.TARGET_H160
    m = blm.master_from_seed(seed)
    c, u = blm.h160s(m)
    if c == T or u == T: return "m"
    for acct, chains, nleaf in WIDE_TREE:
        node = m
        for i in acct: node = node.ckd(i)
        for ch in chains:
            cn = node
            for i in ch: cn = cn.ckd(i)
            for i in range(nleaf):
                c, u = blm.h160s(cn.ckd(i))
                if c == T or u == T: return _pname(acct + ch + (i,))
    pre, n = WIDE_HARD
    node = m
    for i in pre: node = node.ckd(i)
    for i in range(n):
        c, u = blm.h160s(node.ckd(i | H))
        if c == T or u == T: return _pname(pre + (i | H,))
    return None

def bulk_check_n32(seed):
    """m/44'/0'/0'/0/0..31 only - the path the picture's own hints point at (44 stars, 'real', 'first').
    ~1.5 ms/seed vs ~3.8 ms for wide-113: the fast first pass."""
    T = blm.TARGET_H160
    m = blm.master_from_seed(seed)
    a = m.ckd(44 | H).ckd(0 | H).ckd(0 | H).ckd(0)
    for i in range(32):
        c, u = blm.h160s(a.ckd(i))
        if c == T or u == T: return f"m/44h/0h/0h/0/{i}"
    return None

def bulk_check_n2(seed):
    """m/44'/0'/0'/0/0 and /0/1 only. User decision 2026-09-25: no wide scan; fastest first pass."""
    T = blm.TARGET_H160
    a = blm.master_from_seed(seed).ckd(44 | H).ckd(0 | H).ckd(0 | H).ckd(0)
    for i in (0, 1):
        c, u = blm.h160s(a.ckd(i))
        if c == T or u == T: return f"m/44h/0h/0h/0/{i}"
    return None

_paths = os.environ.get("BLM_PATHS", "")
if os.environ.get("BLM_WIDE") == "1" or _paths == "wide":
    bulk_check = bulk_check_wide
elif _paths == "n32":
    bulk_check = bulk_check_n32
elif _paths == "n2":
    bulk_check = bulk_check_n2


HIT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HIT.txt")

def record(mnemonic, path, extra=""):
    line = f"*** HIT *** {mnemonic!r} path={path} {extra}\n"
    sys.stdout.write(line); sys.stdout.flush()
    with open(HIT_FILE, "a") as f: f.write(line)


# ---------------- template ----------------
# Slot syntax:  word          fixed
#               ?             any of the 2048 BIP39 words
#               {a|b|c}       one of these candidates
_T_SLOTS = None; _T_SPLIT = 0; _T_REST = None
def _t_init(slots, split):
    global _T_SLOTS, _T_SPLIT, _T_REST
    _T_SLOTS = slots; _T_SPLIT = split
    _T_REST = [i for i in range(len(slots)) if i != split]

def _t_chunk(val):
    slots = _T_SLOTS; rest = _T_REST
    words = [p[0] for p in slots]
    words[_T_SPLIT] = val
    hits = []
    for combo in itertools.product(*[slots[i] for i in rest]):
        for i, w in zip(rest, combo): words[i] = w
        if not blm.mnemonic_checksum_ok(words): continue
        mn = " ".join(words)
        pth = bulk_check(blm.mnemonic_to_seed(mn))
        if pth: hits.append((mn, pth))
    return hits

def parse_template(tmpl):
    """Return list of per-position candidate lists."""
    toks = tmpl.replace("} ", "}\x00").replace(" {", "\x00{").split()
    out = []
    for t in tmpl.split():
        if t == "?":
            out.append(list(blm.WORDLIST))
        elif t == "@":
            import pool as _pool
            out.append(_pool.build()[0])
        elif t.startswith("{") and t.endswith("}"):
            opts = [w for w in t[1:-1].split("|") if w]
            bad = [w for w in opts if w not in blm.WIDX]
            if bad: raise SystemExit(f"not BIP39 words: {bad}")
            out.append(opts)
        else:
            if t not in blm.WIDX: raise SystemExit(f"not a BIP39 word: {t}")
            out.append([t])
    return out

def run_template(tmpl, label=""):
    slots = parse_template(tmpl)
    total = 1
    for p in slots: total *= len(p)
    nvar = sum(1 for p in slots if len(p) > 1)
    print(f"template{' '+label if label else ''}: {len(slots)} words, {nvar} variable slot(s) -> {total:,} combos")
    if total == 1:
        return run_phrases([" ".join(p[0] for p in slots)])
    split = max(range(len(slots)), key=lambda i: len(slots[i]))
    t0 = time.time(); done = 0
    per = total // len(slots[split])
    with Pool(cpu_count(), _t_init, (slots, split)) as pool:
        for hits in pool.imap_unordered(_t_chunk, slots[split], chunksize=1):
            done += per
            for mn, pth in hits: record(mn, pth)
            el = max(time.time() - t0, 1e-9)
            sys.stderr.write(f"\r{done:,}/{total:,}  {done/el:,.0f}/s  eta {(total-done)/max(done/el,1)/60:.1f}m   ")
            sys.stderr.flush()
    print(f"\ntemplate done in {time.time()-t0:.1f}s")


# ---------------- permute ----------------
_P_WORDS = None
def _p_init(words):
    global _P_WORDS; _P_WORDS = words

def _p_chunk(prefix):
    words = _P_WORDS
    rest = list(words)
    for w in prefix: rest.remove(w)
    hits = []
    for tail in itertools.permutations(rest):
        cand = prefix + tail
        if not blm.mnemonic_checksum_ok(cand): continue
        mn = " ".join(cand)
        p = bulk_check(blm.mnemonic_to_seed(mn))
        if p: hits.append((mn, p))
    return hits

def run_permute(wordstr, fix=2):
    words = wordstr.split()
    n = len(words)
    total = 1
    for i in range(1, n + 1): total *= i
    print(f"permute: {n} words -> {total:,} orderings (~{total//16:,} pass checksum)")
    prefixes = list(dict.fromkeys(itertools.permutations(words, fix)))
    t0 = time.time(); done = 0; per = total // max(len(prefixes), 1)
    with Pool(cpu_count(), _p_init, (words,)) as pool:
        for hits in pool.imap_unordered(_p_chunk, prefixes, chunksize=1):
            done += per
            for mn, p in hits: record(mn, p)
            el = time.time() - t0
            sys.stderr.write(f"\r{done:,}/{total:,}  {done/max(el,1e-9):,.0f}/s  eta {(total-done)/max(done/max(el,1e-9),1)/60:.1f}m")
            sys.stderr.flush()
    print(f"\npermute done in {time.time()-t0:.1f}s")


# ---------------- explicit phrases (wide scan) ----------------
PASSPHRASES = ["", "BLM", "blm", "Black Lives Matter", "black lives matter",
               "CHaRLy", "charly", "bitcoin", "Bitcoin", "1", "12",
               "05.25.20", "11.03.20", "TUESDAY", "tuesday", "order and stability"]

def _ph_one(args):
    mn, pw = args
    if not blm.mnemonic_checksum_ok(mn.split()):
        cs = False
    else:
        cs = True
    r = blm.check_mnemonic(mn, pw, gap=20)
    return (mn, pw, cs, r)

def run_phrases(phrases, passphrases=None):
    pws = passphrases if passphrases is not None else PASSPHRASES
    jobs = [(p, pw) for p in phrases for pw in pws]
    print(f"phrases: {len(phrases)} phrases x {len(pws)} passphrases = {len(jobs):,} tests (wide scan, 301 addrs each)")
    t0 = time.time(); valid = 0
    with Pool(cpu_count()) as pool:
        for i, (mn, pw, cs, r) in enumerate(pool.imap_unordered(_ph_one, jobs, chunksize=4)):
            if cs and pw == "": valid += 1
            if r: record(mn, r[0], f"pass={pw!r} {r[1]}")
            if i % 200 == 0:
                sys.stderr.write(f"\r{i:,}/{len(jobs):,}"); sys.stderr.flush()
    print(f"\nphrases done in {time.time()-t0:.1f}s; {valid} of {len(phrases)} had a valid BIP39 checksum")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["phrases", "template", "permute"])
    ap.add_argument("arg")
    ap.add_argument("--fix", type=int, default=2)
    a = ap.parse_args()
    if a.cmd == "phrases":
        run_phrases([l.strip() for l in open(a.arg) if l.strip() and not l.startswith("#")])
    elif a.cmd == "template":
        run_template(a.arg)
    else:
        run_permute(a.arg, a.fix)
