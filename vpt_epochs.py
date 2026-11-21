# SPDX-License-Identifier: Apache-2.0
"""vpt_epochs 0.1.0: why are Gaia DR3's transit periods wrong for most known planets?

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Pre-registration: findings/2026-11-21-vpt-epochs-prereg.md (written before any Gaia epoch
photometry of these stars was downloaded by this project).

The DR3 rehearsal of step g (findings/2026-11-21-vpt-dr3-results.md) found that Gaia DR3's
published transit_period matches the known period (ratio 1, 1/2 or 2, within 1%) for only 15 of
176 known systems in vari_planetary_transit. This module downloads Gaia DR3's own G-band epoch
photometry for all 214 candidates and asks why:

  T1  validity: for known planets whose Gaia period IS right (ratio 1 or 1/2), do the
      num_in_transit epochs nearest Gaia's transit centres fall inside the real transits
      predicted from the NASA Exoplanet Archive / TOI ephemeris? (checks times and ephemerides)
  WHY for known systems whose Gaia period is wrong: are Gaia's in-transit epochs real transit
      epochs (ALIAS: Gaia saw the real dips but drew the wrong period through them) or not
      (SPURIOUS: PARTIAL or UNRELATED)?
  T3  can Gaia's own photometry flag a wrong period? N_comp = number of separate box-search
      periodogram peaks (0.2-40 d) at least 0.9 x as strong as the peak at Gaia's period.
      Does low N_comp pick out the right periods (AUC, one-sided Mann-Whitney)?

Epoch photometry comes from ESA's DataLink (gea.esac.esa.int/data-server) and, for anything it
does not return, from ESA's bulk CDN files (cdn.gea.esac.esa.int/Gaia/gdr3/Photometry/
epoch_photometry/). ESA's archive closes 25 Nov 2026 12:00 CET until Gaia DR4 opens.

Exit codes: 0 ok; 2 data unavailable (re-file unchanged); 3 self-test failed; 4 inputs missing.
"""
import argparse
import csv
import gzip
import io
import json
import math
import os
import random
import re
import sys
import time
import traceback
import zipfile

VERSION = "0.1.0"

# ---- pre-registered constants (findings/2026-11-21-vpt-epochs-prereg.md) ----
GAIA_T_OFFSET = 2455197.5          # Gaia epoch time = BJD(TCB) - 2455197.5; TCB-TDB ~20 s ignored
PERIOD_TOL = 0.01
MATCH_FACTORS = (1.0, 0.5, 2.0)    # catalogue period / Gaia period
CONTROL_FACTORS = (1.0, 0.5)       # T1 controls: Gaia period = known period or twice it
PURITY_ALIAS = 0.5
MIN_NT = 2                         # real-transit epochs needed for a testable star
MIN_NG = 2                         # Gaia in-transit epochs needed
EPH_SIGMA_FRAC = 0.25              # ephemeris usable if propagated 1-sigma <= 0.25 x T14
MIN_EPOCHS = 15
T1_MIN_SHARE = 0.80
T1_MIN_N = 8
WHY_MIN_N = 10
SEEN_SNR = 3.0                     # real transit "seen" in Gaia epochs
PERIOD_MIN, PERIOD_MAX = 0.2, 40.0
BOX_MIN, BOX_MAX = 0.04, 0.25      # box width (d) from Gaia's transit_duration, clipped
GRID_FACTOR = 2.5                  # d ln f = box / (GRID_FACTOR x baseline)
MAX_FREQS = 600000                 # coarser grid above this (recorded per star)
NIN_MIN = 3
COMP_FRAC = 0.9
CLUSTER_GAP = 5                    # grid steps separating periodogram peaks
T3_MIN_RIGHT = 8
T3_AUC_HI, T3_AUC_LO, T3_P = 0.70, 0.60, 0.01

UA = "gaia-orbit-transits/vpt_epochs (MV2, Munim, Inc.; open research)"
DATALINK_URL = "https://gea.esac.esa.int/data-server/data"
DATALINK_STRUCTURES = ("DATAMODEL_STANDARD", "INDIVIDUAL", "DATAMODEL_GAIA")
CDN_BASE = "https://cdn.gea.esac.esa.int/Gaia/gdr3/Photometry/epoch_photometry/"
EXOARCH_URL = ("https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query="
               "select+pl_name,tic_id,pl_orbper,pl_orbpererr1,pl_tranmid,pl_tranmiderr1,"
               "pl_trandur+from+pscomppars+where+tic_id+is+not+null&format=csv")
TOI_URL = "https://exofop.ipac.caltech.edu/tess/download_toi.php?sort=toi&output=csv"
FP_DISP = ("FP", "FA")
HTTP_TIMEOUT = 180

