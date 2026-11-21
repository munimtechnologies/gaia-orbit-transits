# SPDX-License-Identifier: Apache-2.0
# Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents working in his name).
"""dr4_rows 0.1.0: turn Gaia DR4 nss_two_body_orbit rows into the DR3 row shape that
gaia_orbits.py and run_search.py (pinned, unchanged) read.

Why this exists (found 2026-11-21 from ESA's draft DR4 data model, read by job gaia-dr4dm-v2):
- DR4 renames columns that run_search 0.4.1's query selects: nss_solution_type -> solution_type,
  corr_vec -> correlations, goodness_of_fit -> gof; c_thiele_innes and h_thiele_innes are gone.
  The DR3 query would stop on release day with a column error.
- Worse, a silent trap: DR4 fits astrometric orbits in Campbell elements. Its correlation vector
  for solution_type Orbital is ordered (ra, dec, parallax, pmra, pmdec, semi_major_axis,
  arg_periastron, pos_ascending_node, inclination, eccentricity, period, t_periastron): 12
  parameters, the same length as DR3's Thiele-Innes order (ra, dec, parallax, pmra, pmdec, A, B,
  F, G, e, P, Tp). Read with the DR3 parameter names it would not fail; it would quietly give the
  wrong correlations to every Monte Carlo draw.

What it does: keeps Gaia's own central values (catalogue A, B, F, G when present), maps the DR4
covariance of (a0, omega, Omega, i [, K]) to (A, B, F, G [, C, H]) with the exact Jacobian
(linear propagation), and writes a DR3-order corr_vec and *_error columns. For AstroSpectroSB1 it
rebuilds C = a1 sin i sin(omega), H = a1 sin i cos(omega) [AU] from K, P, e and the RV-defined
omega, so gaia_orbits.rv_omega() returns DR4's omega unchanged.

Self-check per row (dr4_ti_check): A..G computed from DR4's Campbell elements must equal the
catalogue A..G within 1e-3 of a0 (STANDARD). OMEGA_PLUS_PI (all signs flipped) or MISMATCH
means DR4 uses another convention; run_search_dr4.py then stops (exit 4) before any search.

numpy is imported lazily so the stdlib-only test runner can import this module.
"""
import math

VERSION = "0.1.0"
AU_KM = 1.495978707e8
DAY_S = 86400.0
DEG = math.pi / 180.0
TI_TOL = 1e-3          # |catalogue - computed| / a0 for a STANDARD convention check

# Gaia DR4 draft data model, nss_two_body_orbit.bit_index tables (Orbital,
# OrbitalPoorlyConstrained; AstroSpectroSB1).
DR4_ORDER = {
    "orbital": ["ra", "dec", "parallax", "pmra", "pmdec", "semi_major_axis",
                "arg_periastron", "pos_ascending_node", "inclination", "eccentricity",
                "period", "t_periastron"],
    "astrospectrosb1": ["ra", "dec", "parallax", "pmra", "pmdec", "semi_major_axis",
                        "arg_periastron", "pos_ascending_node", "inclination",
                        "semi_amplitude_primary", "center_of_mass_velocity", "eccentricity",
                        "period", "t_periastron"],
}
# Must equal gaia_orbits.PARAM_ORDER (checked in the tests).
DR3_ORDER = {
    "orbital": ["ra", "dec", "parallax", "pmra", "pmdec", "a_thiele_innes",
                "b_thiele_innes", "f_thiele_innes", "g_thiele_innes", "eccentricity",
                "period", "t_periastron"],
    "astrospectrosb1": ["ra", "dec", "parallax", "pmra", "pmdec", "a_thiele_innes",
                        "b_thiele_innes", "f_thiele_innes", "g_thiele_innes",
                        "c_thiele_innes", "h_thiele_innes", "center_of_mass_velocity",
                        "eccentricity", "period", "t_periastron"],
}
TI_KEYS = ["a_thiele_innes", "b_thiele_innes", "f_thiele_innes", "g_thiele_innes"]
CAMPBELL_KEYS = ["semi_major_axis", "arg_periastron", "pos_ascending_node", "inclination"]

