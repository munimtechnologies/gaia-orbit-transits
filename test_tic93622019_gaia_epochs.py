# SPDX-License-Identifier: Apache-2.0
"""Tests for tic93622019_gaia_epochs (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents).

The expected sets and numbers below were worked out by hand on 2026-11-24 from the same epochs
before the code ran; these tests are the machine check of that hand calculation. Stdlib only."""
import unittest

import tic93622019_gaia_epochs as m


def _set(times):
    return {round(t, 3) for t in times}


class TestHelpers(unittest.TestCase):
    def test_offset(self):
        self.assertAlmostEqual(m.offset(10.1, 0.0, 2.0), 0.1)
        self.assertAlmostEqual(m.offset(9.9, 0.0, 2.0), -0.1)
        self.assertAlmostEqual(m.offset(-3.95, 0.0, 2.0), 0.05)

    def test_median_sd(self):
        self.assertEqual(m.median([3, 1, 2]), 2)
        self.assertEqual(m.median([4, 1, 2, 3]), 2.5)
        self.assertAlmostEqual(m.robust_sd([1.0, 1.0, 1.0, 2.0, 0.0]), 0.0)

    def test_ephemerides(self):
        self.assertAlmostEqual(m.T0_TESS_BTJD + m.GAIA_MINUS_BTJD, 5508.5868496, places=5)
        # Gaia's period is a 4:3 alias of the TESS period (to 0.01%)
        self.assertAlmostEqual(m.P_GAIA / m.P_TESS, 4.0 / 3.0, delta=4.0 / 3.0 * 1e-4)


class TestHandCalculation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = m.analyse()

    def test_counts(self):
        self.assertEqual(self.r["n_epochs_listed"], 65)
        self.assertEqual(self.r["n_epochs_used"], 60)
        self.assertAlmostEqual(self.r["median_flux"], 177128.65, delta=20.0)

    def test_tess_windows(self):
        self.assertEqual(_set(self.r["in_tess"]["times"]),
                         _set([2029.652695, 2097.5919583, 2097.6659635, 2106.0960637,
                               2106.170083, 2258.989001, 2333.3100488]))
        core = self.r["core_tess"]
        self.assertEqual(_set(core["times"]),
                         _set([2029.652695, 2097.5919583, 2106.0960637, 2258.989001]))
        for x in core["rel"]:
            self.assertLess(x, -0.008)

    def test_gaia_box(self):
        g = self.r["in_gaia"]
        self.assertEqual(_set(g["times"]),
                         _set([2029.652695, 2097.5919583, 2097.6659635, 2106.0960637,
                               2258.989001, 2409.0160864, 2544.8975992, 2578.871416]))
        for x in g["rel"]:
            self.assertLess(x, -0.005)

    def test_overlap(self):
        both = self.r["both"]
        self.assertEqual(both["n"], 5)
        self.assertAlmostEqual(both["depth"], 0.01283, delta=0.0006)
        self.assertEqual(_set(self.r["tess_only"]["times"]), _set([2106.170083, 2333.3100488]))
        for x in self.r["tess_only"]["rel"]:
            self.assertLess(abs(x), 0.003)
        go = self.r["gaia_only"]
        self.assertEqual(_set(go["times"]), _set([2409.0160864, 2544.8975992, 2578.871416]))
        for ph in go["phase_tess"]:
            self.assertTrue(0.55 < ph < 0.65, ph)

    def test_low_epochs_outside_tess(self):
        o = self.r["outside_tess_windows"]
        self.assertEqual(o["n"], 53)
        self.assertEqual(o["n_low"], 6)
        self.assertEqual(o["n_low_in_gaia_box"], 3)
        self.assertEqual(_set(o["low_times"]),
                         _set([1696.7724808, 2202.823716, 2373.7911766, 2409.0160864,
                               2544.8975992, 2578.871416]))

    def test_scatter_and_snr(self):
        sd = self.r["robust_sd_out_of_both"]
        self.assertTrue(0.0008 < sd < 0.004, sd)
        self.assertGreater(self.r["in_tess"]["snr"], 3.0)
        self.assertLess(self.r["tess_timing_sigma_d"], 0.01)


if __name__ == "__main__":
    unittest.main()
