# Pre-registration: which of Gaia DR3's edge-on double-lined binaries eclipse in TESS?

MV2, Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.
Written 2026-11-22 (~19:30 UTC) before job **sb2-edgeon-screen-v1** ran. Code: `sb2_screen.py`
0.1.0 with tests `test_sb2_screen.py` (this commit).

## Why

Gaia DR3 gives double-lined (SB2) spectroscopic orbits with both velocity amplitudes, so each
system has M1 sin³i and M2 sin³i. Where TESS also sees eclipses, the inclination is known and
the two masses follow, along with radii from the eclipse shape. Double-lined eclipsing binaries
are the benchmarks of stellar astrophysics. Our pilot (`findings/2026-11-22-tic400170926-eclipsing-twin.md`,
section 6) took the 20 brightest G > 9 stars of a 184-star edge-on sample. 7 have SPOC TCEs, all
at half the Gaia period, and one of the 7 (TIC 400170926 = HD 250735) is in no catalogue we could
reach. This job runs the same screen on all 184.

Prior work: Rowan et al. (2023, MNRAS, doi:10.1093/mnras/stad1560) matched Gaia DR3 SB2 orbits with ASAS-SN
eclipsing binaries (ASAS-SN saturates near V ≈ 10-11). Gaia DR3 itself combines eclipsing and SB2
solutions for 53 stars (`binary_masses` method Eclipsing+SB2). We found no screen of Gaia's SB2
orbits against TESS's own pipeline detections.

## Sample (the pilot's rule, unchanged)

Gaia DR3 `nss_two_body_orbit` solutions of type SB2 or SB2C, joined with `binary_masses` method
SB2+M1, P < 8 d, and M1 sin³i = 1.036149×10⁻⁷ (1 − e²)^1.5 (K1 + K2)² K2 P between 0.95 and 1.10
times `binary_masses.m1` (e = 0 where no eccentricity was fitted). The ESA TAP count of SB2+M1
solutions with P < 8 d is 2,436 (22 Nov 2026).

## What the job does

For each selected star: Gaia DR3 → TIC (ExoFOP), the SPOC TCE list and each TCE's period, depth
and S/N (exo.MAST DV header). A TCE with S/N ≥ 7.1 (or no S/N given) **matches** if its period is
within 0.5% of P/2 (HALF) or P (FULL). Stars with a match are checked in VSX (30″), the Villanova
live TESS EB catalogue, ExoFOP TOIs, SIMBAD (Harvard mirror, 10″) and Gaia DR3's own
`vari_eclipsing_binary`, `vari_classifier_result` (class ECL) and Eclipsing+SB2 tables. **NEW** =
a match and none of those (an unreachable source counts as "not found", and we will say so).

## Tests and labels

- **S0 (replication):** the rule selects 184 stars and includes all 20 pilot stars →
  REPLICATES, else DIFFERS (reported, the screen still runs).
- **S1 (twin eclipses):** among stars with any qualifying TCE, the share with one at P/2.
  HALF_DOMINANT ≥ 0.80; MIXED 0.50-0.80; NOT_DOMINANT < 0.50; UNTESTABLE if fewer than 10.
- **S2 (discoveries):** number of NEW stars outside the 20-star pilot.
- **S3 (positive control):** stars that VSX lists as eclipsing and that have a qualifying TCE:
  the share at P or P/2. CONTROLS_OK ≥ 0.80; UNTESTABLE if fewer than 3.

## Predictions (fixed now)

| test | prediction | probability |
|---|---|---|
| S0 | REPLICATES | 80% |
| S1 | HALF_DOMINANT | 75% |
| S3 | CONTROLS_OK | 85% |
| S2 | at least 1 NEW outside the pilot | 75% |
| S2 | at least 3 NEW outside the pilot | 45% |
| pilot | TIC 400170926 comes out NEW | 85% |

## What follows from each outcome

- NEW stars get a dated vetting note (literature, ASAS-SN, the TESS Ten Thousand catalogue when
  VizieR is reachable) before any of them is called new in public, then a VSX submission when MV2
  has an AAVSO account.
- The same screen runs on Gaia DR4's SB2 list on 2 December (runbook step g5, to be added after
  this job is graded).
- Stars with no TCE are not "non-eclipsing": SPOC searches only 2-minute targets. A full-frame
  image search of them is a separate, later step.

## Limits

TCE periods and depths come from SPOC's planet-model fits. They locate eclipses but do not
measure binary parameters. VizieR (and so the TESS Ten Thousand catalogue) was unreachable when
this was written. The job checks catalogues only for stars whose TCE matches.