# Same placeholders as run_search.NSS_QUERY ({schema}, {gmax}, {cosi_server}, {extra} and the
# CHUNK marker); {cosi} is passed by build_nss_query but not needed: DR4 gives inclination.
DR4_NSS_QUERY = """
SELECT n.source_id, n.solution_type AS nss_solution_type, n.bit_index,
 n.correlations AS corr_vec_dr4, n.period, n.period_error,
 n.t_periastron, n.t_periastron_error, n.eccentricity, n.eccentricity_error,
 n.a_thiele_innes, n.a_thiele_innes_error, n.b_thiele_innes, n.b_thiele_innes_error,
 n.f_thiele_innes, n.f_thiele_innes_error, n.g_thiele_innes, n.g_thiele_innes_error,
 n.semi_major_axis, n.semi_major_axis_error, n.arg_periastron, n.arg_periastron_error,
 n.pos_ascending_node, n.pos_ascending_node_error, n.inclination, n.inclination_error,
 n.semi_amplitude_primary, n.semi_amplitude_primary_error,
 n.center_of_mass_velocity, n.center_of_mass_velocity_error,
 n.parallax AS nss_parallax, n.parallax_error AS nss_parallax_error,
 n.significance, n.gof AS goodness_of_fit,
 g.ra, g.dec, g.phot_g_mean_mag, g.bp_rp, g.ruwe, g.ref_epoch
FROM {schema}.nss_two_body_orbit AS n
JOIN {schema}.gaia_source AS g ON g.source_id = n.source_id
WHERE n.solution_type IN ('Orbital', 'AstroSpectroSB1') AND n.inclination IS NOT NULL
 AND g.phot_g_mean_mag < {gmax}
 AND ABS(COS(RADIANS(n.inclination))) < {cosi_server}{extra}/*CHUNK:n.source_id*/
"""

DR4_EB_QUERY = """
SELECT v.source_id FROM {schema}.vari_eclipsing_binary AS v
JOIN {schema}.nss_two_body_orbit AS n ON n.source_id = v.source_id
WHERE n.solution_type IN ('Orbital', 'AstroSpectroSB1') AND n.inclination IS NOT NULL
 AND ABS(COS(RADIANS(n.inclination))) < {cosi_server}/*CHUNK:v.source_id*/
"""

DR3_ONLY_SELECTS = ("n.nss_solution_type", "n.corr_vec", "n.goodness_of_fit",
                    "c_thiele_innes", "h_thiele_innes")


def _np():
    import numpy
    return numpy


def dr4_kind(solution_type):
    s = str(solution_type or "").strip().strip('"').lower()
    if s.startswith("astrospectrosb1"):
        return "astrospectrosb1"
    if s in ("orbital", "orbitalpoorlyconstrained"):
        return "orbital"
    return None


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return float("nan")
    return v


def _fin(*xs):
    return all(math.isfinite(_num(x)) for x in xs)


def _sd(x):
    v = _num(x)
    return v if math.isfinite(v) and v > 0 else 0.0


def campbell_to_ti(a, w, W, i):
    """Thiele-Innes A, B, F, G for semi-major axis a and omega, Omega, i in radians (standard
    convention; inverse of gaia_orbits.thiele_innes_to_elements)."""
    cw, sw, cW, sW, ci = math.cos(w), math.sin(w), math.cos(W), math.sin(W), math.cos(i)
    A = a * (cw * cW - sw * sW * ci)
    B = a * (cw * sW + sw * cW * ci)
    F = a * (-sw * cW - cw * sW * ci)
    G = a * (-sw * sW + cw * cW * ci)
    return A, B, F, G


def ti_jacobian(a, w, W, i):
    """d(A, B, F, G) / d(a, omega, Omega, i), angles in radians: 4 x 4 nested lists."""
    A, B, F, G = campbell_to_ti(a, w, W, i)
    cw, sw, cW, sW, si = math.cos(w), math.sin(w), math.cos(W), math.sin(W), math.sin(i)
    if a != 0:
        da = [A / a, B / a, F / a, G / a]
    else:
        ci = math.cos(i)
        da = [cw * cW - sw * sW * ci, cw * sW + sw * cW * ci,
              -sw * cW - cw * sW * ci, -sw * sW + cw * cW * ci]
    return [
        [da[0], F, -B, a * sw * sW * si],
        [da[1], G, A, -a * sw * cW * si],
        [da[2], -A, -G, a * cw * sW * si],
        [da[3], -B, F, -a * cw * cW * si],
    ]


def a1sini_au(K, P, e):
    return K * DAY_S * P * math.sqrt(max(0.0, 1.0 - e * e)) / (2 * math.pi * AU_KM)


