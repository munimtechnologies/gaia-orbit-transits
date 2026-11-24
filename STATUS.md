# gaia-orbit-transits: current status (2026-11-24)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Newest (24 Nov, ~03:30 UTC): how accurate are Gaia's double-lined orbits? A test against DEBCat

**Pre-registration:** `findings/2026-11-24-sb2-debcat-prereg.md`, code `sb2_debcat.py` 0.1.0 with
tests (`test_sb2_debcat.py`), job sb2-debcat-v1 (queued).
- Gaia DR3 published 5,376 double-lined orbits (VizieR I/357/tbosb2 and tbosb2c). Their velocity
  amplitudes give dynamical masses, which Rowan et al. (2023), our three new eclipsing binaries and
  soon Gaia DR4 rely on. Gaia's own validation paper for this channel is deferred to DR4, and we
  found no systematic comparison with DEBCat, the catalogue of eclipsing binaries with masses known
  to about 2%. Published case studies disagree (RZ Cha agrees; CW CMa 2.6σ high; V570 Per in
  moderate disagreement).
- The job matches every DEBCat system to Gaia through SIMBAD and grades four questions: is the mass
  ratio unbiased (Q1), is the mass scale right (Q2, from (M1+M2) sin³i over DEBCat's mass), are the
  quoted errors realistic (Q3), and do Gaia's masses fail where the two stars' lines overlap (Q4).
  Controls: RZ Cha end to end, VizieR row counts and a known row, SIMBAD's ID for RZ Cha.
- Predictions include: Q2 MASS_SCALE_OK 50%; Q3 errors understated 65%; Q4 blending signal 30%.

**Still queued (pre-registered earlier):** sb2-ebfit-v1 (masses and radii of the three new
eclipsing binaries), sb2-new-ebs-timing-v1, g5-lookup-rehearsal-v1 (`findings/2026-11-24-g5-amendment-1.md`,
release v0.53.0, commit f282d09), gaia-vpt-epochs-box-v1, tic93622019-pixel-011-v1,
gaia-vpt-followup-v1.

## Earlier (24 Nov, ~02:30 UTC): the DR4 double-lined screen gets lookups that cannot fail silently

- `findings/2026-11-24-g5-amendment-1.md`, `sb2_screen_dr4.py` 0.2.0: the DR3 screen's Villanova
  lookup failed on every star because it used http; the live catalogue (https) has no entry for
  CD-28 7251, TYC 3616-2395-1 or HD 250735. Control TICs, VizieR TESS EB and T10K lookups with
  self-generated controls, "unvetted" instead of "new" on any failed lookup, and a DR4 schema gate.

## Earlier (23 Nov): masses and radii pre-registered; the Gaia SB2 x TESS screen graded

- `findings/2026-11-23-sb2-ebfit-prereg.md`: an eclipse model of every TESS eclipse of CD-28 7251,
  TYC 3616-2395-1 and HD 250735, combined with Gaia DR3's K1 and K2 for absolute masses and radii.
- `findings/2026-11-23-sb2-screen-results.md`: 183 edge-on Gaia DR3 double-lined orbits; 66 with a
  qualifying TESS TCE (46 at half the Gaia period). **Three new bright double-lined eclipsing
  binaries with Gaia masses: HD 250735, CD-28 7251 (whose eclipses Gaia's own photometry caught)
  and TYC 3616-2395-1.** Write-up:
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
   timing and mass-radius jobs queued; Gaia DR4's SB2 list on release day (step g5); the accuracy
   of Gaia's double-lined masses themselves is now under test (sb2-debcat).
2. **Gaia's own transit candidates in TESS** (step g): new candidate **TIC 93622019** (pixel re-run
   and Gaia-epoch test queued); the N_comp period flag is a registered out-of-sample test on DR4 (g4b).
3. **A transiting companion first found by Gaia astrometry** (step i, DR4): rehearsal passed.
4. **Do Gaia DR3 inclinations hold up against real eclipses?** 58 of 162 near-edge-on orbits
   eclipse against 80.7 expected (p = 2 × 10⁻⁵). Gaia DR4 decides.
5. **TYC 6340-23-1** (B_OVERSIZED_COMPANION): mass test on DR4 day (step a5).

## Lessons the pipeline now encodes (newest first; full list in commit a34b7885)
- **Before using a catalogue's numbers as truth for new stars, test them against a benchmark set.**
- **When a lookup fails on every star, try the obvious first: the scheme (http vs https).**
- **A failed lookup is not a negative answer, even when the rule says so.** Control rows first;
  "unknown" stays unknown.
- **Recompute a pilot with the registered formula before predicting replication.**
- **Put a self-test in every job and make it run first.**

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** Jobs that still need DR3 tables fall back to the Heidelberg DR3 mirror or
  VizieR (I/357); DR3 epoch photometry falls back to ESA's bulk CDN files.
- Release-day runbook: `runbook/dr4-release-day.md` plus `runbook/dr4-addendum.md` plus
  `findings/2026-11-24-g5-amendment-1.md`.
