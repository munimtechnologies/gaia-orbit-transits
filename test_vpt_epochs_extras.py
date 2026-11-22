# SPDX-License-Identifier: Apache-2.0
"""Tests for vpt_epochs_extras (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents).
Stdlib only (the numpy box fields are exercised by the job, not here)."""
import os
import random
import shutil
import tempfile
import unittest

import vpt_epochs_extras as vx

ve = vx.ve


def _epochs(seed, P, T0g, dur, depth, n_visits=150, noise=0.001):
    rng = random.Random(seed)
    visits = sorted(rng.uniform(1700.0, 2700.0) for _ in range(n_visits))
    t = sorted(visits + [v + 0.0739 for v in visits])
    fn = []
    for x in t:
        c = (x - T0g) / P
        inside = abs(c - round(c)) * P <= dur / 2
        fn.append(1.0 + rng.gauss(0.0, noise) - (depth if inside else 0.0))
    return t, fn


class TestSeed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_split_and_write(self):
        text = ("source_id,time,flux,flux_error,rejected\n"
                "11,1709.9240838,151653.2,149.27,0\n"
                "11,1741.3059606,151894.4,95.321,1\n"
                "22,1800.5,200,1.5,0\n")
        g = vx.split_epochs_text(text)
        self.assertEqual(sorted(g), ["11", "22"])
        self.assertEqual(len(g["11"]), 2)
        self.assertEqual(vx.write_cache(self.tmp, g), 2)
        self.assertEqual(vx.n_cached(self.tmp), 2)
        rec = ve.load_epochs(os.path.join(self.tmp, "11.csv"))
        self.assertEqual(rec["t"], [1709.9240838, 1741.3059606])
        self.assertEqual(rec["rej"], [False, True])
        t, fl, _, nrej = ve.clean_epochs(rec)
        self.assertEqual((len(t), nrej), (1, 1))


class TestCoverage(unittest.TestCase):
    def test_numbers(self):
        rows = [
            {"category": "KNOWN_SYSTEM_OTHER_P", "why_label": "PARTIAL", "n_t": "2", "n_g": "5",
             "n_both": "2", "n_epochs": "50"},
            {"category": "KNOWN_SYSTEM_OTHER_P", "why_label": "UNRELATED", "n_t": "4",
             "n_g": "10", "n_both": "0", "n_epochs": "40"},
            {"category": "KNOWN_SYSTEM_OTHER_P", "why_label": "UNTESTABLE", "n_t": "4",
             "n_g": "10", "n_both": "4", "n_epochs": "40"},
            {"category": "KNOWN_PLANET", "why_label": "ALIAS", "n_t": "3", "n_g": "3",
             "n_both": "3", "n_epochs": "30"},
        ]
        s = vx.coverage_stats(rows)
        w = s["wrong_period"]
        self.assertEqual(w["n_stars"], 2)
        self.assertEqual(w["overlap_observed"], 2)
        self.assertAlmostEqual(w["overlap_expected"], 2 * 0.1 + 4 * 0.25)
        var = 2 * 0.1 * 0.9 + 4 * 0.25 * 0.75
        self.assertAlmostEqual(w["z"], (2 - 1.2) / var ** 0.5)
        self.assertEqual(w["stars_with_overlap"], 1)
        self.assertAlmostEqual(w["stars_with_overlap_expected"], (1 - 0.9 ** 2) + (1 - 0.75 ** 4))
        self.assertEqual(s["controls"]["n_stars"], 1)
        self.assertEqual(s["controls"]["overlap_observed"], 3)


class TestFixedEphemeris(unittest.TestCase):
    P, T0g, dur = 2.1238933, 5508.58685, 0.125

    def test_sees_injected_dip(self):
        t, fn = _epochs(3, self.P, self.T0g, self.dur, 0.01)
        sd = ve.robust_sd(fn)
        r = vx.fixed_ephemeris_test(t, fn, sd, self.P, self.T0g, self.dur, 3e-6, 7e-4)
        self.assertGreaterEqual(r["n_in"], 2)
        self.assertEqual(r["label"], "GAIA_SEES_TESS_EPHEMERIS")
        self.assertGreater(r["snr"], 5)
        self.assertLessEqual(r["p_emp"], 0.01)
        self.assertAlmostEqual(r["depth"], 0.01, delta=0.003)

    def test_flat_not_seen(self):
        t, fn = _epochs(4, self.P, self.T0g, self.dur, 0.0)
        sd = ve.robust_sd(fn)
        r = vx.fixed_ephemeris_test(t, fn, sd, self.P, self.T0g, self.dur, 3e-6, 7e-4)
        self.assertIn(r["label"], ("NOT_SEEN", "UNTESTABLE"))

    def test_imprecise_ephemeris_untestable(self):
        t, fn = _epochs(5, self.P, self.T0g, self.dur, 0.01)
        sd = ve.robust_sd(fn)
        r = vx.fixed_ephemeris_test(t, fn, sd, self.P, self.T0g, self.dur, 1e-3, 7e-4)
        self.assertEqual(r["label"], "UNTESTABLE")
        self.assertEqual(r["reason"], "ephemeris too imprecise")

    def test_few_epochs(self):
        r = vx.fixed_ephemeris_test([1.0, 2.0], [1.0, 1.0], 0.001, self.P, self.T0g, self.dur)
        self.assertEqual(r["label"], "UNTESTABLE")

    def test_time_offset(self):
        self.assertAlmostEqual(vx.GAIA_MINUS_BTJD, 1802.5)
        c = vx.CANDIDATES[0]
        self.assertTrue(c["graded"])
        self.assertAlmostEqual(c["T0_btjd"] + vx.GAIA_MINUS_BTJD, 5508.5868496, places=5)


if __name__ == "__main__":
    unittest.main()
