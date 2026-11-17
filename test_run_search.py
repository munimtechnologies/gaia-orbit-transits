# SPDX-License-Identifier: Apache-2.0
"""Offline tests of the Gaia ranking stage of run_search (no network)."""
import csv
import json
import os
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
        self.assertTrue(os.path.exists(os.path.join(self.out, "nss_query.adql")))


if __name__ == "__main__":
    unittest.main()