STAR_KEYS = [
    "source_id", "status", "category", "category_detail", "tic", "G", "P_gaia", "T0_gaia",
    "dur_gaia", "num_in_transit", "n_epochs", "n_rejected", "baseline_d", "sd_flux",
    "eph_name", "eph_src", "P_true", "T0_true_gaia", "dur_true", "eph_sigma_d", "eph_testable",
    "match_factor", "n_t", "n_g", "n_both", "coverage", "purity", "chance_purity", "depth_t",
    "snr_t", "depth_g", "snr_g_fixed", "gaia_within_frac", "why_label", "box_d", "n_freq",
    "grid_coarsened", "snr_g_free", "snr_true_free", "P_best", "snr_best", "n_comp",
    "frac_above", "true_beats_gaia", "ratio_Pg_Pt", "error"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ================================================================ pure helpers (stdlib)
def fval(row, key, default=float("nan")):
    try:
        v = row.get(key, default) if isinstance(row, dict) else row
        if v is None or (isinstance(v, str) and v.strip().strip('"') in
                         ("", "null", "NaN", "nan", "--", "None")):
            return default
        v = float(str(v).strip().strip('"'))
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def truthy(v):
    return str(v).strip().strip('"').lower() in ("true", "1", "t", "yes")


def norm_tic(v):
    s = str(v or "").upper().replace("TIC", "").strip()
    s = s.split(".")[0].strip()
    return s.lstrip("0")


def period_match(p_gaia, p_cat, tol=PERIOD_TOL, factors=MATCH_FACTORS):
    if not (math.isfinite(p_gaia) and math.isfinite(p_cat)) or p_gaia <= 0 or p_cat <= 0:
        return None
    for f in factors:
        if abs(p_cat / (f * p_gaia) - 1.0) <= tol:
            return f
    return None


def parse_array(s):
    """Gaia array cell ('[1.0, 2.0, null]', '(1,2)', '1 2') -> list of floats (nan for null)."""
    s = str(s or "").strip().strip('"').strip()
    s = s.strip("[]()").strip()
    if not s:
        return []
    parts = re.split(r"[,\s]+", s)
    return [fval({"v": p}, "v") for p in parts if p != ""]


def parse_bool_array(s):
    s = str(s or "").strip().strip('"').strip().strip("[]()").strip()
    if not s:
        return []
    return [truthy(p) for p in re.split(r"[,\s]+", s) if p != ""]


def _empty():
    return {"t": [], "flux": [], "ferr": [], "rej": []}


def parse_epoch_text(text, hint_sid=None):
    """One DataLink / bulk CSV text -> {source_id: {t, flux, ferr, rej}} (G band only).
    Handles the long format (one row per epoch and band, with a 'band' column) and the wide
    format (one row per source with g_transit_time / g_transit_flux arrays)."""
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return {}
    reader = csv.reader(lines)
    try:
        header = [h.strip().strip('"').lower() for h in next(reader)]
    except StopIteration:
        return {}
    out = {}
    if "g_transit_time" in header:
        for row in reader:
            r = dict(zip(header, row))
            sid = str(r.get("source_id", "") or hint_sid or "").strip()
            if not sid:
                continue
            t = parse_array(r.get("g_transit_time", ""))
            fl = parse_array(r.get("g_transit_flux", ""))
            fe = parse_array(r.get("g_transit_flux_error", ""))
            rj = parse_bool_array(r.get("variability_flag_g_reject", ""))
            n = len(t)
            if len(fl) != n:
                continue
            fe = fe if len(fe) == n else [float("nan")] * n
            rj = rj if len(rj) == n else [False] * n
            rec = out.setdefault(sid, _empty())
            rec["t"] += t
            rec["flux"] += fl
            rec["ferr"] += fe
            rec["rej"] += rj
        return out
    tcol = next((c for c in ("time", "obs_time", "g_obs_time") if c in header), None)
    if tcol is None or "flux" not in header:
        return {}
    for row in reader:
        r = dict(zip(header, row))
        band = str(r.get("band", "G")).strip().strip('"').upper()
        if band != "G":
            continue
        sid = str(r.get("source_id", "") or hint_sid or "").strip()
        if not sid:
            continue
        rec = out.setdefault(sid, _empty())
        rec["t"].append(fval(r, tcol))
        rec["flux"].append(fval(r, "flux"))
        rec["ferr"].append(fval(r, "flux_error"))
        rec["rej"].append(truthy(r.get("rejected_by_variability", ""))
                          or truthy(r.get("rejected_by_photometry", "")))
    return out


def parse_datalink_payload(data):
    """DataLink answer (zip or plain text bytes) -> {source_id: epochs}."""
    out = {}
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                if name.endswith("/"):
                    continue
                m = re.findall(r"(\d{6,})", name)
                hint = m[-1] if m else None
                text = z.read(name).decode("utf-8", "replace")
                for sid, rec in parse_epoch_text(text, hint).items():
                    out.setdefault(sid, _empty())
                    for k in rec:
                        out[sid][k] += rec[k]
        return out
    return parse_epoch_text(data.decode("utf-8", "replace"))


def clean_epochs(rec):
    """-> (t, flux, ferr, n_rejected) with finite time, positive flux, not rejected; sorted."""
    rows = []
    nrej = 0
    for t, f, e, r in zip(rec["t"], rec["flux"], rec["ferr"], rec["rej"]):
        if r:
            nrej += 1
            continue
        if math.isfinite(t) and math.isfinite(f) and f > 0:
            rows.append((t, f, e))
    rows.sort()
    return [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows], nrej


def median(v):
    s = sorted(v)
    n = len(s)
    if n == 0:
        return float("nan")
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def robust_sd(v):
    m = median(v)
    return 1.4826 * median([abs(x - m) for x in v])


def phase_dist(t, T0, P):
    """Absolute time distance (d) of each epoch from the nearest transit centre."""
    out = []
    for x in t:
        c = (x - T0) / P
        out.append(abs(c - round(c)) * P)
    return out


def nearest_k(t, T0, P, k):
    d = phase_dist(t, T0, P)
    order = sorted(range(len(t)), key=lambda i: (d[i], i))
    return sorted(order[:max(0, min(k, len(t)))])


def window_set(t, T0, P, half):
    return [i for i, x in enumerate(phase_dist(t, T0, P)) if x <= half]


def set_depth_snr(fn, idx, sd):
    """Mean out-of-set minus mean in-set (normalised flux) and its white-noise S/N."""
    s = set(idx)
    fin = [fn[i] for i in s]
    fout = [fn[i] for i in range(len(fn)) if i not in s]
    if not fin or not fout or not (sd > 0):
        return float("nan"), float("nan")
    d = sum(fout) / len(fout) - sum(fin) / len(fin)
    return d, d / (sd * math.sqrt(1.0 / len(fin) + 1.0 / len(fout)))


def classify_why(eph_testable, n_t, n_g, n_both):
    if not eph_testable or n_t < MIN_NT or n_g < MIN_NG:
        return "UNTESTABLE"
    if n_both / n_g >= PURITY_ALIAS:
        return "ALIAS"
    return "PARTIAL" if n_both > 0 else "UNRELATED"


def eph_sigma(eph, t_mid_gaia):
    """1-sigma timing error (d) of the ephemeris propagated to Gaia time t_mid_gaia."""
    P, Pe, T0, T0e = eph["P"], eph["Perr"], eph["T0g"], eph["T0err"]
    if not (math.isfinite(P) and math.isfinite(Pe) and math.isfinite(T0)):
        return float("nan")
    n = (t_mid_gaia - T0) / P
    T0e = T0e if math.isfinite(T0e) else 0.0
    return math.sqrt((n * Pe) ** 2 + T0e ** 2)


def _mk_eph(name, src, P, Perr, T0, T0err, dur_h, disp=""):
    T0g = T0 - GAIA_T_OFFSET if (math.isfinite(T0) and T0 > 2.4e6) else float("nan")
    return {"name": name, "src": src, "P": P, "Perr": abs(Perr) if math.isfinite(Perr) else Perr,
            "T0g": T0g, "T0err": abs(T0err) if math.isfinite(T0err) else T0err,
            "dur": dur_h / 24.0 if math.isfinite(dur_h) else float("nan"), "disp": disp}


def parse_exoarch_eph(text):
    out = {}
    for r in csv.DictReader(io.StringIO(text or "")):
        tic = norm_tic(r.get("tic_id", ""))
        if not tic:
            continue
        out.setdefault(tic, []).append(_mk_eph(
            r.get("pl_name", ""), "archive", fval(r, "pl_orbper"), fval(r, "pl_orbpererr1"),
            fval(r, "pl_tranmid"), fval(r, "pl_tranmiderr1"), fval(r, "pl_trandur")))
    return out


def parse_toi_eph(text):
    out = {}
    for r in csv.DictReader(io.StringIO(text or "")):
        tic = norm_tic(r.get("TIC ID", ""))
        if not tic:
            continue
        disp = str(r.get("TFOPWG Disposition", "") or "").strip().upper()
        if disp in FP_DISP:
            continue
        out.setdefault(tic, []).append(_mk_eph(
            "TOI-%s" % str(r.get("TOI", "")).strip(), "toi", fval(r, "Period (days)"),
            fval(r, "Period (days) err"), fval(r, "Epoch (BJD)"), fval(r, "Epoch (BJD) err"),
            fval(r, "Duration (hours)"), disp))
    return out


def merge_ephs(arch, toi):
    """Archive ephemerides first; a TOI is added only if no archive planet has its period."""
    out = {}
    for tic in set(arch) | set(toi):
        lst = list(arch.get(tic, []))
        for e in toi.get(tic, []):
            if not any(period_match(e["P"], a["P"], factors=(1.0,)) for a in lst):
                lst.append(e)
        out[tic] = lst
    return out


def wilson(k, n, z=1.96):
    if n <= 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, c - h), min(1.0, c + h)


