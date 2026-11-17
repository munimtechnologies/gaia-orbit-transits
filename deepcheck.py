# SPDX-License-Identifier: Apache-2.0
"""deepcheck.py -- archival test of the best Gaia-forecast targets, with Kepler data and
deep eclipses kept.

gaia-orbit-transits 0.9.0. MV2 of Munim, Inc.; made with AI agents.
Code Apache-2.0, results CC BY 4.0.

Why this exists. The forecast run (job gaia-forecast-v2, run B) ranks its best targets by
the expected number of TESS transits; the top three are nearby M dwarfs (68-111 pc) with
0.08-0.10 Msun companions on 135-194 d orbits. A 0.1 Msun companion in front of a
0.3 Rsun M dwarf blocks 10-20% of the light. archival.py 0.4.1 drops every residual
deeper than max(8 sd, 8%) as an outlier (archival.prepare), so such an eclipse would be
thrown away, while injected copies (added after the clip) would still be "recovered" and
the eclipse wrongly excluded. deepcheck therefore:

 1. keeps residuals up to MAX_DEPTH (60%) deep (prepare_deep);
 2. adds Kepler long-cadence PDCSAP light curves (2009-2013) when the star was a Kepler
    target (one star of run B lies in the Kepler field), and runs a Kepler-only search as
    well as the combined one;
 3. lists the deepest dips in all the data regardless of the Gaia ephemeris, with each
    dip's offset from the predicted conjunctions (deepest_dips, conj_offset), so an
    eclipse at the wrong phase, or an unrelated eclipsing binary, is seen too;
 4. looks the star up in the Kepler eclipsing-binary catalogue (Kirk et al. 2016,
    VizieR J/AJ/151/68).

Everything else (Gaia prior, ephemeris posterior, grid search, shuffled-residual null,
injection-recovery and the p (1 - R) / (1 - p R) update) is archival.py 0.4.1, unchanged.
"""
import argparse
import csv
import json
import os
import sys
import time

import numpy as np

import archival as ar

VERSION = "0.9.0"
BKJD_TO_BTJD = 2454833.0 - 2457000.0      # Kepler BKJD -> TESS BTJD: -2167.0 d
MAX_DEPTH = 0.6
KEPLER_DETREND = (1.5, 0.3)              # same running-median window as TESS
DIP_SEP_D = 1.0
KEPLER_MATCH_ARCSEC = 5.0

ar.DETREND.setdefault("kepler", KEPLER_DETREND)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- pure helpers
def bkjd_to_btjd(t):
    return np.asarray(t, float) + BKJD_TO_BTJD


def prepare_deep(segments, d0, max_depth=MAX_DEPTH):
    """archival.prepare with the upper clip at max(8 sd, max_depth) instead of
    max(8 sd, 0.08). Same outputs (t, d, w, g, survey, segments)."""
    T, D, W, G, S, info = [], [], [], [], [], []
    for gi, sg in enumerate(segments):
        t = np.asarray(sg["t"], float)
        f = np.asarray(sg["f"], float)
        ok = np.isfinite(t) & np.isfinite(f) & (f > 0)
        t, f = t[ok], f[ok]
        if t.size < 10:
            continue
        o = np.argsort(t)
        t, f = t[o], f[o]
        par = ar.DETREND.get(sg.get("survey"), None)
        if par is not None:
            half, ex = par
            ex = max(ex, d0)
            r = ar.detrend(t, f, ex + half, ex)
        else:
            r = f / np.median(f)
        d = 1.0 - r
        d = d - np.median(d)
        sd = 1.4826 * np.median(np.abs(d))
        sd = max(sd, 1e-4)
        keep = (d > -5 * sd) & (d < max(8 * sd, max_depth))
        t, d = t[keep], d[keep]
        if t.size < 10:
            continue
        T.append(t)
        D.append(d)
        W.append(np.full(t.size, 1.0 / sd ** 2))
        G.append(np.full(t.size, gi))
        S.append(np.full(t.size, sg.get("survey", "?"), dtype=object))
        info.append({"name": sg["name"], "survey": sg.get("survey", "?"), "n": int(t.size),
                     "sd": float(sd), "t_min": float(t.min()), "t_max": float(t.max())})
    if not T:
        return None
    t = np.concatenate(T)
    o = np.argsort(t)
    return {"t": t[o], "d": np.concatenate(D)[o], "w": np.concatenate(W)[o],
            "g": np.concatenate(G)[o], "survey": np.concatenate(S)[o], "segments": info}


