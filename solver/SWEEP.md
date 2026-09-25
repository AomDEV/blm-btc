# Pixel-level sweep — consolidated agent findings

Eight element-aligned regions, each rendered in three forensic modes
(local z-score / saturation map / light-band slice) and examined at
native and magnified resolution.

## Region B — headline, flag, STOP  (master 300,25 - 900,580)

**HARD NEW RESULT: the flag carries exactly 44 stars and 13 stripes, verified at
pixel level.**

* Stars counted by chroma mask + 8-connected component labelling with a size
  filter, then every centroid rendered back over a 6x crop and checked by eye:
  **44 star glyphs** (42 fully drawn, 2 deliberately clipped at the canton's
  lower-left edge). Row structure 1,2,2,3,4,4,4,4,4,4,4,3,2,2,1 = 44.
* Stripes counted by de-rotating the flag -27.7 degrees and run-length scanning
  at five independent heights, all agreeing: **13 stripes — 5 black, 4 red,
  4 green** (Pan-African tricolour in place of red/white).

The significance is the *asymmetry*: the stripe count is exactly correct for the
US flag (13) while the star count is short. The artist changed only the stars,
deliberately. **50 - 44 = 6**, and slot 6 is one of the missing even positions.

Candidate: **(flag, 6)**. `flag` is BIP39 #706; `star`, `stars`, `stripe`,
`stripes`, `fist`, `stop`, `stability` are all NOT BIP39, so `flag` is the only
word that can name this element.

The competing digit-sum reading 4+4=8 is weaker — digit-summing is not a
mechanism the image establishes anywhere, whereas subtraction is (the
"1865 - 202...?" line).

**Tested and negative:** all 16 fifteen-word subsets of the index map including
`flag` at 6, plus one-free-slot variants (32 frames). No hit.

**Tension worth recording:** adding `flag` makes the index map 16 words, and 16
is not a valid BIP39 length. So either `flag` at 6 is wrong, or one of the other
15 is wrong, or — most likely — the "sort the known words by index and use them
as the phrase" shortcut is wrong and the phrase really is 24 words with gaps.

### Other region-B results
* Headline confirmed at pixel level as **`FIND THE SEED PHRASE IN THE THIS
  PICTURE`** — the doubled article is real, not a smear.
* **Region B contains no numerals at all.** Whatever supplies slots 8, 14, 15,
  21, 22, 23, 24, none of it is written here.
* `Order and stability` is yellow cursive sitting on the face-recognition graph
  line that joins the four bracket frames — a surveillance caption with no
  number attached. Verified against an isolated yellow-chroma mask over the
  whole image: the stroke runs unbroken x=515..1320 at y~93 and ends bare.
* The "STOP" fist is a plain five-digit hand behind the **flagpole** — the
  diagonal is the pole, not a prohibition slash.
* The background star wallpaper is decorative tiling (~31 px pitch), not a
  bounded countable set. Do not treat it as a count.
* Micrography here is verbatim Bitcoin whitepaper section 2, no interpolated digits.
* Face-detection frames: 4 (consistent with `mask` at 4). Crown rays: 7.

### Follow-up flagged by the sweep
The 3-line symbol script at master (200,42)-(444,105) has word lengths
`1 7 3 4 / 5 9 / 5 9`. A 9-letter word appearing twice is a strong crib, and the
same script runs down the right border column — enough ciphertext for a
substitution attack.

## Region C — Floyd, BLM block, cameras, Space Needle  (master 890,25 - 1400,470)

**No new position found here.** The region contains exactly one number —
`05.25.20` on the hoodie — and that is a real-world date, not an index in 1..24.

### Settled: the BLM block's colours (pixel-sampled)

| line | text | colour | typeface |
|---|---|---|---|
| 1 | BLACK | `#000000` | rounded marker A |
| 2 | LIVES | `#000000` | rounded marker A |
| 3 | MATTER | `#000000` | rounded marker A |
| 4 | NO JUSTICE NO PEACE | navy `#040A77` | comic B |
| 5 | END POLICE BRUTALITY | maroon `#680D19` | comic B |
| 6 | STOP KILLING US | green `#014225` | **serif/slab C, and oversized** |
| 7 | NOT ONE MORE | `#000000` | comic B, smallest |

Only lines 4, 5, 6 are coloured. The established `police` at 5 sits on the red
line and is the *second* word of it, so within this block position = **line
number**, not word index. But extending that rule collides: it would put `black`
at 1 (taken by subject), `matter` at 3 (tower), `peace` at 4 (mask), `one`/`more`
at 7 (liberty). So the block contributes only `police` at 5 and six decoy lines.

