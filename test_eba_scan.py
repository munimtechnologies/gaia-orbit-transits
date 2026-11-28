# SPDX-License-Identifier: Apache-2.0
"""Offline tests for eba_scan 0.1.0. MV2 of Munim, Inc.; made with AI agents."""
import io
import unittest
import zipfile

import eba_scan as es


class TestEbaScan(unittest.TestCase):
    def test_whole_token(self):
        h = es.token_hits("a,1484788901\nb,148478890,x\n", ["148478890"])
        self.assertEqual(h, {"148478890": [2]})

    def test_scan_zip(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("repo-abc/CHECKCARD.csv", "label,TIC\nB6,464315748\n")
            zf.writestr("repo-abc/figs/a.png", "464315748")
            zf.writestr("repo-abc/reviews/x.txt", "nothing here")
        buf.seek(0)
        r = es.scan_zip(buf, ["464315748", "148478890"])
        self.assertEqual(r["n_text"], 2)
        self.assertEqual(r["n_scanned"], 2)
        self.assertEqual([h["file"] for h in r["hits"]["464315748"]], ["CHECKCARD.csv"])
        self.assertNotIn("148478890", r["hits"])

    def test_tic_csv(self):
        hits, n = es.scan_tic_csv(io.StringIO("TIC,score\n306114087,2\n1,0\n"), {306114087, 5})
        self.assertEqual(n, 2)
        self.assertIn("306114087", hits)

    def test_grade(self):
        eba_hits = {"464315748": [{"file": "CHECKCARD.csv"}], "157469799": [{"file": "accepted-systems.csv"}],
                    "428977802": [{"file": "reviews/r.txt"}], "74104445": [{"file": "reviews/q.csv"}]}
        obaf = {"306114087": [{}], "323292655": [{}]}
        v = es.verdicts(eba_hits, obaf)
        g = es.grade(v, {"n_text": 3, "n_scanned": 3, "skipped_large": [], "errors": {}}, True)
        self.assertTrue(g["E0_eba_controls"])
        self.assertTrue(g["E0_obaf_controls"])
        self.assertEqual(g["E1_complete"], "SCAN_COMPLETE")
        self.assertEqual(g["E2_listed"], ["TIC 74104445"])
        self.assertIn("TYC 7628-1267-1", g["E2_unlisted"])


if __name__ == "__main__":
    unittest.main()
