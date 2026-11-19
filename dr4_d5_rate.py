# SPDX-License-Identifier: Apache-2.0
"""dr4_d5_rate 0.1.1: D5 of the Gaia DR4 SB1-reality test. Are DR4's NEW low-mass SB1 orbits purer?

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Pre-registration: findings/2026-11-18-dr4-sb1-reality-prereg.md (D5), amendment 2 (DR4 keeps
SB1 orbits in two tables), sb1_robust amendment 1 (radius_flag) and amendment 3
(findings/2026-11-19-dr4-sb1-reality-amendment-3.md, the implementation rules of this file).
Written 2026-11-19, thirteen days before Gaia DR4 (2 December 2026), with no DR4 data seen.

0.1.1 (2026-11-19, findings/2026-11-19-calib-dr4-amendment-2.md): the DR4 id column of
gaiadr4.dr3_neighbourhood is resolved with dr4_fetch.resolve_new_id ('dr4_source_id', then
'source_id'); neither present = exit 4. 0.1.0 assumed 'source_id', which the DR3 rehearsal of
calib-dr4 showed ESA does not use for gaiadr3.dr2_neighbourhood. Nothing else changed.

D5 (exploratory): rho_DR4-new > rho_DR3, where rho_DR4-new is the transit reality fraction of
DR4 SB1/SB1C orbits that pass the same cuts and were NOT SB1/SB1C orbits in DR3.

Order of operations (amendment 3):
  1. Every orbit table in use (DR4: nss_two_body_orbit, rvs_two_body_orbit and, if present,
     nss_two_body_orbit_supp) is queried with sb1_robust 0.2.0's WHERE clause (SB1/SB1C,
     1 <= P < 13 d, G <= 13, K^3 P < 15440), joined to gaia_source and astrophysical_parameters.
     A table or column the rules need that is missing stops the run (exit 4). A bin that
     returns the archive row cap is split, never truncated.
  2. One row per source: table order of dr4_sb1_reality.table_rank, then RV_PREF, then larger
     significance. Never chosen by period or K.
  3. sb1_transit 0.1.0 star_physics + eligible (imported, unchanged).
  4. radius_flag of sb1_combine (amendment 1, imported) BEFORE sampling: flagged stars leave
     the pool and are only counted.
  5. In-DR3 test: a DR4 source is IN_DR3 if any DR3 neighbour within 1 arcsec
     (gaiadr4.dr3_neighbourhood) has a gaiadr3.nss_two_body_orbit SB1/SB1C row, at any
     period. Otherwise NEW (with or without a DR3 neighbour).
  6. The NEW pool is ordered with sb1_robust's seed (20261119) and split into chunks; each
     chunk runs the sb1_robust 0.2.0 TESS search unchanged. Every chunk records the pool's
     SHA-256 so the grade can check that all chunks used one pool.

Subcommands: pool (pool only, stdlib), chunk (pool + TESS search; needs sb1_robust's
dependencies), grade (combine chunks with sb1_combine and grade D5).
`--schema dr3` is the dress rehearsal: identity match, so every eligible star must come back
IN_DR3, and the pre-flag pool must be the 6,434 stars of sb1_robust 0.2.0.

Exit codes: 0 ok; 2 archive unavailable (re-file unchanged); 3 pool not reproduced / empty;
4 a table or column is missing (d5_schema_found.json lists what exists); 5 chunks disagree on
the pool.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time

import dr4_fetch as df
import dr4_sb1_reality as dsr
import sb1_combine as sc

VERSION = "0.1.1"
P_EDGES = (1, 1.5, 2, 3, 5, 8, 13)
G_MAX = 13.0                    # sb1_transit.G_MAX
KP_SERVER_MAX = 15440.0         # sb1_transit.KP_SERVER_MAX
ROW_CAP = 50000                 # anonymous sync TAP row limit; a bin at the cap is split
MIN_BIN_WIDTH = 0.01            # days; a bin narrower than this at the cap stops the run
MATCH_RADIUS_MAS = df.MATCH_RADIUS_MAS
EXPECTED_DR3_POOL = 6434
SEED_NOTE = "sb1_robust 0.2.0 seed 20261119"

TABLES = {
    "dr4": {"orbits": ("gaiadr4.nss_two_body_orbit", "gaiadr4.rvs_two_body_orbit"),
            "optional_orbits": ("gaiadr4.nss_two_body_orbit_supp",),
            "gaia_source": "gaiadr4.gaia_source",
            "ap": "gaiadr4.astrophysical_parameters",
            "xmatch": "gaiadr4.dr3_neighbourhood",
            "dr3_nss": "gaiadr3.nss_two_body_orbit"},
    "dr3": {"orbits": ("gaiadr3.nss_two_body_orbit",),
            "optional_orbits": (),
            "gaia_source": "gaiadr3.gaia_source",
            "ap": "gaiadr3.astrophysical_parameters",
            "xmatch": None,
            "dr3_nss": "gaiadr3.nss_two_body_orbit"},
}
ORBIT_REQUIRED = ("source_id", "nss_solution_type", "period", "semi_amplitude_primary",
                  "eccentricity", "arg_periastron")
ORBIT_OPTIONAL = ("period_error", "eccentricity_error", "arg_periastron_error", "t_periastron",
                  "t_periastron_error", "semi_amplitude_primary_error", "significance",
                  "goodness_of_fit", "bit_index", "corr_vec")
SOURCE_REQUIRED = ("source_id", "ra", "dec", "phot_g_mean_mag", "bp_rp", "parallax",
                   "parallax_error", "ruwe")
AP_REQUIRED = ("source_id", "mass_flame", "radius_flame", "radius_gspphot", "logg_gspphot")
AP_OPTIONAL = ("teff_gspphot",)
XMATCH_OLD = "dr3_source_id"


class PoolError(RuntimeError):
    def __init__(self, msg, code):
        super().__init__(msg)
        self.code = code


# ------------------------------------------------------------------ schema
def check_tables(schema, query=df.tap_query):
    """{table: {col: meta}} for every table used. Raises df.SchemaError when a required
    table/column is missing. An optional orbit table that is absent is skipped; one that
    exists without the required columns stops the run (its orbits would be lost). The
    neighbourhood table's DR4 id column is resolved with dr4_fetch.resolve_new_id."""
    t = TABLES[schema]
    found, missing = {}, []
    need = {}

    def add(tb, cols):
        need[tb] = tuple(dict.fromkeys(need.get(tb, ()) + tuple(cols)))
    for tb in t["orbits"]:
        add(tb, ORBIT_REQUIRED)
    add(t["gaia_source"], SOURCE_REQUIRED)
    add(t["ap"], AP_REQUIRED)
    add(t["dr3_nss"], ("source_id", "nss_solution_type"))
    if t["xmatch"]:
        add(t["xmatch"], (XMATCH_OLD,) + df.XMATCH_COLS)
    for tb, cols in need.items():
        have = df.table_columns(tb, query)
        found[tb] = have
        if not have:
            missing.append("%s (table)" % tb)
            continue
        missing += ["%s.%s" % (tb, c) for c in cols if c not in have]
        if tb == t["xmatch"]:
            col = df.resolve_new_id(schema, have)
            if col is None:
                missing.append(df.missing_new_id_label(schema))
            else:
                df.set_xmatch_new_id(schema, col)
    for tb in t["optional_orbits"]:
        have = df.table_columns(tb, query)
        found[tb] = have
        if have:
            missing += ["%s.%s" % (tb, c) for c in ORBIT_REQUIRED if c not in have]
    if missing:
        raise df.SchemaError("missing: " + ", ".join(missing),
                             {k: sorted(v) for k, v in found.items()})
    return found


