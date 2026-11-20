# qcut 0.1.0: do Gaia's quality columns pick out the real low-mass SB1 orbits?

Pool rows fetched: 11937 (duplicates dropped 0). Rate-sample stars matched: 3113; unmatched: 0.

## Self-checks

- RC4_n_rate_sample: [3113, 3113, true]
- RC4_E_all: [557.9804020618889, 558.0, true]
- RC4_n_hit: [25, 25, true]
- RC5_E_pop_central_BD: [241.12852506066395, 241.1, true]
- RC1_pool_rows_ge_6434: [11937, 6434, true]
- RC2_all_rate_sample_matched: [0, 0, true]
- RC3_significance_agrees: [0, 3113, true]

## Q1: Gaia's gold sample (Gosset et al. 2024, Appendix J), BD + VLMS classes

**Label: UNDERPOWERED** (SB1-only variant: UNDERPOWERED). Gold stars in the rate sample, all classes: 9.

| group | stars | hits | substellar-size hits | E_iso | rho_all | E_pop central | phi central | E_pop floor | phi floor |
|---|---|---|---|---|---|---|---|---|---|
| gold | 9 | 1 | 1 | 1.2 | 0.847 (95% 0.021-4.717) | 0.7 | 1.343 (95% 0.034-7.485) | 0.3 | 2.908 (95% 0.074-16.204) |
| not gold | 2972 | 24 | 8 | 530.5 | 0.031 (95% 0.015-0.053) | 317.0 | 0.021 (95% 0.006-0.045) | 147.4 | 0.044 (95% 0.013-0.097) |
| gold, SB1 only | 9 | 1 | 1 | 1.2 | 0.847 (95% 0.021-4.717) | 0.7 | 1.343 (95% 0.034-7.485) | 0.3 | 2.908 (95% 0.074-16.204) |
| gold, BD class only | 5 | 0 | 0 | 0.9 | 0.000 (95% 0.000-4.337) | 0.5 | 0.000 (95% 0.000-6.849) | 0.0 | 0.000 (95% 0.000-198.149) |

## Q2: transit rate by Gaia significance (K / sigma_K), BD + VLMS classes

**Label: RISES_PRIMARY_ONLY**

| group | stars | hits | substellar-size hits | E_iso | rho_all | E_pop central | phi central | E_pop floor | phi floor |
|---|---|---|---|---|---|---|---|---|---|
| T1 | 1834 | 13 | 4 | 331.6 | 0.029 (95% 0.010-0.056) | 197.2 | 0.015 (95% 0.000-0.047) | 78.9 | 0.038 (95% 0.001-0.117) |
| T2 | 974 | 7 | 3 | 173.3 | 0.020 (95% 0.000-0.063) | 103.9 | 0.024 (95% 0.001-0.080) | 56.7 | 0.044 (95% 0.002-0.146) |
| T3 | 173 | 5 | 2 | 26.9 | 0.167 (95% 0.042-0.416) | 16.5 | 0.121 (95% 0.015-0.437) | 12.2 | 0.163 (95% 0.020-0.590) |

- Primary (all hits, E_iso), T3 vs T1: {"N": 18, "rho0": 0.03905544466303985, "share_h0": 0.08607148726097485, "p_one_sided": 0.015597977497973894}
- Robustness (substellar-size hits, E_pop central), T3 vs T1: {"N": 6, "rho0": 0.023390949381046352, "share_h0": 0.0644952062577083, "p_one_sided": 0.05241561407080706}

## Q3 (exploratory): median splits, BD + VLMS, all hits vs E_iso, Bonferroni alpha 0.01

| column | median | better half | good-half rho_all | bad-half rho_all | p (one-sided) | pass |
|---|---|---|---|---|---|---|
| efficiency | 0.4249 | high | 0.023 (95% 0.006-0.052) | 0.044 (95% 0.016-0.083) | 0.9009 | False |
| rv_n_good_obs_primary | 21.0000 | high | 0.020 (95% 0.000-0.052) | 0.046 (95% 0.022-0.083) | 0.9443 | False |
| goodness_of_fit | 0.1652 | low | 0.056 (95% 0.031-0.094) | 0.009 (95% 0.000-0.040) | 0.0104 | False |
| conf_spectro_period | 0.9960 | high | 0.033 (95% 0.011-0.066) | 0.032 (95% 0.010-0.068) | 0.5603 | False |
| amp_ratio | 1.1951 | low | 0.047 (95% 0.021-0.085) | 0.019 (95% 0.000-0.050) | 0.1008 | False |
