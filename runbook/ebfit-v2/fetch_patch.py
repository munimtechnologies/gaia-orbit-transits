# SPDX-License-Identifier: Apache-2.0
# MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name.
"""Fetch sb2_ebfit 0.1.0 at its pre-registered commit and apply the one-line fix for v2.

sb2-ebfit-v1 (26 Nov 2026) crashed inside its self-test on
    json.dumps(chk)  ->  TypeError: Object of type bool is not JSON serializable
because chk holds numpy booleans. The fix casts them to Python bools in that log line only.
Nothing else in the code changes except the version string (0.1.0 -> 0.1.1).
targets.json is NOT fetched: the v2 config in this folder adds two stars (BD+15 2743, HD 11239).
"""
import pathlib
import sys
import urllib.request

SHA = "669307ba8fa9e33be3883b5b5fbaeb410e04cd1b"
BASE = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/" + SHA + "/"
FILES = {"sb2_ebfit.py": "sb2_ebfit.py", "test_sb2_ebfit.py": "test_sb2_ebfit.py"}
OLD = 'log("synthetic EB", "PASS" if ok2 else "FAIL", json.dumps(chk),'
NEW = 'log("synthetic EB", "PASS" if ok2 else "FAIL", json.dumps({k: bool(v) for k, v in chk.items()}),'
OLD_V = 'VERSION = "0.1.0"'
NEW_V = 'VERSION = "0.1.1"'


def patch(text):
    if text.count(OLD) != 1:
        raise ValueError("patch anchor found %d times, expected 1" % text.count(OLD))
    if text.count(OLD_V) != 1:
        raise ValueError("version anchor found %d times, expected 1" % text.count(OLD_V))
    return text.replace(OLD, NEW).replace(OLD_V, NEW_V)


def main():
    here = pathlib.Path(__file__).resolve().parent
    for src, dst in FILES.items():
        data = urllib.request.urlopen(BASE + src, timeout=180).read()
        (here / dst).write_bytes(data)
        print("fetched", src, len(data), "bytes")
    p = here / "sb2_ebfit.py"
    p.write_text(patch(p.read_text(encoding="utf-8")), encoding="utf-8")
    print("patched sb2_ebfit.py -> 0.1.1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
