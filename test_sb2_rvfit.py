# Tests for sb2_rvfit.py. MV2, Munim, Inc. Made with AI agents working in his name. Apache-2.0.
import math
import random
import unittest

import sb2_rvfit as rf


class TestGeometry(unittest.TestCase):
    def test_kepler_equation(self):
        for e in (0.0, 0.1, 0.4, 0.85):
            for M in (0.0, 0.3, 1.7, 3.1, 5.9, -2.0, 12.0):
                E = rf.solve_kepler(M, e)
                Mn = math.fmod(M, 2 * math.pi)
                if Mn < 0:
                    Mn += 2 * math.pi
                self.assertAlmostEqual(E - e * math.sin(E), Mn, places=10)

    def test_bad_eccentricity(self):
        with self.assertRaises(ValueError):
            rf.solve_kepler(1.0, 1.0)

    def test_circular_conjunction(self):
        P, tc = 5.0, 100.0
        tp = rf.tperi_from_conjunction(tc, P, 0.0, 0.0, True)
        self.assertAlmostEqual(tp, tc - P / 4.0, places=10)
        # at conjunction the velocity curve crosses gamma, star 1 moving towards the observer next
        self.assertAlmostEqual(rf.rv_shape(tc, P, 0.0, 0.0, tp), 0.0, places=9)
        self.assertLess(rf.rv_shape(tc + 0.1, P, 0.0, 0.0, tp), 0.0)
        # star 1 in front: the other conjunction, half a period away
        tp2 = rf.tperi_from_conjunction(tc, P, 0.0, 0.0, False)
        self.assertAlmostEqual((tp2 - tp) % P, P / 2.0, places=9)

    def test_eccentric_conjunction(self):
        P, e, w, tc = 6.96, 0.3, 343.0, 50.0
        for behind in (True, False):
            tp = rf.tperi_from_conjunction(tc, P, e, w, behind)
            nu = rf.true_anomaly(tc, P, e, tp)
            ang = math.degrees(nu) + w
            target = 90.0 if behind else 270.0
            d = (ang - target) % 360.0
            self.assertTrue(d < 1e-6 or d > 360.0 - 1e-6, (behind, ang))
            # rv_shape there is e cos w
            self.assertAlmostEqual(rf.rv_shape(tc, P, e, w, tp), e * math.cos(math.radians(w)), places=8)


class TestFit(unittest.TestCase):
    def _obs(self, P, e, w, tp, g, K1, K2, n=30, noise=0.0, seed=1):
        rnd = random.Random(seed)
        obs = []
        for i in range(n):
            t = 3.3 * i + 0.17 * i * i % 1.0
            f = rf.rv_shape(t, P, e, w, tp)
            obs.append({"t": t, "v1": g + K1 * f + rnd.gauss(0, noise) if noise else g + K1 * f,
                        "e1": 1.0, "v2": g - K2 * f + (rnd.gauss(0, noise) if noise else 0.0),
                        "e2": 1.0})
        return obs

    def test_exact_recovery(self):
        P, e, w = 3.787, 0.05, 120.0
        tp = rf.tperi_from_conjunction(10.0, P, e, w)
        obs = self._obs(P, e, w, tp, -7.0, 91.5, 85.3)
        r = rf.fit_fixed(obs, P, e, w, tp)
        self.assertAlmostEqual(r["gamma"], -7.0, places=6)
        self.assertAlmostEqual(r["K1"], 91.5, places=6)
        self.assertAlmostEqual(r["K2"], 85.3, places=6)
        self.assertLess(r["chi2"], 1e-12)
        self.assertEqual(r["dof"], 2 * 30 - 3)

    def test_single_lined_epochs_allowed(self):
        P, e, w = 5.9, 0.0, 0.0
        tp = rf.tperi_from_conjunction(0.0, P, e, w)
        obs = self._obs(P, e, w, tp, 3.0, 72.6, 78.9, n=12)
        for o in obs[::2]:
            o["v2"] = None
        r = rf.fit_fixed(obs, P, e, w, tp)
        self.assertAlmostEqual(r["K2"], 78.9, places=6)

    def test_too_few(self):
        with self.assertRaises(ValueError):
            rf.fit_fixed([{"t": 0.0, "v1": 1.0, "e1": 1.0, "v2": None, "e2": None}], 1.0, 0.0, 0.0, 0.0)

    def test_assignment_swaps_and_blends(self):
        P, e, w = 5.9, 0.0, 0.0
        tc = 0.0
        tp = rf.tperi_from_conjunction(tc, P, e, w)
        pairs = []
        for i in range(20):
            t = 0.37 * i + 1.1
            f = rf.rv_shape(t, P, e, w, tp)
            v1, v2 = 72.6 * f, -78.9 * f
            if i % 2:
                pairs.append({"t": t, "va": v2, "ea": 1.0, "vb": v1, "eb": 1.0})
            else:
                pairs.append({"t": t, "va": v1, "ea": 1.0, "vb": v2, "eb": 1.0})
        pairs.append({"t": tc, "va": 0.5, "ea": 1.0, "vb": -0.5, "eb": 1.0})  # at conjunction: blended
        obs, n_sw, n_bl = rf.assign_components(pairs, P, e, w, tp, 0.0, 72.6, 78.9, min_sep=20.0)
        self.assertEqual(n_bl, 1 + sum(1 for p in pairs[:-1] if abs(p["va"] - p["vb"]) < 20.0))
        r = rf.fit_pairs(pairs, P, e, w, tp, 60.0, 90.0, gamma_0=0.0)
        self.assertAlmostEqual(r["K1"], 72.6, places=5)
        self.assertAlmostEqual(r["K2"], 78.9, places=5)
        self.assertGreater(r["n_swapped"], 0)

    def test_scan_recovers_offset(self):
        P, e, w = 6.9611, 0.076, 343.0
        tc = 500.0
        true_dt = 0.04
        tp = rf.tperi_from_conjunction(tc + true_dt, P, e, w)
        pairs = []
        for i in range(40):
            t = 400.0 + 7.31 * i + 0.13 * (i % 5)
            f = rf.rv_shape(t, P, e, w, tp)
            pairs.append({"t": t, "va": 5.0 + 79.8 * f, "ea": 1.0, "vb": 5.0 - 94.7 * f, "eb": 1.0})
        sc = rf.scan_conjunction(pairs, P, e, w, tc, 75.0, 90.0, n_grid=201)
        self.assertLess(abs(sc["dt_best"] - true_dt), 2.5 * sc["grid_step"])
        self.assertFalse(sc["at_edge"])
        self.assertEqual(rf.grade_conjunction(sc), "CONJ_LATE")

    def test_grades(self):
        base = {"at_edge": False, "dt_sigma": 0.01}
        self.assertEqual(rf.grade_conjunction(dict(base, dt_best=0.02)), "CONJ_AGREES")
        self.assertEqual(rf.grade_conjunction(dict(base, dt_best=-0.05)), "CONJ_EARLY")
        self.assertEqual(rf.grade_conjunction(dict(base, dt_best=0.05)), "CONJ_LATE")
        self.assertEqual(rf.grade_conjunction(dict(base, dt_best=0.05), eph_sigma=0.02), "CONJ_AGREES")
        self.assertEqual(rf.grade_conjunction(dict(base, dt_best=0.0, at_edge=True)), "UNCONSTRAINED")


