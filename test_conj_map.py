# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 MV2, Munim, Inc. Made with AI agents working in MV2's name.
import math
import unittest

import conj_map as cm

# Gaia DR3 nss_two_body_orbit rows (AIP TAP, 27 Nov 2026), both SB2C
BD15 = dict(P=2.0672153116960352, tp=-0.2606681436442654, P_err=3.464779e-05, tp_err=0.004288195)
HD250 = dict(P=5.895935077280673, tp=-1.6427050598921045, P_err=0.00018169096, tp_err=0.010175885)
# TESS fold T0 (deepest eclipse) from data/sb2-ebfit-v2/ebfit_summary.json
T0_BD15 = 2703.5453161867226
T0_HD250 = 3242.3996811396873
# ASAS-3 faint (>= median + 0.07 mag) grade A/B points of BD+15 2743, HJD - 2450000
ASAS_BD15 = [2761.67803, 3102.78395, 3483.70113, 3499.74007, 4189.75022,
             4256.72323, 4574.73776, 4603.70529, 4677.55814, 5021.58522]


class TestPhases(unittest.TestCase):
    def test_circular(self):
        self.assertEqual(cm.conj_phases(None, None), (0.25, 0.75))
        self.assertEqual(cm.conj_phases(float("nan"), 10.0), (0.25, 0.75))

    def test_zero_ecc_matches_circular(self):
        b, f = cm.conj_phases(0.0, 0.0)
        self.assertAlmostEqual(b, 0.25, places=9)
        self.assertAlmostEqual(f, 0.75, places=9)

    def test_eccentric_omega90(self):
        b, f = cm.conj_phases(0.3, 90.0)
        self.assertAlmostEqual(min(b, 1.0 - b), 0.0, places=9)
        self.assertAlmostEqual(f, 0.5, places=9)

    def test_conj_times_reference(self):
        b, f = cm.conj_times(BD15["P"], BD15["tp"])
        self.assertAlmostEqual(b, 389.2561356842, places=6)
        self.assertAlmostEqual(f, 390.2897433401, places=6)


class TestNewEBs(unittest.TestCase):
    def test_bd15_2743(self):
        r = cm.map_eclipse(T0_BD15, **BD15)
        self.assertEqual(r["conj_kind"], "star1_in_front")
        self.assertEqual(r["eclipsed"], "gaia2")
        self.assertEqual(r["n_cycles"], 1119)
        self.assertAlmostEqual(r["offset_days"], 0.041639, delta=0.0002)
        self.assertAlmostEqual(r["offset_orbit"], 0.020142, delta=0.0002)
        self.assertAlmostEqual(r["z"], 1.067, delta=0.02)
        self.assertEqual(r["rule"], "MAP_CONJUNCTION")

    def test_hd250735(self):
        r = cm.map_eclipse(T0_HD250, **HD250)
        self.assertEqual(r["conj_kind"], "star1_behind")
        self.assertEqual(r["eclipsed"], "gaia1")
        self.assertEqual(r["n_cycles"], 484)
        self.assertAlmostEqual(r["offset_days"], -0.064175, delta=0.0002)
        self.assertAlmostEqual(r["offset_orbit"], -0.010885, delta=0.0002)
        self.assertAlmostEqual(r["z"], -0.725, delta=0.02)
        self.assertEqual(r["rule"], "MAP_CONJUNCTION")

    def test_quarter_shift_unresolved(self):
        r = cm.map_eclipse(T0_BD15 + 0.25 * BD15["P"], **BD15)
        self.assertEqual(r["rule"], "MAP_UNRESOLVED")


class TestAsas3Frozen(unittest.TestCase):
    def test_window_count_and_p(self):
        btjd = [x - 7000.0 for x in ASAS_BD15]
        k = cm.window_count(btjd, BD15["P"], BD15["tp"], half_width=0.08)
        self.assertEqual(k, 5)
        p = cm.binom_sf(k, len(btjd), 0.32)
        self.assertAlmostEqual(p, 0.1867, delta=0.001)
        self.assertGreater(p, 1e-3)  # frozen rule: FAIL

    def test_binom_sf_total(self):
        self.assertAlmostEqual(cm.binom_sf(0, 10, 0.32), 1.0, places=12)


if __name__ == "__main__":
    unittest.main()
