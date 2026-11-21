# SPDX-License-Identifier: Apache-2.0
"""Tests for vpt_epochs 0.1.0 (stdlib; numpy tests skip when numpy is missing)."""
import io
import math
import unittest
import zipfile

import vpt_epochs as ve

try:
    import numpy  # noqa: F401
    HAVE_NP = True
except ImportError:
    HAVE_NP = False

LONG = """# a comment
source_id,transit_id,band,time,mag,flux,flux_error,flux_over_error,rejected_by_photometry,rejected_by_variability,other_flags,solution_id
111,1,G,1700.5,12.0,1000.0,1.0,1000,false,false,0,1
111,1,BP,1700.5,12.3,800.0,1.0,800,false,false,0,1
111,2,G,1701.5,12.0,990.0,1.0,990,false,true,0,1
111,3,G,1702.5,12.0,1001.0,1.0,1001,true,false,0,1
111,4,G,1703.5,12.0,null,1.0,,false,false,0,1
"""

WIDE = ('solution_id,source_id,n_transits,g_transit_time,g_transit_flux,g_transit_flux_error,'
        'variability_flag_g_reject\n'
        '1,222,3,"[1700.1, 1700.2, 1700.3]","[10.0, 9.0, null]","[0.1, 0.1, 0.1]",'
        '"[false, true, false]"\n')


