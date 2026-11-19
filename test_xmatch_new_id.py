# SPDX-License-Identifier: Apache-2.0
"""dr4_sb1_reality 0.1.1 with ESA-style neighbourhood columns (calib-dr4 amendment 2).

The DR3 rehearsal of calib-dr4 showed that gaiadr3.dr2_neighbourhood names the new-release id
'dr3_source_id' (no 'source_id'). These tests run the dr4_sb1_reality end-to-end fakes of
test_dr4_sb1_reality with the DR4 table named the same way ('dr4_source_id'), and with no
usable id column at all. MV2 of Munim, Inc.; made with AI agents. Stdlib only, offline.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

import dr4_fetch as df
import dr4_sb1_reality as R
import test_dr4_sb1_reality as T


class TestSb1RealityNewId(unittest.TestCase):
    def setUp(self):
        df.reset_xmatch_new_id()
        self.tmp = tempfile.mkdtemp()
        self._old_st = sys.modules.get("sb1_transit")
        sys.modules["sb1_transit"] = T.fake_st()
        self._old_xm = T.XM_COLS

    def tearDown(self):
        T.XM_COLS = self._old_xm
        shutil.rmtree(self.tmp, ignore_errors=True)
        if self._old_st is None:
            sys.modules.pop("sb1_transit", None)
        else:
            sys.modules["sb1_transit"] = self._old_st
        df.reset_xmatch_new_id()

    def test_dr4_source_id_naming(self):
        T.XM_COLS = ["dr4_source_id", "dr3_source_id", "angular_distance",
                     "magnitude_difference"]
        seen = []
        base = T.make_query("dr4")

        def q(adql, timeout=None, **kw):
            seen.append(adql)
            return base(adql, timeout=timeout, **kw)
        http = T.make_http(["EPOCH_PHOTOMETRY"], {})
        rc = R.run(T.args(self.tmp, "dr4", suspend_epochs=True), query=q, http=http)
        self.assertEqual(rc, 0)
        with open(os.path.join(self.tmp, "sb1_reality_summary.json")) as fh:
            s = json.load(fh)
        self.assertEqual(s["xmatch_new_id"], "dr4_source_id")
        self.assertEqual(s["labels"]["DROPPED"], 1)
        xq = [a for a in seen if "dr3_neighbourhood AS x" in a]
        self.assertTrue(xq)
        self.assertTrue(all("x.dr4_source_id AS new_id" in a for a in xq))

    def test_no_new_id_column_stops(self):
        T.XM_COLS = ["dr3_source_id", "angular_distance", "magnitude_difference"]
        http = T.make_http(["EPOCH_PHOTOMETRY"], {})
        rc = R.run(T.args(self.tmp, "dr4", suspend_epochs=True), query=T.make_query("dr4"),
                   http=http)
        self.assertEqual(rc, 4)
        with open(os.path.join(self.tmp, "schema_found.json")) as fh:
            found = json.load(fh)
        self.assertIn("gaiadr4.dr3_neighbourhood", found)


if __name__ == "__main__":
    unittest.main()
