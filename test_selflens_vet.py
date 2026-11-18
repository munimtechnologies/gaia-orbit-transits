# SPDX-License-Identifier: Apache-2.0
"""Tests for selflens_vet.py (gaia-orbit-transits 0.14.0, MV2 of Munim, Inc., made with AI
agents). Expected values are worked by hand in the comments."""
import unittest

import numpy as np

import selflens_vet as sv


def noisy(t, level=1e-3):
    # deterministic +-level pattern: robust sd = 1.4826 * level
    return 1.0 + level * np.where(np.arange(len(t)) % 2 == 0, 1.0, -1.0)


class TestEdge(unittest.TestCase):
    def setUp(self):
        self.t = np.concatenate([np.arange(0, 10.001, 0.1), np.arange(12, 20.001, 0.1)])

    def test_middle(self):
        self.assertAlmostEqual(sv.edge_distance(self.t, 5.0), 5.0, places=6)

    def test_after_gap(self):
        # segment 2 starts at 12.0 -> 0.3 d
        self.assertAlmostEqual(sv.edge_distance(self.t, 12.3), 0.3, places=6)

    def test_before_gap(self):
        # segment 1 ends at 10.0 -> 0.4 d
        self.assertAlmostEqual(sv.edge_distance(self.t, 9.6), 0.4, places=6)

    def test_in_gap_and_outside(self):
        self.assertEqual(sv.edge_distance(self.t, 11.0), 0.0)
        self.assertEqual(sv.edge_distance(self.t, 25.0), 0.0)
        self.assertEqual(sv.edge_distance([], 1.0), 0.0)


class TestShape(unittest.TestCase):
    def setUp(self):
        self.t = np.arange(3.0, 7.0, 0.02)
        self.f = noisy(self.t)
        self.t0, self.D = 5.0, 0.5

    def test_symmetric_pulse(self):
        f = self.f + np.where(np.abs(self.t - self.t0) <= self.D / 2, 0.01, 0.0)
        h = sv.half_amplitudes(self.t, f, self.t0, self.D)
        self.assertAlmostEqual(h["a1"], 0.01, delta=5e-4)
        self.assertAlmostEqual(h["a2"], 0.01, delta=5e-4)
        self.assertFalse(sv.is_asymmetric(h))

    def test_flare_like(self):
        # first half +0.02, second half +0.002: differ by ~0.018 >> 3 x ~6e-4,
        # and 0.002 < 0.5 x 0.02 -> asymmetric
        x = self.t - self.t0
        bump = np.where((x >= -self.D / 2) & (x < 0), 0.02, 0.0) + \
            np.where((x >= 0) & (x <= self.D / 2), 0.002, 0.0)
        h = sv.half_amplitudes(self.t, self.f + bump, self.t0, self.D)
        self.assertTrue(sv.is_asymmetric(h))

    def test_no_baseline(self):
        h = sv.half_amplitudes([5.0, 5.01], [1.0, 1.0], 5.0, 0.5)
        self.assertTrue(np.isnan(h["a1"]))
        self.assertFalse(sv.is_asymmetric(h))

    def test_pulse_model(self):
        # dur 0.6 d, ramp 0.1 d: full at centre, half way down the ramp at x = 0.25
        y = sv.pulse_model(np.array([5.0, 5.25, 4.75, 5.4]), 5.0, 0.6, 0.004)
        self.assertAlmostEqual(y[0], 0.004)
        self.assertAlmostEqual(y[1], 0.002)
        self.assertAlmostEqual(y[2], 0.002)
        self.assertEqual(y[3], 0.0)


class TestBrightening(unittest.TestCase):
    def test_sign_and_size(self):
        import vet_event as ve
        t = np.arange(3.0, 7.0, 1.0 / 48)
        f = noisy(t) + np.where(np.abs(t - 5.0) <= 0.25, 0.01, 0.0)
        m = sv.brightening(ve, t, f, 5.0, 0.5, 1.5)
        self.assertAlmostEqual(m["amp"], 0.01, delta=1e-3)
        self.assertGreater(m["snr"], 5)
        # a dip gives a negative amplitude
        g = noisy(t) - np.where(np.abs(t - 5.0) <= 0.25, 0.01, 0.0)
        self.assertLess(sv.brightening(ve, t, g, 5.0, 0.5, 1.5)["snr"], -5)


class TestVerdict(unittest.TestCase):
    def good(self):
        return {"edge_d": 3.0, "snr": 8.0, "amp": 0.005, "sap_snr": 6.0, "sap_amp": 0.004,
                "other_min_snr": float("nan"), "bkg_snr": 1.0, "nb_n": 8, "nb_frac": 0.0,
                "asymmetric": False, "flag_frac": 0.0, "cut_snr": 5.0, "cut_amp": 0.004,
                "diff_offset_px": 0.3}

    def test_survives(self):
        self.assertEqual(sv.verdict(self.good())[0], "SURVIVES")

    def test_edge(self):
        v = self.good()
        v["edge_d"] = 0.5
        res, why = sv.verdict(v)
        self.assertEqual(res, "REJECTED")
        self.assertTrue(why[0].startswith("EDGE"))

    def test_neighbours(self):
        v = self.good()
        v["nb_frac"] = 0.5
        self.assertEqual(sv.verdict(v)[0], "REJECTED")
        v["nb_n"] = 3          # too few neighbours: rule not applied
        self.assertEqual(sv.verdict(v)[0], "SURVIVES")

    def test_sap_and_background_and_flare(self):
        for k, x in (("sap_snr", 1.0), ("bkg_snr", -6.0), ("asymmetric", True),
                     ("other_min_snr", 1.0), ("flag_frac", 0.8), ("snr", 4.0)):
            v = self.good()
            v[k] = x
            if k == "sap_snr":
                v["sap_amp"] = 0.001
            self.assertEqual(sv.verdict(v)[0], "REJECTED", k)

    def test_unresolved(self):
        v = self.good()
        v["cut_snr"] = 2.0
        self.assertEqual(sv.verdict(v)[0], "UNRESOLVED")
        v = self.good()
        v["cut_amp"] = 0.02     # > 3 x 0.005
        self.assertEqual(sv.verdict(v)[0], "UNRESOLVED")

    def test_off_target(self):
        v = self.good()
        v["diff_offset_px"] = 1.5
        self.assertEqual(sv.verdict(v)[0], "REJECTED")


class TestGrade(unittest.TestCase):
    def test_counts(self):
        def rep(role, verdict, edge=False, inj=8.0):
            return {"event": {"role": role, "near_edge_list": edge}, "verdict": verdict,
                    "measured": {"inj_min_snr": inj}}
        reps = [rep("candidate", "REJECTED", True) for _ in range(15)] + \
            [rep("candidate", "UNRESOLVED"), rep("candidate", "SURVIVES"),
             rep("control", "REJECTED"), rep("control", "UNRESOLVED", inj=3.0)]
        g = sv.grade(reps)
        self.assertTrue(g["V1"]["pass"])
        self.assertTrue(g["V2"]["pass"])
        self.assertTrue(g["V3"]["pass"])
        self.assertTrue(g["V4"]["pass"])
        # 18 of 19 recovered at >= 5 -> 0.947 >= 0.7
        self.assertTrue(g["V5"]["pass"])


if __name__ == "__main__":
    unittest.main()
