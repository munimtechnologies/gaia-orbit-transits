# SPDX-License-Identifier: Apache-2.0
"""Eclipse-model fits for Gaia-weighed eclipsing low-mass companions (EBLM-like systems).

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.

Why this module exists. eblm_screen.py 0.1.0 (job gaia-eblm-v1) called astropy's
BoxLeastSquares without flux errors, so dy defaulted to 1 and its "SNR" was about
depth x sqrt(N): 1-3 for eclipses 1-11 % deep. Every star got NO_ECLIPSE although the
folded TESS light curves show clear eclipses. Its depths were box averages, not eclipse
depths. This module replaces that TESS stage:

 1. same Gaia sample and classes (eblm_screen.sample_adql / classify, unchanged);
 2. same TESS light curves and detrending (eblm_screen.load_tess / detrend, unchanged);
 3. BLS with real errors, only to find the phase of the primary eclipse;
 4. a physical eclipse model fitted to the phase-binned light curve: a quadratic
    limb-darkened primary (ring integration, exact for any k, b), the companion's
    occultation, and harmonics up to 3rd order for ellipsoidal, reflection and beaming
    variation; exposure-time smoothing;
 5. detection from the chi-square gain of the eclipse model (snr_fit);
 6. the primary's radius from the light curve (a/R1 and Kepler's law with the Gaia SB1
    mass), so the companion's radius does not rest on the FLAME radius alone;
 7. the true companion mass from the SB1 mass function and the fitted inclination;
 8. pre-registered verdicts and the short-period radius-inflation statistic.

0.2.0 (fixes fixed in findings/2026-11-19-eblm-holdout-prereg.md before any holdout fit,
after 0.1.0 failed its outside check, findings/2026-11-19-eblm-control-results.md):
 (a) the ellipsoidal amplitude's error includes red noise: the larger of the white-noise
     error times a time-binned beta factor (Winn et al. 2008 style, bins P/16, P/8, P/4)
     and the segment-to-segment scatter of the amplitude with the eclipse shape fixed
     (segments = TESS data split at gaps > 3 d, long stretches cut to <= 27.4 d);
 (b) the occultation phase comes from Gaia's e and omega (exact conjunction phases) and
     is then free within +-0.15 of that phase (grid step 0.0025);
 (c) the grazing check runs before the mass-consistency check; both are reported
     (verdict and mass_check);
 (d) unit tests (test_eblm_fit.py, stdlib + numpy) run as the job's first step;
 (e) eccentric geometry, needed by (b): with a significant Gaia eccentricity
     (e >= 3 sigma_e, or e >= 0.05 when sigma_e is missing), the fitted transit chord
     speed is converted to a/R1 = A sqrt(1-e^2) / (1 + e sin w) and the impact parameter
     to cos i = b (1 + e sin w) / (a/R1 (1-e^2)); the occultation uses its own impact
     parameter and chord speed. With e = 0 every formula reduces to 0.1.0's.
"""
import argparse
import csv
import io
import json
import math
import os
import sys
import time
import traceback
import urllib.parse
import urllib.request

try:
    import eblm_screen as es
except ImportError:  # only the Gaia/TESS stages need it; the unit tests do not
    es = None

VERSION = "0.2.0"
VIZIER_ASU = ["https://vizier.cfa.harvard.edu/viz-bin/asu-tsv",
              "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"]
BD_MAX = 0.075
# Approximate quadratic limb darkening in the TESS band, logg ~4, solar metallicity
# (rounded from Claret 2017; +-0.1). (Teff, u1, u2)
LD_TABLE = [(4000, 0.48, 0.17), (5000, 0.42, 0.20), (6000, 0.33, 0.25), (7000, 0.25, 0.30),
            (8000, 0.19, 0.32), (10000, 0.13, 0.32)]
# Approximate Teff of a ~5 Gyr M/K dwarf (Baraffe et al. 2015, rounded). (M_sun, K)
TMS_TABLE = [(0.08, 2600), (0.10, 2800), (0.20, 3150), (0.30, 3350), (0.40, 3500),
             (0.50, 3650), (0.60, 3850), (0.70, 4150), (0.80, 4950)]
# The 19 systems of gaia-eblm-v1 with TESS data (graded by eye in
# findings/2026-11-17-eblm-v1-results.md) and the five "reliable depth" systems of E6.
V1_IDS = ["4531797363284853888", "3094854481749076736", "996712994297110272",
          "1458828115020019328", "1866019155321938560", "1284528201728528128",
          "4604416051842553216", "6268711824595767808", "6431159410558514432",
          "2255930129115547264", "500430730131632128", "5419029403516595200",
          "2346634757461218816", "2932426102885101184", "5976702667540821376",
          "1043546799456393600", "1967665569327097088", "2841146399886317696",
          "5557223240440494080"]
E6_IDS = ["4531797363284853888", "1458828115020019328", "1866019155321938560",
          "2346634757461218816", "4865466912871027200"]

# 0.2.0 constants (fixed before any holdout fit)
PHI2_HALF_WINDOW = 0.15
PHI2_STEP = 0.0025
ECC_MIN_SIGNIF = 3.0
ECC_MIN_NO_ERR = 0.05
SEG_GAP_DAYS = 3.0
SEG_MAX_DAYS = 30.0
SEG_PART_DAYS = 27.4
BETA_FRACTIONS = (1.0 / 16.0, 1.0 / 8.0, 1.0 / 4.0)
CIRCULAR = (0.5, 1.0, 1.0)   # (phi2, occultation b ratio, occultation chord-speed ratio)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def _interp(table, x):
    if x <= table[0][0]:
        return table[0][1:]
    for lo, hi in zip(table, table[1:]):
        if x <= hi[0]:
            f = (x - lo[0]) / (hi[0] - lo[0])
            return tuple(a + f * (b - a) for a, b in zip(lo[1:], hi[1:]))
    return table[-1][1:]


def ld_coeffs(teff):
    """(u1, u2) for a primary of this Teff (6500 K if unknown)."""
    if not (teff == teff and teff > 0):
        teff = 6500.0
    return _interp(LD_TABLE, float(teff))


def ms_teff(m):
    if not (m == m and m > 0):
        return float("nan")
    return _interp(TMS_TABLE, float(m))[0]


def t_allowed(m2, teff1, a_over_r1):
    """Hottest TESS-band brightness temperature an M/K dwarf of mass m2 can show: its own
    Teff combined (in T^4) with the substellar-point irradiation temperature T1 sqrt(R1/a)
    (zero albedo, no redistribution: a generous ceiling)."""
    tms = ms_teff(m2)
    if not (tms == tms and teff1 == teff1 and a_over_r1 > 0):
        return float("nan")
    tirr = teff1 / math.sqrt(a_over_r1)
    return (tms ** 4 + tirr ** 4) ** 0.25


