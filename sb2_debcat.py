#!/usr/bin/env python3
# sb2_debcat.py 0.2.0
# Gaia double-lined spectroscopic orbits (DR3: VizieR I/357 tbosb2 + tbosb2c, or any Gaia TAP
# schema incl. gaiadr4) against DEBCat, the catalogue of detached eclipsing binaries with masses
# and radii known to about 2%.
# MV2, Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.
# Pre-registration: findings/2026-11-24-sb2-debcat-prereg.md and
# findings/2026-11-24-sb2-debcat-amendment-1.md (both written before this code ran).
"""
What it does
1. Downloads DEBCat (Southworth 2015) twice: the web table (masses with errors) and the ascii
   file debs.dat (log masses). Every mass used is the web-table value that matches debs.dat
   ("anchored"), so a wrong guess about the web table's layout cannot enter the grades.
2. Gaia orbits: VizieR I/357/tbosb2 + tbosb2c in full (default, the registered DR3 test), or a
   Gaia TAP service (--gaia tap --schema gaiadr3|gaiadr4) with a schema gate, and for DR4 the
   DR3->DR4 crossmatch through <schema>.dr3_neighbourhood.
3. Resolves DEBCat names to Gaia DR3 source_id through SIMBAD (Harvard, then CDS) after a
   control lookup (RZ Cha -> Gaia DR3 5198334162577657984).
4. Per DEBCat system with a Gaia double-lined orbit: period status, folded mass ratio, and
   R = (M1+M2) sin^3 i (Gaia) / (M1+M2) (DEBCat).
5. Grades Q1-Q4 and writes sb2_debcat_summary.json, matches.csv, debcat_parsed.csv.
A self-test on synthetic binaries and fixed text snippets runs first and is recorded.
Exit codes: 0 done, 2 Gaia tables unavailable, 3 DEBCat parse/anchor gate failed, 4 schema gate.
"""
import argparse
import csv
import html as htmlmod
import io
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

VERSION = "0.2.0"
MASS_CONST = 1.036149e-7      # M_sun per (km/s)^3 day
UA = "gaia-orbit-transits/sb2_debcat (MV2, Munim, Inc.; open research)"
DEBCAT_URLS = ("https://www.astro.keele.ac.uk/jkt/debcat/",
               "http://www.astro.keele.ac.uk/jkt/debcat/")
DEBS_URLS = ("https://www.astro.keele.ac.uk/jkt/debcat/debs.dat",
             "http://www.astro.keele.ac.uk/jkt/debcat/debs.dat")
VIZ_MIRRORS = ("https://vizier.cfa.harvard.edu/viz-bin/asu-tsv",
               "https://vizier.cds.unistra.fr/viz-bin/asu-tsv")
GAIA_TABLES = (("I/357/tbosb2", 4630), ("I/357/tbosb2c", 746))
TAP_DEFAULT = ("https://gea.esac.esa.int/tap-server/tap/sync", "https://gaia.aip.de/tap/sync")
ORBIT_REQUIRED = ("source_id", "nss_solution_type", "period", "eccentricity",
                  "semi_amplitude_primary", "semi_amplitude_primary_error",
                  "semi_amplitude_secondary", "semi_amplitude_secondary_error")
SIMBAD_MIRRORS = ("https://simbad.cfa.harvard.edu/simbad/sim-id",
                  "https://simbad.cds.unistra.fr/simbad/sim-id")
CONTROL_NAME = "RZ Cha"
CONTROL_GAIA = "5198334162577657984"
CONTROL_P = 2.832
CONTROL_K = (107.8, 108.2)          # Southworth (2025, arXiv:2504.16817) quoting Gaia DR3 tbosb2
CONTROL_K_TOL = 0.5
TABLE_CONTROL_SOURCE = "6030061691987260672"   # first row of I/357/tbosb2, read 24 Nov 2026
TABLE_CONTROL_K1 = 56.3477
P_OK_TOL = 0.005
ALIAS_FACTORS = (0.5, 2.0, 1.0 / 3.0, 3.0)
ALIAS_TOL = 0.005
MIN_DEBCAT = 100
MIN_ANCHORED = 100
MIN_SAMPLE = 15
SCALE_LO, SCALE_HI = 0.97, 1.00
ERR_SCALE_MAX = 1.5
BLEND_P = 0.01
ANCHOR_REL, ANCHOR_ABS = 0.005, 0.0006
SEED = 20261124
N_BOOT = 2000
N_PERM = 5000
HTTP_TIMEOUT = 90
PAUSE = 0.35
CHUNK = 250

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


