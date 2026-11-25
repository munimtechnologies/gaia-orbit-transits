# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""Tests for vpt_fu_checks: hand-computed values (findings/2026-11-25-vpt-followup-results.md)."""
import math
import unittest

import vpt_fu_checks as c


class TestFormulas(unittest.TestCase):
    def test_earth_orbit(self):
        # 1 Msun, 1 yr -> 1 AU
        self.assertAlmostEqual(c.semi_major_axis_rsun(365.25, 1.0), 215.032, places=6)

    def test_planck_ratio_equal_temps(self):
        self.assertAlmostEqual(c.planck_ratio(5000.0, 5000.0), 1.0, places=12)

    def test_required_depth_equal_mags(self):
        self.assertAlmostEqual(c.required_neighbour_depth(0.01, 12.0, 12.0), 0.01, places=12)


class TestHandValues(unittest.TestCase):
    def setUp(self):
        self.r = c.report()

    def close(self, got, want, rel=0.01):
        self.assertTrue(math.isclose(got, want, rel_tol=rel), f"{got} vs {want}")

    def test_tic4638108_orbit(self):
        r = self.r["TIC 4638108"]
        self.close(r["a_rsun"], 8.2943)
        self.close(r["a_over_rstar"], 5.8218)
        self.close(r["t14_central_h"], 3.2617)
        self.close(r["t_dayside"], 2657.1)

    def test_tic4638108_secondary(self):
        r = self.r["TIC 4638108"]
        self.close(r["sec_thermal_planet"], 1.8796e-4)
        self.close(r["sec_reflected_ag05"], 2.0751e-4)
        self.close(r["sec_selfluminous_3100K"], 4.9537e-4)
        # observed 507 +/- 145 ppm lies above the thermal-only planet value by > 2 sigma
        z = (r["sec_observed"] - r["sec_thermal_planet"]) / r["sec_observed_err"]
        self.close(z, 2.207, rel=0.02)

    def test_tic4638108_neighbours_cannot_fake_gaia_dip(self):
        d = self.r["TIC 4638108"]["neighbour_required_depths"]
        self.close(d[0], 2.4162)
        self.close(d[1], 15.773)
        self.close(d[2], 2.4665)
        self.assertTrue(all(x > 1.0 for x in d))

    def test_tic44997521_orbit(self):
        r = self.r["TIC 44997521"]
        self.close(r["a_rsun"], 8.7766)
        self.close(r["t14_central_h"], 2.8146)


if __name__ == "__main__":
    unittest.main()
