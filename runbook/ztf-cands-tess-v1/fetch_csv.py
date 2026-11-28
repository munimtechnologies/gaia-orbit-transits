# SPDX-License-Identifier: Apache-2.0
"""Download the committed hand-phased ZTF faint points (data/ztf-shallow-flags/ztf_faint_points.csv) for
ztf_recheck.py. Never fails the job: if the file cannot be fetched, ztf_recheck (the last step) reports it.
MV2 of Munim, Inc.; made with AI agents."""
import os
import sys
import urllib.request

URL = ("https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/"
       "data/ztf-shallow-flags/ztf_faint_points.csv")
try:
    if not os.path.exists("ztf_faint_points.csv"):
        urllib.request.urlretrieve(URL, "ztf_faint_points.csv")
    print("csv bytes", os.path.getsize("ztf_faint_points.csv"))
except Exception as exc:  # noqa: BLE001
    print("csv fetch failed:", exc)
sys.exit(0)
