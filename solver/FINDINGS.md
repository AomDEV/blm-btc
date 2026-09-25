# BLM 0.2 BTC puzzle — investigation notes

Target: `1KfZGvwZxsvSmemoCmEV75uqcNzYBHjkHZ`
hash160: `ccbd031e54cde2a3189fd59bc49f731367a1779e`

## Status of the prize (checked live)

`total_received = 20,107,284 sat` (0.2011 BTC), **`total_sent = 0`**, 5 incoming txs,
all outputs unredeemed. The puzzle is genuinely still unsolved. Funded
2020-05-10 by tx `fcee21d4…d043`.

## What the picture actually says

The large faint background lettering reads **"FIND THE SEED PHRASE IN THIS ..."**.
So it is a seed-phrase puzzle, as assumed.

### The clock is the ordering mechanism (verified by measurement)

The clock face is drawn *mirrored* (digits are mirror-written; the Great Seal
overlapping it is mirrored too — un-mirroring makes "RERUM COGNOSCERE CAUSAS",
"FIAT IUSTITIA ET PEREAT MUNDUS", "UBI BENE IBI PATRIA" read correctly).

Measured glyph centres and hand angles in the 1600x1200 master, clock centre
≈ (468, 940):

| number | position | angle |
|---|---|---|
| 12 | (295, 880) | 160.9° |
| 1  | (348, 808) | 132.3° |
| 2  | (438, 755) |  99.2° |
| 11 | (288, 975) | 191° |

| hand | tip | angle | lies between | sum |
|---|---|---|---|---|
| **MOON** (labelled) | (325, 843) | 145.9° | 12 and 1 (midpoint 146.6°) | **13** |
| **TOWER** (labelled) | (383, 765) | 115.9° | 1 and 2 (midpoint 115.75°) | **3** |
| third hand (**no label**) | down-left | ~219° | 10 and 11 | **21** |

Both labelled hands sit within 1° of the exact midpoint of their number pair —
this is deliberate, not sloppy drawing. The rune line inside the clock decodes
(per prior work) to "Сумма двух чисел" = **"sum of two numbers"**, which states
the rule outright.

So: **MOON is word 13, TOWER is word 3.** These two are the only seed words
literally written on the image, and they are the anchor for everything else.

### The general rule: each element encodes (word, index)

Applying the same "element tells you its own number" logic:

| # | word | evidence |
|---|---|---|
| 1 | subject | 13th Amendment panel: "Section **1**" and "…any place **subject** to" are the two underlined bits |
| 2 | camera | exactly **two** CCTV cameras |
| 3 | tower | clock hand, 1+2 |
| 4 | mask | **four** masked faces, each in a face-detection box |
| 5 | police | "END POLICE BRUTALITY" is line **5** of the seven-line BLM block |
| 7 | liberty | Statue of Liberty crown has **7** rays |
| 9 | eye | seal's eye sits over clock 4+5 |
| 11 | pyramid | pyramid body sits over clock 5+6 |
| 12 | vote | ".vs." mirrored reads "12"; election panel |
| 13 | moon | clock hand, 12+1 |
| 16 | rifle | **M16**, aimed at the Norinco CQ factory in China |
| 17 | gold | gold chart spans **17** years (Aug 2003 → Sep 2020) |
| 18 | world | "BRAVE NEW WORLD" — the novel has **18** chapters |
| 19 | glove | gloved hand holding a vial marked **CVD19** |
| 20 | second | Leopold **II** with "**XX**" on his head |

That is **15 words**, and 15 is itself a valid BIP39 length — which is why the
15-word orderings are worth testing directly.

### Why the phrase is probably 21 or 24 words, not 12

The recovered index set is {1,2,3,4,5,7,9,11,12,13,16,17,19,20,21}. If the phrase
were 12 words the high indices would have to wrap mod 12, which produces direct
collisions (13→1 collides with subject, 16→4 with mask, 17→5 with police,
19→7 with liberty, 21→9 with eye). No consistent 12-word reading exists.
With 21 or 24 slots there are no collisions at all.

The unlabelled third clock hand points at **21** — either the phrase length, or
a word nobody has identified yet.

### Other observations

* "ONLY real BITCOIN" on the statue base — **real** is written in lower case
  between two capitalised words. Deliberate highlighting; "real" is a BIP39 word.
* The BLM slogan block is colour-coded by line: black / blue / red / green / black.
* "TUESDAY" (the runes above Trump, Gravity Falls cipher) is **not** a BIP39 word,
  so it is a pointer (election day, 3 Nov 2020), not a seed word.
