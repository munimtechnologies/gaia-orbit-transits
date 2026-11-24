# SPDX-License-Identifier: Apache-2.0
"""Tests for gaia_conj_dips_acv2 (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents).

Every expected value below was worked out by hand on 2026-11-24 from the same epochs before the
code was run; these tests are the machine check of that hand calculation. Borderline epochs
(within ~0.002 mag of a threshold) are deliberately not asserted. Stdlib only."""
import unittest

import gaia_conj_dips_acv2 as m

CD44 = "5387577190509272832"
V1229 = "66729880383767168"
S911 = "911500121588495744"
S3032 = "3032388065085357440"
N_LISTED = {"6158619786886806016": 37, "355656522274764288": 22, S3032: 53,
            "4211060509978414208": 22, CD44: 73, V1229: 24, "4945020530510815360": 63,
            "265213581990291840": 32, S911: 41, "3347294105150514688": 24,
            "4582483440569725184": 70, "1853022343761824768": 103, "5645527428755291648": 87,
            "5305914640875063424": 42, "6879998061518438400": 31}
NO_DIPS = [s for s in N_LISTED if s not in (CD44, V1229)]


def ts(ds):
    return {round(d["t"], 3) for d in ds}


def by_t(ds, t):
    return [d for d in ds if round(d["t"], 3) == round(t, 3)][0]


class TestBatch2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = m.analyse_all()
        cls.s = {x["source_id"]: x for x in cls.res["stars"]}

    def test_counts(self):
        self.assertEqual(set(self.s), set(N_LISTED))
        for sid, n in N_LISTED.items():
            self.assertEqual(self.s[sid]["n_listed"], n, sid)
        self.assertEqual(self.res["summary"]["n_listed"], 724)

    def test_cd44_6966(self):
        s = self.s[CD44]
        self.assertEqual(s["n_used"], 68)
        self.assertAlmostEqual(s["median_mag"], 9.9013225, delta=0.0002)
        c1, c2 = s["conj_phases"]
        self.assertAlmostEqual(c2, 0.05570, delta=0.002)
        self.assertAlmostEqual(c1, 0.55687, delta=0.002)
        got = ts(s["dips"])
        self.assertTrue({2103.412, 2313.486} <= got <= {2103.412, 2313.486, 1689.195}, got)
        self.assertAlmostEqual(by_t(s["dips"], 2103.4121447)["phase"], 0.06273, delta=0.002)
        self.assertAlmostEqual(by_t(s["dips"], 2313.4858762)["phase"], 0.06212, delta=0.002)
        for t in (2103.4121447, 2313.4858762):
            d = by_t(s["dips"], t)
            self.assertEqual(d["nearest_conj"], "c2")
            self.assertLessEqual(abs(d["dphase"]), m.WINDOW)
            self.assertTrue(0.045 < d["dmag"] < 0.06, d["dmag"])
        self.assertEqual(ts(s["rejected_faint"]), {2620.669})
        self.assertAlmostEqual(s["rejected_faint"][0]["phase"], 0.74030, delta=0.002)
        self.assertGreater(s["conj_phase_sigma"], 0.2)

    def test_v1229_tau_known_eb(self):
        s = self.s[V1229]
        c1, c2 = s["conj_phases"]
        self.assertAlmostEqual(c2, 0.36073, delta=0.002)
        self.assertAlmostEqual(c1, 0.86811, delta=0.002)
        self.assertAlmostEqual(s["median_mag"], 6.8144095, delta=0.0002)
        self.assertEqual(ts(s["dips"]), {1709.102, 2577.887})
        self.assertAlmostEqual(by_t(s["dips"], 1709.1015109)["phase"], 0.35010, delta=0.002)
        self.assertAlmostEqual(by_t(s["dips"], 2577.8868966)["phase"], 0.34477, delta=0.002)
        for d in s["dips"]:
            self.assertEqual(d["nearest_conj"], "c2")
            self.assertLessEqual(abs(d["dphase"]), m.WINDOW)
            self.assertTrue(0.027 < d["dmag"] < 0.037, d["dmag"])
        self.assertEqual(s["rejected_faint"], [])

    def test_no_dips(self):
        for sid in NO_DIPS:
            self.assertEqual(self.s[sid]["dips"], [], sid)
            self.assertEqual(self.s[sid]["rejected_faint"], [], sid)

    def test_3032_large_scatter(self):
        s = self.s[S3032]
        self.assertAlmostEqual(s["median_mag"], 9.274353, delta=0.0002)
        self.assertGreater(s["dip_threshold_mag"], 0.09)

    def test_911_faintest_at_conjunction(self):
        s = self.s[S911]
        self.assertAlmostEqual(s["median_mag"], 8.397431, delta=0.0001)
        c1 = s["conj_phases"][0]
        self.assertAlmostEqual(c1, 0.13458, delta=0.002)
        f = s["faintest3"]
        self.assertEqual(ts(f), {2666.236, 2167.545, 1892.849})
        exp = {2666.236: 0.13223, 2167.545: 0.13499, 1892.849: 0.13062}
        for d in f:
            self.assertAlmostEqual(d["phase"], exp[round(d["t"], 3)], delta=0.002)
            self.assertLess(abs(d["phase"] - c1), 0.006)
            self.assertTrue(0.012 < d["dmag"] < 0.017, d["dmag"])

    def test_summary(self):
        sm = self.res["summary"]
        self.assertEqual(set(sm["stars_with_dips"]), {"CD-44 6966", "V1229 Tau (HD 23642)"})
        self.assertIn(sm["n_dips"], (4, 5))
        self.assertGreaterEqual(sm["n_dips_in_window"], 4)


