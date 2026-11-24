# SPDX-License-Identifier: Apache-2.0
"""sb2_ffiscan 0.1.0 - fold TESS light curves (SPOC 2-min, else TESS-SPOC or QLP full-frame) of
Gaia DR3's edge-on double-lined binaries at Gaia's own period, look for an eclipse, and test whether
the dip falls at a conjunction that Gaia's spectroscopic orbit predicts.

MV2, Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.
Pre-registration: findings/2026-11-24-sb2-ffiscan-prereg.md in
https://github.com/munimtechnologies/gaia-orbit-transits

Sample: every star of the sb2-edgeon-screen-v1 table (commit 80be282) with status OK and a TIC number.
Roles (fixed by rule, from that table's own columns):
  control - catalogued eclipsing (vsx_eclipsing, gaia_eb or simbad_eb true)
  toi     - not catalogued eclipsing but a TESS Object of Interest
  target  - everything else
Per star:
  1. Gaia DR3 orbit (ESA TAP, else AIP TAP); its period must equal the screen table's (anchor).
  2. Up to MAX_LC TESS sectors (SPOC 120 s > TESS-SPOC > QLP), spread over the baseline.
  3. Per sector: binned-median trend (window clip(P, 0.5, 3) d), then a 2-harmonic fit at Gaia's
     period with low points clipped (removes ellipsoidal and spot modulation, keeps narrow dips),
     residuals in units of the sector's robust scatter, winsorised at +-ZCLIP.
  4. Box search on a fine period grid within +-5 sigma of Gaia's period (NB phase bins, box widths
     WIDTHS bins, a box must be deeper than its two flanks by SHAPE_MIN of its depth).
  5. The same search at NULL_FACTORS x Gaia's period gives the star's own noise level.
  6. DETECTED if S/N >= SNR_MIN, S/N >= NULL_RATIO x the best null S/N and the box holds points from
     at least 2 orbital cycles.
  7. If DETECTED: secondary dip search, Gaia conjunction-time test (PHASE_MATCH within Z_PHASE sigma,
     Monte Carlo over Gaia's errors), and the separation of the two dips vs Gaia's e and omega.
"""
import argparse
import csv
import io
import json
import math
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.parse
import urllib.request

import numpy as np

VERSION = "0.1.0"
SEED = 20261124
GAIA_REF_BTJD = 389.0           # nss t_periastron is days from JD 2457389.0 = BTJD 389.0
SCREEN_URL = ("https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/"
              "80be282773812acc69c0e5d190abc25687de1f5a/data/sb2-edgeon-screen-v1/sb2_screen.csv")
SCREEN_ROWS = 183
TAP_URLS = [("ESA", "https://gea.esac.esa.int/tap-server/tap/sync"),
            ("AIP", "https://gaia.aip.de/tap/sync")]
ORBIT_COLS = ["period", "period_error", "eccentricity", "eccentricity_error", "arg_periastron",
              "arg_periastron_error", "t_periastron", "t_periastron_error", "nss_solution_type"]
UA = "gaia-orbit-transits/sb2_ffiscan (MV2, Munim, Inc.; open research)"
AUTHOR_RANK = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}

NB = 200
WIDTHS = (1, 2, 3, 4, 6, 8, 12, 16, 24)
MIN_PTS = 10
SHAPE_MIN = 0.5
ZCLIP = 8.0
SNR_MIN = 10.0
NULL_RATIO = 1.5
SNR_SEC = 7.0
Z_PHASE = 3.0
MAX_LC = 6
MAX_STEPS = 400
N_HARM = 2
NULL_FACTORS = (0.7321, 0.7887, 0.8165, 0.8452, 0.9330, 1.0718,
                1.1180, 1.1832, 1.2247, 1.3093, 1.3540, 1.4641)
# hand-vetted before this job (findings/2026-11-23-sb2-screen-results.md, 2026-11-24 correction)
NEW_EB = {400170926: "HD 250735", 189269584: "CD-28 7251"}
KNOWN_HAND = {384284045: "TYC 3616-2395-1 (Eclipses by Appointment A179)",
              79548760: "HD 21273 (Prsa+2022)", 238162238: "HIP 34208 (Prsa+2022)",
              137501278: "BD+83 227 (Prsa+2022)", 121083955: "BD+37 3347 (KOI-3161)",
              17342647: "HD 144359 (heartbeat)"}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def fnum(v, default=float("nan")):
    try:
        if v is None:
            return default
        s = str(v).strip().strip('"')
        if s in ("", "null", "NULL", "nan", "NaN", "None", "--"):
            return default
        x = float(s)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def truthy(v):
    return str(v).strip().strip('"').lower() in ("true", "1", "t", "yes")


def finite(x):
    try:
        return x is not None and math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


# ================================================================ orbit geometry
def true_to_phase(nu, e):
    """True anomaly (rad, scalar or array) -> fraction of the period after periastron, in [0, 1)."""
    nu = np.asarray(nu, float)
    e = np.asarray(e, float)
    E = 2.0 * np.arctan2(np.sqrt(1.0 - e) * np.sin(nu / 2.0), np.sqrt(1.0 + e) * np.cos(nu / 2.0))
    M = E - e * np.sin(E)
    return np.mod(M / (2.0 * math.pi), 1.0)


def conjunction_phases(e, omega_deg):
    """Phases after periastron of the two conjunctions (nu + omega = 90 and 270 deg).
    Circular Gaia solutions (SB1C/SB2C) are used with e = 0, omega = 0 (pre-registered)."""
    w = np.radians(np.asarray(omega_deg, float))
    c1 = true_to_phase(math.pi / 2.0 - w, e)
    c2 = true_to_phase(1.5 * math.pi - w, e)
    if np.ndim(c1) == 0:
        return float(c1), float(c2)
    return c1, c2


