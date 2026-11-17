# SPDX-License-Identifier: Apache-2.0
"""Tests for eblm_screen.py (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents).

Reference numbers are hand-checked for Gaia DR3 2346634757461218816 (= HIP 2964), whose
Gaia DR3 values were read from the ESA Gaia archive on 2026-11-17:
SB1 P = 1.2589434045 d, K = 31.777049852 km/s, e = 0.0149136725, omega = 273.0756290 deg;
FLAME M1 = 1.6354012, R1 = 2.4890115; EB Gaussian depth 0.021210926 mag, ellipsoidal
0.012665253 mag; (t_ecl - t_periastron) / P = -129.50659614763757.
"""
import math
import unittest

import eblm_screen as es

P = 1.2589434044789267
K = 31.777049852255296
E = 0.014913672456766896
OM = 273.07562900521754
X = -129.50659614763757


class TestPhysics(unittest.TestCase):
    def test_mass_function(self):
        # 31.777^3 * 1.25894 / 212.908^3 = 40396.6 / 9651081 = 4.1857e-3
        self.assertAlmostEqual(es.mass_function(K, P), 4.1857e-3, delta=3e-6)

    def test_min_companion_mass(self):
        # m^3 / (1.6354 + m)^2 = 4.1843e-3 -> m = 0.24554 (bisection by hand)
        self.assertAlmostEqual(es.min_companion_mass(K, P, 1.6354012, E), 0.2455, delta=5e-4)

    def test_semi_major_axis_and_ellipsoidal(self):
        a = es.semi_major_axis_rsun(P, 1.6354012 + 0.24554)
        self.assertAlmostEqual(a, 6.056, delta=0.005)
        # 1.302 * (0.24554 / 1.6354) * (2.489 / 6.056)^3 = 1.302 * 0.15014 * 0.06942
        self.assertAlmostEqual(es.ellipsoidal_pred(0.24554, 1.6354012, 2.4890115, a), 0.01357, delta=3e-4)
        self.assertAlmostEqual(es.ellipsoidal_alpha(), 1.302, places=6)

    def test_mag_to_flux(self):
        self.assertAlmostEqual(es.mag_to_flux(0.021210926), 0.019346, delta=5e-5)
        self.assertAlmostEqual(es.mag_amp_to_flux(0.012665253), 0.011665, delta=5e-6)

    def test_ms_radius(self):
        self.assertAlmostEqual(es.ms_radius(0.10), 0.12, places=6)
        self.assertAlmostEqual(es.ms_radius(0.25), 0.2675, places=6)

    def test_roche(self):
        self.assertAlmostEqual(es.roche_lobe_fraction(1.0), 0.37892, delta=5e-5)

    def test_planck_and_teff(self):
        self.assertAlmostEqual(es.planck_ratio(3000.0, 6000.0), 0.0475, delta=5e-4)
        d = 0.01 * es.planck_ratio(3000.0, 6000.0)
        self.assertAlmostEqual(es.companion_teff(d, 0.1, 6000.0), 3000.0, delta=0.5)
        self.assertTrue(math.isnan(es.companion_teff(0.0, 0.1, 6000.0)))


class TestConjunction(unittest.TestCase):
    def test_circular(self):
        p = 2.0
        self.assertAlmostEqual(es.conjunction_offset(0.25 * p, 0.0, p, 0.0, 0.0), 0.0, places=9)
        self.assertAlmostEqual(abs(es.conjunction_offset(0.25 * p, 0.0, p, 0.0, 0.0, "occultation")), 0.5,
                               places=9)

    def test_eccentric_limits(self):
        p = 3.0
        # omega = 90 deg: transit at periastron; omega = 270 deg: half a period earlier
        self.assertAlmostEqual(es.conjunction_offset(10 * p, 0.0, p, 90.0, 0.5), 0.0, places=9)
        self.assertAlmostEqual(es.conjunction_offset(-0.5 * p, 0.0, p, 270.0, 0.5), 0.0, places=6)

    def test_hip2964(self):
        # by hand: f = -183.0756 deg, E = -3.196097, M = -3.196909, M / 2pi = -0.508804,
        # offset = -129.506596 + 0.508804 -> +0.0022
        self.assertAlmostEqual(es.conjunction_offset(X * P, 0.0, P, OM, E), 0.0022, delta=5e-4)


def hip2964_row():
    return {"source_id": "2346634757461218816", "period": str(P), "k1": str(K),
            "k1_error": "0.32036537", "eccentricity": str(E), "arg_periastron": str(OM),
            "t_periastron": "0", "frequency": str(1.0 / P), "reference_time": str(2191.5 + X * P),
            "derived_primary_ecl_phase": "0", "derived_primary_ecl_depth": "0.046541303",
            "derived_secondary_ecl_depth": "", "geom_model_gaussian1_phase": "0",
            "geom_model_gaussian1_depth": "0.021210926", "geom_model_gaussian2_phase": "",
            "geom_model_gaussian2_depth": "", "ell_mag": "0.012665253", "mass_flame": "1.6354012",
            "radius_flame": "2.4890115", "teff_gspphot": "6570.6865"}


