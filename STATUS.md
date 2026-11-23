# gaia-orbit-transits: current status (2026-11-23)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Newest (23 Nov, ~10:00 UTC): the Gaia SB2 x TESS screen graded; two more new eclipsing binaries with Gaia masses

**Graded (pre-registered):** `findings/2026-11-23-sb2-screen-results.md`, data
`data/sb2-edgeon-screen-v1/` (job sb2-edgeon-screen-v1, `sb2_screen.py` 0.1.0) and
`data/sb2-new-ebs/` (vetting after the run).
- 183 edge-on Gaia DR3 double-lined orbits (P < 8 d): 66 have a qualifying TESS SPOC TCE, 46 at
  half the Gaia period (S1 0.70, **MIXED**; we predicted HALF_DOMINANT, **wrong**). Controls: all 44
  VSX eclipsing stars with a TCE are at P or P/2 (**CONTROLS_OK**). S0 **DIFFERS** (183, 18 of 20
  pilot stars; **wrong**): the pilot had left the (1 − e²)^1.5 factor out of M1 sin³i, so two
  eccentric pilot stars do not pass the registered rule.
- **The screen's lookup of the Villanova TESS EB catalogue failed for every star (HTTP 400)**, so
  its "new" list of 8 was too long. Vetted by hand (Prša et al. 2022 and T10K through VizieR's CfA
  mirror with control rows, SIMBAD, VSX, ASAS-SN, ExoFOP): 3 are in the TESS EB catalogue, 1 is
  Kepler's KOI-3161, 1 is a known heartbeat star.
- **New eclipsing binaries (in no catalogue we reached): CD-28 7251 (TIC 189269584, A3m, G 8.86;
  Gaia P 6.96109 d, e 0.076; M sin³i 2.06 and 1.74 M_sun) and TYC 3616-2395-1 (TIC 384284045,
  G 10.47; P 3.78709 d, circular; M sin³i 1.05 and 1.12 M_sun)**, besides HD 250735 from the pilot.
- **CD-28 7251's eclipses are in Gaia's own resolved photometry:** two dips (0.27 and 0.19 mag)
  7.004 d apart, both 0.14-0.18 d from the same conjunction of Gaia's own orbit (hand calculation,
  about 0.19 d uncertainty). A brighter star 46″ away dilutes TESS but cannot make these dips.

**Pre-registered next:** `findings/2026-11-23-sb2-new-ebs-prereg.md`, code `sb2_ebtime.py` 0.1.0 with
tests, inputs `runbook/ebtime/targets.json`, job sb2-new-ebs-timing-v1 (queued). Eclipse times of the three new binaries in every
TESS sector against Gaia's period (E1), secondary-eclipse phase from e and ω (E2), conjunction
times (E3) and Gaia's faint epochs (E4), with three known eclipsing binaries as controls chosen by
rule. Predictions: CONTROLS_OK 70%; CD-28 7251 E1 80%, E2 55%, E3 50%, E4 85% (not blind).

## Earlier (23 Nov, ~01:45 UTC): the pixel test's negative-flux failure fixed and re-registered; DR4 runbook addendum; T10K checked

**Amendment 1 to pixel_which_star (pre-registered, not blind for the target):**
`findings/2026-11-23-pixel-which-star-amendment-1.md`, code `pws_amend_011.py` with tests
`test_pws_amend_011.py`, inputs `runbook/pixel2/targets.json`, job tic93622019-pixel-011-v1 (queued).
- **Cause of the 0.1.0 failure, read from its outputs:** HATS-58 A's companion (0.74″ away) was put
  in the shared faint-group column, which sat on the target and traded flux with it (target flux
  -1385 and -233 e/s). TIC 93622019's neighbour (RP 13.49, 2 px away) came out between -520 and
  +963 e/s across six sectors.
- **Fix (one function replaced, everything else pinned):** stars within 0.6 px of a free star are
  merged into its PSF column; star fluxes are constrained to be ≥ 0 (NNLS); a neighbour pinned at
  0 gets its flux from the Gaia RP ratio for converting amplitudes (flagged).
