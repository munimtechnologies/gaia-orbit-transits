# Out-of-sample test of two ZTF-derived eclipse ephemerides (pre-registration)

MV2, Munim, Inc. (mv2@munimtech.com). Written 2026-11-28 ~07:50 UTC, after the ZTF test of
findings/2026-11-28-ztf-sb1-timing-prereg.md was graded (findings/2026-11-28-ztf-sb1-timing-graded.md)
and BEFORE any ZTF g-band data of UCAC4 544-021692 or any ASAS-3 data of either star were fetched.
CC BY 4.0. Carried out with AI agents working in MV2's name; no human expert has checked it.

## Why

The first ZTF test failed as registered, but post hoc the faint ZTF points of both stars lie on one
straight-line ephemeris through Gaia's conjunctions, with periods that differ from Gaia DR3's by
1.5-2.0 sigma. Ephemerides found after looking at data must be tested on data they were not fitted
to. This test uses (a) ZTF g-band exposures of UCAC4 544-021692 (separate exposures from the r-band
points used in the fit) and (b) ASAS-3 V-band photometry from 2000-2009, 9-25 years before the ZTF
epochs used in the fit, which also tests the period by extrapolation.

## Ephemerides (fitted to ZTF only; HJD - 2457000)

| star | primary minimum T0 | P (d) | secondary at phase | fitted to |
|---|---|---|---|---|
| UCAC4 468-115332 (Gaia DR3 4289848214689460736) | 2820.4166 | 5.358483 +/- 0.00007 | 0.7112 (from Gaia e, omega) | 12 ZTF g nights (primary) |
| UCAC4 544-021692 (Gaia DR3 3350386649103238016) | 3094.8414 | 7.245074 +/- 0.00019 | 0.4993 (from Gaia e, omega) | 7 ZTF r nights (both eclipses) |

## Data and rule (frozen)

- ZTF g (UCAC4 544-021692 only): IRSA light-curve service, cone 5 arcsec, filtercode zg,
  catflags == 0, magerr <= 0.03; per-oid median; faint = mag >= median + 0.05.
- ASAS-3 (both stars): www.astrouw.edu.pl ASAS-3 catalogue light curve; grade A and B points;
  aperture MAG_0 (the smallest, best for V ~ 12-12.5); 29.999 / 99.999 values dropped.
  Faint = MAG_0 >= median + 0.15 (UCAC4 468-115332, primary depth ~0.2-0.29 mag in ZTF g) or
  >= median + 0.10 (UCAC4 544-021692, depths ~0.11-0.19 mag in ZTF r).
- Phase from the table above; windows:
  - UCAC4 468-115332, ASAS-3: |phase| <= 0.04 around the primary (p = 0.08); extrapolation error
    ~0.017 phase at 1 sigma over ~1,270 cycles.
  - UCAC4 544-021692, ASAS-3: |phase| <= 0.05 around phase 0 or 0.4993 (p = 0.20); extrapolation
    error ~0.024 phase over ~900 cycles.
  - UCAC4 544-021692, ZTF g: |phase| <= 0.03 around phase 0 or 0.4993 (p = 0.12).
- Statistic: one-sided binomial P(>= k | n faint, p).
- Null: same window widths centred 0.25 later (reported; must hold <= max(2, 2 n p)).

## Predictions

- G1 (80%): UCAC4 544-021692 ZTF g: n >= 5, k >= 4, P < 1e-3, null passes.
- A1 (70%): UCAC4 468-115332 ASAS-3: n >= 5, k >= 4, P < 1e-3, null passes.
- A2 (45%): UCAC4 544-021692 ASAS-3: n >= 5, k >= 4, P < 1e-3, null passes.
- Fewer than 50 good points -> NO_DATA, not graded.

A PASS of G1 or A1/A2 confirms that star's eclipse ephemerides out of sample. Passing ASAS-3 also
confirms the ZTF period over 2000-2025, ruling out the Gaia DR3 period at the 1.5-2 sigma level.
