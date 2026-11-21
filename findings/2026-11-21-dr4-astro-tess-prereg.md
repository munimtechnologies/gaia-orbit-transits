# Pre-registration: Gaia DR4 astrometric orbits x TESS, release-day step (i)

MV2 of Munim, Inc. Made with AI agents working in his name; not yet checked by a human expert.
Text CC BY 4.0, code Apache-2.0. Written 2026-11-21 (~21:30 UTC), before Gaia DR4 exists
(release 2 December 2026, archive 12:00 CET). Nothing below may change after a DR4 row is read,
except through a dated amendment written before the number it affects is looked at.

## The question and the wow

Gaia DR4 (66 months of data) will publish far more astrometric orbits than DR3, reaching down to
giant-planet and brown-dwarf companions. A companion whose orbit Gaia measures from the star's
wobble *and* that transits its star would have a true mass (astrometry) and a radius (transit):
a benchmark. To our knowledge no companion first found by Gaia astrometry has yet been seen to
transit. **Wow, if it works:** a transiting brown dwarf or giant planet on an orbit of weeks to
years, first found by Gaia's astrometry and seen in TESS at the time Gaia's orbit predicts.

## Prior art (checked 2026-11-21)

- Our DR3 search (`findings/2026-11-17-dr3-full-search-results.md`): 24,157 near-edge-on DR3
  orbits, 277 targets with TESS data; no substellar transit at a predicted conjunction (P4
  pass); calibration P2 failed narrowly, with the BF-ceiling caveat of 0.7.0.
- Chopard-Vilhem (Zenodo, 2026-10-13): the same idea on 1,726 DR3 orbits within 1 degree of
  edge-on; seven new eclipsing binaries at 26-242 d. Stellar companions only.
- Holl et al. (arXiv:2206.05439) and Sozzetti et al. (arXiv:2302.00420) fit and validate DR3
  astrometric planet and brown-dwarf candidates; Stevenson et al. 2023 (MNRAS; arXiv:2310.02695)
  list DR3 brown dwarfs. None searches TESS at Gaia-predicted conjunctions. DR4 is unreleased, so
  no DR4 search exists.

## What we found today: the DR3 code would fail on DR4 (and partly silently)

From ESA's draft DR4 data model (read by our job gaia-dr4dm-v2, 19 Nov; sections 10.3 and 10.8):
1. `nss_two_body_orbit` renames `nss_solution_type` -> `solution_type`, `corr_vec` ->
   `correlations`, `goodness_of_fit` -> `gof`, and drops `c_thiele_innes` / `h_thiele_innes`.
   `run_search.py` 0.4.1 selects all of these, so its first DR4 query would fail.
2. **The silent trap.** DR4 fits astrometric orbits in Campbell elements. For `Orbital` the
   correlation vector is ordered (ra, dec, parallax, pmra, pmdec, semi_major_axis,
   arg_periastron, pos_ascending_node, inclination, eccentricity, period, t_periastron): **12
   parameters, the same count as DR3's Thiele-Innes order** (..., A, B, F, G, e, P, Tp). Read
   with DR3's names it would not raise an error; it would quietly give every Monte Carlo draw the
   wrong correlations. For `AstroSpectroSB1` DR4 has 14 parameters (semi_amplitude_primary
   instead of C and H) against DR3's 15.
3. DR4's reference epoch is J2017.5 (BTJD 936.875), not DR3's J2016.0. `run_search.py` 0.4.1
   already reads `gaia_source.ref_epoch` per row, so the conjunction times were safe.
4. `nss_masses` gains `exoplanet_candidate_hrd_proba` (probability that the companion is under
   20 Jupiter masses, from the HR-diagram position) and `lowmass_candidate_hrd_proba` (under 80).

