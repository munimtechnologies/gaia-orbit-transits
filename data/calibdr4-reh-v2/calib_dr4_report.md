# calib_dr4 run (dr3), calib_dr4_run 0.1.1

MV2 of Munim, Inc.; made with AI agents. Code Apache-2.0, text CC BY 4.0.

Sample: 162 targets, E = 58 (reproduction passed). t_ref = 389.0 BTJD (gaiadr3.gaia_source.ref_epoch = 2016.0).

Labels: {"CONFIRMED": 162, "ALIAS": 0, "CHANGED": 0, "DROPPED": 0, "UNTESTABLE": 0}

| test | value | pass |
|---|---|---|
| K1 | {"fail_N": 0.0, "fail_E": 0.0, "diff": 0.0, "lo95": -0.062117855787202914, "hi95": 0.03562135437245191, "fail_N_ci": [0.0, 0.03562135437245191], "fail_E_ci": [0.0, 0.062117855787202914]} | no |
| K2 | {"N_conf_not_edge_on": 0.057692307692307696, "n_N_conf": 104, "E_conf_not_edge_on": 0.017241379310344827, "n_E_conf": 58} | no |
| K3 | {"E_conf_edge_on_3sd": 1.0, "n": 58} | yes |
| K4 | {"rms_z4": 2.6152916169824847, "n_timed": 57} | no |
| K5 | {} | no |
| K6 | {} | no |
| K2b | {"N": {"n": 104, "gain": 0, "loss": 1, "frac3": 0.0673076923076923, "frac4": 0.057692307692307696, "delta": -0.009615384615384616, "p_mcnemar": 1.0}, "E": {"n": 58, "gain": 0, "loss": 0, "frac3": 0.017241379310344827, "frac4": 0.017241379310344827, "delta": 0.0, "p_mcnemar": 1.0}} | no |

Reading: **UNDECIDED: DR4 cannot separate the readings for this sample**

DR3 baseline (|cos i| > lim + 2 sd in DR3 itself): {"E": {"n": 58, "not_edge_on_2sd_dr3": 1}, "N": {"n": 104, "not_edge_on_2sd_dr3": 7}}

## Rehearsal checks

- RH1_all_confirmed: PASS {"n_rows": 162, "n_tested": 162, "n_confirmed": 162, "pass": true}
- RH2_cosi_reproduced: PASS {"n": 162, "frac_dcosi_lt_0.1sd": 0.9938271604938271, "median_sd_ratio": 1.0028522365148205, "frac_sd_ratio_0.8_1.25": 1.0, "pass": true}
- RH3_timing_reproduced: PASS {"n_timed": 57, "rms_z4": 2.6152916169824847, "dr3_rms_z9": 2.665039767525298, "pass": true}
- RH4_no_failures: PASS {"K1_pass": false, "fail_N": 0.0, "fail_E": 0.0, "pass": true}
- DR2->DR3 cross-match smoke test: {"new_id_column": "dr3_source_id", "dr2_counterparts": 164, "resolved_ok_to_a_target": 162, "statuses": {"ok": 162, "none": 2, "ambiguous": 0}}
