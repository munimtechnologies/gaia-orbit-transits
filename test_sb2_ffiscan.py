# SPDX-License-Identifier: Apache-2.0
"""Unit tests for sb2_ffiscan (no network). MV2, Munim, Inc.; made with AI agents."""
import math
import unittest

import numpy as np

import sb2_ffiscan as F


class Geometry(unittest.TestCase):
    def test_circular_convention(self):
        c1, c2 = F.conjunction_phases(0.0, 0.0)
        self.assertAlmostEqual(c1, 0.25, places=9)
        self.assertAlmostEqual(c2, 0.75, places=9)

    def test_eccentric_values(self):
        c1, c2 = F.conjunction_phases(0.076, 342.95)
        self.assertAlmostEqual(c1, 0.2738, delta=0.002)
        self.assertAlmostEqual(c2, 0.8201, delta=0.002)

    def test_array_input(self):
        c1, c2 = F.conjunction_phases(np.array([0.0, 0.1]), np.array([0.0, 30.0]))
        self.assertEqual(c1.shape, (2,))
        self.assertAlmostEqual(float(c1[0]), 0.25, places=9)

    def test_wrap(self):
        self.assertAlmostEqual(float(F.wrap(0.9, 1.0)), -0.1, places=12)
        self.assertAlmostEqual(float(F.wrap(-0.6, 1.0)), 0.4, places=12)


class Predict(unittest.TestCase):
    def test_exact_orbit(self):
        orb = {"P": 3.0, "P_err": 0.0, "e": 0.2, "e_err": 0.0, "omega": 40.0, "omega_err": 0.0,
               "Tp": 11.0, "Tp_err": 0.0}
        c1, c2 = F.conjunction_phases(0.2, 40.0)
        T = 11.0 + F.GAIA_REF_BTJD + c2 * 3.0 + 500 * 3.0
        pr = F.predict_conj(orb, T)
        self.assertAlmostEqual(pr["oc_c2"], 0.0, places=6)
        self.assertAlmostEqual(pr["sd_c2"], 0.0, places=9)
        self.assertFalse(pr["circular"])
        self.assertAlmostEqual(pr["sep_mean"], (c2 - c1) % 1.0, places=9)

    def test_hd250735_circular(self):
        orb = {"P": 5.895935077280673, "P_err": 0.00018169096, "e": float("nan"),
               "omega": float("nan"), "Tp": -1.6427050598921045, "Tp_err": 0.010175885}
        pr = F.predict_conj(orb, 2475.950533)
        self.assertTrue(pr["circular"])
        z = min(abs(pr["oc_c1"]) / pr["sd_c1"], abs(pr["oc_c2"]) / pr["sd_c2"])
        self.assertLessEqual(z, 3.0)
        self.assertAlmostEqual(pr["sep_mean"], 0.5, places=9)


class Box(unittest.TestCase):
    def test_finds_dip(self):
        n = np.full(F.NB, 50.0)
        s = np.zeros(F.NB)
        s[100:104] = -3.0 * 50
        b = F.best_box(s, n)
        self.assertEqual(b["bin"], 100)
        self.assertEqual(b["w"], 4)
        self.assertAlmostEqual(b["snr"], 3.0 * math.sqrt(200), places=6)

    def test_wraps_around(self):
        n = np.full(F.NB, 50.0)
        s = np.zeros(F.NB)
        s[[198, 199, 0, 1]] = -2.0 * 50
        b = F.best_box(s, n)
        self.assertEqual(b["bin"], 198)
        self.assertEqual(b["w"], 4)

    def test_mask(self):
        n = np.full(F.NB, 50.0)
        s = np.zeros(F.NB)
        s[100:104] = -3.0 * 50
        s[10:12] = -2.0 * 50
        mask = np.zeros(F.NB, bool)
        mask[95:110] = True
        b = F.best_box(s, n, mask=mask)
        self.assertEqual(b["bin"], 10)
        self.assertEqual(b["w"], 2)

    def test_min_points(self):
        n = np.full(F.NB, 2.0)
        s = np.zeros(F.NB)
        s[50] = -5.0 * 2
        b = F.best_box(s, n, widths=(1,))
        self.assertIsNone(b)

    def test_scan_recovers_period(self):
        rng = np.random.default_rng(0)
        P = 2.5
        t = np.sort(rng.uniform(1000.0, 1300.0, 40000))
        z = rng.normal(0, 1, t.size)
        ph = np.mod((t - 1000.0) / P, 1.0)
        z[(ph > 0.40) & (ph < 0.42)] -= 4.0
        best, n = F.scan(t, z, P + 1e-5, 1e-4, 1000.0, 300.0)
        self.assertGreater(best["snr"], 30)
        self.assertLess(abs(best["P"] - P), 5e-4)
        phc = (best["bin"] + best["w"] / 2.0) / F.NB
        self.assertLess(abs(phc - 0.41), 0.02)


