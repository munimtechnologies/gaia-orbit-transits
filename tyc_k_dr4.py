#!/usr/bin/env python3
# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""tyc_k_dr4 0.1.0: an independent Gaia DR4 test of TYC 6340-23-1's velocity semi-amplitude K.

Pre-registration: findings/2026-11-20-tyc6340-dr4-k-prereg.md (written before Gaia DR4 exists).

TYC 6340-23-1 = TIC 71945261 = Gaia DR3 6853008555751131648 eclipses every 2.3287 d. Gaia DR3's
SB1 orbit gives K = 16.16 +- 0.48 km/s, so the companion weighs 0.097 M_sun, while the eclipses
make it 0.224 R_sun across (1.9 times a normal star of that mass). A normal-size companion
would need K of about 32.4 km/s. DR3's orbit was fitted to epochs up to 28 May 2017. Gaia DR4
adds epochs up to January 2020, and those later epochs are independent of the DR3 orbit.

This script keeps only those later epochs (Julian date > 2457901.5) that pass the counting rule
of dr4_sb1_reality amendment 1 (finite RV with a positive error, no outlier flag, no emission-line
flag). It fits v = g + a cos(2 pi t/P) + b sin(2 pi t/P) at Gaia DR3's fixed period with free
phase, takes K = sqrt(a^2 + b^2), and grades K against the two hypotheses by the
pre-registered rule (see label()).

Stdlib only. The --fetch path imports dr4_sb1_reality and dr4_fetch (pinned in the job) lazily,
so the unit tests need only this file.