def orbit_tables(schema, found):
    t = TABLES[schema]
    return list(t["orbits"]) + [tb for tb in t["optional_orbits"] if found.get(tb)]


# ------------------------------------------------------------------ queries
def sample_query(schema, table, found, lo, hi):
    """sb1_robust 0.2.0's WHERE clause on one orbit table and period bin."""
    t = TABLES[schema]
    have = found.get(table, {})
    ocols = [c for c in ORBIT_REQUIRED + ORBIT_OPTIONAL if c in have]
    acols = [c for c in AP_REQUIRED[1:] + AP_OPTIONAL if c in found.get(t["ap"], {})]
    sel = (["o.%s" % c for c in ocols] + ["s.%s" % c for c in SOURCE_REQUIRED[1:]] +
           ["a.%s" % c for c in acols])
    return ("SELECT %s FROM %s AS o JOIN %s AS s ON s.source_id = o.source_id "
            "LEFT OUTER JOIN %s AS a ON a.source_id = o.source_id "
            "WHERE o.nss_solution_type IN ('SB1','SB1C') AND o.period >= %r AND o.period < %r "
            "AND s.phot_g_mean_mag <= %g AND o.semi_amplitude_primary*o.semi_amplitude_primary*"
            "o.semi_amplitude_primary*o.period < %g"
            % (", ".join(sel), table, t["gaia_source"], t["ap"], float(lo), float(hi),
               G_MAX, KP_SERVER_MAX))


