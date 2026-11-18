# SPDX-License-Identifier: Apache-2.0
"""calib_dr4.py -- grade the DR3 eclipse deficit against Gaia DR4 orbits (K1-K6).

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Pre-registration: findings/2026-11-18-calib-dr4-prereg.md (written before Gaia DR4).

0.1.0 holds the schema-independent part, fixed before the data exist:
  * label_orbit: CONFIRMED / ALIAS / CHANGED / DROPPED / UNTESTABLE for one DR3 orbit,
  * wilson / newcombe_diff: binomial intervals,
  * grade: the pre-registered predictions K1-K6 and the reading.
The DR4 fetch (cross-match, nss_two_body_orbit, cos i and its error) is added once the
draft data model gives the exact table and column names (job gaia-dr4dm-v2).
Stdlib only.
"""
import math

VERSION = "0.1.0"
Z95 = 1.959963984540054
REL_TOL = 0.005          # 0.5% of P3
NSIG = 3.0
ALIASES = (1.0 / 3.0, 0.5, 2.0, 3.0)
FAIL_LABELS = ("ALIAS", "CHANGED", "DROPPED")
TESTABLE = ("CONFIRMED",) + FAIL_LABELS


def _f(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def label_orbit(p3, s3, p4, s4, matched=True, rel_tol=REL_TOL, nsig=NSIG, aliases=ALIASES):
    """Label one DR3 orbit (period p3 +- s3) against its DR4 orbit (p4 +- s4).
    matched=False (no or ambiguous DR4 source) -> UNTESTABLE; p4 None -> DROPPED."""
    if not matched:
        return "UNTESTABLE"
    p3 = _f(p3)
    if p3 is None or p3 <= 0:
        return "UNTESTABLE"
    p4 = _f(p4)
    if p4 is None:
        return "DROPPED"
    s3 = _f(s3) or 0.0
    s4 = _f(s4) or 0.0

    def close(a):
        tol = max(nsig * math.hypot(a * s3, s4), rel_tol * a * p3)
        return abs(p4 - a * p3) <= tol

    if close(1.0):
        return "CONFIRMED"
    if any(close(a) for a in aliases):
        return "ALIAS"
    return "CHANGED"


def wilson(x, n, z=Z95):
    """Wilson score interval for x successes in n trials; (0, 1) when n = 0."""
    if n <= 0:
        return (0.0, 1.0)
    p = x / n
    z2 = z * z
    den = 1.0 + z2 / n
    centre = (p + z2 / (2.0 * n)) / den
    half = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def newcombe_diff(x1, n1, x2, n2, z=Z95):
    """Newcombe (1998, method 10) hybrid score interval for p1 - p2.
    Returns (d, lo, hi); d is nan when either n is 0."""
    if n1 <= 0 or n2 <= 0:
        return (float("nan"), -1.0, 1.0)
    p1, p2 = x1 / n1, x2 / n2
    l1, u1 = wilson(x1, n1, z)
    l2, u2 = wilson(x2, n2, z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (d, lo, hi)


def _frac(rows, cond):
    n = len(rows)
    x = sum(1 for r in rows if cond(r))
    return x, n, (x / n if n else float("nan"))


def _not_edge_on(r, nsd):
    c, sd, lim = _f(r.get("cosi4")), _f(r.get("cosi4_sd")), _f(r.get("lim4"))
    if c is None or sd is None or lim is None:
        return None
    return abs(c) > lim + nsd * sd


def grade(rows):
    """rows: dicts with group ('E' seen at 9 sigma / 'N' not seen), label (label_orbit),
    and for CONFIRMED rows cosi4, cosi4_sd, lim4 (DR4) and z4 (DR4-propagated offset of the
    observed TESS eclipse, in DR4 sigma_t units; None if not timed).
    Returns the pre-registered grades and the reading."""
    E = [r for r in rows if r.get("group") == "E" and r.get("label") in TESTABLE]
    N = [r for r in rows if r.get("group") == "N" and r.get("label") in TESTABLE]
    xe, ne, fe = _frac(E, lambda r: r["label"] in FAIL_LABELS)
    xn, nn, fn = _frac(N, lambda r: r["label"] in FAIL_LABELS)
    d, lo, hi = newcombe_diff(xn, nn, xe, ne)
    k1 = bool(nn and ne and d >= 0.15 and lo > 0)

    cn = [r for r in N if r["label"] == "CONFIRMED" and _not_edge_on(r, 2.0) is not None]
    ce = [r for r in E if r["label"] == "CONFIRMED" and _not_edge_on(r, 2.0) is not None]
    xcn, ncn, fcn = _frac(cn, lambda r: _not_edge_on(r, 2.0))
    xce, nce, fce = _frac(ce, lambda r: _not_edge_on(r, 2.0))
    k2 = bool(ncn and nce and fcn >= 0.5 and fce <= 0.2)

    ce3 = [r for r in E if r["label"] == "CONFIRMED" and _not_edge_on(r, 3.0) is not None]
    x3, n3, f3 = _frac(ce3, lambda r: not _not_edge_on(r, 3.0))
    k3 = bool(n3 and f3 >= 0.9)

    zs = [_f(r.get("z4")) for r in E if r["label"] == "CONFIRMED"]
    zs = [z for z in zs if z is not None]
    rms = math.sqrt(sum(z * z for z in zs) / len(zs)) if zs else float("nan")
    k4 = bool(len(zs) >= 5 and 0.7 <= rms <= 1.4)

    k5 = bool(nn and fn <= 0.15 and k2)
    k6 = bool(nn and fn >= 0.30 and k1)

    if k1 and k2:
        reading = "BOTH: wrong orbits and too-small errors"
    elif k1:
        reading = "F: mostly wrong orbits"
    elif k2:
        reading = "K: orbits right, errors too small"
    else:
        reading = "UNDECIDED: DR4 cannot separate the readings for this sample"
    n_untestable = sum(1 for r in rows if r.get("label") not in TESTABLE)
    return {
        "version": VERSION,
        "counts": {"E_testable": ne, "N_testable": nn, "untestable": n_untestable,
                   "labels": {lab: sum(1 for r in rows if r.get("label") == lab)
                              for lab in TESTABLE + ("UNTESTABLE",)}},
        "K1": {"fail_N": fn, "fail_E": fe, "diff": d, "lo95": lo, "hi95": hi,
               "fail_N_ci": wilson(xn, nn), "fail_E_ci": wilson(xe, ne), "pass": k1},
        "K2": {"N_conf_not_edge_on": fcn, "n_N_conf": ncn, "E_conf_not_edge_on": fce,
               "n_E_conf": nce, "pass": k2},
        "K3": {"E_conf_edge_on_3sd": f3, "n": n3, "pass": k3},
        "K4": {"rms_z4": rms, "n_timed": len(zs), "pass": k4},
        "K5": {"pass": k5},
        "K6": {"pass": k6},
        "reading": reading,
    }
