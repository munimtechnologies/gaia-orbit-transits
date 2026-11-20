# Pre-registration: can Gaia's own quality columns tell real low-mass SB1 orbits from wrong ones?

MV2 of Munim, Inc. (made with AI agents working in his name). Written 2026-11-20, before any
quality column (efficiency, rv_n_good_obs_primary, goodness_of_fit, conf_spectro_period,
rv_amplitude_robust) of the rate sample was fetched, tabulated or looked at. The only quality column
seen so far is `significance`, which `sb1_stars.csv` has carried since sb1_transit 0.1.0. Its
per-tier transit counts have **not** been computed. The values of the four known transiting
controls were seen (listed below) and shaped the tier edges, which is why Q2 tests T3 against T1
and not against the control range. Code: `qcut.py` 0.1.0 with tests `test_qcut.py`; pinned
dependencies fetched by `fetch_qcut_deps.py` (sb1_combine 0.1.0 @ 25020a8, inclination_floor
0.1.0 @ db5b295). Licence: Apache-2.0 for code, CC BY 4.0 for text and data.

## Why this question

The graded amendment-2 result (findings/2026-11-19-sb1-robust-amendment-2-results.md) says that
most Gaia DR3 SB1 orbits with brown-dwarf-like minimum masses at P = 1-13 d cannot be right.
Even after allowing for heavier companions seen face-on, the fraction that can be right is about
1 % (central population, 95 % upper 3.4 %) to 10 % (most generous population, upper 32 %). The
VLMS class shows the same deficit (φ 0.04-0.07). Anyone who uses these orbits, whether for
brown-dwarf-desert statistics, dark-companion searches or DR4 planning, now needs a rule that keeps
the real ones. Gaia's own SB1 paper offers one. Gosset et al. 2024 (arXiv:2410.14372, Appendix J)
recommends a "gold sample": `efficiency >= 0.2`, `rv_n_good_obs_primary >= 20`,
`significance >= 40` and `2 <= period <= 800` d, with a quoted period-recovery rate of 93 %.
Its Sect. 9.4.6 also says that periods below about 10 d "are generally robust provided the
solution significance is not too low", with about 90-95 % success once the significance exceeds
15-20. Bashi et al. 2022 (arXiv:2207.08832) built a score from LAMOST/GALAH RVs (clean sample at
score > 0.587). Its coefficients are not in a form we could retrieve, so it is not tested here.

Neither paper tests its cut on short-period, low-mass-function orbits against an independent
physical truth. The transit test is one: if an orbit and its minimum mass are right, its
companion transits with a calculable probability. The four known transiting brown-dwarf and
planet controls in our sample (TOI-5427, TOI-1712, TOI-2533, WASP-18) have Gaia significance
of only 6.7-13.6. Real low-mass orbits can therefore sit far below the gold cut, and the
question is not obvious.

## Sample and quantities (fixed)

- Stars: the combined rate sample of sb1_robust 0.2.0 (8 chunks, data/sb1rob-v1/k0-k7; 3,113
  stars, `sb1_combine.in_rate_sample`). Tests use the BD and VLMS classes only (2,981 stars). The
  planet class (132 stars) is excluded because inclination_floor gives it c = 0.
- Quality columns: one sync ADQL query per period bin with exactly sb1_transit 0.1.0's selection
  (SB1/SB1C, 1 <= P < 13 d in bins 1, 1.5, 2, 3, 5, 8, 13; G <= 13; K^3 P < 15440). The query
  returns `efficiency`, `rv_n_obs_primary`, `rv_n_good_obs_primary`, `goodness_of_fit`,
  `conf_spectro_period`, `flags`, `significance` and `period` from gaiadr3.nss_two_body_orbit, plus
  `rv_amplitude_robust`, `rv_nb_transits`, `rv_chisq_pvalue` and `rv_renormalised_gof` from
  gaiadr3.gaia_source. Rows are joined by source_id. All rows are saved as `qcut_columns.csv`
  (≥ 6,434 rows, so the whole DR4 S3 pool is covered).
- Per group: hits n (any size), substellar-size hits n_sub, control false alarms fa / fa_sub,
  E_iso = Σ p_transit × sensitivity, and E_pop = Σ p_transit × sensitivity × c under the
  central and floor populations of inclination_floor 0.1.0. ρ_all = (n − fa)/E_iso and
  φ = (n_sub − fa_sub)/E_pop, with Garwood 95 % intervals, all exactly as in sb1_combine and
  inclination_floor.

## Self-checks (any failure: exit 3, no grade)

- RC1: the archive returns ≥ 6,434 rows.
- RC2: every rate-sample star is matched.
- RC3: `significance` from the archive agrees with sb1_stars.csv (relative 1e-4) for ≥ 99 % of stars.
- RC4: the combined rate sample is reproduced: 3,113 stars, E_iso 558.0 ± 0.5, 25 hits.
- RC5: the BD-class central E_pop is reproduced: 241.1 ± 0.5.

## Q1 (primary): Gaia's gold sample

