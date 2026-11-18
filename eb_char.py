# SPDX-License-Identifier: Apache-2.0
"""Measure the TESS eclipses of Gaia-orbit eclipsing binaries, one target at a time.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Pre-registration: findings/2026-11-18-cd-48-897-prereg.md.

For each target in a JSON config (tic, ephemeris guess, expected duration, Gaia period):
1. every TESS light curve, one per sector (SPOC > TESS-SPOC > QLP);
2. a running-median detrend per segment that ignores the predicted eclipse windows;
3. a trapezoid + linear-baseline fit to every predicted primary eclipse with data;
4. a weighted linear ephemeris from the fitted mid-times (eb_ephem.fit_linear);
5. a box search for a secondary eclipse at all phases, and the depth at the Gaia-predicted
   other conjunction;
6. a census of every dip deeper than 5 sigma in 30-min bins;
7. plots, and for targets with "grade_vsx": the pre-registered criteria E1-E4.
"""
import argparse
import json
import math
import os
import time
import traceback

import numpy as np

import eb_ephem as ee

VERSION = "0.1.0"
AUTH_RANK = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def robust_sd(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 2:
        return float("nan")
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


# ---------------------------------------------------------------- data access
def _arr(x):
    x = getattr(x, "value", x)
    if hasattr(x, "unmasked"):
        d = np.array(x.unmasked, dtype=float)
        d[np.asarray(x.mask, dtype=bool)] = np.nan
        return d
    if np.ma.isMaskedArray(x):
        return np.ma.filled(x.astype(float), np.nan)
    return np.asarray(x, dtype=float)


def sector_of(tab, i):
    for key in ("sequence_number", "sector"):
        if key in tab.colnames:
            try:
                return int(tab[key][i])
            except Exception:
                pass
    digits = "".join(ch for ch in str(tab["mission"][i]) if ch.isdigit())
    return int(digits) if digits else None


def load_tess(tic, data_dir, max_sectors=80):
    """List of dicts {sector, author, t, f} (normalised flux), best author per sector."""
    import lightkurve as lk
    sr = None
    for attempt in range(3):
        try:
            sr = lk.search_lightcurve(f"TIC {tic}", mission="TESS")
            break
        except Exception as exc:
            log("search retry", attempt, exc)
            time.sleep(5 * (attempt + 1))
    if sr is None or len(sr) == 0:
        return []
    tab = sr.table
    best = {}
    for i in range(len(sr)):
        auth = str(tab["author"][i])
        if auth not in AUTH_RANK:
            continue
        sec = sector_of(tab, i)
        if sec is None:
            continue
        try:                                  # prefer 2-min over 20-s SPOC (size)
            exp = float(tab["exptime"][i]) if "exptime" in tab.colnames else 120.0
        except Exception:
            exp = 120.0
        rank = (AUTH_RANK[auth], 0 if abs(exp - 120.0) < 1 else 1)
        if sec not in best or rank < best[sec][0]:
            best[sec] = (rank, i, auth)
    out = []
    for sec in sorted(best)[:max_sectors]:
        _, i, auth = best[sec]
        try:
            lc = sr[i].download(download_dir=data_dir, quality_bitmask="default")
            t = _arr(lc.time.value)
            f = _arr(lc.flux)
            ok = np.isfinite(t) & np.isfinite(f)
            t, f = t[ok], f[ok]
            if t.size < 100:
                continue
            f = f / np.nanmedian(f)
            keep = f > 0.3                    # broken cadences; real eclipses here are < 30%
            sd = robust_sd(f[keep])
            keep &= f < 1 + 5 * sd            # upward outliers only
            out.append({"sector": sec, "author": auth, "t": t[keep], "f": f[keep],
                        "sd_ppm": round(sd * 1e6, 1),
                        "cadence_min": round(float(np.median(np.diff(t[keep]))) * 1440, 2)})
            log("sector", sec, auth, int(keep.sum()))
        except Exception as exc:
            log("download failed", sec, auth, exc)
    return out


# ---------------------------------------------------------------- light-curve tools
def near_any(t, centres, half):
    """Boolean mask: within `half` days of any centre."""
    t = np.asarray(t, float)
    m = np.zeros(t.size, bool)
    for c in centres:
        m |= np.abs(t - c) < half
    return m


def detrend_masked(t, f, masked, window=1.5, gap=0.5):
    """Divide each segment by a running median of the unmasked points."""
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    out = np.full_like(f, np.nan)
    if t.size == 0:
        return out
    step = window / 4.0
    cuts = np.where(np.diff(t) > gap)[0] + 1
    for seg in np.split(np.arange(t.size), cuts):
        ts, fs, ms = t[seg], f[seg], masked[seg]
        good = ~ms
        if good.sum() < 5:
            continue
        grid = np.arange(ts[0], ts[-1] + step, step)
        med = np.full(grid.size, np.nan)
        for k, g in enumerate(grid):
            m = good & (np.abs(ts - g) <= window / 2)
            if m.sum() >= 5:
                med[k] = np.median(fs[m])
        ok = np.isfinite(med)
        if ok.sum() == 0:
            continue
        out[seg] = fs / np.interp(ts, grid[ok], med[ok])
    return out


def shape_np(dt, t14, fin):
    half = 0.5 * t14
    tin = max(fin * half, 1e-9)
    return np.clip((half - np.abs(dt)) / tin, 0.0, 1.0)


def eclipse_model(p, x):
    tc, depth, t14, fin, c0, c1 = p
    return (c0 + c1 * (x - tc)) * (1.0 - depth * shape_np(x - tc, t14, fin))


def fit_eclipse(t, f, tc0, dur0, half_window):
    """Trapezoid fit near tc0 (raw normalised flux, local linear baseline).

    Returns None when there are too few points or the eclipse is not covered."""
    from scipy.optimize import least_squares
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    m = np.isfinite(t) & np.isfinite(f) & (np.abs(t - tc0) <= half_window)
    tt, ff = t[m], f[m]
    if tt.size < 20:
        return None
    cad = float(np.median(np.diff(tt)))
    # starting guesses: the predicted time and the minimum of a 3-point running mean
    sm = np.convolve(ff, np.ones(3) / 3.0, mode="same")
    tmin = float(tt[1 + int(np.argmin(sm[1:-1]))]) if tt.size > 3 else tc0
    d0 = max(float(np.median(ff) - np.min(sm[1:-1])), 1e-4)
    lo = [tc0 - 0.9 * half_window, 0.0, max(2 * cad, 0.005), 0.02, 0.5, -1.0]
    hi = [tc0 + 0.9 * half_window, 1.0, 1.5 * half_window, 1.0, 1.5, 1.0]

    def resid(p):
        return eclipse_model(p, tt) - ff

    best = None
    for tcs in (tc0, tmin):
        for t14s in (0.6 * dur0, dur0, 1.6 * dur0):
            for fin in (0.3, 0.95):
                p0 = [min(max(tcs, lo[0] + 1e-6), hi[0] - 1e-6), min(d0, 0.99),
                      min(max(t14s, lo[2] * 1.01), hi[2] * 0.99), fin, float(np.median(ff)), 0.0]
                try:
                    r = least_squares(resid, p0, bounds=(lo, hi),
                                      x_scale=[0.005, 0.01, 0.01, 0.1, 0.001, 0.001])
                except Exception as exc:
                    log("fit failed", exc)
                    continue
                if best is None or r.cost < best.cost:
                    best = r
    if best is None:
        return None
    p = best.x
    n = tt.size
    dof = max(n - 6, 1)
    s2 = 2.0 * best.cost / dof
    try:
        cov = np.linalg.pinv(best.jac.T @ best.jac) * s2
        err = np.sqrt(np.clip(np.diag(cov), 0, None))
    except Exception:
        err = np.full(6, np.nan)
    tc, depth, t14, fin = float(p[0]), float(p[1]), float(p[2]), float(p[3])
    in_ecl = np.abs(tt - tc) < 0.5 * t14
    expected = t14 / cad if cad > 0 else float("nan")
    # coverage on each side of mid-eclipse (ingress half and egress half)
    left = int(((tt > tc - 0.5 * t14) & (tt <= tc)).sum())
    right = int(((tt >= tc) & (tt < tc + 0.5 * t14)).sum())
    return {"tc": tc, "tc_err": float(err[0]), "depth": depth, "depth_err": float(err[1]),
            "t14_d": t14, "t14_err": float(err[2]), "fin": fin, "c0": float(p[4]), "c1": float(p[5]),
            "n_points": int(n), "n_in": int(in_ecl.sum()),
            "coverage": float(in_ecl.sum() / expected) if expected > 0 else float("nan"),
            "n_left": left, "n_right": right, "cadence_min": cad * 1440.0,
            "rms_ppm": float(math.sqrt(s2) * 1e6),
            "full": bool(left >= 3 and right >= 3 and in_ecl.sum() / max(expected, 1) > 0.5)}


def box_scan(ph, f, sd, P, widths_d, step=0.0025, lo=0.02, hi=0.98, min_n=10):
    """Box depths (1 - mean flux) at every phase centre in [lo, hi]; returns rows sorted by SNR."""
    rows = []
    for w in widths_d:
        hw = 0.5 * w / P
        for c in np.arange(lo, hi + 1e-9, step):
            d = np.abs(((ph - c) + 0.5) % 1.0 - 0.5)
            m = d < hw
            n = int(m.sum())
            if n < min_n:
                continue
            depth = float(1.0 - np.mean(f[m]))
            err = sd / math.sqrt(n)
            rows.append({"phase": round(float(c), 4), "width_d": w, "n": n, "depth": depth,
                         "err": err, "snr": depth / err if err > 0 else float("nan")})
    rows.sort(key=lambda r: -r["snr"] if np.isfinite(r["snr"]) else 0.0)
    return rows


def dip_census(t, f, sd_bin, bin_d=1.0 / 48, nsig=5.0, floor=0.005):
    """Contiguous 30-min bins below 1 - max(floor, nsig*sd_bin)."""
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    ok = np.isfinite(t) & np.isfinite(f)
    t, f = t[ok], f[ok]
    if t.size == 0:
        return []
    idx = np.floor((t - t[0]) / bin_d).astype(np.int64)
    uniq, inv, cnt = np.unique(idx, return_inverse=True, return_counts=True)
    bt = np.bincount(inv, weights=t) / cnt
    bf = np.bincount(inv, weights=f) / cnt
    thr = 1.0 - max(floor, nsig * sd_bin)
    low = bf < thr
    dips = []
    k = 0
    while k < bt.size:
        if not low[k]:
            k += 1
            continue
        j = k
        while j + 1 < bt.size and low[j + 1] and uniq[j + 1] - uniq[j] <= 1:
            j += 1
        seg = slice(k, j + 1)
        i_min = k + int(np.argmin(bf[seg]))
        dips.append({"t_min": float(bt[i_min]), "depth": float(1 - bf[i_min]),
                     "t_start": float(bt[k]), "t_end": float(bt[j]), "n_bins": int(j - k + 1)})
        k = j + 1
    return dips


# ---------------------------------------------------------------- one target
def run_target(cfg, data_dir, out_dir):
    tic = int(cfg["tic"])
    name = cfg.get("name", f"TIC {tic}")
    res = {"tic": tic, "name": name, "config": cfg, "version": VERSION}
    segs = load_tess(tic, data_dir)
    res["sectors"] = [{k: v for k, v in s.items() if k not in ("t", "f")} for s in segs]
    if not segs:
        res["status"] = "NO_TESS_DATA"
        return res
    t0, P = float(cfg["t0"]), float(cfg["period"])
    dur0 = float(cfg["dur_d"])
    mask_half = float(cfg.get("mask_half_d", max(1.5 * dur0, 0.2)))
    half_window = float(cfg.get("fit_half_window_d", max(3 * dur0, 0.4)))
    conj2 = cfg.get("conj2_phase")
    sec_mask_half = float(cfg.get("sec_mask_half_d", 0.0))
    T = np.concatenate([s["t"] for s in segs])
    F = np.concatenate([s["f"] for s in segs])
    S = np.concatenate([np.full(s["t"].size, s["sector"]) for s in segs])
    o = np.argsort(T)
    T, F, S = T[o], F[o], S[o]
    pred = ee.predicted_times(t0, P, float(T.min()) - half_window, float(T.max()) + half_window)
    centres = [tc for _, tc in pred]
    masked = near_any(T, centres, mask_half)
    if conj2 is not None and sec_mask_half > 0:
        sec_centres = [tc + float(conj2) * P for tc in centres] + [tc - (1 - float(conj2)) * P for tc in centres]
        masked |= near_any(T, sec_centres, sec_mask_half)
    D = detrend_masked(T, F, masked, window=float(cfg.get("detrend_window_d", 1.5)))
    # 1. primary eclipses
    ecl = []
    for n, tc in pred:
        near = np.abs(T - tc) <= half_window
        if near.sum() < 20:
            continue
        sec = int(np.median(S[near]))
        r = fit_eclipse(T, D, tc, dur0, half_window)
        if r is None:
            ecl.append({"n": n, "t_pred": tc, "sector": sec, "status": "too_few_points"})
            continue
        r.update({"n": n, "t_pred": tc, "sector": sec,
                  "author": next((s["author"] for s in segs if s["sector"] == sec), ""),
                  "o_minus_c_d": r["tc"] - tc})
        r["status"] = "fitted"
        ecl.append(r)
        log(name, "eclipse n", n, "tc %.4f depth %.4f t14 %.3f d full %s" % (r["tc"], r["depth"], r["t14_d"], r["full"]))
    res["eclipses"] = ecl
    good = [e for e in ecl if e.get("status") == "fitted" and e["full"]
            and e["depth"] > max(5 * e["depth_err"], 0.002) and np.isfinite(e["tc_err"]) and e["tc_err"] > 0]
    res["n_good_eclipses"] = len(good)
    eph = None
    if len(set(e["n"] for e in good)) >= 2:
        # floor timing errors at 1 minute (model error)
        errs = [max(e["tc_err"], 1.0 / 1440) for e in good]
        eph = ee.fit_linear([e["tc"] for e in good], errs, P, t_ref=t0)
        # the fit's n is relative to t0; report T0 at the first good eclipse too
        eph_out = {k: v for k, v in eph.items() if k != "cov"}
        eph_out["t0_btjd"] = eph["t0"]
        res["ephemeris"] = eph_out
        log(name, "ephemeris P %.6f +- %.6f T0 %.5f rms %.2f min" % (eph["p"], eph["sig_p"], eph["t0"], eph["rms"] * 1440))
    Pf = eph["p"] if eph else P
    T0f = eph["t0"] if eph else t0
    # 2. secondary eclipse search, outside the primary windows
    prim = near_any(T, [T0f + n * Pf for n, _ in pred], mask_half)
    sel = np.isfinite(D) & ~prim
    ph = (T[sel] - T0f) / Pf % 1.0
    sd = robust_sd(D[sel])
    widths = cfg.get("sec_widths_d", [0.1, 0.2, 0.35, 0.5])
    rows = box_scan(ph, D[sel], sd, Pf, widths)
    res["secondary_top"] = rows[:8]
    res["phase_coverage"] = float(np.unique(np.floor(ph * 200)).size / 200.0) if ph.size else 0.0
    if conj2 is not None:
        hw2 = float(cfg.get("conj2_halfwidth_phase", 0.03))
        at = [r for r in rows if abs(((r["phase"] - float(conj2)) + 0.5) % 1.0 - 0.5) <= hw2]
        at.sort(key=lambda r: -r["snr"] if np.isfinite(r["snr"]) else 0.0)
        res["secondary_at_conj2"] = at[:3]
        res["conj2_window_covered"] = bool(at)
    res["oot_sd_ppm"] = sd * 1e6
    # 3. dip census on the detrended light curve (primary windows included)
    sd_bin = robust_sd(D[np.isfinite(D)]) / math.sqrt(max(1.0, (1.0 / 48) / max(float(np.median(np.diff(T))), 1e-4)))
    dips = dip_census(T, D, sd_bin)
    for d in dips:
        d["phase"] = float((d["t_min"] - T0f) / Pf % 1.0)
        d["near_primary"] = bool(abs(((d["phase"]) + 0.5) % 1.0 - 0.5) * Pf < mask_half)
    res["dips"] = dips[:200]
    res["n_dips"] = len(dips)
    # 4. VSX criteria (pre-registered) if requested
    if cfg.get("grade_vsx") and eph is not None:
        res["vsx_criteria"] = ee.vsx_criteria([e["depth"] for e in good], eph["rms"], eph["p"],
                                              float(cfg["p_gaia"]), float(cfg["p_gaia_err"]),
                                              float(cfg.get("contam", 0.0)))
        log(name, "VSX criteria", res["vsx_criteria"])
    # 5. plots
    try:
        plot_target(res, T, D, S, T0f, Pf, ecl, out_dir, tic)
    except Exception as exc:
        log("plot failed", exc)
        res["plot_error"] = str(exc)[:300]
    res["status"] = "ok"
    return res


def plot_target(res, T, D, S, T0f, Pf, ecl, out_dir, tic):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fitted = [e for e in ecl if e.get("status") == "fitted"]
    if fitted:
        k = min(len(fitted), 12)
        ncol = 3
        nrow = int(math.ceil(k / ncol))
        fig, axs = plt.subplots(nrow, ncol, figsize=(12, 3.2 * nrow), squeeze=False)
        for ax, e in zip(axs.flat, fitted[:k]):
            hw = 3 * e["t14_d"] + 0.1
            m = np.abs(T - e["tc"]) < hw
            ax.plot((T[m] - e["tc"]) * 24, D[m], ".", ms=2, color="0.4")
            x = np.linspace(e["tc"] - hw, e["tc"] + hw, 600)
            p = [e["tc"], e["depth"], e["t14_d"], e["fin"], e["c0"], e["c1"]]
            ax.plot((x - e["tc"]) * 24, eclipse_model(p, x), "r-", lw=1)
            ax.set_title("n=%d S%d %s tc=%.4f d=%.3f" % (e["n"], e["sector"], e.get("author", ""), e["tc"], e["depth"]), fontsize=8)
            ax.set_xlabel("hours from mid-eclipse", fontsize=8)
        for ax in list(axs.flat)[k:]:
            ax.axis("off")
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, f"eb_char_{tic}_eclipses.png"), dpi=110)
        plt.close(fig)
    fig, axs = plt.subplots(2, 1, figsize=(10, 8))
    ok = np.isfinite(D)
    ph = ((T[ok] - T0f) / Pf + 0.25) % 1.0 - 0.25
    axs[0].plot(ph, D[ok], ",", color="0.3")
    axs[0].set_title(f"TIC {tic} folded at P = {Pf:.6f} d (phase -0.25..0.75)")
    axs[0].set_ylim(np.nanpercentile(D[ok], 0.05) - 0.01, np.nanpercentile(D[ok], 99.9) + 0.005)
    sel = ok & (np.abs(((T - T0f) / Pf + 0.5) % 1.0 - 0.5) * Pf > 0.5)
    php = ((T[sel] - T0f) / Pf) % 1.0
    axs[1].plot(php, D[sel], ",", color="0.3")
    bins = np.linspace(0, 1, 401)
    idx = np.digitize(php, bins)
    bm = [np.nanmedian(D[sel][idx == i]) if (idx == i).sum() >= 5 else np.nan for i in range(1, len(bins))]
    axs[1].plot(0.5 * (bins[1:] + bins[:-1]), bm, "r-", lw=1)
    sdv = robust_sd(D[sel])
    axs[1].set_ylim(1 - 12 * sdv, 1 + 6 * sdv)
    conj2 = res["config"].get("conj2_phase")
    if conj2 is not None:
        axs[1].axvline(float(conj2), color="b", lw=0.8, ls="--")
    axs[1].set_title("outside primary eclipse (blue: Gaia-predicted other conjunction)")
    axs[1].set_xlabel("phase")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, f"eb_char_{tic}_fold.png"), dpi=110)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    os.makedirs(a.data_dir, exist_ok=True)
    with open(a.config) as fh:
        targets = json.load(fh)["targets"]
    summary = {"version": VERSION, "targets": []}
    for cfg in targets:
        log("target", cfg.get("name"), cfg.get("tic"))
        try:
            res = run_target(cfg, a.data_dir, a.out_dir)
        except Exception as exc:
            res = {"tic": cfg.get("tic"), "name": cfg.get("name"), "status": "error",
                   "error": f"{exc}", "trace": traceback.format_exc()[-2000:]}
            log("target failed", cfg.get("tic"), exc)
        with open(os.path.join(a.out_dir, f"eb_char_{cfg.get('tic')}.json"), "w") as fh:
            json.dump(res, fh, indent=1, default=float)
        brief = {k: res.get(k) for k in ("tic", "name", "status", "n_good_eclipses", "ephemeris",
                                          "vsx_criteria", "secondary_at_conj2", "phase_coverage")}
        if brief.get("ephemeris"):
            brief["ephemeris"] = {k: brief["ephemeris"][k] for k in ("t0", "p", "sig_t0", "sig_p", "rms", "chi2", "n")}
        summary["targets"].append(brief)
    with open(os.path.join(a.out_dir, "eb_char_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=float)
    print(json.dumps(summary, default=float)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
