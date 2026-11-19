# gaia-orbit-transits: current status (2026-11-19)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Leads
1. **Do Gaia DR3 inclinations hold up against real eclipses?** Graded in 0.20.0:
   `findings/2026-11-18-calib-window-results.md`.
   - Of 162 near-edge-on DR3 orbits that TESS covered, 50 eclipse within ±3σ of Gaia's
     predicted time, where the published errors predict 69 (p = 1.4 × 10⁻⁴).
   - With windows three times wider, 58 eclipse against 80.7 expected (ratio 0.72,
     p = 2 × 10⁻⁵).
   - **Gaia DR3's predicted conjunction times are too optimistic by ×1.8** (95%: 1.2–2.8).
     **If the orbits are right, σ(cos i) is understated by k = 2.1 (1.4–3.4).**
   - "About a third (14–56%) of these orbits are wrong" fits equally well. **Gaia DR4 will
     decide.** There are two pre-registered tests:
     - `findings/2026-11-18-calib-dr4-prereg.md` (amendment 1), which uses DR4's published
       orbits;
     - `findings/2026-11-19-dr4-wobble-prereg.md` + amendment 1, with release-day code
       `dr4_wobble.py` 0.1.0 (0.25.0). It looks for the photocentre wobble at the DR3 period
       in DR4's raw along-scan epoch astrometry. A rehearsal on ESA's 12-source DR4
       pre-release is queued (job gaia-wobble-reh-v1). It passes if HD 114762 wobbles at its
       DR3 orbit (Δχ² > 30) and the three quasars do not.
2. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?**
   - **0.1.0** (`findings/2026-11-18-sb1-transit-results.md`): ρ = 0.10 (0.03–0.22) from 512
     orbits. The hit rule was fooled by outlying points.
   - **0.2.0, the outlier-proof rerun: 4 of 8 chunks are in** (k0, k1, k2, k7). These are
     interim and descriptive; the grade combines all 8 chunks. The other four are queued.
     (`findings/2026-11-19-sb1-robust-k2-interim.md`; earlier: k0, k1, k7)
     - The four chunks summed: 14 robust hits in 1,633 sensitive stars, against 294
       expected if every orbit were real. ρ (substellar size) = 0.017 (0.006–0.040).
     - **In 1,174 brown-dwarf-mass orbits, 220 transits were expected and one is seen**:
       TOI-6218.01, at 71 M_Jup by Gaia's orbit, right at the brown-dwarf/star boundary.
     - The very-low-mass-star orbits do better, at ~7% (2–17%). They include J1219-39, a
       published EBLM (Triaud et al. 2013) that the pipeline recovered blind. Gaia's mass
       for it (0.094 M☉) matches the RV mass.
   - **Amendment 1** (`findings/2026-11-19-sb1-robust-amendment-1.md`): 17.6% of the pool are
     luminous stars that entered with a fallback main-sequence radius, which biases ρ low. A
     secondary grade (A1) without them comes from `sb1_combine.py` once all 8 chunks are in.
     Chunk 2 gave an outside check: its one rate-sample hit (TIC 412083925) had a 1.3 R☉
     table radius, but the TESS Input Catalog lists 4.9 R☉. The rule's `giant_cmd` test
     already removes it.
     - `dr4_d3_a1.py` 0.1.0 (0.26.0) applies the rule to the TESS grade (D3) of the DR4
       orbit-survival test.
     - **D5**, which asks whether DR4's *new* low-mass SB1 orbits are purer than DR3's:
       `findings/2026-11-19-dr4-sb1-reality-amendment-3.md` fixes the rules.
       - The pool reads every DR4 orbit table and applies the DR3 cuts unchanged.
       - It drops flagged radii *before* sampling, by importing `sb1_combine.radius_flag`.
       - It counts an orbit as new only if no DR3 neighbour within 1″ had an SB1 orbit at
         any period.
       - Code: `dr4_d5_rate.py` 0.1.0, committed only after its unit tests pass. A DR3
         rehearsal of the pool step is queued (job gaia-d5pool-reh-v2). It must reproduce
         the 6,434-star pool and find every star in DR3.
   - **Survivors and rejections (D1):**
     - **TIC 71945261** (chunk 7): a clean ~6% eclipse, about three times deeper than Gaia's
       0.097 M☉ companion allows. A pre-registered fit is queued
       (`findings/2026-11-18-tic71945261-prereg.md`).
     - **TIC 324597856** (chunk 0): rejected as a brown dwarf. It has a secondary eclipse half
       as deep as the primary, so the companion is a star.
     - **TIC 135050395** (chunk 1): the known EBLM J1219-39, not new.
     - **TIC 202283090** (chunk 1): TOI-6218.01, an existing TFOP candidate. Gaia's orbit and
       TESS's transit agree.
     - Chunk 2 has no substellar-size hit.
   - The Gaia DR4 test of *why* the orbits fail is pre-registered, with release-day code
     (`dr4_sb1_reality.py`, amendments 1–3, `dr4_d3_a1.py` and `dr4_d5_rate.py`).
