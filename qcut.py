# SPDX-License-Identifier: Apache-2.0
"""qcut 0.1.0: can Gaia's own quality columns tell real low-mass SB1 orbits from wrong ones?

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents working in his name).
Apache-2.0. Standard library only.
Pre-registration: findings/2026-11-20-quality-cut-prereg.md (written 2026-11-20, before any
quality column of the rate sample was fetched or looked at).

The question
------------
sb1_combine 0.1.0 + inclination_floor 0.1.0 found that Gaia DR3 SB1 orbits with brown-dwarf-like
minimum masses at P = 1-13 d show about 1 % (central) to 10 % (most generous population) of the
TESS transits they should, so most of them cannot be right. Gaia's own SB1 paper (Gosset et al.
2024, arXiv:2410.14372, Appendix J) recommends a "gold sample" (efficiency >= 0.2,
rv_n_good_obs_primary >= 20, significance >= 40, 2 <= P <= 800 d) whose period recovery it puts
at 93 %. This module asks, with the same transit test:
  Q1 does the gold cut select low-mass-function orbits whose transits appear as often as a real
     population predicts?  (label, pre-registered)
  Q2 do transits become more common with Gaia's significance (K / sigma_K)?  (tiers < 10, 10-20,
     >= 20; one-sided conditional test, pre-registered)
  Q3 do efficiency, rv_n_good_obs_primary, goodness_of_fit, conf_spectro_period or the
     amplitude ratio A = rv_amplitude_robust / (2 K) separate them?  (exploratory, Bonferroni)
It also saves the quality columns of the whole S3 pool (qcut_columns.csv) for the Gaia DR4
survival grade (Q4, rules in the pre-registration).

Exit codes: 0 ok; 2 Gaia archive unavailable (re-file unchanged); 3 a reproduction check failed;
4 a column the rules need is missing from the archive's answer.
"""
import argparse
import csv
import io
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "0.1.0"
TAP_SYNC = "https://gea.esac.esa.int/tap-server/tap/sync"
UA = "gaia-orbit-transits-qcut/0.1.0"

# Same selection as sb1_transit 0.1.0 (G_MAX 13.0, K^3 P < 15440, P bins 1-13 d).
G_MAX = 13.0
KP_SERVER_MAX = 15440.0
P_EDGES = (1, 1.5, 2, 3, 5, 8, 13)
ROW_LIMITS = (2000, 3000, 50000)          # a bin returning exactly this many rows is split

QCOLS = ("o.source_id, o.nss_solution_type, o.period, o.semi_amplitude_primary, o.significance, "
         "o.efficiency, o.rv_n_obs_primary, o.rv_n_good_obs_primary, o.goodness_of_fit, "
         "o.conf_spectro_period, o.flags, s.rv_amplitude_robust, s.rv_nb_transits, "
         "s.rv_chisq_pvalue, s.rv_renormalised_gof")
NEEDED = ("source_id", "nss_solution_type", "period", "semi_amplitude_primary", "significance",
          "efficiency", "rv_n_good_obs_primary", "goodness_of_fit", "conf_spectro_period",
          "rv_amplitude_robust")

# Gold sample, Gosset et al. 2024 Appendix J (applied to SB1 and SB1C alike; SB1-only is secondary)
GOLD = {"efficiency_min": 0.2, "n_good_min": 20, "significance_min": 40.0, "period_min": 2.0,
        "period_max": 800.0}
TIERS = ((None, 10.0, "T1"), (10.0, 20.0, "T2"), (20.0, None, "T3"))
PHI_BAR = 0.5
UNDERPOWERED_E_FLOOR = 7.5     # 0.5 * E < 3.69 (Garwood upper for n = 0): FAILS is impossible
ALPHA_Q2 = 0.05
ALPHA_Q3 = 0.01                # 0.05 / 5 columns
Q3_COLUMNS = (                 # (column, direction in which orbits should be MORE often real)
    ("efficiency", "high"),
    ("rv_n_good_obs_primary", "high"),
    ("goodness_of_fit", "low"),
    ("conf_spectro_period", "high"),
    ("amp_ratio", "low"),
)
LOWMASS = ("BD", "VLMS")

