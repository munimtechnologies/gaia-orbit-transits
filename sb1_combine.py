# SPDX-License-Identifier: Apache-2.0
"""sb1_combine 0.1.0: combine the eight sb1_robust 0.2.0 chunks and grade them.

MV2 of Munim, Inc.; made with AI agents working in his name. Apache-2.0. Standard library only.

What it does
------------
1. Reads each chunk's sb1_stars.csv (and sb1_summary.json if present), either from local
   folders (--chunk-dir, repeatable) or from a base URL (--fetch BASE --chunks 0-7), where
   BASE/k<i>/sb1_stars.csv is the layout of data/sb1rob-v1/ in the public repo.
2. Recomputes the rate summary exactly as sb1_transit.rate_summary does (rate sample = status
   OK, not a control, sensitivity >= 0.5; E = sum p_transit * sensitivity; control hits
   averaged over the control periods; Garwood 95 % interval of the hit count), on all chunks
   together (deduplicated by source_id), and splits it by companion class, period and primary
   mass. This is the PRIMARY grade of findings/2026-11-18-sb1-robust-prereg.md.
3. Applies amendment 1 (findings/2026-11-19-sb1-robust-amendment-1.md) as a SECONDARY grade:
   the same numbers after removing stars whose primary radius is not a dwarf radius we can
   trust (radius_flag below). The primary grade is not changed by the amendment.

Why the amendment exists: sb1_transit 0.1.0 falls back to a main-sequence M_G table for the
primary's radius when Gaia gives neither a FLAME nor a GSP-Phot radius. The table stops at
M_G = 0.5 (r1 = 1.9 R_sun), and interp() clamps anything brighter to that value, which is below
the R1_MAX = 2.5 R_sun "evolved" cut. Luminous giants with no Gaia radius therefore entered the
sample with r1 = 1.9 R_sun and an expected transit depth many times the real one. Their
expected transits count in E but a real companion could not be seen, so rho is biased low.
"""
import argparse
import csv
import io
import json
import math
import os
import sys
import urllib.error
import urllib.request

VERSION = "0.1.0"
SENS_MIN = 0.5
MG_TABLE_BRIGHT = 0.5      # bright end of sb1_transit._MG; interp clamps at or above it
R_CLAMP = 1.9              # sb1_transit._RAD[0]
GIANT_BPRP = 1.0           # amendment 1, rule (b): red and luminous = giant branch / clump
GIANT_MG = 3.5
M1_BINS = (("m1<1.2", 0.0, 1.2), ("1.2<=m1<1.5", 1.2, 1.5), ("m1>=1.5", 1.5, 99.0))
P_BINS = (("P<5", 0.0, 5.0), ("P>=5", 5.0, 99.0))
CLASSES = ("planet", "BD", "VLMS")


# ------------------------------------------------------------------ small helpers
def num(v, default=float("nan")):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return x


def truthy(v):
    if isinstance(v, bool):
        return v
    return str(v).strip() in ("True", "true", "1")


def poisson_cdf(n, mu):
    if n < 0:
        return 0.0
    term = math.exp(-mu)
    s = term
    for k in range(1, n + 1):
        term *= mu / k
        s += term
    return min(1.0, s)


def garwood(n, cl=0.95):
    """Exact (Garwood) central interval for a Poisson mean given n counts (as sb1_robust)."""
    a = (1.0 - cl) / 2.0

    def bisect(fn, lo, hi):
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if fn(mid):
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)
    hi_b = 10.0 + 10.0 * n
    lower = 0.0 if n == 0 else bisect(lambda mu: 1.0 - poisson_cdf(n - 1, mu) >= a, 0.0, hi_b)
    upper = bisect(lambda mu: poisson_cdf(n, mu) <= a, 0.0, hi_b)
    return lower, upper


def control_keys(row):
    """The control-period columns present in a row: [(hit_col, class_col), ...]."""
    ks = sorted(k for k in row if k.startswith("ctrl_") and k.endswith("_hit"))
    return [(k, k[:-4] + "_class") for k in ks]


# ------------------------------------------------------------------ amendment 1 rule
# sb1_transit 0.1.0's main-sequence fallback table (copied unchanged)
_MG = [0.5, 1.5, 2.5, 3.5, 4.4, 5.0, 5.6, 6.2, 6.9, 7.6, 8.4, 9.2, 10.0, 10.8, 11.6]
_RAD = [1.9, 1.6, 1.35, 1.15, 1.0, 0.9, 0.82, 0.75, 0.68, 0.62, 0.55, 0.48, 0.40, 0.31, 0.25]


