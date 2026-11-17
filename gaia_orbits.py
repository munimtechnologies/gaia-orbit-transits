# SPDX-License-Identifier: Apache-2.0
"""Gaia astrometric orbits -> geometry, rough masses and predicted conjunctions.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0.

Conventions (Gaia DR3, Halbwachs et al. 2023):
  delta_dec   = A X + F Y
  delta_alpha* = B X + G Y
  X = cos E - e,  Y = sqrt(1 - e^2) sin E,  M = 2 pi (t - Tp) / P
  Tp (t_periastron) is in days from the reference epoch J2016.0 = JD 2457389.0,
  i.e. BTJD (BJD - 2457000) = t_periastron + 389.0 (TCB/TDB difference ignored).
Astrometry alone fixes omega and Omega only modulo pi, so both conjunctions
(true anomaly f = pi/2 - omega and 3 pi/2 - omega) are always considered: for a
dark companion one of them is the transit and the other the occultation.
"""
import numpy as np

GAIA_REF_BTJD = 389.0
RSUN_AU = 0.00465047
MJUP_MSUN = 9.5458e-4
YEAR_D = 365.25

# Rough main-sequence absolute-G relations (for ranking only, not for science claims).
_MG = np.array([0.5, 1.5, 2.5, 3.5, 4.4, 5.0, 5.6, 6.2, 6.9, 7.6, 8.4, 9.2, 10.0,
                10.8, 11.6, 12.5, 13.4, 14.5, 15.5])
_MASS = np.array([2.2, 1.7, 1.4, 1.15, 1.0, 0.92, 0.85, 0.78, 0.70, 0.62, 0.55, 0.48,
                  0.40, 0.32, 0.25, 0.19, 0.14, 0.11, 0.09])
_RAD = np.array([1.9, 1.6, 1.35, 1.15, 1.0, 0.9, 0.82, 0.75, 0.68, 0.62, 0.55, 0.48,
                 0.40, 0.31, 0.25, 0.20, 0.15, 0.12, 0.10])


def _f(x):
    return np.asarray(x, dtype=float)


def elements_to_thiele_innes(a, inc_deg, omega, Omega):
    """Campbell elements (a in mas, angles: inc in degrees, omega/Omega in radians)."""
    a, inc, w, W = _f(a), np.radians(_f(inc_deg)), _f(omega), _f(Omega)
    c = np.cos(inc)
    A = a * (np.cos(w) * np.cos(W) - np.sin(w) * np.sin(W) * c)
    B = a * (np.cos(w) * np.sin(W) + np.sin(w) * np.cos(W) * c)
    F = -a * (np.sin(w) * np.cos(W) + np.cos(w) * np.sin(W) * c)
    G = -a * (np.sin(w) * np.sin(W) - np.cos(w) * np.cos(W) * c)
    return A, B, F, G


def thiele_innes_to_elements(A, B, F, G):
    """Return dict a (same unit as A..G), cosi, inc_deg, omega, Omega (radians).

    Omega is returned in [0, pi); omega carries the same pi shift (astrometric
    ambiguity), in [0, 2 pi).
    """
    A, B, F, G = _f(A), _f(B), _f(F), _f(G)
    u = 0.5 * (A * A + B * B + F * F + G * G)
    v = A * G - B * F
    disc = np.sqrt(np.clip(u * u - v * v, 0.0, None))
    a2 = u + disc
    with np.errstate(invalid="ignore", divide="ignore"):
        cosi = np.where(a2 > 0, v / np.where(a2 > 0, a2, 1.0), np.nan)
    cosi = np.clip(cosi, -1.0, 1.0)
    s = np.arctan2(B - F, A + G)      # omega + Omega
    d = np.arctan2(-B - F, A - G)     # omega - Omega
    omega = 0.5 * (s + d)
    Omega = 0.5 * (s - d)
    shift = np.where(Omega < 0, np.pi, 0.0)
    Omega = Omega + shift
    omega = omega + shift
    shift = np.where(Omega >= np.pi, -np.pi, 0.0)
    Omega = Omega + shift
    omega = np.mod(omega + shift, 2 * np.pi)
    return {"a": np.sqrt(a2), "cosi": cosi, "inc_deg": np.degrees(np.arccos(cosi)),
            "omega": omega, "Omega": Omega}


def solve_kepler(M, e, iters=40):
    M, e = _f(M), _f(e)
    E = np.where(e < 0.8, M, np.pi * np.ones_like(M))
    for _ in range(iters):
        E = E - (E - e * np.sin(E) - M) / (1 - e * np.cos(E))
    return E


def sky_position(t, P, Tp, e, A, B, F, G):
    """Photocentre offset (delta_alpha*, delta_dec) at times t."""
    M = 2 * np.pi * (_f(t) - Tp) / P
    E = solve_kepler(np.mod(M, 2 * np.pi), e)
    X = np.cos(E) - e
    Y = np.sqrt(1 - e * e) * np.sin(E)
    return B * X + G * Y, A * X + F * Y


def true_to_mean(f, e):
    f, e = _f(f), _f(e)
    E = 2 * np.arctan2(np.sqrt(1 - e) * np.sin(f / 2), np.sqrt(1 + e) * np.cos(f / 2))
    return np.mod(E - e * np.sin(E), 2 * np.pi)


def conjunction_times(Tp, P, e, omega):
    """Two conjunction times in [Tp, Tp + P), and the true anomalies used."""
    f1 = np.pi / 2 - _f(omega)
    f2 = 3 * np.pi / 2 - _f(omega)
    t1 = Tp + true_to_mean(f1, e) / (2 * np.pi) * P
    t2 = Tp + true_to_mean(f2, e) / (2 * np.pi) * P
    return t1, t2, f1, f2


