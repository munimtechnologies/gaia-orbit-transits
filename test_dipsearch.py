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
        self.assertLessEqual(best["coherence"], 0.75)

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


class TestFluxFloor(unittest.TestCase):
    """0.4.2: broken cadences (flux ~0.1, as in the Sector 104 QLP light curves)."""

    def _broken(self):
        rng = np.random.default_rng(7)
        t, f = _sector(rng)
        bad = np.abs(t - 1510.0) < 0.3
        f[bad] = 0.1
        return t, f, int(bad.sum())

    def test_floor_drops_broken_cadences(self):
        t, f, nbad = self._broken()
        ev, binned = ds.search(t, f)
        self.assertEqual(binned["n_below_floor"], nbad)
        # 0.4.3: the 0.5-d pad drops more than the sub-floor cadences
        self.assertGreater(binned["n_floor_dropped"], nbad)
        for e in ev:
            if abs(e["t_center"] - 1510.0) < 0.5:
                self.assertLess(e["depth_ppm"], 1e5)

    def test_without_floor_artifact_dominates(self):
        t, f, _ = self._broken()
        ev, binned = ds.search(t, f, flux_floor=None, coherence_max=None)
        self.assertEqual(binned["n_below_floor"], 0)
        self.assertTrue(ev)
        self.assertLess(abs(ev[0]["t_center"] - 1510.0), 0.5)
        self.assertGreater(ev[0]["depth_ppm"], 1e5)


class TestFloorPad(unittest.TestCase):
    """0.4.3: the ramps into and out of the broken stretch (as seen on TIC 41898425,
    Sector 104, in gaia-watchlist-tess-v2) must go too."""

    def _ramped(self):
        rng = np.random.default_rng(31)
        t, f = _sector(rng)
        floor = np.abs(t - 1510.0) < 0.3                  # 1509.7 .. 1510.3 at 0.1
        f[floor] = 0.1
        down = (t >= 1509.4) & (t < 1509.7)               # 1.0 -> 0.5 linearly
        f[down] = 1.0 - 0.5 * (t[down] - 1509.4) / 0.3
        up = (t > 1510.3) & (t <= 1510.6)                 # 0.5 -> 1.0 linearly
        f[up] = 0.5 + 0.5 * (t[up] - 1510.3) / 0.3
        return t, f

    def test_floor_mask_pad(self):
        t = np.arange(0.0, 3.0, 0.1)
        f = np.ones_like(t)
        f[15] = 0.2                                       # t = 1.5
        drop, n_low = ds.floor_mask(t, f, 0.5, 0.5)
        self.assertEqual(n_low, 1)
        # |t - 1.5| <= 0.5 -> t = 1.0 .. 2.0 -> 11 cadences (float rounding aside)
        self.assertIn(int(drop.sum()), (10, 11))
        self.assertTrue(drop[15] and drop[12] and drop[18])
        self.assertFalse(drop[5] or drop[25])
        drop0, _ = ds.floor_mask(t, f, 0.5, 0.0)
        self.assertEqual(int(drop0.sum()), 1)
        dropn, nn = ds.floor_mask(t, f, None, 0.5)
        self.assertEqual((int(dropn.sum()), nn), (0, 0))

    def test_ramps_survive_without_pad(self):
        t, f = self._ramped()
        ev, _ = ds.search(t, f, floor_pad=0.0, coherence_max=None)
        near = [e for e in ev if abs(e["t_center"] - 1510.0) < 0.8]
        self.assertTrue(near, "ramp artefact should appear without the pad")
        self.assertGreater(max(e["depth_ppm"] for e in near), 1e4)

    def test_pad_removes_ramps(self):
        t, f = self._ramped()
        ev, binned = ds.search(t, f)
        for e in ev:
            self.assertLess(e["depth_ppm"], 5000, e)
        # pad covers 1509.2 .. 1510.8, so both ramps are gone
        self.assertGreater(binned["n_floor_dropped"],
                           int((np.abs(t - 1510.0) <= 0.6).sum()) - 1)


class TestCoherence(unittest.TestCase):
    """0.4.3: one scattered 30-min bin (as on TIC 322271767 in gaia-watchlist-tess-v2)."""

    def test_box_coherence_values(self):
        # flat-bottomed dip filling the box: coherence 0
        self.assertAlmostEqual(ds.box_coherence([-0.01] * 4, 0.01), 0.0)
        # half filled: mean d/2, sd d/2 -> 1
        self.assertAlmostEqual(ds.box_coherence([-0.01, -0.01, 0, 0], 0.005), 1.0)
        # one-bin spike in a 4-bin box: sqrt(3)
        self.assertAlmostEqual(ds.box_coherence([-0.2, 0, 0, 0], 0.05), 3 ** 0.5)
        # the TIC 322271767 box: deficits .18, 0, .07, .06 -> mean .0775, sd .0649
        r = [-0.18, 0.0, -0.07, -0.06]
        self.assertAlmostEqual(ds.box_coherence(r, 0.0775), 0.0649 / 0.0775, places=2)
        self.assertEqual(ds.box_coherence([0, 0], 0.0), float("inf"))

    def _spiked(self):
        rng = np.random.default_rng(41)
        t, f = _sector(rng)
        spike = (t >= 1505.0) & (t < 1505.0 + 1 / 48)
        f[spike] = 0.8
        return t, f

    def test_spike_without_coherence_is_an_event(self):
        t, f = self._spiked()
        ev, binned = ds.search(t, f, coherence_max=None)
        self.assertTrue(any(abs(e["t_center"] - 1505.0) < 0.6 for e in ev))
        self.assertEqual(binned["n_incoherent"], 0)

    def test_spike_is_rejected(self):
        t, f = self._spiked()
        ev, binned = ds.search(t, f)
        self.assertFalse(any(abs(e["t_center"] - 1505.0) < 0.6 for e in ev), ev)
        self.assertGreater(binned["n_incoherent"], 0)

    def test_short_real_dip_survives(self):
        # 3-h, 3000 ppm flat dip: the 2-h box sits inside it
        rng = np.random.default_rng(43)
        t, f = _sector(rng)
        tc = 1518.0
        f[np.abs(t - tc) < 1.5 / 24] -= 3e-3
        ev, _ = ds.search(t, f)
        self.assertTrue(ev)
        self.assertLess(abs(ev[0]["t_center"] - tc), 0.1)
        self.assertGreater(ev[0]["depth_ppm"], 2000)

    def test_grazing_v_dip_survives(self):
        # 8-h V-shaped dip, 3000 ppm at the centre
        rng = np.random.default_rng(47)
        t, f = _sector(rng)
        tc, half = 1503.0, 4 / 24.0
        x = np.abs(t - tc)
        inside = x < half
        f[inside] -= 3e-3 * (1 - x[inside] / half)
        ev, _ = ds.search(t, f)
        self.assertTrue(ev)
        self.assertLess(abs(ev[0]["t_center"] - tc), 0.15)
        self.assertLessEqual(ev[0]["coherence"], 0.75)


if __name__ == "__main__":
    unittest.main()