* Likewise "sum", "justice", "free", "new", "star", "king", "four", "five",
  "crown" and "chain" are not in BIP39 and cannot be seed words.
* The claimed "1713 → STOCK" hidden in the COVID graffiti could not be confirmed
  at any zoom level; the repo author says the same.

## Searches run (all negative so far)

The engine was positive-controlled first: a planted seed was recovered
end-to-end by the template search, and all 48 derivation targets round-trip
(24 paths x compressed/uncompressed).

| search | space | result |
|---|---|---|
| repo's own `moon tower food this real subject address total ten black ? ?` | 4,194,304 | **no hit** |
| 12 x 12-word frames, 2-3 slots from a 130-word thematic pool | ~25M | **no hit** |
| 19 x 15-word frames, pooled slots | small | **no hit** |
| 30 x 15-word frames, one slot over the full 2048 wordlist | 61,440 | **no hit** |
| 210 x 15-word frames, two slots over the full wordlist | 880M | *running* |

Each candidate is tested against 24 derivation paths (BIP44 acct 0/1, m/0'/0/i,
m/0/i, chains 0 and 1, i = 0..3, plus bare master), compressed **and**
uncompressed, after a BIP39 checksum filter.

Notable negative: the README's own 15-word table phrase
(`subject camera tower mask police liberty eye black pyramid vote moon rifle
gold glove apple`) **fails the BIP39 checksum outright**, so it cannot be the
answer in that order regardless of derivation path.

## Honest assessment

A full solve is not reachable by brute force from the current hint set. If the
phrase is 24 words we are missing ~9 of them; 2048^9 is ~6e29 candidates.
Even with perfect knowledge of which slots are empty, that is unsearchable.

What *is* reachable, and what this toolkit does:
* exhaustively test any frame with up to ~3 unknown slots over the full wordlist
  (2048^3 ≈ 8.6e9, ~40 h on 8 cores) or unlimited slots over a curated pool;
* full permutation of any 12-word multiset (479M orderings, ~2.7 h on 8 cores).

The productive direction is identifying more (word, index) pairs from the image,
not more compute.

---

# Part 2 — external research (forums, archives, other repos)

## Sources found that the repo does not reference

| source | value |
|---|---|
| `floflo777/open-crypto-puzzles` (blm-brave-new-world-0-2btc) | full negatives ledger, format-fork analysis, oracle tool |
| `rarsn4/blm-0.2btc-analysis` | the most advanced work found: 25.2 billion seed derivations exhausted |
| archived Reddit `r/bitcoinpuzzles/jrr7mo` (Wayback `.json`) | 85 comments incl. the CUDA run analysed below |
| BitcoinTalk 5404767 later pages | RainLarcade's 38-word BIP39-valid inventory |
| `panchpasha/0.2-BTC-Puzzle-script` | community permutation script |

Reddit's live API and pullpush both refuse agent traffic; the Wayback `.json`
snapshot (2026-04-27) was the working route to the comment history.

## A real defect in a widely-cited community negative

Reddit user `tomjohnriddle` posted the output of a CUDA solver:

```
Target: 1KfZGvwZxsvSmemoCmEV75uqcNzYBHjkHZ
Target Hash160: bd031e54cde2a3189fd59bc49f731367a1779eb0
Loaded 12 valid words: subject, camera, food, mask, police, life,
                       liberty, world, moon, black, tower, real
Scan: 479001600 ... Done ... No match.
```

That hash160 is **wrong**. The true value is `ccbd031e…1779e`; the posted value is
the true one **shifted one byte left** (leading `cc` dropped, trailing `b0` added) —
a classic base58 slice-off-by-one. It decodes to `1JEQSw3inxN1FJHFvea2w6h4mAQBLWBxqW`,
not the puzzle address. So that entire 479-million-permutation run could not have
matched **even with the correct words in the correct order**.

The word set is a good one (10 of its 12 words are in the independently
reconstructed index map). It is being re-run here against the correct target —
479,001,600 orderings, 29.9M checksum-valid, ~2h on 8 cores.

## Independent corroboration of the clock analysis

`rarsn4` derives the same parity constraint I did from the geometry:
adjacent clock pairs sum to {3,5,7,9,11,13,15,17,19,21,23} — **always odd** — so
every even slot must come from a count instead (2 cameras, 4 faces, mirrored
`.VS.`=12, M16, XX=20). They also confirm the third hand carries no word
("checked at four contrast settings — a plain wedge, not faint writing"),
matching my own check.

