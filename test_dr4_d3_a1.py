# SPDX-License-Identifier: Apache-2.0
"""Stdlib tests for dr4_d3_a1.py (MV2 of Munim, Inc.; made with AI agents)."""
import csv
import json
import os
import shutil
import tempfile
import unittest

import dr4_d3_a1 as A
import sb1_combine as sc

# 40 stars, every one in the rate sample with p_transit 0.25 and sensitivity 1 (E = 0.25 each).
# Substellar-size hits: 0-5 (and 35). CONFIRMED in DR4: 0-9.
# Radius flags: 9 giant_cmd (table radius at M_G 2.0, BP-RP 1.2); 30-37 and 39 clamped
# (M_G 0.2, r1 1.9); 38 no_distance (no M_G, r1 1.0). All others have a Gaia radius.
FIELDS = ["source_id", "status", "control", "sensitivity", "p_transit", "star_hit",
          "hit_class", "abs_g", "bp_rp", "r1", "m2_class", "P", "m1", "toi", "star_hit_v1"]


def star(i):
    r = {"source_id": str(1000 + i), "status": "OK", "control": "", "sensitivity": "1.0",
         "p_transit": "0.25", "star_hit": "True" if (i < 6 or i == 35) else "False",
         "hit_class": "SUBSTELLAR_SIZE" if (i < 6 or i == 35) else "",
         "abs_g": "4.0", "bp_rp": "0.7", "r1": "1.05", "m2_class": "BD", "P": "3.0",
         "m1": "1.0", "toi": "", "star_hit_v1": "False"}
    if i == 9:
        r.update(abs_g="2.0", bp_rp="1.2", r1=repr(sc.interp(2.0, sc._MG, sc._RAD)))
    if 30 <= i <= 37 or i == 39:
        r.update(abs_g="0.2", bp_rp="1.5", r1="1.9")
    if i == 38:
        r.update(abs_g="", bp_rp="", r1="1.0")
    return r


ROWS = [star(i) for i in range(40)]
CONTROL = dict(star(0), source_id="77", control="WASP-18 b", star_hit="True")
RECS = [{"source_id": str(1000 + i), "label": "CONFIRMED" if i < 10 else "CHANGED"}
        for i in range(40)]


class Rule(unittest.TestCase):
    def test_flags(self):
        self.assertEqual(sc.radius_flag(ROWS[9]), "giant_cmd")
        self.assertEqual(sc.radius_flag(ROWS[31]), "clamped")
        self.assertEqual(sc.radius_flag(ROWS[38]), "no_distance")
        self.assertEqual(sc.radius_flag(ROWS[0]), "")

    def test_drop_flagged(self):
        kept, reasons = A.drop_flagged(ROWS + [ROWS[31]])        # duplicate counted once
        self.assertEqual(len(kept), 29)
        self.assertEqual(reasons, {"giant_cmd": 1, "clamped": 9, "no_distance": 1})

    def test_rate_adapter_matches_combine(self):
        s = sc.rate_summary(ROWS)
        f = A.rate_adapter(ROWS)
        self.assertEqual(f["n_rate_sample"], 40)
        self.assertAlmostEqual(f["expected_if_all_real"], 10.0)
        self.assertEqual(f["rho_substellar_size"], s["rho_substellar_size"]["rho"])
        self.assertEqual(f["rho_substellar_size_ci95"], s["rho_substellar_size"]["ci95"])
        self.assertAlmostEqual(f["rho_substellar_size"], 0.7)


