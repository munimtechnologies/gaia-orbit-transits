# Graded: all-sector, period-free TESS follow-up of Gaia's two surviving transit candidates

Written 2026-11-25 (~01:30 UTC). By MV2 of Munim, Inc.; made with AI agents working in his name,
not yet checked by a human expert. Text and data CC BY 4.0 (Gaia data ESA/Gaia/DPAC; TESS data
from MAST); code Apache-2.0.

- Pre-registration: `findings/2026-11-21-vpt-followup-prereg.md` (written 21 Nov ~17:00 UTC, before
  the job ran). Code `vpt_followup.py` 0.1.0, unchanged.
- Job **gaia-vpt-followup-v1** ran on the Blade 24 Nov 23:37 - 25 Nov 00:11 UTC: unit tests and
  self-test passed, all 5 targets done, no errors.
- Outputs: `data/vpt-followup-v1/` (fu_summary.json, fu_targets_out.csv, fu_sectors.csv,
  fu_scans.csv and the two candidate folds).

## What this adds, and what it does not

Our period-free search of all 214 Gaia DR3 transit candidates (`findings/2026-11-22-vpt-pf-dr3-
results.md`, 22 Nov) had already found the same TESS periods for both stars (2.20828 d and
3.54941 d). This job is the dedicated, pre-registered test written before that search, with its
own positive controls, every TESS sector available on 24 Nov (up to sector 99), and three
eclipsing-binary tests (odd/even, secondary, companion size) plus a per-sector depth check. It
**confirms** the 22 Nov result under a frozen rule; it is not a new detection.

## Grades

| test | result | prediction (21 Nov) | |
|---|---|---|---|
| Controls (WASP-4 b, HATS-52 b, WASP-17 b within 0.1% of known P, S/N >= 7) | **CONTROLS_PASS** (3/3) | CONTROLS_PASS 80% | held |
| TIC 4638108 | **SURVIVES** | SURVIVES 55% | held |
| TIC 44997521 | **SURVIVES** | SURVIVES 45% | held |

All three most-likely outcomes held. The controls also show the period-free design works where
Gaia's period is wrong: for WASP-4 (Gaia 1.30859 d) and WASP-17 (Gaia 2.51408 d) the search found
the true periods, 1.338233 d (known 1.338231) and 3.735494 d (known 3.73543), labelled
SURVIVES_OTHER_P as registered.

## The two candidates

| | TIC 4638108 | TIC 44997521 |
|---|---|---|
| Gaia DR3 source_id | 5431056347037926784 | 5432318139709900160 |
| TESS sectors used (all available) | 6 (8, 9, 35, 62, 89, 99; QLP) | 7 (9, 35, 36, 62, 63, 89, 99; QLP) |
| Gaia P / TESS P (d) | 2.20863 / **2.20828** (0.016% apart) | 3.54975 / **3.54941** (0.009% apart) |
| combined S/N | 99.5 | 20.2 |
| depth TESS (2-h box) / Gaia | 1.41% / 1.57% (ratio 0.89) | 2.04% / 2.22% (ratio 0.92) |
| odd vs even | 1.415% vs 1.398%, z = 0.59 | 1.94% vs 2.15%, z = 1.00 |
| depth half a period later | 507 +/- 145 ppm (3.6% of primary; rule needs >= 10%) | 420 +/- 950 ppm |
| per-sector depths | 1.09-1.52%, chi2 p = 2e-23 (DEPTH_VARIES note) | 1.60-2.33%, p = 0.53 |
| sectors whose own best period agrees | 4 of 6 | 3 of 7 (per-sector S/N 9-11) |
| star radius / companion radius | 1.44 Rsun / 1.66 R_Jup | 0.71 Rsun / 0.99 R_Jup |
| ExoFOP TOI / CTOI / files (25 Nov 01:00 UTC) | none / none / 0 | none / none / 0 |

DEPTH_VARIES is a note, not a flag: two of the three known-planet controls carry it too (WASP-4
p = 6e-7, HATS-52 p = 1e-15), because QLP and SPOC correct each sector's blending differently.
TIC 4638108's low value comes from sector 99 alone (1.09 +/- 0.03%); the other five sectors give
1.39-1.52%.

## Exploratory checks (this run, not pre-registered; `vpt_fu_checks.py` 0.1.0 with tests)

1. **Resolved neighbours cannot make the dip Gaia sees.** Gaia's own photometry of each target
   shows the dip at nearly the TESS depth. Gaia DR3 lists three sources within 6" of TIC 4638108
   (G 18.25 at 2.6", 20.29 at 4.9", 18.28 at 5.7"); even fully inside Gaia's window, each would
   need an eclipse 2.4, 15.8 or 2.5 times deeper than its whole light. TIC 44997521 has no Gaia
   source within 18.8". Its bright neighbour (G 10.59 at 28.2", 19 times brighter) sits inside
   the TESS aperture but far outside Gaia's window, so Gaia's 2.22% on-target depth places the
   signal on the K dwarf. Unresolved companions (< ~0.5") are not excluded. Source:
   `data/vpt-followup-v1/gaia_dr3_neighbours_45arcsec.csv` (AIP Gaia DR3 TAP, 25 Nov).
2. **Durations fit the stars.** With TIC masses and radii, a central transit would last 3.26 h
   for TIC 4638108 (a/R* = 5.82) and 2.81 h for TIC 44997521. The folds show about 2.5 h and
   2.3 h: both are consistent with a non-zero impact parameter, and TIC 4638108's V-shaped fold
   agrees with the grazing geometry noted on 21 Nov.
3. **TIC 4638108's weak signal half a period later.** 507 +/- 145 ppm (3.5 sigma) is below the
   registered EB threshold. In a monochromatic 800-nm blackbody estimate, a zero-albedo,
   no-redistribution hot Jupiter (dayside 2,657 K) would give 188 ppm of thermal emission plus at
   most 208 ppm of reflected light (geometric albedo 0.5); the observed value is 2.2 sigma above
   the thermal-only case and within 1 sigma of the sum. A self-luminous 3,100 K body of the same
   size would give about 495 ppm. So this signal does not decide planet versus low-mass star; it
   makes a stellar companion somewhat more likely for this one, together with the grazing shape
   and the 1.66 R_Jup size.

## Status and next steps

- TIC 44997521 (a hot-Jupiter-sized companion on a 0.7-0.8 Rsun K dwarf, Tmag 13.1, 280 pc) is
  the cleaner candidate: constant depth across seven sectors from 2019 to 2025, no odd/even
  difference, no secondary, and the dip is on target in Gaia's own photometry.
- Neither star has a TOI, a CTOI, or any follow-up file on ExoFOP. The proper channel is a CTOI so
  that TFOP can take radial velocities; filing one needs an ExoFOP account, which MV2 does not have
  yet. Neither is called a planet: only radial velocities can tell a hot Jupiter from a low-mass
  star or brown dwarf.
- Prior work checked 25 Nov: Panahi et al. 2022 (A&A 663, A101; arXiv:2205.10197) found TESS-FFI
  signals for 21 of their 41 candidates but published no per-star list; SIMBAD lists both stars
  only through the Gaia DR3 variability paper (Eyer et al. 2023); RAVEN (arXiv:2603.22597, TESS-SPOC
  FFIs, sectors 1-55) does not list either TIC; the Gaia variability review (arXiv:2412.02744)
  counts only Gaia-1b and Gaia-2b as confirmed.
