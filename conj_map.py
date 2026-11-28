# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 MV2, Munim, Inc. Made with AI agents working in MV2's name.
"""conj_map: Gaia conjunction times, eclipse timing offsets and eclipse-star mapping.

Gaia DR3 nss_two_body_orbit gives t_periastron in days from BJD 2457389.0 (J2016.0), i.e.
BTJD = 389.0 + t_periastron. For circular solutions (SB1C/SB2C, e and omega empty) the
reference time is that of maximum radial velocity of component 1, so component 1 is behind
its companion at phase 0.25 and in front at phase 0.75. For eccentric orbits component 1 is
behind when nu + omega = 90 deg and in front when nu + omega = 270 deg.

0.2.0 (28 Nov 2026) adds Gaia DR4, following ESA's draft DR4 data model (2026-06-26,
section nss_two_body_orbit, read from job gaia-dr4dm-v2):
  * "The epoch at periastron is given relative to gaia_source.ref_epoch, in the range
    [-period/2, +period/2]". DR4's ref_epoch is J2017.5 (TCB), so BTJD = 936.875 + t_periastron.
    Using DR3's 389.0 for a DR4 row shifts every conjunction by 547.875 d, a non-integer
    number of orbits for almost every period, so ref="dr4" (or the row's ref_epoch) is needed.
  * Null eccentricity: for spectroscopic binaries t_periastron is the maximum of the radial
    velocity curve (same as DR3, phases 0.25 / 0.75); for EclipsingBinary and the combined
    EclipsingSpectroSB1/SB2 solutions it is the time of PRIMARY ECLIPSE (phases 0.0 / 0.5).
    Pass solution_type to get the right convention.
  * Gaia times are in TCB; TESS BTJD is in TDB. TCB - TDB is about 19.8 s (0.00023 d) in
    2017; tdb=True subtracts it from the conjunction times. The default (False) keeps every
    earlier DR3 result unchanged; the shift is far below Gaia's t_periastron errors.
  * from_row(row, release) turns a DR3/DR4 nss_two_body_orbit row (dict) into keyword
    arguments for conj_times / nearest / map_eclipse / window_count.
Epoch photometry time is unchanged in DR4: BJD(TCB) - 2455197.5, so BTJD = t_gaia - 1802.5.

Use: given an observed eclipse time (BTJD), find the nearer Gaia conjunction, the offset in
days and orbits, its uncertainty from Gaia's period and t_periastron errors, and which
Gaia component is eclipsed (behind) at that eclipse. sb2_ebfit's MAP_ASSUMED_BRIGHTER rule
can then be replaced by this timing-based rule (MAP_CONJUNCTION) for any orbit.
Standard library only.
"""
import math

VERSION = "0.2.0"
TP_REF_BTJD = 389.0  # BJD 2457389.0 - 2457000 (DR3, J2016.0); default, unchanged since 0.1.0
REF_BTJD = {"dr3": 389.0, "dr4": 936.875}  # J2016.0 and J2017.5 as BJD - 2457000
GAIA_TIME_TO_BTJD = -1802.5  # epoch photometry: BTJD = (BJD - 2455197.5) - 1802.5
L_B = 1.550519768e-8  # IAU 2006 Resolution B3
T0_JD = 2443144.5003725
TDB0_S = -6.55e-5


def ref_epoch_to_btjd(jyear):
    """Julian-year reference epoch (gaia_source.ref_epoch, e.g. 2016.0 or 2017.5) -> BJD - 2457000."""
    return 2451545.0 + (float(jyear) - 2000.0) * 365.25 - 2457000.0


def ref_btjd(ref=None):
    """Reference time (BTJD) for t_periastron. ref: None (DR3), 'dr3', 'dr4', or a BTJD number."""
    if ref is None:
        return TP_REF_BTJD
    if isinstance(ref, str):
        key = ref.strip().lower()
        if key not in REF_BTJD:
            raise ValueError("unknown Gaia release %r (use 'dr3', 'dr4' or a BTJD number)" % ref)
        return REF_BTJD[key]
    val = float(ref)
    if not math.isfinite(val):
        raise ValueError("reference time must be finite")
    return val


def tcb_minus_tdb_days(btjd):
    """TCB - TDB in days at a given time (BTJD), IAU 2006 B3: about 0.00023 d in 2017."""
    jd = float(btjd) + 2457000.0
    return L_B * (jd - T0_JD) - TDB0_S / 86400.0


