# SPDX-License-Identifier: Apache-2.0
"""Vet one TESS dip found at a Gaia-predicted transit window.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0.

Checks (all pre-registered in findings/2026-11-17-vet-41898425-prereg.md):
 A. every TESS light-curve product of the target that covers the event: PDC (or
    the product's detrended flux) against SAP flux, background, centroids and the
    quality flags, all in the same box;
 B. systematics: the same box measured on the nearest other TESS stars observed in
    that sector (same camera region), as a distribution;
 C. pixels: a TESScut stamp, background-subtracted aperture photometry and an
    in-box minus out-of-box difference image, whose centroid is compared with
    the target's position;
 D. repeat epochs: t0 + k P for P within +-3 sigma of the Gaia period, searched in
    every covered sector with a fixed-duration box (cadences with flux < 0.5,
    which are broken data, are dropped);
 E. a positive control: the expected transit injected into the same light curve
    must be recovered by the same box;
 F. catalogue neighbours (Gaia DR3 cone, SIMBAD, VSX via VizieR).
A verdict is derived from fixed rules (see verdict()).
"""
import argparse
import csv
import json
import os
import time
import traceback

import numpy as np

import dipsearch as ds

VERSION = "0.1.0"
AUTHORS = ("SPOC", "TESS-SPOC", "QLP")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- pure helpers
def clean(t, f, floor=0.5):
    """Finite, sorted, normalised; cadences below `floor` (broken data) dropped."""
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    ok = np.isfinite(t) & np.isfinite(f)
    t, f = t[ok], f[ok]
    if t.size == 0:
        return t, f, 0
    o = np.argsort(t)
    t, f = t[o], f[o]
    med = np.median(f)
    if not np.isfinite(med) or med == 0:
        return t[:0], f[:0], 0
    f = f / med
    bad = f < floor
    return t[~bad], f[~bad], int(bad.sum())


def box_depth(t, f, t0, dur_d, window_d=1.5, bin_width=1.0 / 48):
    """Depth of a box of length dur_d centred at t0, against a local linear baseline.

    Baseline: a straight line fitted to binned points within window_d of t0 but
    outside the box (+- 0.25 dur margin). The error is the scatter of the
    baseline residuals divided by sqrt(number of in-box bins). Returns a dict
    with depth (fractional, positive = dimming), err, snr, n_in, n_out, fill
    (fraction of the box with data).
    """
    bt, bf, _ = ds.bin_lc(t, f, bin_width)
    res = {"depth": np.nan, "err": np.nan, "snr": np.nan, "n_in": 0, "n_out": 0,
           "fill": 0.0}
    if bt.size == 0:
        return res
    near = np.abs(bt - t0) <= window_d
    inb = np.abs(bt - t0) <= dur_d / 2
    out = near & (np.abs(bt - t0) > dur_d / 2 + 0.25 * dur_d)
    n_in, n_out = int(inb.sum()), int(out.sum())
    res["n_in"], res["n_out"] = n_in, n_out
    res["fill"] = float(min(1.0, n_in * bin_width / dur_d)) if dur_d > 0 else 0.0
    if n_in < 2 or n_out < 6:
        return res
    x = bt[out] - t0
    A = np.vstack([np.ones_like(x), x]).T
    coef, *_ = np.linalg.lstsq(A, bf[out], rcond=None)
    resid = bf[out] - A @ coef
    sd = ds.robust_sd(resid)
    base_in = coef[0] + coef[1] * (bt[inb] - t0)
    depth = float(np.mean(base_in - bf[inb]))
    err = float(sd / np.sqrt(n_in)) if np.isfinite(sd) and sd > 0 else np.nan
    res.update({"depth": depth, "err": err,
                "snr": float(depth / err) if err and np.isfinite(err) else np.nan})
    return res


def epoch_windows(t0, P, P_sd, kmin=-12, kmax=12, nsig=3.0):
    """[(k, lo, hi)] time intervals where t0 + k P can fall for P in P +- nsig sd."""
    out = []
    for k in range(kmin, kmax + 1):
        if k == 0:
            continue
        a = t0 + k * (P - nsig * P_sd)
        b = t0 + k * (P + nsig * P_sd)
        out.append((k, min(a, b), max(a, b)))
    return out


