# SPDX-License-Identifier: Apache-2.0
"""Pure-Python helpers for eclipse ephemerides and the pre-registered VSX criteria.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
No numpy: this module is tested by the publish lane's test_first.

- fit_linear(times, errs, p_guess): weighted least squares T(n) = T0 + n P.
- predicted_times(t0, p, tmin, tmax): every epoch inside [tmin, tmax].
- trapezoid_shape(dt, t14, fin): 0..1 eclipse shape (1 = full depth).
- phase_of(t, t0, p): phase in [0, 1).
- vsx_criteria(...): E1-E4 of findings/2026-11-18-cd-48-897-prereg.md.
"""
import math

VERSION = "0.1.0"


def phase_of(t, t0, p):
    """Orbital phase in [0, 1), 0 at t0."""
    return ((t - t0) / p) % 1.0


def predicted_times(t0, p, tmin, tmax):
    """List of (n, t) with t = t0 + n p and tmin <= t <= tmax."""
    n0 = math.ceil((tmin - t0) / p)
    n1 = math.floor((tmax - t0) / p)
    return [(n, t0 + n * p) for n in range(n0, n1 + 1)]


def trapezoid_shape(dt, t14, fin):
    """Fraction of full depth at time offset dt from mid-eclipse.

    t14 is the total duration and fin the ingress time as a fraction of t14/2
    (fin = 1 gives a V shape)."""
    half = 0.5 * t14
    tin = max(fin * half, 1e-9)
    return min(1.0, max(0.0, (half - abs(dt)) / tin))


def fit_linear(times, errs, p_guess, t_ref=None):
    """Weighted least-squares linear ephemeris.

    Cycle numbers are n = round((t - t_ref) / p_guess), with t_ref = min(times) by
    default. Returns a dict with t0 (at n = 0), p, sig_t0, sig_p (from the input
    errors, not rescaled), cov, n, resid, chi2 and rms (unweighted)."""
    if len(times) != len(errs) or len(times) < 2:
        raise ValueError("need at least two times with errors")
    if t_ref is None:
        t_ref = min(times)
    ns = [int(round((t - t_ref) / p_guess)) for t in times]
    if len(set(ns)) < 2:
        raise ValueError("all times fall in one cycle")
    w = [1.0 / (e * e) for e in errs]
    s = sum(w)
    sn = sum(wi * n for wi, n in zip(w, ns))
    snn = sum(wi * n * n for wi, n in zip(w, ns))
    st = sum(wi * t for wi, t in zip(w, times))
    snt = sum(wi * n * t for wi, n, t in zip(w, ns, times))
    det = s * snn - sn * sn
    p = (s * snt - sn * st) / det
    t0 = (snn * st - sn * snt) / det
    cov = [[snn / det, -sn / det], [-sn / det, s / det]]   # order (t0, p)
    resid = [t - (t0 + n * p) for t, n in zip(times, ns)]
    chi2 = sum((r / e) ** 2 for r, e in zip(resid, errs))
    rms = math.sqrt(sum(r * r for r in resid) / len(resid))
    return {"t0": t0, "p": p, "sig_t0": math.sqrt(cov[0][0]), "sig_p": math.sqrt(cov[1][1]),
            "cov": cov, "n": ns, "resid": resid, "chi2": chi2, "rms": rms, "t_ref": t_ref}


def median(xs):
    v = sorted(xs)
    m = len(v)
    if m == 0:
        return float("nan")
    return v[m // 2] if m % 2 else 0.5 * (v[m // 2 - 1] + v[m // 2])


def vsx_criteria(depths, rms_oc_d, p_fit, p_gaia, p_gaia_err, contam,
                 min_depth=0.05, min_n=4, max_rms_min=30.0, max_rel_spread=0.25,
                 contam_factor=3.0):
    """Pre-registered criteria for reporting a Gaia-orbit eclipsing binary to VSX.

    E1: at least min_n fitted primary eclipses deeper than min_depth.
    E2: linear-ephemeris rms O-C < max_rms_min minutes and |P_fit - P_Gaia| <= 3 sigma_Gaia.
    E3: (max - min) / median of the depths <= max_rel_spread.
    E4: the shallowest depth > contam_factor x the TIC contamination ratio, so no
        catalogued neighbour can make the eclipse."""
    deep = [d for d in depths if d > min_depth]
    e1 = len(deep) >= min_n
    e2 = (rms_oc_d * 1440.0 < max_rms_min) and (abs(p_fit - p_gaia) <= 3.0 * p_gaia_err)
    med = median(depths)
    spread = (max(depths) - min(depths)) / med if depths and med > 0 else float("inf")
    e3 = spread <= max_rel_spread
    e4 = bool(depths) and min(depths) > contam_factor * contam
    return {"E1": e1, "E2": e2, "E3": e3, "E4": e4, "all": e1 and e2 and e3 and e4,
            "n_deep": len(deep), "rms_oc_min": rms_oc_d * 1440.0,
            "p_diff_sigma": abs(p_fit - p_gaia) / p_gaia_err if p_gaia_err > 0 else float("inf"),
            "depth_spread": spread}
