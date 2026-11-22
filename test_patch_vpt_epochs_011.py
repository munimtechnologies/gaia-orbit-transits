# SPDX-License-Identifier: Apache-2.0
"""Tests for patch_vpt_epochs_011 (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents).
Stdlib only; needs vpt_epochs.py 0.1.0 (commit f868df8e) next to this file."""
import gzip
import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

import patch_vpt_epochs_011 as patch

ve = patch.ve

MD5 = ("75c2  EpochPhotometry_000000-003111.csv.gz\n"
       "7866  EpochPhotometry_003112-005263.csv.gz\n"
       "1234  EpochPhotometry_607600-607800.csv.gz\n"
       "cb1b  EpochPhotometry_786400-786431.csv.gz\n")

TIC93622019_SID = 5345417757181174144   # Gaia DR3 5345417757181174144


class TestHealpix(unittest.TestCase):
    def test_patch_applied(self):
        self.assertEqual(ve.VERSION, "0.1.1")
        self.assertIs(ve.healpix8, patch.healpix8)

    def test_level8_index(self):
        self.assertEqual(patch.healpix8(4295806720), 0)          # a source in HEALPix 0
        self.assertEqual(patch.healpix8((3200 << 43) + 12345), 3200)
        self.assertEqual(patch.healpix8(TIC93622019_SID), 607703)
        # largest possible DR3 source_id (12 * 4**12 level-12 pixels) stays below 12 * 4**8
        self.assertLess(patch.healpix8(12 * 4 ** 12 * 2 ** 35 - 1), 12 * 4 ** 8)

    def test_old_shift_was_level12(self):
        # the 0.1.0 shift gives a level-12 index, out of the files' level-8 range
        self.assertGreater(TIC93622019_SID >> 35, 786431)
        self.assertEqual(TIC93622019_SID >> 35 >> 8, patch.healpix8(TIC93622019_SID))

    def test_file_lookup(self):
        idx = ve.cdn_index(MD5)
        self.assertEqual(len(idx), 4)
        self.assertEqual(ve.cdn_file_for(TIC93622019_SID, idx),
                         "EpochPhotometry_607600-607800.csv.gz")
        self.assertEqual(ve.cdn_file_for((3200 << 43) + 1, idx),
                         "EpochPhotometry_003112-005263.csv.gz")
        self.assertEqual(ve.cdn_file_for(4295806720, idx), "EpochPhotometry_000000-003111.csv.gz")
        self.assertIsNone(ve.cdn_file_for(9999 << 43, idx))


def _bulk_file(rows):
    head = ("# %ECSV 1.0\n# ---\n# datatype: []\n"
            "solution_id,source_id,n_transits,transit_id,g_transit_time,g_transit_flux,"
            "g_transit_flux_error,variability_flag_g_reject\n")
    body = ""
    for sid, times, fluxes in rows:
        n = len(times)
        body += ('375316653866487564,%d,%d,"[%s]","[%s]","[%s]","[%s]","[%s]"\n' % (
            sid, n, ",".join(str(i) for i in range(n)), ",".join(str(t) for t in times),
            ",".join(fluxes), ",".join("1.0" for _ in range(n)),
            ",".join("false" for _ in range(n))))
    return gzip.compress((head + body).encode())


class TestCdnFetch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_end_to_end_stream(self):
        a, c, b = (3200 << 43) + 5, (3200 << 43) + 7, (3200 << 43) + 9
        far = (607703 << 43) + 1
        files = {
            "EpochPhotometry_003112-005263.csv.gz": _bulk_file([
                (a, [1700.1, 1700.2, 1700.3], ["100.0", "101.0", "null"]),
                (c, [1700.4], ["50.0"]),
                (b, [1800.5, 1800.6], ["200.0", "201.0"]),
                ((3200 << 43) + 99, [1.0], ["1.0"]),
            ]),
            "EpochPhotometry_607600-607800.csv.gz": _bulk_file([
                (far, [1900.0, 1900.1, 1900.2, 1900.3], ["10", "11", "12", "13"]),
            ]),
        }
        opened = []

        def fake_urlopen(req, timeout=None):
            name = req.full_url.rsplit("/", 1)[-1]
            opened.append(name)
            return io.BytesIO(files[name])

        with mock.patch.object(ve, "http_get", lambda url, *a, **k: MD5.encode()), \
                mock.patch("urllib.request.urlopen", fake_urlopen):
            out, rows = ve.cdn_fetch([str(a), str(b), str(far)], 10 ** 9, cache_dir=self.tmp)
        self.assertEqual(sorted(out), sorted([str(a), str(b), str(far)]))
        self.assertEqual(len(out[str(a)]["t"]), 3)
        self.assertTrue(out[str(a)]["flux"][2] != out[str(a)]["flux"][2])   # null -> nan
        self.assertEqual(out[str(b)]["flux"], [200.0, 201.0])
        self.assertEqual(len(out[str(far)]["t"]), 4)
        self.assertNotIn(str(c), out)
        self.assertEqual(sorted(opened), sorted(files))
        self.assertTrue(all(r.get("found") == r.get("wanted") for r in rows))
        for sid in (a, b, far):
            self.assertTrue(os.path.exists(os.path.join(self.tmp, "%d.csv" % sid)))
        rec = ve.load_epochs(os.path.join(self.tmp, "%d.csv" % b))
        self.assertEqual(rec["t"], [1800.5, 1800.6])


if __name__ == "__main__":
    unittest.main()
