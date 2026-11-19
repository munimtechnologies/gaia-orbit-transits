# SPDX-License-Identifier: Apache-2.0
"""Fetch sb1_combine.py (0.1.0) pinned to release v0.28.0 of gaia-orbit-transits.

MV2 of Munim, Inc.; made with AI agents working in his name. Apache-2.0.
"""
import sys
import urllib.request

SHA = "25020a830eb9594182a6f8ed9c4aefc185dfd9af"
URL = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/%s/%s"

for name in ("sb1_combine.py",):
    req = urllib.request.Request(URL % (SHA, name), headers={"User-Agent": "mv2-incfloor/0.1.0"})
    with urllib.request.urlopen(req, timeout=60) as fh:
        data = fh.read()
    if b'VERSION = "0.1.0"' not in data:
        print("unexpected version of", name)
        sys.exit(4)
    with open(name, "wb") as out:
        out.write(data)
    print("fetched", name, len(data), "bytes")
