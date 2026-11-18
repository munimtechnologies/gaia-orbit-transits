# Window-loss re-analysis of the Gaia DR3 inclination calibration (calib_window 0.1.0)

MV2 of Munim, Inc.; made with AI agents. Code Apache-2.0, text CC BY 4.0.

Reproduction of calib-v3: {"n_main": 162, "n_obs_v3": 50, "n_obs_here_3sigma": 50, "detection_mismatches": [], "fa3": 0.1, "pass": true}

## Counts with wider timing windows (M0 = Gaia's orbits and errors as published)

| window | seen | expected | ratio | P(<= seen) | mean FA | k (no timing) | timed | rms z |
|---|---|---|---|---|---|---|---|---|
| 3 sigma | 50 | 69.2 | 0.723 | 0.000139 | 0.100 | 2.31 (1.63-3.43) | 49 | 1.60 |
| 4.5 sigma | 55 | 73.4 | 0.749 | 0.000362 | 0.141 | 2.26 (1.56-3.51) | 54 | 2.01 |
| 6 sigma | 57 | 76.6 | 0.744 | 0.000195 | 0.173 | 2.31 (1.56-3.76) | 56 | 2.36 |
| 9 sigma | 58 | 80.7 | 0.719 | 2.09e-05 | 0.219 | 2.60 (1.67-4.53) | 57 | 2.67 |

## Joint fits (inclination model x timing scale s_t)

| fit | parameter best (95%) | s_t best (95%) | lnL |
|---|---|---|---|
| 3sigma_k_fa0.10 | 2.11 (1.39-3.35) | 1.78 (1.22-2.85) | -179.58 |
| 3sigma_f_fa0.10 | 0.36 (0.14-0.56) | 1.70 (1.22-2.85) | -178.51 |
| 3sigma_s_fa0.10 | 0.53 (0.39-0.72) | 1.62 (1.22-2.59) | -177.35 |
| 3sigma_m0_fa0.10 | 1.00 (1.00-1.00) | 2.98 (2.05-4.34) | -184.97 |
| 6sigma_k_fa0.10 | 2.31 (1.60-3.68) | 1.70 (1.17-2.47) | -220.65 |
| 6sigma_f_fa0.10 | 0.42 (0.22-0.60) | 1.62 (1.11-2.36) | -220.00 |
| 6sigma_s_fa0.10 | 0.51 (0.36-0.69) | 1.62 (1.11-2.36) | -218.99 |
| 6sigma_m0_fa0.10 | 1.00 (1.00-1.00) | 2.15 (1.54-4.14) | -231.88 |
| 3sigma_k_fa0.04 | 1.75 (1.21-2.54) | 1.86 (1.34-2.71) | -183.09 |
| 3sigma_k_fa0.20 | 3.05 (1.75-5.85) | 1.54 (0.88-3.13) | -179.86 |

lnL(k, s_t) - lnL(M0, s_t) = 5.39

## Grades

| # | prediction | value | pass |
|---|---|---|---|
| R0 | calib-v3 reproduced at 3 sigma (162 targets, 50 seen, same flags) | {"n_main": 162, "n_obs_v3": 50, "n_obs_here_3sigma": 50, "detection_mismatches": [], "fa3": 0.1, "pass": true} | yes |
| W1 | joint fit: timing scale s_t 95% lower bound > 1 | {"best": 1.7783120139085402, "lo95": 1.2210612700120647, "hi95": 2.8450905632265853, "lnL": -179.58281725381534, "ci_hits_grid_edge": false} | yes |
| W2 | joint fit: k 95% lower bound > 1 (inclination errors too small even after window loss) | {"best": 2.107039331157348, "lo95": 1.3877376159878185, "hi95": 3.351117243556251, "lnL": -179.58281725381534, "ci_hits_grid_edge": false} | yes |
| W3 | 9-sigma windows: ratio <= 0.85 and P(N <= obs | M0) < 0.01 | {"ratio": 0.71869444340881, "p": 2.093018184656434e-05} | yes |
| W4 | ratio(9 sigma) - ratio(3 sigma) >= 0.10 | -0.004005111464845945 | no |
| W5 | W2's verdict unchanged at false-alarm rates 0.04 and 0.20 | [true, true] | yes |
