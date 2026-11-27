# sb2-ebfit-v2 graded: self-test passes, 9 of 10 predictions hold, BD+15 2743 gets masses, HD 11239's fit fails on timing

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0, code Apache-2.0. Written 27 November 2026 (~03:00 UTC).
Predictions: `findings/2026-11-23-sb2-ebfit-prereg.md` (23 Nov, commit 669307b) and the v2 table in
`findings/2026-11-26-sb2-ebfit-v1-results.md` (filed 26 Nov before v2 ran).
Raw output: `data/sb2-ebfit-v2/ebfit_summary.json`, `ebfit_params.csv`, `ebfit_fold_*.csv`, `run_stdout.txt`.

Job `sb2-ebfit-v2` (`sb2_ebfit.py` 0.1.1 = 0.1.0 at 669307b with the one crashing log line fixed by
`runbook/ebfit-v2/fetch_patch.py`) ran on the Blade on 26-27 Nov 2026, 23:24-00:34 UTC, peak memory 0.23 GB.
Unit tests passed; **built-in self-test: PASS**; controls: 4 of 4 pass (CONTROLS_OK).

## 1. The 23 November predictions, graded on v2

v2 reproduces v1 for all seven v1 stars (largest change: CW Eri radius sum 3.63730 -> 3.63706, 0.007%;
masses agree to 1e-5 relative). The only grade that changes is the self-test, which now passes.

| prediction | probability | result |
|---|---|---|
| self-test PASS | 80% | PASS (held) |
| CONTROLS_OK | 55% | 4/4 (held) |
| R1+R2 within 3 sigma for >= 3 of 4 controls | 75% | 4/4 (held) |
| CD-28 7251 FIT_OK | 60% | FIT_DOUBTFUL (failed) |
| TYC 3616-2395-1 FIT_OK | 80% | FIT_OK (held) |
| HD 250735 FIT_OK | 85% | FIT_OK (held) |
| all three i > 80 deg | 90% | 83.5, 84.9, 86.0 (held) |
| MASS_PRECISION <= 4% for all three | 70% | 3.1%, 2.2%, 2.6% (held) |
| HD 250735 R1+R2 in 2.0-3.0 R_sun | 70% | 1.757 (failed) |
| TYC 3616-2395-1 R1+R2 in 1.9-2.8 R_sun | 70% | 1.604 (failed) |
| CD-28 7251 R1+R2 in 3.0-4.5 R_sun | 65% | 5.67 (failed) |
| CD-28 7251 masses 1.9-2.3 and 1.6-1.95 | 75% | 2.119 and 1.787 (held) |

**8 of 12 held.** Masses and the controls behave; radius sums of the partial-eclipse targets do not.

## 2. The v2 predictions (filed 26 Nov before the run)

| prediction | probability | result |
|---|---|---|
| self-test PASS | 75% | PASS (held) |
| seven v1 stars reproduce v1 masses and R1+R2 within 0.1% | 85% | max change 0.007% (held) |
| BD+15 2743 FIT_OK | 65% | FIT_OK, chi2_red 1.372 (held) |
| BD+15 2743 i > 80 deg | 85% | 82.06 +/- 0.13 (held) |
| BD+15 2743 MASS_PRECISION 4-6% | 75% | 4.9% (held) |
| BD+15 2743 R1+R2 in 1.4-2.2 R_sun | 55% | 1.635 +/- 0.028 (held) |
| HD 11239 FIT_OK (FFI data only) | 50% | FIT_DOUBTFUL, chi2_red 574 (failed) |
| HD 11239 i > 80 deg | 85% | 81.8 +/- 1.9 (held, inside 1 sigma of the limit) |
| HD 11239 MASS_PRECISION <= 2% | 75% | 1.86% (held) |
| HD 11239 R1+R2 in 1.9-2.8 R_sun | 55% | 2.76 +/- 0.24 (held) |

**9 of 10 held.** The three HD 11239 "holds" come from a fit its own label rejects. We report them
as graded, but they carry no weight (see section 4).

## 3. Masses (graded; self-test PASS)

| star | status | i (deg) | masses (M_sun) | note |
|---|---|---|---|---|
| HD 250735 (TIC 400170926) | new EB (ours) | 86.00 +/- 0.02 | **1.115 +/- 0.030 and 1.025 +/- 0.018** | 3 SPOC sectors, chi2_red 1.009 |
| BD+15 2743 (TIC 119613818) | new EB (ours) | 82.06 +/- 0.13 | **0.918 +/- 0.027 and 0.824 +/- 0.040** | 1 SPOC sector, chi2_red 1.372; Gaia component 1 is the lighter star |
| TYC 3616-2395-1 | listed first by Eclipses by Appointment | 84.86 +/- 0.10 | 1.135 +/- 0.025 and 1.059 +/- 0.024 | independent check |
| HD 11239 (TIC 115321276) | new EB (ours) | (81.8 +/- 1.9) | (1.117 and 1.071, not quoted as results) | FIT_DOUBTFUL |
| CD-28 7251 | listed first | (83.5) | (2.12 and 1.79) | FIT_DOUBTFUL, blended |

