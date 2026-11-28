# Out-of-sample test of two ZTF-derived eclipse ephemerides: graded

MV2, Munim, Inc. (mv2@munimtech.com), 2026-11-28 (~07:50-08:40 UTC). CC BY 4.0. Carried out with AI
agents working in MV2's name; no human expert has checked it. Pre-registration:
findings/2026-11-28-ztf-ephemeris-confirm-prereg.md. Data: data/ztf-sb1-timing/confirm_faint_points.csv.

## Result

**UCAC4 468-115332 (Gaia DR3 4289848214689460736, TIC 366792984) and UCAC4 544-021692 (Gaia DR3
3350386649103238016, TIC 429591515) are eclipsing binaries.** Each one passed a test on data its
ephemeris was not fitted to (G1 for 544-021692, A1 for 468-115332). Neither is listed as eclipsing in VSX
(Gaia 'VAR' entries with spurious 27- and 52-minute periods only), ATLAS (544-021692 classed
'dubious', periods 0.745 d / 25.9 d), ASAS-SN, ZTF periodic variables, GCVS/NSV, Prsa+2022,
IJspeert+2021/2024, TESS Ten Thousand, ASAS, SIMBAD (type SB*, two Gaia references each) or Eclipses
by Appointment's accepted-systems.csv (all ~1,900 rows), and arXiv and web searches for their names
and Gaia ids return nothing (28 Nov 2026).

| prediction | star, data | n faint | k in window | p | binomial P | null (+0.25) | grade |
|---|---|---|---|---|---|---|---|
| G1 (80%) | UCAC4 544-021692, ZTF g (3 oids, 432 good points; 25 of its 27 nights are not in the r-band fit) | 36 | 36 | 0.12 | 7e-34 | 0 | PASS |
| A1 (70%) | UCAC4 468-115332, ASAS-3 2000-2009 (532 + 219 A/B points, 2 datasets) | 31 | 15 (11 nights) | 0.08 | 3e-9 | 3 (limit 5.0) | PASS |
| A2 (45%) | UCAC4 544-021692, ASAS-3 2000-2009 (298 + 15 + 161 + 38 A/B points, 4 datasets) | 65 | 24 (13 expected) | 0.20 | 1.2e-3 | 14 (limit 26) | FAIL (P above 1e-3) |

## Details

- G1: all 36 faint g points lie within 0.023 of an orbit of the predicted eclipses (28 primary,
  8 secondary; max |offset| 0.0225 primary, 0.0127 secondary). Primary depths reach 0.25 mag in g
  and secondary depths 0.05-0.14 mag, so the primary (at Gaia's conjunction 0, the visible star
  behind) is the deeper eclipse in g, as a single-lined binary requires; in r the two are similar
  (0.11-0.19 mag), so the eclipsed star is the hotter, bluer one. No phase drift is visible from 2018 to 2025,
  so the ZTF period 7.245074 d holds.
- A1: the 15 in-window ASAS-3 points sit at a mean +0.014 of an orbit (scatter 0.02) after the
  predicted primary, ~1,290 cycles before the ZTF epoch. Post hoc, that implies a period about
  0.00006 d shorter: P ~ 5.35843 +/- 0.00002 d from ASAS-3 + ZTF combined (estimate, not graded).
  The Gaia DR3 period (5.3592781) would put these eclipses 0.19 of an orbit away.
- A2: an excess (24 against 13 expected) but not significant at the registered level; ASAS-3's
  0.05-0.09 mag errors at V ~ 12.4 are close to the 0.10 mag cut. The 2000-2009 period of
  UCAC4 544-021692 is not tested.
- WebFetch read the ASAS-3 tables; two HJDs (3329.76732 and 3349.66968) appear in two different
  ASAS fields, which may be a transcription duplicate. Removing either copy changes A2 by at most
  one point and does not touch G1 or A1.

## Ephemerides (HJD - 2457000) and systems

| star | primary minimum | P (d) | secondary phase | depths | f(m) | companion at i = 90 deg |
|---|---|---|---|---|---|---|
| UCAC4 468-115332 | 2820.4166 +/- 0.010 | 5.358483 +/- 0.00007 (ZTF); ~5.35843 with ASAS-3 | 0.7112 (Gaia e = 0.41, omega = 37 deg; ZTF 0.706-0.730) | primary to 0.29 mag (g), secondary ~0.05 mag | 0.133 | ~0.83 Msun for M1 = 1.25 Msun |
| UCAC4 544-021692 | 3094.8414 +/- 0.010 | 7.245074 +/- 0.00019 | 0.4993 | primary to 0.25 mag (g), secondary to 0.14 mag (g) | 0.172 | ~0.91 Msun for M1 = 1.18 Msun |

M1 from TIC 8.2 (Teff 6334 K / 6169 K, R 1.91 Rsun both); distances 556 pc / 624 pc from Gaia
parallax. Both are F/G primaries with G/K-dwarf companions in detached orbits; UCAC4 468-115332's
e = 0.41 at P = 5.36 d is unusually eccentric for a binary this short, which makes its apsidal
motion measurable (TESS will test it).

## What this adds

Two new detached eclipsing binaries with full Gaia DR3 spectroscopic orbits, so they are ready for
masses once TESS light curves give the inclination (sb1-new-ebs-tess-v1 is queued). They raise the
confirmed count from the blind Gaia DR3 SB1 conjunction search to three unlisted eclipsing binaries
(with HD 125386A). The ZTF periods are 7-16x more precise than Gaia DR3's and differ from them by
1.5-2.0 sigma.

## Limits

No light-curve model was fitted; depths are single-point values in ZTF's 1-arcsec photometry. The
ephemerides were found post hoc on ZTF r (544-021692) and ZTF g (468-115332) and are confirmed only
by the out-of-sample tests above. Medians and faint lists were read by WebFetch from IRSA and ASAS-3
pages, not by code; every number is in the CSV for re-checking. Not yet submitted to VSX (no AAVSO
account).
