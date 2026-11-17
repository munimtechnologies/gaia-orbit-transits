# SPDX-License-Identifier: Apache-2.0
"""Offline tests of the Gaia ranking stage of run_search (no network)."""
import csv
import json
import os
import re
import shutil
import tempfile
import unittest

import numpy as np

import gaia_orbits as go
import run_search as rs
from test_gaia_orbits import DR3_ROWS

COLS = ["source_id", "nss_solution_type", "bit_index", "corr_vec", "period", "period_error",
        "t_periastron", "t_periastron_error", "eccentricity", "eccentricity_error",
        "a_thiele_innes", "a_thiele_innes_error", "b_thiele_innes", "b_thiele_innes_error",
        "f_thiele_innes", "f_thiele_innes_error", "g_thiele_innes", "g_thiele_innes_error",
        "c_thiele_innes", "c_thiele_innes_error", "h_thiele_innes", "h_thiele_innes_error",
        "nss_parallax", "nss_parallax_error", "significance", "goodness_of_fit",
        "ra", "dec", "phot_g_mean_mag", "bp_rp", "ruwe", "ref_epoch"]


def _fake_rows():
    out = []
    for i, r in enumerate(DR3_ROWS):
        d = {k: r.get(k, "") for k in COLS}
        for k in ("a_thiele_innes", "b_thiele_innes", "f_thiele_innes", "g_thiele_innes"):
            if k + "_error" not in r:
                d[k + "_error"] = 0.02
        for k, v in (("eccentricity_error", 0.02), ("period_error", 0.5),
                     ("t_periastron_error", 2.0)):
            if k not in r:
                d[k] = v
        for k in list(d):
            if d[k] is None:
                d[k] = ""
        d.update({"nss_parallax": 20.0, "nss_parallax_error": 0.05, "significance": 30.0,
                  "goodness_of_fit": 1.0, "ra": 10.0 * (i + 1), "dec": -5.0 * i,
                  "phot_g_mean_mag": 10.0, "bp_rp": 0.8, "ruwe": 3.0, "ref_epoch": 2016.0,
                  "bit_index": 65535})
        if i == 0:
            n = len(go.PARAM_ORDER["astrospectrosb1"])
            vec = np.zeros(n * (n - 1) // 2)
            vec[::7] = 0.3
            d["corr_vec"] = "(" + ", ".join(repr(float(x)) for x in vec) + ")"
        else:
            d["corr_vec"] = ""
        out.append(d)
    return out


class TestHelpers(unittest.TestCase):
    def test_ref_epochs(self):
        self.assertAlmostEqual(rs.ref_epoch_to_btjd(2016.0), 389.0, places=9)
        self.assertAlmostEqual(rs.ref_epoch_to_btjd(2017.5), 936.875, places=9)

    def test_query_builder(self):
        q = rs.build_nss_query("gaiadr3", 14.5, 0.2)
        self.assertIn("ABS(", q)
        self.assertIn("< 0.2", q)
        self.assertIn("n.corr_vec", q)
        self.assertIn("n.c_thiele_innes", q)
        self.assertIn("n.h_thiele_innes_error", q)
        self.assertNotIn("IN (SELECT", q)
        self.assertIn("/*CHUNK:n.source_id*/", q)
        q4 = rs.build_nss_query("gaiadr4", 13, 1.0, "gaiadr4.gaia_exoplanet_candidates")
        self.assertIn("FROM gaiadr4.nss_two_body_orbit", q4)
        self.assertIn("IN (SELECT source_id FROM gaiadr4.gaia_exoplanet_candidates)", q4)
        qi = rs.build_nss_query("gaiadr3", 17, 0.3, source_ids=[393581461455623296, 12])
        self.assertIn("AND n.source_id IN (393581461455623296,12)", qi)

    def test_read_csv_keeps_corr_vec_string(self):
        text = 'source_id,nss_solution_type,corr_vec,period\n' \
               '123,"Orbital","(0.1, NaN, -0.2)",55.5\n'
        rows = rs.read_csv_text(text)
        self.assertEqual(rows[0]["source_id"], 123)
        self.assertEqual(rows[0]["nss_solution_type"], "Orbital")
        self.assertEqual(go.parse_corr_vec(rows[0]["corr_vec"]).size, 3)
        self.assertEqual(rows[0]["period"], 55.5)

    def test_ari_corr_vec_braces(self):
        # the ARI Heidelberg mirror writes corr_vec as {a,b,...}
        text = 'source_id,nss_solution_type,corr_vec\n4116844801792861952,Orbital,"{-0.08,-0.70,0.25}"\n'
        v = go.parse_corr_vec(rs.read_csv_text(text)[0]["corr_vec"])
        self.assertEqual(v.size, 3)
        self.assertAlmostEqual(v[1], -0.70)

    def test_covered_windows(self):
        r = dict(DR3_ROWS[3])
        s = go.sample_orbit(r, 300, np.random.default_rng(3), ref_btjd=389.0)
        t1c, t2c = go.central_conjunctions(r, ref_btjd=389.0)
        lab = go.transit_label(r, ref_btjd=389.0)
        p = {"period_d": r["period"], "t_conj1_btjd": t1c, "t_conj2_btjd": t2c,
             "transit_conj": lab["transit_conj"]}
        # fake TESS sector straddling the 5th transit after the reference conjunction
        tt = lab["t_transit_rv_btjd"] + 5 * r["period"]
        bt = np.arange(tt - 10, tt + 10, 1 / 48)
        wins = rs.covered_windows(bt, s, p)
        tr = [w for w in wins if w["is_rv_transit"]]
        self.assertEqual(len(tr), 1)
        self.assertLess(abs(tr[0]["centre"] - tt), 0.2)
        self.assertGreater(tr[0]["n_in_1sd"], 10)
        # the other conjunction is P/2 = 36.7 d away: not covered by a 20-day stretch
        self.assertEqual(len(wins), 1)
        self.assertEqual(rs.covered_windows(np.empty(0), s, p), [])


class _FakeArchive:
    """Answers chunked queries from a list of source_ids, like an anonymous Gaia TAP:
    results are truncated at `cap` rows, and ranges holding more than `abort_over`
    rows raise the 60-s execution-time error."""

    BETWEEN = re.compile(r"BETWEEN (\d+) AND (\d+)")

    def __init__(self, ids, cap=10, abort_over=None, fail_all=None):
        self.ids = sorted(ids)
        self.cap = cap
        self.abort_over = abort_over
        self.fail_all = fail_all
        self.queries = []

    def __call__(self, q):
        self.queries.append(q)
        if self.fail_all:
            raise RuntimeError(self.fail_all)
        m = self.BETWEEN.search(q)
        lo, hi = (int(m.group(1)), int(m.group(2))) if m else (0, rs.SOURCE_ID_MAX)
        sel = [i for i in self.ids if lo <= i <= hi]
        if self.abort_over is not None and len(sel) > self.abort_over:
            raise RuntimeError("TAP job ABORTED: Maximum execution time (60 s) reached.")
        sel = sel[:self.cap]
        return "source_id,period\n" + "".join(f"{i},{i % 97}.5\n" for i in sel)


class TestChunkedQuery(unittest.TestCase):
    """0.4.1: anonymous Gaia archive limits (60 s, 50,000 rows) since October 2026."""
    Q = "SELECT source_id, period FROM t AS n WHERE x < 1/*CHUNK:n.source_id*/"

    def _ids(self, n, lo=0, hi=rs.SOURCE_ID_MAX, seed=1):
        rng = np.random.default_rng(seed)
        return sorted({int(x) for x in rng.integers(lo, hi, n, dtype=np.int64)})

    def _got(self, text):
        return sorted(r["source_id"] for r in rs.read_csv_text(text))

    def test_bounds_cover_everything(self):
        b = rs.chunk_bounds(16)
        self.assertEqual(b[0][0], 0)
        self.assertEqual(b[-1][1], rs.SOURCE_ID_MAX - 1)
        for (a0, b0), (a1, _) in zip(b, b[1:]):
            self.assertEqual(b0 + 1, a1)
        self.assertEqual(rs.SOURCE_ID_MAX, 6917529027641081856)
        self.assertGreater(rs.SOURCE_ID_MAX, 6917528997577384320)  # largest DR3 source_id

    def test_merge_and_markers(self):
        ids = self._ids(60)
        fa = _FakeArchive(ids, cap=1000)
        text = rs.chunked_query(self.Q, 16, fa)
        self.assertEqual(self._got(text), ids)
        self.assertEqual(len(fa.queries), 16)
        for q in fa.queries:
            self.assertNotIn("CHUNK", q)
            self.assertIn("AND n.source_id BETWEEN", q)
        self.assertEqual(text.splitlines()[0], "source_id,period")
        self.assertEqual(sum(1 for ln in text.splitlines() if ln.startswith("source_id")), 1)

    def test_single_chunk_has_no_clause(self):
        fa = _FakeArchive([5, 7], cap=1000)
        text = rs.chunked_query(self.Q, 1, fa)
        self.assertEqual(self._got(text), [5, 7])
        self.assertNotIn("BETWEEN", fa.queries[0])
        self.assertNotIn("CHUNK", fa.queries[0])

    def test_row_cap_splits(self):
        ids = self._ids(40, 0, rs.SOURCE_ID_MAX // 16)   # all in the first of 16 ranges
        fa = _FakeArchive(ids, cap=12)
        text = rs.chunked_query(self.Q, 16, fa, row_cap=12)
        self.assertEqual(self._got(text), ids)
        self.assertGreater(len(fa.queries), 16)

    def test_abort_splits(self):
        ids = self._ids(30, seed=4)
        fa = _FakeArchive(ids, cap=1000, abort_over=8)
        text = rs.chunked_query(self.Q, 1, fa)
        self.assertEqual(self._got(text), ids)

    def test_network_error_is_not_split(self):
        fa = _FakeArchive([1, 2], fail_all="Connection refused")
        with self.assertRaises(RuntimeError):
            rs.chunked_query(self.Q, 4, fa)
        self.assertEqual(len(fa.queries), 1)

    def test_empty_ranges(self):
        fa = _FakeArchive([], cap=10)
        text = rs.chunked_query(self.Q, 8, fa)
        self.assertEqual(rs.read_csv_text(text), [])
        self.assertEqual(text.splitlines()[0], "source_id,period")

    def test_cached_query_uses_chunks(self):
        tmp = tempfile.mkdtemp()
        try:
            ids = self._ids(25, seed=9)
            fa = _FakeArchive(ids, cap=1000)
            path = os.path.join(tmp, "q.csv")
            t1 = rs.cached_query(path, self.Q, 8, fa)
            self.assertEqual(len(fa.queries), 8)
            t2 = rs.cached_query(path, self.Q, 8, fa)          # cache hit: no new queries
            self.assertEqual(len(fa.queries), 8)
            self.assertEqual(t1, t2)
            self.assertFalse(os.path.exists(path + ".part"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class _FakeTable:
    """Minimal stand-in for an astropy Table: .colnames and iterable row dicts."""

    def __init__(self, colnames, rows):
        self.colnames = colnames
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class TestTableToCsv(unittest.TestCase):
    """0.4.0: the astroquery fallback crashed on the array column corr_vec."""

    def _check(self, text):
        rows = rs.read_csv_text(text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["source_id"], 393581461455623296)
        v = go.parse_corr_vec(rows[0]["corr_vec"])
        self.assertEqual(v.size, 3)
        self.assertAlmostEqual(v[0], 0.25)
        self.assertTrue(np.isnan(v[1]))
        self.assertAlmostEqual(v[2], -0.5)
        self.assertEqual(rows[0]["nss_solution_type"], "AstroSpectroSB1")
        self.assertAlmostEqual(rows[0]["period"], 73.3403)
        self.assertTrue(np.isnan(rows[1]["period"]))
        self.assertIsNone(go.parse_corr_vec(rows[1]["corr_vec"]))

    def test_numpy_cells(self):
        tbl = _FakeTable(["source_id", "nss_solution_type", "corr_vec", "period"], [
            {"source_id": np.int64(393581461455623296), "nss_solution_type": b"AstroSpectroSB1",
             "corr_vec": np.ma.array([0.25, 9.0, -0.5], mask=[False, True, False]),
             "period": np.float64(73.3403)},
            {"source_id": np.int64(12), "nss_solution_type": "Orbital",
             "corr_vec": np.ma.masked, "period": np.ma.masked},
        ])
        self._check(rs.table_to_csv(tbl))

    def test_astropy_table(self):
        try:
            from astropy.table import MaskedColumn, Table
        except ImportError:
            self.skipTest("astropy not installed")
        tbl = Table()
        tbl["source_id"] = np.array([393581461455623296, 12], dtype=np.int64)
        tbl["nss_solution_type"] = ["AstroSpectroSB1", "Orbital"]
        tbl["corr_vec"] = MaskedColumn(np.array([[0.25, 9.0, -0.5], [0.0, 0.0, 0.0]]),
                                       mask=np.array([[False, True, False], [True, True, True]]))
        tbl["period"] = MaskedColumn([73.3403, 0.0], mask=[False, True])
        text = rs.table_to_csv(tbl)
        rows = rs.read_csv_text(text)
        self.assertEqual(rows[0]["source_id"], 393581461455623296)
        v = go.parse_corr_vec(rows[0]["corr_vec"])
        self.assertEqual(v.size, 3)
        self.assertTrue(np.isnan(v[1]))
        self.assertTrue(np.isnan(rows[1]["period"]))


class TestRankingOffline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data = os.path.join(self.tmp, "data")
        self.out = os.path.join(self.tmp, "out")
        os.makedirs(self.data)
        with open(os.path.join(self.data, "gaiadr3_nss_ti_g14.5_c0.3_v3.csv"), "w",
                  newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS)
            w.writeheader()
            for d in _fake_rows():
                w.writerow(d)
        with open(os.path.join(self.data, "gaiadr3_nss_ti_vari_eb_c0.3.csv"), "w",
                  encoding="utf-8") as fh:
            fh.write("source_id\n" + "\n".join(str(10 ** 15 + i) for i in range(12)) + "\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_tess_run(self):
        rc = rs.main(["--data-dir", self.data, "--out-dir", self.out, "--no-tess",
                      "--cosi-max", "0.3", "--mc", "100"])
        self.assertEqual(rc, 0)
        with open(os.path.join(self.out, "run_summary.json")) as fh:
            summary = json.load(fh)
        self.assertEqual(summary["nss_rows"], 4)
        self.assertEqual(summary["near_edge_on"], 4)
        self.assertEqual(summary["mc_used_correlations"], 1)
        self.assertEqual(summary["circular_solutions"], 1)
        self.assertEqual(summary["rv_transit_labelled"], 3)
        self.assertEqual(summary["rv_transit_consistent"], 3)
        with open(os.path.join(self.out, "gaia_edge_on_priors.csv"), encoding="utf-8") as fh:
            pri = list(csv.DictReader(fh))
        self.assertEqual(len(pri), 4)
        for p in pri:
            self.assertAlmostEqual(float(p["ref_btjd"]), 389.0)
            self.assertGreater(float(p["next1_btjd"]), 4375.5 - 200)
            t1c, t2c = float(p["t_conj1_btjd"]), float(p["t_conj2_btjd"])
            r = [d for d in DR3_ROWS if d["source_id"] == int(p["source_id"])][0]
            P = r["period"]
            ours = sorted(np.mod([t1c, t2c], P))
            theirs = sorted(np.mod(r["adql_t"], P))
            for a, b in zip(ours, theirs):
                self.assertLess(abs(np.mod(a - b + P / 2, P) - P / 2), 2e-3)
            if "transit_t" in r:
                chosen = t1c if p["transit_conj"] == "t1" else t2c
                self.assertLess(abs(np.mod(chosen - r["transit_t"] + P / 2, P) - P / 2), 2e-3)
                self.assertTrue(p["next_transit_btjd"])
            else:
                self.assertEqual(p["transit_conj"], "")
        with open(os.path.join(self.out, "nss_query.adql"), encoding="utf-8") as fh:
            self.assertNotIn("CHUNK", fh.read())


if __name__ == "__main__":
    unittest.main()
