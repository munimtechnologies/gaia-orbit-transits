# SPDX-License-Identifier: Apache-2.0
"""Unit tests for gaia_vpt_tess (stdlib only). MV2 of Munim, Inc.; made with AI agents."""
import math
import unittest

import gaia_vpt_tess as v


class TestPure(unittest.TestCase):
    def test_mmag(self):
        self.assertAlmostEqual(v.mmag_to_frac(10.0), 1 - 10 ** (-0.004), places=12)
        self.assertAlmostEqual(v.mmag_to_frac(10.0), 0.009168, places=5)
        self.assertTrue(math.isnan(v.mmag_to_frac(float("nan"))))

    def test_btjd(self):
        self.assertAlmostEqual(v.gaia_to_btjd(1802.5), 0.0)
        self.assertAlmostEqual(v.gaia_to_btjd(2000.0), 197.5)

    def test_period_match(self):
        self.assertEqual(v.period_match(3.0, 3.02), 1.0)
        self.assertEqual(v.period_match(3.0, 1.5), 0.5)
        self.assertEqual(v.period_match(3.0, 6.03), 2.0)
        self.assertIsNone(v.period_match(3.0, 3.5))
        self.assertIsNone(v.period_match(3.0, 0.0))
        self.assertIsNone(v.period_match(float("nan"), 3.0))

    def test_parse_exoarch(self):
        txt = "pl_name,tic_id,pl_orbper\nWASP-18 b,TIC 100100827,0.94145\nX b,,3.0\n"
        d = v.parse_exoarch(txt)
        self.assertIn("100100827", d)
        self.assertEqual(len(d), 1)
        self.assertAlmostEqual(d["100100827"][0][1], 0.94145)

    def test_classify(self):
        planets = {"1": [("A b", 2.0)], "5": [("E b", 9.0)]}
        tois = {"2": [{"toi": "100.01", "disp": "KP", "period": "3.0"}],
                "3": [{"toi": "200.01", "disp": "FP", "period": "4.0"}],
                "4": [{"toi": "300.01", "disp": "PC", "period": "2.5"}],
                "6": [{"toi": "400.01", "disp": "PC", "period": "7.7"}]}
        self.assertEqual(v.classify_known("1", 2.0, planets, tois)[0], "KNOWN_PLANET")
        self.assertEqual(v.classify_known("001", 4.0, planets, tois)[0], "KNOWN_PLANET")
        self.assertEqual(v.classify_known("2", 3.0, planets, tois)[0], "KNOWN_PLANET")
        self.assertEqual(v.classify_known("3", 4.0, planets, tois)[0], "TOI_FP")
        self.assertEqual(v.classify_known("4", 1.25, planets, tois)[0], "TOI_PC")
        self.assertEqual(v.classify_known("5", 3.0, planets, tois)[0], "KNOWN_SYSTEM_OTHER_P")
        self.assertEqual(v.classify_known("6", 3.0, planets, tois)[0], "KNOWN_SYSTEM_OTHER_P")
        self.assertEqual(v.classify_known("7", 3.0, planets, tois)[0], "NEW")
        self.assertEqual(v.classify_known("", 3.0, planets, tois)[0], "NO_TIC")

    def test_phase_offset(self):
        off, n, dP = v.phase_offset(100.0 + 10 * 3.0 + 0.05, 100.0, 3.0)
        self.assertEqual(n, 10)
        self.assertAlmostEqual(off, 0.05)
        self.assertAlmostEqual(dP, 0.005)
        off, n, dP = v.phase_offset(100.0 - 2.9, 100.0, 3.0)
        self.assertEqual(n, -1)
        self.assertAlmostEqual(off, 0.1)

    def test_radius(self):
        r, src = v.stellar_radius({"radius_flame": "1.2"})
        self.assertEqual((r, src), (1.2, "flame"))
        r, src = v.stellar_radius({"phot_g_mean_mag": "9.4", "parallax": "10.0"})
        self.assertEqual(src, "absG")
        self.assertAlmostEqual(r, 1.0)
        self.assertEqual(v.stellar_radius({})[1], "default")
        self.assertAlmostEqual(v.companion_radius_rj(0.01, 1.0), 0.9731)
        self.assertTrue(math.isnan(v.companion_radius_rj(-0.01, 1.0)))

    def test_flags(self):
        f, pl = v.vet_flags(0.01, 0.0001, 1.0, 0.5, 0.001, 1.0)
        self.assertEqual(f, [])
        self.assertTrue(pl)
        f, pl = v.vet_flags(0.01, 0.004, 9.0, 0.5, 0.001, 1.0)
        self.assertEqual(f, ["SECONDARY"])
        f, pl = v.vet_flags(0.01, 0.0005, 9.0, 0.5, 0.001, 1.0)   # small occultation: planet ok
        self.assertTrue(pl)
        f, pl = v.vet_flags(0.01, float("nan"), float("nan"), 4.0, 0.006, 2.5)
        self.assertEqual(f, ["ODD_EVEN", "MODULATED", "STELLAR_SIZE"])
        self.assertFalse(pl)

    def test_chunks(self):
        ids = [str(i) for i in range(50)]
        a = v.chunk_order(ids, 2, 0)
        b = v.chunk_order(ids, 2, 1)
        self.assertEqual(sorted(a + b), sorted(ids))
        self.assertEqual(len(set(a) & set(b)), 0)
        self.assertEqual(a, v.chunk_order(list(reversed(ids)), 2, 0))

    def test_garwood_wilson(self):
        lo, hi = v.garwood(0)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 3.689, places=2)
        lo, hi = v.garwood(10)
        self.assertAlmostEqual(lo, 4.795, places=2)
        self.assertAlmostEqual(hi, 18.39, places=1)
        lo, hi = v.wilson(8, 10)
        self.assertTrue(0.4 < lo < 0.5 and 0.9 < hi < 0.97)

    def test_adql(self):
        q = v.candidate_adql("gaiadr4", True)
        self.assertTrue(q.startswith("SELECT v.source_id,"))
        self.assertIn("gaiadr4.vari_planetary_transit", q)
        self.assertIn("radius_flame", q)
        self.assertNotIn("radius_flame", v.candidate_adql("gaiadr3", False))