3. **Are M dwarfs in 1–2-day orbits inflated?** +2.2% (95% CI +0.3% to +7.1%) from 14
   systems: **INCONCLUSIVE**, as pre-registered (`findings/2026-11-18-eblm-infl-results.md`).
   - `findings/2026-11-19-eblm-rest-results.md` (0.26.0): the other 97 EBLM-like systems are
     fitted. None is missing, and the raw outputs are in `data/eblm-rest-v1/`. By hand, 14
     more systems pass the main-set cuts (m2 = 0.43–0.60 M☉).
   - The pre-registered full-sample grade (`combine_eblm_full.py`, then `eblm_infl` 0.1.0
     unchanged on all 167 rows) is queued as job gaia-eblm-infl-full-v1.

## Closed with a null result
- **White-dwarf self-lensing at Gaia-predicted conjunctions (DR3)**
  (`findings/2026-11-18-selflens-vet-results.md`).

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
  the in-box median to agree with the mean (`sb1_robust.py`).
- **A fallback table that clamps can carry a whole population through a cut.** Check what
  every fallback value does at the table's edges, and count how many rows sit exactly on a
  fallback value.
- **A rule fixed for one release must be applied by importing it, not by copying it.** The
  DR4 grades (`dr4_d3_a1.py`, `dr4_d5_rate.py`) import `sb1_combine.radius_flag`.
- **Never skip a window that is too wide; cap it.** **Never truncate a query at the row cap;
  split it.**
- A query that silently drops columns changes the sample. Jobs now stop instead.
- **Rehearse release-day code on the previous release** (or on a pre-release sample).
  **Read the real file layout before release day.** DR4's epoch astrometry is one row per
  transit with per-CCD arrays, not one row per CCD (wobble amendment 1).
- **Read every table that can hold the thing you count.**
- **Check that a catalogue service is actually up before reading "no rows" as "not
  listed".** Since 9 November, CDS Strasbourg (SIMBAD, VizieR) has been degraded by a
  security incident. We use the CfA VizieR mirror.

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API), the TESS EB catalogue (Prša et al. 2022), Gaia DR3 vari_eclipsing_binary,
the ZTF (Chen et al. 2020) and ASAS-SN variable catalogues, Green et al. (2023) TESS
ellipsoidal candidates, ExoFOP, SIMBAD, the Chopard-Vilhem Zenodo deposits
(10.5281/zenodo.22998328 and 10.5281/zenodo.23342416) and the *Eclipses by Appointment*
claim tables.

## Gaia DR4 (2 December 2026)
- Tables: `nss_two_body_orbit` (5.9M) + `_supp`, `rvs_two_body_orbit` (639k),
  `dr3_neighbourhood`, `nss_masses` and `nss_acceleration_astro`. DataLink-only epoch
  products: RVS epoch parameters, epoch astrometry (`EPOCH_ASTROMETRY`) and epoch photometry.
- Pre-registered order:
  1. the DR3 → DR4 orbit-survival tests (`dr4_sb1_reality.py` with `dr4_d3_a1.py` for D3,
     and `calib_dr4_run.py`);
  2. the wobble test (`dr4_wobble.py release`);
  3. the SB1 transit-rate test on DR4's new SB1 orbits (D5: `dr4_d5_rate.py`, amendment 3);
  4. the inclination and timing calibration on DR4's own orbits;
  5. EBLM inflation;
  6. the RV transit screen;
  7. exoplanet candidates;
  8. self-lensing.
