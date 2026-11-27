# SPDX-License-Identifier: Apache-2.0
# MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name.
import json
import math
import unittest

import numpy as np

import ecl_timing as et


class TestTiming(unittest.TestCase):
    def test_template_peak_and_smearing(self):
        self.assertAlmostEqual(et.template(np.array([0.0]), 0.09, 120.0)[0], 1.0, places=12)
        # a 30-min exposure lowers the peak of a 0.09-d dip but keeps it symmetric
        a = et.template(np.array([-0.02, 0.0, 0.02]), 0.09, 1800.0)
        self.assertLess(a[1], 1.0)
        self.assertAlmostEqual(a[0], a[2], places=12)
        self.assertEqual(et.n_sub(120.0), 1)
        self.assertEqual(et.n_sub(1800.0) % 2, 1)

    def test_clean_json(self):
        s = et.dumps({"a": np.bool_(True), "b": np.float64(float("nan")), "c": np.int64(3),
                      1: np.array([1.0, 2.0])})
        d = json.loads(s)
        self.assertIs(d["a"], True)
        self.assertIsNone(d["b"])
        self.assertEqual(d["c"], 3)
        self.assertEqual(d["1"], [1.0, 2.0])

    def test_find_events(self):
        ref = {"P": 3.0, "t_conj0": 100.0, "t_conj1": 101.5}
        t = np.arange(100.0, 110.0, 600.0 / et.DAY)
        ev = et.find_events(t, ref, 0.5, 600.0)
        tps = [round(e["tp"], 6) for e in ev]
        # 100.0 lacks its left half; 101.5, 103, 104.5, 106, 107.5, 109 are complete
        self.assertEqual(tps, [101.5, 103.0, 104.5, 106.0, 107.5, 109.0])

    def test_alt_offset(self):
        ref = {"P": 3.0, "t_conj0": 100.0, "t_conj1": 101.5}
        t = np.arange(100.0, 110.0, 600.0 / et.DAY)
        ev = et.find_events(t, ref, 0.5, 600.0)
        alt = {"t_ref": 100.3, "P": 3.0}
        self.assertAlmostEqual(et.alt_offset(ev, alt), 0.3, places=9)

    def test_recovers_offset(self):
        P, t0 = 3.12, 1000.0
        star = {"ref": {"P": P, "t_conj0": t0, "t_conj1": t0 + 0.5 * P}, "window_d": 0.75,
                "fwhm_d": 0.09, "dt_max_d": 0.45, "step_d": 0.002}
        t, f = et.synth(P, t0, 0.07, 0.09, 1800.0, 20.0, 0.003, 0.2, 11)
        r, res = et.measure_lc({"t": t, "f": f, "exptime": 1800.0, "sector": 1,
                                "author": "SYN"}, star)
        self.assertEqual(r["status"], "OK")
        self.assertLess(abs(r["dt_best"] - 0.2), 0.004)
        self.assertGreater(r["dchi2_scaled_at_0"], 25.0)
        self.assertTrue(all(abs(e["dt_best"] - 0.2) < 0.02 for e in r["events"]))

    def test_self_test(self):
        ok, checks = et.self_test()
        self.assertTrue(ok, json.dumps(et.clean(checks)))


if __name__ == "__main__":
    unittest.main()
