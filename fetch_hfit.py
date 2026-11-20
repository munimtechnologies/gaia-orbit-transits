# SPDX-License-Identifier: Apache-2.0
"""Setup step for job gaia-eblm-holdout-fit-v1 (stdlib only).

Part of gaia-orbit-transits by MV2 of Munim, Inc.; made with AI agents working in his name.
Apache-2.0. Rules: findings/2026-11-19-eblm-holdout-prereg.md.

1. Fetches eblm_fit.py (must be 0.2.0), eblm_screen.py, eblm_holdout_fit.py and their tests,
   all pinned to the commit that published eblm_fit 0.2.0 (release v0.31.0).
2. Enforces the pre-registered order "holdout ids committed BEFORE any fit": waits (up to
   --wait-min minutes) until data/eblm-holdout/holdout_ids.csv is on the repo's main branch and
   is identical (line endings aside) to the local holdout_ids.csv. Exit 1 otherwise, and the
   fit never runs.
"""
import argparse
import os
import sys
import time
import urllib.request

SHA = "996ced14d2f4ddd431616b0f2d72d49619bc8095"
REPO = "munimtechnologies/gaia-orbit-transits"
RAW = "https://raw.githubusercontent.com/%s/%s/%s"
FILES = {
    "eblm_fit.py": 'VERSION = "0.2.0"',
    "eblm_screen.py": "classify",
    "eblm_holdout_fit.py": 'VERSION = "0.1.0"',
    "test_eblm_fit.py": "import eblm_fit",
    "test_eblm_holdout_fit.py": "import eblm_holdout_fit",
}
IDS_REPO_PATH = "data/eblm-holdout/holdout_ids.csv"


def get(url, attempts=5):
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gaia-orbit-transits",
                                                       "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            print("fetch failed", url, i + 1, exc, flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError("could not fetch %s: %r" % (url, last))


def norm(b):
    return b.replace(b"\r\n", b"\n").strip()


def fetch_pinned():
    ok = True
    for name, marker in FILES.items():
        data = get(RAW % (REPO, SHA, name))
        with open(name, "wb") as fh:
            fh.write(data)
        has = marker.encode() in data
        print("fetched", name, len(data), "marker ok" if has else "MARKER MISSING", flush=True)
        ok = ok and has
    return ok


def ids_committed(local, wait_min, poll_s=60):
    with open(local, "rb") as fh:
        want = norm(fh.read())
    deadline = time.time() + 60 * wait_min
    while True:
        try:
            got = norm(get(RAW % (REPO, "main", IDS_REPO_PATH) + "?t=%d" % int(time.time()), attempts=1))
            if got == want:
                print("holdout_ids.csv is committed on main and identical", flush=True)
                return True
            print("holdout_ids.csv on main differs from the local copy", flush=True)
            return False
        except Exception as exc:  # noqa: BLE001
            print("not on main yet:", exc, flush=True)
        if time.time() > deadline:
            return False
        time.sleep(poll_s)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids-csv", default="holdout_ids.csv")
    ap.add_argument("--wait-min", type=float, default=40.0)
    a = ap.parse_args(argv)
    if not os.path.exists(a.ids_csv):
        print("missing", a.ids_csv)
        return 1
    if not fetch_pinned():
        return 1
    if not ids_committed(a.ids_csv, a.wait_min):
        print("STOP: the holdout ids are not committed; the pre-registration forbids fitting first")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
