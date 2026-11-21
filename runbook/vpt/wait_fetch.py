# SPDX-License-Identifier: Apache-2.0
"""Fetch one file from munimtechnologies/gaia-orbit-transits at a commit or branch, waiting
until it exists (job helper; MV2 of Munim, Inc., made with AI agents).
Usage: wait_fetch.py REF REPO_PATH LOCAL [--wait-min N]"""
import os
import sys
import time
import urllib.request

URL = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/%s/%s"


def main(argv):
    args = list(argv[1:])
    wait_min = 0.0
    if "--wait-min" in args:
        i = args.index("--wait-min")
        wait_min = float(args[i + 1])
        del args[i:i + 2]
    ref, src, dst = args
    d = os.path.dirname(dst)
    if d:
        os.makedirs(d, exist_ok=True)
    t_end = time.time() + 60.0 * wait_min
    attempt = 0
    while True:
        attempt += 1
        try:
            with urllib.request.urlopen(URL % (ref, src), timeout=60) as r:
                data = r.read()
            with open(dst, "wb") as fh:
                fh.write(data)
            print("fetched", ref[:7], src, len(data), "bytes", flush=True)
            return 0
        except Exception as exc:
            print("fetch failed", src, attempt, exc, flush=True)
        if attempt >= 4 and time.time() > t_end:
            return 1
        time.sleep(min(120, 10 * attempt))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
