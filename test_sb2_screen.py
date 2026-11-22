# SPDX-License-Identifier: Apache-2.0
"""Tests for sb2_screen 0.1.0 (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents).
Stdlib only, no network."""
import math
import unittest

import sb2_screen as s


def row(sid, P, k1, k2, m1, e=""):
    return {"source_id": sid, "period": str(P), "semi_amplitude_primary": str(k1),
            "semi_amplitude_secondary": str(k2), "m1": str(m1), "eccentricity": e}


class TestMass(unittest.TestCase):
    def test_tic400170926(self):
        # pilot row 17: Gaia DR3 3450611154067089408, circular (no eccentricity)
        ms = s.m1sin3i(72.62443658950218, 78.94342367194483, 5.895935077280673, float("nan"))
        self.assertAlmostEqual(ms, 1.108, places=3)
        self.assertAlmostEqual(ms / 1.0540308, 1.0510691057210093, places=3)

    def test_eccentricity_lowers_mass(self):
        self.assertLess(s.m1sin3i(100, 100, 3, 0.3), s.m1sin3i(100, 100, 3, 0.0))

    def test_select(self):
        rows = [row("1", 5.895935077280673, 72.62443658950218, 78.94342367194483, 1.0540308),
                row("1", 5.895935077280673, 72.62443658950218, 78.94342367194483, 1.0540308),
                row("2", 5.895935077280673, 72.62443658950218, 78.94342367194483, 2.0),
                row("3", 9.0, 72.6, 78.9, 1.05),
                row("4", 2.0, "", 78.9, 1.05)]
        sel = s.select_rows(rows)
        self.assertEqual([r["source_id"] for r in sel], ["1"])
        self.assertAlmostEqual(sel[0]["s3_ratio"], 1.0511, places=3)


class TestParsers(unittest.TestCase):
    def test_tic(self):
        self.assertEqual(s.parse_tic('{"status": "OK", "TIC": "163346842", "GAIA": "1"}'),
                         "163346842")
        self.assertIsNone(s.parse_tic('{"status": "ERROR", "message": "No object found."}'))

    def test_tce_list(self):
        txt = '{"TCE":["s0002-s0072:TCE_1","s0043-s0043:TCE_1","s0002-s0072:TCE_2"]}'
        self.assertEqual(s.parse_tce_list(txt),
                         [("s0002-s0072", 1), ("s0043-s0043", 1), ("s0002-s0072", 2)])
        self.assertEqual(s.parse_tce_list('{"TCE":[]}'), [])

    def test_tce_info(self):
        d = s.parse_tce_info({"DV Data Header": {"TPERIOD": 2.947880760006525,
                                                 "TDEPTH": 61063.3, "TSNR": 1296.615,
                                                 "TDUR": 3.1749, "TEPOCH": 2475.95}})
        self.assertAlmostEqual(d["period"], 2.94788076, places=6)
        self.assertEqual(d["snr"], 1296.615)
        self.assertTrue(math.isnan(s.parse_tce_info({})["period"]))

    def test_villanova(self):
        self.assertFalse(s.villanova_status("<h1>TIC 400170926</h1> No associated EB entries found."))
        self.assertTrue(s.villanova_status("<tr><td>In catalog?</td><td>Is this signal in the "
                                           "EB catalog?</td><td>True</td></tr>"))
        self.assertIsNone(s.villanova_status("<html>something else</html>"))
        self.assertIsNone(s.villanova_status(""))

    def test_vsx(self):
        one = {"VSXObjects": {"VSXObject": {"Name": "X", "VariabilityType": "EP"}}}
        self.assertEqual(len(s.vsx_objects(one)), 1)
        many = {"VSXObjects": {"VSXObject": [{"Name": "A", "VariabilityType": "EA/RS:"},
                                             {"Name": "B", "VariabilityType": "ROT"}]}}
        self.assertEqual([o["Name"] for o in s.vsx_objects(many)], ["A", "B"])
        self.assertEqual(s.vsx_objects({"VSXObjects": {}}), [])
        self.assertEqual(s.vsx_objects({"VSXObjects": []}), [])
        for vt, ecl in (("EA", True), ("EA/RS:", True), ("EW", True), ("ECL", True),
                        ("EP", False), ("ELL", False), ("ROT", False), ("", False),
                        ("EB+ROT", True)):
            self.assertEqual(s.is_eclipsing_type(vt), ecl, vt)

    def test_simbad(self):
        txt = ("C.D.S.  -  SIMBAD4\n\nObject HD 250735  ---  SB*  ---  OID=@123   (@@1,0)\n"
               "Coordinates(ICRS,ep=J2000,eq=2000): 06 03 39.9 +32 20 15.9\n")
        self.assertEqual(s.simbad_flags(txt), (False, "HD 250735"))
        self.assertEqual(s.simbad_flags(txt.replace("SB*", "EB*"))[0], True)
        self.assertEqual(s.simbad_flags(""), (None, ""))