- Same target, sectors, controls and pass rule. Exploratory: TIC 4638108 and TIC 44997521 are
  added. Predictions: CONTROLS_PASS 60%; TIC 93622019 WS_UNRESOLVED 75% (a Gaia source 2.39″
  away cannot be excluded by any TESS centroid); PIX_ON_TARGET in every sensitive sector 80%.

**DR4 runbook addendum 1:** `runbook/dr4-addendum.md`.
- **Step g4b (pre-registered out-of-sample test):** the N_comp period flag from Gaia's own epochs
  on every DR4 transit candidate (FLAG_UNIQUE if N_comp ≤ 10). R-g4b: REPLICATES if AUC ≥ 0.70 and
  p ≤ 0.01 on DR4's known planets. Prediction: REPLICATES 65%.
- Step g5 (the edge-on double-lined screen on DR4), the pixel step after G6 (only if the amended
  pixel test passes its controls), and step (i) pinned at b6ae340a (rehearsal passed).

**Prior art, TESS Ten Thousand (T10K) catalogue:** `findings/2026-11-23-t10k-check.md`. Reached
through VizieR's CfA mirror (control row found). **HD 250735 (TIC 400170926) is not in T10K.**
TIC 93622019 and TIC 4638108 are only in T10K's unvetted list (network score > 0.9, never
classified); TIC 44997521 is not in it. ExoFOP still lists no TOI or CTOI for TIC 93622019,
4638108 or 44997521 (23 Nov).

## Earlier (22 Nov, ~23:00 UTC): the epoch test graded (T3 PREDICTIVE, T1 failed); TIC 93622019 pixel test ran (controls failed)

**Graded (pre-registered):** `findings/2026-11-22-vpt-epochs-results.md`, data `data/vpt-epochs-v2/`
(job gaia-vpt-epochs-v2, `vpt_epochs` 0.1.1; all 214 Gaia DR3 transit candidates, 11,081 Gaia DR3
G-band epochs, now saved in the repo).
- **T3 PREDICTIVE (prediction 30%): Gaia's own photometry flags its wrong transit periods.**
  N_comp counts box-search peaks at least 0.9 × as strong as the one at Gaia's period. It separates
  the 15 right periods from the 157 wrong ones with AUC 0.858 (one-sided p = 2.4 × 10⁻⁶). Gaia DR4
  publishes epoch photometry for every source, so every DR4 transit candidate can get this flag on
  release day without TESS. Known failure: TIC 93622019's 4:3 alias has N_comp = 4.
- **T1 TIME_BAD, so WHY is INVALID (as registered).** The cause is a definition, not the times. For
  all 13 controls, every real-transit epoch is inside Gaia's set (coverage 1.0), but Gaia DR3's
  `num_in_transit` counts about 2.6 times more epochs than lie inside Gaia's own `transit_duration`.
  That capped purity at 0.3-0.45 even for correct periods.
- Exploratory: none of the 118 testable wrong-period systems is UNRELATED. The real transit shows in
  Gaia's own epochs at S/N ≥ 3 for 110 of them. In Gaia's data the true period scores at or above
  Gaia's period for 85 of 157 (predicted to exceed half: 40%; it did).

**Amendment 2 (pre-registered, not blind):** `findings/2026-11-22-vpt-epochs-amendment-2.md`, code
`patch_vpt_epochs_012.py` and `vpt_epochs_extras.py` with tests, job gaia-vpt-epochs-box-v1 (queued).
- Gaia's in-transit set becomes the epochs inside Gaia's own box. T1 and WHY are re-graded on the
  same epochs, and T3 must reproduce exactly. Predictions: TIME_OK 80%; then MIXED 45%,
  ALIAS_DOMINATED 35%.
- **New blind test:** does Gaia's photometry show TIC 93622019's dip at the TESS ephemeris
  (2.1238933 d), not only at Gaia's alias? GAIA_SEES_TESS_EPHEMERIS needs S/N ≥ 3 and p ≤ 0.01
  against 1,000 phase shifts. Prediction 75%.

**TIC 93622019 pixel test (job tic93622019-pixel-v1):** `findings/2026-11-22-tic93622019-pixel-results.md`,
data `data/tic93622019-pixel-v1/`.
- **CONTROLS_FAIL, not graded.** HATS-67 b came out WS_ON_TARGET. HATS-58 A b was UNTESTABLE: its
  0.74″ companion makes the free-flux PSF fit give a negative flux (NEGATIVE_FLUX).
