#!/usr/bin/env python3
# vpt_nss.py - Gaia NSS orbit screen for Gaia transit candidates (step g2c, amendment 2).
# By MV2 of Munim, Inc. Made with AI agents working in his name. License: Apache-2.0.
# Pre-registration: findings/2026-11-22-vpt-nss-crossmatch.md, section 6.
"""Label Gaia transit candidates with Gaia's own orbit solutions.

Labels per star (most severe wins when a star has several solutions):
  NSS_STELLAR    double-lined solution, or minimum companion mass >= 0.08 Msun
  NSS_SUBSTELLAR spectroscopic solution with minimum companion mass < 0.08 Msun (a lead, never a veto)
  NSS_NO_K       solution without a primary velocity amplitude (astrometric or photometric only)
  NSS_NONE       no solution (only used when a candidate list is given)

Standard library only. Usage:
  python vpt_nss.py --in rows.csv --out-dir out/
  python vpt_nss.py --fetch --schema gaiadr4 --out-dir out/
"""
import argparse
import csv
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

VERSION = "0.1.0"
STELLAR_MIN_MSUN = 0.08
DEFAULT_M1_MSUN = 1.0
MF_CONST = 1.0361e-7  # Msun per (km/s)^3 per day
TAP_SYNC = "https://gea.esac.esa.int/tap-server/tap/sync"
SEVERITY = {"NSS_STELLAR": 3, "NSS_SUBSTELLAR": 2, "NSS_NO_K": 1, "NSS_NONE": 0}


def to_float(x):
    """float or None for blanks, junk and non-finite values."""
    if x is None:
        return None
    try:
        v = float(str(x).strip())
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def mass_function(k1_kms, period_d, ecc=0.0):
    """Spectroscopic mass function in Msun."""
    e = ecc if ecc is not None else 0.0
    return MF_CONST * (1.0 - e * e) ** 1.5 * k1_kms ** 3 * period_d


def min_companion_mass(k1_kms, period_d, m1_msun, ecc=0.0):
    """Companion mass for sin i = 1: solve m2^3 / (m1 + m2)^2 = f (monotonic in m2)."""
    f = mass_function(k1_kms, period_d, ecc)
    if f <= 0:
        return 0.0

    def g(m2):
        return m2 ** 3 / (m1_msun + m2) ** 2 - f

    lo, hi = 0.0, 1.0
    while g(hi) < 0 and hi < 1e4:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if g(mid) < 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def label_solution(sol_type, k1_kms, period_d, ecc, m1_msun):
    """Return (label, m2_min or None, m1_used or None)."""
    t = (sol_type or "").strip()
    if not t:
        return "NSS_NONE", None, None
    if "SB2" in t.upper():
        return "NSS_STELLAR", None, None
    if k1_kms is not None and period_d is not None and k1_kms > 0 and period_d > 0:
        m1 = m1_msun if (m1_msun is not None and m1_msun > 0) else DEFAULT_M1_MSUN
        m2 = min_companion_mass(k1_kms, period_d, m1, ecc if ecc is not None else 0.0)
        return ("NSS_STELLAR" if m2 >= STELLAR_MIN_MSUN else "NSS_SUBSTELLAR"), m2, m1
    return "NSS_NO_K", None, None


def screen_rows(rows):
    """rows: dicts with source_id, nss_solution_type, nss_period_d, k1_kms, eccentricity,
    bm_m1 (optional), vpt_period_d. Returns (per_solution, per_star)."""
    per_solution = []
    for r in rows:
        sid = str(r.get("source_id", "")).strip()
        if not sid:
            continue
        p_orb = to_float(r.get("nss_period_d"))
        p_vpt = to_float(r.get("vpt_period_d"))
        lab, m2, m1 = label_solution(r.get("nss_solution_type"), to_float(r.get("k1_kms")),
                                     p_orb, to_float(r.get("eccentricity")), to_float(r.get("bm_m1")))
        ratio = (p_orb / p_vpt) if (p_orb and p_vpt) else None
        per_solution.append({
            "source_id": sid,
            "nss_solution_type": (r.get("nss_solution_type") or "").strip(),
            "nss_period_d": p_orb,
            "vpt_period_d": p_vpt,
            "period_ratio_orbit_over_transit": ratio,
            "m1_used_msun": m1,
            "m2_min_msun": m2,
            "label": lab,
        })
    per_star = {}
    for s in per_solution:
        cur = per_star.get(s["source_id"])
        if cur is None or SEVERITY[s["label"]] > SEVERITY[cur["label"]]:
            per_star[s["source_id"]] = s
    return per_solution, per_star


