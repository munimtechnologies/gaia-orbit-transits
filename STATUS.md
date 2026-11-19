# gaia-orbit-transits: current status (2026-11-19, v0.24.0)

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
     - **new in 0.24.0:** `findings/2026-11-19-dr4-wobble-prereg.md`. It looks for the
       photocentre wobble at the DR3 period in DR4's raw along-scan epoch astrometry, for the
       eclipsing and the non-eclipsing targets separately. It is rehearsed on ESA's
       pre-released epoch astrometry.
2. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?**
   - **0.1.0** (`findings/2026-11-18-sb1-transit-results.md`): ρ = 0.10 (0.03–0.22) from 512
     orbits. The hit rule was fooled by outlying points.
   - **0.2.0, the outlier-proof rerun: 2 of 8 chunks are in.** These are interim and
     descriptive, and the grade combines all 8 chunks.
     (`findings/2026-11-18-sb1-robust-k7-interim.md`,
     `findings/2026-11-19-sb1-robust-k0-interim.md`)
     - Chunks 0 and 7 summed: 9 robust hits in 944 sensitive stars, against 170 expected
       if every orbit were real. ρ (substellar size) = 0.018 (0.004–0.052).
     - **No substellar-size transit in 679 brown-dwarf-mass orbits, where 127 were
       expected.** At 95%, fewer than 3% are both real and that light.
     - The median rule removed 65 of the 74 hits the old rule would have made.
   - **A flaw found and fixed before the rest of the data (amendment 1,
     `findings/2026-11-19-sb1-robust-amendment-1.md`).** In 17.6% of the pool (1,132 stars),
     luminous stars with no Gaia radius were given a clamped 1.9 R☉ main-sequence radius,
     which biases ρ low. The primary grade stays as pre-registered. A secondary grade (A1)
     without them is computed by the new `sb1_combine.py` (job gaia-sb1comb-v1).
   - **Survivors and rejections (D1):**
     - **TIC 71945261** (chunk 7): a clean ~6% eclipse, about three times deeper than Gaia's
       0.097 M☉ companion allows. A pre-registered fit is queued
       (`findings/2026-11-18-tic71945261-prereg.md`).
     - **TIC 324597856** (chunk 0): rejected as a brown dwarf. It has a secondary eclipse half
       as deep as the primary, so the companion is a star. It is a probable new eclipsing
       binary whose Gaia orbit (K, e) is distorted, most likely by blended lines.
   - The Gaia DR4 test of *why* the orbits fail is pre-registered, with release-day code
     (`dr4_sb1_reality.py`, amendments 1–2; amendment 1 above adds the radius rule).
3. **Are M dwarfs in 1–2-day orbits inflated?** +2.2% (95% CI +0.3% to +7.1%) from 14
   systems: **INCONCLUSIVE**, as pre-registered (`findings/2026-11-18-eblm-infl-results.md`).
   It moves to DR4.

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
- **Never skip a window that is too wide; cap it.**
- A query that silently drops columns changes the sample. Jobs now stop instead.
- **Rehearse release-day code on the previous release** (or on a pre-release sample).
- **Read every table that can hold the thing you count.**
- **Check that a catalogue service is actually up before reading "no rows" as "not
  listed".**

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
  1. the DR3 → DR4 orbit-survival tests (`dr4_sb1_reality.py`, `calib_dr4_run.py`);
  2. the wobble test (`dr4_wobble.py`, owed before release);
  3. the SB1 transit-rate test (0.2.0 rules plus amendment 1) on DR4's RVS SB1 orbits;
  4. the inclination and timing calibration on DR4's own orbits;
  5. EBLM inflation;
  6. the RV transit screen;
  7. exoplanet candidates;
  8. self-lensing.
