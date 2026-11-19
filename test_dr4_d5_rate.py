# SPDX-License-Identifier: Apache-2.0
"""Tests for dr4_d5_rate 0.1.0 (stdlib only; a fake TAP service, no network)."""
import csv
import json
import os
import shutil
import tempfile
import unittest

import dr4_d5_rate as dr
import dr4_fetch as df
import sb1_transit as st

ORB = list(dr.ORBIT_REQUIRED + dr.ORBIT_OPTIONAL)


def star(sid, P=3.0, K=5.0, G=11.0, plx=10.0, bprp=0.8, mass="0.9", rad="0.85",
         typ="SB1", sig="20"):
    return {"source_id": sid, "nss_solution_type": typ, "period": str(P),
            "semi_amplitude_primary": str(K), "eccentricity": "" if typ == "SB1C" else "0.1",
            "arg_periastron": "" if typ == "SB1C" else "30", "significance": sig,
            "ra": "10.0", "dec": "-5.0", "phot_g_mean_mag": str(G), "bp_rp": str(bprp),
            "parallax": str(plx), "parallax_error": "0.02", "ruwe": "1.0",
            "mass_flame": mass, "radius_flame": rad, "radius_gspphot": "", "logg_gspphot": "",
            "teff_gspphot": ""}


class FakeTap:
    def __init__(self, cols, orbits, xmatch=(), dr3_sb1=()):
        self.cols, self.orbits = cols, orbits
        self.xmatch, self.dr3_sb1 = list(xmatch), set(dr3_sb1)
        self.calls = []

    @staticmethod
    def _in(adql):
        return [x.strip() for x in adql.split(" IN (")[1].split(")")[0].split(",")]

    def __call__(self, adql, timeout=None, **kw):
        self.calls.append(adql)
        if "tap_schema.columns" in adql:
            tb = adql.split("table_name = '")[1].split("'")[0]
            return [{"column_name": c, "unit": "mas" if c == "angular_distance" else "",
                     "description": "t_peri desc" if c == "t_periastron" else ""}
                    for c in self.cols.get(tb, [])]
        if "SELECT TOP 1 *" in adql:
            return []
        if " AS o JOIN " in adql:
            tb = adql.split(" FROM ")[1].split(" AS o")[0]
            lo = float(adql.split("o.period >= ")[1].split(" ")[0])
            hi = float(adql.split("o.period < ")[1].split(" ")[0])
            return [dict(r) for r in self.orbits.get(tb, []) if lo <= float(r["period"]) < hi]
        if "dr3_neighbourhood" in adql:
            ids = set(self._in(adql))
            return [dict(r) for r in self.xmatch if r["new_id"] in ids]
        if " AS n WHERE " in adql:
            return [{"source_id": i, "nss_solution_type": "SB1"} for i in self._in(adql)
                    if i in self.dr3_sb1]
        raise AssertionError("unexpected query: " + adql)


def dr4_cols(supp=None):
    c = {"gaiadr4.nss_two_body_orbit": ORB, "gaiadr4.rvs_two_body_orbit": ORB,
         "gaiadr4.gaia_source": list(dr.SOURCE_REQUIRED),
         "gaiadr4.astrophysical_parameters": list(dr.AP_REQUIRED + dr.AP_OPTIONAL),
         "gaiadr4.dr3_neighbourhood": ["source_id", "dr3_source_id", "angular_distance",
                                       "magnitude_difference"],
         "gaiadr3.nss_two_body_orbit": ORB}
    if supp is not None:
        c["gaiadr4.nss_two_body_orbit_supp"] = supp
    return c


def dr4_fake(**kw):
    nss = [star("101"), star("102"), star("103", G=10.0, plx=1.0, bprp=1.5, mass="", rad=""),
           star("104", typ="SB1C", sig="5"), star("106", K=30.0)]
    rvs = [star("104", sig="50"), star("105"), star("107", P=6.0)]
    xm = [{"new_id": "101", "old_id": "9101", "angular_distance": "12", "magnitude_difference": "0.01"},
          {"new_id": "102", "old_id": "9102", "angular_distance": "8", "magnitude_difference": "0.02"},
          {"new_id": "105", "old_id": "9105", "angular_distance": "1500", "magnitude_difference": "0.1"}]
    return FakeTap(kw.get("cols", dr4_cols()),
                   {"gaiadr4.nss_two_body_orbit": nss, "gaiadr4.rvs_two_body_orbit": kw.get("rvs", rvs)},
                   xm, {"9102", "9105"})


