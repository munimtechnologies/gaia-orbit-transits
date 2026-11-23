# gaia-orbit-transits: current status (2026-11-23)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Newest (23 Nov, ~17:30 UTC): masses and radii of the three new eclipsing binaries pre-registered

**Pre-registered:** `findings/2026-11-23-sb2-ebfit-prereg.md`, code `sb2_ebfit.py` 0.1.0 with tests
(`test_sb2_ebfit.py`), inputs `runbook/ebfit/targets.json`, job sb2-ebfit-v1 (queued).
- An eclipse model (two limb-darkened spheres, eccentric orbit, third light, a free linear
  baseline per eclipse) fitted to every TESS eclipse of CD-28 7251, TYC 3616-2395-1 and HD 250735,
  then combined with Gaia DR3's own K1 and K2 for **absolute masses and radii**. Errors: formal plus
  a jackknife over eclipse windows plus a limb-darkening systematic.
- **Controls chosen before any fit:** ZZ Boo, CW Eri, EY Cep and BK Peg, the four stars of the same
  screen with TESS-based DEBCat-grade masses and radii published 2023-2026. CONTROLS_OK if at least
  3 of 4 match the literature masses and R1+R2 within 3σ. Not blind for masses (Gaia's M sin³i was
  already known); the radius sum is the real test.
- Predictions: CONTROLS_OK 55%; FIT_OK for HD 250735 85%, TYC 3616-2395-1 80%, CD-28 7251 60%;
  CD-28 7251's stars 1.9-2.3 and 1.6-1.95 M_sun (75%).
- Method prior art: Rowan et al. (2023) did this with ASAS-SN light curves for 122 stars; ours
  uses TESS, and our three systems are not in their sample.

**Still queued (pre-registered earlier):** sb2-new-ebs-timing-v1 (eclipse times against Gaia's
orbits), gaia-vpt-epochs-box-v1, tic93622019-pixel-011-v1, gaia-vpt-followup-v1.

## Earlier (23 Nov, ~10:00 UTC): the Gaia SB2 x TESS screen graded; two more new eclipsing binaries with Gaia masses

**Graded (pre-registered):** `findings/2026-11-23-sb2-screen-results.md`, data
`data/sb2-edgeon-screen-v1/` (job sb2-edgeon-screen-v1, `sb2_screen.py` 0.1.0) and
`data/sb2-new-ebs/` (vetting after the run).
- 183 edge-on Gaia DR3 double-lined orbits (P < 8 d): 66 have a qualifying TESS SPOC TCE, 46 at
  half the Gaia period (S1 0.70, **MIXED**; we predicted HALF_DOMINANT, **wrong**). Controls: all 44
  VSX eclipsing stars with a TCE are at P or P/2 (**CONTROLS_OK**). S0 **DIFFERS** (183, 18 of 20
  pilot stars; **wrong**): the pilot had left the (1 − e²)^1.5 factor out of M1 sin³i, so two
  eccentric pilot stars do not pass the registered rule.
- **The screen's lookup of the Villanova TESS EB catalogue failed for every star (HTTP 400)**, so
  its "new" list of 8 was too long. Vetted by hand (Prša et al. 2022 and T10K through VizieR's CfA
  mirror with control rows, SIMBAD, VSX, ASAS-SN, ExoFOP): 3 are in the TESS EB catalogue, 1 is
  Kepler's KOI-3161, 1 is a known heartbeat star.
- **New eclipsing binaries (in no catalogue we reached): CD-28 7251 (TIC 189269584, A3m, G 8.86;
  Gaia P 6.96109 d, e 0.076; M sin³i 2.06 and 1.74 M_sun) and TYC 3616-2395-1 (TIC 384284045,
  G 10.47; P 3.78709 d, circular; M sin³i 1.05 and 1.12 M_sun)**, besides HD 250735 from the pilot.
- **CD-28 7251's eclipses are in Gaia's own resolved photometry:** two dips (0.27 and 0.19 mag)
  7.004 d apart, both 0.14-0.18 d from the same conjunction of Gaia's own orbit (hand calculation,
  about 0.19 d uncertainty). A brighter star 46″ away dilutes TESS but cannot make these dips.

