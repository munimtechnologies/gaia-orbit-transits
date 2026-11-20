# SPDX-License-Identifier: Apache-2.0
"""Tests for qcut 0.1.0 (standard library only). MV2 of Munim, Inc.; made with AI agents. Apache-2.0."""
import math
import unittest

import qcut as qc


def qrow(sid="1", typ="SB1", eff="0.5", ng="25", sig="50", p="3.0", gof="1.0", csp="0.99", amp="20"):
    return {"source_id": sid, "nss_solution_type": typ, "efficiency": eff, "rv_n_good_obs_primary": ng,
            "significance": sig, "period": p, "goodness_of_fit": gof, "conf_spectro_period": csp,
            "rv_amplitude_robust": amp, "semi_amplitude_primary": "10"}


class TestRules(unittest.TestCase):
    def test_gold_pass_and_each_boundary(self):
        self.assertTrue(qc.is_gold(qrow()))
        self.assertTrue(qc.is_gold(qrow(eff="0.2", ng="20", sig="40", p="2.0")))
        self.assertFalse(qc.is_gold(qrow(eff="0.1999")))
        self.assertFalse(qc.is_gold(qrow(ng="19")))
        self.assertFalse(qc.is_gold(qrow(sig="39.99")))
        self.assertFalse(qc.is_gold(qrow(p="1.99")))
        self.assertFalse(qc.is_gold(qrow(eff="")))

    def test_gold_sb1_only(self):
        self.assertTrue(qc.is_gold(qrow(typ="SB1C")))
        self.assertFalse(qc.is_gold(qrow(typ="SB1C"), sb1_only=True))
        self.assertTrue(qc.is_gold(qrow(typ="SB1"), sb1_only=True))

    def test_tiers(self):
        self.assertEqual(qc.tier(5.0), "T1")
        self.assertEqual(qc.tier(9.999), "T1")
        self.assertEqual(qc.tier(10.0), "T2")
        self.assertEqual(qc.tier(19.99), "T2")
        self.assertEqual(qc.tier(20.0), "T3")
        self.assertEqual(qc.tier(500.0), "T3")
        self.assertEqual(qc.tier(float("nan")), "")

    def test_amp_ratio(self):
        self.assertAlmostEqual(qc.amp_ratio({"rv_amplitude_robust": "30"}, 10.0), 1.5)
        self.assertTrue(math.isnan(qc.amp_ratio({"rv_amplitude_robust": ""}, 10.0)))
        self.assertTrue(math.isnan(qc.amp_ratio({"rv_amplitude_robust": "30"}, 0.0)))

    def test_median(self):
        self.assertEqual(qc.median([3.0, 1.0, 2.0]), 2.0)
        self.assertEqual(qc.median([4.0, 1.0, 2.0, 3.0]), 2.5)
        self.assertEqual(qc.median([1.0, float("nan"), 3.0]), 2.0)
        self.assertTrue(math.isnan(qc.median([])))

    def test_binom_sf(self):
        self.assertAlmostEqual(qc.binom_sf(2, 3, 0.5), 0.5)
        self.assertEqual(qc.binom_sf(0, 3, 0.5), 1.0)
        self.assertEqual(qc.binom_sf(4, 3, 0.5), 0.0)
        self.assertAlmostEqual(qc.binom_sf(1, 1, 0.3), 0.3)

    def test_cond_test(self):
        t = qc.cond_test(0, 0.0, 10.0, 4, 0.0, 10.0)
        self.assertAlmostEqual(t["share_h0"], 0.5)
        self.assertAlmostEqual(t["p_one_sided"], 1.0 / 16.0)
        self.assertAlmostEqual(t["rho0"], 0.2)
        # false alarms only: rho0 clamps at 0, share follows the false-alarm split
        t = qc.cond_test(1, 3.0, 10.0, 1, 1.0, 10.0)
        self.assertEqual(t["rho0"], 0.0)
        self.assertAlmostEqual(t["share_h0"], 0.25)
        self.assertAlmostEqual(t["p_one_sided"], 1.0 - 0.75 ** 2)
        self.assertIsNone(qc.cond_test(0, 0.0, 1.0, 0, 0.0, 1.0)["p_one_sided"])

    def test_gold_label(self):
        self.assertEqual(qc.gold_label(5.0, 0.1, 0.1), "UNDERPOWERED")
        self.assertEqual(qc.gold_label(20.0, 0.3, 0.1), "GOLD_FAILS")
        self.assertEqual(qc.gold_label(20.0, 0.9, 0.6), "GOLD_PLAUSIBLE")
        self.assertEqual(qc.gold_label(20.0, 0.9, 0.3), "GOLD_MIXED")

    def test_adql_matches_sb1_transit_selection(self):
        s = qc.adql(1, 1.5)
        self.assertIn("o.nss_solution_type IN ('SB1','SB1C')", s)
        self.assertIn("o.period >= 1.0 AND o.period < 1.5", s)
        self.assertIn("s.phot_g_mean_mag <= 13.0", s)
        self.assertIn("o.semi_amplitude_primary*o.semi_amplitude_primary*o.semi_amplitude_primary*o.period < 15440.0", s)
        for col in ("o.efficiency", "o.rv_n_good_obs_primary", "o.significance", "o.goodness_of_fit",
                    "o.conf_spectro_period", "s.rv_amplitude_robust"):
            self.assertIn(col, s)
        self.assertEqual(qc.P_EDGES, (1, 1.5, 2, 3, 5, 8, 13))


