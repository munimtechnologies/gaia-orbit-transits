# gaia-orbit-transits: current status (2026-11-21)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Newest (21 Nov, ~23:45 UTC): step G6 pre-registered, a period-free TESS search of all 214 Gaia DR3 transit candidates

**Pre-registered:** `findings/2026-11-21-vpt-pf-prereg.md`, code `vpt_pf.py` 0.1.0 with tests
(`test_vpt_pf.py`), set-up `runbook/pf/fetch_deps.py`, rehearsal job gaia-vpt-pf-dr3-v1 (queued).
- **Why:** Gaia's period is wrong for 161 of 176 known systems in DR3, so folding TESS at Gaia's
  period (step g) misses most real signals. G6 runs the unchanged period-free follow-up
  (`vpt_followup.py` 0.1.0, up to 6 sectors) on every candidate and compares the TESS period with
  the known planet and TOI periods.
- **Primary test PF1b:** among known systems whose Gaia period is wrong, does the period-free
  search find the known period (RECOVERS ≥ 0.60)? Prediction: RECOVERS 55%.
- **PF2:** Gaia DR3 new candidates with a planet-like TESS transit, at Gaia's period or another;
  robust if 2 or more sectors alone agree. Prediction: at least one robust at another period 25%.
- **DR4:** the same code runs on all 1,007 DR4 candidates after step g on 2 December.

## Earlier (21 Nov, ~23:20 UTC): the two surviving Gaia transit candidates, vetted in catalogues

**Exploratory (not pre-registered):** `findings/2026-11-21-vpt-survivors-vetting.md`, values and
queries in `data/vpt-survivors-vetting/catalogue_values.md`. The registered follow-up
(gaia-vpt-followup-v1) is still queued; its labels and predictions are unchanged.
- **Both dips are seen in Gaia's own resolved photometry**, so the bright stars about 25-28" away
  (a G 10.59 background star next to TIC 44997521, a G 11.97 foreground rotational variable next to
  TIC 4638108) cannot be the source in Gaia's data. Gaia DR3 shows no star within 18.8" of TIC
  44997521 and no sign of a close companion (RUWE 1.06).
- **Gaia's transit duration fits a dwarf host for TIC 44997521** (2.10 h against 2.5-2.8 h for a
  central transit), but **implies a grazing geometry for TIC 4638108** (1.91 h against 3.3 h;
  impact parameter about 0.92), a warning sign for a stellar companion.
- **Neither is already known:** no TOI, CTOI or follow-up on ExoFOP; VSX holds only Gaia's own EP
  imports; no Gaia EB entry; not in the TESS EB catalogue; no literature. Neither star is bright
  enough for Gaia's RV-variability screen.
- What remains for TIC 44997521 is mainly a low-mass star (about 0.1 M_sun is 1.0-1.2 R_Jup)
  instead of a hot Jupiter; only radial velocities can tell (about 0.17 km/s against 16 km/s).

## Earlier (21 Nov, ~21:30 UTC): a transiting companion found by Gaia's wobble? Step (i), fixed before DR4

**Pre-registered:** `findings/2026-11-21-dr4-astro-tess-prereg.md`, code `dr4_rows.py` 0.1.0 and
`run_search_dr4.py` 0.1.0 with tests (`test_dr4_rows.py`; commit b6ae340a, release v0.44.0),
rehearsal job gaia-dr4-astro-adapter-v1 (queued).
- **The question:** do any companions whose orbits Gaia DR4 measures from the star's wobble
  transit their star in TESS at the time the orbit predicts? A brown dwarf or giant planet found
  this way would have both a true mass and a radius. To our knowledge no companion first found by
  Gaia astrometry has yet been seen to transit.
- **What we found while preparing it:** our DR3 search code cannot read DR4 as it is. ESA's draft
  DR4 data model renames four of the columns it selects, and DR4's orbit correlations are given
  in Campbell elements (a0, omega, Omega, i) in a vector of **the same length** as DR3's
  Thiele-Innes order, so reading them with DR3's names would fail silently. The new adapter maps
  DR4's covariance onto the Thiele-Innes constants with the exact Jacobian and keeps the pinned
  search unchanged; gate G0 stops the release-day run before any TESS download if DR4's
  conventions differ from what we assume.