def summarise(per_star, candidates=None):
    counts = {k: 0 for k in SEVERITY}
    for s in per_star.values():
        counts[s["label"]] += 1
    if candidates is not None:
        counts["NSS_NONE"] = len([c for c in candidates if c not in per_star])
    return {"version": VERSION, "n_stars_with_solution": len(per_star), "counts": counts}


def build_query(schema, with_masses=True):
    s = schema
    q = ("SELECT v.source_id, v.transit_period AS vpt_period_d, n.nss_solution_type, "
         "n.period AS nss_period_d, n.semi_amplitude_primary AS k1_kms, "
         "n.semi_amplitude_secondary AS k2_kms, n.eccentricity")
    if with_masses:
        q += ", b.m1 AS bm_m1"
    q += (" FROM %s.vari_planetary_transit AS v JOIN %s.nss_two_body_orbit AS n "
          "ON v.source_id = n.source_id" % (s, s))
    if with_masses:
        q += " LEFT OUTER JOIN %s.binary_masses AS b ON n.source_id = b.source_id" % s
    return q


def fetch_rows(schema, timeout=180):
    """Run the join on the ESA TAP sync endpoint; retry without binary_masses if it fails."""
    last = None
    for with_masses in (True, False):
        params = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                  "QUERY": build_query(schema, with_masses)}
        url = TAP_SYNC + "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                text = resp.read().decode("utf-8")
            return list(csv.DictReader(text.splitlines())), with_masses
        except (urllib.error.URLError, OSError) as exc:
            last = exc
    raise RuntimeError("TAP query failed: %r" % (last,))


def write_outputs(out_dir, per_solution, summary):
    os.makedirs(out_dir, exist_ok=True)
    cols = ["source_id", "nss_solution_type", "nss_period_d", "vpt_period_d",
            "period_ratio_orbit_over_transit", "m1_used_msun", "m2_min_msun", "label"]
    with open(os.path.join(out_dir, "nss_screen.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for s in per_solution:
            w.writerow({k: ("" if s[k] is None else s[k]) for k in cols})
    with open(os.path.join(out_dir, "nss_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gaia NSS screen for Gaia transit candidates (%s)" % VERSION)
    ap.add_argument("--in", dest="inp", help="CSV with the columns described in screen_rows")
    ap.add_argument("--fetch", action="store_true", help="query the ESA Gaia archive instead")
    ap.add_argument("--schema", default="gaiadr4")
    ap.add_argument("--candidates", help="optional CSV with a source_id column (all transit candidates)")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    meta = {}
    if a.fetch:
        rows, with_masses = fetch_rows(a.schema)
        meta = {"schema": a.schema, "with_binary_masses": with_masses, "n_rows": len(rows)}
        os.makedirs(a.out_dir, exist_ok=True)
        if rows:
            with open(os.path.join(a.out_dir, "nss_raw.csv"), "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
    elif a.inp:
        with open(a.inp, newline="") as fh:
            rows = list(csv.DictReader(fh))
    else:
        ap.error("give --in or --fetch")
    cands = None
    if a.candidates:
        with open(a.candidates, newline="") as fh:
            cands = [str(r["source_id"]).strip() for r in csv.DictReader(fh)]
    per_solution, per_star = screen_rows(rows)
    summary = summarise(per_star, cands)
    summary.update(meta)
    write_outputs(a.out_dir, per_solution, summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