def wrap(x, period):
    """Map x into [-period/2, period/2)."""
    return np.mod(np.asarray(x, float) + period / 2.0, period) - period / 2.0


def predict_conj(orb, T_obs, n_draw=3000, seed=SEED):
    """Monte Carlo over Gaia's orbit errors (no correlations). -> dict with, for c1 and c2, the mean
    and sd of O-C = T_obs - predicted conjunction time (days), and the separation (c2 - c1) mod 1."""
    rng = np.random.default_rng(seed)
    circ = not (finite(orb.get("e")) and finite(orb.get("omega")))
    if circ:
        e0, se, w0, sw = 0.0, 0.0, 0.0, 0.0
    else:
        e0, w0 = float(orb["e"]), float(orb["omega"])
        se = float(orb["e_err"]) if finite(orb.get("e_err")) else 0.0
        sw = float(orb["omega_err"]) if finite(orb.get("omega_err")) else 0.0
    P0 = float(orb["P"])
    sP = float(orb["P_err"]) if finite(orb.get("P_err")) else 0.0
    T0 = float(orb["Tp"]) + GAIA_REF_BTJD
    sT = float(orb["Tp_err"]) if finite(orb.get("Tp_err")) else 0.0
    e = np.clip(rng.normal(e0, se, n_draw), 0.0, 0.95) if se > 0 else np.full(n_draw, e0)
    w = rng.normal(w0, sw, n_draw) if sw > 0 else np.full(n_draw, w0)
    P = rng.normal(P0, sP, n_draw) if sP > 0 else np.full(n_draw, P0)
    Tp = rng.normal(T0, sT, n_draw) if sT > 0 else np.full(n_draw, T0)
    c1, c2 = conjunction_phases(e, w)
    n1, n2 = conjunction_phases(e0, w0)
    out = {"circular": bool(circ), "c1_nominal": float(n1), "c2_nominal": float(n2)}
    for name, c, cn in (("c1", c1, n1), ("c2", c2, n2)):
        k0 = round((T_obs - (T0 + cn * P0)) / P0)
        oc_nom = T_obs - (T0 + cn * P0 + k0 * P0)
        oc = T_obs - (Tp + c * P + k0 * P)
        oc = oc_nom + wrap(oc - oc_nom, P0)
        out["oc_%s" % name] = float(np.mean(oc))
        out["sd_%s" % name] = float(np.std(oc))
        out["cycles_%s" % name] = int(k0)
    sep = np.mod(c2 - c1, 1.0)
    sep_nom = (n2 - n1) % 1.0
    sep = sep_nom + wrap(sep - sep_nom, 1.0)
    out["sep_mean"] = float(np.mean(sep))
    out["sep_sd"] = float(np.std(sep))
    return out


# ================================================================ light curve cleaning
def detrend(t, f, width, n_iter=4):
    """-> relative residual r = f / trend - 1 (trend = binned median, low points clipped)."""
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    good = np.ones(t.size, bool)
    trend = np.full(t.size, np.median(f))
    for _ in range(n_iter):
        edges = np.arange(t.min(), t.max() + width, width)
        idx = np.clip(np.searchsorted(edges, t, side="right") - 1, 0, len(edges) - 1)
        cen, med = [], []
        for k in range(len(edges)):
            sel = (idx == k) & good
            if sel.sum() >= 10:
                cen.append(float(np.median(t[sel])))
                med.append(float(np.median(f[sel])))
        if len(cen) >= 2:
            trend = np.interp(t, cen, med)
        elif len(cen) == 1:
            trend = np.full(t.size, med[0])
        r = f / trend - 1.0
        rg = r[good]
        mad = float(1.4826 * np.median(np.abs(rg - np.median(rg))))
        if not mad > 0:
            break
        good = (r > -3.0 * mad) & (r < 5.0 * mad)
    return f / trend - 1.0


def remove_harmonics(t, r, P0, n_harm=N_HARM, n_iter=4):
    """Fit const + n_harm harmonics of P0 to the points not flagged low; -> (residual, robust sd)."""
    t = np.asarray(t, float)
    r = np.asarray(r, float)
    om = 2.0 * math.pi / P0
    tt = t - t.mean()
    cols = [np.ones(t.size)]
    for k in range(1, n_harm + 1):
        cols += [np.sin(k * om * tt), np.cos(k * om * tt)]
    X = np.vstack(cols).T
    good = np.ones(t.size, bool)
    model = np.zeros(t.size)
    for _ in range(n_iter):
        if good.sum() < 5 * X.shape[1]:
            break
        beta = np.linalg.lstsq(X[good], r[good], rcond=None)[0]
        model = X @ beta
        res = r - model
        rg = res[good]
        mad = float(1.4826 * np.median(np.abs(rg - np.median(rg))))
        if not mad > 0:
            break
        good = (res > -3.0 * mad) & (res < 5.0 * mad)
    res = r - model
    rg = res[good] if good.sum() >= 10 else res
    sd = float(1.4826 * np.median(np.abs(rg - np.median(rg))))
    return res, sd


def clean_sector(t, f, P0):
    width = float(np.clip(P0, 0.5, 3.0))
    r = detrend(t, f, width)
    res, sd = remove_harmonics(t, r, P0)
    if not sd > 0:
        return None
    z = np.clip(res / sd, -ZCLIP, ZCLIP)
    return {"r": res, "z": z, "sd": sd}


