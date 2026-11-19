# SPDX-License-Identifier: Apache-2.0
"""Unit tests for eblm_holdout_fit 0.1.0 (stdlib only). MV2 of Munim, Inc.; made with AI agents."""
import csv
import os
import tempfile
import unittest

import eblm_holdout_fit as hf


def vet(outcome, r2):
    return {"outcome": outcome, "r2": r2}


class TestGrade(unittest.TestCase):
    def test_grade_one(self):
        self.assertEqual(hf.grade_one(vet("C_NORMAL_COMPANION", 0.105), 0.1)[:2], (True, True))
        self.assertEqual(hf.grade_one(vet("C_NORMAL_COMPANION", 0.111), 0.1)[:2], (True, False))
        self.assertEqual(hf.grade_one(vet("A_COMPANION_HEAVIER_THAN_GAIA", 0.1), 0.1)[:2], (True, False))
        self.assertEqual(hf.grade_one(vet("G_GRAZING_RADIUS_UNMEASURED", 0.1), 0.1)[:2], (False, False))
        self.assertEqual(hf.grade_one(vet("UNTESTED", float("nan")), 0.1)[:2], (False, False))
        self.assertEqual(hf.grade_one(vet("C_NORMAL_COMPANION", float("nan")), 0.1)[:2], (True, False))

    def test_validated(self):
        items = [(vet("C_NORMAL_COMPANION", 0.1), 0.1)] * 4 + [(vet("E_NO_ECLIPSE", 0.1), 0.1)]
        g = hf.grade_all(items)
        self.assertEqual((g["n_testable"], g["n_pass"], g["label"]), (5, 4, "PIPELINE_VALIDATED"))

    def test_failed(self):
        items = [(vet("C_NORMAL_COMPANION", 0.1), 0.1)] * 3 + [(vet("E_NO_ECLIPSE", 0.1), 0.1)] * 2
        self.assertEqual(hf.grade_all(items)["label"], "PIPELINE_FAILED")

    def test_inconclusive(self):
        items = [(vet("C_NORMAL_COMPANION", 0.1), 0.1)] * 3 + [(vet("UNTESTED", 0.1), 0.1)] * 5
        self.assertEqual(hf.grade_all(items)["label"], "INCONCLUSIVE")

    def test_median_offset(self):
        items = [(vet("C_NORMAL_COMPANION", r), 0.1) for r in (0.09, 0.1, 0.12, 0.2)]
        self.assertAlmostEqual(hf.grade_all(items)["median_r2_offset"], 0.1, places=9)

    def test_outcome_mapping(self):
        self.assertEqual(hf.outcome({"verdict": "BD_EBLM_GRAZING"}), "G_GRAZING_RADIUS_UNMEASURED")
        self.assertEqual(hf.outcome({"verdict": "EBLM_SMALL_RADIUS"}), "C_NORMAL_COMPANION")
        self.assertEqual(hf.outcome({"verdict": "ERROR"}), "UNTESTED")
        self.assertEqual(hf.outcome({"verdict": "EBLM_LARGE_RADIUS", "r1_ratio": 1.0}), "B_OVERSIZED_COMPANION")
        self.assertEqual(hf.outcome({"verdict": "EBLM_LARGE_RADIUS", "r1_ratio": 1.4}),
                         "B0_LARGE_BUT_PRIMARY_SCALE_DISAGREES")


class TestInputs(unittest.TestCase):
    def test_read_holdouts_keeps_holdouts_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "holdout_ids.csv")
            with open(p, "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["name", "role", "gaia_dr3", "gaia_P", "gaia_K", "gaia_e", "G", "P_pub",
                            "e_pub", "M2_pub", "R2_pub", "R2_up", "R2_lo"])
                w.writerow(["J0123+38", "resolver_control", "323261744326472832", 7.95, 20, 0, 11, 7.95,
                            0, 0.36, 0.36, 0.01, 0.01])
                w.writerow(["J0040+01", "holdout", " 2534155367489600000 ", 7.23, 10, 0.07, 11, 7.23,
                            0.069, 0.1077, 0.1381, 0.006, 0.006])
            rows = hf.read_holdouts(p)
        self.assertEqual([r["name"] for r in rows], ["J0040+01"])
        self.assertEqual(rows[0]["gaia_dr3"], "2534155367489600000")

    def test_adql(self):
        q = hf.adql(["1", "22"])
        self.assertIn("n.eccentricity_error", q)
        self.assertIn("IN (1, 22)", q)
        self.assertIn("nss_solution_type = 'SB1'", q)


if __name__ == "__main__":
    unittest.main()