def fetch_bin(schema, table, found, lo, hi, query, log):
    """Rows of one bin; a bin at the row cap is split in two (never truncated)."""
    rows = query(sample_query(schema, table, found, lo, hi), timeout=300)
    if len(rows) < ROW_CAP:
        return rows
    if hi - lo < MIN_BIN_WIDTH:
        raise PoolError("bin %s %g-%g still at the row cap" % (table, lo, hi), 4)
    mid = 0.5 * (lo + hi)
    log("bin %s %g-%g at the row cap (%d): splitting" % (table, lo, hi, len(rows)))
    return (fetch_bin(schema, table, found, lo, mid, query, log) +
            fetch_bin(schema, table, found, mid, hi, query, log))


def fetch_sample(schema, found, query=df.tap_query, p_edges=P_EDGES, log=print):
    rows, per_table = [], {}
    for table in orbit_tables(schema, found):
        n = 0
        for lo, hi in zip(p_edges[:-1], p_edges[1:]):
            part = fetch_bin(schema, table, found, lo, hi, query, log)
            for r in part:
                r["_table"] = table
            n += len(part)
            rows += part
        per_table[table] = n
        if n == 0 and table in TABLES[schema]["orbits"]:
            raise PoolError("no SB1/SB1C rows in %s: solution-type names differ?" % table, 4)
    return rows, per_table


# ------------------------------------------------------------------ per-source choice
def pick_row(rows):
    """One row per source: table rank, then RV_PREF, then larger significance."""
    return sorted(rows, key=lambda r: (dsr.table_rank(r.get("_table", "")),
                                       dsr._rv_rank(str(r.get("nss_solution_type", "")).strip().strip('"')),
                                       -df.fnum(r.get("significance"), 0.0)))[0]


def dedupe(rows):
    by = {}
    for r in rows:
        by.setdefault(str(r.get("source_id", "")).strip(), []).append(r)
    out = {sid: pick_row(rs) for sid, rs in by.items() if sid}
    n_multi = sum(1 for rs in by.values() if len(rs) > 1)
    return out, n_multi


def flag_of(row, ph):
    """Amendment-1 radius_flag on the values sb1_transit derives for this row."""
    return sc.radius_flag({"abs_g": ph["abs_g"], "bp_rp": row.get("bp_rp"), "r1": ph["r1"]})


# ------------------------------------------------------------------ in-DR3 test
def adql_xmatch_rev(schema, ids):
    t = TABLES[schema]
    new_col = df.SCHEMAS[schema]["xmatch_new_id"]
    return ("SELECT x.%s AS new_id, x.%s AS old_id, %s FROM %s AS x WHERE x.%s IN (%s)"
            % (new_col, XMATCH_OLD, ", ".join("x.%s" % c for c in df.XMATCH_COLS),
               t["xmatch"], new_col, df._ids(ids)))


def adql_dr3_sb1(schema, ids):
    return ("SELECT n.source_id, n.nss_solution_type FROM %s AS n WHERE n.source_id IN (%s) "
            "AND n.nss_solution_type IN ('SB1','SB1C')" % (TABLES[schema]["dr3_nss"], df._ids(ids)))