- Target, reported only: two sensitive sectors (64, 99), both PIX_ON_TARGET (93-96% of the lost light
  on the target). Combined centroid 0.47″ ± 2.23″ from the target (WS_UNRESOLVED). Deblended depth
  1.284% ± 0.014% gives 1.50-1.55 R_Jup. Odd and even depths are equal (z 0.12), and no secondary
  is seen (3σ < 0.70%). Refined P = 2.1238933 ± 0.0000030 d.
- The only star within 3σ, Gaia DR3 5345417757181557248 at 2.39″, is **G = 19.56**. Its RP (16.78)
  is contaminated by the target (BP/RP excess 10.0). It holds 0.16% of the target's G flux and
  cannot make a 1.28% dip (checked after the run).
- Not sent to ExoFOP yet. Next: the Gaia-epoch test above, then a dated fix of the NEGATIVE_FLUX
  failure and a re-run (registered 23 Nov, see top).

**DR4 step (i) rehearsal passed (job gaia-dr4-astro-adapter-v1, 22 Nov 19:00 UTC):** data
`data/dr4-astro-adapter-v1/`. All unit tests and self-tests (S1-S5) passed. R1: 400 of 400 real
DR3 orbits converted to DR4's Campbell form and back return DR3's own correlations, errors and
conjunction times (largest differences 1.8 × 10⁻¹⁵ and 0 d). Step (i) runs on release day with
`dr4_rows.py` / `run_search_dr4.py` at commit b6ae340a25f92c2d16dbcc5212cf9f26f6369951.

## Earlier (22 Nov, ~19:30 UTC): epoch test's fallback fixed; DR3 rehearsal recomputed; the full Gaia SB2 x TESS screen pre-registered

**Amendment 1 to the epoch test:** `findings/2026-11-22-vpt-epochs-amendment-1.md`, code
`patch_vpt_epochs_011.py` with tests `test_patch_vpt_epochs_011.py`, data `data/vpt-epochs-v1/`.
- Job gaia-vpt-epochs-v1 stopped before seeing any data. ESA's DataLink answered 503, and our
  fallback to ESA's bulk files matched no star to a file. The cause: the files are indexed by
  HEALPix level 8 (`source_id >> 43`), and 0.1.0 used level 12 (`>> 35`). Fixed by importing 0.1.0
  unchanged and replacing that one function. Labels and predictions are unchanged, and the test
  is still blind. Job gaia-vpt-epochs-v2 ran on 22 Nov (graded, see above).

**The step-g DR3 rehearsal recomputed by code:** `findings/2026-11-22-vpt-dr3-comb-check.md`,
data `data/vpt-dr3-comb-v1/`. Every count we made by hand holds (15 of 176 periods right, 14 of 15
known planets, 46 of 330 control hits, 7 of 19 new candidates seen, RVS 8 of 12 / 2 of 10 / 2 of
100, the same two survivors).

**Pre-registered:** `findings/2026-11-22-sb2-screen-prereg.md`, code `sb2_screen.py` 0.1.0 with
tests (`test_sb2_screen.py`), job sb2-edgeon-screen-v1 (graded 23 Nov, see top).
- All 184 edge-on Gaia DR3 double-lined orbits (P < 8 d, M1 sin³i ≈ M1) against TESS's SPOC
  detections: which eclipse at half the orbital period (twins) or at the period, and which of
  those are in no catalogue (VSX, the Villanova TESS EB catalogue, ExoFOP, SIMBAD, Gaia's own
  eclipsing tables). Each new one would be a double-lined eclipsing binary with Gaia masses.
- Predictions: S0 REPLICATES 80%; S1 HALF_DOMINANT 75%; S3 CONTROLS_OK 85%; at least 1 new
  outside the pilot 75%, at least 3 new 45%; TIC 400170926 comes out new 85%.

**SIMBAD checked (Harvard mirror; CDS still unreachable), 22 Nov ~19:00 UTC:**
- TIC 93622019, TIC 4638108 and TIC 44997521 each have a single SIMBAD reference, Gaia DR3's
  variability overview (Eyer et al. 2023). ExoFOP still lists no TOI, CTOI or follow-up file for
  any of the three.
