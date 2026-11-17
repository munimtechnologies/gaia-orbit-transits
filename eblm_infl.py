# SPDX-License-Identifier: Apache-2.0
"""Short-period M-dwarf radius inflation against real stellar models (post-processing of
eblm_fit results). Part of gaia-orbit-transits by MV2 of Munim, Inc.; made with AI agents.
Apache-2.0.

Why this module exists. eblm_fit 0.1.0 measures each companion's radius against a rough
mass-radius table (eblm_screen.MS_TABLE). That table is up to ~4 % larger than the
Baraffe et al. (2015, BHAC15) 5-Gyr isochrone near 0.3 M_sun (0.31 vs 0.299 R_sun), the
same size as the effect being tested. Swayne et al. (2024, EBLM XI, MNRAS 528, 5703) found
M dwarfs in EBLM binaries with P < 5 d inflated by about 6 % (from 5 systems, P = 2.8-4.3
d) against <= 3 % at longer periods; EBLM XIX (Davis et al. 2026, arXiv:2610.18338)
removed every P < 5 d binary and found 0.3 +- 1.6 %. This module re-scores the eblm_fit
radii against BHAC15 and runs the tests pre-registered in
findings/2026-11-17-short-period-inflation-prereg.md:

 H1  median inflation of the main set (vs BHAC15 5 Gyr, FLAME-based R1):
     INFLATED if the bootstrap 95 % lower bound > +0.03, NOT_INFLATED if the upper bound
     < +0.03, INCONCLUSIVE otherwise (TOO_FEW if n < 8);
 H2  Spearman rank correlation of inflation with orbital period, one-sided permutation
     test (prediction rho < 0): PERIOD_TREND if p < 0.05;
 plus descriptive period bins, age (1 / 10 Gyr) and light-curve-radius variants, and the
 confounders rho(m2, P) and rho(infl, m2).

It does not import eblm_fit or eblm_screen; input is eblm_fit_results.csv.
"""
import argparse
import csv
import json
import math
import os
import sys
import urllib.request

VERSION = "0.1.0"
BHAC15_URLS = ["https://perso.ens-lyon.fr/isabelle.baraffe/BHAC15dir/BHAC15_iso.2mass",
               "http://perso.ens-lyon.fr/isabelle.baraffe/BHAC15dir/BHAC15_iso.2mass"]
# Fallback only (used, and flagged in the summary, if the download fails): (M/Msun, R/Rsun)
# of the BHAC15 solar-metallicity isochrones, transcribed from BHAC15_iso.2mass on
# 2026-11-17. The job prefers the downloaded file and records which one it used.
BHAC15_FALLBACK = {
    1.0: [(0.08, 0.102), (0.09, 0.113), (0.10, 0.124), (0.11, 0.135), (0.13, 0.156), (0.15, 0.174),
          (0.17, 0.192), (0.20, 0.217), (0.30, 0.291), (0.40, 0.372), (0.50, 0.460), (0.60, 0.554),
          (0.70, 0.637), (0.80, 0.719)],
    5.0: [(0.08, 0.099), (0.09, 0.113), (0.10, 0.124), (0.11, 0.135), (0.13, 0.156), (0.15, 0.175),
          (0.17, 0.192), (0.20, 0.218), (0.30, 0.299), (0.40, 0.377), (0.50, 0.467), (0.60, 0.562),
          (0.70, 0.648), (0.80, 0.742)],
    10.0: [(0.08, 0.099), (0.09, 0.113), (0.10, 0.124), (0.11, 0.135), (0.13, 0.156), (0.15, 0.175),
           (0.17, 0.193), (0.20, 0.220), (0.30, 0.304), (0.40, 0.380), (0.50, 0.471), (0.60, 0.569),
           (0.70, 0.662), (0.80, 0.776)],
}
AGES = (1.0, 5.0, 10.0)
CLEAN_SUFFIXES = ("EBLM_CONSISTENT", "EBLM_LARGE_RADIUS", "EBLM_SMALL_RADIUS")
H1_THRESHOLD = 0.03
SWAYNE_SHORT_P = 0.06
MIN_N = 8
PERIOD_BINS = [(0.0, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 1e9)]
SEED = 20261117


