# SPDX-License-Identifier: Apache-2.0
"""Tests for dr4_datamodel.py 0.2.0 (MV2 of Munim, Inc.; made with AI agents). Stdlib only."""
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

    def test_contexts_no_cap(self):
        text = "\n".join(["corr_vec %d" % i if i % 10 == 0 else "x" for i in range(10000)])
        self.assertEqual(len(dm.contexts(text, ["corr_vec"], width=1, limit=0)), 1000)

    def test_split_parts_roundtrip(self):
        text = "".join("line %05d %s\n" % (i, "y" * (i % 37)) for i in range(5000))
        parts = dm.split_parts(text, size=1000)
        self.assertEqual("".join(parts), text)
        self.assertTrue(all(len(p) <= 1000 for p in parts))
        self.assertTrue(all(p.endswith("\n") for p in parts))
        self.assertEqual(dm.split_parts("", 10), [])
        self.assertEqual("".join(dm.split_parts("a" * 25, 10)), "a" * 25)

    def test_toc_and_sections(self):
        text = "\n".join([
            "17.6 rvs_two_body_orbit . . . . . . . . . 1012",
            "17.7 xp_epoch_crowding . . . . . . . . . 1022",
            "intro text",
            "17.6 rvs_two_body_orbit",
            "period : Orbital period (double)",
            "3.4 mag",
            "corr_vec : correlation vector",
            "17.7 xp_epoch_crowding",
            "other",
        ])
        toc = dm.toc_tables(text)
        self.assertEqual([t[1] for t in toc], ["rvs_two_body_orbit", "xp_epoch_crowding"])
        self.assertEqual(toc[0][2], 1012)
        names = {t[1] for t in toc}
        sec = dm.sections(text, names, names)
        self.assertIn("rvs_two_body_orbit", sec)
        body = sec["rvs_two_body_orbit"]
        self.assertIn("corr_vec", body)          # '3.4 mag' did not cut it short
        self.assertNotIn("other", body)
        self.assertNotIn(". . .", body)          # the TOC line is not the section

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
            self.assertEqual(len(s["full_text_parts"]), 2)
            self.assertTrue(os.path.exists(os.path.join(d, "full", s["full_text_parts"][0])))
            g = open(os.path.join(d, "grep_context.txt"), encoding="utf-8").read()
            self.assertIn("corr_vec", g)
            self.assertIn("J2017.5", g)
            self.assertTrue(json.load(open(os.path.join(d, "summary.json"))))


if __name__ == "__main__":
    unittest.main()
