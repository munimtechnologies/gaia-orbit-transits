# sb1_robust 0.2.0, chunks 3 and 5 of 8, and six chunks together: interim, descriptive only

2026-11-19. By MV2 of Munim, Inc.; made with AI agents working in his name, and not yet
checked by a human expert. Text and data CC BY 4.0.

**This is not the graded result.** The pre-registered grade
(`findings/2026-11-18-sb1-robust-prereg.md`, plus amendment 1) combines all eight chunks.
Chunks 4 and 6 are still waiting for compute. This note puts the outputs of chunks 3 and 5
on record (`data/sb1rob-v1/k3/`, `data/sb1rob-v1/k5/`) and adds them to the hand sums of
chunks 0, 1, 2 and 7. Those sums are superseded when `sb1_combine.py` runs on every chunk.

## Chunks 3 and 5 in numbers

| | chunk 3 | chunk 5 |
|---|---|---|
| Stars processed in 165 min | 353 (347 with TESS data) | 182 (176 with usable data) |
| Rate sample (injection sensitivity ≥ 0.5) | 284 | **141** |
| Expected transits if every orbit were real | 52.2 | 24.5 |
| Robust hits in the rate sample | 1 (MODULATED) | 2 (1 MODULATED, 1 SUBSTELLAR_SIZE) |
| Brown-dwarf-mass orbits: rate sample / expected / substellar-size hits | 203 / 39.3 / **0** | 89 / 15.9 / **0** |
| C1 (known companions recovered) | 4 of 4 | 4 of 4 |
| C2 (control-period hit rate ≤ 3 %) | 0.35 % | 0.35 % |
| C3 (≥ 150 in the rate sample, per job) | pass | **FAIL (141)** |
| 0.1.0 rule hits / rejected by the median rule | 22 / 21 | 4 / 2 |
| Rows on the clamped fallback (m₁ = 2.2 M☉) | 50 of 353 | 30 of 182 |

Both jobs reproduced the pre-registered pool of 6,434 stars exactly.

**C3 fails for chunk 5.** MAST's TESS search timed out repeatedly during that job (logged as
"Timeout limit of 600 exceeded"), so it got through only 182 stars in the fixed 165-minute
budget. The pre-registration makes C3 a per-job check, so the combined report will say that
C3 failed. The job is not re-run: it did not fail, and its stars are a random subset of
its chunk like everyone else's. A failed C3 means this chunk adds less, not that its rows are
wrong.

## Every hit plot was opened

| Gaia DR3 | TIC | Gaia orbit | Class | In rate sample | What the plot shows | Status |
|---|---|---|---|---|---|---|
| 516148832971513344 (k3) | 50453242 | P 1.6465 d, K 13.1 km/s, m₂ sin i 0.098 M☉ | SUBSTELLAR_SIZE, PHASE_MATCH (z = −1.5) | **no** (sensitivity 0.0) | A clean, flat-bottomed ~0.4 % eclipse, ≈ 3 h, identical in sectors 52, 85 and 86, on top of a strong ellipsoidal wave | **BD+65 286: an uncatalogued eclipsing system. Fit pre-registered** (`findings/2026-11-19-bd65-286-prereg.md`) |
| 209360173711680640 (k3) | 267903279 | P 6.164 d, m₁ clamped at 2.2 M☉ | MODULATED | yes | A ramp and two spikes next to the box; one sector of three | Systematics. The star is a luminous red giant (M_G = −1.44, BP−RP = 2.60) that entered on the fallback radius. Amendment 1's `giant_cmd` removes it |
| 6072000501396670464 (k3) | 398632451 | P 6.214 d, RUWE 3.7 | MODULATED | no (0.25) | Jumps of +1 % to +3 % around the box | Systematics |
| 448566526132005760 (k5) | 317029836 | P 2.082 d, m₂ sin i 0.050 M☉ | MODULATED | yes | A broad, shallow 0.04 % sag; expected depth 0.44 % | Not a transit of this companion (ten times too shallow) |
| 1802445358630815104 (k5) | 51318828 | P 6.877 d, m₂ sin i 0.090 M☉ | SUBSTELLAR_SIZE | yes | A clean ~1 % flat-bottomed eclipse in sector 81 | **TOI-7247.01**, already on the TOI list (TFOP: false positive, citing the Gaia orbit; a 2026 RAVEN upload calls it a likely planet). Counted as a hit, not a D1 candidate. Added to the BD+65 286 fit job |

BD+65 286 is outside the rate sample, so it does not enter ρ. Its sensitivity is 0 because
the injected box (0.8 × the expected depth, 0.26 %) sits below S/N 7 under the star's
ellipsoidal residual, while the real 0.40 % eclipse reaches S/N 9–10. That is our reading of
the numbers in `sb1_sectors.csv`, not a separate test.

## Six chunks summed by hand (0, 1, 2, 3, 5, 7; 2,058 stars in the rate sample)

| Sample | Rate sample | Expected if all real | Robust hits | Substellar-size hits | ρ, substellar size (95 %) |
|---|---|---|---|---|---|
| All | 2,058 | 370.7 | 17 | 6 | **0.016 (0.006–0.035)** |
| Brown-dwarf mass (BD) | 1,466 | 275.7 | 6 | **1** | **0.004 (0.0001–0.020)** |
| Very-low-mass star (VLMS) | 503 | 77.9 | 11 | 5 | 0.064 (0.021–0.150) |
| P < 5 d | 1,559 | 325.4 | 5 | 2 | 0.006 (0.0007–0.022) |
| P ≥ 5 d | 499 | 45.3 | 12 | 4 | 0.088 (0.024–0.23) |

Intervals are exact Poisson (Garwood) on the substellar-size count, divided by the expected
count, as in the earlier interim notes. Control periods: 5.5 expected false hits in all, so
ρ_all = (17 − 5.5) / 370.7 = 0.031.

**Reading so far (interim, not a grade):**
- Among 1,466 brown-dwarf-mass Gaia DR3 SB1 orbits with sensitive TESS data, about 276
  transits would be expected if every orbit were real and that light. **One is seen**
  (TOI-6218.01, 71 M_Jup, at the brown-dwarf/star boundary). Chunks 3 and 5 added 55
  expected and none seen.
- The very-low-mass-star orbits keep doing better, at about 6 % (2–15 %). Both
  new eclipsing companions in these chunks (BD+65 286 and TOI-7247.01) are in that class.
- The expected counts still include stars with untrustworthy fallback radii. Chunk 3 shows a
  second direct example: a "dwarf" hit that is really a luminous red giant. The amendment-1
  grade removes these stars.

## What happens next
- Chunks 4 and 6: grade each one as it lands. Then gaia-sb1comb-v2 gives the combined primary
  grade, the C3 result and the amendment-1 grade.
- gaia-bd65286-v1: the pre-registered fit of BD+65 286, with TOI-7247.01 and TOI-1251.01.
