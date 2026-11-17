# SPDX-License-Identifier: Apache-2.0
"""Tests for calib_support.py (gaia-orbit-transits; MV2 of Munim, Inc.; made with AI agents)."""
import csv
import os
import tempfile
import unittest

import calib_support as cs


def t(sid, p, m2="0.1", st="Orbital"):
    return {"source_id": sid, "p_ecl": p, "m2_dark": m2, "solution_type": st}


class TestCompare(unittest.TestCase):
    def test_exact(self):
        tg = [t("1", "0.5"), t("2", "0.25")]
        r = cs.compare(tg, [t("1", "0.5"), t("2", "0.25")])
        self.assertEqual((r["n"], r["n_exact"], r["n_missing"]), (2, 2, 0))
        self.assertTrue(r["pass"])

    def test_missing_fails(self):
        r = cs.compare([t("1", "0.5"), t("2", "0.25")], [t("1", "0.5")])
        self.assertEqual(r["n_missing"], 1)
        self.assertFalse(r["pass"])

    def test_one_small_diff_in_100_passes(self):
        tg = [t(str(i), "0.5") for i in range(100)]
        pr = [t(str(i), "0.5") for i in range(99)] + [t("99", "0.51")]
        r = cs.compare(tg, pr)
        self.assertEqual(r["n_exact"], 99)
        self.assertAlmostEqual(r["max_diff"], 0.01, places=9)
        self.assertTrue(r["pass"])

    def test_large_diff_fails(self):
        tg = [t(str(i), "0.5") for i in range(100)]
        pr = [t(str(i), "0.5") for i in range(99)] + [t("99", "0.6")]
        self.assertFalse(cs.compare(tg, pr)["pass"])

    def test_two_diffs_in_100_fail(self):
        tg = [t(str(i), "0.5") for i in range(100)]
        pr = [t(str(i), "0.5") for i in range(98)] + [t("98", "0.501"), t("99", "0.501")]
        self.assertFalse(cs.compare(tg, pr)["pass"])

    def test_solution_type_chosen(self):
        tg = [t("1", "0.5", st="AstroSpectroSB1")]
        pr = [t("1", "0.9", st="Orbital"), t("1", "0.5", st="AstroSpectroSB1")]
        self.assertTrue(cs.compare(tg, pr)["pass"])

    def test_m2_mismatch_not_exact(self):
        r = cs.compare([t("1", "0.5", m2="0.1")], [t("1", "0.5", m2="0.2")])
        self.assertEqual(r["n_exact"], 0)
        self.assertFalse(r["pass"])


class TestSeen(unittest.TestCase):
    def test_detected_and_extra(self):
        rows = [{"source_id": "1", "tic": "11", "period_d": "10", "detected": "True",
                 "det_mode": "window", "gaia_eb": "False"},
                {"source_id": "2", "tic": "22", "period_d": "20", "detected": "False"},
                {"source_id": "3", "tic": "33", "period_d": "5", "detected": "True",
                 "det_mode": "repeat", "gaia_eb": "False"}]
        out = cs.seen_rows(rows, [("3", "33"), ("4", "44")])
        self.assertEqual([r["source_id"] for r in out], ["1", "3", "4"])
        self.assertTrue(all(r["vet"].startswith("eclipse") for r in out))
        self.assertIn("repeat", out[1]["vet"])


class TestRepro(unittest.TestCase):
    def test_files(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "tess_targets.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["source_id", "solution_type", "p_ecl", "m2_dark"])
            w.writerow(["5", "Orbital", "0.3", "0.08"])
        with open(os.path.join(d, "gaia_edge_on_priors.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["source_id", "solution_type", "p_ecl", "m2_dark", "cosi"])
            w.writerow(["5", "Orbital", "0.3", "0.08", "0.01"])
            w.writerow(["6", "Orbital", "0.2", "0.5", "0.02"])
        out = os.path.join(d, "out")
        rc = cs.main(["repro", "--dir", d, "--out-dir", out])
        self.assertEqual(rc, 0)
        with open(os.path.join(out, "priors_targets.csv"), newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual([r["source_id"] for r in rows], ["5"])
        self.assertEqual(rows[0]["cosi"], "0.01")


if __name__ == "__main__":
    unittest.main()
