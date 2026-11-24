# Correction: TYC 3616-2395-1 was listed before us

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0. Written 2026-11-24 (~09:00 UTC).

## What we claimed

`findings/2026-11-23-sb2-screen-results.md` (23 Nov, release v0.51.0) and the article
https://www.munimtech.com/research/gaia-binaries-new-eclipsing-benchmarks called three Gaia DR3
double-lined binaries eclipsing binaries "in no catalogue we reached": HD 250735 (TIC 400170926),
CD-28 7251 (TIC 189269584) and TYC 3616-2395-1 (TIC 384284045).

## What we found today

A prior-work search for a new thread (24 Nov) found the open GitHub catalogue
**Eclipses by Appointment** (https://github.com/Snowstar38/eclipses-by-appointment). It lists eclipsing
systems found by folding TESS light curves at the periods of Gaia DR3 spectroscopic orbits and by
looking at Gaia-predicted conjunction times. Its README says AI agents made the work and that the
manuscript is under review.

- `overview/systems.csv` contains the row `A179,384284045,confirmed,327.54606,51.80023,true,objects.csv`.
- The same row is already present at commit **36313ad** (2026-10-31 19:36 UTC):
  https://raw.githubusercontent.com/Snowstar38/eclipses-by-appointment/36313ad/overview/systems.csv
- `accepted-systems.csv` (main branch, 24 Nov) lists A179 = TIC 384284045 as "confirmed".

So **TYC 3616-2395-1 had been publicly listed as an eclipsing system at least 23 days before our
claim.** Our claim that it is new is withdrawn. Our own measurements of it (Gaia SB2 orbit x TESS
eclipses at P/2, M sin³i 1.05 and 1.12 M_sun) still stand, and it stays in the queued eclipse-timing and
mass-radius jobs as one of the systems being measured.

## The other two

We searched all of `accepted-systems.csv` (369,313 characters, read in four parts) for
TIC 400170926 and TIC 189269584: **neither is listed.** A web search on 24 Nov for each name
("HD 250735", "CD-28 7251", "TIC 189269584", "TYC 6600-985-1") found only our own pages. HD 250735 and
CD-28 7251 remain eclipsing binaries we found in no catalogue.

## Why our vetting missed it

On 22-23 Nov we checked VSX, the TESS EB catalogue (Prša et al. 2022), TESS Ten Thousand,
IJspeert et al. 2021, ASAS-SN, SIMBAD, ExoFOP and a web search. Open GitHub catalogues made by other
AI-agent projects were not on that list. They are now: every future "new" claim in this project is
checked against Eclipses by Appointment's `accepted-systems.csv` and the Chopard-Vilhem Zenodo deposit
(doi:10.5281/zenodo.23342416) before it is published.
