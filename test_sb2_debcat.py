# Tests for sb2_debcat.py 0.2.0. MV2, Munim, Inc. Made with AI agents working in his name. Apache-2.0.
import math
import unittest

import sb2_debcat as sd


class TestParsers(unittest.TestCase):
    def test_parse_pm(self):
        self.assertEqual(sd.parse_pm("1.488 ± 0.007"), (1.488, 0.007))
        self.assertEqual(sd.parse_pm("2.0 +/- 0.1"), (2.0, 0.1))
        self.assertIsNone(sd.parse_pm("8.09"))

    def test_parse_pms_stacked(self):
        self.assertEqual(sd.parse_pms("1.1345 ± 0.0032 1.1241 ± 0.0045"),
                         [(1.1345, 0.0032), (1.1241, 0.0045)])
        self.assertEqual(sd.parse_pms("7.19 0.57"), [])

    def test_debcat_with_header(self):
        html = ("<table><tr><th>System</th><th>Period</th><th>Mass A</th><th>Mass B</th></tr>"
                "<tr><td>V570 Per</td><td>1.90</td><td>1.449 &plusmn; 0.006</td>"
                "<td>1.350 &plusmn; 0.006</td></tr>"
                "<tr><td>XY Foo*</td><td>3.5</td><td>bad</td><td>1.0 &plusmn; 0.1</td></tr></table>")
        rows = sd.parse_debcat(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "V570 Per")
        self.assertAlmostEqual(rows[0]["P"], 1.90)
        self.assertAlmostEqual(rows[0]["mA"], 1.449)
        self.assertAlmostEqual(rows[0]["emB"], 0.006)
        self.assertTrue(math.isnan(rows[0]["rA"]))

    def test_debcat_unclosed_cells_no_header(self):
        html = ("<TABLE><TR><TD>AI Phe<TD>24.59<TD>K0 IV<TD>1.1938 &pm; 0.0008<TD>1.2438 &pm; 0.0008"
                "<TD>1.835 &pm; 0.014<TD>2.912 &pm; 0.014</TABLE>")
        rows = sd.parse_debcat(html)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["mB"], 1.2438)
        self.assertAlmostEqual(rows[0]["rA"], 1.835)

    def test_debcat_stacked_cells(self):
        rows = sd.parse_debcat(sd.SNIP_STACKED)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["mA"], 1.1345)
        self.assertAlmostEqual(rows[0]["mB"], 1.1241)
        self.assertAlmostEqual(rows[0]["rB"], 1.0593)

    def test_debcat_row_per_star(self):
        rows = sd.parse_debcat(sd.SNIP_TWO_ROW)
        self.assertEqual([r["name"] for r in rows], ["AB Xyz"])
        self.assertEqual(rows[0]["pm_next"], [(1.2, 0.01), (1.3, 0.02)])

    def test_period_with_pm_is_not_a_system(self):
        self.assertIsNone(sd.parse_debcat_row(["K0 V", "1.2 ± 0.01", "1.3 ± 0.02", "1.4 ± 0.1"]))

    def test_debs_dat(self):
        dat, info = sd.parse_debs_dat(sd.SNIP_DAT)
        self.assertEqual(sorted(dat), ["abxyz", "kxcnc"])
        self.assertTrue(info["log_masses"])
        self.assertAlmostEqual(dat["kxcnc"]["m1"], 10 ** 0.0548)
        self.assertAlmostEqual(dat["kxcnc"]["P"], 31.22)

    def test_debs_dat_linear_masses(self):
        dat, info = sd.parse_debs_dat("#System P M1 M2\nAA_Bcd 2.0 1.5 1.2\nshort 1.0\n")
        self.assertFalse(info["log_masses"])
        self.assertAlmostEqual(dat["aabcd"]["m2"], 1.2)
        self.assertEqual(info["n_bad_width"], 1)

    def test_anchoring(self):
        dat, _ = sd.parse_debs_dat(sd.SNIP_DAT)
        kept, chk = sd.apply_anchors(sd.parse_debcat(sd.SNIP_STACKED) + sd.parse_debcat(sd.SNIP_TWO_ROW), dat)
        by = {r["name"]: r for r in kept}
        self.assertEqual(chk["n_anchored"], 2)
        self.assertEqual(chk["n_positional_agrees"], 1)
        self.assertAlmostEqual(by["AB Xyz"]["mB"], 1.2)
        self.assertAlmostEqual(by["AB Xyz"]["emB"], 0.01)
        self.assertEqual(by["KX Cnc"]["mass_src"], "ANCHORED")
        self.assertEqual(chk["label"], "ANCHOR_FAIL")     # fewer than 100 systems

    def test_anchor_twins(self):
        rec = {"pm_all": [(1.0, 0.01), (1.0, 0.02)], "pm_next": []}
        (a, ea), (b, eb) = sd.anchor_masses(rec, 1.0, 1.0)
        self.assertEqual((ea, eb), (0.01, 0.02))
        self.assertIsNone(sd.anchor_masses({"pm_all": [(1.0, 0.01)], "pm_next": []}, 1.0, 2.0))

    def test_norm_name(self):
        self.assertEqual(sd.norm_name("V570 Per"), sd.norm_name("V570_Per"))
        self.assertEqual(sd.norm_name("α CrB"), sd.norm_name("alf_CrB"))
        self.assertEqual(sd.norm_name("alpha CrB"), "alfcrb")

    def test_viz_tsv(self):
        txt = ("#RESOURCE=x\n#Table\tI/357/tbosb2\n\nrecno\tSource\tNSSmodel\tPer\tecc\tK1\te_K1\tK2\te_K2\n"
               "\t\t\td\t\tkm/s\tkm/s\tkm/s\tkm/s\n"
               "-----\t----\t---\t---\t---\t---\t---\t---\t---\n"
               "1\t6030061691987260672\tSB2\t6.591\t0.209\t56.3477\t1.76\t60.37\t1.76\n")
        rows = sd.parse_viz_tsv(txt)
        self.assertEqual(len(rows), 1)
        g = sd.gaia_record(rows[0], "I/357/tbosb2")
        self.assertEqual(g["source_id"], "6030061691987260672")
        self.assertAlmostEqual(g["K1"], 56.3477)
        self.assertEqual(g["model"], "SB2")
        with self.assertRaises(ValueError):
            sd.parse_viz_tsv("#INFO\tQUERY_STATUS=ERROR\n")

    def test_viz_circular_has_zero_ecc(self):
        g = sd.gaia_record({"Source": "1", "NSSmodel": "SB2C", "Per": "2", "K1": "50", "K2": "60"},
                           "I/357/tbosb2c")
        self.assertEqual(g["e"], 0.0)

    def test_tap_csv_and_record(self):
        h, rows = sd.parse_csv_text('"source_id","nss_solution_type","period","eccentricity",'
                                    '"semi_amplitude_primary","semi_amplitude_secondary"\n'
                                    '6030061691987260672,SB2,6.591,0.209,56.3477,60.37\n')
        self.assertIn("semi_amplitude_secondary", h)
        g = sd.tap_record(rows[0], "gaiadr3.nss_two_body_orbit")
        self.assertEqual(g["source_id"], "6030061691987260672")
        self.assertAlmostEqual(g["e"], 0.209)
        self.assertEqual(g["model"], "SB2")
        with self.assertRaises(ValueError):
            sd.parse_csv_text("<?xml version='1.0'?><VOTABLE>error</VOTABLE>")

    def test_neighbours(self):
        self.assertEqual(sd.neighbour_columns(["dr4_source_id", "dr3_source_id", "angular_distance"]),
                         ("dr3_source_id", "dr4_source_id", "angular_distance"))
        self.assertEqual(sd.neighbour_columns(["source_id", "dr3_source_id"])[1], "source_id")
        with self.assertRaises(sd.GateError):
            sd.neighbour_columns(["foo", "bar"])
        nb = sd.best_neighbours([{"a": "7", "b": "70", "d": ""}, {"a": "7", "b": "71", "d": "1.0"}],
                                "a", "b", "d")
        self.assertEqual(nb["7"]["id"], "71")

    def test_simbad_ascii(self):
        txt = ("C.D.S.  -  SIMBAD4 rel 1.8\n\nObject V* RZ Cha  ---  SB*  ---  OID=@3272872\n"
               "Identifiers (23):\n   TIC 394730113    HIP 52381    Gaia DR3 5198334162577657984   \n"
               "   Gaia DR2 5198334162577657984\n")
        gid, main = sd.parse_simbad_ascii(txt)
        self.assertEqual(gid, "5198334162577657984")
        self.assertEqual(main, "V* RZ Cha")
        self.assertEqual(sd.parse_simbad_ascii("!! Identifier not found"), (None, ""))

    def test_name_variants(self):
        self.assertIn("alf CrB", sd.name_variants("α CrB"))
        self.assertIn("alf CrB", sd.name_variants("alpha CrB"))
        self.assertIn("HD 123", sd.name_variants("HD 123 (Aa)"))


