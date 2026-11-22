# Tests for pixel_which_star.py 0.1.0 (standard library only).
# By MV2 of Munim, Inc.; made with AI agents working in his name. License: Apache-2.0.
import math
import random
import unittest

import pixel_which_star as pws


def synth_lc(p=2.0, t0=0.3, dur=0.12, depth=0.01, sec=0.0, shift=0.0, days=20.0, cad=0.01,
             noise=0.0005, trend=0.0, seed=1):
    rng = random.Random(seed)
    t, f = [], []
    x = 0.0
    while x < days:
        v = 1000.0 * (1.0 + trend * math.sin(x / 3.0))
        dt = pws.tp.fold_dt(x, t0 + shift, p)
        v *= 1.0 - depth * pws.trap(dt, dur)
        if sec:
            v *= 1.0 - sec * pws.trap(pws.tp.fold_dt(x, t0 + shift + 0.5 * p, p), dur)
        v *= 1.0 + rng.gauss(0.0, noise)
        t.append(x)
        f.append(v)
        x += cad
    return t, f


class TestShapes(unittest.TestCase):
    def test_trap(self):
        self.assertEqual(pws.trap(0.0, 0.1), 1.0)
        self.assertEqual(pws.trap(0.05, 0.1), 0.0)
        self.assertEqual(pws.trap(-0.07, 0.1), 0.0)
        self.assertAlmostEqual(pws.trap(0.044, 0.1), (0.05 - 0.044) / 0.012, places=9)

    def test_sky_offset_wrap(self):
        e, n = pws.sky_offset(359.999, 0.0, 0.001, 0.0)
        self.assertAlmostEqual(e, 7.2, places=6)
        self.assertAlmostEqual(n, 0.0, places=9)

    def test_wcs_roundtrip_and_scale(self):
        w = pws.FakeWCS(175.6, -52.6, 7.0, 7.0, 21.0, 37.0)
        ra, de = pws.pix2world(w, 3.2, 11.9)
        x, y = pws.world2pix(w, ra, de)
        self.assertAlmostEqual(x, 3.2, places=7)
        self.assertAlmostEqual(y, 11.9, places=7)
        self.assertAlmostEqual(pws.pixel_scale(w, 7.0, 7.0), 21.0, places=2)

    def test_wmean_summarize(self):
        m, s, n = pws.wmean([1.0, 3.0, float("nan")], [1.0, 1.0, 1.0])
        self.assertEqual(n, 2)
        self.assertAlmostEqual(m, 2.0)
        self.assertAlmostEqual(s, 1.0 / math.sqrt(2.0))
        sm = pws.summarize([1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(sm["mean"], 2.5)
        self.assertAlmostEqual(sm["sigma"], pws.tp.std([1.0, 2.0, 3.0, 4.0]) / 2.0)
        self.assertTrue(math.isnan(pws.summarize([1.0, 2.0])["mean"]))


class TestLightCurves(unittest.TestCase):
    def test_detrend_removes_trend_keeps_transit(self):
        t, f = synth_lc(trend=0.01, noise=0.0)
        fn = pws.detrend(t, f, 0.3, 2.0, 0.12)
        outs = [v for x, v in zip(t, fn) if abs(pws.tp.fold_dt(x, 0.3, 2.0)) > 0.3]
        ins = [v for x, v in zip(t, fn) if abs(pws.tp.fold_dt(x, 0.3, 2.0)) < 0.03]
        self.assertLess(max(abs(v - 1.0) for v in outs), 0.003)
        self.assertAlmostEqual(sum(ins) / len(ins), 0.99, delta=0.002)

    def test_epoch_offset(self):
        t, f = synth_lc(shift=0.012)
        fn = pws.detrend(t, f, 0.3, 2.0, 0.12)
        eo = pws.epoch_offset(t, fn, 0.3, 2.0, 0.12)
        self.assertIsNotNone(eo)
        self.assertAlmostEqual(eo["offset"], 0.012, delta=0.002)
        self.assertAlmostEqual(eo["depth"], 0.01, delta=0.001)
        self.assertGreater(eo["dchi2"], 100.0)
        self.assertFalse(eo["edge"])

    def test_fit_ephemeris(self):
        P, T0 = 2.5, 100.0
        ep = [{"n": n, "t": T0 + n * P, "sigma": 0.001} for n in (0, 100, 400)]
        r = pws.fit_ephemeris(ep, 2.5003, 100.01)
        self.assertEqual(r["status"], "REFINED")
        self.assertAlmostEqual(r["P"], P, places=8)
        self.assertAlmostEqual(pws.tp.fold_dt(r["T0"], T0, P), 0.0, places=6)
        one = pws.fit_ephemeris([{"n": 3, "t": 100.0 + 3 * 2.5 + 0.004, "sigma": 0.001}], 2.5, 100.0)
        self.assertEqual(one["status"], "SHIFTED")
        self.assertAlmostEqual(one["T0"], 100.004, places=9)
        bad = pws.fit_ephemeris([{"n": 0, "t": 100.0, "sigma": 0.001},
                                 {"n": 10, "t": 125.1, "sigma": 0.001}], 2.5, 100.0)
        self.assertEqual(bad["status"], "FIT_REJECTED")
        self.assertEqual(bad["P"], 2.5)
        self.assertEqual(pws.fit_ephemeris([], 2.5, 100.0)["status"], "UNREFINED")

    def test_event_depths(self):
        t, f = synth_lc(sec=0.004, noise=0.0002)
        fn = pws.detrend(t, f, 0.3, 2.0, 0.12)
        ev = pws.event_depths(t, fn, 0.3, 2.0, 0.12, 0.5)
        self.assertGreaterEqual(len(ev), 8)
        m = sum(e["depth"] for e in ev) / len(ev)
        self.assertAlmostEqual(m, 0.004, delta=0.0004)
        pr = pws.event_depths(t, fn, 0.3, 2.0, 0.12, 0.0)
        self.assertAlmostEqual(sum(e["depth"] for e in pr) / len(pr), 0.01 * 0.99, delta=0.0006)
        nul = pws.event_depths(t, fn, 0.3, 2.0, 0.12, 0.25)
        self.assertLess(abs(sum(e["depth"] for e in nul) / len(nul)), 0.0003)

    def test_aperture(self):
        self.assertEqual(len(pws.aperture_around(7, 7, 15, 15)), 9)
        self.assertEqual(sorted(pws.aperture_around(0, 0, 15, 15)), [0, 1, 15, 16])


class TestStars(unittest.TestCase):
    def rows(self):
        return [
            {"source_id": "1", "ra": "175.627", "dec": "-52.6274", "pmra": "", "pmdec": "",
             "phot_g_mean_mag": "12.57", "phot_rp_mean_mag": "12.13"},
            {"source_id": "2", "ra": "175.627", "dec": "-52.6224", "pmra": "1.0", "pmdec": "2.0",
             "phot_g_mean_mag": "16.7", "phot_rp_mean_mag": "16.11"},
            {"source_id": "3", "ra": "175.6457", "dec": "-52.6274", "pmra": "", "pmdec": "",
             "phot_g_mean_mag": "14.29", "phot_rp_mean_mag": "13.49"},
            {"source_id": "4", "ra": "175.627", "dec": "-52.6264", "pmra": "", "pmdec": "",
             "phot_g_mean_mag": "20.5", "phot_rp_mean_mag": "19.9"},
            {"source_id": "5", "ra": "175.70", "dec": "-52.6274", "pmra": "", "pmdec": "",
             "phot_g_mean_mag": "8.9", "phot_rp_mean_mag": "7.73"},
        ]

    def test_star_table(self):
        tab = pws.star_table(self.rows(), "1", 0.0088, 2016.0)
        ids = [s["id"] for s in tab]
        self.assertEqual(ids[0], "4")            # 3.6" away
        self.assertNotIn("5", ids)               # 160" away: outside 120"
        s2 = [s for s in tab if s["id"] == "2"][0]
        self.assertAlmostEqual(s2["sep_arcsec"], 18.0, delta=0.05)
        self.assertTrue(s2["capable"])           # ratio 0.026 >= 0.0044
        s4 = [s for s in tab if s["id"] == "4"][0]
        self.assertFalse(s4["capable"])          # ratio 0.0011
        self.assertAlmostEqual(s2["needed_own_depth"], 0.0088 / s2["flux_ratio"])

    def test_build_and_choose(self):
        w = pws.FakeWCS(175.627, -52.6274, 7.0, 7.0, 21.0, 0.0)
        stars, tgt = pws.build_stars(self.rows(), w, 15, 15, "1", 2016.0)
        self.assertEqual(tgt["role"], "T")
        self.assertAlmostEqual(tgt["x"], 7.0, places=6)
        self.assertNotIn("4", [s["id"] for s in stars])   # RP 19.9 is not modelled
        nb = pws.choose_neighbour(stars, tgt, 0.0088, 15, 15)
        self.assertEqual(nb["id"], "3")          # 1.9 px, brightest capable within 3 px
        with self.assertRaises(RuntimeError):
            pws.build_stars(self.rows(), w, 15, 15, "999", 2016.0)


class TestLabels(unittest.TestCase):
    def table(self):
        return [{"id": "far", "east": 20.0, "north": 0.0, "sep_arcsec": 20.0, "rp": 15.0,
                 "capable": True},
                {"id": "faint", "east": 1.0, "north": 0.5, "sep_arcsec": 1.1, "rp": 20.0,
                 "capable": False}]

    def test_ws(self):
        comb = {"east": 0.5, "north": 0.2, "sigma": 1.0, "n_sectors": 3}
        self.assertEqual(pws.ws_label(comb, self.table())["label"], "WS_ON_TARGET")
        t2 = self.table() + [{"id": "close", "east": 1.5, "north": 1.0, "sep_arcsec": 1.8,
                              "rp": 14.0, "capable": True}]
        r = pws.ws_label(comb, t2)
        self.assertEqual(r["label"], "WS_UNRESOLVED")
        self.assertEqual(r["capable_within_3sigma"], ["close"])
        off = pws.ws_label({"east": 19.0, "north": 0.5, "sigma": 1.0}, self.table())
        self.assertEqual(off["label"], "WS_OFF_TARGET")
        self.assertEqual(off["closest_capable"]["id"], "far")
        self.assertEqual(pws.ws_label({"label": "WS_UNTESTABLE", "n_sectors": 1}, [])["label"],
                         "WS_UNTESTABLE")

    def test_combine(self):
        secs = [{"sensitive": True, "offset": {"east": 1.0, "north": 0.0, "sigma": 2.0}},
                {"sensitive": True, "offset": {"east": -1.0, "north": 0.0, "sigma": 2.0}},
                {"sensitive": False, "offset": {"east": 50.0, "north": 0.0, "sigma": 2.0}}]
        c = pws.combine_offsets(secs)
        self.assertEqual(c["n_sectors"], 2)
        self.assertAlmostEqual(c["east"], 0.0)
        self.assertAlmostEqual(c["sigma"], math.sqrt(2.0))
        self.assertEqual(pws.combine_offsets(secs[:1])["label"], "WS_UNTESTABLE")

    def test_sec_oe_eb(self):
        ok = {"z": 0.5}
        self.assertEqual(pws.sec_label({"z": 4.0}, ok, ok), "SEC_DETECTED")
        self.assertEqual(pws.sec_label({"z": 1.0}, ok, ok), "SEC_NOT_DETECTED")
        self.assertEqual(pws.sec_label({"z": 4.0}, {"z": -3.5}, ok), "SEC_UNRELIABLE")
        self.assertEqual(pws.sec_label({"z": float("nan")}, ok, ok), "SEC_UNTESTABLE")
        lab, z = pws.oe_label({"mean": 0.010, "sigma": 0.0002}, {"mean": 0.0090, "sigma": 0.0001})
        self.assertEqual(lab, "OE_DIFFER")
        self.assertAlmostEqual(z, 0.001 / math.hypot(0.0002, 0.0001), places=6)
        lab2, _ = pws.oe_label({"mean": 0.010, "sigma": 0.0002}, {"mean": 0.0099, "sigma": 0.0002})
        self.assertEqual(lab2, "OE_CONSISTENT")
        self.assertEqual(pws.eb_flag("SEC_DETECTED", {"mean": 0.0004, "sigma": 0.00005},
                                     "OE_CONSISTENT"), "EB_SUSPECT")
        self.assertEqual(pws.eb_flag("SEC_DETECTED", {"mean": 0.0002, "sigma": 0.00005},
                                     "OE_CONSISTENT"), "EB_NOT_INDICATED")
        self.assertEqual(pws.eb_flag("SEC_NOT_DETECTED", {"mean": 0.0, "sigma": 0.0001},
                                     "OE_DIFFER"), "EB_SUSPECT")

    def test_depth_label(self):
        self.assertEqual(pws.depth_label(0.0105, 0.0003, 0.0105), "DEPTH_CONSISTENT")
        self.assertEqual(pws.depth_label(0.0060, 0.0003, 0.0105), "DEPTH_SHALLOWER")
        self.assertEqual(pws.depth_label(0.0150, 0.0003, 0.0105), "DEPTH_DEEPER")
        self.assertEqual(pws.depth_label(float("nan"), 0.0003, 0.0105), "DEPTH_UNTESTABLE")

    def test_configure_tp(self):
        pws.configure_tp(0.125, 0.0088)
        self.assertAlmostEqual(pws.tp.IN_HALF, 0.05)
        self.assertAlmostEqual(pws.tp.OUT_LO, 0.075)
        self.assertAlmostEqual(pws.tp.OUT_HI, 0.175)
        self.assertEqual(pws.tp.INJ_T, 0.0088)


if __name__ == "__main__":
    unittest.main()
