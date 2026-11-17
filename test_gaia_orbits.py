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

    def test_face_on_no_nan(self):
        A, B, F, G = go.elements_to_thiele_innes(1.0, 0.0, 0.3, 0.2)
        el = go.thiele_innes_to_elements(A, B, F, G)
        self.assertAlmostEqual(float(el["cosi"]), 1.0, places=9)

    def test_adql_expression_matches_python(self):
        rng = np.random.default_rng(9)
        expr = go.cosi_adql(prefix="").replace("SQRT", "sqrt")
        for _ in range(100):
            A, B, F, G = go.elements_to_thiele_innes(rng.uniform(0.1, 5), rng.uniform(1, 179),
                                                     rng.uniform(0, 6.28), rng.uniform(0, 3.14))
            ns = {"sqrt": np.sqrt, "a_thiele_innes": float(A), "b_thiele_innes": float(B),
                  "f_thiele_innes": float(F), "g_thiele_innes": float(G)}
            val = eval(expr, {"__builtins__": {}}, ns)
            self.assertAlmostEqual(val, float(go.thiele_innes_to_elements(A, B, F, G)["cosi"]),
                                   places=9)


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


# Four real Gaia DR3 orbits. The expected conjunction times (BTJD) and cos i were
# computed independently by an ADQL query on the Gaia archive (2026-11-17), with
# omega = (atan2(B-F, A+G) + atan2(-B-F, A-G)) / 2 and Kepler's equation in closed
# form; values are rounded to 1e-4 d. Times are compared as a set, modulo P.
DR3_ROWS = [
    {"source_id": 2960647744567925632, "nss_solution_type": "AstroSpectroSB1",
     "a_thiele_innes": 0.036382854236142376, "b_thiele_innes": -0.3151243446510355,
     "f_thiele_innes": 0.08772005510178042, "g_thiele_innes": -0.13873646638714984,
     "eccentricity": 0.6757623573545173, "period": 98.25555037153,
     "t_periastron": -31.228462551158923, "adql_t": (366.9909, 453.0342), "adql_cosi": 0.1831},
    {"source_id": 3309006602007842048, "nss_solution_type": "OrbitalTargetedSearchValidated",
     "a_thiele_innes": 0.18393184844326121, "b_thiele_innes": -0.2197559460392094,
     "f_thiele_innes": 1.197511643787416, "g_thiele_innes": 0.6044573801761476,
     "eccentricity": 0.5923695230586918, "period": 814.7061800516827,
     "t_periastron": -70.45497479404082, "adql_t": (705.2193, 1131.8940), "adql_cosi": 0.2075},
    {"source_id": 4854976609869179648, "nss_solution_type": "AstroSpectroSB1",
     "a_thiele_innes": -0.23443925307867822, "b_thiele_innes": -0.12755815901973852,
     "f_thiele_innes": 0.4197439620532465, "g_thiele_innes": 0.14232874617020358,
     "eccentricity": 0.47566114441492535, "period": 406.5013768822883,
     "t_periastron": 189.08043233042088, "adql_t": (860.9515, 182.8270), "adql_cosi": 0.0758},
    {"source_id": 393581461455623296, "nss_solution_type": "AstroSpectroSB1",
     "a_thiele_innes": 0.08254147190319085, "b_thiele_innes": 0.41155537948814036,
     "f_thiele_innes": 0.03236568224919485, "g_thiele_innes": -0.00649125533317565,
     "eccentricity": 4.986257409808453e-06, "period": 73.34027644514153,
     "t_periastron": -6.960108269809396, "adql_t": (400.3748, 437.0452), "adql_cosi": -0.0786,
     # circular solution: G, C and e not fitted (bit_index 65435)
     "a_thiele_innes_error": 0.028047005, "b_thiele_innes_error": 0.026270581,
     "f_thiele_innes_error": 0.03527139, "g_thiele_innes_error": None,
     "eccentricity_error": None, "period_error": 0.118722215,
     "t_periastron_error": 0.5764451},
]


