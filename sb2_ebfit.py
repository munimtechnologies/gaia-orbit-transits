# SPDX-License-Identifier: Apache-2.0
"""sb2_ebfit 0.1.0 - masses and radii of Gaia DR3 double-lined eclipsing binaries from TESS
eclipses plus Gaia's own spectroscopic orbits.

MV2, Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.
Pre-registration: findings/2026-11-23-sb2-ebfit-prereg.md in
https://github.com/munimtechnologies/gaia-orbit-transits

Model: two spherical stars with quadratic limb darkening on an eccentric orbit, the eclipsed
star's light integrated numerically in annuli (exact arc fractions per annulus), third light,
exposure-time smearing for full-frame products, and a free linear baseline per eclipse window
(solved linearly inside the fit). No reflection, ellipsoidal or gravity-darkening terms; they are
absorbed to first order by the per-window baselines.

For every star in the config:
  1. TESS light curves with lightkurve, one author for all sectors (SPOC 120 s, else TESS-SPOC,
     else QLP), at most MAX_SECTORS sectors spread over the baseline.
  2. Period and phase of the eclipses by a fold search limited to Gaia's period +- max(10 sigma,
     3e-4 P), so no other period can be chosen.
  3. Windows around every covered eclipse; least-squares fit of T0, P, e cos w, e sin w, cos i,
     (R1+R2)/a, k = R2/R1, surface-brightness ratio J and third light l3 from several starts.
  4. Errors: formal (Jacobian, scaled by reduced chi-square) plus a jackknife over groups of
     windows (red noise) plus a limb-darkening systematic (u1 +- 0.1).
  5. Masses and radii: Monte Carlo over the fit covariance and Gaia's K1, K2 errors.
     M_tot = 4 pi^2 a^3 / (G P^2), a = sqrt(1 - e^2) (K1 + K2) P / (2 pi sin i).
  6. Controls (literature masses and radii in the config) graded against our values.
"""
import argparse
import csv
import json
import math
import os
import re
import sys
import time

import numpy as np

VERSION = "0.1.0"
SEED = 20261124
N_ANN = 200
GM_SUN = 1.3271244e20          # m^3 s^-2, IAU 2015 nominal
R_SUN_M = 6.957e8              # m, IAU 2015 nominal
DAY = 86400.0
AUTHOR_RANK = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}
MAX_SECTORS = 10
MAX_WINDOWS_PER_FAMILY = 60
N_BINS = 1000
Z_PASS = 3.0
PNAMES = ["T0", "P", "ecw", "esw", "cosi", "rsum", "k", "J", "l3"]
# Approximate TESS-band quadratic limb darkening for log g 4.0-4.5, [M/H] = 0 (rounded values in
# the style of Claret 2017; a systematic of +-0.1 in u1 is propagated).
LD_TABLE = [(4500, 0.48, 0.17), (5000, 0.42, 0.20), (5500, 0.36, 0.23), (6000, 0.31, 0.25),
            (6500, 0.27, 0.27), (7000, 0.23, 0.29), (7500, 0.20, 0.31), (8000, 0.18, 0.32),
            (9000, 0.15, 0.32), (10000, 0.13, 0.32)]


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


# ================================================================ limb darkening and occultation
def ld_coeffs(teff):
    teff = float(teff)
    ts = [r[0] for r in LD_TABLE]
    u1 = float(np.interp(teff, ts, [r[1] for r in LD_TABLE]))
    u2 = float(np.interp(teff, ts, [r[2] for r in LD_TABLE]))
    return u1, u2


def annuli(u1, u2, n=N_ANN):
    """-> (r, w): annulus mid radii and normalised light weights of a quadratic-LD disk."""
    r = (np.arange(n) + 0.5) / n
    mu = np.sqrt(1.0 - r * r)
    inten = 1.0 - u1 * (1.0 - mu) - u2 * (1.0 - mu) ** 2
    w = np.maximum(inten, 0.0) * r
    return r, w / w.sum()


def blocked_fraction(z, p, ann, chunk=20000):
    """Fraction of a limb-darkened star's light hidden by an opaque disk of radius p whose centre
    lies z from the star's centre (both in units of the star's radius)."""
    r, w = ann
    z = np.atleast_1d(np.asarray(z, float))
    out = np.zeros(z.shape)
    m = np.where(z < 1.0 + p)[0]
    rr = r[None, :]
    for s in range(0, m.size, chunk):
        idx = m[s:s + chunk]
        zz = np.maximum(z[idx], 1e-9)[:, None]
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            c = (rr * rr + zz * zz - p * p) / (2.0 * rr * zz)
        c = np.clip(np.nan_to_num(c, nan=1.0, posinf=1.0, neginf=-1.0), -1.0, 1.0)
        out[idx] = (np.arccos(c) / np.pi) @ w
    return out


def uniform_overlap(z, p):
    """Analytic blocked fraction of a uniform unit disk by a disk of radius p at distance z."""
    if z >= 1.0 + p:
        return 0.0
    if z <= abs(1.0 - p):
        return min(p, 1.0) ** 2
    k0 = math.acos((p * p + z * z - 1.0) / (2.0 * p * z))
    k1 = math.acos((1.0 - p * p + z * z) / (2.0 * z))
    area = p * p * k0 + k1 - 0.5 * math.sqrt(max(4.0 * z * z - (1.0 + z * z - p * p) ** 2, 0.0))
    return area / math.pi


# ================================================================ orbit
def kepler_E(M, e):
    M = np.asarray(M, float)
    E = M + e * np.sin(M)
    for _ in range(50):
        dE = (E - e * np.sin(E) - M) / (1.0 - e * np.cos(E))
        E = E - dE
        if np.max(np.abs(dE)) < 1e-12:
            break
    return E


def mean_anom_of_true(nu, e):
    E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0), math.sqrt(1.0 + e) * math.cos(nu / 2.0))
    return E - e * math.sin(E)


