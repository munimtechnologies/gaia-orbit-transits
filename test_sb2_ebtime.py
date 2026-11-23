# SPDX-License-Identifier: Apache-2.0
"""Tests for sb2_ebtime 0.1.0 (MV2, Munim, Inc.; made with AI agents)."""
import io
import math
import unittest
import zipfile

import numpy as np

import sb2_ebtime as eb


class Geometry(unittest.TestCase):
    def test_circular(self):
        c1, c2 = eb.conjunction_phases(0.0, 90.0)
        self.assertAlmostEqual(((c2 - c1) % 1.0), 0.5, places=9)

    def test_cd28_7251(self):
        # hand calculation, Gaia DR3 e = 0.0760, omega = 342.95 deg
        c1, c2 = eb.conjunction_phases(0.07601178, 342.9514761)
        self.assertAlmostEqual(c1, 0.2738, delta=0.002)
        self.assertAlmostEqual(c2, 0.8201, delta=0.002)

    def test_first_order(self):
        e, w = 0.03, 20.0
        c1, c2 = eb.conjunction_phases(e, w)
        approx = 0.5 + 2.0 / math.pi * e * math.cos(math.radians(w))
        self.assertAlmostEqual(min((c2 - c1) % 1.0, (c1 - c2) % 1.0, key=lambda x: abs(x - approx)),
                               approx, delta=0.002)


class Timing(unittest.TestCase):
    def test_fit_minimum(self):
        rng = np.random.default_rng(5)
        t = np.arange(0.0, 1.0, 2.0 / 1440.0)
        r = -0.05 * np.exp(-0.5 * ((t - 0.4321) / 0.03) ** 2) + rng.normal(0, 0.001, t.size)
        fit = eb.fit_minimum(t, r, 0.43, 0.2)
        self.assertTrue(fit["ok"])
        self.assertAlmostEqual(fit["tc"], 0.4321, delta=0.001)
        self.assertLess(fit["tc_err"], 0.002)
        self.assertAlmostEqual(fit["depth"], 0.05, delta=0.005)

    def test_ephemeris_exact(self):
        P, T, D = 3.3, 100.0, 1.75
        times, labels = [], []
        for n in range(0, 40, 3):
            times.append(T + n * P)
            labels.append("A")
            times.append(T + n * P + D)
            labels.append("B")
        res = eb.fit_ephemeris(times, [0.001] * len(times), labels, P + 1e-5, T)
        self.assertAlmostEqual(res["P"], P, places=7)
        self.assertAlmostEqual(res["D"], D, places=6)
        self.assertEqual(res["n_B"], len(times) // 2)

    def test_detrend_keeps_eclipse(self):
        t = np.arange(0.0, 10.0, 2.0 / 1440.0)
        f = 1.0 + 0.01 * np.sin(t) - 0.1 * np.exp(-0.5 * ((t - 5.0) / 0.05) ** 2)
        r, mad = eb.detrend(t, f)
        self.assertLess(r[np.argmin(np.abs(t - 5.0))], -0.09)
        evs = eb.time_events(t, r, max(mad, 1e-4))
        self.assertEqual(len(evs), 1)
        self.assertAlmostEqual(evs[0]["tc"], 5.0, delta=0.002)


class GaiaEpochs(unittest.TestCase):
    def test_parse_long(self):
        text = ("source_id,transit_id,band,time,mag,flux,rejected_by_photometry\n"
                "1,1,G,1766.80,8.855,1,false\n1,1,BP,1766.80,9.0,1,false\n"
                "1,2,G,2035.88,9.129,1,false\n")
        pts = eb.parse_epoch_text(text)
        self.assertEqual(len(pts), 2)
        self.assertAlmostEqual(pts[1][1], 9.129)

    def test_parse_wide_zip(self):
        text = ('source_id,g_transit_time,g_transit_flux\n'
                '1,"[1766.8, 1790.9]","[1000.0, 2000.0]"\n')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("EPOCH_PHOTOMETRY-Gaia DR3 1.csv", text)
        pts = eb.parse_datalink(buf.getvalue())
        self.assertEqual(len(pts), 2)
        self.assertAlmostEqual(pts[0][1], -2.5 * math.log10(1000.0) + eb.G_ZP, places=6)

    def test_epoch_test(self):
        eph = {"P": 5.0, "T_A": 1000.0, "D": 2.5, "P_err": 1e-6, "T_A_err": 1e-4,
               "D_err": 1e-4, "n_B": 3}
        pts = [(1000.0 - k * 5.0 - eb.GAIA_TO_BTJD, 9.4, False) for k in range(100, 106)]
        pts += [(1000.0 - k * 5.0 + 1.2 - eb.GAIA_TO_BTJD, 9.0, False) for k in range(100, 140)]
        res = eb.gaia_epoch_test(pts, eph, 0.1)
        self.assertEqual(res["E4"], "GAIA_DIPS_IN_ECLIPSE")
        self.assertEqual(res["n_faint"], 6)


class SelfTest(unittest.TestCase):
    def test_self_test(self):
        self.assertTrue(eb.self_test())


if __name__ == "__main__":
    unittest.main()