def covered_periods(t, t0, k, P_lo, P_hi, dur_d, min_fill=0.5, step_frac=0.25,
                    bin_width=1.0 / 48):
    """Period values in [P_lo, P_hi] (grid step dur/(4|k|)) whose predicted epoch
    t0 + k P has at least min_fill of a dur_d box covered by data (binned)."""
    bt, _, _ = ds.bin_lc(t, np.ones_like(np.asarray(t, float)), bin_width)
    if bt.size == 0 or k == 0:
        return np.empty(0)
    dP = step_frac * dur_d / abs(k)
    grid = np.arange(P_lo, P_hi + dP / 2, dP)
    need = min_fill * dur_d / bin_width
    keep = []
    for P in grid:
        tc = t0 + k * P
        lo = np.searchsorted(bt, tc - dur_d / 2, side="left")
        hi = np.searchsorted(bt, tc + dur_d / 2, side="right")
        if hi - lo >= need:
            keep.append(P)
    return np.array(keep)


def weighted_centroid(img):
    """Centroid (x, y) of the positive part of a 2-D image (x = column)."""
    w = np.where(np.isfinite(img) & (img > 0), img, 0.0)
    s = w.sum()
    if s <= 0:
        return np.nan, np.nan
    yy, xx = np.indices(w.shape)
    return float((w * xx).sum() / s), float((w * yy).sum() / s)


def neighbour_stats(snrs, target_snr, thresh=3.0):
    """Fraction of neighbours dimming at > thresh sigma in the same box, and the
    target's rank among all (1 = deepest)."""
    s = np.array([x for x in snrs if np.isfinite(x)], float)
    if s.size == 0:
        return {"n": 0, "frac_dim": np.nan, "median_snr": np.nan, "target_rank": None}
    rank = int(1 + (s > target_snr).sum()) if np.isfinite(target_snr) else None
    return {"n": int(s.size), "frac_dim": float((s > thresh).mean()),
            "median_snr": float(np.median(s)), "target_rank": rank}


def verdict(v):
    """Fixed, pre-registered rules. v holds the measured quantities."""
    reasons = []
    if v.get("neighbour_frac_dim") is not None and np.isfinite(v["neighbour_frac_dim"]) \
            and v["neighbour_frac_dim"] >= 0.3:
        reasons.append("SYSTEMATIC: >= 30% of neighbour stars dim > 3 sigma in the same box")
    sap, pdc = v.get("sap_snr"), v.get("pdc_snr")
    if sap is not None and pdc is not None and np.isfinite(sap) and np.isfinite(pdc) \
            and pdc >= 3 and sap < 3 and v.get("sap_depth", 0) < v.get("pdc_depth", 0) / 3:
        reasons.append("SYSTEMATIC: dip absent from SAP flux (made by the PDC correction)")
    if v.get("flagged_frac") is not None and v["flagged_frac"] > 0.5:
        reasons.append("SYSTEMATIC: > 50% of in-box cadences carry quality flags")
    if v.get("diff_offset_px") is not None and np.isfinite(v["diff_offset_px"]) \
            and v["diff_offset_px"] > 1.0 and v.get("cut_snr", 0) >= 3:
        reasons.append("OFF-TARGET: difference-image centroid > 1 pixel from the target")
    if v.get("depth_max") is not None and v.get("pdc_depth") is not None \
            and np.isfinite(v["pdc_depth"]) and v["pdc_depth"] > v["depth_max"]:
        reasons.append("NOT SUBSTELLAR: deeper than the largest substellar depth")
    if v.get("repeat_excluded"):
        reasons.append("NO REPEAT: a covered repeat epoch with the injected depth "
                       "recoverable shows nothing (only for the covered period range)")
    if v.get("box_fill") is not None and v["box_fill"] < 0.5:
        reasons.append("INCONCLUSIVE: less than half the predicted duration has data")
    if v.get("pdc_snr") is not None and np.isfinite(v["pdc_snr"]) and v["pdc_snr"] < 3:
        reasons.append("NOT SIGNIFICANT: PDC box SNR < 3 against the local baseline")
    hard = [r for r in reasons if not r.startswith(("NO REPEAT", "INCONCLUSIVE"))]
    if hard:
        return "REJECTED", reasons
    if reasons:
        return "UNRESOLVED", reasons
    return "SURVIVES", reasons


