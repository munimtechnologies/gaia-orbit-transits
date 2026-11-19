# SPDX-License-Identifier: Apache-2.0
"""dr4_d5_rate 0.1.1 with ESA-style neighbourhood columns (calib-dr4 amendment 2).
MV2 of Munim, Inc.; made with AI agents. Stdlib only, a fake TAP service, no network."""
import unittest

import dr4_d5_rate as dr
import dr4_fetch as df
import sb1_transit as st
import test_dr4_d5_rate as TD

XM_DR4 = ["dr4_source_id", "dr3_source_id", "angular_distance", "magnitude_difference"]


class TestD5NewId(unittest.TestCase):
    def setUp(self):
        df.reset_xmatch_new_id()

    def tearDown(self):
        df.reset_xmatch_new_id()

    def test_dr4_source_id_naming(self):
        cols = TD.dr4_cols()
        cols["gaiadr4.dr3_neighbourhood"] = list(XM_DR4)
        q = TD.dr4_fake(cols=cols)
        rows, recs, info = dr.build_pool("dr4", st, q, log=lambda *a: None)
        self.assertEqual(info["xmatch_new_id"], "dr4_source_id")
        # same answer as test_dr4_pool, whose fake table uses 'source_id'
        self.assertEqual(info["dr3_status"], {"NEW": 1, "IN_DR3": 1, "NEW_NO_DR3_MATCH": 3})
        self.assertEqual(sorted(r["source_id"] for r in rows), ["101", "104", "105", "107"])
        xq = [c for c in q.calls if "dr3_neighbourhood AS x WHERE" in c]
        self.assertTrue(xq)
        self.assertTrue(all("x.dr4_source_id AS new_id" in c and "WHERE x.dr4_source_id IN ("
                            in c for c in xq))

    def test_source_id_fallback(self):
        rows, recs, info = dr.build_pool("dr4", st, TD.dr4_fake(), log=lambda *a: None)
        self.assertEqual(info["xmatch_new_id"], "source_id")

    def test_no_new_id_column_stops(self):
        cols = TD.dr4_cols()
        cols["gaiadr4.dr3_neighbourhood"] = ["dr3_source_id", "angular_distance",
                                             "magnitude_difference"]
        with self.assertRaises(df.SchemaError) as cm:
            dr.build_pool("dr4", st, TD.dr4_fake(cols=cols), log=lambda *a: None)
        self.assertIn("dr4_source_id | source_id", str(cm.exception))

    def test_dr3_rehearsal_has_no_xmatch(self):
        self.assertEqual(dr.TABLES["dr3"]["xmatch"], None)


if __name__ == "__main__":
    unittest.main()
