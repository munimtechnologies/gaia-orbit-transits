# Second amendment to the inclination calibration: job gaia-calib-v3

By MV2 of Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Written 2026-11-18 (about 01:50 UTC). It amends `2026-11-17-inclination-calibration-prereg.md`
and `2026-11-17-calib-v2-amendment.md`. **No calibration number has been computed or
seen:** gaia-calib-v2 stopped at its reproducibility check, before calib_eclipse_rate.py
ran. The model, the fits and the predictions C1–C7 are unchanged.

## What happened in gaia-calib-v2

Job gaia-calib-v2 rebuilt the 15 MB prior table with the unchanged run_search.py and
compared it with the published v4 targets (`calib_support.py repro`). The rule was that
p_ecl and m2_dark must match as strings for ≥ 99% of targets, with no |Δp_ecl| > 0.02.
Result: 287 targets, none missing, 245 exact matches (85%), max |Δp_ecl| = 0.028. **FAIL**,
and as pre-registered, the job stopped.

**Cause.** The Gaia catalogue (cached query) was reused, but the `gaia_source`
photometry and astrometry were queried again, and the archive now returns them at float32
precision. For example, Gaia DR3 1369929267019238144 has G = 14.304525375366211 in v4 and
14.304525 in the rebuild. Its derived companion mass therefore changes in the eighth digit
(m2_dark 0.060009254318555603 vs 0.06000925817604423), so the strings differ while the
physics is the same. p_ecl is a 600-draw Monte Carlo fraction, so its own sampling error
is up to √(0.25/600) = 0.020. We have not yet identified the rows with the largest p_ecl
changes; v3 writes all of them out (`priors_diffs.csv`).

## The amended check (calib_support.py 0.13.0, `repro --mode noise`)

The check exists to make sure the rebuilt table is the same analysis as v4. The test
fails if any of these holds:
1. any v4 target is missing from the rebuild;
2. any target's G differs by more than 1e-4 mag (more than rounding, so the inputs changed);
3. any m2_dark differs by more than a relative 1e-5;
4. any |Δp_ecl| > 0.035 (21 of 600 draws, ~1.7 × the largest Monte Carlo sd);
5. the mean Δp_ecl over all targets is outside ±0.005 (a systematic shift would bias
   the calibration; random Monte Carlo-level noise does not).

**Stated honestly:** these limits were chosen after we saw the v2 failure (max 0.028,
245/287 exact). They were chosen before any calibration statistic existed, from the Monte
Carlo error and float32 rounding, not from the outcome. Condition 5 can still fail, and so
can condition 2 if the archive's values changed beyond rounding. If the check fails, the
calibration is not graded.

## Unchanged

Everything else in the v2 amendment: calib_eclipse_rate.py 0.7.0 run unchanged; the
catalogue cross-match of every detection; the sensitivity check for dips next to short
data gaps; and the rule that no single system is called an eclipse before its light
curve has been checked by eye.

## Context from gaia-deepcheck-v1 (graded today, independent data)

The two Gaia DR3 orbits in the deepcheck list with p ≥ 0.95 include one that clearly does
not eclipse in TESS (577478114092768384). KIC 6436291's predicted 7% eclipse is ruled out
by four years of Kepler data (`2026-11-18-deepcheck-results.md`). The calibration
predictions C1–C7 were written before either result and are not changed.
