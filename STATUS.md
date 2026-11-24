# gaia-orbit-transits: current status (2026-11-24)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and data
CC BY 4.0. This page is newer than the long README. Where the two differ, this page holds.

## Newest (24 Nov, ~11:00 UTC): what the edge-on rule misses, and a registered second tier

**Checked:** `findings/2026-11-24-rowan2023-prior-check.md`. The closest published work,
Rowan et al. (2023, MNRAS 523, 2641; https://arxiv.org/abs/2212.02509), matched all Gaia DR3
double-lined orbits with ASAS-SN eclipsing binaries. Neither HD 250735 nor CD-28 7251 is in it: both
are brighter than ASAS-SN's V = 11 limit. They remain new.

**Measured (exploratory, by hand; the job re-checks it in code):**
`data/rowan2023-check/rowan_tier_check.csv`. Rowan's light-curve inclinations make an independent
set of eclipsing Gaia SB2s. Of the 27 with P < 8 d and a Gaia `binary_masses` m1, our edge-on window
(0.95 ≤ m1 sin³i / m1 ≤ 1.10) caught 11 (41%). 15 of the 16 misses fall below 0.95, because Gaia's
photometric m1 runs high: the median dynamical/photometric mass is 0.976 and the mean 0.955. A window
of 0.85-1.15 would have caught 21 of 27 (78%).

**Registered:** `findings/2026-11-24-g5-amendment-2-tier2.md`, `sb2_tier2.py` 0.1.0 (tests
`test_sb2_tier2.py`), job sb2-tier2-dr3-v1 (`runbook/tier2/job.json`). It screens tier 2
(0.85-0.95 and 1.10-1.15) of Gaia DR3 against TESS now, from the saved public orbit file. ESA's
archive is not needed, and Gaia's own tables fall back to the AIP mirror. On DR4 day it runs as step
5b. Predictions are in the file.

## Earlier (24 Nov, ~09:30 UTC): a correction, and a conjunction-gated search of the 95 unsearched binaries

- **TYC 3616-2395-1 (TIC 384284045) is not new.** The open catalogue Eclipses by Appointment
  listed it on 31 October 2026 (row A179), before our claim. Claim withdrawn:
  `findings/2026-11-24-tyc3616-prior-listing.md`. HD 250735 and CD-28 7251 remain new.
- Registered: `findings/2026-11-24-sb2-ffiscan-prereg.md`, `sb2_ffiscan.py` 0.1.0, job sb2-ffiscan-v1.
  It folds TESS light curves of the 95 edge-on binaries with no pipeline detection at Gaia's period
  and tests Gaia's predicted conjunction times.

## Earlier (24 Nov, ~03:30-07:30 UTC)

- g7 timing fallback fixed before DR4: `findings/2026-11-24-g7-amendment-1.md`.
- Gaia caught HD 250735 in eclipse (exploratory): `findings/2026-11-24-hd250735-gaia-epochs.md`;
  per-transit velocity fits registered for DR4: `findings/2026-11-24-g7-prereg.md`.
- How accurate are Gaia's double-lined orbits? A test against DEBCat:
  `findings/2026-11-24-sb2-debcat-prereg.md`, `findings/2026-11-24-sb2-debcat-amendment-1.md`.

**Still queued (pre-registered earlier):** sb2-debcat-v2, sb2-ebfit-v1, sb2-new-ebs-timing-v1,
g5-lookup-rehearsal-v1, gaia-vpt-epochs-box-v1, tic93622019-pixel-011-v1, gaia-vpt-followup-v1,
sb2-ffiscan-v1, and now sb2-tier2-dr3-v1.

## Earlier (23 Nov): masses and radii pre-registered; the Gaia SB2 x TESS screen graded

- `findings/2026-11-23-sb2-ebfit-prereg.md` and `findings/2026-11-23-sb2-screen-results.md`.
  Write-up: https://www.munimtech.com/research/gaia-binaries-new-eclipsing-benchmarks

## Earlier entries

Full entries for 23 Nov ~10:00 UTC and before are in the git history of this file and in their
`findings/` files.

Published write-ups:
- https://www.munimtech.com/research/gaia-binaries-new-eclipsing-benchmarks
- https://www.munimtech.com/research/gaia-transit-periods-known-planets
- https://www.munimtech.com/research/gaia-quality-cut-low-mass-orbits
- https://www.munimtech.com/research/tyc-6340-23-1-oversized-companion
- https://www.munimtech.com/research/gaia-brown-dwarf-orbits-missing-transits

## Leads
1. **Eclipsing binaries with Gaia masses:** two new (HD 250735, CD-28 7251); timing and mass-radius
   jobs queued; ffiscan (95 unsearched stars) and tier 2 (stars the window missed) queued; DR4 g5,
   g5b and g7 on release day.
2. **How accurate are Gaia's dynamical and photometric masses?** DEBCat (sb2-debcat-v2), Rowan
   inclinations (tier-2 calibration), TESS conjunction times (ffiscan F1), then DR4 (g6).
3. **Gaia's own transit candidates in TESS:** TIC 93622019; N_comp period flag on DR4 (g4b).
4. **A transiting companion first found by Gaia astrometry** (step i, DR4).

## Lessons the pipeline now encodes (newest first)
- **Measure what a selection rule misses, on an independent sample, before release day.**
- **"In no catalogue" must include open project catalogues and the closest paper's own tables**,
  not only the big variable-star indexes.
- **A fallback is a test input too: check it on the controls before the day it is needed.**
- **A failed lookup is not a negative answer.** Control rows first.
- **Put a self-test in every job and make it run first.**

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** DR3 fallbacks: AIP Potsdam TAP (https://gaia.aip.de/tap/sync), VizieR
  (I/357), ESA bulk CDN for epoch photometry.
- Release-day checklist: `runbook/dr4-checklist.md`; step 5b (tier 2) is in
  `findings/2026-11-24-g5-amendment-2-tier2.md`.