- **Rehearsal (R1):** up to 400 real DR3 orbits are converted to DR4's form and back; every one
  must return DR3's own correlations, errors and conjunction times.
- **Predictions:** at least one substellar transit candidate 20%; calibration within a factor 3
  45%.

## Earlier (21 Nov, ~20:00 UTC): why are Gaia's transit periods wrong? A test in Gaia's own epochs

**Pre-registered:** `findings/2026-11-21-vpt-epochs-prereg.md`, code `vpt_epochs.py` 0.1.0 with
tests, job gaia-vpt-epochs-v1 (queued). ESA's archive closes 25 Nov 12:00 CET; ESA's bulk CDN
files are the fallback, and every downloaded epoch is saved and will be committed.
- For the 161 known systems whose Gaia DR3 transit period is wrong, are Gaia's own in-transit
  epochs real transits (**ALIAS**: real dips with a wrong period drawn through them) or not
  (**SPURIOUS**)? Validity check first (T1): for known planets whose Gaia period is right,
  Gaia's in-transit epochs must fall inside the real transits.
- **T3:** can Gaia's own photometry flag a wrong period? N_comp counts box-search peaks nearly
  as strong as the one at Gaia's period. If it separates right from wrong periods (AUC ≥ 0.70,
  p ≤ 0.01), it becomes a period-reliability flag for all 1,007 DR4 candidates on release day.
- Predictions: TIME_OK 75%; ALIAS_DOMINATED 55%; T3 PREDICTIVE 30%.
- Runbook: new step (g3), the period-free TESS follow-up of every DR4 survivor, and a conditional
  step (g4); SHAs of `gaia_vpt_tess.py` 0.1.1 and `vpt_followup.py` 0.1.0 recorded.

## Earlier (21 Nov, ~17:30 UTC): TYC 6340-23-1's "bright 38″ neighbour" is faint; pixel test re-filed

**Amendment:** `findings/2026-11-21-tyc6340-pixel-amendment-1.md`, code `patch_tyc_pixel_011.py`
(turns `tyc_pixel.py` 0.1.0 into 0.1.1), tests `test_tyc_pixel_011.py`, job tyc6340-pixel-v2.
- Job tyc6340-pixel-v1 stopped at the Gaia step, before any pixel was analysed: the neighbour we
  had taken from SuperWASP's archive as **V ≈ 11.25** is **G = 14.39 (RP 13.75)** in Gaia DR3
  (6853008487031438080). SuperWASP's large aperture most likely mixed in the target's light.
- **A flux argument already settles it:** the 38″ star would have to lose 198% of its own light to
  make the 6.09% eclipse, so it **cannot be the source**.
- The pixel test now tests the nearest star that *could* make the eclipse, **Gaia DR3
  6853008452671699328 (G 12.55, 94″; it would need a 43% eclipse)**, and adds a blend screen of
  every Gaia star in the field. Labels, thresholds, controls and predictions are unchanged.

## Earlier (21 Nov, ~17:00 UTC): the full DR3 rehearsal of step g, graded

**Results:** `findings/2026-11-21-vpt-dr3-results.md`, data `data/vpt-dr3-v1/c0/` and
`data/vpt-dr3-v1/c1/` (all 214 Gaia DR3 transit candidates folded in TESS). Counted from the two
chunk files; job gaia-vpt-dr3-comb-v1 recomputes them with 0.1.1 and a fresh RVS query.
- **Gaia DR3's transit period is the known period for only 15 of 176 known systems** (0.085, 95%
  0.052-0.136). On the held-out chunk 1 it was 4 of 86 (PERIODS_MOSTLY_WRONG, as predicted at 85%).
  Examples: HD 189733 b 1.661 d in Gaia vs 2.219 d; HD 209458 b 0.899 vs 3.525; WASP-39 b 0.513 vs
  4.055. We found no published count.
- Known planets at the right period are recovered (14 of 15: PIPELINE_OK). Controls are noisy only
  on stars whose real transit sits at another period (43 of 252 trials) and silent on known planets
  (0 of 30), as amendment 1 predicted. G1 as registered: MIXED, not valid. Our predictions for
  G0b, G1 and G2 were **wrong**.
