# SPDX-License-Identifier: Apache-2.0
"""Tests for eblm_fit.py (MV2 of Munim, Inc.; made with AI agents). Expected values worked
by hand; see the comments."""
import math
import unittest

import numpy as np

import eblm_fit as ef


class TestGeometry(unittest.TestCase):
    def test_circle_overlap(self):
        # two unit circles one radius apart: 2 pi / 3 - sqrt(3) / 2
        self.assertAlmostEqual(float(ef.circle_overlap(1.0, 1.0)[0]), 2 * math.pi / 3 - math.sqrt(3) / 2, places=10)
        # small circle fully inside: pi k^2 = pi / 16
        self.assertAlmostEqual(float(ef.circle_overlap(0.5, 0.25)[0]), math.pi / 16, places=12)
        self.assertEqual(float(ef.circle_overlap(2.0, 0.5)[0]), 0.0)

    def test_blocked_uniform_central(self):
        # uniform disc, k = 0.1 at the centre: k^2 exactly (0.1 falls on a ring edge for n = 400)
        self.assertAlmostEqual(float(ef.blocked_fraction([0.0], 0.1, 0.0, 0.0, n=400)[0]), 0.01, places=12)

    def test_blocked_uniform_partial(self):
        # uniform disc, k = 1 at z = 1: overlap area / pi = 0.3910022
        exp = (2 * math.pi / 3 - math.sqrt(3) / 2) / math.pi
        self.assertAlmostEqual(float(ef.blocked_fraction([1.0], 1.0, 0.0, 0.0, n=4000)[0]), exp, delta=1e-3)

    def test_blocked_limb_darkened(self):
        # u1 = 0.4, u2 = 0.2, k = 0.1 central: (0.01 - 0.4 k^4 / 4 - ...) / (1 - u1/3 - u2/6)
        # = 0.00998997 / 0.8333333 = 0.0119880
        self.assertAlmostEqual(float(ef.blocked_fraction([0.0], 0.1, 0.4, 0.2, n=400)[0]), 0.011988, delta=2e-5)

    def test_outside_is_zero(self):
        self.assertEqual(float(ef.blocked_fraction([1.2], 0.1, 0.4, 0.2)[0]), 0.0)

    def test_eclipse_shapes(self):
        D, O = ef.eclipse_shapes([0.0, 0.5, 0.25], 0.1, 0.0, 5.0, 0.0, 0.0)
        self.assertAlmostEqual(float(D[0]), 0.01, places=10)
        self.assertAlmostEqual(float(O[0]), 0.0, places=12)
        self.assertAlmostEqual(float(D[1]), 0.0, places=12)
        self.assertAlmostEqual(float(O[1]), 1.0, places=10)
        self.assertEqual(float(D[2]), 0.0)
        self.assertEqual(float(O[2]), 0.0)


class TestTables(unittest.TestCase):
    def test_ld(self):
        self.assertEqual(ef.ld_coeffs(6000), (0.33, 0.25))
        u1, u2 = ef.ld_coeffs(float("nan"))           # 6500 K: half-way between 6000 and 7000
        self.assertAlmostEqual(u1, 0.29, places=12)
        self.assertAlmostEqual(u2, 0.275, places=12)
        self.assertEqual(ef.ld_coeffs(3000), (0.48, 0.17))
        self.assertEqual(ef.ld_coeffs(12000), (0.13, 0.32))

    def test_ms_teff_and_ceiling(self):
        self.assertAlmostEqual(ef.ms_teff(0.25), 3250.0, places=9)
        # T1 = 6400 K, a/R1 = 4: T_irr = 3200 K; (3150^4 + 3200^4)^(1/4) = 3776.1 K
        self.assertAlmostEqual(ef.t_allowed(0.2, 6400.0, 4.0), 3776.1, delta=1.0)

    def test_m2_from_fm(self):
        # m1 = 1, m2 = 0.5: f = 0.125 / 2.25
        self.assertAlmostEqual(ef.m2_from_fm(0.125 / 2.25, 1.0), 0.5, places=6)


class TestFit(unittest.TestCase):
    def test_nelder_mead(self):
        x, v = ef.nelder_mead(lambda p: (p[0] - 1) ** 2 + 10 * (p[1] + 2) ** 2, [0.0, 0.0], [0.5, 0.5])
        self.assertLess(abs(x[0] - 1), 1e-3)
        self.assertLess(abs(x[1] + 2), 1e-3)

    def test_synthetic_recovery(self):
        rng = np.random.default_rng(1)
        ph = (np.arange(1000) + 0.5) / 1000 - 0.5
        truth = (0.002, 0.15, 0.3, math.log(4.0))
        u1, u2 = ef.ld_coeffs(6500)
        A, _, _ = ef.design(ph, truth, u1, u2, 0.01)
        coef = np.array([1.0, 0.001, 0.0, -0.01, 0.0, 0.0005, 0.0, 0.0008])
        y = A @ coef + rng.normal(0, 3e-4, ph.size)
        sig = np.full(ph.size, 3e-4)
        fit = ef.fit_eclipse(ph, y, sig, 6500, 0.01, 0.12, 3.5)
        self.assertLess(abs(fit["k"] - 0.15), 0.01)
        self.assertLess(abs(fit["b"] - 0.3), 0.2)
        self.assertLess(abs(fit["a_r"] - 4.0), 0.4)
        self.assertLess(abs(fit["dphi"] - 0.002), 0.002)
        self.assertLess(abs(fit["Ds"] - 0.0008), 0.0003)
        self.assertLess(abs(fit["a_ell"] - 0.01), 0.001)
        self.assertGreater(fit["snr_fit"], 50)

    def test_derive(self):
        c = {"fm": 0.125 / 2.25, "m1_flame": 1.0, "m2_hi2": 0.55, "period": 1.0, "r1_flame": 1.0}
        fit = {"a_r": 4.0, "b": 0.0, "k": 0.1, "a_ell": 0.0, "Ds": 0.0, "err_Ds": 0.0}
        d = ef.derive(c, fit, 6000.0)
        self.assertAlmostEqual(d["inc_deg"], 90.0, places=9)
        self.assertAlmostEqual(d["m2"], 0.5, places=6)
        # Kepler: 1 d, 1.5 M_sun -> a = 0.022403 AU = 4.8173 R_sun
        self.assertAlmostEqual(d["a_rsun"], 4.8173, delta=0.002)
        self.assertAlmostEqual(d["r1_lc"], d["a_rsun"] / 4.0, places=12)
        self.assertAlmostEqual(d["r2"], 0.1 * d["r1_lc"], places=12)
        self.assertAlmostEqual(d["r_ms"], 0.47, places=9)
        self.assertAlmostEqual(d["infl"], d["r2"] / 0.47 - 1, places=12)
        self.assertTrue(d["t2"] != d["t2"])
        self.assertEqual(d["m1_source"], "flame")


