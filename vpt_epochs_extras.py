# SPDX-License-Identifier: Apache-2.0
"""vpt_epochs_extras 0.1.0: helpers for amendment 2 of the Gaia epoch test.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Pre-registration: findings/2026-11-22-vpt-epochs-amendment-2.md.

  seed      fill the epoch cache from the Gaia DR3 epochs that job gaia-vpt-epochs-v2 saved
            (data/vpt-epochs-v2/epochs_g_{1,2}.csv in the repo), so no ESA service is needed.
  coverage  exploratory: are the real-transit epochs of wrong-period systems inside Gaia's
            in-transit set more often than chance? (observed vs expected overlap, z)
  tess      pre-registered: does Gaia's own G-band photometry show TIC 93622019's dip at the
            TESS ephemeris (2.1238933 d), not only at Gaia's 4:3 alias (2.83166 d)?
            Exploratory: box S/N at TESS and Gaia periods for four named candidates.
"""
import argparse
import csv
import io
import json
import math
import os
import random
import sys
import time
import urllib.request

import patch_vpt_epochs_012 as p12

ve = p12.ve

VERSION = "0.1.0"
REPO_RAW = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/"
EPOCH_FILES = ("data/vpt-epochs-v2/epochs_g_1.csv", "data/vpt-epochs-v2/epochs_g_2.csv")
V2_STARS = "data/vpt-epochs-v2/vpt_epochs_stars.csv"
GAIA_MINUS_BTJD = 2457000.0 - 2455197.5      # Gaia epoch time = BTJD + 1802.5 (TCB-TDB ignored)
MIN_CACHED = 200

# ---- pre-registered (amendment 2) ----
N_NULL = 1000
NULL_SEED = 20261122
SEES_SNR = 3.0
SEES_P = 0.01
MIN_IN = 2
EPH_SIGMA_FRAC = 0.25
LOCAL_W = 5e-4          # exploratory local period scan: P (1 +- LOCAL_W)
LOCAL_N = 2001

CANDIDATES = [
    # graded: refined TESS ephemeris from job tic93622019-pixel-v1 (5 sector epochs)
    {"name": "TIC 93622019", "sid": "5345417757181174144", "P": 2.123893332667055,
     "sigma_P": 3.044815104421753e-06, "T0_btjd": 3706.0868496452117,
     "sigma_T0": 0.0006764471524484674, "dur": 0.125, "graded": True},
    # exploratory only (period from the period-free TESS search, no epoch used)
    {"name": "TIC 4638108", "sid": "5431056347037926784", "P": 2.20828, "graded": False},
    {"name": "TIC 44997521", "sid": "5432318139709900160", "P": 3.54941, "graded": False},
    {"name": "TIC 400170926 (HD 250735)", "sid": "3450611154067089408", "P": 5.895742,
     "graded": False},
]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ------------------------------------------------------------------ seed
def split_epochs_text(text):
    """'source_id,time,flux,flux_error,rejected' CSV text -> {sid: [[time, flux, err, rej]]}."""
    out = {}
    for r in csv.DictReader(io.StringIO(text)):
        sid = str(r.get("source_id") or "").strip()
        if not sid:
            continue
        out.setdefault(sid, []).append([r.get("time", ""), r.get("flux", ""),
                                        r.get("flux_error", ""), r.get("rejected", "")])
    return out


