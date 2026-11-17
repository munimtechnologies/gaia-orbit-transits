# SPDX-License-Identifier: Apache-2.0
"""Offline tests for calib_eclipse_rate.py (gaia-orbit-transits 0.7.0; MV2 of Munim, Inc.,
made with AI agents). Expected values are worked by hand in the comments."""
import csv
import json
import math
import os
import shutil
import tempfile
import unittest

import numpy as np

import calib_eclipse_rate as ce


class TestNormal(unittest.TestCase):
    def test_cdf_values(self):
        self.assertAlmostEqual(float(ce.norm_cdf(0.0)), 0.5, places=7)
        self.assertAlmostEqual(float(ce.norm_cdf(1.959964)), 0.975, places=6)
        self.assertAlmostEqual(float(ce.norm_cdf(-1.0)), 0.158655, places=6)


class TestLimits(unittest.TestCase):
    def test_circular_without_durations(self):
        # m1 + m2 = 1, P = 1 yr -> a = 1 AU; r1 + r2 = 1 -> q = 0.00465047 = lim (e = 0)
        l1, l2, q = ce.conj_limits(365.25, 1.0, 0.0, 1.0, 0.0, 0.0, float("nan"), None)
        self.assertAlmostEqual(q, 0.00465047, places=9)
        self.assertAlmostEqual(l1, q, places=12)
        self.assertAlmostEqual(l2, q, places=12)

    def test_circular_with_exact_duration(self):
        q = 0.00465047
        dur_h = 365.25 / math.pi * q * 24.0          # = 12.977 h, so g = 1
        l1, l2, _ = ce.conj_limits(365.25, 1.0, 0.0, 1.0, 0.0, 0.0, dur_h, dur_h)
        self.assertAlmostEqual(l1, q, places=10)

    def test_hd75767(self):
        # Gaia DR3 596878550087942528 (TIC 459056725), values from the v4 priors table.
        # a = 0.0999183 AU, q = 0.0604233, sqrt(1-e^2) = 0.929125, (P/pi) q sqrt = 0.183148
        # g1 = 0.183148 / (5.712992/24) = 0.769397 -> lim1 = q g1 / 0.863272 = 0.053853
        # g2 = 0.183148 / (3.555361/24) = 1.236317 -> lim2 = 0.086534
        l1, l2, q = ce.conj_limits(10.24880847024291, 0.9717517062780523,
                                   0.29522959304566215, 0.9646896328475654,
                                   0.3335369085443566, 0.36976707929143715,
                                   5.712991847886449, 3.5553613290308386)
        self.assertAlmostEqual(q, 0.0604233, delta=2e-6)
        self.assertAlmostEqual(l1, 0.053853, delta=2e-5)
        self.assertAlmostEqual(l2, 0.086534, delta=2e-5)
        # cos i = 0.015493 +- 0.018779: z = 2.0427 and -3.6927 -> p = 0.97946 - 0.00011
        p1 = float(ce.p_inside(0.015492818451815481, 0.018779074761100648, l1))
        self.assertAlmostEqual(p1, 0.97935, delta=5e-4)
        # the Monte Carlo of the search gave p_ecl1 = 0.9833
        self.assertLess(abs(p1 - 0.9833), 0.01)

    def test_g_is_clipped(self):
        # absurd duration -> g clipped to 1 + e
        l1, _, q = ce.conj_limits(100.0, 1.0, 0.5, 1.0, 0.5, 0.5, 1e-6, 1e-6)
        self.assertAlmostEqual(l1, q * 1.5 / 0.75, places=12)


class TestDetectProbability(unittest.TestCase):
    def test_coverage_combinations(self):
        tiny = 1e-9
        self.assertAlmostEqual(float(ce.p_detect(0, tiny, 0.1, 0.1, 1, 0)), 1.0)
        self.assertAlmostEqual(float(ce.p_detect(0, tiny, 0.1, 0.1, 0.5, 0.5)), 0.75)
        # |cos i| = 0.07 eclipses only at conjunction 1 (lim 0.1), not 2 (lim 0.05)
        self.assertAlmostEqual(float(ce.p_detect(0.07, tiny, 0.1, 0.05, 0.3, 0.9)), 0.3)
        self.assertAlmostEqual(float(ce.p_detect(0.07, tiny, 0.05, 0.1, 0.3, 0.9)), 0.9)

    def test_isotropic_fraction(self):
        # f = 1: P(<0.05) = 0.05 at both, plus 0.05 more at the 0.1 conjunction -> 0.1
        self.assertAlmostEqual(float(ce.p_detect(0.0, 0.01, 0.1, 0.05, 1, 1, f=1.0)), 0.1)

    def test_inflation_and_radius_scale(self):
        p1 = float(ce.p_detect(0.0, 0.02, 0.05, 0.05, 1, 1))
        p3 = float(ce.p_detect(0.0, 0.02, 0.05, 0.05, 1, 1, k=3.0))
        ps = float(ce.p_detect(0.0, 0.02, 0.05, 0.05, 1, 1, s=0.5))
        self.assertGreater(p1, 0.98)          # 2.5 sigma either side: 0.9876
        self.assertAlmostEqual(p3, 0.5953, delta=1e-3)   # 0.833 sigma: 2*0.79767-1
        self.assertAlmostEqual(ps, 0.7887, delta=1e-3)   # 1.25 sigma: 2*0.89435-1


