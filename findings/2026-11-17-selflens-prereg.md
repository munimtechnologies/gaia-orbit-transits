# Pre-registration: white-dwarf self-lensing pulses at Gaia-predicted conjunctions

By MV2 of Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Written 2026-11-17 (run 13, gaia-orbit-transits 0.8.0), **before any light curve or
Gaia row of this sample was read**. Code: `selflens.py`. Job: `gaia-selflens-v1`.

## The question
Can a Gaia DR3 astrometric orbit tell us when a white-dwarf companion will pass in front
of its star? If it can, TESS should show a lensing pulse at that time: a brightening of
about 2 (R_E/R1)², a few thousand ppm, lasting hours to a day.

**The wow if it works:** the first self-lensing white dwarf found because a Gaia orbit
said when to look. Its mass could then be measured twice, once by Einstein (from the
pulse amplitude) and once by Newton (from the astrometric orbit), the test that
KOI-3278 made famous (Kruse & Agol 2014; Yahalomi et al. 2019).

## Why we think it is new (searched 2026-11-17)
- Yamaguchi, El-Badry et al. 2024 (PASP; arXiv:2410.13939) searched TESS blindly for
  self-lensing binaries and used Gaia DR3 orbits only to vet candidates. They found
  none, and expected O(1) in TESS.
- Sorabella et al. 2024 (ApJL; arXiv:2401.01477) reported the first TESS self-lensing
  pulses, of the Kepler-known KIC 12254688.
- Shahaf et al. 2024 (MNRAS 529, 3729; arXiv:2309.15143; updated table Zenodo
  10.5281/zenodo.14799795) found about 3,200 Gaia DR3 astrometric binaries whose dark
  companion is probably a white dwarf (3,145 after the 2025 correction). Hallakoun et
  al. 2024 discuss their masses. We found no work that turns these orbits into
  predicted pulse times and checks TESS at those times.
- This project's own DR3 search (`findings/2026-11-17-dr3-full-search-results.md`) looked
  only for dips, not brightenings.

## Sample and method
1. **Sample.** Every source_id in the Shahaf et al. updated Table A1, with a DR3 orbit that
   has Thiele-Innes constants, G < 15 and |cos i| < 0.2. If the table has a red
   colour-excess (likely triple) flag, all rows are still used, and the flag columns
   are reported in `shahaf_info.json`. Restricting the sample would be an amendment.
2. **Priors.** The same Monte Carlo as the eclipse search (600 correlated draws, seed
   20261117), with the companion radius set to a white-dwarf radius (Nauenberg 1972). The
   "eclipse" probability is then the probability that the white dwarf crosses the
   star's disc, and the durations are those of the pulse. The rough main-sequence mass
   and radius of the star and the dark-companion mass come from `run_search.py`.
3. **Which conjunction.** The white dwarf is in front at the RV transit conjunction of
   AstroSpectroSB1 solutions (`transit_conj`, the convention verified in 0.3.0). For
   astrometric-only solutions both conjunctions are searched.
4. **Prediction per target.** a from Kepler's law; R_E² = 4 G M_wd a / c²;
   A = 2 (R_E/R1)² − (R_wd/R1)². The orbital separation at conjunction is approximated
   by a, which is within ±e·a for eccentric orbits.
5. **TESS.** At most 250 targets, highest pulse probability first. Light curves are
   SPOC, then TESS-SPOC, then QLP. The flux is inverted (2 − f) and searched with
   dipsearch (on GitHub main at run time: 0.4.3, with its floor pad and coherence cut).
   Strong original dips (eclipses) are clipped instead of upward outliers.

## The pulse rule (fixed now)
A TESS event is a **pulse candidate** if all of the following hold:
- SNR ≥ 8;
- brightening amplitude within [A/3, 3A];
- duration within [D/3, 3D], with D the predicted duration and at least 2 h;
- not at a segment edge, and not simultaneous with an event in another target;
- inside 3σ + D/2 of a covered predicted window of a lensing conjunction, where that
  half-width is at most P/4.

**Control:** the same rule at windows shifted by ±P/2.

A target counts as **detectable** if A / (median box noise) ≥ 10. **Expected pulses** are
Σ p_cross × coverage, summed over the lensing conjunctions of the detectable targets.

## Predictions
| # | prediction |
|---|---|
| L1 | the expected number of detectable pulses in the TESS data is below 2 (we expect a few tenths) |
| L2 | no target passes the pulse rule: an honest null, which gives an upper limit |
| L3 | at most one control hit |
| L4 | the median predicted pulse amplitude is 1,000–6,000 ppm |

If any target passes the rule, it is a candidate only. It must then pass the checks of
`vet_event.py` (product, background, centroid, neighbours and repeat epochs), plus a
check that the pulse is not a flare (a flare rises fast and decays slowly; a lensing
pulse is symmetric). Only then will it be called a self-lensing candidate, and only
after a SIMBAD/VSX check will it be reported anywhere.

## Limits stated in advance
- The masses and radii are rough (main-sequence relation from absolute G). A is
  uncertain by about ±40%, so the amplitude window is a factor of 3 either way.
- Gaia's DR3 inclination errors may be underestimated (Makarov 2025; our pre-registered
  calibration `calib_eclipse_rate.py` tests this). If so, the pulse probabilities here
  are too optimistic for orbits listed as nearly edge-on, and the true expected number
  is lower.
- The dipsearch artefact filters were designed for dips. In inverted flux, short
  data-gap ramps and scattered light can appear as "brightenings". The control phases
  and plots are there to catch them.
- TESS covers most stars for about 27 days per sector, so most orbits (P ≈ 100–1,000 d)
  have no covered conjunction at all.