- **TIC 400170926 is HD 250735** (BD+32 1172, TYC 2423-351-1). SIMBAD types it SB* from Gaia's
  orbit and lists four references: the HD catalogue, Gaia DR3's variability and non-single-star
  papers, and a 2018 red-clump calibration paper (Ruiz-Dern et al. 2018). None reports eclipses.

**Code now in the repo:** `pixel_which_star.py` 0.1.0 and its tests (pre-registered 22 Nov; the
tests import `tyc_pixel.py` from commit c16e7a2, which job tic93622019-pixel-v1 downloads, so
they ran in that job, where they passed, not in the commit check).

## Earlier (22 Nov, ~16:00 UTC): TYC 6340-23-1's eclipse is on the target (graded); TIC 93622019 pixel test pre-registered

**Graded (pre-registered):** `findings/2026-11-22-tyc6340-pixel-results.md`, data
`data/tyc6340-pixel-v2/` (job tyc6340-pixel-v2, `tyc_pixel.py` 0.1.1, TESS sector 92 pixels).
- **The 6.8% eclipse is on TYC 6340-23-1.** The PSF fit gives 99.85% of the lost light to the
  target (95%: 99.73-100.01%). The eclipse centroid is 0.5″ (0.15σ) from the target's Gaia
  position and 29.6σ from the only nearby star bright enough to make it (G 12.55, 94″). All
  three controls passed. No star that Gaia DR3 resolves can make the eclipse.
- **Deblended depth 0.0679 ± 0.0004**, 11% deeper than the QLP depth behind the 0.224 R_sun
  radius (DEPTH_CONSISTENT, OVERSIZE_SURVIVES). The label stays B_OVERSIZED_COMPANION; still
  not called inflated.
- **SuperWASP (2006-2008) and TESS (2025) join at a unique cycle count:** P = 2.3287747 ±
  0.0000003 d, T0 = BJD_TDB 2460817.00291 ± 0.00012. This agrees with Gaia DR3's
  spectroscopic period (z = −1.11). **All 8 registered predictions came true.**

**Pre-registered:** `findings/2026-11-22-tic93622019-pixel-prereg.md`, code
`pixel_which_star.py` 0.1.0 with tests (`test_pixel_which_star.py`), inputs
`runbook/pixel/targets.json`, job tic93622019-pixel-v1 (ran 22 Nov; controls failed, see above).
- A generic TESS pixel test that imports tyc_pixel's PSF core unchanged. It runs on all six
  TESS sectors of the new candidate TIC 93622019 and combines the transit centroid on the sky.
  It compares that centroid with every Gaia star within 120″ bright enough to make the dip.
  It also measures the deblended depth, plus secondary-eclipse and odd/even depths with
  event-to-event (red-noise) errors.
- Controls by rule: HATS-67 b and HATS-58 A b, the two nearest confirmed planets of similar
  brightness and depth. HATS-58 A has a companion 0.74″ away (Espinoza et al. 2019), so it
  is expected UNRESOLVED.
- Predictions: WS_ON_TARGET 80%; CONTROLS_PASS 85%; SEC_DETECTED 30%; OE_CONSISTENT 85%;
  EB_NOT_INDICATED 70%. If ON_TARGET and not EB-like, the candidate goes to ExoFOP as a
  community TOI.

## Earlier (22 Nov, ~11:00 UTC): step G6 rehearsal graded; a period-free TESS search fixes Gaia's periods and finds TIC 93622019

**Graded (pre-registered):** `findings/2026-11-22-vpt-pf-dr3-results.md`, data `data/vpt-pf-dr3-v1/`
(job gaia-vpt-pf-dr3-v1, `vpt_pf.py` 0.1.0, all 214 Gaia DR3 transit candidates, up to 6 TESS sectors).
- **PF1b (primary): where Gaia's period is wrong, the period-free search finds the known period for
  156 of 160 known systems** (0.975, 95% 0.937-0.990): PF_RECOVERS, as predicted (55%). PF1 176 of
  181; PF_WRONG 4 of 181 (PF2 list reliable). Step G6 runs on DR4 as registered.