class TestParsing(unittest.TestCase):
    def test_parse_array(self):
        v = ve.parse_array('"[1.0, 2.5, null, NaN]"')
        self.assertEqual(v[:2], [1.0, 2.5])
        self.assertTrue(math.isnan(v[2]) and math.isnan(v[3]))
        self.assertEqual(ve.parse_array(""), [])
        self.assertEqual(ve.parse_bool_array("[true, false]"), [True, False])

    def test_long(self):
        out = ve.parse_epoch_text(LONG)
        r = out["111"]
        self.assertEqual(len(r["t"]), 4)            # BP dropped
        self.assertEqual(r["rej"], [False, True, True, False])
        t, f, e, nrej = ve.clean_epochs(r)
        self.assertEqual(t, [1700.5])
        self.assertEqual(nrej, 2)

    def test_wide(self):
        out = ve.parse_epoch_text(WIDE)
        r = out["222"]
        self.assertEqual(r["t"], [1700.1, 1700.2, 1700.3])
        t, f, e, nrej = ve.clean_epochs(r)
        self.assertEqual(t, [1700.1])
        self.assertEqual(nrej, 1)

    def test_zip_payload(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("EPOCH_PHOTOMETRY-Gaia DR3 111.csv", LONG)
            z.writestr("EPOCH_PHOTOMETRY-Gaia DR3 222.csv", WIDE)
        out = ve.parse_datalink_payload(buf.getvalue())
        self.assertEqual(sorted(out), ["111", "222"])
        out2 = ve.parse_datalink_payload(LONG.encode())
        self.assertIn("111", out2)

    def test_hint_sid(self):
        txt = "time,flux,flux_error,band\n1.0,5.0,0.1,G\n"
        out = ve.parse_epoch_text(txt, hint_sid="999")
        self.assertIn("999", out)

    def test_catalogues(self):
        arch = ("pl_name,tic_id,pl_orbper,pl_orbpererr1,pl_tranmid,pl_tranmiderr1,pl_trandur\n"
                "WASP-4 b,TIC 402026209,1.338231,1e-7,2455804.5157,0.0001,2.16\n")
        a = ve.parse_exoarch_eph(arch)
        e = a["402026209"][0]
        self.assertAlmostEqual(e["T0g"], 2455804.5157 - 2455197.5, places=6)
        self.assertAlmostEqual(e["dur"], 0.09, places=6)
        toi = ('TIC ID,TOI,TFOPWG Disposition,Epoch (BJD),Epoch (BJD) err,Period (days),'
               'Period (days) err,Duration (hours)\n'
               '402026209,232.01,KP,2459000.1,0.001,1.3382,0.00001,2.1\n'
               '402026209,232.02,PC,2459000.2,0.001,7.5,0.0001,3.0\n'
               '55,9.01,FP,2459000.2,0.001,7.5,0.0001,3.0\n')
        t = ve.parse_toi_eph(toi)
        self.assertNotIn("55", t)
        m = ve.merge_ephs(a, t)
        names = [x["name"] for x in m["402026209"]]
        self.assertEqual(names, ["WASP-4 b", "TOI-232.02"])
        self.assertEqual(ve.norm_tic("TIC 000123"), "123")
        self.assertEqual(ve.norm_tic("123.0"), "123")


class TestGeometry(unittest.TestCase):
    def test_phase_sets(self):
        t = [0.0, 0.05, 1.0, 2.02, 3.5, 10.0]
        d = ve.phase_dist(t, 0.0, 1.0)
        self.assertAlmostEqual(d[3], 0.02, places=9)
        self.assertAlmostEqual(d[4], 0.5, places=9)
        self.assertEqual(ve.window_set(t, 0.0, 1.0, 0.03), [0, 2, 3, 5])
        self.assertEqual(ve.nearest_k(t, 0.0, 1.0, 2), [0, 2])

    def test_classify(self):
        self.assertEqual(ve.classify_why(True, 4, 4, 3), "ALIAS")
        self.assertEqual(ve.classify_why(True, 4, 4, 2), "ALIAS")
        self.assertEqual(ve.classify_why(True, 4, 4, 1), "PARTIAL")
        self.assertEqual(ve.classify_why(True, 4, 4, 0), "UNRELATED")
        self.assertEqual(ve.classify_why(True, 1, 4, 1), "UNTESTABLE")
        self.assertEqual(ve.classify_why(False, 5, 5, 5), "UNTESTABLE")

    def test_eph_sigma(self):
        e = ve._mk_eph("x", "archive", 2.0, 1e-5, 2457000.0, 1e-3, 2.4)
        s = ve.eph_sigma(e, e["T0g"] - 1000.0)
        self.assertAlmostEqual(s, math.sqrt((500 * 1e-5) ** 2 + 1e-6), places=9)
        e2 = ve._mk_eph("y", "archive", 2.0, float("nan"), 2457000.0, 1e-3, 2.4)
        self.assertTrue(math.isnan(ve.eph_sigma(e2, 0.0)))

    def test_depth(self):
        fn = [1.0] * 20 + [0.99] * 4
        d, s = ve.set_depth_snr(fn, [20, 21, 22, 23], 0.001)
        self.assertAlmostEqual(d, 0.01, places=9)
        self.assertGreater(s, 10)

    def test_analyse_control_and_alias(self):
        # 400 epochs, every ~1.37 d; true P = 3.0, T0 = 0.0, dur 0.3 d
        t = [i * 1.37 + 0.001 * (i % 7) for i in range(400)]
        P, dur = 3.0, 0.3
        intr = set(ve.window_set(t, 0.0, P, dur / 2))
        fl = [990.0 if i in intr else 1000.0 + (i % 3) for i in range(len(t))]
        eph = ve._mk_eph("A b", "archive", P, 1e-7, 0.0 + ve.GAIA_T_OFFSET, 1e-4, dur * 24)
        tg = {"source_id": "5", "category": "KNOWN_PLANET", "category_detail": "", "tic": "9",
              "G": 12.0, "P_gaia": P, "T0_gaia": 0.0, "dur_gaia": dur,
              "num_in_transit": len(intr)}
        r = ve.analyse_epochs(tg, t, fl, [eph])
        self.assertEqual(r["status"], "OK")
        self.assertEqual(r["why_label"], "ALIAS")
        self.assertEqual(r["match_factor"], 1.0)
        self.assertAlmostEqual(r["purity"], 1.0)
        tg2 = dict(tg, category="KNOWN_SYSTEM_OTHER_P", P_gaia=7.77, T0_gaia=1.1)
        r2 = ve.analyse_epochs(tg2, t, fl, [eph])
        self.assertIn(r2["why_label"], ("PARTIAL", "UNRELATED"))
        r3 = ve.analyse_epochs(tg, t[:10], fl[:10], [eph])
        self.assertEqual(r3["status"], "FEW_EPOCHS")
        r4 = ve.analyse_epochs(tg, t, fl, [])
        self.assertEqual(r4["status"], "NO_EPHEMERIS")


class TestStats(unittest.TestCase):
    def test_wilson(self):
        p, lo, hi = ve.wilson(5, 10)
        self.assertAlmostEqual(p, 0.5)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)
        self.assertTrue(math.isnan(ve.wilson(0, 0)[0]))

    def test_mann_whitney(self):
        auc, p = ve.mann_whitney_low([1, 2, 3], [10, 11, 12, 13])
        self.assertEqual(auc, 1.0)
        self.assertLess(p, 0.05)
        auc2, p2 = ve.mann_whitney_low([5, 5], [5, 5])
        self.assertEqual(auc2, 0.5)
        auc3, p3 = ve.mann_whitney_low([10, 11], [1, 2, 3])
        self.assertEqual(auc3, 0.0)
        self.assertGreater(p3, 0.5)

    def test_cdn_index(self):
        md5 = ("75c2  EpochPhotometry_000000-003111.csv.gz\n"
               "7866  EpochPhotometry_003112-005263.csv.gz\n")
        idx = ve.cdn_index(md5)
        self.assertEqual(idx[0], (0, 3111, "EpochPhotometry_000000-003111.csv.gz"))
        sid = 3200 * 2 ** 35 + 12345
        self.assertEqual(ve.healpix8(sid), 3200)
        self.assertEqual(ve.cdn_file_for(sid, idx), "EpochPhotometry_003112-005263.csv.gz")
        self.assertIsNone(ve.cdn_file_for(9999 * 2 ** 35, idx))

    def _rec(self, cat, label, purity=1.0, mf=1.0, ncomp=1, snr_t=5.0):
        r = {k: "" for k in ve.STAR_KEYS}
        r.update({"status": "OK", "category": cat, "why_label": label, "purity": purity,
                  "match_factor": mf, "eph_testable": True, "n_t": 3, "n_g": 3,
                  "n_comp": ncomp, "snr_t": snr_t, "gaia_within_frac": 1.0})
        return r

    def test_grade(self):
        recs = [self._rec("KNOWN_PLANET", "ALIAS", ncomp=i % 3) for i in range(10)]
        recs += [self._rec("KNOWN_SYSTEM_OTHER_P", "ALIAS", purity=0.6, mf="", ncomp=20 + i)
                 for i in range(15)]
        recs += [self._rec("KNOWN_SYSTEM_OTHER_P", "UNRELATED", purity=0.0, mf="", ncomp=30)
                 for i in range(5)]
        g = ve.grade(recs)
        self.assertEqual(g["T1"]["label"], "TIME_OK")
        self.assertEqual(g["WHY"]["n_testable"], 20)
        self.assertEqual(g["WHY"]["alias"], 15)
        self.assertEqual(g["WHY"]["label"], "ALIAS_DOMINATED")
        self.assertEqual(g["T3"]["label"], "PREDICTIVE")
        bad = [self._rec("KNOWN_PLANET", "UNRELATED", purity=0.0, ncomp=1) for _ in range(10)]
        g2 = ve.grade(bad + recs[10:])
        self.assertEqual(g2["T1"]["label"], "TIME_BAD")
        self.assertEqual(g2["WHY"]["label"], "INVALID")


