# SPDX-License-Identifier: Apache-2.0
"""Tests for gaia_chroma 0.1.0. The expected numbers were computed by hand from the saved Gaia
DR3 epoch tables before the code was run; the tolerances are those of the hand calculation.
MV2, Munim, Inc.; made with AI agents."""
import math
import os
import unittest

import gaia_chroma as gc

HERE = os.path.dirname(os.path.abspath(__file__))
A = "5432318139709900160"   # TIC 44997521
B = "5431056347037926784"   # TIC 4638108


class Units(unittest.TestCase):
    def test_residual(self):
        T0g = 1546.48145 + 1802.5
        self.assertAlmostEqual(gc.residual(1790.8064535482451, 3.54941, T0g), 0.01599, places=4)
        self.assertAlmostEqual(gc.residual(T0g + 10 * 3.54941 + 0.01, 3.54941, T0g), 0.01, places=9)

    def test_fnum_truthy(self):
        self.assertTrue(math.isnan(gc.fnum("nan")))
        self.assertTrue(math.isnan(gc.fnum("")))
        self.assertEqual(gc.fnum("2.5"), 2.5)
        self.assertTrue(gc.truthy("True"))
        self.assertFalse(gc.truthy("False"))

    def test_colour_neutral_synthetic(self):
        rows = []
        P, T0 = 2.0, 100.0
        for i in range(60):
            t = T0 + 1802.5 + 0.37 * i + 0.003 * (i % 7)
            r = gc.residual(t, P, T0 + 1802.5)
            d = 0.02 if abs(r) < 0.05 else 0.0
            wob = 1.0 + 0.001 * ((i * 37) % 11 - 5) / 5.0
            rows.append({"g_transit_time": t, "g_transit_flux": 1000 * (1 - d) * wob,
                         "bp_flux": 500 * (1 - d) * wob, "rp_flux": 800 * (1 - d) * wob})
        res = gc.analyse(rows, P, T0)
        if res["n_common"]:
            self.assertAlmostEqual(res["bp_rp_ratio"], 1.0, places=6)


class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = gc.run(HERE)["targets"]

    def test_tic44997521(self):
        r = self.res[A]
        self.assertEqual(r["n_rows_timed"], 66)
        self.assertEqual(r["n_in"], 4)
        self.assertEqual(r["n_out"], 58)
        self.assertEqual(r["n_common"], 3)
        self.assertAlmostEqual(r["baseline"]["G"]["median"], 56384.441, delta=0.5)
        self.assertAlmostEqual(r["baseline"]["BP"]["median"], 22806.896, delta=0.5)
        self.assertAlmostEqual(r["baseline"]["RP"]["median"], 47586.816, delta=0.5)
        self.assertEqual(r["baseline"]["RP"]["n_gross_dropped"], 3)
        self.assertAlmostEqual(r["baseline"]["BP"]["sigma_rel"], 0.00508, delta=0.0005)
        self.assertAlmostEqual(r["baseline"]["RP"]["sigma_rel"], 0.00435, delta=0.0005)
        self.assertAlmostEqual(r["mean_depth"]["G"], 0.025567, delta=0.0003)
        self.assertAlmostEqual(r["mean_depth"]["BP"], 0.026533, delta=0.0003)
        self.assertAlmostEqual(r["mean_depth"]["RP"], 0.023483, delta=0.0003)
        self.assertAlmostEqual(r["bp_rp_ratio"], 1.130, delta=0.01)
        self.assertAlmostEqual(r["bp_rp_ratio_err"], 0.174, delta=0.025)
        self.assertAlmostEqual(r["jackknife_min"], 1.030, delta=0.01)
        self.assertAlmostEqual(r["jackknife_max"], 1.192, delta=0.01)
        self.assertAlmostEqual(r["median_epoch_bp_minus_rp"], 0.00121, delta=0.0003)
        self.assertEqual(r["flags"], {"in_n": 8, "in_flagged": 4, "out_n": 112, "out_flagged": 4})

    def test_tic4638108(self):
        r = self.res[B]
        self.assertEqual(r["n_rows_timed"], 67)
        self.assertEqual(r["n_in"], 6)
        self.assertEqual(r["n_out"], 59)
        self.assertEqual(r["n_common"], 6)
        self.assertAlmostEqual(r["baseline"]["G"]["median"], 144607.368, delta=1.0)
        self.assertAlmostEqual(r["baseline"]["BP"]["median"], 85986.359, delta=1.0)
        self.assertAlmostEqual(r["baseline"]["RP"]["median"], 84376.460, delta=1.0)
        self.assertEqual(r["baseline"]["RP"]["n_gross_dropped"], 4)
        self.assertAlmostEqual(r["baseline"]["BP"]["sigma_rel"], 0.00326, delta=0.0004)
        self.assertAlmostEqual(r["baseline"]["RP"]["sigma_rel"], 0.00267, delta=0.0004)
        self.assertAlmostEqual(r["mean_depth"]["G"], 0.015301, delta=0.0003)
        self.assertAlmostEqual(r["mean_depth"]["BP"], 0.016328, delta=0.0003)
        self.assertAlmostEqual(r["mean_depth"]["RP"], 0.012185, delta=0.0003)
        self.assertAlmostEqual(r["bp_rp_ratio"], 1.340, delta=0.01)
        self.assertAlmostEqual(r["bp_rp_ratio_err"], 0.162, delta=0.025)
        self.assertAlmostEqual(r["jackknife_min"], 0.995, delta=0.01)
        self.assertAlmostEqual(r["jackknife_max"], 1.488, delta=0.01)
        self.assertAlmostEqual(r["median_epoch_bp_minus_rp"], -0.00056, delta=0.0003)
        self.assertEqual(r["flags"], {"in_n": 12, "in_flagged": 3, "out_n": 116, "out_flagged": 6})


if __name__ == "__main__":
    unittest.main()
