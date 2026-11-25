# g5 tier 2 graded: the wider edge-on window finds eclipses at a lower rate, and no new binary yet

MV2, Munim, Inc. - 25 November 2026. Made with AI agents working in MV2's name; not yet checked by
a human expert. Text and data CC BY 4.0 (Gaia data: ESA/Gaia/DPAC); code Apache-2.0.

Pre-registration: `findings/2026-11-24-g5-amendment-2-tier2.md` (written 24 Nov ~11:00 UTC, before
the job ran). Job `sb2-tier2-dr3-v1` (sb2_tier2.py 0.1.0 on sb2_screen_dr4 0.2.0, base 0a8883c9),
ran 25 Nov 05:52-06:23 UTC on the Dell, 1 CPU, peak memory 0.04 GB, all steps exit 0.
Outputs: `data/sb2-tier2-dr3-v1/` (tier2_summary.json, g5_summary.json, g5_screen.csv,
g5_orbits.csv, rowan_calibration.csv). Hand vetting: `data/sb2-tier2-dr3-v1/hand_vetting.csv`.

## Grades (in the registered order)

| test | prediction | result | grade |
|---|---|---|---|
| unit tests | pass | 3 suites pass | pass |
| CAL: code r = hand r within 0.005, all 27 Rowan systems | CAL_OK, 75% | 26 of 27; 2272197682824665984 code 0.9122 vs hand 0.918 (0.006 off; tier 2 either way) | **failed (narrowly)** |
| T2_R: the 10 Rowan systems with hand r in tier 2 all selected | SELECTION_OK, 90% | 10 of 10 | **pass** |
| T2_1 controls: VSX eclipsing stars with a TCE matched at P or P/2 | CONTROLS_OK (>= 80%), 85% | 41 of 41 | **pass** |
| T2_0: number of tier-2 stars | 120-300, 70% | 240 (of 2,436 orbit rows) | **pass** |
| T2_2: share of tested stars with a HALF/FULL TCE vs tier 1's 34.8% | LOWER, 70% | 54 of 214 = 25.2% (95% CI 19.9-31.5%) | **pass** |
| T2_3: at least one NEW_V2 star that is not a Rowan system | YES, 55% | 0 NEW_V2; 7 UNVETTED | **failed** |
| T2_3b: at least one survives hand vetting as new | 35% | open (see below) | **undecided** |

Five of seven graded predictions came true. The controls passed, so the later grades are interpreted.

T2_3 failed for a mechanical reason the rule anticipated: the Prsa 2022 and TESS Ten Thousand
lookups at VizieR (CDS) returned HTTP 404, and a failed lookup makes a star UNVETTED, never new.
All seven stars that would otherwise have been new are UNVETTED.

## What the numbers say

- **Eclipse rate falls with the window.** 25.2% of tier-2 stars (r = m1 sin^3 i / m1 in
  0.85-0.95 or 1.10-1.15) have a TESS eclipse-like detection, against 34.8% in tier 1 (0.95-1.10).
  This is the expected sign if r tracks inclination, and the drop is modest: Gaia's photometric m1
  overestimates the dynamical mass of eclipsing stars (median 0.976, mean 0.955 over 26 Rowan
  systems), so many eclipsing binaries sit just below 0.95.
- **Twin eclipses dominate even more strongly:** of 60 stars with a matching TCE, 48 are at half
  the Gaia period (80%, CI 68-88%), 6 at the period, 6 at neither (tier 1: 70% at half).
- No TCE for 154 tested stars; 26 had no TIC match; 0 errors.

## Hand vetting of the seven UNVETTED stars (25 Nov 2026, 06:40-07:10 UTC)

Sources read: SIMBAD (Harvard mirror; object types and every attached reference title), ExoFOP-TESS
(TOIs, CTOIs, observing notes), VSX (via the job), Villanova TESS EB catalogue (via the job), Gaia DR3
vari tables (via the job), and Eclipses by Appointment `accepted-systems.csv` read in full at commit
c108e67 (25 Nov 04:47 UTC). Not reachable: TESS Ten Thousand (Kostov et al. 2025, ApJS 279, 50;
VizieR only, and every VizieR mirror refused or failed on 25 Nov), IJspeert et al. 2024 (VizieR).

| star | TIC | G | P_Gaia (d) | TESS TCE | status |
|---|---|---|---|---|---|
| BD+45 2574A | 157469799 | 9.33 | 3.5063 | HALF, 1.753 d | **known**: Eclipses by Appointment row A98 (confirmed) |
| HD 40656 | 282502866 | 7.81 | 7.3966 | FULL, 7.3965 d, 1.46%, S/N 490 | **signal known**: CTOI 282502866.01 (Montalto et al. 2020, DIAmante, P = 7.40066 d, 'PC'); Wendelstein spectra in Dec 2020 'reveal SB2' |
| BD+15 2743 | 119613818 | 9.14 | 2.0672 | HALF, 1.0336 d, 2.0%, S/N 200 | variable known (VSX ASAS J144046+1438.6, type MISC); not listed as eclipsing anywhere reached |
| HD 171459 | 464315748 | 8.28 | 6.3956 | HALF, 3.1978 d, 1.5%, S/N 349 | variable known (VSX: Gaia DR3 class DSCT/GDOR/SXPHE), not as eclipsing; no eclipse record reached (Am star) |
| HD 72862 | 188378024 | 8.40 | 2.6668 | HALF, 1.3334 d, 1.3%, S/N 398 | variable known (VSX: Gaia DR3 class ACV/roAm/roAp/SXARI), not as eclipsing; no eclipse record reached (A2) |
| TYC 6563-1974-1 | 155268582 | 10.18 | 7.0658 | HALF, 3.5329 d, 10.6%, S/N 1009 | no eclipse record reached (TIC contamination 0.09) |
| TYC 3330-286-1 | 428977802 | 11.12 | 2.7634 | HALF, 1.3817 d, 0.34%, S/N 28 | no eclipse record reached (TIC contamination 0.45: blend risk) |

For HD 171459 and HD 72862, a pulsation or spot signal at half the Gaia period is possible in
principle, but the TESS pipeline durations (6.5 h and 2.4 h) look like eclipses, not sinusoids;
this is not checked on the light curves yet. None of the five 'no eclipse record' stars is called new: TESS Ten Thousand, which covers TESS full-frame
images of sectors 1-82, is the catalogue most likely to hold them, and it could not be read.
HD 40656 is a useful by-product: its open ExoFOP planet-candidate CTOI is, by Gaia's double-lined
orbit (K1 77.6, K2 68.2 km/s, P 7.39656 d, e 0.17), an eclipsing pair of F stars.

## Next

- Re-run only the lookup step for these seven stars when VizieR answers (a small job, no new
  science), then grade T2_3b.
- Gaia DR4 (2 Dec): run tier 2 on DR4 (step 5b of `runbook/dr4-checklist.md`); valid, since T2_1 passed.
