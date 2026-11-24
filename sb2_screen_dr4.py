# SPDX-License-Identifier: Apache-2.0
"""sb2_screen_dr4 0.2.0: amendment 1 to runbook step g5 (the edge-on double-lined screen on Gaia DR4).

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Amendment: findings/2026-11-24-g5-amendment-1.md (written 24 Nov 2026, eight days before DR4).

Imports sb2_screen 0.1.0 at commit 0a8883c902143934f2ca9933affb57cc01a851b1 UNCHANGED (selection
rule, TCE classification, VSX/SIMBAD parsers, HTTP helper) and changes only what DR3 showed broken:

1. Villanova TESS EB lookup: https instead of http (every http lookup returned HTTP 400 in job
   sb2-edgeon-screen-v1), a parser that reads the signal table, and two control TICs checked
   before any star (TIC 238162238 must be in the catalogue, TIC 189269584 must not). If a control
   fails, the lookup is switched off (None) for every star.
2. Two VizieR lookups (TESS EB catalogue J/ApJS/258/16, TESS Ten Thousand J/ApJS/279/50) through
   two mirrors, each with a self-generated positive control: the first row the catalogue returns
   must be found again by the lookup mode used (cone around its position, else its TIC).
3. A star is NEW_V2 only if every lookup gave a definite answer and all were negative. Any lookup
   that could not answer makes the star UNVETTED (hand vetting), never NEW. (DR3 lesson: a
   100%-failing lookup had counted as "not found".)
4. DR4 schema gate: required columns are read from TAP_SCHEMA first. Missing orbit columns ->
   exit 4 (gate G0, write an adapter). No binary_masses table -> arm B: every SB2 orbit with
   P < 8 d and G < 11, brightest 800 (no edge-on cut, because no mass is available to make it).

Modes: --self-test; --rehearse-csv (re-run the new lookups on the DR3 screen's own output, no
Gaia TAP needed); default = the screen on --schema (gaiadr4 on release day).
Exit codes: 0 ok; 2 data unavailable (re-file unchanged); 3 self-test failed; 4 schema gate G0.
"""
import argparse
import csv
import io
import json
import math
import os
import re
import sys
import time
import urllib.parse

import sb2_screen as s0

VERSION = "0.2.0"
BASE_SHA = "0a8883c902143934f2ca9933affb57cc01a851b1"

VILLANOVA_HTTPS = "https://tessebs.villanova.edu/%010d"
VIL_CTRL_POS = "238162238"    # HIP 34208: in Prsa et al. 2022 and on the live site (checked 24 Nov)
VIL_CTRL_NEG = "189269584"    # CD-28 7251: "No associated EB entries found" (checked 24 Nov)
VIZ_MIRRORS = ("https://vizier.cfa.harvard.edu/viz-bin/asu-tsv",
               "https://vizier.cds.unistra.fr/viz-bin/asu-tsv")
VIZ_CATS = (("tessebs_viz", "J/ApJS/258/16"), ("t10k_viz", "J/ApJS/279/50"))
VIZ_RADIUS_ARCSEC = 10.0
VIZ_CTRL_RADIUS_ARCSEC = 5.0
G_MAX_B = 11.0
N_MAX_B = 800
NEW_V2_MIN_DR4 = 5            # registered in runbook/dr4-addendum.md (prediction 50%)
LOOKUPS = ("vsx_eclipsing", "villanova", "simbad_eb", "tessebs_viz", "t10k_viz", "toi_known")
REQ_NSS = ("source_id", "nss_solution_type", "period", "period_error", "eccentricity",
           "semi_amplitude_primary", "semi_amplitude_primary_error",
           "semi_amplitude_secondary", "semi_amplitude_secondary_error")
REQ_BM = ("source_id", "m1", "combination_method")
REQ_GS = ("source_id", "phot_g_mean_mag", "ra", "dec")
ARM_B_QUERY = (
    "SELECT o.source_id, o.nss_solution_type, o.period, o.period_error, o.eccentricity, "
    "o.semi_amplitude_primary, o.semi_amplitude_primary_error, o.semi_amplitude_secondary, "
    "o.semi_amplitude_secondary_error, g.phot_g_mean_mag, g.ra, g.dec "
    "FROM {s}.nss_two_body_orbit AS o JOIN {s}.gaia_source AS g ON o.source_id = g.source_id "
    "WHERE o.nss_solution_type LIKE 'SB2%' AND o.period < 8 AND g.phot_g_mean_mag < " +
    repr(G_MAX_B))
