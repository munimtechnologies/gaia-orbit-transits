# tyc_period 0.1.0 report

- A detection: **ASASSN_INSENSITIVE**
- A period branch: **BRANCH_UNTESTABLE**
- A TESS link: **EPHEMERIS_INCONSISTENT**
- A WASP link: **WASP_LINK_UNTESTABLE**
- A blend (38 arcsec neighbour): **BLEND_UNRESOLVED**
- B WASP common mode: **COMMON_CLEAN**

```
{
 "version": "0.1.0",
 "stage": "done",
 "B_common_mode": {
  "repro": {
   "target_depth": 0.0742719455360089,
   "target_ok": true,
   "n38_depth": 0.06377234282656619,
   "n38_ok": true,
   "ok": true
  },
  "label": "COMMON_CLEAN",
  "n_usable": 12,
  "n_dippers": 0,
  "comps": [
   {
    "name": "1SWASP J202225.43-220021.0",
    "status": "ok",
    "n_points": 8661,
    "depth": 0.004500513358542549,
    "sigma_boot": 0.004005456009150907,
    "z": 1.1235957524588036,
    "n_eclipse_nights": 9
   },
   {
    "name": "1SWASP J202227.26-215958.9",
    "status": "ok",
    "n_points": 8663,
    "depth": -0.001926616427830669,
    "sigma_boot": 0.004751401144614544,
    "z": -0.4054838497512222,
    "n_eclipse_nights": 9
   },
   {
    "name": "1SWASP J202154.71-220127.7",
    "status": "ok",
    "n_points": 8635,
    "depth": -0.006446978802735176,
    "sigma_boot": 0.001484273642441627,
    "z": -4.343524413820291,
    "n_eclipse_nights": 9
   },
   {
    "name": "1SWASP J202226.81-215939.2",
    "status": "ok",
    "n_points": 8632,
    "depth": 0.001754109461471273,
    "sigma_boot": 0.006209469745009494,
    "z": 0.2824894127040458,
    "n_eclipse_nights": 9
   },
   {
    "name": "1SWASP J202224.40-215920.3",
    "status": "ok",
    "n_points": 8545,
    "depth": 0.00239090094713,
    "sigma_boot": 0.006096763198826143,
    "z": 0.39215906361433533,
    "n_eclipse_nights": 9
   },
   {
    "name": "1SWASP J202154.46-220110.6",
    "status": "ok",
    "n_points": 8632,
    "depth": -0.008507912011579013,
    "sigma_boot": 0.0018884350236306185,
    "z": -4.505271245828777,
    "n_eclipse_nights": 9
   },
   {
    "name": "1SWASP J202222.71-220952.0",
    "status": "ok",
    "n_points": 8592,
    "depth": 0.0015480251454861652,
    "sigma_boot": 0.0021215803831075015,
    "z": 0.7296566077872365,
    "n_eclipse_nights": 9
   },
   {
    "name": "1SWASP J202150.34-220132.3",
    "status": "ok",
    "n_points": 8529,
    "depth": -0.011321852408620062,
    "sigma_boot": 0.0138598116024764,
    "z": -0.8168835719669617,
    "n_eclipse_nights": 9
   },
   {
    "name": "1SWASP J202149.39-220650.1",
    "status": "ok",
    "n_points": 8437,
    "depth": 0.011138124707733657,
    "sigma_boot": 0.020906755850969752,
    "z": 0.5327524168326201,
    "n_eclipse_nights": 9
   },
   {
    "name": "1SWASP J202225.33-215811.9",
    "status": "ok",
    "n_points": 8545,
    "depth": 0.003133543211136502,
    "sigma_boot": 0.002562208462900744,
    "z": 1.2229852709130993,
    "n_eclipse_nights": 9
   },
   {
    "name": "1SWASP J202150.36-220042.7",
    "status": "ok",
    "n_points": 8629,
    "depth": -0.0009022048369020472,
    "sigma_boot": 0.005211113251139105,
    "z": -0.17313092105699926,
    "n_eclipse_nights": 9
   },
   {
    "name": "1SWASP J202147.79-220743.2",
    "status": "ok",
    "n_points": 8661,
    "depth": 0.0005364806044011715,
    "sigma_boot": 0.0016677848889442633,
    "z": 0.3216725417993042,
    "n_eclipse_nights": 9
   }
  ],
  "median_comp_depth": 0.0010422528749436683
 },
 "C_wasp_wide_scan": {
  "chi2_red_after_free_detrend": 3.9033925070357167,
  "controls": {
   "max_snr": 33.939030667745044,
   "p95_snr": 20.191226530990047,
   "median_snr": 13.436949271158785
  },
  "best": {
   "snr": 65.91492855279046,
   "depth": 0.05460932200901228,
   "sigma": 0.0008284818508947688,
   "phase": 0.006000000000000005,
   "period": 2.3287799999999996
  },
  "top_peaks": [
   {
    "period": 2.3287799999999996,
    "snr": 65.91492855279046,
    "depth": 0.05460932200901228
   },
   {
    "period": 2.328575,
    "snr": 51.254467039040605,
    "depth": 0.043721451108081115
   },
   {
    "period": 2.32898,
    "snr": 49.666940043489575,
    "depth": 0.03851396143501698
   },
   {
    "period": 2.327895,
    "snr": 40.27140925965219,
    "depth": 0.043670678425741724
   },
   {
    "period": 2.32972,
    "snr": 40.14159669702753,
    "depth": 0.04664666262902359
   }
  ],
  "snr_at_candidates": {
   "wasp_to_tess_N2943": 26.154612484001472,
   "wasp_to_tess_N2944": 36.865720124285744,
   "wasp_to_tess_N2945": 65.83262269921245,
   "gaia": 56.56420770738498,
   "wasp_local": 39.59269736893962
  }
 },
 "A_fetch_status": {
  "version": "0.1.0",
  "client": "ok",
  "target": {
   "n_sources": 1,
   "picked": {
    "asas_sn_id": "498216376042",
    "ra_deg": "305.56117417",
    "dec_deg": "-22.07374906",
    "catalog_sources": "['stellar_main' 'tic']"
   },
   "columns": [
    "asas_sn_id",
    "jd",
    "flux",
    "flux_err",
    "mag",
    "mag_err",
    "limit",
    "fwhm",
    "image_id",
    "camera",
    "quality",
    "phot_filter"
   ],
   "n_rows": 2451,
   "status": "ok"
  },
  "neighbour": {
   "n_sources": 1,
   "picked": {
    "asas_sn_id": "506806230001",
    "ra_deg": "305.56650986",
    "dec_deg": "-22.082948000000002",
    "catalog_sources": "['stellar_main' 'tic']"
   },
   "columns": [
    "asas_sn_id",
    "jd",
    "flux",
    "flux_err",
    "mag",
    "mag_err",
    "limit",
    "fwhm",
    "image_id",
    "camera",
    "quality",
    "phot_filter"
   ],
   "n_rows": 2458,
   "status": "ok"
  }
 },
 "A_parse": {
  "target": {
   "columns": [
    "asas_sn_id",
    "jd",
    "flux",
    "flux_err",
    "mag",
    "mag_err",
    "limit",
    "fwhm",
    "image_id",
    "camera",
    "quality",
    "phot_filter"
   ],
   "time_col": "jd",
   "n_raw": 2451,
   "n_bad_quality": 345,
   "time_fix": null
  },
  "neighbour": {
   "columns": [
    "asas_sn_id",
    "jd",
    "flux",
    "flux_err",
    "mag",
    "mag_err",
    "limit",
    "fwhm",
    "image_id",
    "camera",
    "quality",
    "phot_filter"
   ],
   "time_col": "jd",
   "n_raw": 2458,
   "n_bad_quality": 342,
   "time_fix": null
  }
 },
 "A_asassn": {
  "status": "ok",
  "data": {
   "n_points": 1644,
   "n_nights": 837,
   "groups": [
    "bA|g",
    "bB|g",
    "bE|g",
    "bF|g",
    "ba|V",
    "bb|V",
    "be|V",
    "bf|V",
    "bi|g",
    "bj|g",
    "bm|g",
    "bn|g",
    "bq|g",
    "br|g"
   ],
   "t_first": 2456751.134243941,
   "t_last": 2460638.519527141,
   "chi2_red": 143.59114631234863
  },
  "controls": {
   "n": 300,
   "max_snr": 7.1357938608367455,
   "median_snr": 3.698807688876835,
   "p95_snr": 5.348479508575022
  },
  "injection": {
   "found_P": 2.600594,
   "snr": 5.302727615435491,
   "passed": false
  },
  "box": {
   "snr": 6.794273942171256,
   "depth": 0.0804742859494536,
   "sigma": 0.011844427621612254,
   "phase": 0.464,
   "period": 2.329208,
   "at_window_edge": false
  },
  "box_snr_at_candidates": {
   "wasp_to_tess_N2943": 3.367579229688744,
   "wasp_to_tess_N2944": 3.829078285577698,
   "wasp_to_tess_N2945": 6.5112006354570715,
   "gaia": 4.820106522500091,
   "wasp_local": 3.7412418548715567
  },
  "box_top_peaks": [
   {
    "period": 2.329208,
    "snr": 6.794273942171256,
    "depth": 0.0804742859494536
   },
   {
    "period": 2.328766,
    "snr": 6.5112006354570715,
    "depth": 0.054709396795715216
   },
   {
    "period": 2.328272,
    "snr": 6.379624214173419,
    "depth": 0.062051217028154186
   },
   {
    "period": 2.327468,
    "snr": 6.171388826475837,
    "depth": 0.0627166839438926
   },
   {
    "period": 2.327106,
    "snr": 5.562877204971418,
    "depth": 0.052714963777955336
   }
  ],
  "fit": {
   "coarse": {
    "period": 2.329198,
    "t0": 2458775.379484512,
    "depth": 0.08529121263068788,
    "sigma_white": 0.012821361578904011,
    "dchi2": 44.25275181456286,
    "edge": true
   },
   "fine": {
    "period": 2.329195,
    "t0": 2459371.654172512,
    "depth": 0.08555432899162456,
    "sigma_white": 0.012786598651459948,
    "dchi2": 44.768641046677,
    "edge": true
   }
  },
  "bootstrap": {
   "n": 150,
   "edge_fraction": 0.5266666666666666,
   "sigma_P": 1.7183990520240524e-05,
   "sigma_T0": 0.007246179310882158,
   "sigma_depth": 0.035615042621515075,
   "grid": [
    2e-05,
    1e-06,
    0.015,
    0.0005
   ],
   "unreliable": true
  },
  "ephemeris": {
   "P": 2.329195,
   "sigma_P": 1.7183990520240524e-05,
   "T0_bjd_tdb": 2459371.654172512,
   "sigma_T0": 0.007246179310882158
  },
  "primary": {
   "depth_mag": 0.08555432899162456,
   "sigma_boot": 0.035615042621515075,
   "snr_fit": 2.402196451112517,
   "n_eclipse_nights": 14
  },
  "odd_even": {
   "odd": 0.03821686896539075,
   "even": 0.12407135910926789
  },
  "secondary": {
   "depth_mag": -0.009875559777339253,
   "sigma_white": 0.008809302416262208
  },
  "label": "ASASSN_INSENSITIVE",
  "branch": {
   "label": "BRANCH_UNTESTABLE",
   "graded": false
  },
  "tess_link": {
   "cycles": 614.5366650229773,
   "N": 615,
   "frac": -0.4633349770226687,
   "sig_x": 0.005518105091089616,
   "label": "EPHEMERIS_INCONSISTENT",
   "P_comb": 2.327440207297876,
   "sig_P_comb": 1.1894074386036911e-05,
   "graded": false
  },
  "time_scale_check": {
   "dchi2_as_hjd": 44.768641046677,
   "dchi2_if_geocentric_jd": 46.008013383056884,
   "T0_shift_d": 0.003000000026077032,
   "P_if_jd": 2.329192,
   "tess_link_if_jd": "EPHEMERIS_INCONSISTENT"
  },
  "wasp_link": {
   "label": "WASP_LINK_UNTESTABLE",
   "graded": false
  },
  "blend": {
   "label": "BLEND_UNRESOLVED",
   "graded": false,
   "n_points": 1651,
   "depth_neighbour": -0.005922132263232951,
   "sigma_diff": 0.036170546396814024,
   "z": 2.529031777715001
  }
 }
}
```
