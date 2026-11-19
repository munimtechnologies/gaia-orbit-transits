# SPDX-License-Identifier: Apache-2.0
"""Tests for combine_eblm_full.py (stdlib only; no network)."""
import unittest

import combine_eblm_full as cf

H = "source_id,tic,verdict,b,reasons\n"


class TestCombine(unittest.TestCase):
    def test_concatenates_in_order(self):
        a = H + "1,10,EBLM_CONSISTENT,0.1,ok\n2,20,EBLM_GRAZING,0.9,\"b 0.9 > 1 - k\"\n"
        b = H + "3,30,NO_ECLIPSE,,x\n"
        header, rows, info = cf.combine([("a", a), ("b", b)])
        self.assertEqual(header[0], "source_id")
        self.assertEqual([r[0] for r in rows], ["1", "2", "3"])
        self.assertEqual(info["parts"], {"a": 2, "b": 1})
        self.assertEqual(info["n_rows"], 3)
        # quoted field with commas survives a round trip
        out = cf.to_csv(header, rows)
        h2, rows2 = cf.parse(out)
        self.assertEqual(h2, header)
        self.assertEqual(rows2[1][4], "b 0.9 > 1 - k")

    def test_header_mismatch(self):
        a = H + "1,10,EBLM_CONSISTENT,0.1,ok\n"
        b = "source_id,tic,verdict,reasons\n3,30,X,y\n"
        with self.assertRaises(ValueError):
            cf.combine([("a", a), ("b", b)])

    def test_duplicate_source_id(self):
        a = H + "1,10,EBLM_CONSISTENT,0.1,ok\n"
        b = H + "1,10,EBLM_CONSISTENT,0.1,ok\n"
        with self.assertRaises(ValueError) as ctx:
            cf.combine([("a", a), ("b", b)])
        self.assertIn("duplicate", str(ctx.exception))

    def test_first_column_must_be_source_id(self):
        with self.assertRaises(ValueError):
            cf.combine([("a", "tic,source_id\n1,2\n")])

    def test_blank_lines_ignored(self):
        a = H + "1,10,EBLM_CONSISTENT,0.1,ok\n\n"
        _, rows, _ = cf.combine([("a", a)])
        self.assertEqual(len(rows), 1)

    def test_parts_pinned(self):
        names = [p[0] for p in cf.PARTS]
        self.assertEqual(names, ["v1", "rest-a", "rest-b"])
        self.assertEqual(sum(p[2] for p in cf.PARTS), cf.N_EBLM_LIKE)
        self.assertTrue(cf.PARTS[0][1].startswith(cf.V1_SHA))


if __name__ == "__main__":
    unittest.main()
