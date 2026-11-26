# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Tests for tyc1316_asas3.py: every number quoted in findings/2026-11-26-tyc1316-asas3.md was
computed by hand first; these tests check the code reproduces them."""
import unittest

import tyc1316_asas3 as t

# hand-computed signed phase from Gaia's conjunction 0 and cycle, per faint point (HJD - 2450000)
HAND = {
    3387.55699: (0.13672, -2461), 3730.64245: (0.09950, -2250), 3831.48468: (0.10725, -2188),
    4517.56332: (-0.02394, -1766), 4782.78164: (0.05844, -1603), 4852.71489: (0.06030, -1560),
}
IN0 = {4517.56332, 4782.78164, 4852.71489}


class TestASAS3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = t.analyse(t.load())

    def test_ephemeris(self):
        self.assertAlmostEqual(t.T0, 2192.12038, delta=2e-4)
        self.assertAlmostEqual(t.D1, 0.45582, delta=2e-4)
        self.assertAlmostEqual(self.res["t_conj0_hjd"], 7389.62038, delta=2e-4)

    def test_baseline_and_threshold(self):
        r = self.res
        self.assertEqual(r["n_ab"], 332)
        self.assertEqual(r["n_dropped_bad"], 0)
        self.assertAlmostEqual(r["baseline_mag2"], 10.686, delta=1e-9)
        self.assertAlmostEqual(r["mad"], 0.024, delta=1e-9)
        self.assertAlmostEqual(r["faint_threshold"], 10.7927472, delta=1e-6)

    def test_faint_points(self):
        r = self.res
        self.assertEqual(r["n_faint"], 6)
        self.assertEqual(sorted(round(f["hjd"], 5) for f in r["faint"]), sorted(HAND))
        for f in r["faint"]:
            key = round(f["hjd"], 5)
            self.assertAlmostEqual(f["phi"], HAND[key][0], delta=0.0005, msg=str(key))
            self.assertEqual(f["cycle"], HAND[key][1], msg=str(key))
            self.assertEqual(f["window"], 0 if key in IN0 else None, msg=str(key))

    def test_grade_fails(self):
        r = self.res
        self.assertEqual(r["n_faint_in_windows"], 3)
        self.assertEqual(r["n_in_conj0"], 3)
        self.assertEqual(r["n_in_conj1"], 0)
        self.assertTrue(0.2930 < r["p_binomial"] < 0.2941, r["p_binomial"])
        self.assertFalse(r["passed"])

    def test_period_corrections(self):
        d_p = self.res["period_correction_conj0_d"]
        self.assertTrue(-2.95e-5 < d_p < -2.88e-5, d_p)
        self.assertTrue(-2.09 < self.res["period_correction_conj0_sigma"] < -2.03)
        d_all = t.posthoc_all_faint_fit(self.res)
        self.assertTrue(-6.40e-5 < d_all < -6.33e-5, d_all)

    def test_span(self):
        lo, hi = self.res["orbits_before_gaia_conj0"]
        self.assertTrue(2931.5 < lo < 2932.0, lo)
        self.assertTrue(1367.2 < hi < 1367.7, hi)
        s_lo, s_hi = self.res["phase_sigma_from_period"]
        self.assertTrue(0.0253 < s_lo < 0.0257, s_lo)
        self.assertTrue(0.0118 < s_hi < 0.0120, s_hi)

    def test_main_exit_code(self):
        self.assertEqual(t.main(), 0)


if __name__ == "__main__":
    unittest.main()
