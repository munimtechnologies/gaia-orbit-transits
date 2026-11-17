# SPDX-License-Identifier: Apache-2.0
"""Search TESS for eclipses/transits of companions on Gaia DR3 astrometric orbits.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0.

Steps
 1. Download every Gaia DR3 nss_two_body_orbit solution that has Thiele-Innes
    constants (G < gmax) from the Gaia archive TAP service (cached in --data-dir).
 2. Keep near edge-on orbits (|cos i| < cosi_max), and for each run a Monte Carlo
    over the catalogue errors: probability that the companion can eclipse/transit,
    predicted conjunction times, rough masses (dark-companion assumption).
 3. Rank and, for the top targets, find the TIC ID, download TESS light curves
    (SPOC 2-min, TESS-SPOC, QLP), run a single-event dip search, and score each
    dip against the predicted conjunction windows.
 4. Write CSVs, plots of the best events and a report.
"""
import argparse
import csv
import io
import json
import os
import sys
import time
import traceback

import numpy as np

import dipsearch as ds
import gaia_orbits as go

TAP = "https://gea.esac.esa.int/tap-server/tap"

NSS_QUERY = """
SELECT n.source_id, n.nss_solution_type, n.period, n.period_error,
 n.t_periastron, n.t_periastron_error, n.eccentricity, n.eccentricity_error,
 n.a_thiele_innes, n.a_thiele_innes_error, n.b_thiele_innes, n.b_thiele_innes_error,
 n.f_thiele_innes, n.f_thiele_innes_error, n.g_thiele_innes, n.g_thiele_innes_error,
 n.parallax AS nss_parallax, n.parallax_error AS nss_parallax_error,
 n.significance, n.goodness_of_fit,
 g.ra, g.dec, g.phot_g_mean_mag, g.bp_rp, g.ruwe
FROM {schema}.nss_two_body_orbit AS n
JOIN {schema}.gaia_source AS g ON g.source_id = n.source_id
WHERE n.a_thiele_innes IS NOT NULL AND g.phot_g_mean_mag < {gmax}
"""

EB_QUERY = """
SELECT v.source_id FROM {schema}.vari_eclipsing_binary AS v
JOIN {schema}.nss_two_body_orbit AS n ON n.source_id = v.source_id
WHERE n.a_thiele_innes IS NOT NULL
"""


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- Gaia TAP
def tap_async(query, timeout_s=3600):
    import requests
    r = requests.post(TAP + "/async", data={"REQUEST": "doQuery", "LANG": "ADQL",
                                            "FORMAT": "csv", "PHASE": "RUN",
                                            "QUERY": query},
                      allow_redirects=False, timeout=120)
    loc = r.headers.get("Location")
    if loc and loc.startswith("/"):
        loc = "https://gea.esac.esa.int" + loc
    if not loc:
        raise RuntimeError(f"TAP async: no job location (HTTP {r.status_code}): {r.text[:500]}")
    t0 = time.time()
    while True:
        ph = requests.get(loc + "/phase", timeout=60).text.strip()
        if ph == "PENDING":
            requests.post(loc + "/phase", data={"PHASE": "RUN"}, timeout=60)
        elif ph == "COMPLETED":
            break
        elif ph in ("ERROR", "ABORTED"):
            err = requests.get(loc + "/error", timeout=60).text
            raise RuntimeError(f"TAP job {ph}: {err[:1000]}")
        if time.time() - t0 > timeout_s:
            raise RuntimeError("TAP job timed out")
        time.sleep(5)
    res = requests.get(loc + "/results/result", timeout=600)
    res.raise_for_status()
    return res.text


def tap_query(query):
    try:
        return tap_async(query)
    except Exception as exc:  # fall back to astroquery
        log("raw TAP failed:", exc, "- trying astroquery")
        from astroquery.gaia import Gaia
        Gaia.ROW_LIMIT = -1
        tbl = Gaia.launch_job_async(query).get_results()
        buf = io.StringIO()
        tbl.write(buf, format="ascii.csv")
        return buf.getvalue()


def read_csv_text(text):
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        d = {}
        for k, v in r.items():
            k = k.strip().lower()
            if k in ("source_id",):
                d[k] = int(float(v)) if "e" in v.lower() else int(v)
            elif k in ("nss_solution_type",):
                d[k] = v.strip().strip('"')
            else:
                try:
                    d[k] = float(v) if v not in ("", "null", "--") else np.nan
                except ValueError:
                    d[k] = v
        out.append(d)
    return out


