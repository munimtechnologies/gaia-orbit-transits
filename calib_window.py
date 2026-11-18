# SPDX-License-Identifier: Apache-2.0
"""Window-loss re-analysis of the Gaia DR3 inclination calibration (calib-v3).

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Pre-registration: findings/2026-11-18-calib-window-prereg.md

Why: calib_eclipse_rate 0.7.0 (job gaia-calib-v3) counted an eclipse only if a clean
TESS dip fell within 3 sigma_t (+ half its duration) of Gaia's predicted conjunction.
It found 50 eclipsing targets where Gaia's orbits predict 69.2 (C2, p = 1.4e-4) and
fitted an inflation k = 2.3 of sigma(cos i). But the detected dips scatter with
rms(z) = 1.62 inside +-3 sigma_t (C4 failed): Gaia's timing errors look too small too.
Real eclipses outside the 3-sigma windows were then never counted, which alone lowers
N_obs. This module separates the two effects:

  1. Reproduce calib-v3 exactly at 3 sigma (gate R0).
  2. Count again with windows of 4.5, 6 and 9 sigma_t (capped at P/4, sample fixed),
     with the false-alarm probability scaled to each target's window length.
  3. A joint maximum-likelihood fit of the inclination model (k, or f, or radius
     scale) together with a timing-error scale s_t, using the detected dips' offsets:
     a real eclipse lands at z ~ N(0, s_t^2) and is caught only if |z| < h (window
     half-width in sigma_t units); a false alarm is uniform inside the window.

Top-level imports are stdlib only, so the unit tests run without numpy; the run
itself needs numpy and calib_eclipse_rate.py (fetched by fetch_deps.py).
"""
import argparse
import csv
import json
import math
import os
import statistics
import sys

VERSION = "0.1.0"
NSIGMAS = (3.0, 4.5, 6.0, 9.0)
WIDE_N = 9.0
FA_SENS = (0.04, 0.20)
S_T_GRID = [0.5 * (16.0 ** (i / 59.0)) for i in range(60)]   # 0.5 .. 8
DLNL_95 = 1.92
REPRO_N_MAIN = 162
REPRO_N_OBS = 50


# ------------------------------------------------------------------ pure helpers
def finite(x):
    try:
        return x is not None and math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def window_frac(h, s):
    """P(|Z| < h) for Z ~ N(0, s^2)."""
    if not (s > 0):
        return 1.0
    return math.erf(h / (s * math.sqrt(2.0)))


def normal_density(z, s):
    return math.exp(-0.5 * (z / s) ** 2) / (s * math.sqrt(2.0 * math.pi))


def target_loglike(p, det, z, h, s, fa):
    """Log-likelihood of one target.

    p   probability that an eclipse happened at a covered conjunction (inclination model)
    det was a clean dip matched to a window?
    z   offset / sigma_t of the matched dip (None or nan: no timing, e.g. repeat mode)
    h   window half-width in sigma_t units (None: repeat mode, no window loss)
    s   timing-error scale (true sigma_t = s x Gaia's)
    fa  probability of a false-alarm dip inside the windows
    """
    p = min(max(float(p), 0.0), 1.0)
    fa = min(max(float(fa), 0.0), 1.0)
    if h is None or not finite(h):
        q = fa + (1.0 - fa) * p
        q = min(max(q, 1e-12), 1.0 - 1e-12)
        return math.log(q) if det else math.log(1.0 - q)
    w = window_frac(h, s)
    if not det:
        return math.log(max((1.0 - fa) * (1.0 - p * w), 1e-12))
    if not finite(z):
        return math.log(min(max(fa + (1.0 - fa) * p * w, 1e-12), 1.0))
    z = float(z)
    real = p * normal_density(z, s) if abs(z) <= h else 0.0
    false = fa * (1.0 - p * w) / (2.0 * h)
    return math.log(max(real + false, 1e-300))


def total_loglike(ps, dets, zs, hs, s, fas):
    return sum(target_loglike(p, d, z, h, s, fa)
               for p, d, z, h, fa in zip(ps, dets, zs, hs, fas))


def profile_ci(grid, prof):
    """Best value and 95% interval (drop of 1.92 in lnL) of a profile likelihood."""
    i = max(range(len(prof)), key=lambda j: prof[j])
    ok = [g for g, v in zip(grid, prof) if v >= prof[i] - DLNL_95]
    return {"best": grid[i], "lo95": min(ok), "hi95": max(ok), "lnL": prof[i],
            "ci_hits_grid_edge": bool(prof[0] >= prof[i] - DLNL_95
                                      or prof[-1] >= prof[i] - DLNL_95)}


