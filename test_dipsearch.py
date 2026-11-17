# SPDX-License-Identifier: Apache-2.0
import unittest

import numpy as np

import dipsearch as ds


def _sector(rng, sigma=1e-3, t0=1500.0):
    t = np.concatenate([np.arange(t0, t0 + 13, 2 / 1440.0),
                        np.arange(t0 + 14, t0 + 27, 2 / 1440.0)])
    f = 1 + sigma * rng.standard_normal(t.size)
    return t, f


class TestBinning(unittest.TestCase):
    def test_bin_and_segments(self):
        t = np.arange(0, 2, 2 / 1440.0)
        bt, bf, bn = ds.bin_lc(t, np.ones_like(t), 1 / 48)
        self.assertEqual(bt.size, 96)
        self.assertTrue(np.allclose(bf, 1))
        segs = ds.segments(np.array([0, 0.1, 0.2, 2.0, 2.1]), gap=0.5)
        self.assertEqual(segs, [(0, 3), (3, 5)])

    def test_running_median_flat(self):
        t = np.linspace(0, 10, 500)
        y = np.full(500, 3.0)
        self.assertTrue(np.allclose(ds.running_median(t, y, 1.0), 3.0))


class TestSearch(unittest.TestCase):
    def test_recovers_injected_dip(self):
        rng = np.random.default_rng(11)
        t, f = _sector(rng)
        tc, dur, depth = 1505.3, 8 / 24.0, 2e-3
        f[np.abs(t - tc) < dur / 2] -= depth
        ev, binned = ds.search(t, f)
        self.assertTrue(ev, "no event found")
        best = ev[0]
        self.assertLess(abs(best["t_center"] - tc), 0.15)
        self.assertGreater(best["snr"], 10)
        self.assertTrue(4 <= best["duration_h"] <= 16)
        self.assertGreater(best["depth_ppm"], 1000)

    def test_recovers_long_dip_with_trend(self):
        rng = np.random.default_rng(5)
        t, f = _sector(rng)
        f = f * (1 + 2e-3 * np.sin(2 * np.pi * (t - t[0]) / 9.0))
        tc, dur, depth = 1520.0, 20 / 24.0, 3e-3
        f[np.abs(t - tc) < dur / 2] -= depth
        ev, _ = ds.search(t, f)
        self.assertTrue(ev)
        self.assertLess(abs(ev[0]["t_center"] - tc), 0.3)

    def test_noise_only_is_quiet(self):
        rng = np.random.default_rng(23)
        t, f = _sector(rng)
        ev, _ = ds.search(t, f, snr_min=7.0)
        self.assertEqual(ev, [])


if __name__ == "__main__":
    unittest.main()