class TestClassify(unittest.TestCase):
    P = 5.895935077280673

    def test_match(self):
        f, dev = s.match_factor(2.947880760006525, self.P)
        self.assertEqual(f, 0.5)
        self.assertLess(abs(dev), 1e-4)
        f, dev = s.match_factor(self.P * 1.003, self.P)
        self.assertEqual(f, 1.0)
        f, dev = s.match_factor(self.P * 0.33, self.P)
        self.assertIsNone(f)

    def test_classes(self):
        half = {"id": "a", "period": self.P / 2, "depth_ppm": 6e4, "snr": 500.0, "dur_h": 3.0}
        full = {"id": "b", "period": self.P, "depth_ppm": 1e3, "snr": 900.0, "dur_h": 3.0}
        other = {"id": "c", "period": 25.48, "depth_ppm": 1e3, "snr": 9.6, "dur_h": 2.0}
        weak = {"id": "d", "period": self.P / 2, "depth_ppm": 1e3, "snr": 5.0, "dur_h": 2.0}
        nosnr = {"id": "e", "period": self.P / 2 * 1.001, "depth_ppm": 3e5,
                 "snr": float("nan"), "dur_h": 2.0}
        self.assertEqual(s.classify_tces([full, half, other], self.P)[0], "HALF")
        self.assertEqual(s.classify_tces([full, half, other], self.P)[1]["id"], "a")
        self.assertEqual(s.classify_tces([full, other], self.P)[0], "FULL")
        self.assertEqual(s.classify_tces([other], self.P)[0], "OTHER")
        self.assertEqual(s.classify_tces([weak], self.P)[0], "NONE")
        self.assertEqual(s.classify_tces([], self.P)[0], "NONE")
        self.assertEqual(s.classify_tces([nosnr, other], self.P)[0], "HALF")


def rec(sid, cls, pilot=False, **kw):
    r = {k: "" for k in s.KEYS}
    r.update({"source_id": sid, "status": "OK", "tce_class": cls, "in_pilot": pilot})
    r.update(kw)
    return r


class TestGrade(unittest.TestCase):
    def test_new(self):
        self.assertTrue(s.is_new(rec("1", "HALF", vsx_eclipsing=False, villanova=False)))
        self.assertTrue(s.is_new(rec("1", "FULL", vsx_eclipsing=None, villanova=None)))
        self.assertFalse(s.is_new(rec("1", "HALF", vsx_eclipsing=True)))
        self.assertFalse(s.is_new(rec("1", "HALF", villanova=True)))
        self.assertFalse(s.is_new(rec("1", "HALF", toi="631.01")))
        self.assertFalse(s.is_new(rec("1", "HALF", gaia_eb=True)))
        self.assertFalse(s.is_new(rec("1", "HALF", gaia_class="ECL")))
        self.assertFalse(s.is_new(rec("1", "HALF", simbad_eb=True)))
        self.assertFalse(s.is_new(rec("1", "OTHER")))
        self.assertFalse(s.is_new(rec("1", "NONE")))

    def test_grade(self):
        recs = [rec(str(i), "HALF", vsx_eclipsing=True) for i in range(8)]
        recs += [rec("10", "HALF", pilot=True, vsx_eclipsing=False),
                 rec("11", "HALF", vsx_eclipsing=False, villanova=False),
                 rec("12", "FULL", vsx_eclipsing=False),
                 rec("13", "OTHER"), rec("14", "NONE")]
        recs.append(dict(rec("15", ""), status="NO_TIC"))
        g = s.grade(recs, 184, 20)
        self.assertEqual(g["S0"]["label"], "REPLICATES")
        self.assertEqual(g["S1"]["n_with_tce"], 12)
        self.assertEqual(g["S1"]["n_half"], 10)
        self.assertEqual(g["S1"]["label"], "HALF_DOMINANT")
        self.assertEqual(g["S2"]["n_new"], 3)
        self.assertEqual(g["S2"]["n_new_excl_pilot"], 2)
        self.assertEqual(g["S2"]["label_ge3"], "NO")
        self.assertEqual(g["S2"]["label_ge1"], "YES")
        self.assertEqual(g["S3"]["label"], "CONTROLS_OK")
        self.assertEqual(g["counts"]["no_tic"], 1)
        self.assertEqual(s.grade(recs, 183, 20)["S0"]["label"], "DIFFERS")
        few = s.grade(recs[:5], 184, 20)
        self.assertEqual(few["S1"]["label"], "UNTESTABLE")

    def test_wilson(self):
        lo, hi = s.wilson(7, 7)
        self.assertGreater(lo, 0.6)
        self.assertAlmostEqual(hi, 1.0, places=9)


if __name__ == "__main__":
    unittest.main()
