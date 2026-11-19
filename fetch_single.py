# SPDX-License-Identifier: Apache-2.0
"""Fetch the unchanged eblm_single 0.1.0 (and its test) pinned to the commit that published it.

Part of gaia-orbit-transits by MV2 of Munim, Inc.; made with AI agents working in his name.
Apache-2.0. Standard library only. Used by job gaia-bd65286-v1
(findings/2026-11-19-bd65-286-prereg.md). Exit 1 if any file is missing, empty or not 0.1.0.
"""
import os
import sys
import time
import urllib.request

SHA = "04c9387f3c5c8394b775fe0dd05439c60acd3038"   # release v0.23.0: eblm_single 0.1.0
RAW = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/%s/%s"
FILES = {"eblm_single.py": 'VERSION = "0.1.0"', "test_eblm_single.py": "import eblm_single"}


def get(url, local):
    for attempt in range(5):
        try:
            urllib.request.urlretrieve(url, local)
            if os.path.getsize(local) > 0:
                print("fetched", local, os.path.getsize(local), url)
                return True
        except Exception as exc:  # noqa: BLE001
            print("fetch failed", url, attempt + 1, exc)
        time.sleep(10 * (attempt + 1))
    return False


def main():
    ok = True
    for name, marker in FILES.items():
        if not get(RAW % (SHA, name), name):
            ok = False
            continue
        with open(name) as fh:
            if marker not in fh.read():
                print("pinned %s lacks %r" % (name, marker))
                ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
