# gaia-orbit-transits: current status (2026-11-18, v0.15.0)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where they differ, this one
holds.

## Leads
1. **CD-48 897 (TIC 200743349, Gaia DR3 4749907416157959424): a new bright eclipsing
   binary weighed by Gaia.** V = 10.6, a G dwarf at 121 pc with a Gaia AstroSpectroSB1
   orbit (P = 26.54 d, e = 0.48). TESS shows five grazing ~10% eclipses of ~2 h at
   T = BTJD 1392.7316 + 26.5328 E. We found it in no catalogue (VSX, TESS-EBs, Gaia DR3
   eclipsing binaries, ExoFOP, Chopard-Vilhem 2026). Its pre-registered characterisation
   (`findings/2026-11-18-cd-48-897-prereg.md`, job gaia-ebchar-v1) is waiting for
   compute. Next predicted eclipses: 2026-11-19 21:43 UTC, 2026-12-16 10:31 UTC,
   2027-01-11 23:18 UTC (±43 min). TESS does not observe it again before mid-January 2027.
2. **New (0.15.0): are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?** Gaia DR3
   has ~21,000 SB1 orbits (G ≤ 13) whose mass function allows a companion below ~0.1 M☉.
   Geometry says 5–20% of the real ones must transit, yet only three such transiting
   companions were found through the TOI list (Stevenson et al. 2023). `sb1_transit.py`
   measures the rate directly in TESS: it folds each sector at the Gaia period, runs
   injection tests and control periods, and checks the timing against Gaia's own
   prediction. Pre-registered in `findings/2026-11-18-sb1-transit-prereg.md` (jobs
   gaia-sb1tr-c0-v1 and -c1-v1). The convention check: from Gaia's SB1 orbit alone, WASP-18 b's
   transit is predicted within 0.022 d of its TESS epoch after 2,991 orbits.
3. **Are M dwarfs in 0.5–3-day orbits inflated?** About 167 Gaia DR3 single-lined
   binaries that Gaia also sees eclipse, with companion masses from Gaia RVs and radii
   from TESS eclipse fits (`findings/2026-11-17-eblm-fit-prereg.md`,
   `findings/2026-11-17-short-period-inflation-prereg.md`). The fits (gaia-eblm-fit-v1)
   are waiting for compute.
4. **Do Gaia DR3 inclinations hold up against real eclipses?** The calibration
   (`findings/2026-11-18-calib-v3-amendment.md`, gaia-calib-v3) is waiting for compute.
5. **White-dwarf self-lensing at Gaia-predicted times.** The first pass failed as a null
   test because of edge artefacts (`findings/2026-11-18-selflens-results.md`). All 17
   events are being vetted (gaia-selflens-vet-v1). No self-lensing candidate is claimed.

## Refuted or closed
- TIC 207399049 (`findings/2026-11-18-tic207399049-results.md`): refuted.
- Archival dips at Gaia-predicted times for the 25-star watch list
  (`findings/2026-11-18-archival-results.md`): 0 found where 0.28 were expected.
- Two "stripped companion" candidates from the EBLM screen (Gaia DR3 5976702667540821376
  = HD 322627 and 5557223240440494080 = TYC 7626-466-1) were checked on 2026-11-18. Both
  are P ≈ 0.86–0.89 d SB1 orbits with RUWE 3.4 and 5.7, and one has e = 0.29 at
  P = 0.86 d, which is implausible for so short a period. Blends or triples are more
  likely than EL CVn systems. They are not pursued.

## Gaia DR4 (2 December 2026)
Pre-registered order: EBLM inflation on DR4 SB1 × eclipsing binaries; the SB1 transit-rate
test on DR4's ~639,000 RVS SB1 orbits; the RV transit screen; exoplanet candidates; the
full astrometric search with calibrated inclinations; self-lensing; the DR4 orbit of
CD-48 897; and the three Kepler self-lensing binaries with large DR3 RUWE.