class Cleaning(unittest.TestCase):
    def test_harmonics_removed_dip_kept(self):
        P = 3.0
        t = np.arange(1500.0, 1526.0, 10.0 / 1440.0)
        dip = 0.02 * np.exp(-0.5 * ((F.wrap(t - 1500.7, P)) / 0.04) ** 2)
        r = 0.01 * np.sin(2 * math.pi * t / P) + 0.004 * np.cos(4 * math.pi * t / P) - dip
        res, sd = F.remove_harmonics(t, r, P)
        out = np.abs(F.wrap(t - 1500.7, P)) > 0.3
        self.assertLess(np.std(res[out]), 0.002)
        inn = np.abs(F.wrap(t - 1500.7, P)) < 0.01
        self.assertGreater(-np.mean(res[inn]), 0.015)


class Inputs(unittest.TestCase):
    CSV = ("source_id,G,P_gaia,P_gaia_err,tic,tce_class,vsx_eclipsing,toi,simbad_eb,simbad_main,gaia_eb,status\n"
           "1,8.0,2.0,1e-5,111,HALF,True,,False,V* A,False,OK\n"
           "2,9.5,3.0,1e-5,222,NONE,False,TOI 1.01,False,B,False,OK\n"
           "3,9.0,4.0,1e-5,400170926,NONE,False,,False,,False,OK\n"
           "4,7.0,5.0,1e-5,,NONE,False,,False,,False,OK\n"
           "5,7.5,6.0,1e-5,555,NONE,False,,False,,False,ERROR\n"
           "6,10.0,7.0,1e-5,666,NONE,False,,False,,True,OK\n")

    def test_select(self):
        import csv
        import io
        rows = list(csv.DictReader(io.StringIO(self.CSV)))
        st = F.select_stars(rows)
        self.assertEqual([s["source_id"] for s in st], ["1", "3", "2", "6"])
        roles = {s["source_id"]: s["role"] for s in st}
        self.assertEqual(roles, {"1": "control", "3": "target", "2": "toi", "6": "control"})
        self.assertEqual(st[1]["vetted"], "new_eb")
        self.assertEqual(st[1]["name"], "Gaia DR3 3")

    def test_anchor(self):
        orb = F.orbit_from_row({"period": "2.0000000001", "t_periastron": "1.0"})
        self.assertTrue(F.anchor_ok(orb, 2.0))
        orb = F.orbit_from_row({"period": "2.00001", "t_periastron": "1.0"})
        self.assertFalse(F.anchor_ok(orb, 2.0))
        orb = F.orbit_from_row({"period": "2.0", "t_periastron": ""})
        self.assertFalse(F.anchor_ok(orb, 2.0))

    def test_vsx_parsing(self):
        obj = {"VSXObjects": {"VSXObject": [{"Name": "V1 X", "VariabilityType": "EA/DM"},
                                            {"Name": "V2 X", "VariabilityType": "ROT"}]}}
        objs = F.vsx_objects(obj)
        self.assertEqual(len(objs), 2)
        self.assertTrue(any(F.is_eclipsing_type(o["VariabilityType"]) for o in objs))
        self.assertFalse(F.is_eclipsing_type("EP"))
        self.assertFalse(F.is_eclipsing_type("ELL"))
        self.assertTrue(F.is_eclipsing_type("EW/KW"))
        self.assertEqual(F.vsx_objects({"VSXObjects": {}}), [])

    def test_pick_sectors(self):
        entries = []
        for sec in range(1, 11):
            entries.append((sec, (2, 0.0), 2 * sec, "QLP", 1800.0))
        entries.append((5, (0, 0.0), 99, "SPOC", 120.0))
        picks = F.pick_sectors(entries, 6)
        self.assertEqual([p[0] for p in picks], [1, 3, 5, 6, 8, 10])
        self.assertEqual([p for p in picks if p[0] == 5][0][2], "SPOC")


class Grading(unittest.TestCase):
    def test_grade(self):
        recs = []
        for i in range(10):
            recs.append({"role": "control", "vetted": "", "n_sectors": 2, "name": "c%d" % i, "tic": i,
                         "label": "DETECTED" if i < 9 else "NOT_DETECTED",
                         "phase": "PHASE_MATCH" if i < 8 else "PHASE_MISMATCH", "circular": i % 2 == 0})
        recs.append({"role": "target", "vetted": "", "n_sectors": 1, "name": "t", "tic": 99, "G": 9.0,
                     "label": "DETECTED", "phase": "PHASE_MATCH"})
        recs.append({"role": "target", "vetted": "new_eb", "n_sectors": 1, "name": "n", "tic": 98,
                     "label": "DETECTED", "phase": "PHASE_MATCH"})
        g = F.grade(recs, False)
        self.assertEqual(g["F0"]["label"], "CONTROLS_OK")
        self.assertEqual(g["F1"]["label"], "GAIA_PHASES_OK")
        self.assertEqual(g["F2"]["n_candidates"], 1)
        self.assertEqual(g["F3"]["label"], "BOTH_RECOVERED")


if __name__ == "__main__":
    unittest.main()