class TestFetch(unittest.TestCase):
    def test_fetch_pool_dedups_and_checks_columns(self):
        header = ",".join(qc.NEEDED)

        def line(sid):
            return ",".join([sid, "SB1", "2.5", "10", "50", "0.5", "25", "1.0", "0.99", "20"])

        calls = []

        def fake(query):
            calls.append(query)
            if "o.period >= 1.0 " in query:
                return header + "\n" + line("1") + "\n" + line("2") + "\n"
            return header + "\n" + line("2") + "\n" + line("3%d" % len(calls)) + "\n"

        pool, dups, missing = qc.fetch_pool(query_fn=fake)
        self.assertEqual(len(calls), 6)
        self.assertEqual(dups, 5)                     # source 2 repeated in five later bins
        self.assertEqual(len(pool), 2 + 5)
        self.assertEqual(missing, [])

    def test_missing_column_reported(self):
        def fake(query):
            return "source_id,period\n1,2.0\n"
        pool, dups, missing = qc.fetch_pool(query_fn=fake)
        self.assertIn("efficiency", missing)

    def test_row_limit_split(self):
        header = "source_id,period\n"

        def fake(query):
            if "o.period >= 1.0 AND o.period < 1.5" in query:
                return header + "".join("%d,1.2\n" % i for i in range(2000))
            return header + "9,1.3\n"
        rows = qc.fetch_bin(1.0, 1.5, 0, fake)
        self.assertEqual(len(rows), 2)               # split into [1, 1.25) and [1.25, 1.5)


class FakeSC:
    """Minimal stand-in for sb1_combine 0.1.0 (one row = one star)."""
    @staticmethod
    def in_rate_sample(r):
        return r.get("status") == "OK"

    @staticmethod
    def rate_summary(rows):
        n_hit = sum(1 for r in rows if r.get("star_hit") == "True")
        n_sub = sum(1 for r in rows if r.get("star_hit") == "True" and r.get("hit_class") == "SUBSTELLAR_SIZE")
        E = sum(float(r["p_transit"]) * float(r["sensitivity"]) for r in rows)
        return {"n_rate_sample": len(rows), "n_hit": n_hit, "n_hit_substellar_size": n_sub,
                "n_control_hits_expected": 0.0, "n_control_hits_substellar_size": 0.0,
                "expected_if_all_real": E, "rho_all": FakeSC.rho(n_hit, 0.0, E),
                "rho_substellar_size": FakeSC.rho(n_sub, 0.0, E)}

    @staticmethod
    def rho(n, fa, E):
        if not E > 0:
            return {"rho": None, "ci95": [None, None]}
        return {"rho": (n - fa) / E, "ci95": [0.0, (n + 3.0) / E]}