class GateError(Exception):
    pass


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


def parse_pms(s):
    """Every 'value ± error' pair in a string, in order."""
    return [(float(a), float(b)) for a, b in PM_RE.findall(s or "")]


def norm_name(s):
    """Name key shared by the web table ('V570 Per', 'α CrB') and debs.dat ('V570_Per')."""
    s = clean_cell(s).replace("_", " ")
    s = "".join(GREEK.get(ch, ch) for ch in s)
    toks = s.split()
    if toks and toks[0].lower() in GREEK_WORDS:
        toks[0] = GREEK_WORDS[toks[0].lower()]
    return re.sub(r"[^a-z0-9]", "", " ".join(toks).lower())


def table_rows(text):
    """HTML -> list of rows, each a list of cleaned cell strings (tolerates unclosed tags)."""
    rows = []
    for chunk in re.split(r"(?i)<tr(?:\s[^>]*)?>", text or "")[1:]:
        chunk = re.split(r"(?i)</tr\s*>|</table\s*>", chunk)[0]
        parts = re.split(r"(?i)<t[dh](?:\s[^>]*)?>", chunk)[1:]
        rows.append([clean_cell(p) for p in parts])
    return rows


def parse_debcat_row(cells, period_idx=None):
    """One web-table row -> record. All ± pairs after the period cell are kept in order
    (pm_all); the positional guess (first two = the two masses) is kept as mA/mB, NaN if it
    is not a plausible pair. The anchored masses (debs.dat) are what the grades use."""
    if len(cells) < 3:
        return None
    name = clean_name(cells[0])
    if not name or re.fullmatch(r"(?i)(system|name|star|object)", name):
        return None
    pidx = 1
    if period_idx is not None and 0 < period_idx < len(cells) and first_float(cells[period_idx]) is not None:
        pidx = period_idx
    if pidx >= len(cells) or parse_pms(cells[pidx]):
        return None                      # DEBCat periods carry no ±: this is not a system row
    P = first_float(cells[pidx])
    if P is None or not (0.05 < P < 20000.0):
        return None
    pms = []
    for j, c in enumerate(cells):
        if j > pidx:
            pms.extend(parse_pms(c))
    if len(pms) < 2:
        return None
    nan = float("nan")
    (mA, eA), (mB, eB) = pms[0], pms[1]
    pos_ok = 0.05 < mA < 150.0 and 0.05 < mB < 150.0 and eA >= 0 and eB >= 0
    rec = {"name": name, "P": P, "mA": mA if pos_ok else nan, "emA": eA if pos_ok else nan,
           "mB": mB if pos_ok else nan, "emB": eB if pos_ok else nan,
           "rA": nan, "erA": nan, "rB": nan, "erB": nan, "pm_all": list(pms), "pm_next": [],
           "mass_src": "POSITIONAL"}
    if pos_ok and len(pms) >= 4:
        (rA, erA), (rB, erB) = pms[2], pms[3]
        if 0.01 < rA < 2000 and 0.01 < rB < 2000:
            rec.update({"rA": rA, "erA": erA, "rB": rB, "erB": erB})
    return rec


def parse_debcat(text):
    """-> list of system dicts (first occurrence of each name kept). Each record also carries
    the ± pairs of the following table row (pm_next), for layouts with one row per star."""
    rows = table_rows(text)
    out, seen, period_idx = [], set(), None
    for i, cells in enumerate(rows):
        if any(re.search(r"(?i)period", c) for c in cells) and not any(parse_pms(c) for c in cells):
            for j, c in enumerate(cells):
                if re.search(r"(?i)period", c):
                    period_idx = j
                    break
            continue
        rec = parse_debcat_row(cells, period_idx)
        if rec and rec["name"] not in seen:
            if i + 1 < len(rows):
                rec["pm_next"] = [pm for c in rows[i + 1] for pm in parse_pms(c)]
            seen.add(rec["name"])
            out.append(rec)
    return out


def _find_col(header, patterns):
    for p in patterns:
        for i, h in enumerate(header):
            if re.fullmatch(p, h, re.I):
                return i
    return None