def ms_mass_radius(abs_g):
    g = _f(abs_g)
    return np.interp(g, _MG, _MASS), np.interp(g, _MG, _RAD)


def companion_mass_dark(a0_mas, plx_mas, P_days, m1):
    """Companion mass (Msun) if the companion is dark (photocentre = primary)."""
    a1 = _f(a0_mas) / _f(plx_mas)
    pyr = _f(P_days) / YEAR_D
    fm = a1 ** 3 / pyr ** 2
    m1 = _f(m1)
    m2 = np.cbrt(fm * m1 ** 2)
    for _ in range(80):
        m2 = np.cbrt(fm * (m1 + m2) ** 2)
    return m2


def companion_radius(m2):
    m2 = _f(m2)
    return np.where(m2 < 0.08, 0.10, np.maximum(0.10, m2 ** 0.9))


def classify(m2):
    m2 = float(m2)
    if not np.isfinite(m2):
        return "unknown"
    if m2 < 13 * MJUP_MSUN:
        return "planet"
    if m2 < 0.075:
        return "brown-dwarf"
    return "star"


def _nz(x):
    x = float(x) if x is not None else np.nan
    return 0.0 if not np.isfinite(x) else x


def sample_orbit(row, n, rng):
    """Monte Carlo samples of an orbit from a Gaia NSS row (independent errors).

    row keys: period, period_error, t_periastron, t_periastron_error, eccentricity,
    eccentricity_error, a/b/f/g_thiele_innes (+ _error).
    """
    def draw(key):
        mu = float(row[key])
        sd = _nz(row.get(key + "_error"))
        return mu + sd * rng.standard_normal(n)

    P = np.abs(draw("period"))
    Tp = draw("t_periastron") + GAIA_REF_BTJD
    e0 = row.get("eccentricity")
    e0 = float(e0) if e0 is not None and np.isfinite(float(e0)) else 0.0
    e = np.clip(e0 + _nz(row.get("eccentricity_error")) * rng.standard_normal(n), 0.0, 0.97)
    A = draw("a_thiele_innes")
    B = draw("b_thiele_innes")
    F = draw("f_thiele_innes")
    G = draw("g_thiele_innes")
    el = thiele_innes_to_elements(A, B, F, G)
    t1, t2, f1, f2 = conjunction_times(Tp, P, e, el["omega"])
    return {"P": P, "Tp": Tp, "e": e, "a0": el["a"], "cosi": el["cosi"],
            "omega": el["omega"], "t1": t1, "t2": t2, "f1": f1, "f2": f2}


def eclipse_geometry(s, m1, r1, m2, r2):
    """Per-sample eclipse possibility and duration at each conjunction."""
    a_au = np.cbrt((m1 + m2) * (s["P"] / YEAR_D) ** 2)
    out = {}
    for k in ("1", "2"):
        f = s["f" + k]
        rc = a_au * (1 - s["e"] ** 2) / (1 + s["e"] * np.cos(f))
        lim = (r1 + r2) * RSUN_AU / rc
        out["ecl" + k] = np.abs(s["cosi"]) < lim
        b = np.abs(s["cosi"]) * rc / ((r1 + r2) * RSUN_AU)
        dur = (s["P"] / np.pi) * ((r1 + r2) * RSUN_AU / a_au) * np.sqrt(1 - s["e"] ** 2) \
            / (1 + s["e"] * np.cos(f)) * np.sqrt(np.clip(1 - b * b, 0, 1))
        out["dur" + k] = dur
        out["dur_central" + k] = (s["P"] / np.pi) * ((r1 + r2) * RSUN_AU / a_au) \
            * np.sqrt(1 - s["e"] ** 2) / (1 + s["e"] * np.cos(f))
    return out


def conj_times_in_range(t_ref, P, tmin, tmax):
    """All times t_ref + k P within [tmin, tmax] for scalar t_ref, P."""
    k0 = np.ceil((tmin - t_ref) / P)
    k1 = np.floor((tmax - t_ref) / P)
    if k1 < k0:
        return np.empty(0)
    return t_ref + P * np.arange(k0, k1 + 1)


def coverage_fraction(samples, key, obs_t, half_width):
    """Fraction of MC samples with at least one conjunction (key 't1'/'t2')
    falling within half_width of an observed (binned) time."""
    obs_t = np.sort(np.asarray(obs_t, float))
    if obs_t.size == 0:
        return 0.0
    tmin, tmax = obs_t[0], obs_t[-1]
    hit = 0
    n = len(samples["P"])
    for j in range(n):
        tc = conj_times_in_range(samples[key][j], samples["P"][j], tmin - 1, tmax + 1)
        if tc.size == 0:
            continue
        idx = np.clip(np.searchsorted(obs_t, tc), 1, obs_t.size - 1)
        near = np.minimum(np.abs(obs_t[idx] - tc), np.abs(obs_t[idx - 1] - tc))
        if np.any(near <= half_width):
            hit += 1
    return hit / max(n, 1)


def phase_offsets(samples, key, t_event):
    """Offset (days) of t_event from the nearest predicted conjunction, per sample."""
    P = samples["P"]
    return np.mod(t_event - samples[key] + P / 2, P) - P / 2


def window_match(samples, key, t_event, duration):
    """Bayes-factor-like score: P(|offset| < duration) under the Gaia orbit,
    divided by the same probability for a random time (2 duration / P)."""
    off = phase_offsets(samples, key, t_event)
    frac = float(np.mean(np.abs(off) < duration))
    base = float(np.median(np.clip(2 * duration / samples["P"], 1e-9, 1)))
    return {"median_offset_d": float(np.median(off)),
            "offset_sd_d": float(1.4826 * np.median(np.abs(off - np.median(off)))),
            "frac_in_window": frac, "bf": frac / base if base > 0 else np.nan}
