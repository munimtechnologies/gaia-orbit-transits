# eblm_infl 0.1.0: short-period M-dwarf inflation vs BHAC15

Model source: https://perso.ens-lyon.fr/isabelle.baraffe/BHAC15dir/BHAC15_iso.2mass

Rows 167, clean EBLM fits 62, main set 28.

## H1 (median inflation, FLAME R1, BHAC15 5 Gyr)

n = 28, median = +0.0627, 95% CI [+0.0101, +0.0882] -> **INCONCLUSIVE**; contains Swayne et al. 2024's +6%: True

## H2 (Spearman inflation vs period, one-sided)

```
{
 "n": 28,
 "rho_infl_P": 0.48549534756431306,
 "p_one_sided": 0.9956004399560044,
 "label": "NO_TREND_DETECTED",
 "rho_m2_P": 0.23864258347016967,
 "rho_infl_m2": 0.3793103448275862
}
```

## Period bins (main set)

| bin | n | median | 95% CI |
|---|---|---|---|
| P_0_1 | 2 | -0.1256 | [-0.1357, -0.1154] |
| P_1_2 | 18 | +0.0381 | [+0.0081, +0.0816] |
| P_2_5 | 8 | +0.0976 | [+0.0700, +0.2482] |
| P_ge_5 | 0 | nan | [nan, nan] |

## Variants

| set/estimator | n | median | 95% CI | label |
|---|---|---|---|---|
| main/infl_flame_1 | 28 | +0.0806 | [+0.0312, +0.1074] | INFLATED |
| main/infl_flame_5 | 28 | +0.0627 | [+0.0101, +0.0882] | INCONCLUSIVE |
| main/infl_flame_10 | 28 | +0.0496 | [-0.0016, +0.0766] | INCONCLUSIVE |
| main/infl_lc_1 | 28 | +0.0658 | [+0.0390, +0.0892] | INFLATED |
| main/infl_lc_5 | 28 | +0.0496 | [+0.0234, +0.0709] | INCONCLUSIVE |
| main/infl_lc_10 | 28 | +0.0363 | [+0.0131, +0.0544] | INCONCLUSIVE |
| all_clean/infl_flame_1 | 43 | +0.0424 | [+0.0210, +0.0711] | INCONCLUSIVE |
| all_clean/infl_flame_5 | 43 | +0.0210 | [+0.0046, +0.0555] | INCONCLUSIVE |
| all_clean/infl_flame_10 | 41 | +0.0015 | [-0.0088, +0.0550] | INCONCLUSIVE |
| all_clean/infl_lc_1 | 62 | +0.0678 | [+0.0390, +0.0982] | INFLATED |
| all_clean/infl_lc_5 | 62 | +0.0513 | [+0.0229, +0.0791] | INCONCLUSIVE |
| all_clean/infl_lc_10 | 59 | +0.0352 | [+0.0075, +0.0595] | INCONCLUSIVE |

## Cuts

- b_ge_0.8: 1
- in_main_set: 28
- m2_outside_0.08_0.6: 10
- no_flame_mass: 20
- not_clean_verdict: 105
- snr_lt_30: 3
