# gaia-orbit-transits: current status (2026-11-20)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Pre-registered 20 Nov (~10:00 UTC): TYC 6340-23-1 in SuperWASP 2006-2008

`findings/2026-11-20-tyc6340-wasp-prereg.md`, code `wasp_tyc.py` 0.1.0 (job tyc6340-wasp-v1).
The public SuperWASP DR1 archive holds a 2006-2008 light curve of the target
(1SWASP J202214.65-220425.1, 9,236 points) and of three neighbours, one of them a V ≈ 11.25 star
only 38″ away. Three graded questions: is the eclipse seen by this independent instrument 17-19
years before TESS (with controls and an injection test); does a single linear ephemeris join WASP
and TESS (expected period precision about 1e-6 d, 100× Gaia's); and is the eclipse on the target
rather than a neighbour (paired depth test)? Predictions: detected 80%, unique ephemeris 85%,
on target 70%.

## Newest results (20 Nov, ~07:00 UTC)

**1. Gaia's own quality columns cannot single out the real low-mass SB1 orbits**
(`findings/2026-11-20-quality-cut-results.md`, data `data/qcut-v1/`). Graded under
`findings/2026-11-20-quality-cut-prereg.md`:
- **Q1 UNDERPOWERED** (predicted, 70%): only **9 of 2,981** brown-dwarf- and very-low-mass-class
  orbits at 1-13 d pass Gaia's recommended "gold sample" cut (Gosset et al. 2024, Appendix J).
  The cut cannot rescue this class; it removes 99.7% of it.
- **Q2 RISES_PRIMARY_ONLY** (predicted only 15%): orbits with significance ≥ 20 transit about
  six times as often, relative to expectation, as those below 10 (ρ_all 0.167 vs 0.029,
  p = 0.016); the substellar-size robustness test gives p = 0.052. Even the top tier is mostly
  not right under the central population (φ 0.12, 95% upper 0.44).
- **Q3** (exploratory): no column passes Bonferroni α = 0.01 (goodness_of_fit p = 0.0104).
- Q4 (DR4 confirmation of the same cuts) runs on release day (step a4).

**2. Our EBLM fitting pipeline failed its pre-registered holdout check**
(`findings/2026-11-20-eblm-holdout-results.md`, data `data/eblm-holdout-fit-v1/`): eblm_fit 0.2.0
passed **6 of 14** published EBLM XIX systems (80% required) → **PIPELINE_FAILED**. Median
radius offset −5.3%. Failures: two false "twin" labels (one grazing eclipse, one odd/even
mismatch across 2020-2024 sectors), one missed eclipse (spot-dominated light curve), one
mass-check failure, four radii 11-20% too small. Our predictions (VALIDATED 50%; median within
±5%, 75%) were **wrong**.
- As pre-registered: **no EBLM result from this pipeline will come from Gaia DR4** (runbook step
  (e) cancelled); the inflation note keeps its caveat and has an addendum
  (`findings/2026-11-20-eblm-inflation-addendum.md`); BD+65 286's label stays not adopted.
- For TYC 6340-23-1 the holdout shows no failure mode that would make a non-grazing companion
  look twice too large (its fit has b = 0.67; every non-grazing miss came out too small). The
  pipeline as a whole is not validated, though, so the radius needs independent confirmation.

**3. Pre-registered before DR4: an independent test of TYC 6340-23-1's mass**
(`findings/2026-11-20-tyc6340-dr4-k-prereg.md`, `tyc_k_dr4.py` 0.1.0). Only Gaia DR4 velocity
epochs after DR3's data window (28 May 2017) are used, and K is graded against Gaia DR3's 16.16
km/s and the 32.4 km/s a normal-size companion would need. Release-day step (a5).

## Graded earlier on 20 Nov (~04:30 UTC)
**TIC 71945261 (TYC 6340-23-1) does not move like a member of any known young group**
(`findings/2026-11-20-tic71945261-followup-results.md`, data `data/tic71945261-followup-v3/`).
AU Mic control passed (0.927); target young-association probability **0.004** →
**FIELD_KINEMATIC**; UVW (−19.6, −14.8, −6.3) km/s. No archival RV in RAVE DR6, GALAH DR3 or
APOGEE DR17, so the K question stays open (now pre-registered for DR4, above). The label stays
**B_OVERSIZED_COMPANION**; **we do not call it inflated** until a spectrum checks lithium and K.

## Graded 19 Nov (~23:15 UTC)
**Face-on stars cannot explain the missing transits: most of Gaia DR3's brown-dwarf-mass SB1
orbits at 1–13 days must be wrong** (`findings/2026-11-19-sb1-robust-amendment-2-results.md`,
data `data/incfloor-v1/`). Pre-registered label **MOSTLY_SPURIOUS**. Write-up:
https://www.munimtech.com/research/gaia-brown-dwarf-orbits-missing-transits
- 2,180 brown-dwarf-class orbits with sensitive TESS data; 407.7 transits expected if every
  orbit were real with its minimum mass; **3 seen** (all known TOIs), 0.5 false alarms expected.
- Allowing heavier stars seen face-on: the fraction of orbits that can be right is
  **φ = 0.010 (95%: 0.0005–0.034)** for the central population and **0.097 (0.005–0.322)** for
  the most generous one. All 36 pre-registered grid scenarios stay below 0.5.
- **Caveat:** on the trusted-radius subset (amendment 1, descriptive) the floor bound loosens to
  0.62 (SPURIOUS_UNLESS_DRY_DESERT). Our most likely predicted label was **wrong** for the
  primary sample; both φ predictions held.
- Related work that does not test 1–13-day SB1 orbits and so does not conflict: Wallace & Casey
  2026 (PASA 43, e010; arXiv:2601.03539) and Stevenson et al. 2023 (arXiv:2310.02695).

## Also on 19 Nov
**The combined grade of the transit test** (`findings/2026-11-19-sb1-robust-combined-results.md`,
data `data/sb1comb-v2/`): 3,113 low-mass SB1 orbits, 558 transits expected, 25 robust hits (9 of
substellar size); ρ_sub 0.013 (0.005–0.028). C3 and H4 (A1) fail; our predicted ρ_sub range was
wrong (lower). Orbits at P ≥ 5 d do far better than those below 5 d (ρ_all 0.129 vs 0.015).

**The first outside check of eblm_fit 0.1.0 failed** (`findings/2026-11-19-eblm-control-results.md`):
2 of 6 passed; radii agreed (median −0.9%); the mass-consistency step failed. The 0.2.0 fixes
(`findings/2026-11-19-eblm-fit-020-build.md`) then failed the fresh holdout above.

## Leads
1. **Do Gaia DR3 inclinations hold up against real eclipses?** (`findings/2026-11-18-calib-window-results.md`)
   58 of 162 near-edge-on orbits eclipse against 80.7 expected (p = 2 × 10⁻⁵); DR3's predicted
   conjunction times are too optimistic by ×1.8. Gaia DR4 decides
   (`findings/2026-11-18-calib-dr4-prereg.md`, `findings/2026-11-19-dr4-wobble-prereg.md`).
2. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?** **Graded: mostly not** (above),
   and Gaia's quality columns do not rescue them (Q1-Q3 above). The DR4 test of *why* they fail
   is pre-registered with release-day code (`dr4_sb1_reality.py`, `dr4_d3_a1.py`,
   `dr4_d5_rate.py`, `qcut_dr4.py`).
   - **Eclipsing companions found by the search:**
     - **TIC 71945261** (TYC 6340-23-1). Label **B_OVERSIZED_COMPANION**
       (`findings/2026-11-19-tic71945261-fit-results.md`; prior art
       `findings/2026-11-19-tic71945261-prior-art.md`): a new 2.3287-day eclipsing system (6.1%
       deep, 0.39% occultation) whose companion is **0.224 R☉** at Gaia's 0.097 M☉, **1.9×** the
       main-sequence value. FIELD_KINEMATIC. Open: Gaia's K (DR4 test pre-registered), youth
       outside known groups, independent radius confirmation, and the SuperWASP check above.
     - **BD+65 286** (TIC 50453242): companion 0.100 M☉, 0.122 R☉. **Label not adopted.**
     - TOI-7247.01: our prediction failed. TIC 324597856: rejected as a brown dwarf.
       TIC 135050395: the known EBLM J1219-39. TIC 202283090: TOI-6218.01.
3. **Are M dwarfs in short orbits inflated?** (`findings/2026-11-19-eblm-infl-full-results.md`)
   +6.3% (95% CI +1.0% to +8.8%), n = 28, **INCONCLUSIVE**, caveated; addendum 20 Nov after the
   pipeline failed its holdout. No DR4 follow-up from this pipeline.

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
- TIC 207399049: refuted. Archival dips for the 25-star watch list: 0 found (0.28 expected).
- Two "stripped companion" candidates are more likely blends or triples.

## Lessons the pipeline now encodes
- **A box depth is a mean, so a few outliers can fake a transit.**
- **A minimum mass is not a mass.** Model face-on companions before calling an orbit wrong.
- **Never skip a window that is too wide; cap it.** **Never truncate a query at the row cap.**
- **Rehearse release-day code on the previous release.** **Read TAP_SCHEMA.** **Pair every empty
  answer with a control query**, and run the controls first.
- **Know a survey's footprint before reading its silence** (eRASS1 covers only l = 180–360°).
- **A white-noise error bar on a small phase-curve term is not an error bar**, and red-noise
  error bars did not make the ellipsoidal mass check safe either (holdout, J1626+57).
- **An odd/even depth test across sectors years apart sees systematics, not twins**; run the
  grazing test before the twin test (holdout, J0040+01 and J1741+21).
- **Gaia's eccentricity can be badly wrong** (J1850+50: 0.26 vs 0.107 published); using it
  shrank the fitted radius by 20%.
- **Before testing a published quality cut, check where the known real objects fall on it.**
- **Controls that shaped a fix cannot validate it**; a fresh holdout did its job here.
- **A fallback table that clamps can carry a whole population through a cut.**
- **A rule fixed for one release must be applied by importing it, not by copying it.**
- **Rehearse the inputs as well as the code:** every URL a release-day step reads from `main`
  must be fetched in a rehearsal.
- **A threshold-crossing event is not a catalogue entry, but it is prior art.**
- **Put a self-test in every job and make it run first.**
- **When a pre-registration says "commit X before Y", make the Y job check that X is committed.**
- **Every network call needs a timeout, and every long job should save partial results.**
- **A one-sector discovery needs an older, independent light curve:** check the ground-based
  archives (SuperWASP DR1, ASAS-SN) for an earlier record and for the neighbours' light curves.

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API), the TESS EB catalogue (Prša et al. 2022), the TESS Ten Thousand catalogue
(Kostov et al. 2025, J/ApJS/279/50), Gaia DR3 vari_eclipsing_binary and vari_classifier_result,
the ZTF (Chen et al. 2020) and ASAS-SN variable catalogues, Green et al. (2023) TESS
ellipsoidal candidates (J/MNRAS/522/29), ExoFOP, the SPOC TCE list (MAST DV API), SIMBAD, the
Chopard-Vilhem Zenodo deposits and the *Eclipses by Appointment* claim tables. From 20 Nov also
the EBLM target tables (EBLM IV, Triaud et al. 2017, J/A+A/608/A129), because EBLM systems were
found as SuperWASP candidates.

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** All Gaia-TAP jobs that needed DR3 before the closure have run.
- Release-day runbook: `runbook/dr4-release-day.md`, with `runbook/release/fetch_release.py`
  pinning every module to the commit that published it.
- Pre-registered order: (a1) orbit survival, (a2) calibration, (a5) TYC 6340-23-1's K, (b)
  wobble, (c) D5; then (a3) D3, (a4) quality-cut Q4, (c2) D5 grade; later (d), (f)-(h).
  (e) EBLM inflation is cancelled.