def cached_query(path, query):
    if os.path.exists(path) and os.path.getsize(path) > 100:
        log("cache hit", path)
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    log("querying Gaia archive ...")
    text = tap_query(query)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


# ---------------------------------------------------------------- ranking
def prior_for_row(row, n, rng):
    plx = row.get("nss_parallax", np.nan)
    if not np.isfinite(plx) or plx <= 0:
        return None
    absg = row["phot_g_mean_mag"] + 5 * np.log10(plx / 100.0)
    m1, r1 = go.ms_mass_radius(absg)
    s = go.sample_orbit(row, n, rng)
    el = go.thiele_innes_to_elements(row["a_thiele_innes"], row["b_thiele_innes"],
                                     row["f_thiele_innes"], row["g_thiele_innes"])
    m2 = float(go.companion_mass_dark(float(el["a"]), plx, row["period"], m1))
    r2 = float(go.companion_radius(m2))
    g = go.eclipse_geometry(s, float(m1), float(r1), m2, r2)
    p_ecl = float(np.mean(g["ecl1"] | g["ecl2"]))
    t1c, t2c, _, _ = go.conjunction_times(row["t_periastron"] + go.GAIA_REF_BTJD,
                                          row["period"], row.get("eccentricity") if np.isfinite(row.get("eccentricity", np.nan)) else 0.0,
                                          el["omega"])
    return {
        "abs_g": float(absg), "m1": float(m1), "r1": float(r1), "m2_dark": m2,
        "r2": r2, "class": go.classify(m2), "cosi": float(el["cosi"]),
        "inc_deg": float(el["inc_deg"]),
        "cosi_sd": float(np.std(s["cosi"])), "a0_mas": float(el["a"]),
        "p_ecl": p_ecl,
        "dur1_h": float(np.median(g["dur_central1"]) * 24),
        "dur2_h": float(np.median(g["dur_central2"]) * 24),
        "t_conj1_btjd": float(t1c), "t_conj2_btjd": float(t2c),
    }, s, g


# ---------------------------------------------------------------- TESS
def find_tic(ra, dec, gmag, source_id):
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astroquery.mast import Catalogs
    for attempt in range(3):
        try:
            t = Catalogs.query_region(SkyCoord(ra, dec, unit="deg"), radius=12 * u.arcsec,
                                      catalog="TIC")
            break
        except Exception as exc:
            log("TIC query retry", attempt, exc)
            time.sleep(5 * (attempt + 1))
    else:
        return None
    if len(t) == 0:
        return None
    best, best_score, gaia_match = None, 1e9, False
    for r in t:
        gid = str(r["GAIA"]).strip() if "GAIA" in t.colnames else ""
        if gid and gid == str(source_id):
            return {"tic": int(r["ID"]), "tmag": float(r["Tmag"]), "ra": float(r["ra"]),
                    "dec": float(r["dec"]), "gaia_match": True,
                    "dist_arcsec": float(r["dstArcSec"])}
        try:
            tm = float(r["Tmag"])
            tm = tm if np.isfinite(tm) else 99.0
        except Exception:
            tm = 99.0
        score = float(r["dstArcSec"]) + 3 * abs(tm - (gmag - 0.5))
        if score < best_score:
            best, best_score = r, score
    if best is None:
        return None
    return {"tic": int(best["ID"]), "tmag": float(best["Tmag"]), "ra": float(best["ra"]),
            "dec": float(best["dec"]), "gaia_match": gaia_match,
            "dist_arcsec": float(best["dstArcSec"])}


AUTHOR_RANK = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}


def _arr(x):
    """Plain float ndarray with NaN where masked (numpy or astropy masked arrays)."""
    x = getattr(x, "value", x)
    if hasattr(x, "unmasked"):
        d = np.array(x.unmasked, dtype=float)
        d[np.asarray(x.mask, dtype=bool)] = np.nan
        return d
    if np.ma.isMaskedArray(x):
        return np.ma.filled(x.astype(float), np.nan)
    return np.asarray(x, dtype=float)


