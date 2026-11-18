# SPDX-License-Identifier: Apache-2.0
"""Unit tests for calib_window (pure Python; MV2 of Munim, Inc., made with AI agents)."""
import math
import random
import unittest

import calib_window as cw


class TestHelpers(unittest.TestCase):
    def test_window_frac(self):
        self.assertAlmostEqual(cw.window_frac(3.0, 1.0), 0.9973, places=3)
        self.assertAlmostEqual(cw.window_frac(3.0, 3.0), 0.6827, places=3)
        self.assertEqual(cw.window_frac(3.0, 0.0), 1.0)

    def test_scaled_fa(self):
        self.assertAlmostEqual(cw.scaled_fa(0.1, 1.0), 0.1)
        self.assertAlmostEqual(cw.scaled_fa(0.1, 2.0), 0.19)
        self.assertEqual(cw.scaled_fa(0.1, 0.0), 0.0)

    def test_loglike_probabilities_sum_to_one(self):
        # P(no det) + integral of the det density over |z| < h = 1
        p, h, s, fa = 0.6, 3.5, 1.7, 0.1
        nodet = math.exp(cw.target_loglike(p, False, None, h, s, fa))
        n = 4000
        dz = 2 * h / n
        det = sum(math.exp(cw.target_loglike(p, True, -h + (i + 0.5) * dz, h, s, fa)) * dz
                  for i in range(n))
        self.assertAlmostEqual(nodet + det, 1.0, places=3)

    def test_repeat_mode(self):
        self.assertAlmostEqual(math.exp(cw.target_loglike(0.5, True, None, None, 2.0, 0.1)),
                               0.55)
        self.assertAlmostEqual(math.exp(cw.target_loglike(0.5, False, None, None, 2.0, 0.1)),
                               0.45)

    def test_detect_at(self):
        wins = [(100.0, 0.1), (150.0, 0.1)]
        clean = [(100.25, 12.0, 4.8)]           # 2.5 sigma + nothing, dur/48 = 0.1 d
        b = cw.detect_at(clean, wins, 50.0, 3.0, skip_wide=True)
        self.assertIsNotNone(b)
        self.assertAlmostEqual(b[1], 2.5)
        self.assertAlmostEqual(b[2], 4.0)        # (0.3 + 0.1) / 0.1
        clean = [(100.5, 12.0, 4.8)]            # 5 sigma: outside 3, inside 6
        self.assertIsNone(cw.detect_at(clean, wins, 50.0, 3.0, skip_wide=True))
        self.assertIsNotNone(cw.detect_at(clean, wins, 50.0, 6.0, skip_wide=False))
        # a window wider than P/4 is skipped at 3 sigma, capped otherwise
        wins = [(100.0, 2.0)]
        clean = [(101.0, 12.0, 4.8)]
        self.assertIsNone(cw.detect_at(clean, wins, 20.0, 3.0, skip_wide=True))
        b = cw.detect_at(clean, wins, 20.0, 9.0, skip_wide=False)
        self.assertAlmostEqual(b[2], 2.5)        # P/4 = 5 d over sd 2 d

    def test_profile_ci(self):
        grid = [0.0, 1.0, 2.0, 3.0, 4.0]
        prof = [-10.0, -3.0, 0.0, -1.0, -5.0]
        r = cw.profile_ci(grid, prof)
        self.assertEqual(r["best"], 2.0)
        self.assertEqual((r["lo95"], r["hi95"]), (2.0, 3.0))
        self.assertFalse(r["ci_hits_grid_edge"])

    def test_recovers_timing_scale(self):
        # 300 targets, every one eclipses (p = 1), true s_t = 2, windows of 3 sigma
        rng = random.Random(7)
        h = 3.0
        dets, zs = [], []
        for _ in range(300):
            z = rng.gauss(0.0, 2.0)
            if abs(z) <= h:
                dets.append(True)
                zs.append(z)
            else:
                dets.append(False)
                zs.append(float("nan"))
        hs = [h] * len(dets)
        fas = [0.0] * len(dets)
        res = cw.joint_fit([1.0], [[1.0] * len(dets)], dets, zs, hs, fas)
        self.assertTrue(1.6 <= res["s_t"]["best"] <= 2.5, res["s_t"])
        self.assertGreater(res["s_t"]["lo95"], 1.0)

    def test_k_and_s_separate(self):
        # inclination fine (p as given), timing too small by 2: the fit must not
        # blame the inclinations. p depends on a fake 'k' parameter: p(k) = p_true / k.
        rng = random.Random(11)
        n, h = 400, 3.0
        p_true = [rng.uniform(0.2, 0.9) for _ in range(n)]
        dets, zs = [], []
        for p in p_true:
            if rng.random() < p:
                z = rng.gauss(0.0, 2.0)
                if abs(z) <= h:
                    dets.append(True)
                    zs.append(z)
                    continue
            dets.append(False)
            zs.append(float("nan"))
        grid = [1.0, 1.25, 1.5, 2.0, 3.0]
        pp = [[p / k for p in p_true] for k in grid]
        res = cw.joint_fit(grid, pp, dets, zs, [h] * n, [0.0] * n)
        self.assertEqual(res["par"]["lo95"], 1.0, res["par"])
        self.assertGreater(res["s_t"]["lo95"], 1.2)


if __name__ == "__main__":
    unittest.main()
