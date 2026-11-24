# gaia-orbit-transits: current status (2026-11-24)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and data
CC BY 4.0. This page is newer than the long README. Where the two differ, this page holds.

## Newest (24 Nov, ~17:30 UTC): two eclipse candidates found in Gaia's own photometry (exploratory)

Before ESA's Gaia archive closed for DR4, we read the Gaia DR3 epochs of all 19 edge-on
double-lined binaries from our screen that TESS's pipeline never searched and that Gaia classified
as a non-eclipsing variable. `findings/2026-11-24-gaia-conj-dips.md`; code `gaia_conj_dips.py` 0.1.0;
data `data/gaia-conj-dips/` (952 usable epochs). The tests (`test_gaia_conj_dips.py`) assert every
number in the note, and the publish lane ran them before this commit.

- Only 2 of the 19 stars dim at all, and every dip falls at a conjunction of the star's own Gaia
  orbit:
  - **CD-63 310** (TIC 349572805, G 9.94, P 5.41063 d): two consecutive Gaia measurements are 0.040
    and 0.031 mag faint, at phases 0.7503 and 0.7639. The conjunction is at 0.75.
  - **CD-72 1603** (TIC 371839648, G 9.91, P 4.56693 d): one measurement is 0.052 mag faint, at
    phase 0.2441. The conjunction is at 0.25.
- Both look like short, grazing eclipses. Neither is listed as eclipsing in VSX, the TESS EB
  catalogue, ExoFOP, Gaia's EB table or the open Eclipses by Appointment catalogue (checked 24 Nov).
  Gaia's classifier labelled both ACV (rotating chemically peculiar stars).
- CD-63 310 is in no queued job, because our screen found no TIC number for it. TESS has full-frame
  data of it from about 37 sectors.
- Registered test: `findings/2026-11-24-gaia-conj-dips-prereg.md`, `gaia_dip_ffi.py` 0.1.0, job
  gaia-dip-ffi-v1. It folds TESS light curves of both candidates, two positive controls and six
  flat stars with the unchanged sb2_ffiscan analysis.

## Earlier (24 Nov, ~15:00 UTC): TIC 93622019's faint Gaia epochs fall in the TESS transits (exploratory)

- `findings/2026-11-24-tic93622019-gaia-epochs-tess-ephemeris.md`; `tic93622019_gaia_epochs.py`.
  The four epochs in the TESS transit core are 0.95-1.89% faint. The five in both sets of windows
  average 1.28%, the deblended TESS depth. Gaia's 2.83-d alias added three low outliers.
  The registered test (gaia-vpt-epochs-box-v1) is still queued.

## Earlier (24 Nov, ~13:45 UTC): the full-frame gap in tier 2, and a registered fold to close it

- `findings/2026-11-24-sb2-ffiscan-t2-prereg.md`, `sb2_ffiscan_t2.py` 0.1.0, job sb2-ffiscan-t2-v1.

## Earlier (24 Nov, ~11:00 UTC): what the edge-on rule misses, and a registered second tier

- `findings/2026-11-24-rowan2023-prior-check.md`; `findings/2026-11-24-g5-amendment-2-tier2.md`,
  `sb2_tier2.py` 0.1.0, job sb2-tier2-dr3-v1.

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
sb2-ffiscan-v1, sb2-tier2-dr3-v1, sb2-ffiscan-t2-v1, and now gaia-dip-ffi-v1.

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
1. **Eclipsing binaries with Gaia masses:** two new (HD 250735, CD-28 7251) and two Gaia-epoch
   candidates (CD-63 310, CD-72 1603); timing and mass-radius jobs queued; ffiscan, tier 2, tier-2
   full-frame and gaia-dip-ffi queued; DR4 g5, g5b and g7 on release day.
2. **How accurate are Gaia's dynamical and photometric masses?** DEBCat (sb2-debcat-v2), Rowan
   inclinations, TESS conjunction times, then DR4 (g6).
3. **Gaia's own transit candidates in TESS:** TIC 93622019; N_comp period flag on DR4 (g4b).
4. **A transiting companion first found by Gaia astrometry** (step i, DR4).

## Lessons the pipeline now encodes (newest first)
- **A screen's lookup failures leave gaps no later job sees.** 22 edge-on binaries got no TIC
  number and so no TESS job; one of them now has the best Gaia-epoch eclipse signal.
- **A period search over sparse epochs can win with an alias that adds a few low outliers to the
  real transits.** Check both ephemerides epoch by epoch.
- **A screen that reads only pipeline detections inherits the pipeline's target list.**
- **"In no catalogue" must include open project catalogues and the closest paper's own tables.**
- **A failed lookup is not a negative answer.** Control rows first.
- **Put a self-test in every job and make it run first.**

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** DR3 fallbacks: AIP Potsdam TAP (https://gaia.aip.de/tap/sync), VizieR
  (I/357), ESA bulk CDN for epoch photometry.
- Release-day checklist: `runbook/dr4-checklist.md`.
