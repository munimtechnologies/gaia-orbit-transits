# EBLM holdout check of eblm_fit 0.2.0, graded: PIPELINE_FAILED (6 of 14 pass)

Written 2026-11-20 (about 06:45 UTC) by MV2 of Munim, Inc.; made with AI agents working in his
name, not checked by a human expert. Text and data CC BY 4.0, code Apache-2.0.

Rules: `findings/2026-11-19-eblm-holdout-prereg.md` (written before eblm_fit 0.2.0 existed).
Holdout ids: `findings/2026-11-20-eblm-holdout-resolution.md` and `data/eblm-holdout/holdout_ids.csv`
(committed before the fit). How the fixes were built: `findings/2026-11-19-eblm-fit-020-build.md`.
Raw output of job **gaia-eblm-holdout-fit-v1**: `data/eblm-holdout-fit-v1/` (`holdout_fit_summary.json`,
`holdout_fit_report.md`, `holdout_fit_vets.json`, `eblm_fit_results.csv`, `eblm_fit_summary.json`,
`fit_plots/`, `job_summary.json`).

The job ran on 20 Nov 05:17-05:32 UTC with eblm_fit 0.2.0 and eblm_holdout_fit 0.1.0 pinned at
996ced14d2f4ddd431616b0f2d72d49619bc8095 (release v0.31.0). Its setup step confirmed that
`holdout_ids.csv` on `main` matched its copy. Unit tests passed (step run-01). Exit 0.

## Grade

| Quantity | Value |
|---|---|
| Holdouts fitted | 14 |
| Testable (not UNTESTED, not GRAZING) | 14 |
| Pass (C_NORMAL_COMPANION and r2 within 10% of the published R2) | **6** |
| Pass share | 43% (80% required; 12 of 14 would have been needed) |
| **Label** | **PIPELINE_FAILED** |
| Median radius offset, median(r2/R2 - 1), all 14 (reported, not graded) | **-5.3%** |
| Labels that change if the mass check is dropped | 1 (J1626+57) |

| System | Gaia DR3 | Outcome | r2 (R_sun) | R2 published | Offset | m2/M2 | e used | Pass |
|---|---|---|---|---|---|---|---|---|
| J0011+63 | 431464378685659008 | C_NORMAL_COMPANION | 0.369 | 0.403 | -8.3% | 1.04 | 0.200 | yes |
| J0040+01 | 2549407310330919168 | D_TWIN_AT_2P | 0.497 | 0.138 | +259.7% | 1.34 | 0.077 | no |
| J0316+40 | 239279607384683264 | C_NORMAL_COMPANION | 0.249 | 0.253 | -1.6% | 1.07 | 0 | yes |
| J0507+29 | 156012354863170304 | C_NORMAL_COMPANION | 0.227 | 0.242 | -6.1% | 0.93 | 0.085 | yes |
| J0719+21 | 3364103129676374272 | C_NORMAL_COMPANION | 0.277 | 0.313 | -11.4% | 0.77 | 0 | no |
| J0955+36 | 796597484292515072 | C_NORMAL_COMPANION | 0.276 | 0.325 | -15.0% | 0.93 | 0 | no |
| J1624+34 | 1329183358958814208 | C_NORMAL_COMPANION | 0.231 | 0.237 | -2.7% | 0.91 | 0.368 | yes |
| J1626+57 | 1431358638065021056 | A2_COMPANION_LIGHTER_THAN_GAIA | 0.213 | 0.223 | -4.5% | 0.88 | 0.075 | no |
| J1640+49 | 1412236069274698880 | C_NORMAL_COMPANION | 0.257 | 0.241 | +6.4% | 0.94 | 0 | yes |
| J1741+21 | 4556083135603641856 | D_TWIN_AT_2P | 0.229 | 0.232 | -1.4% | 0.97 | 0 | no |
| J1850+50 | 2144394917977370880 | C_NORMAL_COMPANION | 0.229 | 0.286 | -20.0% | 1.00 | 0.261 | no |
| J2106+02 | 1730371439418183680 | C_NORMAL_COMPANION | 0.196 | 0.222 | -11.7% | 1.04 | 0 | no |
| J2233+43 | 1981814806503811968 | E_NO_ECLIPSE | 0.010 | 0.224 | -95.7% | 0.82 | 0 | no |
| J2315+23 | 2839193907753424384 | C_NORMAL_COMPANION | 0.272 | 0.263 | +3.6% | 0.95 | 0 | yes |

## How the eight failures fail (read from the outputs and plots; not part of the grade)