KEYS = s0.KEYS[:-2] + ["tessebs_viz", "t10k_viz", "toi_known", "new_v2", "status", "error"]

log = s0.log
fnum = s0.fnum


# ================================================================ pure helpers
def villanova_status_v2(html):
    """True: a signal of this TIC is in the EB catalogue; False: page says no entries, or lists
    signals none of which is in the catalogue; None: cannot tell."""
    if not html:
        return None
    if "No associated EB entries found" in html:
        return False
    if "In catalog" in html:
        if re.search(r">\s*True\s*<", html):
            return True
        if re.search(r">\s*False\s*<", html):
            return False
    return None


def parse_asu_tsv(text):
    """VizieR asu-tsv -> (error, tables). Each table: {"header": [...], "rows": [[...], ...]}."""
    if text is None:
        return True, []
    # a reply that is not VizieR's own (an HTML error page, a proxy page) is an error, never "0 rows"
    err = ("VizieR" not in text or
           bool(re.search(r"QUERY_STATUS=ERROR|not currently reachable|^#\s*\*{3}", text, re.M)))
    tables, header, in_data, cur = [], None, False, None
    for line in text.splitlines():
        if line.startswith("#"):
            in_data, header = False, None
            continue
        if line.strip() == "":
            if header is not None and not in_data:
                continue                      # an all-blank units line
            in_data, header = False, None
            continue
        if in_data:
            cur["rows"].append([c.strip() for c in line.split("\t")])
            continue
        if header is None:
            header = [h.strip() for h in line.split("\t")]
            continue
        if "-" in line and re.fullmatch(r"[-\s]+", line):
            cur = {"header": header, "rows": []}
            tables.append(cur)
            in_data = True
        # anything else between header and dashes is the units line
    return err, tables


def n_rows(tables):
    return sum(len(t["rows"]) for t in tables)


def col_index(header, names):
    low = [h.strip().lower() for h in header]
    for n in names:
        if n.lower() in low:
            return low.index(n.lower())
    return None


def to_deg(s, is_ra):
    """Decimal degrees, or sexagesimal 'hh mm ss' (RA) / '+dd mm ss' (Dec)."""
    s = str(s or "").strip()
    v = fnum(s)
    if math.isfinite(v) and " " not in s and ":" not in s:
        return v
    parts = re.split(r"[\s:]+", s)
    if len(parts) != 3:
        return float("nan")
    try:
        a, b, c = float(parts[0]), float(parts[1]), float(parts[2])
    except ValueError:
        return float("nan")
    sign = -1.0 if parts[0].startswith("-") else 1.0
    deg = abs(a) + b / 60.0 + c / 3600.0
    return sign * deg * (15.0 if is_ra else 1.0)


def parse_bool(v):
    s = str(v if v is not None else "").strip()
    if s == "True":
        return True
    if s == "False":
        return False
    return None


def classify_new_v2(rec):
    if rec.get("tce_class") not in ("HALF", "FULL"):
        return "NO_MATCHING_TCE"
    if (any(rec.get(k) is True for k in LOOKUPS) or rec.get("gaia_eb") is True
            or rec.get("gaia_ecl_sb2") is True
            or str(rec.get("gaia_class", "")).upper().startswith("ECL")):
        return "KNOWN"
    if any(rec.get(k) is None for k in LOOKUPS):
        return "UNVETTED"
    return "NEW_V2"


def schema_gate(cols):
    """cols: {table: set(columns)} -> 'G0' | 'A' | 'B'."""
    nss, gs, bm = cols.get("nss_two_body_orbit", set()), cols.get("gaia_source", set()), \
        cols.get("binary_masses", set())
    if not all(c in nss for c in REQ_NSS) or not all(c in gs for c in REQ_GS):
        return "G0"
    return "A" if all(c in bm for c in REQ_BM) else "B"


def select_rows_b(rows):
    out, seen = [], set()
    for r in rows:
        sid = str(r.get("source_id", "")).strip()
        P, k1, k2 = fnum(r.get("period")), fnum(r.get("semi_amplitude_primary")), \
            fnum(r.get("semi_amplitude_secondary"))
        if not sid or sid in seen or not (P < s0.P_MAX and k1 > 0 and k2 > 0):
            continue
        seen.add(sid)
        rr = dict(r)
        rr["source_id"] = sid
        rr["m1sin3i"] = s0.m1sin3i(k1, k2, P, fnum(r.get("eccentricity")))
        rr["s3_ratio"] = float("nan")
        out.append(rr)
    out.sort(key=lambda r: fnum(r.get("phot_g_mean_mag"), 99))
    return out[:N_MAX_B]