- **New candidate: TIC 93622019** (Gaia DR3 5345417757181174144, G 12.57 F star, about 590 pc).
  Transits every **2.123885 d**, 0.9-1.05% deep, flat-bottomed, 1.3-1.4 R_Jup; **all six TESS sectors
  alone give the same period**. Gaia's 2.83166 d is a 4:3 alias. The duration fits the star. Gaia's own
  photometry shows the dip on this source. Gaia's spectrograph sees no velocity change (27 visits,
  p 0.51), which rules out companions heavier than about 0.1 M_sun. No TOI, CTOI, TCE, VSX, ASAS-SN or
  T16 entry. Warning sign: a possible 3.9σ secondary eclipse (277 ± 71 ppm). Not called a planet;
  radial velocities decide.
- TIC 248569057 (robust, other period) fails vetting: its 6 h duration is twice the maximum for its
  star, and Gaia flags it as an RV-variable binary (RUWE 3.4).
- Gaia DR3's new candidates with TESS data: 18 of 27 eclipsing-binary-like, 8 planet-like (4 robust).
- **N1-N4 graded:** N1 (TIC 400170926 at half its Gaia orbit) **yes**; its two eclipses are unequal
  (3.92% vs 4.59%), so 5.8959 d is the true period. N3 (TOI-1991 at its Gaia orbit period) yes. N2 and
  N4 no.

## Earlier (22 Nov, ~07:30 UTC): TIC 400170926 eclipses; Gaia's "planet candidate" is an eclipsing twin with Gaia masses

**Exploratory:** `findings/2026-11-22-tic400170926-eclipsing-twin.md`, data
`data/tic400170926/spoc_tces.csv` and `data/sb2-edgeon-pilot/sb2_edgeon_pilot.csv`.
- **TESS's own pipeline (SPOC) finds 6.1%-deep eclipses every 2.947881 d (S/N 1297, 22 events,
  sectors 43, 71, 72): exactly half of Gaia DR3's double-lined orbit period** (2 × 2.947881 =
  5.89576 d against 5.895935 ± 0.000182 d, 0.95σ). The two eclipses look alike, as expected for a
  near-twin pair.
- **Masses from Gaia's orbit:** M sin³i = 1.108 ± 0.030 and 1.019 ± 0.017 M_sun; with eclipses
  (i ≳ 82°) M1 = 1.11-1.14 and M2 = 1.02-1.05 M_sun. A bright (G 9.33) double-lined eclipsing binary
  of two Sun-like stars, which Gaia DR3 lists as a planetary-transit candidate (0.8848 d, class EP).
- **Not in any catalogue we could reach:** VSX (only Gaia's EP import), the TESS EB catalogue
  (controls found), ASAS-SN, Gaia's EB table, ExoFOP; no literature. SIMBAD (checked 22 Nov via its
  Harvard mirror) lists it as HD 250735 with no eclipse reported. The TESS Ten Thousand
  catalogue was checked on 23 Nov: not listed (`findings/2026-11-23-t10k-check.md`).