class TestPhysics(unittest.TestCase):
    def test_mass_constant(self):
        self.assertAlmostEqual(sd.ksum_from_masses(1.0, 365.25, 0.0), 29.785, places=2)

    def test_roundtrip_exact(self):
        m1, m2, P, e = 1.8, 1.2, 3.3, 0.1
        ks = sd.ksum_from_masses(m1 + m2, P, e)
        g = {"P": P, "e": e, "K1": ks * m2 / (m1 + m2), "eK1": 0.5,
             "K2": ks * m1 / (m1 + m2), "eK2": 0.5}
        deb = {"P": P, "mA": m2, "emA": 0.01, "mB": m1, "emB": 0.01}
        c = sd.compare(deb, g)
        self.assertEqual(c["pstat"], "PERIOD_OK")
        self.assertAlmostEqual(c["R"], 1.0, places=9)
        self.assertAlmostEqual(c["dq"], 0.0, places=12)
        self.assertAlmostEqual(c["R_heavy"], 1.0, places=9)
        self.assertAlmostEqual(c["R_light"], 1.0, places=9)
        self.assertFalse(c["impossible"])

    def test_inclination_lowers_R(self):
        ks = sd.ksum_from_masses(3.0, 2.0, 0.0, sin3i=0.9)
        g = {"P": 2.0, "e": 0.0, "K1": ks / 2, "eK1": 0.1, "K2": ks / 2, "eK2": 0.1}
        c = sd.compare({"P": 2.0, "mA": 1.5, "emA": 0.01, "mB": 1.5, "emB": 0.01}, g)
        self.assertAlmostEqual(c["R"], 0.9, places=9)

    def test_period_status(self):
        self.assertEqual(sd.period_status(2.001, 2.0), "PERIOD_OK")
        self.assertEqual(sd.period_status(4.0, 2.0), "PERIOD_ALIAS")
        self.assertEqual(sd.period_status(1.0, 2.0), "PERIOD_ALIAS")
        self.assertEqual(sd.period_status(2.7, 2.0), "PERIOD_BAD")
        self.assertEqual(sd.period_status(float("nan"), 2.0), "PERIOD_UNKNOWN")


