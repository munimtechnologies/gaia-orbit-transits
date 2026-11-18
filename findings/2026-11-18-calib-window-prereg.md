# Pre-registration: separating timing-window loss from inclination errors (calib_window 0.1.0)

2026-11-18, written before job gaia-calibw-v1 has run. MV2 of Munim, Inc.; made with AI
agents. Text CC BY 4.0. Code `calib_window.py` 0.1.0 (Apache-2.0), on top of
`calib_eclipse_rate.py` 0.7.0 pinned at commit 2e166f1 (release 0.15.0). Same inputs as
job gaia-calib-v3 (data volume gaia-orbit-tess, `dr3-full-search-v4/`).

**What we have already seen:** the calib-v3 results (`findings/2026-11-18-calib-v3-results.md`):
50 seen vs 69.2 expected, k = 2.31 (1.63–3.43), rms(z) = 1.62 for the 49 timed eclipses.
We have *not* seen any count at wider windows or any joint fit.

## Method (fixed)

1. **R0, reproduction gate.** Rebuild calib-v3's records with the same code and inputs.
   The 3σ detection flags must match calib-v3 for every one of the 162 targets (50 seen).
   If R0 fails, W1–W5 are reported but not graded.
2. **Wider windows.** For each target timed by windows, count a detection if a clean
   dip lies within N σ_t + half its duration of a covered predicted conjunction, for
   N = 3, 4.5, 6 and 9. Above 3σ, the half-width is capped at P/4. The sample stays fixed
   (calib-v3's 162). Targets timed by repeats are unchanged. Each target's false-alarm
   probability scales with its window length: FA_N = 1 − (1 − 0.10)^(hw_N / hw_3).
3. **Joint fit.** Per target, P(detect) = FA + (1 − FA)·p_i(k)·w_i(s_t), where
   w_i = P(|Z| < h_i) for Z ~ N(0, s_t²) and h_i is the window half-width in σ_t units. A
   detected dip at offset z contributes the density p_i·φ(z/s_t)/s_t +
   FA·(1 − p_i w_i)/(2h_i), so real eclipses are Gaussian in time and false alarms are
   uniform. The grid ML runs over k (0.5–20) × s_t (0.5–8), with 95% profile intervals at
   ΔlnL = 1.92. The same fit is repeated with f (wrong-orbit fraction) and with the radius
   scale in place of k, on the 3σ and the 6σ data. The primary fit is k × s_t on the 3σ data
   at FA = 0.10.

## Predictions

| # | prediction | our expectation |
|---|---|---|
| W1 | joint fit: s_t 95% lower bound > 1 (Gaia's timing errors too small) | 85% |
| W2 | joint fit: k 95% lower bound > 1 (inclination errors too small even after window loss) | 40% |
| W3 | 9σ windows: N_obs/N_exp ≤ 0.85 and P(N ≤ N_obs \| M0) < 0.01 | 30% |
| W4 | ratio(9σ) − ratio(3σ) ≥ 0.10 | 55% |
| W5 | W2's verdict is the same at FA = 0.04 and FA = 0.20 | 60% |

## How the result will be read

- W1 passes, W2 fails: the eclipse deficit comes from Gaia's too-small timing errors;
  the DR3 inclination errors are consistent with their published values. We then say
  so, and the "k = 2.3" of calib-v3 is withdrawn.
- W1 and W2 both pass: both kinds of error are too small. The joint k replaces 2.31
  as the headline, with its interval.
- W1 fails: the timing scatter is not well constrained (only 49 timed eclipses), and
  calib-v3's k stands with the caveat in the results note.
- Whatever happens, the method is repeated on Gaia DR4 orbits after 2 December 2026,
  where epoch astrometry makes the test sharper.
