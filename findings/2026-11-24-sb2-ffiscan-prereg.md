# Pre-registration: do Gaia's edge-on double-lined binaries eclipse when Gaia's orbit says they should?

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0, code Apache-2.0. Registered 2026-11-24 (~09:30 UTC), before the job ran and before
any light curve of the target stars was read for this test.
Code: `sb2_ffiscan.py` 0.1.0 (tests `test_sb2_ffiscan.py`), inputs `runbook/ffiscan/`.
Job: **sb2-ffiscan-v1** (1.5 GB, network; unit tests, then a self-test, then the run).

## Why

The 23 Nov screen (`findings/2026-11-23-sb2-screen-results.md`) used only TESS SPOC pipeline
detections (TCEs). SPOC searches 2-minute targets, so **95 of the 161 edge-on Gaia DR3 double-lined
binaries had no TCE**, and the screen never looked at their light curves. These are bright stars
(G 6-11.5) whose Gaia orbits already give both minimum masses. Any that eclipse are new benchmark
candidates. Gaia's orbit also predicts *when* each eclipse must happen (the conjunctions), which
gives a blind test that a pipeline period match cannot give: a dip at the right period **and** the
right time is very unlikely to come from a neighbour or from noise.

## Prior work (checked 24 Nov)

- **Eclipses by Appointment** (https://github.com/Snowstar38/eclipses-by-appointment, open AI-agent
  project; manuscript under review) folds TESS at Gaia DR3 spectroscopic-orbit periods and checks
  Gaia-predicted conjunction times. Its strata are mostly G 10-12.7 and longer periods; it lists
  TYC 3616-2395-1, which is why our claim on that star is withdrawn
  (`findings/2026-11-24-tyc3616-prior-listing.md`). **Every candidate from this job is checked against its
  `accepted-systems.csv` before it is called new.**
- Chopard-Vilhem 2026 (RNAAS 10, 323; Zenodo doi:10.5281/zenodo.23342416): near-edge-on *astrometric*
  orbits, periods 26-242 d. No overlap with P < 8 d SB2s.
- Liakos 2025 (arXiv:2506.14395): Gaia SB2 amplitudes + TESS for four known EBs.
- What is new here: the test of Gaia SB2 conjunction-time predictions against TESS eclipses as a
  measured accuracy on a rule-chosen control set, and a conjunction-gated search of the bright
  (mostly G < 10) edge-on SB2s that pipeline detections missed.

## Sample and roles (fixed by rule)

Input: `data/sb2-edgeon-screen-v1/sb2_screen.csv` at commit 80be282 (183 rows), read by the job from
GitHub at that pinned commit. Stars with status OK and a TIC number (161). Roles from the table's own
columns:
- **control**: catalogued eclipsing (`vsx_eclipsing`, `gaia_eb` or `simbad_eb` true). These lookups
  exist only for stars that had a TCE, so controls are the pipeline-detected, catalogued EBs (about 50).
- **toi**: a TOI (4; all four are retired false positives/EBs on ExoFOP, checked 24 Nov). Reported only.
- **target**: all others (about 105: the 95 without a TCE plus TCE stars not catalogued eclipsing).
- Hand-vetted before this job (reported, not counted as new): HD 250735 and CD-28 7251 (our new EBs),
  TYC 3616-2395-1, HD 21273, HIP 34208, BD+83 227, BD+37 3347, HD 144359.

## Method (as coded)

1. Gaia DR3 orbit from ESA TAP, else AIP Potsdam TAP. **Anchor:** its period must equal the screen
   table's to 1e-9 (relative) and t_periastron must exist, else the conjunction test is UNTESTABLE.
2. Up to 6 TESS sectors per star (SPOC 120 s first, then TESS-SPOC, then QLP; one per sector), spread
   evenly over the available sectors.
3. Per sector: binned-median trend (window clip(P, 0.5, 3) d, low points clipped); fit and remove
   2 harmonics of Gaia's period (low points clipped, so eclipses are not fitted); residuals in units of
   the sector's robust scatter, winsorised at ±8.