def _finite(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


def is_eclipsing_solution(solution_type):
    return bool(solution_type) and str(solution_type).strip().lower().startswith("eclipsing")


def conj_phases(e=None, omega_deg=None, solution_type=None):
    """Phases after t_periastron at which component 1 is (behind, in front).

    Circular (e or omega missing): (0.25, 0.75) for spectroscopic solutions, where the
    reference time is maximum radial velocity; (0.0, 0.5) for Gaia's Eclipsing* solutions,
    where it is the primary eclipse (primary behind the secondary)."""
    if not _finite(e) or not _finite(omega_deg):
        if is_eclipsing_solution(solution_type):
            return (0.0, 0.5)
        return (0.25, 0.75)
    out = []
    for target in (90.0, 270.0):
        nu = math.radians(target - omega_deg)
        E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0), math.sqrt(1.0 + e) * math.cos(nu / 2.0))
        M = E - e * math.sin(E)
        out.append((M / (2.0 * math.pi)) % 1.0)
    return (out[0], out[1])


def conj_times(P, tp, e=None, omega_deg=None, ref=None, solution_type=None, tdb=False):
    """Base-cycle BTJD of (component 1 behind, component 1 in front)."""
    ph_b, ph_f = conj_phases(e, omega_deg, solution_type)
    base = ref_btjd(ref) + tp
    if tdb:
        base -= tcb_minus_tdb_days(base)
    return (base + ph_b * P, base + ph_f * P)


def nearest(t, P, tp, e=None, omega_deg=None, P_err=0.0, tp_err=0.0, ref=None, solution_type=None, tdb=False):
    """Nearest Gaia conjunction to an observed eclipse time t (BTJD)."""
    best = None
    for kind, tc in zip(("star1_behind", "star1_in_front"),
                        conj_times(P, tp, e, omega_deg, ref=ref, solution_type=solution_type, tdb=tdb)):
        n = round((t - tc) / P)
        off = t - tc - n * P
        if best is None or abs(off) < abs(best["offset_days"]):
            best = {"conj_kind": kind, "n_cycles": int(n), "offset_days": off}
    sig = math.hypot(tp_err or 0.0, abs(best["n_cycles"]) * (P_err or 0.0))
    best["offset_orbit"] = best["offset_days"] / P
    best["sigma_days"] = sig
    best["z"] = best["offset_days"] / sig if sig > 0 else float("nan")
    best["eclipsed"] = "gaia1" if best["conj_kind"] == "star1_behind" else "gaia2"
    return best


def map_eclipse(t0, P, tp, e=None, omega_deg=None, P_err=0.0, tp_err=0.0, max_orbit=0.1, max_z=3.0,
                ref=None, solution_type=None, tdb=False):
    """Which Gaia component is eclipsed at t0; MAP_CONJUNCTION if the timing is unambiguous."""
    r = nearest(t0, P, tp, e, omega_deg, P_err, tp_err, ref=ref, solution_type=solution_type, tdb=tdb)
    ok = abs(r["offset_orbit"]) <= max_orbit and (not math.isfinite(r["z"]) or abs(r["z"]) <= max_z)
    r["rule"] = "MAP_CONJUNCTION" if ok else "MAP_UNRESOLVED"
    return r


def binom_sf(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, j) * p ** j * (1.0 - p) ** (n - j) for j in range(k, n + 1))


def window_count(times_btjd, P, tp, e=None, omega_deg=None, half_width=0.08, ref=None, solution_type=None,
                 tdb=False):
    """Number of times within +/- half_width orbit of either conjunction."""
    return sum(1 for t in times_btjd
               if abs(nearest(t, P, tp, e, omega_deg, ref=ref, solution_type=solution_type,
                              tdb=tdb)["offset_orbit"]) <= half_width)


def _num(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x) if math.isfinite(x) else None
    s = str(x).strip()
    if s == "" or s.lower() in ("nan", "null", "none", "--"):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def from_row(row, release):
    """Keyword arguments for conj_times / nearest / map_eclipse / window_count from a Gaia
    nss_two_body_orbit row (dict with Gaia column names; strings or numbers).

    release: 'dr3' or 'dr4'. If the row carries ref_epoch (Julian year, from gaia_source),
    that epoch is used instead and must agree with the release's (else ValueError)."""
    if not isinstance(release, str):
        raise ValueError("release must be 'dr3' or 'dr4'")
    rel = ref_btjd(release)
    ref = rel
    rep = _num(row.get("ref_epoch"))
    if rep is not None:
        ref = ref_epoch_to_btjd(rep)
        if abs(ref - rel) > 1e-6:
            raise ValueError("row ref_epoch %s does not match release %s" % (rep, release))
    P = _num(row.get("period"))
    tp = _num(row.get("t_periastron"))
    if P is None or tp is None or P <= 0:
        raise ValueError("row needs a positive period and a t_periastron")
    return {"P": P, "tp": tp, "e": _num(row.get("eccentricity")), "omega_deg": _num(row.get("arg_periastron")),
            "P_err": _num(row.get("period_error")) or 0.0, "tp_err": _num(row.get("t_periastron_error")) or 0.0,
            "ref": ref, "solution_type": (row.get("nss_solution_type") or None)}
