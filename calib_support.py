# SPDX-License-Identifier: Apache-2.0
"""calib_support.py -- helpers for the Gaia-inclination calibration job (gaia-calib-v2).

Part of gaia-orbit-transits 0.7.1 by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0.

Why it exists: calib_eclipse_rate.py reads the full v4 prior table
(gaia_edge_on_priors.csv, 15 MB). The publish lane accepts files up to 2 MB only, so
that table never reached the repository and gaia-calib-v1 cannot download it. The job
therefore rebuilds the table with the unchanged run_search.py (--no-tess, the same
arguments and seed as job gaia-orbit-tess-v4; every Monte Carlo draw is seeded by the
source_id alone), and this script checks that the rebuild reproduces v4 before the
pre-registered test is run.

Subcommands
  repro  Compare the rebuilt priors with the published v4 tess_targets.csv (p_ecl and
         m2_dark of every target, exact match expected). Writes priors_repro.json and
         priors_targets.csv (only the target rows, small enough to publish). Exits 1
         if fewer than 99% of the targets match exactly or any differs by more than
         0.02 in p_ecl: the calibration must then not be graded.
  seen   Turn calib_targets.csv into an xmatch_prior.py target list: every system the
         window/repeat rule detected, plus any --extra source_id:tic pairs.
"""
import argparse
import csv
import json
import os
import sys
import urllib.request

RAW = ("https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/"
       "data/dr3-full-search-v4/")
MATCH_FRAC = 0.99
MAX_DIFF = 0.02


def fnum(x):
    try:
        s = str(x).strip()
        return float(s) if s not in ("", "nan", "None") else float("nan")
    except ValueError:
        return float("nan")


def compare(targets, priors):
    """targets: v4 tess_targets rows; priors: rebuilt prior rows.
    Returns a dict with n, n_exact, n_missing, max_diff, worst (list), pass."""
    by = {}
    for p in priors:
        by.setdefault(str(p.get("source_id", "")).strip(), []).append(p)
    n = n_exact = n_missing = 0
    max_diff = 0.0
    worst = []
    for t in targets:
        sid = str(t.get("source_id", "")).strip()
        if not sid:
            continue
        n += 1
        rows = by.get(sid, [])
        st = str(t.get("solution_type", "")).strip()
        row = next((r for r in rows if str(r.get("solution_type", "")).strip() == st),
                   rows[0] if rows else None)
        if row is None:
            n_missing += 1
            worst.append({"source_id": sid, "why": "missing"})
            continue
        same = (str(row.get("p_ecl", "")).strip() == str(t.get("p_ecl", "")).strip()
                and str(row.get("m2_dark", "")).strip() == str(t.get("m2_dark", "")).strip())
        d = abs(fnum(row.get("p_ecl")) - fnum(t.get("p_ecl")))
        if d != d:  # nan
            d = 1.0
        max_diff = max(max_diff, d)
        if same:
            n_exact += 1
        elif len(worst) < 20:
            worst.append({"source_id": sid, "v4_p_ecl": t.get("p_ecl"),
                          "rebuilt_p_ecl": row.get("p_ecl"), "diff": d})
    ok = n > 0 and n_exact >= MATCH_FRAC * n and max_diff <= MAX_DIFF and n_missing == 0
    return {"n": n, "n_exact": n_exact, "n_missing": n_missing, "max_diff": max_diff,
            "worst": worst, "pass": bool(ok)}


def seen_rows(calib_rows, extra=()):
    """xmatch_prior.py targets: detected systems plus extra (source_id, tic) pairs."""
    out, have = [], set()
    for r in calib_rows:
        if str(r.get("detected", "")).strip().lower() not in ("true", "1"):
            continue
        sid = str(r.get("source_id", "")).strip()
        if sid in have:
            continue
        have.add(sid)
        out.append({"source_id": sid, "tic": str(r.get("tic", "")).strip(),
                    "period_d": r.get("period_d", ""),
                    "vet": "eclipse-unvetted (calib %s rule)" % (r.get("det_mode") or "window"),
                    "gaia_eb": r.get("gaia_eb", "False")})
    for sid, tic in extra:
        if sid not in have:
            have.add(sid)
            out.append({"source_id": sid, "tic": tic, "period_d": "",
                        "vet": "eclipse-unvetted (named in 0.7.0 correction)",
                        "gaia_eb": "False"})
    return out


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def cmd_repro(a):
    tpath = os.path.join(a.dir, "tess_targets.csv")
    if not os.path.exists(tpath) or os.path.getsize(tpath) == 0:
        urllib.request.urlretrieve(RAW + "tess_targets.csv", tpath + ".part")
        os.replace(tpath + ".part", tpath)
    targets = read_csv(tpath)
    wanted = {str(t.get("source_id", "")).strip() for t in targets}
    pri_path = os.path.join(a.dir, "gaia_edge_on_priors.csv")
    keep, fields = [], None
    with open(pri_path, newline="", encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        fields = rd.fieldnames
        for row in rd:
            if str(row.get("source_id", "")).strip() in wanted:
                keep.append(row)
    res = compare(targets, keep)
    os.makedirs(a.out_dir, exist_ok=True)
    write_csv(os.path.join(a.out_dir, "priors_targets.csv"), keep, fields)
    with open(os.path.join(a.out_dir, "priors_repro.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "worst"}))
    return 0 if res["pass"] else 1


def cmd_seen(a):
    extra = []
    for pair in (a.extra or "").split(","):
        if ":" in pair:
            s, t = pair.split(":", 1)
            extra.append((s.strip(), t.strip()))
    rows = seen_rows(read_csv(a.calib), extra)
    write_csv(a.out, rows, ["source_id", "tic", "period_d", "vet", "gaia_eb"])
    print(len(rows), "targets for xmatch_prior.py")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("repro")
    r.add_argument("--dir", default="/data/dr3-full-search-v4")
    r.add_argument("--out-dir", default="/out")
    s = sub.add_parser("seen")
    s.add_argument("--calib", default="/out/calib_targets.csv")
    s.add_argument("--out", default="/out/xmatch_targets.csv")
    s.add_argument("--extra", default="")
    a = ap.parse_args(argv)
    return cmd_repro(a) if a.cmd == "repro" else cmd_seen(a)


if __name__ == "__main__":
    sys.exit(main())
