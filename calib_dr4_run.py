# SPDX-License-Identifier: Apache-2.0
"""calib_dr4_run.py -- run the pre-registered DR3 -> DR4 test of the eclipse deficit.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Pre-registration: findings/2026-11-18-calib-dr4-prereg.md (+ amendment of 2026-11-18,
findings/2026-11-18-calib-dr4-amendment-1.md).

  --schema dr4   release day (Gaia DR4, 2 December 2026): grade K1-K6 (+ K2b).
  --schema dr3   dress rehearsal before DR4: the same code with DR3 as the "new" release
                 (identity cross-match). Every orbit must come back CONFIRMED with the DR3
                 inclination and timing it started from (checks RH1-RH4). It also measures
                 the DR3 baseline of K2 (how many targets already look 'not edge-on').

Steps: (1) rebuild the calib-window sample (162 targets; E = 58 seen within 9 sigma_t)
from the gaia-orbit-tess volume and check it against data/calib-window-v1; (2) check
every table and column in TAP_SCHEMA; (3) cross-match, fetch orbits, label; (4) for
CONFIRMED orbits get cos i, its error and the conjunction-time offset from Monte Carlo
samples of the new orbit (gaia_orbits.sample_orbit, as for DR3); (5) grade.

Exit codes: 0 done; 2 Gaia archive unreachable; 3 sample not reproduced; 4 table or
column missing (out/schema_found.json lists what exists); 5 unknown solution type among
matched sources (classify it from the data model before grading).
"""
import argparse
import csv
import json
import math
import os
import statistics
import sys

VERSION = "0.1.0"
N_MC = 4000
N_SIGMA = 9.0
EXPECT_MAIN = 162
EXPECT_E = 58
DR3_RMS_Z9 = 2.665039767525298        # calib-window-v1, 57 timed targets at 9 sigma
K2B_MIN_GAIN = 0.20


