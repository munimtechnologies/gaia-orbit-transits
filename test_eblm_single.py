# SPDX-License-Identifier: Apache-2.0
"""Tests for eblm_single (standard library only). MV2 of Munim, Inc.; made with AI agents."""
import json
import math
import unittest

import eblm_single as s


class TestIds(unittest.TestCase):
    def test_clean_ids_keeps_order_and_dedupes(self):
        self.assertEqual(s.clean_ids([" 12", "5", 12]), ["12", "5"])

    def test_clean_ids_rejects_empty_and_junk(self):
        with self.assertRaises(ValueError):
            s.clean_ids([])
        with self.assertRaises(ValueError):
            s.clean_ids(["12; DROP"])

    def test_defaults(self):
        self.assertEqual(s.DEFAULT_IDS[0], "6853008555751131648")
        self.assertEqual(len(s.SHA), 40)
        self.assertIn(s.SHA, s.BASE)


class TestAdql(unittest.TestCase):
    def test_query_shape(self):
        q = s.single_adql(["6853008555751131648", "2160710158704303360"])
        self.assertIn("LEFT JOIN gaiadr3.vari_eclipsing_binary AS v", q)
        self.assertIn("JOIN gaiadr3.gaia_source AS g", q)
        self.assertIn("n.nss_solution_type = 'SB1'", q)
        self.assertIn("IN (6853008555751131648, 2160710158704303360)", q)
        # every column eblm_screen.classify reads is selected
        for col in ("n.period", "AS k1,", "AS k1_error", "n.eccentricity", "n.arg_periastron",
                    "n.t_periastron", "v.frequency", "v.reference_time", "AS ell_mag,",
                    "p.mass_flame", "p.radius_flame", "p.teff_gspphot", "g.phot_g_mean_mag",
                    "v.derived_primary_ecl_phase", "v.geom_model_gaussian2_depth"):
            self.assertIn(col, q)
        # no inner join on the eclipsing-binary table
        self.assertNotIn(" JOIN gaiadr3.vari_eclipsing_binary AS v ON", q.replace("LEFT JOIN", "LJ"))

    def test_schema(self):
        self.assertIn("FROM gaiadr4.nss_two_body_orbit", s.single_adql([1], schema="gaiadr4"))


class TestOutcome(unittest.TestCase):
    def test_untested(self):
        for verdict in ("", None, "NO_TIC", "NO_TESS_DATA", "ERROR"):
            self.assertEqual(s.outcome({"verdict": verdict}), "UNTESTED")

    def test_simple_labels(self):
        self.assertEqual(s.outcome({"verdict": "NO_ECLIPSE"}), "E_NO_ECLIPSE")
        self.assertEqual(s.outcome({"verdict": "TWIN_AT_2P"}), "D_TWIN_AT_2P")
        self.assertEqual(s.outcome({"verdict": "MASS_TENSION_HEAVIER"}), "A_COMPANION_HEAVIER_THAN_GAIA")
        self.assertEqual(s.outcome({"verdict": "TOO_LUMINOUS"}), "A_COMPANION_HEAVIER_THAN_GAIA")
        self.assertEqual(s.outcome({"verdict": "MASS_TENSION_LIGHTER"}), "A2_COMPANION_LIGHTER_THAN_GAIA")
        self.assertEqual(s.outcome({"verdict": "BD_EBLM_GRAZING"}), "G_GRAZING_RADIUS_UNMEASURED")
        self.assertEqual(s.outcome({"verdict": "EBLM_CONSISTENT"}), "C_NORMAL_COMPANION")
        self.assertEqual(s.outcome({"verdict": "BD_EBLM_SMALL_RADIUS"}), "C_NORMAL_COMPANION")
        self.assertEqual(s.outcome({"verdict": "SOMETHING"}), "OTHER:SOMETHING")

    def test_large_radius_needs_primary_scale(self):
        self.assertEqual(s.outcome({"verdict": "EBLM_LARGE_RADIUS", "r1_ratio": 1.02}),
                         "B_OVERSIZED_COMPANION")
        self.assertEqual(s.outcome({"verdict": "BD_EBLM_LARGE_RADIUS", "r1_ratio": "0.81"}),
                         "B_OVERSIZED_COMPANION")
        self.assertEqual(s.outcome({"verdict": "EBLM_LARGE_RADIUS", "r1_ratio": 1.4}),
                         "B0_LARGE_BUT_PRIMARY_SCALE_DISAGREES")
        self.assertEqual(s.outcome({"verdict": "EBLM_LARGE_RADIUS", "r1_ratio": float("nan")}),
                         "B0_LARGE_BUT_PRIMARY_SCALE_DISAGREES")
        self.assertEqual(s.outcome({"verdict": "EBLM_LARGE_RADIUS"}),
                         "B0_LARGE_BUT_PRIMARY_SCALE_DISAGREES")


class TestHelpers(unittest.TestCase):
    def test_present(self):
        self.assertFalse(s.present(""))
        self.assertFalse(s.present(None))
        self.assertFalse(s.present(float("nan")))
        self.assertFalse(s.present(" null "))
        self.assertTrue(s.present("0.4321"))
        self.assertTrue(s.present(0.0))

    def test_jsonable(self):
        obj = {"a": float("nan"), "b": [1.5, float("inf"), "x"], "c": {"d": True}, 3: None}
        out = s.jsonable(obj)
        self.assertEqual(out, {"a": None, "b": [1.5, None, "x"], "c": {"d": True}, "3": None})
        json.dumps(out, allow_nan=False)

    def test_jsonable_numpy_like(self):
        class F:
            def __float__(self):
                return 2.5
        self.assertEqual(s.jsonable(F()), 2.5)
        self.assertTrue(math.isclose(s.jsonable(3.0), 3.0))


if __name__ == "__main__":
    unittest.main()
