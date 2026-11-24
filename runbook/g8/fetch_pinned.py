# SPDX-License-Identifier: Apache-2.0
"""fetch_pinned 0.1.0 - download files of munimtechnologies/gaia-orbit-transits at a fixed commit
(or branch) into a folder. Stdlib only. MV2, Munim, Inc.; made with AI agents.

  python fetch_pinned.py --ref <sha|main> --dest repo --files a.py b.py [--dr3-epochs]

--dr3-epochs also fetches gaia_conj_dips*.py and the saved Gaia DR3 epoch files of every star in
their ORBITS tables, plus data/ijspeert2024-check/ijspeert_check.csv (for the g8 DR3 rehearsal).
"""
import argparse
import importlib
import os
import sys
import time
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/%s/%s"
UA = "gaia-orbit-transits/fetch_pinned (MV2, Munim, Inc.; open research)"
DR3_SETS = (("gaia_conj_dips", "gaia-conj-dips"), ("gaia_conj_dips_acv", "gaia-conj-dips-acv"),
            ("gaia_conj_dips_acv2", "gaia-conj-dips-acv2"))


def get(url):
    last = None
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:
            last = exc
            time.sleep(3 * (a + 1))
    raise RuntimeError("download failed %s: %r" % (url, last))


def fetch(ref, path, dest):
    out = os.path.join(dest, *path.split("/"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    data = get(RAW % (ref, path))
    with open(out, "wb") as fh:
        fh.write(data)
    return len(data)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--dest", default="repo")
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--dr3-epochs", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.dest, exist_ok=True)
    n = 0
    for f in a.files:
        fetch(a.ref, f, a.dest)
        n += 1
    if a.dr3_epochs:
        sys.path.insert(0, os.path.abspath(a.dest))
        fetch(a.ref, "data/ijspeert2024-check/ijspeert_check.csv", a.dest)
        n += 1
        for mod, sub in DR3_SETS:
            fetch(a.ref, mod + ".py", a.dest)
            m = importlib.import_module(mod)
            for sid in m.ORBITS:
                fetch(a.ref, "data/%s/%s_g.csv" % (sub, sid), a.dest)
                n += 1
            n += 1
    print("fetched", n, "files at", a.ref, "into", a.dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
