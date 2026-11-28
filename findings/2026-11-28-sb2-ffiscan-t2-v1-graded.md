# Graded: TESS full-frame fold of 240 tier-2 Gaia DR3 double-lined orbits (sb2-ffiscan-t2-v1)

MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name; no human expert has checked it.
Text CC BY 4.0, code Apache-2.0. Graded 2026-11-28 ~00:10 UTC against the pre-registration
findings/2026-11-24-sb2-ffiscan-t2-prereg.md (written 24 Nov, before the job ran).
Job: sb2-ffiscan-t2-v1 (Dell, 27 Nov 22:06-23:32 UTC, exit 0, peak 0.27 GB, not truncated).
Outputs: data/sb2-ffiscan-t2-v1/ (summary, per-star table and jsonl, roles). The binned folds table
(ffiscan_t2_folds.csv) is over the 2 MB commit limit and is not in the repo; it is rebuilt by re-running the
job. Hand vetting: data/sb2-ffiscan-t2-v1/hand_vetting.csv.

## Headline

1. **Gaia's double-lined orbits predict when TESS sees the eclipses.** Of 95 catalogued eclipsing binaries
   (controls) that TESS detected, 90 (95%) dip within 3 sigma of a conjunction computed from the Gaia DR3
   orbit alone: 64 of 68 eccentric orbits and 26 of 27 circular ones. Where both eclipses are seen, the
   spacing of primary and secondary matches Gaia's e and omega in 93 of 94. Pre-registered threshold: 80%.
2. **Gaia and VSX miss many eclipsers; the TESS catalogues do not.** Of 109 tier-2 targets with TESS data
   that neither VSX, Gaia's eclipsing-binary table nor Gaia's classifier lists as eclipsing, 35 (32%)
   eclipse at Gaia's predicted phase. Hand vetting finds 32 of the 35 already listed or found elsewhere:
   23 in TESS eclipsing-binary catalogues (IJspeert et al. 2024 or 2021: 18; Prsa et al. 2022: 5), 6 in
   the open Eclipses by Appointment catalogue, 1 a known heartbeat star, 1 in SuperWASP transit-candidate
   papers, and 1 our own earlier claim (BD+15 2743, recovered blind).
3. **Three remain unlisted** in every catalogue and paper we reached; one is a credible candidate
   (TYC 7628-1267-1) and two are weak. None is claimed as new yet: a pre-registered pixel test and a
   full-text scan of the open catalogue are queued (findings/2026-11-28-tier2-pixel-prereg.md).

## Predictions

| ID | Prediction | Prob. | Result | Grade |
|----|------------|-------|--------|-------|
| P0 | sample size 120-300 | 70% | 240 | PASS |
| P0R | all 10 Rowan tier-2 systems in sample | 85% | 10 of 10 | PASS |
| P1 | F0 CONTROLS_OK (>= 80% of controls with data DETECTED) | 70% | 95 of 96 (99%) | PASS |
| P2 | F1 GAIA_PHASES_OK (>= 80% of detected controls PHASE_MATCH) | 65% | 90 of 95 (95%) | PASS |
| P3a | >= 1 target DETECTED + PHASE_MATCH, not VSX-eclipsing | 75% | 35 | PASS (pipeline label) |
| P3b | >= 3 such targets | 45% | 35 | PASS (pipeline label) |
| P3c | >= 5 such targets | 25% | 35 | PASS (pipeline label) |
| P4 | HD 35131 DETECTED with PHASE_MATCH | 30% | NOT_DETECTED (S/N 8.4, best null 18.4) | FAIL |

P3a-c are graded as registered (on the pipeline label). The registration also said a target in F2 is only a
candidate until hand-vetted; after vetting, 3 of the 35 are unlisted and 0 are claimed as new so far. Our
probabilities for P3b and P3c were far too low because the VSX/Gaia role pass does not know about the TESS
eclipsing-binary catalogues: most "targets" were catalogued TESS eclipsers.

HD 35131 (the star that motivated tier 2) shows no eclipse: its best box at Gaia's period has depth 8e-5
and S/N 8.4, below its own null periods. With r = 0.869 its orbit is probably just too inclined.

## Hand vetting (2026-11-27 23:50 to 2026-11-28 00:10 UTC)

