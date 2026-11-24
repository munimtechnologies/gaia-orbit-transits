# SPDX-License-Identifier: Apache-2.0
"""Tests for gaia_conj_dips_acv (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents).

Every expected phase and set below was worked out by hand on 2026-11-24 from the same epochs before
the code was run; these tests are the machine check of that hand calculation. Borderline epochs
(within ~0.002 mag of a threshold) are deliberately not asserted either way. Stdlib only."""
import unittest

import gaia_conj_dips_acv as m

HD218299 = "1934924724387752832"
HD101167 = "3479008554410838656"
HD187301 = "4297719103037032832"
V1202CEN = "5866041495122321280"
# number of G rows DataLink listed for each star (incl. rows with no G value)
N_LISTED = {"5409717025365557504": 61, "5448354070122614400": 62, HD218299: 95, HD101167: 75,
            "5322036676774951808": 46, "2562554132208861568": 42, V1202CEN: 84,
            "427015307960557952": 55, "6702507988262437248": 57, "5967067986401035008": 46,
            "1907116872732089216": 83, "4490721395569773184": 43, "2304516276636844800": 39,
            "3231626306540378112": 47, "5759012181375799296": 48, HD187301: 63}
NO_DIPS = ["5409717025365557504", "427015307960557952", "1907116872732089216", "5759012181375799296",
           "6702507988262437248", "5967067986401035008", "2304516276636844800", "2562554132208861568",
           "4490721395569773184"]


def ts(ds):
    return {round(d["t"], 3) for d in ds}


def by_t(ds, t):
    return [d for d in ds if round(d["t"], 3) == round(t, 3)][0]


class TestHelpers(unittest.TestCase):
    def test_circular(self):
        c1, c2 = m.conjunction_phases(None, None)
        self.assertAlmostEqual(c1, 0.25, places=9)
        self.assertAlmostEqual(c2, 0.75, places=9)

    def test_dphase(self):
        self.assertAlmostEqual(m.dphase(0.99, 0.01), -0.02)


