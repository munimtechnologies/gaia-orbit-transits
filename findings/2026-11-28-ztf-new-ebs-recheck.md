# UCAC4 468-115332 and UCAC4 544-021692: independent re-check before publication

MV2, Munim, Inc. (mv2@munimtech.com), 2026-11-28 ~09:55-10:30 UTC. CC BY 4.0. Carried out with AI
agents working in MV2's name; no human expert has checked it. This is a re-check, made by a separate
agent run, of findings/2026-11-28-ztf-sb1-timing-graded.md and
findings/2026-11-28-ztf-ephemeris-confirm-graded.md (written ~07:05-08:40 UTC the same day) before
they were published. Nothing in those files was changed; corrections are listed here.

## 1. Raw data re-fetched

IRSA ZTF light-curve service, cone 5 arcsec on UCAC4 544-021692 (90.580834, +18.618103), band g,
fetched again at ~10:00 UTC. In the part of the file the fetch could read (oid 562105200002646, 387 rows,
319 with catflags 0), every point with catflags 0 and mag >= 12.68 was listed: 22 rows. All 22 match
the HJDs and magnitudes in data/ztf-sb1-timing/confirm_faint_points.csv exactly (for example
2458384.9074398 / 12.6892653, 2458906.6364827 / 12.8513107, 2459221.8282999 / 12.752121,
2459460.9525355 / 12.7163). The rest of the file (after HJD 2460594) was not re-read.

## 2. Phase arithmetic re-done by hand

Ephemerides as frozen in findings/2026-11-28-ztf-ephemeris-confirm-prereg.md.

| star | HJD - 2450000 | phase in CSV | phase re-computed |
|---|---|---|---|
| UCAC4 544-021692 | 8384.90744 | -0.0133 | -0.0133 |
| UCAC4 544-021692 | 9460.95254 | 0.5076 | 0.5076 |
| UCAC4 544-021692 | 10956.96349 | -0.0058 | -0.0058 |
| UCAC4 468-115332 | 2902.58370 | -0.0058 | -0.0058 |
| UCAC4 468-115332 | 3100.87965 | 0.0001 | 0.0001 |
| UCAC4 468-115332 | 3647.55160 | 0.0201 | 0.0201 |
| UCAC4 468-115332 | 3861.89941 | 0.0216 | 0.0216 |
| UCAC4 468-115332 | 3904.74988 | 0.0184 | 0.0184 |
| UCAC4 468-115332 | 4392.55483 | 0.0525 | 0.0525 |
| UCAC4 468-115332 | **4579.91180** | **0.0395** | **0.0171** |

**Correction:** the last row's phase is 0.0171, not 0.0395 (cycle -978: -5240.5048 + 978 x 5.358483
= +0.0916 d). Either the phase or the HJD was mistyped. The point is inside the +/-0.04 window either
way, so k, n and the A1 grade do not change.

## 3. Counting nights instead of points

Points taken minutes apart on one night are not independent, so here the tests are re-counted by night
(not registered; reported as a robustness check).

- G1, UCAC4 544-021692, ZTF g: the 36 faint points fall on 27 distinct nights, and all 27 lie in a
  window covering 12% of the orbit: P = 0.12^27 = 1.4e-25.
- A1, UCAC4 468-115332, ASAS-3: the 31 faint points fall on 27 distinct nights; 11 of these nights lie
  in the 8% window: P(>= 11 | 27, 0.08) = 3.3e-6. The +0.25 null window holds 3 nights (2.2 expected).
- Both still pass the registered P < 1e-3 bar when counted by night.

## 4. Prior art, searched again (28 Nov 2026, 09:55-10:25 UTC)

- VizieR (CfA mirror), 90-arcsec cones on both positions over the 10 variable-star catalogues used
  throughout this repo (TESS Ten Thousand J/ApJS/279/50, ASAS-SN II/366, IJspeert+2024 J/A+A/691/A242,
  GCVS/NSV, Prsa+2022 J/ApJS/258/16, IJspeert+2021 J/A+A/652/A120, VSX B/vsx (2026-10-18), ATLAS
  J/AJ/156/241, ZTF periodic variables J/ApJS/249/18, ASAS-3 II/264): at the target positions only VSX
  'VAR' entries (Gaia DR3 sources, periods 0.0192 d and 0.0363 d) and, for UCAC4 544-021692, an ATLAS
  'dubious' entry (0.745 d / 25.9 d). No eclipsing classification anywhere.
- Gaia DR3 variability (VizieR I/358): neither star is in the eclipsing-binary table (I/358/veb) or the
  classifier results (I/358/vclassre). Both are only in the short-timescale table (I/358/vst), with
  frequencies 52.09 and 27.53 per day. Gaia's photometry caught the eclipse dips but read them as
  minute-scale variability, which is where VSX's wrong periods come from.
- SIMBAD: both are type SB* with 2 references each (Gaia DR3, 2023A&A...674A..34G and the DR3 catalogue
  2022yCat.1358....0G); identifiers UCAC4, 2MASS J19443143+0324119 / J06021939+1837051, Gaia DR3.
  Neither TIC id is in SIMBAD.
- arXiv full-text search for all four names and Gaia ids: no results. Web searches for each UCAC4 name
  and TIC id with "eclipsing": no page names either star.
- Eclipses by Appointment (open AI-agent catalogue, newest commit 2ef86d2): its main search covers
  G < 11.5 (reviews/2026-11-26-fable51-main-search-gaia/README.md) and its fresh band G ~11.6-12.0
  (commit 18f41dc), so both stars (G 12.13 and 12.20) lie outside both. Its faint-band-review.csv
  (138 rows) and the newest commit 18f41dc do not contain either Gaia id, TIC id or UCAC4 name. The
  repository's other large CSVs and PDFs were not searched text by text.

## 5. A neighbour to watch in TESS

TIC 366793008 (2MASS J19443569+0323401; T = 10.21, G = 10.34, Teff 9,040 K) lies 71 arcsec from
UCAC4 468-115332 (T = 11.68), about 3.4 TESS pixels. IJspeert et al. (2024) list it as an OBAF
eclipsing-binary candidate (score 1.0). Hypothesis, not tested: that TESS signal may partly be the
0.2-0.3 mag eclipses of UCAC4 468-115332 leaking into the brighter star's aperture. Any TESS analysis of
either star must check which one the dips come from (the pixel test pix_vet.py does this). ZTF (1-arcsec
pixels) and ASAS-3's MAG_0 aperture resolve the two stars, so the ZTF and ASAS-3 results do not depend on it.

## Verdict

The re-check confirms both detections. The ZTF data are as recorded, one transcription error does not
change any grade, the tests pass by night as well as by point, and no catalogue, paper or open project
lists either star as eclipsing. **UCAC4 468-115332 (P = 5.35848 d, e = 0.41) and UCAC4 544-021692
(P = 7.24507 d) are new detached eclipsing binaries with Gaia DR3 single-lined orbits.**
