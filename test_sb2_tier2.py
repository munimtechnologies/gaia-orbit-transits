# SPDX-License-Identifier: Apache-2.0
"""Unit tests for sb2_tier2 (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents)."""
import math
import unittest

import sb2_screen as s0
import sb2_tier2 as t2


def orbit(sid, ratio, P=3.0, k=100.0):
    ms = s0.m1sin3i(k, k, P, 0.0)
    return {"source_id": sid, "period": repr(P), "semi_amplitude_primary": repr(k),
            "semi_amplitude_secondary": repr(k), "eccentricity": "", "m1": repr(ms / ratio)}


class Tier2Tests(unittest.TestCase):
    def test_self_test_passes(self):
        ok, bad = t2.self_test()
        self.assertTrue(ok, bad)

    def test_tiers_disjoint(self):
        for r in (0.851, 0.9, 0.949, 0.951, 1.0, 1.099, 1.101, 1.149):
            self.assertIn(t2.tier_of(r), (1, 2))
        self.assertEqual(t2.tier_of(0.84), 0)
        self.assertEqual(t2.tier_of(1.16), 0)

    def test_selection_drops_long_period_and_missing_m1(self):
        rows = [orbit("1", 0.9), orbit("2", 0.9, P=9.0), dict(orbit("3", 0.9), m1="")]
        self.assertEqual([r["source_id"] for r in t2.select_tier2(rows)], ["1"])

    def test_selected_row_carries_ratio(self):
        r = t2.select_tier2([orbit("9", 1.12)])[0]
        self.assertAlmostEqual(r["s3_ratio"], 1.12, places=9)
        self.assertTrue(math.isfinite(r["m1sin3i"]))

    def test_calibration_marks_missing_rows(self):
        cal = t2.rowan_calibration([])
        self.assertEqual(len(cal), 27)
        self.assertFalse(any(c["hand_agrees"] for c in cal))
        self.assertEqual(t2.summarize_cal(cal)["label"], "CAL_DIFFERS")

    def test_calibration_with_hand_values(self):
        rows = [orbit(sid, hand) for sid, (_, hand) in t2.ROWAN_CAL.items()]
        s = t2.summarize_cal(t2.rowan_calibration(rows))
        self.assertEqual(s["label"], "CAL_OK")
        self.assertEqual(s["n_tier2"], 10)
        self.assertEqual(s["n_tier1"], 11)

    def test_votable_namespace_free(self):
        v = ('<VOTABLE><RESOURCE><TABLE><FIELD name="source_id"/><DATA><TABLEDATA>'
             '<TR><TD>42</TD></TR></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>')
        self.assertEqual(t2.parse_tap_reply(v), [{"source_id": "42"}])


if __name__ == "__main__":
    unittest.main()
