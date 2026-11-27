# SPDX-License-Identifier: Apache-2.0
"""Tests for sb2_phase_grade (MV2, Munim, Inc.; made with AI agents). Expected numbers were computed
by hand on 27 Nov 2026 from Gaia DR3 orbits (AIP TAP) and sb2-ffiscan-v1 dip times, before this code ran.

27 Nov 2026 (job sb2-phase-grade-v3): job v2 failed in test_regrade_and_frozen_grade because these
hand-made fixture records lacked the "tic" key that the frozen sb2_ffiscan 0.1.0 grade() reads for every
candidate (every real v1 record has it: v1's own grade() ran on them). The fixtures now carry "tic";
no code and no expected value changed. TIC 243126121 is the TESS id of 2825104215999846144; the other
fixture tic values are placeholders, since grade() only copies them into its output."""
import unittest

import sb2_ffiscan as F
import sb2_phase_grade as G

ORB_418 = {"source_id": "418728701136352000", "period": "1.9675448167153748", "period_error": "3.9019335e-05",
           "eccentricity": "0.2253986185299188", "eccentricity_error": "0.010954328",
           "arg_periastron": "32.37950819683473", "arg_periastron_error": "3.9035842",
           "t_periastron": "-0.8148264400473335", "t_periastron_error": "0.02003268", "nss_solution_type": "SB2"}
REC_418 = {"name": "Gaia DR3 418728701136352000", "source_id": "418728701136352000", "tic": "fixture-418",
           "role": "target",
           "vetted": "", "label": "DETECTED", "P_gaia": 1.9675448167153748, "P_best": 1.9675280203128913,
           "T_dip1": 2700.2186955455845, "box_w": 16, "box2_w": 16, "sec": "SEC_DETECTED",
           "sep_obs": 0.6200000000000001, "n_sectors": 6, "G": 8.98}
ORB_282 = {"source_id": "2825104215999846144", "period": "2.4459244940177975", "period_error": "2.3348732e-05",
           "eccentricity": "0.06799525074794158", "eccentricity_error": "0.006550011",
           "arg_periastron": "240.43638271739127", "arg_periastron_error": "5.832804",
           "t_periastron": "-0.6081781478955065", "t_periastron_error": "0.039145075", "nss_solution_type": "SB2"}
REC_282 = {"name": "Gaia DR3 2825104215999846144", "source_id": "2825104215999846144", "tic": "243126121",
           "role": "target",
           "vetted": "", "label": "DETECTED", "P_gaia": 2.4459244940177975, "P_best": 2.4458077503577975,
           "T_dip1": 3204.650508049289, "box_w": 16, "box2_w": 16, "sec": "SEC_DETECTED",
           "sep_obs": 0.495, "n_sectors": 2, "G": 10.38}
ORB_218 = {"source_id": "2186746353538849408", "period": "5.223366008623945", "period_error": "0.00012772053",
           "eccentricity": "", "eccentricity_error": "", "arg_periastron": "", "arg_periastron_error": "",
           "t_periastron": "-2.2187927920734767", "t_periastron_error": "0.00858001", "nss_solution_type": "SB2C"}
REC_218 = {"name": "Gaia DR3 2186746353538849408", "source_id": "2186746353538849408", "tic": "fixture-218",
           "role": "target",
           "vetted": "", "label": "DETECTED", "P_gaia": 5.223366008623945, "P_best": 5.223366008623945,
           "T_dip1": 2660.2423047472294, "box_w": 6, "box2_w": 6, "sec": "SEC_DETECTED", "sep_obs": 0.5,
           "n_sectors": 6, "G": 8.47}
ORB_432_OUTER = {"source_id": "4322674031257647744", "period": "280.989082755396", "period_error": "2.2748928",
                 "eccentricity": "0.32224040243124796", "eccentricity_error": "0.10880015", "arg_periastron": "",
                 "arg_periastron_error": "", "t_periastron": "-136.91028615773814",
                 "t_periastron_error": "14.779244", "nss_solution_type": "Orbital"}
ORB_432_SB2 = {"source_id": "4322674031257647744", "period": "3.778981343214162", "period_error": "9.646207e-05",
               "eccentricity": "0.04491124446209292", "eccentricity_error": "0.012884065",
               "arg_periastron": "356.05551248561534", "arg_periastron_error": "18.10982",
               "t_periastron": "0.04174554817538925", "t_periastron_error": "0.18751061", "nss_solution_type": "SB2"}


