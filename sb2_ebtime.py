# SPDX-License-Identifier: Apache-2.0
"""sb2_ebtime 0.1.0 - eclipse times of Gaia DR3 double-lined binaries in TESS, compared with
Gaia's own orbits (period, secondary-eclipse phase, conjunction times) and with Gaia's own
resolved epoch photometry.

MV2, Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.
Pre-registration: findings/2026-11-23-sb2-new-ebs-prereg.md in
https://github.com/munimtechnologies/gaia-orbit-transits

For every star in the config:
  1. Gaia DR3 orbit (ESA TAP; falls back to the values written in the config, flagged).
  2. Every TESS light curve lightkurve finds (SPOC 120 s first, then TESS-SPOC, then QLP; one
     per sector), detrended per sector with an iteratively clipped binned median.
  3. Eclipse events found without any ephemeris (runs of points below threshold), each timed
     by a Gaussian-dip fit (grid in centre and width, linear in depth), with a chi-square
     profile error.
  4. Events grouped into two eclipse families on Gaia's period (refined on a grid limited to
     +-6 sigma of Gaia's period, so no cycle-count alias is allowed), then a joint linear
     ephemeris t = T_A + n P + [B] D.
  5. Tests: E1 TESS period vs Gaia period; E2 displacement of the secondary eclipse from phase
     0.5 vs Gaia's e and omega; E3 TESS conjunction times vs Gaia's t_periastron (eccentric
     solutions only); E4 Gaia's own G-band epochs: are the faint epochs inside predicted
     eclipses?
"""
import argparse
import csv
import io
import json
import math
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

import numpy as np

VERSION = "0.1.0"
SEED = 20261123
GAIA_TO_BTJD = 2455197.5 - 2457000.0      # Gaia epoch time (BJD_TCB - 2455197.5) -> BTJD
GAIA_REF_BTJD = 2457389.0 - 2457000.0     # nss t_periastron is days from JD 2457389.0
G_ZP = 25.6874
TAP_URL = "https://gea.esac.esa.int/tap-server/tap/sync"
DATALINK_URL = "https://gea.esac.esa.int/data-server/data"
UA = "gaia-orbit-transits/sb2_ebtime (MV2, Munim, Inc.; open research)"
DETREND_BIN = 0.5
MIN_DEPTH = 0.004
Z_AGREE = 3.0
MIN_ERR = 0.0005
PHASE_FLOOR = 0.002   # systematic floor on the secondary-eclipse phase (apsidal motion, timing)
AUTHOR_RANK = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}
ORBIT_COLS = ["period", "period_error", "eccentricity", "eccentricity_error", "arg_periastron",
              "arg_periastron_error", "t_periastron", "t_periastron_error", "nss_solution_type"]


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


# ================================================================ orbit geometry
def true_to_phase(nu, e):
    """True anomaly (rad) -> fraction of the period after periastron, in [0, 1)."""
    E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0),
                         math.sqrt(1.0 + e) * math.cos(nu / 2.0))
    M = E - e * math.sin(E)
    return (M / (2.0 * math.pi)) % 1.0


def conjunction_phases(e, omega_deg):
    """Phases after periastron of the two conjunctions: c1 at nu = 90 deg - omega (the star the
    orbit's omega belongs to is farthest from us), c2 at nu = 270 deg - omega."""
    w = math.radians(omega_deg)
    return true_to_phase(math.pi / 2.0 - w, e), true_to_phase(1.5 * math.pi - w, e)


def circ_dist(a, b):
    d = (np.asarray(a, float) - b) % 1.0
    return np.minimum(d, 1.0 - d)


# ================================================================ light curves
def detrend(t, f, width=DETREND_BIN, n_iter=4):
    """-> (relative residual r = f / trend - 1, robust scatter). Trend = binned median of the
    points not flagged low, interpolated; eclipses are clipped iteratively."""
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    good = np.ones(t.size, bool)
    trend = np.full(t.size, np.median(f))
    mad = float("nan")
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
    return f / trend - 1.0, mad


