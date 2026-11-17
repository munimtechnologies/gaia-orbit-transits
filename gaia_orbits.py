# SPDX-License-Identifier: Apache-2.0
"""Gaia astrometric orbits -> geometry, rough masses and predicted conjunctions.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0.

Conventions (Gaia DR3, Halbwachs et al. 2023):
  delta_dec   = A X + F Y
  delta_alpha* = B X + G Y
  X = cos E - e,  Y = sqrt(1 - e^2) sin E,  M = 2 pi (t - Tp) / P
  Tp (t_periastron) is in days from gaia_source.ref_epoch (J2016.0 = JD 2457389.0
  for DR3, i.e. BTJD = t_periastron + 389.0; TCB/TDB difference ignored).
Astrometry alone fixes omega and Omega only modulo pi, so both conjunctions
(true anomaly f = pi/2 - omega and 3 pi/2 - omega) are always considered: for a
dark companion one of them is the transit and the other the occultation.

0.2.0 (2026-11-17):
  * Monte Carlo uses the full Gaia correlation matrix (corr_vec, column-major upper
    triangle in the parameter order of the solution type) when it is available.
  * Circular solutions (eccentricity and G not fitted, DR3 bit_index 8179/65435):
    Gaia fixes omega = 0, so G = -A F / B. The sampler now imposes that constraint
    instead of holding G fixed while A, B, F vary.
  * Every sample's omega is aligned (modulo pi) with the central omega, so "t1" and
    "t2" always label the same conjunction across samples.

0.3.0 (2026-11-17):
  * AstroSpectroSB1 solutions also carry the spectroscopic Thiele-Innes constants
    C = a1 sin(omega) sin(i) and H = a1 cos(omega) sin(i) (AU), which fix omega of
    the primary without the pi ambiguity. The companion passes in front of the
    primary (transit / primary eclipse) at true anomaly f = pi/2 - omega.
    This convention was checked against the 155 Gaia DR3 EclipsingSpectro
    solutions (RV omega and t_periastron) and the independent eclipse times in
    gaiadr3.vari_eclipsing_binary: the deeper eclipse falls at f = pi/2 - omega in
    every checked system (see findings/2026-11-17-sb1-transit-convention.md and
    TestTransitConvention). `transit_label()` says which of t1/t2 is the transit.
  * For circular AstroSpectroSB1 solutions (bit_index 65435) Gaia fixes omega = 0
    and C is not meaningful (DR3 catalogue validation, arXiv:2206.05989), so the
    sign of H decides: H > 0 -> transit at Tp + P/4.
"""
import numpy as np

GAIA_REF_BTJD = 389.0
RSUN_AU = 0.00465047
MJUP_MSUN = 9.5458e-4
YEAR_D = 365.25

# Parameter order of corr_vec / bit_index (Gaia DR3 data model, nss_two_body_orbit).
PARAM_ORDER = {
    "orbital": ["ra", "dec", "parallax", "pmra", "pmdec", "a_thiele_innes",
                "b_thiele_innes", "f_thiele_innes", "g_thiele_innes", "eccentricity",
                "period", "t_periastron"],
    "astrospectrosb1": ["ra", "dec", "parallax", "pmra", "pmdec", "a_thiele_innes",
                        "b_thiele_innes", "f_thiele_innes", "g_thiele_innes",
                        "c_thiele_innes", "h_thiele_innes", "center_of_mass_velocity",
                        "eccentricity", "period", "t_periastron"],
}
SAMPLE_KEYS = ["a_thiele_innes", "b_thiele_innes", "f_thiele_innes", "g_thiele_innes",
               "eccentricity", "period", "t_periastron"]

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
    # u^2 - v^2 = ((A-G)^2 + (B+F)^2) ((A+G)^2 + (B-F)^2) / 4 >= 0 (no rounding below 0)
    disc = 0.5 * np.sqrt(((A - G) ** 2 + (B + F) ** 2) * ((A + G) ** 2 + (B - F) ** 2))
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


def cosi_adql(prefix="n."):
    """ADQL expression for cos i from the Thiele-Innes columns (server-side filter).

    Same formula as thiele_innes_to_elements; the square root is written in factored
    form so it can never go negative through rounding. Checked live against the Gaia
    DR3 archive on 2026-11-17 (|cos i| < 0.2: 28,685 orbits with both forms).
    """
    A, B, F, G = (f"{prefix}{x}_thiele_innes" for x in "abfg")
    u = f"0.5*({A}*{A}+{B}*{B}+{F}*{F}+{G}*{G})"
    v = f"({A}*{G}-{B}*{F})"
    disc = (f"0.5*SQRT((({A}-{G})*({A}-{G})+({B}+{F})*({B}+{F}))"
            f"*(({A}+{G})*({A}+{G})+({B}-{F})*({B}-{F})))")
    return f"{v}/({u}+{disc})"


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


