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
# For the AstroSpectroSB1 rows, c/h_thiele_innes (AU) and "adql_t_rv" (the transit
# time from omega_rv = atan2(C, H), f = pi/2 - omega_rv, computed in ADQL on the
# archive, 2026-11-17) were added in 0.3.0; "transit_t" is the astrometric
# conjunction (from adql_t) that the RV omega picks.
DR3_ROWS = [
    {"source_id": 2960647744567925632, "nss_solution_type": "AstroSpectroSB1",
     "a_thiele_innes": 0.036382854236142376, "b_thiele_innes": -0.3151243446510355,
     "f_thiele_innes": 0.08772005510178042, "g_thiele_innes": -0.13873646638714984,
     "eccentricity": 0.6757623573545173, "period": 98.25555037153,
     "t_periastron": -31.228462551158923, "adql_t": (366.9909, 453.0342), "adql_cosi": 0.1831,
     "c_thiele_innes": 0.0214630, "c_thiele_innes_error": 0.00609629,
     "h_thiele_innes": -0.0295566, "h_thiele_innes_error": 0.00680217,
     "adql_t_rv": 355.385, "transit_t": 453.0342},
    {"source_id": 3309006602007842048, "nss_solution_type": "OrbitalTargetedSearchValidated",
     "a_thiele_innes": 0.18393184844326121, "b_thiele_innes": -0.2197559460392094,
     "f_thiele_innes": 1.197511643787416, "g_thiele_innes": 0.6044573801761476,
     "eccentricity": 0.5923695230586918, "period": 814.7061800516827,
     "t_periastron": -70.45497479404082, "adql_t": (705.2193, 1131.8940), "adql_cosi": 0.2075},
    {"source_id": 4854976609869179648, "nss_solution_type": "AstroSpectroSB1",
     "a_thiele_innes": -0.23443925307867822, "b_thiele_innes": -0.12755815901973852,
     "f_thiele_innes": 0.4197439620532465, "g_thiele_innes": 0.14232874617020358,
     "eccentricity": 0.47566114441492535, "period": 406.5013768822883,
     "t_periastron": 189.08043233042088, "adql_t": (860.9515, 182.8270), "adql_cosi": 0.0758,
     "c_thiele_innes": -0.0501770, "c_thiele_innes_error": 0.00979076,
     "h_thiele_innes": -0.0519131, "h_thiele_innes_error": 0.0101054,
     "adql_t_rv": 890.437, "transit_t": 860.9515},
    {"source_id": 393581461455623296, "nss_solution_type": "AstroSpectroSB1",
     "a_thiele_innes": 0.08254147190319085, "b_thiele_innes": 0.41155537948814036,
     "f_thiele_innes": 0.03236568224919485, "g_thiele_innes": -0.00649125533317565,
     "eccentricity": 4.986257409808453e-06, "period": 73.34027644514153,
     "t_periastron": -6.960108269809396, "adql_t": (400.3748, 437.0452), "adql_cosi": -0.0786,
     # circular solution: G, C and e not fitted (bit_index 65435)
     "a_thiele_innes_error": 0.028047005, "b_thiele_innes_error": 0.026270581,
     "f_thiele_innes_error": 0.03527139, "g_thiele_innes_error": None,
     "eccentricity_error": None, "period_error": 0.118722215,
     "t_periastron_error": 0.5764451,
     # C is served but not meaningful for circular solutions; omega = 0, H > 0
     "c_thiele_innes": -0.0257056, "c_thiele_innes_error": None,
     "h_thiele_innes": 0.0167755, "h_thiele_innes_error": 0.00484414,
     "adql_t_rv": 400.3748, "transit_t": 400.3748},
]


def _dmod(a, b, P):
    return abs(np.mod(a - b + P / 2, P) - P / 2)


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


