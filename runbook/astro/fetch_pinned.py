# SPDX-License-Identifier: Apache-2.0
# Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents working in his name).
"""Download the pinned search modules that run_search_dr4.py wraps (unchanged) into the
current folder and record their SHA-256. Pinned to main at
f868df8e101aee2c360d9a7b176c3d2356b462b5 (2026-11-21, release v0.43.0)."""
import hashlib
import json
import sys
import time
import urllib.request

SHA = "f868df8e101aee2c360d9a7b176c3d2356b462b5"
BASE = f"https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/{SHA}/"
FILES = ["run_search.py", "gaia_orbits.py", "dipsearch.py"]


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            print("retry", k + 1, url, exc, flush=True)
            time.sleep(5 * (k + 1))
    raise SystemExit(f"FETCH_FAILED {url}")


def main():
    out = {"sha": SHA, "files": {}}
    for f in FILES:
        b = get(BASE + f)
        with open(f, "wb") as fh:
            fh.write(b)
        out["files"][f] = hashlib.sha256(b).hexdigest()
        print("fetched", f, len(b), "bytes", out["files"][f], flush=True)
    with open("pinned_files.json", "w") as fh:
        json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
