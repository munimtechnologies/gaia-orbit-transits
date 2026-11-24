# g5 amendment 2: a second tier for the edge-on SB2 screen, calibrated on Rowan et al. (2023)

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked it yet.
CC BY 4.0 (text), Apache-2.0 (code). Written 2026-11-24 ~11:00 UTC, **before** job sb2-tier2-dr3-v1
ran and eight days before Gaia DR4. Code: `sb2_tier2.py` 0.1.0, tests `test_sb2_tier2.py`, job
`runbook/tier2/job.json`.

## 1. Why (exploratory, from data already public)

The g5 screen calls a Gaia DR3 double-lined orbit "edge-on" when r = m1 sin³i / m1 lies in
[0.95, 1.10]. Here m1 sin³i comes from Gaia's K1, K2, P and e, and m1 from Gaia's `binary_masses`
(method SB2+M1). That rule found HD 250735 and CD-28 7251. We had never measured what it misses.

[Rowan et al. (2023), MNRAS 523, 2641](https://arxiv.org/abs/2212.02509) fitted ASAS-SN light curves of
eclipsing Gaia SB2s and published inclinations for 61 systems
(https://asas-sn.osu.edu/binaries/mass-radius, CSV read 24 Nov 2026). These eclipsing systems give an
independent check of the rule:

- 52 of the 61 have P < 8 d. **27** of those 52 are in our saved DR3 sample (`binary_masses` SB2+M1,
  `data/sb2-edgeon-screen-v1/gaia_sb2_m1_p8.csv`). The other 25 have no SB2+M1 mass, so no rule
  based on m1 can select them.
- Of the 27, the tier-1 window selected **11** (41%). These are exactly the 11 Rowan systems in the
  183-star tier-1 screen, and all 11 have Rowan inclinations of 81-89.8°.
- Of the 16 missed, **15 fall below 0.95** and one above 1.10 (r = 1.160). Values:
  0.944, 0.932, 0.923, 0.918, 0.914, 0.893, 0.889, 0.886, 0.865, 0.862, 0.825, 0.812, 0.757,
  0.701 (CM Dra) and 0.242. The last has Gaia K2 = 28 against K1 = 144 km/s, an implausible
  double-lined solution.
- Dividing r by Rowan's sin³i gives the dynamical mass over Gaia's m1. Over 26 systems (the bad-K
  one excluded) the median is 0.976 and the mean 0.955; 10 of 26 are below 0.95. Gaia's
  photometric m1 tends to be higher than the dynamical mass of these eclipsing stars. For CM Dra,
  Gaia's m1 is 0.319 M_sun against a dynamical 0.224 from Gaia's own K's.
- **A window of [0.85, 1.15] would have selected 21 of the 27 (78%).**

All the numbers above are a **hand calculation** from the files named. They are in
`data/rowan2023-check/rowan_tier_check.csv`. The job recomputes every r in code and compares it
with the hand value (tolerance 0.005); the comparison is reported as CAL_OK or CAL_DIFFERS.

## 2. The registered rule

**Tier 2** = 0.85 ≤ r < 0.95, or 1.10 < r ≤ 1.15, with P < 8 d, K1 > 0, K2 > 0, m1 > 0 (same sample
and maths as tier 1, `sb2_screen` 0.1.0 at 0a8883c9). It shares no star with tier 1. Everything after
selection is `sb2_screen_dr4` 0.2.0 (f282d097), unchanged: TIC from ExoFOP, SPOC TCEs classified
HALF, FULL, OTHER or NONE, and for HALF/FULL the lookups VSX, ExoFOP TOI, SIMBAD, Villanova (with
controls), the Prša 2022 EB catalogue and TESS Ten Thousand (VizieR, self-controlled), plus Gaia
`vari_eclipsing_binary` and `vari_classifier_result`. A star is NEW_V2 only if every lookup answered
and all were negative; any failed lookup gives UNVETTED. A Rowan system is relabelled KNOWN.

Gaia's own tables are queried at ESA first, then at the AIP mirror (https://gaia.aip.de/tap/sync,
checked 24 Nov to serve both tables). The DR3 orbit rows come from the saved, public CSV, so the job
does not need ESA's archive, which is closed from 25 Nov 12:00 CET to 2 Dec.

## 3. Tests and predictions (DR3, job sb2-tier2-dr3-v1)

| test | what | prediction |
|---|---|---|
| self-test, unit tests | must pass before anything is read | — |
| CAL | code r equals hand r within 0.005 for all 27 | CAL_OK, 75% |
| T2_R | the 10 Rowan systems with hand r in tier 2 are all selected | SELECTION_OK, 90% |
| T2_0 | number of tier-2 stars | 120-300, 70% |
| T2_1 | VSX-eclipsing stars with a TCE matched at P or P/2 (≥ 80%) | CONTROLS_OK, 85% |
| T2_2 | share of tested stars with a HALF/FULL TCE, against tier 1's 56/161 = 34.8% | LOWER, 70% |
| T2_3 | at least one NEW_V2 star that is not a Rowan system | YES, 55% |
| T2_3b | at least one survives hand vetting as new | 35% |

Hand vetting of each T2_3 star, before it is called new: Eclipses by Appointment
`accepted-systems.csv` (all of it), Rowan et al. 2023, Prša et al. 2022, TESS Ten Thousand, VSX,
SIMBAD, ASAS-SN, ExoFOP, a web search of its names, and its TESS light curve and DV report. A star is
called a candidate, never a discovery, until that is done.

Grading order: self-test, unit tests, CAL, T2_R and T2_1 (controls), then T2_0, T2_2, T2_3. If a
control fails, the later grades are reported but not interpreted.

## 4. Gaia DR4 (2 December)

After step 5 of `runbook/dr4-checklist.md` (tier 1 on DR4), file step **5b**:
`python sb2_tier2.py --schema gaiadr4 --out-dir /out` with the same job template. This is valid only if
the DR3 job's T2_1 was CONTROLS_OK. T2_R and CAL do not apply to DR4. If DR4 has no `binary_masses`
(schema gate arm B), there is no m1 and tier 2 is not run.

## 5. What this can and cannot show

Tier 2 trades purity for completeness. It should hold more eclipsing systems that tier 1 missed,
and more non-eclipsing ones. The Rowan calibration is a sample of ASAS-SN-detectable eclipsing
binaries (V > 11). It is fainter than most of our stars, and it is not a random sample of Gaia SB2s.
