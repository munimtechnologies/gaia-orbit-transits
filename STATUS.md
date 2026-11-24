# gaia-orbit-transits: current status (2026-11-24)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and data
CC BY 4.0. This page is newer than the long README. Where the two differ, this page holds.

## Newest (24 Nov, ~13:45 UTC): the full-frame gap in tier 2, and a registered fold to close it

**Found by hand (exploratory):** the tier-2 job (sb2-tier2-dr3-v1) only sees stars that TESS's
pipeline searched, i.e. 2-minute targets. A spot check of one bright tier-2 star shows what can
fall through: **HD 35131** (Gaia DR3 262216446435606016, TIC 309683389, G 9.11, double-lined,
P 4.06235 d, m1 sin³i / m1 = 0.869). It has no TESS pipeline detection, no TOI, no VSX entry, no Gaia
variability class and no Gaia epoch photometry. Whether it eclipses can only be seen in TESS
full-frame images. We make no claim about it yet.

**Registered:** `findings/2026-11-24-sb2-ffiscan-t2-prereg.md`, `sb2_ffiscan_t2.py` 0.1.0 (tests
`test_sb2_ffiscan_t2.py`), job sb2-ffiscan-t2-v1 (`runbook/ffiscan-t2/job.json`). It runs the
pre-registered full-frame fold `sb2_ffiscan` 0.1.0, with every threshold unchanged, on all tier-2
stars. Roles (controls from VSX, Gaia's EB tables and Rowan et al. 2023) are fixed from catalogues
before any light curve is read. Gaia orbits come from the AIP mirror first, so it does not need
ESA's archive, which closes on 25 November. There are eight predictions, including one for HD 35131
(30%).

**Gaia DR4 check:** the DR4 table list (https://www.cosmos.esa.int/web/gaia/dr4) has
`nss_masses` (4,323,300 rows), described exactly as DR3's `binary_masses` was ("Masses derived from
the non-single stars (NSS) solutions with orbital parameters"). So the tier rule very likely carries
over on release day. The column list is only in the draft data-model zip, and the schema gate
(`sb2_screen_dr4` arm A/B) still decides on the day.

## Earlier (24 Nov, ~11:00 UTC): what the edge-on rule misses, and a registered second tier

- `findings/2026-11-24-rowan2023-prior-check.md`: Rowan et al. (2023) contains neither HD 250735 nor
  CD-28 7251. Of 27 Rowan eclipsing SB2s with P < 8 d, the edge-on window caught 11; 15 of the 16
  misses fall below 0.95 (Gaia's photometric m1 runs high). `data/rowan2023-check/rowan_tier_check.csv`.
- Registered: `findings/2026-11-24-g5-amendment-2-tier2.md`, `sb2_tier2.py` 0.1.0, job sb2-tier2-dr3-v1.

## Earlier (24 Nov, ~09:30 UTC): a correction, and a conjunction-gated search of the 95 unsearched binaries

- **TYC 3616-2395-1 (TIC 384284045) is not new.** The open catalogue Eclipses by Appointment
  listed it on 31 October 2026 (row A179), before our claim. Claim withdrawn:
  `findings/2026-11-24-tyc3616-prior-listing.md`. HD 250735 and CD-28 7251 remain new.
- Registered: `findings/2026-11-24-sb2-ffiscan-prereg.md`, `sb2_ffiscan.py` 0.1.0, job sb2-ffiscan-v1.

## Earlier (24 Nov, ~03:30-07:30 UTC)

- g7 timing fallback fixed before DR4: `findings/2026-11-24-g7-amendment-1.md`.
- Gaia caught HD 250735 in eclipse (exploratory): `findings/2026-11-24-hd250735-gaia-epochs.md`;
  per-transit velocity fits registered for DR4: `findings/2026-11-24-g7-prereg.md`.
- How accurate are Gaia's double-lined orbits? A test against DEBCat:
  `findings/2026-11-24-sb2-debcat-prereg.md`, `findings/2026-11-24-sb2-debcat-amendment-1.md`.

**Still queued (pre-registered earlier):** sb2-debcat-v2, sb2-ebfit-v1, sb2-new-ebs-timing-v1,
g5-lookup-rehearsal-v1, gaia-vpt-epochs-box-v1, tic93622019-pixel-011-v1, gaia-vpt-followup-v1,
sb2-ffiscan-v1, sb2-tier2-dr3-v1, and now sb2-ffiscan-t2-v1.

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
   jobs queued; ffiscan (95 unsearched tier-1 stars), tier 2 (pipeline) and tier-2 full-frame fold
   queued; DR4 g5, g5b and g7 on release day.
2. **How accurate are Gaia's dynamical and photometric masses?** DEBCat (sb2-debcat-v2), Rowan
   inclinations (tier-2 calibration), TESS conjunction times (ffiscan F1), then DR4 (g6).
3. **Gaia's own transit candidates in TESS:** TIC 93622019; N_comp period flag on DR4 (g4b).
4. **A transiting companion first found by Gaia astrometry** (step i, DR4).

## Lessons the pipeline now encodes (newest first)
- **A screen that reads only pipeline detections inherits the pipeline's target list.** Bright
  full-frame-only stars need their own fold.
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