def mann_whitney_low(a, b):
    """AUC = P(a < b) + 0.5 P(a == b) and one-sided p for 'a tends lower than b'
    (normal approximation with tie and continuity corrections)."""
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return float("nan"), float("nan")
    u = 0.0
    for x in a:
        for y in b:
            u += 1.0 if x < y else (0.5 if x == y else 0.0)
    auc = u / (n1 * n2)
    allv = sorted(list(a) + list(b))
    N = n1 + n2
    ties = 0.0
    i = 0
    while i < N:
        j = i
        while j + 1 < N and allv[j + 1] == allv[i]:
            j += 1
        tcount = j - i + 1
        ties += tcount ** 3 - tcount
        i = j + 1
    var = n1 * n2 / 12.0 * ((N + 1) - ties / (N * (N - 1))) if N > 1 else 0.0
    if var <= 0:
        return auc, float("nan")
    z = (u - n1 * n2 / 2.0 - 0.5) / math.sqrt(var)
    return auc, 0.5 * math.erfc(z / math.sqrt(2.0))


def cdn_index(md5_text):
    """_MD5SUM.txt -> sorted [(hp_lo, hp_hi, file name)]."""
    out = []
    for m in re.finditer(r"(EpochPhotometry_(\d+)-(\d+)\.csv\.gz)", md5_text or ""):
        out.append((int(m.group(2)), int(m.group(3)), m.group(1)))
    return sorted(set(out))


def healpix8(sid):
    return int(sid) >> 35


def cdn_file_for(sid, index):
    hp = healpix8(sid)
    for lo, hi, name in index:
        if lo <= hp <= hi:
            return name
    return None


def clip(x, lo, hi):
    return max(lo, min(hi, x))


# ---------------------------------------------------------------- per-star analysis
def choose_eph(ephs, P_gaia, t, fn, sd, t_mid, control):
    """Return (eph, factor). Controls: the ephemeris whose period matches Gaia's.
    Others: the testable ephemeris whose real-transit window has the highest S/N in Gaia's
    epochs (no use of Gaia's in-transit set), else the first with a period."""
    usable = [e for e in ephs if math.isfinite(e["P"]) and e["P"] > 0]
    if not usable:
        return None, None
    for e in usable:
        f = period_match(P_gaia, e["P"])
        if f is not None and control:
            return e, f
    best, best_s = None, -1e9
    for e in usable:
        sig = eph_sigma(e, t_mid)
        if not (math.isfinite(e["T0g"]) and math.isfinite(e["dur"]) and e["dur"] > 0
                and math.isfinite(sig) and sig <= EPH_SIGMA_FRAC * e["dur"]):
            continue
        idx = window_set(t, e["T0g"], e["P"], e["dur"] / 2.0)
        _, s = set_depth_snr(fn, idx, sd)
        s = s if math.isfinite(s) else -1e8
        if s > best_s:
            best, best_s = e, s
    e = best or usable[0]
    return e, period_match(P_gaia, e["P"])