class FakeIFL:
    CENTRAL = {"c": 0.5}
    FLOOR = {"c": 0.25}

    @staticmethod
    def prepare(rows):
        return [float(r["p_transit"]) * float(r["sensitivity"]) for r in rows], 0

    @staticmethod
    def expected(prep, scen):
        return sum(prep) * scen["c"]


def star(sid, cls, sig, hit=False, sub=False, p=0.2):
    return {"source_id": sid, "status": "OK", "m2_class": cls, "K": "10", "p_transit": str(p), "sensitivity": "1",
            "star_hit": "True" if hit else "False", "hit_class": "SUBSTELLAR_SIZE" if sub else "",
            "significance": str(sig)}


class TestAnalysisWiring(unittest.TestCase):
    def setUp(self):
        self.rows = ([star("a%d" % i, "BD", 5.0) for i in range(50)] +
                     [star("b%d" % i, "VLMS", 50.0, hit=(i < 6), sub=(i < 6)) for i in range(50)] +
                     [star("c%d" % i, "planet", 50.0) for i in range(5)] +
                     [dict(star("x", "BD", 5.0), status="SKIP")])
        self.qmap = {}
        for r in self.rows:
            self.qmap[r["source_id"]] = qrow(sid=r["source_id"], sig=r["significance"],
                                             eff="0.5", ng="25", p="3.0", amp="25")

    def test_attach_q1_q2(self):
        S, unmatched = qc.attach(self.rows, self.qmap, FakeSC)
        self.assertEqual(len(S), 105)
        self.assertEqual(unmatched, [])
        q1 = qc.q1(S, FakeSC, FakeIFL)
        g = q1["gold"]["in"]
        self.assertEqual(g["n_rate_sample"], 50)      # the VLMS stars (sig 50); planets excluded
        self.assertAlmostEqual(g["E_iso"], 10.0)
        self.assertAlmostEqual(g["E_pop_floor"], 2.5)
        self.assertEqual(q1["label"], "UNDERPOWERED")
        self.assertEqual(q1["all_classes_gold_n"], 55)
        q2 = qc.q2(S, FakeSC, FakeIFL)
        self.assertEqual(q2["tiers"]["T1"]["n_rate_sample"], 50)
        self.assertEqual(q2["tiers"]["T3"]["n_hit"], 6)
        self.assertAlmostEqual(q2["primary_test"]["p_one_sided"], 0.5 ** 6)
        self.assertTrue(q2["pass"])
        self.assertEqual(q2["label"], "RISES_WITH_SIGNIFICANCE")
        q3 = qc.q3(S, FakeSC, FakeIFL)
        self.assertIn("efficiency", q3)
        self.assertIn("amp_ratio", q3)
        self.assertEqual(qc.significance_agreement(S)["n_disagree"], 0)
        res = {"pool_rows": 106, "pool_dups": 0, "n_matched": 105, "n_unmatched": 0,
               "checks": {"RC1": [106, 6434, False]}, "Q1": q1, "Q2": q2, "Q3": q3}
        text = qc.report(res)
        self.assertIn("UNDERPOWERED", text)
        self.assertIn("RISES_WITH_SIGNIFICANCE", text)
        self.assertIn("amp_ratio", text)

    def test_unmatched(self):
        del self.qmap["a3"]
        S, unmatched = qc.attach(self.rows, self.qmap, FakeSC)
        self.assertEqual(unmatched, ["a3"])


if __name__ == "__main__":
    unittest.main()
