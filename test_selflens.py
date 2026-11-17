# SPDX-License-Identifier: Apache-2.0
"""Tests for selflens.py (gaia-orbit-transits; MV2 of Munim, Inc.; made with AI agents).
Expected values worked by hand (see comments)."""
import unittest

import selflens as sl


class TestPhysics(unittest.TestCase):
    def test_wd_radius(self):
        # x = 0.6/1.44; 0.0112 * sqrt(x^-2/3 - x^2/3) = 0.0112 * 1.11117 = 0.012445
        self.assertAlmostEqual(sl.wd_radius_rsun(0.6), 0.012445, delta=2e-5)
        self.assertGreater(sl.wd_radius_rsun(0.5), sl.wd_radius_rsun(1.0))
        self.assertEqual(sl.wd_radius_rsun(2.0), 0.003)

    def test_axis(self):
        self.assertAlmostEqual(sl.semi_major_axis_rsun(0.5, 0.5, 365.25), 215.032, places=3)

    def test_einstein_radius(self):
        # 8.49e-6 * 0.6 * 322 = 1.640268e-3 -> 0.0405002 Rsun
        self.assertAlmostEqual(sl.einstein_radius_rsun(0.6, 322.0), 0.0405002, delta=1e-6)

    def test_amplitude(self):
        # 2 * 1.640268e-3 - 0.012445^2 = 3.280536e-3 - 1.5488e-4 = 3.12566e-3
        self.assertAlmostEqual(sl.pulse_amplitude(0.6, 322.0, 1.0), 3.12566e-3, delta=2e-6)


class TestHelpers(unittest.TestCase):
    def test_lens_conjs(self):
        self.assertEqual(sl.lens_conjs("t2"), ["t2"])
        self.assertEqual(sl.lens_conjs(""), ["t1", "t2"])
        self.assertEqual(sl.lens_conjs(None), ["t1", "t2"])

    def test_id_column(self):
        self.assertEqual(sl.pick_id_column(["RA", "DR3_source_id", "x"]), "DR3_source_id")
        self.assertEqual(sl.pick_id_column(["ra", "Source"]), "Source")
        self.assertIsNone(sl.pick_id_column(["ra", "dec"]))

    def test_to_id(self):
        self.assertEqual(sl.to_id("4854976609869179648"), 4854976609869179648)
        self.assertEqual(sl.to_id(" 12.0 "), 12)
        self.assertIsNone(sl.to_id("x"))

    def test_window(self):
        self.assertTrue(sl.in_window(101.4, [(100.0, 0.5)], 0.0, 300.0))
        self.assertFalse(sl.in_window(101.6, [(100.0, 0.5)], 0.0, 300.0))
        self.assertTrue(sl.in_window(251.0, [(100.0, 0.5)], 0.0, 300.0, shift=150.0))
        # half-width 3 * 30 = 90 d > P/4 = 75 d: window not informative
        self.assertFalse(sl.in_window(100.0, [(100.0, 30.0)], 0.0, 300.0))


def ev(t, depth, snr=12.0, dur=8.0, edge="False", other="0", noise="100"):
    return {"source_id": "7", "t_center": str(t), "depth_ppm": str(depth), "snr": str(snr),
            "duration_h": str(dur), "near_edge": edge, "n_other_targets_same_time": other,
            "box_noise_ppm": noise}


class TestEvaluate(unittest.TestCase):
    def setUp(self):
        # m1 = 1, r1 = 1, m2 = 0.6, P = 365.25 d: a = 1.6^(1/3) * 215.032 = 251.503 Rsun;
        # R_E^2 = 8.49e-6 * 0.6 * 251.503 = 1.281147e-3; A = 2.562294e-3 - 1.5488e-4
        # = 2.40741e-3 (2,407 ppm)
        self.priors = [{"source_id": "7", "m1": "1", "r1": "1", "m2_dark": "0.6",
                        "period_d": "365.25", "transit_conj": "t1", "p_ecl1": "0.2",
                        "p_ecl2": "0.2", "dur1_h": "8", "dur2_h": "8", "gmag": "10"}]
        self.targets = [{"source_id": "7", "tic": "70", "status": "ok", "cov1": "0.5",
                         "cov2": "0.5"}]
        self.windows = [{"source_id": "7", "conj": "t1", "centre": "1000.0", "sd": "0.5"},
                        {"source_id": "7", "conj": "t2", "centre": "1100.0", "sd": "0.5"}]

    def test_rule(self):
        events = [ev(1000.3, 2500),                  # candidate
                  ev(1000.1, 20000),                 # far too bright: rejected
                  ev(1000.2, 2500, edge="True"),     # segment edge: rejected
                  ev(1000.25, 2500, dur=1.0),        # too short: rejected
                  ev(1100.1, 2500),                  # t2: WD behind the star, not used
                  ev(1000.0 + 182.625 + 0.2, 2500)]  # control phase
        recs, cands, ctrl = sl.evaluate(self.priors, self.targets, events, self.windows)
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertAlmostEqual(r["a_rsun"], 251.503, delta=0.01)
        self.assertAlmostEqual(r["amp_ppm"], 2407.4, delta=1.0)
        self.assertEqual(r["lens_conj"], "t1")
        self.assertAlmostEqual(r["expected_in_data"], 0.1, places=9)
        self.assertTrue(r["detectable"])  # 2,407 / 100 >= 10
        self.assertEqual(len(cands), 1)
        self.assertAlmostEqual(float(cands[0]["t_center"]), 1000.3)
        self.assertEqual(len(ctrl), 1)
        g, s = sl.grade(recs, cands, ctrl)
        self.assertTrue(g["L1"]["pass"])
        self.assertFalse(g["L2"]["pass"])
        self.assertTrue(g["L3"]["pass"])
        self.assertTrue(g["L4"]["pass"])
        self.assertEqual(s["n_candidates"], 1)

    def test_undetectable(self):
        recs, cands, ctrl = sl.evaluate(self.priors, self.targets, [ev(500.0, 2500, noise="400")],
                                        self.windows)
        self.assertFalse(recs[0]["detectable"])  # 2,407 / 400 < 10
        self.assertEqual(recs[0]["expected_detectable"], 0.0)
        g, _ = sl.grade(recs, cands, ctrl)
        self.assertTrue(g["L2"]["pass"])


if __name__ == "__main__":
    unittest.main()