class TestClassify(unittest.TestCase):
    def test_eclipse_only_depths(self):
        r = {"derived_primary_ecl_phase": "0.79", "geom_model_gaussian1_phase": "0.29",
             "geom_model_gaussian1_depth": "0.08", "geom_model_gaussian2_phase": "0.79",
             "geom_model_gaussian2_depth": "0.12"}
        self.assertEqual(es.eclipse_only_depths(r), (0.12, 0.08))
        p1, p2 = es.eclipse_only_depths({"derived_primary_ecl_phase": "0.7",
                                         "geom_model_gaussian1_phase": "0.7",
                                         "geom_model_gaussian1_depth": "0.02"})
        self.assertEqual(p1, 0.02)
        self.assertTrue(math.isnan(p2))

    def test_hip2964(self):
        c = es.classify(hip2964_row())
        self.assertEqual(c["cls"], "eblm_like")
        self.assertAlmostEqual(c["m2"], 0.2455, delta=5e-4)
        self.assertAlmostEqual(c["dph_transit"], 0.0022, delta=5e-4)
        self.assertAlmostEqual(abs(c["dph_occult"]), 0.4978, delta=0.003)
        self.assertAlmostEqual(c["ell_ratio"], 0.86, delta=0.02)    # 0.011665 / 0.01357
        # R2 = 2.489 * sqrt(0.019346) = 0.3462; MS radius at 0.24554 M_sun
        # = 0.225 + 0.085 * 0.4554 = 0.2637; ratio 1.313
        self.assertAlmostEqual(c["r2_gaia"], 0.3462, delta=0.002)
        self.assertAlmostEqual(c["r2_ratio_ms"], 1.313, delta=0.01)

    def test_twin_blend(self):
        r = hip2964_row()
        r.update({"k1": "9.0", "derived_primary_ecl_depth": "0.124", "derived_secondary_ecl_depth": "0.118",
                  "geom_model_gaussian2_phase": "0.5", "geom_model_gaussian2_depth": "0.118",
                  "geom_model_gaussian1_depth": "0.124"})
        self.assertEqual(es.classify(r)["cls"], "twin_blend_suspect")

    def test_population_stats(self):
        rows = [{"fm": 0.001, "d1_mag": 0.1, "d2_mag": 0.09}, {"fm": 0.001, "d1_mag": 0.1, "d2_mag": 0.02},
                {"fm": 0.1, "d1_mag": 0.1, "d2_mag": 0.02}, {"fm": 0.1, "d1_mag": 0.1, "d2_mag": float("nan")}]
        s = es.population_stats(rows)
        self.assertEqual(s["fm<0.003"], {"n": 2, "twin": 1, "twin_frac": 0.5})
        self.assertEqual(s["fm>0.03"]["n"], 1)


class TestVerdict(unittest.TestCase):
    base = {"snr": 50, "depth_p": 0.01, "err_p": 1e-4, "depth_s": 1e-5, "err_s": 5e-5,
            "depth_odd": 0.01, "err_odd": 1e-4, "depth_even": 0.0101, "err_even": 1e-4,
            "t2": 0.0, "teff1": 6500, "a_ell": 0.010, "err_a_ell": 2e-4, "ell_pred": 0.011,
            "r2": 0.26, "r_ms": 0.25, "m2_hi2": 0.27}

    def v(self, **kw):
        d = dict(self.base)
        d.update(kw)
        return es.verdict(d)[0]

    def test_labels(self):
        self.assertEqual(self.v(), "EBLM_CONSISTENT")
        self.assertEqual(self.v(snr=5), "NO_ECLIPSE")
        self.assertEqual(self.v(depth_odd=0.02), "TWIN_AT_2P")
        self.assertEqual(self.v(depth_s=0.005, t2=9000), "HOT_COMPANION")
        self.assertEqual(self.v(depth_s=0.004, t2=5500), "LUMINOUS_COMPANION")
        self.assertEqual(self.v(a_ell=0.03), "MASS_TENSION_HEAVIER")
        self.assertEqual(self.v(a_ell=0.002), "MASS_TENSION_LIGHTER")
        self.assertEqual(self.v(r2=0.40), "EBLM_LARGE_RADIUS")
        self.assertEqual(self.v(r2=0.15), "EBLM_SMALL_RADIUS")
        self.assertEqual(self.v(m2_hi2=0.07, r2=0.1, r_ms=0.1), "BD_EBLM_CONSISTENT")


class TestAdql(unittest.TestCase):
    def test_schema(self):
        q = es.sample_adql("gaiadr4")
        self.assertIn("gaiadr4.nss_two_body_orbit", q)
        self.assertIn("'SB1'", q)


if __name__ == "__main__":
    unittest.main()
