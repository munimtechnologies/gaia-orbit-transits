# Results: blind Gaia DR3 run of rule g8 on every short-period single-lined orbit with epoch photometry

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked it yet.
Text CC BY 4.0; code Apache-2.0. Graded 2026-11-26 against the pre-registration
findings/2026-11-25-g8-dr3-sb1-prereg.md (written before the run; rule frozen at commit af65d7b).
Job `g8-dr3-sb1-v1` (g8_dr3_sb1.py 0.1.0) ran on the Blade on 26 Nov 2026, 09:44-10:39 UTC; all
five steps exited 0; no star missing. Outputs: data/g8-dr3-sb1-v1/ (run_stdout.txt with the full
summary, g8_dr3_sb1_flagged.csv, g8_dr3_sb1_new_candidates.csv, hand_vetting.csv, and the Gaia
epochs of the six stars listed nowhere).

## Sample
7,978 Gaia DR3 SB1/SB1C orbits, 0.4-15 d, with epoch photometry (matches the pre-registered
7,978). 7,974 classified (4 with too few epochs). 2,156 are Gaia-known eclipsing, 5,818 are not.

## Automatic predictions (job output, unchanged)
| # | Prediction | Threshold | Result | Grade |
|---|---|---|---|---|
| P1 | Share of Gaia-known eclipsing stars flagged | >= 0.25 | 905 / 2,156 = 0.420 | TRUE |
| P2 | Null (quarter-orbit-shifted) flags / classified stars | <= 0.02 | 48 / 7,974 = 0.0060 | TRUE |
| P3 | Median abs(dphase) of in-window dips of ECL_GAIA stars | <= 0.015 | 0.0131 (4,429 dips) | TRUE |
| P4 | New candidates (ECL_GAIA, not Gaia-known) | >= 30 | 111 | TRUE |
| P6 | Deepest in-window dip at conjunction 0 (visible star behind) | share >= 0.65, n >= 20 | 849 / 967 = 0.878 | TRUE |

Labels: 967 ECL_GAIA, 73 ECL_GAIA_SHALLOW, 6,934 NONE with the real conjunctions, against 33, 15
and 7,926 with the conjunctions moved by a quarter orbit. Among the 5,818 stars Gaia does not call
eclipsing, the real run flags 111 (+24 shallow) and the null run 36, so about a third of the 111
are expected to be false flags (pre-registered purity estimate 0.32). Among the 111 new
candidates, P6's share is 0.775 (86 of 111). Gaia variability class of the 111: none 59, LPV 12,
RS 11, DSCT|GDOR|SXPHE 9, SOLAR_LIKE 8, ACV/CP 7, YSO 4, RR 1.

P6 is the physics check: in a single-lined binary the star whose lines Gaia measured dominates the
light, so its eclipse (when it is behind its companion) should be the deeper one. 88% of all
flagged stars obey it, without the rule knowing which conjunction is which.

## P5: hand vetting of the 10 deepest new candidates (graded 26 Nov, 11:30-12:10 UTC)
Pre-registered: at least half of the 10 deepest are listed in none of VSX, SIMBAD, Prsa 2022,
IJspeert 2024, TESS Ten Thousand, Eclipses by Appointment and a web search.
**Result: 0 of 10. P5 is FALSE.** All 10 are in VSX. Six of them are red giants that VSX lists as
long-period pulsators (a Mira, carbon stars, SR variables: V982 Sgr, Kiso C7-129,
IRAS 02205+5143, DZ Lib, IRAS 06548-6741, C* 196); their 0.4-1.9 mag "dips" are pulsation, their
short Gaia SB1 orbits are probably spurious, and the rule's flags for them are false. This was
the failure mode the pre-registration warned about (pulsator classes are a warning sign). Two are
known eclipsing binaries at Gaia's period (ASASSN-V J204246.03+412823.5, NSVS 3667300), one is
listed as rotational (UCAC4 445-001143, ROT 4.905 d) and one as a YSO (ATO J329.3876+53.4434).