class TestGeometry(unittest.TestCase):
    def test_eccentric_conjunctions_hand(self):
        c1, c2 = F.conjunction_phases(0.2253986185299188, 32.37950819683473)
        self.assertAlmostEqual(c1, 0.104875, delta=0.002)   # hand: nu = 57.62 deg
        self.assertAlmostEqual(c2, 0.726196, delta=0.002)   # hand: nu = 237.62 deg

    def test_circular_convention(self):
        c1, c2 = F.conjunction_phases(0.0, 0.0)
        self.assertAlmostEqual(c1, 0.25, places=9)
        self.assertAlmostEqual(c2, 0.75, places=9)


class TestPhaseTest(unittest.TestCase):
    def test_match_and_separation(self):
        orb, typ = G.pick_orbit([ORB_418], REC_418["P_gaia"])
        self.assertEqual(typ, "SB2")
        out = G.phase_test(REC_418, orb)
        self.assertEqual(out["phase"], "PHASE_MATCH")
        self.assertEqual(out["phase_map"], "c1")
        self.assertTrue(-1.5 < out["phase_z"] < 0.0, out["phase_z"])        # hand: -0.038 d / 0.065 d
        self.assertAlmostEqual(out["sep_gaia"], 0.6213, delta=0.003)
        self.assertEqual(out["sep"], "SEP_MATCH")

    def test_mismatch(self):
        orb, _ = G.pick_orbit([ORB_282], REC_282["P_gaia"])
        out = G.phase_test(REC_282, orb)
        self.assertEqual(out["phase"], "PHASE_MISMATCH")
        self.assertEqual(out["phase_map"], "c1")
        self.assertTrue(out["phase_z"] < -3.0, out["phase_z"])              # hand: -0.45 d / 0.08 d

    def test_circular_match(self):
        orb, typ = G.pick_orbit([ORB_218], REC_218["P_gaia"])
        self.assertEqual(typ, "SB2C")
        out = G.phase_test(REC_218, orb)
        self.assertTrue(out["circular"])
        self.assertEqual(out["phase"], "PHASE_MATCH")
        self.assertTrue(abs(out["phase_z"]) < 1.0, out["phase_z"])          # hand: -0.009 d / 0.068 d

    def test_pick_orbit_two_solutions(self):
        orb, typ = G.pick_orbit([ORB_432_SB2, ORB_432_OUTER], 3.778981343214162)
        self.assertEqual(typ, "SB2")
        orb, typ = G.pick_orbit([ORB_432_OUTER, ORB_432_SB2], 3.778981343214162)
        self.assertEqual(typ, "SB2")
        self.assertAlmostEqual(orb["P"], 3.778981343214162, places=12)
        orb, why = G.pick_orbit([ORB_432_OUTER], 3.778981343214162)
        self.assertIsNone(orb)
        self.assertEqual(why, "ANCHOR_FAILED")
        self.assertEqual(G.pick_orbit(None, 1.0), (None, "NO_ORBIT_ROW"))

    def test_regrade_and_frozen_grade(self):
        recs = [dict(REC_418), dict(REC_282), dict(REC_218),
                {"name": "x", "source_id": "1", "tic": "fixture-x", "role": "control", "vetted": "",
                 "label": "NOT_DETECTED", "P_gaia": 1.0, "n_sectors": 1, "G": 9.0}]
        orbits = {"418728701136352000": [ORB_418], "2825104215999846144": [ORB_282],
                  "2186746353538849408": [ORB_218]}
        self.assertEqual(G.regrade(recs, orbits), 3)
        g = F.grade(recs, False)
        self.assertEqual(g["F2"]["n_candidates"], 2)          # 418... and 218... (not VSX-checked here)
        self.assertEqual(len(g["F2"]["detected_phase_not_matched"]), 1)
        self.assertEqual(g["F2"]["detected_phase_not_matched"][0]["tic"], "243126121")
        self.assertEqual(g["F0"]["label"], "CONTROLS_FAIL")   # the one control is not detected


if __name__ == "__main__":
    unittest.main()
