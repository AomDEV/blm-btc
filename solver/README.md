# BLM 0.2 BTC puzzle — solver workspace

Target `1KfZGvwZxsvSmemoCmEV75uqcNzYBHjkHZ` (hash160 `ccbd031e54cde2a3189fd59bc49f731367a1779e`).
Read `FINDINGS.md` (what the picture says, position map, research), `SWEEP.md` (every
measurement and every search, chronological) and `CIPHER.md` (the rune alphabet) first.

## Setup on a new Mac (Apple Silicon)
    git clone --recurse-submodules <this repo>      # BLM_0.2BTC/ is the source repo (pictures)
    brew install openssl@3 secp256k1
    python3 -m pip install numpy scipy pillow coincurve pyopencl
    cd solver/c && ./build.sh && python3 test_blmc.py   # must print ALL PASS on both builds
    cd ../gpu && python3 gpu.py selftest && python3 test_cgpu.py   # kernel + end-to-end, ALL PASS

The 11 OpenCL base kernels are vendored in `gpu/cl/`, so there is no external checkout to find.

## Running a search
    cd solver
    ./run.sh NAME python3 gpu/cgpu.py TEMPLATE.txt              # C engine on all cores + GPU
    ./run.sh NAME python3 gpu/cgpu.py TEMPLATE.txt@passlist.txt # passphrase sweep, both engines
    ./stop.sh NAME                                              # kills the whole process group
    ./stop.sh --orphans                                         # sweep stray ppid-1 workers
    tr '\r' '\n' < logs/NAME.log | tail -3                      # progress; hits -> solver/HIT.txt

To run a queue of frames, loop over them (there is no batch driver any more — the C engine
replaced the Python one):

    for t in t21f3 t21p t21q; do ./run.sh $t python3 gpu/cgpu.py $t.txt; while [ -f logs/$t.pid ] \
      && kill -0 $(cat logs/$t.pid) 2>/dev/null; do sleep 30; done; done

Env: `BLM_THREADS` (default 8 — set to the core count), `BLM_GPU_SHARE` (default 0.46 — the
fraction of the space given to the GPU; **machine-specific**, see below), `BLM_TARGET_H160`
(tests only), `BLM_CL_DIR` (override the kernel directory). Paths searched: m/44'/0'/0'/0/{0,1}.

`BLM_GPU_SHARE` matters: too high and the GPU gates the whole run. Every `cgpu.py` run ends with

    [cgpu] gpu finished at 44s of 44s (18,626 vs 21,827 cpu seeds/s) -> BLM_GPU_SHARE=0.46 balances them

so one run is enough to tune a new machine.

## Template syntax
Fixed word | `?` (any of 2048) | `{a|b|c}`. Current frames: `t21*.txt`, `pp.txt`, `pq.txt`
(21-word frames over the position map); `queue2.lst` is the pending run order.
`blmc --count --template T` gives the checksum-valid count before committing to a run.

## The engines, and where the time goes
`blmc --bench` prints the per-component cost on one core. On an M3 (4P+4E, 10-core GPU):

    pbkdf2 x1 :  105.7 ns/block      raw x1 :  79.8 ns/block
    pbkdf2 x2 :   43.9 ns/block      raw x2 :  44.2 ns/block   <- SHA-512 unit saturated at x2
    pbkdf2 x4 :   46.2 ns/block      raw x4 :  42.7 ns/block
    ec derive :   37.9 us/seed  (4 pubkey mults)   pubkey33: 8.7 us each
    enumerate :   56.9 M combos/s

A seed costs ~218 us: **PBKDF2 83%, EC 17%, enumeration 1%**. "raw" is the compression loop with
no PBKDF2 glue around it; pbkdf2 x2 is within 1% of it, so the SHA-512 unit is the wall and there
is nothing left to win in the hashing. The remaining CPU gains all came out of the other 17%.
Going wider than x2 does not help (the unit saturates at two interleaved streams), which is why
`NWAY` defaults to 2; rebuild with `NWAY=4 ./build.sh` to re-measure on other silicon.

## Direct blmc use
    ./c/blmc --wordlist c/english.txt --template T --threads 8 --naddr 2   # search
    ./c/blmc --template T --passfile passlist.txt                          # sweep, one pass
    ./c/blmc --template T --count | --list | --list-bin                    # sizes / survivors
    ./c/blmc --derive --naddr 2   < mnemonics                              # oracle
    ./c/blmc --bench [--template T]                                        # per-component cost
    ./c/blmc --selftest                                                    # vs OpenSSL
    --part b/n | --part b..c/n       work on part b (to c) of n — how work is split across
                                     the GPU, the CPU, and across machines

`--passfile` sweeps a passphrase list in a **single enumeration pass**: each surviving mnemonic is
derived once per passphrase, with the HMAC key midstate computed once and the lanes packed with
(mnemonic, passphrase) pairs. Blank lines are skipped — the empty passphrase is what a run without
`--passfile` already tests. Hits record the passphrase that produced them.

Rebuild with `c/build.sh` after any change and run `python3 c/test_blmc.py` (ALL PASS on both the
O2 and the ASan+UBSan build) plus `python3 gpu/test_cgpu.py` before trusting a run.