class TestStatistics(unittest.TestCase):
    def test_poisson_binomial(self):
        self.assertAlmostEqual(ce.poisson_binomial_cdf([0.5, 0.5], 0), 0.25)
        self.assertAlmostEqual(ce.poisson_binomial_cdf([0.5, 0.5], 1), 0.75)
        self.assertAlmostEqual(ce.poisson_binomial_cdf([0.5, 0.5], 2), 1.0)
        self.assertAlmostEqual(ce.poisson_binomial_cdf([1.0, 0.0], 0), 0.0)
        self.assertAlmostEqual(ce.poisson_binomial_cdf([1.0, 0.0], 1), 1.0)
        self.assertAlmostEqual(ce.poisson_binomial_cdf([0.2, 0.3, 0.9], 0), 0.8 * 0.7 * 0.1)

    def test_loglike(self):
        self.assertAlmostEqual(ce.loglike([0.5, 0.5], [True, False]), 2 * math.log(0.5))
        # with a false-alarm rate 0.5 a p = 0 target is seen half the time
        self.assertAlmostEqual(ce.loglike([0.0], [True], fa=0.5), math.log(0.5))

    def test_fit_recovers_inflation(self):
        rng = np.random.default_rng(20261117)
        n = 600
        c = rng.uniform(-0.02, 0.02, n)
        sd = np.full(n, 0.02)
        lim = np.full(n, 0.05)
        cov = np.ones(n)
        x = c + 2.5 * sd * rng.standard_normal(n)
        det = np.abs(x) < lim
        fit = ce.fit_1d(lambda k: ce.loglike(ce.p_detect(c, sd, lim, lim, cov, cov, k=k), det),
                        ce.K_GRID)
        self.assertLessEqual(fit["lo95"], 2.5)
        self.assertGreaterEqual(fit["hi95"], 2.5)
        self.assertGreater(fit["lo95"], 1.2)


class TestWindows(unittest.TestCase):
    def test_match_window(self):
        wins = [(100.0, 0.5)]
        # half-width 3 * 0.5 + 4/48 = 1.5833
        m = ce.match_window(101.2, 4.0, wins, 50.0)
        self.assertAlmostEqual(m[0], 1.2)
        self.assertAlmostEqual(m[2], 2.4)
        self.assertIsNone(ce.match_window(102.0, 4.0, wins, 50.0))
        # 3 * 5 + 0.08 > 20 / 4: not informative
        self.assertIsNone(ce.match_window(100.1, 4.0, [(100.0, 5.0)], 20.0))

    def test_control_phases(self):
        q, d = ce.control_phases(0.0, 10.0, 40.0)
        self.assertEqual(q, [5.0, 25.0])
        self.assertEqual(d, 10.0)
        self.assertAlmostEqual(ce.phase_distance(85.0, 5.0, 40.0), 0.0)
        self.assertAlmostEqual(ce.phase_distance(64.0, 5.0, 40.0), 19.0)

    def test_repeat_rule(self):
        # HD 75767-like: dips 10.2488 d apart
        self.assertEqual(ce.repeat_match([2236.206, 2246.455], 10.2488, 0.0048)[2], 1)
        self.assertIsNone(ce.repeat_match([2236.206, 2242.0], 10.2488, 0.0048))
        # a TESS-orbit period is never used
        self.assertIsNone(ce.repeat_match([0.0, 13.7], 13.7, 0.0))
        self.assertTrue(ce.repeat_applicable(10.2488, 0.0048))
        self.assertFalse(ce.repeat_applicable(27.4, 0.0))
        self.assertFalse(ce.repeat_applicable(60.0, 0.01))

    def test_artefact_veto(self):
        self.assertTrue(ce.is_artefact("219744709", 2707.2))
        self.assertFalse(ce.is_artefact("219744709", 2709.0))
        ev = {"snr": "50", "depth_ppm": "20000", "n_other_targets_same_time": "0",
              "near_edge": "False", "t_center": "1000.0", "tic": "1"}
        self.assertTrue(ce.event_quality(ev))
        self.assertFalse(ce.event_quality(dict(ev, near_edge="True")))
        self.assertFalse(ce.event_quality(dict(ev, n_other_targets_same_time="1")))
        self.assertFalse(ce.event_quality(dict(ev, depth_ppm="300")))
        self.assertFalse(ce.event_quality(dict(ev, snr="9.9")))


