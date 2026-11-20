# Tests for wasp_tyc.py. By MV2 of Munim, Inc.; made with AI agents. License: Apache-2.0.
import math
import unittest


def _m():
    import wasp_tyc
    return wasp_tyc


class TestParse(unittest.TestCase):
    def test_parse_csv(self):
        m = _m()
        text = ('HJD,camera,magnitude,"magnitude error"\n'
                "2453862.528264,225,10.9321,0.0900\n"
                "2453862.550451,225,10.8989,0.0290\n"
                "bad,line\n\n"
                "2453862.550880,225,nan,0.03\n")
        rows = m.parse_csv(text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][1], "225")
        self.assertAlmostEqual(rows[1][2], 10.8989)

    def test_url(self):
        m = _m()
        self.assertEqual(m.wasp_url(m.TARGET),
                         "https://wasp.cerit-sc.cz/csv?object=1SWASP%20J202214.65-220425.1")


class TestShape(unittest.TestCase):
    def test_shape(self):
        m = _m()
        self.assertEqual(m.shape(0.0), 1.0)
        self.assertEqual(m.shape(m.T14), 0.0)
        mid = 0.5 * (0.5 * m.T14 + 0.5 * m.T23)
        self.assertAlmostEqual(m.shape(mid), 0.5, places=6)
        self.assertAlmostEqual(m.fold_dt(10.0 + 3 * 2.0 + 0.1, 10.0, 2.0), 0.1, places=9)


class TestControls(unittest.TestCase):
    def test_exclusions(self):
        m = _m()
        ps = m.control_periods(200, 7)
        self.assertEqual(len(ps), 200)
        for p in ps:
            self.assertTrue(1.5 <= p <= 3.5)
            self.assertGreater(abs(p - m.P_GAIA), 0.003 * m.P_GAIA)
            self.assertGreater(abs(p - 2.0), 0.02)


class TestBox(unittest.TestCase):
    def test_box_recovers_injection(self):
        m = _m()
        p, t0 = 2.32905, 2453871.1
        lc = m.build_lc(m.make_synth(5, 0.04, p, t0, n_nights=60))
        best = m.box_scan(lc, p, t0)
        self.assertGreater(best["snr"], 10)
        ph = best["phase"]
        self.assertLess(min(ph, 1 - ph), 0.01)

    def test_grid_fit(self):
        m = _m()
        p, t0 = 2.32905, 2453871.1
        lc = m.build_lc(m.make_synth(6, 0.04, p, t0, n_nights=60))
        m.detrend(lc, p, t0)
        g = m.grid_fit(lc, p + 2e-6, t0 + 0.002, 1e-5, 1e-6, 0.004, 0.0002)
        n = round((g["t0"] - t0) / p)
        self.assertLess(abs(g["t0"] - (t0 + n * p)), 0.002)
        self.assertLess(abs(g["depth"] - 0.04), 0.008)


class TestGrading(unittest.TestCase):
    def test_ephemeris_unique(self):
        m = _m()
        p = 2.32905
        tw = m.T_TESS - 2900 * p
        e = m.combine_ephemeris(tw, 0.001, p + 1e-7, 5e-6)
        self.assertEqual(e["label"], "EPHEMERIS_UNIQUE")
        self.assertEqual(e["N"], 2900)
        self.assertLess(abs(e["P_comb"] - p), 1e-6)
        self.assertTrue(e["gaia_consistent"])

    def test_ephemeris_ambiguous_and_inconsistent(self):
        m = _m()
        p = 2.32905
        tw = m.T_TESS - 2900 * p
        self.assertEqual(m.combine_ephemeris(tw, 0.001, p, 1e-4)["label"],
                         "EPHEMERIS_AMBIGUOUS")
        self.assertEqual(m.combine_ephemeris(tw + 0.5, 0.001, p, 1e-6)["label"],
                         "EPHEMERIS_INCONSISTENT")
        self.assertEqual(m.combine_ephemeris(tw, float("nan"), p, 1e-6)["label"],
                         "EPHEMERIS_UNTESTABLE")

    def test_detection_label(self):
        m = _m()
        self.assertEqual(m.detection_label(20, 8, 10, 12, 0.04, True), "WASP_DETECTED")
        self.assertEqual(m.detection_label(20, 25, 10, 12, 0.04, True), "WASP_NOT_DETECTED")
        self.assertEqual(m.detection_label(20, 8, 10, 3, 0.04, False), "WASP_INSENSITIVE")
        self.assertEqual(m.detection_label(6.9, 5, 10, 12, 0.04, True), "WASP_NOT_DETECTED")

    def test_blend_label(self):
        m = _m()
        self.assertEqual(m.blend_label({})[0], "BLEND_UNTESTABLE")
        self.assertEqual(m.blend_label({"a": 5.0, "b": 9.0})[0], "ON_TARGET")
        self.assertEqual(m.blend_label({"a": 5.0, "b": -4.0}), ("ON_NEIGHBOUR", "b"))
        self.assertEqual(m.blend_label({"a": 5.0, "b": 1.0})[0], "BLEND_UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