**Pre-registered then:** `findings/2026-11-23-sb2-new-ebs-prereg.md`, code `sb2_ebtime.py` 0.1.0
with tests, inputs `runbook/ebtime/targets.json`, job sb2-new-ebs-timing-v1 (queued).

## Earlier entries

Full entries for 23 Nov ~01:45 UTC and before (the pixel test's amendment, the DR4 runbook
addendum, the T10K check, the epoch test, the period-free search and TIC 93622019, TYC 6340-23-1,
the RVS screen and everything from 19-21 Nov) are in the git history of this file (commit
80be2827 and earlier) and in their `findings/` files.

Published write-ups:
- https://www.munimtech.com/research/gaia-transit-periods-known-planets
- https://www.munimtech.com/research/gaia-quality-cut-low-mass-orbits
- https://www.munimtech.com/research/tyc-6340-23-1-oversized-companion
- https://www.munimtech.com/research/gaia-brown-dwarf-orbits-missing-transits

## Leads
1. **Eclipsing binaries with Gaia masses:** screen graded 23 Nov; three new (HD 250735, CD-28 7251,
   TYC 3616-2395-1); eclipse timing (sb2-new-ebs-timing-v1) and masses and radii (sb2-ebfit-v1)
   queued; then Gaia DR4's SB2 list (step g5).
2. **Gaia's own transit candidates in TESS** (step g): new candidate **TIC 93622019** (pixel re-run and
   Gaia-epoch test queued); the N_comp period flag registered as an out-of-sample test on DR4 (g4b).
3. **A transiting companion first found by Gaia astrometry** (step i, DR4): rehearsal passed.
4. **Do Gaia DR3 inclinations hold up against real eclipses?** 58 of 162 near-edge-on orbits
   eclipse against 80.7 expected (p = 2 × 10⁻⁵). Gaia DR4 decides.
5. **TYC 6340-23-1** (B_OVERSIZED_COMPANION): mass test on DR4 day (step a5).

## Lessons the pipeline now encodes (newest first; full list in commit a34b7885)
- **A failed lookup is not a negative answer, even when the rule says so.** Use a catalogue's
  VizieR copy with a control row, and treat a 100% failure rate as a broken check.
- **Recompute a pilot with the registered formula before predicting replication.**
- **A survey that resolves what TESS blends settles "which star" for free.**
- **Stars a PSF cannot separate must share one column, and fluxes must be non-negative.**
- **Pair every empty answer with a control query**, and run the controls first.
- **Put a self-test in every job and make it run first.**

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API at vsx.aavso.org, or its VizieR copy B/vsx), the TESS EB catalogue (Prša et al.
2022; VizieR J/ApJS/258/16 via vizier.cfa.harvard.edu), the TESS Ten Thousand catalogue (Kostov
et al. 2025; J/ApJS/279/50), IJspeert et al. 2021 OBA EBs (J/A+A/652/A120), Gaia DR3
vari_eclipsing_binary, vari_classifier_result and binary_masses (method Eclipsing+SB2), the ZTF
and ASAS-SN variable catalogues (II/366/catv2021), Rowan et al. (2023), DEBCat, ExoFOP, the SPOC
TCE list, SIMBAD (Harvard mirror), Kepler KOIs, and Gaia DR3 nss_two_body_orbit.

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** Jobs that still need DR3 tables fall back to the Heidelberg DR3 mirror;
  DR3 epoch photometry falls back to ESA's bulk CDN files, and the 214 transit candidates' epochs
  are in the repo.
- Release-day runbook: `runbook/dr4-release-day.md` plus `runbook/dr4-addendum.md` (steps g4b and
  g5, the pixel step, step i pinned). Step G6 uses `vpt_pf.py` at commit
  9bf9704211bd129204bb4de091f38021ec76d301; step g2c uses `vpt_nss.py` at commit
  b8f2525dde1bebdabf2b89a33065aac797771e2d.
