# SPDX-License-Identifier: Apache-2.0
"""selflens_vet.py -- vet TESS brightenings found at Gaia-predicted white-dwarf conjunctions.

Part of gaia-orbit-transits 0.14.0 by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0. Pre-registration: findings/2026-11-18-selflens-vet-prereg.md

gaia-selflens-v1 found 17 "pulse" events in 15 stars (and 5 control events) where about
1.9 detectable self-lensing pulses were expected at most. This script runs, for every
event, the checks that the self-lensing pre-registration promised before anything is
called a candidate. All fluxes are inverted (2 - f) so that a brightening is a positive
"amplitude", and the same box and baseline as vet_event.py are used:

  A. every SPOC / TESS-SPOC / QLP light curve of the target that covers the event:
     product flux, SAP flux, background and centroids in the box; quality flags;
     distance to the nearest data gap or segment end;
  B. the shape: a lensing pulse is symmetric, a flare rises fast and decays slowly;
  C. systematics: the same box on the nearest other TESS stars of that sector;
  D. pixels: a TESScut stamp, 3x3 background-subtracted aperture, the background
     itself, and an in-box minus out-of-box difference image whose centroid is
     compared with the target position;
  E. a positive control: the predicted symmetric pulse injected 3 days from the event
     must be recovered by the same box.
A verdict follows from the fixed rules in verdict().
"""
import argparse
import json
import os
import time
import traceback

import numpy as np

VERSION = "0.1.0"
AUTHORS = ("SPOC", "TESS-SPOC", "QLP")

# ---- pre-registered thresholds (do not change after the data are read) ----
EDGE_MIN_D = 1.0        # event centre must be >= 1 d from a gap > 0.5 d or segment end
GAP_D = 0.5
MIN_SNR = 5.0           # product box SNR (local linear baseline)
SAP_MIN_SNR = 3.0
OTHER_MIN_SNR = 3.0     # every other product covering the event must show it at >= 3
BKG_MAX_ABS_SNR = 5.0   # background change in the box
NB_FRAC_MAX = 0.3       # fraction of >= 5 neighbours brightening at > 3 sigma
NB_MIN = 5
ASYM_NSIG = 3.0         # flare test: halves differ by > 3 sigma and ...
ASYM_RATIO = 0.5        # ... the weaker half is < 0.5 x the stronger half
CENTROID_MAX_PX = 1.0
FLAG_FRAC_MAX = 0.5


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- pure helpers
def edge_distance(t, t0, gap_d=GAP_D):
    """Distance (d) from t0 to the nearest end of the data segment containing it.
    Segments are split at gaps > gap_d. If t0 falls in a gap or outside the data,
    the distance is 0."""
    t = np.sort(np.asarray([x for x in t if np.isfinite(x)], float))
    if t.size == 0:
        return 0.0
    cuts = np.where(np.diff(t) > gap_d)[0]
    starts = np.concatenate([[t[0]], t[cuts + 1]])
    ends = np.concatenate([t[cuts], [t[-1]]])
    for s, e in zip(starts, ends):
        if s <= t0 <= e:
            return float(min(t0 - s, e - t0))
    return 0.0


def baseline_fit(t, g, t0, dur_d, window_d=1.5, margin=0.25):
    """Linear baseline fitted to points within window_d of t0 but outside the box
    (+ margin x dur). Returns (coef, sd) or (None, nan)."""
    t = np.asarray(t, float)
    g = np.asarray(g, float)
    near = np.abs(t - t0) <= window_d
    out = near & (np.abs(t - t0) > dur_d / 2 + margin * dur_d)
    if out.sum() < 6:
        return None, float("nan")
    x = t[out] - t0
    A = np.vstack([np.ones_like(x), x]).T
    coef, *_ = np.linalg.lstsq(A, g[out], rcond=None)
    resid = g[out] - A @ coef
    med = np.median(resid)
    sd = 1.4826 * np.median(np.abs(resid - med))
    return coef, float(sd)


