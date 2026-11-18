# SPDX-License-Identifier: Apache-2.0
"""Tests for eblm_fit_rest (pure Python). MV2 of Munim, Inc.; made with AI agents."""
import unittest

import eblm_fit_rest as r


class TestRest(unittest.TestCase):
    def test_done_ids(self):
        text = "source_id,tic,verdict\n123,9,EBLM_CONSISTENT\n456,,NO_TIC\n"
        self.assertEqual(r.done_ids_from_csv(text), {"123", "456"})

    def test_select_skips_done_and_interleaves(self):
        eblm = [{"source_id": i} for i in range(10)]
        done = {"0", "1", "2"}
        a = r.select(eblm, done, 0, 2)
        b = r.select(eblm, done, 1, 2)
        self.assertEqual([c["source_id"] for c in a], [3, 5, 7, 9])
        self.assertEqual([c["source_id"] for c in b], [4, 6, 8])
        # the parts are disjoint and together cover everything not done
        self.assertEqual(sorted(c["source_id"] for c in a + b), list(range(3, 10)))

    def test_select_bad_part(self):
        with self.assertRaises(ValueError):
            r.select([], set(), 2, 2)

    def test_pinned_sha(self):
        self.assertEqual(len(r.SHA), 40)
        self.assertIn(r.SHA, r.BASE)


if __name__ == "__main__":
    unittest.main()