class TestPick(unittest.TestCase):
    def test_table_rank_beats_type_and_significance(self):
        a = dict(star("1", typ="SB1C", sig="1"), _table="gaiadr4.nss_two_body_orbit")
        b = dict(star("1", sig="99"), _table="gaiadr4.rvs_two_body_orbit")
        self.assertIs(dr.pick_row([b, a]), a)

    def test_type_then_significance_never_period(self):
        a = dict(star("1", typ="SB1C", sig="99", P=2.0), _table="gaiadr4.nss_two_body_orbit")
        b = dict(star("1", sig="1", P=9.0), _table="gaiadr4.nss_two_body_orbit")
        c = dict(star("1", sig="5", P=4.0), _table="gaiadr4.nss_two_body_orbit")
        self.assertIs(dr.pick_row([a, b, c]), c)

    def test_flags(self):
        dwarf = star("1")
        self.assertEqual(dr.flag_of(dwarf, st.star_physics(dwarf)), "")
        clamped = star("2", G=10.0, plx=1.0, bprp=1.5, mass="", rad="")
        self.assertEqual(dr.flag_of(clamped, st.star_physics(clamped)), "clamped")
        giant = star("3", G=11.0, plx=2.0, bprp=1.3, mass="", rad="")
        self.assertEqual(dr.flag_of(giant, st.star_physics(giant)), "giant_cmd")
        # a Gaia radius is always kept, even on the giant branch
        g2 = star("4", G=11.0, plx=2.0, bprp=1.3, mass="1.2", rad="2.0")
        self.assertEqual(dr.flag_of(g2, st.star_physics(g2)), "")

    def test_hash_order_free(self):
        self.assertEqual(dr.pool_hash(["3", "1", "2"]), dr.pool_hash(["1", "2", "3 "]))
        self.assertNotEqual(dr.pool_hash(["1", "2"]), dr.pool_hash(["1", "2", "3"]))


