# Pre-registration: are Gaia DR3 astrometric inclinations good enough to predict eclipses?

Written 2026-11-17, 17:10–18:30 UTC, before `calib_eclipse_rate.py` (0.7.0) has been run on
any data. MV2 of Munim, Inc.; made with AI agents. CC BY 4.0.

## The question

Gaia DR3 gives about 170,000 astrometric orbits. Their inclinations and errors are used to
pick eclipsing and transiting candidates (Chopard-Vilhem 2026; this project). With Gaia DR4
(2 December 2026) the same will be done on ~6 million orbits. **How far can one trust a
DR3 inclination near 90°?** Makarov (2025, ApJL, arXiv:2502.20553) showed by simulation
that, for a nearly edge-on high-SNR DR3 orbit, the inclination error is strongly
underestimated (3.65° scatter where Gaia quotes 1.6°). We know of no test of DR3
inclinations against real eclipses. Eclipses are the cleanest possible check: an orbit
seen within (R1 + R2)/a of edge-on *must* eclipse at its conjunctions, and TESS has looked
at most bright stars at those times.

The "wow", if it works: the first external, empirical calibration of Gaia astrometric
inclination errors, from TESS eclipses. It would give the factor by which the DR3 errors
must be inflated before DR4 eclipse and transit forecasts are trusted.

## Why a new analysis is needed: a correction to our own v4 grading

The v4 search (graded in `2026-11-17-dr3-full-search-results.md`) counted a target as
eclipsing only if a dip had a window-match Bayes factor BF > 10. That BF cannot exceed
about P / (2.5 σ_t), where σ_t is the timing error of the predicted conjunction. **A
10-day orbit with σ_t ≈ 1 d can never reach BF > 10, however deep its eclipses.** While
reading the v4 output before writing this note, we saw that:

- **HD 75767 (TIC 459056725, Gaia DR3 596878550087942528, G = 6.4, P = 10.2488 d)** shows
  7.7%-deep eclipses at every covered conjunction in TESS sectors 34, 44–46, 61, 72 and 88
  (SNR up to 5,400), 1.1 d
  (≈ 1σ) before Gaia's predicted t2, and 0.5% secondary eclipses at t1. Its best BF is
  2.9, so v4 did not count it. Its eclipses are known (STEREO: Wraight et al. 2012, MNRAS
  427, 2298; Griffin & Fuhrmann 2013), which makes it a positive control.
- **TIC 272540685 (Gaia DR3 2011730318875048192, P = 82.27 d)** shows 14% eclipses at
  Gaia's RV-identified transit conjunction (BTJD 2894.29 and 3634.22, nine orbits apart,
  i.e. P ≈ 82.215 d) and 4–6% eclipses at the other conjunction, each 1.6–2.6σ from
  prediction. Best BF 9.4: not counted.

So part of v4's "74 expected, ~21 seen" was our detection rule, not Gaia. The P2 grade
stays as it was graded (a fail; pre-registered rules are not re-graded), but the
interpretation "DR3 orbits predict about three times more eclipses than TESS shows" is
withdrawn until this test reports.

**Disclosure.** Before writing this note we read, by hand, the v4 rows of the ~20 targets
with Monte Carlo eclipse probability ≥ 0.9 (tess_targets.csv and their events). Besides
the two above, the clearest apparent non-eclipses were TIC 79020913 (Gaia DR3
6478328150150225664, a 13-pc M dwarf, P = 597 d, cos i = −0.0002 ± 0.0021, expected depth
~16%), TIC 270561176 (P = 19.7 d) and TIC 164720249 (P = 53.0 d). The predictions below
were written knowing this. Everything else (the other ~250 targets, all fits, bins,
controls and timing statistics) has not been looked at.

## Data and rule (fixed now; `calib_eclipse_rate.py` 0.7.0)

Input: the published v4 outputs in `data/dr3-full-search-v4/` (277 targets with TESS, 2,505
dips, 1,079 covered windows) and the v4 prior table `gaia_edge_on_priors.csv` (published
with this release).

**Main sample.** v4 targets with TESS light curves, excluding Gaia-EB targets (inner
binaries confuse the test), OrbitalAlternative* solutions, targets whose conjunctions are
covered with probability < 0.05, targets whose expected eclipse SNR is < 15 (expected
depth (R2/R1)², noise = median 2-h box noise of the star's dips, or a G-magnitude rule if
it has none), and targets that cannot be timed (below).

