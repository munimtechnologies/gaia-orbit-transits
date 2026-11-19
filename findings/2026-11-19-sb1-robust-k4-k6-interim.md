# sb1_robust 0.2.0, chunks 4 and 6: all eight chunks are in (interim hand sums)

2026-11-19. By MV2 of Munim, Inc.; made with AI agents working in his name, not yet checked by
a human expert. Text and data CC BY 4.0.

**This is not the graded result.** The pre-registered grade
(`findings/2026-11-18-sb1-robust-prereg.md`, plus amendment 1) is produced by `sb1_combine.py`
0.1.0, unchanged, on all eight chunks. That job (gaia-sb1comb-v2) is queued. It waits until
this commit is on GitHub before it starts. The hand sums below are superseded by it.

## Chunks 4 and 6 in numbers (`data/sb1rob-v1/k4/`, `data/sb1rob-v1/k6/`)

| | chunk 4 | chunk 6 |
|---|---|---|
| Stars processed in 165 min | 580 (560 with TESS data) | 797 (772 with TESS data) |
| Rate sample (injection sensitivity ≥ 0.5) | 436 | 619 |
| Expected transits if every orbit were real | 76.7 | 110.7 |
| Robust hits in the rate sample (substellar-size) | 1 (0) | 7 (3) |
| Brown-dwarf-mass orbits: rate sample / expected / substellar-size hits | 286 / 52.4 / **0** | 428 / 79.7 / **2** |
| C1 / C2 / C3 | pass / pass (0.23 %) / pass | pass / pass (0.32 %) / pass |
| 0.1.0-rule hits / rejected by the median rule | 25 / 24 | 45 / 38 |
| Rows on the clamped fallback (m₁ = 2.2 M☉) | 98 of 580 | 139 of 797 |

Both jobs reproduced the pre-registered pool of 6,434 stars.

## Every hit plot was opened

| Gaia DR3 | TIC | Class | In rate sample | What the plot shows | Status |
|---|---|---|---|---|---|
| 1119681069075931008 (k4) | 147892154 | MODULATED | yes | A noisy 0.17 % sag next to a slow trend; S/N 7.5 in one sector of three | Not a transit (variability/systematics) |
| 2838654459861938944 (k4) | 436508469 | SUBSTELLAR_SIZE | no (0.25) | A clean 0.4 % transit, ~4 h | **TOI-6117.01**, already a TOI |
| 1869489729418662528 (k6) | 232941965 | SUBSTELLAR_SIZE | yes | Transit in 2 of 3 sectors | **TOI-5882.01**, listed as a confirmed planet (CP) on the TOI list |
| 6594248591617970560 (k6) | 393940766 | SUBSTELLAR_SIZE | yes | A clean 0.44 % transit in all 3 sectors | **TOI-148.01**, a known companion near the hydrogen-burning limit (CP) |
| 3341401062125577088 (k6) | 52420398 | SUBSTELLAR_SIZE | yes | Control | **TOI-5427.01**, one of the four pre-registered controls; it belongs to chunk 6 |
| 125548289270234880 (k6) | 138017750 | MODULATED, PHASE_MATCH | yes | A real ~0.3 % dip on a modulated star | **TOI-1608.01**, already a TFOP false positive |
| 6006881684701920256 (k6) | 148479519 | MODULATED | yes | Ramps up to +30 %: scattered light | Systematics (RUWE 11.7) |
| 5606899283169481856 (k6) | 106415698 | MODULATED | yes | Scatter at a data gap | Systematics (RUWE 40) |
| 4522005765562277504 (k6) | 157429217 | MODULATED | yes | 80 ppm; G = 6.9 | Not a transit |

**D1 (substellar-size hits not on the TOI list) is empty in both chunks. No new candidate.**

## All eight chunks summed by hand (3,113 stars in the rate sample)

| Sample | Rate sample | Expected if all real | Robust hits | Substellar-size hits | ρ, substellar size (95 %) |
|---|---|---|---|---|---|
| All | 3,113 | 558.0 | 25 | 9 | **0.016 (0.007-0.031)** |
| Brown-dwarf mass (BD) | 2,180 | 407.7 | 11 | **3** | **0.007 (0.002-0.022)** |
| Very-low-mass star (VLMS) | 801 | 124.0 | 14 | 6 | 0.048 (0.018-0.105) |
| P < 5 d | 2,343 | 488.3 | 8 | 3 | 0.006 (0.001-0.018) |
| P ≥ 5 d | 770 | 69.7 | 17 | 6 | 0.086 (0.032-0.187) |

Intervals are exact Poisson (Garwood) on the substellar-size count divided by the expected
count, as in the earlier interim notes. Control periods: 8.5 false hits expected in all, so
ρ_all ≈ (25 − 8.5) / 558.0 = 0.030.

**Reading so far (interim, not a grade):**
- Among 2,180 brown-dwarf-mass Gaia DR3 SB1 orbits with sensitive TESS data, about **408
  transits would be expected if every orbit were real and that light. Three are seen**:
  TOI-6218.01, TOI-5427.01 and TOI-5882.01, all already known.
- If it holds in the graded run, **fewer than about 2 % of Gaia DR3's brown-dwarf-mass SB1
  orbits at P = 1-13 d describe a real brown-dwarf-mass companion on that orbit.**
- The very-low-mass-star orbits keep doing better (about 5 %). Both new eclipsing systems
  from this search are in that class: BD+65 286 (not in the rate sample) and TIC 71945261
  (see `findings/2026-11-19-tic71945261-fit-results.md`).
- C3 still fails for chunk 5 (141 < 150), as reported earlier.

## What happens next
- gaia-sb1comb-v2 gives the primary grade, the C3 result and the amendment-1 grade.
- A graded result will be written up with its limits.
