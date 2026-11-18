# Results: Gaia DR3's eclipse deficit is not a timing artefact (job gaia-calibw-v1)

2026-11-18. MV2 of Munim, Inc.; made with AI agents. Text CC BY 4.0, code Apache-2.0.
Pre-registration: `findings/2026-11-18-calib-window-prereg.md` (written before the job ran).
Code: `calib_window.py` 0.1.0 on top of `calib_eclipse_rate.py` 0.7.0 (commit 2e166f1).
Outputs: `data/calib-window-v1/` (`window_report.md`, `window_summary.json`,
`window_targets.csv`). The job ran on 2026-11-18. It used the same inputs as gaia-calib-v3.

## The question

Gaia DR3 publishes an orbit, an inclination and a predicted conjunction time for each
astrometric binary. An orbit within (R1 + R2)/a of edge-on *must* eclipse. TESS therefore
tests Gaia's inclinations and their errors star by star. Our first count
(`findings/2026-11-18-calib-v3-results.md`) found **50 eclipsing systems where Gaia's
published orbits and errors predict 69.2** (162 orbits with |cos i| ≤ 0.2, p = 1.4 × 10⁻⁴).
But the eclipses we did see also arrived further from Gaia's predicted times than its
errors allow (rms z = 1.62 inside ±3σ windows). Real eclipses that fall outside the windows
are never counted, so the deficit could have been an artefact of our timing windows. This
job was built to separate the two effects. It recounts with wider windows and fits the
inclination-error scale k and a timing-error scale s_t together.

## Gate

**R0 passes.** At 3σ the job rebuilt all 162 targets, with 50 seen, the same detection
flags for every target and a false-alarm rate of 0.10.

## Results

| timing window | seen | expected (Gaia as published) | ratio | P(N ≤ seen) |
|---|---|---|---|---|
| 3σ_t | 50 | 69.2 | 0.72 | 1.4 × 10⁻⁴ |
| 4.5σ_t | 55 | 73.4 | 0.75 | 3.6 × 10⁻⁴ |
| 6σ_t | 57 | 76.6 | 0.74 | 2.0 × 10⁻⁴ |
| 9σ_t | 58 | 80.7 | 0.72 | 2.1 × 10⁻⁵ |

Tripling the window width adds 8 detections. False alarms grow with window length, so 11.5
more were expected even with no real eclipses outside 3σ. **The deficit does not close.**

Joint maximum-likelihood fits (95% profile intervals):

| fit (data, model) | inclination parameter | timing scale s_t | lnL |
|---|---|---|---|
| **3σ, k (primary)** | **k = 2.11 (1.39–3.35)** | **1.78 (1.22–2.85)** | −179.58 |
| 6σ, k | k = 2.31 (1.60–3.68) | 1.70 (1.17–2.47) | −220.65 |
| 3σ, wrong-orbit fraction | f = 0.36 (0.14–0.56) | 1.70 (1.22–2.85) | −178.51 |
| 3σ, radius scale | s = 0.53 (0.39–0.72) | 1.62 (1.22–2.59) | −177.35 |
| 3σ, Gaia as published (k = 1) | — | 2.98 (2.05–4.34) | −184.97 |
| 3σ, k, false-alarm rate 0.04 | k = 1.75 (1.21–2.54) | 1.86 (1.34–2.71) | −183.09 |
| 3σ, k, false-alarm rate 0.20 | k = 3.05 (1.75–5.85) | 1.54 (0.88–3.13) | −179.86 |

Even with the timing scale free, letting k vary improves the fit by ΔlnL = 5.39
(2ΔlnL = 10.8 for one parameter, p ≈ 0.001).

## Grades (pre-registered; our prior expectation in brackets)

| # | prediction | value | pass |
|---|---|---|---|
| R0 | calib-v3 reproduced | 162 / 50 / no mismatches | yes |
| W1 | s_t 95% lower bound > 1 (85%) | 1.78 (1.22–2.85) | **yes** |
| W2 | k 95% lower bound > 1 after window loss (40%) | 2.11 (1.39–3.35) | **yes** |
| W3 | 9σ: ratio ≤ 0.85 and p < 0.01 (30%) | 0.72, p = 2.1 × 10⁻⁵ | **yes** |
| W4 | ratio(9σ) − ratio(3σ) ≥ 0.10 (55%) | −0.004 | no |
| W5 | W2 unchanged at false-alarm rates 0.04 and 0.20 (60%) | both pass | **yes** |

The pre-registered reading for "W1 and W2 both pass" is: *both kinds of error are too small;
the joint k replaces 2.31 as the headline, with its interval.* W4's failure points the same
way. The missing eclipses are not hiding just outside our windows. We gave W2 only a 40%
chance, so this outcome went against our own expectation.

## What we can now say

1. **Gaia DR3 orbits that should eclipse do so about 28% less often than their published
   errors allow, and the shortfall is real.** It survives windows three times wider
   (p = 2 × 10⁻⁵) and false-alarm rates from 4% to 20%.
2. **Gaia DR3's predicted conjunction times are too optimistic by a factor of about 1.8**
   (95%: 1.2–2.8), measured from 49 real eclipses.
3. **If the cause is error underestimation, σ(cos i) is too small by k = 2.1 (1.4–3.4).**
   That agrees with Makarov's (2025, ApJL, arXiv:2502.20553) *simulated* factor of 2.3 for
   edge-on orbits. As far as we know this is the first measurement of it with real eclipses.
4. **But the same data fit "about a third (14–56%) of these orbits are wrong" equally well**
   (ΔlnL = 1.1 in favour of f, which is not significant). A radius scale of s = 0.53 fits
   slightly better still (ΔlnL = 2.2). *Post hoc, and labelled as such:* we consider s
   physically unlikely, because it needs the sum of stellar radii to be half the catalogue
   values, where TIC/Gaia radii are good to ~10–20%. It stays in the table. The k reading
   and the f reading cannot be separated with 162 orbits. Gaia DR4 can separate them (see
   below).

Caveat found while grading (post hoc, cannot change a grade): the 0.7.0 rule *skips* a
window whose 3σ half-width exceeds P/4. One target (Gaia DR3 1117674258493434624,
TIC 289661950, P = 118 d) has a dip at z = −0.55 that was therefore not counted at 3σ. The
wider counts and the 6σ fit cap the window instead of skipping it, so they include it. The
6σ fit (k = 2.31, 1.60–3.68) agrees with the primary fit.

## Why it matters

Gaia DR4 (2 December 2026) will publish about 13 times more orbits, including companions
of brown-dwarf and planetary mass whose true masses rest on sin i, plus transit and eclipse
time predictions. If DR4 errors behave like DR3's, inclination-based mass ranges and
predicted transit windows will be about twice too narrow. If instead a third of
near-edge-on orbits are wrong, they will fail outright. This matters for anyone who plans
TESS, PLATO or ground follow-up from Gaia orbits.

## Next

`findings/2026-11-18-calib-dr4-prereg.md` pre-registers, before DR4 exists, the test that
separates the two readings on the same 162 orbits. Under "wrong orbits", the non-eclipsing
orbits should change period or vanish in DR4. Under "errors too small", they should keep
their DR3 period and move away from edge-on.
