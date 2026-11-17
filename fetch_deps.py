# SPDX-License-Identifier: Apache-2.0
"""Fetch the unchanged modules of gaia-orbit-transits that are not in this folder
(job set-up helper; MV2 of Munim, Inc., made with AI agents)."""
import os
import sys
import time
import urllib.request

BASE = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/"
FILES = ["gaia_orbits.py", "dipsearch.py", "run_search.py", "archival.py",
         "test_gaia_orbits.py", "test_dipsearch.py"]
OPTIONAL = {"archival.py"}

for f in FILES:
    if os.path.exists(f):
        print("have", f)
        continue
    for attempt in range(4):
        try:
            urllib.request.urlretrieve(BASE + f, f)
            print("fetched", f, os.path.getsize(f))
            break
        except Exception as exc:
            print("fetch failed", f, attempt + 1, exc)
            time.sleep(5 * (attempt + 1))
    else:
        if f not in OPTIONAL:
            sys.exit(1)
sys.exit(0)
