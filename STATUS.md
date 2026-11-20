# gaia-orbit-transits: current status (2026-11-20)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Newest result (19 Nov, ~23:15 UTC)
**Face-on stars cannot explain the missing transits: most of Gaia DR3's brown-dwarf-mass SB1
orbits at 1–13 days must be wrong** (`findings/2026-11-19-sb1-robust-amendment-2-results.md`,
data `data/incfloor-v1/`). Pre-registered label **MOSTLY_SPURIOUS**.
- 2,180 brown-dwarf-class orbits with sensitive TESS data; 407.7 transits expected if every
  orbit were real with its minimum mass; **3 seen** (all known TOIs), 0.5 false alarms expected.
- Allowing heavier stars seen face-on, star by star with Gaia's exact mass function: the
  fraction of orbits that can be right is **φ = 0.010 (95%: 0.0005–0.034)** for the central
  population and **0.097 (0.005–0.322)** for the population most generous to "real". All 36
  pre-registered grid scenarios stay below 0.5.
- For every orbit to be real, close brown dwarfs would have to be 3.5–87 times rarer (relative
  to close low-mass stars) than the grid's literature ratios.
- **Caveat:** on the trusted-radius subset (amendment 1, descriptive) the floor bound loosens to
  0.62, giving the weaker label SPURIOUS_UNLESS_DRY_DESERT. Our most likely predicted label
  (SPURIOUS_UNLESS_DRY_DESERT, 55%) was **wrong** for the primary sample; both φ predictions held.
- Gaia DR4 (2 December 2026) will show which DR3 orbits survive (`dr4_sb1_reality.py`).

## In progress (20 Nov)
- **EBLM holdout set resolved, not yet fitted** (`findings/2026-11-20-eblm-holdout-resolution.md`,
  data `data/eblm-holdout/`). RC1 passed; 14 of 26 EBLM XIX systems matched exactly one Gaia DR3
  SB1 orbit (predicted 8–16); 1 ambiguous, 11 without an SB1 orbit. Their published masses and
  radii were re-checked against EBLM XIX Table 4 before any fit. The fit job
  (gaia-eblm-holdout-fit-v1, eblm_fit 0.2.0 pinned at 996ced1) refuses to start until these ids
  are on `main`.
- **Quality-cut test** (`findings/2026-11-20-quality-cut-prereg.md`, `qcut.py` 0.1.0, job
  gaia-qcut-v1 queued). Can Gaia's own quality columns pick out the real orbits? (Q1) Gosset et
  al. 2024's "gold sample" cut (efficiency ≥ 0.2, ≥ 20 good RV epochs, significance ≥ 40,
  P ≥ 2 d); (Q2) do transits become more common with significance; (Q3, exploratory) other
  quality columns; (Q4) the same cuts against DR4 orbit survival on 2 December. The known
  transiting controls (TOI-5427, TOI-1712, TOI-2533, WASP-18) have significance of only 7–14,
  so a real low-mass orbit can sit far below the gold cut. The DR4-day grader for Q4
  (`qcut_dr4.py` 0.1.0, stdlib, with tests) was committed on 20 Nov, before DR4 and before
  qcut 0.1.0 produced any output; it imports qcut's gold, tier and amplitude rules.
- **TIC 71945261 youth and archival-RV check:** the v2 job hit its 45-minute limit with no output
  (a network call hung; which one is unknown). `youth_rv_check.py` 0.1.2 adds logging, hard
  timeouts and partial saves, with no change to any rule; re-queued as
  gaia-tic71945261-followup-v3.

## Also on 19 Nov
**The combined grade of the transit test** (`findings/2026-11-19-sb1-robust-combined-results.md`,
data `data/sb1comb-v2/`): 3,113 low-mass SB1 orbits, 558 transits expected, 25 robust hits (9 of
substellar size); ρ_sub 0.013 (0.005–0.028). H1, H1b, H2, H3, C1, C2 and R0 pass; **C3 fails**
(chunk 5: 141 < 150) and **H4 fails** under A1. Our predicted ρ_sub range (0.02–0.08) was wrong
(lower). Orbits at P ≥ 5 d do far better than those below 5 d (ρ_all 0.129 vs 0.015).

**Our EBLM fitting pipeline failed its pre-registered outside check**
(`findings/2026-11-19-eblm-control-results.md`, data `data/eblmctl-v1/`). Only 2 of 6 published
M-dwarf companions (Swayne et al. 2024) passed; 80% was required. The **radii agree** (median
−0.9%, 5 of 6 within ±10%). All four failures come from the ellipsoidal mass-consistency check,
whose white-noise error bars are far too small at 5.5-8 days; eccentric orbits are not modelled.
As pre-registered: **BD+65 286's label is not adopted**, the M-dwarf inflation grade carries a
caveat, and the fit was fixed (eblm_fit 0.2.0, `findings/2026-11-19-eblm-fit-020-build.md`)
before any Gaia DR4 EBLM run. The fresh control set (`findings/2026-11-19-eblm-holdout-prereg.md`)
is now resolved (above).

## Leads
1. **Do Gaia DR3 inclinations hold up against real eclipses?** Graded in 0.20.0:
   `findings/2026-11-18-calib-window-results.md`.
   - Of 162 near-edge-on DR3 orbits that TESS covered, 58 eclipse against 80.7 expected (ratio
     0.72, p = 2 × 10⁻⁵) with windows three times wider than Gaia's errors.
   - **Gaia DR3's predicted conjunction times are too optimistic by ×1.8** (95%: 1.2–2.8).
     **If the orbits are right, σ(cos i) is understated by k = 2.1 (1.4–3.4).** "About a third
     of these orbits are wrong" fits equally well. **Gaia DR4 will decide**:
     `findings/2026-11-18-calib-dr4-prereg.md` (amendments 1 and 2; DR3 dress rehearsal passes,
     `data/calibdr4-reh-v2/`) and `findings/2026-11-19-dr4-wobble-prereg.md` + amendment 1.
2. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?** **Graded: mostly not** (newest
   result above). History: 0.1.0 (`findings/2026-11-18-sb1-transit-results.md`, fooled by
   outliers) → 0.2.0 outlier-proof rerun (combined grade) → amendment 1 (trusted radii) →
   amendment 2 (face-on stars; graded MOSTLY_SPURIOUS) → quality-cut test (pre-registered 20 Nov).
   The Gaia DR4 test of *why* the orbits fail is pre-registered with release-day code
   (`dr4_sb1_reality.py`; amendments 1–3; `dr4_d3_a1.py`, `dr4_d5_rate.py`). All its DR3
   rehearsals have passed.
   - **Eclipsing companions found by the search:**
     - **TIC 71945261** (TYC 6340-23-1). Pre-registered label **B_OVERSIZED_COMPANION**
       (`findings/2026-11-19-tic71945261-fit-results.md`): a new 2.3287-day eclipsing system
       (6.1% deep, equal odd/even eclipses, 0.39% occultation) whose companion's radius is
       **0.224 R☉** at Gaia's 0.097 M☉, **1.9× the main-sequence value**. Youth or a wrong Gaia
       mass are not yet excluded, so we do not call it "inflated". Its youth and archival-RV check
       (`findings/2026-11-19-tic71945261-followup-prereg.md`, `youth_rv_check.py` 0.1.2) is
       queued as gaia-tic71945261-followup-v3. The pipeline's outside check failed on the mass
       step; the radius scale held, but this label carries the same caveat.
     - **BD+65 286** (TIC 50453242): companion 0.100 M☉, 0.122 R☉
       (`findings/2026-11-19-bd65-286-fit-results.md`). **Label not adopted** (controls failed).
       Prior art: Green et al. 2023 and NASA SPOC's sector-52 TCE.
     - TOI-7247.01: our prediction failed (came out D). TIC 324597856: rejected as a brown dwarf.
       TIC 135050395: the known EBLM J1219-39. TIC 202283090: TOI-6218.01.
3. **Are M dwarfs in short orbits inflated?** (`findings/2026-11-19-eblm-infl-full-results.md`)
   28 M dwarfs (0.24–0.60 M☉) in 0.89–3.52-day orbits sit **+6.3% (95% CI +1.0% to +8.8%)**
   above BHAC15 5-Gyr radii. Label **INCONCLUSIVE**; no sign that shorter orbits inflate more;
   our prediction that the median would fall **failed**. Carries the EBLM control caveat.

## Closed with a null result
- **White-dwarf self-lensing at Gaia-predicted conjunctions (DR3)**
  (`findings/2026-11-18-selflens-vet-results.md`).

## Corrected
- **"Most brown-dwarf-mass orbits are not real" was premature on 19 Nov morning** (amendment 2).
  It is now supported for the primary sample by the graded amendment-2 test, with the caveats
  above.
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
- **A minimum mass is not a mass.** Model face-on companions before calling an orbit wrong.
- **A fallback table that clamps can carry a whole population through a cut.**
- **A rule fixed for one release must be applied by importing it, not by copying it.**
- **Never skip a window that is too wide; cap it.** **Never truncate a query at the row cap;
  split it.**
- **Rehearse release-day code on the previous release.** **Read TAP_SCHEMA.** **Pair every empty
  answer with a control query.**
- **A threshold-crossing event is not a catalogue entry, but it is prior art.**
- **Vet a comparison system like a candidate, and prefer controls with independently
  published answers.** **A white-noise error bar on a small phase-curve term is not an error
  bar.**
- **Put a self-test in every job and make it run first.**
- **Before testing a published quality cut, check where the known real objects fall on it.**
- **When a pre-registration says "commit X before Y", make the Y job check that X is committed.**
- **Every network call needs a timeout, and every long job should save partial results.**

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API), the TESS EB catalogue (Prša et al. 2022), the TESS Ten Thousand catalogue
(Kostov et al. 2025, J/ApJS/279/50), Gaia DR3 vari_eclipsing_binary and vari_classifier_result,
the ZTF (Chen et al. 2020) and ASAS-SN variable catalogues, Green et al. (2023) TESS
ellipsoidal candidates (J/MNRAS/522/29), ExoFOP, the SPOC TCE list (MAST DV API), SIMBAD, the
Chopard-Vilhem Zenodo deposits and the *Eclipses by Appointment* claim tables.

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** Still needing the archive before it closes: the EBLM holdout fit
  (gaia-eblm-holdout-fit-v1), the quality-cut test (gaia-qcut-v1) and the TIC 71945261 youth check
  (v3). Each can also run on the DR3 tables after 2 December.
- Release-day runbook: `runbook/dr4-release-day.md`, with `runbook/release/fetch_release.py`
  pinning every module to the commit that published it.
- Pre-registered order: (1) the DR3 → DR4 orbit-survival tests (`dr4_sb1_reality.py` with
  `dr4_d3_a1.py`, and `calib_dr4_run.py`), then the quality-cut grade Q4; (2) the wobble test;
  (3) the SB1 transit-rate test on DR4's new SB1 orbits (D5); (4) the inclination and timing
  calibration on DR4's own orbits; (5) EBLM inflation (only if eblm_fit 0.2.0 passes the holdout
  check); (6) the RV transit screen; (7) exoplanet candidates; (8) self-lensing.
- On the day, also look up BD+65 286 and TIC 71945261 in DR4's orbit tables.