def _f(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def mcnemar_one_sided(b, c):
    """Exact one-sided McNemar p for b 'gains' vs c 'losses' (binomial, p = 1/2)."""
    n = b + c
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def k2b(rows):
    """Paired change of the 'not edge-on at 2 sigma' flag from DR3 to the new release,
    for CONFIRMED targets, by group. Pass: N gains >= 0.20 (McNemar p < 0.05) while E's
    change is <= 0.10."""
    out = {}
    for g in ("N", "E"):
        pr = [r for r in rows if r.get("group") == g and r.get("label") == "CONFIRMED"
              and r.get("ne3") is not None and r.get("ne4") is not None]
        b = sum(1 for r in pr if r["ne4"] and not r["ne3"])
        c = sum(1 for r in pr if r["ne3"] and not r["ne4"])
        n = len(pr)
        out[g] = {"n": n, "gain": b, "loss": c,
                  "frac3": (sum(1 for r in pr if r["ne3"]) / n) if n else None,
                  "frac4": (sum(1 for r in pr if r["ne4"]) / n) if n else None,
                  "delta": ((b - c) / n) if n else None,
                  "p_mcnemar": mcnemar_one_sided(b, c)}
    dn, de = out["N"]["delta"], out["E"]["delta"]
    out["pass"] = bool(dn is not None and de is not None and dn >= K2B_MIN_GAIN
                       and out["N"]["p_mcnemar"] < 0.05 and de <= 0.10)
    return out


def rehearsal_checks(rows, grade):
    """RH1-RH4 for --schema dr3 (no DR4 data involved)."""
    tested = [r for r in rows if r["label"] != "UNTESTABLE"]
    conf = [r for r in rows if r["label"] == "CONFIRMED"]
    dc = [abs(r["cosi4"] - r["cosi3"]) / r["cosi_sd3"] for r in conf
          if r.get("cosi4") is not None and r.get("cosi3") is not None and r.get("cosi_sd3")]
    ratio = [r["cosi4_sd"] / r["cosi_sd3"] for r in conf
             if r.get("cosi4_sd") and r.get("cosi_sd3")]
    zs = [r["z4"] for r in rows if r.get("z4") is not None]
    rms = math.sqrt(sum(z * z for z in zs) / len(zs)) if zs else float("nan")
    return {
        "RH1_all_confirmed": {"n_rows": len(rows), "n_tested": len(tested),
                              "n_confirmed": len(conf),
                              "pass": len(rows) == EXPECT_MAIN and len(conf) == EXPECT_MAIN},
        "RH2_cosi_reproduced": {
            "n": len(dc), "frac_dcosi_lt_0.1sd": (sum(1 for x in dc if x < 0.1) / len(dc))
            if dc else None,
            "median_sd_ratio": statistics.median(ratio) if ratio else None,
            "frac_sd_ratio_0.8_1.25": (sum(1 for x in ratio if 0.8 <= x <= 1.25) / len(ratio))
            if ratio else None,
            "pass": bool(dc and ratio and sum(1 for x in dc if x < 0.1) >= 0.95 * len(dc)
                         and sum(1 for x in ratio if 0.8 <= x <= 1.25) >= 0.9 * len(ratio))},
        "RH3_timing_reproduced": {"n_timed": len(zs), "rms_z4": rms, "dr3_rms_z9": DR3_RMS_Z9,
                                  "pass": bool(zs and abs(rms / DR3_RMS_Z9 - 1) <= 0.15)},
        "RH4_no_failures": {"K1_pass": grade["K1"]["pass"],
                            "fail_N": grade["K1"]["fail_N"], "fail_E": grade["K1"]["fail_E"],
                            "pass": bool(not grade["K1"]["pass"]
                                         and grade["K1"]["fail_N"] == 0
                                         and grade["K1"]["fail_E"] == 0)},
    }


def build_sample(data_dir, expect_csv):
    """The calib-window main sample with group E/N and, for E, the 9-sigma event."""
    import calib_eclipse_rate as cer
    import calib_window as cw
    import dr4_fetch as df

    paths = cer.fetch_inputs(data_dir, True)
    targets = cer.read_csv(paths["tess_targets.csv"])
    wanted = {str(t.get("source_id", "")).strip() for t in targets}
    priors = cer.read_priors(paths["gaia_edge_on_priors.csv"], wanted)
    events = cer.read_csv(paths["events.csv"])
    windows = cer.load_windows(cer.read_csv(paths["covered_windows.csv"]))
    recs = cer.build_records(targets, priors, events, windows)
    main = [r for r in recs if not r["excluded"]]
    ev_by = {}
    for ev in events:
        ev_by.setdefault(str(ev.get("source_id", "")).strip(), []).append(ev)
    sample, problems = [], []
    for r in main:
        sid, P = r["source_id"], r["period_d"]
        clean = [(cer.fnum(e.get("t_center")), cer.fnum(e.get("snr"), 0.0),
                  cer.fnum(e.get("duration_h"), 4.0))
                 for e in ev_by.get(sid, []) if cer.event_quality(e)]
        wk = {"t1": windows.get((sid, "t1"), []), "t2": windows.get((sid, "t2"), [])}
        ev = None
        if r["det_mode"] == "window":
            b = cw.detect_at(clean, wk["t1"] + wk["t2"], P, N_SIGMA, skip_wide=False)
            ev = df.detect_event(clean, wk, P, N_SIGMA)
            if (b is None) != (ev is None) or (b and abs(b[1] - ev[1]) > 1e-9):
                problems.append(f"{sid}: detect_event disagrees with calib_window")
            det = b is not None
        else:
            det = bool(r["detected"])
        sample.append({"rec": r, "source_id": sid, "group": "E" if det else "N",
                       "t_obs": ev[3] if ev else None, "conj_obs": ev[4] if ev else "",
                       "z9_dr3": ev[1] if ev else None})
    if expect_csv and os.path.exists(expect_csv):
        with open(expect_csv, newline="", encoding="utf-8") as fh:
            exp = {row["source_id"]: row["det_9"] == "True" for row in csv.DictReader(fh)}
        for s in sample:
            if s["source_id"] not in exp:
                problems.append(f"{s['source_id']}: not in {expect_csv}")
            elif exp[s["source_id"]] != (s["group"] == "E"):
                problems.append(f"{s['source_id']}: det_9 differs from {expect_csv}")
    n_e = sum(1 for s in sample if s["group"] == "E")
    ok = len(sample) == EXPECT_MAIN and n_e == EXPECT_E and not problems
    return sample, {"n_main": len(sample), "n_E": n_e, "problems": problems[:50], "pass": ok}


def orbit_quantities(row4, rec, t_ref, t_obs, seed):
    """cos i, its MC sd, lim4 and the conjunction-time z of an observed eclipse for one
    new-release orbit row (dict of TAP strings)."""
    import numpy as np
    import gaia_orbits as go
    import dr4_fetch as df

    rng = np.random.default_rng(seed)
    s = go.sample_orbit(row4, N_MC, rng, ref_btjd=t_ref)
    A, B, F, G = (df.fnum(row4.get(f"{x}_thiele_innes")) for x in "abfg")
    if go.is_circular_fixed(row4) and B and abs(B) > 0:
        G = -A * F / B
    el = go.thiele_innes_to_elements(A, B, F, G)
    e = df.fnum(row4.get("eccentricity"), 0.0)
    e = 0.0 if go.is_circular_fixed(row4) else e
    P4 = df.fnum(row4.get("period"))
    w = float(el["omega"])
    lims = [df.lim_at(P4, rec["m1"], rec["m2_dark"], rec["r1"], rec["r2"], e, f)
            for f in (math.pi / 2 - w, 3 * math.pi / 2 - w)]
    out = {"cosi4": float(el["cosi"]), "cosi4_sd": float(np.std(s["cosi"])),
           "lim4": max(lims), "used_corr": bool(s["used_corr"]), "z4": None,
           "z4_conj": "", "z4_sd_d": None, "phase_lost": False}
    if t_obs is not None:
        t1c, t2c = go.central_conjunctions(row4, t_ref)
        d = {k: abs(((t_obs - c) + P4 / 2) % P4 - P4 / 2) for k, c in (("t1", t1c), ("t2", t2c))}
        key = min(d, key=d.get)
        off = go.phase_offsets(s, key, t_obs)
        med = float(np.median(off))
        sd = float(1.4826 * np.median(np.abs(off - med)))
        out["z4_conj"], out["z4_sd_d"] = key, sd
        if sd > 0 and sd < P4 / 4:
            out["z4"] = med / sd
        else:
            out["phase_lost"] = True
    return out


def run(a):
    import calib_dr4 as cd
    import dr4_fetch as df

    os.makedirs(a.out_dir, exist_ok=True)

    def dump(name, obj):
        with open(os.path.join(a.out_dir, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1, default=str)

    sample, repro = build_sample(a.data_dir, a.expect)
    dump("reproduction.json", repro)
    if not repro["pass"]:
        print("REPRODUCTION FAILED", json.dumps(repro)[:2000])
        return 3
    ids = [s["source_id"] for s in sample]

    try:
        avail = df.check_schema(a.schema)
    except df.SchemaError as exc:
        dump("schema_found.json", {"error": str(exc), "found": exc.found})
        print("SCHEMA", exc)
        return 4
    except df.TapError as exc:
        print("TAP DOWN", exc)
        return 2
    dump("schema_found.json", avail)
    sch = df.SCHEMAS[a.schema]

    try:
        # DR3 period errors (the old release), for the CONFIRMED tolerance
        p3err = {}
        for ch in df.chunks(ids):
            for r in df.tap_query(df.adql_nss("gaiadr3.nss_two_body_orbit", ch,
                                              ["source_id", "nss_solution_type", "period",
                                               "period_error"])):
                p3err.setdefault(str(r["source_id"]).strip(), []).append(r)
        if a.t_ref_btjd is not None:
            t_ref, t_ref_src = a.t_ref_btjd, "command line"
        else:
            ep = df.tap_query(df.adql_ref_epoch(sch["gaia_source"], ids[0]))
            t_ref = df.t_ref_btjd(float(ep[0]["ref_epoch"]))
            t_ref_src = f"{sch['gaia_source']}.ref_epoch = {ep[0]['ref_epoch']}"
        unit = avail.get(sch["xmatch"], {}).get("angular_distance", {}).get("unit", "") or "mas"
        matches, xrows = df.fetch_matches(a.schema, ids, unit)
        new_ids = sorted({m[0] for m in matches.values() if m[0]})
        orbits = df.fetch_orbits(a.schema, new_ids, avail)
        smoke = None
        if a.schema == "dr3":
            # exercise the real cross-match path on DR3 <- DR2 (report only)
            back = []
            for ch in df.chunks(ids):
                back += df.tap_query(
                    "SELECT x.source_id AS new_id, x.dr2_source_id AS old_id, "
                    "x.angular_distance, x.magnitude_difference FROM gaiadr3.dr2_neighbourhood "
                    f"AS x WHERE x.source_id IN ({','.join(ch)})")
            olds = sorted({str(r["old_id"]).strip() for r in back})
            res = df.resolve_matches(back, olds, unit)
            ok_back = {o for o, (n, st) in res.items() if st == "ok" and n in set(ids)}
            smoke = {"dr2_counterparts": len(olds),
                     "resolved_ok_to_a_target": len(ok_back),
                     "statuses": {st: sum(1 for v in res.values() if v[1] == st)
                                  for st in ("ok", "none", "ambiguous")}}
    except df.TapError as exc:
        print("TAP DOWN", exc)
        return 2

    rows, unknown_all, n_multi, n_supp = [], set(), 0, 0
    for i, s in enumerate(sample):
        r, sid = s["rec"], s["source_id"]
        p3rows = p3err.get(sid, [])
        p3row = next((x for x in p3rows if str(x.get("nss_solution_type", "")).strip()
                      == r["solution_type"]), p3rows[0] if p3rows else {})
        new_id, st = matches.get(sid, (None, "none"))
        row = {"source_id": sid, "group": s["group"], "match_status": st, "new_id": new_id,
               "solution_type3": r["solution_type"], "p3": r["period_d"],
               "s3": _f(p3row.get("period_error")), "cosi3": _f(r.get("cosi")),
               "cosi_sd3": _f(r.get("cosi_sd")),
               "lim3": max([x for x in (_f(r.get("lim1")), _f(r.get("lim2"))) if x is not None],
                           default=None),
               "t_obs": s["t_obs"], "conj_obs3": s["conj_obs"], "z9_dr3": s["z9_dr3"]}
        if row["cosi3"] is not None and row["cosi_sd3"] and row["lim3"] is not None:
            row["ne3"] = abs(row["cosi3"]) > row["lim3"] + 2.0 * row["cosi_sd3"]
        else:
            row["ne3"] = None
        sol, n_astro, unknown = (None, 0, [])
        if st == "ok":
            sol, n_astro, unknown = df.pick_solution(orbits.get(new_id, []))
            unknown_all.update(unknown)
            n_multi += n_astro > 1
        row.update({"solution_type4": sol.get("nss_solution_type") if sol else "",
                    "table4": sol.get("_table") if sol else "", "n_astro4": n_astro,
                    "p4": _f(sol.get("period")) if sol else None,
                    "s4": _f(sol.get("period_error")) if sol else None})
        n_supp += bool(sol and str(sol.get("_table", "")).endswith("_supp"))
        row["label"] = cd.label_orbit(row["p3"], row["s3"], row["p4"], row["s4"],
                                      matched=(st == "ok"))
        row.update({"cosi4": None, "cosi4_sd": None, "lim4": None, "z4": None, "ne4": None})
        if row["label"] == "CONFIRMED":
            q = orbit_quantities(sol, r, t_ref, s["t_obs"] if s["group"] == "E" else None,
                                 seed=20261202 + i)
            row.update(q)
            row["ne4"] = abs(q["cosi4"]) > q["lim4"] + 2.0 * q["cosi4_sd"]
        rows.append(row)

    if unknown_all and a.schema == "dr4" and not a.allow_unknown:
        dump("unknown_types.json", sorted(unknown_all))
        print("UNKNOWN SOLUTION TYPES", sorted(unknown_all))
        return 5

    g = cd.grade(rows)
    extra = {"K2b": k2b(rows)}
    base = {grp: {"n": sum(1 for r in rows if r["group"] == grp and r["ne3"] is not None),
                  "not_edge_on_2sd_dr3": sum(1 for r in rows if r["group"] == grp and r["ne3"])}
            for grp in ("E", "N")}
    summary = {"version": VERSION, "dr4_fetch": df.VERSION, "calib_dr4": cd.VERSION,
               "schema": a.schema, "tables": {k: v for k, v in sch.items()},
               "t_ref_btjd": t_ref, "t_ref_source": t_ref_src,
               "t_periastron_doc": avail.get(sch["nss"], {}).get("t_periastron", {}),
               "angular_distance_unit": unit, "reproduction": repro,
               "match_status": {k: sum(1 for r in rows if r["match_status"] == k)
                                for k in ("ok", "none", "ambiguous")},
               "n_multi_astro_solutions": n_multi, "n_from_supp": n_supp,
               "unknown_types": sorted(unknown_all),
               "used_corr_frac": (sum(1 for r in rows if r.get("used_corr")) /
                                  max(1, sum(1 for r in rows if r["label"] == "CONFIRMED"))),
               "phase_lost": sum(1 for r in rows if r.get("phase_lost")),
               "dr3_baseline_not_edge_on": base, "grade": g, "extra": extra,
               "xmatch_smoke_dr2": smoke}
    if a.schema == "dr3":
        summary["rehearsal"] = rehearsal_checks(rows, g)

    cols = ["source_id", "group", "match_status", "new_id", "label", "solution_type3",
            "solution_type4", "table4", "n_astro4", "p3", "s3", "p4", "s4", "cosi3",
            "cosi_sd3", "lim3", "ne3", "cosi4", "cosi4_sd", "lim4", "ne4", "used_corr",
            "t_obs", "conj_obs3", "z9_dr3", "z4_conj", "z4_sd_d", "z4", "phase_lost"]
    with open(os.path.join(a.out_dir, "calib_dr4_targets.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow(["" if r.get(c) is None else r.get(c) for c in cols])
    if xrows:
        with open(os.path.join(a.out_dir, "xmatch_raw.csv"), "w", newline="",
                  encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=sorted({k for x in xrows for k in x}))
            w.writeheader()
            w.writerows(xrows)
    dump("calib_dr4_summary.json", summary)

    L = [f"# calib_dr4 run ({a.schema}), calib_dr4_run {VERSION}", "",
         "MV2 of Munim, Inc.; made with AI agents. Code Apache-2.0, text CC BY 4.0.", "",
         f"Sample: {repro['n_main']} targets, E = {repro['n_E']} (reproduction "
         f"{'passed' if repro['pass'] else 'FAILED'}). t_ref = {t_ref} BTJD ({t_ref_src}).", "",
         f"Labels: {json.dumps(g['counts']['labels'])}", "",
         "| test | value | pass |", "|---|---|---|"]
    for k in ("K1", "K2", "K3", "K4", "K5", "K6"):
        v = {x: y for x, y in g[k].items() if x != "pass"}
        L.append(f"| {k} | {json.dumps(v, default=str)[:200]} | {'yes' if g[k]['pass'] else 'no'} |")
    L.append(f"| K2b | {json.dumps({x: y for x, y in extra['K2b'].items() if x != 'pass'}, default=str)[:300]} "
             f"| {'yes' if extra['K2b']['pass'] else 'no'} |")
    L += ["", f"Reading: **{g['reading']}**", "",
          f"DR3 baseline (|cos i| > lim + 2 sd in DR3 itself): {json.dumps(base)}"]
    if a.schema == "dr3":
        L += ["", "## Rehearsal checks", ""]
        for k, v in summary["rehearsal"].items():
            L.append(f"- {k}: {'PASS' if v['pass'] else 'FAIL'} {json.dumps(v, default=str)}")
        L.append(f"- DR2->DR3 cross-match smoke test: {json.dumps(smoke)}")
    with open(os.path.join(a.out_dir, "calib_dr4_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(json.dumps({"labels": g["counts"]["labels"], "reading": g["reading"],
                      "rehearsal": {k: v["pass"] for k, v in summary.get("rehearsal", {}).items()},
                      "K2b": extra["K2b"]["pass"], "baseline": base}, default=str))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--schema", choices=("dr3", "dr4"), required=True)
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--expect", default="window_targets.csv",
                    help="data/calib-window-v1/window_targets.csv (det_9 per target)")
    ap.add_argument("--t-ref-btjd", type=float, default=None,
                    help="override the BTJD of the t_periastron reference epoch")
    ap.add_argument("--allow-unknown", action="store_true")
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
