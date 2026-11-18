# gaia-orbit-transits: current status (2026-11-18, v0.16.0)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where they differ, this one
holds.

## Leads
1. **Do Gaia DR3 inclinations hold up against real eclipses?** (graded in 0.16.0,
   `findings/2026-11-18-calib-v3-results.md`). Of 162 near-edge-on DR3 orbits that TESS
   covered, 50 eclipse, where Gaia's published errors predict 69 (p = 1.4 × 10⁻⁴). The
   detected eclipses also scatter in time about 2–2.5 times more than Gaia's propagated
   errors allow. That timing scatter can push real eclipses outside our ±3σ windows and
   explain much of the deficit, so the "k = 2.3" inclination-error inflation is **not yet
   claimed**. A joint fit of both effects is pre-registered
   (`findings/2026-11-18-calib-window-prereg.md`, job gaia-calibw-v1).
2. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?** About 21,000 DR3 SB1
   orbits (G ≤ 13) have mass functions that allow a companion below ~0.1 M☉. Geometry says
   5–20% of the real ones must transit, yet only three were found via the TOI list
   (Stevenson et al. 2023). `sb1_transit.py` measures the rate directly in TESS
   (`findings/2026-11-18-sb1-transit-prereg.md`, jobs gaia-sb1tr-c0-v1 and -c1-v1, queued).
   *Eclipses by Appointment* (below) does not measure rates or test brown-dwarf orbits.
3. **Are M dwarfs in 0.5–3-day orbits inflated?** About 167 Gaia DR3 SB1 orbits of stars
   that Gaia also sees eclipse, with companion masses from Gaia RVs and radii from TESS fits
   (`findings/2026-11-17-eblm-fit-prereg.md`,
   `findings/2026-11-17-short-period-inflation-prereg.md`). Job gaia-eblm-fit-v1 is
   running.
4. **White-dwarf self-lensing at Gaia-predicted times.** The first pass failed as a null
   test (`findings/2026-11-18-selflens-results.md`). The vetting job is queued. No candidate
   is claimed.

## Corrected
- **CD-48 897 (TIC 200743349) is not a new discovery of ours.** The open working paper
  *Eclipses by Appointment* (github.com/Snowstar38/eclipses-by-appointment) listed it as
  confirmed (claim Q031) by 2026-11-06, twelve days before our 0.12.0 report, which
  missed that repository. Our independent eclipse fits passed their pre-registered tests.
  The ephemeris, T_min = BJD_TDB 2458392.73244(50) + 26.5329072(79) E, and the next
  eclipses (2026-11-19 ~21:58 UTC, 2026-12-16 ~10:47 UTC, 2027-01-11 ~23:36 UTC) are in
  `findings/2026-11-18-ebchar-results.md`. We will not report it to VSX.
- TOI-710.01 (already a TFOP false positive): the eclipses repeat every 72.082 d, a third
  of the TOI period, matching Gaia's SB1 orbit within 2.8σ.

## Refuted or closed
- TIC 207399049 (`findings/2026-11-18-tic207399049-results.md`): refuted.
- Archival dips at Gaia-predicted times for the 25-star watch list
  (`findings/2026-11-18-archival-results.md`): 0 found where 0.28 were expected.
- Two "stripped companion" candidates from the EBLM screen (HD 322627 and TYC 7626-466-1)
  are more likely blends or triples than EL CVn systems. They are not pursued.

## Prior-art sources we now check for every eclipsing system
AAVSO VSX, the TESS EB catalogue (Prša et al. 2022), Gaia DR3 vari_eclipsing_binary,
ExoFOP, SIMBAD, the Chopard-Vilhem Zenodo deposits (10.5281/zenodo.22998328 and
10.5281/zenodo.23342416) and the *Eclipses by Appointment* claim tables.

## Gaia DR4 (2 December 2026)
Pre-registered order: EBLM inflation on DR4 SB1 × eclipsing binaries; the SB1 transit-rate
test on DR4's RVS SB1 orbits; the inclination and timing calibration repeated on DR4
orbits; the RV transit screen; exoplanet candidates; self-lensing; and the three Kepler
self-lensing binaries with large DR3 RUWE.
