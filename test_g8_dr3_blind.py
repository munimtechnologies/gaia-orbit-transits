# SPDX-License-Identifier: Apache-2.0
"""Tests for g8_dr3_blind 0.1.0 (MV2, Munim, Inc.; made with AI agents). Needs sb2_ecl_dr4.py
next to it or in ./repo."""
import math
import unittest

import g8_dr3_blind as b


class T(unittest.TestCase):
    def test_self_test(self):
        ok, bad = b.self_test()
        self.assertTrue(ok, bad)

    def test_votable_arrays(self):
        rows = b.parse_votable(b.SAMPLE_VOT)
        ep = b.epochs_from_row(rows[0])
        self.assertEqual(len(ep), 3)
        self.assertTrue(math.isnan(ep[1][1]))
        self.assertTrue(ep[1][2])          # non-finite magnitude is dropped
        self.assertTrue(ep[2][2])          # Gaia's variability rejection is honoured

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            b.epochs_from_row({"g_transit_time": "1 2", "g_transit_mag": "10",
                               "variability_flag_g_reject": ""})

    def test_queries_frozen(self):
        self.assertIn("o.period >= 0.4 AND o.period <= 15.0", b.SAMPLE_QUERY)
        self.assertIn("has_epoch_photometry = 'True'", b.SAMPLE_QUERY)
        self.assertIn("LIKE 'SB2%'", b.COUNT_QUERY)
        self.assertEqual((b.P1_MIN_SHARE_KNOWN, b.P2_MAX_NULL_SHARE, b.P3_MAX_MEDIAN_DPHASE,
                          b.P4_MIN_NEW_ECL), (0.40, 0.02, 0.015, 10))

    def test_rule_constants_unchanged(self):
        g8 = b.g8
        self.assertEqual(g8.VERSION, "0.1.0")
        self.assertEqual((g8.DIP_MIN_MAG, g8.DIP_MIN_SIGMA, g8.WINDOW, g8.FIT_EXCLUDE,
                          g8.MIN_EPOCHS, g8.NULL_SHIFT), (0.025, 4.0, 0.035, 0.06, 20, 0.25))

    def test_masses(self):
        # HD 171459 (Gaia DR3 6436666383265499136): K1 89.3, K2 87.7 km/s, P 6.3956124 d circular
        m1 = b.g8.m1sin3i(89.3, 87.7, 6.3956124, None)
        self.assertAlmostEqual(m1, 1.82, delta=0.02)


if __name__ == "__main__":
    unittest.main()