def interp(x, xs, ys):
    """sb1_transit.interp, unchanged: clamps outside the table."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            w = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + w * (ys[i] - ys[i - 1])
    return ys[-1]


def table_radius(row):
    """True if r1 is the main-sequence table value for this star's M_G (no Gaia radius)."""
    absg = num(row.get("abs_g"))
    r1 = num(row.get("r1"))
    return math.isfinite(absg) and math.isfinite(r1) and abs(r1 - interp(absg, _MG, _RAD)) < 1e-9


def radius_flag(row):
    """Amendment 1: why this star's primary radius cannot be trusted ('' if it can).

    Only stars whose r1 came from the main-sequence fallback table (no FLAME or GSP-Phot
    radius) can be flagged; a Gaia radius is always kept.
    (a) 'clamped': table radius and M_G <= 0.5, the table's bright end, where interp clamps
        to 1.9 R_sun whatever the star's real size.
    (b) 'giant_cmd': table radius, BP-RP > 1.0 and M_G < 3.5. That is the red-giant branch
        and clump, where a main-sequence radius does not apply. M_G is not corrected for
        extinction, which only makes a dwarf look fainter, so a reddened dwarf is not flagged.
    (c) 'no_distance': no usable parallax (M_G undefined) and r1 is the 1.0 R_sun default.
    """
    absg = num(row.get("abs_g"))
    bprp = num(row.get("bp_rp"))
    r1 = num(row.get("r1"))
    if table_radius(row):
        if absg <= MG_TABLE_BRIGHT:
            return "clamped"
        if math.isfinite(bprp) and bprp > GIANT_BPRP and absg < GIANT_MG:
            return "giant_cmd"
    if not math.isfinite(absg) and math.isfinite(r1) and abs(r1 - 1.0) < 1e-12:
        return "no_distance"
    return ""


# ------------------------------------------------------------------ rates
def in_rate_sample(r):
    return (str(r.get("status", "")).strip() == "OK" and not str(r.get("control") or "").strip()
            and num(r.get("sensitivity"), 0.0) >= SENS_MIN)


def rho(n, fa, E):
    if not (E > 0):
        return {"rho": None, "ci95": [None, None]}
    lo, hi = garwood(int(n))
    return {"rho": (n - fa) / E, "ci95": [max(0.0, (lo - fa) / E), max(0.0, (hi - fa) / E)]}


def rate_summary(rows):
    """Same quantities as sb1_transit.rate_summary, on csv-string rows."""
    S = [r for r in rows if in_rate_sample(r)]
    n_hit = sum(1 for r in S if truthy(r.get("star_hit")))
    n_sub = sum(1 for r in S if truthy(r.get("star_hit")) and r.get("hit_class") == "SUBSTELLAR_SIZE")
    fa_all = fa_sub = 0.0
    for r in S:
        ck = control_keys(r)
        if not ck:
            continue
        fa_all += sum(1.0 for h, _ in ck if truthy(r.get(h))) / len(ck)
        fa_sub += sum(1.0 for _, c in ck if r.get(c) == "SUBSTELLAR_SIZE") / len(ck)
    E = sum(num(r.get("p_transit"), 0.0) * num(r.get("sensitivity"), 0.0) for r in S)
    v1 = sum(1 for r in S if truthy(r.get("star_hit_v1")))
    return {"n_rate_sample": len(S), "n_hit": n_hit, "n_hit_substellar_size": n_sub,
            "n_control_hits_expected": fa_all, "n_control_hits_substellar_size": fa_sub,
            "expected_if_all_real": E,
            "control_rate": (fa_all / len(S)) if S else None,
            "n_hit_v1_rule": v1,
            "n_phase_match": sum(1 for r in S if truthy(r.get("star_hit")) and r.get("phase_label") == "PHASE_MATCH"),
            "n_phase_mismatch": sum(1 for r in S if truthy(r.get("star_hit")) and r.get("phase_label") == "PHASE_MISMATCH"),
            "rho_all": rho(n_hit, fa_all, E),
            "rho_substellar_size": rho(n_sub, fa_sub, E)}


def splits(rows):
    out = {"by_class": {}, "by_period": {}, "by_m1": {}}
    for c in CLASSES:
        out["by_class"][c] = rate_summary([r for r in rows if r.get("m2_class") == c])
    for name, lo, hi in P_BINS:
        out["by_period"][name] = rate_summary([r for r in rows if lo <= num(r.get("P")) < hi])
    for name, lo, hi in M1_BINS:
        out["by_m1"][name] = rate_summary([r for r in rows if lo <= num(r.get("m1")) < hi])
    return out


def _upper(s, key="rho_substellar_size"):
    return s[key]["ci95"][1]