def dr3_status(schema, ids, found, query=df.tap_query):
    """{dr4_id: 'IN_DR3' | 'NEW' | 'NEW_NO_DR3_MATCH'}."""
    ids = sorted(set(ids))
    if schema == "dr3":
        neigh = {i: [i] for i in ids}
    else:
        unit = found.get(TABLES[schema]["xmatch"], {}).get("angular_distance", {}).get("unit", "mas")
        neigh = {i: [] for i in ids}
        for ch in df.chunks(ids):
            for r in query(adql_xmatch_rev(schema, ch)):
                n = str(r.get("new_id", "")).strip()
                if n in neigh and df.angular_mas(r.get("angular_distance"), unit) <= MATCH_RADIUS_MAS:
                    neigh[n].append(str(r.get("old_id", "")).strip())
    olds = sorted({o for v in neigh.values() for o in v if o})
    has = set()
    for ch in df.chunks(olds):
        for r in query(adql_dr3_sb1(schema, ch)):
            has.add(str(r.get("source_id", "")).strip())
    out = {}
    for i in ids:
        if any(o in has for o in neigh[i]):
            out[i] = "IN_DR3"
        else:
            out[i] = "NEW" if neigh[i] else "NEW_NO_DR3_MATCH"
    return out


def pool_hash(ids):
    return hashlib.sha256("\n".join(sorted(str(i).strip() for i in ids)).encode()).hexdigest()


# ------------------------------------------------------------------ the pool
def build_pool(schema, st, query=df.tap_query, p_edges=P_EDGES, all_new=False, log=print):
    """Returns (pool_rows, records, info). pool_rows are the raw rows of the D5 pool (NEW,
    eligible, unflagged), in source_id order. Raises df.SchemaError, df.TapError, PoolError."""
    found = check_tables(schema, query)
    rows, per_table = fetch_sample(schema, found, query, p_edges, log)
    # sb1_transit's own count: eligible ROWS before any deduplication (sb1_robust's 6,434)
    n_elig_rows = sum(1 for r in rows if st.eligible(r, st.star_physics(r))[0])
    by_id, n_multi = dedupe(rows)
    recs, why, flags = [], {}, {}
    elig = {}
    for sid in sorted(by_id):
        r = by_id[sid]
        ph = st.star_physics(r)
        ok, reason = st.eligible(r, ph)
        if not ok:
            why[reason] = why.get(reason, 0) + 1
            continue
        fl = flag_of(r, ph)
        rec = {"source_id": sid, "table": r.get("_table"), "type": r.get("nss_solution_type"),
               "P": ph["P"], "K": ph["K"], "e": ph["e"], "G": df.fnum(r.get("phot_g_mean_mag")),
               "bp_rp": df.fnum(r.get("bp_rp")), "abs_g": ph["abs_g"], "m1": ph["m1"],
               "m1_src": ph["m1_src"], "r1": ph["r1"], "m2sini": ph["m2sini"],
               "m2_class": ph["m2_class"], "p_transit": ph["p_transit"], "radius_flag": fl}
        recs.append(rec)
        if fl:
            flags[fl] = flags.get(fl, 0) + 1
        else:
            elig[sid] = r
    status = dr3_status(schema, list(elig), found, query) if elig else {}
    for rec in recs:
        rec["dr3_status"] = status.get(rec["source_id"], "")
    new_ids = sorted(i for i, s in status.items() if all_new or s != "IN_DR3")
    counts = {}
    for s in status.values():
        counts[s] = counts.get(s, 0) + 1
    info = {"version": VERSION, "schema": schema, "rows_by_table": per_table,
            "sources": len(by_id), "sources_in_several_rows": n_multi,
            "eligible_rows_sb1_transit_count": n_elig_rows, "eligible_before_flags": len(recs), "rejected": why, "radius_flag_removed": flags,
            "eligible_unflagged": len(elig), "dr3_status": counts, "all_new": bool(all_new),
            "pool": len(new_ids), "pool_sha256": pool_hash(new_ids),
            "pool_by_class": {}, "pool_by_table": {}, "seed": SEED_NOTE,
            "xmatch_new_id": df.SCHEMAS[schema]["xmatch_new_id"] if TABLES[schema]["xmatch"] else "",
            "t_periastron_meta": {tb: found.get(tb, {}).get("t_periastron")
                                  for tb in orbit_tables(schema, found)}}
    for rec in recs:
        if rec["source_id"] in new_ids:
            for key, val in (("pool_by_class", rec["m2_class"]), ("pool_by_table", rec["table"])):
                info[key][val] = info[key].get(val, 0) + 1
    return [elig[i] for i in new_ids], recs, info


