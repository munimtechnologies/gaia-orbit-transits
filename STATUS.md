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
       `dr4_fetch.py` 0.2.0 and the modules that use it, **released in v0.28.0**. The
       rehearsal is re-queued (gaia-calibdr4-reh-v2).
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
     - Chunk 5 fails the per-job size check C3 (141 < 150 stars) because MAST searches
       timed out during the job. The combined report will say so.
   - **Amendment 1** (`findings/2026-11-19-sb1-robust-amendment-1.md`): 17.6% of the pool are
     luminous stars that entered with a fallback main-sequence radius, which biases ρ low. A
     secondary grade (A1) without them comes from the same combine job.
     - `dr4_d3_a1.py` 0.1.0 (0.26.0) applies the rule to the DR4 orbit-survival test.
     - **D5** (`findings/2026-11-19-dr4-sb1-reality-amendment-3.md`, `dr4_d5_rate.py`)
       asks whether DR4's *new* low-mass SB1 orbits are purer than DR3's.
   - **Eclipsing companions found by the search:**
     - **TIC 71945261** (TYC 6340-23-1, chunk 7). **Fit graded 19 Nov**
       (`findings/2026-11-19-tic71945261-fit-results.md`): pre-registered label
       **B_OVERSIZED_COMPANION**, as predicted.
       - It is a new 2.3287-day eclipsing system: 6.1% deep, with equal odd and even
         eclipses and a 0.39% occultation. No catalogue, TCE or paper lists it.
       - The companion's radius is **0.224 R☉** at Gaia's 0.097 M☉, **1.9× the main-sequence
         value**.
       - Young age or a wrong Gaia mass are not yet excluded, so we do not call it
         "inflated". A youth and archival-RV check is pre-registered
         (`findings/2026-11-19-tic71945261-followup-prereg.md`) and queued.
       - Gaia's own epoch-RV spread (32.5 km/s ≈ 2K) argues against a mass error; this is
         ungraded.
       - The comparison system TOI-1251.01 failed its prediction: we expected C and it came
         out D (odd/even differ). It is already in the TESS EB catalogue, which we should have
         checked first.
     - **BD+65 286** (TIC 50453242, chunk 3): a V ≈ 9.7 F star eclipsed every 1.6465 days by
       the ~0.1 M☉ companion of its Gaia orbit. **Prior art:** Green et al. 2023 list it as a
       TESS ellipsoidal binary candidate with the same period, and NASA's SPOC pipeline
       flagged the dip in 2022 (sector 52 TCE). The new part is the eclipse identification and
       the Gaia-mass link (`findings/2026-11-19-bd65-286-prior-art-addendum.md`). A
       pre-registered fit is queued (`findings/2026-11-19-bd65-286-prereg.md`).
     - **TOI-7247.01** (chunk 5): already a TOI. It is fitted in the BD+65 286 job.
     - **TIC 324597856** (chunk 0): rejected as a brown dwarf (secondary eclipse half as deep).
     - **TIC 135050395** (chunk 1): the known EBLM J1219-39, not new.
     - **TIC 202283090** (chunk 1): TOI-6218.01, an existing TFOP candidate.
   - The Gaia DR4 test of *why* the orbits fail is pre-registered, with release-day code
     (`dr4_sb1_reality.py`; amendments 1–3; `dr4_d3_a1.py` and `dr4_d5_rate.py`). Its DR3
     rehearsal reproduced the pool (RH1–RH3 pass). The DataLink step (RH4) could not be
     tested then because ESA's DataLink server answered 503. It answers again, and the
     re-test through the exact release-day path is queued (gaia-sb1real-reh-v2).
3. **Are M dwarfs in short orbits inflated? Graded on the full DR3 sample, 19 Nov**
   (`findings/2026-11-19-eblm-infl-full-results.md`):
   - 28 M dwarfs (0.24–0.60 M☉) in 0.89–3.52-day orbits, weighed with Gaia SB1 orbits and
     TESS eclipses, sit **+6.3% (95% CI +1.0% to +8.8%)** above BHAC15 5-Gyr radii.
     Pre-registered label **INCONCLUSIVE**: the interval excludes zero but not the 3% bar.
   - **No sign that shorter orbits inflate more** (pre-registered H2: NO_TREND_DETECTED). The
     rank correlation has the opposite sign (ρ = +0.49).
   - Our prediction that the heavier companions would pull the median down **failed**: it rose
     from +2.2% (14 systems) to +6.3% (28).
   - It agrees with Swayne et al. 2024's ~6% below 5 days and sits above EBLM XIX's
     0.3 ± 1.6% beyond 5 days (cross-study, different models).

## Closed with a null result
- **White-dwarf self-lensing at Gaia-predicted conjunctions (DR3)**
  (`findings/2026-11-18-selflens-vet-results.md`).

## Corrected
- **BD+65 286's variability and period were already published** (Green et al. 2023,
  ellipsoidal candidate). The claim is narrowed in
  `findings/2026-11-19-bd65-286-prior-art-addendum.md`.
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
- **A fallback table that clamps can carry a whole population through a cut.** Count how
  many rows sit exactly on a fallback value.
- **A rule fixed for one release must be applied by importing it, not by copying it.**
- **Never skip a window that is too wide; cap it.** **Never truncate a query at the row cap;
  split it.**
- **Rehearse release-day code on the previous release.** On 19 November this caught a wrong
  column name that would have stopped three release-day tests on 2 December.
- **Don't assume a new table's column names from an older table's documentation; read the
  older table's TAP_SCHEMA.**
- **Check that a catalogue service is actually up before reading "no rows" as "not
  listed".** Pair every empty answer with a control query.
- **A threshold-crossing event is not a catalogue entry, but it is prior art.** Query the
  SPOC DV TCE list on MAST and credit any detection.
- **Vet a comparison system like a candidate.** TOI-1251.01 was chosen as a "normal"
  comparison but was already in the TESS EB catalogue.

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API), the TESS EB catalogue (Prša et al. 2022), the TESS Ten Thousand catalogue
(Kostov et al. 2025, J/ApJS/279/50), Gaia DR3 vari_eclipsing_binary and vari_classifier_result,
the ZTF (Chen et al. 2020) and ASAS-SN variable catalogues, Green et al. (2023) TESS
ellipsoidal candidates (J/MNRAS/522/29), ExoFOP, the SPOC TCE list (MAST DV API), SIMBAD, the
Chopard-Vilhem Zenodo deposits and the *Eclipses by Appointment* claim tables.

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** Every DR3 rehearsal has to run before then.
- Release-day runbook: `runbook/dr4-release-day.md`, with `runbook/release/fetch_release.py`
  pinning every module to the commit that published it (0.28.0 code for the amendment-2 fix).
- Tables: `nss_two_body_orbit` + `_supp`, `rvs_two_body_orbit`, `dr3_neighbourhood`,
  `nss_masses`, `nss_acceleration_astro`, `nss_epoch_flags`, `rvs_epoch_parameters_single`
  (all in ESA's draft DR4 data model). Epoch photometry is DataLink-only.
- `dr3_neighbourhood`'s DR4 id column is read from TAP_SCHEMA (`dr4_source_id`, else
  `source_id`). See calib-dr4 amendment 2.
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