@unittest.skipUnless(HAVE_NP, "numpy not installed")
class TestNumpy(unittest.TestCase):
    def test_box_snr_matches_brute_force(self):
        import numpy as np
        rng = np.random.default_rng(3)
        t = np.sort(rng.uniform(0, 500, 80))
        f = 1 + rng.normal(0, 0.002, t.size)
        x = (t - 1.0) / 2.5
        f[np.abs((x - np.round(x)) * 2.5) < 0.1] -= 0.01
        for fr in (1 / 2.5, 1 / 3.7, 1 / 0.6):
            fast = float(ve.box_snr(t, f, [fr], 0.2)[0])
            ph = np.mod(t * fr, 1.0)
            y = 1 - f
            sd = 1.4826 * np.median(np.abs(y - np.median(y)))
            best = -np.inf
            for p0 in ph:
                m = np.mod(ph - p0, 1.0) < min(0.2 * fr, 0.5)
                if m.sum() >= ve.NIN_MIN and (~m).sum() >= 3:
                    best = max(best, (y[m].mean() - y[~m].mean())
                               / (sd * np.sqrt(1 / m.sum() + 1 / (~m).sum())))
            self.assertAlmostEqual(fast, best, places=6)

    def test_competitors(self):
        import numpy as np
        freqs = np.linspace(0.1, 1.0, 100)
        snr = np.zeros(100)
        snr[10], snr[50], snr[51], snr[90] = 10, 9.5, 9.6, 5
        n, fa = ve.count_competitors(freqs, snr, freqs[10], 10.0)
        self.assertEqual(n, 1)
        self.assertAlmostEqual(fa, 0.01)

    def test_self_test(self):
        self.assertTrue(ve.self_test())


if __name__ == "__main__":
    unittest.main()
