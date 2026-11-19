# SPDX-License-Identifier: Apache-2.0
"""Tests for dr4_wobble 0.1.0 (standard library only). MV2 of Munim, Inc.; made with AI agents."""
import math
import random
import unittest

import dr4_wobble as dw

J2017_5_NS = (2017.5 - 2010.0) * dw.NS_PER_JYEAR


def synth(a=1.0, inc=88.0, omega=40.0, Omega=110.0, P=50.0, e=0.3, tp=100.0, n=140,
          noise=0.05, seed=1, colour=True):
    """Transits with a 5-parameter motion (+ colour) and a photocentre orbit."""
    rng = random.Random(seed)
    A, B, F, G = dw.campbell_to_ti(a, inc, omega, Omega)
    out = []
    for _ in range(n):
        T = rng.uniform(-2.9, 2.6)                  # years from J2017.5
        t_ns = J2017_5_NS + T * dw.NS_PER_JYEAR
        th = rng.uniform(0, 360)
        s, c = math.sin(math.radians(th)), math.cos(math.radians(th))
        pf = rng.uniform(-1, 1)
        col = rng.uniform(-0.05, 0.05) if colour else float("nan")
        X, Y = dw.xy_elliptic(dw.t_dr3_days(t_ns), P, e, tp)
        w = (0.5 * s - 0.3 * c + 10.0 * pf + 5.0 * T * s - 3.0 * T * c
             + (2.0 * col if colour else 0.0)
             + (B * X + G * Y) * s + (A * X + F * Y) * c + rng.gauss(0, noise))
        out.append({"t_ns": t_ns, "theta": th, "pf": pf, "colour": col, "w": w,
                    "sigma": noise, "n_ccd": 8, "excess": 0.0})
    return out, {"P": P, "e": e, "tp": tp}


class TestGeometry(unittest.TestCase):
    def test_kepler(self):
        for e in (0.0, 0.3, 0.9):
            for M in (0.1, 1.0, 3.0, 5.5):
                E = dw.kepler_E(M, e)
                self.assertAlmostEqual(E - e * math.sin(E), M, places=10)

    def test_ti_roundtrip(self):
        for inc in (5.0, 60.0, 88.0, 120.0):
            A, B, F, G = dw.campbell_to_ti(2.5, inc, 33.0, 210.0)
            a, ci = dw.ti_to_a_cosi(A, B, F, G)
            self.assertAlmostEqual(a, 2.5, places=9)
            self.assertAlmostEqual(ci, math.cos(math.radians(inc)), places=9)

    def test_time_zero_points(self):
        self.assertAlmostEqual(dw.t_years(0.0), -7.5, places=12)
        self.assertAlmostEqual(dw.t_years(J2017_5_NS), 0.0, places=12)
        # J2016.0 is 6 Julian years after 2010.0
        self.assertAlmostEqual(dw.t_dr3_days(6.0 * dw.NS_PER_JYEAR), 0.0, places=6)


class TestFit(unittest.TestCase):
    def test_edge_on_orbit_detected(self):
        tr, orb = synth()
        r = dw.fit_source(tr, orb)
        self.assertEqual(r["status"], "OK")
        self.assertTrue(r["colour_column"])
        self.assertGreater(r["dchi2"], 1000)
        self.assertTrue(r["detected"])
        self.assertAlmostEqual(r["a0_mas"], 1.0, delta=0.05)
        self.assertLess(abs(r["cos_i"]), 0.15)
        self.assertTrue(r["edge_on"])
        self.assertGreater(r["sigma_cos_i"], 0)

    def test_face_on_not_edge_on(self):
        tr, orb = synth(inc=15.0)
        r = dw.fit_source(tr, orb)
        self.assertTrue(r["detected"])
        self.assertFalse(r["edge_on"])
        self.assertAlmostEqual(abs(r["cos_i"]), math.cos(math.radians(15.0)), delta=0.03)

    def test_no_orbit_not_detected(self):
        for seed in (2, 3, 4):
            tr, orb = synth(a=0.0, seed=seed)
            r = dw.fit_source(tr, orb)
            self.assertEqual(r["status"], "OK")
            self.assertLess(r["dchi2"], dw.DCHI2_DET)
            self.assertFalse(r["detected"])

    def test_excess_noise_lowers_dchi2(self):
        tr, orb = synth(a=0.2, noise=0.05)
        r0 = dw.fit_source(tr, orb, excess=0.0)
        r1 = dw.fit_source(tr, orb, excess=0.3)
        self.assertLess(r1["dchi2"], r0["dchi2"])
        self.assertAlmostEqual(r1["dchi2_no_excess_noise"], r0["dchi2"], places=6)

    def test_too_few(self):
        tr, orb = synth(n=10)
        self.assertEqual(dw.fit_source(tr, orb)["status"], "TOO_FEW_TRANSITS")

    def test_no_colour(self):
        tr, orb = synth(colour=False)
        r = dw.fit_source(tr, orb)
        self.assertFalse(r["colour_column"])
        self.assertTrue(r["detected"])


HEADER = ("source_id,obs_time_bary_corr,centroid_pos_al,centroid_pos_error_al,scan_pos_angle,"
          "parallax_factor_al,colour_factor_al,obs_time_tcb,used_by_agis_al,used_by_agis_al,"
          "agis_source_excess_noise,ccd_proc_flags,ipd_error_al,nu_eff_used_in_astrometry")