def parse_debs_dat(text):
    """DEBCat ascii file -> (dict norm_name -> {name, P, m1, m2}, info). Header is the last
    '#' line before the data that names a first-star mass column; '-9.99' means missing."""
    header, recs = None, {}
    info = {"n_lines": 0, "n_bad_width": 0, "header": None, "log_masses": None}
    im1 = im2 = ip = None
    is_log = False
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            toks = s.lstrip("#").split()
            c1 = _find_col(toks, [r"log\(?m_?1\)?", r"m_?1", r"mass_?1", r"m_?a"])
            c2 = _find_col(toks, [r"log\(?m_?2\)?", r"m_?2", r"mass_?2", r"m_?b"])
            if c1 is not None and c2 is not None:
                header, im1, im2 = toks, c1, c2
                ip = _find_col(toks, [r"p\(d\)", r"p", r"period.*", r"p\(.*\)", r"per"])
                is_log = "log" in toks[c1].lower()
                info["header"], info["log_masses"] = toks, is_log
            continue
        if header is None:
            continue
        info["n_lines"] += 1
        toks = s.split()
        if len(toks) != len(header):
            info["n_bad_width"] += 1
            continue
        vals = []
        for k in (im1, im2):
            x = fnum(toks[k])
            if not math.isfinite(x) or abs(x + 9.99) < 1e-6:
                vals.append(float("nan"))
            else:
                vals.append(10.0 ** x if is_log else x)
        m1, m2 = vals
        if not (finite(m1, m2) and 0.05 < m1 < 150 and 0.05 < m2 < 150):
            continue
        P = fnum(toks[ip]) if ip is not None else float("nan")
        key = norm_name(toks[0])
        if key and key not in recs:
            recs[key] = {"name": toks[0], "P": P, "m1": m1, "m2": m2}
    return recs, info


def _close(v, m):
    return abs(v - m) <= ANCHOR_REL * m + ANCHOR_ABS


def anchor_masses(rec, m1d, m2d):
    """Find the web-table ± pairs whose values equal debs.dat's masses -> ((m1,e1),(m2,e2)) or
    None. Searched in table order: this row first, then the following row."""
    pool = list(rec.get("pm_all", [])) + list(rec.get("pm_next", []))
    i1 = next((i for i, (v, e) in enumerate(pool) if _close(v, m1d)), None)
    if i1 is None:
        return None
    i2 = next((i for i, (v, e) in enumerate(pool) if i != i1 and _close(v, m2d)), None)
    if i2 is None:
        return None
    return pool[i1], pool[i2]


def apply_anchors(deb, dat):
    """-> (anchored records, check dict). Only systems whose web-table masses equal debs.dat's
    are kept; the positional guess is compared with the anchored values and reported."""
    kept, n_name, n_pos_agree, n_pos = [], 0, 0, 0
    for d in deb:
        a = dat.get(norm_name(d["name"]))
        if not a:
            continue
        n_name += 1
        got = anchor_masses(d, a["m1"], a["m2"])
        if not got:
            continue
        (m1, e1), (m2, e2) = got
        if finite(d["mA"], d["mB"]):
            n_pos += 1
            if sorted([d["mA"], d["mB"]]) == sorted([m1, m2]):
                n_pos_agree += 1
        r = dict(d)
        r.update({"mA": m1, "emA": e1, "mB": m2, "emB": e2, "mass_src": "ANCHORED",
                  "P_dat": a["P"]})
        kept.append(r)
    chk = {"n_web": len(deb), "n_dat": len(dat), "n_name_matched": n_name,
           "n_anchored": len(kept), "n_positional": n_pos, "n_positional_agrees": n_pos_agree,
           "label": "ANCHOR_OK" if len(kept) >= MIN_ANCHORED else "ANCHOR_FAIL"}
    return kept, chk


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


def parse_csv_text(raw):
    """TAP CSV reply -> (lower-case header, list of dict rows). Raises on an XML/HTML reply."""
    t = (raw or "").lstrip("﻿")
    if not t.strip() or t.lstrip().startswith("<"):
        raise ValueError("TAP reply is not CSV: %r" % t[:200])
    rows = list(csv.reader(io.StringIO(t)))
    header = [h.strip().strip('"').lower() for h in rows[0]]
    out = [dict(zip(header, [c.strip() for c in r])) for r in rows[1:] if r and any(x.strip() for x in r)]
    return header, out


