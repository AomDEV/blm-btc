
---

# Part 4 — derivation paths and GPU

## Derivation-path audit (all earlier negatives are conditional)
Every bulk search before this point tested 25 addresses per seed — the BIP44,
`m/0'` and `m/0` families at index **0-3 only**, empty passphrase. Real gaps for
a 2020 puzzle producing a `1...` address: iancoleman.io/bip39 (the usual tool,
and the only common one that generates 21-word phrases) shows the first **20**
addresses; BIP44 account 1 and the all-hardened `m/0'/0'/i'` were untested; and a
BIP39 passphrase is untestable by brute force. BIP49/84 cannot produce a `1...`
address, so those gaps do not matter.

A **wide** set (101 addresses per seed: BIP44 acct-0 receive 0-19, acct-0 change
and acct-1 0-9, `m/0'`/`m/0` families, all-hardened, master) was built at 3.48
ms/seed and positive-controlled at four paths the narrow set could not see. The
two best-motivated frames are re-running on it.

## GPU (Apple M1, OpenCL)
Built on the secp256k1 + BIP32 OpenCL kernels from `johncantrell97/bip39-solver-gpu`
(whose Rust host no longer compiles), with a new kernel that takes word-index
tuples of any BIP39 length, fixes the HMAC key pre-hash for mnemonics over 128
bytes (21/24-word phrases), derives `m/44'/0'/0'/0/i`, and compares hash160.

**Apple's cl2Metal silently kills launches** (returns zeros, fast) when the
work-group is small or the launch exceeds ~3 s. Early throughput numbers of
250k seeds/s were artefacts of killed kernels. Fixes: work-group pinned to 32,
adaptive batch (halves on a kill), and an **embedded canary** — a known mnemonic
carried in every launch against a second target — so a killed launch is refused,
never counted as a negative. Selftest: 7/7 controls including 188- and 215-byte
mnemonics and a hit planted at the last row of two full launches.

**Verified throughput: ~2,200-2,600 seeds/s at 20 addresses.** Decomposition:
PBKDF2 0.25 ms/seed on the whole GPU vs 0.52 ms on one CPU core — the GPU's
PBKDF2 is ~4x slower than the 8 CPU cores, because Apple GPUs have no native
64-bit integer ALU and BIP39's PBKDF2 is 4,096 rounds of 64-bit SHA-512. EC
leaves cost ~5.5 us each, parity with the CPU.

**Verdict:** on this hardware the GPU is an extra ~+40% concurrent worker, not a
multiplier. For calibration, the community's RTX 3060 CUDA run logged ~9,800
seeds/s on the full pipeline — ~4x this M1 GPU and only ~1.5x this 8-core CPU.
BIP39 is PBKDF2-bound by design; no consumer GPU turns this into a fast search.
The bottleneck remains word selection.