# ---------------------------------------------------------------- models
def parse_bhac15(text):
    """{age_gyr: [(M, R), ...]} from a BHAC15 isochrone file. Age blocks start with a line
    containing 't (Gyr) ='; data rows are whitespace-separated numbers M Teff L g R ..."""
    out = {}
    age = None
    for ln in text.splitlines():
        if "t (Gyr)" in ln and "=" in ln:
            try:
                age = round(float(ln.split("=", 1)[1].split()[0]), 6)
                out[age] = []
            except (ValueError, IndexError):
                age = None
            continue
        s = ln.strip()
        if not s or s.startswith("!") or age is None:
            continue
        parts = s.split()
        if len(parts) < 5:
            continue
        try:
            m, r = float(parts[0]), float(parts[4])
        except ValueError:
            continue
        out[age].append((m, r))
    return {a: sorted(rows) for a, rows in out.items() if rows}


def load_models(cache_dir=None, offline=False):
    """(models, source). Tries the BHAC15 download, then the transcribed fallback."""
    if not offline:
        for url in BHAC15_URLS:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "gaia-orbit-transits"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    text = r.read().decode("latin-1", "replace")
                models = parse_bhac15(text)
                if all(a in models for a in AGES):
                    if cache_dir:
                        with open(os.path.join(cache_dir, "BHAC15_iso.2mass"), "w", encoding="latin-1") as fh:
                            fh.write(text)
                    return models, url
            except Exception as exc:  # noqa: BLE001 - logged and fallen back on
                print("BHAC15 download failed:", url, exc, flush=True)
    return {a: list(v) for a, v in BHAC15_FALLBACK.items()}, "fallback_transcribed"


def r_model(m, models, age=5.0):
    """BHAC15 radius at mass m (linear in mass between grid points); NaN off the grid."""
    rows = models.get(round(float(age), 6))
    if not rows or not (m == m) or m < rows[0][0] or m > rows[-1][0]:
        return float("nan")
    for (m0, r0), (m1, r1) in zip(rows, rows[1:]):
        if m0 <= m <= m1:
            return r0 if m1 == m0 else r0 + (r1 - r0) * (m - m0) / (m1 - m0)
    return rows[-1][1]


# ---------------------------------------------------------------- statistics
def _num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def ranks(x):
    """Ranks 1..n with ties given their average rank."""
    order = sorted(range(len(x)), key=lambda i: x[i])
    out = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        avg = 0.5 * (i + j) + 1.0
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def pearson(x, y):
    n = len(x)
    if n < 3:
        return float("nan")
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx <= 0 or syy <= 0:
        return float("nan")
    return sxy / math.sqrt(sxx * syy)


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def perm_p_less(x, y, n_perm=10000, seed=SEED):
    """One-sided permutation p-value for Spearman rho(x, y) being this negative or more:
    (1 + #{rho_perm <= rho_obs}) / (1 + n_perm)."""
    import random
    rho = spearman(x, y)
    if rho != rho:
        return rho, float("nan")
    rx, ry = ranks(x), ranks(y)
    rng = random.Random(seed)
    ry = list(ry)
    count = 0
    for _ in range(n_perm):
        rng.shuffle(ry)
        if pearson(rx, ry) <= rho + 1e-12:
            count += 1
    return rho, (1 + count) / (1 + n_perm)


def median(x):
    s = sorted(x)
    n = len(s)
    if n == 0:
        return float("nan")
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def median_ci(x, n_boot=2000, seed=SEED):
    """Median and bootstrap 95 % interval (percentiles 2.5 / 97.5 of resampled medians)."""
    import random
    x = [v for v in x if v == v]
    if not x:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    meds = sorted(median([x[rng.randrange(len(x))] for _ in x]) for _ in range(n_boot))
    lo = meds[int(math.floor(0.025 * (n_boot - 1)))]
    hi = meds[int(math.ceil(0.975 * (n_boot - 1)))]
    return median(x), lo, hi


def h1_label(n, lo, hi, threshold=H1_THRESHOLD):
    if n < MIN_N:
        return "TOO_FEW"
    if lo > threshold:
        return "INFLATED"
    if hi < threshold:
        return "NOT_INFLATED"
    return "INCONCLUSIVE"


# ---------------------------------------------------------------- sample
def is_clean(row):
    return str(row.get("verdict", "")).endswith(CLEAN_SUFFIXES)


