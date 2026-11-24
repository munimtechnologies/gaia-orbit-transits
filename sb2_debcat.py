#!/usr/bin/env python3
# sb2_debcat.py 0.1.0
# Gaia DR3 double-lined spectroscopic orbits (tbosb2, tbosb2c) against DEBCat, the catalogue of
# detached eclipsing binaries with masses and radii known to about 2%.
# MV2, Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.
# Pre-registration: findings/2026-11-24-sb2-debcat-prereg.md (written before this job ran).
"""
What it does
1. Downloads DEBCat (Southworth 2015; live web table) and parses system name, period and the two
   masses (with errors), plus radii where given. Raw HTML is saved to the output folder.
2. Downloads Gaia DR3's double-lined orbit tables from VizieR (I/357/tbosb2 and I/357/tbosb2c;
   CfA mirror, then CDS), with a row-count and a known-row control.
3. Resolves every DEBCat name to its Gaia DR3 source_id through SIMBAD (Harvard mirror, then
   CDS), after a control lookup (RZ Cha -> Gaia DR3 5198334162577657984).
4. For each DEBCat system with a Gaia double-lined orbit: period status, the folded mass ratio
   (q' = smaller/larger; Gaia K_small/K_large against DEBCat M_small/M_large), and
   R = (M1+M2) sin^3 i from Gaia over DEBCat's M1+M2 (expected slightly below 1 because
   sin^3 i <= 1; about 0.99 for typical detached eclipsing binaries).
5. Grades the registered questions Q1-Q4 and writes sb2_debcat_summary.json, matches.csv,
   debcat_parsed.csv.
A self-test on synthetic binaries runs first and its result is recorded.
"""
import argparse
import csv
import html as htmlmod
import json
import math
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "0.1.0"
MASS_CONST = 1.036149e-7      # M_sun per (km/s)^3 day
UA = "gaia-orbit-transits/sb2_debcat (MV2, Munim, Inc.; open research)"
DEBCAT_URLS = ("https://www.astro.keele.ac.uk/jkt/debcat/",
               "http://www.astro.keele.ac.uk/jkt/debcat/")
VIZ_MIRRORS = ("https://vizier.cfa.harvard.edu/viz-bin/asu-tsv",
               "https://vizier.cds.unistra.fr/viz-bin/asu-tsv")
GAIA_TABLES = (("I/357/tbosb2", 4630), ("I/357/tbosb2c", 746))
SIMBAD_MIRRORS = ("https://simbad.cfa.harvard.edu/simbad/sim-id",
                  "https://simbad.cds.unistra.fr/simbad/sim-id")
CONTROL_NAME = "RZ Cha"
CONTROL_GAIA = "5198334162577657984"
CONTROL_K = (107.8, 108.2)          # Southworth (2025, arXiv:2504.16817) quoting Gaia DR3 tbosb2
CONTROL_K_TOL = 0.5
TABLE_CONTROL_SOURCE = "6030061691987260672"   # first row of I/357/tbosb2, read 24 Nov 2026
TABLE_CONTROL_K1 = 56.3477
P_OK_TOL = 0.005
ALIAS_FACTORS = (0.5, 2.0, 1.0 / 3.0, 3.0)
ALIAS_TOL = 0.005
MIN_DEBCAT = 100
MIN_SAMPLE = 15
SCALE_LO, SCALE_HI = 0.97, 1.00
ERR_SCALE_MAX = 1.5
BLEND_P = 0.01
SEED = 20261124
N_BOOT = 2000
N_PERM = 5000
HTTP_TIMEOUT = 90
PAUSE = 0.35

PM_RE = re.compile(r"([-+]?(?:\d+\.\d*|\.\d+|\d+))\s*(?:±|\+/-|\+-)\s*(\d+\.\d*|\.\d+|\d+)")
NUM_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)")
GAIA_ID_RE = re.compile(r"Gaia DR3\s+(\d{6,20})")
MAIN_RE = re.compile(r"^Object\s+(.+?)\s+---", re.M)

