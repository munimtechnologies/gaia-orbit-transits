# SPDX-License-Identifier: Apache-2.0
"""Tests for tic93622019_gaia_rv 0.1.0 (MV2 of Munim, Inc.; made with AI agents). No network.
Expected values were worked out by hand on 24 Nov 2026 before the code was run."""
import math
import unittest

import tic93622019_gaia_rv as rv


class TestStats(unittest.TestCase):
    def test_norm_ppf(self):
        self.assertAlmostEqual(rv.norm_ppf(0.975), 1.959964, places=5)
        self.assertAlmostEqual(rv.norm_ppf(0.01), -2.326348, places=5)
        self.assertAlmostEqual(rv.norm_ppf(0.5), 0.0, places=9)

    def test_chi2_ppf(self):
        self.assertAlmostEqual(rv.chi2_ppf(0.05, 26), 15.379, delta=0.03)
        self.assertAlmostEqual(rv.chi2_ppf(0.95, 26), 38.885, delta=0.06)

    def test_epoch_sigma(self):
        # sigma^2 = (2N/pi) (err^2 - 0.11^2) = (54/pi) * 2.82504
        self.assertAlmostEqual(rv.epoch_sigma(1.6843823, 27), 6.968, delta=0.01)
        self.assertEqual(rv.epoch_sigma(0.10, 27), 0.0)

    def test_sigma_upper_larger(self):
        s = rv.epoch_sigma(1.6843823, 27)
        self.assertAlmostEqual(rv.sigma_upper(s, 27), 9.06, delta=0.03)


class TestOrbit(unittest.TestCase):
    def test_k_jupiter_one_year(self):
        # textbook: 28.43 m/s for 1 Jupiter mass, 1 yr, 1 solar mass, edge-on
        self.assertAlmostEqual(rv.k_of_m2(1.0, p_days=365.25, mstar=1.0), 28.43, delta=0.05)

    def test_k_per_mjup_here(self):
        self.assertAlmostEqual(rv.k_of_m2(1.0), 130.67, delta=0.3)

    def test_roundtrip(self):
        for m in (0.5, 50.0, 300.0):
            self.assertAlmostEqual(rv.m2_of_k(rv.k_of_m2(m)), m, delta=1e-6 * max(1.0, m))

    def test_geometry(self):
        self.assertAlmostEqual(rv.semi_major_axis_rsun(), 7.647, delta=0.01)
        self.assertAlmostEqual(rv.sini_min(), 0.9802, delta=0.001)


class TestResult(unittest.TestCase):
    def setUp(self):
        self.r = rv.run()

    def test_flags(self):
        self.assertTrue(self.r["valid_epoch_stats"])
        self.assertFalse(self.r["rv_variable_by_katz2023"])

    def test_limits(self):
        r = self.r
        self.assertAlmostEqual(r["K_all_scatter_kms"], 9.855, delta=0.02)
        self.assertAlmostEqual(r["K_95_kms"], 12.81, delta=0.04)
        self.assertAlmostEqual(r["m2_max_all_scatter_mjup"], 79.9, delta=0.7)
        self.assertAlmostEqual(r["m2_max_95_mjup"], 105.0, delta=0.8)
        self.assertAlmostEqual(r["m2_max_95_msun"], 0.1002, delta=0.001)
        self.assertAlmostEqual(r["rp_rjup"], 1.497, delta=0.005)

    def test_stellar_companions_excluded(self):
        r = self.r
        self.assertAlmostEqual(r["K_equal_mass_twin_kms"], 114.7, delta=0.6)
        self.assertAlmostEqual(r["K_0p3msun_kms"], 35.9, delta=0.3)
        self.assertGreater(r["K_0p3msun_kms"], 2.5 * r["K_95_kms"])

    def test_finite(self):
        for k, v in self.r.items():
            if isinstance(v, float):
                self.assertTrue(math.isfinite(v), k)


if __name__ == "__main__":
    unittest.main()
