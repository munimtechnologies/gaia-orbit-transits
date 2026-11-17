# SPDX-License-Identifier: Apache-2.0
"""Tests for vet_short_period.py (MV2 of Munim, Inc.; made with AI agents).
numpy only; expected numbers are worked by hand in the comments."""
import math
import unittest

import numpy as np

import vet_short_period as vsp


class TestHelpers(unittest.TestCase):
    def test_phase(self):
        ph = vsp.phase([0.0, 0.25, 0.5, 0.75, 1.0], 1.0, 0.0)
        np.testing.assert_allclose(ph, [0.0, 0.25, -0.5, -0.25, 0.0], atol=1e-12)

    def test_kepler(self):
        self.assertAlmostEqual(vsp.semi_major_axis_rsun(365.25, 1.0), 215.032, places=3)
        # TIC 207399049: P 0.46023065 d, M 0.9557 + 0.0712: (1.0269 * (1.26004e-3)^2)^(1/3)
        # = 0.011771 AU = 2.531 R_sun
        self.assertAlmostEqual(vsp.semi_major_axis_rsun(0.46023065, 1.0269), 2.531, delta=0.005)

    def test_ellipsoidal(self):
        # alpha = 0.15 * 15.5 * 1.4 / 2.5 = 1.302
        self.assertAlmostEqual(vsp.ellipsoidal_alpha(0.5, 0.4), 1.302, places=6)
        # 1.302 * (0.0712 / 0.9557) * (1.1635 / 2.5312)^3 = 1.302 * 0.0745003 * 0.097122 = 0.009421
        self.assertAlmostEqual(vsp.expected_ellipsoidal(0.0712, 0.9557, 1.1635, 2.5312),
                               0.009421, delta=0.00005)

    def test_duration(self):
        # a/R = 2, k = 0, b = 0: asin(1/2) = pi/6 -> T = P / 6
        self.assertAlmostEqual(vsp.central_duration(1.2, 2.0), 0.2, places=12)

    def test_mass_range(self):
        # Gaia DR3 1622997463177004928 SB1: K 19.6956 +- 1.3143, P 0.46023, e 0.2009, M1 0.9557:
        # m2 = K (m1 + m2)^(2/3) P^(1/3) sqrt(1 - e^2) / 212.908, iterated:
        # K - 2s = 17.0669 -> 0.06131; K -> 0.07122; K + 2s = 22.3243 -> 0.08124 M_sun
        lo, mid, hi = vsp.companion_mass_range(19.695569, 1.3143485, 0.46023065, 0.9556862, 0.2008897)
        self.assertAlmostEqual(lo, 0.06131, delta=0.0003)
        self.assertAlmostEqual(mid, 0.07122, delta=0.0003)
        self.assertAlmostEqual(hi, 0.08124, delta=0.0003)

    def test_detrend(self):
        t = np.arange(0.0, 10.0, 0.01)
        f = 1.0 + 0.01 * (t - 5.0) / 5.0
        d = vsp.running_median_detrend(t, f, window=2.0, gap=0.5)
        self.assertLess(np.nanmax(np.abs(d - 1.0)), 2e-3)
        # two segments at different levels separated by a 1-d gap
        t2 = np.concatenate([np.arange(0, 5, 0.01), np.arange(6, 11, 0.01)])
        f2 = np.where(t2 < 5.5, 1.0, 2.0)
        d2 = vsp.running_median_detrend(t2, f2)
        np.testing.assert_allclose(d2, 1.0, atol=1e-12)

    def test_bin(self):
        bt, bf, cnt = vsp.bin_lc([0.0, 0.1, 0.2, 1.05, 1.15], [1, 2, 3, 4, 6], 1.0)
        np.testing.assert_allclose(bt, [0.1, 1.1])
        np.testing.assert_allclose(bf, [2.0, 5.0])
        np.testing.assert_array_equal(cnt, [3, 2])