- 22 of 24 "hits" at Gaia's wrong period carry an eclipsing-binary flag; 2 look planet-like.
- **Two planet-like NEW candidates survive with no TOI:** TIC 4638108 (P 2.21 d, 1.87 R_Jup on an F
  star) and **TIC 44997521** (Gaia DR3 5432318139709900160; P 3.55 d, 2.2% deep in TESS and Gaia,
  1.03 R_Jup on a K dwarf, or 1.15 R_Jup with the TIC radius; weak TESS detection, S/N 7.6). Both
  are Gaia's candidates (Panahi et al. 2022). Neither is called a planet.

**Pre-registered next:** `findings/2026-11-21-vpt-followup-prereg.md`, code `vpt_followup.py`
0.1.0 (job gaia-vpt-followup-v1, queued): every TESS sector, a period-free box search, odd/even,
secondary and per-sector depths, with three known hot Jupiters as controls (two with wrong Gaia
periods). Predictions: CONTROLS_PASS 80%; TIC 4638108 SURVIVES 55%; TIC 44997521 SURVIVES 45%.

## Earlier (21 Nov, ~16:00 UTC): half of the step-g DR3 rehearsal, and amendment 1 before DR4

**Interim (chunk 0 of 2):** `findings/2026-11-21-vpt-dr3-c0-interim.md`, data
`data/vpt-dr3-v1/c0/`. Superseded by the full results above.

**Amendment 1, fixed before DR4:** `findings/2026-11-21-vpt-amendment-1.md`, code
`gaia_vpt_tess.py` 0.1.1 (no search step changed; release v0.41.0). DR4's primary G1 now uses a
control rate measured on known planets only (G1b); G5 measures how often Gaia's period matches the
known one; an RVS screen (Katz et al. 2023 criterion) feeds G2b.

## Earlier (21 Nov, ~10:00 UTC): Gaia's own transit candidates against TESS (step g), fixed before DR4

