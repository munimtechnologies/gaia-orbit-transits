# Pre-registration: wrong orbits or too-small errors? The DR3 eclipse deficit tested in Gaia DR4

2026-11-18, written 14 days before Gaia DR4 (2 December 2026) and before any DR4 data
exist. MV2 of Munim, Inc.; made with AI agents. Text CC BY 4.0, code Apache-2.0. The code
(`calib_dr4.py`) will be written and published before release day against ESA's draft DR4
data model. Rules below are fixed now. Any change before the data arrive will be logged
here with a date. No change is allowed after.

## Where we stand (DR3)

`findings/2026-11-18-calib-window-results.md`: of 162 Gaia DR3 astrometric orbits with
|cos i| ≤ 0.2 whose predicted conjunctions TESS covered, 58 eclipse within ±9σ_t, where
Gaia's published orbits and errors predict 80.7. The shortfall is real (p = 2 × 10⁻⁵).
Two readings fit equally well:

- **(K) errors too small:** σ(cos i) is understated by k = 2.1 (1.4–3.4) and conjunction
  times by s_t = 1.8 (1.2–2.8); the orbits themselves are right.
- **(F) wrong orbits:** a fraction f = 0.36 (0.14–0.56) of these solutions are wrong (wrong
  period or spurious), and wrong orbits do not eclipse at Gaia's predicted times.

DR4 is based on 66 months of data instead of 34. It re-derives every orbit, so the two
readings make opposite predictions for the same 162 stars.

## Sample and groups (fixed now)

- The 162 targets in `data/calib-window-v1/window_targets.csv` (the calib-v3 main sample).
- **E** = seen at 9σ (`det_9` true; 58 targets). **N** = not seen at 9σ (104 targets).
- Each DR3 source is mapped to DR4 with ESA's DR3→DR4 cross-match table (the name comes
  from the draft data model, job gaia-dr4dm-v2). The best match within 1 arcsec is used.
  Ambiguous matches are labelled UNTESTABLE.

## Labels per target (from DR4 nss_two_body_orbit, astrometric or combined solutions)

- **CONFIRMED:** a DR4 orbit with |P4 − P3| ≤ max(3σ_comb, 0.5% × P3), where σ_comb is
  the DR3 and DR4 period errors added in quadrature.
- **ALIAS:** P4/P3 within the same tolerance of 1/3, 1/2, 2 or 3.
- **CHANGED:** a DR4 orbit at any other period.
- **DROPPED:** no DR4 two-body orbit (single-star or acceleration solution only).
- **UNTESTABLE:** no DR4 source match, or an ambiguous one.
- *Fail* = ALIAS, CHANGED or DROPPED. The fail fraction is computed over testable targets.

## Predictions

| # | prediction | reading it supports | our expectation |
|---|---|---|---|
| K1 | fail(N) − fail(E) ≥ 0.15, and its 95% Newcombe interval excludes 0 | F | 40% |
| K2 | among CONFIRMED targets in N, ≥ 50% have DR4 \|cos i\| > lim₄ + 2σ₄ (now clearly not edge-on); among CONFIRMED targets in E, ≤ 20% do | K | 45% |
| K3 | among CONFIRMED targets in E, ≥ 90% have DR4 \|cos i\| ≤ lim₄ + 3σ₄ (DR4 agrees that they eclipse) | sanity | 80% |
| K4 | for CONFIRMED targets in E with a timed TESS eclipse, the DR4-propagated conjunction offsets have rms z₄ in [0.7, 1.4] (DR4 timing errors are honest) | — | 45% |
| K5 | fail(N) ≤ 0.15 and K2 passes | pure K | 25% |
| K6 | fail(N) ≥ 0.30 and K1 passes | mostly F | 30% |

Here lim₄ = (R1 + R2)/a₄, from the same radii as calib-v3 and the DR4 semi-major axis.
σ₄ is DR4's σ(cos i), propagated from the Thiele–Innes covariance by the same code as in DR3
(`gaia_orbits.py`).

## How the result will be read

- **K1 passes and K2 fails:** the DR3 deficit is mostly **wrong orbits**. The headline
  becomes "about a third of DR3's near-edge-on astrometric orbits are not right", and the
  k = 2.1 of DR3 is withdrawn as an error-scale measurement.
- **K2 passes and K1 fails:** the orbits are right, but their **errors are too small**. The
  headline stays "DR3 inclination errors ×2.1, timing errors ×1.8, measured with real
  eclipses".
- **Both pass:** both effects are present. We then fit k and f jointly on DR3, with DR4
  labels as a prior on which targets are wrong.
- **Neither passes:** DR4 cannot separate the readings for this sample. We say so and run
  the calibration on fresh DR4 orbits instead (below).
- K4 is reported either way. It tells DR4 users whether to inflate DR4 conjunction-time
  errors when planning follow-up.

## Also on release day: the calibration repeated on DR4's own orbits

The same pipeline (`calib_eclipse_rate.py` 0.7.0 plus `calib_window.py` 0.1.0) will be run
on DR4 orbits with |cos i| ≤ 0.2 and G ≤ 14.5 that TESS covers. It will use the DR4 epoch
J2017.5 (JD 2457936.875) and 6σ capped windows from the start (no P/4 skip). The prediction
is fixed now: **k_DR4's 95% lower bound > 1** (our expectation 50%). DR4's sample should be
several times larger than DR3's 162. A clean k_DR4 ≈ 1 would mean DPAC fixed the error
model. A k_DR4 > 1 would tell every DR4 user by how much to inflate the published errors.

## Limits

- DR4 contains the DR3 data (34 of its 66 months), so the two are not fully independent. A
  noise orbit driven by the first 34 months can partly persist. This makes K1 conservative:
  it can only *under*-count wrong DR3 orbits.
- DR4 may publish only some of these sources with orbits for reasons unrelated to reality
  (processing limits). Any DROPPED rate that is also seen in E is treated as a baseline,
  which is why K1 compares N against E rather than against zero.
