# Tests for tyc_pixel.py 0.1.0 (pure standard library; fast).
# By MV2 of Munim, Inc.; made with AI agents working in his name. License: Apache-2.0.
import math
import random
import unittest

import tyc_pixel as tp


class TestMath(unittest.TestCase):
    def test_solve(self):
        x = tp.solve([[4.0, 1.0], [1.0, 3.0]], [1.0, 2.0])
        self.assertAlmostEqual(4 * x[0] + x[1], 1.0, places=10)
        self.assertAlmostEqual(x[0] + 3 * x[1], 2.0, places=10)
        with self.assertRaises(ValueError):
            tp.solve([[0.0, 0.0], [0.0, 0.0]], [1.0, 1.0])

    def test_lstsq(self):
        xs = [i / 10.0 for i in range(50)]
        y = [2.0 + 3.0 * x for x in xs]
        coef, chi2 = tp.lstsq([[1.0] * 50, xs], y, [1.0] * 50)
        self.assertAlmostEqual(coef[0], 2.0, places=6)
        self.assertAlmostEqual(coef[1], 3.0, places=6)
        self.assertLess(chi2, 1e-8)

    def test_nelder_mead(self):
        f = lambda p: (p[0] - 1.0) ** 2 + 3.0 * (p[1] + 2.0) ** 2  # noqa: E731
        p, v, _ = tp.nelder_mead(f, [0.0, 0.0], [0.5, 0.5], maxiter=500, xtol=1e-7)
        self.assertAlmostEqual(p[0], 1.0, places=4)
        self.assertAlmostEqual(p[1], -2.0, places=4)

    def test_pct(self):
        v = list(range(101))
        self.assertAlmostEqual(tp.pct(v, 0.025), 2.5)
        self.assertAlmostEqual(tp.pct(v, 0.975), 97.5)


class TestPSF(unittest.TestCase):
    def test_norm_and_centre(self):
        t = tp.psf_template(7.0, 7.0, 15, 15, (0.8, 0.7, 0.2, 0.0))
        self.assertAlmostEqual(sum(t), 1.0, delta=2e-3)
        self.assertEqual(max(range(225), key=lambda p: t[p]), 7 * 15 + 7)
        th = tp.psf_template(7.0, 7.0, 31, 31, (0.8, 0.7, 0.2, 0.2))
        self.assertAlmostEqual(sum(th), 1.0, delta=5e-3)

    def test_offcentre_pixel_convention(self):
        # x is the column, y the row
        t = tp.psf_template(10.0, 3.0, 15, 15, (0.6, 0.6, 0.0, 0.0))
        self.assertEqual(max(range(225), key=lambda p: t[p]), 3 * 15 + 10)

    def test_two_star_amplitudes(self):
        par = (0.75, 0.65, 0.15, 0.1)
        ct = tp.psf_template(5.0, 5.2, 11, 11, par)
        cn = tp.psf_template(6.5, 4.4, 11, 11, par)
        D = [0.06 * 50000 * a + 3.0 for a in ct]
        coef, _ = tp.lstsq([ct, cn, [1.0] * 121], D, [1.0] * 121)
        self.assertAlmostEqual(coef[0] / 50000, 0.06, places=6)
        self.assertAlmostEqual(coef[1], 0.0, delta=0.01)


class TestWindows(unittest.TestCase):
    def test_windows_and_diff(self):
        times = [tp.T0_BTJD - 1.0003 + k * 0.002 for k in range(2000)]
        frames = [[100.0 - (5.0 if abs(tp.fold_dt(t, tp.T0_BTJD, tp.P_TESS)) <= 0.012 else 0.0)]
                  for t in times]
        w = tp.eclipse_windows(times, tp.T0_BTJD, tp.P_TESS)
        self.assertEqual(len(w), 2)
        D = tp.diff_images(frames, w)
        for d in D:
            self.assertAlmostEqual(d[0], 5.0, places=9)
        idx = tp.mean_image_index(times, tp.T0_BTJD, tp.P_TESS)
        self.assertTrue(all(abs(tp.fold_dt(times[i], tp.T0_BTJD, tp.P_TESS)) > 0.08 for i in idx))

    def test_shape(self):
        self.assertEqual(tp.shape(0.0), 1.0)
        self.assertEqual(tp.shape(0.06), 0.0)
        self.assertAlmostEqual(tp.shape(0.5 * (tp._HALF14 + tp._HALF23)), 0.5)


