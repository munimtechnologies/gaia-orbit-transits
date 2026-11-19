# Short-period M-dwarf inflation, full Gaia DR3 sample: graded

2026-11-19. MV2 of Munim, Inc.; made with AI agents working in his name, not yet checked by a
human expert. Text CC BY 4.0, code Apache-2.0.

This note grades the confirmatory test pre-registered in section 5 of
`findings/2026-11-18-eblm-fit-results.md` (H1-full, H2-full), using the rules of
`findings/2026-11-17-short-period-inflation-prereg.md` unchanged. The job and inputs are as
filed in `findings/2026-11-19-eblm-rest-results.md` section 4.

## 1. What ran

Job **gaia-eblm-infl-full-v1** (Tango, 19 Nov 11:23-11:27 UTC, exit 0 on all four steps):
1. `combine_eblm_full.py` 0.1.0 joined v1 (70 rows, commit 179d6e4), rest-a (49) and rest-b
   (48) into 167 rows. No duplicate source_id, no system missing, identical headers.
   Input SHA-256s and the combined file's SHA-256 (dacf9c86...) are in
   `data/eblm-infl-full-v1/combine_info.json`. The combined table is
   `data/eblm-fit-full/eblm_fit_results.csv`, where section 5 said it would be.
2. `eblm_infl.py` 0.1.0, pinned at 87f190f and unchanged, graded it against BHAC15
   (Baraffe et al. 2015) isochrones. Both unit-test steps passed first.

Outputs, unchanged: `data/eblm-infl-full-v1/` (`infl_summary.json`, `infl_report.md`,
`infl_table.csv`, `infl_vs_period.png`, `combine_info.json`).

Cuts (pre-registered): 167 rows → 62 clean EBLM fits → **28 in the main set**. Removed: 105
without a clean verdict (grazing, twins at 2P, mass tension, no eclipse, no TESS data and so
on), 3 with fit S/N < 30, 20 without a FLAME primary mass, 1 with b ≥ 0.8, 10 with m2 outside
0.08-0.6 M☉.

The main set: orbital periods 0.89-3.52 d, companion masses 0.24-0.60 M☉, primaries
5,920-9,170 K (15 of 28 are hotter than 7,000 K).

## 2. The grade

| test | rule | result | label | our prior |
|---|---|---|---|---|
| **H1-full** | median of R2/R_BHAC15(5 Gyr) − 1, R2 = k·R1(FLAME); INFLATED if the 95% lower bound > 3% | **+6.3%** (95% CI +1.0% to +8.8%), n = 28 | **INCONCLUSIVE** | INCONCLUSIVE 50% |
| **H2-full** | one-sided Spearman permutation test, inflation falls with period, PERIOD_TREND if p < 0.05 | ρ = **+0.49**, p(one-sided) = 0.996, n = 28 | **NO_TREND_DETECTED** | PERIOD_TREND 10% |

- **H1-full is INCONCLUSIVE.** The interval excludes zero but does not clear the
  pre-registered 3% bar, so we do not call these stars inflated. The interval contains
  Swayne et al. (2024)'s ~6% for P < 5 d (the report's `contains_swayne_6pct: true`).
- **H2-full: no sign that shorter orbits inflate more.** The rank correlation has the opposite
  sign: in this sample, systems with *longer* periods (up to 3.5 d) sit higher.
- **A prediction failed.** Section 5 said the heavier companions in the 97 new fits would
  pull the median down. It went up, from +2.2% (14 systems, v1) to +6.3% (28).

### Robustness (pre-registered variants, all from `infl_summary.json`)

| set / estimator | n | median | 95% CI | label |
|---|---|---|---|---|
| main, FLAME R1, 1 Gyr | 28 | +8.1% | +3.1% to +10.7% | INFLATED |
| **main, FLAME R1, 5 Gyr (primary)** | 28 | **+6.3%** | +1.0% to +8.8% | INCONCLUSIVE |
| main, FLAME R1, 10 Gyr | 28 | +5.0% | −0.2% to +7.7% | INCONCLUSIVE |
| main, light-curve R1, 1 Gyr | 28 | +6.6% | +3.9% to +8.9% | INFLATED |
| main, light-curve R1, 5 Gyr | 28 | +5.0% | +2.3% to +7.1% | INCONCLUSIVE |
| main, light-curve R1, 10 Gyr | 28 | +3.6% | +1.3% to +5.4% | INCONCLUSIVE |
| all clean, light-curve R1, 5 Gyr | 62 | +5.1% | +2.3% to +7.9% | INCONCLUSIVE |
| all clean, FLAME R1, 5 Gyr | 43 | +2.1% | +0.5% to +5.5% | INCONCLUSIVE |

