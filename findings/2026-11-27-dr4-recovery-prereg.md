# Pre-registration: does Gaia DR4's own eclipse search recover the eclipsing binaries we found first in DR3?

MV2, Munim, Inc. Written 27 November 2026, ~18:40 UTC, five days **before** Gaia DR4 is released
(2 December 2026, 12:00 CET). Made with AI agents working in his name; not yet checked by a human
expert. Text CC BY 4.0. Repository: https://github.com/munimtechnologies/gaia-orbit-transits

## Why this test

From Gaia DR3 alone (its spectroscopic orbits plus its own epoch photometry at the orbit's conjunction
times), and confirmed in TESS or ASAS-3, we reported eclipsing binaries that no catalogue, paper or open
project we could reach listed (findings of 20-27 Nov 2026). Gaia DR4 will publish, among other things
(ESA DR4 contents page, https://www.cosmos.esa.int/web/gaia/dr4, read 27 Nov 2026):

- `vari_eclipsing_binary`: 2,392,500 rows (DR3: 2,184,477), from 66 months of photometry instead of 34;
- `nss_two_body_orbit`: 5,901,111 rows, "astrometric binaries, spectroscopic binaries, eclipsing binaries
  and certain combinations thereof";
- `nss_masses`: 4,323,300 rows of masses derived from the orbital solutions;
- two papers on "The second Gaia catalogue of eclipsing binary candidates" (geometric and astrophysical
  modelling; https://www.cosmos.esa.int/web/gaia/dr4-papers).

So DR4 is an independent, later test of our DR3 claims. If Gaia's own pipeline lists them, that confirms
them from a different method (period search in photometry, versus our orbit-timed epochs) and shows our
method found them years of data earlier. If it misses them, that measures what a timing-based search
adds to a period search. Either result is informative, and it can only be frozen now, before the data
exist.

## Stars (frozen list)

| # | star | TIC | Gaia DR3 | Gaia orbit P (d) | status before DR4 |
|---|---|---|---|---|---|
| 1 | HD 250735 | 400170926 | (see findings/2026-11-26-sb2-ebfit-v1-results.md) | 5.89594 | SB2, eclipses in TESS, masses 1.115/1.025 |
| 2 | BD+15 2743 | 119613818 | (see findings/2026-11-27-sb2-ebfit-v2-graded.md) | 2.06722 | SB2, eclipses in TESS, masses 0.918/0.824 |
| 3 | HD 11239 | 115321276 | 4961129715887496320 | 3.1208264 | SB2, eclipses in TESS and ASAS-3 |
| 4 | HD 125386A | 1021067547 | 5854558019550047872 | 3.6734169 | SB1, eclipses in ASAS-3 (18 of 22) |
| 5 | TYC 6340-23-1 | 71945261 | 6853008555751131648 | 2.32893 | SB1, eclipses in TESS sector 92 |
| 6 | TYC 3614-1907-1 | - | (findings/2026-11-27-sb1-tier2-prereg.md) | (same file) | tier-2 candidate, TESS test queued |
| 7 | BD+12 3880 | - | (findings/2026-11-27-sb1-tier2-prereg.md) | (same file) | tier-2 candidate, TESS test queued |

DR4 identifiers: the DR3 source_id where DR4 keeps it, otherwise the match in `gaiadr4.dr3_neighbourhood`
(source_id, dr3_source_id) with the smallest angular distance.

## Measurements on DR4 day (frozen)

For each star:
- **R1** in `gaiadr4.vari_eclipsing_binary`? (yes / no)
- **R2** if R1: does its period equal the Gaia DR3 orbit period, or 2x or 1/2 of it, to 0.1% relative?
- **R3** does `gaiadr4.nss_two_body_orbit` give it a solution whose type contains "Eclipsing"
  (combined eclipsing + spectroscopic, as DR3's EclipsingSpectro)? (yes / no)
- **R4** has `gaiadr4.nss_masses` a row for it, and if R3 holds, are any component masses within 3 sigma
  of ours (stars 1 and 2 only)?

## Predictions (frozen, with our probabilities)

- **P1** At least 3 of stars 1-5 are in DR4 `vari_eclipsing_binary` (R1). Probability 50%.
  Reasoning: DR3's catalogue missed all five with 34 months of data; DR4 doubles the epochs but its
  catalogue grows only ~10% in size, and our stars' eclipses are short (a few percent of the orbit).
- **P2** Every star with R1 = yes also passes R2. Probability 85% (a wrong-period listing would be a
  finding in itself).
- **P3** At least 1 of stars 1-3 (the double-lined ones) gets a combined eclipsing + spectroscopic
  solution (R3). Probability 40%.
- **P4** For stars 1-2, if R3 and R4 hold, both of Gaia's masses agree with ours within 3 sigma.
  Probability 70% conditional on R3/R4.
- **P5** Neither tier-2 candidate (stars 6, 7) is in DR4 `vari_eclipsing_binary` unless its TESS test
  (sb1-tier2-tess-v1) passes first. Recorded as a check of consistency, probability 75%.

## Grading and reporting

Graded from one TAP query per table on DR4 day (or as soon as the ESA archive or a DR4 data centre such
as AIP serves gaiadr4), before any other DR4 analysis of these stars. All answers, including "no",
go into findings/<date>-dr4-recovery-graded.md. Any star DR4 lists is then credited to Gaia DR4 in
every later text, and our claim is reworded to "found from DR3 before DR4's catalogue" with dates.
