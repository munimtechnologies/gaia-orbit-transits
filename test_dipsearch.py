# SPDX-License-Identifier: Apache-2.0
import unittest

import numpy as np

import dipsearch as ds


def _sector(rng, sigma=1e-3, t0=1500.0):
    t = np.concatenate([np.arange(t0, t0 + 13, 2 / 1440.0),
                        np.arange(t0 + 14, t0 + 27, 2 / 1440.0)])
    f = 1 + sigma * rng.standard_normal(t.size)
    return t, f


def _with_gap(rng, g0, glen, sigma=1e-3):
    """_sector with the cadences between g0 and g0 + glen removed.
    Returns t, f, tb (last cadence before the gap), ta (first after)."""
    t, f = _sector(rng, sigma)
    keep = ~((t > g0) & (t < g0 + glen))
    t, f = t[keep], f[keep]
    tb = float(t[t <= g0].max())
    ta = float(t[t >= g0 + glen].min())
    return t, f, tb, ta


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


class TestGapMask(unittest.TestCase):
    """0.4.4: the gap pad itself, on exact binary fractions (no float rounding)."""

    def _t(self):
        a = np.arange(0, 1, 0.0625)          # 0 .. 0.9375, 16 cadences
        b = 1.25 + np.arange(0, 1, 0.0625)   # 1.25 .. 2.1875, 16 cadences
        return np.concatenate([a, b])        # one gap: 0.9375 -> 1.25 (0.3125 d)

    def test_gap_edges(self):
        before, after = ds.gap_edges(self._t(), 0.1)
        self.assertEqual(list(before), [0.9375])
        self.assertEqual(list(after), [1.25])
        before, after = ds.gap_edges(self._t(), 0.1, pad_ends=True)
        self.assertEqual(list(before), [0.9375, 2.1875])
        self.assertEqual(list(after), [0.0, 1.25])
        # a gap shorter than gap_min is not a gap
        self.assertEqual(ds.gap_edges(self._t(), 0.5)[0].size, 0)

    def test_gap_mask_counts(self):
        t = self._t()
        drop, n = ds.gap_mask(t, 0.1, 0.25, pad_ends=False)
        self.assertEqual(n, 1)
        # before the gap: 0.6875 .. 0.9375 (5); after: 1.25 .. 1.5 (5)
        self.assertEqual(int(drop.sum()), 10)
        self.assertEqual(sorted(t[drop].tolist()),
                         [0.6875, 0.75, 0.8125, 0.875, 0.9375,
                          1.25, 1.3125, 1.375, 1.4375, 1.5])
        # with the series ends: + 0 .. 0.25 (5) and 1.9375 .. 2.1875 (5)
        drop, n = ds.gap_mask(t, 0.1, 0.25, pad_ends=True)
        self.assertEqual((int(drop.sum()), n), (20, 1))
        # order of the input does not matter
        rng = np.random.default_rng(3)
        p = rng.permutation(t.size)
        dropp, _ = ds.gap_mask(t[p], 0.1, 0.25, pad_ends=True)
        self.assertTrue(np.array_equal(dropp, drop[p]))
        # no pad -> nothing dropped
        self.assertEqual(int(ds.gap_mask(t, 0.1, 0.0)[0].sum()), 0)

    def test_dr4_options_split_segments(self):
        o = ds.DR4_GAP_OPTIONS
        # every padded gap is at least 0.1 + 2 * 0.25 = 0.6 d > the 0.5-d segment gap
        self.assertGreater(o["gap_min"] + 2 * o["gap_pad"], 0.5)


