# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 MV2, Munim, Inc. Made with AI agents working in MV2's name.
"""conj_map: Gaia DR3 conjunction times, eclipse timing offsets and eclipse-star mapping.

Gaia DR3 nss_two_body_orbit gives t_periastron in days from BJD 2457389.0 (J2016.0), i.e.
BTJD = 389.0 + t_periastron. For circular solutions (SB1C/SB2C, e and omega empty) the
reference time is that of maximum radial velocity of component 1, so component 1 is behind
its companion at phase 0.25 and in front at phase 0.75. For eccentric orbits component 1 is
behind when nu + omega = 90 deg and in front when nu + omega = 270 deg.

Use: given an observed eclipse time (BTJD), find the nearer Gaia conjunction, the offset in
days and orbits, its uncertainty from Gaia's period and t_periastron errors, and which
Gaia component is eclipsed (behind) at that eclipse. sb2_ebfit's MAP_ASSUMED_BRIGHTER rule
can then be replaced by this timing-based rule (MAP_CONJUNCTION) for any orbit.
Standard library only.
"""
import math

VERSION = "0.1.0"
TP_REF_BTJD = 389.0  # BJD 2457389.0 - 2457000


def conj_phases(e=None, omega_deg=None):
    """Phases after t_periastron at which component 1 is (behind, in front)."""
    if e is None or omega_deg is None or not math.isfinite(e) or not math.isfinite(omega_deg):
        return (0.25, 0.75)
    out = []
    for target in (90.0, 270.0):
        nu = math.radians(target - omega_deg)
        E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0), math.sqrt(1.0 + e) * math.cos(nu / 2.0))
        M = E - e * math.sin(E)
        out.append((M / (2.0 * math.pi)) % 1.0)
    return (out[0], out[1])


def conj_times(P, tp, e=None, omega_deg=None):
    """Base-cycle BTJD of (component 1 behind, component 1 in front)."""
    ph_b, ph_f = conj_phases(e, omega_deg)
    base = TP_REF_BTJD + tp
    return (base + ph_b * P, base + ph_f * P)


def nearest(t, P, tp, e=None, omega_deg=None, P_err=0.0, tp_err=0.0):
    """Nearest Gaia conjunction to an observed eclipse time t (BTJD)."""
    best = None
    for kind, tc in zip(("star1_behind", "star1_in_front"), conj_times(P, tp, e, omega_deg)):
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


def map_eclipse(t0, P, tp, e=None, omega_deg=None, P_err=0.0, tp_err=0.0, max_orbit=0.1, max_z=3.0):
    """Which Gaia component is eclipsed at t0; MAP_CONJUNCTION if the timing is unambiguous."""
    r = nearest(t0, P, tp, e, omega_deg, P_err, tp_err)
    ok = abs(r["offset_orbit"]) <= max_orbit and (not math.isfinite(r["z"]) or abs(r["z"]) <= max_z)
    r["rule"] = "MAP_CONJUNCTION" if ok else "MAP_UNRESOLVED"
    return r


def binom_sf(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, j) * p ** j * (1.0 - p) ** (n - j) for j in range(k, n + 1))


def window_count(times_btjd, P, tp, e=None, omega_deg=None, half_width=0.08):
    """Number of times within +/- half_width orbit of either conjunction."""
    return sum(1 for t in times_btjd if abs(nearest(t, P, tp, e, omega_deg)["offset_orbit"]) <= half_width)