- Prediction N1 (TESS period 5.8959 d or half) was graded from job gaia-vpt-pf-dr3-v1 (above): yes.
- **Pilot screen of Gaia's edge-on double-lined orbits:** 184 Gaia DR3 SB2 systems with P < 8 d and
  sin³i ≈ 1 (M1 sin³i within 0.95-1.10 of Gaia's m1). Of the 20 brightest with G > 9, 7 have SPOC
  TCEs and all 7 are at half the Gaia period (six within 0.007%); 6 of the 7 are known eclipsing
  binaries (V1010 Cas, ASAS J085256+1449.0, NV TrA, VV Crt, TOI-631, HIP 34208); TIC 400170926 is
  the new one. The full screen was graded on 23 Nov (see top; the pilot's ratio omitted the
  eccentricity factor).
- Gaia's transit period is a near-commensurability, not a harmonic: three eclipse intervals ≈ ten
  Gaia periods (0.047% apart).

## Earlier (22 Nov, ~03:00 UTC): Gaia's orbit catalogue against Gaia's transit list; amendment 2 (NSS screen) before DR4

**Results (exploratory, not blind) and registered predictions:** `findings/2026-11-22-vpt-nss-crossmatch.md`,
data `data/vpt-nss-dr3/vpt_nss_dr3.csv`, code `vpt_nss.py` 0.1.0 with tests (`test_vpt_nss.py`;
commit b8f2525dde1bebdabf2b89a33065aac797771e2d, release v0.46.0).
- **7 of the 214 Gaia DR3 transit candidates have a Gaia DR3 orbit solution.** WASP-18's single-lined
  orbit recovers WASP-18 b (K 1.94 ± 0.14 km/s, 10.5 M_Jup minimum): a positive control.
- **TIC 400170926 (TYC 2423-351-1, G 9.3), one of Gaia's new candidates, is a double-lined binary in
  Gaia's own orbit catalogue:** P 5.8959 d, two Sun-like stars (M sin³i 1.11 and 1.02 M_sun) seen
  nearly edge-on, so eclipses are likely (shown in TESS, see above). Our RVS screen could not test
  it (Gaia DR3 gives no velocity for it). With the 8 RVS-flagged stars, 9 of Gaia DR3's 39
  unconfirmed new candidates now have Gaia's own evidence of a stellar companion.
- **Where Gaia's transit period is wrong, its orbit can be right:** TOI-1991's single-lined orbit
  (6.6591 ± 0.0012 d) matches the TESS period (6.6571 d; already a TFOP false positive, and the match
  was first noted by Tarrants & Mendes 2023), while the transit table gives 3.7463 d.
- **Registered before job gaia-vpt-pf-dr3-v1 ran:** the period-free TESS search finds 5.8959 d (or
  half) for TIC 400170926 (75%), 7.0623 d (or half) for TIC 470993218 (30%), 6.6571 d (or half) for
  TOI-1991 (85%), 0.4602/0.9205/0.2301 d for TIC 207399049 (25%). Graded 22 Nov: yes, no, yes, no.
- **Amendment 2 for DR4 (step g2c):** join every DR4 transit candidate with DR4's orbit table and
  remove double-lined or ≥ 0.08 M_sun companions before the period-free follow-up (g3). Predictions:
  ≥ 70% of NEW candidates with a spectroscopic orbit are stellar (75%); the screen removes at least
  one star the RVS screen could not test (60%).

## Earlier (22 Nov, ~01:45 UTC): Gaia's own spectrograph on all 214 Gaia DR3 transit candidates

**Results (exploratory, not blind):** `findings/2026-11-22-vpt-rvs-full.md`, data
`data/vpt-dr3-v1/rvs/` (job gaia-vpt-rvs-dr3-v1, `gaia_vpt_tess.py` 0.1.1 `--rvs-screen`).
- **8 of the 12 RVS-testable new candidates are radial-velocity variable** (0.67, 95% 0.39-0.86;
  Katz et al. 2023 criterion), against **4 of 110 testable known systems** (0.036), two of which
  host 10-27 Jupiter-mass companions (correct flags). One-sided Fisher p ≈ 2 × 10⁻⁷.
- A hot Jupiter moves its star by 0.1-0.3 km/s, far below this test, so a flag means a stellar
  companion: at least 8 of Gaia DR3's 39 unconfirmed new candidates now have Gaia's own evidence
  against a planet. We found no published RVS screen of them.
- The two survivors (TIC 4638108, TIC 44997521) are too faint for the screen. Still no TOI or CTOI
  on ExoFOP (22 Nov); no ASAS-SN variable-catalogue entry.

## Earlier (21 Nov and before)

Full entries for 21 Nov and earlier (step G6 pre-registration, the survivors' vetting, step (i), the
epoch-test pre-registration, TYC 6340-23-1's neighbour and pixel test, the step-g DR3 rehearsal and
its amendment, the quality-cut tests, ASAS-SN and SuperWASP checks, and the 19-20 Nov results) are
in the git history of this file (commit a34b7885 and earlier) and in their `findings/` files.

## Results of 20 Nov
1. **Gaia's own quality columns cannot single out the real low-mass SB1 orbits**
   (`findings/2026-11-20-quality-cut-results.md`). Write-up:
   https://www.munimtech.com/research/gaia-quality-cut-low-mass-orbits
2. **Our EBLM fitting pipeline failed its pre-registered holdout check**
   (`findings/2026-11-20-eblm-holdout-results.md`): PIPELINE_FAILED.
3. **TYC 6340-23-1**: label B_OVERSIZED_COMPANION; not called inflated. Write-up:
   https://www.munimtech.com/research/tyc-6340-23-1-oversized-companion

## Graded 19 Nov
**Most of Gaia DR3's brown-dwarf-mass SB1 orbits at 1–13 days must be wrong**
(`findings/2026-11-19-sb1-robust-amendment-2-results.md`, data `data/incfloor-v1/`). Write-up:
https://www.munimtech.com/research/gaia-brown-dwarf-orbits-missing-transits

## Leads
1. **Gaia's own transit candidates in TESS** (step g): period-free search graded (PF_RECOVERS; new
   candidate **TIC 93622019**: pixel re-run and Gaia-epoch test queued); the N_comp period flag
   registered as an out-of-sample test on DR4 (g4b); follow-up of TIC 4638108 and TIC 44997521 queued.
   Write-up: https://www.munimtech.com/research/gaia-transit-periods-known-planets
