# SPDX-License-Identifier: Apache-2.0
"""calib_support.py -- helpers for the Gaia-inclination calibration job (gaia-calib-v3).

Part of gaia-orbit-transits 0.13.0 by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0.

Why it exists: calib_eclipse_rate.py reads the full v4 prior table
(gaia_edge_on_priors.csv, 15 MB). The publish lane accepts files up to 2 MB only, so
that table never reached the repository. The job therefore rebuilds the table with the
unchanged run_search.py (--no-tess, the same arguments and seed as job
gaia-orbit-tess-v4; every Monte Carlo draw is seeded by the source_id alone), and this
script checks that the rebuild reproduces v4 before the pre-registered test is run.

Subcommands
  repro  Compare the rebuilt priors with the published v4 tess_targets.csv.
         Two modes:
         * exact (default, the gaia-calib-v2 rule): p_ecl and m2_dark must match as
           strings for >= 99% of targets, none missing, no |dp_ecl| > 0.02.
         * --mode noise (the gaia-calib-v3 amendment, findings/
           2026-11-18-calib-v3-amendment.md): the rebuild may differ from v4 only at
           the level of input rounding and Monte Carlo noise. Passes if no target is
           missing, every |dG| <= --gmag-tol, every relative m2_dark difference <=
           --m2-rel-tol, every |dp_ecl| <= --max-diff and |mean dp_ecl| <= --mean-tol.
         Writes priors_repro.json, priors_targets.csv (target rows only, small enough
         to publish) and priors_diffs.csv (every target that is not an exact match).
         Exits 1 on failure: the calibration must then not be graded.
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
# gaia-calib-v3 noise-mode defaults (see the docstring)
NOISE_MAX_DIFF = 0.035   # ~1.7 x the largest Monte Carlo sd for 600 draws (0.0204)
NOISE_MEAN_TOL = 0.005
NOISE_M2_REL_TOL = 1e-5
NOISE_GMAG_TOL = 1e-4


def fnum(x):
    try:
        s = str(x).strip()
        return float(s) if s not in ("", "nan", "None") else float("nan")
    except ValueError:
        return float("nan")


def _pick(rows, st):
    return next((r for r in rows if str(r.get("solution_type", "")).strip() == st),
                rows[0] if rows else None)


def _reldiff(a, b):
    if a != a or b != b:
        return 0.0 if (a != a and b != b) else float("inf")
    den = max(abs(a), abs(b))
    return 0.0 if den == 0 else abs(a - b) / den


def compare(targets, priors, mode="exact", max_diff=None, match_frac=MATCH_FRAC,
            mean_tol=NOISE_MEAN_TOL, m2_rel_tol=NOISE_M2_REL_TOL,
            gmag_tol=NOISE_GMAG_TOL):
    """targets: v4 tess_targets rows; priors: rebuilt prior rows.
    Returns a dict with n, n_exact, n_missing, max_diff, worst (list), diffs (all
    non-exact rows), pass, and in noise mode mean_diff, max_m2_rel, max_gmag_diff."""
    if max_diff is None:
        max_diff = MAX_DIFF if mode == "exact" else NOISE_MAX_DIFF
    by = {}
    for p in priors:
        by.setdefault(str(p.get("source_id", "")).strip(), []).append(p)
    n = n_exact = n_missing = n_pdiff = 0
    mx = 0.0
    sum_d = 0.0
    n_d = 0
    max_m2_rel = 0.0
    max_gmag = 0.0
    diffs = []
    for t in targets:
        sid = str(t.get("source_id", "")).strip()
        if not sid:
            continue
        n += 1
        st = str(t.get("solution_type", "")).strip()
        row = _pick(by.get(sid, []), st)
        if row is None:
            n_missing += 1
            diffs.append({"source_id": sid, "solution_type": st, "why": "missing"})
            continue
        same = (str(row.get("p_ecl", "")).strip() == str(t.get("p_ecl", "")).strip()
                and str(row.get("m2_dark", "")).strip() == str(t.get("m2_dark", "")).strip())
        pv, pr = fnum(t.get("p_ecl")), fnum(row.get("p_ecl"))
        signed = pr - pv
        d = abs(signed)
        if d != d:  # nan
            d, signed = 1.0, 1.0
        mx = max(mx, d)
        sum_d += signed
        n_d += 1
        if d > 0:
            n_pdiff += 1
        m2r = _reldiff(fnum(t.get("m2_dark")), fnum(row.get("m2_dark")))
        max_m2_rel = max(max_m2_rel, m2r)
        gv, gr = fnum(t.get("gmag")), fnum(row.get("gmag"))
        gd = abs(gv - gr) if (gv == gv and gr == gr) else 0.0
        max_gmag = max(max_gmag, gd)
        if same:
            n_exact += 1
        else:
            diffs.append({"source_id": sid, "solution_type": st,
                          "v4_p_ecl": t.get("p_ecl"), "rebuilt_p_ecl": row.get("p_ecl"),
                          "dp_ecl": signed, "v4_m2_dark": t.get("m2_dark"),
                          "rebuilt_m2_dark": row.get("m2_dark"), "m2_rel_diff": m2r,
                          "v4_gmag": t.get("gmag"), "rebuilt_gmag": row.get("gmag"),
                          "v4_class": t.get("class"), "rebuilt_class": row.get("class"),
                          "period_d": t.get("period_d"), "why": "differs"})
    mean_d = sum_d / n_d if n_d else 0.0
    worst = sorted([x for x in diffs if x.get("why") == "missing"], key=lambda x: x["source_id"])
    worst += sorted([x for x in diffs if x.get("why") == "differs"],
                    key=lambda x: -abs(x["dp_ecl"]))
    if mode == "exact":
        ok = n > 0 and n_exact >= match_frac * n and mx <= max_diff and n_missing == 0
    else:
        ok = (n > 0 and n_missing == 0 and mx <= max_diff and abs(mean_d) <= mean_tol
              and max_m2_rel <= m2_rel_tol and max_gmag <= gmag_tol)
    return {"mode": mode, "n": n, "n_exact": n_exact, "n_missing": n_missing,
            "n_p_ecl_differs": n_pdiff, "max_diff": mx, "mean_diff": mean_d,
            "max_m2_rel": max_m2_rel, "max_gmag_diff": max_gmag,
            "limits": {"max_diff": max_diff, "match_frac": match_frac if mode == "exact" else None,
                       "mean_tol": mean_tol if mode != "exact" else None,
                       "m2_rel_tol": m2_rel_tol if mode != "exact" else None,
                       "gmag_tol": gmag_tol if mode != "exact" else None},
            "worst": worst[:20], "diffs": diffs, "pass": bool(ok)}


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


DIFF_FIELDS = ["source_id", "solution_type", "why", "v4_p_ecl", "rebuilt_p_ecl", "dp_ecl",
               "v4_m2_dark", "rebuilt_m2_dark", "m2_rel_diff", "v4_gmag", "rebuilt_gmag",
               "v4_class", "rebuilt_class", "period_d"]


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
    kw = {"mode": a.mode}
    if a.max_diff is not None:
        kw["max_diff"] = a.max_diff
    res = compare(targets, keep, **kw)
    os.makedirs(a.out_dir, exist_ok=True)
    write_csv(os.path.join(a.out_dir, "priors_targets.csv"), keep, fields)
    write_csv(os.path.join(a.out_dir, "priors_diffs.csv"), res["diffs"], DIFF_FIELDS)
    with open(os.path.join(a.out_dir, "priors_repro.json"), "w", encoding="utf-8") as fh:
        json.dump({k: v for k, v in res.items() if k != "diffs"}, fh, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ("worst", "diffs")}))
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
    r.add_argument("--mode", choices=("exact", "noise"), default="exact")
    r.add_argument("--max-diff", type=float, default=None)
    s = sub.add_parser("seen")
    s.add_argument("--calib", default="/out/calib_targets.csv")
    s.add_argument("--out", default="/out/xmatch_targets.csv")
    s.add_argument("--extra", default="")
    a = ap.parse_args(argv)
    return cmd_repro(a) if a.cmd == "repro" else cmd_seen(a)


if __name__ == "__main__":
    sys.exit(main())