def find_events(t, r, mad, min_depth=MIN_DEPTH, join_gap=0.05, min_pts=4):
    """Runs of points below -max(min_depth, 6 mad); -> list of index arrays."""
    thr = -max(min_depth, 6.0 * mad if math.isfinite(mad) else min_depth)
    low = np.where(np.asarray(r) < thr)[0]
    groups, cur = [], []
    for i in low:
        if cur and t[i] - t[cur[-1]] > join_gap:
            groups.append(cur)
            cur = []
        cur.append(int(i))
    if cur:
        groups.append(cur)
    return [np.array(g) for g in groups if len(g) >= min_pts]


def fit_minimum(t, r, tc0, half_win, n_tc=241):
    """Gaussian dip r = c - d exp(-(t-tc)^2 / 2 s^2) on |t - tc0| <= half_win.
    -> dict(tc, tc_err, depth, fwhm, n, ok) or None."""
    t = np.asarray(t, float)
    r = np.asarray(r, float)
    sel = np.abs(t - tc0) <= half_win
    tt, rr = t[sel], r[sel]
    if tt.size < 8:
        return None
    tcs = np.linspace(tc0 - half_win / 2.0, tc0 + half_win / 2.0, n_tc)
    sigs = half_win * np.array([0.03, 0.045, 0.06, 0.08, 0.1, 0.13, 0.16, 0.2, 0.25, 0.32])
    rc = rr - rr.mean()
    ss = float(rc @ rc)
    prof = np.full(n_tc, ss)
    best = (ss, tc0, sigs[0], 0.0)
    for s in sigs:
        G = np.exp(-0.5 * ((tt[None, :] - tcs[:, None]) / s) ** 2)
        gc = G - G.mean(axis=1)[:, None]
        vg = (gc * gc).sum(axis=1)
        cg = gc @ rc
        beta = np.where(vg > 0, cg / np.where(vg > 0, vg, 1.0), 0.0)
        c2 = np.where(beta < 0, ss - beta * cg, ss)
        prof = np.minimum(prof, c2)
        j = int(np.argmin(c2))
        if c2[j] < best[0]:
            best = (float(c2[j]), float(tcs[j]), float(s), float(-beta[j]))
    c2min, tc, s, depth = best
    if depth <= 0:
        return None
    var = c2min / max(tt.size - 4, 1)
    inside = tcs[prof <= c2min + var]
    step = tcs[1] - tcs[0]
    err = max((inside.max() - inside.min()) / 2.0 if inside.size else step, step / 2.0)
    n_left = int(((tt > tc - 1.5 * s) & (tt < tc)).sum())
    n_right = int(((tt > tc) & (tt < tc + 1.5 * s)).sum())
    edge = abs(tc - tc0) > 0.98 * half_win / 2.0
    return {"tc": tc, "tc_err": float(err), "depth": depth, "fwhm": 2.3548 * s,
            "n": int(tt.size), "n_left": n_left, "n_right": n_right,
            "ok": bool(n_left >= 3 and n_right >= 3 and not edge)}


def time_events(t, r, mad):
    out = []
    for g in find_events(t, r, mad):
        span = float(t[g[-1]] - t[g[0]])
        k = g[int(np.argmin(r[g]))]
        half_win = max(0.12, 1.5 * span + 0.05)
        fit = fit_minimum(t, r, float(t[k]), half_win)
        if fit is None:
            continue
        fit["depth_obs"] = float(-np.min(r[g]))
        out.append(fit)
    # drop duplicates (two runs timed to the same minimum)
    out.sort(key=lambda d: d["tc"])
    dedup = []
    for ev in out:
        if dedup and abs(ev["tc"] - dedup[-1]["tc"]) < 0.5 * max(ev["fwhm"], dedup[-1]["fwhm"]):
            if ev["depth_obs"] > dedup[-1]["depth_obs"]:
                dedup[-1] = ev
            continue
        dedup.append(ev)
    return dedup


# ================================================================ ephemeris
def refine_period(times, P0, sigP0, baseline):
    """Grid over P0 +- max(6 sigma, 2e-5 P0); score = |sum e^{2 pi i phi}|^2 + |sum e^{4 pi i phi}|^2."""
    times = np.asarray(times, float)
    if times.size < 3 or baseline <= 0:
        return P0
    half = max(6.0 * sigP0 if math.isfinite(sigP0) else 0.0, 2e-5 * P0)
    step = max(0.001 * P0 * P0 / baseline, 1e-7)
    grid = np.arange(P0 - half, P0 + half + step / 2.0, step)
    t0 = times.min()
    ph = ((times[None, :] - t0) / grid[:, None]) % 1.0
    s1 = np.abs(np.exp(2j * np.pi * ph).sum(axis=1)) ** 2
    s2 = np.abs(np.exp(4j * np.pi * ph).sum(axis=1)) ** 2
    return float(grid[int(np.argmax(s1 + s2))])