class TestPool(unittest.TestCase):
    def test_dr4_pool(self):
        q = dr4_fake()
        rows, recs, info = dr.build_pool("dr4", st, q, log=lambda *a: None)
        self.assertEqual(sorted(r["source_id"] for r in rows), ["101", "104", "105", "107"])
        self.assertEqual(info["rows_by_table"], {"gaiadr4.nss_two_body_orbit": 5,
                                                 "gaiadr4.rvs_two_body_orbit": 3})
        self.assertEqual(info["sources_in_several_rows"], 1)
        self.assertEqual(info["eligible_rows_sb1_transit_count"], 7)
        self.assertEqual(info["eligible_before_flags"], 6)
        self.assertEqual(info["rejected"], {"m2sini": 1})
        self.assertEqual(info["radius_flag_removed"], {"clamped": 1})
        self.assertEqual(info["dr3_status"], {"NEW": 1, "IN_DR3": 1, "NEW_NO_DR3_MATCH": 3})
        self.assertEqual(info["pool"], 4)
        self.assertEqual(info["pool_by_table"], {"gaiadr4.nss_two_body_orbit": 2,
                                                 "gaiadr4.rvs_two_body_orbit": 2})
        self.assertEqual(info["pool_sha256"], dr.pool_hash(["101", "104", "105", "107"]))
        r104 = [r for r in rows if r["source_id"] == "104"][0]
        self.assertEqual(r104["_table"], "gaiadr4.nss_two_body_orbit")
        self.assertEqual(r104["nss_solution_type"], "SB1C")
        # the flagged giant never reaches the in-DR3 queries. Only the cross-match queries
        # themselves ("... dr3_neighbourhood AS x WHERE ... IN (...)") are checked; the
        # TAP_SCHEMA column lookup for the same table also names it but has no ID list.
        xq = [c for c in q.calls if "dr3_neighbourhood AS x WHERE" in c]
        self.assertTrue(xq)
        self.assertTrue(all("103" not in FakeTap._in(c) for c in xq))
        self.assertTrue(any("101" in FakeTap._in(c) for c in xq))
        self.assertIn("t_peri desc", json.dumps(info["t_periastron_meta"]))

    def test_missing_ap_column_stops(self):
        cols = dr4_cols()
        cols["gaiadr4.astrophysical_parameters"] = ["source_id", "mass_flame", "radius_gspphot",
                                                    "logg_gspphot"]
        with self.assertRaises(df.SchemaError) as cm:
            dr.build_pool("dr4", st, dr4_fake(cols=cols), log=lambda *a: None)
        self.assertIn("radius_flame", str(cm.exception))

    def test_missing_rvs_table_stops(self):
        cols = dr4_cols()
        del cols["gaiadr4.rvs_two_body_orbit"]
        with self.assertRaises(df.SchemaError):
            dr.build_pool("dr4", st, dr4_fake(cols=cols), log=lambda *a: None)

    def test_supp_table_used_if_complete_stops_if_not(self):
        with self.assertRaises(df.SchemaError):
            dr.build_pool("dr4", st, dr4_fake(cols=dr4_cols(supp=["source_id", "period"])),
                          log=lambda *a: None)
        q = dr4_fake(cols=dr4_cols(supp=ORB))
        rows, recs, info = dr.build_pool("dr4", st, q, log=lambda *a: None)
        self.assertEqual(info["rows_by_table"]["gaiadr4.nss_two_body_orbit_supp"], 0)
        self.assertEqual(info["pool"], 4)

    def test_no_sb1_rows_stops(self):
        with self.assertRaises(dr.PoolError) as cm:
            dr.build_pool("dr4", st, dr4_fake(rvs=[]), log=lambda *a: None)
        self.assertEqual(cm.exception.code, 4)

    def test_row_cap_splits_never_truncates(self):
        old = dr.ROW_CAP
        dr.ROW_CAP = 2
        try:
            q = dr4_fake()
            q.orbits["gaiadr4.nss_two_body_orbit"] = [star("201", P=1.1), star("202", P=1.2),
                                                       star("203", P=1.3)]
            found = dr.check_tables("dr4", q)
            got = dr.fetch_bin("dr4", "gaiadr4.nss_two_body_orbit", found, 1.0, 1.5, q,
                               lambda *a: None)
        finally:
            dr.ROW_CAP = old
        self.assertEqual(sorted(r["source_id"] for r in got), ["201", "202", "203"])

    def test_dr3_identity_and_rehearsal(self):
        cols = {"gaiadr3.nss_two_body_orbit": ORB, "gaiadr3.gaia_source": list(dr.SOURCE_REQUIRED),
                "gaiadr3.astrophysical_parameters": list(dr.AP_REQUIRED + dr.AP_OPTIONAL)}
        q = FakeTap(cols, {"gaiadr3.nss_two_body_orbit": [star("1"), star("2"), star(
            "3", G=10.0, plx=1.0, bprp=1.5, mass="", rad="")]}, (), {"1", "2", "3"})
        rows, recs, info = dr.build_pool("dr3", st, q, log=lambda *a: None)
        self.assertEqual(rows, [])
        self.assertEqual(info["dr3_status"], {"IN_DR3": 2})
        old = dr.EXPECTED_DR3_POOL
        dr.EXPECTED_DR3_POOL = 3
        try:
            self.assertEqual(dr.rehearsal_checks(info), {"RH1_pool_reproduced": True,
                                                         "RH2_all_in_dr3": True,
                                                         "RH3_flags_counted": True})
        finally:
            dr.EXPECTED_DR3_POOL = old
        rows, recs, info = dr.build_pool("dr3", st, q, all_new=True, log=lambda *a: None)
        self.assertEqual(sorted(r["source_id"] for r in rows), ["1", "2"])

    def test_query_is_sb1_robust_clause(self):
        found = dr.check_tables("dr4", dr4_fake())
        sql = dr.sample_query("dr4", "gaiadr4.rvs_two_body_orbit", found, 1, 1.5)
        for part in ("o.nss_solution_type IN ('SB1','SB1C')", "o.period >= 1.0", "o.period < 1.5",
                     "s.phot_g_mean_mag <= 13", "o.period < 15440",
                     "LEFT OUTER JOIN gaiadr4.astrophysical_parameters AS a"):
            self.assertIn(part, sql)


