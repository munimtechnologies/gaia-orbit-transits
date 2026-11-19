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
     - `findings/2026-11-18-calib-dr4-prereg.md` (amendments 1 and 2), which uses DR4's
       published orbits. **The DR3 dress rehearsal caught a wrong column-name assumption**
       (ESA's neighbourhood tables name the new id `dr3_source_id`, not `source_id`) before
       release day. Amendment 2 (`findings/2026-11-19-calib-dr4-amendment-2.md`) fixes it in
       `dr4_fetch.py` 0.2.0 and the modules that use it. The rehearsal is re-queued
       (gaia-calibdr4-reh-v2).
     - `findings/2026-11-19-dr4-wobble-prereg.md` + amendment 1, with code `dr4_wobble.py`
       0.1.0. **The rehearsal on ESA's 12-source DR4 pre-release passed**
       (`findings/2026-11-19-dr4-wobble-rehearsal-results.md`):
       - HD 114762's orbit is recovered from DR4's raw epoch astrometry at Δχ² = 60.5,
         a₀ ratio 1.05;
       - all three quasars are at Δχ² ≤ 2.1;
       - Gaia-4's planet-host orbit is recovered at Δχ² = 82.8.
2. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?**
   - **0.1.0** (`findings/2026-11-18-sb1-transit-results.md`): ρ = 0.10 (0.03–0.22) from 512
     orbits. The hit rule was fooled by outlying points.
   - **0.2.0, the outlier-proof rerun: 6 of 8 chunks are in** (k0, k1, k2, k3, k5, k7). These
     are interim and descriptive; the grade combines all 8 chunks. Chunks 4 and 6 are queued.
     (`findings/2026-11-19-sb1-robust-k3-k5-interim.md`; earlier: k2, k0, k1, k7)
     - Six chunks summed: 17 robust hits in 2,058 sensitive stars, against 371 expected if
       every orbit were real. ρ (substellar size) = 0.016 (0.006–0.035).
     - **In 1,466 brown-dwarf-mass orbits, 276 transits were expected and one is seen**:
       TOI-6218.01, at 71 M_Jup by Gaia's orbit, right at the brown-dwarf/star boundary.
     - The very-low-mass-star orbits do better, at ~6% (2–15%).
     - Chunk 5 fails the per-job size check C3 (141 < 150 stars) because MAST searches
       timed out during the job. The combined report will say so.
   - **Amendment 1** (`findings/2026-11-19-sb1-robust-amendment-1.md`): 17.6% of the pool are
     luminous stars that entered with a fallback main-sequence radius, which biases ρ low. A
     secondary grade (A1) without them comes from `sb1_combine.py` once all 8 chunks are in.
     Two hits have now shown the problem from outside: TIC 412083925 (chunk 2; the TESS Input
     Catalog lists 4.9 R☉) and Gaia DR3 209360173711680640 (chunk 3; M_G = −1.4, a luminous
     red giant). The rule's `giant_cmd` test removes both.
     - `dr4_d3_a1.py` 0.1.0 (0.26.0) applies the rule to the DR4 orbit-survival test.
     - **D5** (`findings/2026-11-19-dr4-sb1-reality-amendment-3.md`, `dr4_d5_rate.py`, now
       0.1.1) asks whether DR4's *new* low-mass SB1 orbits are purer than DR3's. A DR3
       rehearsal of its pool step is queued (job gaia-d5pool-reh-v2).
   - **Eclipsing companions found by the search (D1 and others):**
     - **BD+65 286** (TIC 50453242, chunk 3): a V ≈ 9.7 F star eclipsed every 1.6465 days by
       the ~0.1 M☉ companion of its Gaia orbit (0.4% deep, flat-bottomed, at Gaia's predicted
       conjunction in all three sectors). **Prior art, corrected 19 Nov:** Green et al. 2023
       list it as a TESS ellipsoidal binary candidate with the same period, and NASA's SPOC
       pipeline flagged the dip in 2022 (sector 52 TCE). No catalogue or paper identifies it
       as an *eclipsing* system or ties the eclipse, the ellipsoidal signal and the Gaia orbit
       to one ~0.1 M☉ star; that link and the fit's mass and radius are the new part.
       Remaining catalogue checks are done (ASAS-SN, ZTF, Kostov+ 2025, Chopard-Vilhem: none
       list it): `findings/2026-11-19-bd65-286-prior-art-addendum.md`. A pre-registered fit
       is queued (`findings/2026-11-19-bd65-286-prereg.md`).
     - **TIC 71945261** (chunk 7): a clean ~6% eclipse, about three times deeper than Gaia's
       0.097 M☉ companion allows. The full prior-art list is checked
       (`findings/2026-11-19-tic71945261-prior-art.md`). No catalogue, TCE or paper lists it
       as eclipsing or variable. A pre-registered fit is queued
       (`findings/2026-11-18-tic71945261-prereg.md`).
     - **TOI-7247.01** (chunk 5): already a TOI. TFOP calls it a false positive from the Gaia
       orbit; a 2026 RAVEN upload calls it a likely planet. It is fitted in the BD+65 286 job.
     - **TIC 324597856** (chunk 0): rejected as a brown dwarf. It has a secondary eclipse half
       as deep as the primary, so the companion is a star.
     - **TIC 135050395** (chunk 1): the known EBLM J1219-39, not new.
     - **TIC 202283090** (chunk 1): TOI-6218.01, an existing TFOP candidate.
   - The Gaia DR4 test of *why* the orbits fail is pre-registered, with release-day code
     (`dr4_sb1_reality.py`, now 0.1.1; amendments 1–3; `dr4_d3_a1.py` and `dr4_d5_rate.py`).
3. **Are M dwarfs in 1–2-day orbits inflated?** +2.2% (95% CI +0.3% to +7.1%) from 14
   systems: **INCONCLUSIVE**, as pre-registered (`findings/2026-11-18-eblm-infl-results.md`).
   - `findings/2026-11-19-eblm-rest-results.md` (0.26.0): the other 97 EBLM-like systems are
     fitted. The pre-registered full-sample grade (`combine_eblm_full.py`, then `eblm_infl`
     0.1.0 unchanged on all 167 rows) is queued as job gaia-eblm-infl-full-v1.

## Closed with a null result
- **White-dwarf self-lensing at Gaia-predicted conjunctions (DR3)**
  (`findings/2026-11-18-selflens-vet-results.md`).

## Corrected
- **BD+65 286's variability and period were already published** (Green et al. 2023,
  ellipsoidal candidate). Our pre-registration missed that catalogue; the claim is narrowed
  in `findings/2026-11-19-bd65-286-prior-art-addendum.md`.
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
- **A rule fixed for one release must be applied by importing it, not by copying it.**
- **Never skip a window that is too wide; cap it.** **Never truncate a query at the row cap;
  split it.**
