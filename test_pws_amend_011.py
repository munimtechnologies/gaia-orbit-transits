# SPDX-License-Identifier: Apache-2.0
# Tests for pws_amend_011 (MV2 of Munim, Inc.; made with AI agents working in his name).
# Needs tyc_pixel.py 0.1.0 and pixel_which_star.py 0.1.0 next to it (fetch_pinned.py).
import random
import unittest

import pws_amend_011 as am
import tyc_pixel as tp
import pixel_which_star as pws


def kkt_ok(A, b, x, cons, tol=1e-7):
    K = len(b)
    grad = [b[k] - sum(A[k][j] * x[j] for j in range(K)) for k in range(K)]
    sc = max(abs(v) for v in b) or 1.0
    for k in range(K):
        if k in cons:
            if x[k] < 0:
                return False
            if x[k] > 0 and abs(grad[k]) > tol * sc:
                return False
            if x[k] == 0 and grad[k] > tol * sc:
                return False
        elif abs(grad[k]) > tol * sc:
            return False
    return True


class TestNNLS(unittest.TestCase):
    def test_random_problems_satisfy_kkt(self):
        rng = random.Random(5)
        for trial in range(40):
            K, R = rng.randint(2, 7), 12
            G = [[rng.gauss(0, 1) for _ in range(K)] for _ in range(R)]
            y = [rng.gauss(0, 1) for _ in range(R)]
            A = [[sum(G[r][i] * G[r][j] for r in range(R)) for j in range(K)] for i in range(K)]
            b = [sum(G[r][i] * y[r] for r in range(R)) for i in range(K)]
            cons = set(range(K - 1)) if trial % 2 else set(range(K))
            x = am.nnls_normal(A, b, cons)
            self.assertTrue(kkt_ok(A, b, x, cons), (trial, x))

    def test_unconstrained_matches_solve(self):
        A = [[4.0, 1.0], [1.0, 3.0]]
        b = [1.0, -2.0]
        x = am.nnls_normal(A, b, [])
        ref = tp.solve(A, b)
        self.assertAlmostEqual(x[0], ref[0], places=12)
        self.assertAlmostEqual(x[1], ref[1], places=12)

    def test_lstsq_nn_equals_lstsq_when_positive(self):
        cols = [[1.0, 2.0, 0.5, 0.1], [0.0, 1.0, 1.0, 2.0], [1.0, 1.0, 1.0, 1.0]]
        y = [2.52, 5.98, 3.76, 5.14]  # ~ 1.5 col0 + 2 col1 + 1 col2
        w = [1.0, 1.0, 1.0, 1.0]
        c1, x1 = tp.lstsq(cols, y, w)
        c2, x2 = am.lstsq_nn(cols, y, w, [0, 1])
        self.assertTrue(all(v > 0 for v in c1[:2]))
        for a, b in zip(c1, c2):
            self.assertAlmostEqual(a, b, places=8)
        self.assertAlmostEqual(x1, x2, places=8)


class TestGroups(unittest.TestCase):
    def test_split_merges_close_star_into_target(self):
        s = [am.mk("T", 10.0, 5.0, 5.0, "T"), am.mk("N", 12.0, 7.0, 5.0, "N"),
             am.mk("C", 10.3, 5.03, 5.0), am.mk("B", 11.0, 1.0, 1.0), am.mk("F", 15.0, 9.0, 9.0),
             am.mk("G", 15.5, 7.2, 5.1)]
        prim, groups, faint = am.split_groups(s)
        self.assertEqual([p["id"] for p in prim], ["T", "N", "B"])
        self.assertEqual([x["id"] for x in groups[0]], ["T", "C"])
        self.assertEqual([x["id"] for x in groups[1]], ["N", "G"])
        self.assertEqual([x["id"] for x in faint], ["F"])

    def test_group_weights_sum_to_one(self):
        g = [am.mk("T", 10.0, 0, 0, "T"), am.mk("C", 12.5, 0, 0)]
        w = am.group_weights(g)
        self.assertAlmostEqual(sum(w), 1.0)
        self.assertAlmostEqual(w[1] / w[0], 0.1, places=9)

    def test_tie(self):
        g = [[am.mk("T", 10.0, 0, 0, "T")], [am.mk("N", 12.5, 2, 0, "N")]]
        c, src = am.tie_neighbour([2000.0, 0.0], g, 0, 1)
        self.assertEqual(src, "N_FLUX_GAIA_TIED")
        self.assertAlmostEqual(c[1], 200.0)
        c, src = am.tie_neighbour([0.0, 0.0], g, 0, 1)
        self.assertEqual(src, "N_FLUX_FIT")


class TestInstall(unittest.TestCase):
    def test_install_patches(self):
        am.install()
        self.assertIs(tp.fit_mean_image, am.fit_mean_image_011)
        self.assertIs(pws.analyse_sector, am.analyse_sector_011)
        self.assertEqual(pws.VERSION, "0.1.1")
        am.install()  # idempotent
        self.assertIsNot(am._ORIG["analyse_sector"], am.analyse_sector_011)


if __name__ == "__main__":
    unittest.main()
