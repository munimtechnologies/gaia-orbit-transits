# SPDX-License-Identifier: Apache-2.0
"""Pure-Python tests for sb1_robust (no numpy, no sb1_transit needed).
MV2 of Munim, Inc.; made with AI agents. Expected values worked by hand in
findings/2026-11-18-sb1-transit-results.md."""
import unittest

import sb1_robust as sr

# per-job rate summaries of sb1_transit 0.1.0 (gaia-sb1tr-c0-v1 and -c1-v1)
C0 = {"n_rate_sample": 251, "n_hit": 21, "n_hit_substellar_size": 9,
      "n_control_hits_expected": 15.5, "n_control_hits_substellar_size": 5.5,
      "expected_if_all_real": 48.06206797528772}
C1 = {"n_rate_sample": 271, "n_hit": 16, "n_hit_substellar_size": 8,
      "n_control_hits_expected": 10.0, "n_control_hits_substellar_size": 2.0,
      "expected_if_all_real": 45.97011002808695}
# the 10 rate-sample stars that chunk 0 also processed (kept from chunk 1): no hits, no
# control hits, sum of p_transit * sensitivity in chunk 0
DUP = {"n_rate_sample": 10, "expected_if_all_real": 2.4528557685165633}


class TestHelpers(unittest.TestCase):
    def test_median(self):
        self.assertEqual(sr.median([3, 1, 2]), 2)
        self.assertEqual(sr.median([4, 1, 2, 3]), 2.5)

    def test_median_ratio_real_transit(self):
        r_in = [-0.010, -0.0098, -0.0102, -0.0101, -0.0099]
        self.assertAlmostEqual(sr.median_ratio(r_in, 0.010), 1.0, places=6)

    def test_median_ratio_outliers(self):
        # 3 bins at -10 % among 27 flat bins: mean depth 0.01, median 0
        r_in = [0.0] * 27 + [-0.1] * 3
        depth = -sum(r_in) / len(r_in)
        self.assertAlmostEqual(depth, 0.01, places=9)
        self.assertEqual(sr.median_ratio(r_in, depth), 0.0)
        self.assertFalse(sr.robust_hit({"med_ratio": 0.0}, True))

    def test_robust_hit_needs_base(self):
        self.assertFalse(sr.robust_hit({"med_ratio": 1.0}, False))
        self.assertTrue(sr.robust_hit({"med_ratio": 0.5}, True))
        self.assertFalse(sr.robust_hit({"med_ratio": 0.49}, True))
        self.assertFalse(sr.robust_hit(None, True))
        self.assertEqual(sr.median_ratio([], 0.01), 0.0)
        self.assertEqual(sr.median_ratio([-0.01], 0.0), 0.0)

    def test_order_is_a_partition(self):
        ids = [str(10 ** 17 + 7 * i) for i in range(1000)]
        parts = [sr.order_ids(ids, 8, k) for k in range(8)]
        allx = [x for p in parts for x in p]
        self.assertEqual(len(allx), 1000)
        self.assertEqual(set(allx), set(ids))
        self.assertEqual(sr.order_ids(ids, 8, 3), sr.order_ids(list(reversed(ids)), 8, 3))

    def test_garwood(self):
        lo, hi = sr.garwood(0)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 3.689, delta=0.002)
        lo, hi = sr.garwood(5)
        self.assertAlmostEqual(lo, 1.624, delta=0.002)
        self.assertAlmostEqual(hi, 11.668, delta=0.002)
        lo, hi = sr.garwood(17)
        self.assertAlmostEqual(lo, 9.903, delta=0.01)
        self.assertAlmostEqual(hi, 27.219, delta=0.01)


class TestCombineV01(unittest.TestCase):
    def test_straight_sum(self):
        t = sr.combine([C0, C1])
        self.assertEqual(t["n_rate_sample"], 522)
        self.assertEqual(t["n_hit_substellar_size"], 17)
        self.assertAlmostEqual(t["expected_if_all_real"], 94.032178, places=5)
        r = t["rho_substellar_size"]
        self.assertAlmostEqual(r["rho"], 9.5 / 94.032178, places=6)
        self.assertAlmostEqual(r["ci95"][1], 0.2097, delta=0.0005)
        self.assertAlmostEqual(t["control_rate"], 25.5 / 522, places=9)

    def test_deduplicated(self):
        t = sr.combine([C0, C1], minus=DUP)
        self.assertEqual(t["n_rate_sample"], 512)
        self.assertAlmostEqual(t["expected_if_all_real"], 91.579322, places=5)
        r = t["rho_substellar_size"]
        self.assertAlmostEqual(r["rho"], 0.10374, delta=0.0001)
        self.assertAlmostEqual(r["ci95"][0], 0.0262, delta=0.0005)
        self.assertAlmostEqual(r["ci95"][1], 0.2153, delta=0.0005)
        self.assertAlmostEqual(r["upper_no_subtraction"], 0.2972, delta=0.0005)
        self.assertLess(r["ci95"][1], 0.5)                      # H1
        self.assertGreater(t["control_rate"], 0.03)             # C2 failed
        self.assertAlmostEqual(t["rho_all"]["rho"], 11.5 / 91.579322, places=6)


if __name__ == "__main__":
    unittest.main()
