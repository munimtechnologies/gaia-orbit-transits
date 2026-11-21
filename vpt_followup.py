# SPDX-License-Identifier: Apache-2.0
"""vpt_followup 0.1.0: all-sector, period-free TESS follow-up of Gaia transit candidates.

By MV2 of Munim, Inc.; made with AI agents working in his name (not yet checked by a human
expert). Code Apache-2.0. Repository: munimtechnologies/gaia-orbit-transits.
Pre-registration: findings/2026-11-21-vpt-followup-prereg.md.

Why: in the Gaia DR3 rehearsal of step g, Gaia's published transit period matched the known
period for only 15 of 176 known systems, so a TESS "hit" at Gaia's period does not prove the
period. This module looks at every TESS sector of a target without assuming Gaia's period:

 1. every TESS sector (SPOC 120 s > TESS-SPOC > QLP) via sb1_transit.light_curves;
 2. each sector detrended with sb1_transit.detrend (30-min bins, running median of at least
    0.75 d so transits up to ~4 h keep their depth);
 3. a period-free box search (astropy BoxLeastSquares, 0.3-15 d) on each sector alone;
 4. on all sectors together, fine scans (+-1%) around Gaia's P, 2P and P/2 and around every
    sector peak with depth S/N >= 7; the strongest peak is the TESS period;
 5. at that period: depth, odd/even depths, the depth half a period later (secondary), the
    depth at half the period, per-sector depths, companion radius, a folded plot.

Labels (fixed in the pre-registration): NOT_DETECTED (combined depth S/N < 7), EB_LIKE (any of
ODD_EVEN, SECONDARY, STELLAR_SIZE), SURVIVES (TESS period within 1% of Gaia's), or
SURVIVES_OTHER_P. Controls are known planets whose answer is published; CONTROLS_PASS needs
every control's TESS period within 0.1% of the known period.

Top level is stdlib only; numpy, astropy, lightkurve and matplotlib are imported lazily.
"""
import argparse
import csv
import json
import math
import os
import shutil
import sys
import tempfile
import time
import traceback

VERSION = "0.1.0"

PMIN, PMAX = 0.3, 15.0
N_SECTOR_GRID = 30000
DURATIONS_H = (1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0)
DETREND_MIN_D = 0.25          # passed to sb1_transit.detrend as D -> window max(3 D, 0.5) = 0.75 d
SNR_DETECT = 7.0
PERIOD_TOL = 0.01
CONTROL_TOL = 0.001
FACTORS = (1.0, 0.5, 2.0, 1.0 / 3.0, 3.0)
FINE_HALF_WIDTH = 0.01
MAX_FINE = 200001
MAX_CENTERS = 8
OE_Z = 3.0
SEC_Z = 3.0
SEC_RATIO = 0.10
DEPTH_P_MIN = 0.001
R2_STELLAR_RJ = 2.0
RJUP_PER_RSUN = 9.731
GAIA_TO_BTJD = 2455197.5 - 2457000.0

RESULT_KEYS = [
    "name", "role", "source_id", "tic", "label", "flags", "notes", "n_sectors_available",
    "n_sectors_used", "sectors", "P_gaia", "P_tess", "period_factor", "snr", "depth",
    "depth_err", "duration_h", "t0_btjd", "depth_gaia", "depth_ratio_tess_gaia", "depth_odd",
    "depth_odd_err", "depth_even", "depth_even_err", "oddeven_z", "sec_depth", "sec_err",
    "half_depth", "half_err", "depth_chi2", "depth_dof", "depth_p", "r1", "r2_rj",
    "gaia_offset_d", "n_sector_detect", "n_sector_agree", "expect_period", "control_ok",
    "error"]
