# gaia-orbit-transits: current status (2026-11-24)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and data
CC BY 4.0. This page is newer than the long README. Where the two differ, this page holds.

## Newest (24 Nov, ~07:30 UTC): g7's timing fallback was broken for 4 of 7 stars; fixed before DR4

**Amendment:** `findings/2026-11-24-g7-amendment-1.md`, data `data/g7-ephemerides/ephemeris_check.csv`,
filled inputs `runbook/g7/targets.json`, one ordered DR4-day list `runbook/dr4-checklist.md`.
- Step g7 used SPOC's TESS pipeline fits (TCEs) as its fallback eclipse ephemeris. We read all seven:
  ZZ Boo's TCE has the wrong period (6.51 d against 4.99 d), and the TCEs of CW Eri, BK Peg and CD-28 7251
  never converged. As registered, three of the four controls would have failed for a reason unrelated
  to Gaia.
- Controls now use their published eclipse ephemerides (Southworth and co-authors). The targets have
  rule-based fallbacks with honest errors. CD-28 7251's conjunction grade is not made on the fallback.
- Cost, said plainly: on the fallback, HD 250735's ephemeris error rises from 0.005 to 0.023 d. That is
  because two consecutive TESS sectors' pipeline fits disagree by 32 minutes. So the 0.020-d early
  hint can only be tested with the queued eclipse-timing job's ephemeris. Added prediction: that job
  will show the 32-minute offset is a fitting artefact (75%).
- Exploratory: CD-28 7251's Gaia eclipse dips of 2015 and its TESS eclipse of 2023 are linked by
  396 cycles at P ≈ 6.9609 ± 0.0008 d. That agrees with Gaia's spectroscopic period and not with the
  pipeline's biased P/2 fit. The queued sb2-ebfit and timing jobs do not use pipeline TCEs, so they need
  no change.

## Earlier (24 Nov, ~06:30 UTC): Gaia caught HD 250735 in eclipse; per-transit velocity fits registered for DR4

**Exploratory:** `findings/2026-11-24-hd250735-gaia-epochs.md`, data
`data/sb2-new-ebs/hd-250735_gaia_dr3_epoch_g.csv` (saved before ESA's archive closes on 25 Nov).
- HD 250735's 43 Gaia DR3 G-band epochs contain exactly two faint points (by the registered E4 rule),
  and **both fall inside TESS-predicted eclipses**, one in each of the two alternating eclipses.
  Their neighbours, out of eclipse, are at normal brightness. Chance alignment is about 0.2%. Gaia
  resolves 0.4″, so the eclipses belong to HD 250735 itself.
- A lead, not a result: both points, and Gaia's own orbital conjunction (0.020 ± 0.010 d), sit
  *earlier* than the TESS ephemeris extrapolated back to 2014-2017.
- Not the registered E4 grade: that comes from the queued job sb2-new-ebs-timing-v1.

**Registered:** `findings/2026-11-24-g7-prereg.md`, code `sb2_rvfit.py` 0.1.0 (tests
`test_sb2_rvfit.py`, passed on commit, v0.56.0), runner and inputs in `runbook/g7/`.
- On DR4 day, fit Gaia's per-transit double-lined velocities (`rvs_epoch_parameters_double`) of
  the three new eclipsing binaries with the eclipse timing fixed. The fit gives a conjunction-timing
  check, K1 and K2 against DR4's own orbit, and absolute masses with the eclipse-fit inclinations.
  Four literature eclipsing binaries serve as controls. The same fit then runs on every new
  eclipsing binary that the DR4 screen (g5) finds.

## Earlier (24 Nov, ~05:00 UTC): the DEBCat test made layout-proof, and its Gaia DR4 run fixed in advance

**Amendment:** `findings/2026-11-24-sb2-debcat-amendment-1.md`, code `sb2_debcat.py` 0.2.0, job
sb2-debcat-v2. DR4-day step: `runbook/g6/README.md`. Every DEBCat mass is now anchored to DEBCat's
ascii file before use. The same test on DR4's double-lined orbits is registered with predictions.

## Earlier (24 Nov, ~03:30 UTC): how accurate are Gaia's double-lined orbits? A test against DEBCat

- `findings/2026-11-24-sb2-debcat-prereg.md`: Gaia DR3's 5,376 double-lined orbits against DEBCat's
  eclipsing binaries with masses known to about 2%. Grades: mass ratio (Q1), mass scale (Q2), quoted
  errors (Q3), line blending (Q4).

**Still queued (pre-registered earlier):** sb2-debcat-v2, sb2-ebfit-v1 (masses and radii of the
three new eclipsing binaries), sb2-new-ebs-timing-v1, g5-lookup-rehearsal-v1, gaia-vpt-epochs-box-v1,
tic93622019-pixel-011-v1, gaia-vpt-followup-v1.

## Earlier (23 Nov): masses and radii pre-registered; the Gaia SB2 x TESS screen graded

- `findings/2026-11-23-sb2-ebfit-prereg.md`: an eclipse model of every TESS eclipse of CD-28 7251,
  TYC 3616-2395-1 and HD 250735, combined with Gaia DR3's K1 and K2 for absolute masses and radii.
- `findings/2026-11-23-sb2-screen-results.md`: 183 edge-on Gaia DR3 double-lined orbits; 66 with a
  qualifying TESS TCE. **Three new bright double-lined eclipsing binaries with Gaia masses: HD 250735,
  CD-28 7251 and TYC 3616-2395-1.** Write-up:
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
1. **Eclipsing binaries with Gaia masses:** three new (HD 250735, CD-28 7251, TYC 3616-2395-1);
   timing and mass-radius jobs queued; DR4's double-lined list (g5) and per-transit velocities
   (g7) on release day.
2. **How accurate are Gaia's dynamical masses?** DR3 against DEBCat (sb2-debcat-v2), then DR4 on
   release day (step g6).
3. **Gaia's own transit candidates in TESS** (step g): new candidate **TIC 93622019**; the N_comp
   period flag is a registered out-of-sample test on DR4 (g4b).
4. **A transiting companion first found by Gaia astrometry** (step i, DR4): rehearsal passed.
5. **Do Gaia DR3 inclinations hold up against real eclipses?** 58 of 162 near-edge-on orbits
   eclipse against 80.7 expected (p = 2 × 10⁻⁵). Gaia DR4 decides.

## Lessons the pipeline now encodes (newest first; full list in commit a34b7885)
- **A fallback is a test input too: check it on the controls before the day it is needed.** (g7's
  pipeline-TCE fallback failed 3 of 4 controls.)
- **Fix the sample before scanning a parameter:** a χ² scan is only comparable if every step uses
  the same data points (g7 drops blended epochs by observed, not model, separation).
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
