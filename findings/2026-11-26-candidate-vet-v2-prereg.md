# Pre-registration: candidate-vet-v2, every file of Eclipses by Appointment for all our claims

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0, code Apache-2.0. Written 26 November 2026 (~16:00 UTC), before job
**candidate-vet-v2** (`cand_vet.py` 0.2.0, tests `test_cand_vet.py`) ran.

## Why

Twice an open AI-agent catalogue, Eclipses by Appointment (github.com/Snowstar38/eclipses-by-appointment),
had listed an eclipsing binary we then called new: TYC 3616-2395-1 in its main table, and CD-28 7251
and HD 171459 in its observing card `CHECKCARD.csv`, a file our hand vetting never opened
(`findings/2026-11-26-eba-checkcard-correction.md`). Hand reads of single files cannot rule this out
for our other claims. This job reads every text file of the catalogue's HEAD commit (.csv .tsv .json
.md .html .txt, from one codeload zip) and searches each for every TIC and Gaia DR3 source_id below,
as whole digit tokens. It also searches IJspeert et al. (2024) OBAF_EB.csv (Zenodo 20123193) by TIC.

## Targets

- Claims: HD 250735, BD+15 2743, HD 11239 (double-lined), HD 125386A (+ blend TIC 337318750),
  TYC 6340-23-1.
- Candidates: TYC 3330-286-1; transit candidates TIC 93622019, 44997521, 4638108; single-lined
  eclipse candidates TYC 1316-1554-1, TYC 3384-347-1, UCAC4 544-021692, UCAC4 468-115332,
  UCAC4 194-101841 (by Gaia id only).
- Controls that must be found: TYC 3616-2395-1 (TIC 384284045), CD-28 7251 (TIC 189269584),
  HD 171459 (TIC 464315748) in Eclipses by Appointment; RS Cha or ZZ Boo in OBAF_EB.

## Labels and predictions (fixed now)

| label | rule | prediction |
|---|---|---|
| V0 | all three catalogue controls found and one OBAF control found: CONTROLS_OK, else CONTROL_FAIL (then no "not found" counts) | CONTROLS_OK, 85% |
| V1 | every text file read without error, none skipped for size: SCAN_COMPLETE | SCAN_COMPLETE, 75% |
| V2 | none of the six claim tokens found: CLAIMS_UNLISTED, else CLAIM_LISTED | CLAIMS_UNLISTED, 70% |
| V3 | single-lined candidates found in the catalogue (count) | 0, 60%; at least 1, 40% |
| V4 | transit candidates found in either source (count) | 0, 75% |

## What we do with the result

- Any claim found (V2 = CLAIM_LISTED): we read the hit file. If it lists the star as eclipsing before
  our first report, the affected article is corrected under its own slug before anything else is
  published, and the finding files say so.
- A candidate found: it is dropped from our "listed nowhere" table, and the article that mentions it
  is updated.
- A hit that only mentions a number in passing (for example a hash or an unrelated column) is read
  and reported, not counted.

## Limits

A token search finds a star only under its TIC or Gaia DR3 id; a listing by name alone (HD, TYC, BD)
would be missed. Large binary files (PDF, PNG) are not read. The catalogue changes daily: the result
holds at the commit the job records.
