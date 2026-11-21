# SPDX-License-Identifier: Apache-2.0
# Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents working in his name).
"""Tests for dr4_rows 0.1.0. numpy tests skip when numpy is missing (stdlib-only runner)."""
import math
import random
import unittest

import dr4_rows as d

try:
    import numpy as np
    HAVE_NP = True
except ImportError:  # pragma: no cover
    np = None
    HAVE_NP = False

try:
    import gaia_orbits as go
    HAVE_GO = HAVE_NP
except Exception:  # noqa: BLE001
    go = None
    HAVE_GO = False


class TestStdlib(unittest.TestCase):
    def test_version(self):
        self.assertEqual(d.VERSION, "0.1.0")

    def test_kind(self):
        self.assertEqual(d.dr4_kind("Orbital"), "orbital")
        self.assertEqual(d.dr4_kind('"OrbitalPoorlyConstrained"'), "orbital")
        self.assertEqual(d.dr4_kind("AstroSpectroSB1"), "astrospectrosb1")
        self.assertIsNone(d.dr4_kind("OrbitalAlternative"))
        self.assertIsNone(d.dr4_kind("EclipsingBinary"))
        self.assertIsNone(d.dr4_kind(None))

    def test_orders(self):
        self.assertEqual(len(d.DR4_ORDER["orbital"]), 12)
        self.assertEqual(len(d.DR3_ORDER["orbital"]), 12)
        self.assertEqual(len(d.DR4_ORDER["astrospectrosb1"]), 14)
        self.assertEqual(len(d.DR3_ORDER["astrospectrosb1"]), 15)

    def test_query_templates(self):
        q = d.DR4_NSS_QUERY.format(schema="gaiadr4", gmax=14.5, cosi="X", cosi_server=0.2,
                                   extra="")
        self.assertIn("gaiadr4.nss_two_body_orbit", q)
        self.assertIn("n.correlations AS corr_vec_dr4", q)
        self.assertIn("n.gof AS goodness_of_fit", q)
        self.assertIn("ABS(COS(RADIANS(n.inclination))) < 0.2", q)
        self.assertIn("/*CHUNK:n.source_id*/", q)
        for t in d.DR3_ONLY_SELECTS:
            self.assertNotIn(t, q)
        e = d.DR4_EB_QUERY.format(schema="gaiadr4", cosi="X", cosi_server=0.2)
        self.assertIn("gaiadr4.vari_eclipsing_binary", e)
        self.assertIn("/*CHUNK:v.source_id*/", e)

    def test_campbell_edge_on_face(self):
        A, B, F, G = d.campbell_to_ti(1.0, 0.0, 0.0, math.pi / 2)
        self.assertAlmostEqual(A, 1.0)
        self.assertAlmostEqual(B, 0.0)
        self.assertAlmostEqual(F, 0.0)
        self.assertAlmostEqual(G, 0.0)

    def test_jacobian_finite_difference(self):
        rnd = random.Random(7)
        for _ in range(20):
            p = [rnd.uniform(0.2, 3.0), rnd.uniform(-3, 3), rnd.uniform(0, 3), rnd.uniform(0.2, 2.9)]
            J = d.ti_jacobian(*p)
            for c in range(4):
                h = 1e-6
                up = list(p)
                dn = list(p)
                up[c] += h
                dn[c] -= h
                fu, fd = d.campbell_to_ti(*up), d.campbell_to_ti(*dn)
                for r in range(4):
                    num = (fu[r] - fd[r]) / (2 * h)
                    self.assertAlmostEqual(J[r][c], num, places=6)

    def test_parse_vec(self):
        self.assertEqual(d.parse_vec('"(0.1, -0.2, NaN)"')[:2], [0.1, -0.2])
        self.assertTrue(math.isnan(d.parse_vec("[0.1 NaN]")[1]))
        self.assertIsNone(d.parse_vec(""))
        self.assertIsNone(d.parse_vec("null"))

    def test_passthrough(self):
        r = {"source_id": 5}
        self.assertIs(d.convert_row(r), r)
        self.assertNotIn("dr4_ti_check", r)

    def test_gate_empty(self):
        self.assertEqual(d.gate(d.summarise([{"source_id": 1}])), "")


