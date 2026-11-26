# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Tests for hd11239_asas3.py: every number quoted in findings/2026-11-26-hd11239-asas3.md
was computed by hand first; these tests check the code reproduces them."""
import unittest

import hd11239_asas3 as h

# hand-computed signed phase from the nearer Gaia conjunction, for each faint point
HAND = {
    2194.67877: -0.00231, 2219.61281: -0.01274, 2255.55481: +0.00631, 2495.81275: -0.00833,
    2645.63241: -0.00193, 2659.64035: -0.01562, 2996.69688: -0.01329, 3007.63323: -0.00675,
    3068.51741: +0.00002, 3394.62986: -0.00221, 3438.50873: +0.05781, 3631.76812: -0.01648,
    3745.59900: -0.04412, 4280.94085: -0.00340, 4455.69741: -0.00651, 4516.55546: -0.00812,
    4628.92404: -0.00209, 4648.89559: -0.10041, 4722.79683: +0.07738, 4767.62534: -0.05608,
    4814.60459: -0.00262, 4828.57157: -0.02944,
}


class TestASAS3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = h.analyse(h.load())

    def test_ephemeris(self):
        self.assertAlmostEqual(h.T0, 2191.79453, delta=2e-4)
        self.assertAlmostEqual(h.D1, 0.50223, delta=2e-4)
        self.assertAlmostEqual(self.res["t_conj0_hjd"], 7389.29453, delta=2e-4)

    def test_baseline_and_faint(self):
        r = self.res
        self.assertEqual(r["n_good"], 537)
        self.assertAlmostEqual(r["baseline_mag3"], 9.727, places=6)
        self.assertEqual(r["n_faint"], 22)
        self.assertEqual(sorted(round(f["hjd"], 5) for f in r["faint"]), sorted(HAND))

    def test_phases_match_hand(self):
        for f in self.res["faint"]:
            self.assertAlmostEqual(f["dphase"], HAND[round(f["hjd"], 5)], delta=0.0005,
                                   msg=str(f["hjd"]))

    def test_A1_A2(self):
        r = self.res
        self.assertEqual(r["n_faint_in_window"], 20)
        self.assertEqual(r["n_in_window_conj0"], 11)
        self.assertEqual(r["n_in_window_conj1"], 9)
        self.assertEqual(r["n_nights_in_window"], 20)
        self.assertTrue(r["A1"])
        self.assertTrue(r["A2"])
        self.assertTrue(5.0e-11 < r["p_binomial"] < 6.0e-11, r["p_binomial"])

    def test_robustness(self):
        r = self.res
        self.assertEqual(r["robust_n_faint"], 17)
        self.assertEqual(r["robust_n_in_window"], 17)
        self.assertAlmostEqual(r["robust_median_dphase"], -0.00675, delta=0.0005)

    def test_span(self):
        lo, hi = self.res["orbits_before_gaia_conj0"]
        self.assertTrue(1768.5 < lo < 1769.5, lo)
        self.assertTrue(714.3 < hi < 715.3, hi)
        s_lo, s_hi = self.res["phase_sigma_from_period"]
        self.assertTrue(0.0215 < s_lo < 0.0230, s_lo)
        self.assertTrue(0.0085 < s_hi < 0.0095, s_hi)

    def test_main_exit_code(self):
        self.assertEqual(h.main(), 0)


if __name__ == "__main__":
    unittest.main()