def main_set_reason(row):
    """'' if the row is in the pre-registered main set, else the first failed cut."""
    if not is_clean(row):
        return "not_clean_verdict"
    if not (_num(row.get("b")) < 0.8):
        return "b_ge_0.8"
    if not (_num(row.get("snr_fit")) >= 30):
        return "snr_lt_30"
    if row.get("m1_source") != "flame":
        return "no_flame_mass"
    m2 = _num(row.get("m2"))
    if not (0.08 <= m2 <= 0.6):
        return "m2_outside_0.08_0.6"
    if not (_num(row.get("r2_flame")) > 0):
        return "no_flame_radius"
    rr = _num(row.get("r1_ratio"))
    if not (0.8 <= rr <= 1.2):
        return "r1_lc_flame_disagree"
    return ""


def score(rows, models):
    """Adds infl_<radius>_<age> columns: radius 'flame' (k R1_FLAME) or 'lc' (k R1_lc)."""
    out = []
    for r in rows:
        d = dict(r)
        m2 = _num(r.get("m2"))
        for rad, key in (("flame", "r2_flame"), ("lc", "r2")):
            r2 = _num(r.get(key))
            for age in AGES:
                rm = r_model(m2, models, age)
                d[f"infl_{rad}_{int(age)}"] = r2 / rm - 1.0 if rm == rm and rm > 0 and r2 == r2 else float("nan")
        d["main_set_cut"] = main_set_reason(r)
        out.append(d)
    return out


def summarize(scored, n_boot=2000, n_perm=10000):
    main = [d for d in scored if d["main_set_cut"] == ""]
    clean = [d for d in scored if is_clean(d)]
    s = {"version": VERSION, "n_rows": len(scored), "n_clean": len(clean), "n_main": len(main)}
    cuts = {}
    for d in scored:
        cuts[d["main_set_cut"] or "in_main_set"] = cuts.get(d["main_set_cut"] or "in_main_set", 0) + 1
    s["cuts"] = cuts

    x = [d["infl_flame_5"] for d in main if d["infl_flame_5"] == d["infl_flame_5"]]
    med, lo, hi = median_ci(x, n_boot)
    s["H1"] = {"estimator": "R2 = k R1_FLAME vs BHAC15 5 Gyr", "n": len(x), "median": med, "ci95": [lo, hi],
               "label": h1_label(len(x), lo, hi),
               "contains_swayne_6pct": bool(lo == lo and lo <= SWAYNE_SHORT_P <= hi)}
    variants = {}
    for name, sel in (("main", main), ("all_clean", clean)):
        for rad in ("flame", "lc"):
            for age in AGES:
                key = f"infl_{rad}_{int(age)}"
                v = [d[key] for d in sel if d[key] == d[key]]
                m_, l_, h_ = median_ci(v, n_boot)
                variants[f"{name}/{key}"] = {"n": len(v), "median": m_, "ci95": [l_, h_],
                                             "label": h1_label(len(v), l_, h_)}
    s["H1_variants"] = variants

    pairs = [(_num(d.get("period_gaia")), d["infl_flame_5"], _num(d.get("m2"))) for d in main]
    pairs = [p for p in pairs if p[0] == p[0] and p[1] == p[1] and p[2] == p[2]]
    if len(pairs) >= MIN_N:
        rho, p = perm_p_less([p_[0] for p_ in pairs], [p_[1] for p_ in pairs], n_perm)
        s["H2"] = {"n": len(pairs), "rho_infl_P": rho, "p_one_sided": p,
                   "label": "PERIOD_TREND" if p < 0.05 else "NO_TREND_DETECTED",
                   "rho_m2_P": spearman([p_[0] for p_ in pairs], [p_[2] for p_ in pairs]),
                   "rho_infl_m2": spearman([p_[2] for p_ in pairs], [p_[1] for p_ in pairs])}
    else:
        s["H2"] = {"n": len(pairs), "label": "TOO_FEW"}

    bins = {}
    for lo_p, hi_p in PERIOD_BINS:
        v = [d["infl_flame_5"] for d in main
             if lo_p <= _num(d.get("period_gaia")) < hi_p and d["infl_flame_5"] == d["infl_flame_5"]]
        m_, l_, h_ = median_ci(v, n_boot)
        bins[f"P_{lo_p:g}_{hi_p:g}" if hi_p < 1e8 else f"P_ge_{lo_p:g}"] = {"n": len(v), "median": m_,
                                                                             "ci95": [l_, h_]}
    s["period_bins"] = bins
    return s


