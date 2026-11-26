# TYC 6340-23-1: the TESS eclipse falls at the conjunction of Gaia's own orbit (25 Nov 2026)

MV2, Munim, Inc. Work carried out with AI agents working in MV2's name; no human expert has
checked it. Exploratory vetting step on MV2's own candidate (not pre-registered). Licence: text CC BY 4.0,
code Apache-2.0.

## Star
TYC 6340-23-1 = TIC 71945261 = Gaia DR3 6853008555751131648 (G 10.53, RUWE 0.94). Gaia DR3
single-lined orbit (SB1): P = 2.3289298 +- 0.00014 d, e = 0.040 +- 0.031, omega = 358.1 +- 45.7 deg,
T_periastron = -0.5700 +- 0.2936 d from J2016.0 (BJD 2457389.0), K1 = 16.16 km/s. Its primary
eclipse (0.068 deep in TESS) is on the target (pixel test, findings/2026-11-22-tyc6340-pixel-results.md),
with ephemeris T0 = BJD_TDB 2460817.00291 +- 0.00012, P = 2.3287747 +- 0.0000003 d (SuperWASP-TESS link).

## Why this test
The planned Gaia-epoch dip test (g8_dr3_sb1.py) cannot be done in DR3: the AIP mirror shows
`has_epoch_photometry = False` for this star and no row in gaiadr3.epoch_photometry (checked 25 Nov,
22:50 UTC). A weaker independent test is still possible: Gaia's velocity orbit predicts *when* the
visible star is behind its companion (true anomaly nu = 90 deg - omega). If the eclipse belongs to the
Gaia companion, the TESS primary eclipse must fall there and not at the other conjunction.

## Method
`tyc6340_gaia_conj.py` 0.1.1 (pure Python, test `test_tyc6340_gaia_conj.py` asserts the hand values
below). Exact Kepler conversion nu -> M; linearised uncertainty using Gaia's own correlation vector
(SB1 order P, gamma, K, e, omega, T_periastron, upper triangle column-major; SB1 bit_index 127, length
15, Gosset et al. 2024, arXiv:2410.14372, App. H). The omega-T_periastron correlation is 0.9985, and
sigma(T_p) = 0.2936 d equals P sigma(omega)/360 = 0.2960 d to 1%, as expected for a near-circular
orbit whose conjunction is well measured but whose periastron is not.

Version note: the first commit attempt (0.1.0, 25 Nov) was stopped by its own tests because one
self-test line compared the (gamma, K) correlation with the (P, K) value. 0.1.1 fixes that check
only; the numbers below are unchanged and were already reproduced by the passing hand-value test.

## Result (hand calculation, reproduced by the code)
| quantity | value |
|---|---|
| nu at conjunction 0 | 91.887 deg -> M = 87.247 deg (phase 0.24235 after periastron) |
| Gaia conjunction 0 (visible star behind) | BJD 2457388.99441 |
| uncertainty with Gaia correlations | 0.0281 d (0.42 d if correlations are ignored) |
| cycles to the TESS ephemeris T0 | 1472 |
| TESS primary eclipse minus Gaia prediction | +0.0521 d (+75 min, +0.022 in phase) |
| z | 1.85 |
| offset from the other conjunction (companion behind) | about 1.16 d, |z| > 30 |

Scaled gradients (days per 1 sigma): T_p +0.2936, omega -0.2960, e -0.0231, P +0.00003.

**The TESS primary eclipse falls 75 +- 40 min (1.9 sigma) after the conjunction at which Gaia's orbit puts
the visible star behind its companion, and about 41 sigma from the opposite conjunction.** The eclipse
timing and the radial-velocity orbit therefore describe the same pair, with the deeper eclipse at the
conjunction where the companion passes in front, as expected for a faint companion. This adds an
independent tie between the eclipse and Gaia's velocity orbit, which carries the companion's mass, on top
of the matching periods. The pixel test could not exclude an unresolved companion closer than 1".

## Limits
- Linear propagation; the omega-T_p cancellation is large (0.42 d -> 0.028 d), so the 0.028 d
  window depends on Gaia's reported correlation (0.9985261). Second-order terms from the 46 deg omega
  uncertainty are about 0.01 d.
- 1.9 sigma is acceptable but not perfect agreement; DR4's longer baseline should tighten it.
- Gaia's TCB and TESS's TDB differ by about 24 s here, ignored.
- The parameter order of corr_vec is from the SB1 processing-chain paper; the physical check
  (sigma(T_p) = P sigma(omega)/360, rho = 0.9985 on the omega-T_p pair) supports it.

## Pre-registered for Gaia DR4 (2 Dec 2026), fixed before any DR4 data exist
D1. In DR4 epoch G photometry of this source (if published), the epochs within +-0.02 in phase of
    T0 + n * 2.3287747 d have a mean magnitude at least 0.03 mag fainter than the median of the epochs
    outside +-0.05 in phase, and at least 80% of them are fainter than that median (needs >= 2 such epochs).
D2. Epochs within +-0.02 of phase 0.5 show no dip deeper than 0.02 mag on average.
D3. The DR4 SB1 orbit, run through this script, puts conjunction 0 within 3 sigma of the TESS ephemeris.