def fetch_tess(tic, ra, dec, data_dir, max_lcs):
    import astropy.units as u
    import lightkurve as lk
    from astropy.coordinates import SkyCoord
    sr = None
    for attempt in range(3):
        try:
            sr = lk.search_lightcurve(SkyCoord(ra, dec, unit="deg"), radius=3 * u.arcsec,
                                      mission="TESS")
            break
        except Exception as exc:
            log("search retry", attempt, exc)
            time.sleep(5 * (attempt + 1))
    if sr is None or len(sr) == 0:
        return [], []
    tab = sr.table
    pick = {}
    for i in range(len(sr)):
        author = str(tab["author"][i])
        if author not in AUTHOR_RANK:
            continue
        if "target_name" in tab.colnames:
            tn = str(tab["target_name"][i]).strip().lstrip("0")
            if tn and tn.isdigit() and tn != str(tic):
                continue
        exptime = float(tab["exptime"][i]) if "exptime" in tab.colnames else 0
        if author == "SPOC" and exptime < 100:
            continue  # skip 20-s data, use the 120-s version
        sector = None
        for key in ("sequence_number", "sector"):
            if key in tab.colnames:
                try:
                    sector = int(tab[key][i])
                    break
                except Exception:
                    pass
        if sector is None:
            digits = "".join(ch for ch in str(tab["mission"][i]) if ch.isdigit())
            sector = int(digits) if digits else -i
        rank = AUTHOR_RANK[author]
        if sector not in pick or rank < pick[sector][0]:
            pick[sector] = (rank, i, author)
    sectors = sorted(pick)[:max_lcs]
    times, fluxes, meta = [], [], []
    for sec in sectors:
        rank, i, author = pick[sec]
        try:
            lc = sr[i].download(download_dir=data_dir, quality_bitmask="default")
            if lc is None:
                continue
            t = _arr(lc.time.value)
            f = _arr(lc.flux)
            ok = np.isfinite(t) & np.isfinite(f)
            if ok.sum() < 100:
                continue
            t, f = t[ok], f[ok]
            f = f / np.nanmedian(f)
            # clip strong upward outliers only (flares, cosmic rays)
            sd = ds.robust_sd(f)
            keep = f < 1 + 6 * sd
            times.append(t[keep])
            fluxes.append(f[keep])
            meta.append({"sector": int(sec), "author": author, "n": int(keep.sum())})
        except Exception as exc:
            log("download failed", tic, sec, author, exc)
    return list(zip(times, fluxes)), meta


# ---------------------------------------------------------------- plotting
def plot_event(path, title, binned, raw, ev, windows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(10, 7))
    bt, bf = binned["t"], binned["f"]
    tc = ev["t_center"]
    sel = (bt > ev["seg_start"] - 1) & (bt < ev["seg_end"] + 1)
    ax[0].plot(bt[sel], bf[sel], ".", ms=2, color="k")
    for (lo, hi, lab) in windows:
        if hi > bt[sel].min() - 5 and lo < bt[sel].max() + 5:
            ax[0].axvspan(lo, hi, color="orange" if lab == "c1" else "cyan", alpha=0.3)
    ax[0].axvline(tc, color="r", lw=0.8)
    ax[0].set_title(title, fontsize=9)
    ax[0].set_ylabel("binned flux (30 min)")
    half = max(3 * ev["duration_h"] / 24, 1.0)
    rt, rf = raw
    m = np.abs(rt - tc) < half
    ax[1].plot(rt[m], rf[m], ".", ms=1, color="0.6")
    mb = np.abs(bt - tc) < half
    ax[1].plot(bt[mb], bf[mb], "o", ms=3, color="k")
    ax[1].axvspan(tc - ev["duration_h"] / 48, tc + ev["duration_h"] / 48, color="r", alpha=0.15)
    ax[1].set_xlabel("BTJD")
    ax[1].set_ylabel("flux")
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