# reproduction targets (findings/2026-11-19-sb1-robust-combined-results.md, amendment-2 results)
REPRO = {"n_rate_sample": 3113, "E_all": 558.0, "n_hit": 25, "E_pop_central_BD": 241.1}


# ------------------------------------------------------------------ small helpers
def num(v, default=float("nan")):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def finite(x):
    return isinstance(x, float) and math.isfinite(x)


def is_gold(q, sb1_only=False):
    """Gosset et al. 2024 Appendix J gold criteria on one fetched quality row (dict of strings)."""
    if sb1_only and str(q.get("nss_solution_type", "")).strip() != "SB1":
        return False
    eff = num(q.get("efficiency"))
    ng = num(q.get("rv_n_good_obs_primary"))
    sig = num(q.get("significance"))
    p = num(q.get("period"))
    if not all(finite(x) for x in (eff, ng, sig, p)):
        return False
    return (eff >= GOLD["efficiency_min"] and ng >= GOLD["n_good_min"] and sig >= GOLD["significance_min"]
            and GOLD["period_min"] <= p <= GOLD["period_max"])


def tier(sig):
    if not finite(sig):
        return ""
    for lo, hi, name in TIERS:
        if (lo is None or sig >= lo) and (hi is None or sig < hi):
            return name
    return ""


def amp_ratio(q, K):
    a = num(q.get("rv_amplitude_robust"))
    if not (finite(a) and finite(K) and K > 0):
        return float("nan")
    return a / (2.0 * K)


def binom_sf(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    p = min(max(p, 0.0), 1.0)
    return min(1.0, sum(math.comb(n, j) * p ** j * (1.0 - p) ** (n - j) for j in range(k, n + 1)))


def cond_test(n_lo, fa_lo, E_lo, n_hi, fa_hi, E_hi):
    """One-sided test that the 'hi' group has the higher real-orbit rate.

    Under H0 both groups share rho0 = max(0, (N - fa_lo - fa_hi) / (E_lo + E_hi)); the expected
    counts are mu = fa + rho0 * E, and given N = n_lo + n_hi the 'hi' count is
    Binomial(N, mu_hi / (mu_lo + mu_hi)). p = P(X >= n_hi).
    """
    N = int(n_lo) + int(n_hi)
    if N == 0 or not (E_lo + E_hi > 0):
        return {"N": N, "rho0": None, "share_h0": None, "p_one_sided": None}
    rho0 = max(0.0, (N - fa_lo - fa_hi) / (E_lo + E_hi))
    mu_lo, mu_hi = fa_lo + rho0 * E_lo, fa_hi + rho0 * E_hi
    if not (mu_lo + mu_hi > 0):
        return {"N": N, "rho0": rho0, "share_h0": None, "p_one_sided": None}
    share = mu_hi / (mu_lo + mu_hi)
    return {"N": N, "rho0": rho0, "share_h0": share, "p_one_sided": binom_sf(int(n_hi), N, share)}


def gold_label(E_floor, phi_floor_up, phi_central_up):
    if not (E_floor >= UNDERPOWERED_E_FLOOR):
        return "UNDERPOWERED"
    if phi_floor_up is not None and phi_floor_up < PHI_BAR:
        return "GOLD_FAILS"
    if phi_central_up is not None and phi_central_up >= PHI_BAR:
        return "GOLD_PLAUSIBLE"
    return "GOLD_MIXED"


def median(xs):
    xs = sorted(x for x in xs if finite(x))
    if not xs:
        return float("nan")
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else 0.5 * (xs[m - 1] + xs[m])


# ------------------------------------------------------------------ archive
def adql(lo, hi):
    return ("SELECT " + QCOLS + " FROM gaiadr3.nss_two_body_orbit AS o JOIN gaiadr3.gaia_source AS s "
            "ON s.source_id = o.source_id WHERE o.nss_solution_type IN ('SB1','SB1C') AND o.period >= %r "
            "AND o.period < %r AND s.phot_g_mean_mag <= %r AND o.semi_amplitude_primary*"
            "o.semi_amplitude_primary*o.semi_amplitude_primary*o.period < %r"
            % (float(lo), float(hi), G_MAX, KP_SERVER_MAX))


def parse_csv(text):
    return list(csv.DictReader(io.StringIO(text)))


class ArchiveDown(Exception):
    pass


def tap_query(query, tries=4, wait=20.0):
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                   "MAXREC": "200000", "QUERY": query}).encode()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(TAP_SYNC, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as fh:
                return fh.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:2000]
            if 400 <= exc.code < 500 and "column" in body.lower():
                raise KeyError(body)
            last = "HTTP %d %s" % (exc.code, body[:300])
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last = repr(exc)
        time.sleep(wait * (i + 1))
    raise ArchiveDown(last)