# ================================================================ network lookups
def get_text(url, accept_404=False):
    return s0.http_get(url, accept_404=accept_404).decode("utf-8", "replace")


def viz_query(params, get=None):
    get = get or get_text
    last = None
    for m in VIZ_MIRRORS:
        url = m + "?" + urllib.parse.urlencode(params)
        try:
            text = get(url)
        except Exception as exc:
            last = repr(exc)[:160]
            continue
        err, tables = parse_asu_tsv(text)
        if err:
            last = "VizieR error at " + m
            continue
        return m, tables
    raise RuntimeError("all VizieR mirrors failed: %s" % last)


def viz_cone_params(cat, ra, dec, radius):
    return {"-source": cat, "-c": "%.6f %+.6f" % (ra, dec), "-c.rs": "%.1f" % radius,
            "-out.max": "50"}


def viz_setup(cat, get=None):
    """Self-generated positive control. -> {mode: 'cone'|'tic'|None, ...}."""
    info = {"cat": cat, "mode": None, "tic_col": None, "control": None, "error": ""}
    try:
        _, tables = viz_query({"-source": cat, "-out.max": "1", "-out.add": "_RAJ,_DEJ"}, get)
        for t in tables:
            if not t["rows"]:
                continue
            h, row = t["header"], t["rows"][0]
            ira = col_index(h, ("_RAJ2000", "RAJ2000", "RAdeg", "RA_ICRS", "_RA"))
            ide = col_index(h, ("_DEJ2000", "DEJ2000", "DEdeg", "DE_ICRS", "_DE"))
            itic = col_index(h, ("TIC", "TICID", "TIC_ID"))
            if ira is not None and ide is not None and ira < len(row) and ide < len(row):
                ra, de = to_deg(row[ira], True), to_deg(row[ide], False)
                if math.isfinite(ra) and math.isfinite(de):
                    _, tt = viz_query(viz_cone_params(cat, ra, de, VIZ_CTRL_RADIUS_ARCSEC), get)
                    if n_rows(tt) >= 1:
                        info.update({"mode": "cone", "control": [ra, de]})
                        return info
            if itic is not None and itic < len(row) and row[itic].strip().isdigit():
                _, tt = viz_query({"-source": cat, h[itic]: row[itic].strip(), "-out.max": "50"},
                                  get)
                if n_rows(tt) >= 1:
                    info.update({"mode": "tic", "tic_col": h[itic], "control": row[itic].strip()})
                    return info
        info["error"] = "no control row could be found again"
    except Exception as exc:
        info["error"] = repr(exc)[:200]
    return info


def viz_lookup(info, ra, dec, tic, get=None):
    if not info or not info.get("mode"):
        return None
    try:
        if info["mode"] == "cone":
            if not (math.isfinite(ra) and math.isfinite(dec)):
                return None
            _, tt = viz_query(viz_cone_params(info["cat"], ra, dec, VIZ_RADIUS_ARCSEC), get)
        else:
            if not str(tic or "").isdigit():
                return None
            _, tt = viz_query({"-source": info["cat"], info["tic_col"]: str(tic),
                               "-out.max": "50"}, get)
        return n_rows(tt) >= 1
    except Exception:
        return None


def villanova_lookup(tic, get=None):
    get = get or get_text
    try:
        return villanova_status_v2(get(VILLANOVA_HTTPS % int(tic), accept_404=True))
    except Exception:
        return None


def villanova_setup(get=None):
    pos, neg = villanova_lookup(VIL_CTRL_POS, get), villanova_lookup(VIL_CTRL_NEG, get)
    return {"positive": pos, "negative": neg, "ok": pos is True and neg is False}


def lookup_controls(get=None):
    c = {"villanova": villanova_setup(get)}
    for key, cat in VIZ_CATS:
        c[key] = viz_setup(cat, get)
    return c