def grade(rows, per_chunk):
    """Pre-registered combined grades (findings/2026-11-18-sb1-robust-prereg.md)."""
    s = rate_summary(rows)
    sp = splits(rows)
    g = {}
    pools = [c.get("eligible") for c in per_chunk if c.get("eligible") is not None]
    g["R0"] = {"value": pools, "pass": (all(p == 6434 for p in pools) if pools else None)}
    c1 = [c["controls_hit"] >= 3 for c in per_chunk if c["controls_with_data"] >= 3]
    g["C1"] = {"value": [(c["chunk"], c["controls_hit"], c["controls_with_data"]) for c in per_chunk],
               "pass": all(c1) if c1 else None}
    g["C2"] = {"value": s["control_rate"], "pass": (s["control_rate"] <= 0.03) if s["control_rate"] is not None else None}
    g["C3"] = {"value": [(c["chunk"], c["n_rate_sample"]) for c in per_chunk],
               "pass": all(c["n_rate_sample"] >= 150 for c in per_chunk) if per_chunk else None}
    up = _upper(s)
    g["H1"] = {"value": up, "pass": (up < 0.5) if up is not None else None}
    g["H1b"] = {"value": up, "pass": (up < 0.2) if up is not None else None}
    lo_p, hi_p = sp["by_period"]["P<5"]["rho_all"]["rho"], sp["by_period"]["P>=5"]["rho_all"]["rho"]
    g["H2"] = {"value": [lo_p, hi_p], "pass": (hi_p > lo_p) if None not in (lo_p, hi_p) else None}
    timed = s["n_phase_match"] + s["n_phase_mismatch"]
    g["H3"] = {"value": "%d of %d timed hits match" % (s["n_phase_match"], timed),
               "pass": (s["n_phase_match"] > 0.5 * timed) if timed >= 3 else None}
    hot, cool = sp["by_m1"]["m1>=1.5"]["rho_all"]["rho"], sp["by_m1"]["m1<1.2"]["rho_all"]["rho"]
    g["H4"] = {"value": [hot, cool], "pass": (hot < cool) if None not in (hot, cool) else None}
    v1 = s["n_hit_v1_rule"]
    rej = sum(1 for r in rows if in_rate_sample(r) and truthy(r.get("star_hit_v1")) and not truthy(r.get("star_hit")))
    g["R1"] = {"value": (rej / float(v1)) if v1 else None, "n_v1": v1, "n_rejected": rej}
    d1 = [{"source_id": r.get("source_id"), "tic": r.get("tic"), "P": num(r.get("P")),
           "m2_class": r.get("m2_class"), "radius_flag": radius_flag(r)}
          for r in rows if in_rate_sample(r) and truthy(r.get("star_hit"))
          and r.get("hit_class") == "SUBSTELLAR_SIZE" and not str(r.get("toi") or "").strip()]
    g["D1"] = {"value": d1}
    return s, sp, g


# ------------------------------------------------------------------ inputs
def read_csv_text(text):
    return [dict(r) for r in csv.DictReader(io.StringIO(text))]


def chunk_info(name, rows, summary):
    ctl = [r for r in rows if str(r.get("control") or "").strip() and str(r.get("status", "")).strip() == "OK"]
    return {"chunk": name, "eligible": (summary or {}).get("eligible"),
            "n_rows": len(rows), "n_rate_sample": sum(1 for r in rows if in_rate_sample(r)),
            "controls_with_data": len(ctl), "controls_hit": sum(1 for r in ctl if truthy(r.get("star_hit")))}


def merge(chunks):
    """chunks: list of (name, rows). Rate-sample rows deduplicated by source_id (first wins)."""
    seen, out, dups = set(), [], 0
    for name, rows in chunks:
        for r in rows:
            sid = str(r.get("source_id", "")).strip()
            if in_rate_sample(r):
                if sid in seen:
                    dups += 1
                    continue
                seen.add(sid)
            r = dict(r)
            r["_chunk"] = name
            out.append(r)
    return out, dups


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "mv2-sb1-combine/" + VERSION})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return fh.read().decode("utf-8")


def load_chunks(dirs=None, base=None, chunk_ids=()):
    loaded, missing = [], []
    for d in dirs or []:
        p = os.path.join(d, "sb1_stars.csv")
        if not os.path.exists(p):
            missing.append(d)
            continue
        with open(p, newline="") as fh:
            rows = read_csv_text(fh.read())
        sj = os.path.join(d, "sb1_summary.json")
        summ = json.load(open(sj)) if os.path.exists(sj) else None
        loaded.append((os.path.basename(os.path.normpath(d)), rows, summ))
    for i in chunk_ids:
        name = "k%d" % i
        try:
            rows = read_csv_text(_get("%s/%s/sb1_stars.csv" % (base.rstrip("/"), name)))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                missing.append(name)
                continue
            raise
        try:
            summ = json.loads(_get("%s/%s/sb1_summary.json" % (base.rstrip("/"), name)))
        except urllib.error.HTTPError:
            summ = None
        loaded.append((name, rows, summ))
    return loaded, missing


