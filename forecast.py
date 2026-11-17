# SPDX-License-Identifier: Apache-2.0
"""Forecast: which Gaia-predicted transits will TESS (Years 9-10) or the ground see?

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0.

For each Gaia astrometric orbit (DR3 now, DR4 from 2026-12-02) this writes, before
any of the data exist, a falsifiable list of
  * every future TESS sector (108-134, to late 2028) in which the star falls on a
    camera CCD (tess-point >= 0.9.5), with the Monte Carlo probability that a
    transit-conjunction time falls inside that sector, and the expected number of
    observed transits p_geom x p_in_sector;
  * every transit-conjunction window from --t-from to --t-to (centre and robust
    1-sigma), for ground-based campaigns.

Which conjunction is the transit: the RV-labelled one for AstroSpectroSB1 orbits
whose astrometric and spectroscopic omegas agree (gaia_orbits.transit_label);
otherwise both conjunctions, each with weight 0.5.

Sector dates. Year 9 (S108-121): start/end dates published by the TESS Science
Center (tess.mit.edu/tess-year-9-observations, "provisional"). Year 10 (S122-134):
only mid-times are public (tess-point 0.9.5 table); boundaries are the midpoints
between consecutive mid-times and are flagged approx=True. Data gaps at perigee
(~1 d per 13.7-d orbit, ~7%) are not removed.

0.4.1: the Gaia query is split into source_id ranges (run_search.chunked_query),
because anonymous Gaia archive queries are limited to 60 s and 50,000 rows.
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import time

import numpy as np

import gaia_orbits as go

VERSION = "0.4.1"
JD_BTJD = 2457000.0

# Year 9 sector dates (UTC calendar days) from tess.mit.edu, fetched 2026-11-17
YEAR9 = {
    108: ("2026-09-07", "2026-10-05"), 109: ("2026-10-05", "2026-10-31"),
    110: ("2026-10-31", "2026-11-26"), 111: ("2026-11-26", "2026-12-22"),
    112: ("2026-12-22", "2027-01-17"), 113: ("2027-01-17", "2027-02-13"),
    114: ("2027-02-13", "2027-03-14"), 115: ("2027-03-14", "2027-04-12"),
    116: ("2027-04-12", "2027-05-10"), 117: ("2027-05-10", "2027-06-07"),
    118: ("2027-06-07", "2027-07-03"), 119: ("2027-07-03", "2027-07-29"),
    120: ("2027-07-29", "2027-08-23"), 121: ("2027-08-23", "2027-09-19"),
}
# Year 10 sector mid-times (JD) from tess-point 0.9.5 (tess_stars2px.py)
YEAR10_MID_JD = {
    122: 2461681.5, 123: 2461710.0, 124: 2461739.0, 125: 2461767.5, 126: 2461795.0,
    127: 2461821.5, 128: 2461847.5, 129: 2461873.5, 130: 2461900.0, 131: 2461927.5,
    132: 2461956.0, 133: 2461985.0, 134: 2462013.5,
}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def date_to_btjd(s):
    """'YYYY-MM-DD' (00:00 UTC) -> BTJD (UTC ~ TDB to ~1 min; fine for day windows)."""
    d = dt.datetime.strptime(s, "%Y-%m-%d")
    jd = (d - dt.datetime(2000, 1, 1, 12)).total_seconds() / 86400.0 + 2451545.0
    return jd - JD_BTJD


def btjd_to_date(t):
    d = dt.datetime(2000, 1, 1, 12) + dt.timedelta(days=float(t) + JD_BTJD - 2451545.0)
    return d.strftime("%Y-%m-%d %H:%M")


def sector_table():
    """{sector: (start_btjd, end_btjd, approx)} for sectors 108-134."""
    out = {s: (date_to_btjd(a), date_to_btjd(b), False) for s, (a, b) in YEAR9.items()}
    secs = sorted(YEAR10_MID_JD)
    mids = [YEAR10_MID_JD[s] - JD_BTJD for s in secs]
    start = out[121][1]
    for i, s in enumerate(secs):
        end = 0.5 * (mids[i] + mids[i + 1]) if i + 1 < len(secs) else mids[i] + (mids[i] - start)
        out[s] = (start, end, True)
        start = end
    return out


def conj_in_interval(t_ref, P, lo, hi):
    """Per Monte Carlo sample: is there a conjunction t_ref[j] + k P[j] (integer k)
    inside [lo, hi]?"""
    t_ref = np.asarray(t_ref, float)
    P = np.asarray(P, float)
    k = np.ceil((lo - t_ref) / P)
    first = t_ref + k * P
    return first <= hi


def p_conj_in_interval(t_ref, P, lo, hi):
    """Fraction of Monte Carlo samples with a conjunction inside [lo, hi]."""
    return float(np.mean(conj_in_interval(t_ref, P, lo, hi)))


def windows_between(s, key, t_central, P_central, t_from, t_to):
    """Predicted conjunction windows (centre, robust sd) between t_from and t_to."""
    out = []
    k0 = int(np.ceil((t_from - t_central) / P_central))
    k1 = int(np.floor((t_to - t_central) / P_central))
    for k in range(k0, k1 + 1):
        tn = t_central + k * P_central
        off = go.phase_offsets(s, key, tn)
        med = float(np.median(off))
        sd = float(1.4826 * np.median(np.abs(off - med)))
        lo, hi = np.percentile(off, [2.5, 97.5])
        out.append({"centre": tn - med, "sd": sd, "lo95": tn - hi, "hi95": tn - lo,
                    "constrained": sd < P_central / 4})
    return out


def on_silicon(ids, ras, decs):
    """{source_id: [(sector, camera, ccd, col, row), ...]} for sectors 108-134."""
    from tess_stars2px import tess_stars2px_function_entry as t2p
    out = {int(i): [] for i in ids}
    res = t2p(np.asarray(ids), np.asarray(ras, float), np.asarray(decs, float))
    oid, _, _, sec, cam, ccd, col, row = res[:8]
    for i, s, c, d, x, y in zip(oid, sec, cam, ccd, col, row):
        if 108 <= int(s) <= 134:
            out[int(i)].append((int(s), int(c), int(d), float(x), float(y)))
    return out


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv=None):
    import run_search as rs
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--source-ids", default=None)
    ap.add_argument("--schema", default="gaiadr3")
    ap.add_argument("--gmax", type=float, default=17)
    ap.add_argument("--cosi-max", type=float, default=0.3)
    ap.add_argument("--m2-max", type=float, default=0.1,
                    help="keep companions with dark-companion mass below this (Msun)")
    ap.add_argument("--mc", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261117)
    ap.add_argument("--t-from", type=float, default=4375.5, help="BTJD (2026-12-01)")
    ap.add_argument("--t-to", type=float, default=4740.5, help="BTJD (2027-12-01)")
    ap.add_argument("--prefix", default="forecast")
    ap.add_argument("--tap-chunks", type=int, default=16)
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    go.GAIA_REF_BTJD = 936.875 if args.schema.lower().endswith("dr4") else 389.0
    src = None
    tag = f"{args.schema}_nss_ti_g{args.gmax:g}_c{args.cosi_max:g}"
    if args.source_ids:
        src = sorted({int(x) for x in args.source_ids.replace(" ", "").split(",") if x})
        tag += f"_ids{len(src)}-{sum(src) % 1000003}"
    # same cache file names as run_search.py / archival.py (shared data_key)
    query = rs.build_nss_query(args.schema, args.gmax, args.cosi_max, None, src)
    rows = rs.read_csv_text(rs.cached_query(os.path.join(args.data_dir, tag + "_v3.csv"), query,
                                            1 if src else args.tap_chunks))
    log("Gaia rows:", len(rows))

    by_src = {}
    for r in rows:
        ep = r.get("ref_epoch", np.nan)
        r["ref_btjd"] = rs.ref_epoch_to_btjd(ep) if np.isfinite(ep) else go.GAIA_REF_BTJD
        r["_lab"] = bool(go.transit_label(r)["transit_conj"])
        old = by_src.get(r["source_id"])
        if old is None or (r["_lab"] and not old["_lab"]):
            by_src[r["source_id"]] = r

    sectors = sector_table()
    stars = []
    for sid, r in sorted(by_src.items()):
        rng = np.random.default_rng([args.seed, sid % (2 ** 32), sid // (2 ** 32)])
        try:
            res = rs.prior_for_row(r, args.mc, rng, None)
        except Exception as exc:
            log("prior failed", sid, exc)
            continue
        if res is None:
            continue
        pr, s, g = res
        if not (np.isfinite(pr["m2_dark"]) and pr["m2_dark"] < args.m2_max):
            continue
        if pr["transit_conj"] and pr["rv_consistent"]:
            keys = [(pr["transit_conj"], 1.0)]
        else:
            keys = [("t1", 0.5), ("t2", 0.5)]
        stars.append({"sid": sid, "row": r, "pr": pr, "s": s, "g": g, "keys": keys})
    log("stars kept:", len(stars))
    if not stars:
        return 0

    try:
        sil = on_silicon([x["sid"] for x in stars], [x["row"]["ra"] for x in stars],
                         [x["row"]["dec"] for x in stars])
        sil_ok = True
    except Exception as exc:
        log("tess-point failed:", exc)
        sil, sil_ok = {x["sid"]: [] for x in stars}, False

    sec_rows, win_rows, star_rows = [], [], []
    for x in stars:
        sid, r, pr, s, g = x["sid"], x["row"], x["pr"], x["s"], x["g"]
        exp_tess = 0.0
        on = sil.get(sid, [])
        for (sec, cam, ccd, col, row) in on:
            lo, hi, approx = sectors[sec]
            for key, wgt in x["keys"]:
                inside = conj_in_interval(s[key], s["P"], lo, hi)
                ecl = np.asarray(g["ecl" + key[1]], bool)
                pin = float(np.mean(inside))
                pgeo = float(np.mean(ecl))
                e = wgt * float(np.mean(inside & ecl))   # joint over the same samples
                exp_tess += e
                sec_rows.append({"source_id": sid, "sector": sec, "camera": cam, "ccd": ccd,
                                 "col": round(col, 1), "row": round(row, 1),
                                 "start_btjd": round(lo, 2), "end_btjd": round(hi, 2),
                                 "start_utc": btjd_to_date(lo), "end_utc": btjd_to_date(hi),
                                 "dates_approx": approx, "conj": key, "weight": wgt,
                                 "p_conj_in_sector": round(pin, 4), "p_geom": round(pgeo, 4),
                                 "expected_transits": round(e, 5)})
        tc = {"t1": pr["t_conj1_btjd"], "t2": pr["t_conj2_btjd"]}
        for key, wgt in x["keys"]:
            for w in windows_between(s, key, tc[key], float(r["period"]), args.t_from, args.t_to):
                win_rows.append({"source_id": sid, "conj": key, "weight": wgt,
                                 "centre_btjd": round(w["centre"], 3),
                                 "centre_utc": btjd_to_date(w["centre"]),
                                 "sd_d": round(w["sd"], 3), "lo95_btjd": round(w["lo95"], 3),
                                 "hi95_btjd": round(w["hi95"], 3),
                                 "constrained": w["constrained"],
                                 "dur_h": round(pr[f"dur{key[1]}_h"], 2),
                                 "ra": r["ra"], "dec": r["dec"], "gmag": r["phot_g_mean_mag"]})
        star_rows.append({"source_id": sid, "solution_type": r["nss_solution_type"],
                          "ra": r["ra"], "dec": r["dec"], "gmag": r["phot_g_mean_mag"],
                          "period_d": r["period"], "m2_dark": round(pr["m2_dark"], 4),
                          "class": pr["class"], "cosi": round(pr["cosi"], 4),
                          "p_ecl": round(pr["p_ecl"], 4), "transit_conj": pr["transit_conj"],
                          "rv_consistent": pr["rv_consistent"],
                          "dur_transit_h": round(pr[f"dur{x['keys'][0][0][1]}_h"], 2),
                          "sectors_on_silicon": " ".join(str(o[0]) for o in on),
                          "expected_tess_transits_y9_y10": round(exp_tess, 5)})
    star_rows.sort(key=lambda d: -d["expected_tess_transits_y9_y10"])
    p = os.path.join(args.out_dir, args.prefix)
    write_csv(p + "_stars.csv", star_rows, list(star_rows[0].keys()))
    sec_fields = ["source_id", "sector", "camera", "ccd", "col", "row", "start_btjd",
                  "end_btjd", "start_utc", "end_utc", "dates_approx", "conj", "weight",
                  "p_conj_in_sector", "p_geom", "expected_transits"]
    write_csv(p + "_tess_sectors.csv", sec_rows, sec_fields)
    win_fields = ["source_id", "conj", "weight", "centre_btjd", "centre_utc", "sd_d",
                  "lo95_btjd", "hi95_btjd", "constrained", "dur_h", "ra", "dec", "gmag"]
    write_csv(p + "_windows.csv", win_rows, win_fields)
    try:
        from importlib.metadata import version as _v
        tp_version = _v("tess-point")
    except Exception:
        tp_version = ""
    summary = {"version": VERSION, "args": vars(args), "tess_point_ok": sil_ok,
               "tess_point_version": tp_version,
               "max_sector_on_silicon": max([o[0] for v in sil.values() for o in v] or [0]),
               "stars": len(star_rows),
               "stars_on_silicon_y9_y10": sum(1 for d in star_rows if d["sectors_on_silicon"]),
               "expected_tess_transits_total": round(sum(d["expected_tess_transits_y9_y10"]
                                                         for d in star_rows), 4),
               "ground_windows": len(win_rows),
               "ground_windows_constrained": sum(1 for w in win_rows if w["constrained"])}
    with open(p + "_summary.json", "w") as fh:
        json.dump(summary, fh, indent=1, default=str)
    lines = [f"# Forecast of Gaia-predicted transits ({args.schema}), version {VERSION}", "",
             "Made by AI agents working for MV2 of Munim, Inc. Apache-2.0 code, CC BY 4.0 results.",
             "", "```", json.dumps(summary, indent=1, default=str), "```", "",
             "| Gaia source_id | G | P (d) | m2 (Msun) | p_ecl | transit conj | TESS sectors (on CCD) | expected TESS transits |",
             "|---|---|---|---|---|---|---|---|"]
    for d in star_rows:
        lines.append(f"| {d['source_id']} | {d['gmag']:.2f} | {d['period_d']:.3f} | {d['m2_dark']:.3f} | "
                     f"{d['p_ecl']:.3f} | {d['transit_conj'] or 't1/t2'} | {d['sectors_on_silicon'] or '-'} | "
                     f"{d['expected_tess_transits_y9_y10']:.4f} |")
    with open(p + "_report.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log("done", json.dumps(summary, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
