# candidate-vet-v2 graded: no claim is listed in any file of Eclipses by Appointment

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0, code Apache-2.0. Graded 26 November 2026 (~23:00 UTC) against the pre-registration
`findings/2026-11-26-candidate-vet-v2-prereg.md` (committed a5b8023 before the job ran).

Job `candidate-vet-v2` (`cand_vet.py` 0.2.0) ran on 26 Nov 15:54-16:04 UTC. It downloaded the
codeload zip of Eclipses by Appointment (github.com/Snowstar38/eclipses-by-appointment) at commit
**6699c5f** (1.95 GB, 50,117 files), read all **34,176** text files (.csv .tsv .json .md .html .txt;
none skipped for size, no read errors) and searched each for the TIC and Gaia DR3 ids of our claims,
candidates and controls as whole digit tokens. It also searched IJspeert et al. (2024) OBAF_EB.csv
(61,372 rows) by TIC. Raw output: `data/candidate-vet-v2/cand_vet2.json`.

## Grades

| label | prediction | result | held? |
|---|---|---|---|
| V0 controls | CONTROLS_OK (85%) | CONTROLS_OK: TYC 3616-2395-1 (accepted-systems A179 and 50 more files), CD-28 7251 (CHECKCARD B7, paper.html, gaia-epoch-review) and HD 171459 (CHECKCARD B6, paper.html) found; RS Cha found in OBAF_EB | yes |
| V1 scan | SCAN_COMPLETE (75%) | SCAN_COMPLETE (34,176 files, 0 skipped, 0 errors) | yes |
| V2 claims | CLAIMS_UNLISTED (70%) | CLAIMS_UNLISTED: HD 250735, BD+15 2743, HD 11239, HD 125386A (+ blend TIC 337318750), TYC 6340-23-1 in no file | yes |
| V3 single-lined candidates listed | 0 (60%) | 2 token hits (TYC 1316-1554-1, UCAC4 194-101841) | **no** |
| V4 transit candidates listed | 0 (75%) | 0 (TIC 93622019, 44997521, 4638108 in no file and not in OBAF_EB) | yes |

Four of five predictions held. ZZ Boo, the second OBAF control, was not in OBAF_EB; the rule needed
only one OBAF control.

## Reading the hits (as pre-registered: every hit file read)

- **UCAC4 194-101841** (Gaia DR3 5900468269330031744, TIC 126460696): in
  `reviews/2026-11-24-expanded-search/gaia/screened.csv` and `dispositions.csv` with disposition
  **"hold"**: "Sectors give highly inconsistent eclipse depths; only two of four difference images
  favor target. Existing Kostov Table 2 machine flag." We then checked the TESS Ten Thousand
  catalogue (Kostov et al. 2025, VizieR J/ApJS/279/50) ourselves on 26 Nov 22:48 UTC: TIC 126460696
  is in **table 2** ("identifying information for ~900,000 unvetted and unvalidated targets",
  0.12 arcsec), not in table 3 (new EBs) or 4 (known EBs). Our 26 Nov vetting had reported "no
  entry" in the TESS Ten Thousand tables for this star; that was wrong for table 2. **It is
  therefore not "listed nowhere":** a machine flag and a held screen by Eclipses by Appointment
  came first. We never claimed it as eclipsing; the Am-star draft table is corrected.
- **TYC 1316-1554-1** (Gaia DR3 3350075697770930304): one row in the same `screened.csv`, an error:
  "expected one exact Gaia TIC match, got 0". Eclipses by Appointment tried to screen it on 24 Nov
  and could not, so it lists no eclipse. Under the pre-registered rule ("a hit that only mentions a
  number in passing is read and reported, not counted") this is reported, and the star stays a
  candidate. The token count V3 = 2 stands as graded; by reading, 1 of 5 is listed.
- **TYC 3330-286-1** (TIC 428977802, weak candidate): only in two copies of a list saying
  "none of the vetted/unvetted EB tables". Not a listing.
- RS Cha's EbA hit is a field-selection row, not a listing (control for OBAF only).

## Also checked by hand (26 Nov 22:48 UTC, TESS Ten Thousand tables 2-4, 20-arcsec cones by name)

HD 250735, BD+15 2743, HD 11239, HD 125386, TYC 6340-23-1, TYC 1316-1554-1, TYC 3384-347-1,
UCAC4 544-021692, UCAC4 468-115332: **no rows**. UCAC4 194-101841 (the only hit) is the positive
control for table 2.

Eclipses by Appointment commits after 6699c5f on 26 Nov (8f279a3, 7ac8c50, f0cdcc4, 7a0445b,
7d14914, 18f41dc): the patches of 18f41dc and 7a0445b (read through the GitHub API) contain none of
our ids; 7a0445b's 2,393-row target table (G 11.5-12) had no patch text shown, and our claims are
G 8.3-10.5. Not a full re-scan.

## Consequences

- All five eclipsing-binary claims stand: HD 250735, BD+15 2743, HD 11239, HD 125386A, TYC 6340-23-1.
- UCAC4 194-101841 moves to "flagged before us (TESS Ten Thousand table 2 machine flag; Eclipses by
  Appointment hold)".
- Limits: token search finds ids only, not names; PDFs and images not read; the catalogue changes
  daily, so this holds at 6699c5f.
