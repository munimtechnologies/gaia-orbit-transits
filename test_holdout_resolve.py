# SPDX-License-Identifier: Apache-2.0
"""Unit tests for holdout_resolve 0.1.0 (stdlib only). MV2 of Munim, Inc.; made with AI agents."""
import os
import unittest

import holdout_resolve as hr

HERE = os.path.dirname(os.path.abspath(__file__))


def row(sid, typ="SB1", ra=20.8, dec=38.4, P=7.95, K=27.0):
    return {"source_id": sid, "nss_solution_type": typ, "period": str(P), "eccentricity": "0.01",
            "k1": str(K), "ra": str(ra), "dec": str(dec), "phot_g_mean_mag": "11.9"}


class TestNames(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(hr.parse_name("J0011+63"), (0, 11, 1, 63))
        self.assertEqual(hr.parse_name("EBLM J0608−59"), (6, 8, -1, 59))
        self.assertEqual(hr.parse_name("J1219-39"), (12, 19, -1, 39))
        for bad in ("J011+63", "X0011+63", "J2511+63", "J0011*63"):
            with self.assertRaises(ValueError):
                hr.parse_name(bad)

    def test_box_north(self):
        lo, hi, dlo, dhi = hr.name_box("J0123+38")
        self.assertAlmostEqual(lo, 20.5)
        self.assertAlmostEqual(hi, 21.25)
        self.assertEqual((dlo, dhi), (37.0, 40.0))

    def test_box_south(self):
        _, _, dlo, dhi = hr.name_box("J1219-39")
        self.assertEqual((dlo, dhi), (-41.0, -38.0))

    def test_box_wraps(self):
        lo, hi, _, _ = hr.name_box("J0000+29")
        self.assertAlmostEqual(lo, 359.75)
        self.assertAlmostEqual(hi, 0.5)
        self.assertTrue(hr.ra_in(359.9, lo, hi))
        self.assertTrue(hr.ra_in(0.2, lo, hi))
        self.assertFalse(hr.ra_in(1.0, lo, hi))

    def test_period_window_and_adql(self):
        lo, hi = hr.period_window(10.0)
        self.assertAlmostEqual(lo, 9.97)
        self.assertAlmostEqual(hi, 10.03)
        q = hr.box_adql("J0123+38", 7.952946)
        self.assertIn("BETWEEN 7.9290872 AND 7.9768048", q)
        self.assertIn("g.dec BETWEEN 37.0000 AND 40.0000", q)
        self.assertNotIn("nss_solution_type = 'SB1'", q)   # all types fetched, SB1 chosen locally


class TestChoose(unittest.TestCase):
    def test_match(self):
        r = hr.choose("J0123+38", 7.952946, [row("323261744326472832", P=7.95003)])
        self.assertEqual(r["status"], "MATCH")
        self.assertEqual(r["source_id"], "323261744326472832")
        self.assertAlmostEqual(r["dP_frac"], (7.95003 - 7.952946) / 7.952946)

    def test_out_of_ra_box_ignored(self):
        r = hr.choose("J0123+38", 7.95, [row("1", ra=30.0)])
        self.assertEqual(r["status"], "NO_SB1")
        self.assertEqual(r["n_rows_in_box"], 0)

    def test_other_types_reported_not_used(self):
        r = hr.choose("J0123+38", 7.95, [row("1", typ="SB2"), row("2", typ="AstroSpectroSB1")])
        self.assertEqual(r["status"], "NO_SB1")
        self.assertEqual(r["other_types_in_box"], ["AstroSpectroSB1", "SB2"])

    def test_ambiguous_excluded(self):
        r = hr.choose("J0123+38", 7.95, [row("1"), row("2", ra=20.9)])
        self.assertEqual(r["status"], "AMBIGUOUS")
        self.assertEqual(r["source_id"], "")
        self.assertEqual(sorted(r["candidates"]), ["1", "2"])

    def test_rc1(self):
        res = {"J0123+38": {"source_id": "323261744326472832"},
               "J0719+25": {"source_id": "870991952855398656"}}
        self.assertTrue(hr.rc1(res)["pass"])
        res["J0719+25"]["source_id"] = ""
        self.assertFalse(hr.rc1(res)["pass"])


class TestInputTable(unittest.TestCase):
    def test_csv(self):
        cands = [os.path.join(HERE, "eblmxix_sample1_p13.csv"),
                 os.path.join(HERE, "data", "eblm-holdout", "eblmxix_sample1_p13.csv")]
        path = next((p for p in cands if os.path.exists(p)), cands[0])
        rows = hr.read_rows(path)
        self.assertEqual(len(rows), 28)
        names = [r["name"] for r in rows]
        self.assertEqual(len(set(names)), 28)
        roles = [r["role"] for r in rows]
        self.assertEqual(roles.count("resolver_control"), 2)
        self.assertEqual(roles.count("holdout"), 26)
        for r in rows:
            hr.parse_name(r["name"])
            self.assertLessEqual(float(r["P"]), 13.0)
            self.assertGreater(float(r["R2"]), 0.05)
            self.assertLess(float(r["e"]), 1.0)
        # the six systems of the failed first control set are never holdouts
        used = {"J0941-31", "J0540-17", "J0719+25", "J1522+42", "J1741+31", "J0123+38"}
        self.assertFalse(used & {r["name"] for r in rows if r["role"] == "holdout"})
        self.assertEqual(set(hr.RC1_EXPECT), {r["name"] for r in rows
                                              if r["role"] == "resolver_control"})


if __name__ == "__main__":
    unittest.main()
