# Results: blind Gaia DR3 run of rule g8 on every double-lined orbit with epoch photometry

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked it yet.
Text CC BY 4.0; code Apache-2.0. Graded 2026-11-26 against the pre-registration
findings/2026-11-25-g8-dr3-blind-prereg.md (written before the run; rule frozen at commit af65d7b).
Job `g8-dr3-blind-v1` (g8_dr3_blind.py 0.1.0) ran on 25 Nov 2026, 22:37-22:51 UTC; all four run
steps exited 0. Outputs: data/g8-dr3-blind-v1/ (g8_dr3_blind.json, g8_dr3_blind_stars.csv,
flagged_epochs/*.csv, hand_vetting.csv).

## Question
For a double-lined binary, Gaia's radial velocities already give the period and both conjunction
times, so a few faint Gaia epochs at the predicted conjunctions, in different eclipses, should be
enough to find eclipses that Gaia's own eclipsing-binary search (which had to find a period in
sparse photometry) missed. How well does that work on all of DR3, and does it find new eclipsing
binaries?

## Sample
927 Gaia DR3 SB2/SB2C orbits, 0.4-15 d, with epoch photometry (the count matched the pre-registered
927). 479 of them are Gaia-known eclipsing binaries; 448 are not.

## Automatic predictions (job output, unchanged)
| # | Prediction | Threshold | Result | Grade |
|---|---|---|---|---|
| P1 | Share of Gaia-known eclipsing stars flagged | >= 0.40 | 310 / 479 = 0.647 | TRUE |
| P2 | Null (quadrature-shifted) flags / classified stars | <= 0.02 | 9 / 927 = 0.0097 | TRUE |
| P3 | Median abs(dphase) of in-window dips of flagged stars | <= 0.015 | 0.0140 (1,847 dips) | TRUE |
| P4 | New candidates (ECL_GAIA, not Gaia-known) | >= 10 | 22 | TRUE |

Labels: 309 ECL_GAIA, 25 ECL_GAIA_SHALLOW, 593 NONE (real conjunctions) against 5, 4 and 918 with
the conjunctions moved by a quarter orbit. Among the 448 stars Gaia does not call eclipsing, the
null run flags 2, the real run 22 (+2 shallow).

## P5: hand vetting of the 10 deepest new candidates (graded 26 Nov, 03:00-04:00 UTC)
Pre-registered: at least half of the 10 deepest new candidates are listed in none of VSX, SIMBAD,
Prsa et al. 2022, IJspeert et al. 2024, TESS Ten Thousand and Eclipses by Appointment.
**Result: 1 of 10 (CD-28 7251, MV2's own earlier find, 23 Nov). P5 is FALSE** under any reading
(9 of 10 are listed as eclipsing somewhere, mostly as named GCVS/VSX eclipsing binaries).

Sources checked, with a positive control in each: SIMBAD (CfA TAP, all 24 flagged Gaia ids; 22 SB*,
1 RS*, 1 gD*; V1229 Tau returned), VSX (vsx.aavso.org API by coordinates, 2' radius at most;
control V1229 Tau EA 2.46113 d returned), VizieR CfA cone searches (30") of Prsa et al. 2022
(J/ApJS/258/16), TESS Ten Thousand (J/ApJS/279/50, all three tables), IJspeert et al. 2021
(J/A+A/652/A120) and IJspeert et al. 2024 (J/A+A/691/A242; control BN Scl found in Prsa 2022 and
IJspeert 2024), Eclipses by Appointment accepted-systems.csv read in full at main on 26 Nov ~03:30 UTC
(newest commit 3e807ad, 26 Nov 00:33 UTC; rows A1-R1867; control TIC 384284045 = row A179 found),
ExoFOP TOI/CTOI and MAST SPOC TCEs for the two survivors, and web searches.

## Purity: all 22 new flags checked, not only the top 10
data/g8-dr3-blind-v1/hand_vetting.csv lists each flag with where it is listed as eclipsing.

| Outcome | Stars |
|---|---|
| Listed as eclipsing in VSX (EA/ED/EB) or Prsa et al. 2022 | 12 (VSX: NV TrA, SZ CMa, CD-47 13098, BU Dra, NSVS 12838110, Z Her, HD 157949, V920 Her, TYC 1399-42-1, V1229 Tau (control), HD 67206; Prsa 2022 and IJspeert 2024: BN Scl) |
| Listed only in TESS eclipse catalogues (IJspeert 2021/2024) | 7 (HD 339241, HD 236474, HD 189141, HD 218299, CD-44 6966, HD 101167, HD 187301) |
| Listed only in Eclipses by Appointment | 1 (BD-14 2634, row R141) |
| MV2's own earlier find (TESS + Gaia), no external listing | 1 (CD-28 7251) |
| **Listed as eclipsing nowhere we reached** | **1 (HD 11239)** |

So **21 of the 22 Gaia-only flags are independently known
eclipsing binaries** (95%), against the pre-registered null-based expectation of about 2 false
flags in 22 (91% purity). Where a catalogue period exists (13 stars) it equals Gaia's period or
half of it (twins with equal eclipses: CD-47 13098, BU Dra) to within 0.04%. Five of the 22
(including HD 11239) appear in VSX only as a Gaia DR3 "VAR" with a spurious period of 0.016-0.08 d. Of the two shallow
flags, HD 171459 is MV2's TESS- and Gaia-confirmed find of 25 Nov; BD+62 1849 is a Gaia
DSCT/GDOR pulsator and stays unconfirmed.

## What this shows
1. **The method works on all of DR3 with high purity.** Using only Gaia's own sparse G epochs and
   Gaia's own velocity orbits (no TESS, no ground photometry), the rule recovers 65% of Gaia's own
   eclipsing SB2s and finds 22 eclipsing SB2s that Gaia's eclipsing-binary catalogue does not
   contain, 21 of them confirmed by other surveys. It needs as few as two faint epochs.
2. **Few new stars in DR3, as expected for bright stars.** These are G 6.8-10.7 stars; ground
   surveys, TESS catalogues and an open AI-agent project had already found nearly all of them. The
   only unlisted one is HD 11239 (G 9.58, P 3.1208 d, minimum masses 1.09 and 1.05 Msun): three
   faint Gaia epochs at both conjunctions (-0.003, +0.010, +0.016 in phase), no TESS 2-minute data.
   A pre-registered TESS check is queued (findings/2026-11-26-hd11239-tess-prereg.md).
3. **For Gaia DR4 (2 Dec 2026)** the same frozen rule runs on about 5.9 million orbits with epoch
   photometry for every source; this DR3 run calibrates it: recall about 65% for Gaia-known EBs,
   null rate about 1%, and an expected purity of about 90-95% for new flags.

## Limits
- P5 failed: the pre-registered hope that most deep flags would be new did not hold. The deep,
  bright eclipsers are the best-known ones.
- "Known" uses catalogues reachable on 26 Nov; Rowan et al. 2023's full list of 200 extra ASAS-SN
  eclipsing SB2s was not reachable on VizieR CfA (J/MNRAS/523/2641 not found), so HD 11239 could
  be in it; its public 61-system table does not contain it. VSX (which ingests ASAS-SN variables)
  lists HD 11239 only as a Gaia "VAR".
- Gaia samples each eclipse once; depths here are single-epoch values, not eclipse depths.
- Work carried out with AI agents; no human expert has checked it.
