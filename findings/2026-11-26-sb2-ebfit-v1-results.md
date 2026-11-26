# sb2-ebfit-v1: four literature controls pass, the self-test crashed, partial-eclipse radii are not trusted

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0, code Apache-2.0. Written 26 November 2026 (~23:00 UTC). Pre-registration:
`findings/2026-11-23-sb2-ebfit-prereg.md` (commit 669307b, 23 Nov). Raw output:
`data/sb2-ebfit-v1/ebfit_summary.json`, `ebfit_params.csv`, `ebfit_fold_*.csv`.

Job `sb2-ebfit-v1` (`sb2_ebfit.py` 0.1.0) ran on 26 Nov 16:05-17:21 UTC on TESS SPOC 120-s light
curves of four literature controls and three Gaia DR3 double-lined eclipsing binaries.

## Status: not graded (the job's own gate)

The built-in self-test **crashed**: `TypeError('Object of type bool is not JSON serializable')` in
the log line that prints the synthetic-binary checks (numpy booleans passed to `json.dumps`). The
job records this as `self_test: ERROR` and its own rule is "no grading unless PASS". What the log
shows before the crash: the uniform-disk occultation check passed (max error 1.1e-5), and the fit to
the synthetic binary returned P 4.19999997 (true 4.2), e cos ω 0.03000 (0.03), cos i 0.05992 (0.06),
(R1+R2)/a 0.19995 (0.20), k 0.897 (0.9), J 0.7997 (0.8), l3 0.0999 (0.1). The mapping and mass
checks of the self-test were never evaluated. So the registered self-test prediction (PASS, 80%)
**failed**, through a code bug rather than a bad fit, and the numbers below are provisional until
`sb2-ebfit-v2` (same code with that one line fixed) passes its self-test.

## Controls (literature: Southworth 2023; Overall & Southworth 2024; Southworth 2026; Kutluay & Southworth 2026)

| control | fit label (χ²ᵣ) | masses, ours (M_sun) | masses, literature | R1+R2 ours / lit. (R_sun) | z (heavier, lighter, R-sum) | |
|---|---|---|---|---|---|---|
| ZZ Boo | FIT_DOUBTFUL (78.6) | 1.618 ± 0.005, 1.584 ± 0.005 | 1.599, 1.558 | 4.288 ± 0.026 / 4.268 | 1.45, 2.79, 0.73 | PASS |
| CW Eri | FIT_OK (3.18) | 1.568 ± 0.015, 1.359 ± 0.014 | 1.568, 1.314 | 3.637 ± 0.034 / 3.586 | 0.00, 2.64, 1.45 | PASS |
| EY Cep | FIT_DOUBTFUL (5.98) | 1.460 ± 0.041, 1.431 ± 0.042 | 1.523, 1.494 | 2.909 ± 0.029 / 2.937 | -1.50, -1.43, -0.95 | PASS |
| BK Peg | FIT_OK (0.81) | 1.504 ± 0.105, 1.336 ± 0.189 | 1.411, 1.254 | 3.534 ± 0.126 / 3.450 | 0.88, 0.44, 0.66 | PASS |