Gold = all four Appendix-J criteria, applied to SB1 and SB1C alike. The table restriction to
'SB1' in Appendix J is a selection of solution type, not a quality criterion, and circular
orbits are the physically expected case at these periods. The SB1-only variant is reported as a
secondary result. The label is computed on gold BD + VLMS stars:
- **UNDERPOWERED** if E_pop(floor) < 7.5 (then even zero transits could not push the floor upper
  bound below 0.5);
- **GOLD_FAILS** if the floor φ upper 95 % < 0.5 (even under the most generous population, most
  gold orbits are wrong);
- **GOLD_PLAUSIBLE** if the central φ upper 95 % ≥ 0.5 (we cannot reject that most gold orbits
  are right);
- **GOLD_MIXED** otherwise (right only if brown dwarfs are as rare as the floor population says).
The gold-only BD class is reported as a descriptive result.

## Q2 (primary, powered): does the transit rate rise with significance?

Tiers: T1 < 10, T2 10-20, T3 ≥ 20 (BD + VLMS). The test is a one-sided conditional test of T3
against T1. Under H0, both tiers share ρ0 = max(0, (N − fa1 − fa3)/(E1 + E3)), and given
N = n1 + n3 the T3 count is Binomial(N, μ3/(μ1 + μ3)) with μ = fa + ρ0 E.
- Primary: all hits with E_iso. Pass if p < 0.05.
- Robustness: substellar-size hits with central E_pop.
- Label: **RISES_WITH_SIGNIFICANCE** (both p < 0.05), **RISES_PRIMARY_ONLY**, or **NO_RISE**.

## Q3 (exploratory): other columns

Each column is split at its BD + VLMS median and tested with the same conditional test, one-sided
in the direction fixed here, with Bonferroni α = 0.01 over the five columns:
- `efficiency`: high is better.
- `rv_n_good_obs_primary`: high is better.
- `goodness_of_fit`: low is better.
- `conf_spectro_period`: high is better.
- A = `rv_amplitude_robust`/(2K): low is better (an orbit fitted to noise has a K small for the
  RV scatter it was fitted to).

## Q4 (graded on Gaia DR4 day, 2 December 2026, with dr4_sb1_reality's per-source labels)

f_conf = CONFIRMED / testable (UNTESTABLE excluded), with Wilson 95 % intervals, on the whole S3
pool (all classes). The quality columns come from `qcut_columns.csv`, which is DR3-only and fixed
before DR4.
- Q4a: f_conf(gold) > f_conf(not gold), with Wilson intervals not overlapping.
- Q4b: f_conf(T3) > f_conf(T1), with intervals not overlapping.
- Q4c: rate-sample stars with a transit hit are CONFIRMED more often than those without (one-sided
  Fisher exact, p < 0.05). Descriptive, because the 25 hits include about 8 false alarms.
- Q4d (exploratory): the Q3 columns ranked by how well they separate CONFIRMED from
  DROPPED/CHANGED (AUC, reported, not graded).
The Q4 grading code will be written and committed before 2 December, with these rules unchanged.

## Predictions (written before any run)

- Q1: UNDERPOWERED 70 %, GOLD_PLAUSIBLE 12 %, GOLD_MIXED 6 %, GOLD_FAILS 12 %. The reasoning:
  the pool's K^3 P cap limits K to below 20 km/s at P ≥ 2 d. The four controls have
  σ_K = K/significance of 0.14 km/s (WASP-18, G 9.2), 0.61 (TOI-1712, G 10.3), 0.98
  (TOI-5427, G 12.1) and 1.10 (TOI-2533, G 12.0). Significance 40 therefore needs K ≥ 6 km/s
  even for the brightest stars and K ≥ 25 km/s at G ≈ 12, so few low-mass orbits reach it.
- Q2: RISES_WITH_SIGNIFICANCE 45 %, RISES_PRIMARY_ONLY 15 %, NO_RISE 40 %. The controls show that
  real low-mass orbits sit at significance 7-14, so noise fits and real orbits may share T1-T2.
- Q3: at most one column passes (70 %). The most likely to pass is A (35 %).
- Q4a 85 %, Q4b 80 %, Q4c 70 % pass.

## What the outcomes would mean

- GOLD_FAILS, or NO_RISE combined with DR4 confirming the gold orbits, would mean Gaia's quality
  columns do not pick out real low-mass short-period orbits. Users would need an external check
  (transits, ellipsoidal light curves or RVs) before trusting any of them.
- RISES_WITH_SIGNIFICANCE with GOLD_PLAUSIBLE would give a usable cut, and the paper's 15-20 rule
  could be tested directly with T2/T3.
- UNDERPOWERED is an honest outcome: the gold cut removes almost all of the low-mass orbits, so it
  cannot rescue the class we care about. That fact will be stated in the results.

## Limits

These are population statistics; no single orbit is labelled wrong here. The transit test cannot
tell a wrong period from a right period with a diluted K (blended SB2), and only DR4 (Q4) can.
The Gaia archive is closed from 25 November 12:00 CET to 2 December 12:00 CET. If the job
cannot reach it, it exits 2 and is re-filed unchanged; gaiadr3 tables stay in the archive after DR4.
