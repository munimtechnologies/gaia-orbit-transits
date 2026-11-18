# gaia-orbit-transits: current status (2026-11-18, v0.14.0)

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
2. **Are M dwarfs in 0.5–3-day orbits inflated?** About 167 Gaia DR3 single-lined
   binaries that Gaia also sees eclipse, with companion masses from Gaia RVs and radii
   from TESS eclipse fits (`findings/2026-11-17-eblm-fit-prereg.md`,
   `findings/2026-11-17-short-period-inflation-prereg.md`). The fits (gaia-eblm-fit-v1)
   are waiting for compute.
3. **Do Gaia DR3 inclinations hold up against real eclipses?** The calibration
   (`findings/2026-11-18-calib-v3-amendment.md`, gaia-calib-v3) is waiting for compute.
   Evidence so far: about 21 eclipsing systems seen where about 74 were expected.
4. **White-dwarf self-lensing at Gaia-predicted times.** The first pass found 17
   brightenings in 15 stars, against at most 1.9 expected, so the pulse rule failed as
   a null test (`findings/2026-11-18-selflens-results.md`). Most events sit at
   segment edges. All of them are being vetted (`findings/2026-11-18-selflens-vet-prereg.md`,
   gaia-selflens-vet-v1). No self-lensing candidate is claimed.

## Refuted or closed
- TIC 207399049 (`findings/2026-11-18-tic207399049-results.md`): refuted.
- Archival dips at Gaia-predicted times for the 25-star watch list
  (`findings/2026-11-18-archival-results.md`): 0 found where 0.28 were expected; the 5
  threshold crossings are artefacts.

## Gaia DR4 (2 December 2026)
Pre-registered order: EBLM inflation on DR4 SB1 × eclipsing binaries; the RV transit
screen; exoplanet candidates; the full astrometric search with calibrated inclinations;
self-lensing; the DR4 orbit of CD-48 897; and the three Kepler self-lensing binaries
with large DR3 RUWE (KIC 3835482, KIC 6233093, KIC 12254688), which would allow an
Einstein-vs-Newton mass test.