def fetch_bin(lo, hi, depth=0, query_fn=tap_query):
    rows = parse_csv(query_fn(adql(lo, hi)))
    if len(rows) in ROW_LIMITS and depth < 4:
        mid = 0.5 * (lo + hi)
        return fetch_bin(lo, mid, depth + 1, query_fn) + fetch_bin(mid, hi, depth + 1, query_fn)
    return rows


def fetch_pool(query_fn=tap_query):
    out, seen, dups = [], set(), 0
    for lo, hi in zip(P_EDGES[:-1], P_EDGES[1:]):
        for r in fetch_bin(lo, hi, 0, query_fn):
            sid = str(r.get("source_id", "")).strip()
            if sid in seen:
                dups += 1
                continue
            seen.add(sid)
            out.append(r)
    missing = [c for c in NEEDED if out and c not in out[0]]
    return out, dups, missing


# ------------------------------------------------------------------ analysis
def attach(rows, qmap, sc):
    """Rate-sample rows of all chunks, each with its quality row and derived flags."""
    S, unmatched = [], []
    for r in rows:
        if not sc.in_rate_sample(r):
            continue
        sid = str(r.get("source_id", "")).strip()
        q = qmap.get(sid)
        if q is None:
            unmatched.append(sid)
            continue
        r = dict(r)
        K = num(r.get("K"))
        r["_q"] = q
        r["_gold"] = is_gold(q)
        r["_gold_sb1"] = is_gold(q, sb1_only=True)
        r["_tier"] = tier(num(q.get("significance")))
        r["_amp_ratio"] = amp_ratio(q, K)
        S.append(r)
    return S, unmatched


def group_stats(rows, sc, ifl, with_pop=True):
    base = sc.rate_summary(rows)
    res = {"n_rate_sample": base["n_rate_sample"], "n_hit": base["n_hit"],
           "n_sub": base["n_hit_substellar_size"], "fa_all": base["n_control_hits_expected"],
           "fa_sub": base["n_control_hits_substellar_size"], "E_iso": base["expected_if_all_real"],
           "rho_all": base["rho_all"], "rho_sub": base["rho_substellar_size"]}
    if with_pop:
        prep, skipped = ifl.prepare(rows)
        for name, scen in (("central", ifl.CENTRAL), ("floor", ifl.FLOOR)):
            E = ifl.expected(prep, scen)
            res["E_pop_" + name] = E
            res["phi_" + name] = sc.rho(res["n_sub"], res["fa_sub"], E)
        res["skipped_no_mass"] = skipped
    return res


def q1(S, sc, ifl):
    lm = [r for r in S if r.get("m2_class") in LOWMASS]
    out = {}
    for key, flag in (("gold", "_gold"), ("gold_sb1_only", "_gold_sb1")):
        g = [r for r in lm if r[flag]]
        ng = [r for r in lm if not r[flag]]
        gs, ns = group_stats(g, sc, ifl), group_stats(ng, sc, ifl)
        out[key] = {"in": gs, "out": ns,
                    "label": gold_label(gs["E_pop_floor"], gs["phi_floor"]["ci95"][1], gs["phi_central"]["ci95"][1]),
                    "bd_only_in": group_stats([r for r in g if r.get("m2_class") == "BD"], sc, ifl)}
    out["label"] = out["gold"]["label"]
    out["all_classes_gold_n"] = sum(1 for r in S if r["_gold"])
    return out