# ================================================================ box search
def fold_stats(t, y, P, t_ref, nb=NB):
    ph = np.mod((np.asarray(t, float) - t_ref) / P, 1.0)
    idx = np.minimum((ph * nb).astype(int), nb - 1)
    s = np.bincount(idx, weights=y, minlength=nb)
    n = np.bincount(idx, minlength=nb).astype(float)
    return s, n


def best_box(s, n, nb=NB, widths=WIDTHS, mask=None):
    """Most significant dip box. s, n: per-bin sums of z and counts. -> dict or None.
    The box [j, j+w) must have >= MIN_PTS points, a negative mean, and be deeper than the mean of
    its two flanking boxes [j-w, j) and [j+w, j+2w) by >= SHAPE_MIN of its own depth."""
    s3 = np.concatenate([s, s, s])
    n3 = np.concatenate([n, n, n])
    C = np.concatenate([[0.0], np.cumsum(s3)])
    K = np.concatenate([[0.0], np.cumsum(n3)])
    if mask is not None:
        m3 = np.concatenate([mask, mask, mask]).astype(float)
        M = np.concatenate([[0.0], np.cumsum(m3)])
    j = np.arange(nb)
    best = None
    for w in widths:
        if 2 * w > nb:
            continue
        Sb = C[nb + j + w] - C[nb + j]
        Nb = K[nb + j + w] - K[nb + j]
        Sl = C[nb + j] - C[nb + j - w]
        Nl = K[nb + j] - K[nb + j - w]
        Sr = C[nb + j + 2 * w] - C[nb + j + w]
        Nr = K[nb + j + 2 * w] - K[nb + j + w]
        mb = Sb / np.maximum(Nb, 1.0)
        mf = (Sl + Sr) / np.maximum(Nl + Nr, 1.0)
        depth = -mb
        local = mf - mb
        snr = depth * np.sqrt(Nb)
        ok = (Nb >= MIN_PTS) & ((Nl + Nr) >= MIN_PTS) & (depth > 0) & (local >= SHAPE_MIN * depth)
        if mask is not None:
            ok &= (M[nb + j + w] - M[nb + j]) == 0
        if not ok.any():
            continue
        sc = np.where(ok, snr, -np.inf)
        k = int(np.argmax(sc))
        if best is None or sc[k] > best["snr"]:
            best = {"snr": float(sc[k]), "bin": k, "w": int(w), "z_depth": float(depth[k]),
                    "local_ratio": float(local[k] / depth[k]), "n_in": int(Nb[k])}
    return best


def period_grid(P0, sigP, baseline, nb=NB, max_steps=MAX_STEPS):
    half = max(5.0 * sigP if finite(sigP) and sigP > 0 else 0.0, 1e-6 * P0)
    step = 0.25 / nb * P0 * P0 / max(baseline, P0)
    n = int(math.ceil(2.0 * half / step)) + 1
    n = max(3, min(n, max_steps))
    return np.linspace(P0 - half, P0 + half, n)


def scan(T, Z, P0, sigP, t_ref, baseline):
    best = None
    grid = period_grid(P0, sigP, baseline)
    for P in grid:
        s, n = fold_stats(T, Z, P, t_ref)
        b = best_box(s, n)
        if b is not None and (best is None or b["snr"] > best["snr"]):
            b["P"] = float(P)
            best = b
    return best, int(grid.size)


def box_members(T, P, t_ref, b, nb=NB):
    ph = np.mod((T - t_ref) / P, 1.0)
    idx = np.minimum((ph * nb).astype(int), nb - 1)
    return np.mod(idx - b["bin"], nb) < b["w"]


def box_epoch(T, P, t_ref, b, nb=NB):
    """Time of the box centre in the cycle nearest the middle of the data."""
    phc = ((b["bin"] + b["w"] / 2.0) / nb) % 1.0
    tmid = 0.5 * (float(np.min(T)) + float(np.max(T)))
    k = round((tmid - t_ref) / P - phc)
    return t_ref + (k + phc) * P, phc


def describe_box(T, Z, R, SEC, P, t_ref, b):
    inb = box_members(T, P, t_ref, b)
    cyc = np.floor((T[inb] - t_ref) / P)
    d = {"n_cycles": int(np.unique(cyc).size),
         "depth_rel": float(-np.mean(R[inb])) if inb.any() else float("nan")}
    secs = []
    for sec in np.unique(SEC):
        sel = inb & (SEC == sec)
        if sel.sum() >= 5:
            secs.append({"sector": int(sec), "n": int(sel.sum()),
                         "snr": float(-np.mean(Z[sel]) * math.sqrt(sel.sum()))})
    d["sectors"] = secs
    d["n_sectors_dip"] = int(sum(1 for x in secs if x["snr"] >= 3.0))
    return d