SECTOR_KEYS = ["source_id", "name", "sector", "author", "n_bins", "sd", "bls_period",
               "bls_snr", "bls_depth", "n_in_final", "depth_final", "depth_final_err"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ================================================================ pure helpers (stdlib)
def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def fval(row, key, default=float("nan")):
    try:
        v = row.get(key, default)
        if v is None or (isinstance(v, str) and v.strip() in ("", "null", "NaN", "nan", "--")):
            return default
        v = float(v)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def mmag_to_frac(mmag):
    if not finite(mmag):
        return float("nan")
    return 1.0 - 10.0 ** (-0.4 * mmag / 1000.0)


def period_factor(p, p_ref, tol=PERIOD_TOL, factors=FACTORS):
    """Factor f with |p / (f p_ref) - 1| <= tol (that is, p = f x p_ref), else None."""
    if not (finite(p) and finite(p_ref)) or p <= 0 or p_ref <= 0:
        return None
    for f in factors:
        if abs(p / (f * p_ref) - 1.0) <= tol:
            return f
    return None


def chi2_sf(x, k):
    """Survival function of the chi-square distribution (regularised upper gamma Q(k/2, x/2))."""
    if not (finite(x) and k > 0):
        return float("nan")
    if x <= 0:
        return 1.0
    a, xx = k / 2.0, x / 2.0
    gln = math.lgamma(a)
    if xx < a + 1.0:
        ap, s = a, 1.0 / a
        term = s
        for _ in range(1000):
            ap += 1.0
            term *= xx / ap
            s += term
            if abs(term) < abs(s) * 1e-14:
                break
        p = s * math.exp(-xx + a * math.log(xx) - gln)
        return min(1.0, max(0.0, 1.0 - p))
    tiny = 1e-300
    b = xx + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-14:
            break
    return min(1.0, max(0.0, math.exp(-xx + a * math.log(xx) - gln) * h))


def depth_consistency(depths, errs):
    """Chi-square of per-sector depths about their weighted mean: (chi2, dof, p)."""
    pairs = [(d, e) for d, e in zip(depths, errs) if finite(d) and finite(e) and e > 0]
    if len(pairs) < 2:
        return float("nan"), 0, float("nan")
    w = [1.0 / (e * e) for _, e in pairs]
    mean = sum(wi * d for wi, (d, _) in zip(w, pairs)) / sum(w)
    chi2 = sum(((d - mean) / e) ** 2 for d, e in pairs)
    dof = len(pairs) - 1
    return chi2, dof, chi2_sf(chi2, dof)


def z_diff(a, ea, b, eb):
    if not all(finite(v) for v in (a, ea, b, eb)) or ea <= 0 or eb <= 0:
        return float("nan")
    return abs(a - b) / math.sqrt(ea * ea + eb * eb)


def vet_label(res):
    """(flags, notes, label) from a result dict. Only ODD_EVEN, SECONDARY and STELLAR_SIZE
    decide the label; DEPTH_VARIES is a note (QLP and SPOC treat blending differently)."""
    flags, notes = [], []
    if finite(res.get("oddeven_z")) and res["oddeven_z"] >= OE_Z:
        flags.append("ODD_EVEN")
    sec, se, dep = res.get("sec_depth"), res.get("sec_err"), res.get("depth")
    if (finite(sec) and finite(se) and se > 0 and finite(dep) and sec / se >= SEC_Z
            and sec >= SEC_RATIO * dep):
        flags.append("SECONDARY")
    if finite(res.get("r2_rj")) and res["r2_rj"] > R2_STELLAR_RJ:
        flags.append("STELLAR_SIZE")
    if finite(res.get("depth_p")) and res["depth_p"] < DEPTH_P_MIN:
        notes.append("DEPTH_VARIES")
    snr = res.get("snr")
    if not (finite(snr) and snr >= SNR_DETECT):
        label = "NOT_DETECTED"
    elif flags:
        label = "EB_LIKE"
    elif res.get("period_factor") == 1.0:
        label = "SURVIVES"
    else:
        label = "SURVIVES_OTHER_P"
    return flags, notes, label


def control_ok(p_tess, expect, snr):
    return bool(finite(snr) and snr >= SNR_DETECT and
                period_factor(p_tess, expect, tol=CONTROL_TOL, factors=(1.0,)) == 1.0)


def grade(results):
    ctrl = [r for r in results if r.get("role") == "control"]
    cand = [r for r in results if r.get("role") == "candidate"]
    if not ctrl:
        clab = "NO_CONTROLS"
    else:
        clab = "CONTROLS_PASS" if all(bool(r.get("control_ok")) for r in ctrl) else "CONTROLS_FAIL"
    return {"controls_label": clab,
            "controls": {r.get("name"): {"P_tess": r.get("P_tess"),
                                         "expect": r.get("expect_period"),
                                         "ok": r.get("control_ok")} for r in ctrl},
            "candidates": {r.get("name"): {"label": r.get("label"), "flags": r.get("flags"),
                                           "P_tess": r.get("P_tess"),
                                           "period_factor": r.get("period_factor"),
                                           "r2_rj": r.get("r2_rj"),
                                           "valid": clab == "CONTROLS_PASS"} for r in cand}}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, keys):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in keys})


def clean_json(o):
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): clean_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_json(v) for v in o]
    return o