class TestAgainstGaiaArchive(unittest.TestCase):
    def test_conjunctions_match_adql(self):
        for r in DR3_ROWS:
            t1, t2 = go.central_conjunctions(r, ref_btjd=389.0)
            P = r["period"]
            ours = sorted(np.mod([t1, t2], P))
            theirs = sorted(np.mod(r["adql_t"], P))
            for a, b in zip(ours, theirs):
                d = abs(np.mod(a - b + P / 2, P) - P / 2)
                self.assertLess(d, 2e-3, msg=f"{r['source_id']}: {ours} vs {theirs}")

    def test_cosi_matches_adql(self):
        for r in DR3_ROWS:
            el = go.thiele_innes_to_elements(r["a_thiele_innes"], r["b_thiele_innes"],
                                             r["f_thiele_innes"], r["g_thiele_innes"])
            self.assertAlmostEqual(float(el["cosi"]), r["adql_cosi"], delta=6e-5)

    def test_circular_constraint(self):
        r = DR3_ROWS[3]
        self.assertTrue(go.is_circular_fixed(r))
        # Gaia's served G equals -A F / B for this circular solution
        self.assertAlmostEqual(-r["a_thiele_innes"] * r["f_thiele_innes"] / r["b_thiele_innes"],
                               r["g_thiele_innes"], places=12)
        s = go.sample_orbit(r, 400, np.random.default_rng(4), ref_btjd=389.0)
        self.assertTrue(s["circular"])
        # omega = 0 (mod pi) in every sample -> conjunctions at Tp + P/4 and Tp + 3P/4
        ph = np.mod(s["t1"] - s["Tp"], s["P"]) / s["P"]
        self.assertTrue(np.all(np.minimum(np.abs(ph - 0.25), np.abs(ph - 0.75)) < 1e-6))
        # cos i still varies (it is -F/B), with roughly the catalogue spread
        self.assertGreater(np.std(s["cosi"]), 0.03)
        self.assertLess(np.std(s["cosi"]), 0.2)
        # old behaviour (G held fixed) would spread omega; check it no longer does
        dw = np.mod(s["omega"] - s["omega"][0] + np.pi / 2, np.pi) - np.pi / 2
        self.assertLess(np.max(np.abs(dw)), 1e-9)