**Where I disagree with `floflo777`.** Their measurement says the TOWER pointer is
at hour 1.48 and MOON at 0.54, and they treat "not a whole hour" as evidence
*against* `tower`=3 and `moon`=13. But 1.48 and 0.54 are within 0.04 of the exact
midpoints 1.5 and 0.5 — which is precisely what the "sum of two adjacent numbers"
rule predicts, and the rune inside the clock states that rule outright. Their
objection that "a 12-position dial has no position 13" misreads the mechanism: 13
is the *sum* 12+1, not a dial position. Our raw measurements agree; only the
interpretation differs, and the sum reading is the one the image itself documents.

## The Electrum fork is closed (measured, not assumed)

`floflo777` ranks "settle BIP39 vs old-Electrum" as a top open lead. It is
settled by vocabulary: **7 of the 15 image-derived words are absent from the
1626-word Electrum v1 list** (camera, police, liberty, pyramid, vote, rifle,
gold). `rarsn4` reports the identical 7-of-15 count independently. An
old-Electrum v1 implementation was built and verified here end-to-end against
Electrum's official test vector (seed hex → MPK → receiving and change
addresses), so the format can be tested — but the word set cannot exist in it.

## State of the art, and what it means

`rarsn4` reports 25,188,563,424 seed derivations exhausted (BIP39 19.8B +
Electrum v2 5.3B) across four paths, indices 0–35, every template length, pools
of 37–80 words, 65 passphrases, and leave-one-out over the whole 2048-word
dictionary at each gap. Their conclusion matches the one reached here
independently: **the bottleneck is word selection, not order, path or compute.**
Six of the nine unfilled slots (6, 8, 14, 18, 22, 24) are even, so they cannot
come from the clock or the pyramid, and no known element supplies a count for
them. That is the genuine hole in the mechanism inventory.

## Claims to discount

* Several Reddit "I solved it / the wallet was empty" posts are unverified and
  self-contradictory; none produced a seed.
* "The coins are on testnet" is false — the mainnet balance is live and unspent.
* `breathe`, `stop`, `war`, `free`, `needle`, `fist`, `new`, `tuesday`, `justice`,
  `slave`, `kill`, `white`, `death`, `money` circulate as candidate words and
  **none is in the BIP39 list**.

---

# Part 3 — the original post and the creator's footprint

## The original post (located)

| field | value |
|---|---|
| permalink | `reddit.com/user/stsh_n/comments/j79zvj/bitcoin_puzzle_2000/` |
| author | `u/stsh_n` (id `t2_8e21t8pj`) |
| title | **"Bitcoin puzzle (2000$)"** |
| body | none — image only |
| image | `i.redd.it/n1x7g8ceaur51.png`, 1600x1200 |
| posted | **2020-10-08 09:25:30 UTC** |
| score / ratio | 6, upvote ratio 0.70 |
| comments | 161 (none by the author) |

Recovered from a Wayback snapshot of the post; Reddit's live API and pullpush
both refuse agent traffic.

## The account is a purpose-built throwaway

| field | value |
|---|---|
| account created | **2020-10-08 09:21:42 UTC** |
| first (only) post | 2020-10-08 09:25:30 UTC |
| **gap** | **228 seconds — 3 min 48 s** |
| post karma | 1 |
| **comment karma** | **0** |
| posts since | none |

The account was created **three minutes and forty-eight seconds** before the
puzzle went up, has never made a single comment anywhere on Reddit, and has
never posted again. There is no social footprint to mine because the publisher
deliberately created none. Any "hint" attributed to the author in a comment
thread is therefore fabricated — a comment karma of 0 makes it impossible for
the author to have replied to anyone, which corroborates `rarsn4`'s finding that
the two accounts most often cited as confirming word positions never posted
about this puzzle at all.

## The timeline has a five-month hole — and it matters

| date | event |
|---|---|
| 2020-05-10 08:01:46 | wallet funded with **exactly** 0.2 BTC |
| 2020-05-25 | George Floyd killed — "05.25.20" is drawn on the hoodie |
| 2020-06-04 | Leopold II bust defaced — the photo the puzzle copies |
| 2020-09-09 | Wikipedia revision the puzzle cites |
| ~2020-09 | gold chart's right-hand end point |
| **2020-10-08 09:21** | **Reddit account created** |
| 2020-10-08 09:25 | puzzle posted |
| 2020-11-03 | US election — "11.03.20" and the "TUESDAY" rune |

