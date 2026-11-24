# SPDX-License-Identifier: Apache-2.0
"""Offline tests for cand_vet (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents)."""
import unittest

import cand_vet as m


class TestScan(unittest.TestCase):
    def test_scan_tic_csv(self):
        lines = ["TIC,period,depth_1\n", "173207470,3.05,0.07\n", "1,2,3\n", "\n",
                 "57791790.0,3.08,0.04\n", "bad,1,1\n"]
        header, hits, n = m.scan_tic_csv(iter(lines), {173207470, 57791790, 999})
        self.assertEqual(header, ["TIC", "period", "depth_1"])
        self.assertEqual(n, 4)
        self.assertEqual(sorted(hits), [57791790, 173207470])
        self.assertEqual(hits[173207470][0]["period"], "3.05")

    def test_scan_tic_column_not_first(self):
        lines = ["x,tic\n", "5,384284045\n"]
        _, hits, n = m.scan_tic_csv(iter(lines), {384284045})
        self.assertEqual(n, 1)
        self.assertIn(384284045, hits)

    def test_token_hits_whole_numbers_only(self):
        text = "a,1384284045\nb,384284045,c\nTIC 384284045\n3842840450"
        h = m.token_hits(text, ["384284045", "57791790"])
        self.assertEqual(h, {"384284045": [2, 3]})

    def test_targets(self):
        self.assertEqual(len(m.TARGETS), 12)
        self.assertEqual(m.TARGETS[173207470][0], "HD 218299")
        self.assertEqual(m.TARGETS[57791790][1], "3479008554410838656")
        self.assertEqual(m.TARGETS[325802598][1], "4297719103037032832")


if __name__ == "__main__":
    unittest.main()