def transit_phase(e, omega_rv):
    """Phase after periastron (0..1) at which the companion passes in front of the
    primary, for the primary's spectroscopic argument of periastron omega_rv (rad).

    Standard RV convention (v = K [cos(omega + f) + e cos omega]): the primary is
    farthest from the observer at omega + f = pi/2. Checked against Gaia DR3
    EclipsingSpectro solutions (TestTransitConvention).
    """
    return true_to_mean(np.pi / 2 - _f(omega_rv), e) / (2 * np.pi)


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
    try:
        x = float(x) if x is not None else np.nan
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if not np.isfinite(x) else x


def _val(row, key, default=np.nan):
    try:
        v = row.get(key, default)
        v = float(v) if v is not None and v != "" else default
    except (TypeError, ValueError):
        return default
    return v


# ---------------------------------------------------------------- correlations
def param_names(solution_type):
    """corr_vec parameter order for an nss_solution_type, or None if unsupported."""
    st = str(solution_type or "").strip().strip('"').lower()
    if st.startswith("astrospectrosb1"):
        return PARAM_ORDER["astrospectrosb1"]
    if st.startswith("orbital"):
        return PARAM_ORDER["orbital"]
    return None


def parse_corr_vec(x):
    """corr_vec as served by the Gaia TAP CSV: '(0.11, -0.2, NaN, ...)' -> float array."""
    if x is None:
        return None
    if isinstance(x, (list, tuple, np.ndarray)):
        return np.asarray(x, dtype=float)
    s = str(x).strip().strip('"').strip()
    if not s or s.lower() in ("null", "nan", "--"):
        return None
    s = s.strip("()[]{}")
    parts = [p for p in s.replace(";", ",").replace(" ", ",").split(",") if p.strip()]
    out = []
    for p in parts:
        try:
            out.append(float(p))
        except ValueError:
            out.append(np.nan)
    return np.asarray(out, dtype=float)


def corr_matrix(vec, n):
    """Full n x n correlation matrix from Gaia's column-major upper-triangle vector.

    Element order: (0,1), (0,2), (1,2), (0,3), (1,3), (2,3), ... NaN (parameter not
    fitted) becomes 0.
    """
    vec = np.asarray(vec, dtype=float)
    if vec.size != n * (n - 1) // 2:
        raise ValueError(f"corr_vec has {vec.size} elements, expected {n * (n - 1) // 2}")
    R = np.eye(n)
    k = 0
    for j in range(1, n):
        for i in range(j):
            c = vec[k]
            R[i, j] = R[j, i] = c if np.isfinite(c) else 0.0
            k += 1
    return R


def _correlation_for_keys(row, keys):
    names = param_names(row.get("nss_solution_type"))
    vec = parse_corr_vec(row.get("corr_vec"))
    if names is None or vec is None:
        return None
    try:
        R = corr_matrix(vec, len(names))
    except ValueError:
        return None
    idx = [names.index(k) for k in keys]
    return R[np.ix_(idx, idx)]


def _mvn(mu, sd, R, n, rng):
    """n draws from N(mu, diag(sd) R diag(sd)); robust to non-PSD input."""
    sd = np.asarray(sd, float)
    C = np.asarray(R, float) * np.outer(sd, sd)
    C = 0.5 * (C + C.T)
    w, V = np.linalg.eigh(C)
    L = V * np.sqrt(np.clip(w, 0.0, None))
    z = rng.standard_normal((n, len(mu)))
    return np.asarray(mu, float) + z @ L.T


def is_circular_fixed(row):
    """True when Gaia fitted a circular orbit with omega fixed to 0 (G and e not fitted)."""
    return _nz(row.get("g_thiele_innes_error")) == 0.0 and \
        _nz(row.get("eccentricity_error")) == 0.0 and \
        abs(_nz(row.get("eccentricity"))) < 1e-3


