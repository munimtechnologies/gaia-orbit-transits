# SPDX-License-Identifier: Apache-2.0
"""sb1_robust 0.2.0: the Gaia DR3 low-mass SB1 transit-rate test with an outlier-proof hit rule.

MV2 of Munim, Inc.; made with AI agents working in his name. Apache-2.0.

This wraps sb1_transit 0.1.0 (pinned, unchanged; release v0.15.0) and changes three things,
all fixed in findings/2026-11-18-sb1-robust-prereg.md before any 0.2.0 data were read:

1. Median rule. A sector only hits if the median depth of the binned residuals inside the
   best box is at least MED_MIN (0.5) of the box's mean depth. In 0.1.0 most hits were 1-3
   outlying 30-min bins that dragged the box mean down while the other in-box bins sat at
   zero; a real transit fills the box, so its median and mean agree. The rule goes through
   sector_hit, so real folds, control folds and injections are all judged by it.
2. No silent fallback. 0.1.0 retried the Gaia query without astrophysical_parameters when
   the archive timed out (chunk 0's 1-1.5 d bin lost FLAME masses and the log g cut that
   way). 0.2.0 retries the full query and stops with exit 2 rather than drop it.
3. A fresh seeded order (seed 20261119) over the whole eligible pool, split into n chunks.

It also writes robust_extra.json (the 0.1.0 rule's hits in the same data, and rates split by
primary mass) and provides combine() to sum chunk summaries (pure Python).
"""
import csv
import json
import math
import os
import random
import sys
import time

VERSION = "0.2.0"
SEED2 = 20261119
MED_MIN = 0.5
EXPECTED_POOL = 6434          # eligible stars in gaia-sb1tr-c1-v1, the 0.1.0 job with full FLAME
M1_BINS = (("m1<1.2", 0.0, 1.2), ("1.2<=m1<1.5", 1.2, 1.5), ("m1>=1.5", 1.5, 99.0))


# ------------------------------------------------------------------ pure helpers
def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return float("nan")
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def median_ratio(r_in, depth):
    """Median in-box depth (-median of residuals) over the box mean depth; 0 if undefined."""
    if not r_in or not (depth > 0):
        return 0.0
    return -median(r_in) / depth


def robust_hit(res, base_hit):
    return bool(base_hit and res and res.get("med_ratio", 0.0) >= MED_MIN)


def order_ids(ids, n_chunks, chunk, seed=SEED2):
    ids = sorted(ids)
    rnd = random.Random(seed)
    rnd.shuffle(ids)
    return [x for i, x in enumerate(ids) if i % n_chunks == chunk]


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
    """Exact (Garwood) central interval for a Poisson mean given n counts."""
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


def rho(n, fa, E):
    """Reality fraction (n - fa) / E with the Garwood 95 % interval of n."""
    if not (E > 0):
        return {"rho": None, "ci95": [None, None]}
    lo, hi = garwood(int(n))
    return {"rho": (n - fa) / E, "ci95": [max(0.0, (lo - fa) / E), max(0.0, (hi - fa) / E)],
            "upper_no_subtraction": hi / E}


def combine(summaries, minus=None):
    """Sum rate summaries (dicts with n_rate_sample, n_hit, n_hit_substellar_size,
    n_control_hits_expected, n_control_hits_substellar_size, expected_if_all_real) and
    recompute rho. `minus` is an optional dict of the same keys to subtract (duplicates)."""
    keys = ("n_rate_sample", "n_hit", "n_hit_substellar_size", "n_control_hits_expected",
            "n_control_hits_substellar_size", "expected_if_all_real")
    tot = {k: 0.0 for k in keys}
    for s in summaries:
        for k in keys:
            tot[k] += float(s.get(k) or 0.0)
    if minus:
        for k in keys:
            tot[k] -= float(minus.get(k) or 0.0)
    E = tot["expected_if_all_real"]
    tot["control_rate"] = tot["n_control_hits_expected"] / tot["n_rate_sample"] if tot["n_rate_sample"] else None
    tot["rho_all"] = rho(tot["n_hit"], tot["n_control_hits_expected"], E)
    tot["rho_substellar_size"] = rho(tot["n_hit_substellar_size"],
                                     tot["n_control_hits_substellar_size"], E)
    return tot


def _truthy(v):
    return str(v).strip() in ("True", "true", "1")


def _num(v, default=float("nan")):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def star_rows(path):
    """sb1_stars.csv rows with the types that sb1_transit.rate_summary expects."""
    out = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            d = dict(r)
            for k in list(d):
                if k == "star_hit" or k == "star_hit_v1" or (k.startswith("ctrl_") and k.endswith("_hit")):
                    d[k] = _truthy(d[k])
            for k in ("sensitivity", "p_transit", "m1", "P", "m2sini"):
                d[k] = _num(d.get(k), 0.0 if k == "sensitivity" else float("nan"))
            out.append(d)
    return out


