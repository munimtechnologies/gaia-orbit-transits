# SPDX-License-Identifier: Apache-2.0
"""Tests for dr4_votable (MV2, Munim, Inc.; made with AI agents). The two short base64 streams were
encoded by hand from the VOTable 1.3 spec (BINARY2: null-flag byte, then big-endian values)."""
import base64
import csv
import io
import struct
import types
import unittest

import dr4_votable as V

HEAD = ('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<VOTABLE version="1.4" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">'
        '<RESOURCE type="results"><INFO name="QUERY_STATUS" value="OK"/><TABLE>')
TAIL = '</TABLE></RESOURCE></VOTABLE>'


def vot(fields_xml, data_xml):
    return HEAD + fields_xml + "<DATA>" + data_xml + "</DATA>" + TAIL


ONE_INT = '<FIELD name="n" datatype="int"/>'


class TestHandEncoded(unittest.TestCase):
    def test_binary2_int_value(self):
        # bytes 00 | 00 00 00 01 -> "AAAAAAE="
        names, rows = V.parse_votable(vot(ONE_INT, '<BINARY2><STREAM encoding="base64">AAAAAAE=</STREAM></BINARY2>'))
        self.assertEqual(names, ["n"])
        self.assertEqual(rows, [[1]])

    def test_binary2_null_flag(self):
        # bytes 80 | 00 00 00 01 -> "gAAAAAE=": the only field is flagged null
        names, rows = V.parse_votable(vot(ONE_INT, '<BINARY2><STREAM encoding="base64">gAAAAAE=</STREAM></BINARY2>'))
        self.assertEqual(rows, [[None]])

    def test_binary_v1_no_mask(self):
        # BINARY (no null mask): 00 00 00 05 -> "AAAABQ=="
        names, rows = V.parse_votable(vot(ONE_INT, '<BINARY><STREAM encoding="base64">AAAABQ==</STREAM></BINARY>'))
        self.assertEqual(rows, [[5]])


FIELDS = ('<FIELD name="source_id" datatype="long"/>'
          '<FIELD name="band" datatype="char" arraysize="*"/>'
          '<FIELD name="g_transit_time" datatype="double" arraysize="*"/>'
          '<FIELD name="g_transit_mag" datatype="float" arraysize="*"/>'
          '<FIELD name="ok" datatype="boolean"/>'
          '<FIELD name="n" datatype="short"/>')


def row_bytes(mask, sid, band, times, mags, ok, n):
    b = bytes([mask]) + struct.pack(">q", sid)
    b += struct.pack(">i", len(band)) + band.encode()
    b += struct.pack(">i", len(times)) + struct.pack(">%dd" % len(times), *times)
    b += struct.pack(">i", len(mags)) + struct.pack(">%df" % len(mags), *mags)
    b += (b"T" if ok else b"F") + struct.pack(">h", n)
    return b


class TestArrays(unittest.TestCase):
    def setUp(self):
        raw = (row_bytes(0x00, 4961129715887496320, "G", [1717.25, 1718.5], [9.5, 9.75], True, 7)
               + row_bytes(0x04, 2825104215999846144, "BP", [], [], False, 3))   # 0x04 = 6th field (n) null
        self.b2 = vot(FIELDS, '<BINARY2><STREAM encoding="base64">%s</STREAM></BINARY2>'
                      % base64.b64encode(raw).decode())
        self.td = vot(FIELDS, '<TABLEDATA>'
                              '<TR><TD>4961129715887496320</TD><TD>G</TD><TD>1717.25 1718.5</TD>'
                              '<TD>9.5 9.75</TD><TD>T</TD><TD>7</TD></TR>'
                              '<TR><TD>2825104215999846144</TD><TD>BP</TD><TD></TD><TD></TD><TD>F</TD><TD></TD></TR>'
                              '</TABLEDATA>')

    def check(self, text):
        names, rows = V.parse_votable(text)
        self.assertEqual(names, ["source_id", "band", "g_transit_time", "g_transit_mag", "ok", "n"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], 4961129715887496320)
        self.assertEqual(rows[0][1], "G")
        self.assertEqual(rows[0][2], [1717.25, 1718.5])
        self.assertEqual(rows[0][3], [9.5, 9.75])
        self.assertIs(rows[0][4], True)
        self.assertEqual(rows[0][5], 7)
        self.assertEqual(rows[1][2], [])
        self.assertIs(rows[1][4], False)
        self.assertIsNone(rows[1][5])

    def test_binary2(self):
        self.check(self.b2)

    def test_tabledata(self):
        self.check(self.td)

    def test_csv_roundtrip(self):
        for text in (self.b2, self.td):
            rows = list(csv.DictReader(io.StringIO(V.votable_to_csv(text))))
            self.assertEqual(rows[0]["source_id"], "4961129715887496320")
            self.assertEqual(rows[0]["g_transit_time"], "[1717.25,1718.5]")
            vals = [float(x) for x in rows[0]["g_transit_mag"].strip("[]").split(",")]
            self.assertEqual(vals, [9.5, 9.75])
            self.assertEqual(rows[1]["g_transit_time"], "[]")
            self.assertEqual(rows[1]["n"], "")
            self.assertEqual(rows[0]["ok"], "true")


class TestErrorsAndInstall(unittest.TestCase):
    def test_error_status(self):
        err = ('<VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE type="results">'
               '<INFO name="QUERY_STATUS" value="ERROR">bad query</INFO></RESOURCE></VOTABLE>')
        with self.assertRaises(RuntimeError):
            V.parse_votable(err)

    def test_install_converts_only_votables(self):
        mod = types.SimpleNamespace(decode_payload=lambda raw: [raw.decode("utf-8")])
        orig = V.install(mod)
        V.install(mod)  # idempotent
        self.assertIs(mod.decode_payload.__wrapped__, orig)
        out = mod.decode_payload(vot(ONE_INT, '<TABLEDATA><TR><TD>3</TD></TR></TABLEDATA>').encode())
        self.assertEqual(out, ["n\n3\n"])
        self.assertEqual(mod.decode_payload(b"a,b\n1,2\n"), ["a,b\n1,2\n"])
        self.assertTrue(V.looks_like_votable(HEAD))
        self.assertFalse(V.looks_like_votable("source_id,time\n1,2\n"))


if __name__ == "__main__":
    unittest.main()
