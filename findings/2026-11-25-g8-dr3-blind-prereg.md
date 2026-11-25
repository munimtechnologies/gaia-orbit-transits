# Pre-registration: blind Gaia DR3 run of rule g8 on every double-lined orbit with epoch photometry

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked it yet.
Text CC BY 4.0; code Apache-2.0. Written 2026-11-25 ~15:00 UTC, **before** job `g8-dr3-blind-v1`
ran and before any star of the sample was classified. Code: `g8_dr3_blind.py` 0.1.0 +
`test_g8_dr3_blind.py`; the rule is `sb2_ecl_dr4.py` 0.1.0 at commit af65d7b, unchanged.

## Question

Gaia's own eclipsing-binary search (Mowlavi et al. 2023) had to find a period in about 40-100
sparse epochs. For a double-lined binary Gaia's radial velocities already give the period and both
conjunction times, so a few faint epochs at the predicted conjunctions, in two different
eclipses, are enough. How many Gaia DR3 double-lined binaries eclipse in Gaia's own photometry
although Gaia does not call them eclipsing? The wow, if it works: a batch of new eclipsing
double-lined binaries (stars with directly measurable masses and radii) found by Gaia alone,
before Gaia DR4 (2 December) multiplies the sample.

Prior work searched (25 Nov 2026): our own DR3 rehearsal on 50 hand-saved stars
(findings/2026-11-25-g8-rehearsal-dr3-results.md; 5/5 flags real, 0 null flags); web search
"Gaia DR3 SB2 orbits epoch photometry eclipses at spectroscopic conjunction"; Rowan et al. 2023
(arXiv:2212.02509, SB2 x ASAS-SN EBs, V > 11 only); Hon/Beck et al. 2023 (arXiv:2307.10812, edge-on
Gaia binaries in TESS); Chopard-Vilhem 2026 (Zenodo 23342416, astrometric orbits, P 26-242 d);
Eclipses by Appointment (GitHub, Gaia periods x TESS, commit 9334ec7). None runs a conjunction test
on Gaia's epoch photometry for all DR3 double-lined orbits.

## Sample (fixed)

All rows of AIP `gaiadr3.nss_two_body_orbit` x `gaiadr3.gaia_source` with
`nss_solution_type LIKE 'SB2%'`, `0.4 <= period <= 15.0` d and `has_epoch_photometry = 'True'`.
Counted on 25 Nov before the run: **927 stars (744 SB2, 183 SB2C)**; 479 of the SB2 orbits in this
period range are in Gaia's `vari_eclipsing_binary` table (count without the epoch condition).
The job checks the count and stops (exit 2) if the sample query returns a different number.

## Method (fixed)

- Epochs: `gaiadr3.epoch_photometry` G transit times and magnitudes from the AIP mirror; an epoch
  is dropped if `variability_flag_g_reject` is True or the magnitude is not finite.
- Rule: `sb2_ecl_dr4.classify` 0.1.0 unchanged (2-harmonic Fourier model away from conjunctions,
  dip = residual >= max(0.025 mag, 4 sd), ECL_GAIA = >= 2 in-window dips (|dphase| <= 0.035) from
  >= 2 different eclipses and in-window >= 2 x out-of-window dips; ECL_GAIA_SHALLOW; FEW_EPOCHS
  below 20 usable epochs). Orbit time = 2191.5 + t_periastron. Null: conjunctions moved by 0.25.
- "Gaia-known eclipsing" = in `vari_eclipsing_binary`, or any NSS solution of the source whose type
  contains "clipsing", or `vari_classifier_result.best_class_name = 'ECL'`.
- Flagged = ECL_GAIA or ECL_GAIA_SHALLOW. "New candidate" = strict ECL_GAIA and not Gaia-known.

## Predictions (graded automatically by the job, except P5)

| # | Prediction | Threshold | Confidence |
|---|---|---|---|
| P1 | Share of Gaia-known eclipsing stars flagged | >= 0.40 | 65% |
| P2 | Null (quadrature) flags / classified stars | <= 0.02 | 80% |
| P3 | Median abs(dphase) of the in-window dips of ECL_GAIA stars | <= 0.015 | 75% |
| P4 | New candidates (ECL_GAIA, not Gaia-known) | >= 10 | 60% |
| P5 | Of the 10 deepest new candidates (all if fewer), hand-vetted against VSX, SIMBAD, Prsa 2022, IJspeert 2024, TESS Ten Thousand and Eclipses by Appointment (latest commit), at least half are listed in none | >= 50% | 50% |

Graded by hand after the run: P5, and a purity estimate = (null flags among not-Gaia-known stars)
/ (new candidates), reported as the expected false share.

## What counts as success and what does not

Success = P2 and P3 true (the flags are tied to Gaia's conjunctions, not noise) and P4 true. A
candidate is only called a new eclipsing binary after P5's vetting finds it in no catalogue, and
only with its epochs and fold published. If P2 or P3 fails, the candidates are not reported as
eclipsing. If the AIP mirror returns a different sample size or the job fails for data access,
it is re-filed unchanged (version bumped only after a code failure), and nothing here changes.
