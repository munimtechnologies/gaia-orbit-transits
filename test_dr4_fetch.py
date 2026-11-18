# SPDX-License-Identifier: Apache-2.0
"""Tests for dr4_fetch.py (MV2 of Munim, Inc.; made with AI agents). Stdlib only, offline."""
import math
import unittest

import dr4_fetch as df


class TestAdql(unittest.TestCase):
    def test_xmatch_query(self):
        q = df.adql_xmatch("dr4", ["123", 456])
        self.assertIn("FROM gaiadr4.dr3_neighbourhood AS x", q)
        self.assertIn("x.dr3_source_id IN (123,456)", q)
        self.assertIn("x.source_id AS new_id", q)
        self.assertIn("x.dr3_source_id AS old_id", q)

    def test_bad_ids_refused(self):
        with self.assertRaises(ValueError):
            df.adql_xmatch("dr4", ["12; DROP"])

    def test_nss_and_columns(self):
        q = df.adql_nss("gaiadr4.nss_two_body_orbit", ["1", "2"], ["source_id", "period"])
        self.assertEqual(q, "SELECT n.source_id, n.period FROM gaiadr4.nss_two_body_orbit AS n "
                            "WHERE n.source_id IN (1,2)")
        self.assertIn("table_name = 'gaiadr4.dr3_neighbourhood'",
                      df.adql_columns("gaiadr4.dr3_neighbourhood"))

    def test_chunks(self):
        self.assertEqual([len(c) for c in df.chunks(range(320), 150)], [150, 150, 20])


class TestParse(unittest.TestCase):
    def test_csv(self):
        rows = df.parse_csv("source_id,period_error\n1,0.5\n")
        self.assertEqual(rows, [{"source_id": "1", "period_error": "0.5"}])
        self.assertEqual(df.parse_csv("source_id,period\n"), [])

    def test_html_refused(self):
        with self.assertRaises(df.TapError):
            df.parse_csv("<!DOCTYPE html><html>maintenance</html>")
        with self.assertRaises(df.TapError):
            df.parse_csv('<?xml version="1.0"?><VOTABLE><INFO name="QUERY_STATUS" '
                         'value="ERROR"/></VOTABLE>')

    def test_units(self):
        self.assertEqual(df.angular_mas("12", "mas"), 12.0)
        self.assertEqual(df.angular_mas("0.5", "arcsec"), 500.0)
        with self.assertRaises(ValueError):
            df.angular_mas("1", "furlong")


class TestMatch(unittest.TestCase):
    def test_single(self):
        self.assertEqual(df.pick_match([{"new_id": "9", "ang_mas": 3.0, "dmag": 0.01}]),
                         ("9", "ok"))

    def test_none(self):
        self.assertEqual(df.pick_match([{"new_id": "9", "ang_mas": 1500.0, "dmag": 0.0}]),
                         (None, "none"))
        self.assertEqual(df.pick_match([]), (None, "none"))

    def test_faint_neighbour_ok(self):
        c = [{"new_id": "9", "ang_mas": 900.0, "dmag": 4.0},
             {"new_id": "8", "ang_mas": 2.0, "dmag": 0.0}]
        self.assertEqual(df.pick_match(c), ("8", "ok"))

    def test_ambiguous(self):
        c = [{"new_id": "9", "ang_mas": 300.0, "dmag": 0.4},
             {"new_id": "8", "ang_mas": 2.0, "dmag": 0.0}]
        self.assertEqual(df.pick_match(c), (None, "ambiguous"))
        c[0]["dmag"] = float("nan")
        self.assertEqual(df.pick_match(c), (None, "ambiguous"))

    def test_merge_is_ambiguous(self):
        rows = [{"new_id": "77", "old_id": "1", "angular_distance": "5",
                 "magnitude_difference": "0"},
                {"new_id": "77", "old_id": "2", "angular_distance": "400",
                 "magnitude_difference": "0.1"},
                {"new_id": "78", "old_id": "3", "angular_distance": "2",
                 "magnitude_difference": "0"}]
        res = df.resolve_matches(rows, ["1", "2", "3", "4"], unit="mas")
        self.assertEqual(res["1"], (None, "ambiguous"))
        self.assertEqual(res["2"], (None, "ambiguous"))
        self.assertEqual(res["3"], ("78", "ok"))
        self.assertEqual(res["4"], (None, "none"))

    def test_dr3_identity(self):
        res, rows = df.fetch_matches("dr3", ["5", "6"], query=None)
        self.assertEqual(res, {"5": ("5", "ok"), "6": ("6", "ok")})
        self.assertEqual(rows, [])


