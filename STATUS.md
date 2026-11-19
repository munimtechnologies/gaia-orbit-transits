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
       published orbits. The DR3 dress rehearsal caught a wrong column-name assumption
       before release day; amendment 2 (`findings/2026-11-19-calib-dr4-amendment-2.md`) fixes
       it in `dr4_fetch.py` 0.2.0 (v0.28.0). The rehearsal is re-queued (gaia-calibdr4-reh-v2).
     - `findings/2026-11-19-dr4-wobble-prereg.md` + amendment 1, with code `dr4_wobble.py`
       0.1.0. **The rehearsal on ESA's 12-source DR4 pre-release passed**
       (`findings/2026-11-19-dr4-wobble-rehearsal-results.md`).
2. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?**
   - **0.1.0** (`findings/2026-11-18-sb1-transit-results.md`): ρ = 0.10 (0.03–0.22) from 512
     orbits. The hit rule was fooled by outlying points.
   - **0.2.0, the outlier-proof rerun: all 8 chunks are in**
     (`findings/2026-11-19-sb1-robust-k4-k6-interim.md`; earlier: k3+k5, k2, k0, k1, k7).
     The pre-registered combined grade (gaia-sb1comb-v2) is queued. Hand sums, interim:
     - 25 robust hits in 3,113 sensitive stars, against 558 expected if every orbit were
       real. ρ (substellar size) = 0.016 (0.007–0.031).
     - **In 2,180 brown-dwarf-mass orbits, 408 transits were expected and three are seen**
       (TOI-6218.01, TOI-5427.01, TOI-5882.01, all known). ρ_BD = 0.007 (0.002–0.022).
     - The very-low-mass-star orbits do better, at ~5% (2–11%).
     - Chunk 5 fails the per-job size check C3 (141 < 150 stars). The combined report will say
       so.
   - **Amendment 1** (`findings/2026-11-19-sb1-robust-amendment-1.md`): 17.6% of the pool are
     luminous stars that entered with a fallback main-sequence radius, which biases ρ low. A
     secondary grade (A1) without them comes from the same combine job.
   - **Amendment 2** (`findings/2026-11-19-sb1-robust-amendment-2-inclination.md`, code
     `inclination_floor.py` 0.1.0 in v0.29.0, job gaia-incfloor-v1 queued). A missing-transit
     rate measures "real orbit AND near edge-on". Brown dwarfs are rare in close orbits, so right
     orbits of heavier stars seen nearly face-on are a known, large contaminant. The amendment
     computes the fraction φ of orbits that are right under a fixed grid of companion
     populations. **Until it is graded, "most of these orbits are not real" is not a supported
     claim.**
   - The Gaia DR4 test of *why* the orbits fail is pre-registered, with release-day code
     (`dr4_sb1_reality.py`; amendments 1–3; `dr4_d3_a1.py` and `dr4_d5_rate.py`). **All of its
     DR3 rehearsals have now passed**: the pool (RH1–RH3), and on 19 Nov the DataLink step
     (RH4) through the exact release-day fetch path
     (`findings/2026-11-19-bd65-286-fit-results.md`, last section; `data/sb1real-reh-v2/`).
     The D5 pool rehearsal passed too (`findings/2026-11-19-d5-pool-rehearsal-results.md`).
   - **Eclipsing companions found by the search:**
     - **TIC 71945261** (TYC 6340-23-1, chunk 7). Fit graded 19 Nov
       (`findings/2026-11-19-tic71945261-fit-results.md`): pre-registered label
       **B_OVERSIZED_COMPANION**, as predicted. A new 2.3287-day eclipsing system (6.1% deep,
       equal odd/even eclipses, 0.39% occultation) whose companion's radius is **0.224 R☉** at
       Gaia's 0.097 M☉, **1.9× the main-sequence value**. Youth or a wrong Gaia mass are not
       yet excluded, so we do not call it "inflated"; a youth and archival-RV check is queued
       (`findings/2026-11-19-tic71945261-followup-prereg.md`).
     - **BD+65 286** (TIC 50453242, chunk 3). **Fit run 19 Nov**
       (`findings/2026-11-19-bd65-286-fit-results.md`): every pre-registered number held
       (eblm_fit EBLM_CONSISTENT; companion **0.100 M☉, 0.122 R☉**, +1% above the
       main-sequence radius, +9% with Gaia's FLAME primary radius; Gaia's mass confirmed by the
       ellipsoidal signal at 0.81 of prediction). **But the job's control, TOI-1251.01, failed
       its prediction, and our rule says the other labels are then not interpreted, so the
       label is not graded.** A new control set of six published EBLMs (Swayne et al. 2024)
       is pre-registered (`findings/2026-11-19-eblm-control-prereg.md`, job gaia-eblmctl-v1).
       The eclipse itself is in all 8 TESS sectors at Gaia's period. Prior art: Green et al.
       2023 (ellipsoidal candidate, same period) and NASA SPOC's sector-52 TCE (2022).
     - **TOI-7247.01** (chunk 5): our prediction (C or B) failed; it came out D (odd and even
       eclipses differ at Gaia's period). Not interpreted; no statement about the TOI.
     - **TIC 324597856** (chunk 0): rejected as a brown dwarf (secondary eclipse half as deep).
     - **TIC 135050395** (chunk 1): the known EBLM J1219-39, not new.
     - **TIC 202283090** (chunk 1): TOI-6218.01, an existing TFOP candidate.
3. **Are M dwarfs in short orbits inflated? Graded on the full DR3 sample, 19 Nov**
   (`findings/2026-11-19-eblm-infl-full-results.md`):
   - 28 M dwarfs (0.24–0.60 M☉) in 0.89–3.52-day orbits sit **+6.3% (95% CI +1.0% to
     +8.8%)** above BHAC15 5-Gyr radii. Pre-registered label **INCONCLUSIVE**.
   - **No sign that shorter orbits inflate more** (H2: NO_TREND_DETECTED; ρ = +0.49).
   - Our prediction that the heavier companions would pull the median down **failed**.
   - **The pipeline's radius scale has not yet been checked against independently measured
     systems.** The control test above (gaia-eblmctl-v1) does that; if its median offset is
     beyond ±3%, this grade gets an addendum.

## Closed with a null result
- **White-dwarf self-lensing at Gaia-predicted conjunctions (DR3)**
  (`findings/2026-11-18-selflens-vet-results.md`).

## Corrected
- **"Most brown-dwarf-mass orbits are not real" was premature.** See amendment 2 above.
- **BD+65 286's variability and period were already published** (Green et al. 2023). The
  claim is narrowed in `findings/2026-11-19-bd65-286-prior-art-addendum.md`.
- **CD-48 897 (TIC 200743349) is not a new discovery of ours.** *Eclipses by Appointment*
  listed it first (claim Q031).
- TOI-710.01 was already a TFOP false positive.

## Refuted or closed
- TIC 207399049: refuted.
- Archival dips for the 25-star watch list: 0 found, where 0.28 were expected.
- Two "stripped companion" candidates are more likely blends or triples.

## Lessons the pipeline now encodes
- **A box depth is a mean, so a few outliers can fake a transit.** Fold searches require
  the in-box median to agree with the mean (`sb1_robust.py`).
- **A fallback table that clamps can carry a whole population through a cut.**
- **A rule fixed for one release must be applied by importing it, not by copying it.**
- **Never skip a window that is too wide; cap it.** **Never truncate a query at the row cap;
  split it.**
- **Rehearse release-day code on the previous release.**
- **Don't assume a new table's column names; read TAP_SCHEMA.**
- **Pair every empty answer with a control query.** On 19 Nov a position search on
  `nss_two_body_orbit` returned nothing even for BD+65 286: that table's ra/dec are empty for
  SB1 solutions, so positions must come from `gaia_source`.
- **A threshold-crossing event is not a catalogue entry, but it is prior art.**
- **Vet a comparison system like a candidate, and prefer controls with independently
  published answers.** TOI-1251.01 was a known EB; it failed as a control twice, and under our
  own rule that left BD+65 286's label ungraded.
- **A minimum mass is not a mass.**

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API), the TESS EB catalogue (Prša et al. 2022), the TESS Ten Thousand catalogue
(Kostov et al. 2025, J/ApJS/279/50), Gaia DR3 vari_eclipsing_binary and vari_classifier_result,
the ZTF (Chen et al. 2020) and ASAS-SN variable catalogues, Green et al. (2023) TESS
ellipsoidal candidates (J/MNRAS/522/29), ExoFOP, the SPOC TCE list (MAST DV API), SIMBAD, the
Chopard-Vilhem Zenodo deposits and the *Eclipses by Appointment* claim tables.

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** Every DR3 rehearsal has to run before then. Done: wobble, D5 pool,
  sb1real (pool + DataLink). Queued: calib-dr4 v2, the pinned-fetch check, and the EBLM
  control test.
- Release-day runbook: `runbook/dr4-release-day.md`, with `runbook/release/fetch_release.py`
  pinning every module to the commit that published it.
- Tables: `nss_two_body_orbit` + `_supp`, `rvs_two_body_orbit`, `dr3_neighbourhood`,
  `nss_masses`, `nss_acceleration_astro`, `nss_epoch_flags`, `rvs_epoch_parameters_single`
  (all in ESA's draft DR4 data model). Epoch photometry is DataLink-only.
- Pre-registered order:
  1. the DR3 → DR4 orbit-survival tests (`dr4_sb1_reality.py` with `dr4_d3_a1.py`, and
     `calib_dr4_run.py`);
  2. the wobble test (`dr4_wobble.py release`);
  3. the SB1 transit-rate test on DR4's new SB1 orbits (D5);
  4. the inclination and timing calibration on DR4's own orbits;
  5. EBLM inflation;
  6. the RV transit screen;
  7. exoplanet candidates;
  8. self-lensing.
- On the day, also look up BD+65 286 and TIC 71945261 in DR4's orbit tables.
