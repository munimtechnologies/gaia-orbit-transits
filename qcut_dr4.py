# SPDX-License-Identifier: Apache-2.0
"""qcut_dr4 0.1.0: grade Q4 of the quality-cut test against Gaia DR4 orbit survival.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents working in his name).
Apache-2.0. Standard library only.
Pre-registration: findings/2026-11-20-quality-cut-prereg.md, section Q4 (rules unchanged here).
Written and committed on 2026-11-20, before Gaia DR4 (2 December 2026) and before qcut 0.1.0
had produced any output.

Inputs (all files; nothing is fetched):
  --records  sb1_reality_records.csv from dr4_sb1_reality on the DR4 schema (one row per DR3
             source of the S3 pool; columns used: source_id = DR3 id, label in
             CONFIRMED / ALIAS / CHANGED / DROPPED / UNTESTABLE).
  --columns  qcut_columns.csv from job gaia-qcut-v1 (DR3 quality columns of the whole S3 pool,
             fixed before DR4).
  --stars    qcut_stars.csv from the same job (rate-sample stars with star_hit), for Q4c.

Rules (pre-registered):
  f_conf = CONFIRMED / testable (UNTESTABLE excluded), Wilson 95 % intervals, whole S3 pool,
  all classes.
  Q4a  f_conf(gold) > f_conf(not gold), intervals not overlapping (gold lower > not-gold upper).
  Q4b  f_conf(T3) > f_conf(T1), intervals not overlapping.
  Q4c  rate-sample stars with a transit hit are CONFIRMED more often than those without:
       one-sided Fisher exact test, p < 0.05 (descriptive: ~8 of the 25 hits are false alarms).
  Q4d  exploratory: AUC of each Q3 column for CONFIRMED vs DROPPED + CHANGED (ALIAS and
       UNTESTABLE left out), oriented so that 1 means the column's pre-registered "better"
       direction picks CONFIRMED. Reported, not graded.
Gold, tier and amplitude-ratio rules are imported from qcut 0.1.0 (pinned), not copied. For the
whole pool, K in A = rv_amplitude_robust / (2K) is the column semi_amplitude_primary.

Self-check (exit 3, no grade): at least 99 % of records have a qcut_columns row (QC1), and at
least 1 testable record exists (QC2). Unmatched records are listed and left out.
Exit codes: 0 ok; 1 bad input file; 3 a self-check failed.
"""
import argparse
import csv
import json
import math
import os
import sys

import qcut

VERSION = "0.1.0"
LABELS = ("CONFIRMED", "ALIAS", "CHANGED", "DROPPED", "UNTESTABLE")
MATCH_MIN = 0.99
ALPHA_Q4C = 0.05


def wilson(k, n, z=1.959964):
    """Wilson score interval; the same formula as dr4_sb1_reality.wilson."""
    if n <= 0:
        return [None, None]
    p = k / float(n)
    den = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4.0 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def frac(recs):
    test = [r for r in recs if r["label"] != "UNTESTABLE"]
    k = sum(1 for r in test if r["label"] == "CONFIRMED")
    n = len(test)
    return {"n": len(recs), "n_testable": n, "n_confirmed": k,
            "f_conf": (k / float(n)) if n else None, "ci95": wilson(k, n)}


def compare(better, worse):
    """Pass if better.f_conf > worse.f_conf and the Wilson intervals do not overlap."""
    ok = better["f_conf"] is not None and worse["f_conf"] is not None
    return bool(ok and better["f_conf"] > worse["f_conf"] and better["ci95"][0] > worse["ci95"][1])