class TestSolutions(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(df.solution_kind("Orbital"), "astro")
        self.assertEqual(df.solution_kind("OrbitalTargetedSearchValidated"), "astro")
        self.assertEqual(df.solution_kind('"AstroSpectroSB1"'), "astro")
        self.assertEqual(df.solution_kind("SB1"), "other")
        self.assertEqual(df.solution_kind("EclipsingSpectro"), "other")
        self.assertEqual(df.solution_kind("SomethingNew"), "unknown")

    def test_pick_by_type_not_period(self):
        rows = [{"nss_solution_type": "SB1", "period": "10"},
                {"nss_solution_type": "Orbital", "period": "500", "significance": "30"},
                {"nss_solution_type": "AstroSpectroSB1", "period": "50", "significance": "5"}]
        r, n, unk = df.pick_solution(rows)
        self.assertEqual(r["nss_solution_type"], "AstroSpectroSB1")
        self.assertEqual(n, 2)
        self.assertEqual(unk, [])

    def test_pick_significance(self):
        rows = [{"nss_solution_type": "Orbital", "period": "1", "significance": "8"},
                {"nss_solution_type": "Orbital", "period": "2", "significance": "40"}]
        self.assertEqual(df.pick_solution(rows)[0]["period"], "2")

    def test_none_and_unknown(self):
        r, n, unk = df.pick_solution([{"nss_solution_type": "SB1"},
                                      {"nss_solution_type": "NewKind"}])
        self.assertIsNone(r)
        self.assertEqual(n, 0)
        self.assertEqual(unk, ["NewKind"])


class TestGeometry(unittest.TestCase):
    def test_t_ref(self):
        self.assertAlmostEqual(df.t_ref_btjd(2016.0), 389.0)
        self.assertAlmostEqual(df.t_ref_btjd(2017.5), 936.875)

    def test_lim_circular(self):
        # Sun + Sun at P = 1 yr: a = 2^(1/3) AU, lim = 2 R_sun / a
        lim = df.lim_at(365.25, 1.0, 1.0, 1.0, 1.0, 0.0, 0.3)
        self.assertAlmostEqual(lim, 2 * 0.00465047 / 2 ** (1 / 3), places=9)
        self.assertTrue(math.isnan(df.lim_at(float("nan"), 1, 1, 1, 1, 0, 0)))

    def test_lim_eccentric(self):
        near = df.lim_at(100.0, 1.0, 0.5, 1.0, 0.5, 0.5, 0.0)      # periastron: closer
        far = df.lim_at(100.0, 1.0, 0.5, 1.0, 0.5, 0.5, math.pi)   # apastron
        self.assertAlmostEqual(near / far, 3.0, places=9)


class TestDetectEvent(unittest.TestCase):
    def test_matches_window_rule(self):
        wins = {"t1": [(100.0, 1.0)], "t2": [(150.0, 2.0)]}
        clean = [(102.0, 12.0, 4.0), (153.0, 30.0, 4.0), (300.0, 99.0, 4.0)]
        b = df.detect_event(clean, wins, 200.0, 3.0)
        self.assertEqual(b[4], "t2")
        self.assertAlmostEqual(b[3], 153.0)
        self.assertAlmostEqual(b[1], 1.5)
        self.assertAlmostEqual(b[2], (3.0 * 2.0 + 4.0 / 48.0) / 2.0)

    def test_cap_at_quarter_period(self):
        wins = {"t1": [(100.0, 10.0)]}
        self.assertIsNone(df.detect_event([(108.0, 20.0, 4.0)], wins, 20.0, 9.0))
        b = df.detect_event([(104.0, 20.0, 4.0)], wins, 20.0, 9.0)
        self.assertAlmostEqual(b[2], 0.5)

    def test_none(self):
        self.assertIsNone(df.detect_event([], {"t1": [(1.0, 1.0)]}, 10.0, 3.0))


class TestSchemaCheck(unittest.TestCase):
    def _fake(self, tables):
        def q(adql):
            for t, cols in tables.items():
                if f"'{t}'" in adql:
                    return [{"column_name": c, "unit": "mas" if c == "angular_distance" else "",
                             "description": ""} for c in cols]
            return []
        return q

    def test_missing_column_stops(self):
        tables = {"gaiadr4.dr3_neighbourhood": ["source_id", "dr3_source_id",
                                                "angular_distance"],
                  "gaiadr4.nss_two_body_orbit": list(df.NSS_REQUIRED),
                  "gaiadr4.gaia_source": ["source_id", "ref_epoch"]}
        with self.assertRaises(df.SchemaError) as cm:
            df.check_schema("dr4", self._fake(tables))
        self.assertIn("gaiadr4.dr3_neighbourhood.magnitude_difference", str(cm.exception))
        self.assertIn("gaiadr4.dr3_neighbourhood", cm.exception.found)

    def test_complete(self):
        tables = {"gaiadr4.dr3_neighbourhood": ["source_id", "dr3_source_id",
                                                "angular_distance", "magnitude_difference"],
                  "gaiadr4.nss_two_body_orbit": list(df.NSS_REQUIRED) + ["significance"],
                  "gaiadr4.gaia_source": ["source_id", "ref_epoch"]}
        got = df.check_schema("dr4", self._fake(tables))
        self.assertEqual(got["gaiadr4.dr3_neighbourhood"]["angular_distance"]["unit"], "mas")
        self.assertEqual(got["gaiadr4.nss_two_body_orbit_supp"], {})

    def test_fetch_orbits_uses_available_columns(self):
        seen = []

        def q(adql):
            seen.append(adql)
            return [{"source_id": "5", "nss_solution_type": "Orbital", "period": "10"}]
        avail = {"gaiadr4.nss_two_body_orbit": {c: {} for c in ("source_id", "period",
                                                                "nss_solution_type")},
                 "gaiadr4.nss_two_body_orbit_supp": {}}
        got = df.fetch_orbits("dr4", ["5", None, ""], avail, q)
        self.assertEqual(len(seen), 1)
        self.assertIn("n.source_id, n.nss_solution_type, n.period", seen[0])
        self.assertEqual(got["5"][0]["_table"], "gaiadr4.nss_two_body_orbit")


if __name__ == "__main__":
    unittest.main()