def deepest_dips(t, d, w, D, n_top=8, sep=DIP_SEP_D, min_pts=3, survey=None):
    """The n_top strongest box dips of duration D anywhere in the data (box centred on
    each data point, |t - tc| < D/2), at least sep days apart. t must be sorted.
    SNR = sum(w d) / sqrt(sum w), depth = sum(w d) / sum(w)."""
    t = np.asarray(t, float)
    d = np.asarray(d, float)
    w = np.asarray(w, float)
    if t.size == 0:
        return []
    cw = np.concatenate([[0.0], np.cumsum(w)])
    cwd = np.concatenate([[0.0], np.cumsum(w * d)])
    lo = np.searchsorted(t, t - D / 2, side="right")
    hi = np.searchsorted(t, t + D / 2, side="left")
    sw = cw[hi] - cw[lo]
    swd = cwd[hi] - cwd[lo]
    n = hi - lo
    good = (n >= min_pts) & (sw > 0)
    snr = np.full(t.size, -np.inf)
    snr[good] = swd[good] / np.sqrt(sw[good])
    out = []
    for i in np.argsort(-snr, kind="stable"):
        if not np.isfinite(snr[i]):
            break
        if any(abs(t[i] - o["t"]) < sep for o in out):
            continue
        out.append({"t": float(t[i]), "snr": float(snr[i]), "depth": float(swd[i] / sw[i]),
                    "n": int(n[i]),
                    "survey": str(survey[i]) if survey is not None else ""})
        if len(out) >= n_top:
            break
    return out


def conj_offset(t, eph):
    """Offset of time t from the nearest predicted conjunction of an archival.ephemeris
    summary: cycle n, dt (days), its 1-sigma sd = sqrt(T_sd^2 + n^2 P_sd^2 +
    2 n rho T_sd P_sd) and z = dt / sd."""
    P, T0 = float(eph["P_mu"]), float(eph["T_mu"])
    n = int(np.round((t - T0) / P))
    dt = float(t - (T0 + n * P))
    var = (eph["T_sd"] ** 2 + (n * eph["P_sd"]) ** 2
           + 2.0 * n * eph.get("rho", 0.0) * eph["T_sd"] * eph["P_sd"])
    sd = float(np.sqrt(max(var, 1e-12)))
    return {"n": n, "dt_d": dt, "sd_d": sd, "z": dt / sd}


