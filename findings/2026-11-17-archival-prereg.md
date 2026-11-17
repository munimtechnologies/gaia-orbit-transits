# Pre-registration: archival photometry test of the Gaia-predicted transits (0.4.0)

2026-11-17. By MV2 of Munim, Inc. Made with AI agents working in his name.
Text CC BY 4.0, code Apache-2.0. Written and published **before** any archival light curve
was downloaded or looked at by this project. The job is `gaia-archival-v1`. Its results
will be graded against this file in `findings/2026-11-1x-archival-results.md`.

## Why this test

The best target on the watch list is Gaia DR3 393581461455623296:
- G = 12.7, K dwarf (Teff ≈ 4500 K from Gaia GSP-Phot);
- P = 73.34 ± 0.12 d, circular orbit;
- companion about 0.074 M☉ if dark.

Its RV orbit identifies which conjunction is the transit (findings/2026-11-17-sb1-transit-convention.md).
TESS has not tested it: sectors 17, 57 and 84 all ended 1.8 to 3.2σ before a predicted
transit.

**TESS will not test it soon either.** We compared the official TESS Year 9 pointings
(sectors 108–121, 7 Sep 2026 to 19 Sep 2027; tess.mit.edu, "provisional") with the star's
position (RA 2.39°, Dec +48.76°). The closest camera centre in Year 9 is sector 121,
camera 1, at (322.74°, +38.01°). That is about 30° away, well outside a 24° × 24° camera
field, whose corners reach about 17° from its centre. So the transit windows of
2027-01-28 and 2027-04-12 (± 6.6 d) can only be watched from the ground.

The star has years of public ground-based and Gaia photometry, and these cover dozens of
predicted transit epochs:
- Gaia DR3 epoch photometry: 57 G-band field-of-view transits, 2014–2017, the same
  epochs as the orbit itself. Gaia flags the star as VARIABLE, best class SOLAR_LIKE.
  The G scatter is 8.7 mmag and the faintest epoch is +21 mmag.
- ZTF: about 1,300 r-band points from 2018 onwards (IRSA light-curve service), plus g.
- ASAS-SN Sky Patrol v2: V and g.
- TESS: three sectors.

No one has searched these data at the times the Gaia orbit predicts. 0.4.0 adds
`archival.py`, which does so for all 25 watch-list stars.

## Method (fixed before seeing data)

- **Posterior.** Joint posterior of the period and of the transit time at the median
  epoch of the data. It comes from 2,000 Monte Carlo draws of the Gaia orbit, using the
  full correlation matrix.
- **Hypotheses.** The RV-identified conjunction only, when it is labelled and consistent
  with the astrometric one. Otherwise both conjunctions, as separate hypotheses.
- **Search.** A box search over a grid covering ±3.5σ in P and ±3.5 conditional σ in T.
  Durations are D0 (the predicted central duration) and 0.6 D0. Residuals come from a
  running median that skips ±D around each point, and are weighted by each light curve's
  robust scatter.
- **Threshold.** The larger of 6 and the maximum over 30 null runs. In each null run the
  residuals are cyclically shifted within each light curve.
  FAP = (1 + #null ≥ obs) / 31.
- **Injection–recovery.** 300 draws from the Gaia posterior, with impact parameter
  uniform in 0–0.9. Depths: 0.5×, 1× and 2× the predicted depth, plus 0.5% and 1%. The
  predicted depth is (R2/R1)², with R2 = 0.10 R☉ for a brown dwarf and R1 from a
  main-sequence relation.
- **Posterior transit probability.** p_post = p (1 − R) / (1 − p R), where p is the
  pipeline's geometric probability for that conjunction.
- **What counts as a candidate.** SNR ≥ threshold with in-transit points from ≥ 2 epochs.
  A single-epoch excess is reported as a "single-event candidate". Every candidate then
  needs vetting before any claim:
  - consistency between surveys;
  - shape and duration against the stellar density;
  - no ZTF saturation or exposure-time artefact;
  - neighbouring stars;
  - VSX, SIMBAD and the TOI/CTOI lists.

## Predictions

For Gaia DR3 393581461455623296:
1. **Coverage:** ≥ 80% of the Gaia ephemeris posterior has at least one archival point in
   transit (`cov_any` ≥ 0.8).
2. **Sensitivity:** recovery at the predicted depth (about 1.5–2.5%) is between 0.2 and
   0.8, with a best guess of 0.5. ZTF r is close to saturation at this brightness, so its
   scatter is probably 1–1.5%.
3. **Result:** no candidate. The prior transit probability is about 7%, so a detection has
   a chance of only about 0.07 × R ≈ 3%.
4. If prediction 3 holds, the transit probability falls from about 7% to between 3% and
   6%.

For the watch list as a whole (about 27 hypotheses for 25 stars):

5. **False alarms:** 0 to 2 hypotheses pass the threshold. The expected number of
   false alarms is about 27/31 ≈ 0.9, by construction of the threshold. Any that pass are
   expected to fail vetting: one survey only, or a saturation or edge artefact.
6. **Coverage by period:** for stars with P > 300 d, the median `cov_any` is below 0.5,
   because the data hold few cycles. For P < 200 d it is above 0.8.
7. **Data:** at least 20 of the 25 stars have at least one archival light curve. ZTF only
   covers Dec > −31°, so the southern stars depend on ASAS-SN, Gaia and TESS.

## What would make this a "wow"

A transit found at the Gaia-predicted phase, in two or more surveys, of a companion near
the hydrogen-burning limit on a 73-day orbit. That would be the first companion with both
an astrometric orbit and an observed transit found this way, and a benchmark with true mass
and radius. An honest null result still narrows the transit odds and the timing for the
2027 ground campaign. It also sets up the same test on Gaia DR4 (2 December 2026), which
will have many more orbits.