def q2(S, sc, ifl):
    lm = [r for r in S if r.get("m2_class") in LOWMASS]
    tiers = {}
    for _, _, name in TIERS:
        tiers[name] = group_stats([r for r in lm if r["_tier"] == name], sc, ifl)
    t1, t3 = tiers["T1"], tiers["T3"]
    prim = cond_test(t1["n_hit"], t1["fa_all"], t1["E_iso"], t3["n_hit"], t3["fa_all"], t3["E_iso"])
    rob = cond_test(t1["n_sub"], t1["fa_sub"], t1["E_pop_central"], t3["n_sub"], t3["fa_sub"], t3["E_pop_central"])
    p_ok = prim["p_one_sided"] is not None and prim["p_one_sided"] < ALPHA_Q2
    r_ok = rob["p_one_sided"] is not None and rob["p_one_sided"] < ALPHA_Q2
    label = "RISES_WITH_SIGNIFICANCE" if (p_ok and r_ok) else ("RISES_PRIMARY_ONLY" if p_ok else "NO_RISE")
    return {"tiers": tiers, "primary_test": prim, "robustness_test": rob, "pass": p_ok, "label": label}


def q3(S, sc, ifl):
    lm = [r for r in S if r.get("m2_class") in LOWMASS]
    out = {}
    for col, better in Q3_COLUMNS:
        vals = [(r["_amp_ratio"] if col == "amp_ratio" else num(r["_q"].get(col)), r) for r in lm]
        med = median([v for v, _ in vals])
        if not finite(med):
            out[col] = {"median": None, "note": "no finite values"}
            continue
        lo = [r for v, r in vals if finite(v) and v < med]
        hi = [r for v, r in vals if finite(v) and v >= med]
        good, bad = (hi, lo) if better == "high" else (lo, hi)
        gs, bs = group_stats(good, sc, ifl, with_pop=False), group_stats(bad, sc, ifl, with_pop=False)
        t = cond_test(bs["n_hit"], bs["fa_all"], bs["E_iso"], gs["n_hit"], gs["fa_all"], gs["E_iso"])
        out[col] = {"median": med, "better": better, "good_half": gs, "bad_half": bs, "test": t,
                    "n_missing": sum(1 for v, _ in vals if not finite(v)),
                    "pass_bonferroni": t["p_one_sided"] is not None and t["p_one_sided"] < ALPHA_Q3}
    return out


def reproduction(S_all_rate_rows, sc, ifl):
    base = sc.rate_summary(S_all_rate_rows)
    bd = [r for r in S_all_rate_rows if r.get("m2_class") == "BD"]
    prep, _ = ifl.prepare(bd)
    Ec = ifl.expected(prep, ifl.CENTRAL)
    checks = {
        "RC4_n_rate_sample": [base["n_rate_sample"], REPRO["n_rate_sample"], base["n_rate_sample"] == REPRO["n_rate_sample"]],
        "RC4_E_all": [base["expected_if_all_real"], REPRO["E_all"], abs(base["expected_if_all_real"] - REPRO["E_all"]) < 0.5],
        "RC4_n_hit": [base["n_hit"], REPRO["n_hit"], base["n_hit"] == REPRO["n_hit"]],
        "RC5_E_pop_central_BD": [Ec, REPRO["E_pop_central_BD"], abs(Ec - REPRO["E_pop_central_BD"]) < 0.5],
    }
    return checks, all(v[2] for v in checks.values())


def significance_agreement(S):
    n, bad = 0, []
    for r in S:
        a, b = num(r.get("significance")), num(r["_q"].get("significance"))
        if not (finite(a) and finite(b)):
            continue
        n += 1
        if abs(a - b) > 1e-4 * max(1.0, abs(b)):
            bad.append(r.get("source_id"))
    return {"n_compared": n, "n_disagree": len(bad), "examples": bad[:10],
            "pass": n > 0 and len(bad) <= 0.01 * n}