def rehearsal_checks(info):
    """DR3 dress rehearsal: pre-flag pool 6,434, every unflagged eligible star IN_DR3."""
    return {"RH1_pool_reproduced": info["eligible_rows_sb1_transit_count"] == EXPECTED_DR3_POOL,
            "RH2_all_in_dr3": info["dr3_status"].get("IN_DR3", 0) == info["eligible_unflagged"],
            "RH3_flags_counted": sum(info["radius_flag_removed"].values()) ==
            info["eligible_before_flags"] - info["eligible_unflagged"]}


# ------------------------------------------------------------------ grade
def d5_grade(new_summary, rho_dr3, per_chunk_grades):
    """D5 pass rule (pre-registered): rho_DR4-new > rho_DR3, both rho_substellar_size; rho_DR3
    is sb1_combine's amendment-1 value (trusted radii only), the same population rule as this
    pool. Interpretable only if C1 and C2 pass on the D5 chunks."""
    r = new_summary["rho_substellar_size"]
    c1, c2 = per_chunk_grades.get("C1", {}).get("pass"), per_chunk_grades.get("C2", {}).get("pass")
    valid = bool(c1) and bool(c2)
    val = r.get("rho")
    p = (val > rho_dr3) if (val is not None and rho_dr3 is not None) else None
    lo = r.get("ci95", [None, None])[0]
    return {"prediction": "rho_DR4-new > rho_DR3 (rho_substellar_size; rho_DR3 = amendment-1 combined value)",
            "rho_dr4_new": val, "ci95": r.get("ci95"), "rho_dr3": rho_dr3,
            "pass": p if valid else None, "valid": valid, "C1": c1, "C2": c2,
            "lower_bound_above_dr3": (lo is not None and rho_dr3 is not None and lo > rho_dr3)
            if valid else None}


def rho_dr3_from(path):
    with open(path) as fh:
        d = json.load(fh)
    return d["amendment1"]["summary"]["rho_substellar_size"]["rho"]


