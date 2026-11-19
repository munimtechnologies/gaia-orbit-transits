# Amendment 1 to the DR4 wobble pre-registration (filed before any fit)

2026-11-19. By MV2 of Munim, Inc.; made with AI agents working in his name, not yet checked by
a human expert. Text CC BY 4.0. Amends `findings/2026-11-19-dr4-wobble-prereg.md`.

**What had been seen when this was written:** Gaia DR4 does not exist yet (release 2 December
2026). Of ESA's 12-source DR4 pre-release, we had read only the VOTable's field list and its
TIMESYS element (through the unmodified copy that EXOZIPPy commit 722a880 ships), plus the
14-column DataLink CSV sample in ESA's gaia-supdate tests. **No epoch values had been fitted.**
The rehearsal job (gaia-wobble-reh-v1) is filed together with this amendment.

## Why an amendment
The pre-registration assumed one row per CCD, grouped by `transit_id`. ESA's files are not
laid out that way:
- **The pre-release VOTable** (data model "Gaia DR4_RC3") has one row per field-of-view
  transit. Per-CCD quantities are arrays (`obs_time_tcb`, `scan_pos_angle`, `centroid_pos_al`,
  `centroid_pos_error_al`, `used_by_agis_al`, and also `colour_factor_al`). The scalars are
  `transit_id`, `obs_time_bary_corr`, `parallax_factor_al` and `agis_source_excess_noise`.
  TIMESYS is TCB with origin JD 2455197.5, at the barycentre.
- **The DataLink CSV sample** in gaia-supdate has the same per-transit layout, with
  `colour_factor_al` as a scalar. It has **no `transit_id` column**, and `used_by_agis_al`
  appears twice in its header.

Under the original wording, a missing `transit_id` would stop the release-day job (exit 4)
even though every row already is one transit.

## Changes (rules only; thresholds and predictions are unchanged)
1. **`transit_id` is required only when rows are per CCD** (exploded). When the per-CCD
   values are arrays, each row is one transit. All other required names are unchanged, and
   any missing one still stops the job (exit 4).
2. **Per-CCD scalars inside a transit.** `colour_factor_al` and `parallax_factor_al` are
   averaged over the CCDs kept for that transit. The colour column enters the model only if
   it is finite for every transit of the source and not constant.
3. **CCDs kept:** `used_by_agis_al` true, plus a finite centroid, a positive finite error, a
   time > 0, and finite scan angle, barycentric correction and parallax factor. The
   `multipeak` and `blended` flags are not used, as in gaia-supdate's default path. Where a
   duplicated column name occurs, the first occurrence is used.
4. **Transit time** = mean of the kept CCDs' `obs_time_tcb` + `obs_time_bary_corr`. **Scan
   angle** = circular mean of the kept CCDs' angles.
5. **At least 15 transits** per source are needed. Below that, a target is TOO_FEW_TRANSITS:
   it is not counted in W0–W3, but it is counted and reported.
6. **σ(cos i)** is the standard deviation of the signed cos i over the 300 covariance draws
   (seed 20261202).
7. **Rehearsal null test.** Each QSO is fitted at **HD 114762's DR3 P, e and T**, because a
   QSO has no orbit of its own. The six single stars are fitted the same way, reported
   descriptively. If HD 114762 has no astrometric DR3 solution, its DR3 spectroscopic P, e
   and T are used, for the rehearsal only. The release-day test requires a DR3 Thiele-Innes
   orbit, as before.
8. **Download.** The rehearsal reads ESA's zip from the Gaia FTP. If that fails, it falls back
   to the byte-identical XML in EXOZIPPy (commit 722a880) and records the source and SHA-256.
9. **Also reported, not graded:** Δχ² without the excess noise, and a plot of the single-star
   residuals against the fitted orbit term.

## Code
`dr4_wobble.py` 0.1.0 implements the pre-registration plus this amendment. Its tests
(`test_dr4_wobble.py`, standard library only) cover:
- the Kepler solver and the Thiele-Innes inversion;
- ESA's CSV layout;
- the transit_id rule;
- synthetic edge-on, face-on and no-orbit sources;
- the W0–W3 outcome logic.
