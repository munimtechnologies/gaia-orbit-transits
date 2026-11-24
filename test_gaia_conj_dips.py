# SPDX-License-Identifier: Apache-2.0
"""Tests for gaia_conj_dips (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents).

The expected sets and numbers were worked out by hand on 2026-11-24 from the same epochs before
the code ran; these tests are the machine check of that hand calculation. Stdlib only."""
import math
import unittest

import gaia_conj_dips as m

CD63 = "5288669213282803328"
CD72 = "6374372070227419008"
FLAT = ["6025454428973694464", "6370053605166404992", "3043555010111094400",
        "2995056243702062080", "3419201066092932992", "6547214134176807808",
        "3024112659531165568", "5512207383273412864", "5871568499564025472",
        "1734078000491716224", "1615317447472056448", "6668966900715757312",
        "3323030323068415744", "6705693548324328960", "5442901385802064000",
        "5448988969368351616", "3944246249499094272"]
# usable epochs (listed rows with a G value, minus rows flagged rejected), counted by hand
N_USED = {"6025454428973694464": 34, "6370053605166404992": 54, "3043555010111094400": 55,
          "2995056243702062080": 35, "3419201066092932992": 39, "6547214134176807808": 35,
          "3024112659531165568": 44, "5512207383273412864": 41, "5871568499564025472": 98,
          "1734078000491716224": 40, "1615317447472056448": 56, "6668966900715757312": 36,
          "3323030323068415744": 28, "6705693548324328960": 45, "5442901385802064000": 79,
          "5448988969368351616": 53, "3944246249499094272": 50}


def _set(xs):
    return {round(x, 3) for x in xs}


class TestHelpers(unittest.TestCase):
    def test_median_sd(self):
        self.assertEqual(m.median([3, 1, 2]), 2)
        self.assertEqual(m.median([4, 1, 2, 3]), 2.5)
        self.assertAlmostEqual(m.robust_sd([1.0, 1.0, 1.0, 2.0, 0.0]), 0.0)

    def test_circular_conjunctions(self):
        c1, c2 = m.conjunction_phases(None, None)
        self.assertAlmostEqual(c1, 0.25, places=9)
        self.assertAlmostEqual(c2, 0.75, places=9)

    def test_eccentric_conjunctions(self):
        # hand values for Gaia DR3 6025454428973694464 (e 0.1694, omega 335.79)
        c1, c2 = m.conjunction_phases(0.16940352453282803, 335.7909680229006)
        self.assertAlmostEqual(c1, 0.2656, delta=0.003)
        self.assertAlmostEqual(c2, 0.8638, delta=0.003)

    def test_dphase(self):
        self.assertAlmostEqual(m.dphase(0.99, 0.01), -0.02)
        self.assertAlmostEqual(m.dphase(0.26, 0.25), 0.01)


class TestHandCalculation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = m.analyse_all()
        cls.by = {s["source_id"]: s for s in cls.res["stars"]}

    def test_counts(self):
        self.assertEqual(self.res["summary"]["n_stars"], 19)
        self.assertEqual(set(self.by), set(FLAT) | {CD63, CD72})
        for sid, n in N_USED.items():
            self.assertEqual(self.by[sid]["n_used"], n, sid)
        self.assertEqual(sum(s["n_used"] for s in self.res["stars"]), 952)
        self.assertEqual(self.by[CD63]["n_listed"], 76)
        self.assertEqual(self.by[CD63]["n_used"], 75)
        self.assertEqual(self.by[CD72]["n_listed"], 56)
        self.assertEqual(self.by[CD72]["n_used"], 55)

    def test_cd63_310(self):
        s = self.by[CD63]
        self.assertAlmostEqual(s["median_mag"], 9.94356, delta=0.0003)
        self.assertTrue(0.0040 < s["robust_sd"] < 0.0075, s["robust_sd"])
        self.assertEqual(_set(d["t"] for d in s["dips"]), _set([1672.6624380, 1672.7364185]))
        ph = sorted(d["phase"] for d in s["dips"])
        self.assertAlmostEqual(ph[0], 0.75026, delta=0.0015)
        self.assertAlmostEqual(ph[1], 0.76393, delta=0.0015)
        for d in s["dips"]:
            self.assertEqual(d["nearest_conj"], "c2")
            self.assertGreater(d["dmag"], 0.030)
        deep = max(s["dips"], key=lambda d: d["dmag"])
        self.assertAlmostEqual(deep["dmag"], 0.0398, delta=0.0006)
        self.assertLess(abs(deep["offset_d"]), 0.005)
        self.assertTrue(0.02 < deep["conj_time_sigma_d"] < 0.035, deep["conj_time_sigma_d"])
        # epochs near the other conjunction (phase 0.25) are within 0.01 mag of the median
        c1 = s["near_conj"]["c1"]
        self.assertEqual(_set(x["t"] for x in c1), _set([1669.9106516, 2238.0095647, 1891.9494353]))
        for x in c1:
            self.assertLess(abs(x["dmag"]), 0.01)
        c2 = s["near_conj"]["c2"]
        self.assertEqual(_set(x["t"] for x in c2),
                         _set([1672.4862556, 1672.6624380, 1672.7364185, 2024.2048150]))

    def test_cd72_1603(self):
        s = self.by[CD72]
        self.assertEqual(_set(d["t"] for d in s["dips"]), _set([2120.3602638]))
        d = s["dips"][0]
        self.assertAlmostEqual(d["phase"], 0.24406, delta=0.0015)
        self.assertEqual(d["nearest_conj"], "c1")
        self.assertAlmostEqual(d["dmag"], 0.0517, delta=0.0015)
        self.assertGreater(d["dmag_sigma"], 10.0)
        self.assertTrue(0.004 < d["conj_time_sigma_d"] < 0.01, d["conj_time_sigma_d"])
        c1 = s["near_conj"]["c1"]
        self.assertEqual(_set(x["t"] for x in c1),
                         _set([2293.7781314, 2439.9272459, 2440.0012499, 2120.3602638,
                               2590.8657269, 1946.9713689]))
        for x in c1:
            if round(x["t"], 3) != 2120.360:
                self.assertLess(abs(x["dmag"]), 0.006)
        self.assertEqual(s["near_conj"]["c2"], [])

    def test_flat_stars(self):
        for sid in FLAT:
            self.assertEqual(self.by[sid]["dips"], [], sid)

    def test_summary(self):
        sm = self.res["summary"]
        self.assertEqual(sm["n_stars"], 19)
        self.assertEqual(sm["n_stars_with_dips"], 2)
        self.assertEqual(sm["n_dips"], 3)
        self.assertEqual(sm["n_dips_within_0p01_of_conj"], 2)
        self.assertEqual(sorted(sm["stars_with_dips"]), ["CD-63 310", "CD-72 1603"])


if __name__ == "__main__":
    unittest.main()