def _row(kind, w=40.0, W=120.0, i=88.0, a=0.9, e=0.3, P=180.0, flip=False, corr=True):
    names = d.DR4_ORDER[kind]
    n = len(names)
    rng = np.random.default_rng(11)
    M = rng.standard_normal((n, n))
    C = M @ M.T + n * np.eye(n)
    s = np.sqrt(np.diag(C))
    R = C / np.outer(s, s)
    vals = {"semi_major_axis": a, "arg_periastron": w, "pos_ascending_node": W,
            "inclination": i, "eccentricity": e, "period": P, "t_periastron": -10.0,
            "semi_amplitude_primary": 2.0, "center_of_mass_velocity": 3.0}
    errs = {"semi_major_axis": 0.02, "arg_periastron": 2.0, "pos_ascending_node": 1.0,
            "inclination": 0.7, "eccentricity": 0.03, "period": 0.5, "t_periastron": 2.0,
            "semi_amplitude_primary": 0.1, "center_of_mass_velocity": 0.2}
    sd = [errs.get(k, 0.0) for k in names]
    row = {"source_id": 42, "nss_solution_type": "Orbital" if kind == "orbital"
           else "AstroSpectroSB1"}
    if corr:
        row["corr_vec_dr4"] = d.vec_from_corr(R.tolist(), sd)
    for k in names:
        if k in vals:
            row[k] = vals[k]
        row[k + "_error"] = errs.get(k, float("nan"))
    ti = d.campbell_to_ti(a, w * d.DEG, W * d.DEG, i * d.DEG)
    for k, v in zip(d.TI_KEYS, ti):
        row[k] = -v if flip else v
        row[k + "_error"] = 0.02
    return row, R, np.array(sd)


@unittest.skipUnless(HAVE_NP, "numpy missing")
class TestNumpy(unittest.TestCase):
    def test_corr_pack_roundtrip(self):
        n = 5
        rng = np.random.default_rng(3)
        M = rng.standard_normal((n, n))
        C = M @ M.T + np.eye(n)
        s = np.sqrt(np.diag(C))
        R = C / np.outer(s, s)
        vec = d.parse_vec(d.vec_from_corr(R.tolist(), [1.0] * n))
        R2 = d.corr_from_vec(vec, n)
        self.assertTrue(np.allclose(R, R2, atol=1e-12))
        self.assertIsNone(d.corr_from_vec(vec[:-1], n))

    def test_orbital_covariance_matches_jacobian(self):
        row, R4, sd4 = _row("orbital")
        r = d.convert_row(dict(row))
        self.assertEqual(r["dr4_ti_check"], "STANDARD")
        self.assertTrue(r["dr4_corr_used"])
        J = d.build_jacobian("orbital", {"semi_major_axis": 0.9, "arg_periastron": 40.0,
                                         "pos_ascending_node": 120.0, "inclination": 88.0})
        S3 = J @ (R4 * np.outer(sd4, sd4)) @ J.T
        names3 = d.DR3_ORDER["orbital"]
        for k in ("a_thiele_innes", "g_thiele_innes", "period", "eccentricity"):
            j = names3.index(k)
            self.assertAlmostEqual(r[k + "_error"], math.sqrt(S3[j, j]), places=12)
        R3 = d.corr_from_vec(d.parse_vec(r["corr_vec"]), 12)
        ia, ig = names3.index("a_thiele_innes"), names3.index("t_periastron")
        self.assertAlmostEqual(R3[ia, ig], S3[ia, ig] / math.sqrt(S3[ia, ia] * S3[ig, ig]),
                               places=12)
        # ra..pmdec have no errors -> NaN correlations
        self.assertTrue(math.isnan(d.parse_vec(r["corr_vec"])[0]))

    def test_flip_and_mismatch_detected(self):
        r = d.convert_row(dict(_row("orbital", flip=True)[0]))
        self.assertEqual(r["dr4_ti_check"], "OMEGA_PLUS_PI")
        row = _row("orbital")[0]
        row["b_thiele_innes"] += 0.1
        self.assertEqual(d.convert_row(row)["dr4_ti_check"], "MISMATCH")
        summ = d.summarise([r])
        self.assertNotEqual(d.gate(summ), "")

    def test_no_corr_gate(self):
        rows = [d.convert_row(dict(_row("orbital", corr=False)[0])) for _ in range(3)]
        self.assertFalse(rows[0]["dr4_corr_used"])
        self.assertIn("correlation", d.gate(d.summarise(rows)))

    def test_sb1_c_h(self):
        r = d.convert_row(dict(_row("astrospectrosb1", w=-70.0)[0]))
        self.assertAlmostEqual(math.atan2(r["c_thiele_innes"], r["h_thiele_innes"]),
                               -70.0 * d.DEG, places=12)
        s = d.a1sini_au(2.0, 180.0, 0.3)
        self.assertAlmostEqual(math.hypot(r["c_thiele_innes"], r["h_thiele_innes"]), s)
        # 2 km/s, 180 d, e 0.3 -> a1 sin i = 0.0315 AU
        self.assertAlmostEqual(s, 2.0 * 86400 * 180 * math.sqrt(0.91) / (2 * math.pi * d.AU_KM))
        self.assertGreater(r["c_thiele_innes_error"], 0)

    def test_sb1_jacobian_finite_difference(self):
        vals = {"semi_major_axis": 0.7, "arg_periastron": 25.0, "pos_ascending_node": 60.0,
                "inclination": 85.0, "semi_amplitude_primary": 3.0, "period": 50.0,
                "eccentricity": 0.2}
        J = d.build_jacobian("astrospectrosb1", vals)
        n4, n3 = d.DR4_ORDER["astrospectrosb1"], d.DR3_ORDER["astrospectrosb1"]

        def fwd(v):
            ti = d.campbell_to_ti(v["semi_major_axis"], v["arg_periastron"] * d.DEG,
                                  v["pos_ascending_node"] * d.DEG, v["inclination"] * d.DEG)
            s = d.a1sini_au(v["semi_amplitude_primary"], v["period"], v["eccentricity"])
            w = v["arg_periastron"] * d.DEG
            return dict(zip(d.TI_KEYS, ti), c_thiele_innes=s * math.sin(w),
                        h_thiele_innes=s * math.cos(w))
        for k in vals:
            h = 1e-6 * max(1.0, abs(vals[k]))
            up, dn = dict(vals), dict(vals)
            up[k] += h
            dn[k] -= h
            fu, fd = fwd(up), fwd(dn)
            for out in fu:
                num = (fu[out] - fd[out]) / (2 * h)
                self.assertAlmostEqual(J[n3.index(out), n4.index(k)], num, places=6,
                                       msg=f"d{out}/d{k}")


