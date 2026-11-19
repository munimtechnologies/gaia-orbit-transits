# inclination_floor 0.1.0: can face-on stars explain the missing transits?

Chunks used: k0, k1, k2, k3, k4, k5, k6, k7. Missing: none. Duplicate rate-sample rows dropped: 0.

## Primary grade (BD class, primary sample)

Reproduction: n_rate_sample 2180, substellar-size hits 3, control false alarms 0.50, E_iso 407.7 (rho_iso 0.006, 95% 0.000-0.020).

- **central** (F_star 0.040, F_BD 0.0020, BD flat, gamma 0): mean c 0.591, E_pop 241.1, phi 0.010 (95% 0.000-0.034)
- **floor** (F_star 0.080, F_BD 0.0005, BD logflat, gamma -1): mean c 0.063, E_pop 25.7, phi 0.097 (95% 0.005-0.322)

- **I1** floor upper bound < 0.5: 0.322, pass True
- **I2** central upper bound < 0.5: 0.034, pass True
- **Label: MOSTLY_SPURIOUS**
- Grid scenarios with upper bound < 0.5: 36 of 36

### r*: the largest F_BD/F_star for which 'every BD-class orbit is real' survives at 95 %

- flat_gamma0: r* = 0.00058 (ok); literature central 0.0500 -> 86.9 x drier; floor 0.0063 -> 10.9 x drier
- logflat_gamma-1: r* = 0.00181 (ok); literature central 0.0500 -> 27.6 x drier; floor 0.0063 -> 3.5 x drier

### Full grid (BD class)

| F_star | F_BD | BD shape | gamma | mean c | E_pop | phi (95%) |
|---|---|---|---|---|---|---|
| 0.020 | 0.0005 | flat | 0 | 0.415 | 169.4 | 0.015 (0.001-0.049) |
| 0.020 | 0.0005 | flat | -1 | 0.177 | 72.0 | 0.035 (0.002-0.115) |
| 0.020 | 0.0005 | logflat | 0 | 0.413 | 168.3 | 0.015 (0.001-0.049) |
| 0.020 | 0.0005 | logflat | -1 | 0.188 | 76.8 | 0.033 (0.002-0.108) |
| 0.020 | 0.0020 | flat | 0 | 0.784 | 319.6 | 0.008 (0.000-0.026) |
| 0.020 | 0.0020 | flat | -1 | 0.446 | 181.7 | 0.014 (0.001-0.046) |
| 0.020 | 0.0020 | logflat | 0 | 0.763 | 310.9 | 0.008 (0.000-0.027) |
| 0.020 | 0.0020 | logflat | -1 | 0.440 | 179.5 | 0.014 (0.001-0.046) |
| 0.020 | 0.0050 | flat | 0 | 1.029 | 419.7 | 0.006 (0.000-0.020) |
| 0.020 | 0.0050 | flat | -1 | 0.691 | 281.6 | 0.009 (0.000-0.029) |
| 0.020 | 0.0050 | logflat | 0 | 1.019 | 415.4 | 0.006 (0.000-0.020) |
| 0.020 | 0.0050 | logflat | -1 | 0.673 | 274.3 | 0.009 (0.000-0.030) |
| 0.040 | 0.0005 | flat | 0 | 0.271 | 110.7 | 0.023 (0.001-0.075) |
| 0.040 | 0.0005 | flat | -1 | 0.100 | 40.8 | 0.061 (0.003-0.203) |
| 0.040 | 0.0005 | logflat | 0 | 0.280 | 114.1 | 0.022 (0.001-0.072) |
| 0.040 | 0.0005 | logflat | -1 | 0.112 | 45.7 | 0.055 (0.003-0.181) |
| 0.040 | 0.0020 | flat | 0 | 0.591 | 241.1 | 0.010 (0.000-0.034) |
| 0.040 | 0.0020 | flat | -1 | 0.291 | 118.8 | 0.021 (0.001-0.070) |
| 0.040 | 0.0020 | logflat | 0 | 0.576 | 235.0 | 0.011 (0.001-0.035) |
| 0.040 | 0.0020 | logflat | -1 | 0.297 | 121.2 | 0.021 (0.001-0.068) |
| 0.040 | 0.0050 | flat | 0 | 0.846 | 344.9 | 0.007 (0.000-0.024) |
| 0.040 | 0.0050 | flat | -1 | 0.502 | 204.7 | 0.012 (0.001-0.040) |
| 0.040 | 0.0050 | logflat | 0 | 0.825 | 336.4 | 0.007 (0.000-0.025) |
| 0.040 | 0.0050 | logflat | -1 | 0.493 | 201.0 | 0.012 (0.001-0.041) |
| 0.080 | 0.0005 | flat | 0 | 0.165 | 67.5 | 0.037 (0.002-0.123) |
| 0.080 | 0.0005 | flat | -1 | 0.054 | 22.0 | 0.114 (0.005-0.376) |
| 0.080 | 0.0005 | logflat | 0 | 0.179 | 73.1 | 0.034 (0.002-0.113) |
| 0.080 | 0.0005 | logflat | -1 | 0.063 | 25.7 | 0.097 (0.005-0.322) |
| 0.080 | 0.0020 | flat | 0 | 0.415 | 169.4 | 0.015 (0.001-0.049) |
| 0.080 | 0.0020 | flat | -1 | 0.177 | 72.0 | 0.035 (0.002-0.115) |
| 0.080 | 0.0020 | logflat | 0 | 0.413 | 168.3 | 0.015 (0.001-0.049) |
| 0.080 | 0.0020 | logflat | -1 | 0.188 | 76.8 | 0.033 (0.002-0.108) |
| 0.080 | 0.0050 | flat | 0 | 0.653 | 266.0 | 0.009 (0.000-0.031) |
| 0.080 | 0.0050 | flat | -1 | 0.337 | 137.4 | 0.018 (0.001-0.060) |
| 0.080 | 0.0050 | logflat | 0 | 0.634 | 258.7 | 0.010 (0.000-0.032) |
| 0.080 | 0.0050 | logflat | -1 | 0.340 | 138.5 | 0.018 (0.001-0.060) |

## VLMS class (descriptive)

- central: n_sub 6, E_iso 124.0, mean c 0.617, E_pop 76.6, phi 0.065 (95% 0.016-0.157)
- floor: n_sub 6, E_iso 124.0, mean c 0.985, E_pop 122.1, phi 0.041 (95% 0.010-0.099)

## Secondary: amendment-1 sample (trusted dwarf radii only), BD class

- central: n_sub 3, E_iso 282.6, E_pop 156.0, phi 0.016 (95% 0.001-0.053)
- floor: n_sub 3, E_iso 282.6, E_pop 13.4, phi 0.187 (95% 0.009-0.619)
- Label on this sample: SPURIOUS_UNLESS_DRY_DESERT
