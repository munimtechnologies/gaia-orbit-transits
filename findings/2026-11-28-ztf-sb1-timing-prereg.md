# ZTF timing test of two faint Gaia DR3 SB1 eclipse candidates (pre-registration)

MV2, Munim, Inc. (mv2@munimtech.com). Written 2026-11-28 ~07:05 UTC, before any ZTF data for
these stars were fetched. CC BY 4.0. Carried out with AI agents working in MV2's name; no human
expert has checked it.

## Why

Two of the five "listed nowhere" flags of the blind Gaia DR3 single-lined conjunction search
(findings/2026-11-26-g8-dr3-sb1-results.md) are too faint for ASAS-3 and wait for a TESS job that
compute has not started (sb1-new-ebs-tess-v1, queued since 26 Nov). ZTF (1-arcsec pixels, 2018-2025)
covers both, and at G ~ 12.2 its point errors (~0.01-0.02 mag) are 5-10x smaller than the >= 0.10 mag
Gaia dips that flagged them. Power check (lesson of 28 Nov): depth / point error >= 5, so a
faint-point timing test has power here, unless ZTF saturates (G 12.2 is near ZTF's bright limit).

## Stars (Gaia DR3 SB1 orbits; BTJD = BJD - 2457000; Gaia DR3 Tp in BTJD = 389.0 + t_periastron)

| star | Gaia DR3 | RA, Dec (deg) | G | P (d) | sigma_P (d) | e | omega (deg) | conj0 (BTJD) | conj1 - conj0 (phase) |
|---|---|---|---|---|---|---|---|---|---|
| UCAC4 544-021692 | 3350386649103238016 | 90.580834, +18.618103 | 12.20 | 7.2472787 | 0.0011152 | 0.0305 | 267.85 | 392.28328 | 0.4993 |
| UCAC4 468-115332 | 4289848214689460736 | 296.130889, +3.403195 | 12.12 | 5.3592781 | 0.0005246 | 0.4105 | 36.99 | 393.11624 | 0.7112 |
| control: Gaia DR3 1993895376986150272 | 1993895376986150272 | 359.572555, +55.308789 | 12.46 | 2.8802867 | 0.0001997 | 0.0862 | 358.09 | 388.24405 | 0.5547 |

conj0 = visible star behind its companion (true anomaly nu = 90 deg - omega), the repo's conj_map
convention; conj0 for the two candidates equals the frozen values in
findings/2026-11-26-sb1-new-ebs-tess-prereg.md (re-derived by hand here: 392.2833 and 393.1162).
conj1 (nu = 270 deg - omega) and the control's conj0 are derived by hand from Kepler's equation in
this note. Phase drift from sigma_P over the ZTF years (~110-460 cycles): up to 0.07 (UCAC4
544-021692), 0.06 (UCAC4 468-115332), 0.08 (control, ~1,150 cycles) at 1 sigma.

The control is listed by IJspeert et al. (2024) as an OBAF eclipsing-binary candidate (score 1) with
Gaia's period, so it is not new; it checks that ZTF times and Gaia conjunctions line up.

## Data and rule (frozen)

- Source: IRSA ZTF light-curve service (latest public data release), cone radius 1.5 arcsec on the
  Gaia DR3 position, band r (zr) first; zg only if zr has fewer than 50 good points.
- Good point: catflags == 0 and magerr <= 0.03.
- Per object id (oid), baseline = median mag of its good points. Faint point: mag >= baseline + 0.05.
- Phase of a point: dphi = frac((HJD - 2457000 - conj0) / P), mapped to [-0.5, 0.5).
- Windows: UCAC4 544-021692 |dphi| <= 0.12 (fraction p = 0.24), wide because of the 0.07 drift;
  UCAC4 468-115332 |dphi| <= 0.08 (p = 0.16); control |dphi| <= 0.12 (p = 0.24).
- Statistic: k faint points in the conj0 window out of n faint points; one-sided binomial
  P(>= k | n, p).
- Null: the same counts in windows of the same width centred at dphi = +0.25 and -0.25 (reported).

## Predictions (graded in this run if the data arrive)

- Z1 (60%): UCAC4 544-021692 has n >= 5 faint good points, k >= 4 and P < 1e-3.
- Z2 (60%): UCAC4 468-115332 has n >= 5 faint good points, k >= 4 and P < 1e-3.
- C1 (70%): the control has n >= 5, k >= 4 and P < 1e-3.
- N1 (80%): for every star with n >= 5, each quarter-phase null window holds at most
  max(2, 2 x n x p) faint points.
- If a star has fewer than 50 good points in both bands, it is NO_DATA (not a fail).
- Reported, not graded: faint points in the conj1 window (secondary eclipse), and any trend of
  dphi with time (a period correction).

## Decision rule

Z1 or Z2 PASS with N1 PASS for that star -> the star is an eclipsing binary confirmed by an
independent instrument at the time Gaia's orbit predicts; it moves to the unlisted-EB table and its
TESS check stays queued for depth and shape. FAIL -> stays a candidate; no claim.
C1 FAIL with a candidate PASS -> report both; the candidate pass still stands on its own null.