GREEK = {"α": "alf", "β": "bet", "γ": "gam", "δ": "del", "ε": "eps",
         "ζ": "zet", "η": "eta", "θ": "tet", "ι": "iot", "κ": "kap",
         "λ": "lam", "μ": "mu.", "ν": "nu.", "ξ": "ksi", "ο": "omi",
         "π": "pi.", "ρ": "rho", "σ": "sig", "τ": "tau", "υ": "ups",
         "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "ome"}
GREEK_WORDS = {"alpha": "alf", "beta": "bet", "gamma": "gam", "delta": "del", "epsilon": "eps",
               "zeta": "zet", "theta": "tet", "iota": "iot", "kappa": "kap", "lambda": "lam",
               "omicron": "omi", "sigma": "sig", "upsilon": "ups", "omega": "ome"}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ================================================================ pure helpers
def fnum(v, default=float("nan")):
    try:
        if v is None:
            return default
        s = str(v).strip().strip('"')
        if s in ("", "null", "NULL", "NaN", "nan", "None", "--"):
            return default
        x = float(s)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def finite(*xs):
    return all(isinstance(x, (int, float)) and math.isfinite(x) for x in xs)


def clean_cell(s):
    s = re.sub(r"(?s)<[^>]*>", " ", s or "")
    s = htmlmod.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def clean_name(s):
    s = clean_cell(s)
    s = re.sub(r"[*†‡#]+$", "", s).strip()
    return s


def first_float(s):
    m = NUM_RE.search(s or "")
    return float(m.group(0)) if m else None


def parse_pm(s):
    m = PM_RE.search(s or "")
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def table_rows(text):
    """HTML -> list of rows, each a list of cleaned cell strings (tolerates unclosed tags)."""
    rows = []
    for chunk in re.split(r"(?i)<tr(?:\s[^>]*)?>", text or "")[1:]:
        chunk = re.split(r"(?i)</tr\s*>|</table\s*>", chunk)[0]
        parts = re.split(r"(?i)<t[dh](?:\s[^>]*)?>", chunk)[1:]
        rows.append([clean_cell(p) for p in parts])
    return rows


def parse_debcat_row(cells, period_idx=None):
    if len(cells) < 4:
        return None
    name = clean_name(cells[0])
    if not name or re.fullmatch(r"(?i)(system|name|star|object)", name):
        return None
    pidx = 1
    if period_idx is not None and 0 < period_idx < len(cells) and first_float(cells[period_idx]) is not None:
        pidx = period_idx
    P = first_float(cells[pidx]) if pidx < len(cells) else None
    if P is None or not (0.05 < P < 20000.0):
        return None
    pms = []
    for j, c in enumerate(cells):
        if j <= pidx:
            continue
        v = parse_pm(c)
        if v is not None:
            pms.append(v)
    if len(pms) < 2:
        return None
    (mA, eA), (mB, eB) = pms[0], pms[1]
    if not (0.05 < mA < 150.0 and 0.05 < mB < 150.0 and eA >= 0 and eB >= 0):
        return None
    rec = {"name": name, "P": P, "mA": mA, "emA": eA, "mB": mB, "emB": eB,
           "rA": float("nan"), "erA": float("nan"), "rB": float("nan"), "erB": float("nan")}
    if len(pms) >= 4:
        (rA, erA), (rB, erB) = pms[2], pms[3]
        if 0.01 < rA < 2000 and 0.01 < rB < 2000:
            rec.update({"rA": rA, "erA": erA, "rB": rB, "erB": erB})
    return rec


def parse_debcat(text):
    """-> list of system dicts (first occurrence of each name kept)."""
    out, seen, period_idx = [], set(), None
    for cells in table_rows(text):
        if any(re.search(r"(?i)period", c) for c in cells) and not any(parse_pm(c) for c in cells):
            for j, c in enumerate(cells):
                if re.search(r"(?i)period", c):
                    period_idx = j
                    break
            continue
        rec = parse_debcat_row(cells, period_idx)
        if rec and rec["name"] not in seen:
            seen.add(rec["name"])
            out.append(rec)
    return out


def name_variants(name):
    vs = [name]
    base = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
    if base and base not in vs:
        vs.append(base)
    g = "".join(GREEK.get(ch, ch) for ch in base)
    toks = base.split()
    if toks and toks[0].lower() in GREEK_WORDS:
        g = " ".join([GREEK_WORDS[toks[0].lower()]] + toks[1:])
    if g and g not in vs:
        vs.append(g)
    return vs


def parse_simbad_ascii(text):
    m = GAIA_ID_RE.search(text or "")
    mm = MAIN_RE.search(text or "")
    return (m.group(1) if m else None), (mm.group(1).strip() if mm else "")


def parse_viz_tsv(text):
    """VizieR asu-tsv -> list of dicts keyed by column name. Rows whose Source is not digits
    (units line, dashes line) are skipped. Raises ValueError on a VizieR error reply."""
    if text is None or "QUERY_STATUS=ERROR" in text:
        raise ValueError("VizieR error reply")
    lines = [l for l in text.splitlines() if l.strip() and not l.startswith("#")]
    if not lines:
        raise ValueError("empty VizieR reply")
    header = [h.strip() for h in lines[0].split("\t")]
    if "Source" not in header:
        raise ValueError("no Source column: %r" % header[:8])
    si = header.index("Source")
    rows = []
    for l in lines[1:]:
        cells = l.split("\t")
        if len(cells) <= si or not cells[si].strip().isdigit():
            continue
        rows.append({h: (cells[k].strip() if k < len(cells) else "") for k, h in enumerate(header)})
    return rows


def gaia_record(row, table):
    e = fnum(row.get("ecc"))
    return {"source_id": row["Source"].strip(), "table": table,
            "model": (row.get("NSSmodel") or "").strip() or table.split("/")[-1],
            "P": fnum(row.get("Per")), "eP": fnum(row.get("e_Per")),
            "e": e if math.isfinite(e) else 0.0, "ee": fnum(row.get("e_ecc"), 0.0),
            "K1": fnum(row.get("K1")), "eK1": fnum(row.get("e_K1")),
            "K2": fnum(row.get("K2")), "eK2": fnum(row.get("e_K2")),
            "goodness": fnum(row.get("goodness")), "signi": fnum(row.get("Signi")),
            "flags": (row.get("Flags") or "").strip()}


def period_status(p_gaia, p_deb):
    if not (finite(p_gaia, p_deb) and p_gaia > 0 and p_deb > 0):
        return "PERIOD_UNKNOWN"
    r = p_gaia / p_deb
    if abs(r - 1.0) <= P_OK_TOL:
        return "PERIOD_OK"
    if any(abs(r / f - 1.0) <= ALIAS_TOL for f in ALIAS_FACTORS):
        return "PERIOD_ALIAS"
    return "PERIOD_BAD"


def ksum_from_masses(m_tot, period, ecc, sin3i=1.0):
    fe = (1.0 - ecc * ecc) ** 1.5
    return (m_tot * sin3i / (MASS_CONST * fe * period)) ** (1.0 / 3.0)


def compare(deb, g):
    """One DEBCat system against one Gaia double-lined orbit."""
    out = {"pstat": period_status(g["P"], deb["P"])}
    K1, K2, eK1, eK2 = g["K1"], g["K2"], g["eK1"], g["eK2"]
    if not (finite(K1, K2) and K1 > 0 and K2 > 0):
        out["pstat"] = out["pstat"] + "/NO_K"
        return out
    eK1 = eK1 if finite(eK1) else float("nan")
    eK2 = eK2 if finite(eK2) else float("nan")
    (kmin, ekmin), (kmax, ekmax) = sorted([(K1, eK1), (K2, eK2)])
    (mmin, emmin), (mmax, emmax) = sorted([(deb["mA"], deb["emA"]), (deb["mB"], deb["emB"])])
    qg = kmin / kmax
    sqg = qg * math.hypot(ekmin / kmin, ekmax / kmax)
    qd = mmin / mmax
    sqd = qd * math.hypot(emmin / mmin, emmax / mmax)
    dq = qg - qd
    sq = math.hypot(sqg, sqd)
    fe = (1.0 - g["e"] ** 2) ** 1.5
    ksum = K1 + K2
    sks = math.hypot(eK1, eK2)
    mtot_g = MASS_CONST * fe * ksum ** 3 * g["P"]
    mtot_d = mmin + mmax
    smd = math.hypot(emmin, emmax)
    R = mtot_g / mtot_d
    sR = R * math.hypot(3.0 * sks / ksum, smd / mtot_d)
    heavy_g = MASS_CONST * fe * ksum ** 2 * kmax * g["P"]
    light_g = MASS_CONST * fe * ksum ** 2 * kmin * g["P"]
    out.update({"q_gaia": qg, "sq_gaia": sqg, "q_deb": qd, "sq_deb": sqd, "dq": dq,
                "zq": dq / sq if sq > 0 else float("nan"), "ksum": ksum, "sksum": sks,
                "mtot_gaia_sin3i": mtot_g, "mtot_deb": mtot_d, "R": R, "sR": sR,
                "R_heavy": heavy_g / mmax, "R_light": light_g / mmin,
                "impossible": bool(finite(sR) and (R - 1.0) > 3.0 * sR)})
    return out


def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return float("nan")
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def robust_std(xs):
    if not xs:
        return float("nan")
    m = median(xs)
    return 1.4826 * median([abs(x - m) for x in xs])


def boot_median_ci(xs, n=N_BOOT, seed=SEED):
    if len(xs) < 2:
        return [float("nan"), float("nan")]
    rng = random.Random(seed)
    meds = sorted(median([xs[rng.randrange(len(xs))] for _ in xs]) for _ in range(n))
    return [meds[int(0.025 * n)], meds[min(n - 1, int(0.975 * n))]]


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = 0.5 * (i + j) + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    saa = sum((x - ma) ** 2 for x in a)
    sbb = sum((y - mb) ** 2 for y in b)
    return sab / math.sqrt(saa * sbb) if saa > 0 and sbb > 0 else float("nan")


def spearman(a, b, n_perm=N_PERM, seed=SEED):
    """-> (rho, two-sided permutation p, n)."""
    pairs = [(x, y) for x, y in zip(a, b) if finite(x, y)]
    n = len(pairs)
    if n < 5:
        return float("nan"), float("nan"), n
    ra = ranks([p[0] for p in pairs])
    rb = ranks([p[1] for p in pairs])
    rho = pearson(ra, rb)
    if not math.isfinite(rho):
        return rho, float("nan"), n
    rng = random.Random(seed)
    rb2 = list(rb)
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(rb2)
        if abs(pearson(ra, rb2)) >= abs(rho) - 1e-12:
            hits += 1
    return rho, (hits + 1) / (n_perm + 1), n


def grade(recs):
    matched = [r for r in recs if r.get("gaia_source_id")]
    counts = {"n_debcat": len(recs), "n_with_gaia_id": sum(1 for r in recs if r.get("gaia_id")),
              "n_matched_sb2": len(matched)}
    for st in ("PERIOD_OK", "PERIOD_ALIAS", "PERIOD_BAD", "PERIOD_UNKNOWN"):
        counts[st] = sum(1 for r in matched if str(r.get("pstat", "")).startswith(st))
    S = [r for r in matched if r.get("pstat") == "PERIOD_OK" and finite(r.get("dq"), r.get("R"))]
    counts["n_sample"] = len(S)
    nonok = counts["PERIOD_ALIAS"] + counts["PERIOD_BAD"]
    counts["period_failure_rate"] = nonok / len(matched) if matched else float("nan")
    out = {"counts": counts}
    if len(S) < MIN_SAMPLE:
        for q in ("Q1", "Q2", "Q3", "Q4"):
            out[q] = {"label": "UNTESTABLE", "n": len(S)}
        return out
    dq = [r["dq"] for r in S]
    ci = boot_median_ci(dq)
    q1 = "Q_UNBIASED" if ci[0] <= 0.0 <= ci[1] else ("Q_LOW" if ci[1] < 0 else "Q_HIGH")
    out["Q1"] = {"n": len(S), "median_dq": median(dq), "ci95": ci, "label": q1,
                 "share_abs_z_gt3": sum(1 for r in S if finite(r["zq"]) and abs(r["zq"]) > 3) / len(S)}
    Rs = [r["R"] for r in S]
    ciR = boot_median_ci(Rs, seed=SEED + 1)
    if ciR[1] < SCALE_LO:
        q2 = "GAIA_MASSES_LOW"
    elif ciR[0] > SCALE_HI:
        q2 = "GAIA_MASSES_HIGH"
    else:
        q2 = "MASS_SCALE_OK"
    out["Q2"] = {"n": len(S), "median_R": median(Rs), "ci95": ciR, "label": q2,
                 "n_impossible": sum(1 for r in S if r.get("impossible")),
                 "share_R_below_0p93": sum(1 for x in Rs if x < 0.93) / len(S),
                 "median_R_heavy": median([r["R_heavy"] for r in S]),
                 "median_R_light": median([r["R_light"] for r in S])}
    zq = [r["zq"] for r in S if finite(r["zq"])]
    sz = robust_std(zq)
    out["Q3"] = {"n": len(zq), "robust_std_zq": sz, "median_zq": median(zq),
                 "label": "ERRORS_OK" if sz <= ERR_SCALE_MAX else "ERRORS_UNDERSTATED"}
    ks = [r["ksum"] for r in S]
    absz = [abs(r["zq"]) if finite(r["zq"]) else float("nan") for r in S]
    rho_rk, p_rk, n_rk = spearman(Rs, ks)
    q4 = {"rho_R_ksum": rho_rk, "p_R_ksum": p_rk, "n": n_rk,
          "label": "BLEND_SIGNAL" if (finite(rho_rk, p_rk) and rho_rk > 0 and p_rk < BLEND_P)
          else "NO_BLEND_SIGNAL"}
    for key, xs in (("absz_ksum", ks), ("absz_qdeb", [r["q_deb"] for r in S]),
                    ("absz_P", [r["P_gaia"] for r in S]),
                    ("absz_goodness", [r.get("goodness", float("nan")) for r in S]),
                    ("R_qdeb", None)):
        if key == "R_qdeb":
            rho, p, n = spearman(Rs, [r["q_deb"] for r in S])
        else:
            rho, p, n = spearman(absz, xs)
        q4["rho_" + key], q4["p_" + key], q4["n_" + key] = rho, p, n
    sb2 = [abs(r["zq"]) for r in S if r.get("model") == "SB2" and finite(r["zq"])]
    sb2c = [abs(r["zq"]) for r in S if r.get("model") != "SB2" and finite(r["zq"])]
    q4["median_absz_SB2"], q4["n_SB2"] = median(sb2), len(sb2)
    q4["median_absz_SB2C"], q4["n_SB2C"] = median(sb2c), len(sb2c)
    q4["median_R_SB2"] = median([r["R"] for r in S if r.get("model") == "SB2"])
    q4["median_R_SB2C"] = median([r["R"] for r in S if r.get("model") != "SB2"])
    out["Q4"] = q4
    return out


# ================================================================ self-test
def synthetic(n, k_scale=1.0, seed=SEED):
    rng = random.Random(seed)
    recs = []
    for i in range(n):
        m1 = rng.uniform(0.6, 3.0)
        q = rng.uniform(0.5, 1.0)
        m2 = q * m1
        P = math.exp(rng.uniform(math.log(1.0), math.log(20.0)))
        e = 0.0 if i % 2 == 0 else rng.uniform(0.0, 0.3)
        inc = math.radians(rng.uniform(86.0, 90.0))
        ks = ksum_from_masses(m1 + m2, P, e, math.sin(inc) ** 3)
        K1, K2 = ks * m2 / (m1 + m2), ks * m1 / (m1 + m2)
        eK1, eK2 = 0.01 * K1, 0.01 * K2
        g = {"source_id": str(1000 + i), "model": "SB2" if e > 0 else "SB2C", "P": P, "eP": 1e-5,
             "e": e, "ee": 0.0, "K1": k_scale * (K1 + rng.gauss(0, eK1)), "eK1": eK1,
             "K2": k_scale * (K2 + rng.gauss(0, eK2)), "eK2": eK2, "goodness": rng.gauss(0, 1),
             "signi": 50.0, "flags": ""}
        deb = {"name": "SYN %d" % i, "P": P, "mA": m1 * (1 + rng.gauss(0, 0.01)), "emA": 0.01 * m1,
               "mB": m2 * (1 + rng.gauss(0, 0.01)), "emB": 0.01 * m2}
        r = {"name": deb["name"], "gaia_id": g["source_id"], "gaia_source_id": g["source_id"],
             "model": g["model"], "P_gaia": P, "goodness": g["goodness"]}
        r.update(compare(deb, g))
        recs.append(r)
    return recs


def self_test():
    res = {}
    ok = True
    # 1. the mass constant: an Earth-mass-free one-solar-mass orbit of one year has K ~ 29.78 km/s
    ks = ksum_from_masses(1.0, 365.25, 0.0)
    res["ksum_1msun_1yr"] = ks
    ok &= abs(ks - 29.78) < 0.05
    # 2. unbiased synthetic sample
    g0 = grade(synthetic(300))
    res["unbiased"] = {"Q1": g0["Q1"]["label"], "median_dq": g0["Q1"]["median_dq"],
                       "Q2": g0["Q2"]["label"], "median_R": g0["Q2"]["median_R"],
                       "robust_std_zq": g0["Q3"]["robust_std_zq"]}
    ok &= abs(g0["Q1"]["median_dq"]) < 0.01 and g0["Q2"]["label"] == "MASS_SCALE_OK"
    ok &= 0.75 <= g0["Q3"]["robust_std_zq"] <= 1.3 and 0.98 <= g0["Q2"]["median_R"] <= 1.005
    # 3. K amplitudes 3% low -> masses ~9% low
    g1 = grade(synthetic(300, k_scale=0.97, seed=SEED + 7))
    res["biased_k097"] = {"Q2": g1["Q2"]["label"], "median_R": g1["Q2"]["median_R"]}
    ok &= g1["Q2"]["label"] == "GAIA_MASSES_LOW"
    # 4. parsers on fixed snippets
    html = ("<table><tr><th>System</th><th>Period (d)</th><th>V</th><th>Mass A</th><th>Mass B</th>"
            "<th>Radius A</th><th>Radius B</th></tr>"
            "<tr><td>RZ Cha</td><td>2.832</td><td>8.09</td><td>1.488 &plusmn; 0.007</td>"
            "<td>1.493 &plusmn; 0.007</td><td>2.264 &plusmn; 0.010</td><td>2.264 &plusmn; 0.010</td></tr>"
            "<tr><td>AI Phe</td><td>24.59</td><td>8.6</td><td>1.1938 &plusmn; 0.0008</td>"
            "<td>1.2438 &plusmn; 0.0008</td><td>1.835 &plusmn; 0.014</td><td>2.912 &plusmn; 0.014</td></tr></table>")
    deb = parse_debcat(html)
    res["parse_debcat_n"] = len(deb)
    ok &= len(deb) == 2 and abs(deb[0]["mB"] - 1.493) < 1e-9 and abs(deb[1]["rB"] - 2.912) < 1e-9
    res["pass"] = bool(ok)
    return res


# ================================================================ network
def http_get(url, timeout=HTTP_TIMEOUT, tries=3, data=None):
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA},
                                         method="POST" if data is not None else "GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:
            last = exc
        log("HTTP retry", url[:110], a + 1, repr(last)[:160])
        time.sleep(5 * (a + 1))
    raise RuntimeError("HTTP failed %s: %r" % (url[:110], last))


