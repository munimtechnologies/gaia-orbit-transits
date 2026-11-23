# Pre-registration: masses and radii of three new Gaia double-lined eclipsing binaries

MV2, Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.
Written 2026-11-23 (~17:30 UTC) before job **sb2-ebfit-v1** ran. Code `sb2_ebfit.py` 0.1.0 with
tests `test_sb2_ebfit.py`; inputs `runbook/ebfit/targets.json` (this commit). No light curve of
any star below has been fitted by us before this file was written.

## Why

The edge-on SB2 screen (`findings/2026-11-23-sb2-screen-results.md`) left three bright Gaia DR3
double-lined binaries that eclipse in TESS and are in no catalogue we reached: **CD-28 7251**
(TIC 189269584, A3m, G 8.86), **TYC 3616-2395-1** (TIC 384284045, G 10.47) and **HD 250735**
(TIC 400170926, G 9.33). Gaia's orbits give M sin³i for both stars; eclipses give the inclination
and the stars' radii relative to the orbit. Together they give absolute masses and radii, which
is what makes an eclipsing binary a benchmark for stellar models. Method prior art: Rowan et al.
(2023, MNRAS; arXiv:2212.02509) combined 128 Gaia DR3 SB2 orbits with ASAS-SN eclipse fits for
122 stars (median 7.9% in mass, 6.3% in radius). We use TESS instead, and our three systems are
not ASAS-SN eclipsing binaries, so they are not in that work.

## What the job does

`sb2_ebfit.py` 0.1.0, for each star:

1. TESS light curves with lightkurve, **one product for all sectors** (SPOC 120 s if any exists,
   else TESS-SPOC, else QLP), at most 10 sectors spread over the baseline, so that a single
   third-light value is meaningful.
2. Period and eclipse phase by a fold search limited to Gaia's period ± max(10σ, 3×10⁻⁴ P).
3. Windows of ± 2.2 FWHM around every covered eclipse (at most 60 per eclipse family), each with
   its own linear baseline solved inside the fit.
4. Model: two spheres, quadratic limb darkening fixed from an approximate TESS-band table by T_eff
   (u₁ ± 0.1 propagated as a systematic), eccentric orbit, third light, exposure smearing for
   full-frame products. Free: T0, P, e cos ω, e sin ω, cos i, (R1+R2)/a, k = R2/R1, surface
   brightness ratio J, third light l3. Least squares from 5-10 starts.
5. Errors: formal (Jacobian × reduced χ²) **plus** a jackknife over 8 groups of eclipse windows
   (red noise) **plus** the limb-darkening systematic. A fit with l3 fixed at 0 is reported as a
   check, not used.
6. Masses and radii by Monte Carlo over that covariance and Gaia's K1, K2 errors:
   a = √(1−e²)(K1+K2)P / (2π sin i), M_tot = 4π²a³/(GP²), M_1 = M_tot K2/(K1+K2).
7. Which Gaia component is the star eclipsed at the deeper eclipse: by ω (MAP_OMEGA) when both
   Gaia's and our eccentricity are ≥ 5σ, otherwise assumed to be the brighter star in TESS
   (MAP_ASSUMED_BRIGHTER; individual radii are then conditional on that, masses and R1+R2 are not).
8. A self-test runs first inside the job (occultation against the analytic uniform-disk overlap;
   full pipeline on a synthetic eclipsing binary with known parameters); its result is recorded.

Gaia's orbit values are in the config (read from ESA TAP on 23 Nov), so the job does not need
ESA's archive, which closes on 25 Nov.

## Controls, chosen before any fit

The four stars of the same screen that VSX lists as eclipsing and that have a TESS-based analysis
of DEBCat quality published 2023-2026 that we could find: **ZZ Boo** (Southworth 2023), **CW Eri**
(Overall & Southworth 2024), **EY Cep** (Southworth 2026, arXiv:2607.10701; e = 0.44) and **BK Peg**
(Kutluay & Southworth 2026, arXiv:2603.20872). DEBCat's own site was unreachable on 23 Nov, so
other screen stars may qualify; we did not choose among candidates by their Gaia numbers.

**Per control: CONTROL_PASS** if both masses (sorted by mass) and R1+R2 agree with the literature
within |z| ≤ 3 (our total error and the literature error combined). Individual radii are reported
(exploratory). **CONTROLS_OK** if at least 3 of 4 pass.

Not blind, said now: Gaia's M sin³i for the controls is already in our screen table, and for an
eclipsing system sin³i ≈ 1, so the mass half of the control test is mostly a test of Gaia's K1 and
K2 against the literature radial velocities. From those numbers we expect CW Eri's mass ratio
(Gaia 0.867 against 0.838 published) and ZZ Boo's lighter star (Gaia about 1.58 against 1.558 ±
0.008) to be the hardest. The radius sum is the real test of our light-curve fitting.

## Labels per star

- **FIT_OK**: converged, no free parameter at a bound, reduced χ² < 5; else FIT_DOUBTFUL.
- MASS_PRECISION (larger fractional mass error) and RSUM_PRECISION (fractional error of R1+R2).
- Period against Gaia's (z), e cos ω against Gaia's mapped e cos ω (z; only informative under
  MAP_ASSUMED_BRIGHTER, since MAP_OMEGA uses ω itself).

## Predictions (fixed now)

| what | prediction | probability |
|---|---|---|
| self-test | PASS | 80% |
| controls | CONTROLS_OK | 55% |
| controls | R1+R2 within \|z\| ≤ 3 for at least 3 of 4 | 75% |
| CD-28 7251 | FIT_OK | 60% |
| TYC 3616-2395-1 | FIT_OK | 80% |
| HD 250735 | FIT_OK | 85% |
| all three targets | inclination > 80° | 90% |
| all three targets | MASS_PRECISION ≤ 4% (Gaia's K errors set this) | 70% |
| HD 250735 | R1+R2 between 2.0 and 3.0 R_sun | 70% |
| TYC 3616-2395-1 | R1+R2 between 1.9 and 2.8 R_sun | 70% |
| CD-28 7251 | R1+R2 between 3.0 and 4.5 R_sun | 65% |
| CD-28 7251 | heavier star 1.9-2.3 M_sun, lighter 1.6-1.95 M_sun | 75% |

## What follows

- CONTROLS_OK and FIT_OK: the three systems get published masses and radii with these errors as
  new double-lined eclipsing binaries with Gaia orbits, and the write-up on munimtech.com is
  updated. They go to AAVSO VSX once MV2 has an account.
- CONTROLS_FAIL on masses only: Gaia DR3's K amplitudes are biased for these stars at the level
  seen; we report the size of the bias and quote target masses with it as a systematic.
- CONTROLS_FAIL on R1+R2: the fitting is not trusted; we find the cause before quoting radii.
- Gaia DR4 (2 Dec) publishes better orbits; the same code re-runs on them.

## Limits

Spheres, not tidally distorted stars, and no reflection or gravity darkening: fine for these
detached systems at the precision TESS gives, but not at 0.1%. Limb darkening comes from an
approximate table. Partial eclipses of similar stars leave k and l3 poorly constrained; R1+R2 and
the masses are robust to that, individual radii are not. CD-28 7251 shares TESS pixels with a
brighter, variable star 46″ away; SPOC's crowding correction and the free third light handle
dilution, not variability. The code was written without being run by us; the unit tests and the
self-test run first inside the job.
