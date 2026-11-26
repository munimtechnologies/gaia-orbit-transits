# Step g5 rehearsal on DR3 graded (job g5-lookup-rehearsal-v1)

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0. Graded by hand on 26 November 2026 (~15:45 UTC) from
`data/g5-lookup-rehearsal-v1/g5_rehearsal_summary.json` and `g5_rehearsal_rows.csv` (job ran on the
Dell, 26 Nov 13:25-13:45 UTC), against the predictions in `findings/2026-11-24-g5-amendment-1.md`,
which were fixed before the job ran.

## Grades

| prediction (probability) | result | grade |
|---|---|---|
| unit tests and self-test pass (80%) | both steps exit 0 | PASS |
| Villanova controls pass (80%) | TIC 238162238 True, TIC 189269584 False | PASS |
| R1 LOOKUP_REPAIRED (75%) | 8 of 8 hand-vetted stars agree | PASS |
| at least one VizieR catalogue passes its control (65%) | both (J/ApJS/258/16 and J/ApJS/279/50, cone mode, no error) | PASS |
| R3 LOOKUPS_DEFINITE (55%) | 331 of 336 answers definite (0.985) | PASS |
| NEW_V2 is exactly HD 144359, CD-28 7251, HD 250735, BD+37 3347, TYC 3616-2395-1 (50%) | exactly these five (TIC 17342647, 189269584, 400170926, 121083955, 384284045); KNOWN 51 | PASS |
| none of the three discoveries comes out KNOWN (90%) | none does | PASS |

All seven predictions held. The DR4 schema gate could not be rehearsed: ESA's Gaia archive is closed
until DR4, and reading TAP_SCHEMA failed with a CSV "field larger than field limit (131072)" error
(the archive's reply was not a table). The gate stays untested until release day.

## What the rehearsal shows that the grades do not

The lookups now work, but the lookup set is not enough. Two of the five NEW_V2 stars were already
listed by the open Eclipses by Appointment catalogue: TYC 3616-2395-1 (accepted-systems row A179,
31 October) and CD-28 7251 (observing card `CHECKCARD.csv` row B7, 19 October; see
`findings/2026-11-26-eba-checkcard-correction.md`). The seventh prediction passed only because none
of the six automatic lookups reads that catalogue. NEW_V2 therefore means "a candidate for hand
vetting", never "new", and on DR4 day every NEW_V2 star must also be searched for by TIC and Gaia
source_id in every text file of Eclipses by Appointment (`cand_vet.py` 0.2.0 does this) before it
is called new.

## Limits

The rehearsal reuses the DR3 run's VSX, SIMBAD and TOI answers, so it tests only the new lookups. A
positive control proves a lookup worked when it ran. The schema gate and arm B are untested.