class TestMasses(unittest.TestCase):
    def test_simple(self):
        m = rf.masses(100.0, 0.0, 100.0, 0.0, 1.0)
        self.assertAlmostEqual(m["M1"], 1.036149e-7 * 4e4 * 100.0, places=9)
        self.assertAlmostEqual(m["M1"], m["M2"], places=12)
        self.assertAlmostEqual(m["a_rsun"], 0.0197657 * 200.0, places=9)

    def test_hd250735_minimum_masses(self):
        # Gaia DR3 SB2C: K1 72.62 +- 0.40, K2 78.94 +- 1.01, P 5.895935 (findings/2026-11-22-tic400170926-eclipsing-twin.md)
        m = rf.masses(72.62443658950218, 0.4027454, 78.94342367194483, 1.0145377, 5.895935077280673)
        self.assertAlmostEqual(m["M1"], 1.108, delta=0.002)
        self.assertAlmostEqual(m["M2"], 1.019, delta=0.002)
        self.assertAlmostEqual(m["a_rsun"], 17.66, delta=0.02)
        self.assertAlmostEqual(m["M1_err"], 0.030, delta=0.003)
        self.assertAlmostEqual(m["M2_err"], 0.017, delta=0.003)

    def test_inclination(self):
        a = rf.masses(80.0, 1.0, 90.0, 1.0, 4.0, 0.1, 90.0, 0.0)
        b = rf.masses(80.0, 1.0, 90.0, 1.0, 4.0, 0.1, 85.0, 0.5)
        self.assertAlmostEqual(b["M1"] / a["M1"], 1.0 / math.sin(math.radians(85.0)) ** 3, places=9)
        self.assertGreater(b["M1_err"], a["M1_err"] * b["M1"] / a["M1"])


class TestColumns(unittest.TestCase):
    def test_gaia_style(self):
        names = ["solution_id", "source_id", "transit_id", "rv_obs_time", "radial_velocity_1",
                 "radial_velocity_error_1", "radial_velocity_2", "radial_velocity_error_2",
                 "rv_template_teff_1", "vbroad_1", "grvs_mag", "rvs_spec_sig_to_noise"]
        m = rf.map_columns(names)
        self.assertIsNotNone(m)
        self.assertEqual(m["time"], "rv_obs_time")
        self.assertEqual(m["v1"], "radial_velocity_1")
        self.assertEqual(m["e1"], "radial_velocity_error_1")
        self.assertEqual(m["v2"], "radial_velocity_2")
        self.assertEqual(m["e2"], "radial_velocity_error_2")
        self.assertEqual(m["source_id"], "source_id")

    def test_suffix_error_style(self):
        names = ["source_id", "obs_time", "rv_primary", "rv_primary_error", "rv_secondary",
                 "rv_secondary_error"]
        m = rf.map_columns(names)
        self.assertIsNotNone(m)
        self.assertEqual(m["v1"], "rv_primary")
        self.assertEqual(m["e2"], "rv_secondary_error")

    def test_missing(self):
        self.assertIsNone(rf.map_columns(["source_id", "rv_obs_time", "radial_velocity", "radial_velocity_error"]))


class TestSelf(unittest.TestCase):
    def test_self_test_passes(self):
        r = rf.self_test()
        self.assertTrue(r["pass"], r)
        self.assertEqual(r["version"], rf.VERSION)


if __name__ == "__main__":
    unittest.main()