class TestMeasure(unittest.TestCase):
    def test_synthetic_bd_eclipses(self):
        rng = np.random.default_rng(1)
        t = np.arange(0.0, 60.0, 2.0 / 1440)
        P, t0, dur = 0.46, 0.1, 0.08
        ph = vsp.phase(t, P, t0)
        f = 1.0 - 0.009 * np.cos(4 * np.pi * ph) - 0.0005 * np.cos(2 * np.pi * ph)
        half = 0.5 * dur / P
        f = f - 0.012 * (np.abs(ph) < half)
        phs = (ph + 1.0) % 1.0 - 0.5
        f = f - 0.0007 * (np.abs(phs) < half)
        f = f + rng.normal(0, 0.001, t.size)
        m = vsp.measure_eclipses(t, f, P, t0, dur)
        # 43200 points; 7513 in each eclipse (white error 1.2e-5); 20661 outside.
        # Outside eclipse cos(4 pi phase) spans only [-1, -0.07] (sd 0.286), so
        # sigma(a_ell) ~ 0.001 / (0.286 * sqrt(20661)) = 2.4e-5 and the model
        # extrapolated to phase 0 has an error ~ 4.5e-5; tolerances are ~4 sigma.
        self.assertAlmostEqual(m["a_ell"], 0.009, delta=1.2e-4)
        self.assertAlmostEqual(m["a_ref"], 0.0005, delta=1e-4)
        self.assertAlmostEqual(m["depth_p"], 0.012, delta=2e-4)
        self.assertAlmostEqual(m["depth_s"], 0.0007, delta=2e-4)
        # odd - even: the model error cancels; sd ~ sqrt(2) * 0.001 / sqrt(3756) = 2.3e-5
        self.assertAlmostEqual(m["depth_odd"], m["depth_even"], delta=1e-4)
        self.assertGreater(m["err_p"], 1.5e-5)
        self.assertLess(m["err_p"], 1.5e-4)


BASE = {"snr": 50.0, "depth_p": 0.012, "err_p": 1e-4, "depth_s": 7e-4, "err_s": 1e-4,
        "depth_odd": 0.012, "err_odd": 1.4e-4, "depth_even": 0.012, "err_even": 1.4e-4,
        "match_rv": "1:1", "match_phot": "", "r2_rsun": 0.127, "m2_lo": 0.0613,
        "m2_hi": 0.0812, "a_ell": 0.0094, "err_a_ell": 1e-4, "a_ell_pred": 0.0094}


def v(**kw):
    d = dict(BASE)
    d.update(kw)
    return vsp.verdict(d)[0]


class TestVerdict(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(v(), "TRANSITING_BD_OR_VLM_BOUNDARY")
        self.assertEqual(v(m2_hi=0.070), "TRANSITING_BROWN_DWARF_CANDIDATE")
        self.assertEqual(v(m2_lo=0.085, m2_hi=0.1), "TRANSITING_VLM_STAR")
        self.assertEqual(v(snr=5.0), "NO_ECLIPSE")
        self.assertEqual(v(depth_p=2e-4), "NO_ECLIPSE")
        self.assertEqual(v(match_rv=""), "PERIOD_CONFLICT")
        self.assertEqual(v(match_rv="2:1"), "PERIOD_CONFLICT")
        # odd/even: |0.010 - 0.012| = 0.002 > 3 * hypot(1.4e-4, 1.4e-4) = 5.9e-4
        self.assertEqual(v(depth_odd=0.010), "STELLAR_EB")
        self.assertEqual(v(depth_s=0.003), "STELLAR_EB")         # ratio 0.25
        self.assertEqual(v(r2_rsun=0.25), "STELLAR_EB")
        # 0.05 > 3 * 0.0094 + 3e-4 = 0.0285
        self.assertEqual(v(a_ell=0.05), "MASS_TENSION")


if __name__ == "__main__":
    unittest.main()
