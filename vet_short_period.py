# SPDX-License-Identifier: Apache-2.0
"""Vet a short-period Gaia SB1 / transit candidate in TESS light curves.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.

Built for Gaia DR3 1622997463177004928 = TIC 207399049: a Gaia photometric transit
candidate (P_phot = 0.8514 d, 12.8 mmag) whose Gaia RVS orbit is an SB1 with
P = 0.46023 d and K = 19.7 +- 1.3 km/s, i.e. m2 sin i ~ 0.071 M_sun at the
brown-dwarf / star boundary. Rules and predictions are fixed in
findings/2026-11-17-tic207399049-prereg.md before any TESS data are read.

Steps: every TESS light curve (SPOC > TESS-SPOC > QLP, one per sector) -> per-segment
running-median detrend (2 d window, many cycles of the candidate periods) -> 10-min bins
-> Lomb-Scargle and BLS period search -> for each candidate period (BLS best, SB1, 2x SB1,
Gaia photometric) a narrow BLS refinement -> at the strongest: a harmonic fit outside
eclipse (ellipsoidal, reflection, beaming), primary / secondary / odd / even depths
against that model -> companion radius and mass -> verdict() with fixed rules.
"""
import argparse
import json
import math
import os
import sys
import time
import traceback

import numpy as np

import transit_rv_screen as trs