def joint_fit(par_grid, p_by_par, dets, zs, hs, fas, s_grid=S_T_GRID):
    """Grid ML over (inclination parameter, s_t). p_by_par[i] is the list of
    per-target probabilities at par_grid[i]. Returns profiles and the best point."""
    L = [[total_loglike(p_by_par[i], dets, zs, hs, s, fas) for s in s_grid]
         for i in range(len(par_grid))]
    prof_par = [max(row) for row in L]
    prof_s = [max(L[i][j] for i in range(len(par_grid))) for j in range(len(s_grid))]
    bi = max(range(len(par_grid)), key=lambda i: prof_par[i])
    bj = max(range(len(s_grid)), key=lambda j: L[bi][j])
    return {"par": profile_ci(par_grid, prof_par), "s_t": profile_ci(s_grid, prof_s),
            "best": {"par": par_grid[bi], "s_t": s_grid[bj], "lnL": L[bi][bj]}}


def scaled_fa(fa3, ratio):
    """False-alarm probability for a window 'ratio' times longer than the 3-sigma one."""
    ratio = max(float(ratio), 0.0)
    return 1.0 - (1.0 - fa3) ** ratio


def detect_at(clean, wins, P, n, skip_wide):
    """Highest-SNR clean dip within n sigma_t + dur/2 of a covered window.
    clean: [(t, snr, dur_h)]; wins: [(centre, sd)]. With skip_wide the 0.7.0 rule is
    used (a window wider than P/4 is skipped); otherwise the width is capped at P/4.
    Returns (snr, z, h) or None."""
    best = None
    for tt, snr, dh in clean:
        dh = dh if finite(dh) else 4.0
        for c, sd in wins:
            if not (finite(sd) and sd > 0 and finite(c)):
                continue
            hw = n * sd + dh / 48.0
            if hw > P / 4.0:
                if skip_wide:
                    continue
                hw = P / 4.0
            off = tt - c
            if abs(off) <= hw:
                cand = (snr, off / sd, hw / sd)
                if best is None or cand[0] > best[0] or \
                        (cand[0] == best[0] and abs(cand[1]) < abs(best[1])):
                    best = cand
    return best


def typical_h(wins, dur_typ, P, n, sd_fallback):
    sds = [sd for _, sd in wins if finite(sd) and sd > 0]
    if not sds:
        sds = [sd_fallback] if finite(sd_fallback) and sd_fallback > 0 else []
    if not sds:
        return float(n), float("nan")
    sd = statistics.median(sds)
    hw = min(n * sd + dur_typ / 48.0, P / 4.0)
    return hw / sd, hw


