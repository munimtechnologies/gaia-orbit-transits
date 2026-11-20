# SPDX-License-Identifier: Apache-2.0
"""check_inputs.py 0.1.0 -- DR3 rehearsal of the release-day INPUTS of gaia-orbit-transits.

MV2 of Munim, Inc.; made with AI agents working in his name. Apache-2.0. Standard library only.

Run after `fetch_release.py d3a1`, `fetch_release.py d5grade` and `fetch_release.py qcut4` in the
same folder. It checks what the module-fetch rehearsal (gaia-fetchrel-check-v2) did not: that
the inputs the release-day grade steps read from `main` exist and parse with the pinned code.

  I1  the runbook's old path data/sb1comb/combined_summary.json is absent (documents the fix)
  I2  data/sb1comb-v2/combined_summary.json parses; dr4_d3_a1's two rho reads succeed and
      dr4_d5_rate.rho_dr3_from returns the amendment-1 value
  I3  sb1_combine.load_chunks reads all 8 DR3 chunks of data/sb1rob-v1 (dr4_d3_a1 --fetch)
  I4  pinned qcut_dr4 imports pinned qcut and its gold/tier/amp_ratio names exist
  I5  (gaia-qcut-v1 inputs) data/qcut-v1/qcut_columns.csv and qcut_stars.csv on main: reported,
      not required (that job may not have run yet)

Writes OUT/check_inputs.json. Exit 0 if I1-I4 pass, 3 otherwise.
"""
import json
import os
import sys
import urllib.error
import urllib.request

VERSION = "0.1.0"
MAIN = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/"
TIMEOUT = 60


def http_status(url):
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            r.read(1)
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception as exc:          # network trouble is not a 404
        return "error: %s" % exc


def fetch(url, local):
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        data = r.read()
    with open(local, "wb") as fh:
        fh.write(data)
    return len(data)


def main(argv):
    out = argv[0] if argv else "out"
    os.makedirs(out, exist_ok=True)
    sys.path.insert(0, os.getcwd())
    res = {"version": VERSION, "checks": {}}

    st = http_status(MAIN + "data/sb1comb/combined_summary.json")
    res["checks"]["I1_old_path_absent"] = {"status": st, "pass": st == 404}
    print("I1", st, flush=True)

    i2 = {"pass": False}
    try:
        n = fetch(MAIN + "data/sb1comb-v2/combined_summary.json", "combined_summary.json")
        with open("combined_summary.json") as fh:
            comb = json.load(fh)
        a1 = comb["amendment1"]["summary"]["rho_substellar_size"]["rho"]     # dr4_d3_a1 line 71
        pr = comb["primary"]["summary"]["rho_substellar_size"]["rho"]        # dr4_d3_a1 line 72
        import dr4_d5_rate
        rho3 = dr4_d5_rate.rho_dr3_from("combined_summary.json")
        i2 = {"bytes": n, "rho_sub_amendment1": a1, "rho_sub_primary": pr, "d5_rho_dr3": rho3,
              "pass": rho3 == a1 and 0 < a1 < 1 and 0 < pr < 1}
    except Exception as exc:
        i2["error"] = repr(exc)
    res["checks"]["I2_combined_summary"] = i2
    print("I2", json.dumps(i2), flush=True)

    i3 = {"pass": False}
    try:
        import sb1_combine as sc
        loaded, missing = sc.load_chunks(None, MAIN + "data/sb1rob-v1", sc.parse_chunks("0-7"))
        i3 = {"n_loaded": len(loaded), "missing": [str(m) for m in missing],
              "pass": len(loaded) == 8 and not missing}
    except Exception as exc:
        i3["error"] = repr(exc)
    res["checks"]["I3_sb1rob_chunks"] = i3
    print("I3", json.dumps(i3), flush=True)

    i4 = {"pass": False}
    try:
        import qcut
        import qcut_dr4
        names = ["is_gold", "tier", "amp_ratio", "num", "finite", "TIERS", "Q3_COLUMNS"]
        absent = [k for k in names if not hasattr(qcut, k)]
        i4 = {"qcut": qcut.VERSION, "qcut_dr4": qcut_dr4.VERSION, "absent": absent,
              "pass": not absent and qcut.VERSION == "0.1.0" and qcut_dr4.VERSION == "0.1.0"}
    except Exception as exc:
        i4["error"] = repr(exc)
    res["checks"]["I4_qcut_imports"] = i4
    print("I4", json.dumps(i4), flush=True)

    res["checks"]["I5_qcut_v1_on_main"] = {
        "qcut_columns.csv": http_status(MAIN + "data/qcut-v1/qcut_columns.csv"),
        "qcut_stars.csv": http_status(MAIN + "data/qcut-v1/qcut_stars.csv"),
        "required": False}

    required = ["I1_old_path_absent", "I2_combined_summary", "I3_sb1rob_chunks", "I4_qcut_imports"]
    res["pass"] = all(res["checks"][k]["pass"] for k in required)
    with open(os.path.join(out, "check_inputs.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps({"pass": res["pass"]}))
    return 0 if res["pass"] else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