class TestVerdict(unittest.TestCase):
    BASE = dict(snr_fit=50, A_odd=1.0, err_odd=0.01, A_even=1.0, err_even=0.01, a_ell=0.01, err_a_ell=0.001,
                ell_pred_fit=0.01, t2_lo3=3000.0, t_allow=4000.0, m2_hi2=0.3, b=0.2, k=0.15, r2=0.3,
                r_ms=0.27, infl=0.111)

    def v(self, **kw):
        d = dict(self.BASE)
        d.update(kw)
        return ef.verdict(d)[0]

    def test_rules(self):
        self.assertEqual(self.v(), "EBLM_CONSISTENT")
        self.assertEqual(self.v(snr_fit=5), "NO_ECLIPSE")
        self.assertEqual(self.v(snr_fit=float("nan")), "NO_ECLIPSE")
        self.assertEqual(self.v(A_even=0.8), "TWIN_AT_2P")
        self.assertEqual(self.v(A_even=0.95), "EBLM_CONSISTENT")     # 3 sigma but under 10%
        self.assertEqual(self.v(a_ell=0.03), "MASS_TENSION_HEAVIER")
        self.assertEqual(self.v(a_ell=0.001), "MASS_TENSION_LIGHTER")
        self.assertEqual(self.v(a_ell=0.0025), "EBLM_CONSISTENT")    # 0.0055 is not < 0.005
        self.assertEqual(self.v(t2_lo3=5000.0), "TOO_LUMINOUS")       # > 1.15 x 4000
        self.assertEqual(self.v(t2_lo3=float("nan")), "EBLM_CONSISTENT")
        self.assertEqual(self.v(b=0.9), "EBLM_GRAZING")
        self.assertEqual(self.v(infl=0.4), "EBLM_LARGE_RADIUS")
        self.assertEqual(self.v(infl=-0.4), "EBLM_SMALL_RADIUS")
        self.assertEqual(self.v(m2_hi2=0.07), "BD_EBLM_CONSISTENT")


class TestStats(unittest.TestCase):
    def test_inflation_labels(self):
        s = ef.inflation_stats([0.1] * 10)
        self.assertEqual(s["label"], "INFLATED")
        self.assertAlmostEqual(s["median"], 0.1, places=12)
        self.assertEqual(ef.inflation_stats([-0.02, 0.0, 0.02] * 4)["label"], "CONSISTENT")
        self.assertEqual(ef.inflation_stats([-0.1] * 5)["label"], "DEFLATED")
        self.assertEqual(ef.inflation_stats([0.5, -0.5, 0.4, -0.4, 0.45, -0.45])["label"], "INCONCLUSIVE")
        self.assertEqual(ef.inflation_stats([1.0, 2.0])["label"], "TOO_FEW")

    def test_grade(self):
        vets = [{"source_id": "1", "snr_fit": 20.0, "verdict": "EBLM_CONSISTENT", "r1_ratio": 1.0, "infl": 0.1,
                 "infl_flame": 0.1, "period_gaia": 1.0, "depth_ratio_gaia": 0.9},
                {"source_id": "2", "snr_fit": 5.0, "verdict": "NO_ECLIPSE"},
                {"source_id": "3", "verdict": "NO_TESS_DATA"}]
        g = ef.grade(vets)
        self.assertEqual(g["G1"]["n_with_data"], 2)
        self.assertEqual(g["G1"]["n_detected"], 1)
        self.assertFalse(g["G1"]["pass"])
        self.assertTrue(g["G2"]["pass"])
        self.assertFalse(g["G3"]["pass"])
        self.assertTrue(g["E5_redo"]["pass"])

    def test_parse_asu_tsv(self):
        text = ("#comment\n\n_r\tName\tType\n\t\t\n-----\t----\t----\n1.2\tHIP 2964\tVAR\n\n")
        rows = ef.parse_asu_tsv(text)
        self.assertEqual(rows, [{"_r": "1.2", "Name": "HIP 2964", "Type": "VAR"}])
        self.assertEqual(ef.parse_asu_tsv("#only comments\n"), [])


if __name__ == "__main__":
    unittest.main()
