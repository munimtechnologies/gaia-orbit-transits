# SPDX-License-Identifier: Apache-2.0
"""Tests for vpt_followup (MV2 of Munim, Inc.; made with AI agents). The pure helpers need only
the standard library; the synthetic core test runs only where numpy and astropy are installed."""
import math
import unittest

import vpt_followup as fu

try:
    import numpy  # noqa: F401
    import astropy  # noqa: F401
    HAVE_NP = True
except Exception:
    HAVE_NP = False


class PeriodFactor(unittest.TestCase):
    def test_match_and_aliases(self):
        self.assertEqual(fu.period_factor(2.2, 2.2), 1.0)
        self.assertEqual(fu.period_factor(4.41, 2.2), 2.0)
        self.assertEqual(fu.period_factor(1.1, 2.2), 0.5)
        self.assertEqual(fu.period_factor(6.6, 2.2), 3.0)

    def test_no_match(self):
        # WASP-4 b: Gaia DR3 1.30859 d against the known 1.33823 d
        self.assertIsNone(fu.period_factor(1.3085922, 1.3382310))
        self.assertIsNone(fu.period_factor(float("nan"), 2.0))
        self.assertIsNone(fu.period_factor(2.0, 0.0))

    def test_control_tolerance(self):
        self.assertTrue(fu.control_ok(1.33830, 1.338231, 20.0))
        self.assertFalse(fu.control_ok(1.3400, 1.338231, 20.0))
        self.assertFalse(fu.control_ok(1.33830, 1.338231, 5.0))


class Chi2(unittest.TestCase):
    def test_values(self):
        self.assertAlmostEqual(fu.chi2_sf(3.841458820694124, 1), 0.05, places=5)
        self.assertAlmostEqual(fu.chi2_sf(2.0, 2), math.exp(-1.0), places=8)
        self.assertAlmostEqual(fu.chi2_sf(10.0, 2), math.exp(-5.0), places=10)
        self.assertEqual(fu.chi2_sf(0.0, 3), 1.0)
        self.assertLess(fu.chi2_sf(100.0, 2), 1e-20)

    def test_consistency(self):
        chi2, dof, p = fu.depth_consistency([0.01, 0.01, 0.01], [0.001, 0.001, 0.001])
        self.assertAlmostEqual(chi2, 0.0)
        self.assertEqual(dof, 2)
        self.assertAlmostEqual(p, 1.0)
        chi2, dof, p = fu.depth_consistency([0.01, 0.02], [0.001, 0.001])
        self.assertAlmostEqual(chi2, 50.0)
        self.assertLess(p, 1e-6)
        chi2, dof, p = fu.depth_consistency([0.01], [0.001])
        self.assertEqual(dof, 0)


class Labels(unittest.TestCase):
    base = {"snr": 20.0, "depth": 0.01, "oddeven_z": 0.5, "sec_depth": 0.0, "sec_err": 1e-4,
            "r2_rj": 1.2, "depth_p": 0.5, "period_factor": 1.0}

    def lab(self, **kw):
        d = dict(self.base)
        d.update(kw)
        return fu.vet_label(d)

    def test_survives(self):
        self.assertEqual(self.lab()[2], "SURVIVES")
        self.assertEqual(self.lab(period_factor=2.0)[2], "SURVIVES_OTHER_P")
        self.assertEqual(self.lab(period_factor=None)[2], "SURVIVES_OTHER_P")

    def test_not_detected(self):
        self.assertEqual(self.lab(snr=5.0)[2], "NOT_DETECTED")
        self.assertEqual(self.lab(snr=float("nan"))[2], "NOT_DETECTED")

    def test_eb(self):
        f, n, lab = self.lab(oddeven_z=4.0)
        self.assertEqual(lab, "EB_LIKE")
        self.assertIn("ODD_EVEN", f)
        f, n, lab = self.lab(sec_depth=0.002, sec_err=0.0002)
        self.assertIn("SECONDARY", f)
        # significant but below 10% of the primary: a planet's occultation, not a flag
        f, n, lab = self.lab(sec_depth=0.0005, sec_err=0.0001)
        self.assertNotIn("SECONDARY", f)
        self.assertEqual(lab, "SURVIVES")
        f, n, lab = self.lab(r2_rj=2.3)
        self.assertIn("STELLAR_SIZE", f)

    def test_depth_varies_is_note(self):
        f, n, lab = self.lab(depth_p=1e-5)
        self.assertIn("DEPTH_VARIES", n)
        self.assertEqual(lab, "SURVIVES")


class Grade(unittest.TestCase):
    def test_controls(self):
        res = [{"role": "control", "name": "A", "control_ok": True},
               {"role": "control", "name": "B", "control_ok": False},
               {"role": "candidate", "name": "C", "label": "SURVIVES"}]
        g = fu.grade(res)
        self.assertEqual(g["controls_label"], "CONTROLS_FAIL")
        self.assertFalse(g["candidates"]["C"]["valid"])
        res[1]["control_ok"] = True
        self.assertEqual(fu.grade(res)["controls_label"], "CONTROLS_PASS")


@unittest.skipUnless(HAVE_NP, "numpy/astropy not installed")
class Core(unittest.TestCase):
    def test_self_test(self):
        self.assertTrue(fu.self_test())


if __name__ == "__main__":
    unittest.main()
