# sb1_robust 0.2.0, chunk 2 of 8, and chunks 0 + 1 + 2 + 7 together: interim, descriptive only

2026-11-19. By MV2 of Munim, Inc.; made with AI agents working in his name, and not yet
checked by a human expert. Text and data CC BY 4.0.

**This is not the graded result.** The pre-registered grade
(`findings/2026-11-18-sb1-robust-prereg.md`, plus amendment 1) combines all eight chunks.
Chunks 3–6 are still waiting for compute. This note puts chunk 2's outputs
(`data/sb1rob-v1/k2/`) on record and adds them to the hand sums of chunks 0, 1 and 7. Those
sums are superseded when `sb1_combine.py` runs on every chunk.

## Chunk 2 in numbers
- 457 stars processed: 442 with usable TESS data, 15 without. 340 are in the rate sample
  (injection sensitivity ≥ 0.5). The pre-registered pool of 6,434 was reproduced exactly.
- **Robust hits: 1, against 60.0 expected if every orbit were real.** The control periods
  give 0.5 expected false hits (0.15%).
- **No substellar-size hit.** The one hit in the rate sample is MODULATED (below).
- **Brown-dwarf-mass orbits: 248 in the rate sample, 46.3 transits expected, none seen.**
- The old 0.1.0 rule would have flagged 19 hits in the same 340 stars. The median rule removed
  18 of them.
- Checks: C1 4 of 4 known companions recovered; C2 0.15% ≤ 3%; C3 340 ≥ 150; H1 holds in this
  chunk (upper bound 0.061).
- 83 of the 457 processed stars carry the clamped fallback values (m₁ = 2.2 M☉ from the
  absolute-magnitude table). `sb1_combine.py` gives the exact amendment-1 numbers.

## Every chunk-2 hit plot was opened

| Gaia DR3 | TIC | Gaia orbit | Class | In rate sample | What the plot shows | Status |
|---|---|---|---|---|---|---|
| 6073528478949603200 | 412083925 | P 8.574 d, K 7.3 km/s, m₂ sin i 0.088 M☉ | MODULATED | yes (sensitivity 1.0) | One group of low points, ~0.5% deep and ~4 h long, in sector 100 only (1 of 3 sectors); scattered | **A giant, not a dwarf** (below) |
| 6129981769596529152 | 334502995 | P 12.057 d, RUWE 2.1 | MODULATED | no (0.25) | A ramp and a jump next to the box; 0.8% modulation | Systematics |
| 390727988263983360 | 191226967 | P 9.408 d, m₁ clamped at 2.2 M☉ | MODULATED | no (0.25) | Narrow spikes and a shallow 0.06% dip among them | Systematics |

### TIC 412083925: an independent check of amendment 1
- The pipeline gave this star a main-sequence radius of 1.31 R☉ from the fallback table
  (no FLAME or GSP-Phot radius). Its Gaia colour and luminosity (BP−RP = 1.45, M_G = 2.72,
  not corrected for extinction) put it on the red-giant branch.
- The TESS Input Catalog (v8.2, via ExoFOP) independently lists **R = 4.9 R☉ and
  Teff = 5,080 K**: a giant. It has no TOI or CTOI.
- **Amendment 1's `giant_cmd` rule (table radius, BP−RP > 1.0, M_G < 3.5) already removes
  this star** from the A1 grade. This is the first hit where an outside catalogue confirms
  the rule. Around a 4.9 R☉ star, a 0.09 M☉ companion (≈ 1 R_Jup) would block about 0.04%
  of the light, 4 to 12 times less than the dip seen (box depth 0.17%; single points reach
  0.5–0.8%). So the dip cannot be this companion's transit, whatever it is.
- No claim is made about the star.

## Chunks 0, 1, 2 and 7 summed by hand (1,633 stars in the rate sample)

| Sample | Rate sample | Expected if all real | Robust hits | Substellar-size hits | ρ, substellar size (95%) |
|---|---|---|---|---|---|
| All | 1,633 | 294.0 | 14 | 5 | **0.017 (0.006–0.040)** |
| Brown-dwarf mass (BD) | 1,174 | 220.5 | 4 | **1** | **0.005 (0.0001–0.025)** |
| Very-low-mass star (VLMS) | 384 | 59.4 | 10 | 4 | 0.067 (0.018–0.173) |
| P < 5 d | 1,236 | 257.6 | 4 | 2 | 0.008 (0.001–0.028) |
| P ≥ 5 d | 397 | 36.4 | 10 | 3 | 0.082 (0.017–0.24) |

Intervals are exact Poisson (Garwood) on the substellar-size count, divided by the expected
count. ρ_all = (14 − 4.0 control) / 294.0 = 0.034. Of the 109 hits the 0.1.0 rule would have
made in these four chunks, the median rule rejects 95.

**Reading so far (interim, not a grade):**
- Among 1,174 brown-dwarf-mass Gaia DR3 SB1 orbits with sensitive TESS data, 220 transits
  would be expected if every orbit were real and that light. **One is seen**: TOI-6218.01,
  at 71 M_Jup, at the brown-dwarf/star boundary. Chunk 2 added 46 expected and none seen.
- The very-low-mass-star orbits do better, at ~7% (2–17%).
- The expected counts still include stars with untrustworthy fallback radii (amendment 1).
  Chunk 2 shows one directly: a "dwarf" with a hit that is really a 4.9 R☉ giant. The A1
  grade removes these stars.

## What happens next
- Chunks 3–6: grade each one as it lands.
- gaia-sb1comb: once all 8 chunks are in the repo, the combined primary grade and the A1
  grade.
- gaia-tic71945261-v1: the pre-registered fit of the chunk-7 survivor. It is still waiting
  for compute.