def analyse_epochs(target, t, fl, ephs):
    """Everything except the periodogram. Returns the star record (dict)."""
    rec = {k: "" for k in STAR_KEYS}
    rec.update({k: target.get(k, "") for k in ("source_id", "category", "category_detail",
                                                 "tic", "G")})
    Pg, T0g, dg = target["P_gaia"], target["T0_gaia"], target["dur_gaia"]
    nin = target["num_in_transit"]
    rec.update({"P_gaia": Pg, "T0_gaia": T0g, "dur_gaia": dg, "num_in_transit": nin,
                "n_epochs": len(t)})
    if len(t) < MIN_EPOCHS:
        rec["status"] = "FEW_EPOCHS"
        return rec
    med = median(fl)
    fn = [x / med for x in fl]
    sd = robust_sd(fn)
    t_mid = 0.5 * (t[0] + t[-1])
    rec["baseline_d"] = t[-1] - t[0]
    rec["sd_flux"] = sd
    k = int(nin) if isinstance(nin, int) and nin > 0 else 0
    if k > 0:
        S_g = nearest_k(t, T0g, Pg, k)
    else:
        S_g = window_set(t, T0g, Pg, dg / 2.0) if math.isfinite(dg) else []
    if S_g and math.isfinite(dg):
        dist = phase_dist([t[i] for i in S_g], T0g, Pg)
        rec["gaia_within_frac"] = sum(1 for x in dist if x <= dg / 2.0 + 0.01) / len(S_g)
    rec["n_g"] = len(S_g)
    rec["depth_g"], rec["snr_g_fixed"] = set_depth_snr(fn, S_g, sd)
    control = target["category"] == "KNOWN_PLANET"
    e, f = choose_eph(ephs, Pg, t, fn, sd, t_mid, control)
    if e is None:
        rec["status"] = "NO_EPHEMERIS"
        rec["why_label"] = "UNTESTABLE"
        return rec
    sig = eph_sigma(e, t_mid)
    testable = bool(math.isfinite(e["T0g"]) and math.isfinite(e["dur"]) and e["dur"] > 0
                    and math.isfinite(sig) and sig <= EPH_SIGMA_FRAC * e["dur"])
    rec.update({"eph_name": e["name"], "eph_src": e["src"], "P_true": e["P"],
                "T0_true_gaia": e["T0g"], "dur_true": e["dur"], "eph_sigma_d": sig,
                "eph_testable": testable, "match_factor": "" if f is None else f,
                "ratio_Pg_Pt": Pg / e["P"]})
    if testable:
        S_t = window_set(t, e["T0g"], e["P"], e["dur"] / 2.0)
        both = sorted(set(S_t) & set(S_g))
        rec["n_t"], rec["n_both"] = len(S_t), len(both)
        rec["coverage"] = len(both) / len(S_t) if S_t else float("nan")
        rec["purity"] = len(both) / len(S_g) if S_g else float("nan")
        rec["chance_purity"] = len(S_t) / len(t)
        rec["depth_t"], rec["snr_t"] = set_depth_snr(fn, S_t, sd)
        rec["why_label"] = classify_why(True, len(S_t), len(S_g), len(both))
    else:
        rec["why_label"] = "UNTESTABLE"
    rec["status"] = "OK"
    return rec


# ================================================================ grading (stdlib)
def _num(x):
    return fval({"v": x}, "v")


def grade(recs):
    ok = [r for r in recs if r.get("status") == "OK"]
    # T1 controls
    ctrl = [r for r in ok if r["category"] == "KNOWN_PLANET" and r.get("eph_testable") is True
            and _num(r.get("match_factor")) in CONTROL_FACTORS
            and int(r.get("n_t") or 0) >= MIN_NT and int(r.get("n_g") or 0) >= MIN_NG]
    k1 = sum(1 for r in ctrl if _num(r.get("purity")) >= PURITY_ALIAS)
    if len(ctrl) < T1_MIN_N:
        t1 = "UNTESTABLE"
    else:
        t1 = "TIME_OK" if k1 / len(ctrl) >= T1_MIN_SHARE else "TIME_BAD"
    # WHY
    wrong = [r for r in ok if r["category"] == "KNOWN_SYSTEM_OTHER_P"]
    test = [r for r in wrong if r.get("why_label") in ("ALIAS", "PARTIAL", "UNRELATED")]
    na = sum(1 for r in test if r["why_label"] == "ALIAS")
    npart = sum(1 for r in test if r["why_label"] == "PARTIAL")
    nunr = sum(1 for r in test if r["why_label"] == "UNRELATED")
    p, lo, hi = wilson(na, len(test))
    if len(test) < WHY_MIN_N:
        why = "UNTESTABLE"
    elif lo > 0.5:
        why = "ALIAS_DOMINATED"
    elif hi < 0.5:
        why = "SPURIOUS_DOMINATED"
    else:
        why = "MIXED"
    seen = {lab: sum(1 for r in test if r["why_label"] == lab and _num(r.get("snr_t")) >= SEEN_SNR)
            for lab in ("ALIAS", "PARTIAL", "UNRELATED")}
    # T3
    right = [_num(r.get("n_comp")) for r in ok if r["category"] == "KNOWN_PLANET"]
    wr = [_num(r.get("n_comp")) for r in wrong]
    right = [x for x in right if math.isfinite(x)]
    wr = [x for x in wr if math.isfinite(x)]
    auc, pval = mann_whitney_low(right, wr)
    if len(right) < T3_MIN_RIGHT or len(wr) < T3_MIN_RIGHT:
        t3 = "UNTESTABLE"
    elif auc >= T3_AUC_HI and pval <= T3_P:
        t3 = "PREDICTIVE"
    elif auc < T3_AUC_LO:
        t3 = "NOT_PREDICTIVE"
    else:
        t3 = "WEAK"
    # exploratory AUCs (not graded)
    expl = {}
    for key in ("frac_above", "snr_g_free", "num_in_transit", "snr_g_fixed"):
        a = [_num(r.get(key)) for r in ok if r["category"] == "KNOWN_PLANET"]
        b = [_num(r.get(key)) for r in wrong]
        a = [x for x in a if math.isfinite(x)]
        b = [x for x in b if math.isfinite(x)]
        au, pv = mann_whitney_low(a, b)
        expl[key] = {"auc_right_lower": au, "p_one_sided": pv, "n_right": len(a), "n_wrong": len(b)}
    tb = [r for r in wrong if r.get("true_beats_gaia") in (True, False)]
    within = [_num(r.get("gaia_within_frac")) for r in ok]
    within = [x for x in within if math.isfinite(x)]
    return {
        "T1": {"n_controls": len(ctrl), "k_pure": k1, "label": t1,
               "share": k1 / len(ctrl) if ctrl else float("nan")},
        "WHY": {"n_wrong_ok": len(wrong), "n_testable": len(test), "alias": na,
                "partial": npart, "unrelated": nunr, "alias_share": p, "lo": lo, "hi": hi,
                "label": why if t1 != "TIME_BAD" else "INVALID", "raw_label": why,
                "real_transit_seen_snr3": seen},
        "T3": {"n_right": len(right), "n_wrong": len(wr), "auc_right_lower": auc,
               "p_one_sided": pval, "label": t3},
        "exploratory_auc": expl,
        "true_beats_gaia": {"n": len(tb), "true_higher": sum(1 for r in tb
                                                              if r["true_beats_gaia"] is True)},
        "gaia_within_frac_median": median(within) if within else float("nan"),
        "n_ok": len(ok), "n_total": len(recs),
        "status_counts": {s: sum(1 for r in recs if r.get("status") == s)
                          for s in sorted(set(r.get("status", "") for r in recs))},
    }