def m2_from_fm(fm, m1):
    """Companion mass for a mass function fm (already divided by sin^3 i) and primary m1."""
    if not (fm > 0 and m1 > 0):
        return float("nan")
    lo, hi = 0.0, 100.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mid ** 3 / (m1 + mid) ** 2 < fm:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------- 0.2.0: eccentric geometry
def _fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def ecc_used(e, e_err):
    """The eccentricity the fit uses: Gaia's e if significant (e >= 3 sigma_e; or e >= 0.05
    when sigma_e is missing), else 0 (circular)."""
    e, e_err = _fnum(e), _fnum(e_err)
    if not (e == e and 0.0 < e < 0.95):
        return 0.0
    if e_err == e_err and e_err > 0:
        return e if e >= ECC_MIN_SIGNIF * e_err else 0.0
    return e if e >= ECC_MIN_NO_ERR else 0.0


def mean_anomaly(f, e):
    """Mean anomaly for true anomaly f (radians) and eccentricity e."""
    E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(f / 2.0), math.sqrt(1.0 + e) * math.cos(f / 2.0))
    return E - e * math.sin(E)


def phi2_from_gaia(e, omega_deg):
    """Phase of the occultation after the primary eclipse (transit of the companion).

    Gaia's omega is the RV argument of periastron of the primary: transit at
    f = pi/2 - omega, occultation at f = 3 pi/2 - omega (eblm_screen.conjunction_offset).
    To first order this is 0.5 + (2/pi) e cos(omega)."""
    e = _fnum(e)
    om = _fnum(omega_deg)
    if not (e == e and e > 0 and om == om):
        return 0.5
    w = math.radians(om)
    m_tr = mean_anomaly(0.5 * math.pi - w, e)
    m_oc = mean_anomaly(1.5 * math.pi - w, e)
    return ((m_oc - m_tr) / (2.0 * math.pi)) % 1.0


def occ_geometry(e, omega_deg):
    """(phi2, b_occ / b_tr, chord speed at occultation / at transit)."""
    e = _fnum(e)
    om = _fnum(omega_deg)
    if not (e == e and e > 0 and om == om):
        return CIRCULAR
    s = e * math.sin(math.radians(om))
    return (phi2_from_gaia(e, om), (1.0 + s) / (1.0 - s), (1.0 - s) / (1.0 + s))


def true_geometry(a_r_fit, b_fit, e, omega_deg):
    """(a/R1, cos i) from the fitted transit chord speed a_r_fit and impact parameter b_fit.
    The circular model's x = a_r sin(2 pi phase) has chord speed 2 pi a_r per phase; an
    eccentric orbit's speed at transit is 2 pi (a/R1) (1 + e sin w) / sqrt(1 - e^2)."""
    e = _fnum(e)
    om = _fnum(omega_deg)
    if not (e == e and e > 0 and om == om):
        e, s = 0.0, 0.0
    else:
        s = e * math.sin(math.radians(om))
    a_r = a_r_fit * math.sqrt(1.0 - e * e) / (1.0 + s)
    cosi = min(abs(b_fit) * (1.0 + s) / (a_r * (1.0 - e * e)), 1.0)
    return a_r, cosi


# ---------------------------------------------------------------- eclipse geometry
def circle_overlap(d, k):
    """Overlap area of the unit circle and a circle of radius k at centre distance d."""
    import numpy as np
    d = np.abs(np.atleast_1d(np.asarray(d, float)))
    out = np.zeros_like(d)
    full = d <= abs(1.0 - k)
    out[full] = math.pi * min(1.0, k) ** 2
    part = (~full) & (d < 1.0 + k)
    dp = d[part]
    if dp.size:
        a1 = np.clip((dp * dp + k * k - 1.0) / (2.0 * dp * k), -1.0, 1.0)
        a2 = np.clip((dp * dp + 1.0 - k * k) / (2.0 * dp), -1.0, 1.0)
        s = (-dp + k + 1.0) * (dp + k - 1.0) * (dp - k + 1.0) * (dp + k + 1.0)
        out[part] = k * k * np.arccos(a1) + np.arccos(a2) - 0.5 * np.sqrt(np.maximum(s, 0.0))
    return out


def blocked_fraction(z, k, u1, u2, n=300):
    """Fraction of a quadratic limb-darkened star's flux hidden by an opaque disc of radius
    k (stellar radii) whose centre is at projected distance z. Ring integration: the arc of
    each ring inside the disc is 2 r arccos((r^2 + z^2 - k^2) / (2 r z)), clipped."""
    import numpy as np
    z = np.atleast_1d(np.asarray(z, float))
    r = (np.arange(n) + 0.5) / n
    dr = 1.0 / n
    mu = np.sqrt(1.0 - r * r)
    inten = 1.0 - u1 * (1.0 - mu) - u2 * (1.0 - mu) ** 2
    norm = float(np.sum(inten * 2.0 * math.pi * r) * dr)
    out = np.zeros_like(z)
    m = z < 1.0 + k
    if np.any(m):
        zz = np.maximum(z[m], 1e-9)[:, None]
        arg = (r[None, :] ** 2 + zz ** 2 - k * k) / (2.0 * r[None, :] * zz)
        arc = 2.0 * r[None, :] * np.arccos(np.clip(arg, -1.0, 1.0))
        out[m] = (arc * inten[None, :]).sum(axis=1) * dr / norm
    return out


def eclipse_shapes(phase, k, b, a_r, u1, u2, exp_phase=0.0, nsub=5, geom=CIRCULAR):
    """(D, O) at each phase (0 = primary eclipse). D: fraction of the primary's light
    blocked by the companion. O: fraction of the companion's disc hidden behind the
    primary, centred on phase geom[0] with impact parameter b * geom[1] and chord speed
    a_r * geom[2]. Averaged over an exposure of exp_phase (in phase units). With
    geom = CIRCULAR this is exactly 0.1.0's circular model."""
    import numpy as np
    phi2, b_ratio, v_ratio = geom
    ph = np.atleast_1d(np.asarray(phase, float))
    if exp_phase > 0 and nsub > 1:
        offs = (np.arange(nsub) + 0.5) / nsub - 0.5
        p2 = (ph[:, None] + offs[None, :] * exp_phase).ravel()
    else:
        p2, nsub = ph, 1
    w = 2.0 * math.pi * p2
    x = a_r * np.sin(w)
    y = b * np.cos(w)
    z = np.sqrt(x * x + y * y)
    front = np.cos(w) > 0
    w2 = 2.0 * math.pi * (p2 - (phi2 - 0.5))
    x2 = a_r * v_ratio * np.sin(w2)
    y2 = b * b_ratio * np.cos(w2)
    z2 = np.sqrt(x2 * x2 + y2 * y2)
    back = np.cos(w2) < 0
    D = np.zeros_like(z)
    O = np.zeros_like(z)
    mf = front & (z < 1.0 + k)
    if np.any(mf):
        D[mf] = blocked_fraction(z[mf], k, u1, u2)
    mb = back & (z2 < 1.0 + k)
    if np.any(mb):
        O[mb] = circle_overlap(z2[mb], k) / (math.pi * k * k)
    return D.reshape(-1, nsub).mean(axis=1), O.reshape(-1, nsub).mean(axis=1)


