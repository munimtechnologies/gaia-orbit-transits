# SPDX-License-Identifier: Apache-2.0
"""Tests for hd125386a_model.py (MV2 of Munim, Inc.; made with AI agents).

Expected values were computed by hand before the code was run; tolerances are generous
enough for rounding but tight enough to catch a wrong formula."""
import math
import unittest

import hd125386a_model as hm


class TestPieces(unittest.TestCase):
    def test_mass_function_known_case(self):
        # P = 1 d, K = 100 km/s, e = 0 -> 1.0361e-7 * 1e6 = 0.10361
        self.assertAlmostEqual(hm.mass_function(1.0, 100.0, 0.0), 0.10361, places=6)

    def test_companion_mass_inverts(self):
        for m1 in (0.5, 1.0, 2.0):
            for m2 in (0.1, 0.7, 3.0):
                fm = m2 ** 3 / (m1 + m2) ** 2
                self.assertAlmostEqual(hm.companion_mass(fm, m1), m2, places=6)

    def test_kepler_earth(self):
        self.assertAlmostEqual(hm.separation_rsun(1.0, 365.25), hm.AU_RSUN, places=6)

    def test_planck_ratio_equal_temps(self):
        self.assertAlmostEqual(hm.planck_ratio(5000.0, 5000.0, 600e-9), 1.0, places=12)
        self.assertLess(hm.planck_ratio(4000.0, 9000.0, 600e-9), 1.0)


class TestModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = hm.model()

    def test_mass_function(self):
        self.assertAlmostEqual(self.m["mass_function"], 0.04334, delta=2e-4)
        self.assertAlmostEqual(self.m["mass_function_err"], 0.00299, delta=1e-4)

    def test_scenarios(self):
        expect = {
            "low": (0.6146, 13.253, 80.23, 0.1995, 0.1958, 22.04),
            "mid": (0.6568, 13.700, 79.70, 0.2102, 0.1517, 24.79),
            "high": (0.6974, 14.117, 79.18, 0.2208, 0.1212, 27.54),
        }
        for row in self.m["scenarios"]:
            m2, a, imin, t, d, v = expect[row["name"]]
            self.assertAlmostEqual(row["m2_i90"], m2, delta=0.003, msg=row["name"])
            self.assertAlmostEqual(row["a_rsun"], a, delta=0.05, msg=row["name"])
            self.assertAlmostEqual(row["i_min_deg"], imin, delta=0.15, msg=row["name"])
            self.assertAlmostEqual(row["t_central_d"], t, delta=0.003, msg=row["name"])
            self.assertAlmostEqual(row["primary_depth_mag_central_noLD"], d, delta=0.002,
                                   msg=row["name"])
            self.assertAlmostEqual(row["v_sync_kms"], v, delta=0.1, msg=row["name"])
            ratio = row["m2_at_i_min"] / row["m2_i90"]
            self.assertTrue(1.0 < ratio < 1.03, msg=row["name"])

    def test_light_ratios(self):
        self.assertAlmostEqual(self.m["secondary_depth_mag_V_mid"], 0.0064, delta=0.0005)
        self.assertAlmostEqual(self.m["secondary_light_ratio_TESS_mid"], 0.0142, delta=0.0008)
        self.assertAlmostEqual(self.m["sec_to_prim_ratio_TESS_mid"], 0.1088, delta=0.003)
        lo, hi = self.m["sec_to_prim_ratio_TESS_range"]
        self.assertAlmostEqual(lo, 0.0683, delta=0.003)
        self.assertAlmostEqual(hi, 0.1473, delta=0.004)

    def test_ellipsoidal_small(self):
        self.assertAlmostEqual(self.m["ellipsoidal_semi_amplitude_mid"], 0.00078, delta=0.0001)

    def test_json_serialisable(self):
        import json
        json.dumps(self.m)
        self.assertTrue(math.isfinite(self.m["mass_function"]))


if __name__ == "__main__":
    unittest.main()