def run_lookups(rec, ctrl, get=None):
    rec["villanova"] = villanova_lookup(rec.get("tic"), get) if ctrl["villanova"]["ok"] else None
    for key, _ in VIZ_CATS:
        rec[key] = viz_lookup(ctrl[key], fnum(rec.get("ra")), fnum(rec.get("dec")), rec.get("tic"),
                              get)
    rec["new_v2"] = classify_new_v2(rec)
    return rec


def discover(schema):
    q = ("SELECT table_name, column_name FROM tap_schema.columns WHERE table_name IN "
         "('{s}.nss_two_body_orbit', '{s}.binary_masses', '{s}.gaia_source')").format(s=schema)
    cols = {}
    for r in s0.tap(q):
        t = str(r.get("table_name", "")).split(".")[-1].strip().lower()
        cols.setdefault(t, set()).add(str(r.get("column_name", "")).strip().lower())
    return cols


# ================================================================ self-test
def self_test():
    checks = []
    checks.append(villanova_status_v2("<p>No associated EB entries found.</p>") is False)
    checks.append(villanova_status_v2("<th>In catalog?</th><td> True </td>") is True)
    checks.append(villanova_status_v2("<th>In catalog?</th><td>False</td>") is False)
    checks.append(villanova_status_v2("<html>Bad Request</html>") is None)
    checks.append(villanova_status_v2("") is None)
    tsv = ("#   VizieR Astronomical Server\n#INFO\tQUERY_STATUS=OK\n#\n_RAJ2000\t_DEJ2000\tTIC\n deg\t deg\t \n"
           "--------\t--------\t----\n104.1\t-12.3\t238162238\n104.2\t-12.4\t1\n\n#END\n")
    err, tabs = parse_asu_tsv(tsv)
    checks.append(not err and len(tabs) == 1 and n_rows(tabs) == 2
                  and tabs[0]["header"][2] == "TIC" and tabs[0]["rows"][0][2] == "238162238")
    empty = "#   VizieR Astronomical Server\n#INFO\tQUERY_STATUS=OK\n"
    err, tabs = parse_asu_tsv(empty)
    checks.append(not err and n_rows(tabs) == 0)
    err, _ = parse_asu_tsv("#   VizieR\n#INFO\tQUERY_STATUS=ERROR\n#INFO Error=The database is "
                           "not currently reachable.\n")
    checks.append(err)
    err, _ = parse_asu_tsv("<html><body>502 Bad Gateway</body></html>")
    checks.append(err)
    checks.append(abs(to_deg("09 25 44.37", True) - 141.434875) < 1e-5)
    checks.append(abs(to_deg("-29 19 37.2", False) + 29.327) < 1e-5)
    checks.append(abs(to_deg("141.43487", True) - 141.43487) < 1e-9)
    base = {"tce_class": "HALF", "gaia_eb": False, "gaia_ecl_sb2": False, "gaia_class": ""}
    allno = dict(base, **{k: False for k in LOOKUPS})
    checks.append(classify_new_v2(allno) == "NEW_V2")
    checks.append(classify_new_v2(dict(allno, villanova=None)) == "UNVETTED")
    checks.append(classify_new_v2(dict(allno, villanova=None, tessebs_viz=True)) == "KNOWN")
    checks.append(classify_new_v2(dict(allno, tce_class="NONE")) == "NO_MATCHING_TCE")
    full = {"nss_two_body_orbit": set(REQ_NSS), "gaia_source": set(REQ_GS),
            "binary_masses": set(REQ_BM)}
    checks.append(schema_gate(full) == "A")
    checks.append(schema_gate(dict(full, binary_masses=set())) == "B")
    checks.append(schema_gate(dict(full, nss_two_body_orbit={"source_id"})) == "G0")

    def fake_get(url, accept_404=False):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if "-c" in q:
            ra = float(q["-c"][0].split()[0])
            return tsv if abs(ra - 104.1) < 0.01 else empty
        return tsv

    info = viz_setup("X/Y", fake_get)
    checks.append(info["mode"] == "cone")
    checks.append(viz_lookup(info, 104.1, -12.3, "5", fake_get) is True)
    checks.append(viz_lookup(info, 200.0, 10.0, "5", fake_get) is False)
    checks.append(viz_lookup({"mode": None}, 104.1, -12.3, "5", fake_get) is None)
    ok = all(checks)
    return ok, [i for i, c in enumerate(checks) if not c]