class TestCorrelations(unittest.TestCase):
    def test_corr_matrix_column_major(self):
        # Gaia data model: row 1 reads C0, C1, C3, C6; row 2 reads C2, C4, C7; ...
        vec = np.arange(10, dtype=float) / 100.0
        R = go.corr_matrix(vec, 5)
        self.assertEqual(list(R[0, 1:]), [0.00, 0.01, 0.03, 0.06])
        self.assertEqual(list(R[1, 2:]), [0.02, 0.04, 0.07])
        self.assertEqual(list(R[2, 3:]), [0.05, 0.08])
        self.assertEqual(R[3, 4], 0.09)
        self.assertTrue(np.allclose(R, R.T))
        self.assertTrue(np.allclose(np.diag(R), 1.0))

    def test_parse_corr_vec(self):
        v = go.parse_corr_vec('"(0.11160702, 0.09855627, NaN, -0.37598)"')
        self.assertEqual(v.size, 4)
        self.assertTrue(np.isnan(v[2]))
        self.assertAlmostEqual(v[3], -0.37598)
        self.assertIsNone(go.parse_corr_vec(""))

    def test_wrong_length_falls_back(self):
        row = dict(DR3_ROWS[0], corr_vec="(0.1, 0.2)")
        for k in go.SAMPLE_KEYS:
            row.setdefault(k + "_error", 0.01)
        s = go.sample_orbit(row, 50, np.random.default_rng(1), ref_btjd=389.0)
        self.assertFalse(s["used_corr"])

    def test_correlated_sampling(self):
        names = go.PARAM_ORDER["orbital"]
        n = len(names)
        vec = np.full(n * (n - 1) // 2, np.nan)
        ia, ib = names.index("a_thiele_innes"), names.index("b_thiele_innes")
        ip, it = names.index("period"), names.index("t_periastron")
        vec[ib * (ib - 1) // 2 + ia] = 0.9
        vec[it * (it - 1) // 2 + ip] = -0.8
        A, B, F, G = go.elements_to_thiele_innes(1.0, 88.0, 0.4, 0.9)
        row = {"nss_solution_type": "Orbital",
               "corr_vec": "(" + ", ".join("NaN" if not np.isfinite(x) else repr(float(x)) for x in vec) + ")",
               "a_thiele_innes": float(A), "b_thiele_innes": float(B),
               "f_thiele_innes": float(F), "g_thiele_innes": float(G),
               "eccentricity": 0.2, "period": 300.0, "t_periastron": 5.0}
        for k in go.SAMPLE_KEYS:
            row[k + "_error"] = 0.05 if "thiele" in k else (0.02 if k == "eccentricity" else 2.0)
        rng = np.random.default_rng(12)
        names7 = go.SAMPLE_KEYS
        R = go._correlation_for_keys(row, names7)
        self.assertIsNotNone(R)
        X = go._mvn(np.zeros(7), np.ones(7), R, 20000, rng)
        c = np.corrcoef(X.T)
        self.assertAlmostEqual(c[0, 1], 0.9, delta=0.02)
        self.assertAlmostEqual(c[5, 6], -0.8, delta=0.02)
        self.assertLess(abs(c[0, 2]), 0.03)
        s = go.sample_orbit(row, 200, np.random.default_rng(2), ref_btjd=389.0)
        self.assertTrue(s["used_corr"])
        self.assertTrue(np.all(np.isfinite(s["t1"])))


class TestLabelAlignment(unittest.TestCase):
    def test_t1_keeps_its_meaning_near_node_boundary(self):
        # Omega close to 0: noisy samples straddle the Omega = 0 / pi boundary, which
        # used to swap t1 and t2 between samples.
        A, B, F, G = go.elements_to_thiele_innes(1.0, 89.0, 1.0, 0.002)
        row = {"a_thiele_innes": float(A), "b_thiele_innes": float(B),
               "f_thiele_innes": float(F), "g_thiele_innes": float(G),
               "eccentricity": 0.3, "period": 200.0, "t_periastron": 0.0,
               "eccentricity_error": 0.001, "period_error": 0.01,
               "t_periastron_error": 0.01}
        for x in "abfg":
            row[f"{x}_thiele_innes_error"] = 0.01
        s = go.sample_orbit(row, 1000, np.random.default_rng(5), ref_btjd=0.0)
        t1c, t2c = go.central_conjunctions(row, ref_btjd=0.0)
        off = go.phase_offsets(s, "t1", t1c)
        self.assertLess(np.percentile(np.abs(off), 99), 200.0 / 20)
        off2 = go.phase_offsets(s, "t2", t2c)
        self.assertLess(np.percentile(np.abs(off2), 99), 200.0 / 20)

    def test_predict_next(self):
        A, B, F, G = go.elements_to_thiele_innes(1.0, 89.5, 0.7, 1.2)
        row = {"a_thiele_innes": float(A), "b_thiele_innes": float(B),
               "f_thiele_innes": float(F), "g_thiele_innes": float(G),
               "eccentricity": 0.1, "period": 50.0, "t_periastron": 3.0,
               "eccentricity_error": 1e-4, "period_error": 1e-4,
               "t_periastron_error": 1e-3}
        for x in "abfg":
            row[f"{x}_thiele_innes_error"] = 1e-4
        s = go.sample_orbit(row, 300, np.random.default_rng(8), ref_btjd=389.0)
        t1c, _ = go.central_conjunctions(row, ref_btjd=389.0)
        tn, sig = go.predict_next(s, "t1", t1c, 50.0, 4400.0)
        self.assertGreaterEqual(tn, 4400.0 - 0.1)
        self.assertLess(tn, 4450.1)
        self.assertLess(abs(np.mod(tn - t1c + 25, 50) - 25), 0.05)
        self.assertLess(sig, 0.5)
        self.assertGreater(sig, 0.0)


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