- **Two false TWIN_AT_2P labels.** J0040+01 is a grazing eclipse (fitted impact parameter
  b = 0.986, k = 0.257). The radius came out 2.6 times too large and the odd/even depths differ
  (0.934 vs 1.135), so the twin test fired before the grazing test could. J1741+21 has the right
  radius (-1.4%) but its odd and even depths differ (1.104 ± 0.011 vs 0.923 ± 0.010) over five
  sectors spanning four years (2020-2024). The odd/even test treats sector-to-sector systematics as a real
  difference.
- **One missed eclipse.** J2233+43 (TIC 200373531) shows a strong starspot or systematics signal
  with a jump between sectors (`fit_plots/fit_1981814806503811968.png`). The fitted eclipse sits at
  the wrong phase (fit S/N 5.5 against a BLS S/N of 563), so the label is E_NO_ECLIPSE.
- **One mass-check failure.** J1626+57's companion came out 12% lighter than published
  (m2/M2 = 0.88) and the ellipsoidal amplitude was negative (-220 ± 84 ppm), so the mass
  check flagged it. Its radius is fine (-4.5%). Fix (a), red noise in the error bar, did not
  make this check safe.
- **Four radius misses, all too small** (J0719+21 -11%, J0955+36 -15%, J1850+50 -20%,
  J2106+02 -12%). For J1850+50, Gaia's eccentricity (0.26) is far from the published value
  (0.107). eblm_fit 0.2.0 uses Gaia's e when it is significant, which shrinks the radius scale.

Exploratory, not graded: the circular fits (e used = 0, excluding the missed eclipse; 7
systems) have a median offset of -1.6%. The fits that used Gaia's eccentricity (excluding the
grazing J0040+01; 5 systems) have a median of -6.1%, and all five offsets are negative. This
pattern was seen after the grade and needs its own test before anyone relies on it.

## Predictions (written before the fit)

- PIPELINE_VALIDATED 50%, PIPELINE_FAILED 35%, INCONCLUSIVE 15%: **the less likely FAILED happened.**
- Median radius offset within ±5% (75%): **failed narrowly** (-5.3%).
- "The eccentric systems are the most likely to fail if fix (b) is wrong": J1624+34 (e = 0.37)
  **passed** (-2.7%; fitted occultation phase 0.641 against the predicted 0.636). Fix (b) worked
  there. The eccentric system that failed, J1850+50, failed on the radius, not the phase.

## Consequences, as fixed in the pre-registration

- **No EBLM result from this pipeline will be published from Gaia DR4.** The DR4 release-day
  step 5 (EBLM inflation) is cancelled.
- **The M-dwarf inflation note keeps its caveat.** The median offset is outside ±3%, so it gets
  a public addendum: `findings/2026-11-20-eblm-inflation-addendum.md`.
- **BD+65 286's label stays not adopted.** The planned 0.2.0 refits of BD+65 286 and of
  TIC 71945261 were conditional on PIPELINE_VALIDATED and will not be run.

## What this means for TYC 6340-23-1 (TIC 71945261)

Its label B_OVERSIZED_COMPANION came from eblm_fit 0.1.0. For circular orbits, 0.1.0 and 0.2.0
use the same formulas (`findings/2026-11-19-eblm-fit-020-build.md`). The holdout shows two ways
the pipeline gets a companion radius badly wrong:
- **Grazing eclipses inflate the radius.** The one large overestimate (J0040+01, +260%) had
  b = 0.986. TYC 6340-23-1's fit has b = 0.67, and its light-curve stellar radius agrees with
  Gaia's FLAME radius to 0.7% (0.921 vs 0.927 R_sun). Its earlier fit note gives a floor of about
  0.20 R_sun even for a central eclipse, still 1.7 times the main-sequence value.
- **Every other miss is too small, not too large.** No non-grazing holdout came out more than
  6.4% too large.

So the holdout shows no failure mode that would make a normal 0.12 R_sun companion look like a
0.22 R_sun one in a non-grazing fit. But the pipeline as a whole is not validated, so this
system's radius must be confirmed independently, by a second TESS sector or a refit by
another team, before anyone relies on it. The two open questions about it are unchanged: Gaia's
K (mass) and youth outside known groups. A Gaia DR4 test of K using only epochs after DR3's
data window is pre-registered in `findings/2026-11-20-tyc6340-dr4-k-prereg.md`.

## Limits

14 holdouts, all at P = 5.6-10.6 d with F/G/K primaries. The answer key (EBLM XIX Table 4) was
known to us before the fit. The fixes were written down before the holdouts were resolved, so
that knowledge could not shape them. The failure analysis above was done after the grade.
