# gaia-orbit-transits: current status (2026-11-18, v0.23.0)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Leads
1. **Do Gaia DR3 inclinations hold up against real eclipses?** Graded in 0.20.0:
   `findings/2026-11-18-calib-window-results.md`.
   - Of 162 near-edge-on DR3 orbits that TESS covered, 50 eclipse within ±3σ of Gaia's
     predicted time, where the published errors predict 69 (p = 1.4 × 10⁻⁴).
   - **The shortfall is real, not a timing artefact.** With windows three times wider,
     58 eclipse against 80.7 expected (ratio 0.72, p = 2 × 10⁻⁵).
   - **Gaia DR3's predicted conjunction times are too optimistic by ×1.8** (95%:
     1.2–2.8), measured from 49 real eclipses.
   - **If the orbits are right, σ(cos i) is understated by k = 2.1 (1.4–3.4).** This matches
     Makarov's (2025) simulated factor of 2.3. As far as we know it is the first measurement
     with real eclipses.
   - The same data fit "about a third (14–56%) of these orbits are wrong" equally well.
     **Gaia DR4 will decide.** The test is pre-registered
     (`findings/2026-11-18-calib-dr4-prereg.md`, amendment 1) and its release-day code is in
     0.21.0 (`dr4_fetch.py`, `calib_dr4_run.py`).
     - A DR3 dress rehearsal (gaia-calibdr4-reh-v1) is still waiting for compute.
2. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?**
   - **0.1.0** (`findings/2026-11-18-sb1-transit-results.md`): ρ = 0.10 (0.03–0.22) from 512
     orbits. The hit rule was fooled by outlying points.
   - **0.2.0, the outlier-proof rerun, first chunk in (0.23.0).** This is interim and
     descriptive; the grade combines all 8 chunks.
     (`findings/2026-11-18-sb1-robust-k7-interim.md`)
     - Chunk 7: 2 robust hits in 443 sensitive stars, against 82.1 expected if every orbit
       were real. ρ = 0.024 (0.003–0.088).
     - **No transit in 322 brown-dwarf-mass orbits, where 61 were expected.**
     - The median rule removed 26 of the 28 hits the old rule would have made.
   - **One survivor: TIC 71945261 (Gaia DR3 6853008555751131648).**
     - A clean ~6% eclipse at the Gaia period, on a star that is not a TOI and not in VSX
       or the TESS EB catalogue.
     - It is about three times deeper than Gaia's 0.097 M☉ companion allows.
     - Either Gaia's mass is wrong or the companion is oversized. A pre-registered fit
       separates the two (`findings/2026-11-18-tic71945261-prereg.md`, `eblm_single.py`,
       job gaia-tic71945261-v1).
   - The Gaia DR4 test of *why* is pre-registered, with release-day code
     (`dr4_sb1_reality.py`, amendments 1–2). Its DR3 rehearsal (gaia-sb1real-reh-v1) is
     queued.
3. **Are M dwarfs in 1–2-day orbits inflated?** Graded against BHAC15 in 0.21.0:
   `findings/2026-11-18-eblm-infl-results.md`.
   - Median of **+2.2% (95% CI +0.3% to +7.1%)** from 14 systems: **INCONCLUSIVE**, as
     pre-registered.
   - It moves to DR4. Chunks gaia-eblm-rest-a/b-v1 are queued.

## Closed with a null result
- **White-dwarf self-lensing at Gaia-predicted conjunctions (DR3)**
  (`findings/2026-11-18-selflens-vet-results.md`). No candidate is claimed. Four rule
  changes are written down for DR4.

## Corrected
- **CD-48 897 (TIC 200743349) is not a new discovery of ours.** *Eclipses by Appointment*
  (github.com/Snowstar38/eclipses-by-appointment) listed it first (claim Q031).
- TOI-710.01 was already a TFOP false positive.

## Refuted or closed
- TIC 207399049: refuted.
- Archival dips for the 25-star watch list: 0 found, where 0.28 were expected.
- Two "stripped companion" candidates are more likely blends or triples.

## Lessons the pipeline now encodes
- **A box depth is a mean, so a few outliers can fake a transit.** Fold searches require
  the in-box median to agree with the mean (`sb1_robust.py`). In chunk 7 this removed 26 of
  28 hits.
- **Never skip a window that is too wide; cap it.**
- A query that silently drops columns changes the sample. Jobs now stop instead.
- **Rehearse release-day code on the previous release.**
- **Read every table that can hold the thing you count.**
- **Check that a catalogue service is actually up before reading "no rows" as "not
  listed".** VizieR returned empty results while its database was down on 2026-11-18.

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API), the TESS EB catalogue (Prša et al. 2022), Gaia DR3 vari_eclipsing_binary,
ExoFOP, SIMBAD, the Chopard-Vilhem Zenodo deposits (10.5281/zenodo.22998328 and
10.5281/zenodo.23342416) and the *Eclipses by Appointment* claim tables.

## Gaia DR4 (2 December 2026)
- Tables (ESA contents page, read 2026-11-18):
  - `nss_two_body_orbit` (5.9M) + `_supp`;
  - `rvs_two_body_orbit` (639k);
  - `dr3_neighbourhood` (2.45B);
  - `nss_masses`, `nss_acceleration_astro`.
  - DataLink-only epoch products: RVS epoch parameters, epoch astrometry and epoch
    photometry.
- Pre-registered order:
  1. the DR3 → DR4 orbit-survival tests (`dr4_sb1_reality.py`, `calib_dr4_run.py`);
  2. the SB1 transit-rate test (0.2.0 rules) on DR4's RVS SB1 orbits;
  3. the inclination and timing calibration on DR4's own orbits;
  4. EBLM inflation;
  5. the RV transit screen;
  6. exoplanet candidates;
  7. self-lensing.