**The wallet was funded 15 days before George Floyd died** and 151 days before
the account that published it existed. So the seed phrase was fixed before any
of the BLM imagery the artwork is built from existed. The words cannot have been
chosen to fit the pictures — the pictures were chosen to fit words that already
existed. That supports the one-element-one-word reading and means no amount of
re-reading the 2020 news cycle will suggest words the author did not already
have in May.

It also leaves open whether `stsh_n` is the creator or merely a reposter; the
account gives no way to tell.

## On-chain traces (public chain data)

Funding tx `fcee21d4…d043`, 4 P2SH inputs -> 2 outputs, version 1, locktime 0,
sequence `0xffffffff`:

* the puzzle output is a round **20,000,000 sat**, not a swept remainder;
* the change output `39rEPyWKE9Ej2fQ6XJHdTpHW3qbXsqfA3H` holds 5,080,966 sat and
  has **never been spent in six years** — one transaction, ever;
* input `3HXV7WE8…` was itself funded on 2018-12-30 by a 1-in/62-out batch
  payout, the signature of a custodial withdrawal.

The untouched change is the most telling datum: whoever funded this walked away
from ~0.05 BTC sitting beside the prize. That is consistent with abandonment,
and inconsistent with an active creator monitoring the puzzle.

## The "Charly Palmer" attribution does not hold up

The top-left mark does read **"CHaRLy"** (confirmed at 26x). But no independent
source connects the artist Charly Palmer to this image — searches return only
this repo's own README, so the claim is circular. It also conflicts with the
artwork's construction: the README itself traces the vaccine photo to
BigStockPhoto, the Statue of Liberty and the Pan-African flag to Shutterstock
vectors, and the CCTV cameras to a Getty illustration. A collage assembled from
stock art is not an original work by a professional fine artist. "CHaRLy" is far
more likely the puzzle-maker's own tag. Naming a real, living artist as the
author of an anonymous crypto puzzle on this evidence would be wrong.

The bottom-right monogram occupies roughly 24x24 px; it is genuinely illegible
at native resolution and I will not guess at it. (`rarsn4` reports it upscales
to contradictory readings — "-yi-" under Lanczos, a boxed "ER" via VanceAI —
which is a property of the upscaler, not the image.)

## Image provenance: one file, two uploads

The two images deleted from this repo's history (`4pnq77o0ogy51.png` and
`n1x7g8ceaur51_2.png`) were recovered from git and are **byte-identical** to
`n1x7g8ceaur51.png` (all SHA-256 `d0b04378f75d…a782`). The "several variants
from several sources" are one file. The second upload is a different Reddit
post — r/bitcoinpuzzles, 2020-11-10, by a now-deleted account, asking whether
the puzzle was still valid. No earlier publication of the image was found.

## Ops note: why some completions never notified
Monitors built as `tail -f log | tr '\r' '\n' | grep --line-buffered ...` are
**deaf**: macOS `tr` block-buffers when its stdout is a pipe, so matched lines sit
in tr's buffer until EOF — which a `tail -f` never reaches. Verified directly:
`(echo "BATCH DONE"; sleep 4) | tr | grep` delivers nothing at 2 s and the line
only after the producer closes. This is why the 479M permutation, the narrow
21-word run and others finished without a notification and were only caught by
manual checks. Fix: drop `tr` and grep the raw stream with `--line-buffered`
(the completion lines are `\n`-terminated, so they match as proper lines).

## Search throughput: the two decisions that mattered (2026-09-25, late)

**1. Derivation path: index 0 and 1 only (user decision).** The 113-path wide
scan was ~85% of every seed's cost (EC leaves, ~40 us each on CPU). Measured on
one core: wide-113 ~3.8 ms/seed, narrow-32 ~1.5 ms, **n2 ~0.63 ms**. That is a
~6x per-seed gain before any hardware change. The picture's own hints back the
choice: 44 stars = BIP44, "ONLY real BITCOIN" = coin 0, "FIRST" twice = index 0.
Trade-off, stated once: a seed at index 2-31 is now invisible.

