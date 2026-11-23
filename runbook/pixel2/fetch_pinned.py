# SPDX-License-Identifier: Apache-2.0
"""Download pixel_which_star 0.1.0 and its tests (commit bfbff5f2) and tyc_pixel 0.1.0 (commit
c16e7a2a) from gaia-orbit-transits (MV2 of Munim, Inc.; made with AI agents), unchanged, for
pws_amend_011 (job tic93622019-pixel-011-v1)."""
import sys
import time
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/"
PINS = [
    ("bfbff5f27e523478c5be9f6ee1cc0905f0fb644a", {
        "pixel_which_star.py": "pixel_which_star.py",
        "test_pixel_which_star.py": "test_pixel_which_star.py",
    }),
    ("c16e7a2a6a13cce476f73153483cc59ad8443362", {
        "tyc_pixel.py": "tyc_pixel.py",
    }),
]
MARKS = {"pixel_which_star.py": b'VERSION = "0.1.0"', "test_pixel_which_star.py": b"pixel_which_star",
         "tyc_pixel.py": b'VERSION = "0.1.0"'}


def main():
    for sha, files in PINS:
        for local, path in files.items():
            for attempt in range(5):
                try:
                    with urllib.request.urlopen(RAW + sha + "/" + path, timeout=60) as r:
                        data = r.read()
                    if b"Apache-2.0" not in data[:3000] or MARKS[local] not in data:
                        raise ValueError("unexpected content for " + path)
                    with open(local, "wb") as fh:
                        fh.write(data)
                    print("fetched", local, sha[:8], len(data), "bytes", flush=True)
                    break
                except Exception as exc:
                    print("retry", local, attempt + 1, repr(exc)[:200], flush=True)
                    time.sleep(10 * (attempt + 1))
            else:
                print("FAILED", local, flush=True)
                return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
