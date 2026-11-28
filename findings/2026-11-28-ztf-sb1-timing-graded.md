# ZTF timing test of two faint Gaia DR3 SB1 eclipse candidates: graded

MV2, Munim, Inc. (mv2@munimtech.com), 2026-11-28 (~07:10-07:45 UTC). CC BY 4.0. Carried out with AI
agents working in MV2's name; no human expert has checked it. Pre-registration:
findings/2026-11-28-ztf-sb1-timing-prereg.md. Data: data/ztf-sb1-timing/ztf_faint_points.csv.

## Data actually obtained

- IRSA ZTF light-curve service, 28 Nov 2026. The registered 1.5-arcsec cone returned data only
  for UCAC4 544-021692 (zr, 2 oids, 225 rows, 179 with catflags 0). For UCAC4 468-115332 and the
  control, zr returned nothing even in a 5-arcsec cone (deviation: cone widened to 5 arcsec), so,
  as registered, zg was used: UCAC4 468-115332 one main oid 489106400042461 with 382 good points
  (median 12.5324469) and a second oid 1483115400020752 with 22 good points (median 12.5414772,
  no faint points); control oid 1838101300008266, 75 good points (median 12.7569742).
- Medians were computed from sorted value lists read in two 100k-character pages by WebFetch;
  the counts are given in the CSV header columns. All good points have magerr 0.011-0.022.

## Grades (as registered)

| prediction | star | n faint | k in window | window | binomial P | grade |
|---|---|---|---|---|---|---|
| Z1 (60%) | UCAC4 544-021692 (zr) | 16 | 1 | +/-0.12 (p 0.24) | 0.99 | FAIL |
| Z2 (60%) | UCAC4 468-115332 (zg) | 16 | 4 | +/-0.08 (p 0.16) | 0.25 | FAIL |
| C1 (70%) | control 1993895376986150272 (zg) | 5 | 2 | +/-0.12 (p 0.24) | 0.34 | FAIL |
| N1 (80%) | all three | - | null windows: 6/0, 1/0, 0/3 | limits 7.7, 5.1, 2.4 | - | FAIL (control +0.25 window holds 3 > 2.4) |

All four registered predictions failed.

## Why they failed (post hoc, not graded)

The faint points are not scattered: they lie on straight lines in phase versus time, which is what
a period slightly different from Gaia's produces. The windows were sized on the 1-sigma drift; the
true periods differ from Gaia DR3's by 1.5-2.0 sigma, so the eclipses walk out of the windows.

- UCAC4 468-115332: 12 faint points on 12 different nights (2018-2025) lie on one line,
  dphi = -0.0844 - 2.769e-5 (t - 2819.08) (t = HJD - 2457000), residual RMS 0.006 of an orbit.
  At the Gaia epoch the line passes dphi = -0.017, i.e. through Gaia's conjunction. The period that
  makes the line flat is P = 5.358483 +/- 0.00007 d (Gaia DR3: 5.3592781 +/- 0.0005246; 1.5 sigma).
  The other 4 faint points are shallower (0.050-0.058 mag) and fall 0.7077, 0.7061 and 0.730 of an
  orbit after the primary on that ephemeris: Gaia's eccentric orbit (e = 0.41, omega = 37 deg)
  predicts the secondary eclipse at 0.7112. Primary depths reach 0.29 mag in g.
- UCAC4 544-021692: the 16 faint points fall on 7 nights in two groups half an orbit apart; one
  common line with the secondary held at Gaia's 0.4993 fits all 7 nights with RMS 0.007 and passes
  dphi = +0.020 at the Gaia epoch. Period P = 7.245074 +/- 0.00019 d (Gaia DR3 7.2472787 +/-
  0.0011152; 2.0 sigma). Both eclipses are 0.11-0.19 mag deep in r.
- Control: two groups (2018 at dphi +0.07-0.09 and 2023 at +0.19-0.24); a line through two groups
  tests nothing. Inconclusive.

These ephemerides were found after looking at the data, so they are not evidence on their own. They
were frozen in findings/2026-11-28-ztf-ephemeris-confirm-prereg.md and tested on data not used to
fit them; see findings/2026-11-28-ztf-ephemeris-confirm-graded.md.

## Lesson

Gaia DR3 SB1 period errors are too small for extrapolating several hundred cycles (EbA's 26 Nov
commit f0cdcc4 also rescales them). Windows for timing tests must cover >= 3 sigma of drift, or
the test must fit a period correction with its own null.
