# SPDX-License-Identifier: Apache-2.0
"""Offline tests for gaia_dip_ffi (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents)."""
import unittest

import gaia_dip_ffi as g


def rec(name, label="DETECTED", phase="PHASE_MATCH", phase_map="c1", depth=0.04, n=4):
    return {"name": name, "label": label, "phase": phase, "phase_map": phase_map,
            "depth_rel": depth, "n_sectors": n, "snr": 30.0, "phase_z": 0.5, "sec": "SEC_NOT_DETECTED"}


class TestList(unittest.TestCase):
    def test_stars(self):
        s = g.star_dicts()
        self.assertEqual(len(s), 10)
        self.assertEqual(sum(1 for x in s if x["group"] == "candidate"), 2)
        self.assertEqual(sum(1 for x in s if x["group"] == "control"), 2)
        self.assertEqual(sum(1 for x in s if x["group"] == "flat"), 6)
        self.assertEqual(len({x["source_id"] for x in s}), 10)
        self.assertEqual(len({x["tic"] for x in s}), 10)
        by = {x["name"]: x for x in s}
        self.assertEqual(by["CD-63 310"]["tic"], 349572805)
        self.assertEqual(by["CD-72 1603"]["tic"], 371839648)
        self.assertEqual(by["HD 250735"]["role"], "control")


class TestGrade(unittest.TestCase):
    def base(self):
        return [rec("HD 250735"), rec("CD-28 7251")] + [rec(x[2], label="NOT_DETECTED", phase=None)
                                                         for x in g.STARS if x[3] == "flat"]

    def test_both(self):
        r = self.base() + [rec("CD-63 310", phase_map="c2"), rec("CD-72 1603", phase_map="c1")]
        out = g.grade(r)
        self.assertEqual(out["D0"]["label"], "CONTROLS_OK")
        self.assertEqual(out["verdict"], "BOTH_CONFIRMED")
        self.assertTrue(out["D1"]["same_conjunction_as_gaia_dip"])
        self.assertTrue(out["D2"]["grazing_depth"])
        self.assertTrue(out["D3"]["expectation_at_most_1"])

    def test_controls_fail(self):
        r = [rec("HD 250735", label="NOT_DETECTED", phase=None), rec("CD-28 7251")]
        r += [rec("CD-63 310"), rec("CD-72 1603")]
        self.assertEqual(g.grade(r)["verdict"], "UNTESTABLE_CONTROLS_FAILED")

    def test_mismatch_and_missing(self):
        r = self.base() + [rec("CD-63 310", phase="PHASE_MISMATCH")]
        out = g.grade(r)
        self.assertEqual(out["D1"]["label"], "DETECTED_PHASE_MISMATCH")
        self.assertEqual(out["D2"]["label"], "NO_DATA")
        self.assertEqual(out["verdict"], "NEITHER_CONFIRMED")

    def test_one(self):
        r = self.base() + [rec("CD-63 310", depth=0.3), rec("CD-72 1603", label="NOT_DETECTED", phase=None)]
        out = g.grade(r)
        self.assertEqual(out["verdict"], "ONE_CONFIRMED")
        self.assertFalse(out["D1"]["grazing_depth"])
        self.assertFalse(out["D1"]["same_conjunction_as_gaia_dip"])
        self.assertEqual(out["D2"]["label"], "NOT_DETECTED")


if __name__ == "__main__":
    unittest.main()
