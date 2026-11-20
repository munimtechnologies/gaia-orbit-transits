# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qcut_dr4 0.1.0 (stdlib only). MV2 of Munim, Inc.; made with AI agents."""
import csv
import json
import os
import tempfile
import unittest

import qcut_dr4 as q4


def qrow(sid, sig, eff=0.3, ng=25, P=3.0, typ="SB1", K=10.0, amp=20.0):
    return {"source_id": str(sid), "nss_solution_type": typ, "period": str(P), "semi_amplitude_primary": str(K),
            "significance": str(sig), "efficiency": str(eff), "rv_n_good_obs_primary": str(ng),
            "goodness_of_fit": "1.0", "conf_spectro_period": "0.9", "rv_amplitude_robust": str(amp)}


class TestStats(unittest.TestCase):
    def test_wilson_known(self):
        lo, hi = q4.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)
        self.assertEqual(q4.wilson(0, 0), [None, None])

    def test_fisher_known(self):
        self.assertAlmostEqual(q4.fisher_greater(3, 0, 0, 3), 0.05, places=12)
        self.assertAlmostEqual(q4.fisher_greater(0, 3, 3, 0), 1.0, places=12)
        self.assertIsNone(q4.fisher_greater(0, 0, 2, 2))

    def test_auc(self):
        self.assertEqual(q4.auc([3, 4], [1, 2]), 1.0)
        self.assertEqual(q4.auc([1, 2], [3, 4]), 0.0)
        self.assertEqual(q4.auc([1, 1], [1, 1]), 0.5)
        self.assertAlmostEqual(q4.auc([1, 3], [2]), 0.5)
        self.assertIsNone(q4.auc([], [1]))

    def test_compare(self):
        hi = {"f_conf": 0.9, "ci95": [0.8, 0.95]}
        lo = {"f_conf": 0.3, "ci95": [0.2, 0.4]}
        mid = {"f_conf": 0.6, "ci95": [0.35, 0.8]}
        self.assertTrue(q4.compare(hi, lo))
        self.assertFalse(q4.compare(mid, lo))
        self.assertFalse(q4.compare(lo, hi))

    def test_truthy(self):
        self.assertTrue(q4.truthy("True"))
        self.assertFalse(q4.truthy("False"))
        self.assertFalse(q4.truthy(""))


class TestGrade(unittest.TestCase):
    def build(self):
        cols, recs, stars = [], [], []
        for i in range(40):                       # gold, T3, all CONFIRMED
            cols.append(qrow(1000 + i, 50.0))
            recs.append({"source_id": str(1000 + i), "label": "CONFIRMED"})
        for i in range(40):                       # not gold, T1, mostly DROPPED
            cols.append(qrow(2000 + i, 5.0, eff=0.1, amp=60.0))
            recs.append({"source_id": str(2000 + i), "label": "CONFIRMED" if i < 4 else "DROPPED"})
        for i in range(5):
            cols.append(qrow(3000 + i, 15.0))
            recs.append({"source_id": str(3000 + i), "label": "UNTESTABLE"})
        for i in range(6):
            stars.append({"source_id": str(1000 + i), "star_hit": "True"})
            stars.append({"source_id": str(2010 + i), "star_hit": "False"})
        return recs, cols, stars

    def test_grade_passes_clear_case(self):
        recs, cols, stars = self.build()
        res, ok = q4.grade(recs, cols, stars)
        self.assertTrue(ok)
        self.assertEqual(res["labels"]["UNTESTABLE"], 5)
        self.assertEqual(res["Q4a"]["gold"]["n_testable"], 40)
        self.assertTrue(res["Q4a"]["pass"])
        self.assertTrue(res["Q4b"]["pass"])
        self.assertEqual(res["Q4c"]["table"], {"hit_confirmed": 6, "hit_not": 0, "nohit_confirmed": 0,
                                               "nohit_not": 6})
        self.assertTrue(res["Q4c"]["pass"])
        self.assertEqual(res["Q4d"]["columns"]["efficiency"]["auc"] > 0.5, True)
        self.assertEqual(res["Q4d"]["columns"]["amp_ratio"]["auc"] > 0.5, True)
        self.assertEqual(res["Q4d"]["columns"]["efficiency"]["n_confirmed"], 44)

    def test_unmatched_stops(self):
        recs, cols, stars = self.build()
        recs.append({"source_id": "999", "label": "CONFIRMED"})
        recs.append({"source_id": "998", "label": "CONFIRMED"})
        res, ok = q4.grade(recs, cols, stars)
        self.assertFalse(ok)
        self.assertIn("stopped", res)

    def test_main_writes_outputs(self):
        recs, cols, stars = self.build()
        with tempfile.TemporaryDirectory() as d:
            paths = {}
            for name, rows in (("r", recs), ("c", cols), ("s", stars)):
                p = os.path.join(d, name + ".csv")
                with open(p, "w", newline="") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                    w.writeheader()
                    w.writerows(rows)
                paths[name] = p
            out = os.path.join(d, "out")
            rc = q4.main(["--records", paths["r"], "--columns", paths["c"], "--stars", paths["s"],
                          "--out-dir", out])
            self.assertEqual(rc, 0)
            with open(os.path.join(out, "qcut_dr4_summary.json")) as fh:
                self.assertTrue(json.load(fh)["Q4a"]["pass"])
            self.assertTrue(os.path.exists(os.path.join(out, "qcut_dr4_report.md")))


if __name__ == "__main__":
    unittest.main()
