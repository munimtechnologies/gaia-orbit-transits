# SPDX-License-Identifier: Apache-2.0
"""Synthetic end-to-end tests for eb_char (numpy + scipy; no downloads)."""
import unittest

import numpy as np

import eb_char as ec


def synth(seed=1):
    rng = np.random.default_rng(seed)
    dt = 2.0 / 1440
    t = np.concatenate([np.arange(0.0, 12.0, dt), np.arange(26.0, 38.0, dt)])
    trend = 1.0 + 0.002 * np.sin(2 * np.pi * t / 7.0)
    ecl = np.zeros_like(t)
    for tc in (5.3, 31.8):
        ecl += 0.1 * ec.shape_np(t - tc, 0.12, 0.6)
    f = trend * (1.0 - ecl) + rng.normal(0, 1e-3, t.size)
    return t, f


class TestFit(unittest.TestCase):
    def test_detrend_and_fit(self):
        t, f = synth()
        masked = ec.near_any(t, [5.3, 31.8], 0.25)
        d = ec.detrend_masked(t, f, masked, window=1.5)
        oot = ~masked & np.isfinite(d)
        self.assertLess(abs(np.median(d[oot]) - 1.0), 2e-4)
        for tc_true, tc0 in ((5.3, 5.32), (31.8, 31.78)):
            r = ec.fit_eclipse(t, d, tc0, 0.1, 0.4)
            self.assertIsNotNone(r)
            self.assertLess(abs(r["tc"] - tc_true), 3.0 / 1440)
            self.assertLess(abs(r["depth"] - 0.1), 0.005)
            self.assertLess(abs(r["t14_d"] - 0.12), 0.01)
            self.assertTrue(r["full"])

    def test_no_data(self):
        t, f = synth()
        self.assertIsNone(ec.fit_eclipse(t, f, 20.0, 0.1, 0.4))   # in the gap

    def test_box_scan_finds_secondary(self):
        rng = np.random.default_rng(2)
        P, T0 = 26.5, 3.0
        t = np.arange(0.0, 60.0, 2.0 / 1440)
        ph = ((t - T0) / P) % 1.0
        f = 1.0 + rng.normal(0, 1e-3, t.size)
        f[np.abs(ph - 0.74) * P < 0.175] -= 0.003
        rows = ec.box_scan(ph, f, 1e-3, P, [0.2, 0.35])
        self.assertLess(abs(rows[0]["phase"] - 0.74), 0.01)
        self.assertGreater(rows[0]["depth"], 0.0015)
        self.assertGreater(rows[0]["snr"], 20)

    def test_dip_census(self):
        t = np.arange(0.0, 5.0, 2.0 / 1440)
        f = np.ones_like(t)
        f[(t > 2.0) & (t < 2.2)] = 0.95
        dips = ec.dip_census(t, f, 1e-4)
        self.assertEqual(len(dips), 1)
        self.assertAlmostEqual(dips[0]["depth"], 0.05, places=6)
        self.assertTrue(2.0 <= dips[0]["t_min"] <= 2.2)


if __name__ == "__main__":
    unittest.main()
