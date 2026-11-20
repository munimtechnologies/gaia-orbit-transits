# SPDX-License-Identifier: Apache-2.0
"""Offline tests for fetch_release.py (gaia-orbit-transits release-day helper).

MV2 of Munim, Inc.; made with AI agents working in his name. Apache-2.0. Standard library only.
No network: these check the pin table and groups, not the downloads.
"""
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = [os.path.join(HERE, "fetch_release.py"),
              os.path.join(os.getcwd(), "fetch_release.py"),
              os.path.join(os.getcwd(), "runbook", "release", "fetch_release.py")]


def load():
    for path in CANDIDATES:
        if os.path.exists(path):
            spec = importlib.util.spec_from_file_location("fetch_release_under_test", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise unittest.SkipTest("fetch_release.py not found next to the test")


FR = load()
SHA = re.compile(r"^[0-9a-f]{40}$")


class TestPins(unittest.TestCase):
    def test_every_group_path_is_pinned(self):
        for group, paths in FR.GROUPS.items():
            for p in paths:
                self.assertIn(p, FR.PIN, "%s in group %s has no pin" % (p, group))

    def test_pins_are_full_shas(self):
        for p, sha in FR.PIN.items():
            self.assertRegex(sha, SHA, p)

    def test_versions_only_for_pinned_files(self):
        for p in FR.VERSIONS:
            self.assertIn(p, FR.PIN)
            self.assertRegex(FR.VERSIONS[p], r'^VERSION = "\d+\.\d+\.\d+"$')

    def test_local_names_unique_within_group(self):
        for group, paths in FR.GROUPS.items():
            names = [os.path.basename(p) for p in paths]
            self.assertEqual(len(names), len(set(names)), group)

    def test_qcut4_group(self):
        self.assertEqual(FR.GROUPS["qcut4"], ["qcut.py", "qcut_dr4.py"])
        self.assertEqual(FR.PIN["qcut.py"], "2cbdd5b01e6d9bc093afb376b1d176bb8104826d")
        self.assertEqual(FR.PIN["qcut_dr4.py"], "47ffeb67f21388d71122e7a01daa9e4df4f0a1bd")
        self.assertEqual(FR.VERSIONS["qcut.py"], 'VERSION = "0.1.0"')
        self.assertEqual(FR.VERSIONS["qcut_dr4.py"], 'VERSION = "0.1.0"')

    def test_release_v028_pins_unchanged(self):
        for p in ("dr4_fetch.py", "calib_dr4_run.py", "dr4_sb1_reality.py", "dr4_d5_rate.py"):
            self.assertEqual(FR.PIN[p], "25020a830eb9594182a6f8ed9c4aefc185dfd9af", p)

    def test_dr3_combined_points_at_committed_folder(self):
        self.assertTrue(FR.DR3_COMBINED_URL.endswith("/data/sb1comb-v2/combined_summary.json"))
        self.assertNotIn("/data/sb1comb/", FR.DR3_COMBINED_URL)

    def test_raw_url_shape(self):
        url = FR.RAW % (FR.PIN["qcut.py"], "qcut.py")
        self.assertTrue(url.startswith("https://raw.githubusercontent.com/munimtechnologies/"))
        self.assertTrue(url.endswith("/2cbdd5b01e6d9bc093afb376b1d176bb8104826d/qcut.py"))


class TestCli(unittest.TestCase):
    def test_unknown_group_is_refused(self):
        self.assertEqual(FR.main([]), 1)
        self.assertEqual(FR.main(["no-such-group"]), 1)


if __name__ == "__main__":
    unittest.main()
