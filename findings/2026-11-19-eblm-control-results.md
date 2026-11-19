# Results: does our Gaia + TESS EBLM fit recover published M-dwarf radii? (job gaia-eblmctl-v1)

Graded 2026-11-19 (about 18:30 UTC) against the pre-registration
`findings/2026-11-19-eblm-control-prereg.md`, which was committed before the job ran. By MV2 of
Munim, Inc.; made with AI agents working in his name, and not checked by a human expert. Text
CC BY 4.0, code Apache-2.0. Raw outputs: `data/eblmctl-v1/` (job ran 19 Nov 16:39-16:50 UTC on
the unchanged `eblm_single.py` / `eblm_fit` 0.1.0; unit tests passed; all 7 systems fitted).

All seven fit plots were opened before any label was written down.

## Pre-registered grade: **PIPELINE_FAILED**

All six controls are testable (none UNTESTED, none labelled G). **Two of six pass** (33%). The
pre-registered bar was 80% (5 of 6).

| EBLM | Gaia DR3 | label | r2 (R☉) | published R₂ | r2/R₂ − 1 | r2_flame/R₂ | m2 (M☉) | published M₂ | m2/M₂ | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| J0941-31 | 5440085875822885888 | C (EBLM_CONSISTENT) | 0.2253 | 0.2365 | −4.7% | – (no FLAME) | 0.1996 | 0.2173 | 0.918* | **PASS** |
| J0540-17 | 2970781118606872192 | A2 (MASS_TENSION_LIGHTER) | 0.1992 | 0.1949 | +2.2% | 1.017 | 0.1780 | 0.1633 | 1.090 | fail (label) |
| J0719+25 | 870991952855398656 | C (EBLM_CONSISTENT) | 0.1897 | 0.1917 | −1.0% | 0.989 | 0.1502 | 0.1584 | 0.948 | **PASS** |
| J1522+42 | 1393971390134144640 | A2 (MASS_TENSION_LIGHTER) | 0.2092 | 0.1915 | +9.3% | 0.994 | 0.1580 | 0.1656 | 0.954 | fail (label) |
| J1741+31 | 4600624489073375744 | A2 (MASS_TENSION_LIGHTER) | 0.3244 | 0.377 | −14.0% | 1.245 | 0.4301 | 0.461 | 0.933 | fail (label and radius) |
| J0123+38 | 323261744326472832 | A2 (MASS_TENSION_LIGHTER) | 0.3505 | 0.3531 | −0.7% | 0.986 | 0.3457 | 0.338 | 1.023 | fail (label) |

\* J0941-31 has no FLAME primary mass, so the pipeline used its default 1.3 M☉.

Published values: Swayne et al. 2024 (MNRAS 528, 5703), Table 4. Pipeline values: columns `r2`,
`r2_flame`, `m2` of `data/eblmctl-v1/eblm_fit_results.csv`; ratios computed by hand and
collected in `data/eblmctl-v1/grade.json`.

Reported, not graded:
- **Median radius offset of the six testable controls, median(r2/R₂ − 1): −0.9%** (values
  −14.0, −4.7, −1.0, −0.7, +2.2, +9.3%). This is inside ±3%, so under the pre-registration the
  inflation note gets **no offset addendum**.
- Radius alone: 5 of 6 within ±10% of the published value; only J1741+31 is outside (−14%).
- Masses: median m2/M₂ = 0.951 (range 0.918-1.090).
- Descriptive system EBLM J1219-39 (not graded): label C, m2 0.122 M☉, r2 0.135 R☉.

## Our predictions, scored
- PIPELINE_VALIDATED 65% / FAILED 25% / INCONCLUSIVE 10%: **the outcome was FAILED. Our
  favoured outcome was wrong.**
- Median radius offset within ±5% (70%): **held** (−0.9%).
- J1741+31 most likely to fail: it did fail, and it is the only control whose radius is off by
  more than 10%. But three other controls failed too, for a reason we did not anticipate.

## What the pre-registration says happens now (applied)
- **BD+65 286's label C is not adopted.** Its fitted numbers (0.100 M☉, 0.122 R☉) stay public as
  measurements, but no label is claimed and nothing is submitted to AAVSO VSX on the strength
  of this pipeline.
