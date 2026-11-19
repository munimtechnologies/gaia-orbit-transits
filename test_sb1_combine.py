# SPDX-License-Identifier: Apache-2.0
"""Tests for sb1_combine 0.1.0 (standard library only). MV2 of Munim, Inc.; made with AI agents."""
import json
import math
import os
import tempfile
import unittest

import sb1_combine as sc

HERE = os.path.dirname(os.path.abspath(__file__))


def row(sid, p=0.2, s=1.0, hit=False, cls="", m2="BD", P=3.0, m1=1.0, absg=4.0, bprp=0.8,
        r1=1.0, ctrl=("False", "False"), ctrl_cls=("", ""), status="OK", control="", toi="",
        v1=None, m1_src="flame"):
    return {"source_id": str(sid), "p_transit": str(p), "sensitivity": str(s),
            "star_hit": str(hit), "star_hit_v1": str(hit if v1 is None else v1),
            "hit_class": cls, "m2_class": m2, "P": str(P), "m1": str(m1), "abs_g": str(absg),
            "bp_rp": str(bprp), "r1": str(r1), "m1_src": m1_src,
            "ctrl_0.8541_hit": ctrl[0], "ctrl_0.9137_hit": ctrl[1],
            "ctrl_0.8541_class": ctrl_cls[0], "ctrl_0.9137_class": ctrl_cls[1],
            "status": status, "control": control, "toi": toi, "tic": "1", "phase_label": "UNTIMED"}


class TestGarwood(unittest.TestCase):
    def test_known_values(self):
        self.assertAlmostEqual(sc.garwood(0)[1], 3.689, places=3)
        lo, hi = sc.garwood(2)
        self.assertAlmostEqual(lo, 0.2422, places=3)
        self.assertAlmostEqual(hi, 7.2247, places=3)
        lo, hi = sc.garwood(3)
        self.assertAlmostEqual(lo, 0.6187, places=3)
        self.assertAlmostEqual(hi, 8.7673, places=3)
        lo, hi = sc.garwood(9)
        self.assertAlmostEqual(lo, 4.1154, places=3)
        self.assertAlmostEqual(hi, 17.0848, places=3)


class TestRadiusFlag(unittest.TestCase):
    def test_clamped_giant(self):
        # the k7 leak: M_G -3.0, BP-RP 4.6, r1 from the clamped table
        self.assertEqual(sc.radius_flag(row(1, absg=-3.0, bprp=4.6, r1=1.9, m1_src="absG")), "clamped")

    def test_clamped_blue(self):
        self.assertEqual(sc.radius_flag(row(1, absg=0.2, bprp=0.1, r1=1.9)), "clamped")

    def test_bright_with_gaia_radius_kept(self):
        self.assertEqual(sc.radius_flag(row(1, absg=0.2, bprp=0.1, r1=2.31)), "")

    def test_red_giant_cmd(self):
        # table radius at M_G 1.0 is 1.75 R_sun
        self.assertAlmostEqual(sc.interp(1.0, sc._MG, sc._RAD), 1.75)
        self.assertEqual(sc.radius_flag(row(1, absg=1.0, bprp=1.3, r1=1.75)), "giant_cmd")
        # same star with a Gaia radius is kept
        self.assertEqual(sc.radius_flag(row(1, absg=1.0, bprp=1.3, r1=1.6)), "")
        # blue star on the table, not clamped: kept
        self.assertEqual(sc.radius_flag(row(1, absg=1.0, bprp=0.3, r1=1.75)), "")

    def test_subgiant_with_flame_radius_kept(self):
        # TOI-1251-like: FLAME radius 1.51 R_sun
        self.assertEqual(sc.radius_flag(row(1, absg=3.3, bprp=1.05, r1=1.5118316)), "")

    def test_dwarfs_kept(self):
        self.assertEqual(sc.radius_flag(row(1, absg=3.017, bprp=0.664, r1=1.2465)), "")  # TIC 324597856
        self.assertEqual(sc.radius_flag(row(1, absg=7.0, bprp=2.0, r1=0.6)), "")         # red dwarf
        self.assertEqual(sc.radius_flag(row(1, absg=4.27, bprp=0.79, r1=1.199)), "")     # TOI-5427

    def test_no_distance(self):
        self.assertEqual(sc.radius_flag(row(1, absg="nan", bprp=0.8, r1=1.0)), "no_distance")
        self.assertEqual(sc.radius_flag(row(1, absg="nan", bprp=0.8, r1=1.31)), "")


