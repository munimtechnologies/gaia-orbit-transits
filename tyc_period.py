#!/usr/bin/env python3
# tyc_period.py 0.1.0 -- which period does TYC 6340-23-1 (TIC 71945261) really have, is its
# eclipse seen by ASAS-SN (2013-2025), is it on the target rather than the 38 arcsec neighbour,
# and was the SuperWASP 2006-2008 dip found by wasp_tyc 0.1.0 a field-wide systematic?
# By MV2 of Munim, Inc.; made with AI agents working in his name. License: Apache-2.0.
# Rules: findings/2026-11-20-tyc6340-period-prereg.md (written before this job ran).
# Pure standard library (no numpy). ASAS-SN data are fetched separately by fetch_asassn.py.
"""Usage:
  python tyc_period.py --self-test
  python tyc_period.py --data-dir /data/wasp-tyc6340 --asassn-dir /data/asassn-tyc6340 --out-dir /out
Exit codes: 0 ok (labels in tyc_period_summary.json); 3 self-test failed.
"""
import argparse
import csv
import io
import json
import math
import os
import random
import sys
import time
import urllib.parse
import urllib.request

VERSION = "0.1.0"

# ---- fixed inputs (pre-registered) ----
P_GAIA = 2.3289298
SIG_P_GAIA = 0.00014
T_TESS = 2460803.0299          # TESS S92 primary eclipse, BJD_TDB
SIG_T_TESS = 0.001
T14 = 0.0990
T23 = 0.0324
# wasp_tyc 0.1.0 (job tyc6340-wasp-v1) ephemerides
P_W1 = 2.3297429999999992      # fine fit
T_W1 = 2453944.807328705
P_C1 = 2.3297769999999995      # coarse fit (v1 detrended the target at this ephemeris)
T_C1 = 2454003.053903705
SIG_P_W1 = 1e-4                # conservative (v1 bootstrap was unreliable)
SIG_T_W1 = 0.005               # conservative
V1_TARGET_DEPTH = 0.0742719455360089
V1_N38_DEPTH = 0.06377234282656619
REPRO_TOL = 0.002
CANDIDATES = {"wasp_to_tess_N2943": 2.330350856709057,
              "wasp_to_tess_N2944": 2.3295592973147943,
              "wasp_to_tess_N2945": 2.3287682754820898,
              "gaia": P_GAIA, "wasp_local": P_W1}

UTC_TO_TDB_WASP = 65.184 / 86400.0
UTC_TO_TDB_ASASSN = 69.184 / 86400.0

NBIN = 1000
BOX_W = 0.06
N_CONTROL = 300
N_BOOT = 150
SEED = 20261121
ERR_FLOOR = 0.005
MAX_ERR = 0.1
SNR_BOX_MIN = 7.0
SNR_FIT_MIN = 5.0
MIN_ECL_NIGHTS = 5
INJ_P = 2.6
INJ_DEPTH = 0.03
INJ_T0 = 2458000.3
Z_MATCH = 3.0
BLEND_Z = 3.0
EDGE_MAX = 0.2

A_P_LO, A_P_HI, A_P_STEP = 2.3260, 2.3320, 2e-6
W_P_LO, W_P_HI, W_P_STEP = 2.3200, 2.3400, 5e-6

WASP_BASE = "https://wasp.cerit-sc.cz"
UA = "MV2-Munim-research/0.1 (mv2@munimtech.com)"
WASP_TARGET = "1SWASP J202214.65-220425.1"
WASP_N38 = "1SWASP J202215.96-220458.7"
# all SuperWASP DR1 stars 4.7-7.1 arcmin away with V < 13 and > 8000 points (archive search,
# 20 Nov 2026, 50 nearest within 20 arcmin), i.e. outside the target's photometric aperture.
WASP_COMPS = ["1SWASP J202225.43-220021.0", "1SWASP J202227.26-215958.9",
              "1SWASP J202154.71-220127.7", "1SWASP J202226.81-215939.2",
              "1SWASP J202224.40-215920.3", "1SWASP J202154.46-220110.6",
              "1SWASP J202222.71-220952.0", "1SWASP J202150.34-220132.3",
              "1SWASP J202149.39-220650.1", "1SWASP J202225.33-215811.9",
              "1SWASP J202150.36-220042.7", "1SWASP J202147.79-220743.2"]
COMP_MIN_POINTS = 500
COMP_MIN_USABLE = 6
DIP_DEPTH = 0.02
DIP_Z = 3.0

_HALF14 = 0.5 * T14
_HALF23 = 0.5 * T23
_RAMP = _HALF14 - _HALF23


# ---------------------------------------------------------------- helpers
def median(v):
    s = sorted(v)
    n = len(s)
    if n == 0:
        return float("nan")
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def std(v):
    v = [x for x in v if math.isfinite(x)]
    n = len(v)
    if n < 2:
        return float("nan")
    m = sum(v) / n
    return math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))


def fold_dt(t, t0, p):
    return ((t - t0 + 0.5 * p) % p) - 0.5 * p


def shape(dt):
    a = abs(dt)
    if a <= _HALF23:
        return 1.0
    if a >= _HALF14:
        return 0.0
    return (_HALF14 - a) / _RAMP


RA_DEG, DEC_DEG = 305.561052, -22.073651
AU_DAYS = 0.0057755183     # light travel time for 1 au, days