class TestTessTiming(unittest.TestCase):
    """Gaia faint epochs vs IJspeert et al. (2024) TESS eclipse ephemerides (hand values)."""

    def test_hd218299(self):
        t0 = m.IJSPEERT["HD 218299"][2]
        half = 3.051283767729989 / 2.0
        self.assertAlmostEqual(m.tess_offset(1937.1285336, t0, half), 0.0006, delta=0.002)
        self.assertAlmostEqual(m.tess_offset(2237.6795574, t0, half), 0.0002, delta=0.002)

    def test_hd101167(self):
        t0 = m.IJSPEERT["HD 101167"][2]
        P = 3.0836443383497594
        self.assertAlmostEqual(m.tess_offset(1951.0272090, t0, P), 0.0196, delta=0.002)
        self.assertAlmostEqual(m.tess_offset(2321.0709602, t0, P), 0.0260, delta=0.002)

    def test_cd44(self):
        t0 = m.IJSPEERT["CD-44 6966"][2]
        t0y3 = m.IJSPEERT["CD-44 6966 y3"][2]
        half_gaia = 2.3872179377467266 / 2.0
        self.assertAlmostEqual(m.tess_offset(2103.4121447, t0, half_gaia), 0.0342, delta=0.002)
        self.assertAlmostEqual(m.tess_offset(2313.4858762, t0, half_gaia), 0.0327, delta=0.002)
        half_tess = (t0y3 - t0) / 618.0
        self.assertAlmostEqual(half_tess, 1.1935875, delta=2e-6)
        self.assertAlmostEqual(m.tess_offset(2103.4121447, t0, half_tess), 0.0118, delta=0.002)
        self.assertAlmostEqual(m.tess_offset(2313.4858762, t0, half_tess), 0.0141, delta=0.002)

    def test_v1229_tau_secondary(self):
        P = 2.461185529609541
        t0 = m.IJSPEERT["V1229 Tau (HD 23642)"][2] + P / 2.0
        self.assertAlmostEqual(m.tess_offset(1709.1015109, t0, P), 0.0178, delta=0.002)
        self.assertAlmostEqual(m.tess_offset(2577.8868966, t0, P), 0.0047, delta=0.002)

    def test_911(self):
        t0 = m.IJSPEERT["Gaia DR3 911500121588495744"][2]
        half = 2.666836608075459 / 2.0
        for t, exp in ((2167.5449393, -0.0325), (2666.2360239, -0.0398), (1892.8491219, -0.0441)):
            self.assertAlmostEqual(m.tess_offset(t, t0, half), exp, delta=0.002)


if __name__ == "__main__":
    unittest.main()