4. Box search over a period grid within ±5σ of Gaia's period (200 phase bins; box widths 1-24 bins;
   ≥ 10 points; the box must be deeper than its two flanking boxes by ≥ 0.5 of its depth).
5. Null: the same search at 12 off-periods (0.73-1.46 × P, away from ratios with denominators ≤ 8).
6. **DETECTED** if S/N ≥ 10, S/N ≥ 1.5 × the best null S/N, and the box holds points from ≥ 2 cycles.
7. For DETECTED stars: a second dip (S/N ≥ max(7, best null), outside the first box ± one width);
   Gaia's conjunction times by Monte Carlo over Gaia's errors (P, t_periastron, e, ω; no correlations).
   **PHASE_MATCH** if the dip time is within 3σ of either conjunction (σ combines the Monte Carlo spread
   and a quarter of the box width). **SEP_MATCH** if the two dips' phase separation agrees within 3σ
   with Gaia's (c2 − c1) or 1 − (c2 − c1). `p_chance` is the share of the orbit the two 3σ windows cover.
8. Circular Gaia solutions (SB2C, no e and ω) are used with e = 0 and **ω = 0, so conjunctions at
   phases 0.25 and 0.75 after t_periastron.** This convention was chosen from one known case and is
   not blind: HD 250735's TESS pipeline epoch falls 0.042 d from phase 0.25 against a 0.064-d
   prediction error (ω = 90° would put it 1.4 d off). The controls test it; F1 is also reported for
   circular and eccentric orbits separately.
9. For DETECTED non-control stars, VSX is queried (30″). A phase-matched target that VSX lists as
   eclipsing is reported as known, not as a candidate.

Self-test inside the run: geometry, the HD 250735 convention check, a synthetic eccentric EB with spot
modulation (must be DETECTED, PHASE_MATCH, SEC_DETECTED, SEP_MATCH), a synthetic ellipsoidal
non-eclipsing star and pure noise with outliers (both must be NOT_DETECTED).

## Grades

- **F0 (controls):** CONTROLS_OK if ≥ 80% of controls with data are DETECTED, else CONTROLS_FAIL.
- **F1 (Gaia's conjunction times):** among DETECTED controls with a usable orbit, GAIA_PHASES_OK if
  ≥ 80% are PHASE_MATCH, else GAIA_PHASES_POOR. Also the SEP_MATCH rate.
- **F2 (candidates):** targets (not hand-vetted) that are DETECTED and PHASE_MATCH and not eclipsing in
  VSX. Graded only if F0 is CONTROLS_OK. Each candidate then gets a hand check (Prša 2022 and TESS Ten
  Thousand via VizieR, ASAS-SN, SIMBAD, ExoFOP, Eclipses by Appointment, web search) before it is
  called new; the count after that check is the result.
- **F3 (our two new EBs):** HD 250735 and CD-28 7251 both DETECTED and PHASE_MATCH (not blind).
- If the job stops at its 300-minute limit, stars are processed in a fixed order (Gaia G, brightest
  first) and grades use the stars processed, said plainly.

## Predictions (fixed now)

| test | prediction |
|---|---|
| F0 CONTROLS_OK | 75% |
| F1 GAIA_PHASES_OK (all controls) | 60% |
| F1 eccentric controls match better than circular ones | 50% |
| F2 ≥ 1 candidate before hand vetting | 70% |
| F2 ≥ 3 candidates before hand vetting | 40% |
| ≥ 1 candidate survives hand vetting as new | 45% |
| F3 BOTH_RECOVERED | 75% |
| self-test PASS on the first run | 65% |

## Known limits, written down before the run

- Contact and very short-period binaries (P < 1 d) are partly removed by the harmonic fit; a few
  controls may fail for that reason.
- Full-frame light curves of stars with bright neighbours are diluted; a dip at Gaia's period and
  conjunction time is still strong evidence that the target is the eclipsing star.
- The conjunction error ignores correlations between Gaia's orbital elements.
- Controls are pipeline-detected catalogued EBs, so they are easier than the targets.
