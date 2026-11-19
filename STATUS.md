# gaia-orbit-transits: current status (2026-11-19)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Newest result (19 Nov, ~19:50 UTC)
**The combined, pre-registered grade of the brown-dwarf-orbit transit test is in**
(`findings/2026-11-19-sb1-robust-combined-results.md`, data `data/sb1comb-v2/`).
- 3,113 Gaia DR3 low-mass SB1 orbits (P = 1–13 d) with sensitive TESS data. If every orbit
  were real with its minimum mass, 558 transits would be seen; **25 robust hits, 9 of
  substellar size**. ρ_sub = **0.013 (95%: 0.005–0.028)**; with trusted dwarf radii only (A1),
  0.019 (0.007–0.040).
- **Brown-dwarf class: 408 transits expected, 3 seen** (all known TOIs). ρ_BD = 0.006
  (0.0003–0.020).
- H1, H1b, H2 and H3 pass; C1, C2 and R0 pass. **C3 fails** (chunk 5: 141 < 150 stars).
  **H4 fails** under A1 (hot primaries do *not* show fewer real orbits). Our predicted
  ρ_sub range (0.02–0.08) was **wrong**: the value is lower.
- **This does not yet say the orbits are wrong.** Right orbits of heavier stars seen face-on
  also lack transits. Amendment 2's calculation of that (job gaia-incfloor-v1, queued) decides
  the label: MOSTLY_SPURIOUS, SPURIOUS_UNLESS_DRY_DESERT or FACE_ON_SUFFICIENT.

## Also on 19 Nov
**Our EBLM fitting pipeline failed its pre-registered outside check**
(`findings/2026-11-19-eblm-control-results.md`, data `data/eblmctl-v1/`). Only 2 of 6 published
M-dwarf companions (Swayne et al. 2024) passed; 80% was required. The **radii agree** (median
−0.9%, 5 of 6 within ±10%). All four failures come from the ellipsoidal mass-consistency check,
whose white-noise error bars are far too small at 5.5-8 days (three impossible negative
amplitudes at 3.7-10.5σ); eccentric orbits are not modelled. As pre-registered: **BD+65 286's
label is not adopted**, the M-dwarf inflation grade carries a caveat, and the fit is being fixed
(eblm_fit 0.2.0, fresh control set chosen before fitting) before any Gaia DR4 EBLM run.
**The fresh control set is now pre-registered** (`findings/2026-11-19-eblm-holdout-prereg.md`):
26 EBLM XIX (Davis et al. 2026) systems with P ≤ 13 d, matched to Gaia DR3 SB1 orbits by a
fixed rule (job gaia-eblm-holdout-resolve-v1). The pass rule is unchanged, and the planned fixes
are written down before any holdout is fitted.

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
     decide.** Two pre-registered tests:
     - `findings/2026-11-18-calib-dr4-prereg.md` (amendments 1 and 2). **The DR3 dress
       rehearsal now passes (gaia-calibdr4-reh-v2, 19 Nov, RH1–RH4)**: all 162 targets
       confirmed through the DR2 → DR3 cross-match column `dr3_source_id`, cos i and timing
       reproduced. Outputs `data/calibdr4-reh-v2/`.
     - `findings/2026-11-19-dr4-wobble-prereg.md` + amendment 1 (`dr4_wobble.py` 0.1.0).
       Rehearsal on ESA's DR4 pre-release passed
       (`findings/2026-11-19-dr4-wobble-rehearsal-results.md`).
2. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?**
   - **0.1.0** (`findings/2026-11-18-sb1-transit-results.md`): ρ = 0.10 (0.03–0.22) from 512
     orbits; the hit rule was fooled by outlying points.
   - **0.2.0, the outlier-proof rerun: graded** (see the newest result above). Interim chunk
     notes: k0, k1, k2, k3+k5, k4+k6, k7.
   - **Amendment 1** (`findings/2026-11-19-sb1-robust-amendment-1.md`): 17.6% of the pool are
     luminous stars that entered with a fallback main-sequence radius. A1 removes them.
   - **Amendment 2** (`findings/2026-11-19-sb1-robust-amendment-2-inclination.md`, code
     `inclination_floor.py` 0.1.0, job gaia-incfloor-v1 queued). Its reproduction check must
     find n_sub = 3, fa_sub = 0.5, E_iso = 407.70 for the BD class. **Until it is graded, "most
     of these orbits are not real" is not a supported claim.**
   - The Gaia DR4 test of *why* the orbits fail is pre-registered with release-day code
     (`dr4_sb1_reality.py`; amendments 1–3; `dr4_d3_a1.py`, `dr4_d5_rate.py`). All its DR3
     rehearsals have passed (pool, DataLink, D5 pool).
   - **Eclipsing companions found by the search:**
     - **TIC 71945261** (TYC 6340-23-1, chunk 7). Pre-registered label
       **B_OVERSIZED_COMPANION** (`findings/2026-11-19-tic71945261-fit-results.md`): a new
       2.3287-day eclipsing system (6.1% deep, equal odd/even eclipses, 0.39% occultation)
       whose companion's radius is **0.224 R☉** at Gaia's 0.097 M☉, **1.9× the main-sequence
       value**. Youth or a wrong Gaia mass are not yet excluded, so we do not call it
       "inflated". The youth and archival-RV check
       (`findings/2026-11-19-tic71945261-followup-prereg.md`) stopped at its own self-test on
       19 Nov (a date-parsing bug, no data read); `youth_rv_check.py` 0.1.1 fixes it and the
       job is re-queued (gaia-tic71945261-followup-v2). The pipeline's outside check failed on
       the mass step; the radius scale held, but this label carries the same caveat.
     - **BD+65 286** (TIC 50453242, chunk 3): companion 0.100 M☉, 0.122 R☉
       (`findings/2026-11-19-bd65-286-fit-results.md`). Both control sets failed, so **its
       label is not adopted**; the numbers stand as measurements only. Prior art: Green et al.
       2023 and NASA SPOC's sector-52 TCE.
     - **TOI-7247.01** (chunk 5): our prediction failed (came out D). Not interpreted.
     - **TIC 324597856** (chunk 0): rejected as a brown dwarf.
     - **TIC 135050395** (chunk 1): the known EBLM J1219-39, not new.
     - **TIC 202283090** (chunk 1): TOI-6218.01, an existing TFOP candidate.