- **The short-period M-dwarf inflation grade (+6.3%, INCONCLUSIVE) carries a caveat:** the
  pipeline that produced it failed a pre-registered outside check. See the next section for
  which part failed.
- **The fit is investigated before any Gaia DR4 run.** This note is the start of that.

## Why it failed (exploratory, written after seeing the data)
Everything in this section is post hoc. It explains the failure; it does not change the grade.

1. **All four failures come from the mass-consistency step, not from the radius.** eblm_fit
   flags MASS_TENSION_LIGHTER when the fitted ellipsoidal amplitude plus 3σ falls below half
   of the amplitude Gaia's mass predicts. The fitted amplitudes (ppm, ± white-noise error,
   predicted in brackets):
   J0941-31 +122 ± 16 [292]; J0540-17 −7 ± 10 [236]; J0719+25 +142 ± 17 [90];
   J1522+42 −52 ± 14 [146]; **J1741+31 −122 ± 12 [54]; J0123+38 −586 ± 63 [417]**;
   J1219-39 −17 ± 21 [21].
   A tidal ellipsoid cannot have a negative amplitude, yet three of seven are negative by more
   than 3σ (−3.7σ, −10.5σ, −9.4σ). **The quoted errors are too small by large factors at these
   periods.** The fit errors are white-noise errors on phase-binned flux. Red noise is not
   included: starspot modulation, residual systematics in the SPOC light curves, and (point 2)
   unmodelled eclipses. At 5.5-8 days the predicted signal is only 50-420 ppm, so it is easily
   swamped. Of the 167 fits behind the inflation test (jobs gaia-eblm-fit-v1, -rest-a-v1 and
   -rest-b-v1), 9 (5.4%) got a mass-tension label. At the controls' 5.5-8 days, 4 of 6 did.
2. **Eccentric orbits are not modelled.** eblm_fit fixes the occultation at phase 0.5. The plots
   show the secondary eclipse of J0941-31 near phase 0.61, of J0719+25 near 0.45 and of
   J1522+42 near 0.44. Those dips are left in the residuals and leak into the harmonic terms. The
   fitted occultation depths are meaningless for these three (for example J0719+25: −219 ± 90
   ppm). Most systems in the 0.9-3.5-day inflation sample should be tidally circularised, but
   this is not checked.
3. **J1741+31 is nearly grazing** (fitted b = 0.90 with k = 0.36, so b > 1 − k). Without the
   mass-tension label, eblm_fit would have labelled it EBLM_GRAZING (G), which the
   pre-registration treats as untestable. Even then 2 of 5 pass, still FAILED.

## What this does and does not say about earlier results
- **Inflation (+6.3%).** The controls' radius scale agrees with the literature (median −0.9%).
  That suggests the +6.3% is not a pipeline radius offset. But the controls lie at 5.5-8 days with
  G/K primaries, not at the inflation sample's 0.9-3.5 days with mostly F/A primaries. Also, the
  same failing step decides which systems count as clean. The grade stands as published
  (INCONCLUSIVE), with this caveat.
- **TIC 71945261** (B_OVERSIZED_COMPANION, 2.33 d) rests on the same pipeline. Its companion
  radius is 1.9× the main-sequence value. That excess is far larger than any radius error seen
  here, but the label is equally covered by the caveat.
- **BD+65 286** (1.65 d): its ellipsoidal amplitude was 0.81× the prediction, where the predicted
  signal is far larger than at these controls' periods. Under the rule its label is still not
  adopted.

## Next (not yet pre-registered)
- eblm_fit 0.2.0: an ellipsoidal error that includes red noise (sector-to-sector scatter or the
  binned-residual β factor), and an occultation phase from Gaia's e and ω or left free.
- The six controls above shaped the fix, so they cannot validate it. A fresh control set will be
  chosen by rule **before** fitting, for example the Swayne et al. 2024 systems with P ≥ 8 d and
  other published EBLM radii that have a Gaia DR3 SB1 orbit. It will be pre-registered with
  0.2.0 and run before Gaia DR4's EBLM step.
