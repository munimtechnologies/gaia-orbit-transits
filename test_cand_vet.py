# SPDX-License-Identifier: Apache-2.0
"""Offline tests for cand_vet 0.3.0 (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents)."""
import io
import unittest
import zipfile

import cand_vet as m


class TestScan(unittest.TestCase):
    def test_scan_tic_csv(self):
        lines = ["TIC,period,depth_1\n", "173207470,3.05,0.07\n", "1,2,3\n", "\n",
                 "57791790.0,3.08,0.04\n", "bad,1,1\n"]
        header, hits, n = m.scan_tic_csv(iter(lines), {173207470, 57791790, 999})
        self.assertEqual(header, ["TIC", "period", "depth_1"])
        self.assertEqual(n, 4)
        self.assertEqual(sorted(hits), [57791790, 173207470])

    def test_token_hits_whole_numbers_only(self):
        text = "a,1384284045\nb,384284045,c\nTIC 384284045\n3842840450"
        h = m.token_hits(text, ["384284045", "57791790"])
        self.assertEqual(h, {"384284045": [2, 3]})

    def test_tokens_for(self):
        tok = m.tokens_for(m.TARGETS)
        self.assertEqual(tok["189269584"], "CD-28 7251")
        self.assertEqual(tok["5633392634307163776"], "CD-28 7251")
        self.assertEqual(tok["3350075697770930304"], "TYC 1316-1554-1")
        self.assertEqual(tok["1021067547"], "HD 125386A")
        self.assertEqual(tok["430687563"], "TYC 3614-1907-1")
        self.assertEqual(tok["2000830001125603968"], "TYC 3614-1907-1")
        self.assertEqual(tok["300539729"], "BD+12 3880")
        self.assertEqual(tok["4318964656978448768"], "BD+12 3880")
        self.assertEqual(len(m.TARGETS), 22)
        self.assertEqual(len(tok), len({t for t in tok}))

    def test_is_text(self):
        self.assertTrue(m.is_text("CHECKCARD.csv"))
        self.assertTrue(m.is_text("reviews/x/README.md"))
        self.assertTrue(m.is_text("paper.HTML"))
        self.assertFalse(m.is_text("paper.pdf"))
        self.assertFalse(m.is_text("figs/a.png"))


def _zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("repo-abc/", "")
        for name, text in files.items():
            z.writestr("repo-abc/" + name, text)
    buf.seek(0)
    return buf


class TestZip(unittest.TestCase):
    def test_scan_zip(self):
        z = _zip({"CHECKCARD.csv": "label,TIC\nB7,189269584,CD-28 7251\nB6,464315748\n",
                  "reviews/r/README.md": "Gaia DR3 5633392634307163776 here\n",
                  "paper.pdf": "189269584",
                  "accepted-systems.csv": "A179,384284045\n"})
        res = m.scan_zip(z, ["189269584", "464315748", "384284045", "5633392634307163776",
                             "400170926"])
        self.assertEqual(res["n_blobs"], 4)
        self.assertEqual(res["n_text"], 3)
        self.assertEqual(res["n_scanned"], 3)
        self.assertEqual(res["hits"]["189269584"][0]["file"], "CHECKCARD.csv")
        self.assertEqual(res["hits"]["189269584"][0]["lines"], [2])
        self.assertEqual(res["hits"]["5633392634307163776"][0]["file"], "reviews/r/README.md")
        self.assertNotIn("400170926", res["hits"])
        self.assertEqual(len(res["hits"]["189269584"]), 1)  # the pdf is not read


class TestTree(unittest.TestCase):
    def test_list_blobs_completes_truncated_tree(self):
        trees = {
            "root?recursive=1": {"truncated": True, "tree": []},
            "root": {"tree": [{"type": "blob", "path": "a.csv", "size": 5},
                              {"type": "tree", "path": "reviews", "sha": "rv"}]},
            "rv?recursive=1": {"truncated": False,
                               "tree": [{"type": "tree", "path": "x"},
                                        {"type": "blob", "path": "x/b.md", "size": 7}]},
        }

        def getj(url):
            return trees[url.rsplit("/", 1)[1]]

        blobs, calls = m.list_blobs("root", getj)
        self.assertEqual(sorted(blobs), [("a.csv", 5), ("reviews/x/b.md", 7)])
        self.assertEqual(calls, 3)


class TestGrade(unittest.TestCase):
    def _v(self, listed_eba=(), listed_obaf=()):
        eba_hits = {}
        for label, tic, gid, _ in m.TARGETS:
            if label in listed_eba:
                eba_hits[str(tic) if tic else gid] = [{"file": "CHECKCARD.csv"}]
        obaf = {str(tic): [{}] for label, tic, _, _ in m.TARGETS if label in listed_obaf and tic}
        return m.verdicts(m.TARGETS, eba_hits, obaf)

    def test_controls_and_claims(self):
        v = self._v(listed_eba=("TYC 3616-2395-1", "CD-28 7251", "HD 171459", "TYC 3384-347-1"),
                    listed_obaf=("RS Cha",))
        eba = {"n_scanned": 10, "n_text": 11, "skipped_large": [["big.csv", 1]], "errors": {}}
        g = m.grade(v, eba, True)
        self.assertEqual(g["V0_controls"], "CONTROLS_OK")
        self.assertEqual(g["V1_complete"], "SCAN_COMPLETE")
        self.assertEqual(g["V2_claims"], "CLAIMS_UNLISTED")
        self.assertEqual(g["V3_sb1_listed"], ["TYC 3384-347-1"])
        self.assertEqual(g["V4_transit_listed"], [])
        self.assertEqual(g["V5_tier2_listed"], [])

    def test_tier2_listed(self):
        v = self._v(listed_eba=("TYC 3614-1907-1",), listed_obaf=("BD+12 3880",))
        g = m.grade(v, {"n_scanned": 1, "n_text": 1, "skipped_large": [], "errors": {}}, True)
        self.assertEqual(g["V5_tier2_listed"], ["TYC 3614-1907-1", "BD+12 3880"])

    def test_control_fail_and_claim_listed(self):
        v = self._v(listed_eba=("TYC 3616-2395-1", "CD-28 7251", "HD 11239"), listed_obaf=("ZZ Boo",))
        g = m.grade(v, {"n_scanned": 3, "n_text": 4, "skipped_large": [], "errors": {}}, True)
        self.assertEqual(g["V0_controls"], "CONTROL_FAIL")  # HD 171459 control missing
        self.assertEqual(g["V1_complete"], "SCAN_INCOMPLETE")
        self.assertEqual(g["V2_claims"], "CLAIM_LISTED")
        self.assertEqual(g["V2_listed"], ["HD 11239"])

    def test_no_obaf(self):
        v = m.verdicts(m.TARGETS, {}, None)
        self.assertIsNone(v["HD 250735"]["in_ijspeert2024_eb"])
        g = m.grade(v, {}, False)
        self.assertEqual(g["V0_controls"], "CONTROL_FAIL")


if __name__ == "__main__":
    unittest.main()