# ---------------------------------------------------------------- main
def write_csv(path, rows, fields=None):
    if not rows:
        return
    fields = fields or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--gmax", type=float, default=14.5)
    ap.add_argument("--cosi-max", type=float, default=0.2)
    ap.add_argument("--mc", type=int, default=600)
    ap.add_argument("--max-targets", type=int, default=400)
    ap.add_argument("--min-p-ecl", type=float, default=0.002)
    ap.add_argument("--max-lcs", type=int, default=40)
    ap.add_argument("--snr", type=float, default=7.0)
    ap.add_argument("--time-budget-min", type=float, default=200)
    ap.add_argument("--plots", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20261117)
    ap.add_argument("--schema", default="gaiadr3",
                    help="Gaia archive schema (gaiadr3; gaiadr4 after 2026-12-02)")
    ap.add_argument("--ref-btjd", type=float, default=None,
                    help="BTJD of the t_periastron reference epoch "
                         "(default: 389.0 = J2016.0 for DR3, 936.875 = J2017.5 for DR4)")
    args = ap.parse_args(argv)
    if args.ref_btjd is None:
        args.ref_btjd = 936.875 if args.schema.lower().endswith("dr4") else 389.0
    go.GAIA_REF_BTJD = args.ref_btjd
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(os.path.join(args.out_dir, "plots"), exist_ok=True)
    lk_dir = os.path.join(args.data_dir, "lk")
    os.makedirs(lk_dir, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    summary = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "args": vars(args)}

    text = cached_query(os.path.join(args.data_dir, f"{args.schema}_nss_ti_g{args.gmax:g}.csv"),
                        NSS_QUERY.format(gmax=args.gmax, schema=args.schema))
    rows = read_csv_text(text)
    log("NSS rows with Thiele-Innes:", len(rows))
    try:
        ebtext = cached_query(os.path.join(args.data_dir, f"{args.schema}_nss_ti_vari_eb.csv"),
                              EB_QUERY.format(schema=args.schema))
        gaia_eb = {r["source_id"] for r in read_csv_text(ebtext)}
    except Exception as exc:
        log("EB query failed", exc)
        gaia_eb = set()
    summary["nss_rows"] = len(rows)
    summary["gaia_eb_overlap"] = len(gaia_eb)
    types = {}
    for r in rows:
        types[r["nss_solution_type"]] = types.get(r["nss_solution_type"], 0) + 1
    summary["solution_types"] = types

    # central cos i for all, then MC for the near-edge-on subset
    priors, samples, by_id = [], {}, {}
    n_edge = 0

    def src_rng(sid):
        return np.random.default_rng([args.seed, int(sid) % (2 ** 32), int(sid) // (2 ** 32)])

    for r in rows:
        el = go.thiele_innes_to_elements(r["a_thiele_innes"], r["b_thiele_innes"],
                                         r["f_thiele_innes"], r["g_thiele_innes"])
        if not np.isfinite(float(el["cosi"])) or abs(float(el["cosi"])) >= args.cosi_max:
            continue
        if not np.isfinite(r.get("period", np.nan)) or not np.isfinite(r.get("t_periastron", np.nan)):
            continue
        n_edge += 1
        try:
            res = prior_for_row(r, args.mc, src_rng(r["source_id"]))
        except Exception as exc:
            log("prior failed", r.get("source_id"), exc)
            continue
        if res is None:
            continue
        pr = res[0]
        by_id[r["source_id"]] = r
        rec = {"source_id": r["source_id"], "solution_type": r["nss_solution_type"],
               "ra": r["ra"], "dec": r["dec"], "gmag": r["phot_g_mean_mag"],
               "bp_rp": r.get("bp_rp"), "parallax": r["nss_parallax"],
               "period_d": r["period"], "period_err": r.get("period_error"),
               "ecc": r.get("eccentricity"), "significance": r.get("significance"),
               "gaia_eb": r["source_id"] in gaia_eb}
        rec.update(pr)
        priors.append(rec)
    summary["near_edge_on"] = n_edge
    rows = None
    text = None
    log("near edge-on:", n_edge, "with priors:", len(priors))
    priors.sort(key=lambda p: -p["p_ecl"])
    write_csv(os.path.join(args.out_dir, "gaia_edge_on_priors.csv"), priors)

    # choose targets: substellar candidates first, then by eclipse probability
    sub = [p for p in priors if p["class"] in ("planet", "brown-dwarf") and p["p_ecl"] >= args.min_p_ecl]
    star = [p for p in priors if p["class"] == "star" and p["p_ecl"] >= args.min_p_ecl]
    targets = (sub + star)[:args.max_targets]
    summary["n_substellar_candidates"] = len(sub)
    summary["n_targets"] = len(targets)
    log("targets:", len(targets), "substellar:", len(sub))
    # same seeds as the ranking pass -> identical Monte Carlo samples
    for p in targets:
        samples[p["source_id"]] = prior_for_row(by_id[p["source_id"]], args.mc,
                                                src_rng(p["source_id"]))[1]
    by_id.clear()

    # predicted conjunction windows for the near-edge-on substellar candidates (follow-up list)
    write_csv(os.path.join(args.out_dir, "substellar_edge_on_candidates.csv"), sub)

    per_target, all_events = [], []
    store = {}
    expected = 0.0
    for ti, p in enumerate(targets):
        if (time.time() - t_start) / 60 > args.time_budget_min:
            log("time budget reached at target", ti)
            summary["stopped_at_target"] = ti
            break
        sid = p["source_id"]
        rec = {"source_id": sid, "class": p["class"], "p_ecl": p["p_ecl"],
               "period_d": p["period_d"], "gmag": p["gmag"], "m2_dark": p["m2_dark"],
               "gaia_eb": p["gaia_eb"], "tic": "", "n_sectors": 0, "cov1": 0.0, "cov2": 0.0,
               "best_snr": 0.0, "best_t": "", "best_bf": "", "status": ""}
        try:
            tic = find_tic(p["ra"], p["dec"], p["gmag"], sid)
            if tic is None:
                rec["status"] = "no-tic"
                per_target.append(rec)
                continue
            rec["tic"] = tic["tic"]
            rec["tic_gaia_match"] = tic["gaia_match"]
            lcs, meta = fetch_tess(tic["tic"], tic["ra"], tic["dec"], lk_dir, args.max_lcs)
            rec["n_sectors"] = len(meta)
            rec["sectors"] = " ".join(f"{m['sector']}:{m['author']}" for m in meta)
            if not lcs:
                rec["status"] = "no-tess"
                per_target.append(rec)
                continue
            t = np.concatenate([x[0] for x in lcs])
            f = np.concatenate([x[1] for x in lcs])
            o = np.argsort(t)
            t, f = t[o], f[o]
            events, binned = ds.search(t, f, snr_min=args.snr)
            s = samples[sid]
            hw1 = max(p["dur1_h"] / 48.0, 1 / 48)
            hw2 = max(p["dur2_h"] / 48.0, 1 / 48)
            rec["cov1"] = go.coverage_fraction(s, "t1", binned["t"], hw1)
            rec["cov2"] = go.coverage_fraction(s, "t2", binned["t"], hw2)
            expected += p["p_ecl"] * max(rec["cov1"], rec["cov2"])
            for e in events:
                best = None
                for key, dkey in (("t1", "dur1_h"), ("t2", "dur2_h")):
                    wm = go.window_match(s, key, e["t_center"],
                                         max(e["duration_h"], p[dkey]) / 24.0)
                    if best is None or wm["bf"] > best["bf"]:
                        best = dict(wm, conj=key)
                e.update({"source_id": sid, "tic": tic["tic"], "class": p["class"],
                          "period_d": p["period_d"], "p_ecl": p["p_ecl"],
                          "gmag": p["gmag"], "m2_dark": p["m2_dark"], "gaia_eb": p["gaia_eb"],
                          "conj": best["conj"], "bf": best["bf"],
                          "frac_in_window": best["frac_in_window"],
                          "offset_d": best["median_offset_d"],
                          "offset_sd_d": best["offset_sd_d"],
                          "pred_dur_h": p["dur1_h"] if best["conj"] == "t1" else p["dur2_h"]})
                all_events.append(e)
            if events:
                top = max(events, key=lambda e: e["snr"])
                rec["best_snr"], rec["best_t"] = top["snr"], top["t_center"]
                rec["best_bf"] = max(e["bf"] for e in events)
            rec["n_events"] = len(events)
            rec["status"] = "ok"
            # keep memory bounded: binned data plus raw points near the top events only
            if events:
                near = np.zeros(t.size, dtype=bool)
                for e in sorted(events, key=lambda e: -e["snr"])[:5]:
                    near |= np.abs(t - e["t_center"]) < 3.0
                store[sid] = ({"t": binned["t"], "f": binned["f"]}, (t[near], f[near]), p)
        except Exception as exc:
            rec["status"] = "error: " + str(exc)[:200]
            log("target failed", sid, exc)
            traceback.print_exc()
        per_target.append(rec)
        if ti % 10 == 0:
            log(f"[{ti + 1}/{len(targets)}] {sid} {rec['status']} sectors={rec['n_sectors']} "
                f"events={rec.get('n_events', 0)} elapsed={(time.time() - t_start) / 60:.1f} min")
            write_csv(os.path.join(args.out_dir, "tess_targets_partial.csv"), per_target,
                      sorted({k for r in per_target for k in r}))

    # shared-time systematics flag: events in several targets at the same time
    times = np.array([e["t_center"] for e in all_events]) if all_events else np.empty(0)
    for e in all_events:
        e["n_other_targets_same_time"] = int(np.sum(np.abs(times - e["t_center"]) < 0.25)) - 1
        score = min(e["snr"], 50) * (1 + np.log10(max(e["bf"], 1e-3)) if e["bf"] > 1 else 1)
        if e["near_edge"]:
            score *= 0.5
        if e["n_other_targets_same_time"] >= 2:
            score *= 0.3
        e["score"] = float(score)
    all_events.sort(key=lambda e: -e["score"])

    fields_t = sorted({k for r in per_target for k in r})
    write_csv(os.path.join(args.out_dir, "tess_targets.csv"), per_target, fields_t)
    ev_fields = ["score", "source_id", "tic", "class", "gmag", "period_d", "m2_dark", "p_ecl",
                 "gaia_eb", "t_center", "duration_h", "pred_dur_h", "depth_ppm", "snr",
                 "box_noise_ppm", "near_edge", "n_other_targets_same_time", "conj", "bf",
                 "frac_in_window", "offset_d", "offset_sd_d", "seg_start", "seg_end"]
    write_csv(os.path.join(args.out_dir, "events.csv"), all_events, ev_fields)

    # plots for the best-scoring event per target
    done = set()
    n_plot = 0
    for e in all_events:
        if n_plot >= args.plots:
            break
        sid = e["source_id"]
        if sid in done or sid not in store:
            continue
        done.add(sid)
        binned, raw, p = store[sid]
        s = samples[sid]
        windows = []
        for key in ("t1", "t2"):
            off = go.phase_offsets(s, key, e["t_center"])
            c = e["t_center"] - np.median(off)
            sd = max(1.4826 * np.median(np.abs(off - np.median(off))), 0.05)
            for k in range(-40, 41):
                lo, hi = c + k * p["period_d"] - sd, c + k * p["period_d"] + sd
                windows.append((lo, hi, "c1" if key == "t1" else "c2"))
        title = (f"Gaia DR3 {sid}  TIC {e['tic']}  P={p['period_d']:.2f} d  class={p['class']} "
                 f"m2(dark)={p['m2_dark']:.3f} Msun  p_ecl={p['p_ecl']:.2f}\n"
                 f"event t={e['t_center']:.3f} dur={e['duration_h']:.0f} h depth={e['depth_ppm']:.0f} ppm "
                 f"snr={e['snr']:.1f} conj={e['conj']} BF={e['bf']:.1f} offset={e['offset_d']:.2f}+-{e['offset_sd_d']:.2f} d")
        try:
            plot_event(os.path.join(args.out_dir, "plots", f"{n_plot:02d}_{sid}.png"),
                       title, binned, raw, e, windows)
            n_plot += 1
        except Exception as exc:
            log("plot failed", sid, exc)

    ok = [r for r in per_target if r["status"] == "ok"]
    summary.update({
        "targets_processed": len(per_target),
        "targets_with_tess": len(ok),
        "events_total": len(all_events),
        "targets_with_events": len({e["source_id"] for e in all_events}),
        "events_bf_gt_10": sum(1 for e in all_events if e["bf"] > 10),
        "expected_eclipses_covered": expected,
        "covered_either_conj_gt_0.5": sum(1 for r in ok if max(r["cov1"], r["cov2"]) > 0.5),
        "minutes": (time.time() - t_start) / 60,
    })
    with open(os.path.join(args.out_dir, "run_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=str)

    lines = ["# Gaia DR3 astrometric orbits x TESS: eclipse search", "",
             "Made by AI agents working for MV2 of Munim, Inc. Apache-2.0 code, CC BY 4.0 results.", "",
             "```", json.dumps(summary, indent=1, default=str), "```", "",
             "## Top events (score = SNR x conjunction-window match, penalised for edges and shared times)", "",
             "| score | Gaia DR3 | TIC | class | P (d) | t (BTJD) | dur (h) | depth (ppm) | SNR | conj | BF | offset (d) | Gaia EB |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in all_events[:60]:
        lines.append(f"| {e['score']:.1f} | {e['source_id']} | {e['tic']} | {e['class']} | {e['period_d']:.2f} | "
                     f"{e['t_center']:.3f} | {e['duration_h']:.0f} | {e['depth_ppm']:.0f} | {e['snr']:.1f} | "
                     f"{e['conj']} | {e['bf']:.1f} | {e['offset_d']:.2f}+-{e['offset_sd_d']:.2f} | {e['gaia_eb']} |")
    with open(os.path.join(args.out_dir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log("done", json.dumps(summary, default=str)[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
