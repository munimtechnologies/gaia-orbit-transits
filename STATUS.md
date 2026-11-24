# gaia-orbit-transits: current status (2026-11-24)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Newest (24 Nov, ~05:00 UTC): the DEBCat test made layout-proof, and its Gaia DR4 run fixed in advance

**Amendment:** `findings/2026-11-24-sb2-debcat-amendment-1.md`, code `sb2_debcat.py` 0.2.0, job
sb2-debcat-v2 (replaces v1, which never ran). DR4-day step: `runbook/g6/README.md`.
- A description of DEBCat's web table says each column lists both stars' values. Parser 0.1.0 took
  the first value per cell, so it could have read one star's radius as the other's mass without any
  gate noticing. Version 0.2.0 reads every value and keeps a system only if its web-table masses
  equal those in DEBCat's ascii file `debs.dat`. Gate: at least 100 such anchored systems.
- New control: the matched DR3 orbits are re-read from a Gaia TAP service and must agree with
  VizieR, which rehearses the DR4 code path on known data.
- **Registered eight days before Gaia DR4:** the same test on DR4's double-lined orbits (schema gate,
  DR3→DR4 crossmatch through `dr3_neighbourhood`, RZ Cha controls, identical grades), with
  predictions. It asks from outside whether 66 months of Gaia spectroscopy beat 34.

## Earlier (24 Nov, ~03:30 UTC): how accurate are Gaia's double-lined orbits? A test against DEBCat

- `findings/2026-11-24-sb2-debcat-prereg.md`: Gaia DR3's 5,376 double-lined orbits against DEBCat's
  eclipsing binaries with masses known to about 2%. Grades: mass ratio (Q1), mass scale (Q2), quoted
  errors (Q3), line blending (Q4). Gaia's own validation paper for this channel is deferred to DR4.

**Still queued (pre-registered earlier):** sb2-ebfit-v1 (masses and radii of the three new
eclipsing binaries), sb2-new-ebs-timing-v1, g5-lookup-rehearsal-v1 (`findings/2026-11-24-g5-amendment-1.md`),
gaia-vpt-epochs-box-v1, tic93622019-pixel-011-v1, gaia-vpt-followup-v1.

## Earlier (24 Nov, ~02:30 UTC): the DR4 double-lined screen gets lookups that cannot fail silently

- `findings/2026-11-24-g5-amendment-1.md`, `sb2_screen_dr4.py` 0.2.0: control TICs, VizieR TESS EB
  and T10K lookups with controls, "unvetted" instead of "new" on any failed lookup, a DR4 schema gate.

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
   timing and mass-radius jobs queued; Gaia DR4's SB2 list on release day (step g5).
2. **How accurate are Gaia's dynamical masses?** DR3 against DEBCat (sb2-debcat-v2), then DR4 on
   release day (step g6).
3. **Gaia's own transit candidates in TESS** (step g): new candidate **TIC 93622019**; the N_comp
   period flag is a registered out-of-sample test on DR4 (g4b).
4. **A transiting companion first found by Gaia astrometry** (step i, DR4): rehearsal passed.
5. **Do Gaia DR3 inclinations hold up against real eclipses?** 58 of 162 near-edge-on orbits
   eclipse against 80.7 expected (p = 2 × 10⁻⁵). Gaia DR4 decides.

## Lessons the pipeline now encodes (newest first; full list in commit a34b7885)
- **A row-count gate does not prove a parser right. Anchor parsed numbers to a second source.**
- **Before using a catalogue's numbers as truth for new stars, test them against a benchmark set.**
- **When a lookup fails on every star, try the obvious first: the scheme (http vs https).**
- **A failed lookup is not a negative answer, even when the rule says so.** Control rows first.
- **Put a self-test in every job and make it run first.**

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** Jobs that still need DR3 tables fall back to VizieR (I/357), AIP Potsdam
  or the Heidelberg mirror; DR3 epoch photometry falls back to ESA's bulk CDN files.
- Release-day runbook: `runbook/dr4-release-day.md`, `runbook/dr4-addendum.md`,
  `findings/2026-11-24-g5-amendment-1.md`, `runbook/g6/README.md`.