@unittest.skipUnless(HAVE_GO, "numpy or gaia_orbits missing")
class TestWithGaiaOrbits(unittest.TestCase):
    def test_param_order_matches(self):
        self.assertEqual(d.DR3_ORDER, go.PARAM_ORDER)

    def test_inverse_of_thiele_innes_to_elements(self):
        rnd = random.Random(5)
        for _ in range(50):
            a, w, W, i = (rnd.uniform(0.1, 5), rnd.uniform(0, 2 * math.pi),
                          rnd.uniform(0, math.pi), rnd.uniform(0.05, math.pi - 0.05))
            el = go.thiele_innes_to_elements(*d.campbell_to_ti(a, w, W, i))
            self.assertAlmostEqual(float(el["a"]), a, places=9)
            self.assertAlmostEqual(float(el["cosi"]), math.cos(i), places=9)
            back = d.campbell_to_ti(float(el["a"]), float(el["omega"]), float(el["Omega"]),
                                    math.acos(float(el["cosi"])))
            for x, y in zip(back, d.campbell_to_ti(a, w, W, i)):
                self.assertAlmostEqual(x, y, places=9)

    def test_sample_orbit_runs(self):
        r = d.convert_row(dict(_row("orbital")[0]))
        s = go.sample_orbit(r, 500, np.random.default_rng(0), ref_btjd=936.875)
        self.assertTrue(s["used_corr"])
        self.assertTrue(np.all(np.isfinite(s["t1"])))

    def test_rv_omega(self):
        r = d.convert_row(dict(_row("astrospectrosb1", w=130.0)[0]))
        w, snr = go.rv_omega(r)
        self.assertAlmostEqual(w, 130.0 * d.DEG, places=9)
        self.assertGreater(snr, 3)


if __name__ == "__main__":
    unittest.main()