def half_amplitudes(t, g, t0, dur_d, window_d=1.5):
    """Mean excess above a linear baseline (fitted outside the whole box) in the first
    and second half of the box, and their errors. Input should be binned."""
    t = np.asarray(t, float)
    g = np.asarray(g, float)
    coef, sd = baseline_fit(t, g, t0, dur_d, window_d)
    res = {"a1": float("nan"), "a2": float("nan"), "e1": float("nan"), "e2": float("nan")}
    if coef is None or not np.isfinite(sd) or sd <= 0:
        return res
    first = (t >= t0 - dur_d / 2) & (t < t0)
    second = (t >= t0) & (t <= t0 + dur_d / 2)
    for key, m in (("1", first), ("2", second)):
        n = int(m.sum())
        if n < 2:
            continue
        base = coef[0] + coef[1] * (t[m] - t0)
        res["a" + key] = float(np.mean(g[m] - base))
        res["e" + key] = float(sd / np.sqrt(n))
    return res


def is_asymmetric(h):
    """Flare-like: the halves differ by > ASYM_NSIG sigma and the weaker one is below
    ASYM_RATIO x the stronger one."""
    a1, a2, e1, e2 = h["a1"], h["a2"], h["e1"], h["e2"]
    if not all(np.isfinite([a1, a2, e1, e2])):
        return False
    err = float(np.hypot(e1, e2))
    big, small = max(a1, a2), min(a1, a2)
    return bool(err > 0 and abs(a1 - a2) > ASYM_NSIG * err and big > 0
                and small < ASYM_RATIO * big)


def neighbour_frac(snrs, thresh=3.0):
    s = np.array([x for x in snrs if x is not None and np.isfinite(x)], float)
    if s.size == 0:
        return 0, float("nan")
    return int(s.size), float((s > thresh).mean())


def verdict(v):
    """Fixed, pre-registered rules for one event. v holds the measured quantities
    (missing keys mean 'not measured'). Returns (verdict, reasons)."""
    reasons = []

    def fin(k):
        x = v.get(k)
        return x is not None and isinstance(x, (int, float)) and np.isfinite(x)

    if fin("edge_d") and v["edge_d"] < EDGE_MIN_D:
        reasons.append("EDGE: centre < %.1f d from a data gap or segment end" % EDGE_MIN_D)
    if fin("snr") and v["snr"] < MIN_SNR:
        reasons.append("NOT SIGNIFICANT: product box SNR < %.0f" % MIN_SNR)
    if fin("snr") and fin("sap_snr") and v["snr"] >= MIN_SNR and v["sap_snr"] < SAP_MIN_SNR \
            and fin("sap_amp") and fin("amp") and v["sap_amp"] < v["amp"] / 3:
        reasons.append("SYSTEMATIC: brightening absent from SAP flux")
    if fin("other_min_snr") and v["other_min_snr"] < OTHER_MIN_SNR:
        reasons.append("NOT REPRODUCED: another product covering the event shows SNR < 3")
    if fin("bkg_snr") and abs(v["bkg_snr"]) >= BKG_MAX_ABS_SNR:
        reasons.append("SYSTEMATIC: background changes by >= 5 sigma in the box")
    if fin("nb_frac") and v.get("nb_n", 0) >= NB_MIN and v["nb_frac"] >= NB_FRAC_MAX:
        reasons.append("SYSTEMATIC: >= 30% of neighbour stars brighten > 3 sigma in the box")
    if v.get("asymmetric"):
        reasons.append("FLARE-LIKE: the two halves of the box differ (asymmetric)")
    if fin("flag_frac") and v["flag_frac"] > FLAG_FRAC_MAX:
        reasons.append("SYSTEMATIC: > 50% of in-box cadences carry quality flags")
    if fin("diff_offset_px") and v["diff_offset_px"] > CENTROID_MAX_PX \
            and fin("cut_snr") and v["cut_snr"] >= 3:
        reasons.append("OFF-TARGET: difference-image centroid > 1 pixel from the target")
    if not fin("snr"):
        reasons.append("INCONCLUSIVE: no product covering the event could be measured")
    if fin("cut_snr") and v["cut_snr"] < 3:
        reasons.append("INCONCLUSIVE: not seen in the TESScut aperture (SNR < 3)")
    if fin("cut_amp") and fin("amp") and v["amp"] > 0 and \
            not (v["amp"] / 3 <= v["cut_amp"] <= 3 * v["amp"]):
        reasons.append("INCONCLUSIVE: TESScut amplitude not within 3x of the product's")
    hard = [r for r in reasons if not r.startswith("INCONCLUSIVE")]
    if hard:
        return "REJECTED", reasons
    if reasons:
        return "UNRESOLVED", reasons
    return "SURVIVES", reasons


