# SPDX-License-Identifier: Apache-2.0
"""Tests for deepcheck.py (gaia-orbit-transits 0.9.0; MV2 of Munim, Inc., made with AI agents).

All synthetic times are multiples of 1/64 d so that box edges are exact binary fractions."""
import math
import unittest

import numpy as np

import archival as ar
import deepcheck as dc


def _seg(t, f, name="syn"):
    return {"name": name, "survey": "synthetic", "t": t, "f": f}


def _alternating(n):
    k = np.arange(n)
    return np.where(k % 2 == 0, 1.0 + 1.0 / 1024, 1.0 - 1.0 / 1024)


class TestTime(unittest.TestCase):
    def test_bkjd_to_btjd(self):
        # BKJD = BJD - 2454833, BTJD = BJD - 2457000 -> BTJD = BKJD - 2167
        self.assertEqual(float(dc.bkjd_to_btjd(0.0)), -2167.0)
        self.assertEqual(float(dc.bkjd_to_btjd(2167.0)), 0.0)

    def test_kepler_detrend_registered(self):
        self.assertEqual(ar.DETREND["kepler"], (1.5, 0.3))


class TestPrepareDeep(unittest.TestCase):
    def test_deep_dip_kept_but_dropped_by_archival(self):
        # 500 flat points, 5 of them 25% low. median d = 0, sd -> floor 1e-4.
        # archival.prepare clips d >= max(8e-4, 0.08) -> the 5 points are lost (495 left);
        # prepare_deep clips at max(8e-4, 0.6) -> all 500 kept.
        t = np.arange(500) / 64.0
        f = np.ones(500)
        f[100:105] = 0.75
        old = ar.prepare([_seg(t, f)], 0.25)
        new = dc.prepare_deep([_seg(t, f)], 0.25)
        self.assertEqual(old["t"].size, 495)
        self.assertEqual(new["t"].size, 500)
        self.assertAlmostEqual(float(new["d"].max()), 0.25, places=12)

    def test_same_as_archival_for_shallow_data(self):
        t = np.arange(1281) / 64.0
        f = _alternating(1281)
        f[np.abs(t - 10.0) < 0.125] *= 63.0 / 64.0
        old = ar.prepare([_seg(t, f)], 0.25)
        new = dc.prepare_deep([_seg(t, f)], 0.25)
        self.assertTrue(np.array_equal(old["t"], new["t"]))
        self.assertTrue(np.array_equal(old["d"], new["d"]))


class TestDeepestDips(unittest.TestCase):
    def test_finds_injected_dip(self):
        # t = k/64, k = 0..1280. Dip |t - 10| < 0.125 -> k = 633..647 (15 points), depth 1/16.
        # Noise +-1/1024 alternating. After normalising by the median (1 - 1/1024) the 15
        # dipped residuals average 0.0625 - (7/15)*0.00183 ~ 0.0617. A box of D = 0.25
        # centred at t = 10 holds exactly these 15 points; any shifted box loses one.
        t = np.arange(1281) / 64.0
        f = _alternating(1281)
        f[np.abs(t - 10.0) < 0.125] *= 15.0 / 16.0
        data = dc.prepare_deep([_seg(t, f)], 0.25)
        dips = dc.deepest_dips(data["t"], data["d"], data["w"], 0.25, survey=data["survey"])
        self.assertGreaterEqual(len(dips), 2)
        self.assertEqual(dips[0]["t"], 10.0)
        self.assertEqual(dips[0]["n"], 15)
        self.assertLess(abs(dips[0]["depth"] - 1.0 / 16), 0.004)
        self.assertEqual(dips[0]["survey"], "synthetic")
        for other in dips[1:]:
            self.assertGreaterEqual(abs(other["t"] - 10.0), dc.DIP_SEP_D)
            self.assertLess(other["snr"], dips[0]["snr"])

    def test_empty(self):
        self.assertEqual(dc.deepest_dips(np.array([]), np.array([]), np.array([]), 0.25), [])


class TestConjOffset(unittest.TestCase):
    def test_offset_and_sigma(self):
        # n = round((352 - 50) / 100) = 3; T3 = 350; dt = 2;
        # var = 1^2 + 3^2 * 0.5^2 + 0 = 3.25
        eph = {"P_mu": 100.0, "T_mu": 50.0, "P_sd": 0.5, "T_sd": 1.0, "rho": 0.0}
        o = dc.conj_offset(352.0, eph)
        self.assertEqual(o["n"], 3)
        self.assertEqual(o["dt_d"], 2.0)
        self.assertAlmostEqual(o["sd_d"], math.sqrt(3.25), places=12)
        self.assertAlmostEqual(o["z"], 2.0 / math.sqrt(3.25), places=12)

    def test_correlation_term(self):
        # rho = 0.5, n = -1: var = 1 + 0.25 + 2*(-1)*0.5*1*0.5 = 0.75
        eph = {"P_mu": 100.0, "T_mu": 50.0, "P_sd": 0.5, "T_sd": 1.0, "rho": 0.5}
        o = dc.conj_offset(-50.0, eph)
        self.assertEqual(o["n"], -1)
        self.assertEqual(o["dt_d"], 0.0)
        self.assertAlmostEqual(o["sd_d"], math.sqrt(0.75), places=12)


class TestKeplerMatch(unittest.TestCase):
    def test_rules(self):
        self.assertTrue(dc.kepler_match_ok(3.0, None, 13.6))
        self.assertTrue(dc.kepler_match_ok(7.0, 13.9, 13.6))
        self.assertFalse(dc.kepler_match_ok(7.0, 15.0, 13.6))
        self.assertFalse(dc.kepler_match_ok(12.0, 13.6, 13.6))
        self.assertFalse(dc.kepler_match_ok(float("nan"), 13.6, 13.6))
        self.assertFalse(dc.kepler_match_ok(None, 13.6, 13.6))


if __name__ == "__main__":
    unittest.main()
