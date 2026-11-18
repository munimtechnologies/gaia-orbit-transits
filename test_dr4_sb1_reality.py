# SPDX-License-Identifier: Apache-2.0
"""Stdlib tests for dr4_sb1_reality.py (MV2 of Munim, Inc.; made with AI agents)."""
import argparse
import csv
import gzip
import io
import json
import math
import os
import random
import re
import shutil
import sys
import tarfile
import tempfile
import types
import unittest
import zipfile

import dr4_sb1_reality as R


# ---------------------------------------------------------------- fakes
def fake_st():
    st = types.ModuleType("sb1_transit")
    st.G_MAX = 13.0
    st.KP_SERVER_MAX = 15440.0
    st.COLS = "o.source_id, o.period, o.semi_amplitude_primary"
    st.AP_COLS = ""
    st.FROM = ("FROM gaiadr3.nss_two_body_orbit AS o JOIN gaiadr3.gaia_source AS s "
               "ON s.source_id = o.source_id")
    st.AP_JOIN = ""
    st.star_physics = lambda r: {"P": float(r["period"]), "K": float(r["semi_amplitude_primary"]),
                                 "m1": float(r.get("m1", 1.0)), "m2sini": 0.05}
    st.eligible = lambda r, ph: (True, "")
    return st


DR3 = [  # source_id, P, K, m1
    {"source_id": "101", "nss_solution_type": "SB1", "period": "2.0", "period_error": "0.0001",
     "semi_amplitude_primary": "5.0", "semi_amplitude_primary_error": "0.2", "m1": "1.0"},
    {"source_id": "102", "nss_solution_type": "SB1", "period": "3.0", "period_error": "0.0002",
     "semi_amplitude_primary": "2.0", "semi_amplitude_primary_error": "0.3", "m1": "1.6"},
    {"source_id": "103", "nss_solution_type": "SB1C", "period": "4.0", "period_error": "0.001",
     "semi_amplitude_primary": "1.5", "semi_amplitude_primary_error": "0.4", "m1": "1.0"},
    {"source_id": "104", "nss_solution_type": "SB1", "period": "6.0", "period_error": "0.001",
     "semi_amplitude_primary": "4.0", "semi_amplitude_primary_error": "0.4", "m1": "1.3"},
]
NSS_COLS = list(R.SB1_REQUIRED) + ["eccentricity", "significance"]
XM_COLS = ["source_id", "dr3_source_id", "angular_distance", "magnitude_difference"]
# DR4: 101 -> 9101 same orbit; 102 -> 9102 at the 1-day alias of 3 d (0.75 d);
# 103 -> 9103 no orbit (epochs flat); 104 unmatched.
DR4_NSS = [
    {"source_id": "9101", "nss_solution_type": "SB1", "period": "2.00005", "period_error": "0.00005",
     "semi_amplitude_primary": "5.1", "semi_amplitude_primary_error": "0.1", "significance": "40"},
    {"source_id": "9102", "nss_solution_type": "SB1", "period": "0.75", "period_error": "0.00001",
     "semi_amplitude_primary": "2.0", "semi_amplitude_primary_error": "0.1", "significance": "30"},
]
XM = [{"new_id": "9101", "old_id": "101", "angular_distance": "3.0", "magnitude_difference": "0.01"},
      {"new_id": "9102", "old_id": "102", "angular_distance": "2.0", "magnitude_difference": "0.02"},
      {"new_id": "9103", "old_id": "103", "angular_distance": "1.0", "magnitude_difference": "0.0"}]


def _in_ids(adql):
    m = re.search(r"IN \(([\d,]+)\)", adql)
    return set(m.group(1).split(",")) if m else set()


