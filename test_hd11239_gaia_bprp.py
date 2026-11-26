# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Checks hd11239_gaia_bprp.py against the values computed by hand on 2026-11-26
(findings/2026-11-26-hd11239-gaia-bp-rp.md)."""
import unittest

import hd11239_gaia_bprp as h


class TestHD11239(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = h.load()
        cls.res = h.analyse(cls.rows)

    def test_conjunctions_from_orbit(self):
        # hand: M0 = 124.9174 deg -> Tc0 = 2191.5 - 0.788371 + 0.346993 P = 2191.79453
        self.assertAlmostEqual(h.T0, 2191.79453, delta=2e-4)
        # hand: M1 = 305.7177 deg -> second conjunction 0.50223 of an orbit later
        self.assertAlmostEqual(h.D1, 0.50223, delta=2e-4)
        # the TESS pre-registration used BTJD 389.2946 = Gaia 2191.7946
        self.assertAlmostEqual(h.T0 - 1802.5, 389.2946, delta=3e-4)

    def test_counts(self):
        r = self.res
        self.assertEqual(r["n_epochs"], 88)
        self.assertEqual(r["g_rejected"], [34, 35, 76])
        self.assertEqual(r["bp_rejected"], [41])
        self.assertEqual(r["rp_rejected"], [14, 41])
        self.assertEqual([x["index"] for x in r["in_window"]], [6, 7, 16, 37, 67])
        self.assertEqual(r["n_good_g"], 85)

    def test_hand_phases(self):
        hand = {6: -0.02649, 7: -0.00277, 16: 0.00978, 37: 0.02436, 67: 0.01585,
                69: 0.04144, 15: -0.04662, 62: -0.04770, 33: -0.05004, 8: 0.05362, 76: 0.07205}
        by = {r["index"]: r for r in self.rows}
        for i, v in hand.items():
            self.assertAlmostEqual(h.dphase(by[i]["t"]), v, delta=3e-4, msg=str(i))

    def test_medians(self):
        m = self.res["median"]
        self.assertAlmostEqual(m["g"], 9.5827, delta=1e-6)
        self.assertAlmostEqual(m["bp"], 9.87315, delta=1e-6)
        self.assertAlmostEqual(m["rp"], 9.1222, delta=1e-6)
        self.assertTrue(0.003 < self.res["robust_sd_g"] < 0.006)

    def test_dips_in_all_three_bands(self):
        r = self.res
        self.assertEqual(r["n_in_window_fainter_all_bands"], 5)
        d = {x["index"]: x for x in r["in_window"]}
        for i, g, bp, rp in ((7, 0.0856, 0.08695, 0.0847), (16, 0.0536, 0.05375, 0.0578),
                             (67, 0.0400, 0.03565, 0.0360)):
            self.assertAlmostEqual(d[i]["resid_g"], g, delta=2e-6)
            self.assertAlmostEqual(d[i]["resid_bp"], bp, delta=2e-6)
            self.assertAlmostEqual(d[i]["resid_rp"], rp, delta=2e-6)
        self.assertEqual(r["deep_indices"], [7, 16, 67])

    def test_colour_neutral(self):
        r = self.res
        for got, want in zip(r["bp_over_rp_deep"], (1.0266, 0.9299, 0.9903)):
            self.assertAlmostEqual(got, want, delta=5e-4)
        self.assertAlmostEqual(r["bp_over_rp_mean"], 0.9823, delta=5e-4)

    def test_faintest_and_out_of_window(self):
        r = self.res
        self.assertEqual(r["faintest3_g"], [7, 16, 67])
        self.assertAlmostEqual(r["p_faintest3_in_window"], 10 / 98770, delta=1e-9)
        self.assertEqual(r["max_out_of_window_index"], 65)
        self.assertAlmostEqual(r["max_out_of_window_resid_g"], 0.0099, delta=2e-6)

    def test_g_only_outlier_is_not_in_bp_rp(self):
        x = {y["index"]: y for y in self.res["g_rejected_resids"]}[76]
        self.assertAlmostEqual(x["resid_g"], 0.0242, delta=2e-6)
        # hand: BP +0.00605, RP +0.0055, against +0.0242 in G
        self.assertAlmostEqual(x["resid_bp"], 0.00605, delta=2e-6)
        self.assertAlmostEqual(x["resid_rp"], 0.0055, delta=2e-6)
        self.assertLess(x["resid_bp"], 0.3 * x["resid_g"])
        self.assertLess(x["resid_rp"], 0.3 * x["resid_g"])

    def test_main_runs(self):
        self.assertEqual(h.main(), 0)


if __name__ == "__main__":
    unittest.main()