def assign_groups(times, depths, P):
    """-> labels array: 'A' (family of the deepest event), 'B' (the other), '' (neither)."""
    times = np.asarray(times, float)
    depths = np.asarray(depths, float)
    ref = times[int(np.argmax(depths))]
    ph = ((times - ref) / P) % 1.0
    A = circ_dist(ph, 0.0) < 0.12
    lab = np.array(["A" if a else "" for a in A], dtype=object)
    rest = ~A
    if rest.sum():
        ang = 2.0 * np.pi * ph[rest]
        phiB = (math.atan2(np.sin(ang).mean(), np.cos(ang).mean()) / (2.0 * np.pi)) % 1.0
        B = (circ_dist(ph, phiB) < 0.12) & rest
        lab[B] = "B"
    return lab, ref


def fit_ephemeris(times, errs, labels, P0, ref):
    """Weighted LS t = T_A + n P + [B] D, one 5-sigma O-C clip. -> dict or None."""
    times = np.asarray(times, float)
    errs = np.maximum(np.asarray(errs, float), MIN_ERR)
    use = np.array([l in ("A", "B") for l in labels])
    isB = np.array([1.0 if l == "B" else 0.0 for l in labels])
    if use.sum() < 2:
        return None
    hasB = bool((isB[use] > 0).sum() >= 1)
    if hasB:
        dB = (((times[isB > 0] - ref) / P0) % 1.0)
        ang = 2.0 * np.pi * dB
        D0 = (math.atan2(np.sin(ang).mean(), np.cos(ang).mean()) / (2.0 * np.pi)) % 1.0 * P0
    else:
        D0 = 0.0
    n = np.round((times - ref - isB * D0) / P0)
    keep = use.copy()
    res = None
    for _ in range(2):
        cols = [np.ones(keep.sum()), n[keep]] + ([isB[keep]] if hasB else [])
        X = np.vstack(cols).T
        w = 1.0 / errs[keep] ** 2
        XtW = X.T * w
        try:
            cov = np.linalg.inv(XtW @ X)
        except np.linalg.LinAlgError:
            return None
        beta = cov @ (XtW @ times[keep])
        full = np.vstack([np.ones(times.size), n] + ([isB] if hasB else [])).T
        oc = times - full @ beta
        chi2 = float(((oc[keep] / errs[keep]) ** 2).sum())
        dof = max(int(keep.sum()) - X.shape[1], 1)
        scale = max(1.0, chi2 / dof)
        res = {"T_A": float(beta[0]), "P": float(beta[1]),
               "D": float(beta[2]) if hasB else float("nan"),
               "T_A_err": float(math.sqrt(cov[0, 0] * scale)),
               "P_err": float(math.sqrt(cov[1, 1] * scale)),
               "D_err": float(math.sqrt(cov[2, 2] * scale)) if hasB else float("nan"),
               "chi2_red": chi2 / dof, "n_used": int(keep.sum()),
               "n_A": int(((isB == 0) & keep).sum()), "n_B": int(((isB > 0) & keep).sum()),
               "rms_oc_min": float(np.sqrt(np.mean(oc[keep] ** 2)) * 1440.0), "oc": oc,
               "cycle": n}
        mad = 1.4826 * np.median(np.abs(oc[keep]))
        new_keep = use & (np.abs(oc) <= max(5.0 * mad, 5.0 * MIN_ERR))
        if new_keep.sum() == keep.sum() or new_keep.sum() < 3:
            break
        keep = new_keep
    res["clipped"] = int(use.sum() - keep.sum())
    return res