# Gaia DR3 EclipsingSpectro solutions (eclipses + single-lined RV fitted together by
# the NSS pipeline) joined with gaiadr3.vari_eclipsing_binary (eclipse times from the
# separate variability pipeline). Queried on the Gaia archive, 2026-11-17.
# Columns: source_id, period (d), eccentricity, arg_periastron (deg), t_periastron
# (d from J2016.0), tp1 = reference_time + derived_primary_ecl_phase / frequency
# - 2191.5 (deepest eclipse, d from J2016.0; Gaia time is BJD - 2455197.5).
# 1963575553568406528 is left out: its two eclipses are equally deep (0.458 and
# 0.440 mag), so "primary" is arbitrary (its other eclipse matches, phase 0.0006).
ECLIPSING_SPECTRO = [
    # circular (Gaia fixed e = 0, omega = 0)
    (5592279626810866816, 1.0175483226776123, 0.0, 0.0, 0.1350814253091812, 30.911449674690175),
    (289944136822295552, 0.5279802083969116, 0.0, 0.0, 0.05223703011870384, 60.37395721201074),
    (6183905457652903040, 0.7788470983505249, 0.0, 0.0, 0.29819223284721375, 136.79304817458433),
    (520587625832477824, 2.1000421047210693, 0.0, 0.0, -0.021207597106695175, 32.002786852764984),
    (5374894907999920768, 0.573470413684845, 0.0, 0.0, 0.08163893222808838, 37.50121153410555),
    (5587423633706300288, 2.0517420768737793, 0.0, 0.0, 0.286638468503952, 72.61120628636309),
    (4324609893265605888, 0.6433572769165039, 0.0, 0.0, -0.1773567646741867, -49.55353503593187),
    (6156224603884943360, 0.8097625374794006, 0.0, 0.0, -0.21962645649909973, 65.57445773787731),
    (6267913819672876160, 0.7969892621040344, 0.0, 0.0, 0.21520046889781952, -154.99807388471095),
    (1823758498214886912, 0.725960910320282, 0.0, 0.0, -0.32403770089149475, -32.08267813500515),
    # eccentric (omega fitted)
    (2072115497495386368, 0.8061097860336304, 0.01926628313958645, 75.36218311308882,
     0.1602512001991272, 30.826150718246936),
    (4575893582048929536, 2.986567497253418, 0.00428655743598938, 242.81300642789986,
     -0.5640784502029419, 84.78140221426884),
    (498657664552495744, 1.1577541828155518, 0.005317854695022106, 110.08336096638944,
     0.4070581793785095, 48.969718161478795),
    (3041948353046851968, 2.6077027320861816, 0.03322817385196686, 88.26921207822943,
     1.1645307540893555, -1.434677918496618),
    (5566666915748470912, 1.0495829582214355, 0.10662038624286652, 269.91025199755137,
     0.1036873459815979, -3.5682455249038867),
    (5946797527472646272, 1.9953004121780396, 0.0011306977830827236, 25.160009260644546,
     -0.6488774418830872, 149.37035373973413),
    (861690393720718720, 0.6709580421447754, 0.03437914699316025, 272.07211615288713,
     -0.019584456458687782, 6.351663525312688),
    (416422509855555584, 0.6735261082649231, 0.010285554453730583, 268.624810395755,
     0.1730348914861679, 73.25282730172103),
]


def _phase_diff(a, b):
    d = np.mod(a - b, 1.0)
    return min(d, 1.0 - d)


class TestTransitConvention(unittest.TestCase):
    def test_deeper_eclipse_at_pi_over_2_minus_omega(self):
        for sid, P, e, wdeg, tp, tp1 in ECLIPSING_SPECTRO:
            obs = np.mod((tp1 - tp) / P, 1.0)
            pred = float(go.transit_phase(e, np.radians(wdeg)))
            self.assertLess(_phase_diff(obs, pred), 0.02, msg=f"{sid}: obs {obs} pred {pred}")

    def test_opposite_sign_convention_is_rejected(self):
        # omega -> -omega (f = pi/2 + omega) would put the eclipse elsewhere
        rejected = 0
        for sid, P, e, wdeg, tp, tp1 in ECLIPSING_SPECTRO:
            if e == 0.0:
                continue
            obs = np.mod((tp1 - tp) / P, 1.0)
            alt = float(go.transit_phase(e, -np.radians(wdeg)))
            if _phase_diff(obs, alt) > 0.1:
                rejected += 1
        self.assertGreaterEqual(rejected, 7)


