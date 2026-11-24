# SPDX-License-Identifier: Apache-2.0
"""Unit tests for sb2_ffiscan_t2 (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents)."""
import unittest

import sb2_screen as s0
import sb2_tier2 as t2
import sb2_ffiscan_t2 as X


def orbit(sid, ratio, G, P=3.0, k=100.0):
    ms = s0.m1sin3i(k, k, P, 0.0)
    return {"source_id": sid, "period": repr(P), "period_error": "1e-4",
            "semi_amplitude_primary": repr(k), "semi_amplitude_secondary": repr(k),
            "eccentricity": "", "m1": repr(ms / ratio), "phot_g_mean_mag": repr(G),
            "ra": "1.0", "dec": "2.0"}


class FfiscanT2Tests(unittest.TestCase):
    def test_self_test_passes(self):
        ok, bad = X.self_test()
        self.assertTrue(ok, bad)

    def test_select_tier2_only_sorted_by_G(self):
        rows = [orbit("a", 0.80, 7.0), orbit("b", 0.90, 9.0), orbit("c", 1.0, 6.0),
                orbit("d", 1.12, 8.0), orbit("e", 0.86, 9.0, P=9.0)]
        self.assertEqual([s["source_id"] for s in X.select(rows)], ["d", "b"])

    def test_selected_star_fields(self):
        s = X.select([orbit("b", 0.90, 9.0)])[0]
        self.assertEqual(s["name"], "Gaia DR3 b")
        self.assertAlmostEqual(s["s3_ratio"], 0.90, places=9)
        self.assertEqual(s["vetted"], "")
        self.assertAlmostEqual(s["P_screen"], 3.0)

    def test_hd35131_is_tier2(self):
        row = {"source_id": X.HD35131_SID, "period": "4.062349795949258",
               "eccentricity": "0.052425326530381615", "semi_amplitude_primary": "96.12954958426585",
               "semi_amplitude_secondary": "85.04996780935767", "m1": "1.3467268"}
        r = t2.ratio_of(row)
        self.assertAlmostEqual(r, 0.869, delta=0.002)
        self.assertEqual(t2.tier_of(r), 2)

    def test_anchor(self):
        self.assertTrue(X.anchor_ok({"P": 5.0 * (1 + 5e-8), "Tp": 0.0}, 5.0))
        self.assertFalse(X.anchor_ok({"P": 5.0 * (1 + 5e-7), "Tp": 0.0}, 5.0))

    def test_roles(self):
        self.assertEqual(X.role_of({"gaia_eb": True}), "control")
        self.assertEqual(X.role_of({"gaia_class": "ECL", "toi": "1.01"}), "control")
        self.assertEqual(X.role_of({"toi": "1.01"}), "toi")
        self.assertEqual(X.role_of({}), "target")

    def test_extras_not_reached(self):
        e = X.extras([], [], {"n_selected": 200, "rowan_tier2_selected": 10, "hd35131_selected": True})
        self.assertTrue(e["T2F_sample"]["in_range"])
        self.assertEqual(e["HD35131"]["label"], "NOT_REACHED")


if __name__ == "__main__":
    unittest.main()