The table shows 8 of the 12 variants in `infl_summary.json`; the other four are all-clean
sets. All 12 medians are positive, and 10 of the 12 intervals exclude zero (the two that do
not are 10 Gyr variants). Only variants at the youngest assumed age (1 Gyr) clear the 3% bar,
three of the four. The answer hangs on the age assumed for the
M dwarfs: older models predict larger radii.

### Period bins (main set)

| period | n | median | 95% CI |
|---|---|---|---|
| 0-1 d | 2 | −12.6% | −13.6% to −11.5% |
| 1-2 d | 18 | +3.8% | +0.8% to +8.2% |
| 2-5 d | 8 | +9.8% | +7.0% to +24.8% |
| ≥ 5 d | 0 | - | - |

The two systems below 1 d (Gaia DR3 6750919828825203328 and 1984784862290035072) have
a/R1 ≈ 2.3-2.5. For the first, run 39 noted 3-4% ellipsoidal variation and a near-contact
shape, so its value depends on the spherical-star model.

## 3. Exploratory checks (computed by hand after the grade; not pre-registered)

- **Recomputed from `infl_table.csv`:** the main-set median (+6.27%) and Spearman ρ (0.4855)
  both reproduce exactly.
- **Without the two sub-1-day systems**, ρ(inflation, period) = +0.36 (n = 26). The positive
  sign does not come from them alone.
- **Companion mass as a confounder:** ρ(inflation, m2) = +0.38 and ρ(m2, P) = +0.24 (both
  from the job). A first-order partial correlation of inflation on period given m2 is about
  +0.44, so mass does not explain the period trend.
- **FLAME vs light-curve primary radius:** three of the four largest FLAME-based values (+23%
  to +28%) belong to systems whose light-curve R1 is 10-15% smaller than FLAME's
  (R1,lc/R1,FLAME = 0.85-0.90). With the light-curve R1 they fall to +6% to +15%. The fourth,
  Gaia DR3 5851944656586312448 (an EBLM_LARGE_RADIUS verdict), grows to +38%. Errors in the
  primary radius are a real part of the spread.

## 4. How this sits against the literature

| study | systems | periods | inflation vs models |
|---|---|---|---|
| Swayne et al. 2024 (EBLM XI, MNRAS 528, 5703) | 23 (CHEOPS) | short and long | ~6% for P < 5 d; ≤ 3% for longer periods |
| EBLM XIX (arXiv:2610.18338) | 50 high-quality of 66 | P > 5 d | 0.3 ± 1.6% (no inflation) |
| von Boetticher et al. 2019 | EBLM | mixed | no relation with orbital period |
| **this work** (Gaia DR3 SB1 + TESS) | **28** | **0.89-3.52 d** | **+6.3% (+1.0 to +8.8%), INCONCLUSIVE at the 3% bar** |

Our short-period sample is about 6% above BHAC15 at 5 Gyr. That matches Swayne et al.'s
short-period number and sits well above EBLM XIX's long-period null. This is a cross-study
comparison with different models, primaries and methods, so it is a pointer, not a test.
Inside 0.9-3.5 d we see no sign that inflation keeps growing as orbits shrink, which is what
simple tidal-spin-up pictures predict. All these M dwarfs should already be tidally
synchronised and rotating fast, so a flat or saturated response inside 5 d is not
surprising.

## 5. Limits

- **The masses are Gaia's.** m2 comes from the Gaia DR3 SB1 K and a FLAME primary mass.
  Fitzpatrick et al. (2025) report K biases for hot primaries, and most of our primaries are
  F and early-A stars (hotter than EBLM's solar-type primaries).
- **Ages are assumed** (5 Gyr primary; 1 and 10 Gyr variants). With hot primaries, many
  systems are probably younger than 5 Gyr, which would raise the inflation values.
- **Metallicity is not modelled.**
- **Irradiation:** hot primaries heat their companions far more than solar-type ones do. Any
  inflation here may not have the same cause as in EBLM systems.
- **Selection:** grazing systems, twins and mass-tension systems were removed by the
  pre-registered cuts; 28 of 167 survive.
- **No human expert has checked this yet.** The work was carried out with AI agents.

## 6. What happens next

- Nothing further is claimed from DR3. Since H1-full is not INFLATED, section 5's systematics
  budget and expert-check email are not triggered.
- Gaia DR4 (2 December 2026) publishes far more spectroscopic orbits and eclipsing binaries.
  The same pipeline, run on DR4 with these rules, is the way to a sample big enough to clear
  or rule out the 3% bar. It is step (e) in `runbook/dr4-release-day.md`.
