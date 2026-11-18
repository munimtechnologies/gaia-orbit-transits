# SPDX-License-Identifier: Apache-2.0
"""numpy + sb1_transit synthetic checks for sb1_robust 0.2.0.

Run inside a compete job after fetching sb1_transit.py (pinned at v0.15.0):
    python -m unittest -v synthetic_check_sb1_robust
It is not named test_*.py on purpose: it needs numpy and sb1_transit.py, while the
repo's test_*.py files are pure stdlib. Same content as the job copy
test_sb1_robust_np.py used by gaia-sb1rob-k0...k7-v1.
MV2 of Munim, Inc.; made with AI agents."""
import unittest

import numpy as np

import sb1_transit as st
import sb1_robust as sr

sr.install(st)

P, T0, T14, DEPTH = 3.1, 1501.6, 0.125, 0.01


def synthetic(dips=True, outliers=False, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(1500.0, 1527.0, 2.0 / 1440.0)
    t = t[(t < 1513.4) | (t > 1514.6)]                 # a mid-sector downlink gap
    f = 1.0 + 5e-4 * rng.standard_normal(t.size)
    if dips:
        for k in range(10):
            f[np.abs(t - (T0 + k * P)) < T14 / 2] -= DEPTH
    if outliers:
        # three short -10 % glitches at the same orbital phase in three epochs (the 0.1.0
        # failure mode: a few deep bins, the rest of the box flat)
        for k in (1, 4, 7):
            f[np.abs(t - (T0 + k * P)) < 0.0105] -= 0.10
    return t, f


def eph(sig=0.01):
    return {"t0": T0, "t2": T0 + P / 2, "P": P, "used_corr": True,
            "v1": (sig * sig, 0.0, 0.0), "v2": (sig * sig, 0.0, 0.0)}


PHYS = {"depth_exp": DEPTH}


class TestRobust(unittest.TestCase):
    def test_install_is_idempotent(self):
        f1 = st.fold_search
        sr.install(st)
        self.assertIs(st.fold_search, f1)
        self.assertTrue(st.VERSION.startswith("0.2.0"))

    def test_real_transit_still_hits(self):
        t, f = synthetic(dips=True)
        m = st.measure_sector(t, f, P, T14, 0.8 * DEPTH, np.random.default_rng(2))
        self.assertTrue(m["hit"], m["real"])
        self.assertTrue(m["real"]["hit_v1"])
        self.assertGreater(m["real"]["med_ratio"], 0.8)
        for c in st.CONTROL_RATIOS:
            self.assertFalse(m["controls"][str(c)]["hit"], (c, m["controls"][str(c)]["res"]))
        m["sector"] = 1
        res = st.evaluate_star([m], PHYS, eph())
        self.assertTrue(res["star_hit"])
        self.assertTrue(res["star_hit_v1"])
        self.assertEqual(res["phase_label"], "PHASE_MATCH")
        self.assertEqual(res["hit_class"], "SUBSTELLAR_SIZE")
        self.assertGreaterEqual(res["sensitivity"], 0.75)
        self.assertGreater(res["med_ratio_best"], 0.8)

    def test_outlier_glitches_do_not_hit(self):
        t, f = synthetic(dips=False, outliers=True)
        m = st.measure_sector(t, f, P, T14, 0.8 * DEPTH, np.random.default_rng(5))
        print("outlier case: 0.1.0 rule hit =", (m["real"] or {}).get("hit_v1"),
              "med_ratio =", (m["real"] or {}).get("med_ratio"))
        self.assertFalse(m["hit"], m["real"])
        m["sector"] = 1
        res = st.evaluate_star([m], PHYS, eph())
        self.assertFalse(res["star_hit"])
        print("outlier case: sensitivity =", res["sensitivity"])

    def test_flat_star_sensitive_but_no_hit(self):
        t, f = synthetic(dips=False)
        m = st.measure_sector(t, f, P, T14, 0.8 * DEPTH, np.random.default_rng(3))
        self.assertFalse(m["hit"], m["real"])
        m["sector"] = 1
        res = st.evaluate_star([m], PHYS, eph())
        self.assertFalse(res["star_hit"])
        self.assertGreaterEqual(res["sensitivity"], 0.75)


if __name__ == "__main__":
    unittest.main()
