# BLM 0.2 BTC puzzle — solver workspace

Target `1KfZGvwZxsvSmemoCmEV75uqcNzYBHjkHZ` (hash160 `ccbd031e54cde2a3189fd59bc49f731367a1779e`).
Read `FINDINGS.md` (what the picture says, position map, research), `SWEEP.md` (every
measurement and every search, chronological) and `CIPHER.md` (the rune alphabet) first.

## Setup on a new Mac (Apple Silicon)
    git clone --recurse-submodules <this repo>      # BLM_0.2BTC/ is the source repo (pictures)
    brew install openssl@3 secp256k1
    python3 -m pip install numpy scipy pillow coincurve pyopencl
    cd solver/c && ./build.sh && python3 test_blmc.py   # must print ALL PASS on both builds
    cd ../gpu && python3 gpu.py selftest                  # OpenCL kernel canary check

## Running a search (always through the GPU script, per the standing rule)
    cd solver
    ./run.sh NAME python3 gpu/cgpu.py TEMPLATE.txt              # C engine on all cores + GPU slice
    ./run.sh NAME python3 gpu/cgpu.py TEMPLATE.txt@passlist.txt # passphrase sweep (C only)
    ./stop.sh NAME                                              # kills the whole process group
    tr '\r' '\n' < logs/NAME.log | tail -3                      # progress; hits -> solver/HIT.txt
Env: `BLM_THREADS` (default 8 — set to the core count, e.g. 10 on an M4), `BLM_GPU_SHARE`
(default 0.15), `BLM_TARGET_H160` (tests only). Paths searched: m/44'/0'/0'/0/{0,1}.

Template syntax: fixed word | `?` (any of 2048) | `{a|b|c}`. Current frames: `t21*.txt`
(21-word frames over the position map), `queue2.lst` = the pending run order on the M1.
`blmc --count --template T` gives the checksum-valid count before committing to a run.
