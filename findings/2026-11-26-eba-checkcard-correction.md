# Correction: CD-28 7251 and HD 171459 were listed before us

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0. Written 26 November 2026, ~15:40 UTC.

## What we claimed

From 23 November, our article "Gaia's double-lined binaries hide new eclipsing benchmark stars"
(https://www.munimtech.com/research/gaia-binaries-new-eclipsing-benchmarks) and the findings in this
repository called four bright double-lined eclipsing binaries new: HD 250735, CD-28 7251,
BD+15 2743 and HD 171459. The 26 November blind-search results
(`findings/2026-11-26-g8-dr3-blind-results.md`, `data/g8-dr3-blind-v1/hand_vetting.csv`) counted
CD-28 7251 as "found by us earlier" and HD 171459 as "MV2's own earlier find".

## What we found today

The open AI-agent catalogue **Eclipses by Appointment** (https://github.com/Snowstar38/eclipses-by-appointment)
keeps an observing card, `CHECKCARD.csv`, separate from its main `accepted-systems.csv` table. Our
earlier vetting read only the main table. The card was committed on **19 October 2026** (commit
`095c08d`, "CHECKCARD at 190 rows, with a computed_UTC stamp in every row", 2026-10-19T23:42:30Z)
and lists, among its twelve "B" rows (catalogue corrections):

| EbA row | TIC | Star | EbA period (d) | EbA note (verbatim) | computed_UTC |
|---|---|---|---|---|---|
| B6 | 464315748 | HD 171459 | 6.3955 | correction (VSX DSCT\|GDOR 3.19721 d is the eclipse spacing); near-twin 12.7/13.4 ppt | 2026-10-19T23:38:40Z |
| B7 | 189269584 | CD-28 7251 | 6.9610 | correction (VSX VAR 0.0146 d); twin eclipses; contratio 1.77 | 2026-10-19T23:38:40Z |

Both periods equal Gaia DR3's spectroscopic periods (6.39561 d and 6.96109 d). So both stars were
identified as eclipsing binaries at the right period about five weeks before our first report. **We
withdraw the claim that CD-28 7251 and HD 171459 are new.** Our own measurements of them stand as
measurements: Gaia's photometry dims at the conjunctions of Gaia's own orbit (CD-28 7251: two
dips, 0.27 and 0.19 mag; HD 171459: 18 of 18 in-window epochs faint, p = 3.8e-6), which ties the
eclipses to the measured double-lined pair. That is a check of known eclipsing binaries, not a
discovery.

How we found it: job `candidate-vet-v1` (ran 25 Nov 21:55-22:30 UTC; output
`data/candidate-vet-v1/cand_vet.json`) scanned 3,070 CSV files of Eclipses by Appointment at commit
`64fbde8` and hit TIC 189269584 in `CHECKCARD.csv`. The job's verdict was not read until today. We
then read `CHECKCARD.csv` at commit `095c08d` by hand (26 Nov ~15:30 UTC) and found HD 171459 in
row B6 too (it was not among the job's targets).

## What is still unlisted (checked 26 Nov 2026, ~15:30 UTC)

HD 250735 (TIC 400170926), BD+15 2743 (TIC 119613818), HD 11239 (TIC 115321276) and HD 125386A
(TIC 1021067547, blend TIC 337318750) are in none of these Eclipses by Appointment files:
`CHECKCARD.csv` (at `095c08d`), `batch-candidates.csv`, `claim-adjudication.csv` (all 497,661
characters, rows to MIXED154-R1867), `reviews/2026-11-24-gaia-epoch-review/reviewed-stars.csv`, and
`accepted-systems.csv` (read in full 26 Nov ~12:40 and ~14:30 UTC). HD 250735 was also absent from all
3,070 CSV files the job scanned. A job that scans every text file of the catalogue for all our
claims and candidates (`candidate-vet-v2`, pre-registered in
`findings/2026-11-26-candidate-vet-v2-prereg.md`) is queued.

## Parallel work to credit

On 24 November 2026 (commit `a9e7e28`, 23:01 UTC) Eclipses by Appointment also published a search
of Gaia DR3 epoch photometry at the conjunctions of Gaia's spectroscopic orbits, with quarter-phase
and random-phase controls and TESS follow-up of 24 stars
(`reviews/2026-11-24-gaia-epoch-review/README.md`). Our first public conjunction-timed checks of
Gaia's epochs for double-lined orbits are commits `70aa7a1` (24 Nov 16:13 UTC) and `b6f2898`
(24 Nov 17:49 UTC). The two searches were developed separately; neither cites the other. Our work
differs in being pre-registered with graded predictions over every Gaia DR3 SB2 (927) and SB1 (7,978)
orbit, and in confirming new stars with archival ASAS-3 photometry rather than TESS.

## Corrected counts

First and wider screens: eclipsing double-lined binaries we found that no catalogue lists:
**2** (HD 250735, BD+15 2743), down from 4.

Blind search of 927 SB2 orbits, the 22 flags that Gaia's eclipsing tables do not contain
(corrects the bar chart in the article):

| where listed | stars |
|---|---|
| VSX or Prša et al. 2022 | 12 |
| IJspeert et al. 2021 or 2024 only | 7 |
| Eclipses by Appointment only | 2 |
| listed nowhere (HD 11239) | 1 |

The registered prediction "at least half of the 10 deepest flags are new" failed with **0 of 10**
new, not 1 of 10 as first reported (CD-28 7251 was the one).

Over all our eclipsing-binary claims since 19 November: TYC 3616-2395-1, CD-28 7251 and HD 171459
were listed first by Eclipses by Appointment; HD 250735, BD+15 2743, HD 11239, HD 125386A and
TYC 6340-23-1 remain unlisted in everything we could reach.

## Lesson

Vet against every file of an open catalogue, not only its main table, and read every finished vetting
job before publishing anything that depends on it.
