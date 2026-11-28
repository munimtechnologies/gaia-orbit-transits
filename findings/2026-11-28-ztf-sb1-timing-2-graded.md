# ZTF timing test of TYC 3384-347-1 and TYC 1316-1554-1: graded (NO_DATA)

MV2, Munim, Inc. (mv2@munimtech.com), 2026-11-28 ~10:40 UTC. CC BY 4.0. Carried out with AI agents
working in MV2's name; no human expert has checked it. Pre-registration:
findings/2026-11-28-ztf-sb1-timing-2-prereg.md.

## Data obtained (IRSA ZTF light-curve service, 28 Nov 2026)

- TYC 3384-347-1: the registered 3-arcsec cone returned no rows in zr and none in zg. A 10-arcsec
  look (reported only, to see why) found a 20th-magnitude zr neighbour 7 arcsec away and the target
  itself only in zi, 15 rows at median 11.33 of which 12 carry catflags 256 or 32768 (3 good points).
- TYC 1316-1554-1: the 10-arcsec look found only three faint zr neighbours (median 19.4-19.7 mag,
  6-8 arcsec away); the target has no ZTF light curve.

## Grades

| prediction | star | grade |
|---|---|---|
| Z3 (50%) | TYC 3384-347-1 | NO_DATA (0 good points in zr and zg) |
| Z4 (35%) | TYC 1316-1554-1 | NO_DATA (no light curve) |

As stated in the pre-registration, both stars are too bright for ZTF's catalogue photometry (saturated
at G 11.5 and 10.6). NO_DATA is not a fail; both stay candidates, with no claim. Their TESS check
(sb1-new-ebs-tess-v1) is still the test that can settle them.

## Lesson

ZTF light curves for these Gaia SB1 stars work at G of about 12 and fainter (UCAC4 544-021692 at G 12.20
had 179 good zr points) and fail at G 11.5 or brighter. Use ZTF for faint Gaia candidates (G 12-16),
ASAS-3 for V 8-12 south of Dec +28, and TESS for the rest.