## Wider vetting: the next 36 (every new flag deeper than 0.10 mag with no Gaia variability class)
Sources, each queried by coordinates: VSX API (36 arcsec); VizieR CfA cones (5 arcsec; 30 for the
first six) of Prsa 2022, IJspeert 2021 and 2024 (ECLIPSR scores read for every match), TESS Ten
Thousand tables 2-4; Eclipses by Appointment accepted-systems.csv (main at 6699c5f, 26 Nov 08:50
UTC, rows A1-R1867, read in four parts and searched by RA and then by Dec); for survivors, VizieR
CfA cones of ASAS-SN variables (II/366), ZTF periodic variables (J/ApJS/249/18), ATLAS
(J/AJ/156/241), ACVS (II/264) and GCVS/NSV, ExoFOP and a web search. Control: V1229 Tau (SIMBAD).
SIMBAD lists 45 of the 46 only as SB*, LP*, C* or similar, so it does not decide novelty.

| Outcome (46 vetted) | Stars |
|---|---|
| Known eclipsing in VSX (EA/ED) | 12, all at Gaia's period (10 at P, 1 at P/2, 1 at P/4) |
| Known eclipsing in IJspeert et al. 2024 only (ECLIPSR score 1 in each listed dataset) | 6, all within 0.1% of Gaia's P (one dataset at 2P) |
| Known eclipsing in Eclipses by Appointment only | 13 |
| Listed as another variable type (LPV/Mira/SR 6, DSCT 1, ROT 1, YSO 1) | 9 |
| **Listed as eclipsing nowhere we reached** | **6** |

So, of the 37 flags that are not pulsators or other variable types, **31 are independently known
eclipsing binaries (84%)** and none is contradicted; where a catalogue period exists (18 stars) it
matches Gaia's period or a simple fraction of it. The open AI-agent project Eclipses by Appointment,
which folds TESS at Gaia orbit periods, already lists 13 of these 46 (including 3 of the 4 that appear
in TESS Ten Thousand's unvetted table 2), so for this kind of star it got there first.

The six listed nowhere:

| Gaia DR3 | Name | G | P (d) | K1 (km/s) | f(m) (Msun) | Gaia dips (events) | Note |
|---|---|---|---|---|---|---|---|
| 5854558019550047872 | **HD 125386A** (Am star) | 9.49 | 3.67342 | 48.5 | 0.043 | 4 (4) | **confirmed in ASAS-3, 18 of 22 faint points at Gaia's conjunction 0, p = 1.8e-8** (findings/2026-11-26-hd125386a-asas3.md) |
| 3350075697770930304 | TYC 1316-1554-1 | 10.58 | 1.62628 | 95.2 | 0.144 | 5 (5) | ASAS-3 check next (Dec +17.7) |
| 968093290740779008 | TYC 3384-347-1 | 11.47 | 4.00116 | 73.3 | 0.163 | 4 (4) | Dec +50: north of ASAS-3 |
| 3350386649103238016 | UCAC4 544-021692 | 12.20 | 7.24728 | 61.2 | 0.172 | 2 (2) | ATLAS lists it as 'dubious' |
| 4289848214689460736 | UCAC4 468-115332 | 12.12 | 5.35928 | 68.2 | 0.133 | 3 (2) | e = 0.41 |
| 5900468269330031744 | UCAC4 194-101841 | 12.62 | 8.27375 | 53.7 | 0.110 | 2 (2), 1 out of window | in TESS 10K unvetted table 2 only |

## What this shows
1. **The method works on single-lined orbits too.** Gaia's own sparse epochs, timed by Gaia's own
   velocity orbits, flag 42% of Gaia's eclipsing SB1s and 111 that Gaia's eclipse tables miss,
   with a 0.6% null rate, and the deeper dip sits where physics says it should in 88% of cases.
2. **Pulsating red giants are the main contaminant** and must be removed (Gaia class LPV, red
   colour, large scatter) before ranking by depth. For DR4 we will rank only flags with no
   pulsator class, as was done for the 36.
3. **Few are new in DR3**: ground surveys, TESS catalogues and an open AI-agent project already
   list most bright, deep eclipsers. HD 125386A, an Am star at G = 9.5, is the clear exception and is
   now confirmed by a second instrument a decade earlier. The other 65 shallower or pulsator-class
   new flags are not yet vetted.

## Limits
- P5 failed; the ranking by single-epoch depth put pulsators first.
- Work carried out with AI agents; no human expert has checked it.
- "Known" uses catalogues reachable on 26 Nov 2026; the Eclipses by Appointment search was by
  coordinate prefixes read through a text tool, so a miss is possible.
- Gaia samples each eclipse once; depths are single-epoch values.
