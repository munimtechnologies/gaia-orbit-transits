# SPDX-License-Identifier: Apache-2.0
"""Offline tests for pix_vet 0.1.0 (synthetic pixel cubes; no network). MV2 of Munim, Inc.; AI-made."""
import unittest

import numpy as np

import pix_vet as pv

TPOS = (7.0, 7.0)
NPOS = (6.6, 5.5)   # about 1.55 px away, like TYC 7628-1267-1 and its neighbour


def cube(on, depth=0.1, period=3.0, t0=1.0, dur=0.25, seed=1, ntime=1300):
    rng = np.random.default_rng(seed)
    t = np.arange(ntime) * 0.0208
    shape = (15, 15)
    gt = 1000.0 * pv.gauss(shape, TPOS[0] + 0.2, TPOS[1] - 0.1, 1.0)
    gn = 580.0 * pv.gauss(shape, NPOS[0] + 0.2, NPOS[1] - 0.1, 1.0)
    f = np.repeat((gt + gn + 20.0)[None], ntime, axis=0)
    ph = ((t - t0) / period + 0.5) % 1.0 - 0.5
    inside = np.abs(ph * period) < 0.5 * dur
    if on == "target":
        f[inside] -= depth * gt
    elif on == "neighbour":
        f[inside] -= depth * gn
    f += rng.normal(0, 2.0, f.shape)
    return t, f


class TestPixVet(unittest.TestCase):
    def test_events_counted(self):
        t, f = cube("target")
        ev = pv.events(t, f, 1.0, 3.0, 0.25)
        self.assertGreaterEqual(len(ev), 7)

    def test_on_target(self):
        t, f = cube("target")
        r = pv.analyse_sector(t, f, TPOS, NPOS, 1.0, 3.0, 0.25)
        self.assertGreater(r["dchi2"], 9)
        self.assertEqual(pv.verdict([r])["label"], "ON_TARGET")
        self.assertAlmostEqual(r["f_target_joint"], 0.1, delta=0.03)

    def test_on_neighbour(self):
        t, f = cube("neighbour", depth=0.15)
        r = pv.analyse_sector(t, f, TPOS, NPOS, 1.0, 3.0, 0.25)
        self.assertLess(r["dchi2"], -9)
        self.assertEqual(pv.verdict([r])["label"], "ON_NEIGHBOUR")

    def test_no_signal(self):
        t, f = cube(None)
        r = pv.analyse_sector(t, f, TPOS, NPOS, 1.0, 3.0, 0.25)
        self.assertIn(pv.verdict([r])["label"], ("NO_SIGNAL", "UNRESOLVED"))

    def test_injection_recovers_neighbour(self):
        t, f = cube("target", depth=0.04)
        shape = f.shape[1:]
        gn = pv.gauss(shape, NPOS[0], NPOS[1], 1.0)
        t0f = 1.0 + 0.5 * 3.0   # half an orbit away: no overlap with the real eclipse at P = 3 d
        g = pv.inject(t, f, 580.0 * gn, 0.1, t0f, 3.0, 0.25)
        r = pv.analyse_sector(t, g, TPOS, NPOS, t0f, 3.0, 0.25)
        self.assertEqual(pv.verdict([r])["label"], "ON_NEIGHBOUR")

    def test_insufficient(self):
        self.assertEqual(pv.verdict([])["label"], "INSUFFICIENT")

    def test_shift_found(self):
        t, f = cube("target")
        ap = pv.fit_mask(f.shape[1:], 6.8, 6.25, 3.0)
        sh, dip, n = pv.best_shift(t, f, 1.0 - 0.05, 3.0, 0.25, ap)
        self.assertAlmostEqual(sh, 0.05, delta=0.045)   # flat-bottomed box: a plateau of shifts
        self.assertGreater(dip, 0.02)

    def test_grade_controls(self):
        res = [{"name": "x", "role": "target", "verdict": {"label": "ON_TARGET"},
                "verdict_inject_neighbour": {"label": "ON_NEIGHBOUR"},
                "verdict_inject_target": {"label": "ON_TARGET"}},
               {"name": "c", "role": "control", "verdict": {"label": "ON_TARGET"}}]
        g = pv.grade(res)
        self.assertTrue(g["controls_ok"])
        self.assertEqual(g["M_target"], "ON_TARGET")


if __name__ == "__main__":
    unittest.main()