2. **Eclipsing binaries with Gaia masses:** screen graded 23 Nov; three new (HD 250735, CD-28 7251,
   TYC 3616-2395-1); eclipse timing against Gaia's orbits queued (sb2-new-ebs-timing-v1); then
   eclipse-model fits for masses and radii; then Gaia DR4's SB2 list (step g5).
3. **A transiting companion first found by Gaia astrometry** (step i, DR4): rehearsal passed.
4. **Do Gaia DR3 inclinations hold up against real eclipses?** 58 of 162 near-edge-on orbits
   eclipse against 80.7 expected (p = 2 × 10⁻⁵). Gaia DR4 decides.
5. **TYC 6340-23-1** (B_OVERSIZED_COMPANION): mass test on DR4 day (step a5).

## Lessons the pipeline now encodes (newest first; full list in commit a34b7885)
- **A failed lookup is not a negative answer, even when the rule says so:** the screen's Villanova
  lookups all returned HTTP 400, so 3 of its 8 "new" binaries were in the TESS EB catalogue. Use a
  catalogue's VizieR copy with a control row, and treat a 100% failure rate as a broken check.
- **Recompute a pilot with the registered formula before predicting replication:** the pilot had
  left (1 − e²)^1.5 out of M1 sin³i.
- **A survey that resolves what TESS blends settles "which star" for free** (Gaia's epochs for
  CD-28 7251, 23 Nov; TIC 44997521 and TIC 4638108, 21 Nov).
- **Stars a PSF cannot separate must share one column, and fluxes must be non-negative.**
- **Check what a catalogue count column really counts before building a test on it.**
- **Pair every empty answer with a control query**, and run the controls first.
- **Put a self-test in every job and make it run first.**

## Prior-art sources we check for every eclipsing system
AAVSO VSX (API at vsx.aavso.org, or its VizieR copy B/vsx), the TESS EB catalogue (Prša et al.
2022; VizieR J/ApJS/258/16 via vizier.cfa.harvard.edu, since the live site's per-TIC pages answered
HTTP 400 on 23 Nov), the TESS Ten Thousand catalogue (Kostov et al. 2025; J/ApJS/279/50), IJspeert
et al. 2021 OBA EBs (J/A+A/652/A120), Gaia DR3 vari_eclipsing_binary, vari_classifier_result and
binary_masses (method Eclipsing+SB2), the ZTF and ASAS-SN variable catalogues (II/366/catv2021),
Rowan et al. (2023), ExoFOP, the SPOC TCE list, SIMBAD (Harvard mirror), Kepler KOIs, and Gaia DR3
nss_two_body_orbit.

## Gaia DR4 (2 December 2026)
- **ESA's Gaia archive is closed from 25 November 2026 12:00 CET until DR4 opens on
  2 December 12:00 CET.** Jobs that still need DR3 tables fall back to the Heidelberg DR3 mirror;
  DR3 epoch photometry falls back to ESA's bulk CDN files, and the 214 transit candidates' epochs
  are in the repo.
- Release-day runbook: `runbook/dr4-release-day.md` plus `runbook/dr4-addendum.md` (steps g4b and
  g5, the pixel step, step i pinned). Step G6 uses `vpt_pf.py` at commit
  9bf9704211bd129204bb4de091f38021ec76d301; step g2c uses `vpt_nss.py` at commit
  b8f2525dde1bebdabf2b89a33065aac797771e2d.