VERSION = "0.1.0"
AUTH_RANK = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}
RSUN_PER_AU = 215.032


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- pure helpers
def robust_sd(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 2:
        return float("nan")
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def phase(t, P, t0):
    """Orbital phase in [-0.5, 0.5), 0 at t0."""
    return ((np.asarray(t, float) - t0) / P + 0.5) % 1.0 - 0.5


def semi_major_axis_rsun(p_days, mtot):
    return RSUN_PER_AU * (mtot * (p_days / 365.25) ** 2) ** (1.0 / 3.0)


def ellipsoidal_alpha(u=0.5, tau=0.4):
    """Morris (1985) coefficient: 0.15 (15 + u)(1 + tau) / (3 - u)."""
    return 0.15 * (15.0 + u) * (1.0 + tau) / (3.0 - u)


def expected_ellipsoidal(m2, m1, r1, a, sini=1.0, u=0.5, tau=0.4):
    """Semi-amplitude (fraction) of the cos(4 pi phase) ellipsoidal term."""
    return ellipsoidal_alpha(u, tau) * (m2 / m1) * (r1 / a) ** 3 * sini ** 2


def central_duration(p_days, a_over_r1, k=0.0, b=0.0):
    """Total transit duration (d) of a circular orbit."""
    x = math.sqrt(max((1 + k) ** 2 - b ** 2, 0.0)) / a_over_r1
    return p_days / math.pi * math.asin(min(x, 1.0))


def running_median_detrend(t, f, window=2.0, gap=0.5, step=None):
    """Divide each segment (split at gaps > `gap` d) by a running median of width
    `window` d, evaluated every window/4 and interpolated."""
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    out = np.full_like(f, np.nan)
    if t.size == 0:
        return out
    step = step or window / 4.0
    cuts = np.where(np.diff(t) > gap)[0] + 1
    for seg in np.split(np.arange(t.size), cuts):
        ts, fs = t[seg], f[seg]
        if ts.size < 5:
            continue
        grid = np.arange(ts[0], ts[-1] + step, step)
        med = []
        for g in grid:
            m = np.abs(ts - g) <= window / 2
            med.append(np.median(fs[m]) if m.sum() >= 5 else np.nan)
        med = np.array(med)
        ok = np.isfinite(med)
        if ok.sum() == 0:
            continue
        trend = np.interp(ts, grid[ok], med[ok])
        out[seg] = fs / trend
    return out


def bin_lc(t, f, width):
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    ok = np.isfinite(t) & np.isfinite(f)
    t, f = t[ok], f[ok]
    if t.size == 0:
        return t, f, np.zeros(0, int)
    idx = np.floor((t - t[0]) / width).astype(np.int64)
    uniq, inv, cnt = np.unique(idx, return_inverse=True, return_counts=True)
    bt = np.bincount(inv, weights=t) / cnt
    bf = np.bincount(inv, weights=f) / cnt
    return bt, bf, cnt


def harmonic_design(ph):
    w = 2 * np.pi * ph
    return np.vstack([np.ones_like(ph), np.cos(w), np.sin(w), np.cos(2 * w), np.sin(2 * w)]).T


def measure_eclipses(t, f, P, t0, dur):
    """Harmonic model outside both eclipses, then eclipse depths against that model.

    Returns a dict: a_ell (= -cos(4 pi phase) coefficient; ellipsoidal, minima at
    phases 0 and 0.5), a_ref (= -cos(2 pi phase) coefficient; reflection, max at 0.5),
    a_beam (sin(2 pi phase) coefficient), depth_p / err_p (primary), depth_s / err_s
    (secondary, phase 0.5), depth_odd / depth_even and errors, oot_sd, n_in_p, n_in_s."""
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    ok = np.isfinite(t) & np.isfinite(f)
    t, f = t[ok], f[ok]
    ph = phase(t, P, t0)
    half = 0.5 * dur / P
    in_p = np.abs(ph) < half
    ph_s = (ph + 1.0) % 1.0 - 0.5          # 0 at secondary
    in_s = np.abs(ph_s) < half
    oot = (np.abs(ph) > 1.5 * half) & (np.abs(ph_s) > 1.5 * half)
    res = {"P": P, "t0": t0, "dur": dur, "n_oot": int(oot.sum()),
           "n_in_p": int(in_p.sum()), "n_in_s": int(in_s.sum())}
    if oot.sum() < 20:
        return res
    X = harmonic_design(ph)
    coef, *_ = np.linalg.lstsq(X[oot], f[oot], rcond=None)
    model = X @ coef
    r = f - model
    sd = robust_sd(r[oot])
    res.update({"c0": float(coef[0]), "a_ref": float(-coef[1]), "a_beam": float(coef[2]),
                "a_ell": float(-coef[3]), "a_sin2": float(coef[4]), "oot_sd": sd})
    # harmonic coefficient covariance (white noise approximation)
    try:
        cov = np.linalg.inv(X[oot].T @ X[oot]) * sd ** 2
        res["err_a_ell"] = float(math.sqrt(cov[3, 3]))
        res["err_a_ref"] = float(math.sqrt(cov[1, 1]))
    except np.linalg.LinAlgError:
        cov = None

    def depth(m):
        n = int(m.sum())
        if n < 3:
            return None
        var = sd ** 2 / n
        if cov is not None:                   # the model is extrapolated into the eclipse
            xbar = X[m].mean(axis=0)
            var += float(xbar @ cov @ xbar)
        return float(-np.mean(r[m])), float(math.sqrt(var))

    epoch = np.round((t - t0) / P).astype(np.int64)
    for name, m in (("p", in_p), ("s", in_s), ("odd", in_p & (np.abs(epoch) % 2 == 1)),
                    ("even", in_p & (np.abs(epoch) % 2 == 0))):
        d = depth(m)
        if d is not None:
            res[f"depth_{name}"], res[f"err_{name}"] = d
    return res


def companion_mass_range(k, k_err, p, m1, e=0.0):
    return (trs.min_companion_mass(max(k - 2 * k_err, 0.0), p, m1, e),
            trs.min_companion_mass(k, p, m1, e),
            trs.min_companion_mass(k + 2 * k_err, p, m1, e))


def verdict(v):
    """Fixed rules (pre-registered). v keys: snr, depth_p, err_p, depth_s, err_s,
    depth_odd, err_odd, depth_even, err_even, match_rv ('1:1' etc. or ''), match_phot,
    r2_rsun, m2_lo, m2_hi, a_ell, err_a_ell, a_ell_pred. Returns (label, reasons)."""
    reasons = []
    snr = v.get("snr", float("nan"))
    dp, ep = v.get("depth_p", float("nan")), v.get("err_p", float("nan"))
    if not (snr >= 10 and dp >= 3 * ep):
        return "NO_ECLIPSE", [f"strongest eclipse SNR {snr:.1f}, depth {dp:.5f} +- {ep:.5f}"]
    m_rv, m_ph = v.get("match_rv", ""), v.get("match_phot", "")
    if m_rv != "1:1":
        reasons.append(f"eclipse period does not equal the SB1 period (ratio {m_rv or 'none'}; "
                       f"Gaia photometric ratio {m_ph or 'none'})")
        return "PERIOD_CONFLICT", reasons
    reasons.append("eclipse period equals the Gaia SB1 period")
    do, eo = v.get("depth_odd", float("nan")), v.get("err_odd", float("nan"))
    de, ee = v.get("depth_even", float("nan")), v.get("err_even", float("nan"))
    if abs(do - de) > 3 * math.hypot(eo, ee):
        reasons.append(f"odd {do:.5f} vs even {de:.5f} differ by > 3 sigma: twin EB at 2P")
        return "STELLAR_EB", reasons
    ds_ = v.get("depth_s", float("nan"))
    ratio = ds_ / dp if dp > 0 else float("nan")
    r2 = v.get("r2_rsun", float("nan"))
    if ratio >= 0.1 or r2 >= 0.2:
        reasons.append(f"secondary/primary {ratio:.3f}, R2 {r2:.3f} R_sun: a luminous star")
        return "STELLAR_EB", reasons
    a_obs, a_err, a_pred = v.get("a_ell", float("nan")), v.get("err_a_ell", 0.0), v.get("a_ell_pred", float("nan"))
    if a_obs > 3 * a_pred + 3 * a_err:
        reasons.append(f"ellipsoidal {a_obs:.4f} > 3x predicted {a_pred:.4f}: heavier companion")
        return "MASS_TENSION", reasons
    m_lo, m_hi = v.get("m2_lo", float("nan")), v.get("m2_hi", float("nan"))
    reasons.append(f"R2 = {r2:.3f} R_sun, secondary/primary {ratio:.3f}, "
                   f"m2 (2 sigma, sin i = 1) {m_lo:.4f}-{m_hi:.4f} M_sun")
    if m_hi < trs.BD_MAX:
        return "TRANSITING_BROWN_DWARF_CANDIDATE", reasons
    if m_lo > 0.08:
        return "TRANSITING_VLM_STAR", reasons
    return "TRANSITING_BD_OR_VLM_BOUNDARY", reasons


# ---------------------------------------------------------------- data access
def _arr(x):
    """Plain float ndarray with NaN where masked (same as run_search._arr)."""
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


def load_tess(tic, data_dir, max_sectors=40):
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
        return [], []
    tab = sr.table
    best = {}
    for i in range(len(sr)):
        auth = str(tab["author"][i])
        if auth not in AUTH_RANK:
            continue
        sec = sector_of(tab, i)
        if sec is None:
            continue
        rank = AUTH_RANK[auth]                  # SPOC first, then TESS-SPOC, then QLP
        if sec not in best or rank < best[sec][0]:
            best[sec] = (rank, i, auth)
    segs, info = [], []
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
            keep = f > 0.5                       # broken cadences (see dipsearch 0.4.2)
            sd = robust_sd(f[keep])
            keep &= f < 1 + 5 * sd               # upward outliers only
            segs.append((t[keep], f[keep]))
            info.append({"sector": sec, "author": auth, "n": int(keep.sum()),
                         "sd_ppm": round(sd * 1e6, 1)})
            log("sector", sec, auth, int(keep.sum()))
        except Exception as exc:
            log("download failed", sec, auth, exc)
            info.append({"sector": sec, "author": auth, "error": str(exc)[:200]})
    return segs, info


def bls_search(t, f, pmin, pmax, durations, df=None, objective="snr"):
    from astropy.timeseries import BoxLeastSquares
    span = t.max() - t.min()
    df = df or 0.02 / span
    freqs = np.arange(1.0 / pmax, 1.0 / pmin, df)
    periods = np.sort(1.0 / freqs)
    bls = BoxLeastSquares(t, f)
    r = bls.power(periods, durations, objective=objective)
    return periods, r


def refine(t, f, P, durations, rel=1e-3, n=2001):
    from astropy.timeseries import BoxLeastSquares
    periods = np.linspace(P * (1 - rel), P * (1 + rel), n)
    r = BoxLeastSquares(t, f).power(periods, durations, objective="snr")
    j = int(np.argmax(r.power))
    return {"P": float(r.period[j]), "t0": float(r.transit_time[j]), "dur": float(r.duration[j]),
            "snr": float(r.depth_snr[j]), "power": float(r.power[j]), "depth": float(r.depth[j])}


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tic", type=int, required=True)
    ap.add_argument("--gaia", default="")
    ap.add_argument("--p-rv", type=float, required=True)
    ap.add_argument("--k-rv", type=float, required=True)
    ap.add_argument("--k-rv-err", type=float, required=True)
    ap.add_argument("--e-rv", type=float, default=0.0)
    ap.add_argument("--p-phot", type=float, default=float("nan"))
    ap.add_argument("--m1", type=float, required=True)
    ap.add_argument("--r1", type=float, required=True)
    ap.add_argument("--max-sectors", type=int, default=40)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    os.makedirs(a.data_dir, exist_ok=True)
    summary = {"version": VERSION, "tic": a.tic, "gaia": a.gaia, "args": vars(a)}

    def dump():
        with open(os.path.join(a.out_dir, f"vet_sp_{a.tic}.json"), "w") as fh:
            json.dump(summary, fh, indent=1, default=str)

    try:
        segs, info = load_tess(a.tic, a.data_dir, a.max_sectors)
        summary["sectors"] = info
        if not segs:
            summary["verdict"] = "NO_TESS_DATA"
            dump()
            print(json.dumps({"verdict": "NO_TESS_DATA"}))
            return 0
        t = np.concatenate([s[0] for s in segs])
        f = np.concatenate([s[1] for s in segs])
        o = np.argsort(t)
        t, f = t[o], f[o]
        fd = running_median_detrend(t, f, window=2.0, gap=0.5)
        bt, bf, _ = bin_lc(t, fd, 10.0 / 1440)
        summary["n_points"], summary["n_bins"] = int(t.size), int(bt.size)
        summary["span_d"] = float(bt.max() - bt.min())
        # Lomb-Scargle
        from astropy.timeseries import LombScargle
        fr = np.linspace(0.1, 10.0, 200000)
        pw = LombScargle(bt, bf).power(fr)
        top = []
        for j in np.argsort(pw)[::-1]:
            if all(abs(fr[j] - fr[k]) > 0.01 for k in top):
                top.append(j)
            if len(top) == 5:
                break
        summary["ls_top"] = [{"period": float(1 / fr[j]), "power": float(pw[j])} for j in top]
        log("LS", summary["ls_top"][:3])
        # BLS on the densest block (gaps > 30 d split blocks), then candidates on all data
        cuts = np.where(np.diff(bt) > 30)[0] + 1
        blocks = np.split(np.arange(bt.size), cuts)
        blk = max(blocks, key=len)
        blk = blk[bt[blk] <= bt[blk][0] + 60.0]          # at most 60 d for the wide search
        durations = np.array([0.02, 0.03, 0.045, 0.065, 0.09, 0.13])
        periods, r = bls_search(bt[blk], bf[blk], 0.2, 5.0, durations)
        j = int(np.argmax(r.power))
        p_bls = float(r.period[j])
        summary["bls_block"] = {"n": int(len(blk)), "P": p_bls, "snr": float(r.depth_snr[j]),
                                "depth": float(r.depth[j]), "dur": float(r.duration[j])}
        log("BLS block", summary["bls_block"])
        cands = {"bls": p_bls, "rv": a.p_rv, "2rv": 2 * a.p_rv, "2bls": 2 * p_bls}
        if math.isfinite(a.p_phot):
            cands["phot"] = a.p_phot
        refined = {}
        for name, P in cands.items():
            try:
                refined[name] = refine(bt, bf, P, durations)
            except Exception as exc:
                refined[name] = {"error": str(exc)}
        summary["candidates"] = refined
        ok = {k: v for k, v in refined.items() if "snr" in v}
        best_name = max(ok, key=lambda k: ok[k]["snr"])
        best = ok[best_name]
        # Half-period lock (ellipsoidal minima or two eclipses folded together): if the
        # odd and even "eclipses" differ by > 3 sigma, double the period (at most twice).
        doubled = 0
        meas = measure_eclipses(bt, bf, best["P"], best["t0"], best["dur"])
        while doubled < 2:
            do, de = meas.get("depth_odd", np.nan), meas.get("depth_even", np.nan)
            eo, ee = meas.get("err_odd", np.nan), meas.get("err_even", np.nan)
            if not (np.isfinite([do, de, eo, ee]).all() and abs(do - de) > 3 * math.hypot(eo, ee)):
                break
            # put the deeper of the two at phase 0 of the doubled period
            t0 = best["t0"] if do <= de else best["t0"] + best["P"]
            best = refine(bt, bf, 2 * best["P"], durations, rel=2e-4, n=801)
            best_name += "x2"
            doubled += 1
            log("odd/even differ: doubled to", best["P"], "t0 hint", t0)
            meas = measure_eclipses(bt, bf, best["P"], best["t0"], best["dur"])
        summary["doubled"] = doubled
        summary["best"] = {"name": best_name, **best}
        summary["measure"] = meas
        # same measurement at the SB1 period for the record
        if "rv" in ok:
            summary["measure_at_rv"] = measure_eclipses(bt, bf, ok["rv"]["P"], ok["rv"]["t0"], ok["rv"]["dur"])
        pm_rv = trs.period_match(best["P"], a.p_rv, rel_tol=1e-3)
        pm_ph = trs.period_match(best["P"], a.p_phot, rel_tol=1e-3) if math.isfinite(a.p_phot) else None
        m_lo, m_mid, m_hi = companion_mass_range(a.k_rv, a.k_rv_err, a.p_rv, a.m1, a.e_rv)
        a_rs = semi_major_axis_rsun(a.p_rv, a.m1 + m_mid)
        depth = meas.get("depth_p", float("nan"))
        v = dict(meas)
        v.update({"snr": best["snr"],
                  "match_rv": "" if pm_rv is None else f"{pm_rv[0]}:{pm_rv[1]}",
                  "match_phot": "" if pm_ph is None else f"{pm_ph[0]}:{pm_ph[1]}",
                  "r2_rsun": a.r1 * math.sqrt(depth) if depth > 0 else float("nan"),
                  "m2_lo": m_lo, "m2_mid": m_mid, "m2_hi": m_hi, "a_rsun": a_rs,
                  "a_ell_pred": expected_ellipsoidal(m_mid, a.m1, a.r1, a_rs),
                  "dur_central_pred": central_duration(a.p_rv, a_rs / a.r1)})
        v.setdefault("err_a_ell", 0.0)
        label, reasons = verdict(v)
        summary["inputs_to_verdict"] = v
        summary["verdict"] = label
        summary["reasons"] = reasons
        log("VERDICT", label, reasons)
        # plots
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, axs = plt.subplots(3, 1, figsize=(8, 10))
            for ax, (nm, P, t0) in zip(axs, [("best " + best_name, best["P"], best["t0"]),
                                             ("SB1 period", ok.get("rv", best)["P"], ok.get("rv", best)["t0"]),
                                             ("2 x best", 2 * best["P"], best["t0"])]):
                ph = phase(bt, P, t0)
                ax.plot(ph, bf, ",", color="0.6")
                edges = np.linspace(-0.5, 0.5, 101)
                idx = np.digitize(ph, edges) - 1
                med = [np.median(bf[idx == i]) if np.any(idx == i) else np.nan for i in range(100)]
                ax.plot(0.5 * (edges[1:] + edges[:-1]), med, "k-")
                lo, hi = np.nanpercentile(bf, [0.5, 99.5])
                ax.set_ylim(lo, hi)
                ax.set_title(f"TIC {a.tic} folded at {P:.6f} d ({nm})")
            fig.tight_layout()
            fig.savefig(os.path.join(a.out_dir, f"vet_sp_{a.tic}_fold.png"), dpi=110)
            plt.close(fig)
        except Exception as exc:
            summary["plot_error"] = str(exc)
        # catalogues
        try:
            summary["simbad"] = trs.simbad_lookup([a.gaia]) if a.gaia else {}
        except Exception as exc:
            summary["simbad"] = f"failed: {exc}"
    except Exception as exc:
        summary["error"] = traceback.format_exc()
        log("ERROR", exc)
        dump()
        return 1
    dump()
    print(json.dumps({"verdict": summary.get("verdict"), "reasons": summary.get("reasons"),
                      "best": summary.get("best")}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
