# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Unit tests for tyc_k_dr4 (stdlib only)."""
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tyc_k_dr4 as T  # noqa: E402


def exact_pts(K, n=12, t0=2457950.0, span=800.0, sigma=1.0, P=T.P_GAIA):
    pts = []
    for i in range(n):
        t = t0 + span * i / n + 0.137 * i
        v = -17.57 - K * math.sin(2.0 * math.pi * (t - T.T0_TESS_BJD) / P)
        pts.append((t, v, sigma))
    return pts


class TestTime(unittest.TestCase):
    def test_to_jd(self):
        self.assertAlmostEqual(T.to_jd(2458000.5), 2458000.5)
        self.assertAlmostEqual(T.to_jd(58000.0), 2458000.5)
        self.assertAlmostEqual(T.to_jd(2704.0), T.DR3_END_JD)
        self.assertTrue(math.isnan(T.to_jd("")))


class TestCounting(unittest.TestCase):
    def test_epoch_counts(self):
        ok = {"radial_velocity": "1.0", "radial_velocity_error": "2.0",
              "outlier_status": "0", "emission_lines": "false"}
        self.assertTrue(T.epoch_counts(ok))
        self.assertFalse(T.epoch_counts(dict(ok, outlier_status="1")))
        self.assertFalse(T.epoch_counts(dict(ok, emission_lines="true")))
        self.assertFalse(T.epoch_counts(dict(ok, radial_velocity_error="0")))
        self.assertFalse(T.epoch_counts(dict(ok, radial_velocity="nan")))

    def test_select_independent(self):
        rows = [{"obs_time": "2700.0", "radial_velocity": "1", "radial_velocity_error": "1"},
                {"obs_time": "2710.0", "radial_velocity": "1", "radial_velocity_error": "1"}]
        ind, allc = T.select_epochs(rows, "obs_time")
        self.assertEqual(len(allc), 2)
        self.assertEqual(len(ind), 1)


class TestFit(unittest.TestCase):
    def test_exact_recovery_and_phase(self):
        f = T.fit_circular(exact_pts(T.K_GAIA), T.P_GAIA)
        self.assertAlmostEqual(f["K"], T.K_GAIA, places=6)
        self.assertAlmostEqual(f["gamma"], -17.57, places=6)
        self.assertAlmostEqual(T.phase_offset(f["t_conj_jd"]), 0.0, places=6)

    def test_too_few(self):
        self.assertIsNone(T.fit_circular(exact_pts(10.0, n=3), T.P_GAIA))


class TestLabel(unittest.TestCase):
    def fit(self, K, sK):
        return {"K": K, "sK": sK}

    def test_labels(self):
        self.assertEqual(T.label(self.fit(16.0, 1.0), 10), "GAIA_K_CONFIRMED")
        self.assertEqual(T.label(self.fit(32.0, 1.0), 10), "HEAVY_K")
        self.assertEqual(T.label(self.fit(24.0, 1.0), 10), "OTHER_K")
        self.assertEqual(T.label(self.fit(24.0, 4.0), 10), "UNDECIDED")
        self.assertEqual(T.label(self.fit(2.0, 1.0), 10), "NO_ORBIT_SIGNAL")
        self.assertEqual(T.label(self.fit(16.0, 1.0), 5), "UNTESTABLE")
        self.assertEqual(T.label(None, 10), "UNTESTABLE")


class TestEndToEnd(unittest.TestCase):
    def test_self_test(self):
        ok, labels = T.self_test()
        self.assertTrue(ok, labels)

    def test_csv_path(self):
        rows = T.synth_rows(T.K_GAIA, seed=7, time_mode="jd")
        d = tempfile.mkdtemp()
        p = os.path.join(d, "e.csv")
        with open(p, "w") as fh:
            fh.write(",".join(rows[0].keys()) + "\n")
            for r in rows:
                fh.write(",".join(r.values()) + "\n")
        rc = T.main(["--epochs-csv", p, "--out-dir", os.path.join(d, "out")])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(d, "out", "tyc_k_dr4.json")))

    def test_pick_time_col(self):
        self.assertEqual(T.pick_time_col(["source_id", "obs_time", "radial_velocity"]),
                         "obs_time")
        with self.assertRaises(KeyError):
            T.pick_time_col(["a", "b"])


if __name__ == "__main__":
    unittest.main()
