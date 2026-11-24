# gaia-orbit-transits: current status (2026-11-24)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Newest (24 Nov, ~02:30 UTC): the DR4 double-lined screen gets lookups that cannot fail silently

**Amendment:** `findings/2026-11-24-g5-amendment-1.md`, code `sb2_screen_dr4.py` 0.2.0 with tests
(`test_sb2_screen_dr4.py`), pinned import of `sb2_screen.py` 0.1.0 (`runbook/g5/fetch_pinned.py`),
rehearsal job g5-lookup-rehearsal-v1 (queued).
- **Why the DR3 screen's TESS EB lookup failed on every star:** it asked the Villanova catalogue
  over http. The site answers on https; through https the control binary HIP 34208 (TIC 238162238)
  reads "In catalog? True".
- **Prior art, now checked on the live catalogue:** the Villanova TESS EB catalogue has no entry for
  CD-28 7251 (TIC 189269584), TYC 3616-2395-1 (TIC 384284045) or HD 250735 (TIC 400170926).
- 0.2.0 runs control TICs before any star. It adds the TESS EB and TESS Ten Thousand catalogues
  through two VizieR mirrors, each with a self-generated control row, and calls a star new only
  when every lookup answered. Any failed lookup makes a star "unvetted", never "new". A
  TAP_SCHEMA gate either stops the job for an adapter (missing columns) or switches to arm B
  (no binary_masses table in DR4).
- The rehearsal reruns the new lookups on the DR3 screen's own output, so it needs no ESA archive.
  Predictions: R1 LOOKUP_REPAIRED 75%; R3 LOOKUPS_DEFINITE 55%.

**Still queued (pre-registered earlier):** sb2-ebfit-v1 (masses and radii of the three new
eclipsing binaries; `findings/2026-11-23-sb2-ebfit-prereg.md`), sb2-new-ebs-timing-v1 (eclipse
times against Gaia's orbits), gaia-vpt-epochs-box-v1, tic93622019-pixel-011-v1,
gaia-vpt-followup-v1.

## Earlier (23 Nov): masses and radii pre-registered; the Gaia SB2 x TESS screen graded

- `findings/2026-11-23-sb2-ebfit-prereg.md`: an eclipse model of every TESS eclipse of CD-28 7251,
  TYC 3616-2395-1 and HD 250735, combined with Gaia DR3's K1 and K2 for absolute masses and radii.
  Controls: ZZ Boo, CW Eri, EY Cep, BK Peg. Method prior art: Rowan et al. (2023), ASAS-SN x Gaia.
- `findings/2026-11-23-sb2-screen-results.md`: 183 edge-on Gaia DR3 double-lined orbits; 66 with a
  qualifying TESS TCE (46 at half the Gaia period). **Three new bright double-lined eclipsing
  binaries with Gaia masses: HD 250735, CD-28 7251 (whose eclipses Gaia's own photometry caught)
  and TYC 3616-2395-1.** Write-up:
  https://www.munimtech.com/research/gaia-binaries-new-eclipsing-benchmarks

## Earlier entries

Full entries for 23 Nov ~10:00 UTC and before are in the git history of this file (commits
669307b and 80be2827 and earlier) and in their `findings/` files.

Published write-ups:
- https://www.munimtech.com/research/gaia-binaries-new-eclipsing-benchmarks
- https://www.munimtech.com/research/gaia-transit-periods-known-planets
- https://www.munimtech.com/research/gaia-quality-cut-low-mass-orbits
- https://www.munimtech.com/research/tyc-6340-23-1-oversized-companion
- https://www.munimtech.com/research/gaia-brown-dwarf-orbits-missing-transits

## Leads
1. **Eclipsing binaries with Gaia masses:** three new (HD 250735, CD-28 7251, TYC 3616-2395-1);
   timing and mass-radius jobs queued; Gaia DR4's SB2 list on release day (step g5, amended today).
2. **Gaia's own transit candidates in TESS** (step g): new candidate **TIC 93622019** (pixel re-run
   and Gaia-epoch test queued); the N_comp period flag is a registered out-of-sample test on DR4 (g4b).
3. **A transiting companion first found by Gaia astrometry** (step i, DR4): rehearsal passed.
4. **Do Gaia DR3 inclinations hold up against real eclipses?** 58 of 162 near-edge-on orbits
   eclipse against 80.7 expected (p = 2 × 10⁻⁵). Gaia DR4 decides.
5. **TYC 6340-23-1** (B_OVERSIZED_COMPANION): mass test on DR4 day (step a5).

## Lessons the pipeline now encodes (newest first; full list in commit a34b7885)
- **When a lookup fails on every star, try the obvious first: the scheme (http vs https).**
- **A failed lookup is not a negative answer, even when the rule says so.** Control rows first;
  "unknown" stays unknown.
- **Recompute a pilot with the registered formula before predicting replication.**
- **A survey that resolves what TESS blends settles "which star" for free.**
- **Pair every empty answer with a control query**, and run the controls first.
- **Put a self-test in every job and make it run first.**

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API at vsx.aavso.org, or its VizieR copy B/vsx), the live Villanova TESS EB catalogue
(https://tessebs.villanova.edu/), the TESS EB catalogue (Prša et al. 2022; VizieR J/ApJS/258/16),
the TESS Ten Thousand catalogue (Kostov et al. 2025; J/ApJS/279/50), IJspeert et al. 2021 OBA EBs
(J/A+A/652/A120), Gaia DR3 vari_eclipsing_binary, vari_classifier_result and binary_masses (method
Eclipsing+SB2), the ZTF and ASAS-SN variable catalogues (II/366/catv2021), Rowan et al. (2023),
DEBCat, ExoFOP, the SPOC TCE list, SIMBAD (Harvard mirror), Kepler KOIs, and Gaia DR3
nss_two_body_orbit.

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** Jobs that still need DR3 tables fall back to the Heidelberg DR3 mirror;
  DR3 epoch photometry falls back to ESA's bulk CDN files, and the 214 transit candidates' epochs
  are in the repo.
- Release-day runbook: `runbook/dr4-release-day.md` plus `runbook/dr4-addendum.md` (steps g4b and
  g5, the pixel step, step i pinned) plus `findings/2026-11-24-g5-amendment-1.md` (g5 runs
  `sb2_screen_dr4.py` 0.2.0 with `--schema gaiadr4`).