# ================================================================ numpy / astropy core
def bls_best(t, y, dy, periods, durations):
    import numpy as np
    from astropy.timeseries import BoxLeastSquares
    bls = BoxLeastSquares(t, y, dy)
    res = bls.power(periods, durations, objective="snr")
    pw = np.asarray(res.power, float).copy()
    pw[~np.isfinite(pw)] = -np.inf
    i = int(np.argmax(pw))
    return bls, res, i


def analyse_resid(sect, P_g, t0_g, r1):
    """Core analysis on detrended sectors [(sector, author, bt, r, sd)].
    Returns (result dict, sector rows, fold tuple or None)."""
    import numpy as np
    durs_all = np.array(DURATIONS_H, float) / 24.0
    srows = []
    for (sec, au, bt, r, sd) in sect:
        row = {"sector": sec, "author": au, "n_bins": int(bt.size), "sd": sd,
               "bls_period": float("nan"), "bls_snr": float("nan"), "bls_depth": float("nan")}
        span = float(bt.max() - bt.min())
        pmax = min(PMAX, 0.5 * span)
        if pmax > 1.5 * PMIN:
            periods = np.exp(np.linspace(math.log(PMIN), math.log(pmax), N_SECTOR_GRID))
            _, res, i = bls_best(bt, r, np.full(bt.size, sd), periods, durs_all)
            row.update({"bls_period": float(res.period[i]), "bls_snr": float(res.power[i]),
                        "bls_depth": float(res.depth[i])})
        srows.append(row)
    t = np.concatenate([s[2] for s in sect])
    y = np.concatenate([s[3] for s in sect])
    dy = np.concatenate([np.full(s[2].size, s[4]) for s in sect])
    o = np.argsort(t)
    t, y, dy = t[o], y[o], dy[o]
    span = float(t.max() - t.min())
    centers = []

    def add(c):
        if finite(c) and PMIN <= c <= PMAX and all(abs(c / x - 1.0) > 0.005 for x in centers):
            centers.append(float(c))
    for c in (P_g, 2.0 * P_g, 0.5 * P_g):
        add(c)
    for row in sorted(srows, key=lambda q: -(q["bls_snr"] if finite(q["bls_snr"]) else -1e9)):
        if len(centers) >= MAX_CENTERS:
            break
        if finite(row["bls_snr"]) and row["bls_snr"] >= SNR_DETECT:
            add(row["bls_period"])
    best, scans = None, []
    for c in centers:
        lo, hi = max(PMIN, c * (1.0 - FINE_HALF_WIDTH)), min(PMAX, c * (1.0 + FINE_HALF_WIDTH))
        durs = durs_all[durs_all < 0.5 * lo]
        if durs.size == 0:
            continue
        dP = c * float(durs.min()) / (4.0 * max(span, 1.0))
        n = int(min(MAX_FINE, max(1001, 2.0 * FINE_HALF_WIDTH * c / dP + 1)))
        periods = np.linspace(lo, hi, n)
        bls, res, i = bls_best(t, y, dy, periods, durs)
        s = {"center": c, "period": float(res.period[i]), "snr": float(res.power[i]),
             "depth": float(res.depth[i]), "duration": float(res.duration[i]),
             "t0": float(res.transit_time[i]), "n_periods": n}
        scans.append(s)
        if best is None or s["snr"] > best[0]["snr"]:
            best = (s, bls)
    out = {"scans": scans, "P_gaia": P_g}
    if best is None:
        out.update({"snr": float("nan"), "label": "NOT_DETECTED"})
        return out, srows, None
    s, bls = best
    P, dur, t0 = s["period"], s["duration"], s["t0"]
    stats = bls.compute_stats(P, dur, t0)

    def pair(k):
        try:
            v = stats[k]
            return float(v[0]), float(v[1])
        except Exception:
            return float("nan"), float("nan")
    d, de = pair("depth")
    do, doe = pair("depth_odd")
    dv, dve = pair("depth_even")
    sc, sce = pair("depth_phased")
    hf, hfe = pair("depth_half")
    depths, errs = [], []
    for row, (_, _, bt, r, sd) in zip(srows, sect):
        ph = ((bt - t0) / P + 0.5) % 1.0 - 0.5
        inb = np.abs(ph * P) < dur / 2.0
        n_in = int(inb.sum())
        row["n_in_final"] = n_in
        row["depth_final"], row["depth_final_err"] = float("nan"), float("nan")
        if n_in >= 3:
            row["depth_final"] = -float(np.mean(r[inb]))
            row["depth_final_err"] = sd / math.sqrt(n_in)
            depths.append(row["depth_final"])
            errs.append(row["depth_final_err"])
    chi2, dof, pchi = depth_consistency(depths, errs)
    f = period_factor(P, P_g)
    off = float("nan")
    if f == 1.0 and finite(t0_g):
        k = round((t0 - t0_g) / P_g)
        off = t0 - t0_g - k * P_g
    n_det = sum(1 for q in srows if finite(q["bls_snr"]) and q["bls_snr"] >= SNR_DETECT)
    n_agree = sum(1 for q in srows if finite(q["bls_snr"]) and q["bls_snr"] >= SNR_DETECT
                  and period_factor(q["bls_period"], P, factors=(1.0,)) == 1.0)
    r2 = math.sqrt(d) * r1 * RJUP_PER_RSUN if (finite(d) and d > 0 and finite(r1)) else float("nan")
    out.update({"P_tess": P, "period_factor": f, "snr": s["snr"], "depth": d, "depth_err": de,
                "duration_h": dur * 24.0, "t0_btjd": t0, "depth_odd": do, "depth_odd_err": doe,
                "depth_even": dv, "depth_even_err": dve, "oddeven_z": z_diff(do, doe, dv, dve),
                "sec_depth": sc, "sec_err": sce, "half_depth": hf, "half_err": hfe,
                "depth_chi2": chi2, "depth_dof": dof, "depth_p": pchi, "r1": r1, "r2_rj": r2,
                "gaia_offset_d": off, "n_sector_detect": n_det, "n_sector_agree": n_agree})
    flags, notes, label = vet_label(out)
    out.update({"flags": ";".join(flags), "notes": ";".join(notes), "label": label})
    return out, srows, (t, y, P, t0, dur)