def fetch_debcat(local=None):
    if local:
        return open(local, encoding="utf-8", errors="replace").read(), local
    last = None
    for u in DEBCAT_URLS:
        try:
            return http_get(u, timeout=120).decode("utf-8", "replace"), u
        except Exception as exc:
            last = exc
    raise RuntimeError("DEBCat unreachable: %r" % last)


def fetch_viz_table(table, rounds=3):
    last = None
    for rnd in range(rounds):
        for base in VIZ_MIRRORS:
            url = base + "?-source=" + urllib.parse.quote(table, safe="/") + "&-out.all&-out.max=unlimited"
            try:
                rows = parse_viz_tsv(http_get(url, timeout=300, tries=2).decode("utf-8", "replace"))
                return rows, base
            except Exception as exc:
                last = exc
                log("VizieR", table, base, repr(exc)[:160])
        time.sleep(60 * (rnd + 1))
    raise RuntimeError("VizieR %s unavailable: %r" % (table, last))


def simbad_lookup(name, mirrors):
    errors, answered, main = 0, False, ""
    for v in name_variants(name):
        for base in mirrors:
            url = base + "?Ident=" + urllib.parse.quote(v) + "&output.format=ASCII"
            try:
                text = http_get(url, tries=2).decode("utf-8", "replace")
            except Exception:
                errors += 1
                continue
            answered = True
            gid, m = parse_simbad_ascii(text)
            time.sleep(PAUSE)
            if gid:
                return {"gaia_id": gid, "simbad_main": m, "simbad_status": "OK", "variant": v}
            if m:
                main = m
            break
    st = "NO_GAIA_ID" if main else ("NOT_FOUND" if answered else "ERROR")
    return {"gaia_id": None, "simbad_main": main, "simbad_status": st, "variant": ""}