def kepler_match_ok(dist_arcsec, kepmag, gmag):
    """The Kepler target is taken to be the Gaia star if it lies within 5 arcsec, or
    within 10 arcsec with Kp within 1 mag of G (proper motion since the KIC epoch)."""
    if dist_arcsec is None or not np.isfinite(dist_arcsec):
        return False
    if dist_arcsec <= KEPLER_MATCH_ARCSEC:
        return True
    try:
        return dist_arcsec <= 10.0 and abs(float(kepmag) - float(gmag)) <= 1.0
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------- network
def fetch_kepler(ra, dec, gmag, sid, lk_dir, radius_arcsec=10.0):
    """Kepler long-cadence PDCSAP light curves of the nearest Kepler target -> segments."""
    import astropy.units as u
    import lightkurve as lk
    from astropy.coordinates import SkyCoord
    import run_search as rs
    info = {"kepler_target": False}
    sr = None
    c = SkyCoord(ra, dec, unit="deg")
    for kw in ({"author": "Kepler", "exptime": "long"}, {"author": "Kepler"}, {}):
        for attempt in range(3):
            try:
                sr = lk.search_lightcurve(c, radius=radius_arcsec * u.arcsec,
                                          mission="Kepler", **kw)
                break
            except Exception as exc:
                log("kepler search retry", kw, attempt, exc)
                time.sleep(5 * (attempt + 1))
        if sr is not None and len(sr):
            break
    if sr is None or len(sr) == 0:
        return [], info
    tab = sr.table
    names = [str(x).strip() for x in tab["target_name"]]
    dist = (np.asarray(tab["distance"], float) if "distance" in tab.colnames
            else np.zeros(len(names)))
    best = names[int(np.nanargmin(dist))]
    info.update({"target_name": best, "distance_arcsec": float(np.nanmin(dist)),
                 "n_products": len(names)})
    segs, quarters, kepmag, kepid = [], [], None, None
    for i, nm in enumerate(names):
        if nm != best:
            continue
        if "exptime" in tab.colnames:
            try:
                if float(tab["exptime"][i]) < 1000:
                    continue                 # short cadence: keep the long-cadence set
            except (TypeError, ValueError):
                pass
        try:
            lc = sr[i].download(download_dir=lk_dir, quality_bitmask="default")
            if lc is None:
                continue
            t = bkjd_to_btjd(rs._arr(lc.time.value))
            f = rs._arr(lc.flux)
            ok = np.isfinite(t) & np.isfinite(f) & (f > 0)
            if ok.sum() < 100:
                continue
            t, f = t[ok], f[ok]
            f = f / np.nanmedian(f)
            sd = 1.4826 * np.median(np.abs(f - 1.0))
            keep = f < 1 + 6 * max(sd, 1e-5)        # upward outliers only (flares, CRs)
            q = lc.meta.get("QUARTER", i)
            kepmag = lc.meta.get("KEPMAG", kepmag)
            kepid = lc.meta.get("KEPLERID", kepid)
            quarters.append(int(q) if str(q).lstrip("-").isdigit() else str(q))
            segs.append({"name": f"kepler-q{q}", "survey": "kepler", "t": t[keep],
                         "f": f[keep]})
        except Exception as exc:
            log("kepler download failed", sid, i, exc)
    info.update({"kepid": kepid, "kepmag": kepmag, "quarters": quarters,
                 "n_points": int(sum(len(s["t"]) for s in segs))})
    km = None
    try:
        km = float(kepmag)
    except (TypeError, ValueError):
        pass
    info["match_ok"] = kepler_match_ok(info["distance_arcsec"], km, gmag)
    info["kepler_target"] = bool(segs) and info["match_ok"]
    if not info["match_ok"]:
        log("kepler target", best, "rejected as a different star", info)
        return [], info
    return segs, info


def kepler_eb_lookup(ra, dec):
    """Kepler EB catalogue (Kirk et al. 2016, J/AJ/151/68) within 10 arcsec."""
    try:
        import astropy.units as u
        from astropy.coordinates import SkyCoord
        from astroquery.vizier import Vizier
        v = Vizier(columns=["*"], row_limit=10, timeout=120)
        tl = v.query_region(SkyCoord(ra, dec, unit="deg"), radius=10 * u.arcsec,
                            catalog=["J/AJ/151/68"])
        rows = []
        for key in tl.keys():
            tb = tl[key]
            rows += [{k: str(tb[k][i])[:40] for k in tb.colnames} for i in range(len(tb))]
        return {"rows": rows}
    except Exception as exc:
        return {"error": str(exc)[:200]}


