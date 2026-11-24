# SPDX-License-Identifier: Apache-2.0
"""Download the reused modules at pinned commits (gaia-orbit-transits, MV2 of Munim, Inc.;
made with AI agents): sb2_screen 0.1.0 (0a8883c9), sb2_screen_dr4 0.2.0 (f282d097),
sb2_tier2 0.1.0 (ee76c7ff) and sb2_ffiscan 0.1.0 (b53e2b3c), with their tests."""
import sys
import time
import urllib.request

REPO = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/"
FILES = (
    ("0a8883c902143934f2ca9933affb57cc01a851b1", "sb2_screen.py"),
    ("0a8883c902143934f2ca9933affb57cc01a851b1", "test_sb2_screen.py"),
    ("f282d0979bc9ecdbdba9ed353455bdaf57be3eec", "sb2_screen_dr4.py"),
    ("ee76c7ffb8ba55c54f70b7602a8aaac03a821534", "sb2_tier2.py"),
    ("ee76c7ffb8ba55c54f70b7602a8aaac03a821534", "test_sb2_tier2.py"),
    ("b53e2b3c0e0e1adfbd4ec2c41c9f2405e7e512a9", "sb2_ffiscan.py"),
    ("b53e2b3c0e0e1adfbd4ec2c41c9f2405e7e512a9", "test_sb2_ffiscan.py"),
)


def main():
    for sha, path in FILES:
        for attempt in range(5):
            try:
                with urllib.request.urlopen(REPO + sha + "/" + path, timeout=60) as r:
                    data = r.read()
                if b"Apache-2.0" not in data[:400] or len(data) < 500:
                    raise ValueError("unexpected content for " + path)
                with open(path, "wb") as fh:
                    fh.write(data)
                print("fetched", path, sha[:8], len(data), "bytes", flush=True)
                break
            except Exception as exc:
                print("retry", path, attempt + 1, repr(exc)[:200], flush=True)
                time.sleep(10 * (attempt + 1))
        else:
            print("FAILED", path, flush=True)
            return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