# ------------------------------------------------------------------ the run
def run(data_dir, out_dir, offline=True):
    import numpy as np
    import calib_eclipse_rate as cer

    paths = cer.fetch_inputs(data_dir, offline)
    targets = cer.read_csv(paths["tess_targets.csv"])
    wanted = {str(t.get("source_id", "")).strip() for t in targets}
    priors = cer.read_priors(paths["gaia_edge_on_priors.csv"], wanted)
    events = cer.read_csv(paths["events.csv"])
    windows = cer.load_windows(cer.read_csv(paths["covered_windows.csv"]))
    recs = cer.build_records(targets, priors, events, windows)
    main = [r for r in recs if not r["excluded"]]
    cv = [r for r in main if r["control_valid"]]
    fa3 = sum(1 for r in cv if r["control_hit"]) / len(cv) if cv else 0.0
    res3, _ = cer.analyse(main, fa3)

    ev_by = {}
    for ev in events:
        ev_by.setdefault(str(ev.get("source_id", "")).strip(), []).append(ev)

    def clean_of(sid):
        out = []
        for ev in ev_by.get(sid, []):
            if cer.event_quality(ev):
                out.append((cer.fnum(ev.get("t_center")), cer.fnum(ev.get("snr"), 0.0),
                            cer.fnum(ev.get("duration_h"), 4.0)))
        return out

    rows = []
    mismatch = []
    for r in main:
        sid, P = r["source_id"], r["period_d"]
        wins = windows.get((sid, "t1"), []) + windows.get((sid, "t2"), [])
        clean = clean_of(sid)
        dur_typ = np.nanmean([r["dur1_h"], r["dur2_h"]])
        dur_typ = float(dur_typ) if np.isfinite(dur_typ) else 4.0
        row = {"source_id": sid, "tic": r["tic"], "period_d": P, "mode": r["det_mode"],
               "det_v3": bool(r["detected"])}
        h3, hw3 = typical_h(wins, dur_typ, P, 3.0, r.get("next1_sd_d"))
        for n in NSIGMAS:
            key = f"{n:g}"
            if r["det_mode"] != "window":
                row["det_" + key] = bool(r["detected"])
                row["z_" + key] = float("nan")
                row["h_" + key] = None
                row["fa_ratio_" + key] = 1.0
                continue
            b = detect_at(clean, wins, P, n, skip_wide=(n == 3.0))
            h_n, hw_n = typical_h(wins, dur_typ, P, n, r.get("next1_sd_d"))
            row["det_" + key] = b is not None
            row["z_" + key] = b[1] if b else float("nan")
            row["h_" + key] = b[2] if b else h_n
            row["fa_ratio_" + key] = (hw_n / hw3) if (finite(hw_n) and finite(hw3)
                                                      and hw3 > 0) else 1.0
        if row["det_3"] != row["det_v3"]:
            mismatch.append(sid)
        rows.append(row)

    repro = {"n_main": len(main), "n_obs_v3": res3["n_obs"],
             "n_obs_here_3sigma": sum(1 for x in rows if x["det_3"]),
             "detection_mismatches": mismatch, "fa3": fa3,
             "pass": bool(len(main) == REPRO_N_MAIN and res3["n_obs"] == REPRO_N_OBS
                          and not mismatch)}

    A = cer.arrays(main)
    args = (A["cosi"], A["cosi_sd"], A["lim1"], A["lim2"], A["cov1"], A["cov2"])

    # ---- counts with wider windows (inclination model M0, k = 1)
    counts = {}
    p0 = cer.p_detect(*args)
    for n in NSIGMAS:
        key = f"{n:g}"
        fa_i = np.array([scaled_fa(fa3, x["fa_ratio_" + key]) for x in rows])
        det = np.array([x["det_" + key] for x in rows], dtype=bool)
        pexp = fa_i + (1 - fa_i) * p0
        n_obs, n_exp = int(det.sum()), float(pexp.sum())
        fit_k = cer.fit_1d(lambda k: cer.loglike(cer.p_detect(*args, k=k), det, fa_i),
                           cer.K_GRID)
        zs = [x["z_" + key] for x in rows if x["det_" + key] and finite(x["z_" + key])]
        counts[key] = {"n_obs": n_obs, "n_exp_m0": n_exp,
                       "ratio": n_obs / n_exp if n_exp > 0 else float("nan"),
                       "p_le_obs_m0": cer.poisson_binomial_cdf(pexp, n_obs),
                       "mean_fa": float(fa_i.mean()), "fit_k_no_timing": fit_k,
                       "n_timed": len(zs),
                       "rms_z": float(np.sqrt(np.mean(np.square(zs)))) if zs else None,
                       "frac_abs_z_gt3": float(np.mean(np.abs(zs) > 3)) if zs else None}

    # ---- joint fits on the 3-sigma data (primary) and the 6-sigma data
    def joint(key, fa_level, model):
        dets = [x["det_" + key] for x in rows]
        zs = [x["z_" + key] for x in rows]
        hs = [x["h_" + key] for x in rows]
        fas = [scaled_fa(fa_level, x["fa_ratio_" + key]) for x in rows]
        if model == "k":
            grid = [float(k) for k in cer.K_GRID[::2]]
            pp = [list(cer.p_detect(*args, k=g)) for g in grid]
        elif model == "f":
            grid = [float(f) for f in cer.F_GRID[::2]]
            pp = [list(cer.p_detect(*args, f=g)) for g in grid]
        elif model == "s":
            grid = [float(s) for s in cer.S_GRID[::2]]
            pp = [list(cer.p_detect(*args, s=g)) for g in grid]
        else:  # M0: no inclination freedom
            grid = [1.0]
            pp = [list(cer.p_detect(*args))]
        return joint_fit(grid, pp, dets, zs, hs, fas)

    joints = {}
    for key in ("3", "6"):
        for model in ("k", "f", "s", "m0"):
            joints[f"{key}sigma_{model}_fa{fa3:.2f}"] = joint(key, fa3, model)
    for fa in FA_SENS:
        joints[f"3sigma_k_fa{fa:.2f}"] = joint("3", fa, "k")

    prim = joints[f"3sigma_k_fa{fa3:.2f}"]
    m0 = joints[f"3sigma_m0_fa{fa3:.2f}"]
    wide = counts[f"{WIDE_N:g}"]
    base = counts["3"]
    w2_sens = [joints[f"3sigma_k_fa{fa:.2f}"]["par"]["lo95"] > 1.0 for fa in FA_SENS]
    grades = {
        "R0": {"prediction": "calib-v3 reproduced at 3 sigma (162 targets, 50 seen, same flags)",
               "value": repro, "pass": repro["pass"]},
        "W1": {"prediction": "joint fit: timing scale s_t 95% lower bound > 1",
               "value": prim["s_t"], "pass": bool(prim["s_t"]["lo95"] > 1.0)},
        "W2": {"prediction": "joint fit: k 95% lower bound > 1 (inclination errors too "
                             "small even after window loss)",
               "value": prim["par"], "pass": bool(prim["par"]["lo95"] > 1.0)},
        "W3": {"prediction": "9-sigma windows: ratio <= 0.85 and P(N <= obs | M0) < 0.01",
               "value": {"ratio": wide["ratio"], "p": wide["p_le_obs_m0"]},
               "pass": bool(wide["ratio"] <= 0.85 and wide["p_le_obs_m0"] < 0.01)},
        "W4": {"prediction": "ratio(9 sigma) - ratio(3 sigma) >= 0.10",
               "value": wide["ratio"] - base["ratio"],
               "pass": bool(wide["ratio"] - base["ratio"] >= 0.10)},
        "W5": {"prediction": "W2's verdict unchanged at false-alarm rates 0.04 and 0.20",
               "value": w2_sens,
               "pass": bool(all(v == (prim["par"]["lo95"] > 1.0) for v in w2_sens))},
    }
    if not repro["pass"]:
        for k in ("W1", "W2", "W3", "W4", "W5"):
            grades[k]["note"] = "R0 failed: inputs differ from calib-v3; not graded"
    lr = prim["best"]["lnL"] - m0["best"]["lnL"]

    os.makedirs(out_dir, exist_ok=True)
    cols = ["source_id", "tic", "period_d", "mode", "det_v3"] + \
        [f"{c}_{n:g}" for n in NSIGMAS for c in ("det", "z", "h", "fa_ratio")]
    with open(os.path.join(out_dir, "window_targets.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for x in rows:
            w.writerow([x.get(c, "") for c in cols])
    summary = {"version": VERSION, "reproduction": repro, "counts": counts,
               "joint": joints, "lnL_k_minus_m0_with_s_t": lr, "grades": grades}
    with open(os.path.join(out_dir, "window_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, default=float)

    def f3(x, nd=3):
        return "nan" if x is None or not finite(x) else f"{float(x):.{nd}f}"
    L = [f"# Window-loss re-analysis of the Gaia DR3 inclination calibration "
         f"(calib_window {VERSION})", "",
         "MV2 of Munim, Inc.; made with AI agents. Code Apache-2.0, text CC BY 4.0.", "",
         f"Reproduction of calib-v3: {json.dumps(repro, default=float)}", "",
         "## Counts with wider timing windows (M0 = Gaia's orbits and errors as published)",
         "", "| window | seen | expected | ratio | P(<= seen) | mean FA | k (no timing) | "
         "timed | rms z |", "|---|---|---|---|---|---|---|---|---|"]
    for n in NSIGMAS:
        c = counts[f"{n:g}"]
        fk = c["fit_k_no_timing"]
        L.append(f"| {n:g} sigma | {c['n_obs']} | {f3(c['n_exp_m0'], 1)} | {f3(c['ratio'])} | "
                 f"{c['p_le_obs_m0']:.3g} | {f3(c['mean_fa'])} | {f3(fk['best'], 2)} "
                 f"({f3(fk['lo95'], 2)}-{f3(fk['hi95'], 2)}) | {c['n_timed']} | "
                 f"{f3(c['rms_z'], 2)} |")
    L += ["", "## Joint fits (inclination model x timing scale s_t)", "",
          "| fit | parameter best (95%) | s_t best (95%) | lnL |", "|---|---|---|---|"]
    for name, j in joints.items():
        L.append(f"| {name} | {f3(j['par']['best'], 2)} ({f3(j['par']['lo95'], 2)}-"
                 f"{f3(j['par']['hi95'], 2)}) | {f3(j['s_t']['best'], 2)} "
                 f"({f3(j['s_t']['lo95'], 2)}-{f3(j['s_t']['hi95'], 2)}) | "
                 f"{f3(j['best']['lnL'], 2)} |")
    L += ["", f"lnL(k, s_t) - lnL(M0, s_t) = {f3(lr, 2)}", "", "## Grades", "",
          "| # | prediction | value | pass |", "|---|---|---|---|"]
    for k, v in grades.items():
        L.append(f"| {k} | {v['prediction']} | "
                 f"{json.dumps(v['value'], default=float)[:140]} | "
                 f"{'yes' if v['pass'] else 'no'} |")
    with open(os.path.join(out_dir, "window_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(json.dumps({"repro": repro["pass"], "counts": {k: (v["n_obs"], round(v["n_exp_m0"], 1))
                                                         for k, v in counts.items()},
                      "grades": {k: v["pass"] for k, v in grades.items()}}, default=float))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--online", action="store_true",
                    help="download missing inputs from GitHub (the priors file is not there)")
    a = ap.parse_args(argv)
    run(a.data_dir, a.out_dir, offline=not a.online)
    return 0


if __name__ == "__main__":
    sys.exit(main())
