# SPDX-License-Identifier: Apache-2.0
"""Tests for eblm_infl.py (MV2 of Munim, Inc.; made with AI agents). Every expected value
is worked by hand in the comments. No network."""
import math
import unittest

import eblm_infl as ei

SNIPPET = """! BHAC15 models
!  t (Gyr) =   1.0000
!-----------------------------------------------------------------------
! M/Ms  Teff     L/Ls   g    R/Rs   Li/Li0    Mj     Mh     Mk
!-----------------------------------------------------------------------
  0.100  2811.  -3.06  5.25  0.124  0.000  10.36   9.77   9.48
  0.200  3262.  -2.32  5.06  0.217  0.000   8.68   8.08   7.83

!  t (Gyr) =   5.0000
!-----------------------------------------------------------------------
! M/Ms  Teff     L/Ls   g    R/Rs   Li/Li0    Mj     Mh     Mk
  0.100  2811.  -3.06  5.25  0.124  0.000  10.36   9.77   9.48
  0.300  3416.  -1.96  4.96  0.299  0.000   7.85   7.24   7.00
"""


def good_row(**kw):
    r = {"verdict": "EBLM_CONSISTENT", "b": "0.3", "snr_fit": "50", "m1_source": "flame", "m2": "0.2",
         "r2_flame": "0.22", "r2": "0.22", "r1_ratio": "1.0", "period_gaia": "1.0"}
    r.update(kw)
    return r


class TestModels(unittest.TestCase):
    def test_parse(self):
        m = ei.parse_bhac15(SNIPPET)
        self.assertEqual(sorted(m), [1.0, 5.0])
        self.assertEqual(m[1.0], [(0.1, 0.124), (0.2, 0.217)])
        self.assertEqual(m[5.0], [(0.1, 0.124), (0.3, 0.299)])

    def test_offline_fallback(self):
        m, src = ei.load_models(offline=True)
        self.assertEqual(src, "fallback_transcribed")
        self.assertEqual(sorted(m), [1.0, 5.0, 10.0])

    def test_r_model(self):
        F = ei.BHAC15_FALLBACK
        self.assertAlmostEqual(ei.r_model(0.15, F, 5.0), 0.175, places=12)        # grid point
        # halfway between (0.2, 0.218) and (0.3, 0.299): 0.218 + 0.081 / 2 = 0.2585
        self.assertAlmostEqual(ei.r_model(0.25, F, 5.0), 0.2585, places=9)
        self.assertTrue(math.isnan(ei.r_model(0.05, F, 5.0)))                   # below grid
        self.assertTrue(math.isnan(ei.r_model(0.9, F, 5.0)))                    # above grid
        self.assertTrue(math.isnan(ei.r_model(0.2, F, 3.0)))                    # no such age
        self.assertTrue(math.isnan(ei.r_model(float("nan"), F, 5.0)))


class TestStats(unittest.TestCase):
    def test_ranks(self):
        self.assertEqual(ei.ranks([3, 1, 2]), [3.0, 1.0, 2.0])
        self.assertEqual(ei.ranks([1, 1, 2]), [1.5, 1.5, 3.0])

    def test_spearman_ties(self):
        # ranks y = [1.5, 1.5, 3.5, 3.5]; centred x [-1.5,-.5,.5,1.5], y [-1,-1,1,1]
        # sum xy = 4, |x| = sqrt(5), |y| = 2 -> 2 / sqrt(5)
        self.assertAlmostEqual(ei.spearman([1, 2, 3, 4], [1, 1, 2, 2]), 2 / math.sqrt(5), places=12)
        self.assertAlmostEqual(ei.spearman([1, 2, 3], [3, 2, 1]), -1.0, places=12)
        self.assertTrue(math.isnan(ei.spearman([1, 2, 3], [5, 5, 5])))

    def test_perm(self):
        x = list(range(10))
        rho, p = ei.perm_p_less(x, [-v for v in x], n_perm=2000)
        self.assertAlmostEqual(rho, -1.0, places=12)
        self.assertLess(p, 0.002)          # only the exact reversal (1 in 10!) ties it
        rho, p = ei.perm_p_less(x, x, n_perm=2000)
        self.assertAlmostEqual(p, 1.0, places=12)   # every permutation has rho <= +1

    def test_median(self):
        self.assertEqual(ei.median([3, 1, 2]), 2)
        self.assertEqual(ei.median([4, 1, 3, 2]), 2.5)
        self.assertTrue(math.isnan(ei.median([])))

    def test_median_ci_constant(self):
        self.assertEqual(ei.median_ci([0.1] * 10), (0.1, 0.1, 0.1))

    def test_h1_label(self):
        self.assertEqual(ei.h1_label(10, 0.1, 0.1), "INFLATED")
        self.assertEqual(ei.h1_label(10, -0.01, 0.02), "NOT_INFLATED")
        self.assertEqual(ei.h1_label(10, 0.0, 0.1), "INCONCLUSIVE")
        self.assertEqual(ei.h1_label(10, 0.03, 0.1), "INCONCLUSIVE")   # boundary: not > 0.03
        self.assertEqual(ei.h1_label(7, 0.1, 0.2), "TOO_FEW")