def harmonics(phase):
    import numpy as np
    w = 2.0 * math.pi * np.asarray(phase, float)
    return [np.ones_like(w), np.cos(w), np.sin(w), np.cos(2 * w), np.sin(2 * w),
            np.cos(3 * w), np.sin(3 * w)]


def design(phase, theta, u1, u2, exp_phase, geom=CIRCULAR):
    """Columns of the linear part: h_j (1 - D) for 7 harmonics, then (D - O) whose
    coefficient is the occultation depth Ds (companion light diluting the transit)."""
    import numpy as np
    dphi, k, b, lar = theta
    p = np.asarray(phase, float) - dphi
    D, O = eclipse_shapes(p, k, abs(b), math.exp(lar), u1, u2, exp_phase, geom=geom)
    cols = [h * (1.0 - D) for h in harmonics(p)] + [D - O]
    return np.vstack(cols).T, D, O


def lin_solve(A, y, sig):
    import numpy as np
    Aw = A / sig[:, None]
    yw = y / sig
    coef, *_ = np.linalg.lstsq(Aw, yw, rcond=None)
    r = yw - Aw @ coef
    return coef, float(r @ r), Aw


def in_bounds(theta):
    dphi, k, b, lar = theta
    a_r = math.exp(lar) if lar < 10 else 1e9
    return (abs(dphi) <= 0.03 and 0.005 < k <= 0.9 and abs(b) < 1.0 + k
            and a_r > 1.0 + k and 1.2 <= a_r <= 80.0)


def chi2_of(theta, ph, y, sig, u1, u2, exp_phase, geom=CIRCULAR):
    if not in_bounds(theta):
        return 1e30
    A, _, _ = design(ph, theta, u1, u2, exp_phase, geom)
    return lin_solve(A, y, sig)[1]