class TestTransitLabel(unittest.TestCase):
    def test_rv_transit_time_matches_adql(self):
        for r in DR3_ROWS:
            if "adql_t_rv" not in r:
                continue
            t = go.rv_transit_time(r, ref_btjd=389.0)
            self.assertIsNotNone(t)
            self.assertLess(_dmod(t["t_transit_rv_btjd"], r["adql_t_rv"], r["period"]), 0.05,
                            msg=str(r["source_id"]))

    def test_label_picks_expected_conjunction(self):
        for r in DR3_ROWS:
            lab = go.transit_label(r, ref_btjd=389.0)
            if "transit_t" not in r:
                self.assertEqual(lab["transit_conj"], "")
                continue
            t1, t2 = go.central_conjunctions(r, ref_btjd=389.0)
            chosen = t1 if lab["transit_conj"] == "t1" else t2
            self.assertLess(_dmod(chosen, r["transit_t"], r["period"]), 2e-3,
                            msg=str(r["source_id"]))
            self.assertTrue(lab["rv_consistent"])

    def test_circular_sb1_transit_quarter_period(self):
        r = DR3_ROWS[3]
        w, snr = go.rv_omega(r)
        self.assertEqual(w, 0.0)
        self.assertAlmostEqual(snr, 0.0167755 / 0.00484414, places=4)
        lab = go.transit_label(r, ref_btjd=389.0)
        self.assertLess(lab["rv_offset_d"], 0.01)
        tq = r["t_periastron"] + 389.0 + r["period"] / 4
        self.assertLess(_dmod(lab["t_transit_rv_btjd"], tq, r["period"]), 1e-6)

    def test_unconstrained_omega_gets_no_label(self):
        # C/H of Gaia DR3 4422729073976768640: C is 0.02 sigma, omega_rv unconstrained
        r = dict(DR3_ROWS[0], c_thiele_innes=-0.00228324, c_thiele_innes_error=0.129001,
                 h_thiele_innes=-0.0454697, h_thiele_innes_error=0.00763896)
        self.assertGreater(go.rv_omega_sd(r), 2.0)
        lab = go.transit_label(r, ref_btjd=389.0)
        self.assertEqual(lab["transit_conj"], "")
        self.assertGreater(lab["rv_omega_sd_rad"], 2.0)
        # the labelled rows are well constrained
        self.assertLess(go.rv_omega_sd(DR3_ROWS[0]), 0.2)
        self.assertLess(go.rv_omega_sd(DR3_ROWS[2]), 0.2)
        self.assertEqual(go.rv_omega_sd(DR3_ROWS[3]), 0.0)
        # circular solution with H not significant: no label
        r3 = dict(DR3_ROWS[3], h_thiele_innes_error=0.02)
        self.assertEqual(go.transit_label(r3, ref_btjd=389.0)["transit_conj"], "")

    def test_rv_omega_signs(self):
        # C = a1 sin w sin i, H = a1 cos w sin i
        for w in (0.3, 1.9, -2.5, -0.7):
            row = {"c_thiele_innes": 0.1 * np.sin(w), "h_thiele_innes": 0.1 * np.cos(w),
                   "c_thiele_innes_error": 0.01, "h_thiele_innes_error": 0.01,
                   "eccentricity": 0.3, "eccentricity_error": 0.01,
                   "g_thiele_innes_error": 0.01}
            got, snr = go.rv_omega(row)
            self.assertAlmostEqual(got, w, places=9)
            self.assertAlmostEqual(snr, 10.0, places=6)
        self.assertTrue(np.isnan(go.rv_omega({"a_thiele_innes": 1.0})[0]))


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