def sample_orbit(row, n, rng, ref_btjd=None):
    """Monte Carlo samples of an orbit from a Gaia NSS row.

    Uses the catalogue correlation matrix (corr_vec) when available, otherwise
    independent Gaussian errors. row keys: nss_solution_type, corr_vec (optional),
    period, t_periastron, eccentricity, a/b/f/g_thiele_innes and their _error.
    ref_btjd: BTJD of the t_periastron reference epoch (default: row['ref_btjd'] or
    the module-level GAIA_REF_BTJD).
    """
    if ref_btjd is None:
        ref_btjd = _val(row, "ref_btjd", GAIA_REF_BTJD)
        if not np.isfinite(ref_btjd):
            ref_btjd = GAIA_REF_BTJD
    mu = np.array([_val(row, k, 0.0) if k == "eccentricity" else _val(row, k)
                   for k in SAMPLE_KEYS])
    if not np.isfinite(mu[4]):
        mu[4] = 0.0
    sd = np.array([_nz(row.get(k + "_error")) for k in SAMPLE_KEYS])
    R = _correlation_for_keys(row, SAMPLE_KEYS)
    used_corr = R is not None
    if R is None:
        R = np.eye(len(SAMPLE_KEYS))
    X = _mvn(mu, sd, R, n, rng)
    A, B, F, G, e, P, Tp = (X[:, i] for i in range(7))
    circular = is_circular_fixed(row)
    if circular:
        # Gaia convention for circular orbits: omega = 0  =>  G = -A F / B
        with np.errstate(divide="ignore", invalid="ignore"):
            G = np.where(np.abs(B) > 0, -A * F / B, G)
        e = np.zeros(n)
    P = np.abs(P)
    Tp = Tp + ref_btjd
    e = np.clip(e, 0.0, 0.97)
    el = thiele_innes_to_elements(A, B, F, G)
    # align omega of each sample with the central omega (mod pi): t1/t2 keep their meaning
    Gc = mu[3]
    if circular and abs(mu[1]) > 0:
        Gc = -mu[0] * mu[2] / mu[1]
    w_c = float(thiele_innes_to_elements(mu[0], mu[1], mu[2], Gc)["omega"])
    dw = np.mod(el["omega"] - w_c + np.pi / 2, np.pi) - np.pi / 2
    omega = w_c + dw
    t1, t2, f1, f2 = conjunction_times(Tp, P, e, omega)
    return {"P": P, "Tp": Tp, "e": e, "a0": el["a"], "cosi": el["cosi"],
            "omega": omega, "t1": t1, "t2": t2, "f1": f1, "f2": f2,
            "used_corr": used_corr, "circular": circular}


def central_conjunctions(row, ref_btjd=None):
    """Conjunction times (BTJD) from the catalogue central values (same labels as
    sample_orbit's t1/t2)."""
    if ref_btjd is None:
        ref_btjd = _val(row, "ref_btjd", GAIA_REF_BTJD)
        if not np.isfinite(ref_btjd):
            ref_btjd = GAIA_REF_BTJD
    A, B, F, G = (_val(row, f"{x}_thiele_innes") for x in "abfg")
    if is_circular_fixed(row) and abs(B) > 0:
        G = -A * F / B
    e = _val(row, "eccentricity", 0.0)
    e = 0.0 if not np.isfinite(e) else e
    el = thiele_innes_to_elements(A, B, F, G)
    t1, t2, _, _ = conjunction_times(_val(row, "t_periastron") + ref_btjd,
                                     _val(row, "period"), e, float(el["omega"]))
    return float(t1), float(t2)


# ---------------------------------------------------------------- RV: which conjunction transits
def rv_omega(row):
    """(omega_rv, snr) of the primary from the spectroscopic Thiele-Innes C and H.

    Only AstroSpectroSB1 solutions carry C and H. snr is the significance of the
    (C, H) amplitude a1 sin i along its own direction (for circular solutions: of
    H > 0). The precision of omega_rv itself is rv_omega_sd(). Returns (nan, 0)
    when the row has no usable C/H.
    """
    H = _val(row, "h_thiele_innes")
    if not np.isfinite(H):
        return np.nan, 0.0
    herr = _nz(row.get("h_thiele_innes_error"))
    if is_circular_fixed(row):
        # Gaia fixed omega = 0; C is not meaningful. H = a1 sin i > 0 for omega = 0.
        w = 0.0 if H >= 0 else np.pi
        return w, (abs(H) / herr if herr > 0 else np.nan)
    C = _val(row, "c_thiele_innes")
    if not np.isfinite(C):
        return np.nan, 0.0
    cerr = _nz(row.get("c_thiele_innes_error"))
    amp = float(np.hypot(C, H))
    if amp <= 0:
        return np.nan, 0.0
    err = float(np.hypot(C * cerr, H * herr)) / amp
    return float(np.arctan2(C, H)), (amp / err if err > 0 else np.nan)


def rv_omega_sd(row):
    """1-sigma uncertainty (rad) of omega_rv = atan2(C, H) from the C/H errors
    (C/H covariance ignored). 0 for circular solutions (omega fixed by Gaia; there
    the sign of H, i.e. rv_omega's snr, is what matters); nan without C/H."""
    H = _val(row, "h_thiele_innes")
    if not np.isfinite(H):
        return np.nan
    if is_circular_fixed(row):
        return 0.0
    C = _val(row, "c_thiele_innes")
    if not np.isfinite(C):
        return np.nan
    amp2 = C * C + H * H
    if amp2 <= 0:
        return np.nan
    cerr = _nz(row.get("c_thiele_innes_error"))
    herr = _nz(row.get("h_thiele_innes_error"))
    return float(np.hypot(H * cerr, C * herr) / amp2)


