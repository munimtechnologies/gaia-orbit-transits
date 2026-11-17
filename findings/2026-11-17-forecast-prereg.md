# Forecast of Gaia-predicted transits for TESS Years 9-10 and the ground: pre-registration

Written 2026-11-17 (about 10:40 UTC), before `forecast.py` had run on any star.
gaia-orbit-transits 0.4.0. MV2 of Munim, Inc.; made with AI agents. CC BY 4.0.

## What the forecast is

For each Gaia DR3 astrometric orbit with a substellar-mass (dark) companion that is seen
nearly edge-on, `forecast.py` publishes **before the observations exist**:

1. every TESS sector from 108 to 134 (September 2026 to late 2028) in which the star
   lands on a CCD (tess-point 0.9.5 pointing table), with the Monte Carlo probability that
   the transit conjunction falls inside the sector and the expected number of transits
   TESS will record (geometric transit probability × timing probability, joint over the
   same draws);
2. every transit window between 2026-12-01 and 2027-12-01 (centre, robust 1σ, 95%
   range), for ground-based observers.

The transit conjunction is the RV-labelled one (AstroSpectroSB1 orbits whose astrometric
and spectroscopic ω agree), otherwise both conjunctions at weight 0.5 each.

Each forecast is a falsifiable statement: when TESS observes a listed sector, the data
either show the predicted transit or exclude it over the stated fraction of the
posterior.

Sector dates: Year 9 from tess.mit.edu (provisional); Year 10 boundaries are midpoints
between tess-point's sector mid-times and are flagged `dates_approx`. Gaps at perigee
(~7% of each sector) are not removed.

## Runs (job gaia-forecast-v1)

- A: the 25-star watch list (`--gmax 17 --cosi-max 0.3`), output prefix `watchlist_`.
- B: all DR3 orbits with G < 14.5, |cos i| < 0.2 and dark-companion mass < 0.1 M☉,
  prefix `dr3_g14.5_c0.2_`.

## Predictions

- **F1.** The best target, Gaia DR3 393581461455623296 (RA 2.39°, Dec +48.75°), is on
  silicon in none of the sectors 108-121. This agrees with the hand check in run 4. No
  prediction is made for Year 10.
- **F2.** Between 5 and 15 of the 25 watch-list stars are on silicon in at least one of
  the sectors 108-121.
- **F3.** The expected number of TESS-observed transits, summed over the watch list for
  the sectors 108-134, lies between 0.05 and 0.5. No single star exceeds 0.2.
- **F4.** Run B keeps between 5 and 30 stars.
- **F5.** More than 70% of the watch-list transit windows between 2026-12-01 and
  2027-12-01 are constrained (σ < P/4).

## What would count as a result

- A star with expected TESS transits ≥ 0.1 in a single sector is put forward for
  monitoring. Once that sector's light curve is public (about 1-2 months after it ends),
  run_search/archival are run on it.
- Ground windows for stars with G < 13 and 1σ < 3 d go into an observing request (AAVSO
  or Exoplanet Watch). Such a request is only sent after review (see the project's
  outreach rule).
- A transit seen inside a forecast window would be the first transit of a companion
  found because Gaia astrometry said when to look. A miss over a high-probability
  window lowers that star's transit probability through the same p(1 − R)/(1 − pR) update
  used in archival.py.
