# SPDX-License-Identifier: Apache-2.0
"""Offline tests for forecast.py (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents)."""
import csv
import json
import os
import shutil
import tempfile
import unittest

import numpy as np

import forecast as fc
import gaia_orbits as go
from test_gaia_orbits import DR3_ROWS
from test_run_search import COLS, _fake_rows


class TestSectors(unittest.TestCase):
    def test_dates(self):
        self.assertAlmostEqual(fc.date_to_btjd("2026-09-07"), 4290.5, places=6)
        self.assertEqual(fc.btjd_to_date(4290.5), "2026-09-07 00:00")
        self.assertEqual(fc.btjd_to_date(fc.date_to_btjd("2027-01-28") + 0.25), "2027-01-28 06:00")

    def test_table(self):
        t = fc.sector_table()
        self.assertEqual(sorted(t), list(range(108, 135)))
        for s in range(108, 134):
            self.assertAlmostEqual(t[s][1], t[s + 1][0], places=9)   # contiguous
            self.assertGreater(t[s][1] - t[s][0], 24)
            self.assertLess(t[s][1] - t[s][0], 31)
        self.assertFalse(t[121][2])
        self.assertTrue(t[122][2])
        # Year 9 dates agree with tess-point's S121 mid-time (JD 2461654.0)
        self.assertLess(abs(0.5 * (t[121][0] + t[121][1]) - (2461654.0 - 2457000.0)), 1.0)
        for s, mid in fc.YEAR10_MID_JD.items():
            self.assertTrue(t[s][0] < mid - 2457000.0 < t[s][1])


class TestProbabilities(unittest.TestCase):
    def test_interval(self):
        t = np.full(10, 1000.0)
        P = np.full(10, 50.0)
        self.assertEqual(fc.p_conj_in_interval(t, P, 1040, 1060), 1.0)
        self.assertEqual(fc.p_conj_in_interval(t, P, 1001, 1049), 0.0)
        # 0.4.1 test fix: 0 = 1000 - 20 x 50 is itself a conjunction, so use (5, 10)
        self.assertEqual(fc.p_conj_in_interval(t, P, 0, 10), 1.0)
        self.assertEqual(fc.p_conj_in_interval(t, P, 5, 10), 0.0)
        self.assertEqual(fc.p_conj_in_interval(t, P, 750, 750), 1.0)
        tt = 1000.0 + np.linspace(-10, 10, 101)          # step 0.2 d
        # conjunctions tt + 100 inside [1099.9, 1105.1] <=> tt in [999.9, 1005.1]: 26 samples
        p = fc.p_conj_in_interval(tt, np.full(101, 50.0), 1099.9, 1105.1)
        self.assertAlmostEqual(p, 26 / 101)

    def test_windows(self):
        r = dict(DR3_ROWS[3])
        s = go.sample_orbit(r, 400, np.random.default_rng(5), ref_btjd=389.0)
        t1c, _ = go.central_conjunctions(r, ref_btjd=389.0)
        P = r["period"]
        w = fc.windows_between(s, "t1", t1c, P, t1c + 1, t1c + 3 * P + 1)
        self.assertEqual(len(w), 3)
        for k, x in enumerate(w, start=1):
            self.assertTrue(x["lo95"] <= x["centre"] <= x["hi95"])
            self.assertLess(abs(x["centre"] - (t1c + k * P)), P / 4)


class TestMainOffline(unittest.TestCase):
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
        self._orig = fc.on_silicon
        fc.on_silicon = lambda ids, ras, decs: {int(i): [(113, 2, 3, 500.0, 600.0),
                                                         (125, 1, 1, 100.0, 100.0)]
                                                for i in ids}

    def tearDown(self):
        fc.on_silicon = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_run(self):
        rc = fc.main(["--data-dir", self.data, "--out-dir", self.out, "--gmax", "14.5",
                      "--cosi-max", "0.3", "--m2-max", "100", "--mc", "200"])
        self.assertEqual(rc, 0)
        with open(os.path.join(self.out, "forecast_summary.json")) as fh:
            sm = json.load(fh)
        self.assertEqual(sm["stars"], 4)
        self.assertTrue(sm["tess_point_ok"])
        self.assertEqual(sm["stars_on_silicon_y9_y10"], 4)
        with open(os.path.join(self.out, "forecast_tess_sectors.csv"), encoding="utf-8") as fh:
            secs = list(csv.DictReader(fh))
        self.assertGreaterEqual(len(secs), 8)
        for r in secs:
            self.assertTrue(0.0 <= float(r["expected_transits"]) <= float(r["p_conj_in_sector"]) + 1e-12)
            self.assertIn(r["sector"], ("113", "125"))
        with open(os.path.join(self.out, "forecast_windows.csv"), encoding="utf-8") as fh:
            wins = list(csv.DictReader(fh))
        self.assertGreater(len(wins), 0)
        periods = {}
        with open(os.path.join(self.out, "forecast_stars.csv"), encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                periods[r["source_id"]] = float(r["period_d"])
        for w in wins:
            P = periods[w["source_id"]]
            c = float(w["centre_btjd"])
            self.assertTrue(4375.5 - P / 2 - 1e-6 <= c <= 4740.5 + P / 2 + 1e-6)
            self.assertIn(w["constrained"], ("True", "False"))
        self.assertTrue(os.path.exists(os.path.join(self.out, "forecast_report.md")))


if __name__ == "__main__":
    unittest.main()