def digits(s):
    return re.sub(r"\D", "", str(s or ""))


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


def tap_record(row, table):
    e = fnum(row.get("eccentricity"))
    return {"source_id": digits(row.get("source_id")), "table": table,
            "model": (row.get("nss_solution_type") or "").strip() or "?",
            "P": fnum(row.get("period")), "eP": fnum(row.get("period_error")),
            "e": e if math.isfinite(e) else 0.0, "ee": fnum(row.get("eccentricity_error"), 0.0),
            "K1": fnum(row.get("semi_amplitude_primary")),
            "eK1": fnum(row.get("semi_amplitude_primary_error")),
            "K2": fnum(row.get("semi_amplitude_secondary")),
            "eK2": fnum(row.get("semi_amplitude_secondary_error")),
            "goodness": fnum(row.get("goodness_of_fit")), "signi": fnum(row.get("significance")),
            "flags": str(row.get("flags") or "").strip()}


def neighbour_columns(header):
    """-> (dr3 column, dr4 column, distance column or None); GateError if not identifiable."""
    c3 = next((h for h in header if re.fullmatch(r"dr3_?source_id", h)), None)
    c4 = next((h for h in header if re.fullmatch(r"dr4_?source_id", h)), None)
    if c4 is None and "source_id" in header and c3 != "source_id":
        c4 = "source_id"
    if c3 is None or c4 is None:
        raise GateError("dr3_neighbourhood columns not identifiable: %r" % header)
    cd = "angular_distance" if "angular_distance" in header else None
    return c3, c4, cd


def best_neighbours(rows, c3, c4, cd):
    """-> {dr3_id: {"id": dr4_id, "n": candidates, "dist": distance}} (nearest candidate)."""
    cands = {}
    for r in rows:
        d3, d4 = digits(r.get(c3)), digits(r.get(c4))
        if not d3 or not d4:
            continue
        dist = fnum(r.get(cd)) if cd else float("nan")
        cands.setdefault(d3, []).append((dist if math.isfinite(dist) else float("inf"), d4))
    out = {}
    for d3, lst in cands.items():
        lst.sort()
        out[d3] = {"id": lst[0][1], "n": len(lst), "dist": lst[0][0]}
    return out


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


SNIP_STACKED = ("<table><tr><th>System</th><th>Period (days)</th><th>V B-V</th><th>Spectral type</th>"
                "<th>Mass (Msun)</th><th>Radius (Rsun)</th></tr>"
                "<tr><td>KX Cnc</td><td>31.220</td><td>7.19 0.57</td><td>F9 V<br>F9 V</td>"
                "<td>1.1345 &plusmn; 0.0032<br>1.1241 &plusmn; 0.0045</td>"
                "<td>1.0527 &plusmn; 0.0056<br>1.0593 &plusmn; 0.0051</td></tr></table>")
SNIP_TWO_ROW = ("<table><tr><td>AB Xyz</td><td>2.5</td><td>1.500 &plusmn; 0.010</td>"
                "<td>1.800 &plusmn; 0.020</td></tr>"
                "<tr><td>K0 V</td><td>1.200 &plusmn; 0.010</td><td>1.300 &plusmn; 0.020</td></tr></table>")
SNIP_DAT = ("# DEBCat ascii\n"
            "# System P(d) V B-V SpT1 SpT2 log(M1) log(M2) log(R1) log(R2)\n"
            "KX_Cnc 31.220 7.19 0.57 F9_V F9_V 0.0548 0.0508 0.0223 0.0250\n"
            "AB_Xyz 2.500 9.00 0.50 F0_V K0_V 0.1761 0.0792 0.2553 0.1139\n"
            "Bad_One 1.000 9.00 0.50 F0_V K0_V -9.99 0.0792 0.2553 0.1139\n")