All four pass (CONTROLS_OK). Radius sums agree with the literature to 0.5-2.4%. Masses differ by
0-4% for ZZ Boo, CW Eri and EY Cep (this mostly tests Gaia DR3's K1, K2) and by 6.6% for BK Peg,
whose Gaia K2 error is 5.9 km/s. Individual radii: z up to 9 for BK Peg and 5.6 for ZZ Boo
(exploratory, as registered).

## Targets

| star | label (χ²ᵣ) | i (deg) | masses (M_sun) | R1+R2 (R_sun) | k = R2/R1 | third light | individual radii |
|---|---|---|---|---|---|---|---|
| HD 250735 (3 sectors, 22 eclipse windows) | FIT_OK (1.009) | 86.00 ± 0.02 | **1.115 ± 0.030 and 1.025 ± 0.018** | 1.757 ± 0.016 | 2.22 ± 0.09 | 0.119 ± 0.022 | 0.55 and 1.21 |
| TYC 3616-2395-1 (1 sector, 13) | FIT_OK (1.030) | 84.86 ± 0.10 | 1.059 ± 0.024 and 1.135 ± 0.025 | 1.604 ± 0.022 | 0.37 ± 0.04 | 0.375 ± 0.032 | 1.17 and 0.43 |
| CD-28 7251 (1 sector, 6) | FIT_DOUBTFUL (18.4) | 83.48 ± 0.28 | 2.119 ± 0.053 and 1.787 ± 0.055 | 5.67 ± 0.09 | 0.87 ± 0.17 | -0.11 ± 0.09 | 3.03 and 2.63 |

Masses are robust: at i = 84-86° sin³i = 0.988-0.993, so an inclination error of a few degrees moves
them by about 1%. **The radii of the two partial-eclipse systems are not physical**: a star of 1.0-1.1
solar masses cannot have a radius of 0.43-0.55 solar radii, and both radius sums (1.60 and 1.76 R_sun)
are well below what two such main-sequence stars need. Two diagnostics agree that these fits are
degenerate: k and third light are strongly correlated in partial eclipses of similar stars (as the
pre-registration warned), and for both stars the check fit with third light fixed at zero reached a
**lower** χ² than the fit with third light free (χ²ᵣ 1.00662 against 1.00888 for HD 250735, 1.02874
against 1.02990 for TYC 3616-2395-1), so the free fit stopped in a local minimum. CD-28 7251 shares
TESS pixels with a brighter variable star and its fit gives negative third light; we do not use it.

## Predictions as they would grade (not graded, see above)

| prediction | probability | result |
|---|---|---|
| self-test PASS | 80% | ERROR (failed) |
| CONTROLS_OK | 55% | 4/4 pass (held) |
| R1+R2 |z| ≤ 3 for ≥ 3 of 4 controls | 75% | 4/4 (held) |
| CD-28 7251 FIT_OK | 60% | FIT_DOUBTFUL (failed) |
| TYC 3616-2395-1 FIT_OK | 80% | FIT_OK (held; local-minimum caveat) |
| HD 250735 FIT_OK | 85% | FIT_OK (held; local-minimum caveat) |
| all three i > 80° | 90% | 83.5, 84.9, 86.0 (held) |
| MASS_PRECISION ≤ 4% for all three | 70% | 3.1%, 2.2%, 2.6% (held) |
| HD 250735 R1+R2 in 2.0-3.0 | 70% | 1.757 (failed) |
| TYC 3616-2395-1 R1+R2 in 1.9-2.8 | 70% | 1.604 (failed) |
| CD-28 7251 R1+R2 in 3.0-4.5 | 65% | 5.67 (failed) |
| CD-28 7251 masses 1.9-2.3 and 1.6-1.95 | 75% | 2.119 and 1.787 (held) |

7 of 12 would hold. The pattern is clear: masses and well-defined deep eclipses (the controls) work;
the radii of grazing and partial eclipses do not, at least with this least-squares fit.

## sb2-ebfit-v2 (filed 26 Nov 2026, before it ran)

Same code (`fetch_patch.py` downloads `sb2_ebfit.py` and its tests at commit 669307b and changes
only the crashing log line and the version string to 0.1.1), same seven stars, plus two added
targets fitted by us for the first time: **BD+15 2743** (Gaia SB2C, P 2.06722 d, K 106.06 ± 0.88 and
95.12 ± 2.37 km/s; M sin³i 0.82 and 0.92 M_sun by hand) and **HD 11239** (Gaia SB2, P 3.12083 d,
K 91.96 ± 0.46 and 95.92 ± 0.46 km/s; M sin³i 1.09 and 1.05 M_sun by hand). Their orbit values come
from the AIP Gaia TAP mirror, 26 Nov. For the seven old stars the result is expected to repeat v1
(the fit is deterministic), so v2 is not blind for them; it grades the 23 Nov predictions only
because its self-test will have run. Predictions for v2, fixed now:

| prediction | probability |
|---|---|
| self-test PASS | 75% |
| the seven v1 stars reproduce v1's masses and R1+R2 to within 0.1% | 85% |
| BD+15 2743 FIT_OK | 65% |
| BD+15 2743 i > 80° | 85% |
| BD+15 2743 MASS_PRECISION between 4% and 6% (Gaia K2 error 2.5%) | 75% |
| BD+15 2743 R1+R2 between 1.4 and 2.2 R_sun | 55% |
| HD 11239 FIT_OK (FFI data only) | 50% |
| HD 11239 i > 80° | 85% |
| HD 11239 MASS_PRECISION ≤ 2% | 75% |
| HD 11239 R1+R2 between 1.9 and 2.8 R_sun | 55% |

Only masses will be quoted as results for partial-eclipse systems; radii need a fit that maps the
k-third-light degeneracy (a grid or MCMC), which is the next code change, after v2.
