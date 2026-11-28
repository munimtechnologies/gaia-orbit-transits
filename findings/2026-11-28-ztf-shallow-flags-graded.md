# ZTF test of the unvetted shallow Gaia-epoch eclipse flags: results

MV2, Munim, Inc. (mv2@munimtech.com), 2026-11-28 (~15:10-16:40 UTC). CC BY 4.0. Made with AI agents working in
his name; **no human expert has checked it**. Pre-registration: `findings/2026-11-28-ztf-shallow-flags-prereg.md`
(same commit). Data: `data/ztf-shallow-flags/ztf_faint_points.csv` (every faint ZTF point used, with its oid,
HJD, magnitude, Gaia cycle and phase). All phases were computed by hand from the IRSA rows; the queued job
`ztf-cands-tess-v1` recomputes them in code (`ztf_recheck.py`) and reports any disagreement.

## Short answer

- **The frozen two-stage rule confirmed none of the three unlisted stars.** ZTF has no r-band light curve for
  any of them (they are saturated in r), so the declared fallback split the g data at HJD 2459500, and the
  split left too few faint points on one side or the other (verdicts below).
- **Looked at as a whole, after the fact, all three show eclipses on Gaia's spectroscopic period at Gaia's
  predicted conjunction.** They are strong new eclipsing-binary candidates, not yet confirmed by a
  pre-registered test. A blind TESS test with ephemerides frozen today is queued
  (`findings/2026-11-28-ztf-cands-tess-prereg.md`).
- **TYC 2091-796-1** (Gaia DR3 4576721896566803072, P = 12.42 d, e = 0.23) shows both eclipses: a primary on 8
  nights and a secondary on 7 nights, 0.3936 +- 0.0012 of an orbit after the primary, in two independent ZTF
  fields. Gaia's eccentric orbit predicts 0.383 +- ~0.01 (1.2 sigma). The eclipse timing therefore checks
  Gaia's eccentricity and periastron angle from light alone.

## Catalogue check (purity of the shallow flags)

Of the 8 shallow, unclassified, G >= 12, Dec > -28 flags, 3 are already catalogued eclipsers (ASAS-SN EA
981348113867985920; IJspeert et al. 2024 OBAF EB candidates 1993895376986150272 and 4511109601032181504), 2 are
only in TESS Ten Thousand table 2 (unvetted machine targets), and 3 are listed nowhere as eclipsing (VSX lists
each only as a Gaia DR3 "VAR" with a spurious 20-58-minute period). 5 of 8 still untested in TESS.

## Pre-registered verdicts (frozen rule)

| star (Gaia DR3) | ZTF g rows (main oid) | median g | faint g, HJD < 2459500 | faint g, HJD >= 2459500 | verdict |
|---|---|---|---|---|---|
| UCAC4 583-070217 (4535010166315168640) | 348 + 203 | 12.7477 | 2 nights | 8 points | **NOT_FOUND** (stage 1 needs >= 4 faint nights) |
| UCAC4 677-002225 (391817260687992960) | ~1,060 | 12.6580 | 7 nights, 5 within 0.008 of each other | 3 points | stage 1 FOUND; **stage 2 NO_DATA** (< 5 faint points) |
| TYC 2091-796-1 (4576721896566803072) | ~800 | 12.5222 | 18 points: 5 primary nights within 0.017, 3 secondary nights within 0.003 | 50 points | stage 1 FOUND; **stage 2 FAIL** (see below) |
| 4497399653101181184, 4229808420168374400 | - | - | - | - | not tested (time); in the TESS job |

TYC 2091-796-1 fails stage 2 because the main ZTF field's g photometry in 2025 sits about 0.03-0.05 mag faint
for months (42 consecutive faint points between HJD 2460817 and 2460960 at all phases), so faint-point
counting against one all-season median is swamped; of the 50 post-split faint points only 2 primaries and 1
secondary fall at the frozen eclipse times. **Lesson: the faint threshold must be set per season (or per
night) relative to a local median, and a split by date must be checked for power before freezing.**

## What the data show (post hoc, clearly not pre-registered)

Phases below are relative to Gaia's predicted primary conjunction (visible star behind its companion) at
Gaia's period; positive = later.

### UCAC4 583-070217 (TIC 358858602; G 12.35, Teff 6,320 K, R 1.5 Rsun; P_Gaia 3.10003 +- 0.00018 d)

- 10 faint points in the main field (2018-2025). **9 of 10 lie within +-0.010 of an orbit of one linear
  ephemeris**; their Gaia phase drifts steadily from 0.012 (2018) to 0.128 (2025), the signature of a small
  period error. Least squares on the 9: **P = 3.100431 +- 0.000024 d** (Gaia's period + 0.00040 d, 2.2 Gaia
  sigma), rms 0.006 of an orbit (27 min). The tenth point (0.035 mag faint, at the threshold) is 0.071 off.
- Extrapolated back 290 orbits, this ZTF-only ephemeris puts the eclipse 0.020 +- 0.007 of an orbit
  (1.5 h) before **Gaia's spectroscopic conjunction**, which was not used in the fit.
- It also predicts the three Gaia DR3 photometric dips (0.05 mag at Gaia times 2182.97, 2198.48, 2486.80, i.e.
  BTJD 380.47, 395.98, 684.30) to within 0.004-0.012 of an orbit.
