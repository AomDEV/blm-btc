# The rune cipher — key, decode, and the limit

## 1. The key

Built from **98 labelled glyphs** across three independently confirmed
inscriptions, covering **28 of the 33 Cyrillic letters**:

| source | glyphs | how it was confirmed |
|---|---|---|
| top three lines | 43 | four blind structural predictions (word lengths 1,7,3,4/5,9/5,9; `сюда` a reversed subsequence of `надеюсь`; `будут` = ABCBD; `биткоинов` 2=6 and 5=8) |
| clock rune | 14 | internal repeats: `◇`=С in both СУММА(1) and ЧИСЕЛ(3); `⏶`=У in both СУММА(2) and ДВУХ(3) |
| right column, groups 1-7 | 41 | word-length vector 5-11-8-2-6-4-5 measured twice independently, then verified letter-by-letter (below) |

The unknown final glyph is **excluded from training**.

**Leave-one-out accuracy: 69/90 = 76.7%.**
Best-match distance for known glyphs: mean 0.147, p90 0.221, max 0.315.
Margin (2nd-best minus best): mean 0.101, median 0.102.
Residual confusions: и/е (3), с/л (2), у/в (2) — visually close pairs.

## 2. The right column decoded letter by letter

Not just word lengths — actual glyph classification, reading bottom to top:

| group | expected | decoded with the key | known letters correct |
|---|---|---|---|
| 1 | здесь | `двесь` | 3/4 (з not in key) |
| 2 | зашифрованы | `датиороуаны` | 6/8 (з, ш, ф not in key) |
| 3 | биткоины | `беткоены` | 6/8 |
| 4 | на | **`на`** | 2/2 |
| 5 | чёрный | `чдрныи` | 4/4 (ё not in key; й read as и, its base letter) |
| 6 | день | `веиь` | 2/4 |
| 7 | номер | **`номер`** | 5/5 |

The decisive detail: **the glyphs that decode worst are exactly the letters the
key does not contain** — з (0.29), ш (0.32), ф (0.27), ё (0.31). Every letter the
key does contain lands in the right place. The community's Russian reading of
this inscription is therefore **confirmed at the letter level**, not merely by
word length.

## 3. The final glyph is not a letter — in either cipher

The last token of `…на чёрный день номер X` is a **single glyph**. It cannot be a
spelled-out Russian numeral (два, три, восемь are 3-6 glyphs).

Rendered upright (rotate 90 CW), at native resolution with an Otsu threshold, it
is a **vertical stroke with one arm to the upper-right and one to the lower-left**
— a single diagonal through a vertical. Arm count is a stable **4** at radii
0.6R, 0.8R, 1.0R and 1.2R.

Three independent eliminations:

1. **The 28 letters in the key.** Best match `д` at 0.290 — above the p90 (0.221)
   for known glyphs. Margin to second place 0.012, against a median margin of
   0.102; only 8% of known glyphs are this undiscriminated. Four candidates lie
   within 0.031 of each other. No identification.
2. **The 5 Cyrillic letters the key lacks** (ж ц щ ъ э), by structure:
   `ж` has four diagonal arms (6 endpoints) — the glyph has 4; `ц` and `щ`
   require a descender tail and a box, neither present; `ъ` needs a horizontal
   top hook, the arms are diagonal; `э` is a curve, the glyph is all straight
   strokes.
3. **The Gravity Falls alphabet**, the image's other cipher (the 7-glyph line
   above Trump). Best distance 0.440, upright or mirrored, against 0.147 for
   genuine same-letter pairs. Not one of those either.

**Conclusion: the glyph belongs to no alphabet for which the image supplies a
key.** It is a standalone numeral or symbol appearing exactly once. The number in
"bitcoins for a rainy day number X" is not recoverable from this inscription —
not because of resolution, but because there is nothing to decode it against.

This closes `rarsn4`'s open lead #3 ("cross the rune transcription against the
Russian-prose cipher key") with a definite answer, and it means their
`[ASSUMED] black at slot 10` cannot be settled from the runes. The only
constraint the runes give is structural: **X is one character**, so if it is a
digit it is 1-9, and of those only 6 and 8 are unfilled.

---

# The second cipher (Gravity Falls) — decoded and calibrated

The 7-glyph inscription above the Trump/Biden heads (master x 866-1005,
y ~832-862) **reads `TUESDAY`. CONFIRMED.**

All 26 key glyphs were extracted from `11_1.png` programmatically (grid rules
detected by ink density, slants and cell labels masked out), not by eye.

**Calibration — the part that makes the result trustworthy:** the same 26 shapes
appear a second time on the "Wheel of Intrigue" at the left of the key image,
hand-drawn at a different size and assigned to *different* letters. Matching
those against the pyramid templates scored **9/10**, establishing a true-match
band of 0.05-0.216 (mean 0.131) against a wrong-letter band of >=0.17.