def self_test():
    res = {}
    ok = True
    # 1. the mass constant: a one-solar-mass orbit of one year has K ~ 29.78 km/s
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
    # 4. web-table parser on separate-cell, stacked-cell and one-row-per-star layouts
    html = ("<table><tr><th>System</th><th>Period (d)</th><th>V</th><th>Mass A</th><th>Mass B</th>"
            "<th>Radius A</th><th>Radius B</th></tr>"
            "<tr><td>RZ Cha</td><td>2.832</td><td>8.09</td><td>1.488 &plusmn; 0.007</td>"
            "<td>1.493 &plusmn; 0.007</td><td>2.264 &plusmn; 0.010</td><td>2.264 &plusmn; 0.010</td></tr>"
            "<tr><td>AI Phe</td><td>24.59</td><td>8.6</td><td>1.1938 &plusmn; 0.0008</td>"
            "<td>1.2438 &plusmn; 0.0008</td><td>1.835 &plusmn; 0.014</td><td>2.912 &plusmn; 0.014</td></tr></table>")
    deb = parse_debcat(html)
    res["parse_debcat_n"] = len(deb)
    ok &= len(deb) == 2 and abs(deb[0]["mB"] - 1.493) < 1e-9 and abs(deb[1]["rB"] - 2.912) < 1e-9
    st = parse_debcat(SNIP_STACKED)
    ok &= len(st) == 1 and abs(st[0]["mA"] - 1.1345) < 1e-9 and abs(st[0]["mB"] - 1.1241) < 1e-9
    two = parse_debcat(SNIP_TWO_ROW)
    ok &= len(two) == 1 and two[0]["name"] == "AB Xyz"
    # 5. debs.dat anchoring repairs the one-row-per-star layout and keeps the stacked one
    dat, info = parse_debs_dat(SNIP_DAT)
    res["debs_dat_n"] = len(dat)
    ok &= len(dat) == 2 and info["log_masses"] is True
    kept, chk = apply_anchors(st + two, dat)
    res["anchor_check"] = chk
    byname = {r["name"]: r for r in kept}
    ok &= len(kept) == 2 and chk["n_positional_agrees"] == 1
    ok &= abs(byname["AB Xyz"]["mB"] - 1.200) < 1e-9 and abs(byname["AB Xyz"]["emB"] - 0.010) < 1e-12
    ok &= abs(byname["KX Cnc"]["emB"] - 0.0045) < 1e-12
    # 6. TAP csv and neighbour selection
    h, rows = parse_csv_text("source_id,nss_solution_type,period,eccentricity,semi_amplitude_primary,"
                             "semi_amplitude_primary_error,semi_amplitude_secondary,"
                             "semi_amplitude_secondary_error\n5198334162577657984,SB2C,2.83,,107.8,0.4,108.2,0.4\n")
    g = tap_record(rows[0], "tap")
    ok &= g["source_id"] == CONTROL_GAIA and g["e"] == 0.0 and abs(g["K2"] - 108.2) < 1e-9
    nb = best_neighbours([{"dr3_source_id": "1", "dr4_source_id": "11", "angular_distance": "5.0"},
                          {"dr3_source_id": "1", "dr4_source_id": "12", "angular_distance": "0.2"}],
                         "dr3_source_id", "dr4_source_id", "angular_distance")
    ok &= nb["1"]["id"] == "12" and nb["1"]["n"] == 2
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


def fetch_first(urls, local=None, what="file"):
    if local:
        return open(local, encoding="utf-8", errors="replace").read(), local
    last = None
    for u in urls:
        try:
            return http_get(u, timeout=120).decode("utf-8", "replace"), u
        except Exception as exc:
            last = exc
    raise RuntimeError("%s unreachable: %r" % (what, last))


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


def tap_sync(url, adql, timeout=300):
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                   "QUERY": adql}).encode()
    return parse_csv_text(http_get(url, timeout=timeout, tries=2, data=data).decode("utf-8", "replace"))


def tap_header(urls, table):
    """First TAP service that answers 'SELECT TOP 1 *' -> (url, header). RuntimeError if none."""
    last = None
    for u in urls:
        try:
            h, _ = tap_sync(u, "SELECT TOP 1 * FROM %s" % table)
            return u, h
        except Exception as exc:
            last = exc
            log("TAP", u, table, repr(exc)[:200])
    raise RuntimeError("no TAP service answered for %s: %r" % (table, last))


def chunks(xs, n=CHUNK):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def tap_orbits(url, schema, ids):
    out = {}
    ids = sorted(set(digits(i) for i in ids if digits(i)))
    for ch in chunks(ids):
        q = ("SELECT * FROM %s.nss_two_body_orbit WHERE semi_amplitude_secondary IS NOT NULL "
             "AND source_id IN (%s)" % (schema, ",".join(ch)))
        _, rows = tap_sync(url, q)
        for r in rows:
            g = tap_record(r, schema + ".nss_two_body_orbit")
            if g["source_id"]:
                out.setdefault(g["source_id"], g)
        time.sleep(PAUSE)
    return out


