# Can Gaia's own quality columns find the real low-mass SB1 orbits? Graded (job gaia-qcut-v1)

Written 2026-11-20 (about 07:00 UTC) by MV2 of Munim, Inc.; made with AI agents working in his
name, not checked by a human expert. Text and data CC BY 4.0, code Apache-2.0.

Rules: `findings/2026-11-20-quality-cut-prereg.md` (written before any quality column of the rate
sample was fetched). Code: `qcut.py` 0.1.0 (release v0.32.0, commit 2cbdd5b) with pinned
dependencies. Raw output: `data/qcut-v1/` (`qcut_summary.json`, `qcut_report.md`, `job_summary.json`;
the per-star table `qcut_stars.csv` and the archive columns `qcut_columns.csv`, which the Gaia DR4
step Q4 reads). Job ran 20 Nov 04:15-04:19 UTC, unit tests first, exit 0.

## Self-checks: all passed

RC1 archive rows 11,937 (≥ 6,434); RC2 all 3,113 rate-sample stars matched; RC3 significance
agrees for all 3,113; RC4 rate sample reproduced (3,113 stars, E_iso 557.98, 25 hits); RC5 BD-class
central E_pop reproduced (241.13).

## Q1 (primary): Gaia's "gold sample" cut. Label **UNDERPOWERED**

Gosset et al. 2024 (arXiv:2410.14372, Appendix J) recommend efficiency ≥ 0.2,
rv_n_good_obs_primary ≥ 20, significance ≥ 40 and 2 ≤ P ≤ 800 d. Of the 2,981 brown-dwarf- and
very-low-mass-class orbits in our rate sample (P = 1-13 d), **only 9 (0.3%) pass the gold cut**.
Those 9 would be expected to show 1.2 transits if every orbit were real with its minimum mass (E_iso); they
show 1. Under the most generous population, E_pop(floor) = 0.34, far below the 7.5 needed to test
anything, so the label is UNDERPOWERED (the SB1-only variant is identical).

| group | stars | transit hits | E_iso | ρ_all (95%) | φ central (95%) |
|---|---|---|---|---|---|
| gold | 9 | 1 | 1.2 | 0.85 (0.02-4.72) | 1.34 (0.03-7.48) |
| not gold | 2,972 | 24 | 530.5 | 0.031 (0.015-0.053) | 0.021 (0.006-0.045) |

**What it means (as fixed in advance):** the gold cut cannot rescue this class. It removes 99.7%
of Gaia DR3's short-period, low-mass-function SB1 orbits, so it says nothing about whether the
remaining orbits are right. The cut was built for the whole SB1 catalogue. Its significance ≥ 40
requirement shuts out almost every orbit with K below about 6-25 km/s. The four known transiting
brown-dwarf and planet controls in our sample have significance 6.7-13.6, so they are excluded
too.

## Q2 (primary): does the transit rate rise with Gaia's significance? Label **RISES_PRIMARY_ONLY**

| tier (significance) | stars | hits | substellar-size hits | E_iso | ρ_all (95%) | φ central (95%) | φ floor (95%) |
|---|---|---|---|---|---|---|---|
| T1 (< 10) | 1,834 | 13 | 4 | 331.6 | 0.029 (0.010-0.056) | 0.015 (0.000-0.047) | 0.038 (0.001-0.117) |
| T2 (10-20) | 974 | 7 | 3 | 173.3 | 0.020 (0.000-0.063) | 0.024 (0.001-0.080) | 0.044 (0.002-0.146) |
| T3 (≥ 20) | 173 | 5 | 2 | 26.9 | **0.167 (0.042-0.416)** | 0.121 (0.015-0.437) | 0.163 (0.020-0.590) |

- Primary test (all hits against E_iso, T3 vs T1): N = 18, **p = 0.016** (one-sided) → passes.
- Robustness test (substellar-size hits against central E_pop): N = 6, p = 0.052 → does not pass.
- Label: **RISES_PRIMARY_ONLY.**

Orbits with significance ≥ 20 show transits about six times as often, relative to expectation, as
those below 10. Even in the top tier, though, the share of orbits that can be right is about
**12% under the central population (95% upper bound 44%)**. Only the most generous population
allows a majority (floor upper bound 59%). In the lower tiers, where 94% of these orbits sit, the
share is 1.5-4.4% (central to floor populations). Descriptive reading, not a graded label: significance helps, but no
significance tier of this class can be trusted as it stands.

## Q3 (exploratory): other columns. No column passes (Bonferroni α = 0.01)

| column | better half (fixed) | good-half ρ_all | bad-half ρ_all | p (one-sided) |
|---|---|---|---|---|
| efficiency | high | 0.023 | 0.044 | 0.90 |
| rv_n_good_obs_primary | high | 0.020 | 0.046 | 0.94 |
| goodness_of_fit | low | 0.056 | 0.009 | 0.0104 |
| conf_spectro_period | high | 0.033 | 0.032 | 0.56 |
| rv_amplitude_robust / 2K | low | 0.047 | 0.019 | 0.10 (24 stars missing the column) |

goodness_of_fit misses the corrected threshold by a hair, in the pre-registered direction. Two of
the gold-cut ingredients, efficiency and the number of good RV epochs, point the **wrong way**:
the "better" half transits less often. That direction was not tested, so it is only a
description.

## Predictions (written before the job)

- Q1: UNDERPOWERED 70% → **held** (the most likely outcome).
- Q2: RISES_WITH_SIGNIFICANCE 45%, RISES_PRIMARY_ONLY 15%, NO_RISE 40% → **the 15% outcome
  happened.**
- Q3: at most one column passes (70%) → **held** (none passed). Most likely to pass: the amplitude
  ratio A (35%) → **did not pass** (p = 0.10).

## What comes next

Q4 is graded on Gaia DR4 day (2 December 2026) with `qcut_dr4.py` 0.1.0 (committed 20 Nov, before
this output existed). It asks whether DR4 confirms gold-cut and high-significance DR3 orbits more
often than the rest. With only 9 gold stars in the rate sample, Q4a will be judged on the whole
6,434-orbit pool, as pre-registered. If DR4 confirms the Q2 trend, a transit-calibrated reality
score for low-mass SB1 orbits becomes worth building, with a held-out test.

## Limits

These are population statistics; no single orbit is called wrong. The transit test cannot tell a
wrong period from a right period with a diluted K (a blended double-lined binary); only DR4 can.
The tier edges were set after seeing where the four transiting controls fall (which is why T3 is
tested against T1). About 7.5 of the 25 hits in these two classes are expected false alarms (from
control folds), and the rates subtract them.
