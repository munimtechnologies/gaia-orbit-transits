# SPDX-License-Identifier: Apache-2.0
"""Fetch one file from munimtechnologies/gaia-orbit-transits (main) into a local path.
Job helper; MV2 of Munim, Inc., made with AI agents. Usage: fetch_repo_file.py REPO_PATH LOCAL"""
import os
import sys
import time
import urllib.request

URL = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/%s"


def main(argv):
    src, dst = argv[1], argv[2]
    d = os.path.dirname(dst)
    if d:
        os.makedirs(d, exist_ok=True)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(URL % src, timeout=60) as r:
                data = r.read()
            with open(dst, "wb") as fh:
                fh.write(data)
            print("fetched", src, len(data), "bytes")
            return 0
        except Exception as exc:
            print("fetch failed", src, attempt + 1, exc)
            time.sleep(10 * (attempt + 1))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