# ---------------------------------------------------------------- data access
def _col(lc, names):
    for n in names:
        try:
            if n in lc.colnames:
                x = lc[n]
                x = getattr(x, "value", x)
                if hasattr(x, "unmasked"):
                    d = np.array(x.unmasked, dtype=float)
                    d[np.asarray(x.mask, bool)] = np.nan
                    return d
                return np.ma.filled(np.ma.asarray(x, dtype=float), np.nan)
        except Exception:
            continue
    return None


def products(target, data_dir, sector=None, radius_arcsec=3.0):
    import astropy.units as u
    import lightkurve as lk
    for attempt in range(3):
        try:
            return lk.search_lightcurve(target, radius=radius_arcsec * u.arcsec,
                                        mission="TESS", sector=sector)
        except Exception as exc:
            log("search retry", attempt, exc)
            time.sleep(5 * (attempt + 1))
    return None


def sector_of(tab, i):
    for key in ("sequence_number", "sector"):
        if key in tab.colnames:
            try:
                return int(tab[key][i])
            except Exception:
                pass
    digits = "".join(ch for ch in str(tab["mission"][i]) if ch.isdigit())
    return int(digits) if digits else None


def load_product(sr_row, data_dir):
    lc = sr_row.download(download_dir=data_dir, quality_bitmask="none")
    t = np.asarray(getattr(lc.time, "value", lc.time), float)
    out = {"t": t,
           "pdc": _col(lc, ["pdcsap_flux", "kspsap_flux", "flux"]),
           "sap": _col(lc, ["sap_flux"]),
           "bkg": _col(lc, ["sap_bkg", "bkg_flux"]),
           "cx": _col(lc, ["mom_centr1", "centroid_col"]),
           "cy": _col(lc, ["mom_centr2", "centroid_row"]),
           "q": _col(lc, ["quality"])}
    return out