def _lnc(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_greater(a, b, c, d):
    """One-sided Fisher exact p for the 2x2 table [[a, b], [c, d]]:
    P(X >= a) under the hypergeometric with fixed margins (row 1 = hit, col 1 = CONFIRMED)."""
    r1, c1, n = a + b, a + c, a + b + c + d
    if n == 0 or r1 == 0 or c1 == 0:
        return None
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    den = _lnc(n, r1)
    p = 0.0
    for x in range(max(a, lo), hi + 1):
        p += math.exp(_lnc(c1, x) + _lnc(n - c1, r1 - x) - den)
    return min(1.0, p)


def auc(pos, neg):
    """P(score_pos > score_neg) + 0.5 P(tie); None if a side is empty."""
    if not pos or not neg:
        return None
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank_sum, i = 0.0, 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        avg = (i + 1 + j) / 2.0                # mean of ranks i+1..j
        rank_sum += avg * sum(1 for t in allv[i:j] if t[1] == 1)
        i = j
    n1, n0 = len(pos), len(neg)
    return (rank_sum - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def truthy(v):
    return str(v).strip().lower() in ("true", "1", "yes", "1.0")


def read_csv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def column_value(q, col):
    if col == "amp_ratio":
        return qcut.amp_ratio(q, qcut.num(q.get("semi_amplitude_primary")))
    return qcut.num(q.get(col))


def grade(records, columns, stars):
    qmap = {str(q.get("source_id", "")).strip(): q for q in columns}
    recs, unmatched, bad_label = [], [], []
    for r in records:
        sid = str(r.get("source_id", "")).strip()
        lab = str(r.get("label", "")).strip()
        if lab not in LABELS:
            bad_label.append(sid)
            continue
        q = qmap.get(sid)
        if q is None:
            unmatched.append(sid)
            continue
        recs.append({"source_id": sid, "label": lab, "q": q, "gold": qcut.is_gold(q),
                     "gold_sb1": qcut.is_gold(q, sb1_only=True),
                     "tier": qcut.tier(qcut.num(q.get("significance")))})
    n_in = len(records) - len(bad_label)
    match_share = len(recs) / float(n_in) if n_in else 0.0
    allf = frac(recs)
    checks = {"QC1_records_matched_ge_99pct": [len(recs), n_in, match_share >= MATCH_MIN],
              "QC2_some_testable": [allf["n_testable"], 1, allf["n_testable"] >= 1]}
    res = {"version": VERSION, "qcut_version": qcut.VERSION, "n_records": len(records),
           "n_matched": len(recs), "unmatched": unmatched[:50], "n_unmatched": len(unmatched),
           "bad_label": bad_label[:50], "checks": checks,
           "labels": {k: sum(1 for r in recs if r["label"] == k) for k in LABELS}, "all": allf}
    if not all(v[2] for v in checks.values()):
        res["stopped"] = "a self-check failed; no grade"
        return res, False
    g, ng = frac([r for r in recs if r["gold"]]), frac([r for r in recs if not r["gold"]])
    gs, ngs = frac([r for r in recs if r["gold_sb1"]]), frac([r for r in recs if not r["gold_sb1"]])
    res["Q4a"] = {"rule": "f_conf(gold) > f_conf(not gold), Wilson 95% intervals not overlapping",
                  "gold": g, "not_gold": ng, "pass": compare(g, ng),
                  "secondary_sb1_only": {"gold": gs, "not_gold": ngs, "pass": compare(gs, ngs)}}
    tiers = {name: frac([r for r in recs if r["tier"] == name]) for _, _, name in qcut.TIERS}
    tiers["none"] = frac([r for r in recs if not r["tier"]])
    res["Q4b"] = {"rule": "f_conf(T3) > f_conf(T1), Wilson 95% intervals not overlapping",
                  "tiers": tiers, "pass": compare(tiers["T3"], tiers["T1"])}
    lab = {r["source_id"]: r["label"] for r in recs}
    a = b = c = d = 0
    n_star_unmatched = 0
    for s in stars:
        sid = str(s.get("source_id", "")).strip()
        L = lab.get(sid)
        if L is None:
            n_star_unmatched += 1
            continue
        if L == "UNTESTABLE":
            continue
        hit, conf = truthy(s.get("star_hit")), L == "CONFIRMED"
        if hit and conf:
            a += 1
        elif hit:
            b += 1
        elif conf:
            c += 1
        else:
            d += 1
    p = fisher_greater(a, b, c, d)
    res["Q4c"] = {"rule": "hit stars CONFIRMED more often than non-hit stars, one-sided Fisher p < 0.05 "
                          "(descriptive)",
                  "table": {"hit_confirmed": a, "hit_not": b, "nohit_confirmed": c, "nohit_not": d},
                  "f_conf_hit": a / float(a + b) if a + b else None,
                  "f_conf_nohit": c / float(c + d) if c + d else None,
                  "p_one_sided": p, "pass": p is not None and p < ALPHA_Q4C,
                  "n_stars": len(stars), "n_stars_without_record": n_star_unmatched}
    q4d = {}
    for col, better in qcut.Q3_COLUMNS:
        sign = 1.0 if better == "high" else -1.0
        pos, neg, miss = [], [], 0
        for r in recs:
            if r["label"] not in ("CONFIRMED", "DROPPED", "CHANGED"):
                continue
            v = column_value(r["q"], col)
            if not qcut.finite(v):
                miss += 1
                continue
            (pos if r["label"] == "CONFIRMED" else neg).append(sign * v)
        q4d[col] = {"better": better, "auc": auc(pos, neg), "n_confirmed": len(pos),
                    "n_dropped_or_changed": len(neg), "n_missing": miss}
    ranked = sorted((k for k in q4d if q4d[k]["auc"] is not None), key=lambda k: -q4d[k]["auc"])
    res["Q4d"] = {"rule": "exploratory, AUC (1 = the pre-registered better direction picks CONFIRMED)",
                  "columns": q4d, "ranking": ranked}
    return res, True


def report(res):
    def f(x):
        return "n/a" if x is None else "%.3f" % x

    def line(name, fr):
        lo, hi = fr["ci95"]
        return "| %s | %d | %d | %d | %s | %s-%s |" % (name, fr["n"], fr["n_testable"], fr["n_confirmed"],
                                                     f(fr["f_conf"]), f(lo), f(hi))
    L = ["# qcut_dr4 %s: Gaia DR3 quality columns vs DR4 orbit survival" % res["version"], "",
         "Self-checks: " + json.dumps(res["checks"]), "", "Labels: " + json.dumps(res["labels"]), ""]
    if res.get("stopped"):
        return "\n".join(L + ["**" + res["stopped"] + "**", ""])
    H = ["| group | n | testable | CONFIRMED | f_conf | Wilson 95% |", "|---|---|---|---|---|---|"]
    L += ["## Q4a: gold sample: pass = %s" % res["Q4a"]["pass"], ""] + H + [
        line("all", res["all"]), line("gold", res["Q4a"]["gold"]), line("not gold", res["Q4a"]["not_gold"]),
        line("gold (SB1 only)", res["Q4a"]["secondary_sb1_only"]["gold"]), "",
        "## Q4b: significance tiers: pass = %s" % res["Q4b"]["pass"], ""] + H + [
        line(k, v) for k, v in res["Q4b"]["tiers"].items()]
    c = res["Q4c"]
    L += ["", "## Q4c: transit hits (descriptive): pass = %s" % c["pass"], "",
          "table %s; f_conf hit %s vs no hit %s; one-sided Fisher p = %s" % (
              json.dumps(c["table"]), f(c["f_conf_hit"]), f(c["f_conf_nohit"]), f(c["p_one_sided"])), "",
          "## Q4d (exploratory): AUC, CONFIRMED vs DROPPED + CHANGED", "",
          "| column | better | AUC | n CONFIRMED | n DROPPED/CHANGED | missing |", "|---|---|---|---|---|---|"]
    for k in res["Q4d"]["ranking"]:
        v = res["Q4d"]["columns"][k]
        L.append("| %s | %s | %s | %d | %d | %d |" % (k, v["better"], f(v["auc"]), v["n_confirmed"],
                                                      v["n_dropped_or_changed"], v["n_missing"]))
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--records", required=True)
    ap.add_argument("--columns", required=True)
    ap.add_argument("--stars", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    try:
        records, columns, stars = read_csv(a.records), read_csv(a.columns), read_csv(a.stars)
    except (OSError, csv.Error) as exc:
        print("input error:", exc)
        return 1
    os.makedirs(a.out_dir, exist_ok=True)
    res, ok = grade(records, columns, stars)
    with open(os.path.join(a.out_dir, "qcut_dr4_summary.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    with open(os.path.join(a.out_dir, "qcut_dr4_report.md"), "w") as fh:
        fh.write(report(res))
    if not ok:
        print(json.dumps({"stopped": res["stopped"], "checks": res["checks"]}))
        return 3
    print(json.dumps({"Q4a": res["Q4a"]["pass"], "Q4b": res["Q4b"]["pass"], "Q4c": res["Q4c"]["pass"],
                      "Q4c_p": res["Q4c"]["p_one_sided"], "Q4d_ranking": res["Q4d"]["ranking"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