def make_query(schema, nss_cols=None, rvs_cols=None, rvs_rows=None):
    nss_cols = NSS_COLS if nss_cols is None else nss_cols
    rel = "gaiadr4" if schema == "dr4" else "gaiadr3"

    def q(adql, timeout=None, **kw):
        a = adql.lower()
        if "tap_schema.columns" in a:
            t = re.search(r"table_name = '([^']+)'", adql).group(1)
            cols = {"%s.nss_two_body_orbit" % rel: nss_cols,
                    "gaiadr4.rvs_two_body_orbit": rvs_cols or [],
                    "gaiadr4.dr3_neighbourhood": XM_COLS}.get(t, [])
            return [{"column_name": c, "unit": "mas" if c == "angular_distance" else ""}
                    for c in cols]
        if a.startswith("select top 1 *"):
            return []
        if "join gaiadr3.gaia_source" in a:
            m = re.search(r"o\.period >= ([\d.]+) and o\.period < ([\d.]+)", a)
            lo, hi = float(m.group(1)), float(m.group(2))
            return [dict(r) for r in DR3 if lo <= float(r["period"]) < hi]
        if "dr3_neighbourhood" in a:
            ids = _in_ids(adql)
            return [dict(r) for r in XM if r["old_id"] in ids]
        if "nss_two_body_orbit_supp" in a:
            return []
        if "rvs_two_body_orbit" in a:
            ids = _in_ids(adql)
            return [dict(r) for r in (rvs_rows or []) if r["source_id"] in ids]
        if "nss_two_body_orbit" in a:
            ids = _in_ids(adql)
            src = DR4_NSS if schema == "dr4" else DR3
            return [dict(r) for r in src if r["source_id"] in ids]
        raise AssertionError("unexpected query " + adql)
    return q


def zip_of(files):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return b.getvalue()


def epoch_csv(sid, P, K, n, flag_two=False, rng=None):
    lines = ["source_id,obs_time,radial_velocity,radial_velocity_error,outlier_status,emission_lines"]
    for i in range(n):
        t = 0.37 * i + 0.11 * (i % 3)
        v = 12.0 + K * math.sin(2 * math.pi * t / P + 0.4)
        out, em = "0", "false"
        if flag_two and i == 0:
            out = "1"
        if flag_two and i == 1:
            em = "true"
        lines.append("%s,%.5f,%.5f,0.5,%s,%s" % (sid, t, v, out, em))
    return "\n".join(lines) + "\n"


def make_http(types_listed, data_files):
    calls = []

    def http(url, data=None, timeout=300, tries=4):
        calls.append(url)
        if url.startswith(R.LINKS_URL):
            body = "".join('<TD>https://x/data?RETRIEVAL_TYPE=%s&amp;ID=1</TD>' % t for t in types_listed)
            return ("<VOTABLE>%s</VOTABLE>" % body).encode()
        if url == R.DATA_URL:
            return zip_of(data_files)
        raise AssertionError(url)
    http.calls = calls
    return http


def args(out, schema, **kw):
    d = dict(schema=schema, out_dir=out, retrieval_type=None, time_col=None,
             suspend_epochs=False, allow_pool_change=True, max_sources=0)
    d.update(kw)
    return argparse.Namespace(**d)