def ew_of(ecw, esw):
    e = math.hypot(ecw, esw)
    w = math.atan2(esw, ecw) if e > 0 else math.pi / 2.0
    return e, w


def sky_geometry(t, T0, P, ecw, esw, cosi):
    """-> (d, s): projected separation in units of a; s = sin(nu + w) > 0 when star 1 (the star
    eclipsed at T0) is behind. T0 is the conjunction nu + w = 90 deg."""
    e, w = ew_of(ecw, esw)
    e = min(e, 0.95)
    M0 = mean_anom_of_true(math.pi / 2.0 - w, e)
    M = (2.0 * math.pi * (np.asarray(t, float) - T0) / P + M0) % (2.0 * math.pi)
    E = kepler_E(M, e)
    nu = 2.0 * np.arctan2(math.sqrt(1.0 + e) * np.sin(E / 2.0), math.sqrt(1.0 - e) * np.cos(E / 2.0))
    rsep = 1.0 - e * np.cos(E)
    s = np.sin(nu + w)
    c = np.cos(nu + w)
    d = rsep * np.sqrt(c * c + (s * cosi) ** 2)
    return d, s


def secondary_phase(ecw, esw):
    """Phase of the second conjunction (nu + w = 270 deg) after T0."""
    e, w = ew_of(ecw, esw)
    m1 = mean_anom_of_true(math.pi / 2.0 - w, e)
    m2 = mean_anom_of_true(1.5 * math.pi - w, e)
    return ((m2 - m1) / (2.0 * math.pi)) % 1.0


def lc_model(t, th, anns):
    T0, P, ecw, esw, cosi, rsum, k, J, l3 = th
    r1 = rsum / (1.0 + k)
    r2 = rsum * k / (1.0 + k)
    d, s = sky_geometry(t, T0, P, ecw, esw, cosi)
    L2 = k * k * J
    f1, f2 = 1.0 / (1.0 + L2), L2 / (1.0 + L2)
    flux = np.ones(d.shape)
    near = d < r1 + r2
    m1 = near & (s > 0)
    if m1.any():
        flux[m1] -= f1 * blocked_fraction(d[m1] / r1, r2 / r1, anns[0])
    m2 = near & (s <= 0)
    if m2.any():
        flux[m2] -= f2 * blocked_fraction(d[m2] / r2, r1 / r2, anns[1])
    return (1.0 - l3) * flux + l3


# ================================================================ data
class Data:
    def __init__(self, t, f, err, win, tau, fam, exptime, sector):
        self.t, self.f, self.err = np.asarray(t, float), np.asarray(f, float), np.asarray(err, float)
        self.win = np.asarray(win, int)
        self.tau = np.asarray(tau, float)
        self.fam = np.asarray(fam, int)
        self.exptime = np.asarray(exptime, float)
        self.sector = np.asarray(sector, int)
        self.nwin = int(self.win.max()) + 1 if self.win.size else 0
        self.groups = []
        for ex in np.unique(np.round(self.exptime)):
            idx = np.where(np.round(self.exptime) == ex)[0]
            nss = 1 if ex <= 200 else min(int(math.ceil(ex / 120.0)) | 1, 7)
            self.groups.append((idx, nss, float(ex)))

    def subset(self, keep_win):
        keep = np.isin(self.win, keep_win)
        remap = -np.ones(self.nwin, int)
        remap[np.asarray(keep_win, int)] = np.arange(len(keep_win))
        return Data(self.t[keep], self.f[keep], self.err[keep], remap[self.win[keep]],
                    self.tau[keep], self.fam[keep], self.exptime[keep], self.sector[keep])


def model_at(data, th, anns):
    out = np.empty(data.t.size)
    for idx, nss, ex in data.groups:
        if nss == 1:
            out[idx] = lc_model(data.t[idx], th, anns)
        else:
            off = ((np.arange(nss) + 0.5) / nss - 0.5) * ex / DAY
            tt = (data.t[idx][:, None] + off[None, :]).ravel()
            out[idx] = lc_model(tt, th, anns).reshape(-1, nss).mean(axis=1)
    return out


def project_baseline(m, data):
    """Best (a + b tau) per window for f ~ m (a + b tau), weights 1/err^2. -> baseline array."""
    w8 = 1.0 / data.err ** 2
    x1, x2 = m, m * data.tau
    n = data.nwin
    S11 = np.bincount(data.win, w8 * x1 * x1, n)
    S12 = np.bincount(data.win, w8 * x1 * x2, n)
    S22 = np.bincount(data.win, w8 * x2 * x2, n)
    B1 = np.bincount(data.win, w8 * x1 * data.f, n)
    B2 = np.bincount(data.win, w8 * x2 * data.f, n)
    det = S11 * S22 - S12 * S12
    det = np.where(np.abs(det) > 0, det, 1.0)
    a = (S22 * B1 - S12 * B2) / det
    b = (S11 * B2 - S12 * B1) / det
    return a[data.win] + b[data.win] * data.tau


# ================================================================ light curves
def detrend(t, f, width=1.0, n_iter=4):
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


def point_noise(r):
    d = np.diff(np.asarray(r, float))
    if d.size < 10:
        return float(np.std(r)) or 1e-3
    return max(float(1.4826 * np.median(np.abs(d - np.median(d))) / math.sqrt(2.0)), 1e-5)