# ================================================================ one star
def analyse(star, orb, P0, sigP, lcs):
    """star: dict(name, role, tic, ...); orb: Gaia orbit dict or None (anchor failed / missing);
    lcs: list of dict(sector, author, exptime, t, f). -> (record, fold rows)."""
    rec = {k: star.get(k) for k in ("name", "source_id", "tic", "G", "role", "vetted", "tce_class")}
    rec.update({"P_gaia": P0, "P_gaia_err": sigP, "n_sectors": 0, "label": "NO_DATA"})
    Ts, Zs, Rs, Ss, info = [], [], [], [], []
    for lc in lcs:
        t = np.asarray(lc["t"], float)
        f = np.asarray(lc["f"], float)
        if t.size < 100:
            continue
        c = clean_sector(t, f, P0)
        if c is None:
            continue
        Ts.append(t)
        Zs.append(c["z"])
        Rs.append(c["r"])
        Ss.append(np.full(t.size, int(lc["sector"])))
        info.append({"sector": int(lc["sector"]), "author": lc["author"], "exptime": lc.get("exptime"),
                     "n": int(t.size), "sd": c["sd"]})
    rec["sectors"] = info
    rec["n_sectors"] = len(info)
    rec["authors"] = "|".join(sorted(set(x["author"] for x in info)))
    if not Ts:
        return rec, []
    T = np.concatenate(Ts)
    Z = np.concatenate(Zs)
    R = np.concatenate(Rs)
    SEC = np.concatenate(Ss)
    t_ref = float(np.floor(np.min(T)))
    baseline = float(np.max(T) - np.min(T))
    rec["baseline_d"] = baseline
    best, n_steps = scan(T, Z, P0, sigP, t_ref, baseline)
    rec["n_period_steps"] = n_steps
    nulls = []
    for fct in NULL_FACTORS:
        nb_, _ = scan(T, Z, fct * P0, fct * sigP if finite(sigP) else sigP, t_ref, baseline)
        nulls.append(nb_["snr"] if nb_ else 0.0)
    rec["null_max"] = float(max(nulls))
    rec["null_median"] = float(np.median(nulls))
    if best is None:
        rec["label"] = "NOT_DETECTED"
        rec["snr"] = 0.0
        return rec, []
    P = best["P"]
    d = describe_box(T, Z, R, SEC, P, t_ref, best)
    T1, ph1 = box_epoch(T, P, t_ref, best)
    rec.update({"snr": best["snr"], "P_best": P, "box_bin": best["bin"], "box_w": best["w"],
                "box_phase": ph1, "local_ratio": best["local_ratio"], "n_in": best["n_in"],
                "depth_rel": d["depth_rel"], "n_cycles": d["n_cycles"],
                "n_sectors_dip": d["n_sectors_dip"], "T_dip1": T1,
                "dur_d": best["w"] / NB * P})
    det = (best["snr"] >= SNR_MIN and best["snr"] >= NULL_RATIO * rec["null_max"]
           and d["n_cycles"] >= 2)
    rec["label"] = "DETECTED" if det else "NOT_DETECTED"
    fold = []
    if not det:
        return rec, fold
    # secondary
    mask = np.zeros(NB, bool)
    for k in range(-best["w"], 2 * best["w"]):
        mask[(best["bin"] + k) % NB] = True
    s, n = fold_stats(T, Z, P, t_ref)
    b2 = best_box(s, n, mask=mask)
    sec_det = False
    if b2 is not None:
        d2 = describe_box(T, Z, R, SEC, P, t_ref, b2)
        T2, ph2 = box_epoch(T, P, t_ref, b2)
        sec_det = b2["snr"] >= max(SNR_SEC, rec["null_max"]) and d2["n_cycles"] >= 2
        rec.update({"snr2": b2["snr"], "box2_w": b2["w"], "box2_phase": ph2, "depth2_rel": d2["depth_rel"],
                    "T_dip2": T2, "sep_obs": (ph2 - ph1) % 1.0})
    rec["sec"] = "SEC_DETECTED" if sec_det else "SEC_NOT_DETECTED"
    # Gaia conjunction test
    if orb is None:
        rec["phase"] = "UNTESTABLE"
    else:
        sig_obs1 = P * max(best["w"] / (4.0 * NB), 0.5 / NB)
        pr = predict_conj(orb, T1)
        zs = {}
        for c in ("c1", "c2"):
            zs[c] = pr["oc_%s" % c] / math.hypot(pr["sd_%s" % c], sig_obs1)
        bestc = min(zs, key=lambda c: abs(zs[c]))
        cover = sum(2.0 * Z_PHASE * math.hypot(pr["sd_%s" % c], sig_obs1) for c in ("c1", "c2")) / P
        rec.update({"circular": pr["circular"], "oc1_d": pr["oc_c1"], "sd1_d": pr["sd_c1"],
                    "oc2_d": pr["oc_c2"], "sd2_d": pr["sd_c2"], "z_c1": zs["c1"], "z_c2": zs["c2"],
                    "phase_map": bestc, "phase_z": zs[bestc], "p_chance": float(min(1.0, cover)),
                    "cycles_from_gaia": pr["cycles_c1"],
                    "phase": "PHASE_MATCH" if abs(zs[bestc]) <= Z_PHASE else "PHASE_MISMATCH"})
        if sec_det:
            sig_ph1 = sig_obs1 / P
            sig_ph2 = max(b2["w"] / (4.0 * NB), 0.5 / NB)
            sd = math.sqrt(pr["sep_sd"] ** 2 + sig_ph1 ** 2 + sig_ph2 ** 2)
            so = rec["sep_obs"]
            za = (so - pr["sep_mean"]) / sd
            zb = (so - (1.0 - pr["sep_mean"])) / sd
            zsep = za if abs(za) <= abs(zb) else zb
            rec.update({"sep_gaia": pr["sep_mean"], "sep_gaia_sd": pr["sep_sd"], "sep_z": zsep,
                        "sep": "SEP_MATCH" if abs(zsep) <= Z_PHASE else "SEP_MISMATCH"})
        else:
            rec["sep"] = "UNTESTABLE"
    # binned fold for the record (phase relative to the primary box centre)
    sr, nr = fold_stats(T, R, P, t_ref)
    shift = int(round(ph1 * NB))
    for k in range(NB):
        kk = (k + shift) % NB
        if nr[kk] > 0:
            fold.append({"name": star.get("name"), "tic": star.get("tic"),
                         "phase": ((k / NB) + 0.5 / NB + 0.5) % 1.0 - 0.5,
                         "rel_flux": float(sr[kk] / nr[kk]), "n": int(nr[kk])})
    return rec, fold