def gaia_cone(ra, dec, radius_deg, gmax):
    import requests
    q = ("SELECT source_id, ra, dec, phot_g_mean_mag, parallax, ruwe, "
         "DISTANCE(POINT(ra, dec), POINT({ra}, {dec}))*3600 AS sep FROM gaiadr3.gaia_source "
         "WHERE 1=CONTAINS(POINT(ra, dec), CIRCLE({ra}, {dec}, {r})) "
         "AND phot_g_mean_mag < {g} ORDER BY sep").format(ra=ra, dec=dec, r=radius_deg, g=gmax)
    for base in ("https://gea.esac.esa.int/tap-server/tap", "https://gaia.ari.uni-heidelberg.de/tap"):
        try:
            r = requests.post(base + "/sync", data={"REQUEST": "doQuery", "LANG": "ADQL",
                                                    "FORMAT": "csv", "QUERY": q}, timeout=90)
            if r.ok and r.text.startswith("source_id"):
                return list(csv.DictReader(r.text.splitlines()))
        except Exception as exc:
            log("gaia cone failed", base, exc)
    return None


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tic", type=int, required=True)
    ap.add_argument("--gaia", type=str, default="")
    ap.add_argument("--ra", type=float, required=True)
    ap.add_argument("--dec", type=float, required=True)
    ap.add_argument("--gmag", type=float, default=12.0)
    ap.add_argument("--t0", type=float, required=True, help="event centre, BTJD")
    ap.add_argument("--dur-h", type=float, required=True, help="measured box length")
    ap.add_argument("--pred-dur-h", type=float, required=True)
    ap.add_argument("--sector", type=int, required=True)
    ap.add_argument("--period", type=float, required=True)
    ap.add_argument("--period-sd", type=float, required=True)
    ap.add_argument("--exp-depth", type=float, required=True,
                    help="expected fractional depth of a central transit")
    ap.add_argument("--depth-max", type=float, default=0.03)
    ap.add_argument("--neighbours", type=int, default=15)
    ap.add_argument("--window", type=float, default=1.5)
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    coord = SkyCoord(a.ra, a.dec, unit="deg")
    D = a.dur_h / 24.0
    Dp = a.pred_dur_h / 24.0
    rep = {"version": VERSION, "args": vars(a), "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    v = {"depth_max": a.depth_max}

    # ---- A. target products
    sr = products(coord, a.data_dir)
    prod_rows, series = [], {}
    if sr is not None:
        tab = sr.table
        for i in range(len(sr)):
            au = str(tab["author"][i])
            sec = sector_of(tab, i)
            exptime = float(tab["exptime"][i]) if "exptime" in tab.colnames else np.nan
            tn = str(tab["target_name"][i]).strip().lstrip("0") if "target_name" in tab.colnames else ""
            prod_rows.append({"i": i, "author": au, "sector": sec, "exptime": exptime, "target": tn})
    write_rows(os.path.join(a.out_dir, "products.csv"), prod_rows)
    log("products", len(prod_rows))
    for p in prod_rows:
        if p["author"] not in AUTHORS:
            continue
        if p["target"].isdigit() and p["target"] != str(a.tic):
            continue
        if p["author"] == "SPOC" and p["exptime"] < 100:
            continue
        key = f"{p['sector']}:{p['author']}"
        try:
            series[key] = load_product(sr[p["i"]], a.data_dir)
            log("loaded", key, len(series[key]["t"]))
        except Exception as exc:
            log("load failed", key, exc)

    # event-sector measurements, per product and per flux column
    ev_rows = []
    for key, s in series.items():
        sec = int(key.split(":")[0])
        if sec != a.sector:
            continue
        q = s["q"]
        near = np.abs(s["t"] - a.t0) <= D / 2
        flagged = float(np.mean(q[near] > 0)) if q is not None and near.sum() else np.nan
        for col in ("pdc", "sap", "bkg", "cx", "cy"):
            x = s[col]
            if x is None:
                continue
            good = (q == 0) if (q is not None and col in ("pdc", "sap")) else np.ones_like(s["t"], bool)
            if col in ("pdc", "sap"):
                t, f, nb = clean(s["t"][good], x[good])
                m = box_depth(t, f, a.t0, D, a.window)
            else:
                t = s["t"]
                ok = np.isfinite(x)
                m = box_depth(t[ok], x[ok] - np.nanmedian(x[ok]) + 1.0, a.t0, D, a.window)
            ev_rows.append({"product": key, "column": col, "flagged_frac": flagged, **m})
        # plot
        fig, axs = plt.subplots(5, 1, figsize=(9, 11), sharex=True)
        w = np.abs(s["t"] - a.t0) <= a.window + 1.0
        for ax, col in zip(axs, ("pdc", "sap", "bkg", "cx", "cy")):
            x = s[col]
            if x is None:
                continue
            ax.plot(s["t"][w], x[w], ".", ms=2, color="k")
            if q is not None:
                fl = w & (q > 0)
                ax.plot(s["t"][fl], x[fl], ".", ms=3, color="r")
            ax.axvspan(a.t0 - D / 2, a.t0 + D / 2, color="orange", alpha=0.3)
            ax.set_ylabel(col)
        axs[0].set_title(f"TIC {a.tic} {key}  event t0={a.t0} (red = quality-flagged)")
        axs[-1].set_xlabel("BTJD")
        fig.tight_layout()
        fig.savefig(os.path.join(a.out_dir, f"event_{key.replace(':', '_')}.png"), dpi=110)
        plt.close(fig)
    write_rows(os.path.join(a.out_dir, "event_measurements.csv"), ev_rows)
    best = None
    for r in ev_rows:
        if r["column"] == "pdc" and (best is None or r["product"].endswith(":SPOC")):
            best = r
    if best is not None:
        v["pdc_depth"], v["pdc_snr"] = best["depth"], best["snr"]
        v["box_fill"], v["flagged_frac"] = best["fill"], best["flagged_frac"]
        v["event_product"] = best["product"]
        for r in ev_rows:
            if r["product"] == best["product"] and r["column"] == "sap":
                v["sap_depth"], v["sap_snr"] = r["depth"], r["snr"]

    # ---- E. positive control: inject the expected transit at t0 and well away from it
    ctrl = []
    if best is not None:
        s = series[best["product"]]
        good = s["q"] == 0 if s["q"] is not None else np.ones_like(s["t"], bool)
        t, f, _ = clean(s["t"][good], s["pdc"][good])
        for tc in (a.t0, a.t0 - 3.0, a.t0 - 6.0):
            g = f.copy()
            g[np.abs(t - tc) <= Dp / 2] -= a.exp_depth
            m0 = box_depth(t, f, tc, D, a.window)
            m1 = box_depth(t, g, tc, D, a.window)
            ctrl.append({"t_inj": tc, "depth_inj": a.exp_depth, "snr_before": m0["snr"],
                         "snr_after": m1["snr"], "depth_after_minus_before":
                         (m1["depth"] - m0["depth"]) if np.isfinite(m1["depth"]) else np.nan})
    write_rows(os.path.join(a.out_dir, "injection_control.csv"), ctrl)
    rep["injection_control"] = ctrl

    # ---- B. neighbour systematics
    nb_rows = []
    try:
        import lightkurve as lk
        nsr = None
        for rad in (0.4, 0.8, 1.5):
            nsr = lk.search_lightcurve(coord, radius=rad * u.deg, mission="TESS",
                                       sector=a.sector, author=["SPOC", "TESS-SPOC"])
            if nsr is not None and len(nsr) >= a.neighbours + 3:
                break
        if nsr is not None:
            tab = nsr.table
            dist = np.asarray(tab["distance"], float) if "distance" in tab.colnames else np.arange(len(nsr))
            seen = {str(a.tic)}
            for i in np.argsort(dist):
                tn = str(tab["target_name"][i]).strip().lstrip("0")
                ex = float(tab["exptime"][i]) if "exptime" in tab.colnames else 0
                if tn in seen or (str(tab["author"][i]) == "SPOC" and ex < 100):
                    continue
                seen.add(tn)
                try:
                    s = load_product(nsr[int(i)], a.data_dir)
                    good = s["q"] == 0 if s["q"] is not None else np.ones_like(s["t"], bool)
                    t, f, _ = clean(s["t"][good], s["pdc"][good])
                    m = box_depth(t, f, a.t0, D, a.window)
                    nb_rows.append({"tic": tn, "author": str(tab["author"][i]),
                                    "dist_arcsec": float(dist[i]), **m})
                except Exception as exc:
                    log("neighbour failed", tn, exc)
                if len(nb_rows) >= a.neighbours:
                    break
    except Exception:
        traceback.print_exc()
    write_rows(os.path.join(a.out_dir, "neighbours.csv"), nb_rows)
    ns = neighbour_stats([r["snr"] for r in nb_rows], v.get("pdc_snr", np.nan))
    rep["neighbours"] = ns
    v["neighbour_frac_dim"] = ns["frac_dim"]

    # ---- C. pixels
    try:
        import lightkurve as lk
        tpf = lk.search_tesscut(coord, sector=a.sector).download(
            cutout_size=15, download_dir=a.data_dir, quality_bitmask="none")
        t = np.asarray(tpf.time.value, float)
        cube = np.asarray(getattr(tpf.flux, "value", tpf.flux), float)
        q = np.asarray(tpf.quality)
        x0, y0 = tpf.wcs.world_to_pixel(coord)
        x0, y0 = float(x0), float(y0)
        flat = cube.reshape(cube.shape[0], -1)
        bkg = np.nanpercentile(flat, 30, axis=1)
        cube = cube - bkg[:, None, None]
        yy, xx = np.indices(cube.shape[1:])
        ap3 = (np.abs(xx - x0) <= 1.5) & (np.abs(yy - y0) <= 1.5)
        lc_ap = np.nansum(cube[:, ap3], axis=1)
        good = (q == 0) & np.isfinite(lc_ap)
        tt, ff, _ = clean(t[good], lc_ap[good])
        mc = box_depth(tt, ff, a.t0, D, a.window)
        mb = box_depth(t[good], bkg[good] / np.nanmedian(bkg[good]), a.t0, D, a.window)
        v["cut_snr"] = mc["snr"]
        rep["cutout"] = {"aperture_3x3": mc, "background": mb, "x0": x0, "y0": y0}
        inb = good & (np.abs(t - a.t0) <= D / 2)
        outb = good & (np.abs(t - a.t0) > D / 2 + 0.25 * D) & (np.abs(t - a.t0) <= a.window)
        if inb.sum() >= 2 and outb.sum() >= 6:
            diff = np.nanmean(cube[outb], axis=0) - np.nanmean(cube[inb], axis=0)
            mean_img = np.nanmean(cube[outb], axis=0)
            cxd, cyd = weighted_centroid(np.where(np.hypot(xx - x0, yy - y0) <= 3, diff, 0))
            v["diff_offset_px"] = float(np.hypot(cxd - x0, cyd - y0))
            rep["cutout"]["diff_centroid"] = [cxd, cyd]
            fig, axs = plt.subplots(1, 3, figsize=(13, 4))
            axs[0].imshow(mean_img, origin="lower")
            axs[0].set_title("out-of-box mean")
            axs[1].imshow(diff, origin="lower", cmap="RdBu_r")
            axs[1].set_title("out minus in (positive = dimmed)")
            for ax in axs[:2]:
                ax.plot([x0], [y0], "x", color="w")
                ax.plot([cxd], [cyd], "+", color="m")
            w = np.abs(tt - a.t0) <= a.window + 1
            axs[2].plot(tt[w], ff[w], ".", ms=2)
            axs[2].axvspan(a.t0 - D / 2, a.t0 + D / 2, color="orange", alpha=0.3)
            axs[2].set_title("TESScut 3x3 aperture, bkg-subtracted")
            fig.tight_layout()
            fig.savefig(os.path.join(a.out_dir, "pixels.png"), dpi=110)
            plt.close(fig)
    except Exception:
        traceback.print_exc()

    # ---- D. repeat epochs in every product (flux < 0.5 dropped)
    ep_rows = []
    for key, s in series.items():
        good = s["q"] == 0 if s["q"] is not None else np.ones_like(s["t"], bool)
        if s["pdc"] is None:
            continue
        t, f, nbad = clean(s["t"][good], s["pdc"][good])
        if t.size == 0:
            continue
        for k, lo, hi in epoch_windows(a.t0, a.period, a.period_sd):
            if hi < t[0] - Dp or lo > t[-1] + Dp:
                continue
            P_lo = (lo - a.t0) / k if k > 0 else (hi - a.t0) / k
            P_hi = (hi - a.t0) / k if k > 0 else (lo - a.t0) / k
            Ps = covered_periods(t, a.t0, k, P_lo, P_hi, Dp)
            if Ps.size == 0:
                continue
            best_snr, best_tc, worst_inj = -np.inf, np.nan, np.inf
            for P in Ps[:: max(1, Ps.size // 200)]:
                tc = a.t0 + k * P
                m = box_depth(t, f, tc, Dp, a.window)
                if np.isfinite(m["snr"]) and m["snr"] > best_snr:
                    best_snr, best_tc = m["snr"], tc
                g = f.copy()
                g[np.abs(t - tc) <= Dp / 2] -= a.exp_depth
                mi = box_depth(t, g, tc, Dp, a.window)
                if np.isfinite(mi["snr"]):
                    worst_inj = min(worst_inj, mi["snr"])
            ep_rows.append({"product": key, "k": k, "P_cov_min": float(Ps.min()),
                            "P_cov_max": float(Ps.max()), "n_P": int(Ps.size),
                            "frac_of_3sd_range": float(Ps.size * 0.25 * Dp / abs(k) / (P_hi - P_lo)),
                            "best_snr": best_snr, "best_t": best_tc,
                            "min_injected_snr": worst_inj, "dropped_below_half": nbad})
    write_rows(os.path.join(a.out_dir, "repeat_epochs.csv"), ep_rows)
    v["repeat_excluded"] = any(r["best_snr"] < 3 and r["min_injected_snr"] >= 7
                               and r["frac_of_3sd_range"] >= 0.9 for r in ep_rows)

    # ---- F. catalogues
    cat = {}
    g = gaia_cone(a.ra, a.dec, 63 / 3600.0, a.gmag + 7)
    cat["gaia_within_63arcsec"] = g
    try:
        from astroquery.simbad import Simbad
        r = Simbad.query_region(coord, radius=60 * u.arcsec)
        cat["simbad"] = [] if r is None else [str(x) for x in r[r.colnames[0]]]
    except Exception as exc:
        cat["simbad"] = f"failed: {exc}"
    try:
        from astroquery.vizier import Vizier
        r = Vizier(columns=["**"]).query_region(coord, radius=120 * u.arcsec, catalog="B/vsx/vsx")
        cat["vsx"] = [] if len(r) == 0 else [dict(zip(r[0].colnames, map(str, row))) for row in r[0]]
    except Exception as exc:
        cat["vsx"] = f"failed: {exc}"
    rep["catalogues"] = cat

    res, reasons = verdict(v)
    rep["measured"] = {k: (None if isinstance(x, float) and not np.isfinite(x) else x) for k, x in v.items()}
    rep["verdict"] = res
    rep["reasons"] = reasons
    with open(os.path.join(a.out_dir, "vet_summary.json"), "w") as fh:
        json.dump(rep, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log("VERDICT", res, reasons)
    return 0


def write_rows(path, rows):
    if not rows:
        open(path, "w").close()
        return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