# ---------------------------------------------------------------- outputs
OUT_COLS = ["source_id", "tic", "verdict", "main_set_cut", "period_gaia", "m1", "m1_source", "m2", "k", "b",
            "a_r", "snr_fit", "r1_lc", "r1_flame", "r1_ratio", "r2", "r2_flame", "teff1",
            "infl_flame_1", "infl_flame_5", "infl_flame_10", "infl_lc_1", "infl_lc_5", "infl_lc_10"]


def _fmt(x):
    if isinstance(x, float):
        return "" if x != x else f"{x:.6g}"
    return x


def report(s, source):
    h1, h2 = s["H1"], s["H2"]
    L = [f"# eblm_infl {VERSION}: short-period M-dwarf inflation vs BHAC15", "",
         f"Model source: {source}", "",
         f"Rows {s['n_rows']}, clean EBLM fits {s['n_clean']}, main set {s['n_main']}.", "",
         "## H1 (median inflation, FLAME R1, BHAC15 5 Gyr)", "",
         f"n = {h1['n']}, median = {h1['median']:+.4f}, 95% CI [{h1['ci95'][0]:+.4f}, {h1['ci95'][1]:+.4f}]"
         f" -> **{h1['label']}**; contains Swayne et al. 2024's +6%: {h1['contains_swayne_6pct']}", "",
         "## H2 (Spearman inflation vs period, one-sided)", "", "```", json.dumps(h2, indent=1), "```", "",
         "## Period bins (main set)", "", "| bin | n | median | 95% CI |", "|---|---|---|---|"]
    for k, v in s["period_bins"].items():
        L.append(f"| {k} | {v['n']} | {v['median']:+.4f} | [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] |")
    L += ["", "## Variants", "", "| set/estimator | n | median | 95% CI | label |", "|---|---|---|---|---|"]
    for k, v in s["H1_variants"].items():
        L.append(f"| {k} | {v['n']} | {v['median']:+.4f} | [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] | {v['label']} |")
    L += ["", "## Cuts", ""] + [f"- {k}: {v}" for k, v in sorted(s["cuts"].items())]
    return "\n".join(L).replace("+nan", "nan") + "\n"


def plot(scored, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for sel, col, lab in (([d for d in scored if is_clean(d) and d["main_set_cut"]], "0.7", "clean, cut"),
                          ([d for d in scored if d["main_set_cut"] == ""], "C0", "main set")):
        xs = [_num(d.get("period_gaia")) for d in sel]
        ys = [100 * d["infl_flame_5"] for d in sel]
        ax.scatter(xs, ys, s=14, color=col, label=lab)
    ax.axhline(0, color="k", lw=0.8)
    ax.axhline(6, color="C3", lw=0.8, ls="--", label="Swayne+2024, P < 5 d (5 systems)")
    ax.axhline(0.3, color="C2", lw=0.8, ls=":", label="EBLM XIX, P > 5 d")
    ax.set_xscale("log")
    ax.set_xlabel("orbital period (d)")
    ax.set_ylabel("R2 / R_BHAC15(5 Gyr) - 1 (%)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", required=True, help="eblm_fit_results.csv from eblm_fit 0.1.0")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    with open(a.results, newline="") as fh:
        rows = list(csv.DictReader(fh))
    models, source = load_models(a.out_dir, a.offline)
    scored = score(rows, models)
    s = summarize(scored)
    s["model_source"] = source
    s["fallback_check"] = {f"{age:g}Gyr_{m}": [r_model(m, models, age), r_model(m, BHAC15_FALLBACK, age)]
                           for age in AGES for m in (0.1, 0.2, 0.3, 0.4)}
    with open(os.path.join(a.out_dir, "infl_table.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLS, extrasaction="ignore")
        w.writeheader()
        for d in scored:
            w.writerow({k: _fmt(d.get(k, "")) for k in OUT_COLS})
    with open(os.path.join(a.out_dir, "infl_summary.json"), "w") as fh:
        json.dump(s, fh, indent=1, default=lambda x: None)
    with open(os.path.join(a.out_dir, "infl_report.md"), "w") as fh:
        fh.write(report(s, source))
    try:
        plot(scored, os.path.join(a.out_dir, "infl_vs_period.png"))
    except Exception as exc:  # noqa: BLE001
        print("plot failed:", exc)
    print(json.dumps({k: s[k] for k in ("n_clean", "n_main", "H1", "H2")}, default=lambda x: None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