- The second ZTF field (oid 1682103400018216, not part of the rule) has a faint point 0.002 from the ephemeris.
- Frozen ephemeris: **T_min = BTJD 2929.0475 + 3.100431 E** (BTJD = BJD - 2457000).
- Gaia mass function 0.039 Msun -> companion >= 0.49 Msun for a 1.25 Msun primary (an early M or late K dwarf);
  depth of a central transit ~0.1 mag vs faint points 0.035-0.068 mag below median.

### UCAC4 677-002225 (TIC 440168538; G 12.33, Teff 6,260 K, R 1.56 Rsun; P_Gaia 11.36253 +- 0.0016 d)

- **7 of 10 faint nights fall 0.008-0.022 of an orbit after Gaia's predicted conjunction using Gaia's
  period unchanged** (2018-2025, 79-310 orbits after Gaia's epoch); the other 3 are single points
  0.036-0.047 mag faint at phases 0.47, 0.85 and 0.40. On 2019-09-27 (HJD 2458758.85-.88) four consecutive
  points are 0.043-0.068 mag faint, matched by two points in the second field.
- Chance that >= 7 of 10 random faint nights fall within +-0.025 of the predicted phase: 8e-8 (window chosen
  after looking; with a window wide enough for Gaia's period error, +-0.13, it is 4.5e-3).
- Fit to the 7 primary nights: **P = 11.36306 d** (Gaia + 0.00053 d, 0.3 sigma), T0 = BTJD 395.2982, i.e.
  **0.083 d (0.007 orbit) after Gaia's conjunction**; rms 0.003 of an orbit (50 min). Gaia's own two dips (BTJD
  361.16, 520.35) fall 0.003 and 0.013 after it.
- Frozen ephemeris: **T_min = BTJD 395.2982 + 11.363060 E**. Companion >= 0.64 Msun (f(m) = 0.075).

### TYC 2091-796-1 (TIC 135364450; G 12.16, Teff 6,270 K, R 2.1 Rsun; P_Gaia 12.42320 +- 0.0016 d, e 0.231 +- 0.014, omega 217.5 +- 3.9 deg)

- Primary eclipse on 8 nights (7 in the main field, 1 more only in the second field; 3 nights seen in both
  fields), depths up to 0.127 mag (main field, 2025-06-21; 0.072 mag in the second field the same night).
- Fit to the 8 primary nights (both fields): **P = 12.42146 d** (Gaia - 0.0017 d, 1.1 sigma), T0 = BTJD
  395.4568, **0.030 d (0.0024 orbit) before Gaia's conjunction**; rms 0.005 of an orbit (1.5 h).
- **Secondary eclipse in 9 detections on 7 distinct nights** (4 main field, 5 second field, 2 nights in
  both; 0.035-0.092 mag faint) at
  **0.3936 +- 0.0012 of an orbit after the primary** (sd 0.0037). Gaia's orbit predicts 0.3826 (from
  e cos omega = -0.184 +- 0.015), so the light curve gives e cos omega ~ -0.167, 1.2 sigma from Gaia. The
  secondary also comes 0.39, not 0.61, after the primary, the side Gaia's omega requires.
- Post-hoc check on the second ZTF field with the stage-1 ephemeris (main field, HJD < 2459500 only) and
  +-0.02 windows at both eclipses (p = 0.08): 9 of 13 faint nights in the windows (P = 7e-8). Several of these
  nights had been looked at before the check, so it is not a blind test.
- Frozen ephemeris: **T_min = BTJD 395.4568 + 12.421463 E; secondary at +0.3936 P.**
- Puzzle: the secondary is 0.06-0.09 mag deep, about 70% of the primary. A main-sequence companion of the
  minimum mass from Gaia's single-lined orbit (f(m) = 0.106 -> >= 0.74 Msun, a K dwarf) would give a secondary
  of only ~0.02 mag. Either the companion is hotter/larger than that (and Gaia's single-lined K1 is diluted by
  blended lines, so the true masses are larger), or the faint-point depths are biased. TESS will measure both
  depths.

## Neighbours

TIC cones: UCAC4 583-070217 has one G 18.9 star at 4.3"; UCAC4 677-002225 none within 5"; TYC 2091-796-1 has
nothing brighter than G 16.6 within 30" (11.3"). None can make 0.05-0.13 mag dips in ZTF's 2" photometry.

## Prior art (28 Nov 2026, 16:00-16:30 UTC)

VizieR CfA cones (90", ten catalogues incl. VSX, GCVS/NSV, ASAS-SN, ATLAS, ZTF periodic variables, TESS Ten
Thousand, Prsa+2022, IJspeert+2021/2024, ASAS-3): no eclipse listing for the three. SIMBAD: type SB* with only
the two Gaia DR3 references each. Gaia DR3 vari_eclipsing_binary: absent (in_gaia_eb = False in our search).
Web and arXiv full-text searches for the TYC/UCAC4 names and Gaia ids: nothing. Eclipses by Appointment's main
search is limited to G < 11.5 (its README at commit 7d14914); its newest commit is still 2ef86d2 (27 Nov); an
id scan of all its files is in the queued job. **Within these searches, none of the three is a known eclipsing
binary.**

## What this does and does not show

Strong: 31 eclipse nights across three stars (9 + 7 + 8 primary and 7 secondary) fall on ephemerides whose periods agree with Gaia's
spectroscopic periods within 0.3-2.2 Gaia sigma and whose zero points agree with Gaia's spectroscopic
conjunctions within 0.002-0.020 of an orbit; for TYC 2091-796-1 the secondary eclipse falls where Gaia's
eccentric orbit says it should. Not shown: a pre-registered out-of-sample pass, eclipse depths and shapes,
inclinations, or masses. Status: **strong candidates**; the TESS test decides.