**2. GPU + CPU on one frame (hybrid v2).** The first hybrid driver had a design
bug: it called the GPU synchronously in the main loop, so while the GPU chewed
its slice (~8 s) the CPU workers finished theirs in <1 s and idled; the share
tuner then measured the CPU against wall-clock, judged it slow, and pushed more
work to the GPU - a feedback loop that pinned the GPU share at its ceiling. Result:
CPU 500 seeds/s instead of ~12,000, total 1,800/s - *worse* than wide CPU-only,
with the machine at 477% of 800% CPU. Fixed by making both sinks asynchronous with
bounded in-flight queues (GPU 3 slices, CPU 2x workers) so backpressure balances
the split; the tuner is gone.

**GPU in a child process with a deadline.** Apple's OpenCL->Metal layer showed a
third failure mode beyond "zeros" and "killed": a launch that *never returns*
(`queue.finish()` blocked in C, 0.42 s of CPU after 17 min). No in-process
timeout can catch that, so the GPU worker is now a child process; the parent
detects a hang by in-flight age, kills it, halves the batch, restarts, and
re-submits every job that was in flight. The wide GPU kernel additionally crashed
silently on launch and is not used.

Measured hybrid-v2 throughput on the 47-pool 21-word frame (n2), clean machine,
fast enumeration, 2 enum + 5 derive + GPU: **5,994 seeds/s over the completed run** (1,791,122
seeds in 299 s; 862k GPU / 929k CPU; 3 GPU kills recovered, 0 restarts). Early
readings of ~3,400 were depressed by a crash-looping stdin diagnostic and a hung
selftest still resident; once removed, utilisation reached ~600% of 800%. That is
~2.9x the old wide CPU-only runs on the same frame and ~2.9x the earlier GPU-only
narrow run (853 s). Remaining headroom is the single-threaded coordinator. Next
optimisation, if pursued: move dispatch/reap off the main thread or batch larger
slices to cut per-slice coordination cost.

## Ops note: killing a Pool parent orphans its workers (cost: ~48 min of a 2-core tax)
`pkill -f "batch.py t21c.txt"` killed only the parent. Its 8 spawned Pool workers
have `multiprocessing.spawn` command lines, matched nothing, and ran as orphans
(ppid 1) at ~25% CPU each for 48 minutes - silently contending with every run
launched afterwards, which is why both hybrid runs measured ~7x below their
benchmarks. Detected by `ps` showing ppid=1 python processes with high CPU and a
48:27 uptime. Fix: `run.sh` launches with `setsid` (own process group) and
`stop.sh` kills the whole group; `stop.sh --orphans` sweeps ppid-1 workers.
Follow-up: the first `run.sh` used `setsid`, which does not exist on macOS; it
failed on line 7 and the "started pid" message was the dead subshell's pid - a
launch that never happened, only caught by reading the raw log. Replaced with a
Python `os.setsid(); os.execvp()` shim and verified (launched pid == its pgid;
`stop.sh` kills the group). Rule: after any launch, confirm the program's own
first log line appeared, not just that a pid was returned.

## Ops note: two false "finished" verdicts, same root cause - a bad liveness check
* `pgrep -f "python3 -u gpu.py"` matched nothing because the process's command line
  starts with the framework binary `Python`, not `python3`. "Not found" was read as
  "exited". The unbuffered wide selftest had in fact HUNG for 21 minutes (the same
  never-returns GPU failure). Rule: match on the script name only (`pgrep -f gpu.py`),
  never on the interpreter name.
* A diagnostic run as a stdin script (`python3 - <<EOF`) that starts a spawn Pool
  crash-loops forever (the child re-imports `<stdin>`, which does not exist). It was
  manually backgrounded and kept running at ~2% CPU while I believed it had failed and
  stopped. Rule: never start multiprocessing from a stdin script; write a file.
Both caught only by auditing every ppid-1 Python process by command line.

## Search engine moved to C (2026-09-26)
`solver/c/blmc` replaces the Python/OpenCL hybrid for the CPU side: 15,669 seeds/s C-only,
16,968 seeds/s with the GPU taking 15 % of the space through `gpu/cgpu.py` — 2.8x the
hybrid's 5,994. Details, the four-run table and the validation list are in SWEEP.md
("C engine"). The default runner for any candidate search is now:

    ./run.sh <name> python3 gpu/cgpu.py <template>      # C on 8 threads + GPU, paths n2
    ./run.sh <name> ./c/blmc --wordlist c/english.txt --template <template> --threads 8 --naddr 2   # C only

Rebuild with `c/build.sh` after any change and run `python3 c/test_blmc.py` (must print
ALL PASS on both builds) before trusting a run.
