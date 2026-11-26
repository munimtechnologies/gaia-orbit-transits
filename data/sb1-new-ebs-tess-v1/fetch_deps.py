# SPDX-License-Identifier: Apache-2.0
"""Fetch the unchanged gaia-orbit-transits modules the TESS check of the six unlisted Gaia SB1
eclipse candidates uses, pinned by commit (job set-up helper; MV2 of Munim, Inc., made with AI
agents). Same pins as job hd11239-tess-v1."""
import os
import sys
import time
import urllib.request

REPO = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/%s/%s"
PINS = [
    ("c3c6ce7755749e6d0f22cf9764b74694df16986b", "dipsearch.py"),     # v0.13.1, dipsearch 0.4.4
    ("c3c6ce7755749e6d0f22cf9764b74694df16986b", "vet_event.py"),     # v0.13.1, vet_event 0.1.0
    ("2d3d30f9440ea3b5b97976edec5118a270836ff1", "sb1_transit.py"),   # sb1_transit 0.1.0
    ("945ad9850ca0837a93050d77f121c788a5db58e3", "gaia_vpt_tess.py"),  # v0.41.0, 0.1.1
    ("0d8d4c5cddcd3d880cb71371013eb85fe40b9073", "vpt_followup.py"),   # vpt_followup 0.1.0
    ("0d8d4c5cddcd3d880cb71371013eb85fe40b9073", "test_vpt_followup.py"),
]

for sha, f in PINS:
    if os.path.exists(f):
        print("have", f)
        continue
    for attempt in range(4):
        try:
            urllib.request.urlretrieve(REPO % (sha, f), f)
            print("fetched", f, sha[:7], os.path.getsize(f))
            break
        except Exception as exc:
            print("fetch failed", f, attempt + 1, exc)
            time.sleep(5 * (attempt + 1))
    else:
        sys.exit(1)
sys.exit(0)