def parse_vec(x):
    """Gaia TAP array cell -> list of floats (NaN kept), or None."""
    if x is None:
        return None
    if isinstance(x, (list, tuple)):
        return [_num(v) for v in x]
    try:
        import numpy
        if isinstance(x, numpy.ndarray):
            return [float(v) for v in x]
    except ImportError:
        pass
    s = str(x).strip().strip('"').strip()
    if not s or s.lower() in ("null", "nan", "--"):
        return None
    s = s.strip("()[]{}")
    parts = [p for p in s.replace(";", ",").replace(" ", ",").split(",") if p.strip()]
    return [_num(p) for p in parts]


def corr_from_vec(vec, n):
    """n x n correlation (numpy) from the column-major upper triangle; NaN -> 0; None if the
    length is wrong."""
    np = _np()
    if vec is None or len(vec) != n * (n - 1) // 2:
        return None
    R = np.eye(n)
    k = 0
    for j in range(1, n):
        for i in range(j):
            c = vec[k]
            R[i, j] = R[j, i] = c if math.isfinite(c) else 0.0
            k += 1
    return R


def vec_from_corr(R, sd):
    """Column-major upper triangle as a TAP-style string; NaN where a parameter has sd 0."""
    n = len(sd)
    out = []
    for j in range(1, n):
        for i in range(j):
            if sd[i] > 0 and sd[j] > 0:
                out.append(repr(float(R[i][j])))
            else:
                out.append("NaN")
    return "(" + ", ".join(out) + ")"


def build_jacobian(kind, vals):
    """J (numpy, n3 x n4) = d(DR3-order params) / d(DR4-order params), angles in degrees.

    vals: dict with semi_major_axis, arg_periastron, pos_ascending_node, inclination (deg),
    and for astrospectrosb1 semi_amplitude_primary, eccentricity, period."""
    np = _np()
    n4, n3 = DR4_ORDER[kind], DR3_ORDER[kind]
    J = np.zeros((len(n3), len(n4)))
    for r_i, name in enumerate(n3):
        if name in n4:
            J[r_i, n4.index(name)] = 1.0
    a = vals["semi_major_axis"]
    w = vals["arg_periastron"] * DEG
    W = vals["pos_ascending_node"] * DEG
    inc = vals["inclination"] * DEG
    jt = ti_jacobian(a, w, W, inc)
    cols = [n4.index(k) for k in CAMPBELL_KEYS]
    for r_k, key in enumerate(TI_KEYS):
        row = n3.index(key)
        for c_k, col in enumerate(cols):
            scale = 1.0 if c_k == 0 else DEG
            J[row, col] = jt[r_k][c_k] * scale
    if kind == "astrospectrosb1":
        K, P, e = vals["semi_amplitude_primary"], vals["period"], vals["eccentricity"]
        s = a1sini_au(K, P, e)
        dfac = {"semi_amplitude_primary": (s / K) if K else 0.0,
                "period": (s / P) if P else 0.0,
                "eccentricity": (-s * e / (1 - e * e)) if e * e < 1 else 0.0}
        ic, ih = n3.index("c_thiele_innes"), n3.index("h_thiele_innes")
        sw, cw = math.sin(w), math.cos(w)
        jw = n4.index("arg_periastron")
        J[ic, jw] = s * cw * DEG
        J[ih, jw] = -s * sw * DEG
        for k, d in dfac.items():
            J[ic, n4.index(k)] = d * sw
            J[ih, n4.index(k)] = d * cw
    return J


