# sb2-ffiscan-v1 graded: no new eclipsing binary among Gaia's bright edge-on double-lined binaries

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0, code Apache-2.0. Written 2026-11-27 (~16:30 UTC).
Pre-registration: `findings/2026-11-24-sb2-ffiscan-prereg.md` (code `sb2_ffiscan.py` 0.1.0, tag v0.57.0).
Job output (unchanged): `data/sb2-ffiscan-v1/` (ffiscan_summary.json, ffiscan_stars.csv/.jsonl,
ffiscan_folds.csv, job_summary.json). Ran on 27 Nov 14:17-15:16 UTC (Dell, 0.25 GB peak).

## What happened

The light-curve part ran to completion on all 161 stars (not truncated). Unit tests and the in-run
self-test passed on the first run. But the job **could not download a single Gaia orbit**: the ESA
archive is closed until Gaia DR4 (its error page broke the CSV reader), and the AIP Potsdam mirror
answered the job's POST with a VOTABLE instead of CSV. So every conjunction-time test is UNTESTABLE.
That is a download failure, not a result.

## Grades as the frozen code wrote them

| test | prediction | outcome |
|---|---|---|
| self-test PASS on the first run | 65% | **held** |
| F0 controls: >= 80% of catalogued EBs DETECTED | 75% | **held: 82 of 86 (95%)** |
| F1 Gaia conjunction times on controls | 60% OK | **untestable in v1** (no orbits) -> job sb2-phase-grade-v1 |
| F2 >= 1 / >= 3 candidates before hand vetting | 70% / 40% | 0 as coded (needs PHASE_MATCH; untestable) |
| F3 HD 250735 and CD-28 7251 DETECTED + PHASE_MATCH | 75% | both DETECTED; phase untestable in v1 |
| >= 1 candidate survives hand vetting as new | 45% | **failed (0)**, see below |

Noise: 148 of 160 stars with data have a best null S/N above 10, so the 1.5 x null rule, not the
S/N >= 10 floor, is what decides detection. 42 of 62 targets with data were NOT_DETECTED.

## Completing F2 by hand (not blind; labelled as such)

20 targets (not hand-vetted before) were DETECTED at Gaia's period. Their dip times are in
`ffiscan_stars.csv` (T_dip1, BTJD). We fetched their Gaia DR3 orbits from the AIP mirror by GET on
27 Nov and computed the conjunctions by hand (nu + omega = 90/270 deg; circular SB2C solutions at
phases 0.25/0.75, as pre-registered), with a sigma from P, T_peri and omega errors plus a quarter box
width. These hand numbers are approximate; job sb2-phase-grade-v1 recomputes them with the frozen
0.1.0 Monte Carlo. Then every star was looked up by coordinates (30") in VizieR (CfA mirror: VSX,
GCVS/NSV, ASAS-SN II/366, ATLAS J/AJ/156/241, ZTF J/ApJS/249/18, Prsa et al. 2022, IJspeert et al.
2021 and 2024, TESS Ten Thousand tables 2-4), in Gaia DR3 vari_eclipsing_binary (AIP; none of the
13 below is in it), and in the whole `accepted-systems.csv` of Eclipses by Appointment (commit
18f41dc, read in four pieces).