# ------------------------------------------------------------------ patching sb1_transit
def install(st):
    """Patch an imported sb1_transit 0.1.0 module in place (idempotent)."""
    if getattr(st, "_robust_installed", False):
        return st
    orig_fold, orig_hit, orig_eval = st.fold_search, st.sector_hit, st.evaluate_star

    def fold_search(bt, r, P, D, tref):
        res = orig_fold(bt, r, P, D, tref)
        if res is None:
            return None
        ph = ((bt - tref) / P) % 1.0
        inb, _ = st._box_stats(ph, r, res["phase"], D / P)
        rin = [float(x) for x in r[inb]]
        res["med_ratio"] = median_ratio(rin, res["depth"])
        res["frac_neg"] = (sum(1 for x in rin if x < 0) / float(len(rin))) if rin else 0.0
        return res

    def sector_hit(res):
        base = orig_hit(res)
        if res:
            res["hit_v1"] = bool(base)
        return robust_hit(res, base)

    def evaluate_star(sectors_meas, phys, eph):
        res = orig_eval(sectors_meas, phys, eph)
        hits = [m for m in sectors_meas if m["hit"]]
        if hits:
            best = max(hits, key=lambda m: m["real"]["snr"])
            res["med_ratio_best"] = best["real"].get("med_ratio")
        res["star_hit_v1"] = any(bool((m.get("real") or {}).get("hit_v1")) for m in sectors_meas)
        return res

    def query_sample(p_edges=(1, 1.5, 2, 3, 5, 8, 13)):
        rows = []
        for lo, hi in zip(p_edges[:-1], p_edges[1:]):
            where = ("WHERE o.nss_solution_type IN ('SB1','SB1C') AND o.period >= %g AND "
                     "o.period < %g AND s.phot_g_mean_mag <= %g AND o.semi_amplitude_primary*"
                     "o.semi_amplitude_primary*o.semi_amplitude_primary*o.period < %g"
                     % (lo, hi, st.G_MAX, st.KP_SERVER_MAX))
            q = "SELECT " + st.COLS + st.AP_COLS + " " + st.FROM + st.AP_JOIN + " " + where
            part = None
            for attempt in range(4):
                try:
                    part = st.tap_query(q, timeout=300)
                    break
                except RuntimeError as exc:
                    st.log("full query (with astrophysical_parameters) failed; waiting", attempt + 1, exc)
                    time.sleep(120)
            if part is None:
                st.log("Gaia archive unavailable for the full query: stopping (exit 2), no fallback")
                sys.exit(2)
            st.log("Gaia P %g-%g: %d rows (with astrophysical_parameters)" % (lo, hi, len(part)))
            rows.extend(part)
        return rows

    st.fold_search = fold_search
    st.sector_hit = sector_hit
    st.evaluate_star = evaluate_star
    st.query_sample = query_sample
    st.chunk_order = lambda ids, n_chunks, chunk, seed=None: order_ids(ids, n_chunks, chunk)
    st.SEED = SEED2
    st.VERSION = "%s (sb1_robust; sb1_transit 0.1.0 + median rule)" % VERSION
    st._robust_installed = True
    return st


def extras(st, out_dir):
    """robust_extra.json: pool check, 0.1.0-rule hits in the same data, rates by primary mass."""
    with open(os.path.join(out_dir, "sb1_summary.json")) as fh:
        summ = json.load(fh)
    rows = star_rows(os.path.join(out_dir, "sb1_stars.csv"))
    S = [r for r in rows if r.get("status") == "OK" and not r.get("control")
         and r.get("sensitivity", 0) >= st.SENS_MIN]
    out = {"version": VERSION,
           "pool": summ.get("eligible"), "expected_pool": EXPECTED_POOL,
           "pool_matches": summ.get("eligible") == EXPECTED_POOL,
           "v1_rule": {"n_rate_sample": len(S),
                       "n_hit_v1": sum(1 for r in S if r.get("star_hit_v1")),
                       "n_hit_robust": sum(1 for r in S if r.get("star_hit")),
                       "n_hit_v1_only": sum(1 for r in S if r.get("star_hit_v1") and not r.get("star_hit"))},
           "by_m1": {}}
    for name, lo, hi in M1_BINS:
        sub = [r for r in rows if lo <= r.get("m1", float("nan")) < hi]
        out["by_m1"][name] = st.rate_summary(sub)
    out = st.clean_json(out)
    with open(os.path.join(out_dir, "robust_extra.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({"robust_extra": {k: out[k] for k in ("pool", "pool_matches", "v1_rule")}}))
    return out


def _out_dir(argv):
    for i, a in enumerate(argv):
        if a == "--out-dir" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--out-dir="):
            return a.split("=", 1)[1]
    return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    import sb1_transit as st
    install(st)
    rc = st.main(argv)
    od = _out_dir(argv)
    if rc == 0 and od:
        extras(st, od)
    return rc


if __name__ == "__main__":
    sys.exit(main())