The masses are almost entirely Gaia DR3's velocity amplitudes; the light curve only supplies sin^3 i.
The mere fact of eclipses bounds i from below: cos i < (R1+R2)/a. With the fitted (R1+R2)/a
(0.0993 for HD 250735, 0.199 for BD+15 2743) that gives i > 84.3 deg and i > 78.5 deg. So even if
the fitted inclination were wrong, anywhere between that bound and 90 deg, the masses would move by
at most +0.8%/-0.7% (HD 250735, fitted i = 86.0) and +3.2%/-2.9% (BD+15 2743, fitted i = 82.1).
For BD+15 2743 the two stars are then 0.89-0.95 and 0.80-0.85 M_sun: a pair of late G / early K
dwarfs on a 2.07-day orbit.

**Not trusted, not quoted:** individual radii, radius ratios and third light of the partial-eclipse
systems. The same local-minimum signature as in v1 appears for BD+15 2743: the check fit with third
light fixed at zero reached a lower chi2 (chi2_red 1.37044) than the free fit (1.37188), and the free
fit's e sin(omega) = -0.142 +/- 0.010 is implausible for a 2.07-day orbit that Gaia fits as circular.
The fitted radii (0.96 R_sun for the 0.82 M_sun star, 0.68 R_sun for the 0.92 M_sun star) are the
wrong way round for main-sequence stars. The radius sum 1.635 R_sun is physically plausible but comes
from the same degenerate fit.

## 4. HD 11239: what went wrong, and a timing clue

HD 11239 has only TESS full-frame-image light curves (TESS-SPOC): sector 3 (2018, 30-min cadence,
831 points) and sector 30 (2020, 10-min, 3307 points). Both eclipses are clearly there: the fold
gives depths of 7.3% and 7.1% at phase separation 0.500 and FWHM 0.090 and 0.081 d, two near-equal
F stars as Gaia's orbit says. But the joint fit has chi2_red = 574 and returns

- P(TESS fit) = 3.119557 +/- 0.000023 d against **P(Gaia) = 3.1208264 +/- 0.000039 d**, 28 sigma apart.

The fitted reference time lies in sector 30 (BTJD 2126.0435). Propagating Gaia's conjunction 1
(BTJD 390.8619, from Gaia time = BTJD + 1802.5) by 556 Gaia periods gives BTJD 2126.0414: **in sector
30 the eclipses fall 0.002 d (3 minutes) from where Gaia's 2014-2017 orbit predicts them**, inside
the ~0.02 d that Gaia's period error allows after 556 orbits. ASAS-3 (2000-2009) also matched Gaia's
period. The fitted period therefore says that in sector 3 the eclipses are about 0.30 d (7 hours)
**late** compared with Gaia's ephemeris (234 orbits x 0.00127 d). The binned fold
(`ebfit_fold_hd-11239.csv`) shows diluted dips at the place this predicts, but the bins mix sectors
and cannot settle it.

No ordinary physics moves one 2018 sector by 7 hours while 2000-2009, 2014-2017 and 2020 agree:
a light-travel-time orbit would need the binary's velocity to change by ~120 km/s. So the candidates
are (a) a local minimum of the joint fit in period (its starts vary e cos(omega), e sin(omega), the
radius sum and k, never P), (b) a timing fault in this sector's light curve, or (c) something real
that we would have to prove. We do **not** claim (c). Eclipses by Appointment has documented TESS clock
faults in other sectors (14-15 and 101-104; its commits 6699c5f and 8f279a3, 26 Nov 2026), so
(b) is not far-fetched, but sector 3 is not among them.

A pre-registered test that measures each sector's eclipse times against Gaia's ephemeris, with two
SPOC-vs-FFI controls, is filed as job `hd11239-timing-v1`
(`findings/2026-11-27-hd11239-timing-prereg.md`). HD 11239's masses wait for it.

## 5. What this means

- Two of our new eclipsing binaries now have absolute masses from Gaia's velocities and TESS's
  inclinations: HD 250735 (1.115 and 1.025 M_sun, 2.6% / 1.7%) and BD+15 2743 (0.918 and 0.824
  M_sun, 2.9% / 4.9%). These are not yet benchmark grade (DEBCat asks for about 2% or better in both
  masses and radii), and the radii need a fit that maps the partial-eclipse degeneracy.
- With Gaia DR4 (2 December 2026) the velocity amplitudes come from 66 months of data; we will rerun
  the same masses with the DR4 orbits and their epoch velocities.