class TestStats(unittest.TestCase):
    def test_median_and_robust_std(self):
        self.assertEqual(sd.median([3, 1, 2]), 2)
        self.assertEqual(sd.median([4, 1, 2, 3]), 2.5)
        self.assertAlmostEqual(sd.robust_std([-1, 0, 1]), 1.4826)

    def test_ranks_ties(self):
        self.assertEqual(sd.ranks([10, 20, 20, 30]), [1.0, 2.5, 2.5, 4.0])

    def test_spearman(self):
        rho, p, n = sd.spearman(list(range(30)), [x * x for x in range(30)], n_perm=200)
        self.assertAlmostEqual(rho, 1.0)
        self.assertLess(p, 0.01)
        self.assertEqual(n, 30)

    def test_boot_ci_contains_median(self):
        xs = [0.1 * i for i in range(50)]
        lo, hi = sd.boot_median_ci(xs, n=300)
        self.assertLessEqual(lo, sd.median(xs))
        self.assertGreaterEqual(hi, sd.median(xs))

    def test_grade_untestable(self):
        g = sd.grade([{"name": "a", "gaia_id": "1", "gaia_source_id": "1", "pstat": "PERIOD_OK",
                       "dq": 0.0, "R": 1.0}])
        self.assertEqual(g["Q1"]["label"], "UNTESTABLE")
        self.assertEqual(g["counts"]["n_sample"], 1)

    def test_self_test_passes(self):
        res = sd.self_test()
        self.assertTrue(res["pass"], res)


if __name__ == "__main__":
    unittest.main()
