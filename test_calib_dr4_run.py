# SPDX-License-Identifier: Apache-2.0
"""Tests for the stdlib parts of calib_dr4_run.py (MV2 of Munim, Inc.; made with AI
agents). Offline; the run itself needs numpy and the Gaia archive."""
import unittest

import calib_dr4_run as cr


class TestMcNemar(unittest.TestCase):
    def test_values(self):
        self.assertAlmostEqual(cr.mcnemar_one_sided(5, 0), 1 / 32)
        self.assertEqual(cr.mcnemar_one_sided(0, 0), 1.0)
        self.assertAlmostEqual(cr.mcnemar_one_sided(1, 1), 0.75)
        self.assertAlmostEqual(cr.mcnemar_one_sided(0, 3), 1.0)


def _row(group, label, ne3, ne4):
    return {"group": group, "label": label, "ne3": ne3, "ne4": ne4}


class TestK2b(unittest.TestCase):
    def test_pass(self):
        rows = [_row("N", "CONFIRMED", False, True)] * 12 + \
               [_row("N", "CONFIRMED", True, True)] * 8 + \
               [_row("N", "DROPPED", None, None)] * 30 + \
               [_row("E", "CONFIRMED", False, False)] * 20
        k = cr.k2b(rows)
        self.assertEqual(k["N"]["n"], 20)
        self.assertAlmostEqual(k["N"]["delta"], 0.6)
        self.assertAlmostEqual(k["N"]["frac3"], 0.4)
        self.assertAlmostEqual(k["N"]["frac4"], 1.0)
        self.assertEqual(k["E"]["delta"], 0.0)
        self.assertTrue(k["pass"])

    def test_fail_when_e_moves_too(self):
        rows = [_row("N", "CONFIRMED", False, True)] * 10 + \
               [_row("E", "CONFIRMED", False, True)] * 5 + \
               [_row("E", "CONFIRMED", False, False)] * 5
        self.assertFalse(cr.k2b(rows)["pass"])

    def test_empty(self):
        k = cr.k2b([])
        self.assertIsNone(k["N"]["delta"])
        self.assertFalse(k["pass"])


class TestRehearsal(unittest.TestCase):
    def test_perfect_rehearsal(self):
        rows = []
        for i in range(cr.EXPECT_MAIN):
            rows.append({"label": "CONFIRMED", "cosi3": 0.01, "cosi4": 0.01,
                         "cosi_sd3": 0.02, "cosi4_sd": 0.021,
                         "z4": cr.DR3_RMS_Z9 if i % 3 == 0 else None})
        g = {"K1": {"pass": False, "fail_N": 0.0, "fail_E": 0.0}}
        rh = cr.rehearsal_checks(rows, g)
        self.assertTrue(all(v["pass"] for v in rh.values()), rh)

    def test_broken_rehearsal(self):
        rows = [{"label": "CHANGED", "cosi3": 0.01, "cosi_sd3": 0.02}] * 10
        g = {"K1": {"pass": False, "fail_N": 1.0, "fail_E": 1.0}}
        rh = cr.rehearsal_checks(rows, g)
        self.assertFalse(rh["RH1_all_confirmed"]["pass"])
        self.assertFalse(rh["RH2_cosi_reproduced"]["pass"])
        self.assertFalse(rh["RH3_timing_reproduced"]["pass"])
        self.assertFalse(rh["RH4_no_failures"]["pass"])


if __name__ == "__main__":
    unittest.main()