# ------------------------------------------------------------------ io
def _write_csv(path, rows):
    keys = sorted({k for r in rows for k in r}) if rows else ["source_id"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    return o


def _dump(path, obj):
    with open(path, "w") as fh:
        json.dump(_clean(obj), fh, indent=1)


def _pool_step(args, st, query=df.tap_query):
    """Build the pool and write d5_pool.csv / d5_pool_summary.json. Returns (code, rows, info)."""
    out = args.out_dir
    os.makedirs(out, exist_ok=True)
    edges = tuple(float(x) for x in args.p_edges.split(",")) if args.p_edges else P_EDGES
    try:
        rows, recs, info = build_pool(args.schema, st, query, edges, args.all_new)
    except df.SchemaError as exc:
        _dump(os.path.join(out, "d5_schema_found.json"), exc.found)
        print("schema mismatch:", exc)
        return 4, None, None
    except PoolError as exc:
        _dump(os.path.join(out, "d5_pool_summary.json"), {"error": str(exc)})
        print(exc)
        return exc.code, None, None
    except df.TapError as exc:
        print("archive unavailable:", exc)
        return 2, None, None
    if args.schema == "dr3":
        info["rehearsal"] = rehearsal_checks(info)
    info["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _write_csv(os.path.join(out, "d5_pool.csv"), recs)
    _dump(os.path.join(out, "d5_pool_summary.json"), info)
    print(json.dumps(_clean({k: info.get(k) for k in ("rows_by_table", "eligible_before_flags",
                                                       "radius_flag_removed", "dr3_status", "pool",
                                                       "pool_sha256", "rehearsal")})))
    if args.schema == "dr3":
        ok = all(info["rehearsal"].values())
        if not ok:
            print("rehearsal failed:", info["rehearsal"])
            return 3, rows, info
        if not args.all_new:
            return 0, rows, info          # identity match: an empty NEW pool is the right answer
    if not rows:
        print("empty D5 pool")
        return 3, rows, info
    return 0, rows, info


def run_chunk(args):
    import sb1_transit as st
    import sb1_robust as sr
    sr.install(st)
    code, rows, info = _pool_step(args, st)
    if code:
        return code
    if not rows:
        print("empty D5 pool: nothing to search (use --all-new for a DR3 rehearsal)")
        return 3
    st.query_sample = lambda *a, **k: list(rows)      # the D5 pool, flags already removed
    rc = st.main(["--out-dir", args.out_dir, "--chunk", str(args.chunk), "--n-chunks",
                  str(args.n_chunks), "--time-budget-min", str(args.time_budget_min)] +
                 (["--tmp-dir", args.tmp_dir] if args.tmp_dir else []))
    if rc == 0:
        sr.extras(st, args.out_dir)
    _dump(os.path.join(args.out_dir, "d5_chunk_info.json"),
          {"version": VERSION, "chunk": args.chunk, "n_chunks": args.n_chunks,
           "pool": info["pool"], "pool_sha256": info["pool_sha256"], "schema": args.schema})
    return rc


def run_pool(args):
    import sb1_transit as st
    return _pool_step(args, st)[0]


def run_grade(args):
    loaded, missing = sc.load_chunks(args.chunk_dir, None, ())
    if not loaded:
        print("no chunks found; missing:", missing)
        return 3
    hashes = set()
    for d in args.chunk_dir:
        p = os.path.join(d, "d5_chunk_info.json")
        if os.path.exists(p):
            with open(p) as fh:
                hashes.add(json.load(fh).get("pool_sha256"))
        else:
            hashes.add(None)
    if len(hashes) != 1 or None in hashes:
        print("chunks disagree on the pool (or lack d5_chunk_info.json):", hashes)
        return 5
    res = sc.run(loaded, missing)
    rho3 = args.rho_dr3 if args.rho_dr3 is not None else rho_dr3_from(args.dr3_combined)
    g = d5_grade(res["primary"]["summary"], rho3, res["primary"]["grades"])
    g["A1_noop"] = not res["amendment1"]["removed_by_reason"]
    g["by_class"] = {c: res["primary"]["splits"]["by_class"][c]["rho_substellar_size"]
                     for c in res["primary"]["splits"]["by_class"]}
    g["chunks_used"], g["chunks_missing"] = res["chunks_used"], missing
    g["pool_sha256"] = hashes.pop()
    os.makedirs(args.out_dir, exist_ok=True)
    _dump(os.path.join(args.out_dir, "d5_combined.json"), res)
    _dump(os.path.join(args.out_dir, "d5_grade.json"), g)
    print(json.dumps(_clean(g)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    for name in ("pool", "chunk"):
        p = sub.add_parser(name)
        p.add_argument("--schema", choices=("dr3", "dr4"), required=True)
        p.add_argument("--out-dir", required=True)
        p.add_argument("--p-edges", default="")
        p.add_argument("--all-new", action="store_true",
                       help="rehearsal only: treat every unflagged eligible star as new")
        if name == "chunk":
            p.add_argument("--chunk", type=int, required=True)
            p.add_argument("--n-chunks", type=int, default=8)
            p.add_argument("--time-budget-min", type=float, default=160.0)
            p.add_argument("--tmp-dir", default="")
    g = sub.add_parser("grade")
    g.add_argument("--chunk-dir", action="append", default=[], required=True)
    g.add_argument("--rho-dr3", type=float, default=None)
    g.add_argument("--dr3-combined", default="")
    g.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "pool":
        return run_pool(a)
    if a.cmd == "chunk":
        return run_chunk(a)
    if a.cmd == "grade":
        if a.rho_dr3 is None and not a.dr3_combined:
            ap.error("grade needs --rho-dr3 or --dr3-combined")
        return run_grade(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
