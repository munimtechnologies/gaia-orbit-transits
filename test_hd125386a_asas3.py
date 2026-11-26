# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Tests for hd125386a_asas3.py: every number quoted in findings/2026-11-26-hd125386a-asas3.md
was computed by hand first; these tests check the code reproduces them."""
import unittest

import hd125386a_asas3 as h

# hand-computed signed phase from Gaia's conjunction 0, for each faint point (HJD - 2450000)
HAND = {
    2456.50467: -0.01047, 2500.50346: -0.03285, 2643.82087: -0.01811, 2860.56629: -0.01435,
    3098.74797: -0.17508, 3111.64593: +0.33609, 3128.66007: -0.03222, 3510.79218: -0.00588,
    3521.77336: -0.01652, 3630.49038: -0.42091, 3745.82593: -0.02356, 3848.69638: -0.01954,
    4127.85471: -0.02535, 4557.68792: -0.01353, 4568.73481: -0.00627, 4590.77047: -0.00759,
    4671.61063: -0.00079, 4682.61763: -0.00440, 4836.83801: -0.02158, 4909.72929: -0.17867,
    5009.56640: -0.00041, 5031.57202: -0.00990,
}
OUT = {3098.74797, 3111.64593, 3630.49038, 4909.72929}


class TestASAS3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = h.analyse(h.load())

    def test_ephemeris(self):
        self.assertAlmostEqual(h.T0, 2192.44204, delta=2e-4)
        self.assertAlmostEqual(h.D1, 0.50523, delta=2e-4)
        self.assertAlmostEqual(self.res["t_conj0_hjd"], 7389.94204, delta=2e-4)

    def test_baseline_and_faint(self):
        r = self.res
        self.assertEqual(r["n_ab"], 526)
        self.assertEqual(r["n_dropped_bad"], 0)
        self.assertAlmostEqual(r["baseline_mag3"], 9.0985, delta=1e-9)
        self.assertEqual(r["n_faint"], 22)
        self.assertEqual(sorted(round(f["hjd"], 5) for f in r["faint"]), sorted(HAND))

    def test_phases_match_hand(self):
        for f in self.res["faint"]:
            key = round(f["hjd"], 5)
            self.assertAlmostEqual(f["phi"], HAND[key], delta=0.0005, msg=str(key))
            self.assertEqual(f["in_window"], key not in OUT, msg=str(key))

    def test_pass(self):
        r = self.res
        self.assertEqual(r["n_faint_in_window"], 18)
        self.assertEqual(r["n_nights_in_window"], 18)
        self.assertTrue(1.7e-8 < r["p_binomial"] < 2.0e-8, r["p_binomial"])
        self.assertTrue(r["passed"])
        self.assertTrue(r["max_abs_phi_in_window"] < 0.034, r["max_abs_phi_in_window"])
        self.assertAlmostEqual(r["median_phi_in_window"], -0.01394, delta=0.0005)
        self.assertEqual(r["n_faint_within_0.1_of_phase_0.5"], 1)

    def test_period_correction(self):
        d_p = self.res["period_correction_d"]
        self.assertTrue(5.6e-5 < d_p < 6.0e-5, d_p)
        self.assertTrue(0.32 < self.res["period_correction_sigma"] < 0.36)

    def test_span(self):
        lo, hi = self.res["orbits_before_gaia_conj0"]
        self.assertTrue(1491.9 < lo < 1492.9, lo)
        self.assertTrue(626.0 < hi < 627.0, hi)
        s_lo, s_hi = self.res["phase_sigma_from_period"]
        self.assertTrue(0.0679 < s_lo < 0.0688, s_lo)
        self.assertTrue(0.0284 < s_hi < 0.0290, s_hi)

    def test_main_exit_code(self):
        self.assertEqual(h.main(), 0)


if __name__ == "__main__":
    unittest.main()