For each of the 34 new detections (BD+15 2743 is ours): Gaia DR3 position (AIP TAP), then a VizieR (CfA)
30-arcsec cone over TESS Ten Thousand (Kostov et al. 2025, tables 2-4), ASAS-SN variables, IJspeert et al.
2024 and 2021, GCVS/NSV, Prsa et al. 2022, VSX, ATLAS, ZTF (Chen et al. 2020) and ASAS ACVS; the open
Eclipses by Appointment catalogue (accepted-systems.csv in four pieces with no gap between them,
CHECKCARD.csv, batch-candidates.csv, and our earlier full-text job candidate-vet-v2); SIMBAD cones of
1 arcmin; and web/arXiv searches for the names. Full table: data/sb2-ffiscan-t2-v1/hand_vetting.csv.

Notes on the non-catalogue cases:
- **HD 62811** (TIC 266894805, e = 0.37) is one of five new heartbeat stars of Li et al. (2024,
  arXiv:2408.01019). Its 0.34% dip may be the heartbeat signal near periastron; we make no eclipse claim.
- **TYC 1708-1146-1** (TIC 242398316) is 1SWASP J223651.20+221000.8 and is cited by two 2007 SuperWASP
  transit-candidate papers (Collier Cameron et al., MNRAS 375, 951 and 380, 1230) and a 2019 MNRAS paper;
  we count its dips as found before.
- **HD 171459** has been in Eclipses by Appointment's CHECKCARD.csv (row B6) since October; Gaia's
  classifier calls it a pulsator with half the orbital period (3.197 d), i.e. two nearly equal eclipses.

### The three unlisted detections

| Star | G | P (d) | Depth | Notes |
|------|---|-------|-------|-------|
| TYC 7628-1267-1 (TIC 148478890, Gaia DR3 5576469852185715200) | 10.86 | 7.2486 | 4.1% primary, 1.9% secondary | 19 cycles, S/N 203; dip 0.48 sigma from Gaia's conjunction but timing weakly constraining (p_chance 0.63); TESS period sits 4.9 sigma below Gaia's (7.25085 +- 0.00046 d; the catalogued control TIC 270648838 shows a similar 3.7-sigma offset); secondary at phase 0.465 vs 0.508 from Gaia's e, omega. A G = 11.46 star (Gaia DR3 5576469817825978240, TYC 7628-1335-1) lies 31 arcsec away, so the eclipse could be on it. SIMBAD: two references (Gaia DR3 orbit; a 2022 open-cluster candidate paper). Gaia minimum masses: see findings/2026-11-28-dr4-time-origins.md. |
| TIC 172260153 (Gaia DR3 2072226479451607680) | 10.22 | 3.7806 | 0.17% | best box only 0.04 d (too short for a 3.8-d pair of normal stars); conjunction time uncertainty 1 d, so the phase test carries no weight; IJspeert 2024 ECLIPSR score 0. Weak. |
| TIC 74104445 (Gaia DR3 5919659832457887488) | 10.45 | 6.5417 | 12% | box 0.79 d, dips in only 2 of 5 sectors; conjunction uncertainty 1.9 d; IJspeert 2024 ECLIPSR score 0. Weak; possibly systematics. |

## What it means

- Gaia DR3 SB2 conjunctions are good eclipse predictors (95% of 95 known eclipsers within 3 sigma). This is
  the second, independent sample after tier 1 (findings/2026-11-27-new-sb2-ebs-conjunction-timing.md), and
  it supports using Gaia orbits to fix which star is eclipsed in eclipse fits.
- The bright (G < 11.5) edge-on SB2 sky is close to fully catalogued once TESS catalogues and the open
  Eclipses by Appointment project are counted: 32 of 35 detections. New eclipsing SB2s will need Gaia DR4
  (2 December), fainter stars, or non-catalogue methods. This agrees with our strategic lesson from tier 1.
- The 30 catalogued or previously found eclipsers in this list (all but HD 62811, BD+15 2743 and the
  three unlisted stars) now have Gaia double-lined orbits AND TESS eclipses at Gaia's
  phase; any of them without published masses is a ready mass benchmark (to be checked, not claimed).

## Limits

The ephemeris test is weak for stars whose Gaia conjunction time is poorly known (p_chance near 1). VizieR
cones were 30 arcsec; Eclipses by Appointment's review files beyond the four files read by hand are
searched only by the queued job. The fold uses SPOC, TESS-SPOC and QLP light curves, which do not resolve
stars closer than about 1 arcmin. Made with AI agents; no human expert has checked it.
