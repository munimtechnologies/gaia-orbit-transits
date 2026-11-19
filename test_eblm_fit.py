# SPDX-License-Identifier: Apache-2.0
"""Unit tests for eblm_fit 0.2.0 (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents).

Stdlib tests always run; tests that need numpy are skipped when numpy is missing."""
import math
import random
import unittest

import eblm_fit as ef

try:
    import numpy as np
    HAVE_NP = True
except ImportError:  # the stdlib-only publish check
    np = None
    HAVE_NP = False


class TestEccentricGeometry(unittest.TestCase):
    def test_version(self):
        self.assertEqual(ef.VERSION, "0.2.0")

    def test_phi2_circular(self):
        self.assertEqual(ef.phi2_from_gaia(0.0, 37.0), 0.5)
        self.assertEqual(ef.phi2_from_gaia(float("nan"), 37.0), 0.5)
        self.assertEqual(ef.phi2_from_gaia(0.2, float("nan")), 0.5)

    def test_phi2_first_order(self):
        for e, om in ((0.1, 0.0), (0.05, 60.0), (0.1, 180.0), (0.08, 300.0)):
            approx = 0.5 + 2.0 / math.pi * e * math.cos(math.radians(om))
            self.assertAlmostEqual(ef.phi2_from_gaia(e, om), approx, delta=1.5e-3)

    def test_phi2_omega_90_is_half(self):
        self.assertAlmostEqual(ef.phi2_from_gaia(0.3, 90.0), 0.5, places=9)
        self.assertAlmostEqual(ef.phi2_from_gaia(0.3, 270.0), 0.5, places=9)

    def test_phi2_large_e_known_value(self):
        # e = 0.1, omega = 0: hand computation gives 0.56355 (first order 0.56366)
        self.assertAlmostEqual(ef.phi2_from_gaia(0.1, 0.0), 0.56355, delta=2e-4)

    def test_occ_geometry(self):
        self.assertEqual(ef.occ_geometry(0.0, 10.0), ef.CIRCULAR)
        p2, br, vr = ef.occ_geometry(0.2, 90.0)
        self.assertAlmostEqual(p2, 0.5, places=9)
        self.assertAlmostEqual(br, 1.2 / 0.8, places=9)
        self.assertAlmostEqual(vr, 0.8 / 1.2, places=9)

    def test_true_geometry_circular_is_identity(self):
        a_r, cosi = ef.true_geometry(8.0, 0.4, 0.0, 30.0)
        self.assertAlmostEqual(a_r, 8.0)
        self.assertAlmostEqual(cosi, 0.05)

    def test_true_geometry_eccentric(self):
        # e = 0.3, omega = 90: transit at periastron, chord speed (1 + e)/sqrt(1 - e^2)
        e = 0.3
        a_r, cosi = ef.true_geometry(10.0, 0.5, e, 90.0)
        self.assertAlmostEqual(a_r, 10.0 * math.sqrt(1 - e * e) / 1.3, places=9)
        # separation at transit = a (1 - e): b = a cos i (1 - e) / R1
        self.assertAlmostEqual(cosi * a_r * (1 - e), 0.5, places=9)

    def test_ecc_used(self):
        self.assertEqual(ef.ecc_used(0.36, 0.01), 0.36)
        self.assertEqual(ef.ecc_used(0.05, 0.03), 0.0)
        self.assertEqual(ef.ecc_used(float("nan"), float("nan")), 0.0)
        self.assertEqual(ef.ecc_used("", ""), 0.0)
        self.assertEqual(ef.ecc_used(0.1, float("nan")), 0.1)
        self.assertEqual(ef.ecc_used(0.03, None), 0.0)
        self.assertEqual(ef.ecc_used(0.99, 0.001), 0.0)


class TestVerdictOrder(unittest.TestCase):
    def base(self, **kw):
        v = {"snr_fit": 50.0, "b": 0.2, "k": 0.1, "a_ell": 0.0001, "err_a_ell": 0.00001,
             "ell_pred_fit": 0.0001, "t2_lo3": float("nan"), "t_allow": 3000.0, "m2_hi2": 0.2,
             "r2": 0.2, "r_ms": 0.2, "infl": 0.0}
        v.update(kw)
        return v

    def test_consistent(self):
        self.assertEqual(ef.verdict(self.base())[0], "EBLM_CONSISTENT")
        self.assertEqual(ef.mass_check(self.base())[0], "MASS_OK")

    def test_mass_tension_when_not_grazing(self):
        v = self.base(a_ell=0.001)
        self.assertEqual(ef.verdict(v)[0], "MASS_TENSION_HEAVIER")
        v = self.base(a_ell=-0.001)
        self.assertEqual(ef.verdict(v)[0], "MASS_TENSION_LIGHTER")

    def test_grazing_before_mass(self):
        v = self.base(a_ell=0.001, b=0.95, k=0.1)
        self.assertEqual(ef.verdict(v)[0], "EBLM_GRAZING")
        self.assertEqual(ef.mass_check(v)[0], "MASS_TENSION_HEAVIER")
        v["m2_hi2"] = 0.05
        self.assertEqual(ef.verdict(v)[0], "BD_EBLM_GRAZING")

    def test_no_eclipse_and_twin_first(self):
        self.assertEqual(ef.verdict(self.base(snr_fit=5.0, b=0.95))[0], "NO_ECLIPSE")
        v = self.base(b=0.95, A_odd=0.05, A_even=0.03, err_odd=0.001, err_even=0.001)
        self.assertEqual(ef.verdict(v)[0], "TWIN_AT_2P")

    def test_mass_na(self):
        self.assertEqual(ef.mass_check(self.base(err_a_ell=float("nan")))[0], "MASS_NA")