# ================================================================ numpy periodogram
def freq_grid(baseline, box, pmin=PERIOD_MIN, pmax=PERIOD_MAX, factor=GRID_FACTOR,
              max_freqs=MAX_FREQS):
    import numpy as np
    dlnf = box / (factor * max(baseline, 1.0))
    n = int(math.ceil(math.log(pmax / pmin) / dlnf)) + 1
    coarse = n > max_freqs
    n = min(n, max_freqs)
    return np.exp(np.linspace(math.log(1.0 / pmax), math.log(1.0 / pmin), n)), coarse


def box_snr(t, fn, freqs, box, nin_min=NIN_MIN):
    """Phase-free box search: for each frequency the best S/N of a dip of width `box` (d)
    containing >= nin_min epochs. fn = normalised flux. Returns array like freqs."""
    import numpy as np
    t = np.asarray(t, float)
    y = 1.0 - np.asarray(fn, float)
    n = t.size
    med = np.median(y)
    sd = 1.4826 * np.median(np.abs(y - med))
    freqs = np.atleast_1d(np.asarray(freqs, float))
    out = np.full(freqs.size, -np.inf)
    if n < nin_min + 3 or not (sd > 0):
        return out
    ytot = y.sum()
    chunk = max(50, int(300000 // max(n, 1)))
    ii = np.arange(n)[None, :]
    for s in range(0, freqs.size, chunk):
        fr = freqs[s:s + chunk]
        m = fr.size
        ph = np.mod(np.outer(fr, t), 1.0)
        order = np.argsort(ph, axis=1)
        phs = np.take_along_axis(ph, order, axis=1)
        ys = y[order]
        ph2 = np.concatenate([phs, phs + 1.0], axis=1)
        y2 = np.concatenate([ys, ys], axis=1)
        cs = np.concatenate([np.zeros((m, 1)), np.cumsum(y2, axis=1)], axis=1)
        w = np.minimum(box * fr, 0.5)[:, None]
        offs = (np.arange(m) * 4.0)[:, None]
        flat = (ph2 + offs).ravel()
        ends = (phs + offs + w).ravel()
        j = np.searchsorted(flat, ends, side="left").reshape(m, n) - (np.arange(m) * 2 * n)[:, None]
        j = np.clip(j, 0, 2 * n)
        cnt = j - ii
        sin = np.take_along_axis(cs, j, axis=1) - np.take_along_axis(cs, np.broadcast_to(ii, (m, n)), axis=1)
        nout = n - cnt
        valid = (cnt >= nin_min) & (nout >= 3)
        cntf = np.where(valid, cnt, 1).astype(float)
        noutf = np.where(valid, nout, 1).astype(float)
        depth = sin / cntf - (ytot - sin) / noutf
        snr = depth / (sd * np.sqrt(1.0 / cntf + 1.0 / noutf))
        snr = np.where(valid, snr, -np.inf)
        out[s:s + m] = snr.max(axis=1)
    return out


def count_competitors(freqs, snr, f0, snr0, frac=COMP_FRAC, gap=CLUSTER_GAP):
    """Separate peaks (clusters of grid points with snr >= frac*snr0) other than the cluster
    at f0; and the fraction of grid points with snr >= snr0."""
    import numpy as np
    if not (math.isfinite(snr0) and snr0 > 0):
        return float("nan"), float("nan")
    above = np.nonzero(snr >= frac * snr0)[0]
    frac_above = float(np.mean(snr >= snr0))
    if above.size == 0:
        return 0, frac_above
    i0 = int(np.argmin(np.abs(freqs - f0)))
    splits = np.nonzero(np.diff(above) > gap)[0]
    starts = np.concatenate([[above[0]], above[splits + 1]])
    ends = np.concatenate([above[splits], [above[-1]]])
    n = 0
    for a, b in zip(starts, ends):
        if a - gap <= i0 <= b + gap:
            continue
        n += 1
    return n, frac_above


def periodogram_fields(rec, t, fl):
    import numpy as np
    if rec.get("status") not in ("OK", "NO_EPHEMERIS"):
        return rec
    tt = np.asarray(t, float)
    fn = np.asarray(fl, float) / np.median(fl)
    dg = rec["dur_gaia"]
    box = clip(dg if math.isfinite(dg) else 0.1, BOX_MIN, BOX_MAX)
    freqs, coarse = freq_grid(tt[-1] - tt[0], box)
    snr = box_snr(tt, fn, freqs, box)
    fg = 1.0 / rec["P_gaia"]
    sg = float(box_snr(tt, fn, [fg], box)[0])
    ib = int(np.argmax(snr))
    ncomp, fa = count_competitors(freqs, snr, fg, sg)
    rec.update({"box_d": box, "n_freq": int(freqs.size), "grid_coarsened": bool(coarse),
                "snr_g_free": sg, "P_best": float(1.0 / freqs[ib]), "snr_best": float(snr[ib]),
                "n_comp": ncomp, "frac_above": fa})
    Pt = _num(rec.get("P_true"))
    if math.isfinite(Pt) and Pt > 0:
        dt = _num(rec.get("dur_true"))
        box_t = clip(dt if math.isfinite(dt) else box, BOX_MIN, BOX_MAX)
        st = float(box_snr(tt, fn, [1.0 / Pt], box_t)[0])
        sg_same = float(box_snr(tt, fn, [fg], box_t)[0])
        rec["snr_true_free"] = st
        if math.isfinite(st) and math.isfinite(sg_same):
            rec["true_beats_gaia"] = bool(st >= sg_same)
    return rec


# ================================================================ network
def http_get(url, timeout=HTTP_TIMEOUT, tries=3, data=None):
    import urllib.request
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA},
                                         method="POST" if data is not None else "GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:
            last = exc
            log("HTTP retry", url[:90], a + 1, repr(exc)[:160])
            time.sleep(10 * (a + 1))
    raise RuntimeError("HTTP failed %s: %r" % (url[:90], last))


_DL_ORDER = list(DATALINK_STRUCTURES)


def datalink_fetch(ids, timeout=120):
    import urllib.parse
    got, used = {}, ""
    for structure in list(_DL_ORDER):
        body = urllib.parse.urlencode({
            "RETRIEVAL_TYPE": "EPOCH_PHOTOMETRY", "ID": ",".join(str(i) for i in ids),
            "RELEASE": "Gaia DR3", "FORMAT": "csv", "DATA_STRUCTURE": structure,
            "VALID_DATA": "false", "USE_ZIP_ALWAYS": "true"}).encode()
        try:
            data = http_get(DATALINK_URL, timeout=timeout, tries=2, data=body)
        except Exception as exc:
            log("DataLink", structure, "failed:", repr(exc)[:200])
            continue
        try:
            got = parse_datalink_payload(data)
        except Exception as exc:
            log("DataLink", structure, "unparseable:", repr(exc)[:200], data[:200])
            got = {}
        log("DataLink", structure, "bytes", len(data), "sources", len(got))
        if got:
            used = structure
            _DL_ORDER.remove(structure)
            _DL_ORDER.insert(0, structure)
            break
    return got, used


class _Counter(io.RawIOBase):
    def __init__(self, f):
        self.f, self.n = f, 0

    def readable(self):
        return True

    def readinto(self, b):
        chunk = self.f.read(len(b))
        if not chunk:
            return 0
        b[:len(chunk)] = chunk
        self.n += len(chunk)
        return len(chunk)


def cdn_fetch(sids, max_bytes, timeout=HTTP_TIMEOUT, max_seconds=7200, cache_dir=None):
    """Stream ESA's bulk epoch-photometry files and keep only the wanted sources (each found
    source is saved to cache_dir at once, so a later run resumes)."""
    import urllib.request
    out, total, log_rows = {}, 0, []
    t_start = time.time()
    index = cdn_index(http_get(CDN_BASE + "_MD5SUM.txt").decode("utf-8", "replace"))
    log("CDN index files", len(index))
    groups = {}
    for s in sids:
        name = cdn_file_for(s, index)
        if name:
            groups.setdefault(name, set()).add(str(s))
    for name in sorted(groups):
        want = groups[name]
        if total >= max_bytes or time.time() - t_start > max_seconds:
            log_rows.append({"file": name, "skipped": "byte or time cap"})
            continue
        maxid = max(int(x) for x in want)
        try:
            req = urllib.request.Request(CDN_BASE + name, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                cnt = _Counter(resp)
                gz = gzip.GzipFile(fileobj=io.BufferedReader(cnt))
                txt = io.TextIOWrapper(gz, encoding="utf-8", errors="replace")
                header, idx, last, mono, found = None, None, -1, True, 0
                for line in txt:
                    if line.startswith("#") or not line.strip():
                        continue
                    if header is None:
                        header = [h.strip().strip('"').lower()
                                  for h in next(csv.reader([line]))]
                        idx = header.index("source_id")
                        continue
                    parts = line.split(",", idx + 1)
                    try:
                        sid = int(parts[idx].strip().strip('"'))
                    except (ValueError, IndexError):
                        continue
                    mono = mono and sid >= last
                    last = sid
                    if str(sid) in want:
                        txt1 = ",".join(header) + "\n" + line
                        for k, v in parse_epoch_text(txt1).items():
                            out[k] = v
                            if cache_dir and v["t"]:
                                save_epochs(os.path.join(cache_dir, k + ".csv"), v)
                        found += 1
                        if found == len(want):
                            break
                    elif mono and sid > maxid:
                        break
                total += cnt.n
                log_rows.append({"file": name, "wanted": len(want), "found": found,
                                 "bytes": cnt.n})
                log("CDN", name, "found", found, "of", len(want), "MB", round(cnt.n / 1e6, 1))
        except Exception as exc:
            log_rows.append({"file": name, "error": repr(exc)[:200]})
            log("CDN", name, "error", repr(exc)[:200])
    return out, log_rows


# ================================================================ io
def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, keys):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})