**An eclipse is seen** if a dip has SNR ≥ 10, depth ≥ 500 ppm, is not at a segment edge,
does not occur in any other target at the same time, is not one of the two artefacts
vetted by eye in v4 (TIC 219744709 at BTJD 2707.40, TIC 152964265 at 2165.37), and:

- **window rule:** lies within 3σ + half its duration of a covered predicted conjunction
  (σ from the Monte Carlo of that window), where that half-width is ≤ P/4;
- **repeat rule,** only for targets where the half-width exceeds P/4 ("untimeable"): two
  such dips are n·P apart within 0.2 d + 3nσ_P (tolerance < P/10; P ≤ 25 d; P not within
  0.5 d of 13.7 or 27.4 d). Untimeable targets where the repeat rule cannot work are
  excluded.

**False-alarm control.** The same rule at the two phases half-way between the
conjunctions, for timeable targets where those windows do not overlap the conjunction
windows. The control hit rate enters every model as a constant false-alarm probability.

**Model.** For each target, cos i ~ N(cos i_Gaia, (k σ)²), with σ the Monte Carlo spread
from Gaia's full correlation matrix. Each conjunction eclipses if |cos i| < lim_j =
q g_j / (1 − e²), with q = (R1 + R2)/a from the rough main-sequence masses and radii of v4
and g_j = 1 + e cos f_j recovered from the v4 durations. Both conjunctions share one
inclination, and each is weighted by its TESS coverage. M0 means k = 1, f = 0, s = 1
(Gaia as published). Fits: k (σ inflation), f (a fraction of orbits wrong and randomly
oriented) and s (all radii scaled), each alone, and k with f together. 95% intervals are
from ΔlnL = 1.92.

## Predictions

| # | prediction | pass if |
|---|---|---|
| C1 | Gaia over-predicts eclipses, but by much less than v4 suggested | 0.45 ≤ N_seen / N_expected(M0) ≤ 0.85 |
| C2 | Gaia's published errors are too small for edge-on orbits | P(N ≤ N_seen \| M0) < 0.01 |
| C3 | the σ(cos i) inflation is moderate, like Makarov's simulated factor of ~2.3 | 1.5 ≤ k_ML ≤ 5 and k = 1 outside the 95% interval |
| C4 | Gaia's conjunction *times* are well calibrated even if inclinations are not | 0.6 ≤ rms(z) ≤ 1.4, z = offset / σ_t of each window-rule eclipse |
| C5 | solutions confirmed by Gaia's own RVs (AstroSpectroSB1) are more reliable | ratio(AstroSpectroSB1) ≥ 1.3 × ratio(Orbital + OrbitalTargetedSearch*) |
| C6 | an error-inflation model explains the shortfall better than wrong radii | lnL(k) − lnL(s) ≥ 2 |
| C7 | the old BF > 10 rule missed many real eclipses | N_seen ≥ 1.3 × N(old strong-match rule) in the same sample |

Our expectation in one line: Gaia DR3 inclinations of near-edge-on orbits are right in
the mean but their errors are 2–3× too small. If so, any eclipse or transit probability
computed from DR3 (and probably DR4) orbits must be computed with inflated errors.

## What would change our mind

- C1 > 0.85 with k = 1 inside its interval: DR3 inclinations are fine; v4's shortfall was
  entirely our detection rule.
- f ≫ 0 with k ≈ 1 (the k+f fit): the problem is a minority of wrong orbits, not
  generally underestimated errors. The "predicted but not seen" list then becomes a list
  of suspect DR3 solutions to check with RVs.
- A control hit rate above 0.1: the dip catalogue is too noisy for this test, and the
  result is reported as inconclusive.

## Known limits, stated in advance

- Masses and radii are rough main-sequence values; luminous companions make the true m2
  (and R2) larger, which raises the true eclipse probability (so M0 is, if anything,
  conservative).
- The v4 dip catalogue keeps at most ~20 dips per star, preferring dips inside windows,
  so the control under-counts false alarms for stars with many dips.
- Coverage is the probability that a conjunction lands on data, not that the dip search
  would find an eclipse there. The SNR cut keeps this small but not zero.
- The test uses the v4 targets: 287 of 400 ranked by eclipse probability, which is not a
  random sample of DR3 orbits.

Job: `gaia-calib-v1` (`python calib_eclipse_rate.py --data-dir /data --out-dir /out`).
