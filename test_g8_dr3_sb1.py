# SPDX-License-Identifier: Apache-2.0
"""Tests for g8_dr3_sb1 0.1.0 (MV2, Munim, Inc.; made with AI agents). Needs sb2_ecl_dr4.py
(af65d7b) and g8_dr3_blind.py (f0e1fb6) next to it or in ./repo."""
import unittest

import g8_dr3_sb1 as s


class T(unittest.TestCase):
    def test_self_test(self):
        ok, bad = s.self_test()
        self.assertTrue(ok, bad)

    def test_queries_frozen(self):
        self.assertIn("LIKE 'SB1%'", s.SAMPLE_QUERY)
        self.assertIn("LIKE 'SB1%'", s.COUNT_QUERY)
        self.assertIn("o.period >= 0.4 AND o.period <= 15.0", s.SAMPLE_QUERY)
        self.assertIn("has_epoch_photometry = 'True'", s.SAMPLE_QUERY)
        self.assertEqual(s.N_PREREG, 7978)

    def test_thresholds_frozen(self):
        self.assertEqual((s.P1_MIN_SHARE_KNOWN, s.P2_MAX_NULL_SHARE, s.P3_MAX_MEDIAN_DPHASE,
                          s.P4_MIN_NEW_ECL, s.P6_MIN_C1_SHARE, s.P6_MIN_N, s.MAX_MISSING_SHARE),
                         (0.25, 0.02, 0.015, 30, 0.65, 20, 0.01))

    def test_rule_unchanged(self):
        g8 = s.g8
        self.assertEqual(g8.VERSION, "0.1.0")
        self.assertEqual(s.b.VERSION, "0.1.0")
        self.assertEqual((g8.DIP_MIN_MAG, g8.DIP_MIN_SIGMA, g8.WINDOW, g8.FIT_EXCLUDE,
                          g8.MIN_EPOCHS, g8.NULL_SHIFT), (0.025, 4.0, 0.035, 0.06, 20, 0.25))

    def test_conjunction_convention(self):
        # circular orbit, omega not given: conjunction 0 at phase 0.25 (true anomaly 90 deg)
        c1, c2 = s.g8.conjunction_phases(None, None)
        self.assertAlmostEqual(c1, 0.25, places=12)
        self.assertAlmostEqual(c2, 0.75, places=12)

    def test_mass_function(self):
        # K1 = 20 km/s, P = 2 d, e = 0: 1.036149e-7 * 8000 * 2 = 1.6578384e-3 Msun
        self.assertAlmostEqual(s.mass_function(20.0, 2.0, 0.0), 1.6578384e-3, places=10)


if __name__ == "__main__":
    unittest.main()