def clean_json(o):
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): clean_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_json(v) for v in o]
    return o


def load_targets(inputs):
    targets = []
    for c in ("c0", "c1"):
        cand = {r["source_id"]: r for r in read_csv(os.path.join(inputs, c + "_candidates.csv"))}
        for s in read_csv(os.path.join(inputs, c + "_stars.csv")):
            sid = s["source_id"]
            cr = cand.get(sid, {})
            nin = fval(cr, "num_in_transit")
            targets.append({
                "source_id": sid, "chunk": c, "category": s.get("category", ""),
                "category_detail": s.get("category_detail", ""), "tic": norm_tic(s.get("tic", "")),
                "G": fval(s, "G"), "P_gaia": fval(cr, "transit_period"),
                "T0_gaia": fval(cr, "transit_reference_time"),
                "dur_gaia": fval(cr, "transit_duration"),
                "num_in_transit": int(nin) if math.isfinite(nin) else 0})
    return targets


def save_epochs(path, rec):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["time", "flux", "flux_error", "rejected"])
        for t, f, e, r in zip(rec["t"], rec["flux"], rec["ferr"], rec["rej"]):
            w.writerow(["%.7f" % t if math.isfinite(t) else "", "%.7g" % f if math.isfinite(f) else "",
                        "%.5g" % e if math.isfinite(e) else "", int(bool(r))])