def chunk_dir(base, name, ids, h, hit_id=None):
    d = os.path.join(base, name)
    os.makedirs(d)
    keys = ["source_id", "status", "control", "sensitivity", "star_hit", "star_hit_v1", "hit_class",
            "p_transit", "ctrl_0.8541_hit", "ctrl_0.8541_class", "ctrl_0.9137_hit",
            "ctrl_0.9137_class", "P", "m1", "m2_class", "abs_g", "bp_rp", "r1", "toi", "tic",
            "phase_label"]
    rows = []
    for i, c in enumerate(("WASP-18 b", "TOI-2533 b", "TOI-1712 b")):
        rows.append({"source_id": "c%s%d" % (name, i), "status": "OK", "control": c,
                     "sensitivity": "1", "star_hit": "True", "p_transit": "0.1"})
    for i in ids:
        hit = i == hit_id
        rows.append({"source_id": i, "status": "OK", "control": "", "sensitivity": "1.0",
                     "star_hit": str(hit), "star_hit_v1": str(hit),
                     "hit_class": "SUBSTELLAR_SIZE" if hit else "", "p_transit": "0.1",
                     "ctrl_0.8541_hit": "False", "ctrl_0.8541_class": "",
                     "ctrl_0.9137_hit": "False", "ctrl_0.9137_class": "", "P": "3.0",
                     "m1": "1.0", "m2_class": "BD", "abs_g": "4.5", "bp_rp": "0.8",
                     "r1": "1.0", "toi": "", "tic": "1", "phase_label": "UNTIMED"})
    with open(os.path.join(d, "sb1_stars.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    with open(os.path.join(d, "d5_chunk_info.json"), "w") as fh:
        json.dump({"pool_sha256": h}, fh)
    return d


class TestGrade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_d5_rule(self):
        s = {"rho_substellar_size": {"rho": 0.1, "ci95": [0.05, 0.2]}}
        g = dr.d5_grade(s, 0.02, {"C1": {"pass": True}, "C2": {"pass": True}})
        self.assertTrue(g["pass"] and g["valid"] and g["lower_bound_above_dr3"])
        g = dr.d5_grade(s, 0.12, {"C1": {"pass": True}, "C2": {"pass": True}})
        self.assertFalse(g["pass"])
        g = dr.d5_grade(s, 0.02, {"C1": {"pass": True}, "C2": {"pass": False}})
        self.assertIsNone(g["pass"])
        self.assertFalse(g["valid"])

    def test_grade_end_to_end(self):
        a = chunk_dir(self.tmp, "k0", ["1", "2", "3", "4"], "h", hit_id="2")
        b = chunk_dir(self.tmp, "k1", ["5", "6", "7", "8"], "h")
        out = os.path.join(self.tmp, "out")
        rc = dr.main(["grade", "--chunk-dir", a, "--chunk-dir", b, "--rho-dr3", "0.02",
                      "--out-dir", out])
        self.assertEqual(rc, 0)
        g = json.load(open(os.path.join(out, "d5_grade.json")))
        # 1 substellar-size hit, E = 8 x 0.1 = 0.8 -> rho = 1.25
        self.assertAlmostEqual(g["rho_dr4_new"], 1.25, places=6)
        self.assertTrue(g["valid"])
        self.assertTrue(g["pass"])
        self.assertTrue(g["A1_noop"])
        self.assertEqual(g["pool_sha256"], "h")

    def test_grade_refuses_mixed_pools(self):
        a = chunk_dir(self.tmp, "k0", ["1"], "h1")
        b = chunk_dir(self.tmp, "k1", ["2"], "h2")
        rc = dr.main(["grade", "--chunk-dir", a, "--chunk-dir", b, "--rho-dr3", "0.02",
                      "--out-dir", os.path.join(self.tmp, "o")])
        self.assertEqual(rc, 5)

    def test_rho_dr3_from_combined(self):
        p = os.path.join(self.tmp, "c.json")
        with open(p, "w") as fh:
            json.dump({"amendment1": {"summary": {"rho_substellar_size": {"rho": 0.031}}}}, fh)
        self.assertAlmostEqual(dr.rho_dr3_from(p), 0.031)


if __name__ == "__main__":
    unittest.main()
