#!/usr/bin/env python3
# tyc_pixel.py 0.1.0 -- TYC 6340-23-1 (TIC 71945261) in the TESS sector 92 pixels:
#   Part A  which star dims during the eclipse (the target or the V = 11.25 star 38 arcsec away),
#           and how deep the eclipse is on the target once a PSF model separates the two stars;
#   Part C  eclipse times from the sector 92 pixels (one-sector period and a measured epoch);
#   Part B  a SuperWASP (2006-2008) to TESS (2025) cycle link and a 19-year period.
# By MV2 of Munim, Inc.; made with AI agents working in his name. License: Apache-2.0.
# Rules: findings/2026-11-20-tyc6340-pixel-prereg.md (written before this job ran).
# The analysis core is pure standard library. astropy/numpy are imported only inside the
# functions that read the TESScut file; tyc_period.py (v0.38.0) only inside Part B.
"""Usage:
  python tyc_pixel.py --self-test
  python tyc_pixel.py --data-dir /data/pixel-tyc6340 --wasp-dir /data/wasp-tyc6340 --out-dir /out
Exit codes: 0 ok (labels in tyc_pixel_summary.json); 3 self-test failed; 4 TESScut or Gaia
download failed (re-file unchanged).
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
import zipfile

VERSION = "0.1.0"

# ---- fixed inputs (pre-registered) ----
RA_T, DEC_T = 305.561052, -22.073651
GAIA_T = "6853008555751131648"
RA_N, DEC_N = 305.566500, -22.082972      # the 38 arcsec neighbour (V = 11.25)
SECTOR = 92
CUT = 15
BTJD0 = 2457000.0
P_TESS = 2.3287                           # S92 QLP fit
T0_BTJD = 3803.0299                       # S92 primary eclipse, BTJD (TDB)
T_TESS_BJD = BTJD0 + T0_BTJD
SIG_T_TESS_FIXED = 0.001
P_GAIA = 2.3289298
SIG_P_GAIA = 0.00014
T14, T23 = 0.0990, 0.0324
EPOCH_TESS = 2025.35                      # Julian year of the S92 eclipses (Gaia pm propagation)

IN_HALF = 0.012                           # in-eclipse window (inside the flat bottom +-0.0162 d)
OUT_LO, OUT_HI = 0.065, 0.15              # out-of-eclipse windows on both sides
MIN_IN, MIN_OUT_SIDE = 5, 5
MASK_HALF = 0.08                          # mean image leaves out +-0.08 d of primary and secondary
MIN_ECL = 4

D_REF = 0.0609                            # S92 QLP model depth (findings/2026-11-19-tic71945261-fit-results.md)
R2_FIT, R2_MS = 0.224, 0.117
DEPTH_TOL = 0.15
SURVIVE_R = (1.5 * R2_MS / R2_FIT) ** 2   # 0.614: depth ratio above which R2 stays >= 1.5x MS
WITHDRAW_R = (1.3 * R2_MS / R2_FIT) ** 2  # 0.461: depth ratio below which R2 < 1.3x MS

N_BOOT = 500
N_BOOT_POS = 200
SEED = 20261122
INJ_N = 0.10                              # control C2: dip injected on the neighbour (phase 0.25)
INJ_T = 0.03                              # control C3: dip injected on the target (phase 0.75)
INJ_TOL = 0.30
F_ON, F_OFF = 0.7, 0.3
Z_DET = 5.0
Z_NULL = 3.0
Z_POS = 3.0
SIG_SYS_DEFAULT = 0.15                    # px, if fewer than 3 astrometric control stars
SIG_SYS_MIN = 0.05
CTRL_RP_MAX = 12.5
CTRL_ISO_PX = 3.0
CTRL_ISO_DMAG = 3.0
CTRL_MOVE_MAX = 1.5

FREE_RP = 14.0
FAINT_RP = 17.0
MERGE_PX = 0.6
EDGE_PAD = 2.0
NSUB = 4
HALO_SCALE = 3.0
ROBUST_PX = 5.0

# Part B (SuperWASP link)
WB_P_LO, WB_P_HI, WB_P_STEP = 2.3280, 2.3296, 5e-6
WB_N_BOOT = 200
WB_EDGE_MAX = 0.2
WB_SNR_MIN = 10.0
WB_RATIO = 2.0
Z_PERIOD = 3.0

GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
TESSCUT = "https://mast.stsci.edu/tesscut/api/v0.1/astrocut"
UA = "MV2-Munim-research/0.1 (mv2@munimtech.com)"
NAN = float("nan")

_HALF14 = 0.5 * T14
_HALF23 = 0.5 * T23
_RAMP = _HALF14 - _HALF23


# ---------------------------------------------------------------- small helpers
def median(v):
    s = sorted(x for x in v if x == x)
    n = len(s)
    if n == 0:
        return NAN
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def std(v):
    v = [x for x in v if isinstance(x, (int, float)) and math.isfinite(x)]
    n = len(v)
    if n < 2:
        return NAN
    m = sum(v) / n
    return math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))


def pct(v, q):
    s = sorted(x for x in v if math.isfinite(x))
    if not s:
        return NAN
    k = q * (len(s) - 1)
    lo = int(math.floor(k))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def fold_dt(t, t0, p):
    return ((t - t0 + 0.5 * p) % p) - 0.5 * p


def shape(dt):
    a = abs(dt)
    if a <= _HALF23:
        return 1.0
    if a >= _HALF14:
        return 0.0
    return (_HALF14 - a) / _RAMP


def solve(A, b):
    """Gaussian elimination with partial pivoting. Raises ValueError if singular."""
    n = len(b)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-300:
            raise ValueError("singular")
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]
        for r in range(c + 1, n):
            f = M[r][c] / pv
            if f:
                row_r = M[r]
                row_c = M[c]
                for k in range(c, n + 1):
                    row_r[k] -= f * row_c[k]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = M[i][n] - sum(M[i][k] * x[k] for k in range(i + 1, n))
        x[i] = s / M[i][i]
    return x


def lstsq(cols, y, w, ridge=1e-12):
    """Weighted linear least squares y ~ sum_k coef_k cols_k. Returns (coef, chi2)."""
    K = len(cols)
    wc = [[wi * ci for wi, ci in zip(w, c)] for c in cols]
    A = [[0.0] * K for _ in range(K)]
    bv = [0.0] * K
    for k in range(K):
        wk = wc[k]
        bv[k] = sum(a * b for a, b in zip(wk, y))
        for l in range(k, K):
            v = sum(a * b for a, b in zip(wk, cols[l]))
            A[k][l] = v
            A[l][k] = v
    tr = sum(A[k][k] for k in range(K)) / max(K, 1)
    for k in range(K):
        A[k][k] += ridge * tr
    coef = solve(A, bv)
    model = [0.0] * len(y)
    for k in range(K):
        ck = coef[k]
        col = cols[k]
        model = [m + ck * c for m, c in zip(model, col)]
    chi2 = sum(wi * (yi - mi) ** 2 for wi, yi, mi in zip(w, y, model))
    return coef, chi2


def nelder_mead(f, x0, steps, maxiter=400, xtol=1e-4):
    n = len(x0)
    pts = [list(x0)]
    for i in range(n):
        p = list(x0)
        p[i] += steps[i]
        pts.append(p)
    vals = [f(p) for p in pts]
    it = 0
    while it < maxiter:
        it += 1
        order = sorted(range(n + 1), key=lambda k: vals[k])
        pts = [pts[k] for k in order]
        vals = [vals[k] for k in order]
        size = max(abs(pts[k][i] - pts[0][i]) for k in range(1, n + 1) for i in range(n))
        if size < xtol:
            break
        cen = [sum(p[i] for p in pts[:-1]) / n for i in range(n)]
        xr = [cen[i] + (cen[i] - pts[-1][i]) for i in range(n)]
        fr = f(xr)
        if fr < vals[0]:
            xe = [cen[i] + 2.0 * (cen[i] - pts[-1][i]) for i in range(n)]
            fe = f(xe)
            if fe < fr:
                pts[-1], vals[-1] = xe, fe
            else:
                pts[-1], vals[-1] = xr, fr
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            if fr < vals[-1]:
                xc = [cen[i] + 0.5 * (xr[i] - cen[i]) for i in range(n)]
            else:
                xc = [cen[i] + 0.5 * (pts[-1][i] - cen[i]) for i in range(n)]
            fc = f(xc)
            if fc < min(fr, vals[-1]):
                pts[-1], vals[-1] = xc, fc
            else:
                for k in range(1, n + 1):
                    pts[k] = [pts[0][i] + 0.5 * (pts[k][i] - pts[0][i]) for i in range(n)]
                    vals[k] = f(pts[k])
    k = min(range(n + 1), key=lambda j: vals[j])
    return pts[k], vals[k], it


# ---------------------------------------------------------------- PSF model
def psf_template(x0, y0, ny, nx, par, ns=NSUB):
    """Pixel-integrated PSF (unit total flux): rotated elliptical Gaussian core plus a
    circular Gaussian halo (fraction h, width HALO_SCALE x mean core sigma).
    Pixel (row i, col j) has its centre at (x=j, y=i). Returns a row-major list."""
    sx, sy, rho, h = par
    det = 1.0 - rho * rho
    a = 1.0 / (sx * sx * det)
    c = 1.0 / (sy * sy * det)
    b2 = -2.0 * rho / (sx * sy * det)
    nc = (1.0 - h) / (2.0 * math.pi * sx * sy * math.sqrt(det))
    sh = HALO_SCALE * 0.5 * (sx + sy)
    nh = h / (2.0 * math.pi * sh * sh)
    ih = 0.5 / (sh * sh)
    offs = [(k + 0.5) / ns - 0.5 for k in range(ns)]
    inv = 1.0 / (ns * ns)
    ex = math.exp
    out = [0.0] * (ny * nx)
    for i in range(ny):
        dys = [i + v - y0 for v in offs]
        for j in range(nx):
            dxs = [j + u - x0 for u in offs]
            s = 0.0
            for dy in dys:
                cy = c * dy * dy
                by = b2 * dy
                hy = dy * dy
                for dx in dxs:
                    s += nc * ex(-0.5 * (a * dx * dx + by * dx + cy))
                    if nh:
                        s += nh * ex(-(dx * dx + hy) * ih)
            out[i * nx + j] = s * inv
    return out


def par_ok(par):
    sx, sy, rho, h = par
    return 0.3 < sx < 3.0 and 0.3 < sy < 3.0 and -0.9 < rho < 0.9 and 0.0 <= h <= 0.6


def bkg_cols(ny, nx):
    cx, cy = 0.5 * (nx - 1), 0.5 * (ny - 1)
    one = [1.0] * (ny * nx)
    gx = [(p % nx - cx) / nx for p in range(ny * nx)]
    gy = [(p // nx - cy) / ny for p in range(ny * nx)]
    return [one, gx, gy]


def split_stars(stars):
    """Free-flux stars (target, neighbour, RP < FREE_RP not merged) and the faint group."""
    free = [s for s in stars if s["role"] in ("T", "N")]
    rest = sorted([s for s in stars if s["role"] not in ("T", "N")], key=lambda s: s["rp"])
    faint = []
    for s in rest:
        if s["rp"] < FREE_RP and all(math.hypot(s["x"] - f["x"], s["y"] - f["y"]) > MERGE_PX
                                     for f in free):
            free.append(s)
        elif s["rp"] < FAINT_RP:
            faint.append(s)
    return free, faint


def design(free, faint, par, dx, dy, ny, nx):
    cols = [psf_template(s["x"] + dx, s["y"] + dy, ny, nx, par) for s in free]
    if faint:
        rp0 = min(s["rp"] for s in faint)
        fc = [0.0] * (ny * nx)
        for s in faint:
            wgt = 10.0 ** (-0.4 * (s["rp"] - rp0))
            t = psf_template(s["x"] + dx, s["y"] + dy, ny, nx, par)
            fc = [a + wgt * b for a, b in zip(fc, t)]
        cols.append(fc)
    return cols + bkg_cols(ny, nx)


def pixel_weights(M):
    floor = max(median(M), 1e-3 * max(M), 1.0)
    return [1.0 / max(v, floor) for v in M]


def fit_mean_image(M, stars, ny, nx, maxiter=500, log=print):
    free, faint = split_stars(stars)
    w = pixel_weights(M)

    def f(p):
        dx, dy, sx, sy, rho, h = p
        if not (abs(dx) <= 1.5 and abs(dy) <= 1.5 and par_ok((sx, sy, rho, h))):
            return 1e300
        try:
            _, chi2 = lstsq(design(free, faint, (sx, sy, rho, h), dx, dy, ny, nx), M, w)
        except ValueError:
            return 1e300
        return chi2

    x0 = [0.0, 0.0, 0.8, 0.8, 0.0, 0.15]
    best, val, it1 = nelder_mead(f, x0, [0.3, 0.3, 0.2, 0.2, 0.2, 0.1], maxiter=maxiter)
    best, val, it2 = nelder_mead(f, best, [0.1, 0.1, 0.05, 0.05, 0.05, 0.03], maxiter=maxiter)
    dx, dy, sx, sy, rho, h = best
    par = (sx, sy, rho, h)
    cols = design(free, faint, par, dx, dy, ny, nx)
    coef, chi2 = lstsq(cols, M, w)
    fluxes = {s["id"]: coef[k] for k, s in enumerate(free)}
    log("[mean] dx %.3f dy %.3f sx %.3f sy %.3f rho %.3f h %.3f chi2 %.4g (it %d+%d)" % (
        dx, dy, sx, sy, rho, h, chi2, it1, it2))
    return {"dx": dx, "dy": dy, "par": par, "chi2": chi2, "fluxes": fluxes, "coef": coef,
            "free": free, "faint": faint, "cols": cols, "w": w, "n_free": len(free),
            "n_faint": len(faint)}


def fit_position(D, w, par, starts, ny, nx, maxiter=150):
    """Single PSF at a free position plus a constant; amplitude must be positive."""
    one = [1.0] * len(D)

    def f(p):
        x, y = p
        if not (-1.0 <= x <= nx and -1.0 <= y <= ny):
            return 1e300
        try:
            coef, chi2 = lstsq([psf_template(x, y, ny, nx, par), one], D, w)
        except ValueError:
            return 1e300
        return chi2 if coef[0] > 0 else chi2 + 1e200
    best = None
    for s in starts:
        p, v, _ = nelder_mead(f, list(s), [0.3, 0.3], maxiter=maxiter, xtol=1e-3)
        if best is None or v < best[1]:
            best = (p, v)
    x, y = best[0]
    coef, chi2 = lstsq([psf_template(x, y, ny, nx, par), one], D, w)
    return {"x": x, "y": y, "amp": coef[0], "chi2": chi2}


# ---------------------------------------------------------------- frames and windows
def frame_mean(frames, idx):
    if hasattr(frames, "shape"):
        import numpy as np  # noqa: PLC0415 (job only)
        return [float(v) for v in np.mean(frames[list(idx)], axis=0)]
    idx = list(idx)
    acc = [0.0] * len(frames[idx[0]])
    for i in idx:
        acc = [a + b for a, b in zip(acc, frames[i])]
    return [a / len(idx) for a in acc]


def aperture_series(frames, pix):
    if hasattr(frames, "shape"):
        return [float(v) for v in frames[:, list(pix)].sum(axis=1)]
    return [sum(f[p] for p in pix) for f in frames]


def eclipse_windows(times, t0, p, phase_off=0.0):
    tmin, tmax = min(times), max(times)
    n0 = int(math.floor((tmin - t0) / p)) - 1
    n1 = int(math.ceil((tmax - t0) / p)) + 1
    res = []
    for n in range(n0, n1 + 1):
        tc = t0 + (n + phase_off) * p
        ins, left, right = [], [], []
        for i, t in enumerate(times):
            d = t - tc
            if d < -OUT_HI or d > OUT_HI:
                continue
            if abs(d) <= IN_HALF:
                ins.append(i)
            elif -OUT_HI <= d <= -OUT_LO:
                left.append(i)
            elif OUT_LO <= d <= OUT_HI:
                right.append(i)
        if len(ins) >= MIN_IN and len(left) >= MIN_OUT_SIDE and len(right) >= MIN_OUT_SIDE:
            res.append({"n": n, "tc": tc, "in": ins, "left": left, "right": right})
    return res


def diff_images(frames, wins):
    """D = mean(out) - mean(in), positive where light is lost; out = mean of both sides."""
    out = []
    for e in wins:
        mi = frame_mean(frames, e["in"])
        ml = frame_mean(frames, e["left"])
        mr = frame_mean(frames, e["right"])
        out.append([0.5 * (a + b) - c for a, b, c in zip(ml, mr, mi)])
    return out


def mean_image_index(times, t0, p):
    return [i for i, t in enumerate(times)
            if abs(fold_dt(t, t0, p)) > MASK_HALF and abs(fold_dt(t, t0 + 0.5 * p, p)) > MASK_HALF]


# ---------------------------------------------------------------- labels
def star_label(f_lo, f_hi, z_t, z_n, n_bad_frac=0.0):
    if n_bad_frac > 0.1:
        return "PIX_UNRESOLVED"
    if f_lo >= F_ON and z_t >= Z_DET:
        return "PIX_ON_TARGET"
    if f_hi <= F_OFF and z_n >= Z_DET:
        return "PIX_ON_NEIGHBOUR"
    return "PIX_UNRESOLVED"


def centroid_label(d_t, d_n):
    if not (math.isfinite(d_t) and math.isfinite(d_n)):
        return "CENTROID_UNTESTABLE"
    if d_t < Z_POS and d_n > Z_POS:
        return "CENTROID_ON_TARGET"
    if d_n < Z_POS and d_t > Z_POS:
        return "CENTROID_ON_NEIGHBOUR"
    if d_t < Z_POS and d_n < Z_POS:
        return "CENTROID_AMBIGUOUS"
    return "CENTROID_ELSEWHERE"


def depth_label(d, s, ref=D_REF):
    r = d / ref
    if (1.0 - DEPTH_TOL) <= r <= (1.0 + DEPTH_TOL) or abs(d - ref) <= 2.0 * s:
        return "DEPTH_CONSISTENT"
    return "DEPTH_SHALLOWER" if d < ref else "DEPTH_DEEPER"


def oversize_label(d, s, ref=D_REF):
    lo = (d - 2.0 * s) / ref
    hi = (d + 2.0 * s) / ref
    if lo >= SURVIVE_R:
        return "OVERSIZE_SURVIVES"
    if hi < WITHDRAW_R:
        return "OVERSIZE_WITHDRAWN"
    return "OVERSIZE_WEAKENED"


def link_label(snr_n, snr_alt, edge_frac):
    if edge_frac > WB_EDGE_MAX or not math.isfinite(snr_n):
        return "LINK_AMBIGUOUS"
    if snr_n >= WB_SNR_MIN and snr_n >= WB_RATIO * max(max(snr_alt), 0.0):
        return "LINK_UNIQUE"
    return "LINK_AMBIGUOUS"


# ---------------------------------------------------------------- Part A analysis
def analyse_diffs(Ds, w, col_t, col_n, f_t, f_n, par, pos_t, pos_n, sig_sys, ny, nx,
                  n_boot=N_BOOT, n_boot_pos=N_BOOT_POS, seed=SEED, do_pos=True,
                  extra_cols=None, log=print, tag=""):
    n = len(Ds)
    res = {"n_eclipses": n}
    if n < MIN_ECL:
        res["label"] = "PIX_UNTESTABLE"
        return res
    one = [1.0] * len(w)

    def mean_of(idx):
        acc = [0.0] * len(w)
        for k in idx:
            acc = [a + b for a, b in zip(acc, Ds[k])]
        return [a / len(idx) for a in acc]

    def amps(D, extra=None):
        cols = [col_t, col_n, one] + (extra or [])
        coef, _ = lstsq(cols, D, w)
        return coef[0], coef[1]

    dbar = mean_of(range(n))
    a_t, a_n = amps(dbar)
    res["a_t"], res["a_n"] = a_t, a_n
    res["delta_t"], res["delta_n"] = a_t / f_t, a_n / f_n
    res["per_eclipse_delta_t"] = [amps(D)[0] / f_t for D in Ds]
    res["per_eclipse_delta_n"] = [amps(D)[1] / f_n for D in Ds]
    if extra_cols:
        rt, rn = amps(dbar, extra_cols)
        res["robust_delta_t"], res["robust_delta_n"] = rt / f_t, rn / f_n
    rng = random.Random(seed)
    draws = [[rng.randrange(n) for _ in range(n)] for _ in range(n_boot)]
    bt, bn, bf = [], [], []
    for d in draws:
        t_, n_ = amps(mean_of(d))
        bt.append(t_ / f_t)
        bn.append(n_ / f_n)
        s = t_ + n_
        bf.append(t_ / s if s > 0 else NAN)
    s_t, s_n = std(bt), std(bn)
    n_bad = sum(1 for x in bf if not math.isfinite(x))
    res.update({"sigma_delta_t": s_t, "sigma_delta_n": s_n,
                "z_t": res["delta_t"] / s_t if s_t > 0 else NAN,
                "z_n": res["delta_n"] / s_n if s_n > 0 else NAN,
                "f_t": a_t / (a_t + a_n) if (a_t + a_n) > 0 else NAN,
                "f_t_lo": pct(bf, 0.025), "f_t_hi": pct(bf, 0.975),
                "f_t_undefined_frac": n_bad / max(len(bf), 1)})
    res["label"] = star_label(res["f_t_lo"], res["f_t_hi"], res["z_t"], res["z_n"],
                              res["f_t_undefined_frac"])
    if do_pos:
        starts = [pos_t, pos_n]
        fp = fit_position(dbar, w, par, starts, ny, nx)
        xs, ys = [], []
        for k, d in enumerate(draws[:n_boot_pos]):
            g = fit_position(mean_of(d), w, par, [(fp["x"], fp["y"])], ny, nx, maxiter=100)
            xs.append(g["x"])
            ys.append(g["y"])
            if (k + 1) % 50 == 0:
                log("[pos%s] %d/%d" % (tag, k + 1, n_boot_pos))
        sx = math.hypot(std(xs), sig_sys)
        sy = math.hypot(std(ys), sig_sys)
        d_t = math.hypot((fp["x"] - pos_t[0]) / sx, (fp["y"] - pos_t[1]) / sy)
        d_n = math.hypot((fp["x"] - pos_n[0]) / sx, (fp["y"] - pos_n[1]) / sy)
        res["centroid"] = {"x": fp["x"], "y": fp["y"], "sigma_x": sx, "sigma_y": sy,
                           "sigma_boot_x": std(xs), "sigma_boot_y": std(ys),
                           "sig_sys": sig_sys, "d_target_sigma": d_t,
                           "d_neighbour_sigma": d_n,
                           "offset_target_px": math.hypot(fp["x"] - pos_t[0], fp["y"] - pos_t[1]),
                           "offset_neighbour_px": math.hypot(fp["x"] - pos_n[0],
                                                             fp["y"] - pos_n[1]),
                           "label": centroid_label(d_t, d_n)}
    return res


def astrometric_control(M, mf, stars, ny, nx, log=print):
    """C4: free-position fits of isolated bright stars in the mean image."""
    free = mf["free"]
    cols, coef, w, par = mf["cols"], mf["coef"], mf["w"], mf["par"]
    offs = []
    rows = []
    for k, s in enumerate(free):
        if s["role"] in ("T", "N") or s["rp"] >= CTRL_RP_MAX:
            continue
        x, y = s["x"] + mf["dx"], s["y"] + mf["dy"]
        if not (2.0 <= x <= nx - 3.0 and 2.0 <= y <= ny - 3.0):
            continue
        iso = all(not (o is not s and o["rp"] < s["rp"] + CTRL_ISO_DMAG
                       and math.hypot(o["x"] - s["x"], o["y"] - s["y"]) < CTRL_ISO_PX)
                  for o in stars)
        if not iso:
            continue
        model_other = [0.0] * len(M)
        for j, c in enumerate(cols):
            if j == k:
                continue
            model_other = [m + coef[j] * v for m, v in zip(model_other, c)]
        R = [a - b for a, b in zip(M, model_other)]
        g = fit_position(R, w, par, [(x, y)], ny, nx)
        ox, oy = g["x"] - x, g["y"] - y
        moved = math.hypot(ox, oy) > CTRL_MOVE_MAX
        rows.append({"id": s["id"], "rp": s["rp"], "dx": ox, "dy": oy, "excluded": moved})
        if not moved:
            offs.append((ox, oy))
    if len(offs) >= 3:
        rx = math.sqrt(sum(o[0] ** 2 for o in offs) / len(offs))
        ry = math.sqrt(sum(o[1] ** 2 for o in offs) / len(offs))
        sig = max(math.hypot(rx, ry) / math.sqrt(2.0), SIG_SYS_MIN)
    else:
        sig = SIG_SYS_DEFAULT
    log("[C4] %d control stars, sigma_sys %.3f px" % (len(offs), sig))
    return {"n_used": len(offs), "stars": rows, "sigma_sys_px": sig}


def run_part_a(times, frames, stars, ny, nx, scale_arcsec, n_boot=N_BOOT,
               n_boot_pos=N_BOOT_POS, seed=SEED, maxiter=500, log=print):
    out = {}
    midx = mean_image_index(times, T0_BTJD, P_TESS)
    M = frame_mean(frames, midx)
    out["n_frames"] = len(times)
    out["n_mean_frames"] = len(midx)
    mf = fit_mean_image(M, stars, ny, nx, maxiter=maxiter, log=log)
    free = mf["free"]
    k_t = [k for k, s in enumerate(free) if s["role"] == "T"][0]
    k_n = [k for k, s in enumerate(free) if s["role"] == "N"][0]
    f_t, f_n = mf["coef"][k_t], mf["coef"][k_n]
    col_t, col_n = mf["cols"][k_t], mf["cols"][k_n]
    pos_t = (free[k_t]["x"] + mf["dx"], free[k_t]["y"] + mf["dy"])
    pos_n = (free[k_n]["x"] + mf["dx"], free[k_n]["y"] + mf["dy"])
    sep_px = math.hypot(pos_t[0] - pos_n[0], pos_t[1] - pos_n[1])
    extra = [mf["cols"][k] for k, s in enumerate(free)
             if s["role"] not in ("T", "N")
             and math.hypot(s["x"] - free[k_t]["x"], s["y"] - free[k_t]["y"]) < ROBUST_PX]
    out["mean_fit"] = {"dx": mf["dx"], "dy": mf["dy"], "psf": list(mf["par"]),
                       "chi2": mf["chi2"], "n_free": mf["n_free"], "n_faint": mf["n_faint"],
                       "flux_target": f_t, "flux_neighbour": f_n,
                       "flux_ratio_n_over_t": f_n / f_t if f_t else NAN,
                       "pos_target": pos_t, "pos_neighbour": pos_n, "sep_px": sep_px,
                       "arcsec_per_px": scale_arcsec, "n_robust_extra": len(extra)}
    w = mf["w"]
    out["C4_astrometry"] = astrometric_control(M, mf, stars, ny, nx, log=log)
    sig_sys = out["C4_astrometry"]["sigma_sys_px"]
    common = dict(sig_sys=sig_sys, ny=ny, nx=nx, n_boot=n_boot, n_boot_pos=n_boot_pos,
                  seed=seed, log=log)
    W0 = eclipse_windows(times, T0_BTJD, P_TESS)
    W25 = eclipse_windows(times, T0_BTJD, P_TESS, 0.25)
    W75 = eclipse_windows(times, T0_BTJD, P_TESS, 0.75)
    out["n_windows"] = {"primary": len(W0), "phase_0.25": len(W25), "phase_0.75": len(W75)}
    out["eclipse_epochs"] = [e["tc"] for e in W0]
    if min(len(W0), len(W25), len(W75)) < MIN_ECL:
        out["L0"] = "PIX_UNTESTABLE"
        return out, M, mf, None
    D0, D25, D75 = diff_images(frames, W0), diff_images(frames, W25), diff_images(frames, W75)
    # C1 nulls
    c1 = {}
    for tag, Ds in (("0.25", D25), ("0.75", D75)):
        r = analyse_diffs(Ds, w, col_t, col_n, f_t, f_n, mf["par"], pos_t, pos_n,
                          do_pos=False, tag=tag, **common)
        c1[tag] = {k: r.get(k) for k in ("delta_t", "delta_n", "sigma_delta_t",
                                          "sigma_delta_n", "z_t", "z_n")}
        c1[tag]["pass"] = abs(r["z_t"]) < Z_NULL and abs(r["z_n"]) < Z_NULL
    c1["pass"] = c1["0.25"]["pass"] and c1["0.75"]["pass"]
    out["C1_null"] = c1
    log("[C1] null pass %s" % c1["pass"])
    # C2 injection on the neighbour (phase 0.25)
    injN = [[d + INJ_N * f_n * c for d, c in zip(D, col_n)] for D in D25]
    r2 = analyse_diffs(injN, w, col_t, col_n, f_t, f_n, mf["par"], pos_t, pos_n,
                       tag="C2", **common)
    c2_pass = (r2["label"] == "PIX_ON_NEIGHBOUR"
               and abs(r2["delta_n"] - INJ_N) <= INJ_TOL * INJ_N
               and r2["centroid"]["label"] == "CENTROID_ON_NEIGHBOUR")
    out["C2_inject_neighbour"] = {"label": r2["label"], "delta_n": r2["delta_n"],
                                  "delta_t": r2["delta_t"],
                                  "centroid": r2["centroid"]["label"], "pass": c2_pass}
    log("[C2] %s delta_n %.4f centroid %s pass %s" % (r2["label"], r2["delta_n"],
                                                     r2["centroid"]["label"], c2_pass))
    # C3 injection on the target (phase 0.75)
    injT = [[d + INJ_T * f_t * c for d, c in zip(D, col_t)] for D in D75]
    r3 = analyse_diffs(injT, w, col_t, col_n, f_t, f_n, mf["par"], pos_t, pos_n,
                       tag="C3", **common)
    c3_pass = (r3["label"] == "PIX_ON_TARGET"
               and abs(r3["delta_t"] - INJ_T) <= INJ_TOL * INJ_T
               and r3["centroid"]["label"] == "CENTROID_ON_TARGET")
    out["C3_inject_target"] = {"label": r3["label"], "delta_t": r3["delta_t"],
                               "delta_n": r3["delta_n"],
                               "centroid": r3["centroid"]["label"], "pass": c3_pass}
    log("[C3] %s delta_t %.4f centroid %s pass %s" % (r3["label"], r3["delta_t"],
                                                     r3["centroid"]["label"], c3_pass))
    sensitive = c1["pass"] and c2_pass and c3_pass
    out["L0"] = "PIX_SENSITIVE" if sensitive else "PIX_INSENSITIVE"
    # the real eclipse
    r = analyse_diffs(D0, w, col_t, col_n, f_t, f_n, mf["par"], pos_t, pos_n,
                      extra_cols=extra, tag="A", **common)
    out["A_eclipse"] = r
    out["L1_star"] = r["label"]
    out["L2_centroid"] = r["centroid"]["label"]
    if r["label"] == "PIX_ON_TARGET":
        out["L3_depth"] = depth_label(r["delta_t"], r["sigma_delta_t"])
        out["L4_oversize"] = oversize_label(r["delta_t"], r["sigma_delta_t"])
        out["depth_ratio"] = r["delta_t"] / D_REF
        out["R2_implied_rsun"] = R2_FIT * math.sqrt(max(r["delta_t"], 0.0) / D_REF)
    elif r["label"] == "PIX_ON_NEIGHBOUR":
        out["L3_depth"] = "DEPTH_NOT_GRADED"
        out["L4_oversize"] = "OVERSIZE_WITHDRAWN"
    else:
        out["L3_depth"] = "DEPTH_NOT_GRADED"
        out["L4_oversize"] = "OVERSIZE_NOT_GRADED"
    out["graded"] = sensitive
    log("[A] %s centroid %s delta_t %.4f +- %.4f delta_n %.4f +- %.4f f_t %.3f [%.3f, %.3f]" % (
        r["label"], r["centroid"]["label"], r["delta_t"], r["sigma_delta_t"], r["delta_n"],
        r["sigma_delta_n"], r["f_t"], r["f_t_lo"], r["f_t_hi"]))
    dbar = [sum(v) / len(D0) for v in zip(*D0)]
    return out, M, mf, dbar


# ---------------------------------------------------------------- Part C: TESS eclipse times
def linfit(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx if sxx > 0 else 0.0
    return my - b * mx, b


def tess_timing(times, flux, t0=T0_BTJD, p=P_TESS, log=print):
    wins = eclipse_windows(times, t0, p)
    segs = []
    for e in wins:
        tc = e["tc"]
        io_ = e["left"] + e["right"]
        a, b = linfit([times[i] - tc for i in io_], [flux[i] for i in io_])
        pts = []
        lo = min(e["left"])
        hi = max(e["right"])
        for i in range(lo, hi + 1):
            d = times[i] - tc
            if abs(d) <= OUT_HI:
                base = a + b * d
                if base > 0:
                    pts.append((d, 1.0 - flux[i] / base))
        resid_out = [r for d, r in pts if abs(d) >= OUT_LO]
        sg = std(resid_out)
        segs.append({"n": e["n"], "tc": tc, "pts": pts,
                     "sig": sg if math.isfinite(sg) and sg > 0 else 1.0})
    if len(segs) < MIN_ECL:
        return {"label": "TIMING_UNTESTABLE", "n_eclipses": len(segs)}
    best = None
    for k in range(-50, 51):
        off = k * 2e-4
        num = den = 0.0
        for s in segs:
            iv = 1.0 / max(s["sig"], 1e-6) ** 2
            for d, r in s["pts"]:
                sh = shape(d - off)
                num += iv * r * sh
                den += iv * sh * sh
        if den > 0 and (best is None or num * num / den > best[0]):
            best = (num * num / den, off, num / den)
    depth = best[2]
    times_e = []
    for s in segs:
        sig = max(s["sig"], 1e-6)
        chis = []
        for k in range(-300, 301):
            off = k * 5e-5
            c = sum((r - depth * shape(d - off)) ** 2 for d, r in s["pts"]) / sig ** 2
            chis.append((c, off))
        cmin, omin = min(chis)
        within = [o for c, o in chis if c <= cmin + 1.0]
        err = max(0.5 * (max(within) - min(within)), 5e-5)
        times_e.append({"n": s["n"], "t": s["tc"] + omin, "sigma": err, "edge": abs(omin) > 0.0149})
    good = [e for e in times_e if not e["edge"]]
    if len(good) < MIN_ECL:
        return {"label": "TIMING_UNTESTABLE", "n_eclipses": len(good), "times": times_e}
    nm = int(round(median([e["n"] for e in good])))
    xs = [e["n"] - nm for e in good]
    ws = [1.0 / e["sigma"] ** 2 for e in good]
    sw = sum(ws)
    mx = sum(w * x for w, x in zip(ws, xs)) / sw
    my = sum(w * e["t"] for w, e in zip(ws, good)) / sw
    sxx = sum(w * (x - mx) ** 2 for w, x in zip(ws, xs))
    pp = sum(w * (x - mx) * (e["t"] - my) for w, x, e in zip(ws, xs, good)) / sxx
    tref = my - pp * mx
    res = [e["t"] - (tref + pp * x) for e, x in zip(good, xs)]
    chi2r = sum(w * r * r for w, r in zip(ws, res)) / max(len(good) - 2, 1)
    scale = math.sqrt(max(chi2r, 1.0))
    s_p = scale / math.sqrt(sxx)
    s_t = scale * math.sqrt(1.0 / sw + mx * mx / sxx)
    log("[C] T_ref BTJD %.5f +- %.5f P %.6f +- %.6f (n %d, chi2r %.2f)" % (
        tref, s_t, pp, s_p, len(good), chi2r))
    return {"label": "TIMING_OK", "n_eclipses": len(good), "depth_window_fit": depth,
            "n_ref": nm, "T_ref_btjd": tref, "T_ref_bjd_tdb": tref + BTJD0, "sigma_T": s_t,
            "P": pp, "sigma_P": s_p, "chi2_red": chi2r, "times": times_e,
            "o_minus_c_d": res}


# ---------------------------------------------------------------- Part B: SuperWASP link
def wasp_link_from_rows(rows, t_tess, s_tess, n_boot=WB_N_BOOT, seed=SEED, log=print,
                        p_lo=WB_P_LO, p_hi=WB_P_HI, p_step=WB_P_STEP):
    import tyc_period as tp  # noqa: PLC0415 (v0.38.0, same repo)
    lc = tp.build_lc(rows)
    tp.detrend_free(lc)
    sc = tp.scan(lc, t_tess, p_lo, p_hi, p_step)
    best = tp.best_of(sc)
    t_mid = tp.median(lc["t"])
    tc = tp.box_epoch_near(best, t_tess, t_mid)
    pb = best["period"]
    g1 = tp.grid_fit(lc, pb, tc, 0.0, 0.0, 0.03, 0.0005)
    if g1 is None:
        return {"label": "LINK_AMBIGUOUS", "error": "no WASP points near the eclipse",
                "scan_best": {"period": pb, "snr": best["snr"]}}
    wc = tp.weighted_centre(lc, pb, g1["t0"])
    tw0 = g1["t0"] + round((wc - g1["t0"]) / pb) * pb if wc is not None else g1["t0"]
    g2 = tp.grid_fit(lc, pb, tw0, 0.0, 0.0, 0.006, 0.0001)
    t_w = g2["t0"]
    draws = tp.night_draws(lc["night"], n_boot, seed)
    bt = []
    n_edge = 0
    for m in draws:
        g = tp.grid_fit(lc, pb, t_w, 0.0, 0.0, 0.012, 0.0002, mult=m)
        if g is None:
            continue
        bt.append(g["t0"])
        n_edge += 1 if g["edge"] else 0
    s_w = std(bt)
    edge = n_edge / max(len(bt), 1)
    n_c = int(round((t_tess - t_w) / pb))
    links = []
    for k in (n_c - 1, n_c, n_c + 1):
        pk = (t_tess - t_w) / k
        d = tp.depth_fit(lc, pk, t_tess)
        snr = d["depth"] / d["sigma_white"] if d["sigma_white"] > 0 else NAN
        spk = math.hypot(s_w, s_tess) / k
        links.append({"N": k, "P": pk, "sigma_P": spk, "depth": d["depth"], "snr": snr,
                      "z_gaia": (pk - P_GAIA) / math.hypot(spk, SIG_P_GAIA)})
    snr_n = links[1]["snr"]
    lab = link_label(snr_n, [links[0]["snr"], links[2]["snr"]], edge)
    out = {"scan_best": {"period": pb, "snr": best["snr"], "depth": best["depth"]},
           "T_W_bjd": t_w, "sigma_T_W": s_w, "boot_edge_fraction": edge, "n_boot": len(bt),
           "wasp_depth_at_T_W": g2["depth"], "links": links, "label": lab,
           "chi2_red_after_free_detrend": lc["chi2_red"],
           "t_first": min(lc["t"]), "t_last": max(lc["t"])}
    if lab == "LINK_UNIQUE":
        L = links[1]
        out["P_19yr"] = L["P"]
        out["sigma_P_19yr"] = L["sigma_P"]
        out["gaia_label"] = "GAIA_PERIOD_OK" if abs(L["z_gaia"]) <= Z_PERIOD else "GAIA_PERIOD_OFF"
    log("[B] T_W %.5f +- %.5f N %d P %.7f snr %s label %s" % (
        t_w, s_w, n_c, links[1]["P"], ["%.1f" % L["snr"] for L in links], lab))
    return out


# ---------------------------------------------------------------- I/O (job only)
def http_get(url, timeout=600, tries=3, data=None):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(10 * (k + 1))
    raise RuntimeError("download failed %s: %s" % (url, last))


def fetch_tesscut(data_dir, log=print):
    fits_path = os.path.join(data_dir, "tesscut_s%04d_%dx%d.fits" % (SECTOR, CUT, CUT))
    if os.path.exists(fits_path) and os.path.getsize(fits_path) > 100000:
        return fits_path
    q = urllib.parse.urlencode({"ra": RA_T, "dec": DEC_T, "y": CUT, "x": CUT, "sector": SECTOR})
    blob = http_get(TESSCUT + "?" + q)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = [n for n in z.namelist() if n.endswith(".fits")]
        if not names:
            raise RuntimeError("TESScut zip has no FITS file")
        with open(fits_path, "wb") as f:
            f.write(z.read(names[0]))
        log("[fetch] TESScut %s (%d bytes)" % (names[0], os.path.getsize(fits_path)))
    return fits_path


def read_tesscut(path):
    import numpy as np  # noqa: PLC0415
    from astropy.io import fits  # noqa: PLC0415
    from astropy.wcs import WCS  # noqa: PLC0415
    with fits.open(path) as hd:
        tab = hd[1].data
        t = np.asarray(tab["TIME"], dtype=float)
        fl = np.asarray(tab["FLUX"], dtype=float)
        q = np.asarray(tab["QUALITY"], dtype=int)
        n, ny, nx = fl.shape
        flat = fl.reshape(n, ny * nx)
        good = np.isfinite(t) & (q == 0) & np.all(np.isfinite(flat), axis=1)
        wcs = None
        try:
            w2 = WCS(hd[2].header)
            if w2.has_celestial:
                wcs = w2.celestial
        except Exception:  # noqa: BLE001
            wcs = None
        if wcs is None:
            h1 = hd[1].header
            keys = {"1CTYP5": "CTYPE1", "2CTYP5": "CTYPE2", "1CRPX5": "CRPIX1",
                    "2CRPX5": "CRPIX2", "1CRVL5": "CRVAL1", "2CRVL5": "CRVAL2",
                    "1CUNI5": "CUNIT1", "2CUNI5": "CUNIT2", "1CDLT5": "CDELT1",
                    "2CDLT5": "CDELT2", "11PC5": "PC1_1", "12PC5": "PC1_2",
                    "21PC5": "PC2_1", "22PC5": "PC2_2"}
            wcs = WCS({v: h1[k] for k, v in keys.items() if k in h1})
        info = {"n_cadences": int(n), "n_good": int(good.sum()), "ny": int(ny), "nx": int(nx),
                "t_first": float(np.nanmin(t)), "t_last": float(np.nanmax(t))}
    return [float(v) for v in t[good]], flat[good], wcs, info


def fetch_gaia_field(data_dir, log=print):
    path = os.path.join(data_dir, "gaia_field.csv")
    if not (os.path.exists(path) and os.path.getsize(path) > 200):
        q = ("SELECT source_id, ra, dec, pmra, pmdec, phot_g_mean_mag, phot_rp_mean_mag "
             "FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT('ICRS',ra,dec),"
             "CIRCLE('ICRS',%.6f,%.6f,0.075)) AND phot_rp_mean_mag < %.1f" % (RA_T, DEC_T,
                                                                              FAINT_RP))
        body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                       "QUERY": q}).encode()
        blob = http_get(GAIA_TAP, timeout=120, data=body)
        with open(path, "wb") as f:
            f.write(blob)
    with open(path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    log("[fetch] Gaia field %d stars" % len(rows))
    return rows


def ang_sep_arcsec(ra1, de1, ra2, de2):
    r1, d1, r2, d2 = map(math.radians, (ra1, de1, ra2, de2))
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 3600.0


def build_stars(rows, wcs, ny, nx):
    dt = EPOCH_TESS - 2016.0
    stars = []
    for r in rows:
        try:
            ra, de, rp = float(r["ra"]), float(r["dec"]), float(r["phot_rp_mean_mag"])
        except (TypeError, ValueError):
            continue
        try:
            pmra, pmde = float(r["pmra"]), float(r["pmdec"])
        except (TypeError, ValueError):
            pmra = pmde = 0.0
        ra += pmra * dt / 3.6e6 / math.cos(math.radians(de))
        de += pmde * dt / 3.6e6
        x, y = wcs.all_world2pix([[ra, de]], 0)[0]
        x, y = float(x), float(y)
        if -EDGE_PAD <= x <= nx - 1 + EDGE_PAD and -EDGE_PAD <= y <= ny - 1 + EDGE_PAD:
            stars.append({"id": str(r["source_id"]), "ra": ra, "dec": de, "rp": rp,
                          "g": float(r["phot_g_mean_mag"]) if r.get("phot_g_mean_mag") else NAN,
                          "x": x, "y": y, "role": "other"})
    tg = [s for s in stars if s["id"] == GAIA_T]
    if not tg:
        raise RuntimeError("target not in Gaia field")
    tg[0]["role"] = "T"
    cand = [s for s in stars if s["role"] != "T" and s["g"] < 13.0
            and ang_sep_arcsec(s["ra"], s["dec"], RA_N, DEC_N) < 5.0]
    if not cand:
        raise RuntimeError("38 arcsec neighbour not in Gaia field")
    nb = min(cand, key=lambda s: ang_sep_arcsec(s["ra"], s["dec"], RA_N, DEC_N))
    nb["role"] = "N"
    scale = ang_sep_arcsec(tg[0]["ra"], tg[0]["dec"], nb["ra"], nb["dec"]) / math.hypot(
        tg[0]["x"] - nb["x"], tg[0]["y"] - nb["y"])
    return stars, scale


def clean_json(o):
    if isinstance(o, dict):
        return {str(k): clean_json(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [clean_json(v) for v in o]
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


# ---------------------------------------------------------------- self-test
def make_synth(seed, dip_role, depth, ny=11, nx=11, days=12.0, cad=0.002, shift=(0.2, -0.15)):
    """Synthetic cutout: target, a neighbour 1.7 px away, two faint stars; Poisson-like noise.
    Returns (times, frames, stars-as-catalogued [positions offset by -shift])."""
    rng = random.Random(seed)
    par = (0.75, 0.65, 0.15, 0.1)
    truth = [("T", 5.0, 5.2, 50000.0, 10.1), ("N", 6.5, 4.4, 29000.0, 10.7),
             ("a", 2.0, 8.0, 3000.0, 13.2), ("b", 9.0, 2.0, 2000.0, 13.6),
             ("c", 8.5, 8.6, 9000.0, 12.0)]
    tmpl = {s[0]: psf_template(s[1], s[2], ny, nx, par) for s in truth}
    flux = {s[0]: s[3] for s in truth}
    bkg = 100.0
    times, frames = [], []
    t = T0_BTJD - 1.3
    while t < T0_BTJD - 1.3 + days:
        img = [bkg] * (ny * nx)
        for name, *_ in truth:
            f = flux[name]
            if name == dip_role and depth:
                f *= 1.0 - depth * shape(fold_dt(t, T0_BTJD, P_TESS))
            img = [a + f * b for a, b in zip(img, tmpl[name])]
        img = [v + rng.gauss(0.0, math.sqrt(max(v, 1.0))) for v in img]
        times.append(t)
        frames.append(img)
        t += cad
    stars = []
    for name, x, y, f, rp in truth:
        stars.append({"id": name, "x": x - shift[0], "y": y - shift[1], "rp": rp,
                      "role": name if name in ("T", "N") else "other"})
    return times, frames, stars, par


def self_test(log=print):
    checks = {}
    q = lambda s: None  # noqa: E731
    # unit-level
    t = psf_template(7.0, 7.0, 15, 15, (0.8, 0.7, 0.2, 0.0))
    checks["psf_norm"] = abs(sum(t) - 1.0) < 2e-3
    # eclipse on the target
    times, frames, stars, par = make_synth(1, "T", 0.06)
    a, M, mf, _ = run_part_a(times, frames, stars, 11, 11, 21.0, n_boot=60, n_boot_pos=15,
                             maxiter=400, log=q)
    checks["offset"] = abs(mf["dx"] - 0.2) < 0.05 and abs(mf["dy"] + 0.15) < 0.05
    checks["psf_width"] = abs(mf["par"][0] - par[0]) < 0.1 * par[0]
    checks["L0_sensitive"] = a.get("L0") == "PIX_SENSITIVE"
    checks["T_on_target"] = a.get("L1_star") == "PIX_ON_TARGET"
    checks["T_centroid"] = a.get("L2_centroid") == "CENTROID_ON_TARGET"
    d = a.get("A_eclipse", {}).get("delta_t", 0.0)
    checks["T_depth"] = abs(d - 0.06) < 0.006
    log("[self-test] target case: L0 %s L1 %s L2 %s delta_t %.4f C1 %s C2 %s C3 %s" % (
        a.get("L0"), a.get("L1_star"), a.get("L2_centroid"), d,
        a.get("C1_null", {}).get("pass"), a.get("C2_inject_neighbour", {}).get("pass"),
        a.get("C3_inject_target", {}).get("pass")))
    # timing on the same data (3x3 aperture on the target)
    ap = [i * 11 + j for i in range(4, 7) for j in range(4, 7)]
    tm = tess_timing(times, aperture_series(frames, ap), log=q)
    checks["timing"] = (tm.get("label") == "TIMING_OK"
                        and abs(fold_dt(tm["T_ref_btjd"], T0_BTJD, P_TESS)) < 0.001
                        and abs(tm["P"] - P_TESS) < 3e-4)
    # eclipse on the neighbour
    times, frames, stars, par = make_synth(2, "N", 0.12)
    b, _, _, _ = run_part_a(times, frames, stars, 11, 11, 21.0, n_boot=60, n_boot_pos=15,
                            maxiter=400, log=q)
    checks["N_on_neighbour"] = b.get("L1_star") == "PIX_ON_NEIGHBOUR"
    checks["N_centroid"] = b.get("L2_centroid") == "CENTROID_ON_NEIGHBOUR"
    checks["N_oversize_withdrawn"] = b.get("L4_oversize") == "OVERSIZE_WITHDRAWN"
    # WASP link (needs tyc_period.py next to this file)
    try:
        import tyc_period as tp  # noqa: PLC0415
        p_true = 2.328785
        t_tess = T_TESS_BJD
        rows = tp.make_wasp_synth(5, 0.06, p_true, t_tess)
        wl = wasp_link_from_rows(rows, t_tess, 0.0005, n_boot=30, log=q)
        L = wl["links"][1]
        checks["wasp_link"] = (wl["label"] == "LINK_UNIQUE"
                               and abs(L["P"] - p_true) < 3e-6)
        log("[self-test] wasp link %s P %.7f snr %s" % (
            wl["label"], L["P"], [round(x["snr"], 1) for x in wl["links"]]))
    except ImportError:
        checks["wasp_link"] = False
    ok = True
    for k, v in checks.items():
        log("[self-test] %-22s %s" % (k, "ok" if v else "FAIL"))
        ok = ok and v
    return ok


# ---------------------------------------------------------------- main
def report(out):
    A = out.get("A", {})
    B = out.get("B_wasp_link", {})
    C = out.get("C_tess_timing", {})
    lines = ["# tyc_pixel %s report" % VERSION, "",
             "- L0 sensitivity: **%s**" % A.get("L0"),
             "- L1 which star (PSF amplitudes): **%s**" % A.get("L1_star"),
             "- L2 centroid of the eclipse signal: **%s**" % A.get("L2_centroid"),
             "- L3 deblended depth: **%s**" % A.get("L3_depth"),
             "- L4 oversized companion: **%s**" % A.get("L4_oversize"),
             "- C TESS timing: **%s**" % C.get("label"),
             "- B SuperWASP-TESS link: **%s** (%s)" % (B.get("label"), B.get("gaia_label")),
             "", "```", json.dumps(clean_json(out), indent=1, default=str)[:60000], "```"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--wasp-dir", default="wasp")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    if a.self_test:
        ok = self_test()
        print("SELF_TEST_OK" if ok else "SELF_TEST_FAILED")
        return 0 if ok else 3
    os.makedirs(a.data_dir, exist_ok=True)
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "stage": "start"}
    summ = os.path.join(a.out_dir, "tyc_pixel_summary.json")

    def save():
        with open(summ, "w", encoding="utf-8") as f:
            json.dump(clean_json(out), f, indent=1, default=str)

    try:
        path = fetch_tesscut(a.data_dir)
        times, frames, wcs, info = read_tesscut(path)
        grows = fetch_gaia_field(a.data_dir)
        stars, scale = build_stars(grows, wcs, info["ny"], info["nx"])
    except Exception as exc:  # noqa: BLE001
        out["stage"] = "fetch_failed"
        out["error"] = str(exc)
        save()
        print("FETCH_FAILED", exc)
        return 4
    ny, nx = info["ny"], info["nx"]
    out["tesscut"] = info
    out["stars_in_model"] = len(stars)
    tg = [s for s in stars if s["role"] == "T"][0]
    nb = [s for s in stars if s["role"] == "N"][0]
    out["target_px"] = (tg["x"], tg["y"])
    out["neighbour_px"] = (nb["x"], nb["y"])
    out["neighbour"] = {"id": nb["id"], "rp": nb["rp"], "g": nb["g"]}
    out["target_rp"] = tg["rp"]
    out["stage"] = "fetched"
    save()
    A, M, mf, dbar = run_part_a(times, frames, stars, ny, nx, scale)
    out["A"] = A
    out["stage"] = "A"
    save()
    # per-pixel map
    with open(os.path.join(a.out_dir, "pixel_depth_map.csv"), "w", encoding="utf-8") as f:
        f.write("row,col,mean_flux,diff_flux,frac_depth,model_target_frac,model_neighbour_frac\n")
        free = mf["free"]
        kt = [k for k, s in enumerate(free) if s["role"] == "T"][0]
        kn = [k for k, s in enumerate(free) if s["role"] == "N"][0]
        for p in range(ny * nx):
            tot = sum(mf["coef"][k] * mf["cols"][k][p] for k in range(len(mf["cols"])))
            ft = mf["coef"][kt] * mf["cols"][kt][p] / tot if tot > 0 else NAN
            fn = mf["coef"][kn] * mf["cols"][kn][p] / tot if tot > 0 else NAN
            dv = dbar[p] if dbar is not None else NAN
            f.write("%d,%d,%.3f,%.4f,%.6f,%.4f,%.4f\n" % (
                p // nx, p % nx, M[p], dv, dv / M[p] if M[p] > 0 else NAN, ft, fn))
    # Part C: TESS timing on a 3x3 aperture centred on the target's brightest model pixel
    kt = [k for k, s in enumerate(mf["free"]) if s["role"] == "T"][0]
    col_t = mf["cols"][kt]
    pk = max(range(ny * nx), key=lambda p: col_t[p])
    r0, c0 = pk // nx, pk % nx
    ap_pix = [i * nx + j for i in range(max(r0 - 1, 0), min(r0 + 2, ny))
              for j in range(max(c0 - 1, 0), min(c0 + 2, nx))]
    C = tess_timing(times, aperture_series(frames, ap_pix))
    C["aperture_centre"] = [r0, c0]
    out["C_tess_timing"] = C
    out["stage"] = "C"
    save()
    with open(os.path.join(a.out_dir, "tess_eclipse_times.csv"), "w", encoding="utf-8") as f:
        f.write("cycle,t_btjd,sigma_d,edge\n")
        for e in C.get("times", []):
            f.write("%d,%.6f,%.6f,%s\n" % (e["n"], e["t"], e["sigma"], e["edge"]))
    # Part B: SuperWASP link, anchored on the pixel-measured TESS epoch when available
    if C.get("label") == "TIMING_OK":
        t_tess, s_tess = C["T_ref_bjd_tdb"], C["sigma_T"]
        anchor = "pixel_timing"
    else:
        t_tess, s_tess = T_TESS_BJD, SIG_T_TESS_FIXED
        anchor = "fixed_qlp_epoch"
    try:
        import tyc_period as tp  # noqa: PLC0415
        rows = tp.wasp_rows(tp.WASP_TARGET, a.wasp_dir)
        if rows:
            B = wasp_link_from_rows(rows, t_tess, s_tess)
        else:
            B = {"label": "LINK_UNTESTABLE", "error": "no SuperWASP data"}
    except Exception as exc:  # noqa: BLE001
        B = {"label": "LINK_UNTESTABLE", "error": str(exc)}
    B["anchor"] = anchor
    out["B_wasp_link"] = B
    if B.get("links"):
        with open(os.path.join(a.out_dir, "wasp_link.csv"), "w", encoding="utf-8") as f:
            f.write("N,P,sigma_P,depth,snr,z_gaia\n")
            for L in B["links"]:
                f.write("%d,%.8f,%.8f,%.5f,%.3f,%.3f\n" % (L["N"], L["P"], L["sigma_P"],
                                                           L["depth"], L["snr"], L["z_gaia"]))
    out["stage"] = "done"
    save()
    with open(os.path.join(a.out_dir, "tyc_pixel_report.md"), "w", encoding="utf-8") as f:
        f.write(report(out))
    print(json.dumps({"L0": A.get("L0"), "L1": A.get("L1_star"), "L2": A.get("L2_centroid"),
                      "L3": A.get("L3_depth"), "L4": A.get("L4_oversize"),
                      "C": C.get("label"), "B": B.get("label"),
                      "gaia": B.get("gaia_label")}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
