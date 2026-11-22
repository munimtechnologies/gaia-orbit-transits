# pixel_which_star 0.1.0 report

- Controls: **CONTROLS_FAIL**
- Graded: **False**

## TIC 93622019 (target)
- status: ok
- WS: **WS_UNRESOLVED**; offset 0.47 arcsec, sigma 2.23 arcsec, d_target 0.21 sigma, capable stars within 3 sigma: ['5345417757181557248']
- L1 counts {'PIX_ON_TARGET': 2}; DEPTH DEPTH_DEEPER (0.01284 +- 0.00014); SEC SEC_NOT_DETECTED; OE OE_CONSISTENT; EB EB_NOT_INDICATED
- ephemeris: {"P": 2.123893332667055, "sigma_P": 3.044815104421753e-06, "T0": 3706.0868496452117, "sigma_T0": 0.0006764471524484674, "n_ref": 1005, "chi2_red": 1.3907332500147476, "status": "REFINED", "n_epochs": 5}
  - sector 10: NEGATIVE_FLUX sensitive None L1 None L2 None offset null
  - sector 37: NEGATIVE_FLUX sensitive None L1 None L2 None offset null
  - sector 64: OK sensitive True L1 PIX_ON_TARGET L2 CENTROID_ON_TARGET offset {"east": 0.7825017147256778, "north": -1.1409656622760167, "sigma": 3.1491950969731186, "offset_target_px": 0.06615617057709283, "d_target_sigma_px": 0.4351229225107688, "d_neighbour_sigma_px": 13.182504647022908}
  - sector 90: NEGATIVE_FLUX sensitive None L1 None L2 None offset null
  - sector 99: OK sensitive True L1 PIX_ON_TARGET L2 CENTROID_ON_TARGET offset {"east": -1.7321720565187833, "north": 1.3321089698450805, "sigma": 3.172277063895181, "offset_target_px": 0.10449695713192902, "d_target_sigma_px": 0.6904193793014362, "d_neighbour_sigma_px": 12.092001924002902}
  - sector 100: NEGATIVE_FLUX sensitive None L1 None L2 None offset null

## HATS-67 b (control)
- status: ok
- WS: **WS_ON_TARGET**; offset 1.06 arcsec, sigma 1.79 arcsec, d_target 0.59 sigma, capable stars within 3 sigma: []
- L1 counts {'PIX_ON_TARGET': 3}; DEPTH DEPTH_CONSISTENT (0.01160 +- 0.00017); SEC SEC_NOT_DETECTED; OE OE_CONSISTENT; EB EB_NOT_INDICATED
- ephemeris: {"P": 1.6091788, "T0": 796.89126999978, "sigma_T0": 0.0005, "status": "SHIFTED", "n_epochs": 1}
  - sector 99: OK sensitive True L1 PIX_ON_TARGET L2 CENTROID_ON_TARGET offset {"east": -1.6440588621969832, "north": -0.8913135466428912, "sigma": 3.1289990312913756, "offset_target_px": 0.09216723044374572, "d_target_sigma_px": 0.6091348756151053, "d_neighbour_sigma_px": 18.99885239790279}
  - sector 100: OK sensitive True L1 PIX_ON_TARGET L2 CENTROID_ON_TARGET offset {"east": -1.1204865735586498, "north": 0.5997942053937777, "sigma": 3.1679309169240693, "offset_target_px": 0.06183936569821025, "d_target_sigma_px": 0.4046822344438271, "d_neighbour_sigma_px": 18.156600658210746}
  - sector 101: OK sensitive True L1 PIX_ON_TARGET L2 CENTROID_ON_TARGET offset {"east": -0.1974911279280876, "north": -0.9211510238998244, "sigma": 3.0193622423321202, "offset_target_px": 0.04642258325565999, "d_target_sigma_px": 0.3067358991556775, "d_neighbour_sigma_px": 19.3846850953644}

## HATS-58 A b (control)
- status: ok
- WS: **WS_UNTESTABLE**; offset None arcsec, sigma None arcsec, d_target None sigma, capable stars within 3 sigma: None
- L1 counts {}; DEPTH DEPTH_UNTESTABLE (nan +- nan); SEC SEC_UNTESTABLE; OE OE_UNTESTABLE; EB EB_NOT_INDICATED
- ephemeris: {"P": 4.218131266666697, "sigma_P": 0.0001717960677340692, "T0": 4065.5379600666497, "sigma_T0": 0.000487695829613317, "n_ref": 854, "chi2_red": 1.0, "status": "REFINED", "n_epochs": 2}
  - sector 99: UNTESTABLE sensitive None L1 None L2 None offset null
  - sector 100: NEGATIVE_FLUX sensitive None L1 None L2 None offset null
  - sector 101: NEGATIVE_FLUX sensitive None L1 None L2 None offset null