# ---------------------------------------------------------------- plotting
def plot_fold(path, title, data, eph, D0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = ar.wrap(data["t"] - eph["T_mu"], eph["P_mu"])
    half = min(max(4 * eph["T_sd"], 3 * D0, 1.0), eph["P_mu"] / 2)
    m = np.abs(x) < half
    fig, ax = plt.subplots(figsize=(9, 4))
    colors = {"tess": "tab:blue", "ztf": "tab:green", "asassn": "tab:orange",
              "gaia": "tab:red", "kepler": "tab:purple"}
    for sv in sorted(set(data["survey"][m].tolist())):
        mm = m & (data["survey"] == sv)
        ax.plot(x[mm], 1 - data["d"][mm], ".", ms=2, color=colors.get(sv, "k"), label=sv)
    ax.axvspan(-eph["T_sd"], eph["T_sd"], color="0.85", zorder=0)
    ax.set_xlabel("days from predicted conjunction (folded on the Gaia period; "
                  "grey = 1 sigma at the reference epoch)")
    ax.set_ylabel("detrended flux")
    ax.legend(fontsize=7)
    ax.set_title(title, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


# ---------------------------------------------------------------- main
def _analyse_block(data, eph, D0, pred_depth, p_prior, args, rng):
    out = ar.analyse(data, eph, D0, pred_depth, p_prior, args.n_null, args.n_inj, rng)
    return {"best_snr": out["obs"]["snr"], "best_P": out["obs"]["P"],
            "best_T": out["obs"]["T"], "best_D_h": out["obs"]["D"] * 24,
            "best_depth": out["obs"]["depth"], "best_n_epochs": out["obs"]["n_epochs"],
            "thr": out["thr"], "fap": out["fap"], "cov_any": out["injection"]["cov1"],
            "cov_2epochs": out["injection"]["cov_2ep"],
            "recovery_pred_depth": out["recovery_at_pred_depth"],
            "p_transit_prior": out["p_transit_prior"],
            "p_transit_post": out["p_transit_post"], "verdict": out["verdict"],
            "by_survey_snr": json.dumps({k: round(v, 2)
                                         for k, v in out["by_survey_snr"].items()})}, out


def main(argv=None):
    import run_search as rs
    import gaia_orbits as go
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--source-ids", required=True)
    ap.add_argument("--schema", default="gaiadr3")
    ap.add_argument("--gmax", type=float, default=17)
    ap.add_argument("--cosi-max", type=float, default=0.3)
    ap.add_argument("--mc", type=int, default=2000)
    ap.add_argument("--n-null", type=int, default=30)
    ap.add_argument("--n-inj", type=int, default=300)
    ap.add_argument("--surveys", default="gaia,ztf,asassn,tess,kepler")
    ap.add_argument("--max-lcs", type=int, default=20)
    ap.add_argument("--max-depth", type=float, default=MAX_DEPTH)
    ap.add_argument("--time-budget-min", type=float, default=230)
    ap.add_argument("--seed", type=int, default=20261117)
    args = ap.parse_args(argv)
    t0 = time.time()
    surveys = {s.strip() for s in args.surveys.split(",") if s.strip()}
    order = list(dict.fromkeys(int(x) for x in args.source_ids.replace(" ", "").split(",") if x))
    src = sorted(set(order))
    os.makedirs(args.out_dir, exist_ok=True)
    pdir = os.path.join(args.out_dir, "deepcheck")
    os.makedirs(pdir, exist_ok=True)
    cache = os.path.join(args.data_dir, "archival")
    os.makedirs(cache, exist_ok=True)
    lk_dir = os.path.join(args.data_dir, "lk")
    os.makedirs(lk_dir, exist_ok=True)
    go.GAIA_REF_BTJD = 389.0

    tag = f"{args.schema}_nss_ti_g{args.gmax:g}_c{args.cosi_max:g}"
    tag += f"_ids{len(src)}-{sum(src) % 1000003}"
    query = rs.build_nss_query(args.schema, args.gmax, args.cosi_max, None, src)
    rows = rs.read_csv_text(rs.cached_query(os.path.join(args.data_dir, tag + "_v3.csv"), query))
    log("Gaia rows:", len(rows))
    by_src = {}
    for r in rows:
        ep = r.get("ref_epoch", np.nan)
        r["ref_btjd"] = rs.ref_epoch_to_btjd(ep) if np.isfinite(ep) else go.GAIA_REF_BTJD
        r["_labelled"] = bool(go.transit_label(r)["transit_conj"])
        old = by_src.get(r["source_id"])
        if old is None or (r["_labelled"] and not old["_labelled"]):
            by_src[r["source_id"]] = r

    results, kepler_meta = [], {}
    summary = {"version": VERSION, "args": vars(args),
               "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for sid in order:
        if (time.time() - t0) / 60 > args.time_budget_min:
            summary["stopped_before"] = sid
            log("time budget reached before", sid)
            break
        r = by_src.get(sid)
        if r is None:
            log("no Gaia row for", sid)
            results.append({"source_id": sid, "verdict": "no Gaia row"})
            continue
        rng = np.random.default_rng([args.seed, sid % (2 ** 32), sid // (2 ** 32)])
        try:
            res = rs.prior_for_row(r, args.mc, rng, None)
        except Exception as exc:
            log("prior failed", sid, exc)
            res = None
        if res is None:
            results.append({"source_id": sid, "verdict": "no prior"})
            continue
        pr, s, _ = res
        segs, tic = [], ""
        if "gaia" in surveys:
            try:
                segs += ar.fetch_gaia_epoch(sid, cache, "Gaia DR3")
            except Exception as exc:
                log("gaia epoch failed", sid, exc)
        if "ztf" in surveys and r["dec"] > -31:
            try:
                segs += ar.fetch_ztf(r["ra"], r["dec"], cache, sid)
            except Exception as exc:
                log("ztf failed", sid, exc)
        if "asassn" in surveys:
            try:
                segs += ar.fetch_asassn(r["ra"], r["dec"], cache, sid)
            except Exception as exc:
                log("asassn failed", sid, exc)
        if "tess" in surveys:
            try:
                ts, tic = ar.fetch_tess_segments(r["ra"], r["dec"], r["phot_g_mean_mag"], sid,
                                                 lk_dir, args.max_lcs)
                segs += ts
            except Exception as exc:
                log("tess failed", sid, exc)
        kinfo = {}
        if "kepler" in surveys:
            try:
                ks, kinfo = fetch_kepler(r["ra"], r["dec"], r["phot_g_mean_mag"], sid, lk_dir)
                segs += ks
            except Exception as exc:
                log("kepler failed", sid, exc)
                kinfo = {"error": str(exc)[:200]}
            if kinfo.get("kepler_target") or kinfo.get("target_name"):
                kinfo["kepler_eb_catalogue"] = kepler_eb_lookup(r["ra"], r["dec"])
            kepler_meta[str(sid)] = kinfo
        log(sid, "segments:", [(sg["name"], len(sg["t"])) for sg in segs])
        keys = [pr["transit_conj"]] if pr["transit_conj"] and pr["rv_consistent"] else ["t1", "t2"]
        for key in keys:
            D0 = pr[f"dur{key[1]}_h"] / 24.0
            if not np.isfinite(D0) or D0 <= 0:
                D0 = 0.25
            D0 = max(D0, 1.0 / 24)
            rec = {"source_id": sid, "key": key, "rv_labelled": key == pr["transit_conj"],
                   "tic": tic, "kepid": kinfo.get("kepid", ""), "period_d": r["period"],
                   "gmag": r["phot_g_mean_mag"], "abs_g": pr["abs_g"], "m1": pr["m1"],
                   "r1": pr["r1"], "m2_dark": pr["m2_dark"], "r2": pr["r2"],
                   "class": pr["class"], "cosi": pr["cosi"], "D0_h": D0 * 24}
            data = prepare_deep(segs, D0, args.max_depth)
            if data is None:
                rec["verdict"] = "no data"
                results.append(rec)
                continue
            tc = pr["t_conj1_btjd"] if key == "t1" else pr["t_conj2_btjd"]
            eph = ar.ephemeris(s["P"], s[key], tc, float(r["period"]),
                               float(np.median(data["t"])))
            r2r1 = pr["r2"] / pr["r1"] if pr["r1"] > 0 else 0.15
            pred_depth = float(min(max(r2r1 ** 2, 0.002), 0.5))
            p_prior = pr[f"p_ecl{key[1]}"]
            counts = {}
            for sg in data["segments"]:
                counts[sg["survey"]] = counts.get(sg["survey"], 0) + sg["n"]
            rec.update({"n_points": int(data["t"].size), "points_by_survey": json.dumps(counts),
                        "pred_depth": pred_depth, "P_mu": eph["P_mu"], "P_sd": eph["P_sd"],
                        "T_ref_mu": eph["T_mu"], "T_ref_sd": eph["T_sd"], "rho_PT": eph["rho"]})
            detail = {"record": rec, "ephemeris": eph, "segments": data["segments"]}
            try:
                block, out = _analyse_block(data, eph, D0, pred_depth, p_prior, args, rng)
                rec.update(block)
                detail["result"] = out
            except Exception as exc:
                import traceback
                traceback.print_exc()
                rec["verdict"] = "error: " + str(exc)[:200]
            # Kepler on its own (one instrument, four continuous years)
            ks = [sg for sg in segs if sg.get("survey") == "kepler"]
            if ks:
                kd = prepare_deep(ks, D0, args.max_depth)
                if kd is not None:
                    keph = ar.ephemeris(s["P"], s[key], tc, float(r["period"]),
                                        float(np.median(kd["t"])))
                    try:
                        kb, kout = _analyse_block(kd, keph, D0, pred_depth, p_prior, args, rng)
                        rec.update({"kepler_" + k: v for k, v in kb.items()})
                        detail["kepler_result"] = kout
                        detail["kepler_ephemeris"] = keph
                    except Exception as exc:
                        rec["kepler_verdict"] = "error: " + str(exc)[:200]
            # deepest dips anywhere, and where they fall against the prediction
            dips = deepest_dips(data["t"], data["d"], data["w"], D0, survey=data["survey"])
            for dp in dips:
                dp.update({"conj_" + k: v for k, v in conj_offset(dp["t"], eph).items()})
            detail["deepest_dips"] = dips
            if dips:
                rec.update({"dip1_t": dips[0]["t"], "dip1_depth": dips[0]["depth"],
                            "dip1_snr": dips[0]["snr"], "dip1_survey": dips[0]["survey"],
                            "dip1_conj_z": dips[0]["conj_z"]})
            results.append(rec)
            with open(os.path.join(pdir, f"{sid}_{key}.json"), "w") as fh:
                json.dump(ar._jsonable(detail), fh, indent=1, default=str)
            try:
                if "result" in detail:
                    ar.plot_result(os.path.join(pdir, f"{sid}_{key}_best.png"),
                                   f"Gaia DR3 {sid} ({key}) deepcheck {VERSION}", data, eph,
                                   detail["result"])
                plot_fold(os.path.join(pdir, f"{sid}_{key}_fold.png"),
                          f"Gaia DR3 {sid} ({key}) P={eph['P_mu']:.3f}+-{eph['P_sd']:.3f} d "
                          f"pred depth {pred_depth * 100:.1f}% D0={D0 * 24:.1f} h", data, eph, D0)
            except Exception as exc:
                log("plot failed", sid, exc)
            log(sid, key, rec.get("verdict"), "kepler:", rec.get("kepler_verdict", "-"),
                "dip1:", rec.get("dip1_depth"), rec.get("dip1_conj_z"))
        _write(args.out_dir, results, kepler_meta, summary, t0)
    _write(args.out_dir, results, kepler_meta, summary, t0, final=True)
    return 0


def _write(out_dir, results, kepler_meta, summary, t0, final=False):
    fields = sorted({k for x in results for k in x})
    with open(os.path.join(out_dir, "deepcheck_results.csv"), "w", newline="",
              encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        wr.writeheader()
        for x in results:
            wr.writerow(x)
    with open(os.path.join(out_dir, "kepler_meta.json"), "w") as fh:
        json.dump(kepler_meta, fh, indent=1, default=str)
    summary.update({"stars": len({x["source_id"] for x in results}),
                    "hypotheses": len(results),
                    "candidates": sum(1 for x in results if "candidate" in str(x.get("verdict"))),
                    "kepler_candidates": sum(1 for x in results
                                             if "candidate" in str(x.get("kepler_verdict"))),
                    "minutes": (time.time() - t0) / 60, "final": final})
    with open(os.path.join(out_dir, "run_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=str)
    lines = ["# deepcheck: archival test of the best Gaia-forecast targets", "",
             "Made by AI agents working for MV2 of Munim, Inc. Apache-2.0 code, CC BY 4.0 results.",
             "", "```", json.dumps(summary, indent=1, default=str), "```", "",
             "| Gaia DR3 | conj | P (d) | G | M1 | pred depth | points | best SNR | thr | epochs |"
             " R(pred) | p prior -> post | verdict | Kepler verdict | Kepler p post |"
             " deepest dip (depth, survey, z vs conj) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for x in results:
        if "best_snr" not in x:
            lines.append(f"| {x['source_id']} | {x.get('key', '')} | | | | | | | | | | | "
                         f"{x.get('verdict')} | | | |")
            continue
        dip = (f"{x.get('dip1_depth', 0) * 100:.1f}% {x.get('dip1_survey', '')} "
               f"z={x.get('dip1_conj_z', float('nan')):.1f}") if "dip1_depth" in x else ""
        kp = x.get("kepler_p_transit_post")
        lines.append(
            f"| {x['source_id']} | {x['key']}{'*' if x['rv_labelled'] else ''} | "
            f"{x['period_d']:.2f} | {x['gmag']:.2f} | {x['m1']:.2f} | "
            f"{x['pred_depth'] * 100:.1f}% | {x['n_points']} | {x['best_snr']:.2f} | "
            f"{x['thr']:.2f} | {x['best_n_epochs']} | {x['recovery_pred_depth']:.2f} | "
            f"{x['p_transit_prior']:.3f} -> {x['p_transit_post']:.3f} | {x['verdict']} | "
            f"{x.get('kepler_verdict', '-')} | {'' if kp is None else '%.3f' % kp} | {dip} |")
    with open(os.path.join(out_dir, "deepcheck_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
