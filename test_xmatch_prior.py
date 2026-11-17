# SPDX-License-Identifier: Apache-2.0
"""Offline tests for xmatch_prior.py (gaia-orbit-transits 0.6.2; MV2 of Munim, Inc.,
made with AI agents). Every expected value is worked by hand in the comments."""
import csv
import json
import os
import shutil
import tempfile
import unittest

import xmatch_prior as xm

SID = "6360777231720947328"


class TestIds(unittest.TestCase):
    def test_gaia_ids_skip_float_decimals(self):
        # 0.18794660757309373 has 17 digits after the point: not an id.
        text = "id,x\n%s,0.18794660757309373\n" % SID
        self.assertEqual(xm.gaia_ids_in_text(text), {SID})

    def test_gaia_ids_reject_20_digit_runs(self):
        self.assertEqual(xm.gaia_ids_in_text("12345678901234567890"), set())

    def test_tic_ids(self):
        text = "TIC_ID,period\n398402989,58.7\n00018178958,64\n"
        self.assertEqual(xm.tic_ids_in_text(text), {"398402989", "18178958"})
        self.assertEqual(xm.tic_ids_in_text("see TIC 342194997."), {"342194997"})

    def test_rows_with_value(self):
        text = "a,b\n1,%s\n2,5\n3,%s.0\n" % (SID, SID)
        rows = xm.rows_with_value(text, SID)
        self.assertEqual([r["a"] for r in rows], ["1", "3"])

    def test_parse_csv(self):
        self.assertEqual(xm.parse_table(b"x,y\n1,2\n"), [{"x": "1", "y": "2"}])


class TestInclination(unittest.TestCase):
    def test_hand_cases(self):
        # a=1, i=60, w=W=0: A=1, B=F=0, G=cos60=0.5. u=0.625, v=0.5,
        # disc=0.5*sqrt(0.25*2.25)=0.375, a2=1 -> cos i=0.5 -> 60 deg.
        self.assertAlmostEqual(xm.inclination_deg(1, 0, 0, 0.5), 60.0, places=9)
        # edge-on, w=W=0: (1,0,0,0) -> u=0.5, v=0 -> 90 deg.
        self.assertAlmostEqual(xm.inclination_deg(1, 0, 0, 0), 90.0, places=9)
        # edge-on, w=0, W=pi/2: (0,1,0,0) -> disc=0.5, a2=1, v=0 -> 90 deg.
        self.assertAlmostEqual(xm.inclination_deg(0, 1, 0, 0), 90.0, places=9)
        # face-on: (1,0,0,1) -> u=1, v=1, disc=0 -> 0 deg.
        self.assertAlmostEqual(xm.inclination_deg(1, 0, 0, 1), 0.0, places=6)


class TestClasses(unittest.TestCase):
    def test_vsx(self):
        for t in ("EA", "EW/RS", "EB", "E", "EA+UV"):
            self.assertTrue(xm.is_eclipsing_vsx(t), t)
        for t in ("ELL", "ROT+ELL", "EP", "EXOR", "BY:", "", None):
            self.assertFalse(xm.is_eclipsing_vsx(t), t)

    def test_simbad(self):
        self.assertTrue(xm.is_eclipsing_otypes(["EB*", "*"]))
        self.assertFalse(xm.is_eclipsing_otypes(["*", "SB*"]))

    def test_grade_p3(self):
        self.assertEqual(xm.grade_p3([{"known_eb": True}, {"known_eb": True},
                                      {"known_eb": False}]), (2, 3, True))
        # exactly half is not "more than half"
        self.assertEqual(xm.grade_p3([{"known_eb": True}, {"known_eb": False}]),
                         (1, 2, False))
        self.assertEqual(xm.grade_p3([]), (0, 0, False))


FILES = {
    "pkg/track3_detail.csv": "source_id,period\n%s,58.7\n" % SID,
    "pkg/vetting/literature.txt": "TIC 398402989 was checked by hand.",
    "pkg/other.csv": "source_id\n1\n",
}


class TestPrior(unittest.TestCase):
    def test_lookup(self):
        in_sel, hits, rows = xm.prior_lookup(FILES, SID, "398402989")
        self.assertTrue(in_sel)
        self.assertEqual(hits, ["pkg/track3_detail.csv", "pkg/vetting/literature.txt"])
        self.assertIn("pkg/track3_detail.csv", rows)
        in_sel, hits, rows = xm.prior_lookup(FILES, "5840649029966569088", "342194997")
        self.assertFalse(in_sel)
        self.assertEqual(hits, [])


class TestMainOffline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.saved = (xm.load_zenodo, xm.query_gaia_orbits, xm.simbad)
        xm.load_zenodo = lambda d, log: (FILES, {"record": "test"})
        xm.query_gaia_orbits = lambda sids, log: [{
            "source_id": SID, "solution_type": "AstroSpectroSB1", "period": "58.73",
            "a_thiele_innes": "1", "b_thiele_innes": "0", "f_thiele_innes": "0",
            "g_thiele_innes": "0", "ra": "285.0", "dec": "-81.0"}]
        xm.simbad = lambda s, t, log: {"Gaia DR3 %s" % SID: {
            "main_id": "HD TEST", "otype": "EB*", "nbref": "3", "otypes": {"EB*", "*"}}}
        self.targets = os.path.join(self.tmp, "t.csv")
        with open(self.targets, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["source_id", "tic", "period_d", "vet", "gaia_eb"])
            w.writerow([SID, "398402989", "58.73", "eclipse (plot checked)", "False"])
            w.writerow(["5840649029966569088", "342194997", "550.75",
                        "eclipse (plot checked)", "False"])

    def tearDown(self):
        xm.load_zenodo, xm.query_gaia_orbits, xm.simbad = self.saved
        shutil.rmtree(self.tmp)

    def test_run(self):
        out = os.path.join(self.tmp, "out")
        xm.main(["--targets", self.targets, "--data-dir", os.path.join(self.tmp, "d"),
                 "--out-dir", out, "--no-vizier"])
        with open(os.path.join(out, "xmatch_summary.json")) as fh:
            s = json.load(fh)
        # one of two is a SIMBAD EB* -> 1/2 is not > 50% -> P3 fails
        self.assertEqual((s["P3_known_eb"], s["n_targets"], s["P3_pass"]), (1, 2, False))
        self.assertEqual(s["in_chopard_vilhem_selection"], 1)
        # the second star is in no source in this offline test
        self.assertEqual(s["new_vs_all_sources"], ["5840649029966569088"])
        with open(os.path.join(out, "xmatch.csv")) as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(rows[0]["inc_deg"], "90.00")
        self.assertEqual(rows[0]["simbad_main_id"], "HD TEST")


if __name__ == "__main__":
    unittest.main()
