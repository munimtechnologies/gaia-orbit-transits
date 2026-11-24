# SPDX-License-Identifier: Apache-2.0
"""Tests for sb2_screen_dr4 0.2.0 (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents).
Pure functions only; no network."""
import unittest

import sb2_screen_dr4 as g5


class TestG5(unittest.TestCase):
    def test_self_test(self):
        ok, bad = g5.self_test()
        self.assertTrue(ok, "failed checks %s" % bad)

    def test_villanova_none_on_error_page(self):
        self.assertIsNone(g5.villanova_status_v2("<h1>400 Bad Request</h1>"))

    def test_two_tables(self):
        text = ("#   VizieR\n#RESOURCE=1\nTIC\tP\n\t d\n---\t---\n1\t2.0\n\n"
                "#RESOURCE=2\nTIC\n \n----\n7\n8\n")
        err, tabs = g5.parse_asu_tsv(text)
        self.assertFalse(err)
        self.assertEqual(len(tabs), 2)
        self.assertEqual(g5.n_rows(tabs), 3)

    def test_tic_mode_setup(self):
        tsv = "#   VizieR\nTIC\tPer\n \t d\n----\t----\n238162238\t2.43\n"

        def get(url, accept_404=False):
            return tsv if "238162238" in url or "-out.max=1&" in url else "#   VizieR\n"

        info = g5.viz_setup("J/X/1", get)
        self.assertEqual(info["mode"], "tic")
        self.assertTrue(g5.viz_lookup(info, float("nan"), float("nan"), "238162238", get))
        self.assertFalse(g5.viz_lookup(info, float("nan"), float("nan"), "5", get))

    def test_setup_fails_safe(self):
        def get(url, accept_404=False):
            raise RuntimeError("down")

        info = g5.viz_setup("J/X/1", get)
        self.assertIsNone(info["mode"])
        self.assertIsNone(g5.viz_lookup(info, 1.0, 2.0, "3", get))

    def test_arm_b_selection(self):
        rows = [{"source_id": "1", "period": "3.0", "semi_amplitude_primary": "50",
                 "semi_amplitude_secondary": "60", "eccentricity": "", "phot_g_mean_mag": "10.5"},
                {"source_id": "2", "period": "9.0", "semi_amplitude_primary": "50",
                 "semi_amplitude_secondary": "60", "eccentricity": "", "phot_g_mean_mag": "9"},
                {"source_id": "3", "period": "2.0", "semi_amplitude_primary": "40",
                 "semi_amplitude_secondary": "45", "eccentricity": "0.1", "phot_g_mean_mag": "8"},
                {"source_id": "3", "period": "2.0", "semi_amplitude_primary": "40",
                 "semi_amplitude_secondary": "45", "eccentricity": "0.1", "phot_g_mean_mag": "8"}]
        sel = g5.select_rows_b(rows)
        self.assertEqual([r["source_id"] for r in sel], ["3", "1"])
        self.assertGreater(sel[0]["m1sin3i"], 0)

    def test_parse_bool(self):
        self.assertIs(g5.parse_bool("True"), True)
        self.assertIs(g5.parse_bool("False"), False)
        self.assertIsNone(g5.parse_bool(""))

    def test_keys(self):
        self.assertEqual(g5.KEYS[-2:], ["status", "error"])
        self.assertIn("t10k_viz", g5.KEYS)
        self.assertIn("villanova", g5.KEYS)


if __name__ == "__main__":
    unittest.main()