def load_epochs(path):
    rec = _empty()
    for r in read_csv(path):
        rec["t"].append(fval(r, "time"))
        rec["flux"].append(fval(r, "flux"))
        rec["ferr"].append(fval(r, "flux_error"))
        rec["rej"].append(truthy(r.get("rejected", "")))
    return rec


# ================================================================ self-test (numpy)
def self_test():
    import numpy as np
    for seed in range(1, 20):
        rng = np.random.default_rng(seed)
        visits = np.sort(rng.uniform(0, 1000, 40))
        t = np.sort(np.concatenate([visits, visits + 0.0739]))
        P, T0, dur, dep = 2.0, 10.0, 0.2, 0.01
        x = (t - T0) / P
        intr = np.abs((x - np.round(x)) * P) <= dur / 2
        if intr.sum() >= 4:
            break
    f = 1.0 + rng.normal(0, 0.001, t.size)
    f[intr] -= dep
    fl = list(f * 1e5)
    tl = list(t)
    ok = True
    tgt = {"source_id": "1", "category": "KNOWN_PLANET", "category_detail": "", "tic": "1",
           "G": 12.0, "P_gaia": P, "T0_gaia": T0, "dur_gaia": dur,
           "num_in_transit": int(intr.sum())}
    eph = _mk_eph("X b", "archive", P, 1e-6, T0 + GAIA_T_OFFSET, 1e-4, dur * 24)
    rec = analyse_epochs(tgt, tl, fl, [eph])
    if not (rec["status"] == "OK" and rec["why_label"] == "ALIAS" and rec["purity"] == 1.0):
        log("SELFTEST fail: control purity", rec["why_label"], rec.get("purity"))
        ok = False
    tgt2 = dict(tgt, category="KNOWN_SYSTEM_OTHER_P", P_gaia=5.1234567, T0_gaia=13.3)
    rec2 = analyse_epochs(tgt2, tl, fl, [eph])
    if not (rec2["status"] == "OK" and _num(rec2["purity"]) < 0.5):
        log("SELFTEST fail: random period purity", rec2.get("purity"))
        ok = False
    rec = periodogram_fields(rec, tl, fl)
    sc = float(box_snr(t, f, [1.0 / (P * 0.8541)], dur)[0])
    if not (rec["snr_g_free"] > 8 and rec["snr_g_free"] > sc):
        log("SELFTEST fail: periodogram", rec["snr_g_free"], sc)
        ok = False
    # brute-force check of box_snr at one frequency
    fr = 1.0 / P
    ph = np.mod(t * fr, 1.0)
    y = 1.0 - f
    sd = 1.4826 * np.median(np.abs(y - np.median(y)))
    best = -np.inf
    for p0 in ph:
        d = np.mod(ph - p0, 1.0)
        m = d < dur * fr
        if m.sum() >= NIN_MIN and (~m).sum() >= 3:
            s = (y[m].mean() - y[~m].mean()) / (sd * np.sqrt(1 / m.sum() + 1 / (~m).sum()))
            best = max(best, s)
    fast = float(box_snr(t, f, [fr], dur)[0])
    if not abs(best - fast) < 1e-6 * max(1.0, abs(best)):
        log("SELFTEST fail: box_snr vs brute force", fast, best)
        ok = False
    log("self-test", "OK" if ok else "FAILED", "snr", round(rec["snr_g_free"], 2),
        "n_comp", rec["n_comp"], "nfreq", rec["n_freq"])
    return ok