class TestSample(unittest.TestCase):
    def test_cuts(self):
        f = ei.main_set_reason
        self.assertEqual(f(good_row()), "")
        self.assertEqual(f(good_row(verdict="BD_EBLM_LARGE_RADIUS")), "")
        self.assertEqual(f(good_row(verdict="TOO_LUMINOUS")), "not_clean_verdict")
        self.assertEqual(f(good_row(verdict="EBLM_GRAZING")), "not_clean_verdict")
        self.assertEqual(f(good_row(b="0.85")), "b_ge_0.8")
        self.assertEqual(f(good_row(b="")), "b_ge_0.8")
        self.assertEqual(f(good_row(snr_fit="29")), "snr_lt_30")
        self.assertEqual(f(good_row(m1_source="default_1.3")), "no_flame_mass")
        self.assertEqual(f(good_row(m2="0.7")), "m2_outside_0.08_0.6")
        self.assertEqual(f(good_row(r2_flame="")), "no_flame_radius")
        self.assertEqual(f(good_row(r1_ratio="1.25")), "r1_lc_flame_disagree")

    def test_score(self):
        d = ei.score([good_row(r2_flame="0.25", r2="0.218")], ei.BHAC15_FALLBACK)[0]
        self.assertAlmostEqual(d["infl_flame_5"], 0.25 / 0.218 - 1, places=12)
        self.assertAlmostEqual(d["infl_flame_1"], 0.25 / 0.217 - 1, places=12)
        self.assertAlmostEqual(d["infl_flame_10"], 0.25 / 0.220 - 1, places=12)
        self.assertAlmostEqual(d["infl_lc_5"], 0.0, places=12)
        self.assertEqual(d["main_set_cut"], "")

    def test_summarize_trend(self):
        # 10 main-set rows, P = 0.5 .. 5.0 d, inflation 0.20, 0.18, ..., 0.02 (falls with P)
        rows = [good_row(period_gaia=str(0.5 + 0.5 * i), r2_flame=repr(0.218 * (1.2 - 0.02 * i)))
                for i in range(10)]
        rows.append(good_row(verdict="NO_ECLIPSE"))
        s = ei.summarize(ei.score(rows, ei.BHAC15_FALLBACK), n_boot=500, n_perm=2000)
        self.assertEqual(s["n_main"], 10)
        self.assertEqual(s["cuts"], {"in_main_set": 10, "not_clean_verdict": 1})
        self.assertAlmostEqual(s["H1"]["median"], 0.11, places=9)     # (0.12 + 0.10) / 2
        self.assertAlmostEqual(s["H2"]["rho_infl_P"], -1.0, places=12)
        self.assertEqual(s["H2"]["label"], "PERIOD_TREND")
        # bins: [0,1): 0.5 | [1,2): 1.0, 1.5 | [2,5): 2.0 .. 4.5 | >= 5: 5.0
        self.assertEqual([v["n"] for v in s["period_bins"].values()], [1, 2, 6, 1])

    def test_summarize_too_few(self):
        s = ei.summarize(ei.score([good_row()] * 3, ei.BHAC15_FALLBACK), n_boot=100, n_perm=100)
        self.assertEqual(s["H1"]["label"], "TOO_FEW")
        self.assertEqual(s["H2"]["label"], "TOO_FEW")


if __name__ == "__main__":
    unittest.main()