# ------------------------------------------------------------------ report
def _f(x, nd=3):
    return "n/a" if x is None or (isinstance(x, float) and not math.isfinite(x)) else ("%.*f" % (nd, x))


def _ci(d):
    return "%s (95%% %s-%s)" % (_f(d["rho"]), _f(d["ci95"][0]), _f(d["ci95"][1]))


def group_line(name, g):
    s = "| %s | %d | %d | %d | %.1f | %s |" % (name, g["n_rate_sample"], g["n_hit"], g["n_sub"], g["E_iso"], _ci(g["rho_all"]))
    if "E_pop_central" in g:
        s += " %.1f | %s | %.1f | %s |" % (g["E_pop_central"], _ci(g["phi_central"]), g["E_pop_floor"], _ci(g["phi_floor"]))
    else:
        s += " | | | |"
    return s


def report(res):
    H = ("| group | stars | hits | substellar-size hits | E_iso | rho_all | E_pop central | phi central | "
         "E_pop floor | phi floor |")
    L = ["# qcut %s: do Gaia's quality columns pick out the real low-mass SB1 orbits?" % VERSION, "",
         "Pool rows fetched: %d (duplicates dropped %d). Rate-sample stars matched: %d; unmatched: %d." % (
             res["pool_rows"], res["pool_dups"], res["n_matched"], res["n_unmatched"]), "",
         "## Self-checks", ""]
    for k, v in res["checks"].items():
        L.append("- %s: %s" % (k, json.dumps(v)))
    q = res["Q1"]
    L += ["", "## Q1: Gaia's gold sample (Gosset et al. 2024, Appendix J), BD + VLMS classes", "",
          "**Label: %s** (SB1-only variant: %s). Gold stars in the rate sample, all classes: %d." % (
              q["label"], q["gold_sb1_only"]["label"], q["all_classes_gold_n"]), "", H,
          "|---|---|---|---|---|---|---|---|---|---|",
          group_line("gold", q["gold"]["in"]), group_line("not gold", q["gold"]["out"]),
          group_line("gold, SB1 only", q["gold_sb1_only"]["in"]), group_line("gold, BD class only", q["gold"]["bd_only_in"])]
    q2_ = res["Q2"]
    L += ["", "## Q2: transit rate by Gaia significance (K / sigma_K), BD + VLMS classes", "",
          "**Label: %s**" % q2_["label"], "", H, "|---|---|---|---|---|---|---|---|---|---|"]
    for name in ("T1", "T2", "T3"):
        L.append(group_line(name, q2_["tiers"][name]))
    L += ["", "- Primary (all hits, E_iso), T3 vs T1: %s" % json.dumps(q2_["primary_test"]),
          "- Robustness (substellar-size hits, E_pop central), T3 vs T1: %s" % json.dumps(q2_["robustness_test"]),
          "", "## Q3 (exploratory): median splits, BD + VLMS, all hits vs E_iso, Bonferroni alpha 0.01", "",
          "| column | median | better half | good-half rho_all | bad-half rho_all | p (one-sided) | pass |",
          "|---|---|---|---|---|---|---|"]
    for col, v in res["Q3"].items():
        if v.get("median") is None:
            L.append("| %s | n/a | | | | | |" % col)
            continue
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (col, _f(v["median"], 4), v["better"], _ci(v["good_half"]["rho_all"]),
                                                         _ci(v["bad_half"]["rho_all"]), _f(v["test"]["p_one_sided"], 4),
                                                         v["pass_bonferroni"]))
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main
def write_csv(path, rows, keys):
    with open(path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        wr.writeheader()
        for r in rows:
            wr.writerow(r)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fetch", required=True, help="raw base URL of data/sb1rob-v1")
    ap.add_argument("--chunks", default="0-7")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    import sb1_combine as sc            # pinned copies fetched by fetch_qcut_deps.py
    import inclination_floor as ifl
    os.makedirs(a.out_dir, exist_ok=True)
    try:
        pool, dups, missing_cols = fetch_pool()
    except ArchiveDown as exc:
        print("archive unavailable:", exc)
        return 2
    except KeyError as exc:
        print("column error from archive:", exc)
        return 4
    if missing_cols:
        print("missing columns:", missing_cols)
        return 4
    keys = list(pool[0].keys()) if pool else list(NEEDED)
    write_csv(os.path.join(a.out_dir, "qcut_columns.csv"), pool, keys)
    qmap = {str(r["source_id"]).strip(): r for r in pool}

    loaded, missing = sc.load_chunks(None, a.fetch, sc.parse_chunks(a.chunks))
    rows, chunk_dups = sc.merge([(nm, rr) for nm, rr, _ in loaded])
    rate_rows = [r for r in rows if sc.in_rate_sample(r)]
    checks, repro_ok = reproduction(rate_rows, sc, ifl)
    S, unmatched = attach(rows, qmap, sc)
    checks["RC1_pool_rows_ge_6434"] = [len(pool), 6434, len(pool) >= 6434]
    checks["RC2_all_rate_sample_matched"] = [len(unmatched), 0, len(unmatched) == 0]
    sig = significance_agreement(S)
    checks["RC3_significance_agrees"] = [sig["n_disagree"], sig["n_compared"], sig["pass"]]
    res = {"version": VERSION, "pool_rows": len(pool), "pool_dups": dups, "chunks_missing": missing,
           "chunk_dups": chunk_dups, "n_matched": len(S), "n_unmatched": len(unmatched),
           "unmatched_examples": unmatched[:20], "checks": checks, "gold_rule": GOLD,
           "tiers": [[lo, hi, nm] for lo, hi, nm in TIERS]}
    ok = repro_ok and all(v[2] for v in checks.values()) and not missing
    if not ok:
        res["stopped"] = "a reproduction check failed; no grade"
        with open(os.path.join(a.out_dir, "qcut_summary.json"), "w") as fh:
            json.dump(res, fh, indent=1)
        print(json.dumps({"stopped": res["stopped"], "checks": checks}))
        return 3
    res["Q1"] = q1(S, sc, ifl)
    res["Q2"] = q2(S, sc, ifl)
    res["Q3"] = q3(S, sc, ifl)
    with open(os.path.join(a.out_dir, "qcut_summary.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    with open(os.path.join(a.out_dir, "qcut_report.md"), "w") as fh:
        fh.write(report(res))
    star_rows = []
    for r in S:
        q = r["_q"]
        star_rows.append({"source_id": r.get("source_id"), "m2_class": r.get("m2_class"), "P": r.get("P"),
                          "K": r.get("K"), "G": r.get("G"), "m2sini": r.get("m2sini"),
                          "w": num(r.get("p_transit"), 0.0) * num(r.get("sensitivity"), 0.0),
                          "star_hit": r.get("star_hit"), "hit_class": r.get("hit_class"),
                          "significance": q.get("significance"), "efficiency": q.get("efficiency"),
                          "rv_n_good_obs_primary": q.get("rv_n_good_obs_primary"),
                          "goodness_of_fit": q.get("goodness_of_fit"),
                          "conf_spectro_period": q.get("conf_spectro_period"),
                          "amp_ratio": r["_amp_ratio"], "gold": r["_gold"], "tier": r["_tier"]})
    write_csv(os.path.join(a.out_dir, "qcut_stars.csv"), star_rows, list(star_rows[0].keys()) if star_rows else ["source_id"])
    print(json.dumps({"Q1": res["Q1"]["label"], "Q1_sb1_only": res["Q1"]["gold_sb1_only"]["label"],
                      "Q2": res["Q2"]["label"], "Q2_p": res["Q2"]["primary_test"]["p_one_sided"],
                      "Q3": {k: v.get("pass_bonferroni") for k, v in res["Q3"].items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
