# SPDX-License-Identifier: Apache-2.0
# MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name.
# https://github.com/munimtechnologies/gaia-orbit-transits
"""ecl_timing 0.1.0: eclipse times of every TESS light curve, sector by sector and
eclipse by eclipse, measured against a FIXED reference ephemeris (for HD 11239: the
conjunctions of its Gaia DR3 double-lined orbit; nothing is fitted to the period).

Why: sb2-ebfit-v2 (27 Nov 2026) fitted HD 11239's TESS sectors 3 and 30 jointly and
returned P = 3.119557 d, 28 sigma below Gaia's 3.1208264 d, while ASAS-3 (2000-2009)
had matched Gaia's period. This job asks, per sector, where the eclipses actually are.

Method, per light curve (one TESS product = one sector from one pipeline):
  * predicted eclipse times tp = t_conj_f + n P for both conjunction families f = 0, 1;
  * each eclipse window |t - tp| <= W with enough cadences is one event, with its own
    linear baseline a_k + b_k (t - tp);
  * a Gaussian eclipse template of the star's FWHM, averaged over each exposure, with one
    depth per family, is shifted by a common offset dt over a grid; least squares at each
    dt (depths >= 0); chi2(dt) is computed on a fixed set of points, so chi2 values at
    different dt compare directly;
  * best dt = grid minimum refined by a parabola; sigma from the curvature with chi2
    rescaled to chi2_red = 1; the best rival minimum more than one FWHM away is reported
    with its delta chi2 (bimodality check);
  * the same scan per single event gives eclipse-by-eclipse O-C.
"""
import argparse
import csv
import json
import math
import os
import re
import sys
import time

import numpy as np