def tess_lightcurves(tic, cache_dir, max_lc=MAX_SECTORS):
    import lightkurve as lk
    sr = None
    for a in range(3):
        try:
            sr = lk.search_lightcurve("TIC %d" % int(tic), mission="TESS")
            break
        except Exception as exc:
            log("search retry", tic, repr(exc)[:160])
            time.sleep(10 * (a + 1))
    if sr is None or len(sr) == 0:
        return [], ""
    tab = sr.table
    pick = {}
    for i in range(len(sr)):
        author = str(tab["author"][i])
        if author not in AUTHOR_RANK:
            continue
        exptime = fnum(np.asarray(tab["exptime"])[i])
        if author == "SPOC" and not (100 <= exptime <= 200):
            continue
        if not math.isfinite(exptime) or exptime <= 0:
            exptime = 600.0
        m = re.search(r"(\d+)", str(tab["mission"][i]))
        if not m:
            continue
        sec = int(m.group(1))
        pick.setdefault(author, {})
        key = abs(exptime - 120.0)
        if sec not in pick[author] or key < pick[author][sec][0]:
            pick[author][sec] = (key, i, exptime)
    if not pick:
        return [], ""
    author = min(pick, key=lambda a: AUTHOR_RANK[a])
    secs = sorted(pick[author])
    if len(secs) > max_lc:
        sel = np.unique(np.round(np.linspace(0, len(secs) - 1, max_lc)).astype(int))
        secs = [secs[j] for j in sel]
    out = []
    for sec in secs:
        _, i, exptime = pick[author][sec]
        for a in range(3):
            try:
                lc = sr[i].download(download_dir=cache_dir, quality_bitmask="default")
                lc = lc.remove_nans()
                t = np.asarray(lc.time.value, float)
                f = np.asarray(lc.flux.value, float)
                ok = np.isfinite(t) & np.isfinite(f) & (f > 0)
                if ok.sum() >= 100:
                    out.append({"sector": sec, "author": author, "exptime": exptime,
                                "t": t[ok], "f": f[ok] / np.median(f[ok])})
                    log("TIC", tic, "sector", sec, author, exptime, int(ok.sum()), "points")
                break
            except Exception as exc:
                log("download retry TIC", tic, "sector", sec, repr(exc)[:160])
                time.sleep(10 * (a + 1))
    return out, author


# ================================================================ ephemeris from a fold search
def binned_profile(t, r, P, tref, n_bins=N_BINS):
    ph = ((t - tref) / P) % 1.0
    b = np.minimum((ph * n_bins).astype(int), n_bins - 1)
    cnt = np.bincount(b, minlength=n_bins)
    s = np.bincount(b, r, n_bins)
    mean = np.where(cnt >= 3, s / np.maximum(cnt, 1), 0.0)
    return mean, cnt


