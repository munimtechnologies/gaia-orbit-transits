# Faint tier-2 single-lined flags: all six already listed (27 Nov 2026)

MV2, Munim, Inc. Work carried out by AI agents working in his name; not yet checked by a human expert.
Text CC BY 4.0.

## Question
Run 109 (findings/2026-11-27-sb2-ffiscan-v1-graded.md) found that bright (G < 11) edge-on Gaia DR3
double-lined eclipsers are all catalogued already. The playbook's next lead was the fainter flags of the
Gaia DR3 single-lined conjunction search (job g8-dr3-sb1-v1): flags at G 10.5-12.7 with in-window
dips shallower than 0.10 mag and no Gaia variability class. Are any of them new eclipsing binaries?

## What we checked (27 Nov 2026, 17:40-18:00 UTC)
For each star: Gaia DR3 position and orbit from the AIP TAP mirror; one VizieR (CfA mirror) cone of
30 arcsec over TESS Ten Thousand (J/ApJS/279/50), ASAS-SN variables (II/366), IJspeert et al. 2024
(J/A+A/691/A242), GCVS/NSV, Prsa et al. 2022 (J/ApJS/258/16), IJspeert et al. 2021 (J/A+A/652/A120),
VSX (B/vsx), ATLAS (J/AJ/156/241) and ZTF (J/ApJS/249/18); TIC 8.2 for the TIC id; the full
`accepted-systems.csv` of Eclipses by Appointment (main = commit 18f41dc, all four 100 kB pieces); ExoFOP.

| Gaia DR3 | TIC | G | BP-RP | P (d) | e | K1 (km/s) | already listed as |
|---|---|---|---|---|---|---|---|
| 430669156898315392 | 284210588 | 11.80 | 0.60 | 2.61372 | 0.059 | 79.1 | IJspeert+2024 OBAF EB candidate (score 2) |
| 1993895376986150272 | 417030993 | 12.46 | 0.64 | 2.88029 | 0.086 | 47.1 | IJspeert+2024 OBAF EB candidate (score 1) |
| 5607967248251092352 | 63665158 | 12.21 | 0.66 | 3.99109 | 0.054 | 47.7 | IJspeert+2024 OBAF EB candidate (score 1) |
| 6724645379272706944 | 337882244 | 11.00 | 0.50 | 6.42735 | 0.053 | 59.9 | IJspeert+2024 OBAF EB candidate (score 2) |
| 5890772462234597504 | 263425251 | 12.09 | 0.87 | 6.03788 | 0.158 | 41.6 | Eclipses by Appointment R1803 (confirmed; 24 Nov 2026 Gaia epoch review) |
| 6149942887797746560 | 135251275 | 10.96 | 0.79 | 6.10608 | 0.038 | 29.4 | Eclipses by Appointment R054 (confirmed; listed by 5 Nov 2026); VSX: ROT, 3.03679 d |

VSX lists the first five only as Gaia DR3 'VAR' with spurious periods of 21-50 minutes. None has a TOI
or CTOI. For 5890772462234597504 the IJspeert+2024 row 23.7 arcsec away is a different star
(TIC 264024979).

## Result
**0 of 6 new.** Four are TESS eclipse candidates of IJspeert et al. (2024) (all are F stars, BP-RP
< 0.7, inside that catalogue's OBAF scope); the two cooler ones are in Eclipses by Appointment. Together
with run 109 (bright double-lined stars: 0 new of 20 detections), the Gaia DR3 spectroscopic-orbit
eclipse lane is now picked clean down to G ~ 12.5 by IJspeert et al. (2021, 2024) and Eclipses by
Appointment. The remaining edge is Gaia DR4 (2 Dec 2026): new orbits, epoch photometry for every
source, speed, pre-registration and measured purity.

## Also found this run (method note)
The AIP Gaia TAP mirror returns a VOTABLE (TABLEDATA) for GET and POST alike, with FORMAT=csv or
RESPONSEFORMAT=csv; that is why jobs sb2-ffiscan-v1 (orbits) and sb2-phase-grade-v1 failed. Fixed in
runbook/sb2-phase-grade-v2/fetch_deps.py (reads CSV or VOTABLE). For DR4 day, dr4_votable.py converts
VOTABLE / BINARY2 replies to the CSV that the frozen DR4 scripts parse, without changing their rules.
