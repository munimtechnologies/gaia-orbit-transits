# SPDX-License-Identifier: Apache-2.0
"""Tests for patch_vpt_epochs_012 (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents).
Stdlib only; needs vpt_epochs.py 0.1.0 (f868df8e) and patch_vpt_epochs_011.py (824cbe54) here.
Run in its own process (the patches change the shared vpt_epochs module)."""
import unittest

import patch_vpt_epochs_012 as p12

ve = p12.ve


class TestPatch012(unittest.TestCase):
    def test_applied(self):
        self.assertEqual(ve.VERSION, "0.1.2")
        self.assertIs(ve.analyse_epochs, p12.analyse_epochs_box)
        self.assertEqual(ve.healpix8(5345417757181174144), 607703)   # 0.1.1 fix kept
        self.assertIsNot(p12._ORIG, p12.analyse_epochs_box)

    def test_apply_twice_no_recursion(self):
        p12.apply()
        p12.apply()
        self.assertIs(ve.analyse_epochs, p12.analyse_epochs_box)
        self.assertIs(ve._analyse_epochs_010, p12._ORIG)

    def test_box_set(self):
        self.assertTrue(p12.box_check())

    def test_box_record(self):
        t, fl, P, T0, dur, intr = p12._synthetic(seed=7)
        n_in = sum(intr)
        tgt = {"source_id": "2", "category": "KNOWN_SYSTEM_OTHER_P", "category_detail": "",
               "tic": "2", "G": 12.0, "P_gaia": P, "T0_gaia": T0, "dur_gaia": dur,
               "num_in_transit": 5 * n_in}
        rec = ve.analyse_epochs(tgt, t, fl, [])
        self.assertEqual(rec["n_g"], n_in)
        self.assertEqual(rec["num_in_transit"], 5 * n_in)
        self.assertEqual(tgt["num_in_transit"], 5 * n_in)     # caller's dict untouched
        self.assertEqual(rec["status"], "NO_EPHEMERIS")
        self.assertAlmostEqual(rec["gaia_within_frac"], 1.0)

    def test_missing_duration_gives_empty_set(self):
        t, fl, P, T0, dur, intr = p12._synthetic(seed=9)
        tgt = {"source_id": "3", "category": "NEW", "category_detail": "", "tic": "3",
               "G": 12.0, "P_gaia": P, "T0_gaia": T0, "dur_gaia": float("nan"),
               "num_in_transit": 10}
        rec = ve.analyse_epochs(tgt, t, fl, [])
        self.assertEqual(rec["n_g"], 0)


if __name__ == "__main__":
    unittest.main()
