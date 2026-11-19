# SPDX-License-Identifier: Apache-2.0
"""Tests for inclination_floor 0.1.0 (MV2 of Munim, Inc.; made with AI agents). Standard library only."""
import math
import unittest

import inclination_floor as inf
import sb1_combine as sc


def brute_D(mu, m1, dens, n=4000):
    """Independent check: integrate the posterior over cos i directly, solving m(i) by bisection."""
    gm = inf.g(mu, m1)
    tot = 0.0
    h = 1.0 / n
    for k in range(n):
        c = (k + 0.5) * h
        s = math.sqrt(1.0 - c * c)
        target = gm / s ** 3
        if inf.g(m1, m1) < target:
            continue          # would need m > m1
        lo, hi = mu, m1
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if inf.g(mid, m1) < target:
                lo = mid
            else:
                hi = mid
        m = 0.5 * (lo + hi)
        tot += h * dens(m) / (inf.gprime(m, m1) * s ** 3)
    return tot


def row(sid, cls, mu, m1, p=0.1, sens=1.0, hit=False, sub=False):
    return {"source_id": sid, "status": "OK", "control": "", "sensitivity": str(sens), "m2_class": cls,
            "m2sini": str(mu), "m1": str(m1), "p_transit": str(p), "star_hit": str(hit),
            "hit_class": "SUBSTELLAR_SIZE" if sub else ("MODULATED" if hit else ""), "star_hit_v1": "False",
            "abs_g": "4.5", "bp_rp": "0.7", "r1": "1.0"}


class TestPopulation(unittest.TestCase):
    def test_normalisations(self):
        for sh in inf.BD_SHAPES:
            nd = inf.bd_norm(sh)
            n, tot = 20000, 0.0
            h = (inf.M_BD_HI - inf.M_BD_LO) / n
            for k in range(n):
                tot += h * inf.bd_unit_density(inf.M_BD_LO + (k + 0.5) * h, sh)
            self.assertAlmostEqual(tot, 1.0, places=4, msg=(sh, nd))
        for gm_ in inf.GAMMAS:
            m1, n, tot = 1.3, 20000, 0.0
            h = (m1 - 0.1 * m1) / n
            for k in range(n):
                tot += h * inf.star_unit_density(0.1 * m1 + (k + 0.5) * h, m1, gm_)
            self.assertAlmostEqual(tot, 1.0, places=4)

    def test_textbook_limit_bd_only(self):
        # m1 -> infinity, flat BDs only: c = 1 / (pi/2 - asin(mu / M_BD_HI))
        mu, m1 = 0.05, 1.0e4
        t = inf.star_terms(mu, m1)
        c = inf.c_factor(t, 0.0, 1.0, "flat", 0.0)
        self.assertAlmostEqual(c, 1.0 / (math.pi / 2 - math.asin(mu / inf.M_BD_HI)), delta=2e-3)

    def test_textbook_limit_mixed(self):
        mu, m1, fb, fs = 0.05, 1.0e4, 0.002, 0.04
        t = inf.star_terms(mu, m1)
        c = inf.c_factor(t, fs, fb, "flat", -1.0)
        a_bd = fb / inf.bd_norm("flat")
        d_bd = a_bd * (math.pi / 2 - math.asin(mu / inf.M_BD_HI))
        d_st = fs / (inf.q_norm(-1.0) * mu) * (math.cos(math.asin(mu / m1)) - math.cos(math.asin(mu / inf.M_BD_HI)))
        self.assertAlmostEqual(c / (a_bd / (d_bd + d_st)), 1.0, delta=3e-3)

    def test_against_bruteforce_finite_m1(self):
        mu, m1 = 0.05, 1.1
        for sh, gm_ in (("flat", 0.0), ("logflat", -1.0)):
            fb, fs = 0.002, 0.04

            def dens(m):
                return fb * inf.bd_unit_density(m, sh) + fs * inf.star_unit_density(m, m1, gm_)
            t = inf.star_terms(mu, m1)
            D = fb * t["S"]["bd_" + sh] + fs * t["S"]["star_%g" % gm_]
            self.assertAlmostEqual(D / brute_D(mu, m1, dens), 1.0, delta=1e-2)

    def test_c_monotone_in_desert(self):
        t = inf.star_terms(0.05, 1.0)
        cs = [inf.c_factor(t, 0.04, fb, "flat", 0.0) for fb in (1e-4, 1e-3, 1e-2)]
        self.assertTrue(cs[0] < cs[1] < cs[2])
        self.assertLess(inf.c_factor(t, 0.08, 0.002, "flat", 0.0), inf.c_factor(t, 0.02, 0.002, "flat", 0.0))

    def test_planet_and_bad_rows(self):
        t = inf.star_terms(0.005, 1.0)
        self.assertEqual(inf.c_factor(t, 0.04, 0.002, "flat", 0.0), 0.0)
        t = inf.star_terms(float("nan"), 1.0)
        self.assertEqual(inf.c_factor(t, 0.04, 0.002, "flat", 0.0), 0.0)