# ================================================================ Gaia predictions
def predict_from_orbit(orb, T_A, D_meas, n_draw=4000, seed=SEED):
    """Monte Carlo over Gaia's orbit errors. -> dict with sep (c2 - c1) and, if eccentric, the
    O-C of the TESS family A against each conjunction."""
    rng = random.Random(seed)
    e0, se = orb["e"], orb["e_err"]
    w0, sw = orb["omega"], orb["omega_err"]
    circular = not (math.isfinite(e0) and math.isfinite(w0))
    if circular:
        e0, se, w0, sw = 0.0, 0.0, 90.0, 0.0
    P0, sP = orb["P"], orb["P_err"] if math.isfinite(orb["P_err"]) else 0.0
    T0, sT = orb["Tp"], orb["Tp_err"] if math.isfinite(orb["Tp_err"]) else 0.0
    seps, oc1, oc2 = [], [], []
    for _ in range(n_draw):
        e = min(max(rng.gauss(e0, se or 0.0), 0.0), 0.95)
        w = rng.gauss(w0, sw or 0.0)
        P = rng.gauss(P0, sP)
        Tp = rng.gauss(T0, sT) + GAIA_REF_BTJD
        c1, c2 = conjunction_phases(e, w)
        seps.append((c2 - c1) % 1.0)
        if not circular and math.isfinite(Tp):
            for c, acc in ((c1, oc1), (c2, oc2)):
                tc = Tp + c * P
                k = round((T_A - tc) / P)
                acc.append(T_A - (tc + k * P))
    seps = np.array(seps)
    out = {"circular": circular, "sep_mean": float(seps.mean()), "sep_sd": float(seps.std()),
           "disp_mean": float(np.abs(seps - 0.5).mean()), "disp_sd": float(np.abs(seps - 0.5).std())}
    if oc1:
        for name, acc in (("c1", oc1), ("c2", oc2)):
            a = np.array(acc)
            out["oc_A_%s_d" % name] = float(a.mean())
            out["oc_A_%s_sd" % name] = float(a.std())
    return out


def grade_star(eph, orb, pred, P_gaia_err):
    g = {}
    if eph is None:
        return {"E1": "UNTESTABLE", "E2": "UNTESTABLE", "E3": "UNTESTABLE"}
    z1 = (eph["P"] - orb["P"]) / math.hypot(eph["P_err"], P_gaia_err if math.isfinite(P_gaia_err) else 0.0)
    g["E1_z"] = z1
    g["E1"] = "PERIOD_AGREES" if abs(z1) <= Z_AGREE else "PERIOD_DIFFERS"
    if eph["n_B"] >= 2 and math.isfinite(eph["D"]):
        dphi = (eph["D"] / eph["P"]) % 1.0
        sd = eph["D_err"] / eph["P"]
        disp = abs(dphi - 0.5)
        z2 = (disp - pred["disp_mean"]) / math.sqrt(sd ** 2 + pred["disp_sd"] ** 2 + PHASE_FLOOR ** 2)
        g.update({"dphi": dphi, "dphi_err": sd, "disp_tess": disp, "disp_gaia": pred["disp_mean"],
                  "disp_gaia_sd": pred["disp_sd"], "E2_z": z2,
                  "E2": "SEC_PHASE_AGREES" if abs(z2) <= Z_AGREE else "SEC_PHASE_DIFFERS"})
    else:
        g["E2"] = "UNTESTABLE"
    if pred.get("circular") or "oc_A_c1_d" not in pred:
        g["E3"] = "UNTESTABLE"
    else:
        zs = {}
        for c in ("c1", "c2"):
            zs[c] = pred["oc_A_%s_d" % c] / math.hypot(pred["oc_A_%s_sd" % c], eph["T_A_err"])
        best = min(zs, key=lambda c: abs(zs[c]))
        g.update({"E3_mapping": "A=" + best, "E3_z": zs[best], "E3_z_other": zs["c2" if best == "c1" else "c1"],
                  "E3_oc_d": pred["oc_A_%s_d" % best],
                  "E3": "TIMES_AGREE" if abs(zs[best]) <= Z_AGREE else "TIMES_DIFFER"})
    return g


