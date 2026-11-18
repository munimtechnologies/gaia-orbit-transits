# eblm_infl 0.1.0: short-period M-dwarf inflation vs BHAC15

Model source: https://perso.ens-lyon.fr/isabelle.baraffe/BHAC15dir/BHAC15_iso.2mass

Rows 70, clean EBLM fits 26, main set 14.

## H1 (median inflation, FLAME R1, BHAC15 5 Gyr)

n = 14, median = +0.0216, 95% CI [+0.0031, +0.0713] -> **INCONCLUSIVE**; contains Swayne et al. 2024's +6%: True

## H2 (Spearman inflation vs period, one-sided)

```
{
 "n": 14,
 "rho_infl_P": 0.4857142857142857,
 "p_one_sided": 0.9623037696230377,
 "label": "NO_TREND_DETECTED",
 "rho_m2_P": 0.4945054945054945,
 "rho_infl_m2": 0.23076923076923078
}
```

## Period bins (main set)

| bin | n | median | 95% CI |
|---|---|---|---|
| P_0_1 | 1 | -0.1357 | [-0.1357, -0.1357] |
| P_1_2 | 10 | +0.0216 | [-0.0109, +0.0713] |
| P_2_5 | 3 | +0.0700 | [+0.0016, +0.2482] |
| P_ge_5 | 0 | nan | [nan, nan] |

## Variants

| set/estimator | n | median | 95% CI | label |
|---|---|---|---|---|
| main/infl_flame_1 | 14 | +0.0385 | [+0.0228, +0.0965] | INCONCLUSIVE |
| main/infl_flame_5 | 14 | +0.0216 | [+0.0031, +0.0713] | INCONCLUSIVE |
| main/infl_flame_10 | 14 | +0.0099 | [-0.0116, +0.0580] | INCONCLUSIVE |
| main/infl_lc_1 | 14 | +0.0483 | [+0.0240, +0.0841] | INCONCLUSIVE |
| main/infl_lc_5 | 14 | +0.0318 | [+0.0012, +0.0610] | INCONCLUSIVE |
| main/infl_lc_10 | 14 | +0.0218 | [-0.0111, +0.0446] | INCONCLUSIVE |
| all_clean/infl_flame_1 | 17 | +0.0306 | [-0.0252, +0.0901] | INCONCLUSIVE |
| all_clean/infl_flame_5 | 17 | +0.0081 | [-0.0418, +0.0700] | INCONCLUSIVE |
| all_clean/infl_flame_10 | 17 | -0.0054 | [-0.0545, +0.0550] | INCONCLUSIVE |
| all_clean/infl_lc_1 | 26 | +0.0400 | [+0.0015, +0.0923] | INCONCLUSIVE |
| all_clean/infl_lc_5 | 26 | +0.0258 | [-0.0184, +0.0709] | INCONCLUSIVE |
| all_clean/infl_lc_10 | 26 | +0.0176 | [-0.0322, +0.0539] | INCONCLUSIVE |

## Cuts

- b_ge_0.8: 1
- in_main_set: 14
- no_flame_mass: 9
- not_clean_verdict: 44
- snr_lt_30: 2