**Pre-registered:** `findings/2026-11-21-vpt-tess-prereg.md`, code `gaia_vpt_tess.py` 0.1.0.
Gaia DR4 publishes **1,007** photometric transit candidates (`vari_planetary_transit`; DR3 had
214, of which Gaia-1b and Gaia-2b were confirmed). The module folds every candidate's TESS light
curves at the Gaia period with the unchanged `sb1_transit` search (controls at two non-harmonic
periods, injections at 0.8 × Gaia depth), sorts candidates into KNOWN_PLANET / TOI_FP / TOI_PC /
KNOWN_SYSTEM_OTHER_P / NEW, and flags eclipsing-binary signs. G0 (validity), G1 (main: what
fraction of Gaia's NEW candidates TESS sees), G2 (planet-like list), G3 (EB share), G4 (aliases).
DR4 predictions: MOSTLY_SEEN 40%, MIXED 35%; 6 or more new planet-like signals 55%.

## Earlier (20 Nov, ~23:30 UTC): two more quality-cut tests fixed before Gaia DR4

**Pre-registered:** `findings/2026-11-20-qcut-q4ef-prereg.md`, graded on DR4 day at step (a4).
- **Q4e:** does `goodness_of_fit` (p = 0.0104 against α = 0.01 in the transit test) predict which
  DR3 orbits DR4 confirms? **Q4f:** do DR4 survival and the transit test agree on the gold-cut
  ingredients? Predictions: GOF_REPLICATES 75%; YARDSTICKS_DISAGREE 60%.

## Earlier (20 Nov, ~20:00 UTC): ASAS-SN insensitive; the SuperWASP dip is not a field systematic; the period tension was ours

**Graded:** `findings/2026-11-20-tyc6340-period-results.md` (data `data/tyc6340-period-v1/`).
- **ASAS-SN: ASASSN_INSENSITIVE** (we had predicted DETECTED, 65%: **wrong**).
- **SuperWASP common mode: COMMON_CLEAN**: 0 of 12 comparison stars show the dip.
- **Reported, not graded:** SuperWASP's strongest peak is **2.32878 d**, which joins 2006-2008 to
  the 2025 TESS eclipse and agrees with Gaia DR3; the earlier "5.8σ period tension" was **very
  likely our artefact**.

**Pre-registered next:** `findings/2026-11-20-tyc6340-pixel-prereg.md`, code `tyc_pixel.py` 0.1.0
(job tyc6340-pixel-v1; amended 21 Nov, see above): which star dims, the deblended depth, and a
19-year period. Predictions: on target 82%; depth consistent 55%; oversize survives 75%; link
unique 70%.

## Results of 20 Nov

1. **Gaia's own quality columns cannot single out the real low-mass SB1 orbits**
   (`findings/2026-11-20-quality-cut-results.md`): the gold cut keeps 9 of 2,981; the top
   significance tier transits about six times as often (p = 0.016) but is still mostly not right.
   Write-up: https://www.munimtech.com/research/gaia-quality-cut-low-mass-orbits
2. **Our EBLM fitting pipeline failed its pre-registered holdout check**
   (`findings/2026-11-20-eblm-holdout-results.md`): 6 of 14 → **PIPELINE_FAILED**; no EBLM result
   from this pipeline will come from Gaia DR4.
3. **Pre-registered before DR4: an independent test of TYC 6340-23-1's mass**
   (`findings/2026-11-20-tyc6340-dr4-k-prereg.md`, `tyc_k_dr4.py` 0.1.0), release-day step (a5).
4. **TIC 71945261 (TYC 6340-23-1) does not move like a member of any known young group**
   (`findings/2026-11-20-tic71945261-followup-results.md`): FIELD_KINEMATIC; label stays
   **B_OVERSIZED_COMPANION**; **we do not call it inflated**.
   Write-up: https://www.munimtech.com/research/tyc-6340-23-1-oversized-companion

## Graded 19 Nov
**Most of Gaia DR3's brown-dwarf-mass SB1 orbits at 1–13 days must be wrong**
(`findings/2026-11-19-sb1-robust-amendment-2-results.md`, data `data/incfloor-v1/`): 407.7 transits
expected, 3 seen; φ = 0.010 (95%: 0.0005–0.034) for the central population; caveat on the
trusted-radius subset (0.62). Write-up:
https://www.munimtech.com/research/gaia-brown-dwarf-orbits-missing-transits
Also: the combined transit-test grade (`findings/2026-11-19-sb1-robust-combined-results.md`) and
the failed first outside check of eblm_fit 0.1.0 (`findings/2026-11-19-eblm-control-results.md`).

## Leads
1. **Gaia's own transit candidates in TESS** (step g): DR3 rehearsal graded (above); why the
   periods are wrong (epoch test, queued); the blind test on DR4's 1,007 candidates on release
   day; follow-up of TIC 4638108 and TIC 44997521 (catalogue vetting done, period-free TESS test
   queued).
2. **A transiting companion first found by Gaia astrometry** (step i, DR4): pre-registered with
   a DR4 adapter and gate; rehearsal queued.
3. **Do Gaia DR3 inclinations hold up against real eclipses?** (`findings/2026-11-18-calib-window-results.md`)
   58 of 162 near-edge-on orbits eclipse against 80.7 expected (p = 2 × 10⁻⁵). Gaia DR4 decides.
4. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?** Graded: mostly not; the DR4 test
   of why is pre-registered with release-day code. Eclipsing companions found: **TIC 71945261**
   (TYC 6340-23-1, B_OVERSIZED_COMPANION); BD+65 286 (label not adopted).
5. **Are M dwarfs in short orbits inflated?** INCONCLUSIVE, caveated; no DR4 follow-up.

## Closed with a null result
- **White-dwarf self-lensing at Gaia-predicted conjunctions (DR3)**
  (`findings/2026-11-18-selflens-vet-results.md`).

## Corrected
- **TIC 44997521's radius estimate depends on the stellar radius:** 1.03 R_Jup with R* 0.71 R_sun,
  1.15 R_Jup with the TIC's 0.80 R_sun (21 Nov, vetting note).
- **TYC 6340-23-1's 38″ neighbour is G = 14.39, not V ≈ 11.25** (21 Nov; SuperWASP's archive
  magnitude was blended). It cannot make the eclipse; the pixel test now targets the 94″ G = 12.55
  star (`findings/2026-11-21-tyc6340-pixel-amendment-1.md`).
