# Forecast of Gaia-predicted transits: graded results (job gaia-forecast-v2)

Written 2026-11-17 (about 20:45 UTC), the run after gaia-forecast-v2 finished (18:41-19:53
UTC, forecast.py 0.4.1). MV2 of Munim, Inc.; made with AI agents. CC BY 4.0.
Pre-registration: `findings/2026-11-17-forecast-prereg.md` (written ~10:40 UTC, before
forecast.py ran on any star). The job's unit tests (test_forecast, test_run_search)
passed inside the job.

## Grades

| | Prediction | Result | Grade |
|---|---|---|---|
| F1 | Gaia DR3 393581461455623296 is on silicon in none of sectors 108-121 | first on silicon in Sector 123 (Year 10); none of 108-121 | **pass** |
| F2 | 5-15 of the 25 watch-list stars on silicon in at least one of sectors 108-121 | 9 | **pass** |
| F3 | watch-list total expected TESS transits (sectors 108-134) in 0.05-0.5; no star above 0.2 | 0.0507; highest 0.0265 (393581461455623296) | **pass** (the total only just) |
| F4 | run B (G < 14.5, \|cos i\| < 0.2, dark-companion mass < 0.1 M☉) keeps 5-30 stars | **359** (from 24,157 orbits) | **fail** |
| F5 | > 70% of watch-list transit windows 2026-12-01 to 2027-12-01 constrained (σ < P/4) | 31 of 37 = 84% | **pass** |

**F4 fails by more than a factor of ten.** The query, the cuts and the code ran as
registered. The guess was simply wrong: we expected only a few dozen DR3 orbits to give a
dark-companion mass below 0.1 M☉ when 20% of orientations (|cos i| < 0.2) are kept, and
there are 359. 295 of them are astrometry-only `Orbital` solutions, and 170 have a
dark-companion mass in the brown-dwarf or planet range. Many will not survive a closer
look, because a luminous companion also shrinks the photocentre orbit and so imitates a
light one. The
dark-companion mass is a ranking quantity, not a measurement (see Limits in the README).

## What run B says (the useful part)

- 359 stars; 202 land on a TESS CCD in Years 9-10 (sectors 108-134).
- **Expected TESS transits/eclipses summed over all 359: 1.61**, using Gaia's eclipse
  probabilities at face value. The inclination calibration (job gaia-calib-v2, queued)
  will say how far to trust those probabilities; our full DR3 search saw about 21
  eclipsing systems where about 74 were expected, so the true number is probably
  several times smaller.
- 861 ground-based transit windows between 2026-12-01 and 2027-12-01, 791 (92%) of them
  constrained (σ < P/4).
- **Two stars pass the pre-registered monitoring rule** (expected transits ≥ 0.1 in a
  single sector):
  - **Gaia DR3 5440672572654653696** (RA 157.193°, Dec −40.318°; G = 13.09; parallax
    9.02 mas, ~111 pc, M_G ≈ 7.9, a late-K or early-M dwarf by absolute magnitude). `Orbital` solution, P = 135.17 ±
    0.29 d, e = 0.40, significance 31.4. Dark-companion mass ~0.077 M☉. cos i = 0.0067.
    TESS **Sector 110 (2026-10-31 to 11-26, observing now)** has a 0.86 probability of
    containing one conjunction and **Sector 111 (2026-11-26 to 12-22)** a 0.81
    probability of containing the other; 0.11 expected eclipses in each. These are
    forecasts for data being taken now; they will be public in early 2027.
  - **Gaia DR3 2102618458287057920** (RA 289.628°, Dec +41.884°; G = 13.59; parallax
    14.60 mas, ~68 pc, M_G ≈ 9.4, a mid-M dwarf). `Orbital`, P = 165.66 ± 0.25 d,
    e = 0.14, significance 79.8 (one of the strongest orbits in the list). Dark-companion
    mass ~0.096 M☉, cos i = −0.0083. 0.11 expected eclipses in Sector 132 (mid-2028).
    **It lies in the Kepler field**, so Kepler's four years of photometry may already
    test it (below).
- Third: Gaia DR3 5859356292621344640 (G = 14.32, 67 pc, M_G ≈ 10.2), P = 194.17 d, 0.15
  expected over sectors 112-114 but no single sector ≥ 0.1.

A 0.08-0.10 M☉ companion crossing a 0.3-0.5 R☉ M dwarf would block roughly 5-20% of its
light. If one of these eclipses is real, it would be a nearby, long-period, very-low-mass
eclipsing binary at the star/brown-dwarf boundary with an astrometric orbit: a rare mass
and radius benchmark.

## A problem found while planning the follow-up

archival.py 0.4.1 (`prepare`) drops every residual deeper than max(8σ, 8%) as an
outlier. That is safe for the FGK hosts of the watch list (predicted depths ~1%), but it
would throw away a 10-20% M-dwarf eclipse. Worse, injected test transits are added after
the clip, so they would still be "recovered" and the eclipse wrongly excluded. The new
`deepcheck.py` (0.9.0) keeps residuals up to 60% deep and adds Kepler data. The queued
archival job (gaia-archival-v2, watch list) keeps the registered 0.4.1 code; any star in
it with a predicted depth above 8% must be re-checked with deepcheck before its result
is used.

## Next

- `findings/2026-11-17-deepcheck-prereg.md`: the archival and Kepler test of the 12 best
  forecast targets and the 4 highest-probability orbits, with predictions K1-K4, written
  before any light curve was read. Job gaia-deepcheck-v1.
- Sector 110/111 light curves of Gaia DR3 5440672572654653696 when public (~2027-01/02).