def _rec(cat, sens, hit, c1=False, c2=False, plike="", status="OK"):
    return {"status": status, "category": cat, "in_rate_sample": str(sens), "star_hit": str(hit),
            "ctrl_0.8541_hit": str(c1), "ctrl_0.9137_hit": str(c2), "planet_like": plike,
            "alias_hit": "False", "source_id": "x"}


class TestGrade(unittest.TestCase):
    def test_grade_ok(self):
        recs = [_rec("KNOWN_PLANET", True, True) for _ in range(18)]
        recs += [_rec("KNOWN_PLANET", True, False) for _ in range(2)]
        recs += [_rec("NEW", True, True, plike="True") for _ in range(3)]
        recs += [_rec("NEW", True, True, plike="False") for _ in range(3)]
        recs += [_rec("NEW", True, False) for _ in range(14)]
        recs += [_rec("NEW", False, False)]
        recs += [_rec("NEW", False, False, status="NO_TESS")]
        recs[0]["ctrl_0.8541_hit"] = "True"
        g = v.grade(recs)
        self.assertEqual(g["G0"]["label_a"], "PIPELINE_OK")
        self.assertAlmostEqual(g["G0"]["recovery"], 0.9)
        self.assertEqual(g["n_rate_sample"], 40)
        self.assertAlmostEqual(g["control_rate"], 1 / 80.0)
        self.assertEqual(g["G0"]["label_b"], "CONTROLS_OK")
        self.assertEqual(g["G1"]["new_sensitive"], 20)
        self.assertEqual(g["G1"]["new_hits"], 6)
        self.assertAlmostEqual(g["G1"]["fraction_seen"], (6 - 20 / 80.0) / 20)
        self.assertEqual(g["G1"]["label"], "MIXED")
        self.assertTrue(g["G1"]["valid"])
        self.assertEqual(g["G2"]["n_planet_like"], 3)
        self.assertEqual(g["G3"]["n_eb_like"], 3)
        self.assertEqual(g["status_counts"]["NO_TESS"], 1)

    def test_grade_untestable_and_fail(self):
        recs = [_rec("KNOWN_PLANET", True, False) for _ in range(12)]
        recs += [_rec("NEW", True, False) for _ in range(5)]
        g = v.grade(recs)
        self.assertEqual(g["G0"]["label_a"], "PIPELINE_FAILS")
        self.assertEqual(g["G1"]["label"], "UNTESTABLE")
        self.assertFalse(g["G1"]["valid"])
        g = v.grade([])
        self.assertEqual(g["G0"]["label_a"], "UNTESTABLE")
        self.assertEqual(g["G0"]["label_b"], "UNTESTABLE")


if __name__ == "__main__":
    unittest.main()