def write_cache(cache_dir, groups):
    os.makedirs(cache_dir, exist_ok=True)
    for sid, rows in groups.items():
        with open(os.path.join(cache_dir, sid + ".csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["time", "flux", "flux_error", "rejected"])
            w.writerows(rows)
    return len(groups)


def n_cached(cache_dir):
    if not os.path.isdir(cache_dir):
        return 0
    return sum(1 for n in os.listdir(cache_dir) if n.endswith(".csv") and n[:-4].isdigit())


def fetch(url, deadline_s, wait_s=120):
    """GET with waiting: the repo files are committed right after the run that filed this job."""
    start = time.time()
    while True:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ve.UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as exc:
            if time.time() - start > deadline_s:
                raise
            log("waiting for", url, repr(exc)[:120])
            time.sleep(wait_s)


def cmd_seed(a):
    if a.v2_stars:
        try:
            data = fetch(REPO_RAW + V2_STARS, a.deadline_minutes * 60)
            with open(a.v2_stars, "wb") as fh:
                fh.write(data)
            log("v2 stars", len(data), "bytes")
        except Exception as exc:
            log("v2 stars unavailable", repr(exc)[:200])
    have = n_cached(a.cache_dir)
    if have >= MIN_CACHED:
        log("cache already holds", have, "stars; not seeding")
        return 0
    groups = {}
    try:
        for f in EPOCH_FILES:
            text = fetch(REPO_RAW + f, a.deadline_minutes * 60).decode("utf-8", "replace")
            for sid, rows in split_epochs_text(text).items():
                groups.setdefault(sid, []).extend(rows)
    except Exception as exc:
        log("seed failed (the module will use ESA's CDN instead):", repr(exc)[:200])
        return 0
    n = write_cache(a.cache_dir, groups)
    log("seeded", n, "stars,", sum(len(v) for v in groups.values()), "epochs")
    return 0


# ------------------------------------------------------------------ coverage
def _i(x):
    v = ve.fval({"v": x}, "v")
    return int(v) if math.isfinite(v) else None


def coverage_stats(rows):
    """Observed vs chance overlap of the real-transit set S_t with Gaia's set S_g.
    Chance: each of the n_t real-transit epochs falls in S_g with probability q = n_g / N."""
    out = {}
    for group, cat in (("wrong_period", "KNOWN_SYSTEM_OTHER_P"), ("controls", "KNOWN_PLANET")):
        obs = exp = var = e_any = 0.0
        k_any = n = 0
        for r in rows:
            if r.get("category") != cat or r.get("why_label") not in ("ALIAS", "PARTIAL",
                                                                      "UNRELATED"):
                continue
            nt, ng, nb, N = (_i(r.get(k)) for k in ("n_t", "n_g", "n_both", "n_epochs"))
            if None in (nt, ng, nb, N) or N <= 0:
                continue
            q = min(1.0, ng / N)
            n += 1
            obs += nb
            exp += nt * q
            var += nt * q * (1 - q)
            k_any += 1 if nb > 0 else 0
            e_any += 1 - (1 - q) ** nt
        z = (obs - exp) / math.sqrt(var) if var > 0 else float("nan")
        out[group] = {"n_stars": n, "overlap_observed": obs, "overlap_expected": exp,
                      "ratio": obs / exp if exp > 0 else float("nan"), "z": z,
                      "p_one_sided": 0.5 * math.erfc(z / math.sqrt(2)) if math.isfinite(z)
                      else float("nan"),
                      "stars_with_overlap": k_any, "stars_with_overlap_expected": e_any}
    return out


def cmd_coverage(a):
    res = {"version": VERSION}
    for path, lab in zip(a.stars, a.labels):
        if not os.path.exists(path):
            res[lab] = {"error": "missing " + path}
            continue
        res[lab] = coverage_stats(ve.read_csv(path))
    with open(a.out, "w") as fh:
        json.dump(ve.clean_json(res), fh, indent=1)
    print(json.dumps(ve.clean_json(res)))
    return 0


# ------------------------------------------------------------------ tess
def fixed_ephemeris_test(t, fn, sd, P, T0g, dur, sigma_P=0.0, sigma_T0=0.0,
                         n_null=N_NULL, seed=NULL_SEED):
    """Dip S/N in Gaia epochs inside the TESS-predicted windows (|dt| <= dur/2), with an
    empirical p from n_null random phase shifts (shift uniform in [dur, P - dur])."""
    res = {"n_epochs": len(t)}
    if len(t) < ve.MIN_EPOCHS:
        res["label"] = "UNTESTABLE"
        res["reason"] = "few epochs"
        return res
    t_mid = 0.5 * (t[0] + t[-1])
    ncyc = (t_mid - T0g) / P
    sig = math.sqrt((ncyc * sigma_P) ** 2 + sigma_T0 ** 2)
    res["timing_sigma_d"] = sig
    idx = ve.window_set(t, T0g, P, dur / 2.0)
    res["n_in"] = len(idx)
    if len(idx) < MIN_IN or sig > EPH_SIGMA_FRAC * dur:
        res["label"] = "UNTESTABLE"
        res["reason"] = "few in-window epochs" if len(idx) < MIN_IN else "ephemeris too imprecise"
        return res
    depth, snr = ve.set_depth_snr(fn, idx, sd)
    rng = random.Random(seed)
    n_valid = n_ge = 0
    for _ in range(n_null):
        off = rng.uniform(dur, P - dur)
        ii = ve.window_set(t, T0g + off, P, dur / 2.0)
        if not ii:
            continue
        _, s = ve.set_depth_snr(fn, ii, sd)
        if not math.isfinite(s):
            continue
        n_valid += 1
        n_ge += 1 if s >= snr else 0
    p = (1 + n_ge) / (1 + n_valid)
    res.update({"depth": depth, "snr": snr, "n_null": n_valid, "n_null_ge": n_ge, "p_emp": p,
                "in_window_times": [t[i] for i in idx]})
    res["label"] = ("GAIA_SEES_TESS_EPHEMERIS" if (math.isfinite(snr) and snr >= SEES_SNR
                                                   and p <= SEES_P) else "NOT_SEEN")
    return res


def box_fields(t, fn, P_tess, P_gaia, box):
    """Exploratory (numpy): phase-free box S/N at the TESS and Gaia periods and the best
    period in a +-LOCAL_W scan around the TESS period."""
    out = {"box_d": box}
    try:
        import numpy as np
        tt = np.asarray(t, float)
        ff = np.asarray(fn, float)
        out["snr_box_tess_P"] = float(ve.box_snr(tt, ff, [1.0 / P_tess], box)[0])
        if P_gaia and math.isfinite(P_gaia) and P_gaia > 0:
            out["snr_box_gaia_P"] = float(ve.box_snr(tt, ff, [1.0 / P_gaia], box)[0])
        fr = np.linspace(1.0 / (P_tess * (1 + LOCAL_W)), 1.0 / (P_tess * (1 - LOCAL_W)), LOCAL_N)
        s = ve.box_snr(tt, ff, fr, box)
        i = int(np.argmax(s))
        out.update({"local_best_P": float(1.0 / fr[i]), "local_best_snr": float(s[i])})
    except Exception as exc:
        out["error"] = repr(exc)[:200]
    return out


def cmd_tess(a):
    gaia = {}
    if a.stars and os.path.exists(a.stars):
        for r in ve.read_csv(a.stars):
            gaia[r.get("source_id", "")] = r
    res = {"version": VERSION, "candidates": []}
    for c in CANDIDATES:
        row = {"name": c["name"], "source_id": c["sid"], "P_tess": c["P"], "graded": c["graded"]}
        g = gaia.get(c["sid"], {})
        P_gaia = ve.fval(g, "P_gaia")
        dur_gaia = ve.fval(g, "dur_gaia")
        row.update({"P_gaia": P_gaia, "dur_gaia": dur_gaia})
        path = os.path.join(a.cache_dir, c["sid"] + ".csv")
        if not os.path.exists(path):
            row["label"] = "UNTESTABLE"
            row["reason"] = "no epochs"
            res["candidates"].append(row)
            continue
        t, fl, _, nrej = ve.clean_epochs(ve.load_epochs(path))
        if len(t) < ve.MIN_EPOCHS:
            row["label"] = "UNTESTABLE"
            row["reason"] = "few epochs"
            res["candidates"].append(row)
            continue
        med = ve.median(fl)
        fn = [x / med for x in fl]
        sd = ve.robust_sd(fn)
        row.update({"n_epochs": len(t), "n_rejected": nrej, "sd_flux": sd})
        if c.get("T0_btjd") is not None:
            T0g = c["T0_btjd"] + GAIA_MINUS_BTJD
            row["T0_gaia_time"] = T0g
            row["fixed"] = fixed_ephemeris_test(t, fn, sd, c["P"], T0g, c["dur"],
                                                c.get("sigma_P", 0.0), c.get("sigma_T0", 0.0))
            row["label"] = row["fixed"]["label"]
            box = ve.clip(c["dur"], ve.BOX_MIN, ve.BOX_MAX)
        else:
            row["label"] = "EXPLORATORY_ONLY"
            box = ve.clip(dur_gaia if math.isfinite(dur_gaia) else 0.1, ve.BOX_MIN, ve.BOX_MAX)
        row["box"] = box_fields(t, fn, c["P"], P_gaia, box)
        res["candidates"].append(row)
        log(c["name"], row["label"], json.dumps(ve.clean_json(row.get("fixed", {})))[:300])
    with open(a.out, "w") as fh:
        json.dump(ve.clean_json(res), fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="vpt_epochs amendment-2 helpers")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("seed")
    s.add_argument("--cache-dir", required=True)
    s.add_argument("--v2-stars", default="")
    s.add_argument("--deadline-minutes", type=float, default=90.0)
    c = sub.add_parser("coverage")
    c.add_argument("--stars", nargs="+", required=True)
    c.add_argument("--labels", nargs="+", required=True)
    c.add_argument("--out", required=True)
    t = sub.add_parser("tess")
    t.add_argument("--cache-dir", required=True)
    t.add_argument("--stars", default="")
    t.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "seed":
        return cmd_seed(a)
    if a.cmd == "coverage":
        return cmd_coverage(a)
    if a.cmd == "tess":
        return cmd_tess(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