# ================================================================ Gaia epochs
def parse_epoch_text(text):
    """Gaia DR3 epoch photometry CSV (long or wide format) -> list of (t_gaia, mag, rej_phot)."""
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return []
    rows = list(csv.reader(lines))
    head = [h.strip().strip('"').lower() for h in rows[0]]
    out = []
    if "g_transit_time" in head:
        def arr(s):
            s = str(s or "").strip().strip('"').strip("[]()").strip()
            return [fnum(p) for p in re.split(r"[,\s]+", s) if p != ""] if s else []
        for row in rows[1:]:
            r = dict(zip(head, row))
            t = arr(r.get("g_transit_time"))
            m = arr(r.get("g_transit_mag"))
            if len(m) != len(t):
                fl = arr(r.get("g_transit_flux"))
                m = [(-2.5 * math.log10(x) + G_ZP) if x > 0 else float("nan") for x in fl]
            for ti, mi in zip(t, m):
                out.append((ti, mi, False))
        return out
    tcol = next((c for c in ("time", "obs_time", "g_obs_time") if c in head), None)
    if tcol is None:
        return []
    for row in rows[1:]:
        r = dict(zip(head, row))
        if str(r.get("band", "G")).strip().strip('"').upper() != "G":
            continue
        m = fnum(r.get("mag"))
        if not math.isfinite(m):
            fl = fnum(r.get("flux"))
            m = -2.5 * math.log10(fl) + G_ZP if fl > 0 else float("nan")
        out.append((fnum(r.get(tcol)), m, truthy(r.get("rejected_by_photometry", ""))))
    return out


def parse_datalink(data):
    if data[:2] == b"PK":
        out = []
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                if not name.endswith("/"):
                    out += parse_epoch_text(z.read(name).decode("utf-8", "replace"))
        return out
    return parse_epoch_text(data.decode("utf-8", "replace"))


def fetch_gaia_epochs(source_id):
    tries = [
        (DATALINK_URL, urllib.parse.urlencode({
            "RETRIEVAL_TYPE": "EPOCH_PHOTOMETRY", "ID": str(source_id), "RELEASE": "Gaia DR3",
            "FORMAT": "csv", "DATA_STRUCTURE": "INDIVIDUAL", "VALID_DATA": "false",
            "USE_ZIP_ALWAYS": "true"}).encode()),
        (DATALINK_URL + "?RETRIEVAL_TYPE=EPOCH_PHOTOMETRY&ID=Gaia+DR3+%s&FORMAT=CSV&VALID_DATA=false"
         % source_id, None)]
    for url, body in tries:
        try:
            pts = parse_datalink(http(url, data=body))
        except Exception as exc:
            log("Gaia epochs failed", source_id, repr(exc)[:160])
            continue
        pts = [p for p in pts if math.isfinite(p[0]) and math.isfinite(p[1])]
        if pts:
            return pts
    return []


def binom_tail(k, n, p):
    if k <= 0:
        return 1.0
    return float(sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1)))


def gaia_epoch_test(pts, eph, fwhm):
    """E4. pts: (t_gaia, mag, rej_phot). Faint = mag > median_out + max(5 MAD, 0.02)."""
    if not pts or eph is None or not math.isfinite(fwhm):
        return {"E4": "UNTESTABLE", "n_epochs": len(pts)}
    t = np.array([p[0] for p in pts]) + GAIA_TO_BTJD
    m = np.array([p[1] for p in pts])
    ok = np.array([not p[2] for p in pts])
    t, m = t[ok], m[ok]
    P, TA = eph["P"], eph["T_A"]
    hasB = math.isfinite(eph["D"]) and eph["n_B"] >= 1
    nA = np.round((t - TA) / P)
    ocA = t - (TA + nA * P)
    sig_t = np.abs(nA) * eph["P_err"] + eph["T_A_err"]
    win = fwhm + 3.0 * sig_t
    inA = np.abs(ocA) <= win
    inB = np.zeros(t.size, bool)
    ocB = np.full(t.size, np.nan)
    if hasB:
        nB = np.round((t - TA - eph["D"]) / P)
        ocB = t - (TA + eph["D"] + nB * P)
        inB = np.abs(ocB) <= win + 3.0 * eph["D_err"]
    inE = inA | inB
    base = m[~inE] if (~inE).sum() >= 10 else m
    med = float(np.median(base))
    mad = float(1.4826 * np.median(np.abs(base - med)))
    thr = med + max(5.0 * mad, 0.02)
    faint = m > thr
    duty = float(np.clip(np.mean(2.0 * win / P) * (2.0 if hasB else 1.0), 0.0, 1.0))
    nf, nfi = int(faint.sum()), int((faint & inE).sum())
    p = binom_tail(nfi, nf, duty) if nf else 1.0
    if nf == 0:
        lab = "GAIA_NO_DIPS"
    elif nfi == nf and p <= 0.01:
        lab = "GAIA_DIPS_IN_ECLIPSE"
    else:
        lab = "GAIA_DIPS_ELSEWHERE" if nfi < nf else "GAIA_DIPS_IN_ECLIPSE_NOT_SIGNIFICANT"
    rows = [{"btjd": float(a), "mag": float(b), "oc_A_d": float(c), "oc_B_d": float(d),
             "in_eclipse": bool(e), "faint": bool(f)}
            for a, b, c, d, e, f in zip(t, m, ocA, ocB, inE, faint)]
    return {"E4": lab, "n_epochs": int(t.size), "median_mag": med, "mad_mag": mad,
            "n_faint": nf, "n_faint_in_eclipse": nfi, "duty": duty, "p_binom": p,
            "max_dip_mag": float(m.max() - med), "rows": rows}