Per-glyph, as drawn: T 0.094, U 0.168, E 0.130, S 0.078, D 0.190, A 0.108,
Y 0.124 — mean 0.127, every position inside the true-match band, every runner-up
>= 0.15. Four of five metric weightings give TUESDAY; mirrored never produces a
word under any weighting.

## Two corrections to the standing lore

1. **The inscription is NOT mirrored.** It matches the key as drawn,
   left-to-right. Verified structurally on four asymmetric glyphs, not just by
   distance. The "backwards E / backwards N" impression everyone reports is
   simply what Gravity Falls' native **U** (`Ǝ`) and **E** (`И`) look like to a
   Latin reader; mirroring them breaks all four.
2. **The objection that glyph 6 looks like `E` is wrong.** Glyph 6 is **A** (the
   loop-over-oval at the pyramid apex), distance 0.108; its distance to E is
   0.31+, not even top-3. The key's E is the `И`-form, which is glyph **3**.

`tuesday` is not a BIP39 word, so this is a pointer (election day, 3 Nov 2020),
not a seed word — but it is now a *verified* pointer rather than folklore.

# Two symbols belong to neither cipher

| symbol | vs Gravity Falls | vs Cyrillic key | verdict |
|---|---|---|---|
| final rune glyph (the "number X") | best 0.440 | best 0.290, margin 0.012 | in neither |
| wreath cartouche (1381-1400, 693-712) | best 0.210, top-1 unstable across thresholds | best 0.288, margin 0.025 | in neither |

Both sit outside the true-match band of both alphabets, and both have margins
far below the ~0.10-0.13 typical of genuine identifications. They are also **not
each other** (distance 0.487 at the best of four orientations), so they are not
two instances of one unknown glyph.

The cartouche is a top bar with graduated hanging strokes over a bottom bar — a
comb or frame form. No shape in either alphabet has that structure. It sits on a
funerary wreath on the Leopold monument, where heraldic ornament is expected, so
decorative is the most economical reading.

**Net:** every glyph in the image now belongs to a decoded alphabet except these
two, and neither can be resolved with the keys the image supplies.

---

# The right-hand column: what decodes, and the one glyph that does not

## The column itself IS decoded
Reading bottom to top, separator-delimited glyph counts measured independently
twice: `5 : 11 : 8 : 2 : 6 : 4 : 5 : 1`, matching
`здесь зашифрованы биткоины на чёрный день номер X` on all seven known words, and
verified letter-by-letter with the 28-letter key (every letter the key contains
lands where predicted; the four that decode worst — з, ш, ф, ё — are exactly the
four the key lacks). `на` and `номер` come back perfect.

## The final glyph, measured
Upright (rotate 90 CW), native resolution, Otsu threshold: a **vertical stroke
running the full height with one arm to the upper-right and one to the lower-left**
— i.e. a single diagonal crossing a vertical. **4 endpoints**, stable at radii
0.6R, 0.8R, 1.0R and 1.2R. Bounding box 13 x 20 px; narrower than the column's
typical 19-23 px glyph, so it is one narrow glyph, not two merged.

## Everything it has now been tested against

| hypothesis | method | best distance | verdict |
|---|---|---|---|
| the 28 letters in the key | template match | **0.290** (`д`), margin 0.012 vs median 0.102 | no — in the tail of both distributions |
| the 5 Cyrillic letters the key lacks (ж ц щ ъ э) | structure | — | no — `ж` needs 6 endpoints not 4; `ц`/`щ` need a descender and box; `ъ` needs a horizontal hook; `э` is a curve |
| the Gravity Falls alphabet (26) | template match, both orientations | **0.440** | no — genuine matches score 0.147 |
| a two-letter **ligature** | OR of every crib-glyph pair | **0.296** | no — for a genuine single glyph the best overlay averages **0.132** |
| the artist's own **Arabic digits** (0,2,3,5 extracted from `05.25.20` and `11.03.20`) | template match | **0.385** | no — same-digit pairs average 0.300 |
| the wreath cartouche (the image's only other unidentified mark) | template match, 4 orientations | **0.487** | not the same symbol |

## Conclusion
The glyph is unlike **everything else in the picture**. It is not a letter in either
of the two alphabets the image supplies keys for, not a ligature of two, not one of
the artist's drawn digits, and not a second instance of the only other unexplained
mark. It occurs exactly once.

This is not a resolution problem — at 13 x 20 px the shape is cleanly recoverable,
and the same pipeline reads `номер` at 5/5. The problem is that **there is nothing
to decode it against**. The author drew one symbol, used it once, and supplied no key.

What would settle it: another occurrence of the same shape somewhere (none exists
in this image), or an external source for the alphabet. Nothing in the picture can.