# ================================================================ main
def run(args):
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.cache_dir, exist_ok=True)
    meta = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        targets = load_targets(args.inputs)
    except Exception as exc:
        json.dump({"error": "inputs: %r" % exc}, open(os.path.join(args.out_dir,
                  "vpt_epochs_summary.json"), "w"))
        return 4
    if args.limit:
        targets = targets[:args.limit]
    log("targets", len(targets))
    # catalogues
    try:
        arch = parse_exoarch_eph(http_get(EXOARCH_URL).decode("utf-8", "replace"))
    except Exception as exc:
        log("archive failed", exc)
        arch = {}
    try:
        toi = parse_toi_eph(http_get(TOI_URL).decode("utf-8", "replace"))
    except Exception as exc:
        log("TOI failed", exc)
        toi = {}
    if not arch:
        json.dump({"error": "planet archive unavailable"},
                  open(os.path.join(args.out_dir, "vpt_epochs_summary.json"), "w"))
        return 2
    ephs = merge_ephs(arch, toi)
    meta.update({"archive_tics": len(arch), "toi_tics": len(toi)})
    # epochs
    epochs, source = {}, {}
    for tg in targets:
        p = os.path.join(args.cache_dir, tg["source_id"] + ".csv")
        if os.path.exists(p):
            epochs[tg["source_id"]] = load_epochs(p)
            source[tg["source_id"]] = "cache"
    missing = [tg["source_id"] for tg in targets if tg["source_id"] not in epochs]
    log("cached", len(epochs), "missing", len(missing))
    used = set()
    fails = 0
    for i in range(0, len(missing), args.batch):
        if fails >= 2:
            log("DataLink gave nothing twice in a row; going to the CDN")
            break
        ids = missing[i:i + args.batch]
        got, st = datalink_fetch(ids)
        if st:
            used.add(st)
            fails = 0
        else:
            fails += 1
        for sid, rec in got.items():
            if sid in ids and rec["t"]:
                epochs[sid] = rec
                source[sid] = "datalink"
                save_epochs(os.path.join(args.cache_dir, sid + ".csv"), rec)
    missing = [tg["source_id"] for tg in targets if tg["source_id"] not in epochs]
    cdn_log = []
    if missing and not args.no_cdn:
        log("CDN fallback for", len(missing))
        try:
            got, cdn_log = cdn_fetch(missing, int(args.cdn_max_gb * 1e9),
                                     max_seconds=60 * args.cdn_max_minutes,
                                     cache_dir=args.cache_dir)
        except Exception as exc:
            log("CDN failed", repr(exc)[:200])
            got = {}
        for sid, rec in got.items():
            if rec["t"]:
                epochs[sid] = rec
                source[sid] = "cdn"
                save_epochs(os.path.join(args.cache_dir, sid + ".csv"), rec)
    meta.update({"datalink_structures": sorted(used), "cdn_log": cdn_log,
                 "epochs_from": {s: sum(1 for v in source.values() if v == s)
                                 for s in ("cache", "datalink", "cdn")}})
    have = sum(1 for tg in targets if tg["source_id"] in epochs)
    log("epochs for", have, "of", len(targets))
    # raw epochs to /out (two halves)
    sids = sorted(epochs, key=int)
    half = (len(sids) + 1) // 2
    for part, chunk in ((1, sids[:half]), (2, sids[half:])):
        with open(os.path.join(args.out_dir, "epochs_g_%d.csv" % part), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["source_id", "time", "flux", "flux_error", "rejected"])
            for sid in chunk:
                r = epochs[sid]
                for t, f, e, rj in zip(r["t"], r["flux"], r["ferr"], r["rej"]):
                    w.writerow([sid, "%.7f" % t if math.isfinite(t) else "",
                                "%.7g" % f if math.isfinite(f) else "",
                                "%.5g" % e if math.isfinite(e) else "", int(bool(rj))])
    if have < 0.5 * len(targets):
        json.dump(clean_json({"error": "epoch photometry unavailable", "have": have,
                              "meta": meta}),
                  open(os.path.join(args.out_dir, "vpt_epochs_summary.json"), "w"), indent=1)
        return 2
    recs = []
    for n, tg in enumerate(targets):
        sid = tg["source_id"]
        try:
            if sid not in epochs:
                r = {k: "" for k in STAR_KEYS}
                r.update({k: tg.get(k, "") for k in ("source_id", "category", "category_detail",
                                                     "tic", "G")})
                r["status"] = "NO_EPOCHS"
                recs.append(r)
                continue
            t, fl, _, nrej = clean_epochs(epochs[sid])
            r = analyse_epochs(tg, t, fl, ephs.get(tg["tic"], []))
            r["n_rejected"] = nrej
            r = periodogram_fields(r, t, fl)
        except Exception as exc:
            traceback.print_exc()
            r = {k: "" for k in STAR_KEYS}
            r.update({"source_id": sid, "category": tg.get("category", ""), "status": "ERROR",
                      "error": repr(exc)[:300]})
        recs.append(r)
        log("[%d/%d]" % (n + 1, len(targets)), sid, r.get("category"), r.get("status"),
            r.get("why_label"), "ncomp", r.get("n_comp"))
        if (n + 1) % 20 == 0:
            write_csv(os.path.join(args.out_dir, "vpt_epochs_stars.csv"), recs, STAR_KEYS)
    write_csv(os.path.join(args.out_dir, "vpt_epochs_stars.csv"), recs, STAR_KEYS)
    g = grade(recs)
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    summary = {"grades": g, "meta": meta}
    with open(os.path.join(args.out_dir, "vpt_epochs_summary.json"), "w") as fh:
        json.dump(clean_json(summary), fh, indent=1)
    print(json.dumps(clean_json({"T1": g["T1"]["label"], "WHY": g["WHY"]["label"],
                                 "alias": g["WHY"]["alias"], "testable": g["WHY"]["n_testable"],
                                 "T3": g["T3"]["label"], "auc": g["T3"]["auc_right_lower"]})))
    try:
        import shutil
        shutil.copy(os.path.abspath(__file__), os.path.join(args.out_dir, "vpt_epochs.py"))
    except Exception:
        pass
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--inputs", default="inputs")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-cdn", action="store_true")
    ap.add_argument("--cdn-max-gb", type=float, default=40.0)
    ap.add_argument("--cdn-max-minutes", type=float, default=120.0)
    a = ap.parse_args(argv)
    if a.self_test:
        return 0 if self_test() else 3
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
