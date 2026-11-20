# SPDX-License-Identifier: Apache-2.0
"""Fetch the two modules qcut 0.1.0 uses, each pinned to the commit that published it.

sb1_combine.py 0.1.0 at release v0.28.0 (25020a8) and inclination_floor.py 0.1.0 at release
v0.29.0 (db5b295). MV2 of Munim, Inc.; made with AI agents working in his name. Apache-2.0.
"""
import sys
import urllib.request

URL = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/%s/%s"
PINS = (("25020a830eb9594182a6f8ed9c4aefc185dfd9af", "sb1_combine.py", b'VERSION = "0.1.0"'),
        ("db5b295fe37bbbacae0c76c764eba42f8a281fc9", "inclination_floor.py", b'VERSION = "0.1.0"'))

for sha, name, marker in PINS:
    req = urllib.request.Request(URL % (sha, name), headers={"User-Agent": "gaia-orbit-transits-qcut/0.1.0"})
    with urllib.request.urlopen(req, timeout=60) as fh:
        data = fh.read()
    if marker not in data:
        print("unexpected version of", name)
        sys.exit(4)
    with open(name, "wb") as out:
        out.write(data)
    print("fetched", name, "at", sha[:7], len(data), "bytes")
