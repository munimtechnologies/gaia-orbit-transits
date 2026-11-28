# ZTF timing test of two brighter Gaia DR3 SB1 eclipse flags (pre-registration)

MV2, Munim, Inc. (mv2@munimtech.com). Written 2026-11-28 ~10:35 UTC, BEFORE any ZTF data for these
stars were fetched (only their Gaia DR3 orbits, VizieR I/357/tbosb1, were read). CC BY 4.0. Carried out
with AI agents working in MV2's name; no human expert has checked it.

## Why

The same ZTF faint-point timing test confirmed UCAC4 468-115332 and UCAC4 544-021692 as eclipsing
binaries today (findings/2026-11-28-ztf-ephemeris-confirm-graded.md, re-checked in
findings/2026-11-28-ztf-new-ebs-recheck.md). Two other "listed nowhere" flags of the blind Gaia DR3 SB1
search (findings/2026-11-26-g8-dr3-sb1-results.md) are still unconfirmed: TYC 3384-347-1 (Dec +50, north
of ASAS-3) and TYC 1316-1554-1 (ASAS-3 inconclusive, 3 of 6). Their TESS job has waited since 26 Nov.
Risk stated up front: at G 11.5 and 10.6 both are at or above ZTF's bright limit, so saturation may leave
too few good points (then NO_DATA, not a fail).

Lesson applied from the first ZTF test: windows now cover the 3-sigma phase drift from Gaia's period
error over the ZTF years, not 1 sigma.

## Stars (Gaia DR3 SB1; BTJD = BJD - 2457000; conj0 frozen in findings/2026-11-26-sb1-new-ebs-tess-prereg.md)

| star | Gaia DR3 | RA, Dec (deg) | G | P (d) | sigma_P (d) | e | omega (deg) | conj0 (BTJD) |
|---|---|---|---|---|---|---|---|---|
| TYC 3384-347-1 | 968093290740779008 | 96.983203, +49.958672 | 11.47 | 4.0011609 | 0.00020 | 0.035 | 157 | 389.44621 |
| TYC 1316-1554-1 | 3350075697770930304 | 88.149251, +17.688585 | 10.58 | 1.6262843 | 0.000014 | 0.078 | 153 | 389.62038 |

Drift over ZTF 2018-2025 (up to ~880 and ~2,160 cycles from conj0): 0.045 and 0.019 of an orbit at
1 sigma, so 3-sigma windows of +/-0.13 and +/-0.06.

## Data and rule (frozen)

- IRSA ZTF light-curve service, cone 3 arcsec on the Gaia DR3 position; band r (zr) first, zg only if zr
  has fewer than 50 good points. Good point: catflags == 0 and magerr <= 0.03.
- Per oid baseline = median of its good points; faint point = mag >= baseline + 0.05.
- dphi = frac((HJD - 2457000 - conj0) / P) mapped to [-0.5, 0.5).
- Windows: TYC 3384-347-1 |dphi| <= 0.13 (p = 0.26); TYC 1316-1554-1 |dphi| <= 0.06 (p = 0.12).
- Statistic: one-sided binomial P(>= k | n, p), k = faint points in the conj0 window, n = all faint points.
  Also reported by night (distinct integer HJD).
- Null: same width centred at dphi = +0.25 and -0.25; each must hold <= max(2, 2 n p).
- Fewer than 50 good points in both bands: NO_DATA.

## Predictions

- Z3 (50%): TYC 3384-347-1: n >= 5, k >= 4, P < 1e-3, nulls pass.
- Z4 (35%): TYC 1316-1554-1: n >= 5, k >= 4, P < 1e-3, nulls pass.
- Reported, not graded: faint points near dphi = 0.5 +/- 0.13 (secondary eclipse; e is small, so conj1
  sits within ~0.02 of 0.5), and any linear trend of dphi with time (period correction; if one is seen it
  must be frozen and tested on data not used to find it before any claim).

## Decision rule

PASS (with nulls) -> the star is an eclipsing binary confirmed by an independent instrument at Gaia's
predicted time, and joins the unlisted-EB table. FAIL or NO_DATA -> it stays a candidate; no claim.