# ================================================================ inputs
def select_stars(rows):
    out = []
    for r in rows:
        if str(r.get("status", "")).strip() != "OK":
            continue
        tic = str(r.get("tic", "")).strip()
        if not re.fullmatch(r"\d+(\.0+)?", tic):
            continue
        tic_i = int(float(tic))
        sid = str(r.get("source_id", "")).strip()
        cat = truthy(r.get("vsx_eclipsing")) or truthy(r.get("gaia_eb")) or truthy(r.get("simbad_eb"))
        toi = str(r.get("toi", "")).strip()
        role = "control" if cat else ("toi" if toi else "target")
        vetted = "new_eb" if tic_i in NEW_EB else ("known_hand" if tic_i in KNOWN_HAND else "")
        name = str(r.get("simbad_main", "") or "").strip() or ("Gaia DR3 " + sid)
        out.append({"source_id": sid, "tic": tic_i, "G": fnum(r.get("G")), "name": name,
                    "ra": fnum(r.get("ra")), "dec": fnum(r.get("dec")),
                    "P_screen": fnum(r.get("P_gaia")), "P_screen_err": fnum(r.get("P_gaia_err")),
                    "role": role, "vetted": vetted, "tce_class": str(r.get("tce_class", "")).strip()})
    out.sort(key=lambda s: (s["G"] if finite(s["G"]) else 99.0, s["source_id"]))
    return out


def orbit_from_row(r):
    return {"P": fnum(r.get("period")), "P_err": fnum(r.get("period_error")),
            "e": fnum(r.get("eccentricity")), "e_err": fnum(r.get("eccentricity_error"), 0.0),
            "omega": fnum(r.get("arg_periastron")), "omega_err": fnum(r.get("arg_periastron_error"), 0.0),
            "Tp": fnum(r.get("t_periastron")), "Tp_err": fnum(r.get("t_periastron_error"), 0.0),
            "type": str(r.get("nss_solution_type", "")).strip().strip('"')}


def anchor_ok(orb, P_screen):
    return (orb is not None and finite(orb["P"]) and finite(P_screen)
            and abs(orb["P"] - P_screen) <= 1e-9 * P_screen and finite(orb["Tp"]))


def pick_sectors(entries, max_lc=MAX_LC):
    """entries: (sector, rank_key, index, author, exptime). One per sector (best rank), then at most
    max_lc sectors spread evenly over the sorted list."""
    best = {}
    for sec, key, i, author, exptime in entries:
        if sec not in best or key < best[sec][0]:
            best[sec] = (key, i, author, exptime)
    secs = sorted(best)
    if len(secs) > max_lc:
        idx = sorted(set(int(round(x)) for x in np.linspace(0, len(secs) - 1, max_lc)))
        secs = [secs[k] for k in idx]
    return [(s, best[s][1], best[s][2], best[s][3]) for s in secs]


# ================================================================ network
def http(url, data=None, timeout=180, tries=3):
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:
            last = exc
            log("HTTP retry", url[:90], a + 1, repr(exc)[:160])
            time.sleep(5 * (a + 1))
    raise RuntimeError("HTTP failed %s: %r" % (url[:90], last))


VSX_URL = "https://vsx.aavso.org/index.php?view=api.list&ra=%.6f&dec=%.6f&radius=%.6f&format=json"
VSX_RADIUS_DEG = 30.0 / 3600.0


def vsx_objects(obj):
    if not isinstance(obj, dict):
        return []
    v = obj.get("VSXObjects", {})
    v = v.get("VSXObject", []) if isinstance(v, dict) else v
    if isinstance(v, dict):
        v = [v]
    return [x for x in (v or []) if isinstance(x, dict)]


def is_eclipsing_type(vt):
    for tok in re.split(r"[+|/:\s,()]+", str(vt or "").upper()):
        if tok.startswith("E") and tok not in ("EP", "ELL", ""):
            return True
    return False


def vsx_lookup(ra, dec):
    """-> dict(vsx_names, vsx_types, vsx_eclipsing) or None if VSX could not be read."""
    if not (finite(ra) and finite(dec)):
        return None
    try:
        obj = json.loads(http(VSX_URL % (ra, dec, VSX_RADIUS_DEG), timeout=90).decode("utf-8", "replace"))
    except Exception as exc:
        log("VSX failed", ra, dec, repr(exc)[:160])
        return None
    objs = vsx_objects(obj)
    return {"vsx_names": "|".join(str(o.get("Name", "")) for o in objs),
            "vsx_types": "|".join(str(o.get("VariabilityType", "")) for o in objs),
            "vsx_eclipsing": any(is_eclipsing_type(o.get("VariabilityType")) for o in objs)}


def fetch_orbits(ids):
    q = ("SELECT source_id, " + ", ".join(ORBIT_COLS) + " FROM gaiadr3.nss_two_body_orbit "
         "WHERE source_id IN (%s)" % ",".join(str(int(i)) for i in ids))
    body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                   "QUERY": q}).encode()
    errs = []
    for name, url in TAP_URLS:
        try:
            text = http(url, data=body).decode("utf-8", "replace")
            rows = {}
            for r in csv.DictReader(io.StringIO(text)):
                sid = str(r.get("source_id", "")).strip().strip('"')
                if sid:
                    rows[sid] = r
            if rows:
                return rows, name, errs
            errs.append("%s: no rows (%s)" % (name, text[:120].replace("\n", " ")))
        except Exception as exc:
            errs.append("%s: %s" % (name, repr(exc)[:200]))
    return {}, "none", errs


