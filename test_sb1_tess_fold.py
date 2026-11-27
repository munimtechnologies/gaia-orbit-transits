# SPDX-License-Identifier: Apache-2.0
"""Offline tests for sb1_tess_fold 0.1.0 (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI
agents). Expected conjunction times were computed by hand from Kepler's equation (27 Nov 2026)."""
import json
import os
import unittest

import numpy as np

import sb1_tess_fold as m

HERE = os.path.dirname(os.path.abspath(__file__))


class TestGeometry(unittest.TestCase):
    def test_conj_tyc3614(self):
        t0, t1 = m.conj_times(3.3597641326623937, 0.15189719629668968,
                              0.021337869940452676, 139.15387281478363)
        self.assertAlmostEqual(t0, 388.7102, delta=0.002)
        self.assertAlmostEqual(t1 - t0, 1.6455, delta=0.002)

    def test_conj_bd12(self):
        t0, t1 = m.conj_times(1.9958003486397644, -0.9110619774831055,
                              0.010040041785658815, 97.9559822338739)
        self.assertAlmostEqual(t0, 388.0457, delta=0.002)
        self.assertAlmostEqual(t1 - t0, 0.99614, delta=0.002)

    def test_conj_hd76320_eccentric(self):
        t0, t1 = m.conj_times(7.772944146679363, -3.253631710535638,
                              0.18021504106350542, 80.57105879613859)
        self.assertAlmostEqual(t0, 385.8857, delta=0.002)
        self.assertTrue(t0 < t1 < t0 + 7.772944146679363)

    def test_circular_half_period(self):
        t0, t1 = m.conj_times(4.0, 0.0, 0.0, 90.0)
        self.assertAlmostEqual(t0, 389.0, places=9)
        self.assertAlmostEqual(t1 - t0, 2.0, places=9)

    def test_phase_dist(self):
        self.assertAlmostEqual(float(m.phase_dist(0.98, 0.0)), -0.02, places=12)
        self.assertAlmostEqual(float(m.phase_dist(0.52, 0.49)), 0.03, places=12)
        self.assertAlmostEqual(float(m.phase_dist(0.01, 0.99)), 0.02, places=12)

    def test_tolerance(self):
        star = {"P": 2.0, "t_conj0": 0.0, "sigma_P": 1e-5, "tol_extra_d": 0.1}
        self.assertAlmostEqual(m.tolerance_d(star, 2000.0), 3 * 1000 * 1e-5 + 0.1, places=12)


class TestSynthetic(unittest.TestCase):
    def test_self_test_passes(self):
        ok, checks = m.self_test()
        self.assertTrue(ok, msg=m.dumps(checks))

    def test_no_data(self):
        self.assertEqual(m.analyse([], {"P": 2.0, "t_conj0": 0.0, "t_conj1": 1.0,
                                        "window_phase": 0.1, "bin_phase": 0.01})["status"],
                         "NO_DATA")

    def test_clean_nonfinite(self):
        self.assertEqual(json.loads(m.dumps({"a": float("nan"), "b": np.float64(1.5)})),
                         {"a": None, "b": 1.5})


class TestConfig(unittest.TestCase):
    def test_targets(self):
        path = os.path.join(HERE, "targets.json")
        if not os.path.exists(path):   # repo layout: inputs live in runbook/
            path = os.path.join(HERE, "runbook", "sb1-tier2-tess-v1", "targets.json")
        if not os.path.exists(path):
            self.skipTest("targets.json not present in this layout")
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
        names = [s["name"] for s in cfg["stars"]]
        self.assertEqual(names, ["TYC 3614-1907-1", "BD+12 3880", "HD 76320"])
        kinds = [s["kind"] for s in cfg["stars"]]
        self.assertEqual(kinds, ["eb", "ell", "control"])


if __name__ == "__main__":
    unittest.main()
