# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Tests for tyc6340_gaia_conj.py: the code must reproduce the hand calculation in
findings/2026-11-25-tyc6340-gaia-conjunction.md."""
import math
import unittest

import tyc6340_gaia_conj as t


class TestConj(unittest.TestCase):
    def test_self_test(self):
        self.assertTrue(t.self_test())

    def test_corr_unpack_symmetric(self):
        c = t.corr_matrix(t.ORBIT["corr_vec"])
        for i in range(6):
            self.assertEqual(c[i][i], 1.0)
            for j in range(6):
                self.assertEqual(c[i][j], c[j][i])
        self.assertAlmostEqual(c[0][1], -0.30027038)  # P - gamma, element 0
        self.assertAlmostEqual(c[0][2], 0.38529134)   # P - K, element 1
        self.assertAlmostEqual(c[1][2], -0.48674697)  # gamma - K, element 2
        self.assertAlmostEqual(c[3][5], 0.19881018)   # e - Tp
        self.assertAlmostEqual(c[0][5], 0.4354885)    # P - Tp

    def test_kepler_against_series(self):
        # hand: nu = 91.8867 deg, e = 0.04049 -> M = 87.2466 deg (series 87.250)
        nu = math.radians(91.88673313796323)
        m = math.degrees(t.mean_anomaly_from_true(nu, 0.04048587359818022))
        self.assertAlmostEqual(m, 87.2466, delta=0.002)

    def test_hand_values(self):
        tc, s, s_ind, grad = t.propagate()
        # hand: Tc = 2457389.0 - 0.5700116 + 0.242352 * 2.3289298 = 2457388.994408
        self.assertAlmostEqual(tc, 2457388.994408, delta=5e-5)
        # hand: scaled gradients e -0.0231, omega -0.2960, Tp +0.2936 d; sigma 0.0281 d
        self.assertAlmostEqual(grad["e"], -0.0231, delta=0.0005)
        self.assertAlmostEqual(grad["omega"], -0.2960, delta=0.0005)
        self.assertAlmostEqual(grad["Tp"], 0.29357, delta=1e-4)
        self.assertAlmostEqual(s, 0.0281, delta=0.0015)
        self.assertGreater(s_ind, 0.40)  # without correlations the window would be ~0.42 d
        r = t.compare(tc, s)
        self.assertEqual(r["n_cycles"], 1472)
        # hand: 2460817.00291 - (2457388.994408 + 1472 * 2.3287747) = +0.05214 d
        self.assertAlmostEqual(r["offset_d"], 0.05214, delta=5e-4)
        self.assertAlmostEqual(r["z"], 1.85, delta=0.12)
        self.assertGreater(abs(r["other_conjunction_z"]), 30.0)

    def test_main_runs(self):
        self.assertEqual(t.main(), 0)


if __name__ == "__main__":
    unittest.main()