ROW1 = ('3937211745905473024,100000000.0,"(1.0, 2.0, 2.2, NaN)","(0.5, 0.1, 0.1, 0.1)",'
        '"(10.0, 10.0, 10.0, 10.0)",0.3,0.01,'
        '"(237000000000000000, 237000004000000000, 237000008000000000, 0)",'
        '"(false, true, true, true)","(false, false, false, false)",0.08,'
        '"(0, 0, 0, 0)","(0.1, 0.1, 0.1, 0.1)",1.6')
ROW2 = ('3937211745905473024,,"(NaN, NaN, NaN, NaN)","(NaN, NaN, NaN, NaN)",'
        '"(NaN, NaN, NaN, NaN)",0.3,0.01,"(0, 0, 0, 0)",'
        '"(false, false, false, false)","(false, false, false, false)",0.08,'
        '"(0, 0, 0, 0)","(NaN, NaN, NaN, NaN)",1.6')


class TestReaders(unittest.TestCase):
    def test_esa_csv_layout(self):
        rows = dw.read_csv_rows("\n".join([HEADER, ROW1, ROW2]))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["source_id"], "3937211745905473024")
        self.assertEqual(rows[0]["used_by_agis_al"], [False, True, True, True])
        self.assertIn("used_by_agis_al.1", rows[0])
        tr = dw.to_transits(rows)
        self.assertEqual(list(tr), ["3937211745905473024"])
        t = tr["3937211745905473024"]
        self.assertEqual(len(t), 1)                     # the empty transit is dropped
        self.assertEqual(t[0]["n_ccd"], 2)              # NaN centroid and unused CCD dropped
        self.assertAlmostEqual(t[0]["w"], 2.1, places=9)
        self.assertAlmostEqual(t[0]["sigma"], math.sqrt(1 / 200.0), places=9)
        self.assertAlmostEqual(t[0]["theta"], 10.0, places=9)
        self.assertAlmostEqual(t[0]["t_ns"], 237000006000000000 + 100000000.0, delta=1e3)

    def test_missing_column_stops(self):
        rows = dw.read_csv_rows("\n".join([HEADER, ROW1]))
        for r in rows:
            del r["colour_factor_al"]
        with self.assertRaises(dw.SchemaError):
            dw.to_transits(rows)

    def test_exploded_rows_need_transit_id(self):
        base = {"source_id": "7", "obs_time_tcb": 2.37e17, "obs_time_bary_corr": 1e8,
                "scan_pos_angle": 30.0, "parallax_factor_al": 0.1, "colour_factor_al": 0.0,
                "centroid_pos_al": 1.0, "centroid_pos_error_al": 0.2, "used_by_agis_al": True,
                "agis_source_excess_noise": 0.0}
        with self.assertRaises(dw.SchemaError):
            dw.to_transits([dict(base), dict(base)])
        rows = [dict(base, transit_id=1), dict(base, transit_id=1, centroid_pos_al=3.0),
                dict(base, transit_id=2)]
        tr = dw.to_transits(rows)["7"]
        self.assertEqual(len(tr), 2)
        self.assertEqual(sorted(d["n_ccd"] for d in tr), [1, 2])
        self.assertIn(2.0, [round(d["w"], 9) for d in tr])

    def test_parse_cell(self):
        self.assertEqual(dw.parse_cell("(1, 2)"), [1.0, 2.0])
        self.assertTrue(math.isnan(dw.parse_cell("NaN")))
        self.assertIsNone(dw.parse_cell(""))
        self.assertIs(dw.parse_cell("true"), True)


def res(ecl, det, edge, a0r=1.0):
    return {"status": "OK", "eclipsing": ecl, "detected": det, "edge_on": edge, "a0_ratio": a0r}


class TestGrade(unittest.TestCase):
    def test_spurious(self):
        rs = [res(True, True, True) for _ in range(50)]
        rs += [res(False, i < 20, True) for i in range(100)]
        g = dw.grade(rs, n_boot=300)
        self.assertTrue(g["W0"])
        self.assertAlmostEqual(g["D_ratio"], 0.2)
        self.assertTrue(g["W1"])
        self.assertEqual(g["outcome"], "SPURIOUS_ORBITS")
        self.assertLess(g["D_ratio_ci95"][0], 0.2)
        self.assertGreater(g["D_ratio_ci95"][1], 0.2)

    def test_understated(self):
        rs = [res(True, True, True) for _ in range(50)]
        rs += [res(False, i < 95, i < 20) for i in range(100)]
        g = dw.grade(rs, n_boot=300)
        self.assertTrue(g["W2"])
        self.assertTrue(g["W3"])
        self.assertEqual(g["outcome"], "UNDERSTATED_INCLINATION_ERRORS")

    def test_mixed(self):
        rs = [res(True, True, True) for _ in range(50)]
        rs += [res(False, i < 75, i < 70) for i in range(100)]
        self.assertEqual(dw.grade(rs, n_boot=300)["outcome"], "MIXED_OR_INCONCLUSIVE")

    def test_w0_fail(self):
        rs = [res(True, i < 25, True) for i in range(50)]
        rs += [res(False, i < 20, True) for i in range(100)]
        g = dw.grade(rs, n_boot=300)
        self.assertFalse(g["W0"])
        self.assertEqual(g["outcome"], "W0_FAILED_NOT_INTERPRETED")

    def test_not_ok_rows_excluded(self):
        rs = [res(True, True, True) for _ in range(10)] + [res(False, True, True)]
        rs.append({"status": "NO_MATCH", "eclipsing": False})
        g = dw.grade(rs, n_boot=100)
        self.assertEqual(g["n_ok"], 11)
        self.assertEqual(g["n_not_ok"], 1)


if __name__ == "__main__":
    unittest.main()
