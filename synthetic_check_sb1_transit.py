# SPDX-License-Identifier: Apache-2.0
"""numpy + dipsearch checks for sb1_transit (not pure Python: run them where numpy and
dipsearch.py from v0.13.1 are installed, e.g. `python -m unittest -v synthetic_check_sb1_transit`).
The compete jobs run the same checks as test_sb1_transit_np.py.
MV2 of Munim, Inc.; made with AI agents."""
import unittest

import numpy as np

import sb1_transit as st

P, T0, T14, DEPTH = 3.1, 1501.6, 0.125, 0.01


def synthetic(dips=True, seed=1, single=False):
    rng = np.random.default_rng(seed)
    t = np.arange(1500.0, 1527.0, 2.0 / 1440.0)
    t = t[(t < 1513.4) | (t > 1514.6)]                 # a mid-sector downlink gap
    f = 1.0 + 5e-4 * rng.standard_normal(t.size)
    if dips:
        ks = [2] if single else range(10)
        for k in ks:
            f[np.abs(t - (T0 + k * P)) < T14 / 2] -= DEPTH
    return t, f


def eph(sig=0.01):
    return {"t0": T0, "t2": T0 + P / 2, "P": P, "used_corr": True,
            "v1": (sig * sig, 0.0, 0.0), "v2": (sig * sig, 0.0, 0.0)}


PHYS = {"depth_exp": DEPTH}


class TestFold(unittest.TestCase):
    def test_real_transits_hit_at_right_phase(self):
        t, f = synthetic(True)
        m = st.measure_sector(t, f, P, T14, 0.8 * DEPTH, np.random.default_rng(2))
        self.assertTrue(m["hit"], m["real"])
        r = m["real"]
        self.assertGreaterEqual(r["n_ep"], 6)
        self.assertAlmostEqual(r["depth"], DEPTH, delta=0.002)
        expect = ((T0 - t.min()) / P) % 1.0
        self.assertLess(abs((r["phase"] - expect + 0.5) % 1.0 - 0.5), 0.02)
        for c in st.CONTROL_RATIOS:
            self.assertFalse(m["controls"][str(c)]["hit"], (c, m["controls"][str(c)]["res"]))
        self.assertGreater(m["n_masked_for_controls"], 0)
        m["sector"] = 1
        res = st.evaluate_star([m], PHYS, eph())
        self.assertTrue(res["star_hit"])
        self.assertEqual(res["phase_label"], "PHASE_MATCH")
        self.assertEqual(res["hit_class"], "SUBSTELLAR_SIZE")
        self.assertGreaterEqual(res["sensitivity"], 0.75)

    def test_wrong_timing_is_flagged(self):
        t, f = synthetic(True)
        m = st.measure_sector(t, f, P, T14, 0.8 * DEPTH, np.random.default_rng(2))
        m["sector"] = 1
        e = eph()
        e["t0"] = T0 + 0.5           # Gaia predicts 0.5 d later, sigma 0.01 d
        res = st.evaluate_star([m], PHYS, e)
        self.assertEqual(res["phase_label"], "PHASE_MISMATCH")

    def test_flat_star_sensitive_but_no_hit(self):
        t, f = synthetic(False)
        m = st.measure_sector(t, f, P, T14, 0.8 * DEPTH, np.random.default_rng(3))
        self.assertFalse(m["hit"], m["real"])
        m["sector"] = 1
        res = st.evaluate_star([m], PHYS, eph())
        self.assertFalse(res["star_hit"])
        self.assertGreaterEqual(res["sensitivity"], 0.75)
        self.assertEqual(res["hit_class"], "")

    def test_single_dip_is_not_a_hit(self):
        t, f = synthetic(True, single=True)
        m = st.measure_sector(t, f, P, T14, 0.8 * DEPTH, np.random.default_rng(4))
        self.assertFalse(m["hit"], m["real"])


if __name__ == "__main__":
    unittest.main()
