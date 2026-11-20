#!/usr/bin/env python3
# wasp_tyc.py 0.1.0 -- SuperWASP DR1 check of TYC 6340-23-1 (TIC 71945261): is the TESS eclipse
# seen by an independent instrument in 2006-2008, what is the 17-year ephemeris, and is the
# eclipse on the target rather than a WASP neighbour?
# By MV2 of Munim, Inc.; made with AI agents working in his name. License: Apache-2.0.
# Rules: findings/2026-11-20-tyc6340-wasp-prereg.md (written before this job ran).
# Pure standard library (no numpy) so the tests run anywhere.
"""Usage:
  python wasp_tyc.py --self-test
  python wasp_tyc.py --data-dir /data/wasp-tyc6340 --out-dir /out
Exit codes: 0 ok; 2 network failure on the target light curve (re-file unchanged);
3 self-test failed.
"""
import argparse
import json
import math
import os
import random
import sys
import time
import urllib.parse
import urllib.request

VERSION = "0.1.0"
BASE = "https://wasp.cerit-sc.cz"
TARGET = "1SWASP J202214.65-220425.1"
NEIGHBOURS = ["1SWASP J202215.96-220458.7",   # 38 arcsec, 11.25 mag
              "1SWASP J202209.46-220414.3",   # 73 arcsec, 13.84 mag
              "1SWASP J202211.21-220522.8"]   # 75 arcsec, 12.68 mag
UA = "MV2-Munim-research/0.1 (mv2@munimtech.com)"

P_GAIA = 2.3289298          # Gaia DR3 SB1 period (d)
SIG_P_GAIA = 0.00014
T_TESS = 2460803.0299       # TESS sector 92 primary eclipse, BJD_TDB
SIG_T_TESS = 0.001          # conservative, fixed in the pre-registration
TESS_DEPTH_MAG = 0.068
T14 = 0.0990                # total eclipse duration (d) from the TESS fit geometry
T23 = 0.0324                # flat part (d)
UTC_TO_TDB = 65.184 / 86400.0   # TT-UTC 2006-2008 (TDB ~ TT); HJD vs BJD (< 4 s) ignored
P_LO, P_HI, P_STEP = 2.3280, 2.3298, 5e-6
NBIN = 1000
BOX_W = 0.06
N_CONTROL = 300
N_BOOT = 150
SEED = 20261120
ERR_FLOOR = 0.005
MAX_ERR = 0.1
SNR_BOX_MIN = 7.0
SNR_FIT_MIN = 5.0
MIN_ECL_NIGHTS = 5
INJ_P = 2.6
INJ_DEPTH = 0.03
INJ_T0 = 2454200.3
BLEND_Z = 3.0

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


def parse_csv(text):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or not (line[0].isdigit()):
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
        if not (math.isfinite(t) and math.isfinite(m) and math.isfinite(e)):
            continue
        rows.append((t, parts[1].strip(), m, e))
    return rows


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


# ---------------------------------------------------------------- light curves
def build_lc(rows):
    """rows: (HJD_UTC, camera, mag, err). Returns a light-curve dict (times in BJD_TDB)."""
    rows = [x for x in rows if 0.0 < x[3] <= MAX_ERR]
    t = [x[0] + UTC_TO_TDB for x in rows]
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


def detrend(lc, p, t0, win=0.1, min_out=10):
    """Subtract each (camera, night) median of points outside +-win of the predicted eclipse."""
    groups = {}
    for i in range(len(lc["t"])):
        groups.setdefault((lc["cam"][i], lc["night"][i]), []).append(i)
    r = list(lc["r0"])
    n_corr = 0
    for idx in groups.values():
        out = [lc["r0"][i] for i in idx if abs(fold_dt(lc["t"][i], t0, p)) > win]
        if len(out) >= min_out:
            m = median(out)
            n_corr += 1
            for i in idx:
                r[i] = lc["r0"][i] - m
    lc["r"] = r
    set_weights(lc, p, t0)
    return n_corr


