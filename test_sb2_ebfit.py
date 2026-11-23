# SPDX-License-Identifier: Apache-2.0
"""Unit tests for sb2_ebfit (MV2, Munim, Inc.; made with AI agents). numpy only."""
import math
import unittest

import numpy as np

import sb2_ebfit as ef


def brute_ld_blocked(z, p, u1, u2, n=1200):
    """Brute-force 2D grid integration of the hidden light of a quadratic-LD unit disk."""
    xs = (np.arange(n) + 0.5) / n * 2.0 - 1.0
    X, Y = np.meshgrid(xs, xs)
    R2 = X * X + Y * Y
    inside = R2 < 1.0
    mu = np.sqrt(np.clip(1.0 - R2, 0.0, 1.0))
    inten = np.where(inside, 1.0 - u1 * (1.0 - mu) - u2 * (1.0 - mu) ** 2, 0.0)
    cover = (X - z) ** 2 + Y ** 2 < p * p
    return float((inten * cover).sum() / inten.sum())


class TestOccultation(unittest.TestCase):
    def test_uniform_matches_analytic(self):
        ann = ef.annuli(0.0, 0.0, 400)
        for z, p in ((0.0, 0.5), (0.3, 0.5), (0.9, 0.4), (1.2, 0.5), (0.5, 1.2), (0.2, 0.9), (1.6, 0.5)):
            got = ef.blocked_fraction([z], p, ann)[0]
            self.assertAlmostEqual(got, ef.uniform_overlap(z, p), delta=2e-3, msg=str((z, p)))

    def test_limb_darkened_matches_brute_force(self):
        u1, u2 = ef.ld_coeffs(6000)
        ann = ef.annuli(u1, u2)
        for z, p in ((0.0, 0.6), (0.5, 0.8), (1.1, 0.9), (0.3, 1.1)):
            got = ef.blocked_fraction([z], p, ann)[0]
            self.assertAlmostEqual(got, brute_ld_blocked(z, p, u1, u2), delta=3e-3, msg=str((z, p)))

    def test_no_overlap_is_zero(self):
        ann = ef.annuli(0.3, 0.2)
        self.assertEqual(ef.blocked_fraction([2.0], 0.5, ann)[0], 0.0)

    def test_full_cover(self):
        ann = ef.annuli(0.3, 0.2)
        self.assertAlmostEqual(ef.blocked_fraction([0.05], 1.5, ann)[0], 1.0, places=9)


class TestOrbit(unittest.TestCase):
    def test_conjunction_at_T0(self):
        for ecw, esw, cosi in ((0.0, 0.0, 0.05), (0.03, -0.04, 0.1), (-0.2, 0.3, 0.02)):
            d, s = ef.sky_geometry(np.array([100.0]), 100.0, 3.0, ecw, esw, cosi)
            e, w = ef.ew_of(ecw, esw)
            rsep = (1 - e * e) / (1 + e * math.sin(w))
            self.assertAlmostEqual(float(s[0]), 1.0, places=9)
            self.assertAlmostEqual(float(d[0]), rsep * cosi, places=9)

    def test_circular_secondary_at_half(self):
        d, s = ef.sky_geometry(np.array([101.5]), 100.0, 3.0, 0.0, 0.0, 0.05)
        self.assertAlmostEqual(float(s[0]), -1.0, places=9)
        self.assertAlmostEqual(ef.secondary_phase(0.0, 0.0), 0.5, places=12)

    def test_secondary_phase_small_e(self):
        # t2 - t1 ~ P/2 (1 + (4/pi) e cos w) for small e; check sign and size
        ph = ef.secondary_phase(0.01, 0.0)
        self.assertAlmostEqual(ph - 0.5, 2.0 / math.pi * 0.01, delta=2e-4)

    def test_model_depths(self):
        th = np.array([0.0, 4.0, 0.0, 0.0, 0.0, 0.2, 1.0, 1.0, 0.0])
        anns = [ef.annuli(0.0, 0.0), ef.annuli(0.0, 0.0)]
        f = ef.lc_model(np.array([0.0, 2.0, 1.0]), th, anns)
        self.assertAlmostEqual(f[0], 0.5, delta=2e-3)   # equal uniform stars, central: half the light
        self.assertAlmostEqual(f[1], 0.5, delta=2e-3)
        self.assertAlmostEqual(f[2], 1.0, places=12)
        th[8] = 0.2
        f = ef.lc_model(np.array([0.0]), th, anns)
        self.assertAlmostEqual(f[0], 0.6, delta=2e-3)


