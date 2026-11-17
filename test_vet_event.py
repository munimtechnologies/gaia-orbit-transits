# SPDX-License-Identifier: Apache-2.0
"""Offline tests for vet_event (MV2 of Munim, Inc.; made with AI agents)."""
import unittest

import numpy as np

import vet_event as ve


class TestClean(unittest.TestCase):
    def test_sort_normalise_floor(self):
        t = np.array([3, 1, 2, 4, 5], float)
        f = np.array([2, 2, 0.5, 2, np.nan])
        tt, ff, nbad = ve.clean(t, f)
        self.assertEqual(list(tt), [1, 3, 4])
        self.assertTrue(np.allclose(ff, 1.0))
        self.assertEqual(nbad, 1)


class TestBoxDepth(unittest.TestCase):
    def _lc(self, slope=0.0):
        rng = np.random.default_rng(3)
        t = np.arange(0, 4, 2 / 1440.0)
        f = 1 + 1e-3 * rng.standard_normal(t.size) + slope * (t - 2)
        f[np.abs(t - 2.0) <= 1 / 6] -= 0.01
        return t, f

    def test_recovers_depth(self):
        t, f = self._lc()
        m = ve.box_depth(t, f, 2.0, 1 / 3, 1.5)
        self.assertAlmostEqual(m["depth"], 0.01, delta=1e-3)
        self.assertGreater(m["snr"], 50)
        self.assertGreater(m["fill"], 0.9)

    def test_linear_baseline(self):
        t, f = self._lc(slope=2e-3)
        m = ve.box_depth(t, f, 2.0, 1 / 3, 1.5)
        self.assertAlmostEqual(m["depth"], 0.01, delta=1e-3)

    def test_no_data(self):
        t = np.arange(10, 12, 2 / 1440.0)
        m = ve.box_depth(t, np.ones_like(t), 2.0, 1 / 3, 1.5)
        self.assertEqual(m["n_in"], 0)
        self.assertTrue(np.isnan(m["depth"]))


class TestEpochs(unittest.TestCase):
    def test_epoch_windows(self):
        w = ve.epoch_windows(100.0, 10.0, 0.1, kmin=-1, kmax=2, nsig=3.0)
        self.assertEqual([x[0] for x in w], [-1, 1, 2])
        self.assertAlmostEqual(w[0][1], 89.7)
        self.assertAlmostEqual(w[0][2], 90.3)
        self.assertAlmostEqual(w[1][1], 109.7)
        self.assertAlmostEqual(w[2][1], 119.4)
        self.assertAlmostEqual(w[2][2], 120.6)

    def test_covered_periods(self):
        t = np.arange(119.0, 120.0, 2 / 1440.0)
        Ps = ve.covered_periods(t, 100.0, 2, 9.7, 10.3, 0.2)
        self.assertAlmostEqual(Ps.min(), 9.7)
        self.assertTrue(9.97 < Ps.max() < 10.02)


class TestPixelsAndNeighbours(unittest.TestCase):
    def test_weighted_centroid(self):
        img = np.zeros((5, 5))
        img[1, 3] = 2
        img[3, 3] = 2
        img[0, 0] = -5
        x, y = ve.weighted_centroid(img)
        self.assertAlmostEqual(x, 3.0)
        self.assertAlmostEqual(y, 2.0)

    def test_neighbour_stats(self):
        s = ve.neighbour_stats([1, 2, 4, 5, np.nan], 4.5)
        self.assertEqual(s["n"], 4)
        self.assertAlmostEqual(s["frac_dim"], 0.5)
        self.assertAlmostEqual(s["median_snr"], 3.0)
        self.assertEqual(s["target_rank"], 2)


class TestVerdict(unittest.TestCase):
    def _clean(self):
        return {"neighbour_frac_dim": 0.0, "pdc_snr": 10.0, "pdc_depth": 0.01,
                "sap_snr": 9.0, "sap_depth": 0.009, "flagged_frac": 0.0,
                "diff_offset_px": 0.3, "cut_snr": 5.0, "depth_max": 0.03,
                "box_fill": 0.9, "repeat_excluded": False}

    def test_survives(self):
        self.assertEqual(ve.verdict(self._clean())[0], "SURVIVES")

    def test_neighbours_reject(self):
        v = self._clean()
        v["neighbour_frac_dim"] = 0.5
        res, reasons = ve.verdict(v)
        self.assertEqual(res, "REJECTED")
        self.assertTrue(any(r.startswith("SYSTEMATIC") for r in reasons))

    def test_sap_reject(self):
        v = self._clean()
        v["sap_snr"], v["sap_depth"] = 1.0, 0.001
        self.assertEqual(ve.verdict(v)[0], "REJECTED")

    def test_too_deep(self):
        v = self._clean()
        v["pdc_depth"] = 0.05
        self.assertEqual(ve.verdict(v)[0], "REJECTED")

    def test_no_repeat_is_unresolved(self):
        v = self._clean()
        v["repeat_excluded"] = True
        self.assertEqual(ve.verdict(v)[0], "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
