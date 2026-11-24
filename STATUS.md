# gaia-orbit-transits: current status (2026-11-24)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and data
CC BY 4.0. This page is newer than the long README. Where the two differ, this page holds.

## Newest (24 Nov, ~09:30 UTC): a correction, and a conjunction-gated search of the 95 unsearched binaries

**Correction:** `findings/2026-11-24-tyc3616-prior-listing.md`.
- **TYC 3616-2395-1 (TIC 384284045) is not new.** The open catalogue Eclipses by Appointment
  (https://github.com/Snowstar38/eclipses-by-appointment) listed it as an eclipsing system by
  31 October 2026 (row A179, commit 36313ad), 23 days before our claim. We withdraw the claim that it
  is new. Our measurements of it stand, and it stays in the mass-radius and timing jobs.
- **HD 250735 and CD-28 7251 are not in that catalogue** (all of `accepted-systems.csv` read on
  24 Nov) or in any other catalogue, paper or project we could reach. They remain our two new
  eclipsing binaries.
- Open AI-agent catalogues are now part of every "new" check in this project.

**Registered:** `findings/2026-11-24-sb2-ffiscan-prereg.md`, code `sb2_ffiscan.py` 0.1.0 (tests
`test_sb2_ffiscan.py`), job sb2-ffiscan-v1.
- The 23 Nov screen used only TESS pipeline detections, so 95 of the 161 edge-on Gaia DR3 double-lined
  binaries were never looked at. The new job folds every star's TESS light curves (2-minute or
  full-frame) at Gaia's own period. It then asks whether any dip falls at a conjunction time that
  Gaia's spectroscopic orbit predicts, with about 50 catalogued eclipsing binaries as controls.
- Two results: how accurate Gaia's conjunction times are (F1), and new candidates (F2), each
  checked by hand before being called new.

## Earlier (24 Nov, ~07:30 UTC): g7's timing fallback was broken for 4 of 7 stars; fixed before DR4

`findings/2026-11-24-g7-amendment-1.md`, `data/g7-ephemerides/ephemeris_check.csv`,
`runbook/g7/targets.json`, `runbook/dr4-checklist.md`. SPOC TCEs failed as a fallback eclipse
ephemeris for 3 of 4 controls (wrong period or no convergence); controls now use published
ephemerides and the targets have rule-based fallbacks with honest errors.

## Earlier (24 Nov, ~06:30 UTC): Gaia caught HD 250735 in eclipse; per-transit velocity fits registered for DR4

- Exploratory: `findings/2026-11-24-hd250735-gaia-epochs.md`. HD 250735's two faint Gaia DR3 epochs
  both fall inside TESS-predicted eclipses (chance about 0.2%).
- Registered: `findings/2026-11-24-g7-prereg.md`, `sb2_rvfit.py` 0.1.0 (v0.56.0): on DR4 day, fit
  Gaia's per-transit double-lined velocities of the new eclipsing binaries with the eclipse timing fixed.

## Earlier (24 Nov, ~03:30-05:00 UTC): how accurate are Gaia's double-lined orbits? A test against DEBCat

`findings/2026-11-24-sb2-debcat-prereg.md` and `findings/2026-11-24-sb2-debcat-amendment-1.md`
(`sb2_debcat.py` 0.2.0, job sb2-debcat-v2; DR4 step `runbook/g6/README.md`).

**Still queued (pre-registered earlier):** sb2-debcat-v2, sb2-ebfit-v1, sb2-new-ebs-timing-v1,
g5-lookup-rehearsal-v1, gaia-vpt-epochs-box-v1, tic93622019-pixel-011-v1, gaia-vpt-followup-v1,
and now sb2-ffiscan-v1.

## Earlier (23 Nov): masses and radii pre-registered; the Gaia SB2 x TESS screen graded

- `findings/2026-11-23-sb2-ebfit-prereg.md`: an eclipse model of every TESS eclipse of CD-28 7251,
  TYC 3616-2395-1 and HD 250735, combined with Gaia DR3's K1 and K2 for absolute masses and radii.
- `findings/2026-11-23-sb2-screen-results.md`: 183 edge-on Gaia DR3 double-lined orbits; 66 with a
  qualifying TESS TCE. Two new bright double-lined eclipsing binaries with Gaia masses: HD 250735 and
  CD-28 7251 (a third, TYC 3616-2395-1, was listed before us; see the correction above). Write-up:
  https://www.munimtech.com/research/gaia-binaries-new-eclipsing-benchmarks

## Earlier entries

Full entries for 23 Nov ~10:00 UTC and before are in the git history of this file (commits
f282d09, 669307b and 80be2827 and earlier) and in their `findings/` files.

Published write-ups:
- https://www.munimtech.com/research/gaia-binaries-new-eclipsing-benchmarks
- https://www.munimtech.com/research/gaia-transit-periods-known-planets
- https://www.munimtech.com/research/gaia-quality-cut-low-mass-orbits
- https://www.munimtech.com/research/tyc-6340-23-1-oversized-companion
- https://www.munimtech.com/research/gaia-brown-dwarf-orbits-missing-transits

## Leads
1. **Eclipsing binaries with Gaia masses:** two new (HD 250735, CD-28 7251) plus TYC 3616-2395-1
   (listed earlier by others); timing and mass-radius jobs queued; the conjunction-gated light-curve
   search (sb2-ffiscan-v1) covers the 95 stars the pipeline screen could not; DR4's double-lined list
   (g5) and per-transit velocities (g7) on release day.
2. **How accurate are Gaia's dynamical masses and conjunction times?** DR3 against DEBCat
   (sb2-debcat-v2) and against TESS eclipse times (sb2-ffiscan-v1 F1), then DR4 (step g6).
3. **Gaia's own transit candidates in TESS** (step g): new candidate **TIC 93622019**; the N_comp
   period flag is a registered out-of-sample test on DR4 (g4b).
4. **A transiting companion first found by Gaia astrometry** (step i, DR4): rehearsal passed.
5. **Do Gaia DR3 inclinations hold up against real eclipses?** 58 of 162 near-edge-on orbits
   eclipse against 80.7 expected (p = 2 × 10⁻⁵). Gaia DR4 decides.

## Lessons the pipeline now encodes (newest first; full list in commit a34b7885)
- **"In no catalogue" must include open project catalogues** (GitHub, Zenodo), not only journals and
  the big variable-star indexes. (TYC 3616-2395-1 had been listed 23 days earlier.)
- **A fallback is a test input too: check it on the controls before the day it is needed.**
- **Fix the sample before scanning a parameter.**
- **A row-count gate does not prove a parser right. Anchor parsed numbers to a second source.**
- **Before using a catalogue's numbers as truth for new stars, test them against a benchmark set.**
- **A failed lookup is not a negative answer, even when the rule says so.** Control rows first.
- **Put a self-test in every job and make it run first.**

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** Jobs that still need DR3 tables fall back to VizieR (I/357), AIP Potsdam
  or the Heidelberg mirror; DR3 epoch photometry falls back to ESA's bulk CDN files.
- Release-day checklist: `runbook/dr4-checklist.md` (order), with the rules in
  `runbook/dr4-release-day.md`, `runbook/dr4-addendum.md`, `findings/2026-11-24-g5-amendment-1.md`,
  `runbook/g6/README.md`, `runbook/g7/README.md` and `findings/2026-11-24-g7-amendment-1.md`.
