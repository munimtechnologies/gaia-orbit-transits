# SPDX-License-Identifier: Apache-2.0
"""Offline tests for archival.py (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents)."""
import io
import unittest
import zipfile

import numpy as np

import archival as ar

ZTF_HEADER = ("oid,expid,hjd,mjd,mag,magerr,catflags,filtercode,ra,dec,chi,sharp,filefracday,"
              "field,ccdid,qid,limitmag,magzp,magzprms,clrcoeff,clrcounc,exptime,airmass,programid")
GAIA_HDR = ("solution_id,source_id,transit_id,band,time,mag,flux,flux_error,flux_over_error,"
            "rejected_by_photometry,rejected_by_variability,other_flags")


def ztf_row(expid, hjd, mag, catflags=0, filt="zr", exptime=30):
    return (f"736210200020009,{expid},{hjd},{hjd - 2400000.5},{mag},0.011,{catflags},{filt},"
            f"2.39,48.75,0.3,0.0,20180511483438,736,0xa,0x2,20.1,26.05,0.03,0.08,1e-05,"
            f"{exptime},1.5,1")


def gaia_lines():
    lines = [GAIA_HDR]
    for i in range(10):
        lines.append(f"1,393581461455623296,{i},G,{2191.5 + 10 * i},12.73,{1000 + i},1.0,1000,false,false,0")
    lines.append("1,393581461455623296,77,G,2300.0,12.73,5.0,1.0,5,true,false,0")
    lines.append("1,393581461455623296,78,G,,12.73,1000,1.0,1000,false,false,0")
    for i in range(6):
        lines.append(f"1,393581461455623296,{i},BP,{2191.5 + 10 * i},13.4,{500 + i},2.0,250,false,false,0")
    return lines


class TestParsers(unittest.TestCase):
    def test_ztf(self):
        lines = [ZTF_HEADER]
        for i in range(20):
            lines.append(ztf_row(i, 2458249.5 + i, 12.65 + 0.001 * (i % 3)))
        lines.append(ztf_row(98, 2458300.5, 12.0, catflags=4))          # flagged
        lines.append(ztf_row(99, 2458301.5, 13.9, exptime=180))          # saturated long exposure
        for i in range(5):                                               # too few g points
            lines.append(ztf_row(200 + i, 2458249.6 + i, 13.3, filt="zg"))
        segs = ar.parse_ztf_csv("\n".join(lines) + "\n")
        self.assertEqual(len(segs), 1)
        s = segs[0]
        self.assertTrue(s["name"].startswith("ztf-zr-f736"))
        self.assertEqual(len(s["t"]), 20)
        self.assertAlmostEqual(s["t"][0], 1249.5, places=6)
        self.assertAlmostEqual(float(np.median(s["f"])), 1.0, places=6)
        self.assertLess(float(np.max(np.abs(s["f"] - 1))), 0.003)

    def test_gaia_epoch(self):
        segs = ar.parse_gaia_epoch_csv("\n".join(gaia_lines()))
        names = [s["name"] for s in segs]
        self.assertEqual(names, ["gaia-BP", "gaia-G"])
        g = segs[1]
        self.assertEqual(len(g["t"]), 10)
        self.assertAlmostEqual(g["t"][0], 389.0, places=6)    # J2016.0 = BTJD 389.0
        self.assertLess(abs(float(np.median(g["f"])) - 1.0), 1e-9)

    def test_datalink_payloads(self):
        """0.4.1: DataLink answers come raw or zipped (DATAMODEL_STANDARD)."""
        text = "\n".join(gaia_lines())
        self.assertEqual(ar.datalink_payload_to_text(text.encode()), text)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("EPOCH_PHOTOMETRY-Gaia DR3 393581461455623296.csv", text)
        out = ar.datalink_payload_to_text(buf.getvalue())
        segs = ar.parse_gaia_epoch_csv(out)
        self.assertEqual([s["name"] for s in segs], ["gaia-BP", "gaia-G"])
        self.assertEqual(ar.DATALINK_TRIES[0][0], "DATAMODEL_STANDARD")

    def test_asassn(self):
        hdr = "jd,flux,flux_err,mag,mag_err,limit,fwhm,asas_sn_id,cam"
        lines = [hdr]
        for i in range(15):
            lines.append(f"{2458000.5 + i},20.0,0.3,13.1,0.02,17,1.5,661430,bd")
        for i in range(5):
            lines.append(f"{2458000.5 + i},3.0,0.3,15.1,0.1,17,1.5,999,bd")
        lines.append("2458100.5,-1.0,0.3,99,0.1,17,1.5,661430,bd")
        segs = ar.parse_asassn_csv("\n".join(lines))
        self.assertEqual(len(segs), 1)
        self.assertEqual(len(segs[0]["t"]), 15)
        self.assertIn("bd", segs[0]["name"])
        self.assertAlmostEqual(segs[0]["t"][0], 1000.5, places=6)


class TestEphemeris(unittest.TestCase):
    def test_wrap_and_carry(self):
        P_s = np.array([10.0, 10.0, 10.1, 10.0])
        T_s = np.array([100.2, 109.9, 100.0, 90.1])
        eph = ar.ephemeris(P_s, T_s, 100.0, 10.0, 100.0)
        self.assertTrue(np.all(np.abs(eph["T_s"] - 100.0) < 0.5))
        eph = ar.ephemeris(P_s, T_s, 100.0, 10.0, 200.0)
        self.assertEqual(eph["n_cycles"], 10.0)
        self.assertAlmostEqual(eph["T_s"][2], 100.0 + 10 * 10.1, places=9)