def tap_neighbours(url, schema, dr3_ids):
    _, header = tap_header([url], schema + ".dr3_neighbourhood")
    c3, c4, cd = neighbour_columns(header)
    rows = []
    ids = sorted(set(digits(i) for i in dr3_ids if digits(i)))
    for ch in chunks(ids):
        _, rr = tap_sync(url, "SELECT * FROM %s.dr3_neighbourhood WHERE %s IN (%s)"
                         % (schema, c3, ",".join(ch)))
        rows.extend(rr)
        time.sleep(PAUSE)
    return best_neighbours(rows, c3, c4, cd), {"dr3_col": c3, "dr4_col": c4, "dist_col": cd,
                                               "n_rows": len(rows)}


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
OUT_KEYS = ["name", "mass_src", "simbad_main", "simbad_status", "gaia_id", "gaia_source_id",
            "n_dr4_candidates", "model", "P_deb", "P_gaia", "pstat", "e_gaia", "K1", "eK1", "K2",
            "eK2", "mA", "emA", "mB", "emB", "q_gaia", "sq_gaia", "q_deb", "sq_deb", "dq", "zq",
            "ksum", "mtot_gaia_sin3i", "mtot_deb", "R", "sR", "R_heavy", "R_light", "impossible",
            "goodness", "signi", "flags"]


def write_csv(path, rows, keys):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})


def loader_check(recs, urls):
    """Rehearsal of the TAP loader on DR3: matched VizieR orbits must equal the TAP rows."""
    ids = [r["gaia_source_id"] for r in recs if r.get("gaia_source_id")]
    try:
        url, header = tap_header(urls, "gaiadr3.nss_two_body_orbit")
        miss = [c for c in ORBIT_REQUIRED if c not in header]
        if miss:
            return {"label": "LOADER_SCHEMA_MISMATCH", "missing": miss, "url": url}
        tap = tap_orbits(url, "gaiadr3", ids)
    except Exception as exc:
        return {"label": "LOADER_CONTROL_UNAVAILABLE", "error": repr(exc)[:300]}
    n, agree, bad = 0, 0, []
    for r in recs:
        sid = r.get("gaia_source_id")
        if not sid:
            continue
        n += 1
        t = tap.get(sid)
        if t and finite(t["P"], t["K1"], t["K2"], r["P_gaia"], r["K1"], r["K2"]) and \
                abs(t["P"] / r["P_gaia"] - 1) < 1e-4 and abs(t["K1"] - r["K1"]) < 0.01 and \
                abs(t["K2"] - r["K2"]) < 0.01:
            agree += 1
        else:
            bad.append(sid)
    return {"url": url, "n": n, "n_agree": agree, "disagree": bad[:20],
            "label": "LOADER_CONTROL_OK" if n and agree == n else "LOADER_CONTROL_FAIL"}