def tess_lightcurves(tic, cache_dir, max_lc=MAX_LC):
    import lightkurve as lk
    sr = None
    for a in range(3):
        try:
            sr = lk.search_lightcurve("TIC %d" % int(tic), mission="TESS")
            break
        except Exception as exc:
            log("search retry TIC", tic, a + 1, repr(exc)[:160])
            time.sleep(10 * (a + 1))
    if sr is None or len(sr) == 0:
        return [], 0
    tab = sr.table
    entries = []
    for i in range(len(sr)):
        author = str(tab["author"][i])
        if author not in AUTHOR_RANK:
            continue
        exptime = fnum(np.asarray(tab["exptime"])[i])
        if author == "SPOC" and exptime < 100:
            continue
        m = re.search(r"(\d+)", str(tab["mission"][i]))
        if not m:
            continue
        entries.append((int(m.group(1)), (AUTHOR_RANK[author], abs(exptime - 120.0)), i, author, exptime))
    picks = pick_sectors(entries, max_lc)
    out = []
    for sec, i, author, exptime in picks:
        try:
            lc = sr[i].download(download_dir=cache_dir, quality_bitmask="default")
            lc = lc.remove_nans()
            t = np.asarray(lc.time.value, float)
            f = np.asarray(lc.flux.value, float)
            ok = np.isfinite(t) & np.isfinite(f) & (f > 0)
            if ok.sum() < 100:
                continue
            out.append({"sector": sec, "author": author, "exptime": exptime,
                        "t": t[ok], "f": f[ok] / np.median(f[ok])})
        except Exception as exc:
            log("download failed TIC", tic, "sector", sec, author, repr(exc)[:160])
    return out, len(set(e[0] for e in entries))


# ================================================================ grading
def grade(recs, truncated):
    def frac_ok(num, den, thr):
        return den > 0 and num >= thr * den
    ctrl = [r for r in recs if r["role"] == "control" and r.get("n_sectors", 0) > 0]
    cdet = [r for r in ctrl if r["label"] == "DETECTED"]
    F0 = "CONTROLS_OK" if frac_ok(len(cdet), len(ctrl), 0.8) else "CONTROLS_FAIL"
    ph = [r for r in cdet if r.get("phase") in ("PHASE_MATCH", "PHASE_MISMATCH")]
    pm = [r for r in ph if r["phase"] == "PHASE_MATCH"]
    F1 = ("UNTESTABLE" if not ph else
          ("GAIA_PHASES_OK" if frac_ok(len(pm), len(ph), 0.8) else "GAIA_PHASES_POOR"))
    split = {}
    for lab, sel in (("eccentric", lambda r: not r.get("circular")), ("circular", lambda r: bool(r.get("circular")))):
        a = [r for r in ph if sel(r)]
        split[lab] = {"n": len(a), "match": sum(1 for r in a if r["phase"] == "PHASE_MATCH")}
    sp = [r for r in cdet if r.get("sep") in ("SEP_MATCH", "SEP_MISMATCH")]
    tg = [r for r in recs if r["role"] == "target" and r["vetted"] == "" and r.get("n_sectors", 0) > 0]
    matched = [r for r in tg if r["label"] == "DETECTED" and r.get("phase") == "PHASE_MATCH"]
    cand = [r for r in matched if r.get("vsx_eclipsing") is not True]
    in_vsx = [r for r in matched if r.get("vsx_eclipsing") is True]
    other = [r for r in tg if r["label"] == "DETECTED" and r.get("phase") != "PHASE_MATCH"]
    new = [r for r in recs if r["vetted"] == "new_eb"]
    F3 = ("BOTH_RECOVERED" if new and all(r["label"] == "DETECTED" and r.get("phase") == "PHASE_MATCH" for r in new)
          else "NOT_ALL_RECOVERED")
    nd = [r for r in recs if r.get("n_sectors", 0) > 0]
    return {
        "truncated": truncated,
        "F0": {"label": F0, "n_controls_with_data": len(ctrl), "n_detected": len(cdet)},
        "F1": {"label": F1, "n_tested": len(ph), "n_match": len(pm), "split": split,
               "sep_tested": len(sp), "sep_match": sum(1 for r in sp if r["sep"] == "SEP_MATCH")},
        "F2": {"n_targets_with_data": len(tg), "n_candidates": len(cand),
               "candidates": [{"name": r["name"], "tic": r["tic"], "G": r["G"], "P": r.get("P_best"),
                               "snr": r.get("snr"), "depth_rel": r.get("depth_rel"),
                               "phase_z": r.get("phase_z"), "p_chance": r.get("p_chance"),
                               "sec": r.get("sec"), "sep": r.get("sep"), "authors": r.get("authors"),
                               "vsx_checked": r.get("vsx_eclipsing") is not None,
                               "vsx_names": r.get("vsx_names")}
                              for r in cand],
               "n_phase_matched_already_in_vsx": len(in_vsx),
               "already_in_vsx": [{"name": r["name"], "tic": r["tic"], "vsx_names": r.get("vsx_names"),
                                   "vsx_types": r.get("vsx_types")} for r in in_vsx],
               "detected_phase_not_matched": [{"name": r["name"], "tic": r["tic"], "phase": r.get("phase"),
                                               "phase_z": r.get("phase_z"), "snr": r.get("snr")} for r in other],
               "ge1": len(cand) >= 1, "ge3": len(cand) >= 3, "ge5": len(cand) >= 5},
        "F3": {"label": F3, "rows": [{"name": r["name"], "label": r["label"], "phase": r.get("phase"),
                                      "phase_z": r.get("phase_z")} for r in new]},
        "noise": {"n_with_data": len(nd),
                  "null_max_ge_snr_min": sum(1 for r in nd if r.get("null_max", 0) >= SNR_MIN),
                  "targets_not_detected": sum(1 for r in tg if r["label"] == "NOT_DETECTED")},
        "known_hand": [{"name": r["name"], "tic": r["tic"], "label": r["label"], "phase": r.get("phase")}
                       for r in recs if r["vetted"] == "known_hand"],
        "toi": [{"name": r["name"], "tic": r["tic"], "label": r["label"], "phase": r.get("phase")}
                for r in recs if r["role"] == "toi"],
    }