def convert_row(r, ti_tol=TI_TOL):
    """Return r (modified in place) in DR3 shape. Rows without DR4 orbit columns pass
    through unchanged (e.g. the eclipsing-binary id list)."""
    if "semi_major_axis" not in r and "corr_vec_dr4" not in r:
        return r
    np = _np()
    kind = dr4_kind(r.get("nss_solution_type"))
    r["dr4_adapter"] = VERSION
    if kind is None:
        r["dr4_ti_check"] = "UNSUPPORTED_TYPE"
        return r
    a = _num(r.get("semi_major_axis"))
    W = _num(r.get("pos_ascending_node"))
    inc = _num(r.get("inclination"))
    w = _num(r.get("arg_periastron"))
    e = _num(r.get("eccentricity"))
    if not math.isfinite(e):
        e = 0.0
    if not math.isfinite(w):
        w = 0.0          # circular: Gaia sets omega = 0 (periastron at the ascending node)
    if not _fin(a, W, inc):
        r["dr4_ti_check"] = "NO_CAMPBELL"
        return r
    calc = campbell_to_ti(a, w * DEG, W * DEG, inc * DEG)
    cat = [_num(r.get(k)) for k in TI_KEYS]
    if all(math.isfinite(c) for c in cat) and a > 0:
        d_std = max(abs(c - x) for c, x in zip(cat, calc)) / a
        d_flip = max(abs(c + x) for c, x in zip(cat, calc)) / a
        if d_std < ti_tol:
            r["dr4_ti_check"] = "STANDARD"
        elif d_flip < ti_tol:
            r["dr4_ti_check"] = "OMEGA_PLUS_PI"
        else:
            r["dr4_ti_check"] = "MISMATCH"
        r["dr4_ti_maxdev"] = min(d_std, d_flip)
        for k, c in zip(TI_KEYS, cat):
            r[k + "_dr4cat"] = c
            r[k + "_error_dr4cat"] = _num(r.get(k + "_error"))
    else:
        r["dr4_ti_check"] = "NO_CATALOGUE_TI"
        r["dr4_ti_maxdev"] = float("nan")
    central = cat if r["dr4_ti_check"] == "STANDARD" else list(calc)
    for k, v in zip(TI_KEYS, central):
        r[k] = v
    vals = {"semi_major_axis": a, "arg_periastron": w, "pos_ascending_node": W,
            "inclination": inc, "eccentricity": e,
            "period": _num(r.get("period")),
            "semi_amplitude_primary": _num(r.get("semi_amplitude_primary"))}
    names4, names3 = DR4_ORDER[kind], DR3_ORDER[kind]
    has_rv = kind == "astrospectrosb1" and _fin(vals["semi_amplitude_primary"], vals["period"])
    if kind == "astrospectrosb1":
        if has_rv:
            s = a1sini_au(vals["semi_amplitude_primary"], vals["period"], e)
            r["c_thiele_innes"] = s * math.sin(w * DEG)
            r["h_thiele_innes"] = s * math.cos(w * DEG)
        else:
            r["c_thiele_innes"] = float("nan")
            r["h_thiele_innes"] = float("nan")
    sd4 = np.array([_sd(r.get(k + "_error")) for k in names4])
    R4 = corr_from_vec(parse_vec(r.get("corr_vec_dr4")), len(names4))
    r["dr4_corr_used"] = R4 is not None
    if R4 is None:
        R4 = np.eye(len(names4))
    S4 = R4 * np.outer(sd4, sd4)
    if kind == "astrospectrosb1" and not has_rv:
        vals["semi_amplitude_primary"] = 0.0
        vals["period"] = vals["period"] if math.isfinite(vals["period"]) else 1.0
    J = build_jacobian(kind, vals)
    S3 = J @ S4 @ J.T
    sd3 = np.sqrt(np.clip(np.diag(S3), 0.0, None))
    with np.errstate(invalid="ignore", divide="ignore"):
        R3 = S3 / np.outer(np.where(sd3 > 0, sd3, 1.0), np.where(sd3 > 0, sd3, 1.0))
    R3 = np.clip(R3, -1.0, 1.0)
    np.fill_diagonal(R3, 1.0)
    r["corr_vec"] = vec_from_corr(R3.tolist(), sd3.tolist())
    for k, s in zip(names3, sd3.tolist()):
        if k in ("ra", "dec", "parallax", "pmra", "pmdec"):
            continue
        r[k + "_error"] = s
    return r


def summarise(rows):
    """Counts of the convention check over converted rows (for the release-day gate)."""
    out = {"version": VERSION, "n_rows": 0, "checks": {}, "n_corr_used": 0}
    for r in rows:
        if "dr4_ti_check" not in r:
            continue
        out["n_rows"] += 1
        c = r["dr4_ti_check"]
        out["checks"][c] = out["checks"].get(c, 0) + 1
        if r.get("dr4_corr_used"):
            out["n_corr_used"] += 1
    n_cmp = sum(out["checks"].get(k, 0) for k in ("STANDARD", "OMEGA_PLUS_PI", "MISMATCH"))
    out["n_compared"] = n_cmp
    out["standard_fraction"] = (out["checks"].get("STANDARD", 0) / n_cmp) if n_cmp else None
    return out


def gate(summary, min_standard=0.95, min_corr=0.5):
    """'' if the release-day search may go on, else the reason (pre-registered gate G0)."""
    if summary["n_rows"] == 0:
        return ""
    sf = summary["standard_fraction"]
    if sf is not None and sf < min_standard:
        return f"Thiele-Innes convention check: STANDARD fraction {sf:.3f} < {min_standard}"
    if summary["n_corr_used"] / summary["n_rows"] < min_corr:
        return (f"correlation vectors usable for {summary['n_corr_used']} of "
                f"{summary['n_rows']} rows (< {min_corr:.0%})")
    return ""