class TestGapEdgeArtefacts(unittest.TestCase):
    """0.4.4: the two gap-edge artefacts of gaia-watchlist-tess-v3."""

    def _step(self):
        # TIC 322271767-like: 2-h, 8% step down right after a 0.3-d gap
        rng = np.random.default_rng(53)
        t, f, tb, ta = _with_gap(rng, 1505.0, 0.3)
        f[(t >= ta) & (t < ta + 2 / 24)] -= 0.08
        return t, f, tb, ta

    def _ramp(self):
        # TIC 231290240-like: 0.7% ramp over the 4 h before a 0.17-d gap, level
        # 0.1% higher after it
        rng = np.random.default_rng(59)
        t, f, tb, ta = _with_gap(rng, 1508.0, 0.17)
        m = (t >= tb - 4 / 24) & (t <= tb)
        f[m] -= 0.007 * (t[m] - (tb - 4 / 24)) / (4 / 24)
        f[(t >= ta) & (t < 1513.0)] += 0.001
        return t, f, tb, ta

    def test_step_found_without_gap_pad(self):
        t, f, tb, ta = self._step()
        ev, binned = ds.search(t, f)                     # 0.4.3 defaults
        self.assertEqual(binned["n_gap_dropped"], 0)
        near = [e for e in ev if abs(e["t_center"] - ta) < 0.3]
        self.assertTrue(near, "gap-edge step should appear with 0.4.3 defaults")
        self.assertGreater(max(e["depth_ppm"] for e in near), 4e4)

    def test_step_removed_by_gap_pad(self):
        t, f, tb, ta = self._step()
        ev, binned = ds.search(t, f, **ds.DR4_GAP_OPTIONS)
        # gaps: the 0.3-d one and the 1-d mid-sector one
        self.assertEqual(binned["n_gaps"], 2)
        self.assertGreater(binned["n_gap_dropped"], 0)
        for e in ev:
            if abs(e["t_center"] - ta) < 0.5:
                self.assertLess(e["depth_ppm"], 5000, e)

    def test_ramp_found_without_gap_pad(self):
        t, f, tb, ta = self._ramp()
        ev, _ = ds.search(t, f)
        near = [e for e in ev if abs(e["t_center"] - tb) < 0.4]
        self.assertTrue(near, "pre-gap ramp should appear with 0.4.3 defaults")
        self.assertGreater(max(e["depth_ppm"] for e in near), 1500)

    def test_ramp_removed_by_gap_pad(self):
        t, f, tb, ta = self._ramp()
        ev, _ = ds.search(t, f, **ds.DR4_GAP_OPTIONS)
        for e in ev:
            if abs(e["t_center"] - tb) < 0.5:
                self.assertLess(e["depth_ppm"], 1500, e)

    def test_transit_one_day_from_gap_survives(self):
        # 6-h, 2000 ppm flat transit 1 d after the 0.3-d gap
        rng = np.random.default_rng(61)
        t, f, tb, ta = _with_gap(rng, 1505.0, 0.3)
        tc = ta + 1.0
        f[np.abs(t - tc) < 3 / 24] -= 2e-3
        ev, _ = ds.search(t, f, **ds.DR4_GAP_OPTIONS)
        near = [e for e in ev if abs(e["t_center"] - tc) < 0.1]
        self.assertTrue(near, ev)
        best = max(near, key=lambda e: e["snr"])
        self.assertGreater(best["snr"], 10)
        # 4-h box ~2000 ppm, or 8-h box 6/8 x 2000 = 1500 ppm minus ~110 ppm of
        # running-median pull (25% of the 1-d window is in transit)
        self.assertGreater(best["depth_ppm"], 1000)
        # nearest edge is the padded gap end, ~0.75 d away
        self.assertGreater(best["edge_dist_d"], 0.5)
        self.assertFalse(best["near_edge"])

    def test_short_gap_counts_as_edge(self):
        # 8-h, 3000 ppm transit 0.3 d after a 0.2-d gap, no pad: only edge_gap
        # can flag it (the gap is shorter than the 0.5-d segment gap)
        rng = np.random.default_rng(67)
        t, f, tb, ta = _with_gap(rng, 1505.0, 0.2)
        tc = ta + 0.3
        f[np.abs(t - tc) < 4 / 24] -= 3e-3
        ev, _ = ds.search(t, f)
        near = [e for e in ev if abs(e["t_center"] - tc) < 0.15]
        self.assertTrue(near)
        self.assertFalse(near[0]["near_edge"])           # 0.4.3 behaviour
        self.assertNotIn("edge_dist_d", near[0])
        ev, _ = ds.search(t, f, edge_gap=0.1)
        near = [e for e in ev if abs(e["t_center"] - tc) < 0.15]
        self.assertTrue(near)
        self.assertTrue(near[0]["near_edge"])
        self.assertLess(near[0]["edge_dist_d"], 0.5)


if __name__ == "__main__":
    unittest.main()
