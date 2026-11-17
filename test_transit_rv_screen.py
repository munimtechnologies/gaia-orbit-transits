# SPDX-License-Identifier: Apache-2.0
"""Tests for transit_rv_screen.py (MV2 of Munim, Inc.; made with AI agents).
Every expected number is worked by hand in the comments."""
import csv
import json
import math
import os
import tempfile
import unittest

import transit_rv_screen as trs


class TestPhysics(unittest.TestCase):
    def test_constant(self):
        # (2 pi G M_sun / 86400 s)^(1/3) with GM_sun = 1.32712440018e20 m^3 s^-2
        k = (2 * math.pi * 1.32712440018e20 / 86400.0) ** (1 / 3) / 1000.0
        self.assertAlmostEqual(k, trs.K_SUN, places=2)

    def test_earth_and_jupiter(self):
        # Earth: K = 212.908 * 3.0035e-6 / 365.25^(1/3) = 6.3947e-4 / 7.14822 = 0.08946 m/s
        k = trs.k_semi_amplitude(3.0035e-6, 365.25, 1.0) * 1000
        self.assertAlmostEqual(k, 0.0895, delta=0.0005)
        # Jupiter: 212.908 * 9.546e-4 / 1.000636 / 16.30233 = 12.459 m/s
        k = trs.k_semi_amplitude(9.546e-4, 4332.6, 1.0) * 1000
        self.assertAlmostEqual(k, 12.46, delta=0.03)

    def test_mass_function(self):
        # P = 1 d, K = 100 km/s: f = 1e6 / 212.908^3 = 1e6 / 9.65112e6 = 0.103615 M_sun
        self.assertAlmostEqual(trs.mass_function(100.0, 1.0), 0.10362, places=4)

    def test_min_mass_round_trip(self):
        for m2, p, m1 in [(0.01, 0.94, 1.2), (0.3, 7.0, 1.4), (1.0, 100.0, 1.0)]:
            k = trs.k_semi_amplitude(m2, p, m1)
            self.assertAlmostEqual(trs.min_companion_mass(k, p, m1), m2, places=7)
        self.assertEqual(trs.min_companion_mass(0.0, 1.0, 1.0), 0.0)

    def test_wasp18_mass(self):
        # Gaia DR3 SB1 for WASP-18: K = 1.938 km/s, P = 0.94147 d, e = 0.1234, M1 = 1.197.
        # f = 0.977246 * 7.278826 * 0.94147 / 9.65112e6 = 6.9390e-7;
        # m2^3 = f (1.2070)^2 = 1.01097e-6 -> m2 = 0.010036 M_sun = 10.5 M_Jup
        # (literature ~10.4 M_Jup).
        m2 = trs.min_companion_mass(1.938, 0.94147, 1.197, 0.1234)
        self.assertAlmostEqual(m2, 0.01004, delta=0.00005)

    def test_epoch_scatter_and_k_lower(self):
        # N = 2: sqrt(pi/4) = 0.886227; sigma = 10 -> rv_err = 0.11 + 8.86227
        self.assertAlmostEqual(trs.epoch_scatter(8.97227, 2), 10.0, places=4)
        # sqrt(2 (100 - 36)) = sqrt(128) = 11.3137
        self.assertAlmostEqual(trs.k_lower(10.0, 6.0), 11.3137, places=4)
        self.assertEqual(trs.k_lower(5.0, 7.0), 0.0)
        self.assertTrue(math.isnan(trs.epoch_scatter("", 10)))
        # Gaia DR3 2685725036820337408: rv_err 3.1584, N 19:
        # (3.1584 - 0.11) / sqrt(pi / 38) = 3.0484 / 0.28753 = 10.602
        self.assertAlmostEqual(trs.epoch_scatter(3.1584013, 19), 10.602, delta=0.002)

    def test_period_match(self):
        self.assertEqual(trs.period_match(0.94148, 0.94147), (1, 1))
        self.assertEqual(trs.period_match(1.2175, 0.60875), (2, 1))
        self.assertEqual(trs.period_match(0.4602, 0.9204), (1, 2))
        self.assertIsNone(trs.period_match(2.5979, 7.0623))
        self.assertIsNone(trs.period_match(0.8514, 0.4602))   # ratio 1.850
        self.assertIsNone(trs.period_match("", 1.0))


def row(**kw):
    base = {"source_id": "1", "transit_period": "1.0", "mass_flame": "1.0", "nss_type": "",
            "nss_period": "", "nss_k1": "", "nss_k1_error": "", "nss_ecc": "",
            "rv_method_used": "1", "rv_nb_transits": "20", "radial_velocity_error": "0.5",
            "rv_chisq_pvalue": "0.5", "rv_renormalised_gof": "1.0", "accel_type": ""}
    base.update({k: str(v) for k, v in kw.items()})
    return base