class TestRates(unittest.TestCase):
    def setUp(self):
        self.rows = [
            row(1, p=0.2, s=1.0, hit=True, cls="SUBSTELLAR_SIZE", m2="VLMS", P=2.0),
            row(2, p=0.1, s=0.5, ctrl=("True", "False"), m2="BD", P=6.0),
            row(3, p=0.3, s=0.75, m2="BD", P=3.0, v1=True),
            row(4, p=0.5, s=0.4, hit=True, cls="SUBSTELLAR_SIZE"),          # sensitivity < 0.5
            row(5, p=0.5, s=1.0, hit=True, control="WASP-18 b"),            # control star
            row(6, p=0.5, s=1.0, status="NO_TESS"),
        ]

    def test_rate_summary(self):
        s = sc.rate_summary(self.rows)
        self.assertEqual(s["n_rate_sample"], 3)
        self.assertEqual(s["n_hit"], 1)
        self.assertEqual(s["n_hit_substellar_size"], 1)
        self.assertAlmostEqual(s["n_control_hits_expected"], 0.5)
        self.assertAlmostEqual(s["expected_if_all_real"], 0.2 + 0.05 + 0.225)
        self.assertEqual(s["n_hit_v1_rule"], 2)
        E = 0.475
        self.assertAlmostEqual(s["rho_all"]["rho"], (1 - 0.5) / E)
        self.assertAlmostEqual(s["rho_substellar_size"]["rho"], 1 / E)
        self.assertAlmostEqual(s["rho_substellar_size"]["ci95"][1], sc.garwood(1)[1] / E)

    def test_merge_dedupes(self):
        rows, dups = sc.merge([("a", self.rows), ("b", self.rows)])
        self.assertEqual(dups, 3)
        self.assertEqual(sc.rate_summary(rows)["n_rate_sample"], 3)

    def test_run_and_amendment(self):
        giant = row(7, p=0.3, s=1.0, absg=-2.0, bprp=2.5, r1=1.9, m1=2.2, m1_src="absG")
        res = sc.run([("k0", self.rows + [giant], {"eligible": 6434})], ["k1"])
        self.assertEqual(res["primary"]["summary"]["n_rate_sample"], 4)
        self.assertEqual(res["amendment1"]["summary"]["n_rate_sample"], 3)
        self.assertEqual(res["amendment1"]["removed_by_reason"], {"clamped": 1})
        self.assertEqual(res["primary"]["grades"]["R0"]["pass"], True)
        self.assertEqual(res["primary"]["grades"]["C1"]["pass"], None)
        self.assertEqual(len(res["primary"]["grades"]["D1"]["value"]), 1)
        txt = sc.report(res)
        self.assertIn("amendment 1", txt)
        json.dumps(res)

    def test_main_with_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            cdir = os.path.join(d, "k3")
            os.makedirs(cdir)
            keys = list(self.rows[0].keys())
            with open(os.path.join(cdir, "sb1_stars.csv"), "w", newline="") as fh:
                fh.write(",".join(keys) + "\n")
                for r in self.rows:
                    fh.write(",".join('"%s"' % r[k] if "," in r[k] or " " in r[k] else r[k] for k in keys) + "\n")
            out = os.path.join(d, "out")
            self.assertEqual(sc.main(["--chunk-dir", cdir, "--out-dir", out]), 0)
            with open(os.path.join(out, "combined_summary.json")) as fh:
                res = json.load(fh)
            self.assertEqual(res["chunks_used"], ["k3"])
            self.assertEqual(res["primary"]["summary"]["n_rate_sample"], 3)

    def test_parse_chunks(self):
        self.assertEqual(sc.parse_chunks("0-2,5"), [0, 1, 2, 5])


class TestReproducesJobOutput(unittest.TestCase):
    """If chunk k0's published output is next to this file, the re-implementation must
    reproduce the job's own summary exactly."""

    def test_k0(self):
        p = os.path.join(HERE, "data", "sb1rob-v1", "k0", "sb1_stars.csv")
        if not os.path.exists(p):
            self.skipTest("k0 data not present")
        with open(p, newline="") as fh:
            rows = sc.read_csv_text(fh.read())
        s = sc.rate_summary(rows)
        self.assertEqual(s["n_rate_sample"], 501)
        self.assertEqual(s["n_hit"], 7)
        self.assertEqual(s["n_hit_substellar_size"], 1)
        self.assertAlmostEqual(s["n_control_hits_expected"], 1.5)
        self.assertTrue(math.isclose(s["expected_if_all_real"], 87.83492528982423, rel_tol=1e-9))
        self.assertEqual(s["n_hit_v1_rule"], 46)

    def test_k7(self):
        p = os.path.join(HERE, "data", "sb1rob-v1", "k7", "sb1_stars.csv")
        if not os.path.exists(p):
            self.skipTest("k7 data not present")
        with open(p, newline="") as fh:
            rows = sc.read_csv_text(fh.read())
        s = sc.rate_summary(rows)
        self.assertEqual(s["n_rate_sample"], 443)
        self.assertEqual(s["n_hit"], 2)
        self.assertTrue(math.isclose(s["expected_if_all_real"], 82.14822230054666, rel_tol=1e-9))


if __name__ == "__main__":
    unittest.main()
