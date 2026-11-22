# Tests for vpt_nss.py. By MV2 of Munim, Inc. Made with AI agents. License: Apache-2.0.
# Fixture: the seven Gaia DR3 transit candidates with an NSS solution (22 Nov 2026 TAP query;
# data/vpt-nss-dr3/vpt_nss_dr3.csv).
import csv
import io
import json
import os
import tempfile
import unittest

import vpt_nss

FIXTURE = """source_id,name,vpt_period_d,nss_solution_type,nss_period_d,k1_kms,eccentricity,bm_m1
4955371367334610048,WASP-18,0.9414777434661444,SB1,0.9414684606070756,1.9382581841901922,0.1233766991234055,1.202525
5656896924435896832,HATS-26,3.302618976848641,OrbitalTargetedSearch,193.53658040052832,,0.4545115195106782,
5348534425968598400,TOI-1991,3.7463005282283746,SB1,6.659057724349355,9.571462460115908,0.0726617663390752,
1748596020745038208,WASP-2,0.6680249841344066,OrbitalTargetedSearch,38.04406110046708,,0.3887104214960128,0.8419213
3450611154067089408,TIC 400170926,0.8847834934791456,SB2C,5.895935077280673,72.62443658950218,,1.0540308
4535127268607000320,TIC 470993218,2.5978749383004702,SB1,7.062258704422171,22.403876102953035,0.10678583091074959,1.3905127
1622997463177004928,TIC 207399049,0.851375396953779,SB1,0.4602306497601689,19.69556861332535,0.20088969439415774,1.0263727
"""


def rows():
    return list(csv.DictReader(io.StringIO(FIXTURE)))


class TestMass(unittest.TestCase):
    def test_mass_function_wasp18(self):
        f = vpt_nss.mass_function(1.9382581841901922, 0.9414684606070756, 0.1233766991234055)
        self.assertAlmostEqual(f / 6.94e-7, 1.0, delta=0.02)

    def test_min_mass_small_companion_limit(self):
        # for m2 << m1, m2 ~ (f m1^2)^(1/3)
        f = vpt_nss.mass_function(0.1, 3.0, 0.0)
        m2 = vpt_nss.min_companion_mass(0.1, 3.0, 1.0, 0.0)
        self.assertAlmostEqual(m2 / (f ** (1.0 / 3.0)), 1.0, delta=0.01)

    def test_min_mass_solves_equation(self):
        m2 = vpt_nss.min_companion_mass(30.0, 5.0, 1.2, 0.1)
        f = vpt_nss.mass_function(30.0, 5.0, 0.1)
        self.assertAlmostEqual(m2 ** 3 / (1.2 + m2) ** 2, f, places=10)

    def test_zero_amplitude(self):
        self.assertEqual(vpt_nss.min_companion_mass(0.0, 5.0, 1.0, 0.0), 0.0)


class TestLabels(unittest.TestCase):
    def setUp(self):
        self.per_solution, self.per_star = vpt_nss.screen_rows(rows())

    def lab(self, sid):
        return self.per_star[sid]

    def test_wasp18_substellar(self):
        s = self.lab("4955371367334610048")
        self.assertEqual(s["label"], "NSS_SUBSTELLAR")
        self.assertTrue(0.0095 < s["m2_min_msun"] < 0.0106)
        self.assertAlmostEqual(s["period_ratio_orbit_over_transit"], 1.0, delta=1e-4)

    def test_sb2_stellar(self):
        s = self.lab("3450611154067089408")
        self.assertEqual(s["label"], "NSS_STELLAR")
        self.assertAlmostEqual(s["period_ratio_orbit_over_transit"], 6.6637, delta=0.001)

    def test_tic470993218_stellar(self):
        s = self.lab("4535127268607000320")
        self.assertEqual(s["label"], "NSS_STELLAR")
        self.assertTrue(0.27 < s["m2_min_msun"] < 0.30)

    def test_toi1991_default_m1(self):
        s = self.lab("5348534425968598400")
        self.assertEqual(s["label"], "NSS_STELLAR")
        self.assertEqual(s["m1_used_msun"], 1.0)
        self.assertTrue(0.085 < s["m2_min_msun"] < 0.093)

    def test_tic207399049_boundary(self):
        s = self.lab("1622997463177004928")
        self.assertEqual(s["label"], "NSS_SUBSTELLAR")
        self.assertTrue(0.070 < s["m2_min_msun"] < 0.080)

    def test_astrometric_no_k(self):
        self.assertEqual(self.lab("5656896924435896832")["label"], "NSS_NO_K")
        self.assertEqual(self.lab("1748596020745038208")["label"], "NSS_NO_K")

    def test_summary_counts(self):
        cands = list(self.per_star.keys()) + ["1", "2"]
        summ = vpt_nss.summarise(self.per_star, cands)
        self.assertEqual(summ["counts"], {"NSS_STELLAR": 3, "NSS_SUBSTELLAR": 2,
                                          "NSS_NO_K": 2, "NSS_NONE": 2})

    def test_most_severe_wins(self):
        extra = dict(rows()[0])
        extra["nss_solution_type"] = "SB2"
        _, per_star = vpt_nss.screen_rows(rows() + [extra])
        self.assertEqual(per_star["4955371367334610048"]["label"], "NSS_STELLAR")

    def test_blank_and_junk(self):
        self.assertIsNone(vpt_nss.to_float(""))
        self.assertIsNone(vpt_nss.to_float("nan"))
        self.assertIsNone(vpt_nss.to_float("abc"))
        self.assertEqual(vpt_nss.label_solution("", 1.0, 1.0, 0.0, 1.0)[0], "NSS_NONE")


class TestQueryAndCli(unittest.TestCase):
    def test_query_text(self):
        q = vpt_nss.build_query("gaiadr4")
        self.assertIn("gaiadr4.vari_planetary_transit", q)
        self.assertIn("gaiadr4.binary_masses", q)
        self.assertNotIn("binary_masses", vpt_nss.build_query("gaiadr3", with_masses=False))

    def test_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            inp = os.path.join(d, "in.csv")
            with open(inp, "w", newline="") as fh:
                fh.write(FIXTURE)
            out = os.path.join(d, "out")
            self.assertEqual(vpt_nss.main(["--in", inp, "--out-dir", out]), 0)
            with open(os.path.join(out, "nss_summary.json")) as fh:
                summ = json.load(fh)
            self.assertEqual(summ["n_stars_with_solution"], 7)
            self.assertEqual(summ["counts"]["NSS_STELLAR"], 3)
            with open(os.path.join(out, "nss_screen.csv"), newline="") as fh:
                self.assertEqual(len(list(csv.DictReader(fh))), 7)


if __name__ == "__main__":
    unittest.main()
