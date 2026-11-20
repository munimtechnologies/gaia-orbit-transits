# SPDX-License-Identifier: Apache-2.0
"""Unit tests for youth_rv_check 0.1.2 (stdlib only). MV2 of Munim, Inc.; made with AI agents."""
import unittest

import youth_rv_check as y


class TestPure(unittest.TestCase):
    def test_version(self):
        self.assertEqual(y.VERSION, "0.1.2")

    def test_self_test(self):
        self.assertTrue(y.self_test())

    def test_reading(self):
        ctl = {"ALL": {"BPMG": 0.95}}
        self.assertEqual(y.reading_youth({"YA_PROB_float": 0.9}, ctl), "YOUNG_KINEMATIC")
        self.assertEqual(y.reading_youth({"YA_PROB_float": 0.1}, ctl), "FIELD_KINEMATIC")
        self.assertEqual(y.reading_youth({"YA_PROB_float": 0.5}, ctl), "AMBIGUOUS")
        self.assertEqual(y.reading_youth({"YA_PROB_float": 0.9}, {"ALL": {"BPMG": 0.5}}),
                         "CONTROL_FAILED")
        self.assertEqual(y.reading_youth({"error": "x"}, ctl), "UNTESTED")

    def test_find_rvs(self):
        vz = {"III/283": {"target": {"tables": [{"table": "t", "n": 1, "rows": [
            {"HRV": "-12.5", "e_HRV": "1.1", "Obsdate": "20090612"}]}]}}}
        f = y.find_rvs(vz)
        self.assertEqual(len(f), 1)
        self.assertEqual((f[0]["rv"], f[0]["erv"], f[0]["epoch_col"]), (-12.5, 1.1, "obsdate"))


if __name__ == "__main__":
    unittest.main()