def detrend_sectors(secs):
    import numpy as np
    import sb1_transit as st
    import dipsearch as ds
    out = []
    for (sec, au, t, f) in secs:
        bt, r, _ = st.detrend(t, f, DETREND_MIN_D)
        if bt.size < 50:
            continue
        sd = float(ds.robust_sd(r))
        if not (np.isfinite(sd) and sd > 0):
            continue
        out.append((sec, au, bt, r, sd))
    return out


def plot_fold(plt, path, title, fold):
    import numpy as np
    t, y, P, t0, dur = fold
    x = (((t - t0) / P + 0.5) % 1.0 - 0.5) * P * 24.0
    win = max(4.0 * dur * 24.0, 6.0)
    m = np.abs(x) < win
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(x[m], 100.0 * y[m], ".", ms=2, alpha=0.35, color="0.55")
    edges = np.linspace(-win, win, 61)
    idx = np.digitize(x[m], edges)
    xb, yb = [], []
    for k in range(1, edges.size):
        sel = idx == k
        if sel.sum() >= 3:
            xb.append(0.5 * (edges[k - 1] + edges[k]))
            yb.append(100.0 * float(np.median(y[m][sel])))
    ax.plot(xb, yb, "o-", ms=3, color="C3")
    ax.set_xlabel("hours from mid-transit (P = %.5f d)" % P)
    ax.set_ylabel("flux change (%)")
    ax.set_title(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def analyse_star(row, args):
    import sb1_transit as st
    import gaia_vpt_tess as gv
    rec = {k: "" for k in RESULT_KEYS}
    rec.update({"name": row.get("name", ""), "role": row.get("role", ""),
                "source_id": str(row.get("source_id", "")),
                "expect_period": fval(row, "expect_period")})
    P_g = fval(row, "transit_period")
    t0_g = fval(row, "transit_reference_time") + GAIA_TO_BTJD
    dep_g = mmag_to_frac(fval(row, "transit_depth"))
    r1, _ = gv.stellar_radius(row)
    rec.update({"P_gaia": P_g, "depth_gaia": dep_g, "r1": r1})
    tmp = tempfile.mkdtemp(prefix="vfu_", dir=args.tmp_dir)
    try:
        tic, secs, nav = st.light_curves(row, tmp, args.max_sectors)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    rec.update({"tic": tic, "n_sectors_available": nav, "n_sectors_used": len(secs),
                "sectors": ";".join("%s:%s" % (s[0], s[1]) for s in secs)})
    if not secs:
        rec["label"] = "NO_TESS"
        return rec, [], [], None
    sect = detrend_sectors(secs)
    if not sect:
        rec["label"] = "NO_TESS"
        return rec, [], [], None
    res, srows, fold = analyse_resid(sect, P_g, t0_g, r1)
    scans = res.pop("scans", [])
    rec.update(res)
    if finite(rec.get("depth")) and finite(dep_g) and dep_g > 0:
        rec["depth_ratio_tess_gaia"] = rec["depth"] / dep_g
    if rec["role"] == "control":
        rec["control_ok"] = control_ok(rec.get("P_tess"), rec["expect_period"], rec.get("snr"))
    for q in srows:
        q["source_id"], q["name"] = rec["source_id"], rec["name"]
    for q in scans:
        q["source_id"], q["name"] = rec["source_id"], rec["name"]
    return rec, srows, scans, fold


def self_test():
    """Synthetic checks of the core (numpy + astropy): a planet and an eclipsing binary."""
    import numpy as np
    rng = np.random.default_rng(7)
    ok = True

    def sectors(model):
        out = []
        for k, start in enumerate((0.0, 400.0, 800.0)):
            bt = np.arange(start, start + 27.0, 1.0 / 48.0)
            r = rng.normal(0.0, 1e-3, bt.size) + model(bt)
            out.append((k + 1, "SYN", bt, r, 1e-3))
        return out

    def box(bt, P, t0, dur, depth):
        ph = ((bt - t0) / P + 0.5) % 1.0 - 0.5
        return np.where(np.abs(ph * P) < dur / 2.0, -depth, 0.0)

    res, srows, _ = analyse_resid(sectors(lambda bt: box(bt, 2.5, 1.3, 0.1, 0.01)),
                                  2.5 * 1.002, 1.3, 1.0)
    log("self-test planet:", res.get("label"), res.get("P_tess"), res.get("flags"),
        "oe z %.2f" % res.get("oddeven_z", float("nan")))
    ok &= res.get("label") == "SURVIVES" and abs(res["P_tess"] / 2.5 - 1.0) < 0.001
    eb = lambda bt: box(bt, 5.0, 1.3, 0.1, 0.01) + box(bt, 5.0, 3.8, 0.1, 0.004)
    res, _, _ = analyse_resid(sectors(eb), 2.5, 1.3, 1.0)
    log("self-test EB:", res.get("label"), res.get("P_tess"), res.get("flags"))
    ok &= res.get("label") == "EB_LIKE"
    res, _, _ = analyse_resid(sectors(lambda bt: 0.0 * bt), 2.5, 1.3, 1.0)
    log("self-test flat:", res.get("label"), "snr %.2f" % res.get("snr", float("nan")))
    ok &= res.get("label") == "NOT_DETECTED"
    log("self-test", "PASS" if ok else "FAIL")
    return bool(ok)


def run(args):
    os.makedirs(args.out_dir, exist_ok=True)
    if args.tmp_dir:
        os.makedirs(args.tmp_dir, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = read_csv(args.targets)
    results, srows_all, scans_all = [], [], []
    for row in rows:
        log("target", row.get("role"), row.get("name"), row.get("source_id"))
        try:
            rec, srows, scans, fold = analyse_star(row, args)
        except Exception as exc:
            traceback.print_exc()
            rec = {"name": row.get("name", ""), "role": row.get("role", ""),
                   "source_id": str(row.get("source_id", "")), "label": "ERROR",
                   "error": repr(exc)[:300]}
            srows, scans, fold = [], [], None
        log("->", rec.get("name"), rec.get("label"), "P_tess", rec.get("P_tess"),
            "snr", rec.get("snr"), "flags", rec.get("flags"))
        results.append(rec)
        srows_all += srows
        scans_all += scans
        if fold is not None:
            try:
                plot_fold(plt, os.path.join(args.out_dir, "fu_fold_%s.png" % rec["source_id"]),
                          "%s (Gaia DR3 %s): %s" % (rec["name"], rec["source_id"],
                                                    rec.get("label")), fold)
            except Exception as exc:
                log("plot failed", exc)
        summ = {"version": VERSION, "n_targets": len(rows), "n_done": len(results),
                "grade": grade(results), "targets": results}
        with open(os.path.join(args.out_dir, "fu_summary.json"), "w", encoding="utf-8") as fh:
            json.dump(clean_json(summ), fh, indent=1)
        write_csv(os.path.join(args.out_dir, "fu_targets_out.csv"), results, RESULT_KEYS)
        write_csv(os.path.join(args.out_dir, "fu_sectors.csv"), srows_all, SECTOR_KEYS)
        write_csv(os.path.join(args.out_dir, "fu_scans.csv"), scans_all,
                  ["source_id", "name", "center", "period", "snr", "depth", "duration", "t0",
                   "n_periods"])
    print(json.dumps(clean_json(grade(results))))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--targets", default="fu_targets.csv")
    p.add_argument("--out-dir", default="out")
    p.add_argument("--tmp-dir", default=None)
    p.add_argument("--max-sectors", type=int, default=99)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return 0 if self_test() else 3
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