def brightening(ve, t, f, t0, dur_d, window_d):
    """vet_event.box_depth applied to the inverted flux 2 - f: amp and snr are positive
    for a brightening of the normalised flux f."""
    m = ve.box_depth(t, 2.0 - np.asarray(f, float), t0, dur_d, window_d)
    return {"amp": m["depth"], "err": m["err"], "snr": m["snr"], "fill": m["fill"],
            "n_in": m["n_in"], "n_out": m["n_out"]}


def pulse_model(t, t0, dur_d, amp):
    """Symmetric pulse used for injection: a box with linear ingress/egress of dur/6."""
    t = np.asarray(t, float)
    x = np.abs(t - t0)
    ramp = dur_d / 6.0
    full = x <= dur_d / 2 - ramp
    edge = (x > dur_d / 2 - ramp) & (x < dur_d / 2)
    out = np.zeros_like(t)
    out[full] = amp
    out[edge] = amp * (dur_d / 2 - x[edge]) / ramp
    return out


# ---------------------------------------------------------------- per event
def measure_event(ev, a, plt):
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    import lightkurve as lk
    import vet_event as ve

    coord = SkyCoord(ev["ra"], ev["dec"], unit="deg")
    t0 = float(ev["t0"])
    D = float(ev["dur_h"]) / 24.0
    Dp = max(float(ev["pred_dur_h"]), 2.0) / 24.0
    tag = "%s_%.2f" % (ev["source_id"], t0)
    rep = {"event": ev, "products": []}
    v = {}

    sr = ve.products(coord, a.data_dir)
    series = {}
    if sr is not None:
        tab = sr.table
        for i in range(len(sr)):
            au = str(tab["author"][i])
            if au not in AUTHORS:
                continue
            tn = str(tab["target_name"][i]).strip().lstrip("0") if "target_name" in tab.colnames else ""
            if tn.isdigit() and tn != str(ev["tic"]):
                continue
            ex = float(tab["exptime"][i]) if "exptime" in tab.colnames else np.nan
            if au == "SPOC" and ex < 100:
                continue
            sec = ve.sector_of(tab, i)
            key = "%s:%s:%d" % (sec, au, int(ex) if np.isfinite(ex) else 0)
            try:
                s = ve.load_product(sr[i], a.data_dir)
            except Exception as exc:
                log("load failed", key, exc)
                continue
            tt = s["t"][np.isfinite(s["t"])]
            if tt.size and tt.min() - 0.1 <= t0 <= tt.max() + 0.1:
                s["sector"] = sec
                series[key] = s
                log(tag, "covers", key)
    rows = []
    for key, s in series.items():
        q = s["q"]
        good = (q == 0) if q is not None else np.ones_like(s["t"], bool)
        r = {"product": key}
        pdc = s["pdc"]
        if pdc is None:
            continue
        fin = np.isfinite(s["t"]) & np.isfinite(pdc)
        r["edge_d"] = edge_distance(s["t"][fin], t0)
        near = np.abs(s["t"] - t0) <= D / 2
        r["flag_frac"] = float(np.mean(q[near] > 0)) if (q is not None and near.sum()) else np.nan
        t, f, _ = ve.clean(s["t"][good], pdc[good])
        m = brightening(ve, t, f, t0, D, a.window)
        r.update({"amp": m["amp"], "err": m["err"], "snr": m["snr"], "fill": m["fill"]})
        bt, bf, _ = ve.ds.bin_lc(t, f, 1.0 / 48)
        h = half_amplitudes(bt, bf, t0, D, a.window)
        r.update(h)
        r["asymmetric"] = is_asymmetric(h)
        if s["sap"] is not None:
            ts, fs, _ = ve.clean(s["t"][good], s["sap"][good])
            ms = brightening(ve, ts, fs, t0, D, a.window)
            r["sap_amp"], r["sap_snr"] = ms["amp"], ms["snr"]
        for col in ("bkg", "cx", "cy"):
            x = s[col]
            if x is None:
                continue
            ok = np.isfinite(x) & np.isfinite(s["t"])
            mb = ve.box_depth(s["t"][ok], x[ok] - np.nanmedian(x[ok]) + 1.0, t0, D, a.window)
            r[col + "_snr"] = -mb["snr"]       # positive = rises in the box
        # positive control: inject the predicted pulse 3 d before (or after) the event
        inj = []
        for tc in (t0 - 3.0, t0 + 3.0):
            if edge_distance(t, tc) < Dp:
                continue
            fi = f + pulse_model(t, tc, Dp, float(ev["pred_amp_ppm"]) * 1e-6)
            mi = brightening(ve, t, fi, tc, Dp, a.window)
            m0 = brightening(ve, t, f, tc, Dp, a.window)
            inj.append({"t_inj": tc, "snr_after": mi["snr"], "snr_before": m0["snr"]})
        r["inj"] = inj
        rows.append(r)
        # plot
        try:
            fig, axs = plt.subplots(4, 1, figsize=(9, 10), sharex=True)
            w = np.abs(s["t"] - t0) <= a.window + 1.5
            for ax, (lab, x) in zip(axs, (("flux (up = brighter)", None), ("SAP flux", s["sap"]),
                                          ("background", s["bkg"]), ("centroid col", s["cx"]))):
                if x is None and lab.startswith("flux"):
                    fw = np.abs(t - t0) <= a.window + 1.5
                    ax.plot(t[fw], f[fw], ".", ms=2, color="k")
                    bw = np.abs(bt - t0) <= a.window + 1.5
                    ax.plot(bt[bw], bf[bw], "o", ms=3, color="b")
                elif x is not None:
                    ax.plot(s["t"][w], x[w], ".", ms=2, color="k")
                    if q is not None:
                        fl = w & (q > 0)
                        ax.plot(s["t"][fl], x[fl], ".", ms=3, color="r")
                ax.axvspan(t0 - D / 2, t0 + D / 2, color="orange", alpha=0.3)
                ax.set_ylabel(lab, fontsize=8)
            axs[0].set_title("Gaia DR3 %s TIC %s %s  t0=%.3f  (red = flagged)"
                             % (ev["source_id"], ev["tic"], key, t0), fontsize=9)
            axs[-1].set_xlabel("BTJD")
            fig.tight_layout()
            fig.savefig(os.path.join(a.out_dir, "plots", "%s_%s.png" % (tag, key.replace(":", "_"))), dpi=90)
            plt.close(fig)
        except Exception:
            traceback.print_exc()
    rep["products"] = rows

    # the measuring product: the one with the highest SNR (it is the one that found it)
    best = None
    for r in rows:
        if np.isfinite(r.get("snr", np.nan)) and (best is None or r["snr"] > best["snr"]):
            best = r
    if best is not None:
        for k in ("edge_d", "flag_frac", "amp", "snr", "sap_amp", "sap_snr", "asymmetric", "a1", "a2"):
            if k in best:
                v[k] = best[k]
        v["bkg_snr"] = best.get("bkg_snr", np.nan)
        v["product"] = best["product"]
        others = [r["snr"] for r in rows if r is not best and np.isfinite(r.get("snr", np.nan))
                  and r.get("fill", 0) >= 0.5]
        v["other_min_snr"] = float(min(others)) if others else np.nan
        v["n_products"] = len(rows)
        inj = best.get("inj") or []
        v["inj_min_snr"] = float(min(x["snr_after"] for x in inj)) if inj else np.nan
    sec = series[best["product"]]["sector"] if best is not None else None

    # C. neighbours
    nb = []
    if sec is not None and a.neighbours > 0:
        try:
            nsr = None
            for rad in (0.3, 0.6, 1.2):
                nsr = lk.search_lightcurve(coord, radius=rad * u.deg, mission="TESS", sector=sec,
                                           author=list(AUTHORS))
                if nsr is not None and len(nsr) >= a.neighbours + 3:
                    break
            if nsr is not None:
                tab = nsr.table
                dist = np.asarray(tab["distance"], float) if "distance" in tab.colnames else np.arange(len(nsr))
                seen = {str(ev["tic"])}
                for i in np.argsort(dist):
                    tn = str(tab["target_name"][i]).strip().lstrip("0")
                    ex = float(tab["exptime"][i]) if "exptime" in tab.colnames else 0
                    if tn in seen or (str(tab["author"][i]) == "SPOC" and ex < 100):
                        continue
                    seen.add(tn)
                    try:
                        s = ve.load_product(nsr[int(i)], a.data_dir)
                        good = s["q"] == 0 if s["q"] is not None else np.ones_like(s["t"], bool)
                        t, f, _ = ve.clean(s["t"][good], s["pdc"][good])
                        m = brightening(ve, t, f, t0, D, a.window)
                        nb.append({"tic": tn, "author": str(tab["author"][i]),
                                   "dist_arcsec": float(dist[i]), "snr": m["snr"], "amp": m["amp"]})
                    except Exception as exc:
                        log("neighbour failed", tn, exc)
                    if len(nb) >= a.neighbours:
                        break
        except Exception:
            traceback.print_exc()
    v["nb_n"], v["nb_frac"] = neighbour_frac([r["snr"] for r in nb])
    rep["neighbours"] = nb

    # D. pixels
    if sec is not None and not a.no_tesscut:
        try:
            tpf = lk.search_tesscut(coord, sector=sec).download(
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
            tt, ff, _ = ve.clean(t[good], lc_ap[good])
            mc = brightening(ve, tt, ff, t0, D, a.window)
            mb = ve.box_depth(t[good], bkg[good] / np.nanmedian(bkg[good]), t0, D, a.window)
            v["cut_amp"], v["cut_snr"] = mc["amp"], mc["snr"]
            v["cut_bkg_snr"] = -mb["snr"]
            v["cut_edge_d"] = edge_distance(tt, t0)
            inb = good & (np.abs(t - t0) <= D / 2)
            outb = good & (np.abs(t - t0) > D / 2 + 0.25 * D) & (np.abs(t - t0) <= a.window)
            if inb.sum() >= 2 and outb.sum() >= 6:
                diff = np.nanmean(cube[inb], axis=0) - np.nanmean(cube[outb], axis=0)
                cxd, cyd = ve.weighted_centroid(np.where(np.hypot(xx - x0, yy - y0) <= 3, diff, 0))
                v["diff_offset_px"] = float(np.hypot(cxd - x0, cyd - y0))
                fig, axs = plt.subplots(1, 3, figsize=(13, 4))
                axs[0].imshow(np.nanmean(cube[outb], axis=0), origin="lower")
                axs[0].set_title("out-of-box mean")
                axs[1].imshow(diff, origin="lower", cmap="RdBu_r")
                axs[1].set_title("in minus out (positive = brightened)")
                for ax in axs[:2]:
                    ax.plot([x0], [y0], "x", color="w")
                    ax.plot([cxd], [cyd], "+", color="m")
                w = np.abs(tt - t0) <= a.window + 1.5
                axs[2].plot(tt[w], ff[w], ".", ms=2)
                axs[2].axvspan(t0 - D / 2, t0 + D / 2, color="orange", alpha=0.3)
                axs[2].set_title("TESScut 3x3 aperture (up = brighter)")
                fig.tight_layout()
                fig.savefig(os.path.join(a.out_dir, "plots", "%s_pixels.png" % tag), dpi=90)
                plt.close(fig)
        except Exception:
            traceback.print_exc()

    res, reasons = verdict(v)
    rep["measured"] = v
    rep["verdict"], rep["reasons"] = res, reasons
    return rep


def clean_json(o):
    if isinstance(o, dict):
        return {k: clean_json(x) for k, x in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_json(x) for x in o]
    if hasattr(o, "item"):
        o = o.item()
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o


def grade(reps):
    cand = [r for r in reps if "candidate" in r["event"]["role"]]
    ctrl = [r for r in reps if r["event"]["role"] == "control"]
    edge = [r for r in cand if r["event"].get("near_edge_list")]
    n_rej = sum(r["verdict"] == "REJECTED" for r in cand)
    n_surv = sum(r["verdict"] == "SURVIVES" for r in reps)
    inj = [r["measured"].get("inj_min_snr") for r in reps]
    inj = [x for x in inj if x is not None and np.isfinite(x)]
    return {
        "V1": {"prediction": "at least 15 of the 17 candidate events are REJECTED",
               "value": n_rej, "pass": n_rej >= 15},
        "V2": {"prediction": "every candidate listed as within 1.7 d of a segment edge is REJECTED",
               "value": sum(r["verdict"] == "REJECTED" for r in edge), "n": len(edge),
               "pass": all(r["verdict"] == "REJECTED" for r in edge)},
        "V3": {"prediction": "both extra control events are REJECTED or UNRESOLVED (none SURVIVES)",
               "value": [r["verdict"] for r in ctrl],
               "pass": all(r["verdict"] != "SURVIVES" for r in ctrl)},
        "V4": {"prediction": "at most one event SURVIVES", "value": n_surv, "pass": n_surv <= 1},
        "V5": {"prediction": "the injected predicted pulse is recovered at SNR >= 5 in at least "
                             "70% of measured events (the vet can see a real pulse)",
               "value": (float(np.mean([x >= 5 for x in inj])) if inj else None),
               "pass": bool(inj) and float(np.mean([x >= 5 for x in inj])) >= 0.7},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--events", default="events.json")
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--neighbours", type=int, default=8)
    ap.add_argument("--window", type=float, default=1.5)
    ap.add_argument("--no-tesscut", action="store_true")
    ap.add_argument("--time-budget-min", type=float, default=150.0)
    a = ap.parse_args(argv)
    os.makedirs(os.path.join(a.out_dir, "plots"), exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with open(a.events, encoding="utf-8") as fh:
        events = json.load(fh)["events"]
    start = time.time()
    reps = []
    for ev in events:
        if (time.time() - start) / 60.0 > a.time_budget_min:
            log("time budget reached; skipping", ev["source_id"], ev["t0"])
            reps.append({"event": ev, "verdict": "NOT RUN", "reasons": ["time budget"], "measured": {}})
            continue
        log("event", ev["source_id"], ev["t0"], ev["role"])
        try:
            rep = measure_event(ev, a, plt)
        except Exception as exc:
            traceback.print_exc()
            rep = {"event": ev, "verdict": "ERROR", "reasons": [str(exc)], "measured": {}}
        log("VERDICT", ev["source_id"], ev["t0"], rep["verdict"], rep["reasons"])
        reps.append(rep)
        with open(os.path.join(a.out_dir, "selflens_vet_events.json"), "w", encoding="utf-8") as fh:
            json.dump(clean_json(reps), fh, indent=1)
    grades = grade(reps)
    table = []
    for r in reps:
        m = r.get("measured", {})
        table.append({k: m.get(k) for k in ("product", "edge_d", "snr", "amp", "sap_snr", "bkg_snr",
                                            "other_min_snr", "nb_n", "nb_frac", "asymmetric",
                                            "cut_snr", "cut_amp", "diff_offset_px", "inj_min_snr")})
        table[-1].update({"source_id": r["event"]["source_id"], "t0": r["event"]["t0"],
                          "role": r["event"]["role"], "verdict": r["verdict"],
                          "reasons": " | ".join(r.get("reasons", []))})
    summary = {"version": VERSION, "n_events": len(reps),
               "verdicts": {k: sum(r["verdict"] == k for r in reps)
                            for k in ("SURVIVES", "UNRESOLVED", "REJECTED", "ERROR", "NOT RUN")},
               "grades": grades, "table": table,
               "minutes": (time.time() - start) / 60.0}
    with open(os.path.join(a.out_dir, "selflens_vet_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(clean_json(summary), fh, indent=1)
    print(json.dumps(clean_json({"verdicts": summary["verdicts"], "grades": grades})))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