VERSION = "0.1.0"
DAY = 86400.0
AUTHORS = ("SPOC", "TESS-SPOC", "QLP")
MAX_PRODUCTS = 16


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def clean(o):
    """Make numpy scalars, arrays and non-finite floats JSON-safe."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        x = float(o)
        return x if math.isfinite(x) else None
    return o


def dumps(o, **kw):
    return json.dumps(clean(o), **kw)


def fnum(v, default=float("nan")):
    try:
        if v is None:
            return default
        s = str(v).strip().strip('"')
        if s in ("", "null", "NULL", "nan", "NaN", "None", "--"):
            return default
        x = float(s)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- model pieces

def n_sub(exptime):
    """Odd number of sub-samples across one exposure (1 for <= 200 s)."""
    if not math.isfinite(exptime) or exptime <= 200:
        return 1
    return min(int(math.ceil(exptime / 120.0)) | 1, 15)


def template(x, fwhm, exptime):
    """Gaussian dip shape (peak 1 at x = 0 for short exposures), averaged over the exposure.
    x: time from eclipse centre in days (array)."""
    x = np.asarray(x, float)
    s = fwhm / 2.3548200450309493
    nss = n_sub(exptime)
    if nss == 1:
        return np.exp(-0.5 * (x / s) ** 2)
    off = ((np.arange(nss) + 0.5) / nss - 0.5) * exptime / DAY
    xx = x[:, None] + off[None, :]
    return np.exp(-0.5 * (xx / s) ** 2).mean(axis=1)


def find_events(t, ref, window, exptime, min_frac=0.5):
    """Eclipse windows of both families inside the data. Returns list of dicts
    {family, n, tp, idx} with idx the indices of points with |t - tp| <= window."""
    t = np.asarray(t, float)
    if t.size == 0:
        return []
    P = float(ref["P"])
    cad = max(float(exptime), 20.0) / DAY
    need = min_frac * (2.0 * window / cad)
    ev = []
    for fam, key in ((0, "t_conj0"), (1, "t_conj1")):
        t0 = float(ref[key])
        n_lo = int(math.floor((t.min() - window - t0) / P))
        n_hi = int(math.ceil((t.max() + window - t0) / P))
        for n in range(n_lo, n_hi + 1):
            tp = t0 + n * P
            idx = np.nonzero(np.abs(t - tp) <= window)[0]
            if idx.size < max(need, 12):
                continue
            # both halves of the window must have data (baseline on both sides)
            left = np.sum(t[idx] < tp - 0.5 * window)
            right = np.sum(t[idx] > tp + 0.5 * window)
            if left < 3 or right < 3:
                continue
            ev.append({"family": fam, "n": n, "tp": tp, "idx": idx})
    ev.sort(key=lambda e: e["tp"])
    return ev


def solve_at(t, f, events, dt, fwhm, exptime):
    """Least squares at one offset dt. Returns (chi2, depths dict, n_points, n_par)."""
    idx_all = np.concatenate([e["idx"] for e in events])
    tt = t[idx_all]
    ff = f[idx_all]
    m = tt.size
    k = len(events)
    cols = []
    row0 = 0
    fam_cols = {0: np.zeros(m), 1: np.zeros(m)}
    for j, e in enumerate(events):
        nj = e["idx"].size
        c1 = np.zeros(m)
        c2 = np.zeros(m)
        c1[row0:row0 + nj] = 1.0
        c2[row0:row0 + nj] = tt[row0:row0 + nj] - e["tp"]
        cols.append(c1)
        cols.append(c2)
        fam_cols[e["family"]][row0:row0 + nj] = -template(
            tt[row0:row0 + nj] - e["tp"] - dt, fwhm, exptime)
        row0 += nj
    fams = [fa for fa in (0, 1) if np.any(fam_cols[fa] != 0)]
    depths = {}
    active = list(fams)
    for _ in range(3):
        A = np.column_stack(cols + [fam_cols[fa] for fa in active]) if active else np.column_stack(cols)
        coef, _, _, _ = np.linalg.lstsq(A, ff, rcond=None)
        dep = {fa: float(coef[2 * k + i]) for i, fa in enumerate(active)}
        neg = [fa for fa, d in dep.items() if d < 0]
        if not neg:
            break
        active = [fa for fa in active if fa not in neg]
    else:
        A = np.column_stack(cols)
        coef, _, _, _ = np.linalg.lstsq(A, ff, rcond=None)
        dep = {}
    resid = ff - A @ coef
    for fa in (0, 1):
        depths[fa] = dep.get(fa, 0.0)
    return float(resid @ resid), depths, m, A.shape[1]


def scan(t, f, events, fwhm, exptime, dt_max, step):
    grid = np.arange(-dt_max, dt_max + 0.5 * step, step)
    chi = np.empty(grid.size)
    deps = []
    npts = npar = 0
    for i, dt in enumerate(grid):
        chi[i], d, npts, npar = solve_at(t, f, events, dt, fwhm, exptime)
        deps.append(d)
    i0 = int(np.argmin(chi))
    dof = max(npts - npar, 1)
    s2 = chi[i0] / dof
    # parabola over points within fwhm/4 of the minimum
    sel = np.abs(grid - grid[i0]) <= max(fwhm / 4.0, 2.5 * step)
    best = float(grid[i0])
    sig = float("nan")
    if sel.sum() >= 3:
        c2, c1, c0 = np.polyfit(grid[sel], chi[sel], 2)
        if c2 > 0:
            v = -c1 / (2.0 * c2)
            if abs(v - grid[i0]) <= 2 * step:
                best = float(v)
            sig = float(math.sqrt(s2 / c2))
    # best rival minimum more than one FWHM away from the best
    far = np.abs(grid - grid[i0]) > fwhm
    rival = None
    loc = np.zeros(grid.size, bool)
    if grid.size >= 3:
        loc[1:-1] = (chi[1:-1] <= chi[:-2]) & (chi[1:-1] <= chi[2:])
    cand = far & loc
    if cand.any():
        j = int(np.argmin(np.where(cand, chi, np.inf)))
        rival = {"dt": float(grid[j]), "dchi2_scaled": float((chi[j] - chi[i0]) / s2)}
    at0 = int(np.argmin(np.abs(grid)))
    return {"grid": grid, "chi2": chi, "dt_best": best, "dt_sigma": sig,
            "chi2_min": float(chi[i0]), "chi2_red": float(s2), "n_points": int(npts),
            "n_par": int(npar), "depths_at_best": deps[i0],
            "dchi2_scaled_at_0": float((chi[at0] - chi[i0]) / s2), "rival": rival}


def dchi2_at(res, dt):
    """Scaled delta chi2 (vs the minimum) at an arbitrary offset, linear interpolation."""
    g, c = res["grid"], res["chi2"]
    if dt < g[0] or dt > g[-1]:
        return float("nan")
    return float((np.interp(dt, g, c) - res["chi2_min"]) / res["chi2_red"])


def alt_offset(events, alt):
    """Mean offset of an alternative linear ephemeris from the reference, over these events."""
    if not alt:
        return float("nan")
    out = []
    for e in events:
        n = round((e["tp"] - alt["t_ref"]) / alt["P"])
        ta = alt["t_ref"] + n * alt["P"]
        # the alternative's other family sits half a period away
        cands = [ta, ta + 0.5 * alt["P"], ta - 0.5 * alt["P"]]
        out.append(min(cands, key=lambda x: abs(x - e["tp"])) - e["tp"])
    return float(np.mean(out)) if out else float("nan")


def clip_high(f, nsig=5.0):
    med = np.median(f)
    mad = 1.4826 * np.median(np.abs(f - med))
    if not mad > 0:
        return np.ones(f.size, bool)
    return f < med + nsig * mad


def measure_lc(lc, star):
    t, f, ex = lc["t"], lc["f"], float(lc["exptime"])
    ok = clip_high(f)
    t, f = t[ok], f[ok]
    W, fwhm = star["window_d"], star["fwhm_d"]
    events = find_events(t, star["ref"], W, ex)
    out = {"sector": lc["sector"], "author": lc["author"], "exptime": ex,
           "n_events": len(events), "events": []}
    if len(events) < 1:
        out["status"] = "NO_EVENTS"
        return out, None
    res = scan(t, f, events, fwhm, ex, star["dt_max_d"], star["step_d"])
    out.update({k: res[k] for k in ("dt_best", "dt_sigma", "chi2_red", "n_points",
                                    "dchi2_scaled_at_0", "rival", "depths_at_best")})
    a = alt_offset(events, star.get("alt"))
    out["alt_offset"] = a
    out["dchi2_scaled_at_alt"] = dchi2_at(res, a) if math.isfinite(a) else float("nan")
    out["status"] = "OK"
    for e in events:
        r1 = scan(t, f, [e], fwhm, ex, star["dt_max_d"], star["step_d"])
        out["events"].append({"family": e["family"], "n": e["n"], "tp": e["tp"],
                              "n_points": int(e["idx"].size), "dt_best": r1["dt_best"],
                              "dt_sigma": r1["dt_sigma"],
                              "depth": r1["depths_at_best"][e["family"]],
                              "dchi2_scaled_at_0": r1["dchi2_scaled_at_0"]})
    return out, res


# ---------------------------------------------------------------- self-test

def synth(P, t0, depth, fwhm, exptime, days, noise, offset, seed):
    rng = np.random.default_rng(seed)
    cad = exptime / DAY
    t = np.arange(t0 + 0.37, t0 + 0.37 + days, cad)
    f = np.ones(t.size)
    for tc0 in (t0, t0 + 0.5 * P):
        n = np.round((t - tc0 - offset) / P)
        f -= depth * template(t - tc0 - offset - n * P, fwhm, exptime)
    f += 0.002 * (t - t.mean()) / days       # slow trend
    f += rng.normal(0, noise, t.size)
    return t, f


def self_test():
    P, t0 = 3.12, 1000.0
    ref = {"P": P, "t_conj0": t0, "t_conj1": t0 + 0.5 * P}
    star = {"ref": ref, "window_d": 0.75, "fwhm_d": 0.09, "dt_max_d": 0.45, "step_d": 0.002}
    checks = {}
    for name, ex, off in (("s30min_off012", 1800.0, 0.12), ("s10min_off0", 600.0, 0.0),
                          ("s30min_offm030", 1800.0, -0.30)):
        t, f = synth(P, t0, 0.07, 0.09, ex, 20.0, 0.003, off, 7)
        lc = {"t": t, "f": f, "exptime": ex, "sector": 0, "author": "SYN"}
        r, _ = measure_lc(lc, star)
        good = (r["status"] == "OK" and abs(r["dt_best"] - off) <= 0.004
                and math.isfinite(r["dt_sigma"]) and r["dt_sigma"] < 0.01)
        checks[name] = {"ok": bool(good), "dt": r.get("dt_best"), "sigma": r.get("dt_sigma"),
                        "n_events": r["n_events"]}
    tpl = template(np.array([0.0]), 0.09, 120.0)[0]
    checks["template_peak"] = {"ok": bool(abs(tpl - 1.0) < 1e-12), "value": float(tpl)}
    ok = all(c["ok"] for c in checks.values())
    log("self-test", "PASS" if ok else "FAIL", dumps(checks))
    return ok, checks


# ---------------------------------------------------------------- data

def tess_products(tic, cache_dir, authors=AUTHORS, max_products=MAX_PRODUCTS):
    """Every (author, sector) light curve; SPOC only at ~2-min cadence."""
    import lightkurve as lk
    sr = None
    for a in range(3):
        try:
            sr = lk.search_lightcurve("TIC %d" % int(tic), mission="TESS")
            break
        except Exception as exc:
            log("search retry", tic, repr(exc)[:160])
            time.sleep(10 * (a + 1))
    if sr is None or len(sr) == 0:
        return []
    tab = sr.table
    pick = {}
    for i in range(len(sr)):
        author = str(tab["author"][i])
        if author not in authors:
            continue
        exptime = fnum(np.asarray(tab["exptime"])[i])
        if author == "SPOC" and not (100 <= exptime <= 200):
            continue
        if not math.isfinite(exptime) or exptime <= 0:
            exptime = 600.0 if author != "SPOC" else 120.0
        m = re.search(r"(\d+)", str(tab["mission"][i]))
        if not m:
            continue
        sec = int(m.group(1))
        key = (author, sec)
        if key not in pick or abs(exptime - 120.0) < abs(pick[key][1] - 120.0):
            pick[key] = (i, exptime)
    out = []
    for (author, sec) in sorted(pick, key=lambda k: (k[1], AUTHORS.index(k[0])))[:max_products]:
        i, exptime = pick[(author, sec)]
        for a in range(3):
            try:
                lc = sr[i].download(download_dir=cache_dir, quality_bitmask="default")
                lc = lc.remove_nans()
                t = np.asarray(lc.time.value, float)
                f = np.asarray(lc.flux.value, float)
                ok = np.isfinite(t) & np.isfinite(f) & (f > 0)
                if ok.sum() >= 100:
                    out.append({"sector": sec, "author": author, "exptime": exptime,
                                "t": t[ok], "f": f[ok] / np.median(f[ok])})
                    log("TIC", tic, "sector", sec, author, exptime, int(ok.sum()), "points")
                break
            except Exception as exc:
                log("download retry TIC", tic, "sector", sec, author, repr(exc)[:160])
                time.sleep(10 * (a + 1))
    return out


# ---------------------------------------------------------------- driver

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="targets.json")
    ap.add_argument("--data-dir", default="/data/timing")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--self-test-only", action="store_true")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    ok, checks = self_test()
    meta = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "self_test": "PASS" if ok else "FAIL", "self_test_checks": checks}
    if args.self_test_only:
        return 0 if ok else 3
    with open(args.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    summary = {"meta": meta, "stars": []}
    srows, erows, crows = [], [], []
    for star in cfg["stars"]:
        log("star", star["name"], "TIC", star["tic"])
        lcs = tess_products(star["tic"], os.path.join(args.data_dir, "lk"))
        st = {"name": star["name"], "role": star["role"], "tic": star["tic"],
              "ref": star["ref"], "products": []}
        for lc in lcs:
            r, res = measure_lc(lc, star)
            st["products"].append(r)
            log(star["name"], "sector", r["sector"], r["author"], r["status"],
                dumps({k: r.get(k) for k in ("n_events", "dt_best", "dt_sigma", "chi2_red",
                                              "dchi2_scaled_at_0", "alt_offset",
                                              "dchi2_scaled_at_alt", "rival")}))
            srows.append([star["name"], r["sector"], r["author"], r["exptime"], r["status"],
                          r["n_events"], r.get("dt_best"), r.get("dt_sigma"), r.get("chi2_red"),
                          r.get("dchi2_scaled_at_0"), r.get("alt_offset"),
                          r.get("dchi2_scaled_at_alt"),
                          (r.get("rival") or {}).get("dt"),
                          (r.get("rival") or {}).get("dchi2_scaled")])
            for e in r["events"]:
                erows.append([star["name"], r["sector"], r["author"], e["family"], e["n"],
                              e["tp"], e["n_points"], e["dt_best"], e["dt_sigma"], e["depth"],
                              e["dchi2_scaled_at_0"]])
            if res is not None:
                for g, c in zip(res["grid"], res["chi2"]):
                    crows.append([star["name"], r["sector"], r["author"], round(float(g), 4),
                                  float((c - res["chi2_min"]) / res["chi2_red"])])
        summary["stars"].append(st)
        with open(os.path.join(args.out_dir, "timing_summary.json"), "w", encoding="utf-8") as fh:
            fh.write(dumps(summary, indent=1))
    meta["complete"] = True
    meta["written"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def wcsv(name, head, rows):
        with open(os.path.join(args.out_dir, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(head)
            for row in rows:
                w.writerow(clean(row))
    wcsv("timing_sectors.csv", ["star", "sector", "author", "exptime_s", "status", "n_events",
                                "dt_best_d", "dt_sigma_d", "chi2_red", "dchi2_at_ref",
                                "alt_offset_d", "dchi2_at_alt", "rival_dt_d", "rival_dchi2"], srows)
    wcsv("timing_events.csv", ["star", "sector", "author", "family", "n", "t_pred_btjd",
                               "n_points", "dt_best_d", "dt_sigma_d", "depth",
                               "dchi2_at_ref"], erows)
    wcsv("timing_chi2_curves.csv", ["star", "sector", "author", "dt_d", "dchi2_scaled"], crows)
    with open(os.path.join(args.out_dir, "timing_summary.json"), "w", encoding="utf-8") as fh:
        fh.write(dumps(summary, indent=1))
    log("done", len(srows), "products")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