class TestScreenRow(unittest.TestCase):
    def test_wasp18_is_gaia_mass_planet(self):
        r = trs.screen_row(row(source_id="4955371367334610048", transit_period=0.9414777,
                               mass_flame=1.1969767, nss_type="SB1", nss_period=0.9414685,
                               nss_k1=1.9382582, nss_k1_error=0.14212629, nss_ecc=0.1233767,
                               radial_velocity_error=0.34195697, rv_nb_transits=31,
                               rv_chisq_pvalue=0.0, rv_renormalised_gof=11.09))
        # K + 2 sigma = 2.2225 -> m2 ~ 0.01004 * 2.2225 / 1.938 = 0.01151 < 13 M_Jup = 0.01241
        self.assertEqual(r["nss_match"], "1:1")
        self.assertEqual(r["class"], "GAIA_MASS_PLANET")
        self.assertLess(r["m2_from_k1_hi2"], trs.PLANET_MAX)

    def test_rv_scatter_excludes_planet(self):
        # 2685725036820337408: sigma_obs 10.60; K_lo = sqrt(2 (112.4 - 49)) = 11.26 km/s;
        # 13 M_Jup at 0.25 d around 1.18 M_sun: 2.6420 / 1.1245 / 0.62996 = 3.73 km/s
        r = trs.screen_row(row(transit_period=1.9465478, mass_flame=1.1797106,
                               radial_velocity_error=3.1584013, rv_nb_transits=19,
                               rv_chisq_pvalue=0.0, rv_renormalised_gof=11.64,
                               accel_type="Acceleration9"))
        self.assertAlmostEqual(r["k_lower"], 11.26, delta=0.02)
        self.assertAlmostEqual(r["k_planet_max_any_p"], 3.73, delta=0.01)
        self.assertEqual(r["class"], "RV_EXCLUDES_PLANET_ONLY")
        self.assertIn("outer companion", r["reasons"])

    def test_wasp163_noise_not_flagged(self):
        # WASP-163 (a real hot Jupiter): sigma_obs = 2.1633 / 0.37789 = 5.72 < 7 -> K_lo = 0
        r = trs.screen_row(row(transit_period=0.5573328, mass_flame=0.913,
                               radial_velocity_error=2.2732947, rv_nb_transits=11,
                               rv_chisq_pvalue=5.7e-9, rv_renormalised_gof=5.1))
        self.assertEqual(r["k_lower"], 0.0)
        self.assertEqual(r["class"], "RV_VARIABLE_WEAK")

    def test_other_classes(self):
        r = trs.screen_row(row(nss_type="SB2C", nss_period=5.896, nss_k1=72.6, nss_k1_error=0.4))
        self.assertEqual(r["class"], "DOUBLE_LINED")
        # SB1 at 7.06 d with K 22.4 around 1.39 M_sun: m2 sin i ~ 0.284 M_sun
        r = trs.screen_row(row(transit_period=2.5979, mass_flame=1.394, nss_type="SB1",
                               nss_period=7.0623, nss_k1=22.404, nss_k1_error=1.144,
                               nss_ecc=0.1068))
        self.assertEqual(r["class"], "STELLAR_SB1_OTHER_PERIOD")
        self.assertAlmostEqual(r["m2_from_k1"], 0.284, delta=0.003)
        r = trs.screen_row(row(transit_period=3.30, nss_type="OrbitalTargetedSearch",
                               nss_period=193.5))
        self.assertEqual(r["class"], "ASTROMETRIC_OTHER_PERIOD")
        r = trs.screen_row(row(rv_method_used=2))
        self.assertEqual(r["class"], "NO_RV")
        self.assertEqual(trs.screen_row(row())["class"], "RV_QUIET")

    def test_short_period_sb1_boundary(self):
        # 1622997463177004928: SB1 P 0.46023 d, K 19.696 +- 1.314, e 0.2009, M1 0.9557.
        # f = 0.94008 * 7640.2 * 0.46023 / 9.65112e6 = 3.4251e-4;
        # m2^3 = f (1.02690)^2 -> m2 sin i = 0.07122 M_sun (74.6 M_Jup).
        r = trs.screen_row(row(transit_period=0.8513754, mass_flame=0.9556862, nss_type="SB1",
                               nss_period=0.46023065, nss_k1=19.695569, nss_k1_error=1.3143485,
                               nss_ecc=0.2008897))
        self.assertAlmostEqual(r["m2_from_k1"], 0.0712, delta=0.0003)
        self.assertEqual(r["nss_match"], "")
        self.assertEqual(r["class"], "SB1_OTHER_PERIOD")


class TestOffline(unittest.TestCase):
    def test_main_offline(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "in.csv")
            rows = [row(source_id="a"), row(source_id="b", nss_type="SB2C", nss_period=5.9,
                                             nss_k1=70, nss_k1_error=1)]
            with open(p, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            self.assertEqual(trs.main(["--input-csv", p, "--no-catalogues", "--out-dir", d]), 0)
            with open(os.path.join(d, "transit_rv_screen_summary.json")) as fh:
                s = json.load(fh)
            self.assertEqual(s["n"], 2)
            self.assertEqual(s["classes"], {"RV_QUIET": 1, "DOUBLE_LINED": 1})
            self.assertIn("SELECT", trs.screen_adql("gaiadr4"))
            self.assertIn("gaiadr4.nss_two_body_orbit", trs.screen_adql("gaiadr4"))


if __name__ == "__main__":
    unittest.main()