# ================================================================ network
def http(url, data=None, timeout=120, tries=3):
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


def fetch_orbits(ids):
    q = ("SELECT source_id, " + ", ".join(ORBIT_COLS) + " FROM gaiadr3.nss_two_body_orbit "
         "WHERE source_id IN (%s)" % ",".join(str(int(i)) for i in ids))
    url = TAP_URL + "?" + urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL",
                                                  "FORMAT": "csv", "QUERY": q})
    text = http(url).decode("utf-8", "replace")
    out = {}
    for r in csv.DictReader(io.StringIO(text)):
        out[str(r["source_id"]).strip()] = r
    return out


def orbit_from_row(r):
    return {"P": fnum(r.get("period")), "P_err": fnum(r.get("period_error")),
            "e": fnum(r.get("eccentricity")), "e_err": fnum(r.get("eccentricity_error"), 0.0),
            "omega": fnum(r.get("arg_periastron")), "omega_err": fnum(r.get("arg_periastron_error"), 0.0),
            "Tp": fnum(r.get("t_periastron")), "Tp_err": fnum(r.get("t_periastron_error"), 0.0),
            "type": str(r.get("nss_solution_type", ""))}


def tess_lightcurves(tic, cache_dir, max_lc=16):
    import lightkurve as lk
    sr = lk.search_lightcurve("TIC %d" % int(tic), mission="TESS")
    tab = sr.table
    pick = {}
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
        sec = int(m.group(1))
        key = (AUTHOR_RANK[author], abs(exptime - 120.0))
        if sec not in pick or key < pick[sec][0]:
            pick[sec] = (key, i, author, exptime)
    out = []
    for sec in sorted(pick)[:max_lc]:
        _, i, author, exptime = pick[sec]
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
            log("TIC", tic, "sector", sec, author, int(ok.sum()), "points")
        except Exception as exc:
            log("download failed TIC", tic, "sector", sec, author, repr(exc)[:160])
    return out