def dip_width(mean, j, depth):
    """Width (in bins) of the contiguous run around j with mean below -depth/2 (one-bin gaps ok)."""
    n = mean.size
    half = -0.5 * depth
    width = 1
    for step in (1, -1):
        k, miss = j, 0
        for _ in range(n // 4):
            k = (k + step) % n
            if mean[k] < half:
                width += 1 + miss
                miss = 0
            else:
                miss += 1
                if miss > 1:
                    break
    return width


def fold_search(t, r, P0, sP):
    t = np.asarray(t, float)
    r = np.asarray(r, float)
    base = float(t.max() - t.min())
    half = max(10.0 * sP if math.isfinite(sP) else 0.0, 3e-4 * P0)
    step = max(5e-4 * P0 * P0 / max(base, P0), 1e-7)
    n = int(2 * half / step) + 1
    if n > 4001:
        step = 2 * half / 4000
        n = 4001
    grid = P0 - half + step * np.arange(n)
    tref = float(t.min())
    best = (np.inf, P0)
    for P in grid:
        mean, _ = binned_profile(t, r, P, tref)
        v = float(mean.min())
        if v < best[0]:
            best = (v, float(P))
    P = best[1]
    mean, cnt = binned_profile(t, r, P, tref)
    j1 = int(np.argmin(mean))
    d1 = float(-mean[j1])
    w1 = dip_width(mean, j1, d1)
    nb = mean.size
    dist = np.minimum((np.arange(nb) - j1) % nb, (j1 - np.arange(nb)) % nb)
    mask = dist > max(3 * w1, 0.03 * nb)
    noise = float(1.4826 * np.median(np.abs(mean[mask & (cnt >= 3)]))) if (mask & (cnt >= 3)).any() else 0.0
    j2 = int(np.argmin(np.where(mask, mean, np.inf)))
    d2 = float(-mean[j2])
    sec_found = d2 > max(5.0 * noise, 0.1 * d1 * 0.05)
    w2 = dip_width(mean, j2, d2) if sec_found else w1
    ph1 = (j1 + 0.5) / nb
    ph2 = (j2 + 0.5) / nb if sec_found else (ph1 + 0.5) % 1.0
    T0 = tref + ph1 * P
    tmid = float(np.median(t))
    T0 += round((tmid - T0) / P) * P
    return {"P": P, "T0": T0, "depth1": d1, "depth2": d2 if sec_found else 0.0,
            "sec_found": bool(sec_found), "dphase": (ph2 - ph1) % 1.0,
            "fwhm1_d": w1 / nb * P, "fwhm2_d": w2 / nb * P, "profile_noise": noise}


# ================================================================ windows
def build_windows(lcs, eph):
    """Windows around every covered eclipse of both families."""
    P, T0 = eph["P"], eph["T0"]
    fams = [(0, 0.0, eph["fwhm1_d"]), (1, eph["dphase"], eph["fwhm2_d"])]
    rows = {"t": [], "f": [], "err": [], "win": [], "tau": [], "fam": [], "exptime": [], "sector": []}
    wins = []
    for lc in lcs:
        t, f = lc["t"], lc["f"]
        r = detrend(t, f)
        sig = point_noise(r)
        for fam, dph, fw in fams:
            hw = max(2.2 * fw, 0.12)
            n0 = math.floor((t.min() - T0) / P) - 1
            n1 = math.ceil((t.max() - T0) / P) + 1
            for n in range(n0, n1 + 1):
                tc = T0 + (n + dph) * P
                sel = np.abs(t - tc) <= hw
                if sel.sum() < 12:
                    continue
                tau = t[sel] - tc
                left = (tau < -1.5 * fw).sum()
                right = (tau > 1.5 * fw).sum()
                core = (np.abs(tau) < 0.5 * fw).sum()
                if left < 3 or right < 3 or core < 3:
                    continue
                wins.append({"fam": fam, "tc": tc, "sector": lc["sector"], "n": int(sel.sum()),
                             "t": t[sel], "f": f[sel], "tau": tau, "sig": sig, "exptime": lc["exptime"]})
    out = []
    for fam in (0, 1):
        fw = [w for w in wins if w["fam"] == fam]
        if len(fw) > MAX_WINDOWS_PER_FAMILY:
            sel = np.unique(np.round(np.linspace(0, len(fw) - 1, MAX_WINDOWS_PER_FAMILY)).astype(int))
            fw = [fw[j] for j in sel]
        out += fw
    out.sort(key=lambda w: w["tc"])
    for k, w in enumerate(out):
        m = w["t"].size
        rows["t"].append(w["t"])
        rows["f"].append(w["f"])
        rows["err"].append(np.full(m, w["sig"]))
        rows["win"].append(np.full(m, k))
        rows["tau"].append(w["tau"])
        rows["fam"].append(np.full(m, w["fam"]))
        rows["exptime"].append(np.full(m, w["exptime"]))
        rows["sector"].append(np.full(m, w["sector"]))
    if not out:
        return None, []
    cat = {k: np.concatenate(v) for k, v in rows.items()}
    data = Data(cat["t"], cat["f"], cat["err"], cat["win"], cat["tau"], cat["fam"], cat["exptime"], cat["sector"])
    meta = [{"k": k, "fam": w["fam"], "tc": w["tc"], "sector": w["sector"], "n": w["n"]} for k, w in enumerate(out)]
    return data, meta


# ================================================================ fitting
SCALE = np.array([1e-3, 1e-5, 1e-3, 1e-2, 1e-2, 1e-3, 1e-2, 1e-2, 1e-2])


def fit_lc(data, th_init, free, anns, bounds_lo, bounds_hi, max_nfev=300):
    from scipy.optimize import least_squares
    th_init = np.asarray(th_init, float)
    free = np.asarray(free, bool)
    ref = th_init.copy()
    sc = SCALE[free]
    lo = (bounds_lo[free] - ref[free]) / sc
    hi = (bounds_hi[free] - ref[free]) / sc
    x0 = np.zeros(free.sum())
    x0 = np.clip(x0, lo + 1e-6 * (hi - lo), hi - 1e-6 * (hi - lo))

    def theta(x):
        th = ref.copy()
        th[free] = ref[free] + x * sc
        return th

    def resid(x):
        th = theta(x)
        m = model_at(data, th, anns)
        base = project_baseline(m, data)
        return (data.f - m * base) / data.err

    res = least_squares(resid, x0, bounds=(lo, hi), diff_step=1e-2, x_scale=1.0, max_nfev=max_nfev,
                        method="trf")
    th = theta(res.x)
    n = data.t.size
    nfree = int(free.sum()) + 2 * data.nwin
    chi2 = float(2.0 * res.cost)
    chi2_red = chi2 / max(n - nfree, 1)
    cov = np.full((len(th), len(th)), np.nan)
    try:
        Jm = res.jac
        cx = np.linalg.pinv(Jm.T @ Jm) * max(chi2_red, 1.0)
        cf = cx * sc[:, None] * sc[None, :]
        fi = np.where(free)[0]
        cov = np.zeros((len(th), len(th)))
        cov[np.ix_(fi, fi)] = cf
    except Exception as exc:
        log("covariance failed", repr(exc)[:120])
    span = hi - lo
    at_bound = bool(np.any((res.x - lo) < 1e-4 * span) or np.any((hi - res.x) < 1e-4 * span))
    return {"theta": th, "cov": cov, "chi2": chi2, "chi2_red": chi2_red, "n": n,
            "success": bool(res.success), "status": int(res.status), "nfev": int(res.nfev),
            "at_bound": at_bound}


def default_bounds(th0, eph, sP):
    P = th0[1]
    dP = max(5e-4 * P, 20.0 * sP if math.isfinite(sP) else 0.0)
    lo = np.array([th0[0] - 0.2, P - dP, -0.7, -0.7, -0.6, 0.01, 0.2, 0.02, -0.5])
    hi = np.array([th0[0] + 0.2, P + dP, 0.7, 0.7, 0.6, 0.9, 5.0, 50.0, 0.95])
    return lo, hi


def initial_ecc(eph, gaia):
    """-> list of (ecw0, esw0) start pairs from the observed secondary phase and Gaia's e, w."""
    dph = eph["dphase"]
    e_g, w_g = fnum(gaia.get("e")), fnum(gaia.get("omega"))
    starts = []
    if math.isfinite(e_g) and math.isfinite(w_g) and e_g > 0:
        cands = []
        for wdeg in (w_g, w_g + 180.0):
            ecw, esw = e_g * math.cos(math.radians(wdeg)), e_g * math.sin(math.radians(wdeg))
            cands.append((abs(((secondary_phase(ecw, esw) - dph + 0.5) % 1.0) - 0.5), ecw, esw))
        cands.sort()
        starts.append((cands[0][1], cands[0][2]))
        starts.append((cands[0][1], -cands[0][2]))
    else:
        grid = np.linspace(-0.3, 0.3, 601)
        err = [abs(((secondary_phase(x, 0.0) - dph + 0.5) % 1.0) - 0.5) for x in grid]
        starts.append((float(grid[int(np.argmin(err))]), 0.0))
    return starts


def fit_star(data, eph, gaia, anns, sP, l3_free=True):
    d1 = max(eph["depth1"], 1e-3)
    J0 = float(np.clip(eph["depth2"] / d1 if eph["sec_found"] else 0.2, 0.05, 5.0))
    rsum0 = float(np.clip(math.pi * 2.2 * eph["fwhm1_d"] / eph["P"], 0.03, 0.7))
    best = None
    tried = []
    for ecw0, esw0 in initial_ecc(eph, gaia):
        for cosi0, k0 in ((0.02, 1.0), (0.08, 1.0), (0.15, 1.0), (0.05, 0.75), (0.05, 1.33)):
            th0 = np.array([eph["T0"], eph["P"], ecw0, esw0, cosi0, rsum0, k0, J0, 0.0])
            lo, hi = default_bounds(th0, eph, sP)
            free = np.ones(9, bool)
            free[8] = l3_free
            try:
                res = fit_lc(data, th0, free, anns, lo, hi, max_nfev=60)
            except Exception as exc:
                log("fit failed from start", cosi0, k0, repr(exc)[:160])
                continue
            tried.append({"start": [ecw0, esw0, cosi0, k0], "chi2": res["chi2"]})
            if best is None or res["chi2"] < best["chi2"]:
                best = res
                best["lo"], best["hi"], best["free"] = lo, hi, free
    if best is None:
        return None
    lo, hi, free = best["lo"], best["hi"], best["free"]
    try:
        fin = fit_lc(data, best["theta"], free, anns, lo, hi, max_nfev=400)
        if fin["chi2"] <= best["chi2"] * (1.0 + 1e-9):
            best = fin
            best["lo"], best["hi"], best["free"] = lo, hi, free
    except Exception as exc:
        log("final refit failed", repr(exc)[:160])
    best["starts"] = tried
    return best


def jackknife(data, best, anns, n_groups=8):
    nw = data.nwin
    G = min(n_groups, nw // 2)
    if G < 3:
        return None, 0
    order = np.arange(nw)
    grp = order * G // nw
    thetas = []
    for g in range(G):
        keep = np.where(grp != g)[0]
        sub = data.subset(keep)
        try:
            r = fit_lc(sub, best["theta"], best["free"], anns, best["lo"], best["hi"], max_nfev=150)
            thetas.append(r["theta"])
        except Exception as exc:
            log("jackknife fit failed", g, repr(exc)[:120])
    if len(thetas) < 3:
        return None, len(thetas)
    T = np.array(thetas)
    m = T.mean(axis=0)
    n = len(thetas)
    cov = (n - 1) / n * ((T - m).T @ (T - m))
    return cov, n


# ================================================================ physics
def physical_mc(theta, cov, K1, sK1, K2, sK2, n=20000, seed=SEED):
    """-> dict of percentiles for masses (Gaia component 1 and 2), radii of LC stars 1 and 2, a, i."""
    rng = np.random.default_rng(seed)
    cov = np.nan_to_num(np.asarray(cov, float))
    cov = 0.5 * (cov + cov.T)
    vals, vecs = np.linalg.eigh(cov)
    vals = np.clip(vals, 0.0, None)
    draws = theta[None, :] + (rng.standard_normal((n, len(theta))) * np.sqrt(vals)[None, :]) @ vecs.T
    k1 = rng.normal(K1, sK1, n)
    k2 = rng.normal(K2, sK2, n)
    P = draws[:, 1]
    e = np.minimum(np.hypot(draws[:, 2], draws[:, 3]), 0.95)
    cosi = np.abs(draws[:, 4])
    sini = np.sqrt(np.clip(1.0 - cosi ** 2, 1e-6, 1.0))
    rsum = draws[:, 5]
    kk = np.clip(draws[:, 6], 1e-3, None)
    asini = np.sqrt(1.0 - e ** 2) * (k1 + k2) * 1e3 * P * DAY / (2.0 * math.pi)
    a = asini / sini
    mtot = 4.0 * math.pi ** 2 * a ** 3 / (GM_SUN * (P * DAY) ** 2)
    out = {"M_gaia1": mtot * k2 / (k1 + k2), "M_gaia2": mtot * k1 / (k1 + k2),
           "R_lc1": rsum / (1.0 + kk) * a / R_SUN_M, "R_lc2": rsum * kk / (1.0 + kk) * a / R_SUN_M,
           "R_sum": rsum * a / R_SUN_M, "a_rsun": a / R_SUN_M,
           "inc_deg": np.degrees(np.arccos(cosi)), "M1sin3i_gaia1": mtot * sini ** 3 * k2 / (k1 + k2)}
    res = {}
    for k, v in out.items():
        v = v[np.isfinite(v)]
        q16, q50, q84 = np.percentile(v, [16, 50, 84])
        res[k] = {"median": float(q50), "lo": float(q50 - q16), "hi": float(q84 - q50),
                  "sd": float(0.5 * (q84 - q16))}
    return res


def msini_direct(K1, K2, P, e):
    """M sin^3 i of both Gaia components (M_sun), conventional formula."""
    f = (1.0 - e * e) ** 1.5 * (K1 + K2) ** 2 * P * DAY * 1e9 / (2.0 * math.pi * GM_SUN)
    return f * K2, f * K1


def angdiff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


def map_components(theta, cov, gaia):
    """Which Gaia component is LC star 1 (the star eclipsed at T0)?"""
    ecw, esw = theta[2], theta[3]
    e = math.hypot(ecw, esw)
    se = math.sqrt(max(cov[2, 2] * (ecw / e) ** 2 + cov[3, 3] * (esw / e) ** 2, 0.0)) if e > 0 else float("inf")
    e_g, se_g, w_g = fnum(gaia.get("e")), fnum(gaia.get("e_err")), fnum(gaia.get("omega"))
    L2 = theta[6] ** 2 * theta[7]
    out = {"e_fit": e, "e_fit_err": se, "omega_fit_deg": math.degrees(math.atan2(esw, ecw)) % 360.0,
           "L2_over_L1": L2}
    if (math.isfinite(e_g) and math.isfinite(se_g) and se_g > 0 and e_g / se_g >= 5.0
            and math.isfinite(se) and e / se >= 5.0 and math.isfinite(w_g)):
        d0 = angdiff(out["omega_fit_deg"], w_g)
        d180 = angdiff(out["omega_fit_deg"], w_g + 180.0)
        out.update({"rule": "MAP_OMEGA", "lc1_is": "gaia1" if abs(d0) <= abs(d180) else "gaia2",
                    "omega_diff_deg": d0 if abs(d0) <= abs(d180) else d180})
    else:
        out.update({"rule": "MAP_ASSUMED_BRIGHTER",
                    "lc1_is": "gaia1" if L2 <= 1.0 else "gaia2"})
    return out


def grade_control(phys, mapping, lit):
    mg = sorted([(phys["M_gaia1"]["median"], phys["M_gaia1"]["sd"], "gaia1"),
                 (phys["M_gaia2"]["median"], phys["M_gaia2"]["sd"], "gaia2")], reverse=True)
    ml = sorted([(lit["M1"], lit["M1_err"], lit["R1"], lit["R1_err"]),
                 (lit["M2"], lit["M2_err"], lit["R2"], lit["R2_err"])], reverse=True)
    zM = [(a[0] - b[0]) / math.hypot(a[1], b[1]) for a, b in zip(mg, ml)]
    rs, rsl = phys["R_sum"], lit["R1"] + lit["R2"]
    zR = (rs["median"] - rsl) / math.hypot(rs["sd"], math.hypot(lit["R1_err"], lit["R2_err"]))
    # radii by mapping (exploratory)
    lc_of = {"gaia1": "R_lc1" if mapping["lc1_is"] == "gaia1" else "R_lc2",
             "gaia2": "R_lc2" if mapping["lc1_is"] == "gaia1" else "R_lc1"}
    zRi = []
    for (m, sm, comp), (mL, smL, rL, srL) in zip(mg, ml):
        r = phys[lc_of[comp]]
        zRi.append((r["median"] - rL) / math.hypot(r["sd"], srL))
    ok = all(abs(z) <= Z_PASS for z in zM) and abs(zR) <= Z_PASS
    return {"z_mass_heavier": zM[0], "z_mass_lighter": zM[1], "z_radius_sum": zR,
            "z_radius_heavier_mapped": zRi[0], "z_radius_lighter_mapped": zRi[1],
            "mass_frac_diff": [(a[0] - b[0]) / b[0] for a, b in zip(mg, ml)],
            "radius_sum_frac_diff": (rs["median"] - rsl) / rsl,
            "label": "CONTROL_PASS" if ok else "CONTROL_FAIL"}


# ================================================================ one star
def analyse(star, lcs, author):
    g = star["gaia"]
    rec = {"name": star["name"], "role": star["role"], "tic": star["tic"], "source_id": star["source_id"],
           "author": author, "sectors": [lc["sector"] for lc in lcs]}
    if not lcs:
        rec["label"] = "NO_DATA"
        return rec, None
    t = np.concatenate([lc["t"] for lc in lcs])
    r = np.concatenate([detrend(lc["t"], lc["f"]) for lc in lcs])
    P0, sP = fnum(g["P"]), fnum(g.get("P_err"))
    eph = fold_search(t, r, P0, sP)
    rec["fold"] = eph
    log(star["name"], "fold", json.dumps({k: eph[k] for k in ("P", "T0", "depth1", "depth2", "dphase", "fwhm1_d")}))
    data, meta = build_windows(lcs, eph)
    if data is None or data.nwin < 2:
        rec["label"] = "NO_WINDOWS"
        return rec, None
    rec["n_windows"] = data.nwin
    rec["n_windows_fam"] = [int(sum(1 for m in meta if m["fam"] == f)) for f in (0, 1)]
    rec["n_points"] = int(data.t.size)
    teff1, teff2 = star.get("teff1", 6000), star.get("teff2", 6000)
    u = [ld_coeffs(teff1), ld_coeffs(teff2)]
    anns = [annuli(*u[0]), annuli(*u[1])]
    rec["ld"] = u
    best = fit_star(data, eph, g, anns, sP, l3_free=True)
    if best is None:
        rec["label"] = "FIT_FAILED"
        return rec, None
    th = best["theta"]
    log(star["name"], "best", json.dumps(dict(zip(PNAMES, [float(x) for x in th]))), "chi2r", best["chi2_red"])
    jcov, nj = jackknife(data, best, anns)
    # limb-darkening systematic
    ld_th = []
    for du in (-0.1, 0.1):
        a2 = [annuli(u[0][0] + du, u[0][1]), annuli(u[1][0] + du, u[1][1])]
        try:
            ld_th.append(fit_lc(data, th, best["free"], a2, best["lo"], best["hi"], max_nfev=150)["theta"])
        except Exception as exc:
            log("LD refit failed", repr(exc)[:120])
    ld_sd = 0.5 * np.abs(ld_th[1] - ld_th[0]) if len(ld_th) == 2 else np.zeros(9)
    # third light fixed at 0 (check)
    try:
        free0 = best["free"].copy()
        free0[8] = False
        th0 = th.copy()
        th0[8] = 0.0
        fix0 = fit_lc(data, th0, free0, anns, best["lo"], best["hi"], max_nfev=200)
    except Exception as exc:
        log("l3=0 refit failed", repr(exc)[:120])
        fix0 = None
    cov_tot = np.nan_to_num(best["cov"]) + (np.nan_to_num(jcov) if jcov is not None else 0.0) + np.diag(ld_sd ** 2)
    phys = physical_mc(th, cov_tot, fnum(g["K1"]), fnum(g["K1_err"]), fnum(g["K2"]), fnum(g["K2_err"]))
    mapping = map_components(th, cov_tot, g)
    sd = np.sqrt(np.clip(np.diag(cov_tot), 0.0, None))
    rec.update({"theta": dict(zip(PNAMES, th)), "err_total": dict(zip(PNAMES, sd)),
                "err_formal": dict(zip(PNAMES, np.sqrt(np.clip(np.diag(np.nan_to_num(best["cov"])), 0, None)))),
                "err_jackknife": dict(zip(PNAMES, np.sqrt(np.clip(np.diag(jcov), 0, None)))) if jcov is not None else None,
                "n_jackknife": nj, "err_ld": dict(zip(PNAMES, ld_sd)), "chi2_red": best["chi2_red"],
                "success": best["success"], "at_bound": best["at_bound"], "starts": best["starts"],
                "l3_zero_fit": ({"theta": dict(zip(PNAMES, fix0["theta"])), "chi2_red": fix0["chi2_red"]}
                                if fix0 else None),
                "phys": phys, "mapping": mapping,
                "msini_direct": msini_direct(fnum(g["K1"]), fnum(g["K2"]), th[1],
                                             fnum(g.get("e"), 0.0) if math.isfinite(fnum(g.get("e"))) else 0.0)})
    # Gaia comparison: period, e cos w
    rec["z_period_vs_gaia"] = (th[1] - P0) / math.hypot(sd[1], sP if math.isfinite(sP) else 0.0)
    e_g, w_g = fnum(g.get("e")), fnum(g.get("omega"))
    if math.isfinite(e_g) and math.isfinite(w_g):
        wmap = w_g if mapping["lc1_is"] == "gaia1" else w_g + 180.0
        ecw_g = e_g * math.cos(math.radians(wmap))
        wr = math.radians(wmap)
        s_ecw_g = math.hypot(math.cos(wr) * fnum(g.get("e_err"), 0.0),
                             e_g * math.sin(wr) * math.radians(fnum(g.get("omega_err"), 0.0)))
        rec["ecw_gaia_mapped"] = ecw_g
        rec["ecw_gaia_mapped_err"] = s_ecw_g
        rec["z_ecw_vs_gaia"] = (th[2] - ecw_g) / math.hypot(sd[2], s_ecw_g + 1e-9)
    fit_ok = bool(best["success"] and not best["at_bound"] and best["chi2_red"] < 5.0
                  and np.all(np.isfinite(sd[2:8])))
    rec["FIT_OK"] = fit_ok
    m1, m2 = phys["M_gaia1"], phys["M_gaia2"]
    rec["MASS_PRECISION"] = max(m1["sd"] / m1["median"], m2["sd"] / m2["median"])
    rec["RSUM_PRECISION"] = phys["R_sum"]["sd"] / phys["R_sum"]["median"]
    rec["label"] = "FIT_OK" if fit_ok else "FIT_DOUBTFUL"
    if star["role"] == "control" and star.get("literature"):
        rec["control"] = grade_control(phys, mapping, star["literature"])
    fold_rows = fold_table(data, th, anns, meta)
    return rec, fold_rows


def fold_table(data, th, anns, meta, n_bins=120):
    """Binned, baseline-corrected data and model against time from each window's predicted centre."""
    m = model_at(data, th, anns)
    base = project_baseline(m, data)
    fn = data.f / base
    rows = []
    for fam in (0, 1):
        sel = data.fam == fam
        if not sel.any():
            continue
        tau = data.tau[sel]
        lo, hi = tau.min(), tau.max()
        edges = np.linspace(lo, hi, n_bins + 1)
        b = np.clip(np.searchsorted(edges, tau) - 1, 0, n_bins - 1)
        cnt = np.bincount(b, minlength=n_bins)
        sf = np.bincount(b, fn[sel], n_bins)
        sm = np.bincount(b, m[sel], n_bins)
        for j in range(n_bins):
            if cnt[j] >= 3:
                rows.append({"family": fam, "dt_d": 0.5 * (edges[j] + edges[j + 1]), "n": int(cnt[j]),
                             "flux": sf[j] / cnt[j], "model": sm[j] / cnt[j]})
    return rows


# ================================================================ self-test
def synth(seed=7):
    rng = np.random.default_rng(seed)
    th = np.array([2000.3, 4.2, 0.03, 0.04, 0.06, 0.20, 0.9, 0.8, 0.1])
    u = [ld_coeffs(6200), ld_coeffs(6000)]
    anns = [annuli(*u[0]), annuli(*u[1])]
    lcs = []
    for k, t0 in enumerate((1990.0, 2600.0)):
        t = np.arange(t0, t0 + 26.0, 120.0 / DAY)
        t = t[(t < t0 + 12.5) | (t > t0 + 13.5)]
        f = lc_model(t, th, anns) * (1.0 + 0.003 * np.sin(2 * np.pi * t / 5.3)) + rng.normal(0, 6e-4, t.size)
        lcs.append({"sector": k + 1, "author": "SPOC", "exptime": 120.0, "t": t, "f": f})
    return th, lcs


def self_test():
    ok = True
    ann0 = annuli(0.0, 0.0, 400)
    errs = []
    for z, p in ((0.0, 0.5), (0.3, 0.5), (0.9, 0.4), (1.2, 0.5), (0.5, 1.2), (0.2, 0.9)):
        errs.append(abs(blocked_fraction([z], p, ann0)[0] - uniform_overlap(z, p)))
    ok1 = max(errs) < 2e-3
    log("uniform occultation", "PASS" if ok1 else "FAIL", max(errs))
    ok &= ok1
    th, lcs = synth()
    K1, K2 = 80.0, 90.0
    star = {"name": "synthetic", "role": "selftest", "tic": "0", "source_id": "0",
            "teff1": 6200, "teff2": 6000,
            "gaia": {"P": th[1] + 3e-5, "P_err": 2e-5, "e": math.hypot(th[2], th[3]), "e_err": 0.005,
                     "omega": math.degrees(math.atan2(th[3], th[2])), "omega_err": 5.0,
                     "K1": K1, "K1_err": 0.5, "K2": K2, "K2_err": 0.5}}
    rec, _ = analyse(star, lcs, "SPOC")
    got = rec.get("theta", {})
    chk = {"cosi": abs(abs(got.get("cosi", 9)) - th[4]) < 0.01,
           "rsum": abs(got.get("rsum", 9) - th[5]) < 0.004,
           "ecw": abs(got.get("ecw", 9) - th[2]) < 0.003,
           "P": abs(got.get("P", 9) - th[1]) < 2e-5,
           "map": rec.get("mapping", {}).get("lc1_is") == "gaia1"}
    # masses: true from th and K's
    e = math.hypot(th[2], th[3])
    sini = math.sqrt(1 - th[4] ** 2)
    m1s, m2s = msini_direct(K1, K2, th[1], e)
    ph = rec.get("phys", {})
    chk["M1"] = abs(ph.get("M_gaia1", {}).get("median", 0) - m1s / sini ** 3) / (m1s / sini ** 3) < 0.02
    ok2 = all(chk.values())
    log("synthetic EB", "PASS" if ok2 else "FAIL", json.dumps(chk),
        json.dumps({k: float(v) for k, v in got.items()}) if got else "no fit")
    ok &= ok2
    log("self-test", "PASS" if ok else "FAIL")
    return bool(ok)


# ================================================================ driver
def jclean(o):
    if isinstance(o, dict):
        return {str(k): jclean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jclean(v) for v in o]
    if isinstance(o, np.ndarray):
        return [jclean(v) for v in o.tolist()]
    if isinstance(o, (np.floating, float)):
        x = float(o)
        return x if math.isfinite(x) else None
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def run(args):
    cfg = json.load(open(args.config))
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.data_dir, exist_ok=True)
    meta = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "orbit_source": "config (Gaia DR3 nss_two_body_orbit, read from ESA TAP 2026-11-23)"}
    try:
        meta["self_test"] = "PASS" if self_test() else "FAIL"
    except Exception as exc:
        log("self-test crashed", repr(exc)[:300])
        meta["self_test"] = "ERROR"
    log("self-test result recorded:", meta["self_test"], "(registered: no grading unless PASS)")
    order = sorted(cfg["stars"], key=lambda s: 0 if s["role"] == "control" else 1)
    recs = []
    rows_csv = []
    for s in order:
        if args.only and s["name"] not in args.only:
            continue
        log("star", s["name"], s["role"], "TIC", s["tic"])
        try:
            lcs, author = tess_lightcurves(s["tic"], os.path.join(args.data_dir, "lk"))
            rec, fold = analyse(s, lcs, author)
        except Exception as exc:
            log("star failed", s["name"], repr(exc)[:300])
            rec, fold = {"name": s["name"], "role": s["role"], "label": "ERROR", "error": repr(exc)[:300]}, None
        recs.append(rec)
        if fold:
            slug = re.sub(r"[^a-z0-9]+", "-", s["name"].lower()).strip("-")
            with open(os.path.join(args.out_dir, "ebfit_fold_%s.csv" % slug), "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=["family", "dt_d", "n", "flux", "model"])
                w.writeheader()
                for r in fold:
                    w.writerow(r)
        ph = rec.get("phys", {})
        row = {"name": s["name"], "role": s["role"], "label": rec.get("label"), "author": rec.get("author"),
               "n_sectors": len(rec.get("sectors", [])), "n_windows": rec.get("n_windows"),
               "chi2_red": rec.get("chi2_red"), "map_rule": rec.get("mapping", {}).get("rule"),
               "lc1_is": rec.get("mapping", {}).get("lc1_is"),
               "control": (rec.get("control") or {}).get("label", "")}
        for k in ("inc_deg", "M_gaia1", "M_gaia2", "R_lc1", "R_lc2", "R_sum"):
            if k in ph:
                row[k] = ph[k]["median"]
                row[k + "_err"] = ph[k]["sd"]
        for k in ("ecw", "esw", "k", "J", "l3", "rsum"):
            if "theta" in rec:
                row[k] = rec["theta"][k]
                row[k + "_err"] = rec["err_total"][k]
        rows_csv.append(row)
        log("result", s["name"], json.dumps(jclean(row)))
        controls = write_outputs(args.out_dir, meta, recs, rows_csv, final=False)
    controls = write_outputs(args.out_dir, meta, recs, rows_csv, final=True)
    print(json.dumps(jclean({"controls": controls})))
    return 0


def write_outputs(out_dir, meta, recs, rows_csv, final):
    """Written after every star, so a timeout keeps what finished."""
    ctrls = [r for r in recs if r.get("role") == "control"]
    npass = sum(1 for r in ctrls if (r.get("control") or {}).get("label") == "CONTROL_PASS")
    controls = {"n": len(ctrls), "n_pass": npass,
                "label": "CONTROLS_OK" if ctrls and npass >= len(ctrls) - 1 else "CONTROLS_FAIL"}
    meta = dict(meta)
    meta["complete"] = bool(final)
    meta["written"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(out_dir, "ebfit_summary.json"), "w") as fh:
        json.dump(jclean({"meta": meta, "controls": controls, "stars": recs}), fh, indent=1)
    keys = sorted({k for r in rows_csv for k in r}, key=lambda k: (k not in ("name", "role", "label"), k))
    with open(os.path.join(out_dir, "ebfit_params.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows_csv:
            w.writerow(jclean(r))
    return controls


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--config", default="targets.json")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args(argv)
    if a.self_test:
        return 0 if self_test() else 3
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
