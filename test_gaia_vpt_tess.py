# SPDX-License-Identifier: Apache-2.0
"""Unit tests for gaia_vpt_tess (stdlib only). MV2 of Munim, Inc.; made with AI agents."""
import math
import unittest

import gaia_vpt_tess as v


class TestPure(unittest.TestCase):
    def test_version(self):
        self.assertEqual(v.VERSION, "0.1.1")

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
        q = v.rvs_adql("gaiadr3")
        self.assertTrue(q.startswith("SELECT v.source_id,"))
        for col in ("rv_chisq_pvalue", "rv_renormalised_gof", "rv_nb_transits",
                    "rv_amplitude_robust", "grvs_mag", "gaiadr3.vari_planetary_transit"):
            self.assertIn(col, q)

    def test_classify_rv(self):
        # values from Gaia DR3 (ESA TAP, 21 Nov 2026)
        wasp18 = {"rv_chisq_pvalue": "0.0", "rv_renormalised_gof": "11.086616",
                  "rv_nb_transits": "31"}
        hd189733 = {"rv_chisq_pvalue": "0.00487329", "rv_renormalised_gof": "1.7946414",
                    "rv_nb_transits": "37"}
        faint = {"rv_chisq_pvalue": "", "rv_renormalised_gof": "", "rv_nb_transits": "30"}
        few = {"rv_chisq_pvalue": "0.0", "rv_renormalised_gof": "9.0", "rv_nb_transits": "8"}
        self.assertEqual(v.classify_rv(wasp18), "RV_VARIABLE")
        self.assertEqual(v.classify_rv(hd189733), "RV_QUIET")
        self.assertEqual(v.classify_rv(faint), "RV_UNTESTED")
        self.assertEqual(v.classify_rv(few), "RV_UNTESTED")
        self.assertEqual(v.classify_rv({"rv_chisq_pvalue": "0.01", "rv_renormalised_gof": "4.0",
                                        "rv_nb_transits": "10"}), "RV_QUIET")
        self.assertEqual(v.classify_rv({"rv_chisq_pvalue": "0.01", "rv_renormalised_gof": "4.01",
                                        "rv_nb_transits": "10"}), "RV_VARIABLE")
        hot = dict(wasp18, rv_template_teff="8500.0")
        self.assertEqual(v.classify_rv(hot), "RV_UNTESTED")
        ok = dict(wasp18, rv_template_teff="6750.0")
        self.assertEqual(v.classify_rv(ok), "RV_VARIABLE")

    def test_merge_rv(self):
        recs = [{"source_id": "1"}, {"source_id": "2"}]
        rows = [{"source_id": "1", "rv_chisq_pvalue": "0.0", "rv_renormalised_gof": "8.6",
                 "rv_nb_transits": "13", "rv_amplitude_robust": "46.3", "grvs_mag": "11.5"}]
        v.merge_rv(recs, rows)
        self.assertEqual(recs[0]["rv_class"], "RV_VARIABLE")
        self.assertEqual(recs[0]["rv_amplitude_robust"], "46.3")
        self.assertEqual(recs[1]["rv_class"], "RV_NOT_SCREENED")


def _rec(cat, sens, hit, c1=False, c2=False, plike="", status="OK", rv=""):
    return {"status": status, "category": cat, "in_rate_sample": str(sens), "star_hit": str(hit),
            "ctrl_0.8541_hit": str(c1), "ctrl_0.9137_hit": str(c2), "planet_like": plike,
            "alias_hit": "False", "source_id": "x", "rv_class": rv}


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
        # amendment 1
        self.assertEqual(g["G0b_kp"]["trials"], 40)
        self.assertEqual(g["G0b_kp"]["hits"], 1)
        self.assertEqual(g["G0b_kp"]["label"], "CONTROLS_OK")
        self.assertAlmostEqual(g["G1b"]["fraction_seen"], (6 - 20 / 40.0) / 20)
        self.assertTrue(g["G1b"]["valid"])
        self.assertEqual(g["control_by_category"]["KNOWN_PLANET"]["hits"], 1)
        self.assertEqual(g["control_by_category"]["NEW"]["trials"], 40)
        self.assertEqual(g["G5"]["n_known_systems"], 20)
        self.assertEqual(g["G5"]["label"], "PERIODS_MOSTLY_RIGHT")
        self.assertNotIn("G2b", g)

    def test_noisy_controls_on_other_period_systems(self):
        # real signals at another period make the pooled controls noisy; G1b uses KP only
        recs = [_rec("KNOWN_PLANET", True, True) for _ in range(10)]
        recs += [_rec("KNOWN_SYSTEM_OTHER_P", True, False, c1=True, c2=True) for _ in range(30)]
        recs += [_rec("KNOWN_SYSTEM_OTHER_P", True, False) for _ in range(30)]
        recs += [_rec("NEW", True, True) for _ in range(4)]
        recs += [_rec("NEW", True, False) for _ in range(6)]
        g = v.grade(recs)
        self.assertEqual(g["G0"]["label_b"], "CONTROLS_NOISY")
        self.assertFalse(g["G1"]["valid"])
        self.assertEqual(g["G0b_kp"]["label"], "CONTROLS_OK")
        self.assertTrue(g["G1b"]["valid"])
        self.assertAlmostEqual(g["G1b"]["fraction_seen"], 0.4)
        self.assertEqual(g["G1b"]["label"], "MIXED")
        self.assertTrue(g["G1b"]["fraction_seen_conservative"] < 0.4)
        self.assertEqual(g["G5"]["n_known_systems"], 70)
        self.assertAlmostEqual(g["G5"]["fraction_match"], 10 / 70.0)
        self.assertEqual(g["G5"]["label"], "PERIODS_MOSTLY_WRONG")

    def test_rvs_block(self):
        recs = [_rec("KNOWN_PLANET", True, True, rv="RV_QUIET") for _ in range(10)]
        recs += [_rec("NEW", True, True, plike="True", rv="RV_VARIABLE")]
        recs += [_rec("NEW", True, True, plike="True", rv="RV_UNTESTED")]
        g = v.grade(recs)
        self.assertEqual(g["G2b"]["n_planet_like"], 2)
        self.assertEqual(g["G2b"]["n_rv_variable"], 1)
        self.assertEqual(len(g["G2b"]["survivors"]), 1)
        self.assertEqual(g["RVS"]["by_category"]["NEW"]["RV_VARIABLE"], 1)

    def test_grade_untestable_and_fail(self):
        recs = [_rec("KNOWN_PLANET", True, False) for _ in range(12)]
        recs += [_rec("NEW", True, False) for _ in range(5)]
        g = v.grade(recs)
        self.assertEqual(g["G0"]["label_a"], "PIPELINE_FAILS")
        self.assertEqual(g["G1"]["label"], "UNTESTABLE")
        self.assertFalse(g["G1"]["valid"])
        self.assertFalse(g["G1b"]["valid"])
        g = v.grade([])
        self.assertEqual(g["G0"]["label_a"], "UNTESTABLE")
        self.assertEqual(g["G0"]["label_b"], "UNTESTABLE")
        self.assertEqual(g["G5"]["label"], "UNTESTABLE")


if __name__ == "__main__":
    unittest.main()