| Gaia DR3 | TIC | G | P (d) | Gaia sol. | TESS depth | hand O-C (d) | hand z | listed as eclipsing before us |
|---|---|---|---|---|---|---|---|---|
| 6370053605166404992 (HIP 104391) | 311430361 | 7.80 | 2.22995 | SB2 | 4.9% | -0.03 | -0.2 | IJspeert+2024 EB list (score 2) |
| 4558912591329144064 | 143009538 | 7.85 | 6.92649 | | 4.5% | | | VSX V0920 Her (EA) |
| 261894152090105088 (HIP 25316) | 309682332 | 8.18 | 7.18861 | | 17.6% | | | VSX (E) |
| 2186746353538849408 | 276477308 | 8.47 | 5.22337 | SB2C | 1.6% | -0.009 | -0.1 | IJspeert+2021 eb-cat (P 5.22299), +2024 |
| 418728701136352000 | 452997239 | 8.98 | 1.96754 | SB2, e 0.225 | 8.6% | -0.038 | -0.6 | IJspeert+2021 eb-cat (P 1.96756), +2024 |
| 5697475844169557248 | 153514323 | 9.07 | 7.28360 | | 8.4% | | | VSX V0587 Pup (EA) |
| 1226781889693185408 | 310396365 | 9.26 | 2.02448 | SB2, e 0.081 | 6.0% | +0.060 | +0.9 | IJspeert+2024 (score 2) |
| 1584571769464585856 | 157332634 | 9.66 | 4.37433 | SB2 | 6.2% | +0.055 | +0.2 | IJspeert+2024 (score 4) |
| 6374372070227419008 | 371839648 | 9.91 | 4.56693 | SB2C | 4.8% | -0.038 | -0.5 | IJspeert+2024 (score 4); VSX ACV (Gaia class) |
| 5642018474833614464 | 185806911 | 9.98 | 3.15990 | | 10.7% | | | VSX ASAS J084309-3011.6 (ED) |
| 1993111257691035904 | 26804032 | 10.05 | 7.21975 | SB2, e 0.316 | 9.7% | +0.098 | +1.4 | Eclipses by Appointment R131 (confirmed) |
| 5597873804538618496 | 153734545 | 10.09 | 6.43790 | SB2 | 1.6% | +0.12 | +0.3 | IJspeert+2024 (score 4) |
| 3443821674062259328 | 309334280 | 10.18 | 5.91795 | SB2C | 12.1% | -0.028 | -0.1 | IJspeert+2024 (score 4) |
| 2599211025245327232 | 12653017 | 10.20 | 6.71999 | | 20.8% | | | VSX BW Aqr (EA) |
| 2825104215999846144 | 243126121 | 10.38 | 2.44592 | SB2, e 0.068 | 4.5% | **-0.45** | **-5.7** | none found |
| 510467347154606592 | 444617279 | 10.52 | 4.26674 | SB2 | 2.2% | +0.031 | +0.1 | IJspeert+2024 (score 2) |
| 4322674031257647744 | 339787086 | 10.78 | 3.77898 | SB2 + 281-d astrometric orbit | 2.4% | +0.22 | +0.8 | Eclipses by Appointment R012 (confirmed) |
| 5871568499564025472 | 453601725 | 10.88 | 5.56674 | SB2 | 2.2% | -0.05 | -0.1 | Eclipses by Appointment A204 (confirmed); VSX ROT |
| 555108687465591040 | 137328861 | 10.94 | 6.33428 | | 18.1% | | | VSX V1176 Cas (EA) |
| 657205695088834560 | 82329624 | 11.17 | 4.36397 | | 18.0% | | | VSX NSVS 10094199 (EA) |

(Hand timing was computed only for the 13 that VSX does not list as eclipsing.)

**Result: 0 new.** 19 of the 20 detections are eclipsing binaries listed before us (7 in VSX, 9 only
in the IJspeert et al. TESS OBA/OBAF eclipsing-binary lists, 3 only in Eclipses by Appointment). The
one star nobody lists, Gaia DR3 2825104215999846144 (TIC 243126121), dips at Gaia's period but about
0.45 d (0.18 of an orbit) away from both of Gaia's conjunctions, and its two dips are 0.495 of an
orbit apart where Gaia's e and omega predict 0.479. By the frozen rule it is PHASE_MISMATCH, so it is
not a candidate. Possible causes (not tested): a wrong Gaia periastron time, or a blended eclipsing
neighbour at the same period (TIC 243126124, Tmag 12.4, is 27" away). Gaia DR4's orbit and epoch
photometry can decide.

Two physical checks came out clean where the test is sharp: for the eccentric 418728701136352000
(e = 0.225) Gaia predicts the secondary 0.621 of an orbit after the primary and TESS shows 0.620;
for 1993111257691035904 (e = 0.316) TESS sees one eclipse, at the conjunction near periastron where
the stars are 1.9 times closer than at the other conjunction.

## What this means

The pre-registered bet that bright (G 7.8-11.5) edge-on Gaia SB2s still hide unlisted eclipsing
binaries failed: among those with TESS data, every detected one that keeps Gaia's timing is already
catalogued, mostly by IJspeert et al.'s automated TESS searches of hot stars and by the open Eclipses
by Appointment catalogue. Our earlier finds in this sample (HD 250735, BD+15 2743, HD 11239) came
from stars these lists missed for specific reasons; this scan shows such gaps are now rare at G < 11.
For Gaia DR4 the new-find space is fainter stars and the new orbits themselves.

## Next

Job **sb2-phase-grade-v1** (`sb2_phase_grade.py` 0.1.0 + `fetch_deps.py`, 0.5 GB) applies the
frozen 0.1.0 conjunction test to v1's stored dip times with orbits fetched by GET, unchanged except
that it keeps every Gaia solution of a source and uses the one whose period anchors (v1 kept only
the last row). It grades F1 on the 82 detected controls, which we have NOT computed by hand, so F1
stays blind. Predictions (from the 24 Nov registration): GAIA_PHASES_OK 60%; eccentric controls
match better than circular ones 50%. Added now, before the job: SEP_MATCH for >= 80% of eccentric
controls with a secondary, 45%.
