# SPDX-License-Identifier: Apache-2.0
"""Fetch the unchanged gaia-orbit-transits modules and the Gaia DR3 input table that vpt_pf
uses, each pinned by full commit SHA (job set-up helper; MV2 of Munim, Inc., made with AI
agents)."""
import os
import sys
import time
import urllib.request

REPO = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/%s/%s"
PINS = [
    ("c3c6ce7755749e6d0f22cf9764b74694df16986b", "dipsearch.py", "dipsearch.py"),
    ("c3c6ce7755749e6d0f22cf9764b74694df16986b", "vet_event.py", "vet_event.py"),
    ("2d3d30f9440ea3b5b97976edec5118a270836ff1", "sb1_transit.py", "sb1_transit.py"),
    ("945ad9850ca0837a93050d77f121c788a5db58e3", "gaia_vpt_tess.py", "gaia_vpt_tess.py"),
    ("d1805bf07a146795e004e384057d5f9c8e6a3c3f", "vpt_followup.py", "vpt_followup.py"),
    # all 214 rows of gaiadr3.vari_planetary_transit + gaia_source/FLAME columns, as written by
    # gaia_vpt_tess 0.1.0 in job gaia-vpt-dr3-c0-v1 (committed in 9d8db1a9)
    ("9d8db1a9e6c37a931c6ca44a2f11f81901303e09", "data/vpt-dr3-v1/c0/vpt_candidates.csv",
     "vpt_candidates.csv"),
]

for sha, path, local in PINS:
    if os.path.exists(local):
        print("have", local)
        continue
    for attempt in range(4):
        try:
            urllib.request.urlretrieve(REPO % (sha, path), local)
            print("fetched", path, sha[:8], os.path.getsize(local))
            break
        except Exception as exc:
            print("fetch failed", path, attempt + 1, exc)
            time.sleep(5 * (attempt + 1))
    else:
        sys.exit(1)
sys.exit(0)