def run(args):
    os.makedirs(args.out_dir, exist_ok=True)
    summ_path = os.path.join(args.out_dir, "sb2_debcat_summary.json")
    dr4 = args.gaia == "tap" and args.schema != "gaiadr3"
    meta = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "gaia": args.gaia, "schema": args.schema if args.gaia == "tap" else "vizier I/357"}
    summary = {"meta": meta}
    st = self_test()
    summary["self_test"] = st
    log("self-test", "PASS" if st["pass"] else "FAIL", json.dumps(st)[:300])

    def dump(code):
        meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        meta["exit_code"] = code
        json.dump(summary, open(summ_path, "w"), indent=1, default=str)
        return code

    # DEBCat: web table + ascii file, anchored
    try:
        text, src = fetch_first(DEBCAT_URLS, args.debcat_file, "DEBCat web table")
        dtext, dsrc = fetch_first(DEBS_URLS, args.debs_file, "DEBCat debs.dat")
    except Exception as exc:
        summary["error"] = repr(exc)
        return dump(3)
    open(os.path.join(args.out_dir, "debcat_raw.html"), "w", encoding="utf-8").write(text)
    open(os.path.join(args.out_dir, "debs_raw.dat"), "w", encoding="utf-8").write(dtext)
    deb_all = parse_debcat(text)
    dat, dinfo = parse_debs_dat(dtext)
    meta["debcat_source"], meta["debcat_n"] = src, len(deb_all)
    meta["debs_source"], meta["debs_n"], meta["debs_info"] = dsrc, len(dat), dinfo
    m = re.search(r"(?i)(last\s+(?:updated|modified)[^<]{0,80})", text)
    meta["debcat_updated_text"] = clean_cell(m.group(1)) if m else ""
    deb, chk = apply_anchors(deb_all, dat)
    meta["anchor_check"] = chk
    write_csv(os.path.join(args.out_dir, "debcat_parsed.csv"), deb,
              ["name", "P", "P_dat", "mA", "emA", "mB", "emB", "rA", "erA", "rB", "erB", "mass_src"])
    log("DEBCat web rows", len(deb_all), "debs.dat", len(dat), "anchored", len(deb), json.dumps(chk))
    if len(deb_all) < MIN_DEBCAT or len(dat) < MIN_DEBCAT or chk["label"] != "ANCHOR_OK":
        summary["error"] = "DEBCat gate failed: web %d, debs.dat %d, anchored %d" % (
            len(deb_all), len(dat), len(deb))
        summary["debcat_rows_sample"] = table_rows(text)[:25]
        summary["debs_sample"] = dtext.splitlines()[:25]
        return dump(3)

    # SIMBAD control, then every anchored DEBCat name
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
        r = {"name": d["name"], "mass_src": d["mass_src"], "P_deb": d["P"], "mA": d["mA"],
             "emA": d["emA"], "mB": d["mB"], "emB": d["emB"]}
        r.update(s)
        recs.append(r)
        if (i + 1) % 50 == 0:
            log("looked up", i + 1, "of", len(deb))
    meta["simbad_status_counts"] = {k: sum(1 for r in recs if r["simbad_status"] == k)
                                    for k in ("OK", "NO_GAIA_ID", "NOT_FOUND", "ERROR")}
    dr3_ids = sorted(set([r["gaia_id"] for r in recs if r.get("gaia_id")] + [CONTROL_GAIA]))

    # Gaia double-lined orbits
    idmap = {i: {"id": i, "n": 1, "dist": 0.0} for i in dr3_ids}
    if args.gaia == "vizier":
        gaia, tables = {}, {}
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
    else:
        urls = [u for u in args.tap_url.split(",") if u.strip()]
        try:
            url, header = tap_header(urls, args.schema + ".nss_two_body_orbit")
        except Exception as exc:
            summary["error"] = repr(exc)
            return dump(2)
        miss = [c for c in ORBIT_REQUIRED if c not in header]
        meta["schema_gate"] = {"url": url, "missing": miss, "header": header,
                               "label": "SCHEMA_OK" if not miss else "SCHEMA_FAIL"}
        if miss:
            return dump(4)
        if dr4:
            try:
                idmap, nmeta = tap_neighbours(url, args.schema, dr3_ids)
            except GateError as exc:
                meta["neighbour_gate"] = {"label": "SCHEMA_FAIL", "error": str(exc)}
                return dump(4)
            except Exception as exc:
                summary["error"] = repr(exc)
                return dump(2)
            rz = idmap.get(CONTROL_GAIA)
            nmeta["map_control"] = {"dr3": CONTROL_GAIA, "dr4": rz["id"] if rz else None,
                                    "n": rz["n"] if rz else 0,
                                    "label": "MAP_CONTROL_OK" if rz else "MAP_CONTROL_FAIL"}
            meta["neighbours"] = nmeta
        try:
            gaia = tap_orbits(url, args.schema, [v["id"] for v in idmap.values()])
        except Exception as exc:
            summary["error"] = repr(exc)
            return dump(2)
        meta["gaia_tables"] = {"tap": url, "orbits_returned": len(gaia)}
    log("Gaia double-lined orbits available", len(gaia))

    for r, d in zip(recs, deb):
        mp = idmap.get(r.get("gaia_id")) if r.get("gaia_id") else None
        g = gaia.get(mp["id"]) if mp else None
        if mp:
            r["n_dr4_candidates"] = mp["n"] if dr4 else ""
        if g:
            r.update({"gaia_source_id": g["source_id"], "model": g["model"], "P_gaia": g["P"],
                      "e_gaia": g["e"], "K1": g["K1"], "eK1": g["eK1"], "K2": g["K2"],
                      "eK2": g["eK2"], "goodness": g["goodness"], "signi": g["signi"],
                      "flags": g["flags"]})
            r.update(compare(d, g))
    write_csv(os.path.join(args.out_dir, "matches.csv"), recs, OUT_KEYS)

    # end-to-end control: RZ Cha
    rz = [r for r in recs if r.get("gaia_id") == CONTROL_GAIA and r.get("gaia_source_id")]
    if rz and not dr4:
        ks = sorted([rz[0]["K1"], rz[0]["K2"]])
        pc = all(abs(a - b) <= CONTROL_K_TOL for a, b in zip(ks, sorted(CONTROL_K)))
        summary["pipeline_control"] = {"found": True, "K": ks, "label": "PIPE_CONTROL_OK" if pc
                                       else "PIPE_CONTROL_FAIL", "R": rz[0].get("R"),
                                       "dq": rz[0].get("dq"), "pstat": rz[0].get("pstat")}
    elif rz and dr4:
        ks = sorted([rz[0]["K1"], rz[0]["K2"]])
        pc = period_status(rz[0]["P_gaia"], CONTROL_P) == "PERIOD_OK"
        summary["pipeline_control"] = {"found": True, "K": ks,
                                       "K_minus_dr3": [a - b for a, b in zip(ks, sorted(CONTROL_K))],
                                       "label": "PIPE_CONTROL_OK" if pc else "PIPE_CONTROL_FAIL",
                                       "R": rz[0].get("R"), "dq": rz[0].get("dq"),
                                       "pstat": rz[0].get("pstat")}
    else:
        summary["pipeline_control"] = {"found": False,
                                       "label": "PIPE_CONTROL_ABSENT" if dr4 else "PIPE_CONTROL_FAIL"}

    summary["grades"] = grade(recs)
    log("grades", json.dumps(summary["grades"], default=str)[:1500])

    if args.tap_check and args.gaia == "vizier":
        summary["loader_check"] = loader_check(recs, [u for u in args.tap_check.split(",") if u])
        log("loader check", json.dumps(summary["loader_check"])[:400])

    if dr4:      # exploratory: Gaia's own published masses for the matched systems
        try:
            ids = [r["gaia_source_id"] for r in recs if r.get("gaia_source_id")]
            mrows = []
            for ch in chunks(sorted(set(ids))):
                h, rr = tap_sync(url, "SELECT * FROM %s.nss_masses WHERE source_id IN (%s)"
                                 % (args.schema, ",".join(ch)))
                mrows.extend(rr)
            byid = {}
            for mr in mrows:
                byid.setdefault(digits(mr.get("source_id")), mr)
            ratios = []
            for r in recs:
                mr = byid.get(r.get("gaia_source_id") or "")
                if mr and r.get("pstat") == "PERIOD_OK":
                    m1, m2 = fnum(mr.get("m1")), fnum(mr.get("m2"))
                    if finite(m1, m2) and m1 > 0 and m2 > 0:
                        ratios.append((m1 + m2) / (r["mA"] + r["mB"]))
            if mrows:
                write_csv(os.path.join(args.out_dir, "nss_masses_matched.csv"), mrows,
                          sorted(mrows[0].keys()))
            summary["nss_masses_exploratory"] = {"rows": len(mrows), "n_ratio": len(ratios),
                                                 "median_mtot_ratio": median(ratios),
                                                 "robust_std": robust_std(ratios)}
        except Exception as exc:
            summary["nss_masses_exploratory"] = {"error": repr(exc)[:300]}
    return dump(0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--debcat-file", default=None, help="local DEBCat HTML instead of the web")
    ap.add_argument("--debs-file", default=None, help="local DEBCat debs.dat instead of the web")
    ap.add_argument("--gaia", choices=("vizier", "tap"), default="vizier")
    ap.add_argument("--schema", default="gaiadr3", help="TAP schema, e.g. gaiadr3 or gaiadr4")
    ap.add_argument("--tap-url", default=",".join(TAP_DEFAULT), help="comma-separated TAP sync URLs")
    ap.add_argument("--tap-check", default="", help="vizier mode: also compare with these TAP URLs")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        res = self_test()
        print(json.dumps(res, indent=1))
        return 0 if res["pass"] else 1
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
