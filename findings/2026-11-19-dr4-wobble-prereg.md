# Pre-registration: do Gaia DR3's near-edge-on orbits that do not eclipse still wobble in DR4 epoch astrometry?

2026-11-19. MV2 of Munim, Inc.; made with AI agents working in his name, not yet checked by a
human expert. Text CC BY 4.0. Written **before Gaia DR4 (2 December 2026)**. The code
(`dr4_wobble.py`) is owed before release day and must implement exactly these rules.

## The question
Lead 1 (`findings/2026-11-18-calib-window-results.md`) found that of 162 Gaia DR3
astrometric orbits with |cos i| ≤ 0.2 and G ≤ 14.5 that TESS covered, only 58 eclipse inside
windows three times the nominal width, where 80.7 were expected (p = 2 × 10⁻⁵). Two
explanations fit equally well:
- **(K) the orbits are real, but DR3 understates σ(cos i)** by k ≈ 2.1, so some
  "edge-on" orbits are not edge-on;
- **(F) about a third of these orbits are wrong** (f = 0.36, 0.14–0.56).

The calib-dr4 test compares DR3 with DR4's *published* orbits. This test asks a more direct
question of the raw DR4 data: **at the DR3 period, is there a photocentre orbit in DR4's
along-scan epoch astrometry, and is it edge-on?** Under (K), the non-eclipsing targets wobble
as often as the eclipsing ones but are less edge-on. Under (F), many of them do not wobble at
all.

## Data
- **Targets:** the 162 rows of `data/calib-window-v1/window_targets.csv`. Eclipsing = `det_9`
  True (expected 58), non-eclipsing = the rest. If the count is not 58, the job reports it
  and continues.
- **DR3 orbit elements:** `gaiadr3.nss_two_body_orbit` (P, e, t_periastron at J2016.0).
- **DR4 epoch astrometry** (DataLink `RETRIEVAL_TYPE=EPOCH_ASTROMETRY`, release Gaia DR4).
  Field names follow ESA's gaia-supdate reader: `transit_id`, `obs_time_tcb` and
  `obs_time_bary_corr` (ns from 2010-01-01 TCB), `scan_pos_angle` (deg), `parallax_factor_al`,
  `colour_factor_al`, `centroid_pos_al`, `centroid_pos_error_al`, `used_by_agis_al`,
  `agis_source_excess_noise`.
  - If any of these names is missing on release day, the job stops (exit 4). It never
    guesses.

## Model and fit (fixed)
1. Keep CCD rows with `used_by_agis_al` true. Combine rows sharing a `transit_id` into one
   weighted mean (σ = combined formal error). Add `agis_source_excess_noise` in quadrature.
2. Time t = years from J2017.5 (TCB), computed as in gaia-supdate.
3. **Single-star model:** columns [sin θ, cos θ, parallax_factor_al, t·sin θ, t·cos θ], plus
   `colour_factor_al` when it is non-null, with θ = scan_pos_angle.
4. **Orbit model:** the single-star model plus four Thiele-Innes columns [X sin θ, Y sin θ,
   X cos θ, Y cos θ] (B, G, A, F). Here X = cos E − e and Y = √(1−e²) sin E, with E solved from
   the **DR3** P, e and periastron time, which are held fixed. Both models are linear weighted
   least squares.
5. **Statistics:**
   - Δχ² = χ²(single) − χ²(orbit), 4 degrees of freedom;
   - a₀ and cos i from (A, B, F, G) by the standard Thiele-Innes inversion;
   - σ(cos i) from 300 draws of the parameter covariance.
6. **Detected** = Δχ² > 30 (p ≈ 5 × 10⁻⁶ for χ²₄). **Edge-on** = |cos i| − 2σ(cos i) ≤ 0.2.

## Predictions and pass rules
| | prediction | pass rule |
|---|---|---|
| W0 | the method works: the eclipsing targets wobble and are edge-on | ≥ 80% of eclipsers detected, and ≥ 80% of the detected ones edge-on. **If W0 fails, nothing below is interpreted.** |
| W1 | (F) predicts many non-eclipsers do not wobble | D_ne / D_e ≤ 0.60, where D = detected fraction |
| W2 | (K) predicts non-eclipsers wobble as often | D_ne / D_e ≥ 0.85 |
| W3 | (K) also predicts the detected non-eclipsers are less edge-on | edge-on fraction among detected non-eclipsers < 0.6 × the eclipsers' |
| W4 | (report) a₀(DR4 epoch, P fixed) / a₀(DR3), by group | median and 68% range |

**Outcomes:**
- **"Spurious orbits":** W1 passes.
- **"Understated inclination errors":** W2 and W3 both pass.
- **Mixed or inconclusive:** anything else.

95% intervals on D_ne / D_e come from a binomial bootstrap (10,000 draws, seed 20261202).

## Rehearsal before 2 December
ESA's pre-release of DR4 epoch astrometry (12 sources, `gaia-dr4-prerelease-epoch-astrometry_2026-06-26.zip`
on the Gaia anonymous FTP) includes three sources with published astrometric orbits (HD 114762,
Gaia-4, Gaia BH3). Before release day, `dr4_wobble.py` must:
- read that file;
- give Δχ² > 30 for HD 114762 at its DR3 orbit, with P, e and T fixed;
- give Δχ² < 30 for the three QSOs.

If the rehearsal fails, the code is fixed and this note gets an amendment before 2 December.

## Limits stated in advance
- The DR3 P, e and T are held fixed. If DR3's period is right but T has drifted, the fit
  loses power, which favours (F). The W0 control on eclipsers, whose T is checked by TESS,
  measures this.
- The photocentre wobble shrinks for bright companions (luminous binaries). A real but
  low-contrast pair can fail detection, which also favours (F).
- 162 targets give wide intervals. The test can separate (K) from (F) only if the
  difference is large.

## The "wow" if it works
The first direct check, in DR4's own raw measurements, of whether Gaia DR3's near-edge-on
astrometric orbits are real. It splits "Gaia's inclinations are too optimistic" from "a third
of these orbits do not exist" on release day.
