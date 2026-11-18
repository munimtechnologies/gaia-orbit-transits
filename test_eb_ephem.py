# SPDX-License-Identifier: Apache-2.0
"""Tests for eb_ephem (pure Python). Expected values worked by hand."""
import math
import unittest

import eb_ephem as ee


class TestShapes(unittest.TestCase):
    def test_trapezoid(self):
        # t14 = 2 -> half = 1; fin = 0.5 -> ingress 0.5
        self.assertEqual(ee.trapezoid_shape(0.0, 2.0, 0.5), 1.0)
        self.assertEqual(ee.trapezoid_shape(0.5, 2.0, 0.5), 1.0)
        self.assertAlmostEqual(ee.trapezoid_shape(0.75, 2.0, 0.5), 0.5)
        self.assertAlmostEqual(ee.trapezoid_shape(-0.75, 2.0, 0.5), 0.5)
        self.assertEqual(ee.trapezoid_shape(1.0, 2.0, 0.5), 0.0)
        self.assertEqual(ee.trapezoid_shape(1.5, 2.0, 0.5), 0.0)

    def test_v_shape(self):
        self.assertAlmostEqual(ee.trapezoid_shape(0.5, 2.0, 1.0), 0.5)
        self.assertEqual(ee.trapezoid_shape(0.0, 2.0, 1.0), 1.0)

    def test_phase(self):
        self.assertAlmostEqual(ee.phase_of(10.0 + 1.5 * 4.0, 10.0, 4.0), 0.5)
        self.assertAlmostEqual(ee.phase_of(10.0 - 1.0, 10.0, 4.0), 0.75)

    def test_predicted_times(self):
        self.assertEqual(ee.predicted_times(10.0, 4.0, 11.0, 23.0),
                         [(1, 14.0), (2, 18.0), (3, 22.0)])
        self.assertEqual(ee.predicted_times(10.0, 4.0, 2.0, 6.0), [(-2, 2.0), (-1, 6.0)])


class TestLinear(unittest.TestCase):
    def test_exact(self):
        r = ee.fit_linear([100.0, 126.5, 179.5], [0.01, 0.01, 0.01], 26.4)
        self.assertEqual(r["n"], [0, 1, 3])
        self.assertAlmostEqual(r["p"], 26.5, places=9)
        self.assertAlmostEqual(r["t0"], 100.0, places=9)
        self.assertAlmostEqual(r["rms"], 0.0, places=9)

    def test_noisy_equal_weights(self):
        # n = 0,1,2; t = 0, 10.5, 20 -> P = 10, T0 = 1/6, resid = -1/6, 1/3, -1/6
        r = ee.fit_linear([0.0, 10.5, 20.0], [1.0, 1.0, 1.0], 10.0)
        self.assertAlmostEqual(r["p"], 10.0, places=12)
        self.assertAlmostEqual(r["t0"], 1.0 / 6.0, places=12)
        for got, want in zip(r["resid"], [-1.0 / 6.0, 1.0 / 3.0, -1.0 / 6.0]):
            self.assertAlmostEqual(got, want, places=12)
        # X^T X = [[3, 3], [3, 5]], det 6 -> var(P) = 3/6, var(T0) = 5/6
        self.assertAlmostEqual(r["sig_p"], math.sqrt(0.5), places=12)
        self.assertAlmostEqual(r["sig_t0"], math.sqrt(5.0 / 6.0), places=12)
        self.assertAlmostEqual(r["chi2"], 1.0 / 6.0, places=12)
        self.assertAlmostEqual(r["rms"], math.sqrt((1 / 36 + 1 / 9 + 1 / 36) / 3), places=12)

    def test_weights(self):
        # the third point has a huge error and is ignored
        r = ee.fit_linear([0.0, 10.0, 31.0], [0.001, 0.001, 1000.0], 10.0)
        self.assertEqual(r["n"], [0, 1, 3])
        self.assertAlmostEqual(r["p"], 10.0, places=6)
        self.assertAlmostEqual(r["t0"], 0.0, places=6)

    def test_one_cycle_rejected(self):
        with self.assertRaises(ValueError):
            ee.fit_linear([0.0, 0.1], [1.0, 1.0], 10.0)


class TestCriteria(unittest.TestCase):
    def test_all_pass(self):
        c = ee.vsx_criteria([0.10, 0.10, 0.11, 0.09, 0.09], 0.01, 26.533, 26.5369, 0.0034, 0.021)
        self.assertTrue(c["E1"] and c["E2"] and c["E3"] and c["E4"] and c["all"])
        self.assertEqual(c["n_deep"], 5)
        self.assertAlmostEqual(c["rms_oc_min"], 14.4)

    def test_failures(self):
        c = ee.vsx_criteria([0.10, 0.10, 0.10], 0.03, 26.533, 26.5369, 0.0034, 0.021)
        self.assertFalse(c["E1"])          # only three eclipses
        self.assertFalse(c["E2"])          # 43.2 min rms
        self.assertTrue(c["E3"])
        self.assertTrue(c["E4"])
        self.assertFalse(c["all"])

    def test_period_and_blend(self):
        c = ee.vsx_criteria([0.06, 0.06, 0.06, 0.06], 0.001, 26.6, 26.5, 0.01, 0.03)
        self.assertFalse(c["E2"])          # 10 sigma from the Gaia period
        self.assertFalse(c["E4"])          # 0.06 < 3 x 0.03
        self.assertTrue(c["E1"])

    def test_spread(self):
        c = ee.vsx_criteria([0.06, 0.10, 0.10, 0.10], 0.001, 26.5, 26.5, 0.01, 0.0)
        self.assertFalse(c["E3"])          # (0.10 - 0.06) / 0.10 = 0.4

    def test_median(self):
        self.assertEqual(ee.median([3.0, 1.0, 2.0]), 2.0)
        self.assertEqual(ee.median([4.0, 1.0, 2.0, 3.0]), 2.5)


if __name__ == "__main__":
    unittest.main()
