# SPDX-License-Identifier: Apache-2.0
"""Unit tests for fetch_hfit (stdlib only). MV2 of Munim, Inc.; made with AI agents."""
import unittest

import fetch_hfit as fh


class TestFetchHfit(unittest.TestCase):
    def test_pin(self):
        self.assertEqual(fh.SHA, "996ced14d2f4ddd431616b0f2d72d49619bc8095")
        self.assertEqual(fh.FILES["eblm_fit.py"], 'VERSION = "0.2.0"')

    def test_norm_ignores_line_endings(self):
        self.assertEqual(fh.norm(b"a,b\r\n1,2\r\n"), fh.norm(b"a,b\n1,2"))
        self.assertNotEqual(fh.norm(b"a,b\n1,2"), fh.norm(b"a,b\n1,3"))


if __name__ == "__main__":
    unittest.main()