def helio_corr_days(jd, ra_deg=RA_DEG, dec_deg=DEC_DEG):
    """HJD - JD (days) from a low-precision Sun position (error << 1 s for this purpose)."""
    n = jd - 2451545.0
    L = (280.460 + 0.9856474 * n) % 360.0
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)
    lam = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    R = 1.00014 - 0.01671 * math.cos(g) - 0.00014 * math.cos(2 * g)
    eps = math.radians(23.439 - 0.0000004 * n)
    x = R * math.cos(lam)
    y = R * math.cos(eps) * math.sin(lam)
    z = R * math.sin(eps) * math.sin(lam)
    a = math.radians(ra_deg)
    d = math.radians(dec_deg)
    sx, sy, sz = math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d)
    return -(x * sx + y * sy + z * sz) * AU_DAYS


def assign_seasons(t, gap=60.0):
    order = sorted(range(len(t)), key=lambda i: t[i])
    season = [0] * len(t)
    s = 0
    prev = None
    for i in order:
        if prev is not None and t[i] - prev > gap:
            s += 1
        season[i] = s
        prev = t[i]
    return season


# ---------------------------------------------------------------- parsing
def parse_wasp_csv(text):
    """SuperWASP DR1 CSV -> rows (BJD_TDB approx, camera, mag, err)."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        parts = line.split(",")
        if len(parts) < 4:
            continue
        try:
            t = float(parts[0])
            m = float(parts[2])
            e = float(parts[3])
        except ValueError:
            continue
        if math.isfinite(t) and math.isfinite(m) and math.isfinite(e):
            rows.append((t + UTC_TO_TDB_WASP, parts[1].strip(), m, e))
    return rows


def _pick(cols, names):
    low = {c.lower(): c for c in cols}
    for n in names:
        if n in low:
            return low[n]
    return None


def parse_asassn_csv(text):
    """ASAS-SN Sky Patrol CSV -> (rows (BJD_TDB approx, group, mag, err), info)."""
    rd = csv.DictReader(io.StringIO(text))
    cols = rd.fieldnames or []
    c_t = _pick(cols, ["jd", "hjd", "bjd"])
    c_m = _pick(cols, ["mag"])
    c_e = _pick(cols, ["mag_err", "magerr", "mag_error"])
    c_q = _pick(cols, ["quality"])
    c_c = _pick(cols, ["camera", "cam"])
    c_f = _pick(cols, ["phot_filter", "filter", "band"])
    info = {"columns": cols, "time_col": c_t, "n_raw": 0, "n_bad_quality": 0,
            "time_fix": None}
    if not (c_t and c_m and c_e):
        info["error"] = "missing time/mag/err column"
        return [], info
    raw = []
    for r in rd:
        info["n_raw"] += 1
        if c_q and str(r.get(c_q, "")).strip() not in ("G", "g", ""):
            info["n_bad_quality"] += 1
            continue
        try:
            t = float(r[c_t])
            m = float(r[c_m])
            e = float(r[c_e])
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(t) and math.isfinite(m) and math.isfinite(e)) or m > 50:
            continue
        grp = "%s|%s" % (r.get(c_c, "") if c_c else "", r.get(c_f, "") if c_f else "")
        raw.append((t, grp, m, e))
    if not raw:
        return [], info
    tm = median([x[0] for x in raw])
    add = 0.0
    if 2440000 < tm < 2480000:
        add = 0.0
    elif 40000 < tm < 80000:
        add = 2400000.5
        info["time_fix"] = "MJD+2400000.5"
    elif 0 < tm < 20000:
        add = 2450000.0
        info["time_fix"] = "+2450000"
    else:
        info["error"] = "unrecognised time scale (median %.3f)" % tm
        return [], info
    rows = [(x[0] + add + UTC_TO_TDB_ASASSN, x[1], x[2], x[3]) for x in raw]
    return rows, info


# ---------------------------------------------------------------- light curves
def build_lc(rows):
    """rows: (t_bjd, group, mag, err). Clean per (group, season); weights rescaled later."""
    rows = [x for x in rows if 0.0 < x[3] <= MAX_ERR]
    t = [x[0] for x in rows]
    season = assign_seasons(t)
    groups = {}
    for i, x in enumerate(rows):
        groups.setdefault((x[1], season[i]), []).append(i)
    keep = [False] * len(rows)
    r0 = [0.0] * len(rows)
    for idx in groups.values():
        if len(idx) < 20:
            continue
        med = median([rows[i][2] for i in idx])
        res = [rows[i][2] - med for i in idx]
        s = 1.4826 * median([abs(v) for v in res])
        if not s > 0:
            s = 0.01
        hi = max(10.0 * s, 0.3)
        for i, v in zip(idx, res):
            r0[i] = v
            keep[i] = (-5.0 * s <= v <= hi)
    lc = {"t": [], "r0": [], "w": [], "cam": [], "night": [], "season": [], "n_in": len(rows)}
    for i, x in enumerate(rows):
        if keep[i]:
            lc["t"].append(t[i])
            lc["r0"].append(r0[i])
            lc["w"].append(1.0 / max(x[3], ERR_FLOOR) ** 2)
            lc["cam"].append(x[1])
            lc["night"].append(int(math.floor(t[i])))
            lc["season"].append(season[i])
    lc["r"] = list(lc["r0"])
    set_weights(lc)
    return lc


def set_weights(lc, p=None, t0=None):
    num = 0.0
    n = 0
    for i in range(len(lc["t"])):
        if p is not None and abs(fold_dt(lc["t"][i], t0, p)) < 0.1:
            continue
        num += lc["w"][i] * lc["r"][i] ** 2
        n += 1
    chi2 = num / max(n - 1, 1)
    if not chi2 > 0:
        chi2 = 1.0
    lc["chi2_red"] = chi2
    lc["we"] = [wi / chi2 for wi in lc["w"]]


def detrend_eph(lc, p, t0, win=0.1, min_out=10):
    """wasp_tyc 0.1.0 detrend: per (camera, night) median of points outside +-win of eclipse."""
    groups = {}
    for i in range(len(lc["t"])):
        groups.setdefault((lc["cam"][i], lc["night"][i]), []).append(i)
    r = list(lc["r0"])
    for idx in groups.values():
        out = [lc["r0"][i] for i in idx if abs(fold_dt(lc["t"][i], t0, p)) > win]
        if len(out) >= min_out:
            m = median(out)
            for i in idx:
                r[i] = lc["r0"][i] - m
    lc["r"] = r
    set_weights(lc, p, t0)


def detrend_free(lc, min_n=10):
    """Ephemeris-free detrend: subtract each (camera, night) median of all its points."""
    groups = {}
    for i in range(len(lc["t"])):
        groups.setdefault((lc["cam"][i], lc["night"][i]), []).append(i)
    r = list(lc["r0"])
    for idx in groups.values():
        if len(idx) >= min_n:
            m = median([lc["r0"][i] for i in idx])
            for i in idx:
                r[i] = lc["r0"][i] - m
    lc["r"] = r
    set_weights(lc)


def inject(lc, depth, p, t0):
    new = dict(lc)
    add = [depth * shape(fold_dt(t, t0, p)) for t in lc["t"]]
    new["r0"] = [a + b for a, b in zip(lc["r0"], add)]
    new["r"] = [a + b for a, b in zip(lc["r"], add)]
    return new


# ---------------------------------------------------------------- search and fits
def box_scan(lc, period, tref, nbin=NBIN, box_w=BOX_W):
    sw = [0.0] * nbin
    swr = [0.0] * nbin
    t, r, w = lc["t"], lc["r"], lc["we"]
    for i in range(len(t)):
        b = int((((t[i] - tref) / period) % 1.0) * nbin)
        if b >= nbin:
            b = nbin - 1
        sw[b] += w[i]
        swr[b] += w[i] * r[i]
    W = sum(sw)
    S = sum(swr)
    nb = max(1, int(round(box_w / period * nbin)))
    sw2 = sw + sw[:nb]
    swr2 = swr + swr[:nb]
    win_w = sum(sw2[:nb])
    win_s = sum(swr2[:nb])
    best = (-1e30, 0, 0.0, 0.0)
    for start in range(nbin):
        if start > 0:
            win_w += sw2[start + nb - 1] - sw2[start - 1]
            win_s += swr2[start + nb - 1] - swr2[start - 1]
        wo = W - win_w
        if win_w <= 1e-12 or wo <= 1e-12:
            continue
        d = win_s / win_w - (S - win_s) / wo
        sig = math.sqrt(1.0 / win_w + 1.0 / wo)
        if d / sig > best[0]:
            best = (d / sig, start, d, sig)
    snr, start, d, sig = best
    phase = ((start + 0.5 * nb) / nbin) % 1.0
    return {"snr": snr, "depth": d, "sigma": sig, "phase": phase, "period": period}


def scan(lc, tref, p_lo, p_hi, step):
    n = int(round((p_hi - p_lo) / step)) + 1
    return [box_scan(lc, p_lo + j * step, tref) for j in range(n)]


def best_of(results):
    return max(results, key=lambda r: r["snr"])


def top_peaks(results, k=5, sep=2e-4):
    out = []
    for r in sorted(results, key=lambda r: -r["snr"]):
        if all(abs(r["period"] - o["period"]) > sep for o in out):
            out.append({"period": r["period"], "snr": r["snr"], "depth": r["depth"]})
        if len(out) >= k:
            break
    return out


def snr_near(results, p, half=1e-5):
    sel = [r["snr"] for r in results if abs(r["period"] - p) <= half]
    return max(sel) if sel else None


def control_periods(n=N_CONTROL, seed=SEED):
    rng = random.Random(seed)
    out = []
    ratios = (0.5, 2.0 / 3.0, 0.75, 1.0, 4.0 / 3.0, 1.5)
    while len(out) < n:
        p = rng.uniform(1.5, 3.5)
        if any(abs(p - P_GAIA * f) < 0.003 * P_GAIA * f for f in ratios):
            continue
        if any(abs(p - m / 2.0) < 0.02 for m in range(3, 8)):
            continue
        if abs(p - INJ_P) < 0.01:
            continue
        out.append(p)
    return out


def box_epoch_near(best, tref, t_mid):
    p = best["period"]
    n = round((t_mid - tref) / p - best["phase"])
    return tref + (best["phase"] + n) * p


def grid_fit(lc, p_c, t0_c, dp_half, dp_step, dt_half, dt_step, mult=None):
    t, r, w, nights = lc["t"], lc["r"], lc["we"], lc["night"]
    n_p = int(round(2 * dp_half / dp_step)) + 1 if dp_half > 0 else 1
    n_t = int(round(2 * dt_half / dt_step)) + 1
    reach = dt_half + _HALF14
    best = None
    for a in range(n_p):
        p = p_c - dp_half + a * dp_step
        sel = []
        for i in range(len(t)):
            m = 1 if mult is None else mult.get(nights[i], 0)
            if m == 0:
                continue
            x = ((t[i] - t0_c + 0.5 * p) % p) - 0.5 * p
            if -reach < x < reach:
                sel.append((x, r[i], w[i] * m))
        for b in range(n_t):
            off = -dt_half + b * dt_step
            num = 0.0
            den = 0.0
            for x, ri, wi in sel:
                y = x - off
                if y < 0:
                    y = -y
                if y >= _HALF14:
                    continue
                s = 1.0 if y <= _HALF23 else (_HALF14 - y) / _RAMP
                num += wi * ri * s
                den += wi * s * s
            if den <= 0:
                continue
            dchi = num * num / den if num > 0 else -num * num / den
            if best is None or dchi > best["dchi2"]:
                best = {"period": p, "t0": t0_c + off, "depth": num / den,
                        "sigma_white": 1.0 / math.sqrt(den), "dchi2": dchi,
                        "edge": (n_p > 1 and a in (0, n_p - 1)) or b in (0, n_t - 1)}
    return best


def depth_fit(lc, p, t0, phase_off=0.0, parity=None, mult=None):
    num = 0.0
    den = 0.0
    nights = set()
    tc = t0 + phase_off * p
    for i in range(len(lc["t"])):
        m = 1 if mult is None else mult.get(lc["night"][i], 0)
        if m == 0:
            continue
        x = fold_dt(lc["t"][i], tc, p)
        s = shape(x)
        if s <= 0:
            continue
        if parity is not None:
            cyc = int(math.floor((lc["t"][i] - tc) / p + 0.5))
            if cyc % 2 != parity:
                continue
        num += lc["we"][i] * m * lc["r"][i] * s
        den += lc["we"][i] * m * s * s
        if s > 0.5:
            nights.add(lc["night"][i])
    if den <= 0:
        return {"depth": float("nan"), "sigma_white": float("nan"), "n_nights": 0}
    return {"depth": num / den, "sigma_white": 1.0 / math.sqrt(den), "n_nights": len(nights)}


def night_draws(nights, n_boot, seed):
    rng = random.Random(seed + 1)
    nl = sorted(set(nights))
    draws = []
    for _ in range(n_boot):
        mult = {}
        for _k in range(len(nl)):
            nn = nl[rng.randrange(len(nl))]
            mult[nn] = mult.get(nn, 0) + 1
        draws.append(mult)
    return draws


def weighted_centre(lc, p, t0):
    sw = 0.0
    swt = 0.0
    for i, t in enumerate(lc["t"]):
        s = shape(fold_dt(t, t0, p))
        if s > 0:
            sw += lc["we"][i] * s
            swt += lc["we"][i] * s * t
    return swt / sw if sw > 0 else None


# ---------------------------------------------------------------- labels
def detection_label(snr_box, control_max, snr_fit, n_nights, depth, inj_ok):
    det = (depth > 0 and snr_box >= SNR_BOX_MIN and snr_box > control_max
           and snr_fit >= SNR_FIT_MIN and n_nights >= MIN_ECL_NIGHTS)
    if det:
        return "ASASSN_DETECTED"
    return "ASASSN_NOT_DETECTED" if inj_ok else "ASASSN_INSENSITIVE"


def branch_label(p_a, sig_a):
    zg = (p_a - P_GAIA) / math.sqrt(sig_a ** 2 + SIG_P_GAIA ** 2)
    zw = (p_a - P_W1) / math.sqrt(sig_a ** 2 + SIG_P_W1 ** 2)
    g = abs(zg) <= Z_MATCH
    w = abs(zw) <= Z_MATCH
    if g and w:
        lab = "BOTH_CONSISTENT"
    elif g:
        lab = "GAIA_BRANCH"
    elif w:
        lab = "WASP_BRANCH"
    else:
        lab = "NEITHER"
    return lab, zg, zw


def combine_ephemeris(t_a, st_a, p_a, sp_a, t_t=T_TESS, st_t=SIG_T_TESS):
    x = (t_t - t_a) / p_a
    n = int(round(x))
    frac = x - n
    sig_x = math.sqrt(st_t ** 2 + st_a ** 2 + (n * sp_a) ** 2) / p_a
    out = {"cycles": x, "N": n, "frac": frac, "sig_x": sig_x}
    if n == 0 or not math.isfinite(sig_x):
        out["label"] = "EPHEMERIS_UNTESTABLE"
        return out
    p_c = (t_t - t_a) / n
    sp_c = math.sqrt(st_t ** 2 + st_a ** 2) / abs(n)
    if sig_x >= 0.1:
        label = "EPHEMERIS_AMBIGUOUS"
    elif abs(frac) <= 3.0 * sig_x:
        label = "EPHEMERIS_UNIQUE"
    else:
        label = "EPHEMERIS_INCONSISTENT"
    out.update({"label": label, "P_comb": p_c, "sig_P_comb": sp_c})
    return out


def wasp_link(p_at, sp_at, t_w=T_W1, st_w=SIG_T_W1):
    x = (T_TESS - t_w) / p_at
    n = int(round(x))
    resid = (x - n) * p_at
    sig = math.sqrt(st_w ** 2 + SIG_T_TESS ** 2 + (n * sp_at) ** 2)
    if not math.isfinite(sig) or sig >= 0.1 * p_at:
        lab = "WASP_LINK_UNTESTABLE"
    elif abs(resid) <= 3.0 * sig:
        lab = "WASP_ON_EPHEMERIS"
    else:
        lab = "WASP_OFF_EPHEMERIS"
    return {"label": lab, "N": n, "resid_d": resid, "sigma_d": sig,
            "P_19yr": (T_TESS - t_w) / n if n else None}


def blend_label_one(z):
    if z is None or not math.isfinite(z):
        return "BLEND_UNTESTABLE"
    if z > BLEND_Z:
        return "ON_TARGET"
    if z < -BLEND_Z:
        return "ON_NEIGHBOUR"
    return "BLEND_UNRESOLVED"


def common_mode_label(comps):
    usable = [c for c in comps if c.get("status") == "ok"]
    dippers = [c for c in usable if c["depth"] > DIP_DEPTH and c["z"] > DIP_Z]
    if len(usable) < COMP_MIN_USABLE:
        return "COMMON_UNTESTABLE", len(usable), len(dippers)
    if len(dippers) >= 4:
        return "COMMON_MODE", len(usable), len(dippers)
    if len(dippers) <= 1:
        return "COMMON_CLEAN", len(usable), len(dippers)
    return "COMMON_MIXED", len(usable), len(dippers)


# ---------------------------------------------------------------- part A: ASAS-SN
def bootstrap_fit(lc, p, t0, draws, dp_half, dp_step, dt_half, dt_step, log):
    bp, bt, bd = [], [], []
    n_edge = 0
    for k, mult in enumerate(draws):
        g = grid_fit(lc, p, t0, dp_half, dp_step, dt_half, dt_step, mult=mult)
        if g is None:
            continue
        n_edge += 1 if g["edge"] else 0
        bp.append(g["period"])
        bt.append(g["t0"])
        bd.append(g["depth"])
        if (k + 1) % 25 == 0:
            log("[boot] %d/%d" % (k + 1, len(draws)))
    return {"n": len(bp), "edge_fraction": n_edge / max(len(bp), 1),
            "sigma_P": std(bp), "sigma_T0": std(bt), "sigma_depth": std(bd),
            "grid": [dp_half, dp_step, dt_half, dt_step]}


def analyse_asassn(rows, nb_rows, n_control=N_CONTROL, n_boot=N_BOOT, seed=SEED, log=print,
                   p_lo=A_P_LO, p_hi=A_P_HI, p_step=A_P_STEP):
    res = {"status": "ok"}
    lc = build_lc(rows)
    if len(lc["t"]) < 200:
        res["label"] = "ASASSN_INSENSITIVE"
        res["error"] = "too few points (%d)" % len(lc["t"])
        return res, None
    ts = sorted(lc["t"])
    t_mid = ts[len(ts) // 2]
    res["data"] = {"n_points": len(lc["t"]), "n_nights": len(set(lc["night"])),
                   "groups": sorted(set(lc["cam"])), "t_first": ts[0], "t_last": ts[-1],
                   "chi2_red": lc["chi2_red"]}
    # 1. controls first
    cst = sorted(box_scan(lc, p, T_TESS)["snr"] for p in control_periods(n_control, seed))
    cmax = cst[-1]
    res["controls"] = {"n": len(cst), "max_snr": cmax, "median_snr": median(cst),
                       "p95_snr": cst[int(0.95 * (len(cst) - 1))]}
    log("[A] controls max %.2f" % cmax)
    # 2. injection
    inj = inject(lc, INJ_DEPTH, INJ_P, INJ_T0)
    bi = best_of(scan(inj, T_TESS, INJ_P - 0.0009, INJ_P + 0.0009, p_step))
    inj_ok = bi["snr"] > cmax and bi["snr"] >= SNR_BOX_MIN and abs(bi["period"] - INJ_P) < 1e-4
    res["injection"] = {"found_P": bi["period"], "snr": bi["snr"], "passed": inj_ok}
    log("[A] injection snr %.2f passed %s" % (bi["snr"], inj_ok))
    # 3. search
    sc = scan(lc, T_TESS, p_lo, p_hi, p_step)
    best = best_of(sc)
    res["box"] = dict(best)
    res["box"]["at_window_edge"] = (best["period"] - p_lo < 2.5 * p_step
                                    or p_hi - best["period"] < 2.5 * p_step)
    res["box_snr_at_candidates"] = {k: snr_near(sc, v) for k, v in CANDIDATES.items()}
    res["box_top_peaks"] = top_peaks(sc)
    log("[A] box best P %.6f snr %.2f" % (best["period"], best["snr"]))
    # 4. fits
    t0b = box_epoch_near(best, T_TESS, t_mid)
    c = grid_fit(lc, best["period"], t0b, 1e-5, 5e-7, 0.02, 0.001)
    if c is None:
        res["label"] = "ASASSN_NOT_DETECTED" if inj_ok else "ASASSN_INSENSITIVE"
        res["error"] = "no points near the box epoch"
        return res, lc
    tw = weighted_centre(lc, c["period"], c["t0"]) or t_mid
    t0r = c["t0"] + round((tw - c["t0"]) / c["period"]) * c["period"]
    fine = grid_fit(lc, c["period"], t0r, 3e-6, 1e-7, 0.004, 0.0002) or dict(c, t0=t0r)
    p_a, t_a = fine["period"], fine["t0"]
    res["fit"] = {"coarse": c, "fine": fine}
    # 5. bootstrap (widened once if more than 20% of draws hit the grid edge)
    draws = night_draws(lc["night"], n_boot, seed)
    bs = bootstrap_fit(lc, p_a, t_a, draws, 5e-6, 2.5e-7, 0.006, 0.0003, log)
    if bs["edge_fraction"] > EDGE_MAX:
        log("[A] widening bootstrap grid (edge %.2f)" % bs["edge_fraction"])
        bs = bootstrap_fit(lc, p_a, t_a, draws, 2e-5, 1e-6, 0.015, 0.0005, log)
    bs["unreliable"] = bs["edge_fraction"] > EDGE_MAX
    res["bootstrap"] = bs
    prim = depth_fit(lc, p_a, t_a)
    sd = bs["sigma_depth"]
    snr_fit = prim["depth"] / sd if sd and sd > 0 else float("nan")
    res["ephemeris"] = {"P": p_a, "sigma_P": bs["sigma_P"], "T0_bjd_tdb": t_a,
                        "sigma_T0": bs["sigma_T0"]}
    res["primary"] = {"depth_mag": prim["depth"], "sigma_boot": sd, "snr_fit": snr_fit,
                      "n_eclipse_nights": prim["n_nights"]}
    odd = depth_fit(lc, p_a, t_a, parity=1)
    even = depth_fit(lc, p_a, t_a, parity=0)
    sec = depth_fit(lc, p_a, t_a, phase_off=0.5)
    res["odd_even"] = {"odd": odd["depth"], "even": even["depth"]}
    res["secondary"] = {"depth_mag": sec["depth"], "sigma_white": sec["sigma_white"]}
    lab = detection_label(best["snr"], cmax, snr_fit, prim["n_nights"], prim["depth"], inj_ok)
    res["label"] = lab
    det = lab == "ASASSN_DETECTED"
    # 6. period branch
    if bs["unreliable"] or not math.isfinite(bs["sigma_P"]):
        res["branch"] = {"label": "BRANCH_UNTESTABLE", "graded": det}
    else:
        bl, zg, zw = branch_label(p_a, bs["sigma_P"])
        res["branch"] = {"label": bl, "z_gaia": zg, "z_wasp_local": zw, "graded": det}
    # 7. TESS link
    eph = combine_ephemeris(t_a, bs["sigma_T0"], p_a, bs["sigma_P"])
    eph["graded"] = det
    res["tess_link"] = eph
    # reported only: what if the ASAS-SN 'jd' column were geocentric JD rather than HJD?
    lcj = dict(lc)
    lcj["t"] = [t + helio_corr_days(t) for t in lc["t"]]
    fj = grid_fit(lcj, p_a, t_a, 3e-6, 1e-7, 0.01, 0.0002)
    if fj is not None:
        ej = combine_ephemeris(fj["t0"], bs["sigma_T0"], fj["period"], bs["sigma_P"])
        res["time_scale_check"] = {"dchi2_as_hjd": fine.get("dchi2"),
                                   "dchi2_if_geocentric_jd": fj["dchi2"],
                                   "T0_shift_d": fj["t0"] - t_a, "P_if_jd": fj["period"],
                                   "tess_link_if_jd": ej.get("label")}
    # 8. WASP link
    if eph.get("label") == "EPHEMERIS_UNIQUE":
        wl = wasp_link(eph["P_comb"], eph["sig_P_comb"])
        wl["graded"] = det
        bl2, zg2, zw2 = branch_label(eph["P_comb"], eph["sig_P_comb"])
        res["combined"] = {"P": eph["P_comb"], "sigma_P": eph["sig_P_comb"],
                           "T0_bjd_tdb": T_TESS, "z_gaia": zg2, "z_wasp_local": zw2}
    else:
        wl = {"label": "WASP_LINK_UNTESTABLE", "graded": False}
    res["wasp_link"] = wl
    # 9. blend against the 38 arcsec neighbour
    bl = {"label": "BLEND_UNTESTABLE", "graded": det}
    if nb_rows:
        nl = build_lc(nb_rows)
        if len(nl["t"]) >= 300:
            dn = depth_fit(nl, p_a, t_a)
            diffs = []
            for mult in draws:
                a = depth_fit(lc, p_a, t_a, mult=mult)["depth"]
                b = depth_fit(nl, p_a, t_a, mult=mult)["depth"]
                if math.isfinite(a) and math.isfinite(b):
                    diffs.append(a - b)
            sdiff = std(diffs)
            z = (prim["depth"] - dn["depth"]) / sdiff if sdiff and sdiff > 0 else float("nan")
            bl = {"label": blend_label_one(z), "graded": det, "n_points": len(nl["t"]),
                  "depth_neighbour": dn["depth"], "sigma_diff": sdiff, "z": z}
            res["_nl"] = nl
        else:
            bl["n_points"] = len(nl["t"])
    res["blend"] = bl
    return res, lc


# ---------------------------------------------------------------- part B: WASP common mode
def analyse_common(target_rows, n38_rows, comp_rows, n_boot=N_BOOT, seed=SEED, log=print,
                   check_repro=True):
    res = {}
    lc = build_lc(target_rows)
    detrend_eph(lc, P_C1, T_C1)
    d_t = depth_fit(lc, P_W1, T_W1)["depth"]
    rep = {"target_depth": d_t, "target_ok": abs(d_t - V1_TARGET_DEPTH) < REPRO_TOL}
    if n38_rows:
        nl = build_lc(n38_rows)
        detrend_eph(nl, P_W1, T_W1)
        d38 = depth_fit(nl, P_W1, T_W1)["depth"]
        rep["n38_depth"] = d38
        rep["n38_ok"] = abs(d38 - V1_N38_DEPTH) < REPRO_TOL
    rep["ok"] = rep["target_ok"] and rep.get("n38_ok", False) if check_repro else True
    res["repro"] = rep
    draws = night_draws(lc["night"], n_boot, seed)
    comps = []
    for name, rows in comp_rows.items():
        if not rows:
            comps.append({"name": name, "status": "no data"})
            continue
        cl = build_lc(rows)
        if len(cl["t"]) < COMP_MIN_POINTS:
            comps.append({"name": name, "status": "too few points", "n": len(cl["t"])})
            continue
        detrend_eph(cl, P_W1, T_W1)
        d = depth_fit(cl, P_W1, T_W1)
        bd = [depth_fit(cl, P_W1, T_W1, mult=m)["depth"] for m in draws]
        sb = std(bd)
        z = d["depth"] / sb if sb and sb > 0 else float("nan")
        comps.append({"name": name, "status": "ok", "n_points": len(cl["t"]),
                      "depth": d["depth"], "sigma_boot": sb, "z": z,
                      "n_eclipse_nights": d["n_nights"]})
        log("[B] %s depth %.4f z %.2f" % (name, d["depth"], z))
    lab, n_use, n_dip = common_mode_label(comps)
    if check_repro and not rep["ok"]:
        lab = "COMMON_REPRO_FAILED"
    ok = [c for c in comps if c.get("status") == "ok"]
    res.update({"label": lab, "n_usable": n_use, "n_dippers": n_dip, "comps": comps,
                "median_comp_depth": median([c["depth"] for c in ok]) if ok else None})
    return res


# ---------------------------------------------------------------- part C: WASP wide scan
def analyse_wasp_wide(target_rows, n_control=N_CONTROL, seed=SEED, log=print,
                      p_lo=W_P_LO, p_hi=W_P_HI, p_step=W_P_STEP):
    lc = build_lc(target_rows)
    detrend_free(lc)
    cst = sorted(box_scan(lc, p, T_TESS)["snr"] for p in control_periods(n_control, seed))
    sc = scan(lc, T_TESS, p_lo, p_hi, p_step)
    best = best_of(sc)
    log("[C] wide best P %.6f snr %.2f" % (best["period"], best["snr"]))
    return {"chi2_red_after_free_detrend": lc["chi2_red"],
            "controls": {"max_snr": cst[-1], "p95_snr": cst[int(0.95 * (len(cst) - 1))],
                         "median_snr": median(cst)},
            "best": best, "top_peaks": top_peaks(sc),
            "snr_at_candidates": {k: snr_near(sc, v) for k, v in CANDIDATES.items()},
            "_scan": [(r["period"], r["snr"]) for r in sc]}


def folded_bins(lc, p, t0, nbin=200):
    sums = [0.0] * nbin
    cnt = [0] * nbin
    for t, r in zip(lc["t"], lc["r"]):
        b = min(nbin - 1, int((fold_dt(t, t0, p) / p + 0.5) * nbin))
        sums[b] += r
        cnt[b] += 1
    return [((b + 0.5) / nbin - 0.5, sums[b] / cnt[b] if cnt[b] else float("nan"), cnt[b])
            for b in range(nbin)]


# ---------------------------------------------------------------- I/O
def fetch(url, path, timeout=90, tries=3):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            return text
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(5 * (k + 1))
    raise RuntimeError("fetch failed %s: %s" % (url, last))


def wasp_rows(name, data_dir, log=print):
    fn = os.path.join(data_dir, name.replace(" ", "_").replace("+", "p") + ".csv")
    url = WASP_BASE + "/csv?" + urllib.parse.urlencode({"object": name},
                                                       quote_via=urllib.parse.quote)
    try:
        rows = parse_wasp_csv(fetch(url, fn))
        log("[fetch] %s rows %d" % (name, len(rows)))
        return rows
    except RuntimeError as exc:
        log(str(exc))
        return []


def clean_json(o):
    if isinstance(o, dict):
        return {k: clean_json(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, list):
        return [clean_json(v) for v in o]
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


# ---------------------------------------------------------------- self-test
def make_asassn_synth(seed, depth, p, t0, noise=0.015):
    rng = random.Random(seed)
    rows = []
    t = 2456500.0
    while t < 2460900.0:
        doy = (t - 2456500.0) % 365.25
        if doy < 250 and rng.random() < 0.65:
            band = "bA|V" if t < 2458400 else "bF|g"
            tv = t + 0.2 + 0.5 * rng.random()
            for j in range(3):
                tt = tv + j * 0.0015
                m = 10.8 + rng.gauss(0.0, noise)
                if depth:
                    m += depth * shape(fold_dt(tt, t0, p))
                rows.append((tt, band, m, noise))
        t += 1.0
    return rows


def make_wasp_synth(seed, depth, p, t0, n_nights=110, noise=0.012):
    rng = random.Random(seed)
    rows = []
    for base in (2453870.0, 2454235.0):
        for k in range(n_nights // 2):
            if rng.random() < 0.3:
                continue
            off = rng.gauss(0.0, 0.004)
            for j in range(40):
                t = base + k + 0.25 + j * 0.008
                m = 10.9 + off + rng.gauss(0.0, noise)
                if depth:
                    m += depth * shape(fold_dt(t, t0, p))
                rows.append((t, "225", m, noise))
    return rows


def self_test(log=print):
    checks = {}
    p_true = 2.32885
    rows = make_asassn_synth(1, 0.05, p_true, T_TESS)
    nb = make_asassn_synth(2, 0.004, p_true, T_TESS)
    q = lambda s: None  # noqa: E731
    r, _ = analyse_asassn(rows, nb, n_control=30, n_boot=12, log=q,
                          p_lo=2.3284, p_hi=2.3293, p_step=2e-6)
    e = r.get("ephemeris", {})
    checks["A_detected"] = r.get("label") == "ASASSN_DETECTED"
    checks["A_injection"] = r.get("injection", {}).get("passed") is True
    checks["A_period"] = abs(e.get("P", 0) - p_true) < 3e-6
    checks["A_branch_gaia"] = r.get("branch", {}).get("label") == "GAIA_BRANCH"
    checks["A_tess_unique"] = r.get("tess_link", {}).get("label") == "EPHEMERIS_UNIQUE"
    checks["A_on_target"] = r.get("blend", {}).get("label") == "ON_TARGET"
    rn, _ = analyse_asassn(make_asassn_synth(3, 0.0, p_true, T_TESS), [], n_control=30,
                           n_boot=5, log=q, p_lo=2.3284, p_hi=2.3293, p_step=2e-6)
    checks["A_null_not_detected"] = rn.get("label") != "ASASSN_DETECTED"
    tw = make_wasp_synth(4, 0.07, P_W1, T_W1)
    clean = {"c%d" % i: make_wasp_synth(10 + i, 0.0, P_W1, T_W1) for i in range(7)}
    rc = analyse_common(tw, [], clean, n_boot=12, log=q, check_repro=False)
    checks["B_clean"] = rc["label"] == "COMMON_CLEAN"
    dirty = {"c%d" % i: make_wasp_synth(20 + i, 0.05, P_W1, T_W1) for i in range(7)}
    rd = analyse_common(tw, [], dirty, n_boot=12, log=q, check_repro=False)
    checks["B_common"] = rd["label"] == "COMMON_MODE"
    checks["labels"] = (branch_label(2.32974, 2e-6)[0] == "WASP_BRANCH"
                        and wasp_link(2.3287683, 2e-6)["label"] == "WASP_ON_EPHEMERIS"
                        and wasp_link(2.3289298, 2e-6)["label"] == "WASP_OFF_EPHEMERIS")
    ok = True
    for k, v in checks.items():
        log("[self-test] %-22s %s" % (k, "ok" if v else "FAIL"))
        ok = ok and v
    log("[self-test] A: P=%s label=%s branch=%s link=%s blend=%s" % (
        e.get("P"), r.get("label"), r.get("branch", {}).get("label"),
        r.get("tess_link", {}).get("label"), r.get("blend", {}).get("label")))
    return ok


# ---------------------------------------------------------------- main
def load_asassn(path):
    if not os.path.exists(path) or os.path.getsize(path) < 200:
        return [], {"error": "file missing"}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return parse_asassn_csv(f.read())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--asassn-dir", default="asassn")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    if a.self_test:
        ok = self_test()
        print("SELF_TEST_OK" if ok else "SELF_TEST_FAILED")
        return 0 if ok else 3
    os.makedirs(a.data_dir, exist_ok=True)
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "stage": "start"}
    summ = os.path.join(a.out_dir, "tyc_period_summary.json")

    def save():
        with open(summ, "w", encoding="utf-8") as f:
            json.dump(clean_json(out), f, indent=1, default=str)

    # Part B and C first (WASP; data partly cached by tyc6340-wasp-v1)
    trows = wasp_rows(WASP_TARGET, a.data_dir)
    n38 = wasp_rows(WASP_N38, a.data_dir)
    comps = {n: wasp_rows(n, a.data_dir) for n in WASP_COMPS}
    if trows:
        out["B_common_mode"] = analyse_common(trows, n38, comps)
        out["stage"] = "B"
        save()
        wide = analyse_wasp_wide(trows)
        with open(os.path.join(a.out_dir, "wasp_wide_scan.csv"), "w", encoding="utf-8") as f:
            f.write("period,snr\n")
            for p, s in wide["_scan"]:
                f.write("%.6f,%.4f\n" % (p, s))
        out["C_wasp_wide_scan"] = wide
        out["stage"] = "C"
        save()
    else:
        out["B_common_mode"] = {"label": "COMMON_UNTESTABLE", "error": "no target WASP data"}
    with open(os.path.join(a.out_dir, "common_mode.csv"), "w", encoding="utf-8") as f:
        f.write("name,status,n_points,depth_mag,sigma_boot,z\n")
        for c in out["B_common_mode"].get("comps", []):
            f.write("%s,%s,%s,%s,%s,%s\n" % (c["name"], c["status"], c.get("n_points", ""),
                                            c.get("depth", ""), c.get("sigma_boot", ""),
                                            c.get("z", "")))
    # Part A: ASAS-SN
    st_path = os.path.join(a.asassn_dir, "fetch_status.json")
    if os.path.exists(st_path):
        with open(st_path, "r", encoding="utf-8") as f:
            out["A_fetch_status"] = json.load(f)
    arows, ainfo = load_asassn(os.path.join(a.asassn_dir, "target.csv"))
    nrows, ninfo = load_asassn(os.path.join(a.asassn_dir, "neighbour.csv"))
    out["A_parse"] = {"target": ainfo, "neighbour": ninfo}
    if not arows:
        out["A_asassn"] = {"label": "ASASSN_UNAVAILABLE"}
    else:
        ra, lc = analyse_asassn(arows, nrows)
        nl = ra.pop("_nl", None)
        out["A_asassn"] = ra
        if lc is not None and "ephemeris" in ra:
            with open(os.path.join(a.out_dir, "asassn_folded.csv"), "w", encoding="utf-8") as f:
                f.write("object,ephemeris,phase,mean_resid_mag,n\n")
                eph = [("asassn", ra["ephemeris"]["P"], ra["ephemeris"]["T0_bjd_tdb"]),
                       ("gaia_P_tess_T0", P_GAIA, T_TESS)]
                for tag, p, t0 in eph:
                    for obj, l in (("target", lc), ("neighbour38", nl)):
                        if l is None:
                            continue
                        for ph, m, c in folded_bins(l, p, t0):
                            f.write("%s,%s,%.4f,%.5f,%d\n" % (obj, tag, ph, m, c))
    out["stage"] = "done"
    save()
    A = out["A_asassn"]
    lines = ["# tyc_period %s report" % VERSION, "",
             "- A detection: **%s**" % A.get("label"),
             "- A period branch: **%s**" % A.get("branch", {}).get("label"),
             "- A TESS link: **%s**" % A.get("tess_link", {}).get("label"),
             "- A WASP link: **%s**" % A.get("wasp_link", {}).get("label"),
             "- A blend (38 arcsec neighbour): **%s**" % A.get("blend", {}).get("label"),
             "- B WASP common mode: **%s**" % out["B_common_mode"].get("label"), "",
             "```", json.dumps(clean_json(out), indent=1, default=str)[:40000], "```"]
    with open(os.path.join(a.out_dir, "tyc_period_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({"A": A.get("label"), "branch": A.get("branch", {}).get("label"),
                      "tess_link": A.get("tess_link", {}).get("label"),
                      "wasp_link": A.get("wasp_link", {}).get("label"),
                      "blend": A.get("blend", {}).get("label"),
                      "P": A.get("ephemeris", {}).get("P"),
                      "B": out["B_common_mode"].get("label")}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
