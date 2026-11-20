# Quality-cut amendment: Q4e and Q4f, graded on Gaia DR4 day (pre-registration)

Written 2026-11-20 (about 23:30 UTC) by MV2 of Munim, Inc.; made with AI agents working in his
name, not checked by a human expert. Text CC BY 4.0. Gaia DR4 (2 December 2026) does not exist
yet, so no DR4 label for any orbit has been seen. The DR3-side inputs are already fixed and public:
`data/qcut-v1/qcut_columns.csv` (committed 20 Nov, commit 5e73cd7) and the grader `qcut_dr4.py`
0.1.0 (commit 47ffeb6, release v0.34.0).

## Why

The graded quality-cut test (`findings/2026-11-20-quality-cut-results.md`) left two loose ends:

1. **goodness_of_fit** missed the corrected threshold by a hair (p = 0.0104 against Bonferroni
   α = 0.01), in the pre-registered direction: the better-fitting half of the 2,981 low-mass
   orbits transits about six times as often relative to expectation (ρ_all 0.056 vs 0.009).
   A near-miss found in one test should be tested again on data that test did not use.
2. Two ingredients of Gaia's recommended "gold" cut, **efficiency** and
   **rv_n_good_obs_primary**, pointed the **wrong way** in the transit test: the half Gaia would
   call better transits less often (efficiency ρ_all 0.023 vs 0.044; good RV epochs 0.020 vs
   0.046). That direction was not tested, so it was only a description.

Gaia DR4 gives a second, different yardstick: whether each DR3 orbit is CONFIRMED in DR4
(`dr4_sb1_reality.py`, release-day step a1). Transits test whether an orbit can be real; DR4
survival tests whether Gaia finds the same orbit again with about twice the data. These are
not the same thing. An orbit could come back in DR4 because the same systematic is still there.
This amendment asks whether the two yardsticks agree on which DR3 columns pick out real orbits.
If they disagree, the planned per-orbit "reality score" cannot be trained on DR4 survival alone.

## Inputs (nothing new is computed by new code)

Both tests are graded from `qcut_dr4_summary.json`, section **Q4d**, written by `qcut_dr4.py`
0.1.0 at step a4 of the release-day runbook. For each column Q4d gives `auc`, `n_confirmed` (n1)
and `n_dropped_or_changed` (n0). The AUC is oriented so that 1 means the column's pre-registered
"better" direction (qcut 0.1.0: goodness_of_fit low, efficiency high, rv_n_good_obs_primary high)
picks CONFIRMED over DROPPED + CHANGED; ALIAS and UNTESTABLE are left out. The sample is the whole
S3 pool (all classes), as Q4d computes it.

**Fixed significance rule (written now, applied by hand or by a short script at grading):**
z = (AUC − 0.5) / sqrt((n1 + n0 + 1) / (12 · n1 · n0)), the Mann-Whitney null variance with no
tie correction (ties make the true variance smaller, so this is conservative). One-sided p from
the standard normal. If n1 < 20 or n0 < 20 for a column, its label is **UNTESTABLE**.

## Q4e (graded): does goodness_of_fit predict DR4 survival?

- **GOF_REPLICATES**: AUC > 0.5 and one-sided p < 0.05.
- **GOF_REVERSED**: AUC < 0.5 and one-sided p (for the opposite direction) < 0.05.
- **GOF_NOT_REPLICATED**: otherwise.

## Q4f (graded): do DR4 survival and the transit test agree on the gold-cut ingredients?

Graded separately for **efficiency** and **rv_n_good_obs_primary**, at α = 0.025 each (two
columns):
- **AGREES_WITH_TRANSITS**: AUC < 0.5 and one-sided p < 0.025 (Gaia's "better" half survives
  less often, as it transits less often).
- **DISAGREES_WITH_TRANSITS**: AUC > 0.5 and one-sided p < 0.025 (Gaia's "better" half survives
  more often, though it transits less often).
- **UNDECIDED**: otherwise.

Overall label: **YARDSTICKS_DISAGREE** if either column is DISAGREES_WITH_TRANSITS;
**YARDSTICKS_AGREE** if both are AGREES_WITH_TRANSITS; **YARDSTICKS_UNCLEAR** otherwise.

## Consequences fixed now

- YARDSTICKS_DISAGREE: DR4 survival is not a stand-in for reality for these orbits. Any reality
  score is calibrated on transits (with a held-out chunk) and DR4 survival is reported next to
  it, never used as its training label. The write-up must say that the DR4 survival rate
  overstates how many orbits are real by an unknown amount.
- YARDSTICKS_AGREE: the transit pattern is real, not noise from 25 hits. Gaia's own gold-cut
  ingredients then point the wrong way for this class, which we report as a finding about the
  cut (not about the catalogue as a whole).
- GOF_REPLICATES: goodness_of_fit enters the reality score as a pre-declared feature.
  GOF_NOT_REPLICATED or GOF_REVERSED: the Q3 near-miss is reported as not replicated.

## Predictions (written before DR4)

- Q4e: GOF_REPLICATES 75%, GOF_NOT_REPLICATED 22%, GOF_REVERSED 3%. (A poorly fitting DR3 orbit
  should be less likely to come back, real or not.)
- Q4f rv_n_good_obs_primary: DISAGREES 50%, UNDECIDED 35%, AGREES 15%. (More epochs should make
  an orbit more repeatable, whether or not it is real.)
- Q4f efficiency: DISAGREES 35%, UNDECIDED 45%, AGREES 20%.
- Overall: YARDSTICKS_DISAGREE 60%, YARDSTICKS_UNCLEAR 32%, YARDSTICKS_AGREE 8%.

## Limits

- DR4 reprocesses DR3's epochs together with new ones, so DR4 survival is not independent of the
  DR3 columns. That is the point of Q4f, but it also means a GOF_REPLICATES label shows
  repeatability, not reality.
- Q4d covers the whole S3 pool (6,434 orbits, all classes), and the Q3 pattern was seen in the
  2,981 brown-dwarf- and very-low-mass-class orbits at 1-13 days. A different answer could come
  from the different sample, and we will say so.
- If `qcut_dr4.py` stops on a self-check (exit 3), these labels are not graded until it runs.