def inject(lc, depth, p, t0):
    new = dict(lc)
    add = [depth * shape(fold_dt(t, t0, p)) for t in lc["t"]]
    new["r0"] = [a + b for a, b in zip(lc["r0"], add)]
    new["r"] = [a + b for a, b in zip(lc["r"], add)]
    return new


# ---------------------------------------------------------------- search
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
        snr = d / sig
        if snr > best[0]:
            best = (snr, start, d, sig)
    snr, start, d, sig = best
    phase = ((start + 0.5 * nb) / nbin) % 1.0
    return {"snr": snr, "depth": d, "sigma": sig, "phase": phase, "period": period}


def search(lc, tref, p_lo=P_LO, p_hi=P_HI, step=P_STEP):
    n = int(round((p_hi - p_lo) / step)) + 1
    best = None
    for j in range(n):
        res = box_scan(lc, p_lo + j * step, tref)
        if best is None or res["snr"] > best["snr"]:
            best = res
    return best


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
    n_p = int(round(2 * dp_half / dp_step)) + 1
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
                        "edge": a in (0, n_p - 1) or b in (0, n_t - 1)}
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


# ---------------------------------------------------------------- grading
def combine_ephemeris(t_w, st_w, p_w, sp_w, t_t=T_TESS, st_t=SIG_T_TESS):
    x = (t_t - t_w) / p_w
    n = int(round(x))
    frac = x - n
    sig_x = math.sqrt(st_t ** 2 + st_w ** 2 + (n * sp_w) ** 2) / p_w
    out = {"cycles": x, "N": n, "frac": frac, "sig_x": sig_x}
    if n == 0 or not math.isfinite(sig_x):
        out["label"] = "EPHEMERIS_UNTESTABLE"
        return out
    p_c = (t_t - t_w) / n
    sp_c = math.sqrt(st_t ** 2 + st_w ** 2) / abs(n)
    if sig_x >= 0.1:
        label = "EPHEMERIS_AMBIGUOUS"
    elif abs(frac) <= 3.0 * sig_x:
        label = "EPHEMERIS_UNIQUE"
    else:
        label = "EPHEMERIS_INCONSISTENT"
    gz = (p_c - P_GAIA) / math.sqrt(SIG_P_GAIA ** 2 + sp_c ** 2)
    out.update({"label": label, "P_comb": p_c, "sig_P_comb": sp_c, "gaia_z": gz,
                "gaia_consistent": abs(gz) <= 3.0,
                "alt_periods": {str(n + d): (t_t - t_w) / (n + d) for d in (-1, 1)}})
    return out


def detection_label(snr_box, control_max, snr_fit, n_nights, depth, inj_ok):
    det = (depth > 0 and snr_box >= SNR_BOX_MIN and snr_box > control_max
           and snr_fit >= SNR_FIT_MIN and n_nights >= MIN_ECL_NIGHTS)
    if det:
        return "WASP_DETECTED"
    return "WASP_NOT_DETECTED" if inj_ok else "WASP_INSENSITIVE"


def blend_label(zs):
    """zs: {name: (d_target - d_neighbour)/sigma_diff}."""
    if not zs:
        return "BLEND_UNTESTABLE", None
    worst = min(zs, key=lambda k: zs[k])
    if zs[worst] < -BLEND_Z:
        return "ON_NEIGHBOUR", worst
    if all(v > BLEND_Z for v in zs.values()):
        return "ON_TARGET", None
    return "BLEND_UNRESOLVED", None


