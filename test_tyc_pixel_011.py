# Tests for patch_tyc_pixel_011.py (tyc_pixel 0.1.0 -> 0.1.1, amendment 1). Standard library only.
# By MV2 of Munim, Inc.; made with AI agents working in his name. License: Apache-2.0.
import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import patch_tyc_pixel_011 as pt  # noqa: E402

SRC = os.path.join(HERE, "tyc_pixel.py")
SRC010 = os.path.join(HERE, "tyc_pixel_010.py")


def load_011():
    with open(SRC, "r", encoding="utf-8") as f:
        src = f.read()
    if 'VERSION = "0.1.1"' not in src:
        src = pt.apply(src)
    mod = types.ModuleType("tyc_pixel_011_mem")
    exec(compile(src, "tyc_pixel_011_mem.py", "exec"), mod.__dict__)  # noqa: S102
    return mod


# Gaia DR3 values (anonymous TAP, 2026-11-21)
ROWS = [
    {"source_id": "6853008555751131648", "ra": "305.56117809741227", "dec": "-22.07375226448781",
     "phot_rp_mean_mag": "9.967938"},
    {"source_id": "6853008487031438080", "ra": "305.5665", "dec": "-22.0829",
     "phot_rp_mean_mag": "13.75"},
    {"source_id": "6853008452671699328", "ra": "305.54999412955374", "dec": "-22.097617989953907",
     "phot_rp_mean_mag": "12.079847"},
    {"source_id": "x-bad", "ra": "", "dec": "", "phot_rp_mean_mag": ""},
]


@unittest.skipUnless(os.path.exists(SRC), "tyc_pixel.py not next to this test")
class TestPatch(unittest.TestCase):
    def setUp(self):
        self.m = load_011()

    def test_version_and_neighbour(self):
        self.assertEqual(self.m.VERSION, "0.1.1")
        sep = self.m.ang_sep_arcsec(self.m.RA_T, self.m.DEC_T, self.m.RA_N, self.m.DEC_N)
        self.assertAlmostEqual(sep, 94.0, delta=1.5)
        sep38 = self.m.ang_sep_arcsec(self.m.RA_T, self.m.DEC_T, self.m.RA_N38, self.m.DEC_N38)
        self.assertAlmostEqual(sep38, 38.0, delta=1.5)
        # labels and thresholds unchanged
        self.assertEqual(self.m.D_REF, 0.0609)
        self.assertEqual(self.m.Z_DET, 5.0)
        self.assertEqual(self.m.F_ON, 0.7)

    def test_blend_screen(self):
        b = self.m.blend_screen(ROWS)
        self.assertEqual(b["n_stars"], 2)
        self.assertEqual(b["n_capable"], 1)
        self.assertEqual(b["capable"][0]["id"], "6853008452671699328")
        self.assertAlmostEqual(b["capable"][0]["needed_own_depth"], 0.426, delta=0.01)
        s38 = b["star_38_arcsec"][0]
        self.assertEqual(s38["id"], "6853008487031438080")
        self.assertFalse(s38["capable"])
        self.assertGreater(s38["needed_own_depth"], 1.0)
        self.assertAlmostEqual(b["dm_max"], 3.035, delta=0.01)
        self.assertEqual(self.m.blend_screen(ROWS[1:]), {"error": "target not in Gaia rows"})

    def test_patch_is_exact(self):
        src_path = SRC010 if os.path.exists(SRC010) else SRC
        with open(src_path, "r", encoding="utf-8") as f:
            src = f.read()
        if 'VERSION = "0.1.0"' not in src:
            self.skipTest("0.1.0 source not available")
        new = pt.apply(src)
        with self.assertRaises(pt.PatchError):
            pt.apply(new)
        self.assertIn('out["blend_screen"] = blend_screen(grows)', new)
        self.assertNotIn("V = 11.25", new)


if __name__ == "__main__":
    unittest.main()