def _write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        d = os.path.join(self.tmp, "data", "dr3-full-search-v4")
        os.makedirs(d)
        _write(os.path.join(d, "tess_targets.csv"),
               ["source_id", "tic", "solution_type", "class", "gmag", "period_d", "cov1",
                "cov2", "gaia_eb", "status", "n_sectors", "p_ecl"],
               [["1", "11", "AstroSpectroSB1", "star", "10", "100", "1", "1", "False", "ok",
                 "2", "1"],
                ["2", "22", "Orbital", "star", "10", "100", "1", "1", "False", "ok", "2", "1"],
                ["3", "", "Orbital", "star", "10", "100", "0", "0", "False", "no-tic", "0",
                 "1"],
                ["4", "44", "Orbital", "star", "10", "100", "1", "1", "True", "ok", "2", "1"]])
        prior_h = ["source_id", "solution_type", "period_d", "period_err", "cosi", "cosi_sd",
                   "m1", "m2_dark", "r1", "r2", "ecc", "dur1_h", "dur2_h", "p_ecl1", "p_ecl2",
                   "significance", "ruwe", "t_conj1_btjd", "t_conj2_btjd", "next1_sd_d",
                   "next2_sd_d", "transit_conj"]

        def prior(sid, st):
            return [sid, st, "100", "0.01", "0", "0.001", "1", "0.5", "1", "0.5", "0", "", "",
                    "1", "1", "30", "1.5", "0", "50", "0.5", "0.5", ""]
        _write(os.path.join(d, "gaia_edge_on_priors.csv"), prior_h,
               [prior("1", "AstroSpectroSB1"), prior("2", "Orbital"), prior("3", "Orbital"),
                prior("4", "Orbital"), prior("999", "Orbital")])
        _write(os.path.join(d, "events.csv"),
               ["source_id", "tic", "t_center", "duration_h", "depth_ppm", "snr",
                "box_noise_ppm", "near_edge", "n_other_targets_same_time", "bf", "conj",
                "offset_d", "offset_sd_d"],
               [["1", "11", "1000.3", "4", "20000", "50", "100", "False", "0", "30", "t1",
                 "0.3", "0.5"],
                ["1", "11", "1025.0", "4", "800", "8", "100", "False", "0", "0", "t1",
                 "25", "0.5"]])
        _write(os.path.join(d, "covered_windows.csv"),
               ["source_id", "tic", "class_", "period_d", "conj", "is_rv_transit", "centre",
                "sd", "n_in_1sd", "n_in_3sd"],
               [["1", "11", "star", "100", "t1", "False", "1000", "0.5", "10", "30"],
                ["1", "11", "star", "100", "t2", "False", "1050", "0.5", "10", "30"],
                ["2", "22", "star", "100", "t1", "False", "1000", "0.5", "10", "30"],
                ["2", "22", "star", "100", "t2", "False", "1050", "0.5", "10", "30"]])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_run(self):
        out = os.path.join(self.tmp, "out")
        s = ce.run(os.path.join(self.tmp, "data"), out, offline=True)
        self.assertEqual(s["n_main"], 2)
        self.assertEqual(s["excluded"], {"gaia_eb": 1, "no_tess": 1})
        self.assertEqual(s["main"]["n_obs"], 1)
        # cos i = 0 +- 0.001 against lim = q = 0.01445: both certain -> 2 expected
        self.assertAlmostEqual(s["main"]["n_exp_m0"], 2.0, places=6)
        self.assertAlmostEqual(s["main"]["ratio"], 0.5, places=6)
        self.assertEqual(s["control"], {"valid": 2, "hits": 0, "rate": 0.0})
        self.assertEqual(s["timing"]["n"], 1)
        self.assertAlmostEqual(s["timing"]["rms_z"], 0.6, places=6)
        self.assertEqual(s["n_strong_rule_main"], 1)
        self.assertFalse(s["grades"]["C7"]["pass"])
        for name in ("calib_targets.csv", "calib_summary.json", "calib_report.md"):
            self.assertTrue(os.path.exists(os.path.join(out, name)))
        with open(os.path.join(out, "calib_summary.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["version"], ce.VERSION)
        with open(os.path.join(out, "calib_report.md"), encoding="utf-8") as fh:
            rep = fh.read()
        self.assertIn("| 2 | 22 |", rep)        # predicted with p >= 0.8 but not seen


if __name__ == "__main__":
    unittest.main()