# ================================================================ main
OUT_KEYS = ["name", "simbad_main", "simbad_status", "gaia_id", "gaia_source_id", "model", "P_deb",
            "P_gaia", "pstat", "e_gaia", "K1", "eK1", "K2", "eK2", "mA", "emA", "mB", "emB",
            "q_gaia", "sq_gaia", "q_deb", "sq_deb", "dq", "zq", "ksum", "mtot_gaia_sin3i",
            "mtot_deb", "R", "sR", "R_heavy", "R_light", "impossible", "goodness", "signi", "flags"]


def write_csv(path, rows, keys):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})


def run(args):
    os.makedirs(args.out_dir, exist_ok=True)
    summ_path = os.path.join(args.out_dir, "sb2_debcat_summary.json")
    meta = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    summary = {"meta": meta}
    st = self_test()
    summary["self_test"] = st
    log("self-test", "PASS" if st["pass"] else "FAIL", json.dumps(st)[:300])

    def dump(code):
        meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        json.dump(summary, open(summ_path, "w"), indent=1, default=str)
        return code

    # DEBCat
    try:
        text, src = fetch_debcat(args.debcat_file)
    except Exception as exc:
        summary["error"] = repr(exc)
        return dump(3)
    open(os.path.join(args.out_dir, "debcat_raw.html"), "w", encoding="utf-8").write(text)
    deb = parse_debcat(text)
    meta["debcat_source"], meta["debcat_n"] = src, len(deb)
    m = re.search(r"(?i)(last\s+(?:updated|modified)[^<]{0,80})", text)
    meta["debcat_updated_text"] = clean_cell(m.group(1)) if m else ""
    write_csv(os.path.join(args.out_dir, "debcat_parsed.csv"), deb,
              ["name", "P", "mA", "emA", "mB", "emB", "rA", "erA", "rB", "erB"])
    log("DEBCat systems parsed", len(deb))
    if len(deb) < MIN_DEBCAT:
        rows = table_rows(text)
        summary["error"] = "DEBCat parse gave %d systems (< %d)" % (len(deb), MIN_DEBCAT)
        summary["debcat_rows_sample"] = rows[:25]
        return dump(3)

    # Gaia double-lined tables
    gaia = {}
    tables = {}
    for table, expected in GAIA_TABLES:
        try:
            rows, mirror = fetch_viz_table(table)
        except Exception as exc:
            summary["error"] = repr(exc)
            return dump(2)
        tables[table] = {"rows": len(rows), "expected": expected, "mirror": mirror,
                         "complete": len(rows) >= 0.98 * expected}
        for r in rows:
            g = gaia_record(r, table)
            gaia.setdefault(g["source_id"], g)
    ctrl = gaia.get(TABLE_CONTROL_SOURCE)
    tables["control_row_ok"] = bool(ctrl and abs(ctrl["K1"] - TABLE_CONTROL_K1) < 0.01)
    meta["gaia_tables"] = tables
    log("Gaia SB2 orbits", len(gaia), json.dumps(tables))

    # SIMBAD control, then every DEBCat name
    mirrors = list(SIMBAD_MIRRORS)
    c = simbad_lookup(CONTROL_NAME, mirrors)
    if c["gaia_id"] != CONTROL_GAIA:
        mirrors = mirrors[1:] + mirrors[:1]
        c = simbad_lookup(CONTROL_NAME, mirrors)
    meta["simbad_control"] = {"name": CONTROL_NAME, "got": c["gaia_id"], "expected": CONTROL_GAIA,
                              "ok": c["gaia_id"] == CONTROL_GAIA, "mirror_first": mirrors[0]}
    recs = []
    for i, d in enumerate(deb):
        s = simbad_lookup(d["name"], mirrors)
        r = {"name": d["name"], "P_deb": d["P"], "mA": d["mA"], "emA": d["emA"], "mB": d["mB"],
             "emB": d["emB"]}
        r.update(s)
        g = gaia.get(s["gaia_id"]) if s["gaia_id"] else None
        if g:
            r.update({"gaia_source_id": g["source_id"], "model": g["model"], "P_gaia": g["P"],
                      "e_gaia": g["e"], "K1": g["K1"], "eK1": g["eK1"], "K2": g["K2"],
                      "eK2": g["eK2"], "goodness": g["goodness"], "signi": g["signi"],
                      "flags": g["flags"]})
            r.update(compare(d, g))
        recs.append(r)
        if (i + 1) % 50 == 0:
            log("looked up", i + 1, "of", len(deb))
    write_csv(os.path.join(args.out_dir, "matches.csv"), recs, OUT_KEYS)
    meta["simbad_status_counts"] = {k: sum(1 for r in recs if r["simbad_status"] == k)
                                    for k in ("OK", "NO_GAIA_ID", "NOT_FOUND", "ERROR")}

    # end-to-end control: RZ Cha
    rz = [r for r in recs if r.get("gaia_source_id") == CONTROL_GAIA]
    if rz:
        ks = sorted([rz[0]["K1"], rz[0]["K2"]])
        pc = all(abs(a - b) <= CONTROL_K_TOL for a, b in zip(ks, sorted(CONTROL_K)))
        summary["pipeline_control"] = {"found": True, "K": ks, "label": "PIPE_CONTROL_OK" if pc
                                       else "PIPE_CONTROL_FAIL", "R": rz[0].get("R"),
                                       "dq": rz[0].get("dq"), "pstat": rz[0].get("pstat")}
    else:
        summary["pipeline_control"] = {"found": False, "label": "PIPE_CONTROL_FAIL"}

    summary["grades"] = grade(recs)
    log("grades", json.dumps(summary["grades"], default=str)[:1500])
    return dump(0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--debcat-file", default=None, help="local DEBCat HTML instead of the web")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        res = self_test()
        print(json.dumps(res, indent=1))
        return 0 if res["pass"] else 1
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
