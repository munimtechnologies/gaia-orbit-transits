# SPDX-License-Identifier: Apache-2.0
"""Tests for sb2_screen_dr4_nssm 0.1.0 (g5 amendment 3; MV2 of Munim, Inc.; made with AI agents).
No network."""
import unittest

import sb2_screen_dr4 as g5
import sb2_screen_dr4_nssm as g5n


class TestNssMasses(unittest.TestCase):
    def setUp(self):
        self.saved = g5.s0.ORBIT_QUERY

    def tearDown(self):
        g5.s0.ORBIT_QUERY = self.saved

    def full(self):
        return {"nss_two_body_orbit": set(g5.REQ_NSS), "gaia_source": set(g5.REQ_GS)}

    def test_query_text(self):
        q = g5n.ORBIT_QUERY_NSSM
        self.assertIn("{s}.nss_masses", q)
        self.assertNotIn("binary_masses", q)
        self.assertIn("b.combination_method LIKE 'SB2%'", q)
        self.assertIn("o.period < 8", q)

    def test_dr4_names(self):
        cols = dict(self.full(), nss_masses=set(g5.REQ_BM))
        out, used = g5n.adapt(cols)
        self.assertEqual(used, "nss_masses")
        self.assertEqual(g5.schema_gate(out), "A")
        self.assertEqual(g5.s0.ORBIT_QUERY, g5n.ORBIT_QUERY_NSSM)

    def test_dr3_names_unchanged(self):
        cols = dict(self.full(), binary_masses=set(g5.REQ_BM), nss_masses=set(g5.REQ_BM))
        out, used = g5n.adapt(cols)
        self.assertEqual(used, "binary_masses")
        self.assertEqual(g5.schema_gate(out), "A")
        self.assertEqual(g5.s0.ORBIT_QUERY, g5n.ORBIT_QUERY_BM)

    def test_no_masses_is_arm_b(self):
        out, used = g5n.adapt(self.full())
        self.assertIsNone(used)
        self.assertEqual(g5.schema_gate(out), "B")


if __name__ == "__main__":
    unittest.main()
