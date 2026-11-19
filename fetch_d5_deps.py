# SPDX-License-Identifier: Apache-2.0
"""Fetch the unchanged gaia-orbit-transits modules that dr4_d5_rate imports, pinned by commit
(job set-up helper; MV2 of Munim, Inc., made with AI agents). Apache-2.0."""
import os
import sys
import time
import urllib.request

REPO = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/%s/%s"
PINS = [
    ("2e166f126ff045775b5d0430a0338b2f59375da0", "sb1_transit.py", 'VERSION = "0.1.0"'),
    ("2f9aa36307f2c501d7f56c24b0088c7bb4061d44", "sb1_robust.py", 'VERSION = "0.2.0"'),
    ("0c4ca340a679e1903ccd4cdffe19aee4ea6b4f2f", "sb1_combine.py", 'VERSION = "0.1.0"'),
    ("707f6681aeb46d7bf126ba6abbdffed8f70aefc9", "dr4_fetch.py", 'VERSION = "0.1.0"'),
    ("ee8fcea33e8e81d87c9915f8543f2c78aa3e43e9", "dr4_sb1_reality.py", 'VERSION = "0.1.0"'),
    ("c3c6ce7755749e6d0f22cf9764b74694df16986b", "dipsearch.py", None),
    ("c3c6ce7755749e6d0f22cf9764b74694df16986b", "vet_event.py", None),
]

for sha, f, ver in PINS:
    if not os.path.exists(f):
        for attempt in range(5):
            try:
                urllib.request.urlretrieve(REPO % (sha, f), f)
                print("fetched", f, sha[:7], os.path.getsize(f))
                break
            except Exception as exc:
                print("fetch failed", f, attempt + 1, exc)
                time.sleep(10 * (attempt + 1))
        else:
            sys.exit(1)
    if ver:
        with open(f) as fh:
            if ver not in fh.read():
                print("pinned %s is not %s" % (f, ver))
                sys.exit(1)
sys.exit(0)
