# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Checks hd171459_gaia_conj.py against the values computed by hand on
2026-11-25 (findings/2026-11-25-hd171459-gaia-conjunction-eclipses.md)."""
import unittest

import hd171459_gaia_conj as h


class TestHD171459(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = h.load()
        cls.res = h.analyse(cls.rows)

    def test_counts(self):
        r = self.res
        self.assertEqual(r["n_epochs"], 98)
        self.assertEqual(r["rejected_indices"], [33, 40])
        self.assertEqual(r["n_out_of_window"], 78)
        self.assertEqual(r["n_in_window"], 18)
        self.assertEqual(r["n_null_window"], 14)

    def test_hand_phases(self):
        self.assertLess(self.res["max_abs_phase_hand_error"], 3e-4)
        for row in self.rows:
            if row["reject"]:
                continue
            self.assertAlmostEqual(h.dphase(h.phase(row["t"])), row["dphase_hand"], delta=3e-4)

    def test_baseline(self):
        self.assertAlmostEqual(self.res["baseline_g_median"], 8.2761495, delta=2e-6)
        self.assertTrue(0.003 < self.res["robust_sd_g"] < 0.006)

    def test_in_window_all_fainter(self):
        r = self.res
        self.assertEqual(r["n_in_window_fainter"], 18)
        self.assertAlmostEqual(r["mean_resid_in_window"], 0.0115738, delta=2e-5)
        self.assertAlmostEqual(r["p_all_in_window_fainter_sign_test"], 0.5 ** 18)

    def test_null_quadrature(self):
        r = self.res
        self.assertEqual(r["n_null_window_fainter"], 1)
        self.assertAlmostEqual(r["mean_resid_null_window"], -0.0038381, delta=2e-5)

    def test_deepest_at_conjunction(self):
        d = self.res["deepest4"]
        self.assertEqual(sorted(x["index"] for x in d), [1, 25, 31, 67])
        self.assertEqual(self.res["deepest4_distinct_conjunction_passages"], 4)
        for x in d:
            self.assertLess(abs(x["dphase"]), 0.0065)
            self.assertTrue(0.020 < x["resid_g"] < 0.027)

    def test_colours_dim_together(self):
        self.assertTrue(0.006 < self.res["mean_resid_bp_in_window"] < 0.016)
        self.assertTrue(0.006 < self.res["mean_resid_rp_in_window"] < 0.016)


if __name__ == "__main__":
    unittest.main()