# ---------------------------------------------------------------- tests
class Pure(unittest.TestCase):
    def test_k_from_ch(self):
        K, sK = R.k_from_ch(0.0, 0.01, 10.0, 0.0, 0.001, 0.001)
        self.assertAlmostEqual(K, 2 * math.pi * 0.01 * R.AU_KM / (10 * 86400.0), 9)
        self.assertAlmostEqual(K, 10.879, 2)
        self.assertAlmostEqual(sK, K * 0.1, 6)
        Ke, _ = R.k_from_ch(0.006, 0.008, 10.0, 0.6)
        self.assertAlmostEqual(Ke, K / 0.8, 6)
        self.assertTrue(math.isnan(R.k_from_ch("", 0.01, 10.0)[0]))

    def test_rv_orbit(self):
        o = R.rv_orbit({"period": "2", "semi_amplitude_primary": "3", "nss_solution_type": "SB1"})
        self.assertEqual((o["K"], o["K_src"]), (3.0, "semi_amplitude_primary"))
        o = R.rv_orbit({"period": "10", "c_thiele_innes": "0", "h_thiele_innes": "0.01",
                        "nss_solution_type": "AstroSpectroSB1"})
        self.assertEqual(o["K_src"], "thiele_innes_CH")
        self.assertIsNone(R.rv_orbit({"period": "10", "a_thiele_innes": "1"}))
        self.assertIsNone(R.rv_orbit({"period": "", "semi_amplitude_primary": "3"}))

    def test_pick_rv(self):
        rows = [{"period": "2", "semi_amplitude_primary": "3", "nss_solution_type": "SB2",
                 "significance": "90", "_table": "gaiadr4.nss_two_body_orbit"},
                {"period": "5", "semi_amplitude_primary": "4", "nss_solution_type": "SB1",
                 "significance": "10", "_table": "gaiadr4.nss_two_body_orbit"},
                {"period": "2", "semi_amplitude_primary": "3", "nss_solution_type": "SB1",
                 "significance": "99", "_table": "gaiadr4.nss_two_body_orbit_supp"}]
        o, n, supp = R.pick_rv(rows)
        self.assertEqual((o["P"], n, supp), (5.0, 3, False))
        o, n, supp = R.pick_rv(rows[2:])
        self.assertEqual((o["P"], supp), (2.0, True))
        self.assertEqual(R.pick_rv([]), (None, 0, False))
        rvs = {"period": "7", "semi_amplitude_primary": "4", "_table": "gaiadr4.rvs_two_body_orbit"}
        o, n, supp = R.pick_rv(rows[2:] + [rvs])        # rvs table beats _supp
        self.assertEqual((o["P"], n, supp), (7.0, 2, False))
        o, _, _ = R.pick_rv(rows[1:] + [rvs])           # main table beats rvs table
        self.assertEqual(o["P"], 5.0)
        self.assertEqual([R.table_rank(t) for t in ("gaiadr4.nss_two_body_orbit",
                          "gaiadr4.rvs_two_body_orbit", "gaiadr4.nss_two_body_orbit_supp")], [0, 1, 2])
        self.assertTrue(R.rvs_table_ok({"source_id": 1, "period": 1, "semi_amplitude_primary": 1}))
        self.assertTrue(R.rvs_table_ok({"source_id": 1, "period": 1, "c_thiele_innes": 1,
                                        "h_thiele_innes": 1}))
        self.assertFalse(R.rvs_table_ok({"source_id": 1, "period": 1, "k1": 1}))

    def test_alias_and_labels(self):
        al = R.alias_periods(2.0)
        for want in (4.0, 1.0, 2.0 / 3.0):
            self.assertTrue(any(abs(a - want) < 1e-9 for a in al), want)
        self.assertTrue(R.is_alias(3.0, 0.75))           # 1/(1/3 + 1) = 0.75
        self.assertTrue(R.is_alias(3.0, 6.0))
        self.assertTrue(R.is_alias(5.0, 1.0 / (0.2 - 1 / 63.0)))
        self.assertFalse(R.is_alias(3.0, 4.4))
        d3 = {"P": 3.0, "sP": 0.0002, "K": 2.0, "sK": 0.3}
        self.assertEqual(R.orbit_label(d3, {"P": 3.0001, "sP": 0.0001, "K": 2.2, "sK": 0.1}), "CONFIRMED")
        self.assertEqual(R.orbit_label(d3, {"P": 3.004, "sP": 0.0001, "K": 2.2, "sK": 0.1}), "CONFIRMED")
        self.assertEqual(R.orbit_label(d3, {"P": 3.0001, "sP": 0.0001, "K": 4.0, "sK": 0.1}), "CHANGED")
        self.assertEqual(R.orbit_label(d3, {"P": 0.75, "sP": 0.0001, "K": 2.0, "sK": 0.1}), "ALIAS")
        self.assertEqual(R.orbit_label(d3, {"P": 4.4, "sP": 0.0001, "K": 2.0, "sK": 0.1}), "CHANGED")

    def test_source_label(self):
        self.assertEqual(R.source_label("ambiguous", "CONFIRMED", 50, True), "UNTESTABLE")
        self.assertEqual(R.source_label("ok", "ALIAS", 0, True), "ALIAS")
        self.assertEqual(R.source_label("ok", "", 10, True), "DROPPED")
        self.assertEqual(R.source_label("ok", "", 9, True), "UNTESTABLE")
        self.assertEqual(R.source_label("ok", "", None, False), "DROPPED")
        self.assertEqual(R.source_label("none", "", None, False), "UNTESTABLE")

    def test_epoch_counts(self):
        base = {"radial_velocity": "3", "radial_velocity_error": "0.5", "outlier_status": "0",
                "emission_lines": "false"}
        self.assertTrue(R.epoch_counts(base))
        self.assertTrue(R.epoch_counts(dict(base, outlier_status="")))
        self.assertFalse(R.epoch_counts(dict(base, outlier_status="2")))
        self.assertFalse(R.epoch_counts(dict(base, emission_lines="True")))
        self.assertFalse(R.epoch_counts(dict(base, radial_velocity="")))
        self.assertFalse(R.epoch_counts(dict(base, radial_velocity_error="0")))

    def test_pick_time_col(self):
        self.assertEqual(R.pick_time_col(["source_id", "rv_obs_time", "radial_velocity"]), "rv_obs_time")
        self.assertEqual(R.pick_time_col(["obs_time_tcb", "time_flag", "transit_time"]), "obs_time_tcb")
        self.assertEqual(R.pick_time_col(["a_time", "b_time"], "b_time"), "b_time")
        with self.assertRaises(R.EpochSchemaError):
            R.pick_time_col(["a_time", "b_time"])
        with self.assertRaises(R.EpochSchemaError):
            R.pick_time_col(["radial_velocity"])

    def test_fit_circular(self):
        rng = random.Random(3)
        t = [rng.uniform(0, 1000) for _ in range(30)]
        v = [7.0 + 4.0 * math.cos(2 * math.pi * x / 3.7 - 1.0) for x in t]
        f = R.fit_circular(t, v, [0.5] * 30, 3.7)
        self.assertAlmostEqual(f["K"], 4.0, 6)
        self.assertAlmostEqual(f["gamma"], 7.0, 6)
        self.assertGreater(f["sK"], 0.0)
        self.assertEqual(R.epoch_label(f, 4.2, 0.3), "EPOCH_OK")
        self.assertEqual(R.epoch_label(f, 9.0, 0.3), "EPOCH_DIFF")
        flat = R.fit_circular(t, [7.0 for _ in t], [0.5] * 30, 3.7)
        self.assertEqual(R.epoch_label(flat, 4.0, 0.3), "EPOCH_FLAT")
        self.assertIsNone(R.fit_circular([1, 2, 3], [1, 2, 3], [1, 1, 1], 2.0))
        self.assertEqual(R.epoch_label(None, 1, 1), "EPOCH_NOFIT")
        # error inflation by sqrt(chi2_red) when the scatter exceeds the quoted errors
        big = R.fit_circular(t, [7.0 + 4.0 * math.cos(2 * math.pi * x / 3.7) + rng.gauss(0, 2.0)
                                 for x in t], [0.5] * 30, 3.7)
        self.assertGreater(big["chi2_red"], 4.0)
        self.assertGreater(big["sK"], 0.5 * math.sqrt(2.0 / 30) * 1.5)

    def test_wilson(self):
        lo, hi = R.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, 3)
        self.assertAlmostEqual(hi, 0.7634, 3)
        self.assertEqual(R.wilson(0, 0), [None, None])

    def test_grades(self):
        recs = ([{"label": "CONFIRMED", "K3": 5.0, "m1": 1.0}] * 30
                + [{"label": "CHANGED", "K3": 1.0, "m1": 1.0}] * 30
                + [{"label": "CONFIRMED", "K3": 1.0, "m1": 1.6}] * 2
                + [{"label": "DROPPED", "K3": 1.0, "m1": 1.6}] * 8
                + [{"label": "UNTESTABLE", "K3": 1.0, "m1": 1.0}] * 5)
        g = R.grade_tables(recs, len(recs))
        self.assertEqual(g["D1"]["value"]["n_testable"], 70)
        self.assertTrue(g["R0"]["pass"])
        self.assertTrue(g["D1"]["pass"])
        self.assertTrue(g["D2"]["pass"])
        self.assertTrue(g["D4"]["pass"])
        self.assertIn("(S)", R.reading(dict(g, D3={"pass": True})))
        self.assertIn("(N)", R.reading(dict(g, D3={"pass": False})))
        self.assertIn("not yet", R.reading(g))

    def test_grade_d3(self):
        recs = [{"source_id": str(i), "label": "CONFIRMED" if i < 10 else "CHANGED"} for i in range(40)]
        rows = [{"source_id": str(i), "control": "", "hit": i < 6} for i in range(40)]
        rows.append({"source_id": "3", "control": "", "hit": True})       # duplicate dropped

        def rate(rs):
            n = len(rs)
            h = sum(1 for r in rs if r["hit"])
            E = 0.1 * n
            return {"n_rate_sample": n, "rho_substellar_size": h / E if E else float("nan"),
                    "rho_substellar_size_ci95": [0.5 * h / E if E else float("nan"), 2 * h / E if E else 0]}
        d = R.grade_d3(recs, rows, rate, 0.05)
        self.assertEqual(d["n_rate_all"], 40)
        self.assertEqual(d["n_rate_conf"], 10)
        self.assertAlmostEqual(d["rho_conf"], 6.0)
        self.assertTrue(d["pass"])