3. **Are M dwarfs in short orbits inflated?** (`findings/2026-11-19-eblm-infl-full-results.md`)
   - 28 M dwarfs (0.24–0.60 M☉) in 0.89–3.52-day orbits sit **+6.3% (95% CI +1.0% to
     +8.8%)** above BHAC15 5-Gyr radii. Pre-registered label **INCONCLUSIVE**.
   - **No sign that shorter orbits inflate more** (H2: NO_TREND_DETECTED; ρ = +0.49).
   - Our prediction that the heavier companions would pull the median down **failed**.
   - **Caveat:** the pipeline failed its outside check (above) on the mass step; the radius
     scale agreed (median −0.9%), but at longer periods and cooler primaries than this sample.

## Closed with a null result
- **White-dwarf self-lensing at Gaia-predicted conjunctions (DR3)**
  (`findings/2026-11-18-selflens-vet-results.md`).

## Corrected
- **"Most brown-dwarf-mass orbits are not real" was premature.** See amendment 2.
- **BD+65 286's variability and period were already published** (Green et al. 2023).
- **CD-48 897 (TIC 200743349) is not a new discovery of ours** (*Eclipses by Appointment*, Q031).
- TOI-710.01 was already a TFOP false positive.

## Refuted or closed
- TIC 207399049: refuted.
- Archival dips for the 25-star watch list: 0 found, where 0.28 were expected.
- Two "stripped companion" candidates are more likely blends or triples.

## Lessons the pipeline now encodes
- **A box depth is a mean, so a few outliers can fake a transit.** Fold searches require
  the in-box median to agree with the mean (`sb1_robust.py`).
- **A fallback table that clamps can carry a whole population through a cut.** (It also
  flipped an exploratory test: H4 passed only because of those stars.)
- **A rule fixed for one release must be applied by importing it, not by copying it.**
- **Never skip a window that is too wide; cap it.** **Never truncate a query at the row cap;
  split it.**
- **Rehearse release-day code on the previous release.**
- **Don't assume a new table's column names; read TAP_SCHEMA.**
- **Pair every empty answer with a control query.** `nss_two_body_orbit` ra/dec are empty for
  SB1 solutions, so positions must come from `gaia_source`.
- **A threshold-crossing event is not a catalogue entry, but it is prior art.**
- **Vet a comparison system like a candidate, and prefer controls with independently
  published answers.**
- **A white-noise error bar on a small phase-curve term is not an error bar.**
- **A minimum mass is not a mass.**
- **Put a self-test in every job and make it run first.** On 19 Nov one caught a date bug
  before any data were read.

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API), the TESS EB catalogue (Prša et al. 2022), the TESS Ten Thousand catalogue
(Kostov et al. 2025, J/ApJS/279/50), Gaia DR3 vari_eclipsing_binary and vari_classifier_result,
the ZTF (Chen et al. 2020) and ASAS-SN variable catalogues, Green et al. (2023) TESS
ellipsoidal candidates (J/MNRAS/522/29), ExoFOP, the SPOC TCE list (MAST DV API), SIMBAD, the
Chopard-Vilhem Zenodo deposits and the *Eclipses by Appointment* claim tables.

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** Every DR3 rehearsal has to run before then. **Done:** wobble, D5 pool,
  sb1real (pool + DataLink), the pinned-fetch check (all six release-day groups), the EBLM
  control test (failed; see above) and **calib-dr4 (v2, RH1–RH4 pass, 19 Nov 18:33 UTC)**. Still
  needing the archive before it closes: the TIC 71945261 youth check (v2) and the EBLM holdout
  resolution (gaia-eblm-holdout-resolve-v1). Either can also run on the DR3 tables after
  2 December.
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
  5. EBLM inflation (**on hold until eblm_fit 0.2.0 passes a fresh, pre-registered control
     set**);
  6. the RV transit screen;
  7. exoplanet candidates;
  8. self-lensing.
- On the day, also look up BD+65 286 and TIC 71945261 in DR4's orbit tables.