class TestHand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = m.analyse_all()
        cls.s = {x["source_id"]: x for x in cls.res["stars"]}

    def test_counts(self):
        self.assertEqual(set(self.s), set(N_LISTED))
        for sid, n in N_LISTED.items():
            self.assertEqual(self.s[sid]["n_listed"], n, sid)
        self.assertEqual(self.res["summary"]["n_listed"], 946)

    def test_hd218299(self):
        s = self.s[HD218299]
        c1, c2 = s["conj_phases"]
        self.assertAlmostEqual(c1, 0.29041, delta=0.002)
        self.assertAlmostEqual(c2, 0.79411, delta=0.002)
        self.assertTrue({1937.129, 2101.971} <= ts(s["dips"]), ts(s["dips"]))
        self.assertAlmostEqual(by_t(s["dips"], 1937.1285336)["phase"], 0.78817, delta=0.002)
        self.assertAlmostEqual(by_t(s["dips"], 2101.9709680)["phase"], 0.81213, delta=0.002)
        self.assertTrue(0.067 < by_t(s["dips"], 1937.1285336)["dmag"] < 0.076)
        for d in s["dips"]:
            self.assertLessEqual(abs(d["dphase"]), m.WINDOW, d)
        self.assertTrue({1955.387, 2237.680, 2427.395} <= ts(s["rejected_faint"]), ts(s["rejected_faint"]))
        self.assertAlmostEqual(by_t(s["rejected_faint"], 1955.3870087)["phase"], 0.77204, delta=0.002)
        self.assertAlmostEqual(by_t(s["rejected_faint"], 2237.6795574)["phase"], 0.28803, delta=0.002)
        self.assertAlmostEqual(by_t(s["rejected_faint"], 2427.3953117)["phase"], 0.46375, delta=0.002)

    def test_hd101167(self):
        s = self.s[HD101167]
        self.assertAlmostEqual(s["conj_phases"][1], 0.93335, delta=0.002)
        self.assertEqual(ts(s["dips"]), {1951.027, 2321.071})
        self.assertAlmostEqual(by_t(s["dips"], 1951.0272090)["phase"], 0.92993, delta=0.002)
        self.assertAlmostEqual(by_t(s["dips"], 2321.0709602)["phase"], 0.93202, delta=0.002)
        for d in s["dips"]:
            self.assertEqual(d["nearest_conj"], "c2")
            self.assertLess(abs(d["dphase"]), 0.006)
            self.assertGreater(d["dmag"], 0.035)
        self.assertEqual(ts(s["rejected_faint"]), {1953.028})
        self.assertAlmostEqual(s["rejected_faint"][0]["phase"], 0.57889, delta=0.002)

    def test_hd187301(self):
        s = self.s[HD187301]
        c1, c2 = s["conj_phases"]
        self.assertAlmostEqual(c1, 0.19116, delta=0.002)
        self.assertAlmostEqual(c2, 0.71083, delta=0.002)
        self.assertEqual(ts(s["dips"]), {2083.752, 2354.684, 2356.686})
        exp = {2083.7524917: (0.72777, "c2"), 2354.6844838: (0.20654, "c1"), 2356.6859063: (0.70503, "c2")}
        for t, (ph, which) in exp.items():
            d = by_t(s["dips"], t)
            self.assertAlmostEqual(d["phase"], ph, delta=0.002)
            self.assertEqual(d["nearest_conj"], which)
            self.assertLessEqual(abs(d["dphase"]), m.WINDOW)
            self.assertTrue(0.027 < d["dmag"] < 0.036, d["dmag"])
        self.assertEqual(s["rejected_faint"], [])

    def test_v1202_cen_control(self):
        s = self.s[V1202CEN]
        c1, c2 = s["conj_phases"]
        self.assertAlmostEqual(c2, 0.00862, delta=0.001)
        self.assertAlmostEqual(c1, 0.5158, delta=0.003)
        self.assertEqual(ts(s["dips"]), {2542.333, 2542.407})
        self.assertAlmostEqual(by_t(s["dips"], 2542.3331696)["phase"], 0.02005, delta=0.001)
        self.assertAlmostEqual(by_t(s["dips"], 2542.4071794)["phase"], 0.04214, delta=0.001)
        for d in s["dips"]:
            self.assertEqual(d["nearest_conj"], "c2")
            self.assertLessEqual(abs(d["dphase"]), m.WINDOW)
            self.assertGreater(d["dmag"], 0.08)

    def test_rejected_faint_off_conjunction(self):
        exp = {"2562554132208861568": {1698.869: 0.45533, 2059.067: 0.19595, 2429.933: 0.12770, 2430.183: 0.20253},
               "4490721395569773184": {2400.836: 0.94848, 2491.210: 0.50054},
               "5967067986401035008": {1913.386: 0.62668},
               "6702507988262437248": {2588.773: 0.59204},
               "2304516276636844800": {2020.088: 0.80058}}
        for sid, pts in exp.items():
            s = self.s[sid]
            self.assertEqual(ts(s["rejected_faint"]), set(pts), sid)
            for d in s["rejected_faint"]:
                self.assertAlmostEqual(d["phase"], pts[round(d["t"], 3)], delta=0.002)
                self.assertGreater(abs(d["dphase"]), 0.08, (sid, d))
        s = self.s["5448354070122614400"]
        self.assertIn(1672.012, ts(s["rejected_faint"]))
        self.assertAlmostEqual(by_t(s["rejected_faint"], 1672.0117868)["phase"], 0.83713, delta=0.002)
        s = self.s["5322036676774951808"]
        self.assertIn(2203.271, ts(s["rejected_faint"]))
        self.assertAlmostEqual(by_t(s["rejected_faint"], 2203.2710298)["phase"], 0.07843, delta=0.002)
        s = self.s["3231626306540378112"]
        self.assertIn(2250.377, ts(s["rejected_faint"]))
        self.assertGreater(s["conj_phase_sigma"], 0.2)

    def test_flat(self):
        for sid in NO_DIPS:
            self.assertEqual(self.s[sid]["dips"], [], sid)

    def test_summary(self):
        sm = self.res["summary"]
        four = {"HD 218299", "HD 101167", "HD 187301", "V1202 Cen"}
        allowed = four | {"Gaia DR3 5322036676774951808", "Gaia DR3 3231626306540378112",
                          "Gaia DR3 5448354070122614400"}
        self.assertTrue(four <= set(sm["stars_with_dips"]) <= allowed, sm["stars_with_dips"])


if __name__ == "__main__":
    unittest.main()