class Transport(unittest.TestCase):
    def test_members_and_parse(self):
        z = zip_of({"a.csv": "source_id,x\n1,2\n", "inner.zip": zip_of({"b.csv": "source_id,x\n3,4\n"})})
        names = sorted(n for n, _ in R._members(z))
        self.assertEqual(names, ["a.csv", "b.csv"])
        b = io.BytesIO()
        with tarfile.open(fileobj=b, mode="w:gz") as t:
            data = b"# %ECSV 1.0\n# ---\nsource_id,x\n5,6\n"
            info = tarfile.TarInfo("c.ecsv")
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
        (name, text), = list(R._members(b.getvalue()))
        self.assertEqual(R.parse_table_text(text), [{"source_id": "5", "x": "6"}])
        (name, text), = list(R._members(gzip.compress(b"source_id,x\n7,8\n")))
        self.assertEqual(R.parse_table_text(text)[0]["x"], "8")
        with self.assertRaises(R.df.TapError):
            R.parse_table_text("<html>down</html>")

    def test_choose_rv_type(self):
        self.assertEqual(R.choose_rv_type(["EPOCH_PHOTOMETRY", "RVS_EPOCH_PARAMETERS"])[0],
                         "RVS_EPOCH_PARAMETERS")
        self.assertIsNone(R.choose_rv_type(["EPOCH_PHOTOMETRY", "RVS"])[0])
        self.assertIsNone(R.choose_rv_type(["EPOCH_RV", "RADIAL_VELOCITY_EPOCH"])[0])
        self.assertEqual(R.choose_rv_type(["EPOCH_RV", "X"], "X")[0], "X")
        self.assertIsNone(R.choose_rv_type(["EPOCH_RV"], "Y")[0])

    def test_fetch_epoch_rows(self):
        http = make_http([], {"9101.csv": epoch_csv("9101", 2.0, 5.0, 3)})
        got = R.fetch_epoch_rows("Gaia DR4", "RVS_EPOCH", ["9101"], http)
        self.assertEqual(len(got["9101"]), 3)
        with self.assertRaises(ValueError):
            R.fetch_epoch_rows("Gaia DR4", "RVS_EPOCH", list(range(501)), http)
        http = make_http([], {"x.csv": "obs_time,radial_velocity\n1,2\n"})
        with self.assertRaises(R.EpochSchemaError):
            R.fetch_epoch_rows("Gaia DR4", "RVS_EPOCH", ["1"], http)


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._old = sys.modules.get("sb1_transit")
        sys.modules["sb1_transit"] = fake_st()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        if self._old is None:
            sys.modules.pop("sb1_transit", None)
        else:
            sys.modules["sb1_transit"] = self._old

    def _summary(self):
        with open(os.path.join(self.tmp, "sb1_reality_summary.json")) as fh:
            return json.load(fh)

    def test_dr4(self):
        http = make_http(["EPOCH_PHOTOMETRY", "RVS_EPOCH_PARAMETERS"],
                         {"9101.csv": epoch_csv("9101", 2.0, 5.0, 15),
                          "9103.csv": epoch_csv("9103", 4.0, 0.0, 14, flag_two=True)})
        rc = R.run(args(self.tmp, "dr4"), query=make_query("dr4"), http=http)
        self.assertEqual(rc, 0)
        s = self._summary()
        self.assertEqual(s["labels"], {"CONFIRMED": 1, "ALIAS": 1, "CHANGED": 0, "DROPPED": 1,
                                       "UNTESTABLE": 1})
        self.assertTrue(s["epochs_active"])
        self.assertEqual(s["epoch_labels"].get("EPOCH_OK"), 1)
        self.assertEqual(s["epoch_labels"].get("EPOCH_FLAT"), 1)
        with open(os.path.join(self.tmp, "sb1_reality_records.csv"), newline="") as fh:
            recs = {r["source_id"]: r for r in csv.DictReader(fh)}
        self.assertEqual(recs["103"]["n_epochs"], "12")
        self.assertEqual(recs["104"]["match_status"], "none")
        with open(os.path.join(self.tmp, "confirmed_ids.txt")) as fh:
            self.assertEqual(fh.read().split(), ["101"])
        dl = json.load(open(os.path.join(self.tmp, "datalink_found.json")))
        self.assertEqual(dl["retrieval_type"], "RVS_EPOCH_PARAMETERS")
        self.assertEqual(dl["time_col"], "obs_time")

    def test_dr4_rvs_table(self):
        http = make_http(["RVS_EPOCH_PARAMETERS"], {})
        rvs_rows = [{"source_id": "9103", "period": "4.0005", "semi_amplitude_primary": "1.4"}]
        q = make_query("dr4", rvs_cols=["source_id", "period", "semi_amplitude_primary"],
                       rvs_rows=rvs_rows)
        self.assertEqual(R.run(args(self.tmp, "dr4"), query=q, http=http), 0)
        s = self._summary()
        self.assertEqual(s["labels"]["CONFIRMED"], 2)
        self.assertEqual(s["labels"]["DROPPED"], 0)
        self.assertEqual(s["orbit_table"].get("gaiadr4.rvs_two_body_orbit"), 1)
        q = make_query("dr4", rvs_cols=["source_id", "period", "k1"])
        self.assertEqual(R.run(args(self.tmp, "dr4"), query=q, http=http), 4)

    def test_dr4_suspended(self):
        http = make_http(["EPOCH_PHOTOMETRY"], {})
        self.assertEqual(R.run(args(self.tmp, "dr4"), query=make_query("dr4"), http=http), 6)
        rc = R.run(args(self.tmp, "dr4", suspend_epochs=True), query=make_query("dr4"), http=http)
        self.assertEqual(rc, 0)
        s = self._summary()
        self.assertFalse(s["epochs_active"])
        self.assertEqual(s["labels"]["DROPPED"], 1)

    def test_exit_codes(self):
        http = make_http(["RVS_EPOCH_PARAMETERS"], {})
        self.assertEqual(R.run(args(self.tmp, "dr4", allow_pool_change=False),
                               query=make_query("dr4"), http=http), 3)
        cols = [c for c in NSS_COLS if c != "semi_amplitude_primary_error"]
        self.assertEqual(R.run(args(self.tmp, "dr4"), query=make_query("dr4", cols), http=http), 4)
        found = json.load(open(os.path.join(self.tmp, "schema_found.json")))
        self.assertIn("gaiadr4.nss_two_body_orbit", found)
        bad = make_http(["RVS_EPOCH_PARAMETERS"], {"9101.csv": "source_id,obs_time,radial_velocity\n9101,1,2\n"})
        self.assertEqual(R.run(args(self.tmp, "dr4"), query=make_query("dr4"), http=bad), 4)

        def down(adql, **kw):
            raise R.df.TapError("down")
        self.assertEqual(R.run(args(self.tmp, "dr4"), query=down, http=http), 2)

    def test_dr3_rehearsal(self):
        phot = "source_id,transit_id,band,time,mag\n101,1,G,1700.1,12.3\n101,2,G,1701.2,12.31\n"
        http = make_http(["EPOCH_PHOTOMETRY", "XP_SAMPLED"], {"101.csv": phot})
        rc = R.run(args(self.tmp, "dr3"), query=make_query("dr3"), http=http)
        self.assertEqual(rc, 0)
        s = self._summary()
        self.assertEqual(s["labels"]["CONFIRMED"], 4)
        rh = s["rehearsal"]
        self.assertFalse(rh["RH1_pool_reproduced"])      # 4 fake stars, not 6,434
        self.assertTrue(rh["RH2_all_matched"])
        self.assertTrue(rh["RH3_all_confirmed"])
        self.assertTrue(rh["RH4_datalink_plumbing"])
        self.assertFalse(s["epochs_active"])

    def test_dr3_rehearsal_datalink_broken(self):
        def http(url, data=None, **kw):
            raise R.df.TapError("no datalink")
        rc = R.run(args(self.tmp, "dr3"), query=make_query("dr3"), http=http)
        self.assertEqual(rc, 0)
        s = self._summary()
        self.assertTrue(s["rehearsal"]["RH3_all_confirmed"])
        self.assertFalse(s["rehearsal"]["RH4_datalink_plumbing"])


if __name__ == "__main__":
    unittest.main()