# ---------------------------------------------------------------- pipeline
def analyse(target_rows, neighbour_rows, n_control=N_CONTROL, n_boot=N_BOOT, seed=SEED,
            log=print, save=None):
    res = {"version": VERSION, "stage": "start"}

    def stage(name):
        res["stage"] = name
        log("[stage] %s %s" % (name, time.strftime("%H:%M:%S")))
        if save:
            save(res)

    lc = build_lc(target_rows)
    if len(lc["t"]) < 200:
        res["label"] = "WASP_INSENSITIVE"
        res["error"] = "too few points"
        return res
    tref = T_TESS
    t_sorted = sorted(lc["t"])
    t_mid = t_sorted[len(t_sorted) // 2]
    res["target"] = {"name": TARGET, "n_rows_err_ok": lc["n_in"], "n_points": len(lc["t"]),
                     "n_nights": len(set(lc["night"])), "n_seasons": len(set(lc["season"])),
                     "cameras": sorted(set(lc["cam"])), "t_first": t_sorted[0],
                     "t_last": t_sorted[-1], "chi2_red_initial": lc["chi2_red"]}
    stage("loaded")

    # 1. control periods (no planted signal), before anything else
    cps = control_periods(n_control, seed)
    cst = sorted(box_scan(lc, p, tref)["snr"] for p in cps)
    cmax = cst[-1]
    res["controls"] = {"n": len(cst), "max_snr": cmax, "median_snr": median(cst),
                       "p95_snr": cst[int(0.95 * (len(cst) - 1))]}
    stage("controls")

    # 2. injection control
    inj = inject(lc, INJ_DEPTH, INJ_P, INJ_T0)
    bi = search(inj, tref, INJ_P - 0.0009, INJ_P + 0.0009)
    inj_ok = bi["snr"] > cmax and bi["snr"] >= SNR_BOX_MIN and abs(bi["period"] - INJ_P) < 1e-4
    res["injection"] = {"P": INJ_P, "depth": INJ_DEPTH, "found_P": bi["period"],
                        "snr": bi["snr"], "passed": inj_ok}
    stage("injection")

    # 3. box search in Gaia's period window
    best = search(lc, tref)
    res["box"] = dict(best)
    stage("box")

    # 4. trapezoid fit (coarse, per-night detrend, fine)
    t0b = box_epoch_near(best, tref, t_mid)
    c = grid_fit(lc, best["period"], t0b, 1.5e-4, 2e-6, 0.03, 0.001)
    if c is None:
        res["label"] = "WASP_NOT_DETECTED" if inj_ok else "WASP_INSENSITIVE"
        res["error"] = "no points near the box epoch"
        return res
    n_corr = detrend(lc, c["period"], c["t0"])
    c2 = grid_fit(lc, c["period"], c["t0"], 3e-5, 1e-6, 0.006, 0.0002) or c
    # reference epoch near the weighted centre of in-eclipse points
    sw = 0.0
    swt = 0.0
    for i, t in enumerate(lc["t"]):
        s = shape(fold_dt(t, c2["t0"], c2["period"]))
        if s > 0:
            sw += lc["we"][i] * s
            swt += lc["we"][i] * s * t
    tw = swt / sw if sw > 0 else t_mid
    nref = round((tw - c2["t0"]) / c2["period"])
    t0r = c2["t0"] + nref * c2["period"]
    fine = grid_fit(lc, c2["period"], t0r, 4e-6, 2e-7, 0.003, 0.0001) or dict(c2, t0=t0r)
    p_w, t_w = fine["period"], fine["t0"]
    res["fit"] = {"coarse": c, "nights_detrended": n_corr, "fine": fine,
                  "chi2_red_after_detrend": lc["chi2_red"]}
    stage("fit")

    # 5. night bootstrap (period, epoch, depth, odd/even, secondary)
    draws = night_draws(lc["night"], n_boot, seed)
    bp, bt, bd, bodd, beven, bsec = [], [], [], [], [], []
    n_edge = 0
    for k, mult in enumerate(draws):
        g = grid_fit(lc, p_w, t_w, 3e-5, 1e-6, 0.006, 0.0002, mult=mult)
        if g is None:
            continue
        n_edge += 1 if g["edge"] else 0
        bp.append(g["period"])
        bt.append(g["t0"])
        bd.append(g["depth"])
        bodd.append(depth_fit(lc, p_w, t_w, parity=1, mult=mult)["depth"])
        beven.append(depth_fit(lc, p_w, t_w, parity=0, mult=mult)["depth"])
        bsec.append(depth_fit(lc, p_w, t_w, phase_off=0.5, mult=mult)["depth"])
        if (k + 1) % 25 == 0:
            log("[boot] %d/%d" % (k + 1, len(draws)))
    sp, st, sd = std(bp), std(bt), std(bd)
    prim = depth_fit(lc, p_w, t_w)
    odd = depth_fit(lc, p_w, t_w, parity=1)
    even = depth_fit(lc, p_w, t_w, parity=0)
    sec = depth_fit(lc, p_w, t_w, phase_off=0.5)
    s_oe = std([a - b for a, b in zip(bodd, beven) if math.isfinite(a - b)])
    s_sec = std([v for v in bsec if math.isfinite(v)])
    res["bootstrap"] = {"n": len(bp), "edge_fraction": n_edge / max(len(bp), 1),
                        "sigma_P": sp, "sigma_T0": st, "sigma_depth": sd}
    snr_fit = prim["depth"] / sd if sd > 0 else float("nan")
    res["wasp_ephemeris"] = {"T0_bjd_tdb": t_w, "sigma_T0": st, "P": p_w, "sigma_P": sp}
    res["primary"] = {"depth_mag": prim["depth"], "sigma_boot": sd, "snr_fit": snr_fit,
                      "n_eclipse_nights": prim["n_nights"],
                      "ratio_to_tess_depth": prim["depth"] / TESS_DEPTH_MAG}
    res["odd_even"] = {"odd": odd["depth"], "even": even["depth"], "sigma_diff": s_oe,
                       "consistent": abs(odd["depth"] - even["depth"]) <= 3 * s_oe}
    res["secondary"] = {"depth_mag": sec["depth"], "sigma_boot": s_sec,
                        "below_third_of_primary": sec["depth"] < prim["depth"] / 3.0}
    lab = detection_label(best["snr"], cmax, snr_fit, prim["n_nights"], prim["depth"], inj_ok)
    res["label"] = lab
    stage("bootstrap")

    # 6. ephemeris against TESS (graded only if detected)
    eph = combine_ephemeris(t_w, st, p_w, sp)
    eph["graded"] = lab == "WASP_DETECTED"
    if "P_comb" in eph:
        # reported: phase error Gaia's period would give at the DR4 epoch mid-point (2018.7)
        t_dr4 = 2458350.0
        eph["dr4_phase_shift_using_gaia_P"] = (
            (t_dr4 - T_TESS) / P_GAIA - (t_dr4 - T_TESS) / eph["P_comb"])
    res["ephemeris"] = eph
    stage("ephemeris")

    # 7. blend test
    zs = {}
    blend = {}
    for name, rows in neighbour_rows.items():
        if not rows:
            blend[name] = {"status": "no data"}
            continue
        nl = build_lc(rows)
        if len(nl["t"]) < 500:
            blend[name] = {"status": "too few points", "n": len(nl["t"])}
            continue
        detrend(nl, p_w, t_w)
        dn = depth_fit(nl, p_w, t_w)
        diffs = []
        for mult in draws:
            a = depth_fit(lc, p_w, t_w, mult=mult)["depth"]
            b = depth_fit(nl, p_w, t_w, mult=mult)["depth"]
            if math.isfinite(a) and math.isfinite(b):
                diffs.append(a - b)
        sdiff = std(diffs)
        z = (prim["depth"] - dn["depth"]) / sdiff if sdiff > 0 else float("nan")
        blend[name] = {"status": "ok", "n_points": len(nl["t"]), "depth_mag": dn["depth"],
                       "sigma_diff": sdiff, "z_target_minus_neighbour": z}
        if math.isfinite(z):
            zs[name] = z
    bl, who = blend_label(zs)
    res["blend"] = {"label": bl, "neighbour": who, "per_neighbour": blend,
                    "graded": lab == "WASP_DETECTED"}
    stage("blend")

    # 8. reported: per-season eclipse times at the WASP period
    seasons = {}
    for s in sorted(set(lc["season"])):
        sub = {k: [v for v, ss in zip(lc[k], lc["season"]) if ss == s]
               for k in ("t", "r", "we", "night")}
        if len(sub["t"]) < 200:
            continue
        ts = sorted(sub["t"])
        tm = ts[len(ts) // 2]
        n0 = round((tm - t_w) / p_w)
        g = grid_fit(sub, p_w, t_w + n0 * p_w, 0.0, 1e-7, 0.02, 0.0002)
        seasons[str(s)] = {"n_points": len(sub["t"]), "cycle": n0,
                           "o_minus_c_d": (g["t0"] - (t_w + n0 * p_w)) if g else None,
                           "sigma_white_depth": g["sigma_white"] if g else None}
    res["seasons"] = seasons
    res["lc"] = lc
    stage("done")
    return res


def folded_bins(lc, p, t0, nbin=200):
    sums = [0.0] * nbin
    cnt = [0] * nbin
    for t, r in zip(lc["t"], lc["r"]):
        ph = fold_dt(t, t0, p) / p
        b = min(nbin - 1, int((ph + 0.5) * nbin))
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


def wasp_url(name):
    return BASE + "/csv?" + urllib.parse.urlencode({"object": name}, quote_via=urllib.parse.quote)


def prior_art(out_dir):
    """Reported only: VizieR catalogues with a row within 10 arcsec, and the EBLM IV table."""
    out = {}
    queries = {
        "all_10as": "https://vizier.cds.unistra.fr/viz-bin/asu-tsv?-c=305.561052%20-22.073651"
                    "&-c.rs=10&-out.max=3&-out=_r",
        "eblm_iv_60as": "https://vizier.cds.unistra.fr/viz-bin/asu-tsv?-source=J/A%2BA/608/A129"
                        "&-c=305.561052%20-22.073651&-c.rs=60&-out.all",
    }
    for key, url in queries.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read(400000).decode("utf-8", errors="replace")
            with open(os.path.join(out_dir, "vizier_%s.tsv" % key), "w", encoding="utf-8") as f:
                f.write(text)
            names = [ln.split(":", 1)[1].strip() for ln in text.splitlines()
                     if ln.startswith("#Name:")]
            titles = [ln.split(":", 1)[1].strip() for ln in text.splitlines()
                      if ln.startswith("#Title:")]
            flags = [n + " | " + tt for n, tt in zip(names, titles)
                     if any(w in (n + tt).lower() for w in ("eblm", "wasp", "eclips", "variab"))]
            out[key] = {"status": "ok", "n_tables": len(names), "tables": names[:200],
                        "flagged": flags}
        except Exception as exc:  # noqa: BLE001
            out[key] = {"status": "failed", "error": str(exc)[:300]}
    return out


def write_report(res, out_dir):
    e = res.get("ephemeris", {})
    lines = ["# wasp_tyc %s report" % VERSION, "",
             "Detection label: **%s**" % res.get("label"),
             "Ephemeris label: **%s** (graded: %s)" % (e.get("label"), e.get("graded")),
             "Blend label: **%s** %s (graded: %s)" % (res.get("blend", {}).get("label"),
                                                    res.get("blend", {}).get("neighbour") or "",
                                                    res.get("blend", {}).get("graded")),
             "", "```", json.dumps({k: v for k, v in res.items() if k != "lc"}, indent=1,
                                   default=str)[:20000], "```"]
    with open(os.path.join(out_dir, "wasp_tyc_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- self-test
def make_synth(seed, depth, p, t0, n_nights=110, noise=0.012, cam="225"):
    rng = random.Random(seed)
    rows = []
    for base in (2453870.0, 2454235.0):
        for k in range(n_nights // 2):
            if rng.random() < 0.3:
                continue
            off = rng.gauss(0.0, 0.004)
            start = base + k + 0.25
            for j in range(40):
                t = start + j * 0.008
                m = 10.9 + off + rng.gauss(0.0, noise)
                if depth:
                    m += depth * shape(fold_dt(t + UTC_TO_TDB, t0, p))
                rows.append((t, cam, m, noise))
    return rows


def self_test(log=print):
    ok = True
    p_true = 2.32905
    t0_true = T_TESS - 2975 * p_true
    rows = make_synth(1, 0.04, p_true, t0_true)
    nrows = {"nb": make_synth(2, 0.008, p_true, t0_true)}
    r = analyse(rows, nrows, n_control=40, n_boot=20, log=lambda s: None)
    w = r["wasp_ephemeris"]
    n = round((w["T0_bjd_tdb"] - t0_true) / p_true)
    dt = w["T0_bjd_tdb"] - (t0_true + n * p_true)
    checks = {
        "detected": r["label"] == "WASP_DETECTED",
        "injection_passed": r["injection"]["passed"],
        "period": abs(w["P"] - p_true) < 3e-5,
        "epoch": abs(dt) < 0.003,
        "depth": abs(r["primary"]["depth_mag"] - 0.04) < 0.008,
        "ephemeris_unique": r["ephemeris"]["label"] == "EPHEMERIS_UNIQUE",
        "p_comb": abs(r["ephemeris"].get("P_comb", 0) - p_true) < 3e-6,
        "on_target": r["blend"]["label"] == "ON_TARGET",
        "odd_even": r["odd_even"]["consistent"],
    }
    rn = analyse(make_synth(3, 0.0, p_true, t0_true), {}, n_control=20, n_boot=5,
                 log=lambda s: None)
    checks["null_not_detected"] = rn["label"] != "WASP_DETECTED"
    for k, v in checks.items():
        log("[self-test] %-20s %s" % (k, "ok" if v else "FAIL"))
        ok = ok and v
    log("[self-test] P=%.7f T0 err=%.5f depth=%.4f label=%s eph=%s blend=%s" % (
        w["P"], dt, r["primary"]["depth_mag"], r["label"], r["ephemeris"]["label"],
        r["blend"]["label"]))
    return ok


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    if a.self_test:
        ok = self_test()
        print("SELF_TEST_OK" if ok else "SELF_TEST_FAILED")
        return 0 if ok else 3
    os.makedirs(a.data_dir, exist_ok=True)
    os.makedirs(a.out_dir, exist_ok=True)

    def save(res):
        with open(os.path.join(a.out_dir, "wasp_tyc_summary.json"), "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in res.items() if k != "lc"}, f, indent=1, default=str)

    def fname(n):
        return os.path.join(a.data_dir, n.replace(" ", "_").replace("+", "p") + ".csv")
    try:
        trows = parse_csv(fetch(wasp_url(TARGET), fname(TARGET)))
    except RuntimeError as exc:
        print(str(exc))
        return 2
    print("[fetch] target rows %d" % len(trows))
    if len(trows) < 1000:
        print("target light curve too short or not CSV")
        return 2
    nrows = {}
    for n in NEIGHBOURS:
        try:
            nrows[n] = parse_csv(fetch(wasp_url(n), fname(n)))
            print("[fetch] %s rows %d" % (n, len(nrows[n])))
        except RuntimeError as exc:
            print(str(exc))
            nrows[n] = []
    res = analyse(trows, nrows, save=save)
    lc = res.get("lc")
    if lc and "wasp_ephemeris" in res:
        e = res["wasp_ephemeris"]
        with open(os.path.join(a.out_dir, "wasp_tyc_folded.csv"), "w", encoding="utf-8") as f:
            f.write("object,phase,mean_resid_mag,n\n")
            for ph, m, c in folded_bins(lc, e["P"], e["T0_bjd_tdb"]):
                f.write("%s,%.4f,%.5f,%d\n" % (TARGET, ph, m, c))
            for n, rows in nrows.items():
                if len(rows) > 500:
                    nl = build_lc(rows)
                    detrend(nl, e["P"], e["T0_bjd_tdb"])
                    for ph, m, c in folded_bins(nl, e["P"], e["T0_bjd_tdb"]):
                        f.write("%s,%.4f,%.5f,%d\n" % (n, ph, m, c))
    res["prior_art_reported_only"] = prior_art(a.out_dir)
    save(res)
    write_report(res, a.out_dir)
    print(json.dumps({"label": res.get("label"),
                      "ephemeris": res.get("ephemeris", {}).get("label"),
                      "P_comb": res.get("ephemeris", {}).get("P_comb"),
                      "blend": res.get("blend", {}).get("label"),
                      "depth_mag": res.get("primary", {}).get("depth_mag"),
                      "snr_box": res.get("box", {}).get("snr"),
                      "control_max": res.get("controls", {}).get("max_snr")}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