class TestSample(unittest.TestCase):
    def rows(self):
        rs = [row("b%d" % i, "BD", 0.03 + 0.0004 * i, 1.0, p=0.12) for i in range(100)]
        rs[0] = row("b0", "BD", 0.03, 1.0, p=0.12, hit=True, sub=True)
        rs += [row("v%d" % i, "VLMS", 0.085, 1.2, p=0.1) for i in range(20)]
        rs.append(row("b5", "BD", 0.05, 1.0, p=0.12))     # duplicate id: merge drops it
        return rs

    def test_expected_matches_sum(self):
        rows, dups = sc.merge([("k0", self.rows())])
        self.assertEqual(dups, 1)
        bd = inf.class_rows(rows, "BD")
        prep, skipped = inf.prepare(bd)
        self.assertEqual((len(prep), skipped), (100, 0))
        E = inf.expected(prep, inf.CENTRAL)
        E2 = sum(0.12 * inf.c_factor(inf.star_terms(sc.num(r["m2sini"]), 1.0), **inf.CENTRAL) for r in bd)
        self.assertAlmostEqual(E, E2, places=9)

    def test_analyse_and_grade(self):
        rows, _ = sc.merge([("k0", self.rows())])
        res = inf.analyse_class(rows, "BD")
        self.assertEqual(res["n_sub"], 1)
        self.assertAlmostEqual(res["E_iso"], 12.0, places=6)
        self.assertEqual(len(res["grid"]), 36)
        self.assertLess(res["floor"]["E_pop"], res["central"]["E_pop"])
        g = inf.grade(res)
        self.assertIn(g["label"], ("MOSTLY_SPURIOUS", "SPURIOUS_UNLESS_DRY_DESERT", "FACE_ON_SUFFICIENT"))
        # r*: at r*, E_pop equals the 95 % upper count
        r = res["r_star"]["flat_gamma0"]
        if not r["note"]:
            E = inf.expected(inf.prepare(inf.class_rows(rows, "BD"))[0],
                             {"f_star": 0.04, "f_bd": r["r_star"] * 0.04, "bd_shape": "flat", "gamma": 0.0})
            self.assertAlmostEqual(E, sc.garwood(1)[1], places=4)

    def test_grade_labels(self):
        def fake(up_c, up_f):
            return {"central": {"phi": {"ci95": [0.0, up_c]}}, "floor": {"phi": {"ci95": [0.0, up_f]}}, "grid": []}
        self.assertEqual(inf.grade(fake(0.1, 0.3))["label"], "MOSTLY_SPURIOUS")
        self.assertEqual(inf.grade(fake(0.1, 0.7))["label"], "SPURIOUS_UNLESS_DRY_DESERT")
        self.assertEqual(inf.grade(fake(0.6, 0.9))["label"], "FACE_ON_SUFFICIENT")

    def test_run_and_report(self):
        res = inf.run([("k0", self.rows(), None)], [])
        txt = inf.report(res)
        self.assertIn("Label:", txt)
        self.assertIn("amendment-1", txt)


if __name__ == "__main__":
    unittest.main()
