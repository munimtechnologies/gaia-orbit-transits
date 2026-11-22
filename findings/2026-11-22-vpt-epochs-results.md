# Gaia's own epoch photometry and its transit periods: results of the pre-registered test

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked it yet.
Text CC BY 4.0, code Apache-2.0. Written 2026-11-22 (~23:00 UTC).
Pre-registration: `findings/2026-11-21-vpt-epochs-prereg.md` (fixed 21 Nov, before any epoch
photometry was downloaded). Amendment 1 (file lookup only): `findings/2026-11-22-vpt-epochs-amendment-1.md`.
Job **gaia-vpt-epochs-v2** (22 Nov 18:26-18:48 UTC, `vpt_epochs` 0.1.1). Data: `data/vpt-epochs-v2/`
(`vpt_epochs_summary.json`, `vpt_epochs_stars.csv`, the raw Gaia DR3 G-band epochs of all 214
stars in `epochs_g_1.csv` and `epochs_g_2.csv`, the job record and the run log).

## What ran

All 214 stars of Gaia DR3's transit table (`vari_planetary_transit`) got their Gaia DR3 G-band
field-of-view epochs from ESA's bulk files (ESA's DataLink service answered 503). That is 11,081
epochs. 179 stars had a usable record and 35 had no known ephemeris. Unit tests, the 0.1.1 tests
and the self-test passed. Ephemerides came from the NASA Exoplanet Archive (4,566 TICs) and the
ExoFOP TOI list (6,434 TICs), both fetched by the job.

## Grades (exactly as registered)

| Test | Result | Registered label | Prediction |
|---|---|---|---|
| T1 validity: controls (known planets with Gaia's period right) with purity ≥ 0.5 | 1 of 13 | **TIME_BAD** | TIME_OK 75%: **failed** |
| WHY: alias share among testable wrong-period systems | 4 of 118 (95%: 1.3-8.4%) | **INVALID** (because T1 is TIME_BAD; raw label SPURIOUS_DOMINATED) | ALIAS_DOMINATED 55%; INVALID 5% |
| T3: does N_comp flag wrong periods? AUC (right lower), one-sided p | **0.858**, p = 2.4 × 10⁻⁶ (15 right, 157 wrong) | **PREDICTIVE** | PREDICTIVE 30%: **came true** |
| True period scores at or above Gaia's period in Gaia's own data, for more than half of the wrong-period systems | 85 of 157 (54%) | (reported) | 40%: **came true** |

## Why T1 failed: Gaia's `num_in_transit` is not the number of epochs inside the transit

The registered T1 asks whether the `num_in_transit` epochs nearest Gaia's transit centres are real
transit epochs for known planets whose Gaia period is right. Only HATS-24 b passed (purity 0.56).
The timing is not the problem. **For all 13 controls, every epoch inside the real transit
(predicted from the Exoplanet Archive ephemeris) is in Gaia's set** (coverage 1.0 for 13 of 13).
Gaia's set is simply larger: summed over the 13 controls, 248 Gaia epochs against 96 real-transit
epochs (2.6 times as many). Only 46% of the `num_in_transit` nearest epochs (median over all
stars) lie inside Gaia's own `transit_duration`. So in Gaia DR3, `num_in_transit` counts about
2.6 times more epochs than fall inside Gaia's own transit box. The pre-registration took it to be
the in-transit count, and that capped purity near 0.3-0.45 even for correct periods.

As registered, WHY is reported as INVALID, and the fix goes into a dated module version
(0.1.2). Amendment 2 (`findings/2026-11-22-vpt-epochs-amendment-2.md`) defines Gaia's in-transit
set by Gaia's own box. It was written after this failure was seen and is not blind.

## What the data already show (exploratory, not graded)

- **No wrong-period system is UNRELATED.** All 118 testable wrong-period systems have at least
  one real-transit epoch inside Gaia's in-transit set. None of them has a Gaia in-transit set
  that avoids the real transits.
- **The real transit is in Gaia's photometry.** For 110 of the 118, the epochs inside the real
  transit windows show a dip at S/N ≥ 3 in Gaia's own data (3 of 4 ALIAS, 107 of 114 PARTIAL).
- **In Gaia's own data, the true period beats Gaia's period for 85 of 157** wrong-period systems
  (same box width, phase-free box search). For these, the data held the right answer and the
  pipeline did not pick it.
- Other period-reliability numbers (AUC = P(right group lower)): fraction of the periodogram
  above Gaia's peak, 0.81 (p 4 × 10⁻⁵). Gaia's S/N at its own period, 0.20, so right periods
  have the higher S/N. `num_in_transit`, 0.23.

**N_comp in bins (bins chosen after seeing the data):**

| N_comp (peaks at least 0.9 × as strong as Gaia's) | right period | wrong period | share right |
|---|---|---|---|
| 0-10 | 7 | 2 | 78% |
| 11-99 | 2 | 24 | 8% |
| 100 or more | 6 | 131 | 4% |

Base rate: 15 right out of 172 (9%).

**A known failure of the flag:** TIC 93622019 (Gaia DR3 5345417757181174144) has N_comp = 4,
and the box search on Gaia's own epochs prefers 2.8317 d, Gaia's period. TESS shows that is a 4:3
alias of the true 2.12389 d. The flag measures how unique Gaia's peak is in Gaia's data. When the
sampling makes an alias the unique best peak, the flag cannot catch it.

## What it means for Gaia DR4 (2 December 2026)

T3 holds as registered, because it never uses the ephemerides that T1 checks. A star's N_comp
comes only from its own Gaia epochs, and DR4 publishes epoch photometry for every source. **So
every one of DR4's transit candidates can get a period-reliability flag on release day, without
TESS.** Low-N_comp candidates can be followed at Gaia's period, and the rest by a period-free
search. The other readings above suggest the wrong periods come from period selection on real
dips, not from spurious detections. That question is graded only by amendment 2.

## Limits

Not blind: the known systems were known (the categories came from the step-g rehearsal). T1
failed, so the main WHY question is still open. The binned table and the 'no UNRELATED' and S/N
readings are exploratory. Ephemerides were fetched live on 22 Nov, and a later run may see
slightly different catalogue entries. ESA's TCB time and the archive's TDB times differ by about
20 s (ignored).