class Grade(unittest.TestCase):
    def test_grade_numbers(self):
        res = A.grade(RECS, ROWS + [CONTROL], 0.05, 0.04)
        d3, raw = res["D3_A1"], res["D3_without_radius_rule"]
        # A1: conf = 0-8 (9 stars, E 2.25, 6 hits); all = 29 stars (E 7.25, 6 hits)
        self.assertEqual(d3["n_rate_conf"], 9)
        self.assertEqual(d3["n_rate_all"], 29)
        self.assertAlmostEqual(d3["rho_conf"], 6 / 2.25)
        self.assertAlmostEqual(d3["rho_all"], 6 / 7.25)
        self.assertEqual(d3["rho_dr3"], 0.05)
        self.assertEqual(d3["n_removed"], 11)
        self.assertTrue(d3["pass"])
        # without the rule: conf = 0-9 (E 2.5), all = 40 stars (E 10, 7 hits), control dropped
        self.assertEqual(raw["n_rate_conf"], 10)
        self.assertEqual(raw["n_rate_all"], 40)
        self.assertAlmostEqual(raw["rho_conf"], 6 / 2.5)
        self.assertAlmostEqual(raw["rho_all"], 0.7)
        self.assertEqual(raw["rho_dr3"], 0.04)
        self.assertTrue(res["agree"])

    def test_rule_can_flip_the_grade(self):
        # rho_DR3 just above the A1 lower bound but below the unflagged one
        lo_a1 = A.grade(RECS, ROWS, 0.0)["D3_A1"]["rho_conf_ci95"][0]
        lo_raw = A.grade(RECS, ROWS, 0.0)["D3_without_radius_rule"]["rho_conf_ci95"][0]
        self.assertGreater(lo_a1, lo_raw)          # E_conf shrinks, so the bound rises
        mid = 0.5 * (lo_a1 + lo_raw)
        res = A.grade(RECS, ROWS, mid, mid)
        self.assertTrue(res["D3_A1"]["pass"])
        self.assertFalse(res["D3_without_radius_rule"]["pass"])
        self.assertFalse(res["agree"])

    def test_rho_from_combined(self):
        comb = {"primary": {"summary": {"rho_substellar_size": {"rho": 0.021}}},
                "amendment1": {"summary": {"rho_substellar_size": {"rho": 0.026}}}}
        self.assertEqual(A.rho_from_combined(comb), (0.026, 0.021))
        with self.assertRaises(KeyError):
            A.rho_from_combined({"primary": {}})


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_csv(self, path, rows, fields):
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    def test_end_to_end(self):
        for name, part in (("k0", ROWS[:20]), ("k1", ROWS[20:] + [CONTROL])):
            d = os.path.join(self.tmp, name)
            os.makedirs(d)
            self._write_csv(os.path.join(d, "sb1_stars.csv"), part, FIELDS)
        rec = os.path.join(self.tmp, "recs.csv")
        self._write_csv(rec, RECS, ["source_id", "label"])
        comb = os.path.join(self.tmp, "combined_summary.json")
        with open(comb, "w") as fh:
            json.dump({"primary": {"summary": {"rho_substellar_size": {"rho": 0.04}}},
                       "amendment1": {"summary": {"rho_substellar_size": {"rho": 0.05}}}}, fh)
        summ = os.path.join(self.tmp, "reality.json")
        with open(summ, "w") as fh:
            json.dump({"grades": {"D1": {"pass": True}}}, fh)
        out = os.path.join(self.tmp, "out")
        rc = A.main(["--records", rec, "--combined", comb, "--chunk-dir",
                     os.path.join(self.tmp, "k0"), "--chunk-dir", os.path.join(self.tmp, "k1"),
                     "--reality-summary", summ, "--out-dir", out])
        self.assertEqual(rc, 0)
        with open(os.path.join(out, "d3_a1_grade.json")) as fh:
            res = json.load(fh)
        self.assertEqual(res["chunks_used"], ["k0", "k1"])
        self.assertEqual(res["rho_dr3_a1"], 0.05)
        self.assertEqual(res["D3_A1"]["n_rate_all"], 29)
        self.assertTrue(res["D3_A1"]["pass"])
        self.assertIn("(S)", res["reading"])

    def test_bad_combined(self):
        rec = os.path.join(self.tmp, "recs.csv")
        self._write_csv(rec, RECS, ["source_id", "label"])
        comb = os.path.join(self.tmp, "c.json")
        with open(comb, "w") as fh:
            json.dump({"primary": {}}, fh)
        self.assertEqual(A.main(["--records", rec, "--combined", comb, "--out-dir", self.tmp]), 4)

    def test_no_chunks(self):
        rec = os.path.join(self.tmp, "recs.csv")
        self._write_csv(rec, RECS, ["source_id", "label"])
        comb = os.path.join(self.tmp, "c.json")
        with open(comb, "w") as fh:
            json.dump({"primary": {"summary": {"rho_substellar_size": {"rho": 0.04}}},
                       "amendment1": {"summary": {"rho_substellar_size": {"rho": 0.05}}}}, fh)
        self.assertEqual(A.main(["--records", rec, "--combined", comb, "--chunk-dir",
                                 os.path.join(self.tmp, "nope"), "--out-dir", self.tmp]), 3)


if __name__ == "__main__":
    unittest.main()