- **TYC 6340-23-1's "5.8σ period tension" (20 Nov 14:30 UTC) was very likely our detrending
  artefact** (`findings/2026-11-20-tyc6340-period-results.md`).
- **"Most brown-dwarf-mass orbits are not real" was premature on 19 Nov morning** (amendment 2).
- **Chunk 0 of the step-g rehearsal suggested most of Gaia's NEW candidates are seen in TESS
  (0.55); the full sample says MIXED (0.37 with the known-planet control rate).**
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
- **Know a survey's footprint before reading its silence.**
- **A white-noise error bar on a small phase-curve term is not an error bar.**
- **An odd/even depth test across sectors years apart sees systematics, not twins.**
- **Gaia's eccentricity can be badly wrong.**
- **Before testing a published quality cut, check where the known real objects fall on it.**
- **Controls that shaped a fix cannot validate it**; a fresh holdout did its job here.
- **A rule fixed for one release must be applied by importing it, not by copying it.**
- **Rehearse the inputs as well as the code.**
- **Put a self-test in every job and make it run first.**
- **Every network call needs a timeout, and every long job should save partial results.**
- **A one-sector discovery needs an older, independent light curve.**
- **Detrend without assuming an ephemeris first.**
- **A blended discovery needs a pixel-level test** before a radius is quoted.
- **Check every neighbour's brightness in Gaia before building a blend test around it:** a
  wide-aperture survey's catalogue magnitude for a close neighbour can include the target's light.
- **A near-miss is a hypothesis, not a result:** test it again on data the first test did not use.
- **A control is only a noise control where the real signal has been removed.**
- **Check a catalogue's periods against known objects before folding new ones at them:** Gaia
  DR3's transit periods match the known period for 15 of 176 known systems.
- **A hit at a catalogue's period does not prove the period:** search the full light curve without
  assuming it.
- **Half a sample can mislead:** chunk 0 said MOSTLY_SEEN, the full sample says MIXED.
- **Use the survey's own other instruments as a vetting step** (Gaia RVS).
- **Save a survey's raw data before its archive goes dark:** the epoch test stores every Gaia DR3
  epoch it downloads, ahead of the 25 Nov - 2 Dec archive closure.
- **A new release can change a table's parameterisation, not just its column names:** check the
  order and meaning of every correlation vector, not only that the query runs.
- **A survey that resolves what TESS blends settles "which star" for free:** when Gaia's own
  photometry shows the dip, a bright neighbour tens of arcseconds away cannot be its source in
  Gaia's data. **Check a catalogue transit's duration against the host's density** before any
  pixel work.

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API, or its VizieR copy B/vsx when the API refuses), the TESS EB catalogue (Prša et al.
2022), the TESS Ten Thousand catalogue (Kostov et al. 2025), Gaia DR3 vari_eclipsing_binary and
vari_classifier_result, the ZTF and ASAS-SN variable catalogues, Green et al. (2023), ExoFOP, the
SPOC TCE list, SIMBAD, the Chopard-Vilhem Zenodo deposits, the *Eclipses by Appointment* claim
tables and the EBLM target tables.

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** Jobs that still need DR3 tables fall back to the Heidelberg DR3 mirror;
  DR3 epoch photometry falls back to ESA's bulk CDN files.
- Release-day runbook: `runbook/dr4-release-day.md`, with every module pinned to the commit that
  published it.
- Pre-registered order: (a1) orbit survival, (a2) calibration, (a5) TYC 6340-23-1's K, (b)
  wobble, (c) D5; then (a3) D3, (a4) quality-cut Q4 + Q4e/Q4f, (c2) D5 grade; then (g) Gaia
  transit candidates x TESS (0.1.1, 6 chunks + RVS screen g2), (g3) the period-free follow-up of
  every G2b survivor, (g4) only if the epoch test's T3 is PREDICTIVE, (G6) the period-free search
  of every DR4 candidate via `vpt_pf.py` (`findings/2026-11-21-vpt-pf-prereg.md`), and (i)
  astrometric orbits x TESS via `run_search_dr4.py`; later (d), (f), (h). (e) EBLM inflation is
  cancelled.