class TestErrors(unittest.TestCase):
    def test_segment_scatter(self):
        self.assertTrue(math.isnan(ef.segment_scatter([1.0])))
        self.assertAlmostEqual(ef.segment_scatter([1.0, 3.0]), 1.0)
        self.assertAlmostEqual(ef.segment_scatter([2.0, 2.0, 2.0]), 0.0)

    def test_combine_err(self):
        self.assertAlmostEqual(ef.combine_err(1e-5, 2.0, float("nan")), 2e-5)
        self.assertAlmostEqual(ef.combine_err(1e-5, 2.0, 5e-5), 5e-5)
        self.assertAlmostEqual(ef.combine_err(1e-5, 1.0, 5e-6), 1e-5)
        self.assertTrue(math.isnan(ef.combine_err(float("nan"), 1.0, float("nan"))))


@unittest.skipUnless(HAVE_NP, "numpy not installed")
class TestNumpyParts(unittest.TestCase):
    def test_circular_shapes_match_01(self):
        ph = np.linspace(-0.5, 0.5, 2001)
        D, O = ef.eclipse_shapes(ph, 0.1, 0.0, 6.0, 0.4, 0.2)
        self.assertGreater(D[1000], 0.009)            # centre of transit
        self.assertAlmostEqual(float(O[0]), 1.0, places=6)   # phase -0.5: full occultation
        self.assertEqual(float(D[0]), 0.0)

    def test_shifted_occultation(self):
        ph = np.array([0.5, 0.6, -0.4])
        D, O = ef.eclipse_shapes(ph, 0.1, 0.0, 6.0, 0.4, 0.2, geom=(0.6, 1.0, 1.0))
        self.assertEqual(float(O[0]), 0.0)
        self.assertAlmostEqual(float(O[1]), 1.0, places=6)
        self.assertAlmostEqual(float(O[2]), 1.0, places=6)   # same phase, wrapped
        self.assertTrue(np.all(D == 0))

    def test_occultation_impact_ratio(self):
        # b_occ = b * ratio: a large ratio makes the occultation miss
        D, O = ef.eclipse_shapes(np.array([0.5]), 0.1, 0.8, 6.0, 0.4, 0.2, geom=(0.5, 1.5, 1.0))
        self.assertEqual(float(O[0]), 0.0)

    def test_segments(self):
        t = np.concatenate([np.arange(0, 13, 0.01), np.arange(14, 27, 0.01), np.arange(60, 125, 0.01)])
        segs = ef.segments(t)
        spans = [t[s[-1]] - t[s[0]] for s in segs]
        self.assertEqual(sum(len(s) for s in segs), t.size)
        self.assertTrue(all(sp <= ef.SEG_PART_DAYS + 0.02 for sp in spans))
        self.assertEqual(len(segs), 1 + 3)   # 0-27 joined (gap 1 d); 60-125 cut in 3

    def test_beta_white_and_red(self):
        rng = np.random.default_rng(1)
        t = np.arange(0, 54, 10.0 / 1440)
        white = rng.normal(0, 1e-3, t.size)
        b_w, _ = ef.beta_factor(t, white, [0.25, 0.5, 1.0])
        self.assertLess(b_w, 1.5)
        red = white + 1e-3 * np.sin(2 * np.pi * t / 3.1)
        b_r, _ = ef.beta_factor(t, red, [0.25, 0.5, 1.0])
        self.assertGreater(b_r, 3.0)

    def test_fit_recovers_shifted_occultation(self):
        rng = np.random.default_rng(7)
        ph = (np.arange(1000) + 0.5) / 1000 - 0.5
        geom = (0.58, 1.0, 1.0)
        A, _, _ = ef.design(ph, (0.0, 0.12, 0.3, math.log(7.0)), 0.4, 0.2, 0.001, geom)
        coef = np.zeros(8)
        coef[0] = 1.0
        coef[3] = -2e-4
        coef[7] = 2e-3
        y = A @ coef + rng.normal(0, 1e-4, ph.size)
        sig = np.full(ph.size, 1e-4)
        fit = ef.fit_eclipse(ph, y, sig, 5800.0, 0.001, 0.12, 7.0, b_starts=(0.3,), geom=ef.CIRCULAR)
        p2, chi_best, chi_c = ef.scan_phi2(ph, y, sig, fit, 0.001, 0.5)
        self.assertAlmostEqual(p2, 0.58, delta=0.01)
        self.assertGreater(chi_c - chi_best, 25.0)


if __name__ == "__main__":
    unittest.main()