The fix, `dr4_rows.py` 0.1.0 and `run_search_dr4.py` 0.1.0 (this commit), wraps the pinned
`run_search.py` 0.4.1 (main at f868df8e101aee2c360d9a7b176c3d2356b462b5) unchanged. It swaps
the query for one with DR4 names (cut on DR4's own `inclination`), keeps Gaia's own A, B, F, G
central values, maps DR4's covariance of (a0, omega, Omega, i [, K]) to (A, B, F, G [, C, H])
with the exact Jacobian, and rebuilds C = a1 sin i sin(omega), H = a1 sin i cos(omega) for
AstroSpectroSB1, so the DR3 code's RV-based transit label works unchanged.

## Gates (fixed now)

- **R1, before DR4 (job gaia-dr4-astro-adapter-v1):** unit tests, an offline self-test (S0-S5),
  and a real-data round trip: up to 400 DR3 `Orbital` orbits are turned into DR4-shaped rows
  (Campbell elements, covariance by the inverse Jacobian) and back. Every row must return DR3's
  own correlations (max diff < 1e-6), errors (relative < 1e-6) and conjunction times (< 1e-6 d).
  PASS needs at least 50 rows tested and all passing. FAIL -> a dated 0.1.1 before 2 Dec. If the
  DR3 rows are unavailable (SKIPPED), the synthetic checks S1-S4 stand alone and we say so.
- **G0, on release day, inside the run, before any TESS download:** (a) among DR4 rows that
  carry catalogue A, B, F, G, at least 95% must equal the values computed from DR4's Campbell
  elements within 1e-3 of a0 (STANDARD); (b) at least 50% of rows must have a correlation vector
  of the expected length. Otherwise exit 4 and `dr4_adapter_gate.json`: a dated amendment on the
  convention found, then -v2. No other change is allowed at that point. If DR4 has no catalogue
  A, B, F, G at all, (a) is UNCHECKED and the run goes on; we report that.

## Fixed settings (identical to the registered DR3 search unless stated)

G < 14.5; |cos i| < 0.2 (now from DR4's `inclination`); solution types `Orbital` and
`AstroSpectroSB1` only (`OrbitalPoorlyConstrained`, `OrbitalAlternative` and VIMO excluded);
600 correlated draws per orbit; eclipse probability >= 0.002; up to 400 targets, substellar class
first (dark-companion mass < 0.075 Msun from the code's own mass estimate), then by eclipse
probability; 200-minute budget; TESS dips SNR >= 7, 2-24 h; seed 20261117; predictions from
BTJD 4375.5 (1 Dec 2026). Match BF > 10; strong match also SNR > 10, away from segment edges,
and no same-time event in two or more other targets. If substellar-class targets are left
unreached by the budget, they are run in follow-up jobs of 150 (`--source-ids`, rank order, same
settings) before anything is graded.

## Hypotheses and predictions (graded on DR4)

- **H1 method check:** among targets also in DR4's eclipsing-binary table with predicted-window
  coverage > 0.5, at least half show a match at BF > 3 -> TIMING_OK; fewer -> TIMING_BAD (no other
  result is trusted); fewer than 5 such targets -> UNINFORMATIVE. Prediction: UNINFORMATIVE 50%,
  TIMING_OK 35%, TIMING_BAD 15%.
- **H2 calibration:** strong-match count S against the code's `expected_eclipses_covered` E:
  E/3 <= S <= 3E -> CALIBRATED; S < E/3 -> OVERPREDICTED; S > 3E -> UNDERPREDICTED. Reported with
  the BF-ceiling caveat (short periods cannot reach BF > 10). Prediction: CALIBRATED 45%,
  OVERPREDICTED 50%, UNDERPREDICTED 5%.
- **H3 (primary, the wow):** a substellar-class target with a strong match whose depth is at most
  5% (a companion of at most about 1 Jupiter radius blocks roughly 1-5% of a Sun-like or K star;
  deeper dips point to a luminous near-twin binary, as in the DR3 registration) ->
  SUBSTELLAR_TRANSIT_CANDIDATE. Prediction: at least one, 20%; none, 80%. A candidate is not a
  planet or brown dwarf. It then gets, in order: its plots opened; prior art (ExoFOP TOI/CTOI,
  VSX, SIMBAD, the TESS EB catalogues, arXiv); its DR4 `nss_masses` row (m2 range,
  `exoplanet_candidate_hrd_proba`, `lowmass_candidate_hrd_proba`, flags) as description only; a
  pixel test; a second predicted conjunction if TESS has one. Only then a CTOI request (needs an
  ExoFOP login MV2 does not have).
- **Descriptive:** the G0 summary; DR4 near-edge-on counts by solution type; substellar-class
  count; for every TESS target, its `nss_masses` columns (one small TAP query by source_id).

## What would make this wrong

A DR4 convention we did not foresee that G0 does not catch (e.g. a changed time scale for
`t_periastron`); TESS coverage too sparse at long periods; DR4 substellar orbits that are mostly
spurious, as DR3's short-period brown-dwarf SB1 orbits were
(`findings/2026-11-19-sb1-robust-amendment-2-results.md`). Every one of these is reported, not
hidden.
