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

To run a queue of frames, put one command per line in a list and run it inside one job:

    ./run.sh q3 ./queue.sh queue3.lst        # sequential; stop.sh q3 kills the whole queue
    grep "=== \[" logs/q3.log                # one START/END line per entry, with wall time

Env: `BLM_THREADS` (default 8 — set to the core count), `BLM_GPU_SHARE` (default 0.46 — the
fraction of the space given to the GPU; **machine-specific**, see below), `BLM_TARGET_H160`
(tests only), `BLM_CL_DIR` (override the kernel directory), `BLM_BLMC_ARGS` (extra blmc flags
appended to every blmc call, see "Coverage" below).

## Coverage: what a run tests, and the switches that widen it
Default: paths m/44'/0'/0'/0/{0,1}, **compressed and uncompressed** pubkey hash160 for each
(uncompressed costs 0.6 %; a hit says `key=uncompressed`), BIP39-checksum-valid phrases only,
empty passphrase. The audit of these assumptions and the wallet behaviour behind them is in
SWEEP.md ("what the checker itself could miss"). Widening switches, all through `BLM_BLMC_ARGS`:

    BLM_BLMC_ARGS="--nochecksum" python3 gpu/cgpu.py T.txt   # derive EVERY combo (Electrum's BIP39
                                                            # import accepts invalid checksums): 128x the work
    BLM_BLMC_ARGS="--paths ext"  python3 gpu/cgpu.py T.txt   # + m/44'/0'/0'/1/i, m/44'/0'/1'/0/i, m/0'/0/i,
                                                            # m/0/i, m, m/0'/0'/0'  (1.83x; C only, GPU is
                                                            # switched off because the kernel is std)
    T.txt@passlist.txt                                      # passphrase sweep (one enumeration pass)
    --compressed-only                                       # the pre-audit behaviour, for A/B only

`BLM_GPU_SHARE` matters: too high and the GPU gates the whole run. Every `cgpu.py` run ends with

    [cgpu] gpu finished at 44s of 44s (18,626 vs 21,827 cpu seeds/s) -> BLM_GPU_SHARE=0.46 balances them

so one run is enough to tune a new machine.

## Template syntax
Fixed word | `?` (any of 2048) | `{a|b|c}`. Current frames: `t21*.txt`, `pp.txt`, `pq.txt`
(21-word frames over the position map); `queue3.lst` is the coverage re-run order (ext paths,
passphrase sweeps, checksum-free), `queue2.lst` the older word-frame order (not yet run).
`blmc --count --template T` gives the checksum-valid count before committing to a run.

## The engines, and where the time goes
`blmc --bench` prints the per-component cost on one core. On an M3 (4P+4E, 10-core GPU):

    pbkdf2 x1 :  105.7 ns/block      raw x1 :  79.8 ns/block
    pbkdf2 x2 :   43.9 ns/block      raw x2 :  44.2 ns/block   <- SHA-512 unit saturated at x2
    pbkdf2 x4 :   46.2 ns/block      raw x4 :  42.7 ns/block
    ec derive :   37.9 us/seed  (4 pubkey mults)   pubkey33: 8.7 us each
    enumerate :   56.9 M combos/s

A seed costs ~218 us: **PBKDF2 83%, EC 17%, enumeration 1%**. The GPU kernel runs at 21,528
seeds/s and is 89% PBKDF2; hybrid throughput on this machine is ~42,100 seeds/s. "raw" is the compression loop with
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
