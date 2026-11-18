# Are M dwarfs in 1-2-day orbits inflated? Results of eblm_infl 0.1.0 (graded)

2026-11-18. MV2 of Munim, Inc.; made with AI agents working in his name. No human expert has
checked this yet. Text CC BY 4.0, code Apache-2.0.
Pre-registration: `findings/2026-11-17-short-period-inflation-prereg.md` (written before
job gaia-eblm-fit-v1 had produced anything). Job: `gaia-eblm-infl-v1` (eblm_infl 0.1.0,
unchanged), 2026-11-18 18:24-18:27 UTC. Outputs: `data/eblm-infl-v1/`.

## Inputs and reference model

- 70 rows of `data/eblm-fit-v1/eblm_fit_results.csv`.
  - 26 clean EBLM fits.
  - **14 in the pre-registered main set**: b < 0.8, fit SNR ≥ 30, FLAME mass and radius,
    0.08 ≤ m₂ ≤ 0.6 M☉, and light-curve R₁ within 20% of FLAME's.
  - Cuts: 44 not a clean verdict, 9 without a FLAME mass, 2 with SNR < 30, 1 with b ≥ 0.8.
- The reference is the real BHAC15 isochrone file, downloaded from the authors' site
  (`model_source` in `infl_summary.json`); the transcribed fallback was not needed.
  - The fallback values agree with the file at every check point (0.1-0.4 M☉; 1, 5 and
    10 Gyr).
- The main set spans **P = 0.9-2.2 d** (10 of 14 at 1-2 d). Swayne et al. (2024) found their
  inflation at 2.78-4.30 d, so **this sample does not overlap their short-period group**.
  It tests whether that inflation continues to shorter periods.

## Grades

| test | pre-registered rule | result | grade |
|---|---|---|---|
| **H1** median inflation (k·R₁,FLAME vs BHAC15 5 Gyr) | INFLATED if lower 95% > +3%; NOT_INFLATED if upper < +3% | n = 14, median **+2.2%**, 95% CI [+0.3%, +7.1%]; contains Swayne's +6% | **INCONCLUSIVE** |
| **H2** Spearman ρ(inflation, P), one-sided ρ < 0 | PERIOD_TREND if p < 0.05 | ρ = **+0.49** (opposite sign), one-sided p = 0.96 | **NO_TREND_DETECTED** |

Our pre-registered odds were INCONCLUSIVE 35% and PERIOD_TREND 25%.

**Confounder flag (pre-registered):** ρ(m₂, P) = +0.49, which is above the 0.3 threshold.
The positive ρ(inflation, P) is therefore not interpretable as a period effect. Longer
periods in this sample also have heavier companions, and ρ(inflation, m₂) = +0.23. No
period claim is made either way.

## Reported, not graded

| set / R₁ source / age | n | median | 95% CI |
|---|---|---|---|
| main, FLAME, 1 Gyr | 14 | +3.9% | [+2.3, +9.7] |
| main, FLAME, 5 Gyr (primary) | 14 | +2.2% | [+0.3, +7.1] |
| main, FLAME, 10 Gyr | 14 | +1.0% | [−1.2, +5.8] |
| main, light curve, 5 Gyr | 14 | +3.2% | [+0.1, +6.1] |
| all clean, FLAME, 5 Gyr | 17 | +0.8% | [−4.2, +7.0] |
| all clean, light curve, 5 Gyr | 26 | +2.6% | [−1.8, +7.1] |

- Period bins of the main set:
  - 0-1 d: one system at −13.6%;
  - 1-2 d: n = 10, +2.2% [−1.1, +7.1];
  - 2-5 d: n = 3, +7.0% [+0.2, +24.8];
  - ≥ 5 d: none.
- The plot is `data/eblm-infl-v1/infl_vs_period.png`. One main-set system at 2.1 d
  (Gaia DR3 5851944656586312448, verdict EBLM_LARGE_RADIUS) sits at +25%. Without it the
  2-5 d bin would be +3.6% (n = 2, post hoc, not used).
- The 3 clean fits far below zero (−91% to −97%) were already cut from the main set by the
  pre-registered rules (SNR < 30, or b ≥ 0.8). Their radius ratios are tiny (k = 0.005-0.021; one sits
  at the fit's lower bound), so they are fit failures, not small stars.

## What it means

- With 14 Gaia-weighed systems, M dwarfs in 1-2-day orbits are consistent with a few
  percent of inflation (+2%, 95% CI +0.3% to +7%) against BHAC15. That range includes both
  the ~3% long-period norm and Swayne et al.'s ~6%.
- The data cannot separate those values.
- **Nothing here shows that inflation grows toward shorter periods.** The trend in the
  sample goes the other way, but it is confounded with companion mass.
- Every age and estimator choice gives the same INCONCLUSIVE label.
- As pre-registered for INCONCLUSIVE, the test moves to Gaia DR4 (2 December 2026). Its
  ~639k RVS SB1 orbits (3.5 times DR3) should multiply the main set. The two remaining
  eblm_fit chunks (gaia-eblm-rest-a/b-v1) are still waiting for compute and will be added
  with the same code before then.

## Limits

- n = 14.
- Metallicity is not modelled (BHAC15 is solar).
- Gaia DR3 SB1 amplitudes for broad-lined primaries may be biased.
- Selection favours deep eclipses.
- The main set does not reach Swayne et al.'s 2.8-4.3-day range, so this is not a direct
  replication of their result.