class TestScan(unittest.TestCase):
    def _brute(self, t, d, w, eph, gr):
        best = 0.0
        for P in gr["Ps"]:
            Tm = ar.t_mean_given_p(eph, P)
            h = ar.t_halfwidth(eph, P, gr["D"])
            nT = int(np.ceil(h / gr["dT"]))
            for m in range(-nT, nT + 1):
                s, _, n, _ = ar.snr_at(t, d, w, P, Tm + m * gr["dT"], gr["D"])
                if n < ar.MIN_PTS:
                    s = 0.0
                best = max(best, s)
        return best

    def test_scan_matches_brute_force(self):
        rng = np.random.default_rng(3)
        t = np.sort(rng.uniform(0, 1000, 800))
        d = rng.normal(0, 0.01, 800)
        w = np.full(800, 1e4)
        for tsd in (0.5, 40.0):          # narrow window, and the full-phase (wrapped) branch
            eph = {"P_mu": 50.0, "P_sd": 0.01, "T_mu": 500.0, "T_sd": tsd, "rho": 0.3}
            gr = ar.grid(eph, 1000.0, 0.3)
            best, per_p = ar.scan(t, d, w, eph, gr)
            self.assertEqual(per_p.size, gr["Ps"].size)
            self.assertAlmostEqual(best["snr"], self._brute(t, d, w, eph, gr), places=6)
            s, _, _, _ = ar.snr_at(t, d, w, best["P"], best["T"], best["D"])
            self.assertAlmostEqual(best["snr"], s, places=6)

    def test_grid_edge_box_keeps_its_points(self):
        """0.4.1 regression: a box at the edge of the T grid (|dg| = nT dT > h) must
        see points beyond h + D/2; before the fix they were dropped."""
        eph = {"P_mu": 50.0, "P_sd": 0.01, "T_mu": 500.0, "T_sd": 0.5, "rho": 0.0}
        gr = ar.grid(eph, 1000.0, 0.3)
        h = ar.t_halfwidth(eph, 50.0, 0.3)
        nT = int(np.ceil(h / gr["dT"]))
        edge = nT * gr["dT"]
        self.assertGreater(edge, h)
        # points only at the far edge of the last box, with a strong positive dip signal
        t = 500.0 + edge + np.array([0.11, 0.12, 0.13, 0.14]) + 50.0 * np.arange(4)[:, None]
        t = np.sort(t.ravel())
        d = np.full(t.size, 0.02)
        w = np.ones(t.size)
        best, _ = ar.scan(t, d, w, eph, gr)
        self.assertAlmostEqual(best["snr"], self._brute(t, d, w, eph, gr), places=9)
        self.assertGreater(best["snr"], 0.0)


def synthetic(inject, seed=7):
    rng = np.random.default_rng(seed)
    # irregular, ground-like: 70% of nights observed, 4 points from a random start
    nights = np.sort(rng.choice(2000, 1400, replace=False)).astype(float)
    start = rng.uniform(0.05, 0.20, nights.size)
    t = ((nights + start)[:, None] + 0.05 * np.arange(4)[None, :]).ravel()
    f = 1 + rng.normal(0, 0.01, t.size)
    P_true, T_true, D = 73.32, 400.3, 0.25
    if inject:
        f[np.abs(ar.wrap(t - T_true, P_true)) < D / 2] -= 0.03
    srng = np.random.default_rng(seed + 1)
    P_s = srng.normal(73.3, 0.05, 2000)
    T_s = 400.0 + srng.normal(0, 0.5, 2000)
    return t, f, P_s, T_s, P_true, T_true


class TestAnalyse(unittest.TestCase):
    def _run(self, inject):
        t, f, P_s, T_s, P_true, T_true = synthetic(inject)
        data = ar.prepare([{"name": "syn", "survey": "synthetic", "t": t, "f": f}], 0.25)
        eph = ar.ephemeris(P_s, T_s, 400.0, 73.3, float(np.median(data["t"])))
        res = ar.analyse(data, eph, 0.25, 0.03, 0.1, n_null=5, n_inj=60,
                         rng=np.random.default_rng(11))
        return res, eph, P_true, T_true

    def test_injected_transit_found(self):
        res, eph, P_true, T_true = self._run(True)
        ob = res["obs"]
        self.assertTrue(res["verdict"].startswith("candidate"), res["verdict"])
        self.assertGreater(ob["snr"], res["thr"])
        self.assertLess(abs(ob["P"] - P_true), 0.02)
        self.assertLess(abs(ar.wrap(ob["T"] - T_true, P_true)), 0.15)
        self.assertGreater(ob["depth"], 0.015)
        self.assertGreaterEqual(ob["n_epochs"], 2)

    def test_noise_only(self):
        res, eph, _, _ = self._run(False)
        self.assertEqual(res["verdict"], "no detection")
        self.assertGreater(res["injection"]["cov1"], 0.9)
        self.assertGreater(res["recovery_at_pred_depth"], 0.6)
        self.assertLess(res["p_transit_post"], 0.1)
        self.assertGreaterEqual(res["thr"], ar.SNR_FLOOR)


class TestDetrend(unittest.TestCase):
    def test_dip_survives_detrending(self):
        rng = np.random.default_rng(5)
        t = np.arange(0, 27, 1 / 48)
        t = t[(t < 13) | (t > 14)]
        f = 1 + 0.005 * np.sin(2 * np.pi * t / 20) + rng.normal(0, 0.001, t.size)
        dip = (t > 10.0) & (t < 10.25)
        f[dip] -= 0.01
        data = ar.prepare([{"name": "tess-s1", "survey": "tess", "t": t, "f": f}], 0.25)
        m = (data["t"] > 10.0) & (data["t"] < 10.25)
        self.assertGreater(m.sum(), 8)
        self.assertAlmostEqual(float(np.mean(data["d"][m])), 0.01, delta=0.002)


if __name__ == "__main__":
    unittest.main()