Exit codes: 0 graded (any label, including UNTESTABLE); 2 network or DataLink failure (re-file);
4 a column the rule needs is missing; 6 the DataLink epoch-RV retrieval type is not uniquely
identified (rerun with --retrieval-type).
"""
import argparse
import csv
import json
import math
import os
import random
import sys

VERSION = "0.1.0"
SOURCE_ID = "6853008555751131648"
P_GAIA = 2.3289298492522734          # Gaia DR3 nss_two_body_orbit period (d)
P_TESS = 2.3287                      # TESS sector 92 (sensitivity fit only)
T0_TESS_BJD = 2460803.0299           # TESS primary eclipse (BJD_TDB)
K_GAIA = 16.15912885263879           # Gaia DR3 semi_amplitude_primary (km/s)
SK_GAIA = 0.47582424
K_HEAVY = 32.4                       # K a normal-size (0.21 M_sun) companion would need
DR3_END_JD = 2457901.5               # 28 May 2017 00:00, end of DR3 data
GAIA_JD0 = 2455197.5                 # Gaia time origin (2010-01-01 00:00)
MIN_EPOCHS = 6
NSIG = 3.0
SNR_MIN = 3.0
LABELS = ("GAIA_K_CONFIRMED", "HEAVY_K", "OTHER_K", "UNDECIDED", "NO_ORBIT_SIGNAL",
          "UNTESTABLE")


# ------------------------------------------------------------------ pure helpers
def fnum(x, default=float("nan")):
    try:
        v = float(str(x).strip().strip('"'))
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def to_jd(t):
    """Julian date from a Gaia epoch time: full JD (> 2.4e6), MJD (4e4..1e5) or Gaia time
    (days since 2010-01-01, below 4e4). NaN stays NaN."""
    t = fnum(t)
    if not math.isfinite(t):
        return t
    if t > 2.4e6:
        return t
    if 4.0e4 < t < 1.0e5:
        return t + 2400000.5
    return t + GAIA_JD0


def _flag(v):
    s = str(v if v is not None else "").strip().strip('"').lower()
    return s not in ("", "0", "false", "f", "null", "none", "nan", "--")


def epoch_counts(row, rv_col="radial_velocity", err_col="radial_velocity_error"):
    """dr4_sb1_reality amendment 1 rule 3: finite RV with a positive error, outlier_status
    not set, emission_lines not set."""
    v, s = fnum(row.get(rv_col)), fnum(row.get(err_col))
    if not (math.isfinite(v) and s > 0):
        return False
    return not _flag(row.get("outlier_status")) and not _flag(row.get("emission_lines"))


def select_epochs(rows, time_col, rv_col="radial_velocity", err_col="radial_velocity_error",
                  after_jd=DR3_END_JD):
    """(independent, all_counted): lists of (jd, rv, err). Independent = counted and
    jd > after_jd."""
    allc, ind = [], []
    for r in rows:
        if not epoch_counts(r, rv_col, err_col):
            continue
        jd = to_jd(r.get(time_col))
        if not math.isfinite(jd):
            continue
        p = (jd, fnum(r.get(rv_col)), fnum(r.get(err_col)))
        allc.append(p)
        if jd > after_jd:
            ind.append(p)
    return ind, allc


def _solve3(A, b):
    n = 3
    M = [list(A[i]) + [b[i]] + [1.0 if j == i else 0.0 for j in range(n)] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-300:
            return None, None
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        M[c] = [x / piv for x in M[c]]
        for r in range(n):
            if r != c and M[r][c] != 0.0:
                f = M[r][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n] for i in range(n)], [M[i][n + 1:] for i in range(n)]


def fit_circular(pts, P):
    """Weighted fit v = g + a cos(2 pi t/P) + b sin(2 pi t/P) at fixed P, pts = (t, v, s).
    sigma_K from the covariance, scaled by sqrt(chi2_red) when chi2_red > 1 (never shrunk).
    Also the time of the descending zero crossing (the primary-eclipse conjunction for a
    circular orbit). Returns a dict, or None with fewer than 4 points or a singular system."""
    pts = [(t, v, s) for t, v, s in pts if math.isfinite(t) and math.isfinite(v) and s > 0]
    n = len(pts)
    if n < 4 or not (P > 0):
        return None
    t_ref = pts[0][0]
    A = [[0.0] * 3 for _ in range(3)]
    y = [0.0] * 3
    rows = []
    for t, v, s in pts:
        ph = 2.0 * math.pi * (t - t_ref) / P
        x = (1.0, math.cos(ph), math.sin(ph))
        w = 1.0 / (s * s)
        rows.append((x, v, w))
        for i in range(3):
            y[i] += w * x[i] * v
            for j in range(3):
                A[i][j] += w * x[i] * x[j]
    sol, cov = _solve3(A, y)
    if sol is None:
        return None
    g, a, b = sol
    chi2 = sum(w * (v - sum(p * q for p, q in zip(x, sol))) ** 2 for x, v, w in rows)
    chi2r = chi2 / (n - 3) if n > 3 else float("nan")
    scale = max(1.0, chi2r) if math.isfinite(chi2r) else 1.0
    K = math.hypot(a, b)
    if K > 0:
        varK = (a * a * cov[1][1] + b * b * cov[2][2] + 2 * a * b * cov[1][2]) / (K * K)
    else:
        varK = 0.5 * (cov[1][1] + cov[2][2])
    sK = math.sqrt(max(varK, 0.0) * scale)
    # v - g = K cos(ph - theta); descending zero crossing at ph - theta = pi/2
    theta = math.atan2(b, a)
    t_conj = t_ref + P * (theta + 0.5 * math.pi) / (2.0 * math.pi)
    return {"n": n, "gamma": g, "K": K, "sK": sK, "chi2_red": chi2r, "t_conj_jd": t_conj,
            "t_first": min(p[0] for p in pts), "t_last": max(p[0] for p in pts)}


def phase_offset(t_conj, P=P_GAIA, t0=T0_TESS_BJD):
    """Phase of the fitted conjunction relative to the TESS primary eclipse, in [-0.5, 0.5).
    Reported only (the period error propagated over ~1000 cycles is ~0.06 in phase)."""
    if not math.isfinite(t_conj):
        return float("nan")
    d = ((t_conj - t0) / P) % 1.0
    return d - 1.0 if d >= 0.5 else d


def label(fit, n_ind):
    """The pre-registered label of the independent-epoch fit."""
    if n_ind < MIN_EPOCHS or not fit or not (fit["sK"] > 0):
        return "UNTESTABLE"
    K, sK = fit["K"], fit["sK"]
    if K / sK < SNR_MIN:
        return "NO_ORBIT_SIGNAL"
    ok_g = abs(K - K_GAIA) <= NSIG * math.hypot(sK, SK_GAIA)
    ok_h = abs(K - K_HEAVY) <= NSIG * sK
    if ok_g and not ok_h:
        return "GAIA_K_CONFIRMED"
    if ok_h and not ok_g:
        return "HEAVY_K"
    if ok_g and ok_h:
        return "UNDECIDED"
    return "OTHER_K"


def grade(rows, time_col, rv_col="radial_velocity", err_col="radial_velocity_error"):
    ind, allc = select_epochs(rows, time_col, rv_col, err_col)
    fit = fit_circular(ind, P_GAIA)
    out = {"n_rows": len(rows), "n_counted": len(allc), "n_independent": len(ind),
           "fit_independent": fit, "label": label(fit, len(ind)),
           "reported_only": {}}
    ro = out["reported_only"]
    ro["fit_independent_P_TESS"] = fit_circular(ind, P_TESS)
    ro["fit_all_counted_not_independent"] = fit_circular(allc, P_GAIA)
    ro["phase_offset_vs_TESS"] = phase_offset(fit["t_conj_jd"]) if fit else None
    if fit and fit["sK"] > 0:
        ro["z_vs_gaia"] = (fit["K"] - K_GAIA) / math.hypot(fit["sK"], SK_GAIA)
        ro["z_vs_heavy"] = (fit["K"] - K_HEAVY) / fit["sK"]
    return out


# ------------------------------------------------------------------ synthetic self-test
def synth_rows(K, n=28, sigma=2.5, seed=1, t_start=2456880.0, t_end=2458850.0,
               time_mode="gaia"):
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        jd = t_start + (t_end - t_start) * (i + rnd.random()) / n
        v = -17.57 - K * math.sin(2.0 * math.pi * (jd - T0_TESS_BJD) / P_GAIA) \
            + rnd.gauss(0.0, sigma)
        t = jd - GAIA_JD0 if time_mode == "gaia" else jd
        rows.append({"source_id": SOURCE_ID, "obs_time": "%.6f" % t,
                     "radial_velocity": "%.4f" % v, "radial_velocity_error": "%.4f" % sigma,
                     "outlier_status": "0", "emission_lines": "false"})
    return rows


def self_test():
    a = grade(synth_rows(K_GAIA, seed=3), "obs_time")["label"]
    b = grade(synth_rows(K_HEAVY, seed=4), "obs_time")["label"]
    c = grade(synth_rows(K_GAIA, n=8, seed=5, t_end=2457800.0), "obs_time")["label"]
    ok = a == "GAIA_K_CONFIRMED" and b == "HEAVY_K" and c == "UNTESTABLE"
    return ok, {"gaia": a, "heavy": b, "dr3_only": c}


# ------------------------------------------------------------------ I/O
def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        lines = [ln for ln in fh if ln.strip() and not ln.startswith("#")]
    return [{str(k).strip().lower(): v for k, v in r.items() if k is not None}
            for r in csv.DictReader(lines)]


def pick_time_col(columns, override=None):
    cols = [c.strip().lower() for c in columns]
    if override:
        if override.lower() in cols:
            return override.lower()
        raise KeyError("time column %r not found in %s" % (override, cols))
    t = [c for c in cols if "time" in c and not c.endswith(("_error", "_flag"))]
    if len(t) == 1:
        return t[0]
    t2 = [c for c in t if "obs" in c]
    if len(t2) == 1:
        return t2[0]
    raise KeyError("epoch time column not unique: %s (columns %s)" % (t, cols))


def fetch_rows(release, rtype_override=None):
    """Epoch-RV rows for the target through Gaia DataLink, using dr4_sb1_reality's pinned
    plumbing. Returns (rows, info)."""
    import dr4_sb1_reality as rr  # pinned in the job's setup step
    types, head = rr.link_types(release, SOURCE_ID)
    rtype, why = rr.choose_rv_type(types, rtype_override)
    info = {"release": release, "types": types, "retrieval_type": rtype, "why": why}
    if not rtype:
        return None, info
    got = rr.fetch_epoch_rows(release, rtype, [SOURCE_ID])
    return got.get(SOURCE_ID, []), info


def report_md(res):
    f = res.get("fit_independent") or {}
    lines = ["# tyc_k_dr4 %s: TYC 6340-23-1 K from Gaia epochs after DR3" % VERSION, "",
             "**Label: %s**" % res["label"], "",
             "- Epoch rows: %d; counted: %d; independent (JD > %.1f): %d"
             % (res["n_rows"], res["n_counted"], DR3_END_JD, res["n_independent"])]
    if f:
        lines.append("- Independent fit at P = %.6f d: K = %.2f +- %.2f km/s, gamma = %.2f, "
                     "chi2_red = %.2f" % (P_GAIA, f["K"], f["sK"], f["gamma"], f["chi2_red"]))
    lines.append("- Hypotheses: Gaia DR3 K = %.2f +- %.2f; normal-size companion K = %.1f"
                 % (K_GAIA, SK_GAIA, K_HEAVY))
    lines.append("")
    lines.append("Reported only: ```%s```" % json.dumps(res.get("reported_only"), default=str))
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--epochs-csv", help="local epoch-RV CSV instead of --fetch")
    ap.add_argument("--fetch", action="store_true", help="fetch through Gaia DataLink")
    ap.add_argument("--release", default="Gaia DR4")
    ap.add_argument("--retrieval-type")
    ap.add_argument("--time-col")
    ap.add_argument("--rv-col", default="radial_velocity")
    ap.add_argument("--err-col", default="radial_velocity_error")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    ok, st = self_test()
    print(json.dumps({"self_test": ok, "labels": st}))
    if not ok:
        return 3
    if a.self_test:
        return 0
    info = {}
    if a.epochs_csv:
        rows = read_csv(a.epochs_csv)
    elif a.fetch:
        try:
            rows, info = fetch_rows(a.release, a.retrieval_type)
        except Exception as exc:  # network, DataLink or schema trouble: re-file
            json.dump({"error": repr(exc)}, open(os.path.join(a.out_dir, "fetch_error.json"),
                                                 "w"), indent=1)
            print("fetch failed: %r" % exc)
            return 2
        json.dump(info, open(os.path.join(a.out_dir, "datalink_info.json"), "w"), indent=1)
        if rows is None:
            print("epoch-RV retrieval type not identified: %s" % info)
            return 6
    else:
        ap.error("give --epochs-csv or --fetch")
    if rows:
        cols = list(rows[0].keys())
        try:
            tcol = pick_time_col(cols, a.time_col)
        except KeyError as exc:
            print(str(exc))
            return 4
        for need in (a.rv_col, a.err_col):
            if need not in cols:
                print("column %s missing; columns: %s" % (need, cols))
                return 4
        with open(os.path.join(a.out_dir, "tyc_epochs.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        res = grade(rows, tcol, a.rv_col, a.err_col)
        res["time_col"] = tcol
    else:
        res = grade([], "obs_time")
    res.update({"version": VERSION, "source_id": SOURCE_ID, "datalink": info,
                "self_test": st})
    with open(os.path.join(a.out_dir, "tyc_k_dr4.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=str)
    with open(os.path.join(a.out_dir, "tyc_k_dr4_report.md"), "w") as fh:
        fh.write(report_md(res))
    print(json.dumps({"label": res["label"], "n_independent": res["n_independent"],
                      "fit": res["fit_independent"]}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