**Line 6 is the standout** — the only serif line and the only oversized one, a
loud "look here" marker — and slot 6 is missing. But none of `stop`, `killing`,
`us` is a BIP39 word, so if 6 is sourced here the word must come from something
attached to the line rather than its text. `green` (the line's unique colour) is
a BIP39 word and is the obvious candidate. This competes with (flag, 6).

### Settled: the CCTV junction-box glyph is an EYE INSIDE A TRIANGLE
Resolved at 22x local stretch: equilateral triangle outline, lens-shaped eye with
a round pupil on its base. Not a bare eye, not a bare triangle — the composite.
One glyph therefore bridges `camera`, `eye` and `pyramid` (positions 2, 9, 11).

### Settled: the yellow line is a camera sight-line
RGB `#E0DA4C`, running x=382..1320 at y=93..99, terminating exactly on camera
#1's lens (centre ~1307-1333, 75-100). The camera is pointed at the phrase
*Order and stability*. Of those words only `order` is BIP39. (The line reads grey
in the luminance-based views because they discard hue.)

### Refuted: "food" down the Space Needle
The spire (1165-1210, 335-435) carries **no letters at all** at 8x stretch. Four
sub-legible marks do exist in the elevator shaft at (1188-1206, 652-686), but an
independent check of the raw pixels there shows the whole feature spans only
**67 grey levels (128..195)** across a 30 px strip, each mark ~6 px tall, and the
upscale resolves as shaft rails and internal structure, not letterforms. `food`
has been in every community word list since 2020 and is **unproven**.

### Other region-C results
* `brutality` is NOT misspelled — the "BRVTALITY" look is a low-res artefact.
* Line 7 renders as `NOT ONe MORe` — lowercase `e` glyphs, unlike line 5's proper `E`.
* Cameras 2, cables 2, cable glands 2, junction boxes 1, slogan lines 7, words 16.
* BIP39-valid here: `black`, `matter`, `peace`, `end`, `police`, `one`, `more`,
  `order`, `camera`, `eye`, `pyramid`, `tower`, `history`.
  NOT BIP39: `lives`, `justice`, `brutality`, `stop`, `killing`, `us`, `not`,
  `breathe`, `stability`.

## THE RUNE CIPHER IS NOW BROKEN (crib + validated classifier)

The region-A agent measured the three top rune lines structurally, without
knowing any plaintext: word-glyph counts `1:7:3:4 / 5:9 / 5:9`, plus three
internal repeat patterns. Tested against the Russian sentence long claimed for
those lines — **`Я надеюсь что сюда будут присылать много биткоинов`** — all
four predictions hold:

| measured from pixels | plaintext | match |
|---|---|---|
| word lengths 1,7,3,4,5,9,5,9 | Я(1) надеюсь(7) что(3) сюда(4) будут(5) присылать(9) много(5) биткоинов(9) | yes |
| L1 word4's glyphs are a **reversed subsequence** of word2's | `сюда` inside `надеюсь` at positions [5,4,2,1] — strictly decreasing | yes |
| L2 word1 = pattern A B C B D | `будут` — letters 2 and 4 are both `у` | yes |
| L3 word2 has glyphs 2=6 and 5=8 | `биткоинов` — `и`=2,6 and `о`=5,8 | yes |

Four independent structural predictions confirmed. The top lines are settled,
and they are a **43-glyph known-plaintext crib** covering 22 Cyrillic letters.

### Building and validating the key
Glyphs were segmented per line at tuned thresholds (L1 p25, L2 p25, L3 p18),
each word split into exactly its known glyph count, normalised to 26x20 bitmaps
at 5x upscale. Separability: intra-letter distance 0.222, inter-letter 0.472.

**Blind validation:** the right-hand column's last word before the final token
was classified with no plaintext supplied. It returned **`номер`** — 5 of 5
glyphs correct, each as top match (н 0.156, о 0.092, м 0.273, е 0.221, р 0.204).
The classifier is therefore calibrated and credible.

### The right-hand column's structure is confirmed exactly
Reading bottom-to-top, separator-delimited glyph counts measured from pixels:

`5 : 11 : 8 : 2 : 6 : 4 : 5 : 1`

against `здесь(5) зашифрованы(11) биткоины(8) на(2) чёрный(6) день(4) номер(5) X(?)`
— an exact match on all seven known words.

### What X is
**X is a SINGLE glyph.** That is the key structural result: the number in
"чёрный день номер X" is one character, so it cannot be a spelled-out Russian
numeral (два=3, три=3, восемь=6 glyphs). It is a digit or a single-letter
numeral.

Classified against the 22-letter crib, X's best fit is `д` at distance 0.287,
then `и` 0.312, `ь` 0.321, `е` 0.327. **That best fit is worse than every one of
the five validated `номер` letters** (0.092-0.273), and the margin to second
place is 0.025. The honest conclusion: X does not confidently match any letter
in the crib, which is consistent with it being outside the Cyrillic letter set —
a digit, or one of the 11 Cyrillic letters the crib does not cover
(ж з й ф х ц ш щ ъ э ё).

**Consequence:** if X is a single digit it is 1-9, so `black` sits at 1-9. Of
those, only **6 and 8** are unfilled. This is independent of, and converges with,
the region-H finding that the Latin line is exactly 8 words with `niger` = black.

## Region G — clock and Great Seal: three corrections and a definitive negative

**CORRECTION (mine): the clock is NOT mirrored — it is rotated 90 degrees CCW.**
Proven with an 8-way rotation x mirror grid per digit plus a whole-dial rotation:
rotating the master 90 CW makes every digit and both hand-labels read upright,
while mirroring turns them to nonsense (12->"√5", 2->"5", 3->"Ǝ", 10->"0I").
Only the Great Seal layer is mirrored. Two different transforms in one region.
This does not change the flanking-digit sums, so 3 / 13 / 21 stand.

**CORRECTION (everyone's): digits 4 and 7 ARE recoverable**, at (614,819) and
(592,1075). Only 5 and 6 are truly lost under the pyramid brickwork — not 5,6,7.
10 of 12 dial digits are legible.

Fitted dial: centre (471.5, 940.0), radius 184, spacing -30.5 deg/hour.

| hand | angle | exact midpoint | flanks | sum | word |
|---|---|---|---|---|---|
| TOWER | 117.15 | 116.75 | 1 and 2 | **3** | TOWER |
| MOON | 145.90 | 147.25 | 12 and 1 | **13** | MOON |
| third | 209.65 | 207.30 | 10 and 11 | **21** | **none** |

**Exactly 3 hands**, established by a 0-360 angular scan at seven radii keeping
only features whose angle is invariant with radius (everything else is seal arcs,
ribbon or brick rows).

**THIRD HAND — DEFINITIVE NEGATIVE.** Straightened (radius, perpendicular-offset)
strips with sub-pixel sampling along the hand's exact axis, r=0..210, +/-70 px
both sides, five local-contrast scales, plus mirrored and 180-rotated renders.
The identical pipeline renders MOON and TOWER sharply, so it is validated. The
third shaft is completely bare. **Position 21 is not supplied by a word here.**

**Clock rune decoded with an internal consistency proof:**
`СУММА : ДВУХ : ЧИСЕЛ` ("sum of two numbers"), 14 glyphs, 2 separators. The
repeat structure checks out — glyph `◇` is С in both СУММА(1) and ЧИСЕЛ(3);
glyph `⏶` is У in both СУММА(2) and ДВУХ(3). It sits **directly above the
word-less third hand**: the runes are the instruction, and the bare hand is the
one whose answer must be computed rather than read.

Pyramid brick courses: **13** (measured from mortar-line minima), matching the
real Great Seal. Eye rays: **not countable** — ~40-60 irregular strokes, angular
scans at four radii gave 19/11/23/30. Decoration, not a 13.

## Region F — Statue of Liberty

* **`SHT` recovered** — exactly 3 glyphs, drawn at ~13/255 opacity over the
  tablet fill. Nothing before or after it.
* **`1865 - 202...?` transcribed exactly**: three ellipsis dots (individually
  resolved), and the final mark is a question mark.
* **The `?` is RED (192,1,24) and is the only coloured text element in the whole
  region** — the digits and all three dots are neutral black. Strongest
  typographic signal in F.
* Crown rays **7** confirmed (re-derives liberty at 7). Tablet lines 3.
* Pedestal: **6 bands / 7 rules** — the only count in F landing on an unfilled
  slot. Attaches to `ONLY real BITCOIN`, where `real` is the region's only
  deliberate case anomaly. A third competing candidate for slot 6.
* The tablet's "XX" is a hand-drawn circle around an illegible ~10px mark. Best
  fit is two X-strokes but it is **not legible** and **not a written number**, so
  it cannot supply a position. (Leopold's XX in region D is a different mark.)

## Where slot 6 stands

Three mutually exclusive candidates, all inferences rather than things written:
* **(flag, 6)** — 50 real stars minus 44 drawn = 6; stripes are exactly 13, so
  only the stars were altered.
* **(green, 6)** — BLM line 6 is the only serif and only oversized line, and its
  unique colour is the only BIP39-valid thing attached to it.
* **(real, 6)** — 6 pedestal bands, and `real` is the artist's only deliberate
  lower-casing.

Tested: 15,300 index-ordered 12- and 15-word subsets across all four variants
(935 checksum-valid). No hit.

## Region E — the micrography (first full transcription)

25 letterforms in 3 rows, each drawn from Bitcoin whitepaper section 2,
transcribed complete and contiguous — but **the reading order is row 2 -> row 3
-> row 1**, i.e. BRAVE -> NEW WORLD -> WELCOME TO THE. Rows 2 and 3 had never
been transcribed by anyone; they now are, letter by letter.

The "one line vs two lines" rule is about **strokes**, not letters: every stroke
of a `WELCOME TO THE` letter carries 1 line of writing, every stroke of a
`BRAVE NEW WORLD` letter carries 2.

### The typo list in circulation is partly wrong
* `doudle` — **does not exist**. The E of BRAVE reads `double` with a clear `b`,
  and the L of WORLD reads `double-spend` correctly.
* `creeks` for "checks" — **new, nobody had found it** (E of BRAVE, line 7;
  unambiguous at 50x: no `h` ascender, both middle letters are `e`).
* Confirmed in region E: `introdue`, `creeks`, `sing`, `attemps`, plus a partial
  `-ense` for "absence". `proot` and `wich` live in the bottom band, not here.
* `participans` could **not** be confirmed — that word is beyond the resolution.

### Five omissions — a second, distinct anomaly channel
Words silently dropped from the source text: "a trusted", "that", the "[1]"
citation, "for", and the entire closing clause "in which they were received"
(the text stops dead at "history of the order").

### The typo channel is selective
Two of the typos turn one BIP39 word into **another** BIP39 word:

| correct | BIP39 | as written | BIP39 |
|---|---|---|---|
| sign | #1602 | **sing** | **#1610** |
| check | #312 | **creek** | **#409** |

The remaining typos corrupt `introduce`, `attempts`, `absence`, `participants`
and `mint` — **none of which is a BIP39 word at all**, so they could not have
produced a BIP39->BIP39 pair. So every typo whose base word is in BIP39 lands on
another BIP39 word, 2 for 2. Both also sit at the 5th letter of their display
word (`creeks` in the E of BRAVE, `sing` in the O of WORLD).

Caveat worth stating: `check`->`creek` is two substitutions, not a slip, and the
sample is two. Suggestive, not conclusive.

**Region E contains no numerals and no countable objects** — on the established
mechanism it supplies words, not positions.

**Tested:** 75,690 index-ordered 12/15/18-word frames across 4 slot-6 variants x
3 slot-10 variants (4,561 checksum-valid). No hit.

## Region D — rune column, Leopold, 13th Amendment

### Independent confirmation of the rune column structure
Measured separately from my own pass, by a different method:
**42 glyphs, 7 colon separators, 8 groups**, sizes bottom-to-top
`5 - 11 - 8 - 2 - 6 - 4 - 5 - 1`, reading direction bottom-to-top confirmed
(`rotate(-90)` stands the glyphs upright), separators at master y 909, 638, 448,
396, 246, 147, 58. 18-22 distinct glyph classes across 42 glyphs.

That is an **exact match** to my independent measurement and to
`здесь(5) зашифрованы(11) биткоины(8) на(2) чёрный(6) день(4) номер(5) X(1)`.
Two independent pixel measurements, same answer, including the crucial
**final group of size 1**.

### New count: Leopold's uniform has exactly 8 buttons
Double-breasted, 4 left + 4 right, at (1353,544) (1351,567) (1352,605)
(1354,641) and (1425,544) (1427,567) (1421,605) (1417,641). Triple-verified:
visual at 8x, colour-mask binarisation, and a blue-minus-red channel map. It is
the only even-valued count in region D, and **8 is a missing position**.

Tension to note: the bust already carries its own marker (`XX` = 20 -> second),
so either the coat is a separate element from the head, or the count belongs
elsewhere. No word is labelled, so proposing one would be invention.

### Firm negative: the 13th Amendment has exactly TWO underlines
`1` (y 822-823, x 1420-1434) and `subject` (y 902, x 1402-1447). **There is no
third.** The apparent bar under "the" in "within the United States" is the
font's terminal-`e` exit stroke — it appears on every word-final `e` in the
panel (`crime`, `place`, `the`) and fails the >=7px dark-run test both real
underlines pass. The panel is word-for-word identical to the real amendment:
no typo, no inserted or omitted word.

### Other
* The gag cloth on the bust reads `BREATHE` (7 glyphs). `breathe` is NOT BIP39.
* A **third** eye-in-triangle sits on the CCTV junction box at (1408-1434,
  196-218) — the `eye`/`pyramid` motif recurs.
* The wreath cartouche at (1379-1397, 696-712) holds a rune-like symbol that
  **matches none** of the 42 column glyphs (best distance 109 vs 55-65 for
  genuine same-class pairs). Unexplained.
* Wreath leaves and background stars are NOT reliably countable — do not use.

---

# CONSOLIDATED POSITION MAP AFTER THE SWEEP

| pos | word | source | confidence |
|---|---|---|---|
| 1 | subject | 13th Amdt: `Section 1` + `subject`, the only two underlines | high |
| 2 | camera | two CCTV cameras | high |
| 3 | tower | clock hand, 117.15 deg, bisects 1 and 2 | **measured** |
| 4 | mask | four masked faces, four detection frames | high |
| 5 | police | line 5 of the seven-line BLM block | high |
| 6 | flag? green? real? | 50-44 stars / serif line 6 / 6 pedestal bands | **contested** |
| 7 | liberty | 7 crown rays, counted | high |
| 8 | black? | Latin line = 8 words, `niger` = black; also 8 buttons | plausible |
| 9 | eye | seal's eye over clock 4+5 | medium |
| 10 | ? | (README's `black` here is now doubtful) | open |
| 11 | pyramid | pyramid over clock 5+6 | medium |
| 12 | vote | `.VS.` = 12 under **vertical** flip | high |
| 13 | moon | clock hand, 145.90 deg, bisects 12 and 1 | **measured** |
| 14 | ? | | open |
| 15 | ? | | open |
| 16 | rifle | M16 | high |
| 17 | gold | 17-year chart | high |
| 18 | world | Brave New World, 18 chapters | medium |
| 19 | glove | CVD19 | high |
| 20 | second | Leopold II, XX | high |
| 21 | ? | third clock hand, **proven wordless** | open |
| 22-24 | ? | | open |

Still open: 6 (contested), 10, 14, 15, 21, 22, 23, 24.

---

# FOLLOW-UP PASS

## CORRECTION: "food" IS in the Space Needle — I was wrong to refute it

Master **x 1188-1212, y ~653-679**, written down the right-hand elevator shaft,
four letterforms reading **`Food`** (capital F, two closed `o` loops, a `d` with
a clear ascender).

Why it was missed, twice: the band spans only 128-195 in grey (67 levels), and
both my pass and the region-C pass normalised contrast **over the small text
patch itself**, which flattens it. Normalising over the **tall shaft strip**
(master 1186-1214 x 545-700, percentiles 3/97) and only then cutting out the
text band makes it legible. That is a general lesson: autocontrast on a tiny
crop hides exactly the thing you are looking for.

`food` is BIP39 #726. **Its position is still unknown** — the saucer ribs do not
give a stable count (7, 8, 11 or 15 depending on threshold and box, because they
are loosely drawn and partly occluded), and the Space Needle does not overlap the
clock dial, so the dial cannot assign it either.

## REFUTED: the clock is not a global protractor

The "clock rays" theory — that rays from the dial centre assign a position to
every element in the picture — is testable and **fails**. Using the fitted dial
(centre 471.5, 940; -30.5 deg/hour) to predict the slots of elements whose slots
are already known:

| element | dial prediction | actual | |
|---|---|---|---|
| seal eye (651,845) | between 4 and 5 -> 9 | 9 | MATCH |
| pyramid body (650,958) | between 5 and 6 -> 11 | 11 | MATCH |
| cameras (1400,140) | between 3 and 4 -> 7 | 2 | **miss** |
| Statue of Liberty (170,800) | between 12 and 1 -> 13 | 7 | **miss** |
| Leopold bust (1390,560) | between 4 and 5 -> 9 | 20 | **miss** |
| M16 / China (900,750) | between 4 and 5 -> 9 | 16 | **miss** |

It works for exactly the two elements that physically **overlap** the dial and
fails for everything else. So the dial speaks only for what is drawn on it
(3, 13, 21 from the hands; 9 and 11 from the seal). Every other element takes its
number from its own count. This closes off a theory that has circulated since
2020 and is the basis of the `n1x7g8ceaur51-clock.png` overlay in the source repo.

## Also checked
A coverage audit found two areas no agent had examined: **x 1060-1269, y 470-689**
(209x219 px, the Space Needle mid-section — where `Food` turned out to be) and a
19x219 sliver at x 400-419. The rest of the canvas was covered.

## Wide-window sweep (sigma=30) — results

Re-rendered the whole canvas with the normalisation that found `Food`, and swept
all 12 tiles plus targeted follow-ups (wide-strip percentile stretches, 90/270
rotations, midtone-only stretches, high-pass at four scales, OCR at four
rotations).

### New text
* **Ghost graffiti `BITCOIN`** — master x ~880-1075, y ~85-215, large spray-style
  word rising diagonally behind George Floyd's head, distinct from the pedestal's
  "ONLY real BITCOIN". Invisible at sigma=9 and washed out by a 3/97 stretch; it
  only resolves under a narrow midtone stretch (percentiles 25/80). Not BIP39.
* `CHaRLy` signature (x 44-80, y 38-78) and the `CHR` monogram (x 1533-1553,
  y 1132-1152) confirmed as a diagonal pair of artist marks. Neither is BIP39;
  both are authorship, not payload.

### New / confirmed counts
* Chart y-axis: **9** labelled gridlines (1800 down to 200).
* Great Seal pyramid: **13** brick courses, measured programmatically.
* Space Needle shaft: **7** window slots directly above `Food`; stable across
  thresholds, unlike the saucer ribs. The shaft below `Food` is blank.
* Crown rays: **7**, by radial sampling at r=40 and 46 about (178,602). The
  agent's own first eyeball said 8; the radial scan showed the extra spike is the
  left ray splitting at small radius. Liberty = 7 survives.
* Leopold coat buttons: **8**, independently re-confirmed.

### Two numeric tensions, both resolved as non-signals
* Pyramid has **13** brick courses but is assigned slot **11**, and 13 is moon's.
  The 13 is simply a faithful reproduction of the real Great Seal, which has 13
  courses. The 11 comes from the dial overlap (5+6), a different mechanism.
* The chart shows **9** gridlines but gold is at 17 (year span) and 9 is eye's
  (dial overlap). Nine gridlines at a 200 interval over 0-1800 is ordinary chart
  design, not a count.

### Clean
Camera bodies, mounts and cables (the "graffiti tag" behind them is the cameras'
own drop shadow, verified by median-filtered low-pass); the M16; both suits;
Biden's lapel pin (featureless); the crowd figure's shirt pocket (empty); the
plinth's lower blocks; every large flat area (sky, walls, map, clothing); the
x 400-419 sliver from the coverage audit; alpha uniform 255.

### Honest bottom line from the sweep
No number was found for `food`, and no candidate was produced for slots 6, 10,
14, 15, 21, 22, 23 or 24. The Space Needle's only stable count is 7, already
taken. The remaining unexplained faint structure in the picture is grunge texture
and drop shadows, not lettering. **The outstanding positions are very probably
not hidden in the pixels at all** — they must come from a property of an element
nobody has thought to measure, or they are not recoverable.

## Underdrawing-layer sweep (luminance, not geometry)

The geometric sweep came back a clean negative (96 tile views across 8 transforms,
the six targeted elements, and a block-wise self-similarity search - all empty
except the `CHaRLy` signature). The productive axis is **luminance**.

### Genuinely new
* **A full-bleed US flag underlies the entire canvas** - large 5-point stars on a
  ~95 px staggered grid plus faint stripes, running edge to edge **including
  outside the black picture frame**, visible in both margins. The star "wallpaper"
  several passes dismissed as decorative texture is a flag.
* **Content exists outside the frame.** The chart's y-axis numerals
  (1800/1600/.../200, nine labels) sit at x 17-40, *outside* the drawn black
  border, in the left margin.
* The rifle in the underdrawing is **wider than previously measured**:
  (598,595)-(1018,760), not (720,650)-(980,775).

### A useful negative about where to look
The area behind BRAVE NEW WORLD - which the instruction headline appears to point
at, and which I picked as the densest region - contains, in the underdrawing,
**only the rifle and the China map**. Swept at six windows and three sigma values
in 250x160 sub-tiles; everything else there is wash texture. The vertical drip
streaks behind BRAVE that read as tally marks at a glance are airbrush drips at 3x.
The real density is the **lower left, around the clock**.

### Texture-only, verified
All windows above luminance 245 are paper grain plus 8x8 mottle - anything "found"
there is noise. Also clean: the soft blob behind the cameras (an airbrushed spray
shadow, no letterform at four smoothing scales and six windows), the bright grunge
speckle at (390,260)-(520,420) and (1350,300)-(1480,420), the right margin, the
bottom strip, and the region below NEW WORLD.

### Third independent measurement of the clock
Reported in compass convention; converting (math = 90 - compass) gives
TOWER 116.70 vs my 117.15, MOON 145.60 vs 145.90, third 210.40 vs 209.65 - all
within 0.75 degrees. **Three independent passes now agree**, and all three
independently report that the hands **bisect** digit pairs rather than pointing at
digits. Combined with the rune directly above the unlabelled hand reading
`СУММА ДВУХ ЧИСЕЛ`, the sums 13 / 3 / 21 are settled.

### One honest ambiguity re-opened
The Space Needle shaft text: this pass reads it as 4 glyphs but flags
**`500 ft`** as an alternative to `Food` - the real Space Needle's restaurant sits
at 500 ft, which the source README itself mentions. My own render shows two clearly
closed round bowls and a final letter with a right-side ascender, which favours
`Food`, but `500 ft` cannot be excluded at 24x62 px. Recording the doubt rather
than burying it. Note this is a **dark-on-dark** concealment - a different
technique from the light-on-light layer - so a dedicated dark-band sweep
(windows 120-200 inside black-inked shapes) is the natural follow-up.

---

# DARK-ON-DARK PASS

## `Food` vs `500 ft` — settled as `Food`

The Space Needle shaft text was re-rendered at four narrow dark windows
(125-165, 130-175, 135-185, 140-195). At every window the string shows
**four glyphs and no word gap**:

* glyph 1 — vertical stem with a horizontal arm (`F`)
* glyphs 2, 3 — closed round bowls (`o`, `o`)
* glyph 4 — a bowl with an ascender on the **right** side (`d`)

`500 ft` requires **five** marks plus a word space, and its final letter would
show a crossbar (`t`), not a right-side ascender. The glyph count alone decides
it, independent of how anyone reads the individual shapes.

**`Food` confirmed.** BIP39 #726. Position still unknown.

## Why a dark-band sweep was the right next move

`Food` is ink at grey ~132 sitting inside a shape of ~190 — dark-on-dark. That is
a different concealment technique from the light-on-light underdrawing layer, and
it is invisible to every bright-band method used so far. It had never been swept
for systematically.

The dark range is big: **48.6% of pixels are below 200, 28% below 170, 17.6%
below 140.** Low-end percentiles: p5=54, p10=95, p15=126, p20=149, p25=163,
p30=174. So there is a great deal of room inside dark shapes for more of this.

Whole-image and per-region renders at seven overlapping windows
(40-80, 70-110, 95-135, 120-155, 140-175, 160-195, 180-210) are in
`forensics/dark/`.

Two sweeps now running: the whole canvas shape by shape, and a deep pass on the
lower-left quadrant — the area the luminance sweep identified as the densest part
of the underdrawing, and which contains the one object most worth re-checking:
the **third clock hand**. Prior passes cleared it for light-on-light and
bright-band text, but dark-on-dark has never been tried on it, and it is the hand
that points at the unfilled slot 21.

## Whole-canvas dark-on-dark sweep — result

**No new text. No new numbers.** Every string the sweep surfaced was already on
record. The dark-on-dark hypothesis has now been tested systematically and it
yielded exactly one item, `Food`, which was already known.

### Two long-standing claims killed outright

* **"1713 -> STOCK hidden in the COVID graffiti"** — the graffiti reads exactly
  `COVID 19 IS A HOAX / 5G IS THE KILLER` at 13x and contains nothing else. This
  claim has been in the source README since 2020 (the repo author noted he could
  not see it either). It is now **refuted**, not merely unconfirmed.
* **The wreath cartouche is not a Roman `III`.** Quantified by threshold
  response: at thr 120 it is two strokes of height 6 and 5, both confined to rows
  698-703 — the *upper half only*; at thr 140 they merge; at thr 160 everything
  merges into the frame. A Roman `III` needs three equal, baseline-aligned
  strokes. What is there is 2-4 strokes of differing heights and offsets that do
  not survive a threshold change.

### The third hand is now clean in three concealment channels
Straightened along its own axis at five angles: no label. It was already cleared
for light-on-light and bright-band text; dark-on-dark now joins them. MOON and
TOWER render clearly under the identical treatment, so the method is validated.

### A methodological finding that qualifies earlier negatives
Narrow-window band stretching requires guessing the right window per shape, which
is why `Food` was missed twice. **Local-contrast normalisation is
level-independent and needs no guessing**: median filter 9-11 px, subtract,
multiply the residual by 6-8, re-centre at 128. That makes `Food` legible in a
single pass and surfaced the plinth amendment text, the pedestal prediction lines
and `BREATHE` in the same pass.

**Sensitivity threshold: 8x magnification on ~200x150 px tiles. At 4x, `Food` is
invisible.** Several earlier passes in this session ran at 2-3x, so their "clean"
verdicts are not reliable negatives. The whole canvas has now been re-swept at 8x
on a full 64-tile grid with the level-independent method, which supersedes them.

### Shapes swept and clean at 8x
Space Needle (shaft above and below `Food`, second leg, saucer underside);
Statue of Liberty (robe, crown, tablet, arm, pedestal blocks); all three clock
hands; Great Seal (ring, 13 brick courses, base band, torch shapes); Leopold bust
(tunic, both plinth blocks, wreath leaves); flag (canton, stripes, pole); rifle
(receiver, magazine, handguard, stock); Trump and Biden (hair, faces, suits, tie);
Floyd (hoodie, hair); CCTV (bodies, mounts, cables); the black picture frame, all
four bands end-to-end at 9x; the interiors of the `FUCK THIS SHIT` letters; both
margins. The grey wash in the upper middle is airbrush texture, not a smoke plume.

## The chroma channel — swept, one mark, mundane explanation

The lower-left sweep found something no greyscale pass could: **the MOON clock
hand is drawn in red ink; TOWER and the third hand are mathematically neutral.**
Verified independently by sampling R-G across each shaft at 5 px radial steps:

| hand | mean ink RGB | median R-G | mean R-G | samples >= 12 |
|---|---|---|---|---|
| TOWER 117.15 deg | (187,187,187) | **0.0** | 0.0 | 0 of 27 |
| **MOON 145.90 deg** | **(215,190,191)** | **+26.0** | +25.6 | **27 of 27** |
| THIRD 209.65 deg | (205,205,205) | **0.0** | 0.0 | 0 of 24 |

It is a 5-6 px stroke centred on the hand axis, falling to exactly 0 three pixels
either side, reproducible at r = 60, 100 and 140. TOWER — a darker, thicker line
30 px away — reads 0.000 over 787 ink pixels, so the encoding is perfectly capable
of neutral ink there. MOON also has a **57 px counterweight tail**; the other two
have none.

### Then I swept every other neutral-drawn set, and they are all clean

| set | result |
|---|---|
| all 12 clock digits | R-G = **0.0** on every one |
| top rune lines 1, 2, 3 | R-G = 0.0 |
| clock rune (СУММА ДВУХ ЧИСЕЛ) | R-G = 0.0 |
| right-hand rune column | -9.2, explained by the blue sky gradient behind it |
| Gravity Falls line | -30.4, explained by the green wash behind it |

So the chroma channel contains **exactly one deliberate mark in the whole
neutral-drawn stratum**, and it is the MOON hand.

### The honest reading
The economical explanation is clock convention, not a hidden pointer: on real
clocks the **seconds hand is red and carries a counterweight tail**. MOON is red,
thin, and has a 57 px tail. That makes it the seconds hand — which is exactly what
the source README assumed in 2020 ("the seconds hand has the moon word").

So this is a real, reproducible, previously unrecorded observation that
**corroborates the existing reading rather than adding a new position**. It is
recorded as a hard discriminator among the three hands, not as a new lead.

---

# LENGTH AND ORDER — fresh evidence

## Two independent routes to 21
* The third clock hand bisects 10 and 11 -> **21**, and carries no word.
* The whitepaper band's one complete sentence ("The payee needs proot that at the
  time of each transaction, the majority of nodes agreed it was the first
  received") is exactly **21 words** — and it is the sentence about *order*
  ("the first received").
No count in the image lands on 24, 18 or 15 with comparable support. 12 is ruled
out by index collisions. **21 is now the best-supported length.**

## The "Order and stability" line, traced
Isolated with a relaxed yellow mask: one continuous stroke of 4,444 px spanning
**x 512 -> 1298**, beginning immediately after the fourth face-detection box
(431-483) and terminating at camera #1's lens. Upstream of it, the four yellow
corner-bracket boxes are joined by a polyline: box 1 (largest face, x 116-186)
-> box 2 (x 252-309) -> box 3 (x 297-398) -> box 4 (x 431-483) -> the labelled
line -> camera.

So it is a face-recognition chain: the camera "sees" four faces in sequence, and
the link is captioned *Order and stability* — an authoritarian slogan on a
surveillance graph. **It visits only the four faces and the camera.** It does not
route through any other element, so it is not a global ordering device for the
seed; it supplies the literal word `order` (position unknown) and a theme.

## Element census
30 distinct pictorial elements; 23 have a word, 16 have a position. Some yield
several words, some none. That is consistent with a 21- or 24-word phrase and
inconsistent with 12.

## New literal words
From the 21-word sentence: `that` (#1791), `time` (#1799), `first`.
From the micrography's five deliberately OMITTED words: `trust`, `that`, `they`
(#1796). Note the dropped clause "in which they were received" appears exactly
once elsewhere — in the bottom band, with the `wich` typo — so the omission
singles it out. `they` and `that` are new to the inventory.

## GPU run: 21-word frame, 47-word pool DISJOINT from the CPU's 60-pool
16 canvas/count-derived pairs fixed, 5 free slots (6, 10, 14, 15, 21) over the 47
inventory words the CPU pool does not contain: 47^5 = 229,345,007 combos ->
**1,791,122 checksum-valid seeds derived on the GPU, 0 hits**, 853 s, 2 driver
kills detected by the embedded canary and recovered. Paths: m/44'/0'/0'/0/0..19
(narrow kernel). Every launch canary-verified.

## C engine (`solver/c/blmc`) — same 47-pool frame, four runs, 0 hits (2026-09-26)
The Python/OpenCL hybrid was replaced by a C engine for the CPU side. Every run below is
the same 21-word frame (`t21d.txt`: 16 fixed pairs, 5 free slots over the 47-word pool,
47^5 = 229,345,007 combos), paths m/44'/0'/0'/0/{0,1}, target
`ccbd031e54cde2a3189fd59bc49f731367a1779e`. All four derive exactly **1,791,122**
checksum-valid seeds — the same count the hybrid produced — and all four are negative.

| engine | seeds/s | wall | notes |
|---|---|---|---|
| hybrid v2 (Python + OpenCL GPU) | 5,994 | 299 s | previous best |
| blmc v1: OpenSSL `PKCS5_PBKDF2_HMAC`, 8 threads | 7,506 | 239 s | PBKDF2 = 682 µs/seed, bottleneck |
| blmc v2: ARMv8 SHA-512 instructions, HMAC midstates, 4 seeds interleaved per thread | 14,163 | 127 s | PBKDF2 = 369 µs/seed/thread |
| blmc v3: + hardware SHA-256 checksum, own HMAC-SHA512 for BIP32, incremental odometer packing | **15,669** | 114 s | C only |
| `gpu/cgpu.py`: blmc on 85 % of the space + GPU on 15 % (blmc `--list` feeds the kernel) | **16,968** | 106 s | GPU 3,659/s, 2 driver kills recovered, 0 hangs |

Where the time goes now (per seed, per thread): PBKDF2 2048×2 SHA-512 compressions ≈ 369 µs
(hardware-bound; 4-way interleave hides the instruction latency), three secp256k1 pubkey
creations ≈ 69 µs, everything else ≈ 70 µs. The M1's SHA-512 unit is the wall: OpenSSL's
own asm runs at the same ~92 ns/block. Further gains would need a faster `ecmult_gen`
table (secp256k1 built with a larger `ECMULT_GEN_KB`) — at most ~10 % — or more machines.

Validation before each run: `c/test_blmc.py` (14 checks on the ASan+UBSan build and the O2
build: SHA-256/SHA-512/HMAC/PBKDF2 vs OpenSSL, derivation vs `blm.py` on 202 mnemonics of
12–24 words incl. the >128-byte pre-hash case, survivor-set equality with the Python
enumerator, planted hits in partial and full 4-way batches, no false hit) and the `--part`
partition test (7 parts: disjoint, union == full list). `cgpu.py` end-to-end: planted hit
in the GPU part found by the GPU, in the CPU part by blmc, and an injected GPU fault falls
back to the CPU with identical coverage.

---

# 2026-09-26 — picture pass: two measured facts, one firm negative

## The bottom band is written in TWO ink tones (new, measured)
The whitepaper band (`in wich they were received. the payee needs proot ... was the
first received`) is hand-lettered in black except for two runs written in grey:

| run | master x | ink on the frame line | frame line there |
|---|---|---|---|
| `... of each transaction, the` | 560-690 | **11** | 68 |
| **`majority of no`** | 690-770 | **46** | 68 |
| `des agreed it` | 775-865 | **10** | 65 |
| **`was the first received`** | 880-1015 | **45** | 65 |

Luminance of the darkest stroke pixels on the frame-line rows (1155-1160). The grey
runs are the same brush at roughly one-third opacity, uniform across whole words;
the boundaries are sharp and one of them falls **inside a word: `no|des`**. It is not a
wash over the region — the frame line is equally dark under black and grey text, and a
translucent layer over both would scale their contrast together, which it does not.
The README noticed the colour difference in 2020; nobody had measured it or recorded
the mid-word split. **Meaning: unknown.** Word positions in the 21-word whitepaper
sentence: grey = 13, 14, 15(first half), 18, 19, 20, 21; black = 1-12, 15(second
half), 16, 17. Recorded as a fact, not as a lead — a pressure-sensitive pen could also
produce it, though the tone is uniform within each run rather than varying stroke by
stroke, which argues against that.

## The rune alphabet is not a real script (firm negative)
The 28-letter key (98 glyphs) was matched against every ancient or constructed
alphabet with a local font — Glagolitic, Old Permic (Abur), Old Hungarian, Old Turkic,
Old Italic, Lycian, Carian, Lydian, Gothic, Coptic, Tifinagh, Phoenician, Ugaritic,
Old South/North Arabian, Elbasan, Caucasian Albanian, Cypriot, Avestan, Samaritan,
Old Persian, Meroitic, Runic (23 scripts) — allowing mirror and 90°/180° rotations.
Best median nearest-neighbour distance 0.247 (Old Turkic) with 21 % of letters inside
the in-image same-letter band (0.22); a genuine source script would put most letters
there. The two scripts that carry a Cyrillic mapping fail on that mapping too:
Glagolitic 1/27 letters match, Old Permic 0/26. **The author invented the alphabet**,
so the unidentified final glyph ("number X") cannot be read off any external key.
Re-viewed at 8x in all four orientations: a single slanted stroke with one short
crossing bar near its top; still unlike every other mark in the image.

## Coverage note that matters for the next search
Every 21-word frame run so far (`t21`, `t21b`, `t21c`, `t21d`) fixes **`black` at 8** —
a "plausible", not measured, assignment. The 15 measured/high pairs with 8 left OPEN
(free slots 6, 8, 10, 14, 15, 21 over the 60-pool: 60^6 = 4.67e10 combos, ~3.6e8
checksum-valid seeds, ~6 h on `cgpu.py`) has not been run.

# 2026-09-26 (later) — knowledge-derived positions: the channel that gave `world`=18

The map already contains one position that comes from outside knowledge rather than
from a count in the picture: `world` = 18 because *Brave New World* has 18 chapters.
Today the same channel produced three more candidates, all fact-checked:

| word | position | basis | verified | grade |
|---|---|---|---|---|
| **order** | **10** | the caption "Order and stability" is a quotation from the novel; it occurs **exactly once**, in Chapter 10 (all 18 chapters downloaded and grepped; huxley.net) | yes | high as a fact; collides with the README's `black`@10 (Roman X = 10 reading of "number X"), so both are searched |
| **food** | **21** | the Space Needle was built for the 1962 Seattle World's Fair, officially the **Century 21 Exposition**; the Needle opened on its first day (21 Apr 1962) and the fair closed 21 Oct 1962. Explains why the third clock hand (21) carries no label — the 21st word lives in the Needle | yes (Wikipedia: Space Needle, Century 21 Exposition; HistoryLink) | medium-high |
| brave | 8 or 15 | "brave new world" occurs in the body text of chapters 8 (3x, first occurrence), 11 (2x) and 15 (5x); 11 is taken | yes | medium that it is one of the two; unresolved |
| black | 8 | 8:46 (Chauvin's knee time as reported in 2020) beside the Floyd portrait; converges with the 8-word Latin line and the 8 buttons | yes | plausible |

Checked and NOT landing on an open slot: Tempest Act 5 Sc 1 ("O brave new world"); Tarot
Tower XVI / Moon XVIII / **World XXI** (the labelled hands are Major Arcana names and the
unlabelled hand points at XXI — recorded as an alternative frame `world`@21 + `brave`@18,
not as an addition); Leopold II reign 1865-1909 = 44 years (= the 44 stars, coincidence);
13th Amendment ratified 6 Dec 1865 (a 6, but the plinth's marked word is already `subject`@1);
11.03.20 -> 11+3 = 14 (no word attaches); "welcome" occurs in chapters 2, 3, 17.

## Space Needle window column, measured at 8x
Six rounded window slots are visible above `Food` (a seventh is hidden under the saucer),
pitch 16.4 px (y 563, 581, 597, 613, 629, 645); the word occupies the 7th and 8th pitch
positions (y 650-690). Internal readings: `food`@8 (starts at the 8th position) or
`food`@15 (7+8, the clock's own "sum of two numbers"). Weaker than Century 21; searched anyway.

## Numbers as BIP39 indices — a channel the community used, now recorded
`1865` = #1865 **trouble**, `2020` = #2020 **wise** (2021 wish, 2022 witness, 2023 wolf,
2024 woman …), `1713` = stock (the refuted graffiti claim was this mechanism), `1400` on
the gold axis = **puzzle**, `1800` = thought, `05.25` = 525 = **dose**, `11.03` = 1103 = mean.
Nothing in the picture confirms the mechanism; the words are added to the search pool
(`t21g2`/`t21h2`, 127-word pool) rather than assigned positions.

## Canonical-source audit (agent, 56 crops)
Every quoted text compared with its source: the 13th Amendment panel, the BLM block and
the COVID graffiti are verbatim; the Great Seal mottos are standard short forms with
nothing inserted; the Latin proverb is the exact dictionary form (verbum.by, 1993
six-language proverb dictionary) — **no inserted word**, so `niger` is not an anomaly.
Re-casings only: `Stability`->`stability`, `The payee`->`the payee`, `I can't BREATHE`.
Correction to the Region-E note: the clause "in which they were received" is not omitted
from the picture — Region E stops at "history of the order" and the bottom band resumes
with it; four omissions stand ("a trusted", "that", "[1]", "for"). Written BIP39 words
missing from the inventory: `only`, `neither`, `can` (all stop-words inside quotations; added
to the pool only).

## Searches this round (21-word frames, inventory pool, paths 0/1, C+GPU)
| frame | fixed beyond the 15 measured pairs | free | seeds | result |
|---|---|---|---|---|
| t21f | order@10, black@8 | 6,14,15,21 | 489,220 | no hit |
| t21g | order@10 | 6,8,14,15,21 | ~43.6M | running |
| t21h | black@10 | 6,8,14,15,21 | ~43.6M | queued |
| t21j-o | food@8 / food@15 x order/black@10 | 3-4 free | small | queued |
| t21p/q | food@21 x order/black@10 (127-pool) | 6,8,14,15 | ~2.0M each | queued |
| t21v/w | world@21 + brave@18 x order/black@10 | 6,8,14,15 | ~2.0M each | queued |
| t21g2/h2 | order/black@10, 127-pool (index words added) | 6,8,14,15,21 | ~258M each | queued (~4 h each) |

## Flag canton re-measured in the star grid's own frame
The 44 stars sit on a staggered square grid whose axes run at 45° / 135° in image
space (nearest-neighbour vector histogram: 135° x38, 45° x34), i.e. NOT aligned with the
flag's stripes (~58°). Along the 135° axis there are **8 lines** of 5,6,5,5,6,5,6,6 stars
(= 44); along the 45° axis also 8 lines (2,4,7,8,8,8,5,2, ragged because the canton is cut
at the flag's angle). The earlier "1,2,2,3,4,…" structure was the image-horizontal
diagonal of this grid. Real 50-star flag: 9 rows of 6/5. So the only clean counts the flag
offers are 44 (stars), 13 (stripes) and **8** (grid lines) — (flag, 8) joins (flag, 6) as
a weak candidate; both are in the free-slot pool anyway.

## Also checked this round (negative)
* Rune alphabet vs the Gravity Falls symbol set, letter by letter (28-letter key sheet vs
  the pyramid key in 11_1.png): same drawing *style* (diamond, triangle, box, chain-of-
  circles, hatched strokes) but no consistent letter mapping — the artist drew a GF-style
  alphabet of their own. No fan Cyrillic chart surfaced on the web. Final glyph still unread.
* Typo channel as a position source: `creeks` is on line 7 of the E of BRAVE (7 = liberty);
  `sing` runs around the ring of the O of WORLD where "line number" is undefined. Closed.
* Wreath cartouche at 10x: a square frame with three short inner strokes; junction box:
  eye-in-triangle, 4 corner screws, 2 cables; China map: no marks beyond the outline. Nothing
  numeric. The "?" beside the map is the debate's question mark.
* Alternative-word frames queued (`t21alt_o/_b`, ~2.2 h each): the fixed slots may take
  {camera|twin}, {police|end}, {vote|debate}, {rifle|gun|weapon}, {gold|price},
  {world|brave|welcome}, {glove|hand} — 288 alternates x 4 free slots over the 89-pool.

# 2026-09-26 (night) — two angles nobody had tried

## 1. A BIP39 passphrase
Several emphasised words in the picture are NOT BIP39 words and so cannot be seed words:
`TUESDAY` (hidden in its own cipher above the candidates), `BREATHE` (written twice),
`STOP`, `BLM`, `SHT`, the dates, the signature `CHaRLy`. A non-BIP39 word that the artist
went to the trouble of enciphering is the classic shape of a **passphrase** hint — and a
passphrase makes every seed-only search miss regardless of words and order. The C engine
now takes `--passphrase` (salt = "mnemonic"||passphrase, precomputed salt blocks, verified
against OpenSSL and `blm.py` incl. >111-byte salts; `test_blmc.py` covers it). `cgpu.py
TEMPLATE@PASSFILE` sweeps a passphrase list (C only; the GPU kernel has the empty salt
hard-coded). Planted-hit test with passphrase `TUESDAY`: found and tagged. Queued:
`passlist.txt` (49 candidates, NFKD) on the order@10/black@8 frame; the 20 strongest on
the two `food`@21 frames.

## 2. Words the artist may have DRAWN rather than written
A wallet hands the artist 21 random words; some are easy to letter (moon, tower) and the
rest must be depicted. BIP39 words that name drawn things and were never in the pool:
`question` (two red ?), `virus` (COVID graffiti), `dollar` (the Great Seal is the dollar
bill), `blood` (the red paint on Leopold), `hood` (Floyd's hoodie), `glass` (the first
face's spectacles), `lens`, `cable`, `box` (the CCTV set), `hair`, `face`, `nose`, `eagle`,
`torch`, `spray`, `wall`, `shadow` (only the cameras cast one), `mirror`/`reflect`/`flip`
(the mirrored seal and .VS.), `pole`, `ribbon`, `wire`, `map`… 84 such words added: the
free-slot pool is now 206 words (`t21f3`, `t21p/q/v/w/y/z` rebuilt on it, ~13 min each).