# ================================================================ self-test
def synth_eb(t, P, e, omega, Tp_btjd, d1=0.03, d2=0.02, s=0.04, noise=0.002, spot=0.01, ell=0.0, seed=1):
    rng = np.random.default_rng(seed)
    f = np.ones(t.size)
    if d1 > 0 or d2 > 0:
        c1, c2 = conjunction_phases(e, omega)
        for c, d in ((c1, d1), (c2, d2)):
            tc0 = Tp_btjd + c * P
            n = np.round((t - tc0) / P)
            f -= d * np.exp(-0.5 * ((t - (tc0 + n * P)) / s) ** 2)
    f *= 1.0 + spot * np.sin(2 * math.pi * t / P + 0.3 * math.floor(t[0] / 100.0))
    f *= 1.0 - ell * np.cos(4 * math.pi * (t - Tp_btjd) / P)
    return f + rng.normal(0, noise, t.size)


def self_test():
    ok = True
    c1, c2 = conjunction_phases(0.0, 0.0)
    g1 = abs(c1 - 0.25) < 1e-9 and abs(c2 - 0.75) < 1e-9
    c1, c2 = conjunction_phases(0.076, 342.95)
    g2 = abs(c1 - 0.2738) < 0.002 and abs(c2 - 0.8201) < 0.002
    log("geometry", "PASS" if g1 and g2 else "FAIL", c1, c2)
    ok &= g1 and g2
    # HD 250735 (not blind; documented in the pre-registration): SPOC epoch vs Gaia SB2C orbit
    orb = {"P": 5.895935077280673, "P_err": 0.00018169096, "e": float("nan"), "omega": float("nan"),
           "Tp": -1.6427050598921045, "Tp_err": 0.010175885}
    pr = predict_conj(orb, 2475.950533)
    zz = min(abs(pr["oc_c1"]) / pr["sd_c1"], abs(pr["oc_c2"]) / pr["sd_c2"])
    g3 = zz <= 3.0
    log("HD 250735 circular convention", "PASS" if g3 else "FAIL", json.dumps(pr))
    ok &= g3
    P, e, w, Tp = 4.3, 0.10, 60.0, 400.0
    orb = {"P": P + 2e-5, "P_err": 5e-5, "e": e, "e_err": 0.005, "omega": w, "omega_err": 3.0,
           "Tp": Tp - GAIA_REF_BTJD, "Tp_err": 0.02}
    cases = []
    for kind in ("eb", "ellipsoidal", "noise"):
        lcs = []
        for k, t0 in enumerate((1500.0, 2200.0)):
            t = np.arange(t0, t0 + 26.0, 10.0 / 1440.0)
            if kind == "eb":
                f = synth_eb(t, P, e, w, Tp, seed=k + 3)
            elif kind == "ellipsoidal":
                f = synth_eb(t, P, e, w, Tp, d1=0.0, d2=0.0, spot=0.0, ell=0.006, seed=k + 5)
            else:
                f = synth_eb(t, P, e, w, Tp, d1=0.0, d2=0.0, spot=0.0, seed=k + 7)
                f[np.arange(50, f.size, 997)] -= 0.05      # isolated low outliers
            lcs.append({"sector": k + 1, "author": "QLP", "exptime": 600.0, "t": t, "f": f})
        rec, fold = analyse({"name": "synthetic-" + kind, "role": "selftest", "tic": 0, "vetted": ""},
                            orb, P + 2e-5, 5e-5, lcs)
        cases.append((kind, rec))
        log("synthetic", kind, json.dumps({k: rec.get(k) for k in (
            "label", "snr", "null_max", "P_best", "phase", "phase_z", "sec", "sep", "sep_z",
            "depth_rel", "n_cycles")}, default=str))
    eb = cases[0][1]
    g4 = (eb["label"] == "DETECTED" and eb.get("phase") == "PHASE_MATCH"
          and eb.get("sec") == "SEC_DETECTED" and eb.get("sep") == "SEP_MATCH"
          and abs(eb.get("depth_rel", 0) - 0.03) < 0.015)
    g5 = cases[1][1]["label"] == "NOT_DETECTED"
    g6 = cases[2][1]["label"] == "NOT_DETECTED"
    log("synthetic EB", "PASS" if g4 else "FAIL")
    log("synthetic ellipsoidal (must not detect)", "PASS" if g5 else "FAIL")
    log("synthetic noise + outliers (must not detect)", "PASS" if g6 else "FAIL")
    ok &= g4 and g5 and g6
    log("self-test", "PASS" if ok else "FAIL")
    return bool(ok)