- A query that silently drops columns changes the sample. Jobs now stop instead.
- **Rehearse release-day code on the previous release** (or on a pre-release sample). On
  19 November this caught a wrong column name that would have stopped three release-day
  tests on 2 December.
- **Don't assume a new table's column names from an older table's documentation; read the
  older table's TAP_SCHEMA.** Then accept only a short, fixed list of names.
- **Read every table that can hold the thing you count.**
- **Check that a catalogue service is actually up before reading "no rows" as "not
  listed".** CDS Strasbourg (SIMBAD, VizieR) has been degraded since 9 November. The CfA
  VizieR mirror was down early on 19 November and back by 09:12 UTC; the CfA SIMBAD mirror
  worked. The Gaia DataLink server answered 503 at 09:18 UTC on 19 November.
- **A threshold-crossing event is not a catalogue entry, but it is prior art.** Before calling
  an eclipse new, query the SPOC DV TCE list on MAST and credit any detection.
- **A close binary with an eclipse usually also has an ellipsoidal or reflection signal, and
  that may already be catalogued.** Run the whole prior-art list below before writing
  "not in any catalogue", including the ellipsoidal and machine-learning EB lists.

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API), the TESS EB catalogue (Prša et al. 2022), the TESS Ten Thousand catalogue
(Kostov et al. 2025, J/ApJS/279/50, including its unvetted list), Gaia DR3
vari_eclipsing_binary and vari_classifier_result, the ZTF (Chen et al. 2020) and ASAS-SN
variable catalogues, Green et al. (2023) TESS ellipsoidal candidates (J/MNRAS/522/29), ExoFOP,
the SPOC TCE list (MAST DV API), SIMBAD, the Chopard-Vilhem Zenodo deposits
(10.5281/zenodo.22998328 and 10.5281/zenodo.23342416) and the *Eclipses by Appointment* claim
tables.

## Gaia DR4 (2 December 2026)
- Tables: `nss_two_body_orbit` (5.9M) + `_supp`, `rvs_two_body_orbit` (639k),
  `dr3_neighbourhood`, `nss_masses` and `nss_acceleration_astro`. DataLink-only epoch
  products: RVS epoch parameters, epoch astrometry (`EPOCH_ASTROMETRY`) and epoch photometry.
- `dr3_neighbourhood`'s DR4 id column is read from TAP_SCHEMA (`dr4_source_id`, else
  `source_id`; anything else stops the run). See calib-dr4 amendment 2.
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