# ================================================================ rehearsal on DR3 output
def read_text(src):
    if re.match(r"https?://", src):
        return get_text(src)
    with open(src, encoding="utf-8") as fh:
        return fh.read()


def rehearse(args):
    os.makedirs(args.out_dir, exist_ok=True)
    meta = {"version": VERSION, "base_sha": BASE_SHA, "mode": "rehearse-dr3",
            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        rows = list(csv.DictReader(io.StringIO(read_text(args.rehearse_csv))))
        vet = list(csv.DictReader(io.StringIO(read_text(args.vetting_csv))))
    except Exception as exc:
        json.dump({"error": "inputs unavailable: %r" % exc, "meta": meta},
                  open(os.path.join(args.out_dir, "g5_rehearsal_summary.json"), "w"), indent=1)
        return 2
    try:
        cols = discover("gaiadr3")
        meta["tap_schema_gaiadr3"] = {k: sorted(v) for k, v in cols.items()}
        meta["schema_gate_gaiadr3"] = schema_gate(cols)
    except Exception as exc:
        meta["tap_schema_gaiadr3"] = "unavailable: %r" % exc
        meta["schema_gate_gaiadr3"] = "UNTESTED"
    ctrl = lookup_controls()
    log("controls", json.dumps(ctrl))
    recs = []
    for r in rows:
        if r.get("tce_class") not in ("HALF", "FULL"):
            continue
        rec = dict(r)
        for k in ("vsx_eclipsing", "simbad_eb", "gaia_eb", "gaia_ecl_sb2"):
            rec[k] = parse_bool(r.get(k))
        rec["toi_known"] = bool(str(r.get("toi", "")).strip())
        run_lookups(rec, ctrl)
        recs.append(rec)
        log(rec.get("tic"), rec.get("villanova"), rec.get("tessebs_viz"), rec.get("t10k_viz"),
            rec["new_v2"])
        time.sleep(s0.PAUSE)
    keys = ["source_id", "tic", "G", "P_gaia", "tce_class", "vsx_eclipsing", "simbad_eb", "toi",
            "gaia_eb", "gaia_class", "villanova", "tessebs_viz", "t10k_viz", "new_v2"]
    with open(os.path.join(args.out_dir, "g5_rehearsal_rows.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for rec in recs:
            w.writerow({k: s0.fmt(rec.get(k, "")) for k in keys})
    # R1: Villanova repaired?
    by_tic = {str(r.get("tic")): r for r in recs}
    comp = []
    for v in vet:
        tic = str(v.get("tic", "")).strip()
        expect = str(v.get("prsa2022_tess_eb", "")).strip().lower().startswith("yes")
        got = by_tic.get(tic, {}).get("villanova")
        comp.append({"tic": tic, "name": v.get("name"), "expected": expect, "got": got,
                     "match": got is expect})
    n_match = sum(1 for c in comp if c["match"])
    r1 = ("LOOKUP_REPAIRED" if ctrl["villanova"]["ok"] and n_match >= len(comp) - 1
          else "LOOKUP_STILL_BROKEN")
    # R2, R3
    counts = {}
    for rec in recs:
        counts[rec["new_v2"]] = counts.get(rec["new_v2"], 0) + 1
    n_cells = len(recs) * len(LOOKUPS)
    n_def = sum(1 for rec in recs for k in LOOKUPS if rec.get(k) is not None)
    share = n_def / n_cells if n_cells else float("nan")
    summary = {
        "R1": {"label": r1, "villanova_controls": ctrl["villanova"], "n_vetted": len(comp),
               "n_match": n_match, "rows": comp},
        "R2": {"counts": counts,
               "new_v2": [{"tic": r.get("tic"), "source_id": r.get("source_id"), "G": r.get("G")}
                          for r in recs if r["new_v2"] == "NEW_V2"],
               "unvetted": [r.get("tic") for r in recs if r["new_v2"] == "UNVETTED"]},
        "R3": {"definite_share": share, "n_cells": n_cells,
               "label": "LOOKUPS_DEFINITE" if share >= 0.95 else "LOOKUPS_GAPS"},
        "viz_controls": {k: ctrl[k] for k, _ in VIZ_CATS},
        "meta": meta,
    }
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    json.dump(s0.clean(summary), open(os.path.join(args.out_dir, "g5_rehearsal_summary.json"), "w"),
              indent=1)
    print(json.dumps({"R1": r1, "R2": counts, "R3": summary["R3"]["label"]}))
    return 0


# ================================================================ the screen (release day)
def screen(args):
    os.makedirs(args.out_dir, exist_ok=True)
    meta = {"version": VERSION, "base_sha": BASE_SHA, "schema": args.schema,
            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    out_sum = os.path.join(args.out_dir, "g5_summary.json")
    try:
        cols = discover(args.schema)
    except Exception as exc:
        json.dump({"error": "TAP_SCHEMA unavailable: %r" % exc, "meta": meta}, open(out_sum, "w"),
                  indent=1)
        return 2
    gate = schema_gate(cols)
    meta.update({"arm": gate, "columns": {k: sorted(v) for k, v in cols.items()}})
    if gate == "G0":
        json.dump({"error": "schema gate G0: required columns missing", "meta": meta},
                  open(out_sum, "w"), indent=1)
        return 4
    try:
        if gate == "A":
            rows = s0.tap(s0.ORBIT_QUERY.format(s=args.schema))
            sel = s0.select_rows(rows)
            sel.sort(key=lambda r: fnum(r.get("phot_g_mean_mag"), 99))
        else:
            rows = s0.tap(ARM_B_QUERY.format(s=args.schema))
            sel = select_rows_b(rows)
    except Exception as exc:
        json.dump({"error": "orbit query failed: %r" % exc, "meta": meta}, open(out_sum, "w"),
                  indent=1)
        return 2
    meta.update({"n_orbit_rows": len(rows), "n_selected": len(sel)})
    with open(os.path.join(args.out_dir, "g5_orbits.csv"), "w", newline="") as fh:
        if rows:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    if args.limit:
        sel = sel[:args.limit]
    ids = [r["source_id"] for r in sel]
    eb_ids, gclass = set(), {}
    try:
        eb_ids = {r["source_id"] for r in s0.tap_ids(
            "SELECT source_id FROM {s}.vari_eclipsing_binary WHERE source_id IN ({ids})",
            ids, args.schema)}
        for r in s0.tap_ids("SELECT source_id, best_class_name FROM {s}.vari_classifier_result "
                            "WHERE source_id IN ({ids})", ids, args.schema):
            gclass[r["source_id"]] = r.get("best_class_name", "")
    except Exception as exc:
        meta["gaia_tables_error"] = repr(exc)[:200]   # recorded; Gaia's own tables then unknown
    gaia_tables_ok = "gaia_tables_error" not in meta
    ctrl = lookup_controls()
    meta["lookup_controls"] = ctrl
    log("controls", json.dumps(ctrl))
    recs = []
    for n, r in enumerate(sel):
        sid = r["source_id"]
        rec = {k: "" for k in KEYS}
        rec.update({"source_id": sid, "in_pilot": False, "G": fnum(r.get("phot_g_mean_mag")),
                    "ra": fnum(r.get("ra")), "dec": fnum(r.get("dec")),
                    "P_gaia": fnum(r.get("period")), "P_gaia_err": fnum(r.get("period_error")),
                    "ecc": fnum(r.get("eccentricity")), "K1": fnum(r.get("semi_amplitude_primary")),
                    "K2": fnum(r.get("semi_amplitude_secondary")), "m1": fnum(r.get("m1")),
                    "m2": fnum(r.get("m2")), "m1sin3i": r["m1sin3i"], "s3_ratio": r["s3_ratio"],
                    "gaia_eb": (sid in eb_ids) if gaia_tables_ok else None, "gaia_ecl_sb2": False,
                    "gaia_class": gclass.get(sid, "")})
        try:
            tic = s0.parse_tic(get_text(s0.EXOFOP_TIC % sid))
            time.sleep(s0.PAUSE)
            if not tic:
                rec["status"] = "NO_TIC"
                recs.append(rec)
                continue
            rec["tic"] = tic
            lst = s0.parse_tce_list(get_text(s0.TCE_LIST % tic, accept_404=True))
            time.sleep(s0.PAUSE)
            tces = []
            for sector, num in lst[:args.max_tces]:
                d = s0.parse_tce_info(s0.get_json(s0.TCE_INFO % (tic, num, sector)) or {})
                d["id"] = "%s:TCE_%d" % (sector, num)
                tces.append(d)
                time.sleep(s0.PAUSE)
            rec["n_tce"] = len(lst)
            cls, best, f, dev = s0.classify_tces(tces, rec["P_gaia"])
            rec["tce_class"] = cls
            if best:
                rec.update({"tce_best_id": best["id"], "tce_best_period": best["period"],
                            "tce_best_factor": f, "tce_best_dev_pct": 100.0 * dev,
                            "tce_best_depth_ppm": best["depth_ppm"],
                            "tce_best_snr": best["snr"], "tce_best_dur_h": best["dur_h"]})
            if cls in ("HALF", "FULL"):
                v = s0.get_json(s0.VSX_URL % (rec["ra"], rec["dec"], s0.VSX_RADIUS_DEG))
                objs = s0.vsx_objects(v) if v is not None else None
                if objs is not None:
                    rec["vsx_names"] = "|".join(o.get("Name", "") for o in objs)
                    rec["vsx_types"] = "|".join(o.get("VariabilityType", "") for o in objs)
                    rec["vsx_eclipsing"] = any(s0.is_eclipsing_type(o.get("VariabilityType"))
                                               for o in objs)
                else:
                    rec["vsx_eclipsing"] = None
                t = s0.get_json(s0.EXOFOP_TARGET % tic)
                if t is None:
                    rec["toi_known"] = None
                else:
                    tois = t.get("tois") or []
                    tois = tois if isinstance(tois, list) else [tois]
                    rec["toi"] = "|".join(str(x.get("toi", x.get("TOI", "TOI"))) if isinstance(x, dict)
                                          else str(x) for x in tois)
                    rec["toi_known"] = bool(tois)
                try:
                    eb, main = s0.simbad_flags(get_text(s0.SIMBAD % (rec["ra"], rec["dec"],
                                                                     s0.SIMBAD_RADIUS_ARCSEC)))
                except Exception:
                    eb, main = None, ""
                rec["simbad_eb"], rec["simbad_main"] = eb, main
                run_lookups(rec, ctrl)
            else:
                rec["new_v2"] = classify_new_v2(rec)
            rec["status"] = "OK"
        except Exception as exc:
            rec["status"] = "ERROR"
            rec["error"] = repr(exc)[:300]
        recs.append(rec)
        log("[%d/%d]" % (n + 1, len(sel)), sid, rec.get("tic"), rec.get("status"),
            rec.get("tce_class"), rec.get("new_v2"))
        if (n + 1) % 20 == 0:
            write_rows(os.path.join(args.out_dir, "g5_screen.csv"), recs)
    write_rows(os.path.join(args.out_dir, "g5_screen.csv"), recs)
    g = s0.grade(recs, len(ids), 0)
    tested = [r for r in recs if r.get("status") == "OK"]
    new2 = [r for r in tested if r.get("new_v2") == "NEW_V2"]
    unv = [r for r in tested if r.get("new_v2") == "UNVETTED"]
    g["S0"]["label"] = "NOT_APPLICABLE_DR4"
    g["S2_v2"] = {"n_new_v2": len(new2), "n_unvetted": len(unv),
                  "label": "YES" if len(new2) >= NEW_V2_MIN_DR4 else "NO",
                  "new_v2": [{"source_id": r["source_id"], "tic": r.get("tic"), "G": r.get("G"),
                              "P_gaia": r.get("P_gaia"), "tce_class": r.get("tce_class"),
                              "depth_ppm": r.get("tce_best_depth_ppm")} for r in new2],
                  "unvetted": [r.get("tic") for r in unv]}
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    json.dump(s0.clean({"grades": g, "meta": meta}), open(out_sum, "w"), indent=1)
    print(json.dumps(s0.clean({"arm": gate, "S1": g["S1"]["label"], "S3": g["S3"]["label"],
                               "S2_v2": g["S2_v2"]["label"], "n_new_v2": len(new2)})))
    return 0 if len(tested) >= 0.5 * max(1, len(sel)) else 2


def write_rows(path, recs):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=KEYS, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            w.writerow({k: s0.fmt(r.get(k, "")) for k in KEYS})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--rehearse-csv", default="")
    ap.add_argument("--vetting-csv", default="")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--schema", default="gaiadr4")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-tces", type=int, default=40)
    a = ap.parse_args(argv)
    if a.self_test:
        ok, bad = self_test()
        print("SELF_TEST", "PASS" if ok else "FAIL", bad)
        return 0 if ok else 3
    if a.rehearse_csv:
        return rehearse(a)
    return screen(a)


if __name__ == "__main__":
    sys.exit(main())