def nelder_mead(fun, x0, step, maxiter=1500, xtol=1e-6, ftol=1e-3):
    """Plain Nelder-Mead (no scipy needed). Returns (x_best, f_best)."""
    import numpy as np
    n = len(x0)
    pts = [np.array(x0, float)]
    for i in range(n):
        x = np.array(x0, float)
        x[i] += step[i]
        pts.append(x)
    vals = [fun(p) for p in pts]
    for _ in range(maxiter):
        order = np.argsort(vals)
        pts = [pts[i] for i in order]
        vals = [vals[i] for i in order]
        spread = max(float(np.max(np.abs(p - pts[0]))) for p in pts[1:])
        if abs(vals[-1] - vals[0]) <= ftol and spread <= xtol:
            break
        c = np.mean(pts[:-1], axis=0)
        xr = c + (c - pts[-1])
        fr = fun(xr)
        if fr < vals[0]:
            xe = c + 2.0 * (c - pts[-1])
            fe = fun(xe)
            if fe < fr:
                pts[-1], vals[-1] = xe, fe
            else:
                pts[-1], vals[-1] = xr, fr
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (xr - c) if fr < vals[-1] else c + 0.5 * (pts[-1] - c)
            fc = fun(xc)
            if fc < min(fr, vals[-1]):
                pts[-1], vals[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    pts[i] = pts[0] + 0.5 * (pts[i] - pts[0])
                    vals[i] = fun(pts[i])
    i = int(np.argmin(vals))
    return pts[i], float(vals[i])


def fit_eclipse(ph, y, sig, teff, exp_phase, k0, ar0, b_starts=(0.1, 0.5, 0.85), u_shift=(0.0, 0.0),
                geom=CIRCULAR):
    """Fit (dphi, k, b, a_r) by Nelder-Mead with the linear part solved exactly at every
    step. a_r is the transit chord-speed parameter (= a/R1 for a circular orbit). Returns
    a dict of the best fit, its linear coefficients and their covariance."""
    import numpy as np
    u1, u2 = ld_coeffs(teff)
    u1, u2 = u1 + u_shift[0], u2 + u_shift[1]
    k0 = min(max(k0, 0.02), 0.6)
    ar0 = min(max(ar0, 1.3 + k0), 60.0)
    f = lambda th: chi2_of(th, ph, y, sig, u1, u2, exp_phase, geom)
    best = None
    for b0 in b_starts:
        th0 = [0.0, k0, b0, math.log(ar0)]
        x, v = nelder_mead(f, th0, [0.002, 0.2 * k0, 0.15, 0.1])
        x, v = nelder_mead(f, x, [0.001, 0.05 * x[1], 0.05, 0.03])
        if best is None or v < best[1]:
            best = (x, v)
    th, chi2 = best
    A, D, O = design(ph, th, u1, u2, exp_phase, geom)
    coef, chi2, Aw = lin_solve(A, y, sig)
    dof = max(len(y) - A.shape[1] - 4, 1)
    red = chi2 / dof
    cov = np.linalg.pinv(Aw.T @ Aw) * max(1.0, red)
    # null model: harmonics only
    H = np.vstack(harmonics(np.asarray(ph) - th[0])).T
    _, chi2_null, _ = lin_solve(H, y, sig)
    snr = math.sqrt(max(chi2_null - chi2, 0.0) / max(1.0, red))
    c0 = coef[0]
    return {"dphi": float(th[0]), "k": float(th[1]), "b": float(abs(th[2])), "a_r": float(math.exp(th[3])),
            "u1": u1, "u2": u2, "chi2": chi2, "chi2_red": red, "snr_fit": snr, "coef": coef, "cov": cov,
            "geom": tuple(float(g) for g in geom),
            "Ds": float(coef[7]), "err_Ds": float(math.sqrt(max(cov[7, 7], 0.0))),
            "a_ell": float(-coef[3] / c0), "err_a_ell": float(math.sqrt(max(cov[3, 3], 0.0)) / abs(c0)),
            "depth_model": float(np.max(D) * (1.0 - coef[7])) if D.size else float("nan")}


def _theta(fit):
    return (fit["dphi"], fit["k"], fit["b"], math.log(fit["a_r"]))


def scan_phi2(ph, y, sig, fit, exp_phase, center, half=PHI2_HALF_WINDOW, step=PHI2_STEP):
    """Best occultation phase within center +- half, eclipse shape fixed (fix b).
    Returns (phi2_best, chi2_best, chi2_at_center)."""
    th = _theta(fit)
    g = fit.get("geom", CIRCULAR)
    n = int(round(half / step))
    best = None
    chi_c = float("nan")
    for i in range(-n, n + 1):
        p2 = center + i * step
        c2 = lin_solve(design(ph, th, fit["u1"], fit["u2"], exp_phase, (p2, g[1], g[2]))[0], y, sig)[1]
        if i == 0:
            chi_c = c2
        if best is None or c2 < best[1]:
            best = (p2, c2)
    return best[0], best[1], chi_c


# ---------------------------------------------------------------- 0.2.0: red noise (fix a)
def segments(t, gap=SEG_GAP_DAYS, max_len=SEG_MAX_DAYS, part=SEG_PART_DAYS):
    """Index arrays of data segments: split at gaps > gap days; any stretch longer than
    max_len days is cut into equal parts no longer than part days."""
    import numpy as np
    t = np.asarray(t, float)
    if t.size == 0:
        return []
    cuts = np.where(np.diff(t) > gap)[0] + 1
    out = []
    for idx in np.split(np.arange(t.size), cuts):
        if idx.size == 0:
            continue
        span = t[idx[-1]] - t[idx[0]]
        if span > max_len:
            n = int(math.ceil(span / part))
            edges = t[idx[0]] + span * np.arange(1, n) / n
            for sub in np.split(idx, np.searchsorted(t[idx], edges)):
                if sub.size:
                    out.append(sub)
        else:
            out.append(idx)
    return out


def beta_factor(t, r, widths, min_bins=8, min_per_bin=3):
    """Time-correlated noise factor: max over bin widths of the rms of binned residuals
    divided by its white-noise expectation (never below 1)."""
    import numpy as np
    t = np.asarray(t, float)
    r = np.asarray(r, float)
    ok = np.isfinite(t) & np.isfinite(r)
    t, r = t[ok], r[ok]
    if r.size < min_bins * min_per_bin:
        return 1.0, {}
    s1 = float(np.std(r))
    if not s1 > 0:
        return 1.0, {}
    betas = {}
    for w in widths:
        if not w > 0:
            continue
        idx = np.floor((t - t[0]) / w).astype(np.int64)
        _, inv, cnt = np.unique(idx, return_inverse=True, return_counts=True)
        sums = np.bincount(inv, weights=r)
        keep = cnt >= min_per_bin
        m = int(keep.sum())
        if m < min_bins:
            continue
        means = sums[keep] / cnt[keep]
        nbar = float(np.mean(cnt[keep]))
        expect = s1 / math.sqrt(nbar) * math.sqrt(m / (m - 1.0))
        betas[f"{w:.5g}"] = float(np.std(means) / expect)
    beta = max([1.0] + list(betas.values()))
    return beta, betas


def segment_amplitudes(t, f, P, t0, fit, exp_phase, min_cycles=1.5, min_points=200, nbins=200):
    """Ellipsoidal amplitude in each segment with the eclipse shape fixed."""
    import numpy as np
    th = _theta(fit)
    g = fit.get("geom", CIRCULAR)
    amps = []
    for idx in segments(t):
        ts, fs = np.asarray(t)[idx], np.asarray(f)[idx]
        if ts.size < min_points or ts[-1] - ts[0] < min_cycles * P:
            continue
        ph, y, sig, _ = phase_bin(ts, fs, P, t0, nbins=nbins, min_n=2)
        if y.size < 50:
            continue
        A = design(ph, th, fit["u1"], fit["u2"], exp_phase, g)[0]
        coef = lin_solve(A, y, sig)[0]
        if coef[0] != 0:
            amps.append(float(-coef[3] / coef[0]))
    return amps


def segment_scatter(amps):
    """Standard error of the mean amplitude from segment-to-segment scatter (NaN if < 2)."""
    if len(amps) < 2:
        return float("nan")
    m = sum(amps) / len(amps)
    var = sum((a - m) ** 2 for a in amps) / (len(amps) - 1)
    return math.sqrt(var / len(amps))


def combine_err(white, beta, seg):
    """Fix (a): the larger of white x beta and the segment scatter (NaNs ignored)."""
    cands = [x for x in (white * beta if white == white and beta == beta else float("nan"), seg)
             if x == x]
    return max(cands) if cands else float("nan")


def time_model(t, P, t0, fit, exp_phase):
    import numpy as np
    ph = ((np.asarray(t) - t0) / P + 0.5) % 1.0 - 0.5
    A = design(ph, _theta(fit), fit["u1"], fit["u2"], exp_phase, fit.get("geom", CIRCULAR))[0]
    return A @ fit["coef"]


def phase_bin(t, f, P, t0, nbins=1000, min_n=3):
    """Phase-fold (0 = t0) into nbins; returns mean phase, mean flux, error and count per
    bin (bins with fewer than min_n points dropped). The per-point scatter is the robust
    scatter of the residuals from the bin means."""
    import numpy as np
    ph = ((np.asarray(t) - t0) / P + 0.5) % 1.0 - 0.5
    idx = np.minimum((ph + 0.5) * nbins, nbins - 1).astype(np.int64)
    cnt = np.bincount(idx, minlength=nbins).astype(float)
    sf = np.bincount(idx, weights=f, minlength=nbins)
    sp = np.bincount(idx, weights=ph, minlength=nbins)
    good = cnt >= min_n
    mf = np.where(cnt > 0, sf / np.maximum(cnt, 1), np.nan)
    sd = robust_sd(np.asarray(f) - mf[idx])
    return (sp[good] / cnt[good], mf[good], sd / np.sqrt(cnt[good]), cnt[good])


def robust_sd(x):
    import numpy as np
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(1.4826 * np.median(np.abs(x - np.median(x)))) if x.size > 1 else float("nan")


def odd_even(t, f, P, t0, fit, exp_phase):
    """Separate transit amplitudes for odd and even epochs (time series, best shape)."""
    import numpy as np
    ph = ((t - t0) / P + 0.5) % 1.0 - 0.5 - fit["dphi"]
    D, O = eclipse_shapes(ph, fit["k"], fit["b"], fit["a_r"], fit["u1"], fit["u2"], exp_phase,
                          geom=fit.get("geom", CIRCULAR))
    ep = np.round((t - t0) / P - fit["dphi"]).astype(np.int64)
    odd = (np.abs(ep) % 2) == 1
    if (D[odd] > 0).sum() < 5 or (D[~odd] > 0).sum() < 5:
        return {}
    X = np.vstack(harmonics(ph) + [-D * odd, -D * (~odd), -O]).T
    coef, *_ = np.linalg.lstsq(X, f, rcond=None)
    r = f - X @ coef
    sd = robust_sd(r)
    cov = np.linalg.pinv(X.T @ X) * sd ** 2
    return {"A_odd": float(coef[7]), "err_odd": float(math.sqrt(max(cov[7, 7], 0))),
            "A_even": float(coef[8]), "err_even": float(math.sqrt(max(cov[8, 8], 0)))}


# ---------------------------------------------------------------- physics and verdict
def derive(c, fit, teff1, e=0.0, omega_deg=float("nan")):
    """Masses and radii from the fit plus the Gaia SB1 orbit (c: eblm_screen.classify row).
    e, omega: the eccentricity used by the fit (0 = circular) and Gaia's omega."""
    out = {}
    k = fit["k"]
    a_r, cosi = true_geometry(fit["a_r"], fit["b"], e, omega_deg)
    out["a_r_true"] = a_r
    sini = math.sqrt(max(1.0 - cosi * cosi, 0.0))
    out["inc_deg"] = math.degrees(math.acos(cosi))
    m1 = c.get("m1_flame", float("nan"))
    out["m1_source"] = "flame" if m1 == m1 and m1 > 0 else "default_1.3"
    m1 = m1 if m1 == m1 and m1 > 0 else 1.3
    out["m1"] = m1
    fm = c["fm"]
    m2 = m2_from_fm(fm / sini ** 3, m1) if sini > 0 else float("nan")
    out["m2"] = m2
    k_hi = c["m2_hi2"]
    out["m2_hi2"] = k_hi / sini if k_hi == k_hi and sini > 0 else float("nan")    # first order in sin i
    a = es.semi_major_axis_rsun(c["period"], m1 + m2)
    out["a_rsun"] = a
    r1 = a / a_r
    out["r1_lc"] = r1
    r1f = c.get("r1_flame", float("nan"))
    out["r1_flame"] = r1f
    out["r1_ratio"] = r1 / r1f if r1f == r1f and r1f > 0 else float("nan")
    out["r2"] = k * r1
    out["r2_flame"] = k * r1f if r1f == r1f else float("nan")
    out["r_ms"] = es.ms_radius(m2)
    out["infl"] = out["r2"] / out["r_ms"] - 1.0 if out["r_ms"] > 0 else float("nan")
    out["infl_flame"] = out["r2_flame"] / out["r_ms"] - 1.0 if out["r_ms"] > 0 else float("nan")
    out["ell_pred_fit"] = es.ellipsoidal_pred(m2, m1, r1, a, sini)
    out["ell_ratio_fit"] = fit["a_ell"] / out["ell_pred_fit"] if out["ell_pred_fit"] > 0 else float("nan")
    ds, eds = fit["Ds"], fit["err_Ds"]
    out["t2"] = es.companion_teff(ds, k, teff1) if ds > 0 else float("nan")
    out["t2_lo3"] = es.companion_teff(ds - 3 * eds, k, teff1) if ds - 3 * eds > 0 else float("nan")
    out["t_allow"] = t_allowed(m2, teff1, a_r)
    return out


def mass_check(v):
    """Ellipsoidal mass-consistency check alone (0.1.0 rule, 0.2.0 error bar)."""
    a, ea, pr = (v.get(key, float("nan")) for key in ("a_ell", "err_a_ell", "ell_pred_fit"))
    if not (a == a and ea == ea and pr == pr):
        return "MASS_NA", []
    if a - 3 * ea > 2 * pr:
        return "MASS_TENSION_HEAVIER", [f"ellipsoidal {a:.5f} > 2 x predicted {pr:.5f}"]
    if a + 3 * ea < 0.5 * pr:
        return "MASS_TENSION_LIGHTER", [f"ellipsoidal {a:.5f} < 0.5 x predicted {pr:.5f}"]
    return "MASS_OK", []


def verdict(v):
    """0.1.0's pre-registered rules (findings/2026-11-17-eblm-fit-prereg.md) with fix (c):
    the grazing check now runs before the mass-consistency check."""
    g = lambda key: v.get(key, float("nan"))
    if not (g("snr_fit") >= 10):
        return "NO_ECLIPSE", [f"snr_fit {g('snr_fit'):.1f}"]
    ao, ae, eo, ee = g("A_odd"), g("A_even"), g("err_odd"), g("err_even")
    if ao == ao and ae == ae:
        if abs(ao - ae) > 3 * math.hypot(eo, ee) and abs(ao - ae) > 0.1 * 0.5 * (ao + ae):
            return "TWIN_AT_2P", [f"odd {ao:.4f} vs even {ae:.4f}"]
    pre = "BD_" if g("m2_hi2") < BD_MAX else ""
    if g("b") > 1.0 - g("k"):
        return pre + "EBLM_GRAZING", [f"b {g('b'):.2f} > 1 - k"]
    mc, why = mass_check(v)
    if mc in ("MASS_TENSION_HEAVIER", "MASS_TENSION_LIGHTER"):
        return mc, why
    if g("t2_lo3") > 1.15 * g("t_allow"):
        return "TOO_LUMINOUS", [f"T2 > {g('t2_lo3'):.0f} K (3 sigma) vs at most {g('t_allow'):.0f} K for an M dwarf"]
    reasons = [f"R2 {g('r2'):.3f} vs MS {g('r_ms'):.3f} R_sun ({100 * g('infl'):+.0f}%)"]
    if g("infl") > 0.3:
        return pre + "EBLM_LARGE_RADIUS", reasons
    if g("infl") < -0.3:
        return pre + "EBLM_SMALL_RADIUS", reasons
    return pre + "EBLM_CONSISTENT", reasons


def is_clean_eblm(v):
    lab = v.get("verdict", "")
    return lab.endswith("EBLM_CONSISTENT") or lab.endswith("EBLM_LARGE_RADIUS") or lab.endswith("EBLM_SMALL_RADIUS")


def inflation_stats(values, n_boot=2000, seed=20261117):
    """Median of R2/R_MS - 1 and its bootstrap 95% interval; label per the pre-registration:
    INFLATED if the lower bound > +0.05, CONSISTENT if the interval contains 0 and is
    narrower than 0.2, DEFLATED if the upper bound < -0.05, else INCONCLUSIVE."""
    import numpy as np
    x = np.asarray([v for v in values if v == v], float)
    if x.size < 3:
        return {"n": int(x.size), "label": "TOO_FEW"}
    rng = np.random.default_rng(seed)
    meds = np.median(x[rng.integers(0, x.size, size=(n_boot, x.size))], axis=1)
    lo, hi = (float(q) for q in np.percentile(meds, [2.5, 97.5]))
    med = float(np.median(x))
    if lo > 0.05:
        lab = "INFLATED"
    elif hi < -0.05:
        lab = "DEFLATED"
    elif lo <= 0.0 <= hi and hi - lo < 0.2:
        lab = "CONSISTENT"
    else:
        lab = "INCONCLUSIVE"
    return {"n": int(x.size), "median": med, "ci95": [lo, hi], "label": lab}


# ---------------------------------------------------------------- catalogues
def parse_asu_tsv(text):
    """Rows (dicts) of a VizieR ASU-TSV answer: header, units and dashes lines, then data."""
    raw = [ln for ln in text.splitlines() if not ln.startswith("#")]
    dash = next((i for i, ln in enumerate(raw) if ln.strip() and set(ln.strip()) <= set("-\t ")), None)
    if dash is None:
        return []
    heads = [ln for ln in raw[:dash] if ln.strip()]
    if not heads:
        return []
    head = [h.strip() for h in heads[0].split("\t")]
    rows = []
    for ln in raw[dash + 1:]:
        if not ln.strip():
            continue
        parts = [p.strip() for p in ln.split("\t")]
        if len(parts) == len(head):
            rows.append(dict(zip(head, parts)))
    return rows


def vizier_cone(cat, ra, dec, radius_arcsec=10.0, timeout=60):
    q = urllib.parse.urlencode({"-source": cat, "-c": f"{float(ra):.6f} {float(dec):+.6f}",
                                "-c.rs": str(radius_arcsec), "-out.max": "10"})
    last = None
    for base in VIZIER_ASU:
        try:
            req = urllib.request.Request(base + "?" + q, headers={"User-Agent": "gaia-orbit-transits"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return parse_asu_tsv(r.read().decode("utf-8", "replace"))
        except Exception as exc:
            last = exc
    raise RuntimeError(f"vizier failed: {last}")


def catalogues(ra, dec):
    out = {}
    for key, cat in (("vsx", "B/vsx/vsx"), ("tess_eb", "J/ApJS/258/16")):
        try:
            rows = vizier_cone(cat, ra, dec)
            out[key + "_n"] = len(rows)
            if rows:
                out[key + "_name"] = rows[0].get("Name", rows[0].get("TIC", ""))
                out[key + "_type"] = rows[0].get("Type", rows[0].get("Morph", ""))
                out[key + "_period"] = rows[0].get("Period", rows[0].get("Per", ""))
        except Exception as exc:
            out[key + "_n"] = f"failed: {str(exc)[:80]}"
    return out


# ---------------------------------------------------------------- one system
def vet_fit(c, data_dir, max_sectors, plot_dir=None):
    """c: an eblm_screen.classify row; 0.2.0 also reads c['e_err'] and c['omega'] (Gaia's
    eccentricity_error and arg_periastron) when present."""
    import numpy as np
    from astropy.timeseries import BoxLeastSquares
    res = {"source_id": c["source_id"], "period_gaia": c["period"], "m2_sini": c["m2"], "fm": c["fm"],
           "ra": c.get("ra", ""), "dec": c.get("dec", ""), "G": c.get("phot_g_mean_mag", ""),
           "eblm_fit_version": VERSION}
    tic, tmag = es.resolve_tic(c["source_id"], c["ra"], c["dec"])
    res.update({"tic": tic, "tmag": tmag})
    if tic is None:
        res["verdict"] = "NO_TIC"
        return res
    lc, info = es.load_tess(tic, data_dir, max_sectors)
    res["sectors"] = ";".join(f"{i.get('sector')}:{i.get('author')}" for i in info if "n" in i)
    if lc is None:
        res["verdict"] = "NO_TESS_DATA"
        return res
    t, f = lc
    cad = float(np.median(np.diff(t))) if t.size > 1 else 2.0 / 1440
    P0 = c["period"]
    fd = es.detrend(t, f, window=max(2.0, 3.0 * P0))
    ok = np.isfinite(fd)
    t, fd = t[ok], fd[ok]
    idx = np.floor((t - t[0]) / (10.0 / 1440)).astype(np.int64)
    _, inv, cnt = np.unique(idx, return_inverse=True, return_counts=True)
    bt = np.bincount(inv, weights=t) / cnt
    bf = np.bincount(inv, weights=fd) / cnt
    exp_d = max(10.0 / 1440, cad)
    sd = robust_sd(np.diff(bf)) / math.sqrt(2.0)
    a_r_guess = c["a_rsun"] / c["r1_flame"] if c.get("r1_flame") == c.get("r1_flame") and c.get("r1_flame") else 4.0
    dur_c = P0 / math.pi * math.asin(min(1.0, 1.0 / max(a_r_guess, 1.01)))
    durs = np.clip(np.array([0.5, 0.7, 0.85, 1.0, 1.2]) * dur_c, 0.02, 0.4 * P0)
    periods = np.linspace(P0 * (1 - 1e-3), P0 * (1 + 1e-3), 3001)
    bls = BoxLeastSquares(bt, bf, dy=np.full(bf.size, max(sd, 1e-6)))
    r = bls.power(periods, durs, objective="likelihood")
    j = int(np.argmax(r.power))
    P, t0 = float(r.period[j]), float(r.transit_time[j])
    res.update({"P_tess": P, "t0_btjd": t0, "snr_bls": float(r.depth_snr[j]), "n_bins": int(bt.size),
                "cadence_min": cad * 1440, "noise_10min": sd})
    ph, y, sig, n = phase_bin(bt, bf, P, t0, nbins=1000)
    oot = np.abs(ph) > 0.15
    base = float(np.median(y[oot])) if oot.any() else 1.0
    near = np.abs(ph) < 0.05
    dmin = float(np.min(np.convolve(y[near], np.ones(5) / 5, mode="valid"))) if near.sum() > 5 else base
    k0 = math.sqrt(max(base - dmin, 1e-4))
    teff1 = es._f(c, "teff_gspphot")
    # fix (b) + (e): eccentric geometry from Gaia, then a free occultation phase
    e_u = ecc_used(c.get("e", 0.0), c.get("e_err", float("nan")))
    om = _fnum(c.get("omega", float("nan")))
    if not (om == om):
        e_u = 0.0
    geom0 = occ_geometry(e_u, om) if e_u > 0 else CIRCULAR
    res.update({"e_gaia": c.get("e", ""), "e_err_gaia": c.get("e_err", ""), "omega_gaia": c.get("omega", ""),
                "e_used": e_u, "phi2_center": geom0[0]})
    fit = fit_eclipse(ph, y, sig, teff1, exp_d / P, k0, a_r_guess, geom=geom0)
    p2, chi_best, chi_c = scan_phi2(ph, y, sig, fit, exp_d / P, geom0[0])
    res.update({"phi2_fit": p2, "dchi2_phi2": chi_c - chi_best})
    if abs(p2 - geom0[0]) > 0.5 * PHI2_STEP:
        fit = fit_eclipse(ph, y, sig, teff1, exp_d / P, fit["k"], fit["a_r"], b_starts=(fit["b"],),
                          geom=(p2, geom0[1], geom0[2]))
    res.update({key: fit[key] for key in ("dphi", "k", "b", "a_r", "u1", "u2", "chi2_red", "snr_fit", "Ds",
                                          "err_Ds", "a_ell", "err_a_ell", "depth_model")})
    # fix (a): red-noise error of the ellipsoidal amplitude
    white = fit["err_a_ell"]
    try:
        resid = bf - time_model(bt, P, t0, fit, exp_d / P)
        beta, betas = beta_factor(bt, resid, [P * q for q in BETA_FRACTIONS])
    except Exception as exc:  # noqa: BLE001
        beta, betas = 1.0, {"error": str(exc)[:120]}
    try:
        amps = segment_amplitudes(bt, bf, P, t0, fit, exp_d / P)
    except Exception as exc:  # noqa: BLE001
        amps, res["seg_error"] = [], str(exc)[:120]
    seg = segment_scatter(amps)
    res.update({"err_a_ell_white": white, "beta_red": beta, "beta_by_width": json.dumps(betas),
                "n_seg_amp": len(amps), "seg_amps": ";".join(f"{a:.6g}" for a in amps),
                "err_a_ell_seg": seg, "err_a_ell": combine_err(white, beta, seg)})
    res["teff1"] = teff1
    res.update(odd_even(bt, bf, P, t0, fit, exp_d / P))
    res.update(derive(c, fit, teff1, e_u, om))
    gd = es.mag_to_flux(c["ecl1_mag"]) if c.get("ecl1_mag") == c.get("ecl1_mag") else float("nan")
    res["gaia_depth_flux"] = gd
    res["depth_ratio_gaia"] = fit["depth_model"] / gd if gd and gd == gd else float("nan")
    res["mass_check"] = mass_check(res)[0]
    label, reasons = verdict(res)
    res["verdict"], res["reasons"] = label, reasons
    if is_clean_eblm(res) or label.endswith("EBLM_GRAZING"):
        try:
            f2 = fit_eclipse(ph, y, sig, teff1, exp_d / P, fit["k"], fit["a_r"], b_starts=(fit["b"],),
                             u_shift=(0.1, 0.0), geom=fit["geom"])
            res["k_ld_shift"] = f2["k"]
        except Exception as exc:
            res["k_ld_shift_error"] = str(exc)[:120]
    if plot_dir:
        try:
            plot_fit(c, res, ph, y, fit, exp_d / P, os.path.join(plot_dir, f"fit_{c['source_id']}.png"))
        except Exception as exc:
            res["plot_error"] = str(exc)[:200]
    return res


def plot_fit(c, res, ph, y, fit, exp_phase, path):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    A, _, _ = design(ph, _theta(fit), fit["u1"], fit["u2"], exp_phase, fit.get("geom", CIRCULAR))
    model = A @ fit["coef"]
    x = (ph + 0.25) % 1.0 - 0.25
    o = np.argsort(x)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.5), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    a1.plot(x, y, ".", ms=2, color="0.5")
    a1.plot(x[o], model[o], "r-", lw=1)
    a1.set_title(f"Gaia DR3 {c['source_id']} = TIC {res.get('tic')}, P = {res.get('P_tess', 0):.6f} d: "
                 f"{res.get('verdict')} (eblm_fit {VERSION})", fontsize=9)
    a1.text(0.01, 0.03, f"k={fit['k']:.4f} b={fit['b']:.2f} a_r={fit['a_r']:.2f} Ds={fit['Ds']:.5f} "
            f"phi2={res.get('phi2_fit', 0.5):.3f} snr={fit['snr_fit']:.0f} R2={res.get('r2', float('nan')):.3f} "
            f"m2={res.get('m2', float('nan')):.3f}", transform=a1.transAxes, fontsize=8)
    a2.plot(x, y - model, ".", ms=2, color="0.3")
    a2.set_xlabel("phase (0 = primary eclipse)")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- grading (0.1.0 sample run)
def grade(vets):
    import numpy as np
    with_data = [v for v in vets if v.get("snr_fit") == v.get("snr_fit") and "snr_fit" in v]
    n_data = len(with_data)
    det = [v for v in with_data if v["snr_fit"] >= 10]
    clean = [v for v in vets if is_clean_eblm(v)]
    g = {}
    g["G1"] = {"n_with_data": n_data, "n_detected": len(det),
               "pass": n_data > 0 and len(det) >= 0.8 * n_data}
    ratios = [v["r1_ratio"] for v in clean if v.get("r1_ratio") == v.get("r1_ratio")]
    med_r = float(np.median(ratios)) if ratios else float("nan")
    g["G2"] = {"n": len(ratios), "median_r1_lc_over_flame": med_r, "pass": 0.85 <= med_r <= 1.15}
    g["G3"] = {"n_clean_eblm": len(clean), "pass": len(clean) >= 10}
    st = inflation_stats([v.get("infl", float("nan")) for v in clean])
    st_f = inflation_stats([v.get("infl_flame", float("nan")) for v in clean])
    short = inflation_stats([v.get("infl", float("nan")) for v in clean if v.get("period_gaia", 9) < 1.5])
    longer = inflation_stats([v.get("infl", float("nan")) for v in clean if v.get("period_gaia", 0) >= 1.5])
    g["G4"] = {"inflation_lc_radius": st, "inflation_flame_radius": st_f, "P_lt_1.5d": short,
               "P_ge_1.5d": longer, "outcome": st.get("label")}
    lum = [v for v in vets if v.get("verdict") == "TOO_LUMINOUS"]
    g["G5"] = {"n_too_luminous": len(lum), "pass": len(lum) >= 3}
    v1 = [v for v in vets if str(v.get("source_id")) in V1_IDS]
    v1_det = [v for v in v1 if v.get("snr_fit", 0) >= 10]
    g["G6"] = {"n_v1_vetted": len(v1), "n_detected": len(v1_det), "pass": len(v1_det) >= 15}
    e6 = [v for v in vets if str(v.get("source_id")) in E6_IDS]
    g["E6"] = {"n": len(e6), "n_large_radius": sum(1 for v in e6 if v.get("verdict", "").endswith("EBLM_LARGE_RADIUS")),
               "verdicts": {str(v["source_id"]): v.get("verdict") for v in e6}}
    g["E6"]["pass"] = g["E6"]["n_large_radius"] <= 2
    dr = [v["depth_ratio_gaia"] for v in det if v.get("depth_ratio_gaia") == v.get("depth_ratio_gaia")]
    g["E5_redo"] = {"n": len(dr), "median_tess_over_gaia_depth": float(np.median(dr)) if dr else float("nan")}
    g["E5_redo"]["pass"] = bool(dr) and g["E5_redo"]["median_tess_over_gaia_depth"] < 1
    cat = [v for v in vets if isinstance(v.get("vsx_n"), int) or isinstance(v.get("tess_eb_n"), int)]
    g["catalogues"] = {"n_checked": len(cat),
                       "n_in_vsx": sum(1 for v in cat if isinstance(v.get("vsx_n"), int) and v["vsx_n"] > 0),
                       "n_in_tess_eb": sum(1 for v in cat if isinstance(v.get("tess_eb_n"), int) and v["tess_eb_n"] > 0)}
    return g


FIT_COLS = ["source_id", "tic", "tmag", "G", "verdict", "mass_check", "eblm_fit_version", "period_gaia", "P_tess",
            "t0_btjd", "sectors", "cadence_min", "noise_10min", "snr_bls", "snr_fit", "chi2_red", "k", "b", "a_r",
            "a_r_true", "inc_deg", "dphi", "e_gaia", "e_err_gaia", "omega_gaia", "e_used", "phi2_center",
            "phi2_fit", "dchi2_phi2", "u1", "u2", "k_ld_shift", "Ds", "err_Ds", "a_ell", "err_a_ell",
            "err_a_ell_white", "beta_red", "beta_by_width", "n_seg_amp", "seg_amps", "err_a_ell_seg",
            "ell_pred_fit", "ell_ratio_fit", "A_odd", "err_odd", "A_even", "err_even", "teff1", "m1", "m1_source",
            "fm", "m2_sini", "m2", "m2_hi2", "a_rsun", "r1_lc", "r1_flame", "r1_ratio", "r2", "r2_flame", "r_ms",
            "infl", "infl_flame", "t2", "t2_lo3", "t_allow", "depth_model", "gaia_depth_flux", "depth_ratio_gaia",
            "vsx_n", "vsx_name", "vsx_type", "vsx_period", "tess_eb_n", "tess_eb_name", "ra", "dec", "reasons"]


def _fmt(x):
    if isinstance(x, float):
        return "" if x != x else f"{x:.6g}"
    if isinstance(x, (list, tuple)):
        return " | ".join(str(i) for i in x)
    return x


def write_outputs(out_dir, vets, summary):
    with open(os.path.join(out_dir, "eblm_fit_results.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIT_COLS, extrasaction="ignore")
        w.writeheader()
        for v in vets:
            w.writerow({k: _fmt(v.get(k, "")) for k in FIT_COLS})
    with open(os.path.join(out_dir, "eblm_fit_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=lambda x: None if isinstance(x, float) and x != x else str(x))


def report(vets, summary):
    lines = [f"# eblm_fit {VERSION} report", "", f"Systems vetted: {len(vets)}", "",
             "## Verdicts", ""]
    for k_, n_ in sorted(summary.get("verdicts", {}).items(), key=lambda kv: -kv[1]):
        lines.append(f"- {k_}: {n_}")
    lines += ["", "## Grades", "", "```", json.dumps(summary.get("grades", {}), indent=1, default=str), "```", "",
              "## Clean EBLM fits (sorted by companion mass)", "",
              "| Gaia DR3 | TIC | P (d) | m2 (M_sun) | R2 (R_sun) | R_MS | infl | R1 lc/FLAME | b | e used | phi2 | snr | mass check |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    clean = sorted([v for v in vets if is_clean_eblm(v)], key=lambda v: v.get("m2", 9))
    for v in clean:
        lines.append(f"| {v['source_id']} | {v.get('tic')} | {v.get('period_gaia', 0):.5f} | {v.get('m2', 0):.3f} | "
                     f"{v.get('r2', 0):.3f} | {v.get('r_ms', 0):.3f} | {100 * v.get('infl', 0):+.0f}% | "
                     f"{v.get('r1_ratio', float('nan')):.2f} | {v.get('b', 0):.2f} | {v.get('e_used', 0):.3f} | "
                     f"{v.get('phi2_fit', 0.5):.3f} | {v.get('snr_fit', 0):.0f} | {v.get('mass_check', '')} |")
    lines += ["", "## Other verdicts", ""]
    for v in vets:
        if not is_clean_eblm(v):
            lines.append(f"- {v['source_id']} (TIC {v.get('tic')}): {v.get('verdict')} "
                         f"(mass check {v.get('mass_check', '')}) {v.get('reasons', '')}")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--schema", default="gaiadr3")
    ap.add_argument("--n-tess", type=int, default=200)
    ap.add_argument("--max-sectors", type=int, default=4)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--time-budget-min", type=float, default=330.0)
    ap.add_argument("--no-catalogues", action="store_true")
    a = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(a.out_dir, exist_ok=True)
    os.makedirs(a.data_dir, exist_ok=True)
    plot_dir = os.path.join(a.out_dir, "fit_plots")
    os.makedirs(plot_dir, exist_ok=True)
    raw = es.tap_csv(es.GAIA_TAP, es.sample_adql(a.schema))
    rows = [es.classify(r) for r in raw]
    for r, c in zip(raw, rows):
        c["omega"] = _fnum(r.get("arg_periastron"))
    eblm = sorted([r for r in rows if r["cls"] == "eblm_like" and r["fm"] < 0.3], key=lambda r: r["m2"])
    log("sample", len(rows), "eblm_like", len(eblm))
    summary = {"version": VERSION, "schema": a.schema, "n_sample": len(rows), "n_eblm_like": len(eblm)}
    vets = []
    for c in eblm[:a.n_tess]:
        if (time.time() - t_start) / 60.0 > a.time_budget_min:
            summary["stopped_by_time_budget"] = True
            break
        log("fit", c["source_id"], f"P={c['period']:.5f} m2sini={c['m2']:.3f}")
        try:
            v = vet_fit(c, a.data_dir, a.max_sectors, plot_dir)
        except Exception:
            v = {"source_id": c["source_id"], "verdict": "ERROR", "reasons": [traceback.format_exc()[-400:]]}
        if not a.no_catalogues:
            v.update(catalogues(c["ra"], c["dec"]))
        log("->", v.get("verdict"), v.get("reasons"))
        vets.append(v)
        if len(vets) % 10 == 0:
            write_outputs(a.out_dir, vets, summary)
    summary["n_vetted"] = len(vets)
    summary["verdicts"] = {}
    for v in vets:
        summary["verdicts"][v.get("verdict", "?")] = summary["verdicts"].get(v.get("verdict", "?"), 0) + 1
    summary["grades"] = grade(vets)
    summary["minutes"] = (time.time() - t_start) / 60.0
    write_outputs(a.out_dir, vets, summary)
    with open(os.path.join(a.out_dir, "eblm_fit_report.md"), "w") as fh:
        fh.write(report(vets, summary))
    print(json.dumps(summary, default=str)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