class TestLabels(unittest.TestCase):
    def test_star_label(self):
        self.assertEqual(tp.star_label(0.9, 1.05, 40, 0.5), "PIX_ON_TARGET")
        self.assertEqual(tp.star_label(-0.1, 0.1, 0.2, 30), "PIX_ON_NEIGHBOUR")
        self.assertEqual(tp.star_label(0.4, 0.9, 10, 5), "PIX_UNRESOLVED")
        self.assertEqual(tp.star_label(0.9, 1.0, 4.0, 0.1), "PIX_UNRESOLVED")
        self.assertEqual(tp.star_label(0.9, 1.0, 40, 0.1, 0.2), "PIX_UNRESOLVED")

    def test_centroid_label(self):
        self.assertEqual(tp.centroid_label(0.5, 9.0), "CENTROID_ON_TARGET")
        self.assertEqual(tp.centroid_label(9.0, 0.5), "CENTROID_ON_NEIGHBOUR")
        self.assertEqual(tp.centroid_label(1.0, 2.0), "CENTROID_AMBIGUOUS")
        self.assertEqual(tp.centroid_label(5.0, 6.0), "CENTROID_ELSEWHERE")
        self.assertEqual(tp.centroid_label(float("nan"), 1.0), "CENTROID_UNTESTABLE")

    def test_depth_and_oversize(self):
        self.assertEqual(tp.depth_label(0.060, 0.001), "DEPTH_CONSISTENT")
        self.assertEqual(tp.depth_label(0.045, 0.001), "DEPTH_SHALLOWER")
        self.assertEqual(tp.depth_label(0.075, 0.001), "DEPTH_DEEPER")
        self.assertEqual(tp.depth_label(0.050, 0.006), "DEPTH_CONSISTENT")
        self.assertEqual(tp.oversize_label(0.060, 0.001), "OVERSIZE_SURVIVES")
        self.assertEqual(tp.oversize_label(0.020, 0.001), "OVERSIZE_WITHDRAWN")
        self.assertEqual(tp.oversize_label(0.033, 0.002), "OVERSIZE_WEAKENED")
        self.assertAlmostEqual(tp.SURVIVE_R, (1.5 * 0.117 / 0.224) ** 2)
        self.assertAlmostEqual(tp.WITHDRAW_R, (1.3 * 0.117 / 0.224) ** 2)

    def test_link_label(self):
        self.assertEqual(tp.link_label(60.0, [20.0, 25.0], 0.05), "LINK_UNIQUE")
        self.assertEqual(tp.link_label(60.0, [20.0, 35.0], 0.05), "LINK_AMBIGUOUS")
        self.assertEqual(tp.link_label(8.0, [1.0, 1.0], 0.05), "LINK_AMBIGUOUS")
        self.assertEqual(tp.link_label(60.0, [1.0, 1.0], 0.5), "LINK_AMBIGUOUS")


class TestAnalyseDiffs(unittest.TestCase):
    def test_small_case(self):
        rng = random.Random(3)
        par = (0.75, 0.65, 0.15, 0.1)
        ny = nx = 9
        ct = tp.psf_template(4.0, 4.2, ny, nx, par)
        cn = tp.psf_template(5.5, 3.4, ny, nx, par)
        f_t, f_n = 50000.0, 29000.0
        Ds = [[0.05 * f_t * a + rng.gauss(0, 20.0) for a in ct] for _ in range(8)]
        w = [1.0] * (ny * nx)
        r = tp.analyse_diffs(Ds, w, ct, cn, f_t, f_n, par, (4.0, 4.2), (5.5, 3.4), 0.15, ny, nx,
                             n_boot=50, n_boot_pos=5, log=lambda s: None)
        self.assertEqual(r["label"], "PIX_ON_TARGET")
        self.assertAlmostEqual(r["delta_t"], 0.05, delta=0.003)
        self.assertEqual(r["centroid"]["label"], "CENTROID_ON_TARGET")
        self.assertTrue(math.isfinite(r["f_t_lo"]))


if __name__ == "__main__":
    unittest.main()
