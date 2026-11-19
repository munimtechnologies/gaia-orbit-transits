# SPDX-License-Identifier: Apache-2.0
"""fetch_release.py -- Gaia DR4 release-day set-up helper for gaia-orbit-transits.

MV2 of Munim, Inc.; made with AI agents working in his name. Apache-2.0. Standard library only.

Fetches the unchanged, already-published modules a release-day step needs, each pinned to the
commit that published it, so a release-day job's workdir only has to hold this file.

    python fetch_release.py GROUP [URL::LOCALNAME ...]

GROUP is one of: sb1real, d3a1, calib, wobble, d5, d5grade. Extra URL::LOCALNAME pairs fetch
inputs that earlier release-day jobs committed to the repo (for example a records CSV).
Exit 1 if any file cannot be fetched or is empty: never run a step on a partial set.

2026-11-19 (run 41): dr4_fetch 0.2.0, calib_dr4_run 0.1.1, dr4_sb1_reality 0.1.1 and
dr4_d5_rate 0.1.1 re-pinned to 25020a830eb9594182a6f8ed9c4aefc185dfd9af (release v0.28.0,
calib-dr4 amendment 2: the neighbourhood table's new-release id column is read from TAP_SCHEMA).
"""
import os
import sys
import time
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/%s/%s"

V028 = "25020a830eb9594182a6f8ed9c4aefc185dfd9af"   # release v0.28.0

# path in repo -> full commit SHA of the commit that published it
PIN = {
    "dr4_fetch.py": V028,
    "calib_dr4_run.py": V028,
    "dr4_sb1_reality.py": V028,
    "dr4_d5_rate.py": V028,
    "sb1_transit.py": "2e166f126ff045775b5d0430a0338b2f59375da0",
    "calib_eclipse_rate.py": "2e166f126ff045775b5d0430a0338b2f59375da0",
    "gaia_orbits.py": "2e166f126ff045775b5d0430a0338b2f59375da0",
    "sb1_robust.py": "2f9aa36307f2c501d7f56c24b0088c7bb4061d44",
    "sb1_combine.py": "0c4ca340a679e1903ccd4cdffe19aee4ea6b4f2f",
    "dipsearch.py": "c3c6ce7755749e6d0f22cf9764b74694df16986b",
    "vet_event.py": "c3c6ce7755749e6d0f22cf9764b74694df16986b",
    "calib_window.py": "51b8a35f4dbd28516d14f71e91abbbc778b25a5c",
    "calib_dr4.py": "cd17d1ad75bdfdb8194082975cba55812c7bc1cf",
    "data/calib-window-v1/window_targets.csv": "74736a623df08f3231deb5c0cbc77694fea3b330",
    "dr4_wobble.py": "ea4f08302e25275daa58b7e9e9f6173f78b3e88d",
    "dr4_d3_a1.py": "1e94a8aa30ce0f7457e786cce5c91ad474a9d118",
}
VERSIONS = {"sb1_transit.py": 'VERSION = "0.1.0"', "sb1_robust.py": 'VERSION = "0.2.0"',
            "sb1_combine.py": 'VERSION = "0.1.0"', "dr4_fetch.py": 'VERSION = "0.2.0"',
            "calib_dr4_run.py": 'VERSION = "0.1.1"',
            "dr4_sb1_reality.py": 'VERSION = "0.1.1"', "dr4_d3_a1.py": 'VERSION = "0.1.0"',
            "dr4_d5_rate.py": 'VERSION = "0.1.1"'}
SEARCH = ["sb1_transit.py", "sb1_robust.py", "dipsearch.py", "vet_event.py"]
GROUPS = {
    "sb1real": ["dr4_fetch.py", "dr4_sb1_reality.py"] + SEARCH,
    "d3a1": ["dr4_fetch.py", "dr4_sb1_reality.py", "sb1_combine.py", "dr4_d3_a1.py",
             "sb1_transit.py"],
    "calib": ["dr4_fetch.py", "calib_dr4_run.py", "calib_dr4.py", "calib_eclipse_rate.py",
              "gaia_orbits.py", "calib_window.py", "data/calib-window-v1/window_targets.csv"],
    "wobble": ["dr4_fetch.py", "dr4_wobble.py"],
    "d5": ["dr4_fetch.py", "dr4_sb1_reality.py", "sb1_combine.py", "dr4_d5_rate.py"] + SEARCH,
    "d5grade": ["dr4_fetch.py", "dr4_sb1_reality.py", "sb1_combine.py", "dr4_d5_rate.py"],
}


def get(url, local):
    for attempt in range(5):
        try:
            urllib.request.urlretrieve(url, local)
            if os.path.getsize(local) > 0:
                print("fetched", local, os.path.getsize(local), url)
                return True
        except Exception as exc:
            print("fetch failed", url, attempt + 1, exc)
        time.sleep(10 * (attempt + 1))
    return False


def main(argv):
    if not argv or argv[0] not in GROUPS:
        print("usage: python fetch_release.py {%s} [URL::LOCAL ...]" % ",".join(sorted(GROUPS)))
        return 1
    ok = True
    for path in GROUPS[argv[0]]:
        local = os.path.basename(path)
        if not (os.path.exists(local) and os.path.getsize(local) > 0):
            ok = get(RAW % (PIN[path], path), local) and ok
        if ok and path in VERSIONS:
            with open(local) as fh:
                if VERSIONS[path] not in fh.read():
                    print("pinned %s is not %s" % (local, VERSIONS[path]))
                    ok = False
    for pair in argv[1:]:
        url, _, local = pair.partition("::")
        if not local:
            print("extra input needs URL::LOCAL:", pair)
            return 1
        os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
        ok = get(url, local) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
