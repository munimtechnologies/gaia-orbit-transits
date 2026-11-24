# SPDX-License-Identifier: Apache-2.0
"""Tests for sb2_ecl_dr4 0.1.0 (gaia-orbit-transits step g8; MV2 of Munim, Inc.; made with AI
agents). Pure functions and synthetic light curves only; no network."""
import io
import math
import unittest
import zipfile

import sb2_ecl_dr4 as g8


def rec(**kw):
    base = {"status": "OK", "G": 10.0, "gaia_eb": False, "gaia_ecl_sol": False,
            "gaia_class_ecl": False, "vsx_ecl": False, "simbad_eb": False, "tessebs_viz": False,
            "t10k_viz": False, "a_label": "NONE", "a_null_label": "NONE", "a_n_dips": 0,
            "a_n_in": 0}
    base.update(kw)
    return base


class TestRule(unittest.TestCase):
    def test_self_test(self):
        ok, bad = g8.self_test()
        self.assertTrue(ok, "failed checks %s" % bad)

    def test_eclipsing_and_null(self):
        t, m = g8.synth(11, depth1=0.4, depth2=0.2)
        self.assertEqual(g8.classify(t, m, 3.0, 0.0, None, None)["label"], "ECL_GAIA")
        self.assertNotEqual(g8.classify(t, m, 3.0, 0.0, None, None, shift=0.25)["label"],
                            "ECL_GAIA")

    def test_wrong_reference_time_loses_eclipses(self):
        # a reference time off by a quarter period puts the eclipses at quadrature
        t, m = g8.synth(12, depth1=0.4, depth2=0.2)
        self.assertNotEqual(g8.classify(t, m, 3.0, 0.75, None, None)["label"], "ECL_GAIA")

    def test_ellipsoidal_is_not_an_eclipse(self):
        t, m = g8.synth(13, ell=0.06, noise=0.003)
        self.assertEqual(g8.classify(t, m, 3.0, 0.0, None, None)["label"], "NONE")

    def test_eccentric_conjunctions(self):
        c1, c2 = g8.conjunction_phases(0.3, 90.0)
        # omega = 90: conjunctions at periastron and apastron, half a period apart
        self.assertAlmostEqual(c1, 0.0, places=9)
        self.assertAlmostEqual((c2 - c1) % 1.0, 0.5, places=6)
        # omega = 0: conjunctions at true anomaly 90 and 270 deg, not half a period apart
        c1, c2 = g8.conjunction_phases(0.3, 0.0)
        self.assertAlmostEqual(c1, 0.156, places=2)
        self.assertAlmostEqual(c1 + c2, 1.0, places=9)
        self.assertNotAlmostEqual((c2 - c1) % 1.0, 0.5, places=2)

    def test_few_epochs(self):
        t, m = g8.synth(14, n_pairs=9)
        self.assertEqual(g8.classify(t, m, 3.0, 0.0, None, None)["label"], "FEW_EPOCHS")


class TestHelpers(unittest.TestCase):
    def test_auc(self):
        auc, p = g8.auc_greater([3.0, 4.0], [1.0, 2.0])
        self.assertAlmostEqual(auc, 1.0)
        auc, _ = g8.auc_greater([1.0, 2.0], [1.0, 2.0])
        self.assertAlmostEqual(auc, 0.5)
        self.assertTrue(math.isnan(g8.auc_greater([], [1.0])[0]))

    def test_wilson(self):
        lo, hi = g8.wilson(86, 111)
        self.assertAlmostEqual(lo, 0.6886, places=3)
        self.assertAlmostEqual(hi, 0.8425, places=3)

    def test_chunks_cover(self):
        ids = [str(1000003 * i + 7) for i in range(400)]
        seen = {g8.chunk_of(s, 8) for s in ids}
        self.assertEqual(seen, set(range(8)))

    def test_zip_payload(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("EPOCH_PHOTOMETRY-1.csv", "band,time,mag\nG,1.0,10.0\nRP,1.0,9.0\n")
        texts = g8.decode_payload(buf.getvalue())
        self.assertEqual(g8.parse_epoch_csv(texts[0]), [(1.0, 10.0, False)])

    def test_masses_table(self):
        self.assertEqual(g8.masses_table({"nss_masses": {"source_id", "m1"}}), "nss_masses")
        self.assertEqual(g8.masses_table({"binary_masses": {"source_id", "m1"}}), "binary_masses")
        self.assertIsNone(g8.masses_table({}))

    def test_schema_gate(self):
        cols = {"nss_two_body_orbit": set(g8.REQ_ORB), "gaia_source": set(g8.REQ_GS)}
        self.assertEqual(g8.schema_gate(cols), "OK")
        self.assertEqual(g8.schema_gate({"gaia_source": set(g8.REQ_GS)}), "G0")


class TestGrades(unittest.TestCase):
    def test_vet_status(self):
        self.assertEqual(g8.vet_status(rec()), "NEW")
        self.assertEqual(g8.vet_status(rec(gaia_eb=True)), "KNOWN")
        self.assertEqual(g8.vet_status(rec(vsx_ecl=None)), "UNVETTED")
        self.assertEqual(g8.vet_status(rec(vsx_ecl=None, simbad_eb=True)), "KNOWN")

    def test_blind(self):
        self.assertIs(g8.blind_of(rec(G=14.0)), True)
        self.assertIs(g8.blind_of(rec(G=12.0, crowd=0.8)), True)
        self.assertIs(g8.blind_of(rec(G=12.0, crowd=0.1)), False)
        self.assertIsNone(g8.blind_of(rec(G=12.0)))

    def test_grade_all(self):
        recs = [rec(source_id=str(i), gaia_eb=True, a_label="ECL_GAIA", a_n_dips=3, a_n_in=3)
                for i in range(25)]
        recs += [rec(source_id=str(100 + i), G=15.0, a_label="ECL_GAIA") for i in range(3)]
        recs += [rec(source_id="200", G=15.0, a_label="ECL_GAIA", vsx_ecl=None)]
        recs += [rec(source_id=str(300 + i), G=12.0) for i in range(10)]
        recs += [rec(source_id="400", status="ERROR")]
        g = g8.grade_all(recs)
        self.assertEqual(g["ref"], "a")
        self.assertTrue(g["interpreted"])
        self.assertEqual(g["T0"]["a"]["label"], "TIME_OK")
        self.assertEqual(g["T0"]["b"]["label"], "UNTESTABLE")
        self.assertEqual(g["R1"]["label"], "RECALL_OK")
        self.assertEqual(g["N1"]["label"], "NULL_OK")
        self.assertEqual(g["B1"]["label"], "PRECISION_OK")
        self.assertEqual(g["M1"]["label"], "UNTESTABLE")
        self.assertEqual(g["MAIN"]["n_new"], 3)
        self.assertEqual(g["MAIN"]["n_unvetted"], 1)
        self.assertEqual(g["MAIN"]["label"], "FEW")
        self.assertEqual(g["counts"]["n_tested"], 39)


if __name__ == "__main__":
    unittest.main()