# ================================================================ one star
def analyse_star(star, orb, lcs, gaia_pts):
    events = []
    sectors = []
    for lc in lcs:
        r, mad = detrend(lc["t"], lc["f"])
        evs = time_events(lc["t"], r, mad)
        for ev in evs:
            ev.update({"sector": lc["sector"], "author": lc["author"]})
        events += evs
        sectors.append({"sector": lc["sector"], "author": lc["author"], "exptime": lc["exptime"],
                        "n_points": int(lc["t"].size), "mad": mad, "n_events": len(evs),
                        "n_events_ok": sum(1 for e in evs if e["ok"])})
    good = [e for e in events if e["ok"]]
    rec = {"name": star["name"], "role": star["role"], "source_id": star["source_id"],
           "tic": star["tic"], "n_sectors": len(lcs), "n_events": len(events), "n_events_ok": len(good)}
    eph = None
    if len(good) >= 3:
        times = np.array([e["tc"] for e in good])
        base = float(times.max() - times.min())
        Pg = refine_period(times, orb["P"], orb["P_err"], base)
        labels, ref = assign_groups(times, [e["depth_obs"] for e in good], Pg)
        for e, l in zip(good, labels):
            e["family"] = l
        eph = fit_ephemeris(times, [e["tc_err"] for e in good], labels, Pg, ref)
        if eph is not None:
            for e, oc, n in zip(good, eph["oc"], eph["cycle"]):
                e["oc_min"] = float(oc) * 1440.0
                e["cycle"] = int(n)
            rec.update({"P_scan": Pg, "baseline_d": base})
            for fam in ("A", "B"):
                ev = [e for e in good if e.get("family") == fam]
                if ev:
                    rec["depth_%s" % fam] = float(np.median([e["depth_obs"] for e in ev]))
                    rec["fwhm_%s_d" % fam] = float(np.median([e["fwhm"] for e in ev]))
    pred = predict_from_orbit(orb, eph["T_A"] if eph else 0.0, eph["D"] if eph else float("nan"))
    g = grade_star(eph, orb, pred, orb["P_err"])
    fw = np.nanmean([rec.get("fwhm_A_d", np.nan), rec.get("fwhm_B_d", np.nan)]) if eph else float("nan")
    e4 = gaia_epoch_test(gaia_pts, eph, float(fw))
    if eph:
        rec.update({k: v for k, v in eph.items() if k not in ("oc", "cycle")})
    rec.update({"P_gaia": orb["P"], "P_gaia_err": orb["P_err"], "e_gaia": orb["e"],
                "omega_gaia": orb["omega"], "orbit_type": orb["type"], "pred": pred})
    rec.update(g)
    rec["gaia_epochs"] = {k: v for k, v in e4.items() if k != "rows"}
    rec["E4"] = e4["E4"]
    return rec, events, sectors, e4.get("rows", [])


# ================================================================ self-test
def synth_lc(P, e, omega, Tp_btjd, t, d1=0.08, d2=0.05, s=0.04, noise=0.001, seed=1):
    rng = np.random.default_rng(seed)
    c1, c2 = conjunction_phases(e, omega)
    f = np.ones(t.size)
    for c, d in ((c1, d1), (c2, d2)):
        tc0 = Tp_btjd + c * P
        n = np.round((t - tc0) / P)
        f -= d * np.exp(-0.5 * ((t - (tc0 + n * P)) / s) ** 2)
    f *= 1.0 + 0.002 * np.sin(2 * np.pi * t / 3.1)
    return f + rng.normal(0, noise, t.size)


def self_test():
    ok = True
    c1, c2 = conjunction_phases(0.0, 90.0)
    ok &= abs(c1) < 1e-9 or abs(c1 - 1.0) < 1e-9
    ok &= abs(((c2 - c1) % 1.0) - 0.5) < 1e-9
    c1, c2 = conjunction_phases(0.076, 342.95)
    ok &= abs(c1 - 0.2738) < 0.002 and abs(c2 - 0.8201) < 0.002
    log("geometry", "PASS" if ok else "FAIL", c1, c2)
    P, e, w, Tp = 5.3, 0.08, 30.0, 400.0 - GAIA_REF_BTJD
    lcs = []
    for k, t0 in enumerate((1500.0, 2250.0)):
        t = np.arange(t0, t0 + 25.0, 2.0 / 1440.0)
        lcs.append({"sector": k + 1, "author": "SPOC", "exptime": 120.0, "t": t,
                    "f": synth_lc(P, e, w, Tp + GAIA_REF_BTJD, t, seed=k + 3)})
    orb = {"P": P + 2e-5, "P_err": 1e-4, "e": e, "e_err": 0.005, "omega": w, "omega_err": 2.0,
           "Tp": Tp, "Tp_err": 0.01, "type": "SB2"}
    c1, c2 = conjunction_phases(e, w)
    tg = np.array([Tp + GAIA_REF_BTJD + c1 * P + k * P for k in range(-200, -190)]) - GAIA_TO_BTJD
    pts = [(float(x), 9.3, False) for x in tg] + [
        (float(x), 9.0 + 0.003 * (i % 3), False)
        for i, x in enumerate(np.linspace(1700.0, 2600.0, 40))]
    rec, events, sectors, rows = analyse_star(
        {"name": "synthetic", "role": "selftest", "source_id": "0", "tic": "0"}, orb, lcs, pts)
    ok2 = (rec.get("E1") == "PERIOD_AGREES" and abs(rec.get("P", 0) - P) < 2e-4
           and rec.get("E2") == "SEC_PHASE_AGREES" and rec.get("E3") == "TIMES_AGREE"
           and rec.get("E4") == "GAIA_DIPS_IN_ECLIPSE")
    log("synthetic EB", "PASS" if ok2 else "FAIL",
        json.dumps({k: rec.get(k) for k in ("P", "E1", "E2", "E3", "E4", "dphi", "E3_z",
                                             "n_events_ok", "depth_A", "depth_B")}, default=str))
    ok &= ok2
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
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def write_csv(path, rows, keys):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})


