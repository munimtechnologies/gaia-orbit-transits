# SPDX-License-Identifier: Apache-2.0
"""Tests for vpt_pf 0.1.0 (stdlib only). MV2 of Munim, Inc.; made with AI agents."""
import json
import os
import shutil
import tempfile
import unittest

import vpt_pf as m


PLANETS = {"123": [("X b", 2.5), ("X c", 40.0)], "500": [("Y b", 20.0)]}
TOIS = {"123": [{"toi": "9.01", "disp": "KP", "period": "2.5"}],
        "77": [{"toi": "8.01", "disp": "FP", "period": "1.2"}],
        "88": [{"toi": "7.01", "disp": "PC", "period": ""}]}


def rec(label, snr, p_tess, p_gaia, tic="", sid="1", agree=0):
    return {"label": label, "snr": snr, "P_tess": p_tess, "P_gaia": p_gaia, "tic": tic,
            "source_id": sid, "n_sector_agree": agree, "n_sectors_used": 3}


class Helpers(unittest.TestCase):
    def test_norm_tic(self):
        self.assertEqual(m.norm_tic("TIC 00123"), "123")
        self.assertEqual(m.norm_tic(123), "123")
        self.assertEqual(m.norm_tic("123.0"), "123")
        self.assertEqual(m.norm_tic(None), "")

    def test_known_periods(self):
        k = m.known_periods("123", PLANETS, TOIS)
        self.assertEqual(len(k), 3)
        self.assertEqual(m.known_periods("77", PLANETS, TOIS), [("TOI-8.01 FP", 1.2)])
        self.assertEqual(m.known_periods("88", PLANETS, TOIS), [])
        self.assertEqual(m.known_periods("", PLANETS, TOIS), [])

    def test_match_period(self):
        k = [("a", 2.0)]
        self.assertEqual(m.match_period(2.019, k, (1.0,))[2], 1.0)
        self.assertIsNone(m.match_period(2.03, k, (1.0,)))
        self.assertEqual(m.match_period(1.0, k, m.HARMONICS)[2], 0.5)
        self.assertEqual(m.match_period(6.0, k, m.HARMONICS)[2], 3.0)
        self.assertIsNone(m.match_period(float("nan"), k, (1.0,)))
        self.assertIsNone(m.match_period("", k, (1.0,)))

    def test_in_range(self):
        self.assertTrue(m.has_in_range([("a", 2.0), ("b", 40.0)]))
        self.assertFalse(m.has_in_range([("b", 40.0)]))

    def test_pf_class(self):
        k = [("a", 2.0)]
        self.assertEqual(m.pf_class(rec("SURVIVES", 10.0, 2.0, 2.0), k), "KNOWN_RECOVERED")
        self.assertEqual(m.pf_class(rec("SURVIVES", 10.0, 4.0, 4.0), k), "KNOWN_HARMONIC")
        self.assertEqual(m.pf_class(rec("SURVIVES", 10.0, 2.7, 2.7), k), "KNOWN_OTHER_P")
        self.assertEqual(m.pf_class(rec("NOT_DETECTED", 5.0, 2.0, 2.0), k),
                         "KNOWN_NOT_DETECTED")
        self.assertEqual(m.pf_class(rec("EB_LIKE", 30.0, 3.0, 3.0), []), "NEW_EB_LIKE")
        self.assertEqual(m.pf_class(rec("NO_TESS", "", "", 3.0), k), "NO_TESS")
        self.assertEqual(m.pf_class(rec("ERROR", "", "", 3.0), k), "ERROR")
        self.assertEqual(m.pf_class(rec("", "", "", 3.0), []), "NO_TESS")

    def test_annotate(self):
        k = m.known_periods("123", PLANETS, TOIS)
        r = m.annotate(rec("SURVIVES_OTHER_P", 12.0, 2.51, 1.7, "123"), k, "KNOWN_SYSTEM_OTHER_P")
        self.assertEqual(r["pf_class"], "KNOWN_RECOVERED")
        self.assertIs(r["gaia_right"], False)
        self.assertIs(r["has_known_in_range"], True)
        self.assertEqual(r["tess_match_factor"], 1.0)
        r = m.annotate(rec("SURVIVES", 9.0, 3.3, 3.3), [])
        self.assertIsNone(r["gaia_right"])
        self.assertEqual(r["pf_class"], "NEW_SURVIVES")
        k5 = m.known_periods("500", PLANETS, TOIS)
        r = m.annotate(rec("SURVIVES", 9.0, 3.3, 3.3, "500"), k5)
        self.assertIs(r["has_known_in_range"], False)

    def test_labels(self):
        self.assertEqual(m.ratio_label(5, 10), "UNTESTABLE")
        self.assertEqual(m.ratio_label(12, 20), "PF_RECOVERS")
        self.assertEqual(m.ratio_label(11, 20), "PF_PARTIAL")
        self.assertEqual(m.ratio_label(6, 20), "PF_PARTIAL")
        self.assertEqual(m.ratio_label(5, 20), "PF_FAILS")
        lo, hi = m.wilson(15, 176)
        self.assertAlmostEqual(lo, 0.052, places=2)
        self.assertAlmostEqual(hi, 0.136, places=2)

    def test_order_ids(self):
        ids = [str(i) for i in range(50)]
        a = m.order_ids(ids, 4, 0)
        self.assertEqual(a, m.order_ids(list(reversed(ids)), 4, 0))
        allc = sum((m.order_ids(ids, 4, c) for c in range(4)), [])
        self.assertEqual(sorted(allc), sorted(ids))
        self.assertEqual(len(m.order_ids(ids)), 50)

    def test_grade(self):
        k = [("a", 2.0)]
        recs = []
        for i in range(25):   # known, Gaia wrong, recovered
            recs.append(m.annotate(rec("SURVIVES_OTHER_P", 20.0, 2.0, 1.3, sid="r%d" % i), k))
        for i in range(5):    # known, Gaia right, other period
            recs.append(m.annotate(rec("SURVIVES_OTHER_P", 20.0, 2.9, 2.0, sid="o%d" % i), k))
        recs.append(m.annotate(rec("SURVIVES_OTHER_P", 11.0, 4.4, 1.1, sid="n1", agree=2), []))
        recs.append(m.annotate(rec("SURVIVES", 8.0, 1.1, 1.1, sid="n2", agree=1), []))
        recs.append(m.annotate(rec("EB_LIKE", 30.0, 3.0, 3.0, sid="n3"), []))
        g = m.grade(recs)
        self.assertEqual(g["PF1"]["n"], 30)
        self.assertEqual(g["PF1"]["k"], 25)
        self.assertEqual(g["PF1"]["label"], "PF_RECOVERS")
        self.assertEqual(g["PF1b"]["n"], 25)
        self.assertEqual(g["PF1b"]["k"], 25)
        self.assertAlmostEqual(g["PF_WRONG"]["rate"], 5 / 30)
        self.assertTrue(g["PF_WRONG"]["pf2_reliable"])
        self.assertEqual(g["PF2"]["n_planet_like"], 2)
        self.assertEqual(g["PF2"]["n_robust"], 1)
        self.assertEqual(g["PF2"]["list"][0]["source_id"], "n1")
        self.assertEqual(len(g["gaia_period_fixed"]), 25)
        self.assertEqual(g["classes"]["NEW_EB_LIKE"], 1)

    def test_checkpoint_roundtrip(self):
        d = tempfile.mkdtemp()
        try:
            e = {"rec": {"source_id": "42", "label": "SURVIVES", "snr": float("nan"),
                         "has_known_in_range": True}, "sectors": []}
            m.save_ckpt(d, "42", e)
            m.save_ckpt(d, "43", {"rec": {"source_id": "43", "label": "ERROR"}})
            got = m.load_ckpt(d)
            self.assertEqual(list(got), ["42"])
            self.assertIsNone(got["42"]["rec"]["snr"])
            self.assertIs(got["42"]["rec"]["has_known_in_range"], True)
            with open(os.path.join(d, "42.json"), encoding="utf-8") as fh:
                json.load(fh)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(m.load_ckpt(None), {})

    def test_self_test_pure_part(self):
        k = m.known_periods("TIC 0123", PLANETS, TOIS)
        r = m.annotate(rec("SURVIVES", 9.0, 5.0, 5.0), k)
        self.assertEqual(r["pf_class"], "KNOWN_HARMONIC")


if __name__ == "__main__":
    unittest.main()
