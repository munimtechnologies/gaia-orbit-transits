# SPDX-License-Identifier: Apache-2.0
"""Offline tests for ztf_recheck 0.1.0. MV2 of Munim, Inc.; made with AI agents."""
import unittest

import ztf_recheck as zr


class TestZtfRecheck(unittest.TestCase):
    def test_wrap(self):
        self.assertAlmostEqual(zr.wrap(0.98), -0.02, places=9)
        self.assertAlmostEqual(zr.wrap(-0.51), 0.49, places=9)
        self.assertAlmostEqual(zr.wrap(0.25), 0.25, places=9)

    def test_cycle_phase(self):
        n, ph = zr.cycle_phase(389.858 + 290 * 3.10003166 + 0.0357, 389.858, 3.10003166)
        self.assertEqual(n, 290)
        self.assertAlmostEqual(ph, 0.0357 / 3.10003166, places=9)

    def test_linfit_exact(self):
        es = [0, 10, 25, 40, 77]
        ts = [100.0 + 3.25 * e for e in es]
        a, b, sa, sb, rms = zr.linfit(es, ts)
        self.assertAlmostEqual(a, 100.0, places=8)
        self.assertAlmostEqual(b, 3.25, places=10)
        self.assertLess(rms, 1e-9)

    def test_recheck_flags_mismatch(self):
        gid = "4535010166315168640"
        t0, p = zr.GAIA[gid]
        hjd = 2457000.0 + t0 + 290 * p + 0.0357
        good = {"star": "x", "gaia_dr3": gid, "oid": "1", "hjd": repr(hjd), "gaia_phase": "%.5f" % (0.0357 / p),
                "assigned": "primary", "stage": "1"}
        bad = dict(good, gaia_phase="0.0500")
        new = dict(good, gaia_phase="")
        res = zr.recheck([good, bad, new])
        self.assertEqual(res["n_mismatches"], 1)
        self.assertEqual(len(res["phased_new"]), 1)

    def test_secondary_and_fit(self):
        gid = "4576721896566803072"
        t0, p, sec = zr.FROZEN[gid]
        rows = []
        for e in (70, 96, 105, 151, 200, 276):
            rows.append({"star": "t", "gaia_dr3": gid, "oid": "1", "hjd": repr(2457000.0 + t0 + e * p),
                         "gaia_phase": "", "assigned": "primary", "stage": "1"})
        for e in (68, 103, 224):
            rows.append({"star": "t", "gaia_dr3": gid, "oid": "1",
                         "hjd": repr(2457000.0 + t0 + (e + sec) * p), "gaia_phase": "",
                         "assigned": "secondary", "stage": "2"})
        res = zr.recheck(rows)
        s = res["stars"][gid]
        self.assertAlmostEqual(s["fit_P"], p, places=6)
        self.assertAlmostEqual(s["secondary_offset_mean"], sec, places=6)
        self.assertEqual(s["post_split_in_pm0.02"], 3)


if __name__ == "__main__":
    unittest.main()
