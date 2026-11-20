# wasp_tyc 0.1.0 report

Detection label: **WASP_INSENSITIVE**
Ephemeris label: **EPHEMERIS_INCONSISTENT** (graded: False)
Blend label: **BLEND_UNRESOLVED**  (graded: False)

```
{
 "version": "0.1.0",
 "stage": "done",
 "target": {
  "name": "1SWASP J202214.65-220425.1",
  "n_rows_err_ok": 8765,
  "n_points": 8738,
  "n_nights": 142,
  "n_seasons": 3,
  "cameras": [
   "225"
  ],
  "t_first": 2453862.5290184445,
  "t_last": 2454614.6910554445,
  "chi2_red_initial": 33.5823998023569
 },
 "controls": {
  "n": 300,
  "max_snr": 22.41249325819821,
  "median_snr": 11.093145441538923,
  "p95_snr": 16.301434617782416
 },
 "injection": {
  "P": 2.6,
  "depth": 0.03,
  "found_P": 2.60078,
  "snr": 19.681454133713103,
  "passed": false
 },
 "box": {
  "snr": 22.2074196177446,
  "depth": 0.07280571194244717,
  "sigma": 0.00327844086326322,
  "phase": 0.299,
  "period": 2.329795
 },
 "fit": {
  "coarse": {
   "period": 2.3297769999999995,
   "t0": 2454003.053903705,
   "depth": 0.08545013764115868,
   "sigma_white": 0.003549525656592593,
   "dchi2": 579.5419715200117,
   "edge": false
  },
  "nights_detrended": 134,
  "fine": {
   "period": 2.3297429999999992,
   "t0": 2453944.807328705,
   "depth": 0.07427194555642747,
   "sigma_white": 0.0010454307983347073,
   "dchi2": 5047.29885398778,
   "edge": true
  },
  "chi2_red_after_detrend": 2.8423304632164865
 },
 "bootstrap": {
  "n": 150,
  "edge_fraction": 0.5333333333333333,
  "sigma_P": 2.0197154649309316e-05,
  "sigma_T0": 0.003258898960428055,
  "sigma_depth": 0.01959095559369174
 },
 "wasp_ephemeris": {
  "T0_bjd_tdb": 2453944.807328705,
  "sigma_T0": 0.003258898960428055,
  "P": 2.3297429999999992,
  "sigma_P": 2.0197154649309316e-05
 },
 "primary": {
  "depth_mag": 0.0742719455360089,
  "sigma_boot": 0.01959095559369174,
  "snr_fit": 3.7911343926441425,
  "n_eclipse_nights": 9,
  "ratio_to_tess_depth": 1.0922344931766013
 },
 "odd_even": {
  "odd": 0.07969131211322646,
  "even": 0.06925950108458227,
  "sigma_diff": 0.053392444917808805,
  "consistent": true
 },
 "secondary": {
  "depth_mag": -0.0013029181497106544,
  "sigma_boot": 0.0006425808187285018,
  "below_third_of_primary": true
 },
 "label": "WASP_INSENSITIVE",
 "ephemeris": {
  "cycles": 2943.7678625044723,
  "N": 2944,
  "frac": -0.23213749552769514,
  "sig_x": 0.025564218341847366,
  "label": "EPHEMERIS_INCONSISTENT",
  "P_comb": 2.3295592973147943,
  "sig_P_comb": 1.157905594885752e-06,
  "gaia_z": 4.496255609989686,
  "gaia_consistent": false,
  "alt_periods": {
   "2943": 2.330350856709057,
   "2945": 2.3287682754820898
  },
  "graded": false,
  "dr4_phase_shift_using_gaia_P": -0.28462074835260864
 },
 "blend": {
  "label": "BLEND_UNRESOLVED",
  "neighbour": null,
  "per_neighbour": {
   "1SWASP J202215.96-220458.7": {
    "status": "ok",
    "n_points": 8638,
    "depth_mag": 0.06377234282656619,
    "sigma_diff": 0.0032475802614184263,
    "z_target_minus_neighbour": 3.233054109294549
   },
   "1SWASP J202209.46-220414.3": {
    "status": "ok",
    "n_points": 7405,
    "depth_mag": 0.008816927308245012,
    "sigma_diff": 0.06618342090558284,
    "z_target_minus_neighbour": 0.9889941821100772
   },
   "1SWASP J202211.21-220522.8": {
    "status": "ok",
    "n_points": 8624,
    "depth_mag": 0.018244606786566375,
    "sigma_diff": 0.01730279052970936,
    "z_target_minus_neighbour": 3.2380521889369263
   }
  },
  "graded": false
 },
 "seasons": {
  "0": {
   "n_points": 4729,
   "cycle": -9,
   "o_minus_c_d": -0.00039999978616833687,
   "sigma_white_depth": 0.0010989280996781786
  },
  "2": {
   "n_points": 3594,
   "cycle": 171,
   "o_minus_c_d": -0.015399999916553497,
   "sigma_white_depth": 0.0026313606077013165
  },
  "3": {
   "n_points": 415,
   "cycle": 282,
   "o_minus_c_d": 0.01640000008046627,
   "sigma_white_depth": 0.41432672022478934
  }
 },
 "prior_art_reported_only": {
  "all_10as": {
   "status": "failed",
   "error": "HTTP Error 404: Not Found"
  },
  "eblm_iv_60as": {
   "status": "failed",
   "error": "HTTP Error 404: Not Found"
  }
 }
}
```
