# Tests for tyc_period.py 0.1.0 (pure standard library). By MV2 of Munim, Inc.; made with AI
# agents working in his name. License: Apache-2.0.
import math
import unittest


def _m():
    import tyc_period  # lazy so the publish gate only needs the listed files
    return tyc_period


class TestParsing(unittest.TestCase):
    def test_asassn_csv(self):
        m = _m()
        text = ("jd,flux,flux_err,mag,mag_err,limit,fwhm,quality,camera,phot_filter\n"
                "2458000.5,1,0.1,10.80,0.010,16,1.5,G,bF,g\n"
                "2458001.5,1,0.1,10.81,0.010,16,1.5,B,bF,g\n"
                "2458002.5,1,0.1,99.99,99.99,16,1.5,G,bF,g\n"
                "2458003.5,1,0.1,10.79,0.012,16,1.5,G,ba,V\n")
        rows, info = m.parse_asassn_csv(text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(info["n_bad_quality"], 1)
        self.assertAlmostEqual(rows[0][0], 2458000.5 + 69.184 / 86400.0, places=9)
        self.assertEqual(rows[0][1], "bF|g")
        self.assertEqual(rows[1][1], "ba|V")

    def test_asassn_mjd_fix(self):
        m = _m()
        rows, info = m.parse_asassn_csv("jd,mag,mag_err\n58000.0,10.8,0.01\n")
        self.assertEqual(info["time_fix"], "MJD+2400000.5")
        self.assertAlmostEqual(rows[0][0], 2458000.5 + 69.184 / 86400.0, places=9)

    def test_asassn_missing_columns(self):
        rows, info = _m().parse_asassn_csv("time,flux\n1,2\n")
        self.assertEqual(rows, [])
        self.assertIn("error", info)

    def test_wasp_csv(self):
        m = _m()
        rows = m.parse_wasp_csv('HJD,camera,magnitude,"magnitude error"\n'
                                "2453862.529,225,10.91,0.01\n")
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0][0], 2453862.529 + 65.184 / 86400.0, places=9)


class TestLabels(unittest.TestCase):
    def test_branch(self):
        m = _m()
        self.assertEqual(m.branch_label(2.32890, 2e-6)[0], "GAIA_BRANCH")
        self.assertEqual(m.branch_label(2.32974, 2e-6)[0], "WASP_BRANCH")
        self.assertEqual(m.branch_label(2.3310, 2e-6)[0], "NEITHER")
        self.assertEqual(m.branch_label(2.32930, 2e-4)[0], "BOTH_CONSISTENT")

    def test_wasp_link(self):
        m = _m()
        self.assertEqual(m.wasp_link(2.3287683, 2e-6)["label"], "WASP_ON_EPHEMERIS")
        self.assertEqual(m.wasp_link(2.3289298, 2e-6)["label"], "WASP_OFF_EPHEMERIS")
        self.assertEqual(m.wasp_link(2.3287683, 1e-4)["label"], "WASP_LINK_UNTESTABLE")

    def test_combine(self):
        m = _m()
        p = 2.32880
        t_a = m.T_TESS - 900 * p
        e = m.combine_ephemeris(t_a, 0.001, p, 1e-6)
        self.assertEqual(e["label"], "EPHEMERIS_UNIQUE")
        self.assertEqual(e["N"], 900)
        e2 = m.combine_ephemeris(t_a + 0.3, 0.001, p, 1e-6)
        self.assertEqual(e2["label"], "EPHEMERIS_INCONSISTENT")
        e3 = m.combine_ephemeris(t_a, 0.001, p, 1e-3)
        self.assertEqual(e3["label"], "EPHEMERIS_AMBIGUOUS")

    def test_detection(self):
        m = _m()
        self.assertEqual(m.detection_label(20, 10, 8, 9, 0.06, True), "ASASSN_DETECTED")
        self.assertEqual(m.detection_label(9, 10, 8, 9, 0.06, True), "ASASSN_NOT_DETECTED")
        self.assertEqual(m.detection_label(20, 10, 4, 9, 0.06, False), "ASASSN_INSENSITIVE")
        self.assertEqual(m.detection_label(20, 10, 8, 4, 0.06, True), "ASASSN_NOT_DETECTED")

    def test_blend(self):
        m = _m()
        self.assertEqual(m.blend_label_one(4.0), "ON_TARGET")
        self.assertEqual(m.blend_label_one(-4.0), "ON_NEIGHBOUR")
        self.assertEqual(m.blend_label_one(1.0), "BLEND_UNRESOLVED")
        self.assertEqual(m.blend_label_one(float("nan")), "BLEND_UNTESTABLE")

    def test_common_mode(self):
        m = _m()

        def c(d, z):
            return {"status": "ok", "depth": d, "z": z}
        clean = [c(0.001, 0.2)] * 10 + [c(0.03, 5)]
        self.assertEqual(m.common_mode_label(clean)[0], "COMMON_CLEAN")
        mixed = [c(0.001, 0.2)] * 8 + [c(0.03, 5)] * 3
        self.assertEqual(m.common_mode_label(mixed)[0], "COMMON_MIXED")
        dirty = [c(0.001, 0.2)] * 6 + [c(0.03, 5)] * 4
        self.assertEqual(m.common_mode_label(dirty)[0], "COMMON_MODE")
        few = [c(0.001, 0.2)] * 5 + [{"status": "no data"}] * 7
        self.assertEqual(m.common_mode_label(few)[0], "COMMON_UNTESTABLE")
        weak = [c(0.03, 2.0)] * 10
        self.assertEqual(m.common_mode_label(weak)[0], "COMMON_CLEAN")


class TestCore(unittest.TestCase):
    def test_shape(self):
        m = _m()
        self.assertEqual(m.shape(0.0), 1.0)
        self.assertEqual(m.shape(0.06), 0.0)
        self.assertTrue(0.0 < m.shape(0.03) < 1.0)

    def test_box_finds_planted_dip(self):
        m = _m()
        import random
        rng = random.Random(5)
        p, t0 = 2.3, 2458000.0
        rows = []
        for k in range(3000):
            t = 2458000.0 + k * 0.37 + rng.random() * 0.01
            mag = 10.0 + rng.gauss(0, 0.01) + 0.05 * m.shape(m.fold_dt(t, t0, p))
            rows.append((t, "x|g", mag, 0.01))
        lc = m.build_lc(rows)
        r = m.box_scan(lc, p, t0)
        self.assertGreater(r["snr"], 10)
        self.assertLess(abs(m.fold_dt(t0 + r["phase"] * p, t0, p)), 0.04)
        d = m.depth_fit(lc, p, t0)
        self.assertLess(abs(d["depth"] - 0.05), 0.01)

    def test_helio_corr(self):
        m = _m()
        vals = [m.helio_corr_days(2460700.5 + k) for k in range(366)]
        self.assertLess(max(abs(v) for v in vals), 0.0059)
        self.assertGreater(max(vals), 0.0050)
        # Sun opposite the star (early August): light reaches Earth first, so HJD > JD
        self.assertGreater(m.helio_corr_days(2460894.5), 0.005)

    def test_clean_json(self):
        m = _m()
        o = m.clean_json({"a": float("nan"), "_x": 1, "b": [1.0, float("inf")]})
        self.assertEqual(o, {"a": None, "b": [1.0, None]})
        self.assertTrue(math.isfinite(m.P_GAIA))


if __name__ == "__main__":
    unittest.main()
