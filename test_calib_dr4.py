# SPDX-License-Identifier: Apache-2.0
"""Tests for calib_dr4.py (MV2 of Munim, Inc.; made with AI agents). Stdlib only."""
import math
import unittest

import calib_dr4 as cd


class TestLabels(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(cd.label_orbit(100.0, 1.0, 101.0, 1.0), "CONFIRMED")
        self.assertEqual(cd.label_orbit(100.0, 0.0, 100.4, 0.0), "CONFIRMED")   # 0.5% rule
        self.assertEqual(cd.label_orbit(100.0, 0.0, 101.0, 0.0), "CHANGED")
        self.assertEqual(cd.label_orbit(100.0, 0.1, 200.2, 0.1), "ALIAS")
        self.assertEqual(cd.label_orbit(90.0, 0.1, 30.05, 0.05), "ALIAS")
        self.assertEqual(cd.label_orbit(100.0, 1.0, None, None), "DROPPED")
        self.assertEqual(cd.label_orbit(100.0, 1.0, 100.0, 1.0, matched=False), "UNTESTABLE")
        self.assertEqual(cd.label_orbit(None, 1.0, 100.0, 1.0), "UNTESTABLE")
        self.assertEqual(cd.label_orbit(100.0, None, float("nan"), None), "DROPPED")


class TestIntervals(unittest.TestCase):
    def test_wilson(self):
        lo, hi = cd.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)
        self.assertEqual(cd.wilson(0, 0), (0.0, 1.0))
        lo, hi = cd.wilson(0, 20)
        self.assertAlmostEqual(lo, 0.0, places=9)
        self.assertTrue(0.1 < hi < 0.2)

    def test_newcombe_example(self):
        # Newcombe (1998) example: 56/70 vs 48/80 -> 0.0524 to 0.3339
        d, lo, hi = cd.newcombe_diff(56, 70, 48, 80)
        self.assertAlmostEqual(d, 0.2, places=9)
        self.assertAlmostEqual(lo, 0.0524, places=3)
        self.assertAlmostEqual(hi, 0.3339, places=3)
        d, lo, hi = cd.newcombe_diff(1, 0, 1, 5)
        self.assertTrue(math.isnan(d))


def _rows(n_e, fail_e, n_n, fail_n, conf_n_off=0.0, conf_e_off=0.0, z=1.0):
    rows = []
    for i in range(n_e):
        lab = "CHANGED" if i < fail_e else "CONFIRMED"
        off = (i - fail_e) < conf_e_off * (n_e - fail_e)
        rows.append({"group": "E", "label": lab, "cosi4": 0.05 if off else 0.001,
                     "cosi4_sd": 0.005, "lim4": 0.01, "z4": z if i % 2 == 0 else -z})
    for i in range(n_n):
        lab = "DROPPED" if i < fail_n else "CONFIRMED"
        off = (i - fail_n) < conf_n_off * (n_n - fail_n)
        rows.append({"group": "N", "label": lab, "cosi4": 0.05 if off else 0.001,
                     "cosi4_sd": 0.005, "lim4": 0.01, "z4": None})
    rows.append({"group": "N", "label": "UNTESTABLE"})
    return rows


class TestGrade(unittest.TestCase):
    def test_wrong_orbits_reading(self):
        g = cd.grade(_rows(58, 5, 104, 45))
        self.assertTrue(g["K1"]["pass"])
        self.assertFalse(g["K2"]["pass"])
        self.assertTrue(g["K3"]["pass"])
        self.assertTrue(g["K4"]["pass"])
        self.assertTrue(g["K6"]["pass"])
        self.assertTrue(g["reading"].startswith("F"))
        self.assertEqual(g["counts"]["untestable"], 1)
        self.assertEqual(g["counts"]["N_testable"], 104)

    def test_error_reading(self):
        g = cd.grade(_rows(58, 3, 104, 6, conf_n_off=0.7, conf_e_off=0.05, z=2.0))
        self.assertFalse(g["K1"]["pass"])
        self.assertTrue(g["K2"]["pass"])
        self.assertTrue(g["K5"]["pass"])
        self.assertFalse(g["K4"]["pass"])          # rms z = 2: DR4 timing still too small
        self.assertTrue(g["reading"].startswith("K"))

    def test_undecided(self):
        g = cd.grade(_rows(10, 1, 10, 2))
        self.assertFalse(g["K1"]["pass"])
        self.assertFalse(g["K2"]["pass"])
        self.assertTrue(g["reading"].startswith("UNDECIDED"))


if __name__ == "__main__":
    unittest.main()
