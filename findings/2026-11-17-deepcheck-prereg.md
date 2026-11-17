# Archival and Kepler test of the best Gaia-forecast targets: pre-registration

Written 2026-11-17 (about 20:50 UTC), before any light curve of these stars was read and
before job gaia-deepcheck-v1 ran. gaia-orbit-transits 0.9.0 (`deepcheck.py`).
MV2 of Munim, Inc.; made with AI agents. CC BY 4.0.

## Question

The forecast (findings/2026-11-17-forecast-results.md) ranks Gaia DR3 orbits by how many
transits or eclipses TESS should record in 2026-2028. Do the best of them already
eclipse in the data that exist (Kepler 2009-2013, TESS 2018-2026, ZTF, ASAS-SN, Gaia's
own epoch photometry), and are Gaia's highest eclipse probabilities (p > 0.9) right?

**The wow if it works:** a nearby (68-111 pc) M dwarf with a companion at the
star/brown-dwarf boundary on a 135-195 d orbit, seen to eclipse where Gaia's astrometry
said, would be a rare benchmark: a true mass from astrometry and a radius from the
eclipse, for a cool, long-period object. A clean miss is also a result. It measures how
far Gaia's near-edge-on inclinations can be trusted, which every Gaia DR4 forecast
(2 December 2026) needs.

## Targets (fixed)

From run B of gaia-forecast-v2 (G < 14.5, |cos i| < 0.2, dark companion < 0.1 M☉):
- the 12 with the highest expected TESS transits: 2102618458287057920,
  5440672572654653696, 5859356292621344640, 1117674258493434624, 1094180924823720832,
  1905661394212548224, 1538418974318927488, 2255242560688999040, 1712614124767394816,
  1270263417048771456, 1369929267019238144, 2981815100045965440;
- the 4 with the highest Gaia eclipse probability p_ecl not already listed:
  577478114092768384 (p = 0.967, P = 19.72 d, OrbitalTargetedSearch),
  6478328150150225664 (p = 0.951, P = 597.2 d), 43574131143039104 (p = 0.511,
  P = 10.59 d, OrbitalTargetedSearch), 1509074593817942400 (p = 0.363, P = 541.3 d).

## Method (deepcheck.py 0.9.0)

archival.py 0.4.1 unchanged (Gaia Monte Carlo prior, joint period/transit-time
posterior, box search over ±3.5σ, threshold = max(6, maximum of 30 shuffled-residual
null runs), injection-recovery R, update p → p(1 − R)/(1 − pR)), with three changes:
1. residuals are kept up to 60% deep (archival.py drops everything deeper than 8%);
2. Kepler long-cadence PDCSAP light curves are added when the star was a Kepler target
   (match within 5″, or within 10″ with Kp within 1 mag of G), and a Kepler-only search
   is run as well as the combined one;
3. the 8 deepest box dips of duration D0 anywhere in the data are listed, with their
   offsets (in σ) from the predicted conjunction.
Plus: SIMBAD, VSX and the TESS EB catalogue (xmatch_prior.py), and the Kepler EB
catalogue (Kirk et al. 2016) for Kepler targets.

A "candidate" is the archival.py verdict "candidate (needs vetting)": SNR ≥ threshold
with ≥ 2 epochs in the best cell. "Excluded" means p_post < 0.05.

## What we expect, and why

Gaia's p_ecl values are probably too high. In our full DR3 search about 21 eclipsing
systems were seen where about 74 were expected (the formal calibration, job
gaia-calib-v2, is still queued). The 16 targets sum to Σp_ecl ≈ 5.1 at face value, or
about 1.5 if Gaia's probabilities are ~3.5× too high, and the data cover only part of
each posterior.

## Predictions

- **K1 (Kepler).** If Gaia DR3 2102618458287057920 has Kepler long-cadence data, the
  Kepler-only search finds no candidate at either conjunction, and its eclipse
  probability falls below 0.05 at both. (No Kepler data: K1 is void, and we say so.)