# ================================================================ driver
def jclean(o):
    if isinstance(o, dict):
        return {k: jclean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jclean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        x = float(o)
        return x if math.isfinite(x) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


STAR_COLS = ["name", "source_id", "tic", "G", "role", "vetted", "tce_class", "orbit_type",
             "orbit_anchor", "P_gaia", "P_gaia_err", "e_gaia", "omega_gaia", "n_sectors_available",
             "n_sectors", "authors", "baseline_d", "label", "snr", "null_max", "null_median", "P_best",
             "box_phase", "box_w", "dur_d", "depth_rel", "local_ratio", "n_cycles", "n_sectors_dip",
             "T_dip1", "phase", "phase_map", "phase_z", "oc1_d", "sd1_d", "oc2_d", "sd2_d", "p_chance",
             "circular", "sec", "snr2", "depth2_rel", "sep_obs", "sep_gaia", "sep_gaia_sd", "sep_z", "sep",
             "vsx_eclipsing", "vsx_names", "vsx_types", "error"]


def write_csv(path, rows, keys):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: jclean(r.get(k, "")) for k in keys})


def run(args):
    os.makedirs(args.out_dir, exist_ok=True)
    t_start = time.time()
    meta = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "screen_url": SCREEN_URL}
    text = http(SCREEN_URL).decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    meta["screen_rows"] = len(rows)
    meta["screen_rows_ok"] = len(rows) == SCREEN_ROWS
    stars = select_stars(rows)
    meta["n_selected"] = len(stars)
    meta["roles"] = {k: sum(1 for s in stars if s["role"] == k) for k in ("control", "toi", "target")}
    log("selected", len(stars), json.dumps(meta["roles"]))
    tap, src, errs = fetch_orbits([s["source_id"] for s in stars])
    meta.update({"orbit_source": src, "orbit_errors": errs, "n_orbits": len(tap)})
    log("orbits", src, len(tap), errs)
    recs, folds = [], []
    truncated = False
    jl = open(os.path.join(args.out_dir, "ffiscan_stars.jsonl"), "w")
    for i, s in enumerate(stars):
        if (time.time() - t_start) / 60.0 > args.max_minutes:
            truncated = True
            log("time limit reached; stopping before star", i)
            break
        row = tap.get(s["source_id"])
        orb = orbit_from_row(row) if row else None
        anc = anchor_ok(orb, s["P_screen"])
        P0 = orb["P"] if anc else s["P_screen"]
        sigP = orb["P_err"] if anc else s["P_screen_err"]
        tmp = tempfile.mkdtemp(prefix="lk_")
        try:
            try:
                lcs, n_av = tess_lightcurves(s["tic"], tmp)
            except Exception as exc:
                log("lightkurve failed", s["name"], repr(exc)[:200])
                lcs, n_av = [], 0
            try:
                rec, fold = analyse(s, orb if anc else None, P0, sigP, lcs)
            except Exception as exc:
                log("analysis failed", s["name"], repr(exc)[:300])
                rec = {k: s.get(k) for k in ("name", "source_id", "tic", "G", "role", "vetted", "tce_class")}
                rec.update({"label": "ERROR", "error": repr(exc)[:300], "n_sectors": 0})
                fold = []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rec.update({"orbit_type": orb["type"] if orb else "", "orbit_anchor": bool(anc),
                    "e_gaia": orb["e"] if orb else None, "omega_gaia": orb["omega"] if orb else None,
                    "n_sectors_available": n_av})
        if rec.get("label") == "DETECTED" and s["role"] != "control":
            v = vsx_lookup(s.get("ra"), s.get("dec"))
            if v is None:
                rec["vsx_eclipsing"] = None
            else:
                rec.update(v)
        recs.append(rec)
        folds += fold
        jl.write(json.dumps(jclean(rec)) + "\n")
        jl.flush()
        log("[%d/%d]" % (i + 1, len(stars)), s["name"], s["role"], s["vetted"], rec["label"],
            json.dumps(jclean({k: rec.get(k) for k in ("snr", "null_max", "phase", "phase_z", "sec", "sep",
                                                          "depth_rel", "authors")})))
    jl.close()
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    grades = grade(recs, truncated)
    summary = {"meta": meta, "grades": grades,
               "params": {"NB": NB, "WIDTHS": WIDTHS, "MIN_PTS": MIN_PTS, "SHAPE_MIN": SHAPE_MIN,
                          "ZCLIP": ZCLIP, "SNR_MIN": SNR_MIN, "NULL_RATIO": NULL_RATIO, "SNR_SEC": SNR_SEC,
                          "Z_PHASE": Z_PHASE, "MAX_LC": MAX_LC, "MAX_STEPS": MAX_STEPS, "N_HARM": N_HARM,
                          "NULL_FACTORS": NULL_FACTORS}}
    with open(os.path.join(args.out_dir, "ffiscan_summary.json"), "w") as fh:
        json.dump(jclean(summary), fh, indent=1)
    write_csv(os.path.join(args.out_dir, "ffiscan_stars.csv"), recs, STAR_COLS)
    write_csv(os.path.join(args.out_dir, "ffiscan_folds.csv"), folds, ["name", "tic", "phase", "rel_flux", "n"])
    print(json.dumps(jclean({k: (v if k != "F2" else {kk: vv for kk, vv in v.items()
                                                       if kk != "detected_phase_not_matched"})
                             for k, v in grades.items() if k not in ("known_hand", "toi")})))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--max-minutes", type=float, default=300.0)
    a = ap.parse_args(argv)
    if a.self_test:
        return 0 if self_test() else 3
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