# ------------------------------------------------------------------ report
def _fmt(x, nd=3):
    return "n/a" if x is None else ("%.*f" % (nd, x))


def _line(name, s):
    r = s["rho_substellar_size"]
    a = s["rho_all"]
    return "| %s | %d | %.1f | %d | %d | %s (%s-%s) | %s (%s-%s) |" % (
        name, s["n_rate_sample"], s["expected_if_all_real"], s["n_hit"], s["n_hit_substellar_size"],
        _fmt(a["rho"]), _fmt(a["ci95"][0]), _fmt(a["ci95"][1]),
        _fmt(r["rho"]), _fmt(r["ci95"][0]), _fmt(r["ci95"][1]))


def report(result):
    L = ["# sb1_combine %s: combined grade of sb1_robust 0.2.0" % VERSION, "",
         "Chunks used: %s. Missing: %s. Duplicate rate-sample rows dropped: %d." % (
             ", ".join(result["chunks_used"]), ", ".join(result["chunks_missing"]) or "none",
             result["duplicates_dropped"]), ""]
    for key, title in (("primary", "Primary grade (as pre-registered)"),
                       ("amendment1", "Secondary grade: amendment 1, trusted dwarf radii only")):
        blk = result[key]
        L += ["## " + title, ""]
        if key == "amendment1":
            L += ["Removed from the rate sample: %s." % json.dumps(blk["removed_by_reason"]), ""]
        L += ["| sample | rate sample | E (all real) | hits | substellar-size hits | rho_all (95%) | rho_sub (95%) |",
              "|---|---|---|---|---|---|---|", _line("all", blk["summary"])]
        for grp in ("by_class", "by_period", "by_m1"):
            for name, s in blk["splits"][grp].items():
                L.append(_line(name, s))
        L.append("")
        for k, v in blk["grades"].items():
            L.append("- **%s**: %s, pass %s" % (k, json.dumps(v.get("value")), v.get("pass")))
        L.append("")
    return "\n".join(L)


def run(loaded, missing):
    per_chunk = [chunk_info(n, rows, summ) for n, rows, summ in loaded]
    rows, dups = merge([(n, rows) for n, rows, _ in loaded])
    s, sp, g = grade(rows, per_chunk)
    kept = [r for r in rows if not (in_rate_sample(r) and radius_flag(r))]
    reasons = {}
    for r in rows:
        if in_rate_sample(r) and radius_flag(r):
            reasons[radius_flag(r)] = reasons.get(radius_flag(r), 0) + 1
    per_chunk2 = []
    for c, (n, crows, summ) in zip(per_chunk, loaded):
        c2 = dict(c)
        c2["n_rate_sample"] = sum(1 for r in crows if in_rate_sample(r) and not radius_flag(r))
        per_chunk2.append(c2)
    s2, sp2, g2 = grade(kept, per_chunk2)
    hits = [{k: r.get(k) for k in ("_chunk", "source_id", "tic", "toi", "P", "m2_class", "hit_class",
                                   "abs_g", "bp_rp", "r1", "m1_src", "ruwe")}
            for r in rows if in_rate_sample(r) and truthy(r.get("star_hit"))]
    for h in hits:
        h["radius_flag"] = radius_flag(h)
    return {"version": VERSION, "chunks_used": [n for n, _, _ in loaded], "chunks_missing": missing,
            "duplicates_dropped": dups, "per_chunk": per_chunk,
            "primary": {"summary": s, "splits": sp, "grades": g},
            "amendment1": {"summary": s2, "splits": sp2, "grades": g2, "removed_by_reason": reasons},
            "hits": hits}


def parse_chunks(spec):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        elif part.strip():
            out.append(int(part))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--chunk-dir", action="append", default=[])
    ap.add_argument("--fetch", default="")
    ap.add_argument("--chunks", default="0-7")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    loaded, missing = load_chunks(a.chunk_dir, a.fetch or None, parse_chunks(a.chunks) if a.fetch else ())
    if not loaded:
        print("no chunks found; missing:", missing)
        return 3
    res = run(loaded, missing)
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "combined_summary.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    with open(os.path.join(a.out_dir, "combined_report.md"), "w") as fh:
        fh.write(report(res))
    print(json.dumps({"chunks_used": res["chunks_used"], "missing": missing,
                      "primary": {k: res["primary"]["grades"][k].get("pass") for k in res["primary"]["grades"]},
                      "rho_sub_primary": res["primary"]["summary"]["rho_substellar_size"],
                      "rho_sub_amend1": res["amendment1"]["summary"]["rho_substellar_size"],
                      "removed": res["amendment1"]["removed_by_reason"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
