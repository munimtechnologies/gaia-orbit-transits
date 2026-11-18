# gaia-orbit-transits: current status (2026-11-18, v0.22.0)

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
     **Gaia DR4 will decide.**
     - The test is pre-registered 14 days before the release
       (`findings/2026-11-18-calib-dr4-prereg.md`).
     - Amendment 1 (0.21.0, `findings/2026-11-18-calib-dr4-amendment-1.md`) fixes the
       tables, the match and solution rules, and adds a paired test K2b. Both were written
       before any DR4 data exist.
   - **0.21.0 adds the release-day code.** `dr4_fetch.py` does the DR4 cross-match and
     orbit fetch and checks every table and column in TAP_SCHEMA. `calib_dr4_run.py` runs
     the whole test.
     - A DR3 dress rehearsal (job gaia-calibdr4-reh-v1, queued) runs the same code with DR3
       as the "new" release. Every orbit must come back unchanged.
2. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?** First results in
   0.19.0: `findings/2026-11-18-sb1-transit-results.md`.
   - TESS was searched at the Gaia period for 512 random DR3 SB1 orbits (P = 1–13 d,
     G ≤ 13, minimum companion mass 5–105 M_Jup).
   - 17 substellar-size hits, against 91.6 expected if every orbit were real and 7.5
     expected false alarms.
   - **ρ = 0.10 (95% CI 0.03–0.22)**: most of these orbits are not both real and truly
     that light. The hit rule was fooled by outlying points (C2 and H3 failed), so the true ρ
     is lower still. **No new brown dwarf is claimed.** The only clean transit in the random
     sample is the known TOI-6218.01.
   - A re-run with an outlier-proof median rule on ~2,600 stars is pre-registered
     (`findings/2026-11-18-sb1-robust-prereg.md`, jobs gaia-sb1rob-k0…k7-v1, queued).
   - The Gaia DR4 test of *why* is pre-registered
     (`findings/2026-11-18-dr4-sb1-reality-prereg.md`). Noise orbits should vanish in DR4.
     Real signals from something other than a brown dwarf should persist and still not
     transit.
     - Amendment 1 (`findings/2026-11-18-dr4-sb1-reality-amendment-1.md`): DR4 epoch RVs
       are fetched through DataLink, with fixed epoch-counting rules.
     - **0.22.0 adds the release-day code, `dr4_sb1_reality.py`**, and amendment 2
       (`findings/2026-11-18-dr4-sb1-reality-amendment-2.md`), which fixes every rule the
       code had to choose. The main one: DR4 has a second orbit table,
       `rvs_two_body_orbit` (638,966 rows), next to `nss_two_body_orbit`. Orbits are read
       from both, in a fixed order, so a real orbit in the second table is not miscounted
       as "dropped". Other rules: K from Thiele-Innes C/H for combined solutions; how the
       epoch-RV DataLink product is identified; the circular epoch-RV fit; the D3 statistic.
     - A DR3 dress rehearsal (job gaia-sb1real-reh-v1, queued) must return all 6,434 S3
       orbits CONFIRMED and show that the DataLink transport works.
   - Both leads point the same way: near the limits of DR3, a sizeable fraction of
     published orbits, or of their errors, cannot be taken at face value.
3. **Are M dwarfs in 1–2-day orbits inflated?** Graded against BHAC15 in 0.21.0:
   `findings/2026-11-18-eblm-infl-results.md`.
   - 14 Gaia-weighed systems at P = 0.9–2.2 d give a median of **+2.2% (95% CI +0.3% to
     +7.1%)**. As pre-registered, that is **INCONCLUSIVE**: it includes both the ~3% norm
     and Swayne et al.'s ~6%.
   - **No trend toward shorter periods** (ρ = +0.49, the opposite sign), but period is
     confounded with companion mass in this sample.
   - The test moves to DR4. Chunks gaia-eblm-rest-a/b-v1 are queued.

## Closed with a null result
- **White-dwarf self-lensing at Gaia-predicted conjunctions (DR3)**
  (`findings/2026-11-18-selflens-vet-results.md`). Of 19 brightenings, 13 were rejected,
  4 could not be measured and 2 passed the vet but fail physical checks. No candidate is
  claimed. Four rule changes are written down for DR4.

## Corrected
- **CD-48 897 (TIC 200743349) is not a new discovery of ours.** *Eclipses by Appointment*
  (github.com/Snowstar38/eclipses-by-appointment) listed it first (claim Q031).
- TOI-710.01 was already a TFOP false positive (eclipses every 72.082 d, a third of the TOI
  period, matching Gaia's SB1 orbit within 2.8σ).

## Refuted or closed
- TIC 207399049: refuted.
- Archival dips for the 25-star watch list: 0 found, where 0.28 were expected.
- Two "stripped companion" candidates are more likely blends or triples.

## Lessons the pipeline now encodes
- **A box depth is a mean, so a few outliers can fake a transit.** Fold searches require
  the in-box median to agree with the mean (`sb1_robust.py`).
- **Never skip a window that is too wide; cap it.** calib 0.7.0 skipped windows wider than
  P/4, which lost one real eclipse. DR4 code uses capped 6σ windows from the start.
- A query that silently drops columns changes the sample. Jobs now stop instead.
- **Rehearse release-day code on the previous release.** Running the DR4 pipeline with DR3
  as "DR4" must return every orbit unchanged before the real data arrive.
- **Read every table that can hold the thing you count.** A "dropped" orbit may simply live
  in another table. If an orbit table exists but can't be read, the run stops.

## Prior-art sources we check for every eclipsing system
AAVSO VSX, the TESS EB catalogue (Prša et al. 2022), Gaia DR3 vari_eclipsing_binary,
ExoFOP, SIMBAD, the Chopard-Vilhem Zenodo deposits (10.5281/zenodo.22998328 and
10.5281/zenodo.23342416) and the *Eclipses by Appointment* claim tables.

## Gaia DR4 (2 December 2026)
- ESA's DR4 contents page (read 2026-11-18) lists these tables:
  - `nss_two_body_orbit`: 5,901,111 rows, TAP, consolidated from several pipelines; plus a
    bright-source `_supp` table;
  - `rvs_two_body_orbit`: 638,966 rows, TAP; spectroscopic-binary solutions from the Line
    Integral Analysis modules;
  - `dr3_neighbourhood`: 2,448,832,159 rows, TAP; this is the DR3 → DR4 cross-match;
  - `nss_masses`: 4,323,300 rows; `nss_acceleration_astro`: 3,365,947 rows;
  - `rvs_epoch_parameters_single`, `epoch_astrometry` and `epoch_photometry`: **DataLink
    only**.
- The draft data model (2026-06-26) also lists 2,392,500 eclipsing binaries, 1,007 transit
  candidates and 6,224 compact-companion candidates.
- `dr4_datamodel.py` 0.2.0 (job gaia-dr4dm-v2, queued) extracts the full text, for the
  exact columns and the corr_vec order.
- Pre-registered order:
  1. the DR3 → DR4 orbit-survival tests: the SB1 reality test (`dr4_sb1_reality.py`) and
     the eclipse-deficit test (`calib_dr4_run.py`);
  2. the SB1 transit-rate test (0.2.0 rules) on DR4's new RVS SB1 orbits;
  3. the inclination and timing calibration on DR4's own orbits;
  4. EBLM inflation on DR4 SB1 × eclipsing binaries, with the k-at-bound rule;
  5. the RV transit screen;
  6. exoplanet candidates;
  7. self-lensing with the four new rules and the Kepler positive controls.
