# SPDX-License-Identifier: Apache-2.0
"""Tests for dr4_datamodel.py (MV2 of Munim, Inc.; made with AI agents)."""
import io
import json
import os
import tempfile
import unittest
import zipfile

import dr4_datamodel as dm


class TestDataModel(unittest.TestCase):
    def test_strip_html(self):
        s = dm.strip_html("<html><style>x{}</style><table><tr><td>corr_vec</td><td>float[]</td>"
                          "</tr></table><p>a &amp; b</p></html>")
        self.assertIn("corr_vec", s)
        self.assertIn("a & b", s)
        self.assertNotIn("<", s)
        self.assertNotIn("x{}", s)

    def test_contexts(self):
        text = "\n".join(["l%d" % i for i in range(20)] + ["the corr_vec order"] + ["m"] * 5)
        c = dm.contexts(text, ["CORR_VEC"], width=1)
        self.assertEqual(len(c), 1)
        self.assertIn("l19", c[0])
        self.assertIn("corr_vec", c[0])

    def test_run_on_small_zip(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("dm/nss_two_body_orbit.html",
                       "<p>inclination</p><p>corr_vec: period, t_periastron</p>")
            z.writestr("dm/gaia_source.html", "<p>ra</p><p>J2017.5 reference epoch</p>")
            z.writestr("dm/readme.bin", b"\x00\x01")
        with tempfile.TemporaryDirectory() as d:
            s = dm.run(buf.getvalue(), d)
            self.assertEqual(s["members"], 3)
            self.assertEqual(s["picked"], ["dm/nss_two_body_orbit.html"])
            files = os.listdir(os.path.join(d, "dm"))
            self.assertTrue(any(f.endswith(".txt") for f in files))
            g = open(os.path.join(d, "grep_context.txt"), encoding="utf-8").read()
            self.assertIn("corr_vec", g)
            self.assertIn("J2017.5", g)
            self.assertTrue(json.load(open(os.path.join(d, "summary.json"))))


if __name__ == "__main__":
    unittest.main()