def run(args):
    cfg = json.load(open(args.config))
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.data_dir, exist_ok=True)
    stars = cfg["stars"]
    meta = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        tap = fetch_orbits([s["source_id"] for s in stars])
        meta["orbit_source"] = "ESA TAP gaiadr3.nss_two_body_orbit"
    except Exception as exc:
        log("TAP failed, using config orbits", repr(exc)[:200])
        tap = {}
        meta["orbit_source"] = "config fallback (transcribed 2026-11-23)"
    recs, all_events, all_sectors, all_gaia = [], [], [], []
    for s in stars:
        sid = str(s["source_id"])
        row = tap.get(sid) or s.get("orbit_fallback", {})
        orb = orbit_from_row(row)
        orb["from_tap"] = sid in tap
        log("star", s["name"], "TIC", s["tic"], "P_gaia", orb["P"], "e", orb["e"], "tap", orb["from_tap"])
        try:
            lcs = tess_lightcurves(s["tic"], os.path.join(args.data_dir, "lk"))
        except Exception as exc:
            log("lightkurve failed", s["name"], repr(exc)[:200])
            lcs = []
        pts = fetch_gaia_epochs(sid)
        log("Gaia epochs", s["name"], len(pts))
        try:
            rec, events, sectors, grows = analyse_star(s, orb, lcs, pts)
        except Exception as exc:
            log("analysis failed", s["name"], repr(exc)[:300])
            rec, events, sectors, grows = {"name": s["name"], "role": s["role"], "error": repr(exc)[:300]}, [], [], []
        rec["orbit_from_tap"] = orb["from_tap"]
        recs.append(rec)
        for e in events:
            e["name"] = s["name"]
        all_events += events
        for x in sectors:
            x["name"] = s["name"]
        all_sectors += sectors
        for x in grows:
            x["name"] = s["name"]
        all_gaia += grows
        log("result", s["name"], json.dumps(jclean({k: rec.get(k) for k in (
            "P", "P_err", "E1", "E1_z", "dphi", "E2", "E2_z", "E3", "E3_z", "E4",
            "depth_A", "depth_B", "n_A", "n_B")})))
    ctrls = [r for r in recs if r.get("role") == "control"]
    c_e1 = sum(1 for r in ctrls if r.get("E1") == "PERIOD_AGREES")
    c_e2 = sum(1 for r in ctrls if r.get("E2") == "SEC_PHASE_AGREES")
    controls = {"n": len(ctrls), "E1_agree": c_e1, "E2_agree": c_e2,
                "label": ("CONTROLS_OK" if ctrls and c_e1 == len(ctrls) and c_e2 >= len(ctrls) - 1
                          else "CONTROLS_FAIL")}
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    summary = {"meta": meta, "controls": controls, "stars": recs}
    with open(os.path.join(args.out_dir, "ebtime_summary.json"), "w") as fh:
        json.dump(jclean(summary), fh, indent=1)
    write_csv(os.path.join(args.out_dir, "ebtime_events.csv"), all_events,
              ["name", "sector", "author", "tc", "tc_err", "depth", "depth_obs", "fwhm", "n",
               "n_left", "n_right", "ok", "family", "cycle", "oc_min"])
    write_csv(os.path.join(args.out_dir, "ebtime_sectors.csv"), all_sectors,
              ["name", "sector", "author", "exptime", "n_points", "mad", "n_events", "n_events_ok"])
    write_csv(os.path.join(args.out_dir, "ebtime_gaia_epochs.csv"), all_gaia,
              ["name", "btjd", "mag", "oc_A_d", "oc_B_d", "in_eclipse", "faint"])
    print(json.dumps(jclean({"controls": controls, "labels": {r["name"]: {k: r.get(k) for k in (
        "E1", "E2", "E3", "E4")} for r in recs}})))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--config", default="targets.json")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    if a.self_test:
        return 0 if self_test() else 3
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
