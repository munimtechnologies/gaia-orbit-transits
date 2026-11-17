# SPDX-License-Identifier: Apache-2.0
import unittest

import numpy as np

import gaia_orbits as go


class TestThieleInnes(unittest.TestCase):
    def test_round_trip(self):
        rng = np.random.default_rng(3)
        for _ in range(200):
            a = rng.uniform(0.1, 10)
            inc = rng.uniform(1, 179)
            w = rng.uniform(0, 2 * np.pi)
            W = rng.uniform(0, np.pi)
            A, B, F, G = go.elements_to_thiele_innes(a, inc, w, W)
            el = go.thiele_innes_to_elements(A, B, F, G)
            self.assertAlmostEqual(float(el["a"]), a, places=6)
            self.assertAlmostEqual(float(el["inc_deg"]), inc, places=4)
            dW = np.mod(float(el["Omega"]) - W + np.pi / 2, np.pi) - np.pi / 2
            dw = np.mod(float(el["omega"]) - w + np.pi / 2, np.pi) - np.pi / 2
            self.assertAlmostEqual(dW, 0.0, places=5)
            self.assertAlmostEqual(dw, 0.0, places=5)

    def test_edge_on_cosi_zero(self):
        A, B, F, G = go.elements_to_thiele_innes(2.0, 90.0, 0.7, 1.1)
        el = go.thiele_innes_to_elements(A, B, F, G)
        self.assertLess(abs(float(el["cosi"])), 1e-9)


class TestConjunction(unittest.TestCase):
    def test_conjunction_is_minimum_projected_separation(self):
        rng = np.random.default_rng(7)
        for _ in range(25):
            e = rng.uniform(0, 0.7)
            w = rng.uniform(0, 2 * np.pi)
            W = rng.uniform(0, np.pi)
            P, Tp = rng.uniform(5, 500), rng.uniform(-100, 100)
            A, B, F, G = go.elements_to_thiele_innes(1.0, 89.99, w, W)
            el = go.thiele_innes_to_elements(A, B, F, G)
            t1, t2, _, _ = go.conjunction_times(Tp, P, e, el["omega"])
            t = np.linspace(Tp, Tp + P, 400001)
            x, y = go.sky_position(t, P, Tp, e, A, B, F, G)
            sep = np.hypot(x, y)
            # local minima of the projected separation
            mins = t[1:-1][(sep[1:-1] < sep[:-2]) & (sep[1:-1] < sep[2:])]
            for tc in (float(t1), float(t2)):
                d = np.abs(np.mod(mins - tc + P / 2, P) - P / 2)
                self.assertLess(d.min(), 2e-3 * P, msg=f"e={e} w={w} P={P}")

    def test_circular_quarter_period(self):
        t1, t2, _, _ = go.conjunction_times(0.0, 100.0, 0.0, 0.0)
        self.assertAlmostEqual(float(t1), 25.0, places=6)
        self.assertAlmostEqual(float(t2), 75.0, places=6)


class TestMasses(unittest.TestCase):
    def test_jupiter_analogue(self):
        m1, mj = 1.0, go.MJUP_MSUN
        a_tot = (1 + mj) ** (1 / 3) * 11.862 ** (2 / 3)
        a1 = a_tot * mj / (1 + mj)
        m2 = go.companion_mass_dark(a1 * 100.0, 100.0, 11.862 * go.YEAR_D, m1)
        self.assertAlmostEqual(float(m2) / mj, 1.0, delta=0.01)

    def test_equal_mass(self):
        # dark equal-mass companion: a1 = a/2
        P = 365.25
        a_tot = 2 ** (1 / 3)
        m2 = go.companion_mass_dark(a_tot / 2 * 50.0, 50.0, P, 1.0)
        self.assertAlmostEqual(float(m2), 1.0, delta=1e-3)

    def test_classify(self):
        self.assertEqual(go.classify(0.005), "planet")
        self.assertEqual(go.classify(0.05), "brown-dwarf")
        self.assertEqual(go.classify(0.3), "star")


class TestMonteCarlo(unittest.TestCase):
    def _row(self, inc):
        A, B, F, G = go.elements_to_thiele_innes(1.0, inc, 0.4, 0.9)
        row = {"period": 50.0, "period_error": 0.001, "t_periastron": 10.0,
               "t_periastron_error": 0.1, "eccentricity": 0.1, "eccentricity_error": 0.01}
        for k, v in zip("abfg", (A, B, F, G)):
            row[f"{k}_thiele_innes"] = float(v)
            row[f"{k}_thiele_innes_error"] = 0.001
        return row

    def test_edge_on_eclipses(self):
        s = go.sample_orbit(self._row(90.0), 500, np.random.default_rng(1))
        g = go.eclipse_geometry(s, 1.0, 1.0, 0.05, 0.1)
        self.assertGreater(np.mean(g["ecl1"] | g["ecl2"]), 0.9)
        self.assertTrue(np.all(g["dur_central1"] > 0.1))

    def test_inclined_never_eclipses(self):
        s = go.sample_orbit(self._row(60.0), 500, np.random.default_rng(1))
        g = go.eclipse_geometry(s, 1.0, 1.0, 0.05, 0.1)
        self.assertEqual(np.mean(g["ecl1"] | g["ecl2"]), 0.0)

    def test_window_match_and_coverage(self):
        s = go.sample_orbit(self._row(90.0), 400, np.random.default_rng(2))
        tc = float(np.median(s["t1"])) + 30 * 50.0
        wm = go.window_match(s, "t1", tc, 0.3)
        self.assertGreater(wm["frac_in_window"], 0.9)
        self.assertGreater(wm["bf"], 10)
        obs = np.arange(tc - 5, tc + 5, 1 / 48)
        self.assertGreater(go.coverage_fraction(s, "t1", obs, 0.05), 0.9)
        obs_far = np.arange(tc + 10, tc + 20, 1 / 48)
        self.assertLess(go.coverage_fraction(s, "t1", obs_far, 0.05), 0.05)


if __name__ == "__main__":
    unittest.main()