- **K2.** At most 2 of the 16 stars get the verdict "candidate" in the combined search.
- **K3 (Gaia's surest orbits).** Of 577478114092768384 (p = 0.967) and
  6478328150150225664 (p = 0.951), at least one is not seen to eclipse although the
  data cover it: p_post < 0.3 at every searched conjunction. If both eclipse where
  predicted, Gaia's inclinations are good at the high-confidence end. That would be a
  positive result, and we would report it as one.
- **K4 (what is known).** At most 3 of the 16 stars are already listed as eclipsing
  binaries (VSX, SIMBAD eclipsing types, the TESS EB catalogue or the Kepler EB
  catalogue).

## What counts as a result

- A candidate with ≥ 2 epochs at the Gaia conjunction, whose depth is within a factor of
  2 of (R2/R1)², and which is in none of the catalogues, goes to full vetting
  (vet_event.py: pixels, centroids, neighbours, SAP/PDC). Only after that is it written
  up and reported (AAVSO VSX for an eclipsing binary; for a brown-dwarf-mass companion,
  TFOP/ExoFOP, which needs a membership we do not have yet).
- A deep dip that is not at the predicted conjunction (|z| > 3) is listed as an
  unrelated eclipse, a wrong Gaia ephemeris or an artefact. It is never counted for K2.
- Every p_post is reported, so the misses feed the inclination calibration.

## Notes added after the predictions were written (no prediction changed; no light curve read)

Gaia DR3 `gaia_source` for six targets (ESA archive, 2026-11-17):

| Gaia DR3 | G | BP−RP | parallax (mas) | M_G | RUWE | note |
|---|---|---|---|---|---|---|
| 2102618458287057920 | 13.59 | 2.46 | 14.64 | 9.4 | 4.92 | Kepler field; pm 105 mas/yr |
| 5440672572654653696 | 13.09 | 2.02 | 8.86 | 7.9 | 1.81 | Teff (GSP-Phot) 4104 K |
| 5859356292621344640 | 14.32 | 2.70 | 15.31 | 10.2 | 4.36 | |
| 577478114092768384 | 10.94 | 2.25 | 42.09 | 9.1 | 2.00 | OrbitalTargetedSearch, e = 0.84, significance 12.2 |
| 6478328150150225664 | 11.98 | 2.81 | 74.46 | 11.3 | 35.5 | goodness_of_fit 16.0, significance 126 |
| 43574131143039104 | 12.18 | 3.20 | 103.50 | 12.3 | 3.73 | = LHS 1610 (below) |

All six are M dwarfs within 115 pc (three within 25 pc), so a companion of
0.06-0.1 M☉ would block a large fraction of the light.

**43574131143039104 is LHS 1610**, an M5 dwarf at 9.7 pc with a known brown dwarf, LHS 1610 b
(Winters et al. 2018, AJ 155, 125: P = 10.59 d, m sin i = 44.8 M_Jup). Fitzmaurice et al.
(2023, arXiv:2310.07827) combined the Gaia DR3 orbit with TRES and HPF radial velocities
and found i = 114.5° (+7.4/−10.0) and a mass of 49.5 M_Jup. They also found that Gaia's
eccentricity (0.52 ± 0.03) disagrees with the RV value (0.3702 ± 0.0003). Gaia alone gives
cos i = −0.049 (i ≈ 92.8°) in our Monte Carlo and p_ecl = 0.51. If the joint-fit
inclination is right, LHS 1610 b does not transit, and this is a published case in which a
significant DR3 orbit looks closer to edge-on than it is. The archival search will show
whether TESS excludes a transit at the Gaia-predicted conjunctions.

**2102618458287057920 is KIC 6436291** (MAST KIC search: 1.9″ away, Kp = 13.649,
KIC Teff 3515 K). Kepler observed it in long cadence in all 17 quarters (Q1-Q17,
2009-05-13 to 2013-05-11; Q6-Q9 under guest-observer programme GO20031), so K1 will be
graded. The Villanova Kepler Eclipsing Binary Catalog (last updated 2019-08-08) has no
entry for it. A web search found no paper naming it. Over the 1,459 days of Kepler data
there are about nine conjunctions of each kind, so a 10-20% eclipse at either
conjunction would very probably have been catalogued. That is why we expect K1 to pass.

6478328150150225664 has RUWE 35 and goodness_of_fit 16, so its formal errors (and
therefore p_ecl = 0.95) are the least trustworthy of the list. This is exactly the case
K3 tests.