# a label is only given when omega_rv is known well enough to tell the two
# conjunctions apart (they differ by pi in omega): sigma_omega < 0.6 rad, or for
# circular solutions H > 0 at 2 sigma or more
MAX_OMEGA_SD = 0.6
MIN_CIRC_H_SNR = 2.0


def rv_transit_time(row, ref_btjd=None):
    """BTJD of a transit (companion in front of the primary) from the RV omega, or None."""
    w, snr = rv_omega(row)
    if not np.isfinite(w):
        return None
    if ref_btjd is None:
        ref_btjd = _val(row, "ref_btjd", GAIA_REF_BTJD)
        if not np.isfinite(ref_btjd):
            ref_btjd = GAIA_REF_BTJD
    e = 0.0 if is_circular_fixed(row) else _val(row, "eccentricity", 0.0)
    e = 0.0 if not np.isfinite(e) else e
    P = _val(row, "period")
    t = _val(row, "t_periastron") + ref_btjd + float(transit_phase(e, w)) * P
    return {"t_transit_rv_btjd": float(t), "omega_rv": float(w), "rv_omega_snr": snr}


def transit_label(row, ref_btjd=None):
    """Which central conjunction ('t1' or 't2') is the transit, from the RV omega.

    Returns a dict with transit_conj ('' when unknown), t_transit_rv_btjd,
    rv_offset_d (distance of the RV transit time from the chosen astrometric
    conjunction, modulo P), rv_omega_snr and rv_consistent (offset < 0.1 P).
    A large offset means the astrometric and spectroscopic omegas disagree; then
    both windows should be kept.
    """
    out = {"transit_conj": "", "t_transit_rv_btjd": np.nan, "rv_offset_d": np.nan,
           "rv_omega_snr": np.nan, "rv_omega_sd_rad": np.nan, "rv_consistent": False}
    r = rv_transit_time(row, ref_btjd)
    if r is None:
        return out
    wsd = rv_omega_sd(row)
    out["rv_omega_sd_rad"] = wsd
    out["rv_omega_snr"] = r["rv_omega_snr"]
    if is_circular_fixed(row):
        if not (np.isfinite(r["rv_omega_snr"]) and r["rv_omega_snr"] >= MIN_CIRC_H_SNR):
            return out
    elif not (np.isfinite(wsd) and wsd < MAX_OMEGA_SD):
        return out
    P = _val(row, "period")
    t1, t2 = central_conjunctions(row, ref_btjd)
    d1 = abs(np.mod(t1 - r["t_transit_rv_btjd"] + P / 2, P) - P / 2)
    d2 = abs(np.mod(t2 - r["t_transit_rv_btjd"] + P / 2, P) - P / 2)
    lab, off = ("t1", d1) if d1 <= d2 else ("t2", d2)
    out.update({"transit_conj": lab, "t_transit_rv_btjd": r["t_transit_rv_btjd"],
                "rv_offset_d": float(off), "rv_omega_snr": r["rv_omega_snr"],
                "rv_consistent": bool(off < 0.1 * P)})
    return out


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


def predict_next(samples, key, t_central, P_central, t_from):
    """Next conjunction after t_from: (centre BTJD, robust 1-sigma in days).

    t_central is the catalogue-central conjunction time for `key`. The spread is
    the scatter of the Monte Carlo samples around the central prediction; a sigma
    above P/4 means the phase is effectively unconstrained by then.
    """
    k = np.ceil((t_from - t_central) / P_central)
    tn = t_central + k * P_central
    off = phase_offsets(samples, key, tn)
    med = float(np.median(off))
    sig = float(1.4826 * np.median(np.abs(off - med)))
    return float(tn - med), sig


def window_match(samples, key, t_event, duration):
    """Bayes-factor-like score: P(|offset| < duration) under the Gaia orbit,
    divided by the same probability for a random time (2 duration / P)."""
    off = phase_offsets(samples, key, t_event)
    frac = float(np.mean(np.abs(off) < duration))
    base = float(np.median(np.clip(2 * duration / samples["P"], 1e-9, 1)))
    return {"median_offset_d": float(np.median(off)),
            "offset_sd_d": float(1.4826 * np.median(np.abs(off - np.median(off)))),
            "frac_in_window": frac, "bf": frac / base if base > 0 else np.nan}