class TestPhysics(unittest.TestCase):
    def test_msini_matches_screen(self):
        # CD-28 7251, Gaia DR3 5633392634307163776: the screen's m1sin3i = 2.0605557900615
        m1, m2 = ef.msini_direct(79.81466872566406, 94.66300256795384, 6.96108580484263, 0.07601178028086204)
        self.assertAlmostEqual(m1 / 2.0605557900615, 1.0, delta=0.005)
        self.assertGreater(m1, m2)

    def test_mc_edge_on(self):
        th = np.array([0.0, 6.96108580484263, 0.0, 0.0, 0.0, 0.2, 1.0, 1.0, 0.0])
        cov = np.diag(np.array([1e-4, 1e-6, 1e-4, 1e-4, 1e-4, 1e-4, 1e-3, 1e-3, 1e-3]) ** 2)
        ph = ef.physical_mc(th, cov, 79.81, 0.01, 94.66, 0.01, n=4000)
        m1, _ = ef.msini_direct(79.81, 94.66, 6.96108580484263, 0.0)
        self.assertAlmostEqual(ph["M_gaia1"]["median"] / m1, 1.0, delta=0.002)
        self.assertAlmostEqual(ph["R_lc1"]["median"], ph["R_lc2"]["median"], delta=0.01)

    def test_mapping_omega(self):
        th = np.array([0.0, 5.0, 0.2 * math.cos(math.radians(100)), 0.2 * math.sin(math.radians(100)),
                       0.0, 0.2, 1.0, 1.0, 0.0])
        cov = np.diag(np.full(9, 1e-6))
        m = ef.map_components(th, cov, {"e": 0.2, "e_err": 0.005, "omega": 280.0})
        self.assertEqual(m["rule"], "MAP_OMEGA")
        self.assertEqual(m["lc1_is"], "gaia2")
        m = ef.map_components(th, cov, {"e": 0.2, "e_err": 0.005, "omega": 95.0})
        self.assertEqual(m["lc1_is"], "gaia1")


class TestFoldAndBaseline(unittest.TestCase):
    def test_fold_finds_period(self):
        th = np.array([1000.2, 3.3, 0.0, 0.0, 0.05, 0.18, 1.0, 0.7, 0.0])
        anns = [ef.annuli(0.3, 0.25), ef.annuli(0.3, 0.25)]
        t = np.concatenate([np.arange(1000.0, 1027.0, 120 / 86400.0), np.arange(1700.0, 1727.0, 120 / 86400.0)])
        rng = np.random.default_rng(1)
        f = ef.lc_model(t, th, anns) + rng.normal(0, 5e-4, t.size)
        r = ef.detrend(t, f)
        eph = ef.fold_search(t, r, 3.3 + 4e-5, 2e-5)
        self.assertAlmostEqual(eph["P"], 3.3, delta=2e-5)
        self.assertAlmostEqual(((eph["T0"] - th[0]) / th[1] + 0.5) % 1.0 - 0.5, 0.0, delta=0.002)
        self.assertAlmostEqual(eph["dphase"], 0.5, delta=0.003)

    def test_projection_recovers_linear_baseline(self):
        tau = np.tile(np.linspace(-0.2, 0.2, 50), 2)
        win = np.repeat([0, 1], 50)
        m = 1.0 - 0.1 * np.exp(-0.5 * (tau / 0.05) ** 2)
        base_true = np.where(win == 0, 1.01 + 0.02 * tau, 0.99 - 0.03 * tau)
        f = m * base_true
        data = ef.Data(tau + 10.0 * win, f, np.full(f.size, 1e-3), win, tau, np.zeros(f.size, int),
                       np.full(f.size, 120.0), np.ones(f.size, int))
        base = ef.project_baseline(m, data)
        self.assertLess(float(np.max(np.abs(base - base_true))), 1e-10)


if __name__ == "__main__":
    unittest.main()
