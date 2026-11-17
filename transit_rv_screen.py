# SPDX-License-Identifier: Apache-2.0
"""Screen Gaia's own photometric transit candidates with Gaia's own radial velocities.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.

Gaia DR3 published 214 transit candidates (vari_planetary_transit; 173 known planets and
41 new candidates, Panahi et al. 2022, A&A 663, A101). They were vetted with TESS
full-frame images, not with Gaia's RVS radial velocities. DR4 (2 Dec 2026) publishes
1,007 such candidates. This module asks, for every candidate:

 1. Does Gaia have a two-body orbit (nss_two_body_orbit) for the star? If an SB1 or
    astrometric orbit has the transit period, the companion's mass follows from Gaia
    alone (a "Gaia-only" mass for a transiting object). If it has another period, the
    system is hierarchical or one of the periods is an alias.
 2. Is the star's RV scatter (bright stars, rv_method_used = 1) too large for any planet?
    A planet of at most 13 Jupiter masses cannot move a ~1 M_sun star by more than about
    4 km/s at any period longer than 0.25 d.
 3. An astrometric acceleration (nss_acceleration_astro) marks an outer companion.

The RV scatter of an epoch series is recovered from the DR3 error model for bright stars,
radial_velocity_error = sqrt(pi / (2 N)) * sigma + 0.11 km/s (Katz et al. 2023). For a
sinusoidal signal of semi-amplitude K in noise sigma_n, sigma^2 = K^2 / 2 + sigma_n^2, so
K >= sqrt(2 (sigma^2 - sigma_n^2)) when sigma_n is an upper bound on the noise.
"""
import argparse
import csv
import io
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

VERSION = "0.1.0"
K_SUN = 212.908          # km/s, (2 pi G M_sun / 1 day)^(1/3); 28.43 m/s for M_Jup at 1 yr
MJUP = 9.5458e-4         # M_sun
RV_FLOOR = 0.11          # km/s, DR3 error floor for rv_method_used = 1
PLANET_MAX = 13 * MJUP   # deuterium-burning limit, M_sun
BD_MAX = 0.075           # hydrogen-burning limit, M_sun (about 78.6 M_Jup)
P_FLOOR = 0.25           # d, shortest orbit considered for a period-free planet bound
GAIA_TAP = ["https://gea.esac.esa.int/tap-server/tap/sync"]
SIMBAD_TAP = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
VIZIER_TAP = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- physics
def k_semi_amplitude(m2, p_days, m1, sini=1.0, e=0.0):
    """RV semi-amplitude of the primary (km/s) for companion m2 (M_sun), period p_days."""
    return K_SUN * m2 * sini / ((m1 + m2) ** (2.0 / 3.0) * p_days ** (1.0 / 3.0)
                                * math.sqrt(1.0 - e * e))


def mass_function(k, p_days, e=0.0):
    """Spectroscopic mass function m2^3 sin^3 i / (m1 + m2)^2 in M_sun (K in km/s)."""
    return (1.0 - e * e) ** 1.5 * k ** 3 * p_days / K_SUN ** 3


def min_companion_mass(k, p_days, m1, e=0.0):
    """Smallest m2 (M_sun, sin i = 1) that gives semi-amplitude k at period p_days."""
    f = mass_function(k, p_days, e)
    if not (f > 0) or not (m1 > 0):
        return 0.0
    lo, hi = 0.0, 1000.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mid ** 3 / (m1 + mid) ** 2 < f:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def epoch_scatter(rv_err, n, floor=RV_FLOOR):
    """Per-epoch RV scatter (km/s) implied by a DR3 radial_velocity_error (bright stars)."""
    try:
        rv_err, n = float(rv_err), int(n)
    except (TypeError, ValueError):
        return float("nan")
    if not (n >= 2) or not math.isfinite(rv_err):
        return float("nan")
    return max(rv_err - floor, 0.0) / math.sqrt(math.pi / (2.0 * n))


def k_lower(sigma_obs, sigma_noise):
    """Lower bound on a sinusoid's semi-amplitude from total scatter and a noise ceiling."""
    if not (math.isfinite(sigma_obs) and math.isfinite(sigma_noise)):
        return float("nan")
    v = sigma_obs ** 2 - sigma_noise ** 2
    return math.sqrt(2.0 * v) if v > 0 else 0.0


def period_match(p1, p2, rel_tol=2e-3, max_harmonic=3):
    """(n, m) with p1 / p2 = n / m within rel_tol, n, m <= max_harmonic; else None.

    Returns the simplest ratio (smallest n + m) that matches."""
    try:
        p1, p2 = float(p1), float(p2)
    except (TypeError, ValueError):
        return None
    if not (p1 > 0 and p2 > 0):
        return None
    best = None
    for n in range(1, max_harmonic + 1):
        for m in range(1, max_harmonic + 1):
            if math.gcd(n, m) != 1:
                continue
            if abs(p1 / p2 - n / m) <= rel_tol * n / m:
                if best is None or n + m < sum(best):
                    best = (n, m)
    return best


def _f(row, key):
    v = row.get(key, "")
    try:
        x = float(v)
        return x if math.isfinite(x) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def screen_row(row, sigma_noise=7.0, m1_default=1.0):
    """Classify one candidate. `row` is a dict of the screen query's columns."""
    out = {"source_id": row.get("source_id", "")}
    p_tr = _f(row, "transit_period")
    m1 = _f(row, "mass_flame")
    m1_used = m1 if m1 > 0 else m1_default
    out["m1_used"] = round(m1_used, 4)
    # 1. NSS orbit
    nss_type = (row.get("nss_type") or "").strip()
    p_nss = _f(row, "nss_period")
    k1 = _f(row, "nss_k1")
    k1e = _f(row, "nss_k1_error")
    ecc = _f(row, "nss_ecc")
    ecc = ecc if 0 <= ecc < 1 else 0.0
    out["nss_type"] = nss_type
    out["nss_period"] = p_nss
    out["nss_match"] = ""
    out["m2_from_k1"] = float("nan")
    out["m2_from_k1_lo2"] = float("nan")
    out["m2_from_k1_hi2"] = float("nan")
    if nss_type:
        pm = period_match(p_tr, p_nss)
        out["nss_match"] = "" if pm is None else f"{pm[0]}:{pm[1]}"
        if k1 > 0:
            out["m2_from_k1"] = min_companion_mass(k1, p_nss, m1_used, ecc)
            if k1e > 0:
                out["m2_from_k1_lo2"] = min_companion_mass(max(k1 - 2 * k1e, 0.0), p_nss, m1_used, ecc)
                out["m2_from_k1_hi2"] = min_companion_mass(k1 + 2 * k1e, p_nss, m1_used, ecc)
    # 2. RV scatter (bright-star method only)
    method = _f(row, "rv_method_used")
    n = _f(row, "rv_nb_transits")
    sig = epoch_scatter(row.get("radial_velocity_error"), n) if method == 1 else float("nan")
    variable = (_f(row, "rv_chisq_pvalue") <= 0.01 and _f(row, "rv_renormalised_gof") > 4
                and n >= 10)
    out["rv_sigma_obs"] = sig
    out["rv_variable"] = bool(variable)
    out["k_lower"] = k_lower(sig, sigma_noise) if variable else (0.0 if math.isfinite(sig) else float("nan"))
    out["k_planet_max_any_p"] = k_semi_amplitude(PLANET_MAX, P_FLOOR, m1_used)
    out["k_planet_max_at_p"] = (k_semi_amplitude(PLANET_MAX, p_tr, m1_used)
                                if p_tr > 0 else float("nan"))
    out["m2_min_rv_at_p"] = (min_companion_mass(out["k_lower"], p_tr, m1_used)
                             if p_tr > 0 and out["k_lower"] > 0 else float("nan"))
    # 3. acceleration
    out["accel"] = (row.get("accel_type") or "").strip()
    # classification (fixed rules)
    reasons = []
    if nss_type and out["nss_match"] and out["m2_from_k1"] == out["m2_from_k1"]:
        m2 = out["m2_from_k1"]
        hi = out["m2_from_k1_hi2"] if out["m2_from_k1_hi2"] == out["m2_from_k1_hi2"] else m2
        lo = out["m2_from_k1_lo2"] if out["m2_from_k1_lo2"] == out["m2_from_k1_lo2"] else m2
        if hi < PLANET_MAX:
            cls = "GAIA_MASS_PLANET"
        elif lo > BD_MAX:
            cls = "GAIA_MASS_STAR"
        elif lo >= PLANET_MAX and hi <= BD_MAX:
            cls = "GAIA_MASS_BROWN_DWARF"
        else:
            cls = "GAIA_MASS_BOUNDARY"
        reasons.append(f"{nss_type} at the transit period ({out['nss_match']}), m2 sin i = {m2:.4f} M_sun")
    elif nss_type.startswith("SB2"):
        cls = "DOUBLE_LINED"
        reasons.append(f"{nss_type} at P = {p_nss:.4f} d: two bright stars")
    elif nss_type.startswith("SB1") and out["m2_from_k1"] > BD_MAX:
        cls = "STELLAR_SB1_OTHER_PERIOD"
        reasons.append(f"SB1 at P = {p_nss:.4f} d with m2 sin i = {out['m2_from_k1']:.3f} M_sun")
    elif nss_type.startswith("SB1") and out["m2_from_k1"] == out["m2_from_k1"]:
        cls = "SB1_OTHER_PERIOD"
        reasons.append(f"SB1 at P = {p_nss:.4f} d (not the transit period), m2 sin i = {out['m2_from_k1']:.4f}")
    elif out["k_lower"] == out["k_lower"] and out["k_lower"] > out["k_planet_max_any_p"]:
        cls = "RV_EXCLUDES_PLANET_ONLY"
        reasons.append(f"K >= {out['k_lower']:.1f} km/s > {out['k_planet_max_any_p']:.2f} km/s "
                       f"(13 M_Jup at P = {P_FLOOR} d)")
    elif nss_type:
        cls = "ASTROMETRIC_OTHER_PERIOD"
        reasons.append(f"{nss_type} at P = {p_nss:.3f} d")
    elif variable:
        cls = "RV_VARIABLE_WEAK"
        reasons.append("RV-variable but the scatter is within the noise ceiling")
    elif math.isfinite(sig):
        cls = "RV_QUIET"
    else:
        cls = "NO_RV"
    if out["accel"]:
        reasons.append(f"astrometric {out['accel']}: outer companion")
    out["class"] = cls
    out["reasons"] = "; ".join(reasons)
    return out


# ---------------------------------------------------------------- queries
def screen_adql(schema="gaiadr3", table="vari_planetary_transit"):
    s = schema
    return (
        "SELECT v.source_id, v.transit_reference_time, v.transit_period, v.transit_depth, "
        "v.transit_duration, v.num_in_transit, g.ra, g.dec, g.phot_g_mean_mag, g.grvs_mag, "
        "g.bp_rp, g.parallax, g.ruwe, g.non_single_star, g.rv_method_used, g.rv_nb_transits, "
        "g.radial_velocity, g.radial_velocity_error, g.rv_amplitude_robust, g.rv_chisq_pvalue, "
        "g.rv_renormalised_gof, g.teff_gspphot, p.mass_flame, p.radius_flame, "
        "n.nss_solution_type AS nss_type, n.period AS nss_period, n.period_error AS nss_period_error, "
        "n.eccentricity AS nss_ecc, n.semi_amplitude_primary AS nss_k1, "
        "n.semi_amplitude_primary_error AS nss_k1_error, n.significance AS nss_significance, "
        "a.nss_solution_type AS accel_type, a.significance AS accel_significance "
        f"FROM {s}.{table} AS v JOIN {s}.gaia_source AS g ON g.source_id = v.source_id "
        f"LEFT JOIN {s}.astrophysical_parameters AS p ON p.source_id = v.source_id "
        f"LEFT JOIN {s}.nss_two_body_orbit AS n ON n.source_id = v.source_id "
        f"LEFT JOIN {s}.nss_acceleration_astro AS a ON a.source_id = v.source_id "
        "ORDER BY v.source_id")


def tap_csv(url, query, timeout=120, tries=3, lang="ADQL"):
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": lang, "FORMAT": "csv",
                                   "QUERY": query}).encode()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "gaia-orbit-transits"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                text = r.read().decode("utf-8", "replace")
            return list(csv.DictReader(io.StringIO(text)))
        except Exception as exc:
            last = exc
            log("tap retry", i + 1, url, exc)
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"TAP failed: {last}")


def simbad_lookup(source_ids, release="DR3"):
    """{source_id: (main_id, otype)} from SIMBAD TAP; {} on failure."""
    ids = ", ".join(f"'Gaia {release} {s}'" for s in source_ids)
    if not ids:
        return {}
    q = ("SELECT i.id, b.main_id, b.otype FROM ident AS i JOIN basic AS b ON i.oidref = b.oid "
         f"WHERE i.id IN ({ids})")
    try:
        rows = tap_csv(SIMBAD_TAP, q, timeout=60, tries=2)
    except Exception as exc:
        log("simbad failed", exc)
        return {}
    out = {}
    for r in rows:
        sid = (r.get("id") or "").split()[-1]
        out[sid] = (r.get("main_id", ""), r.get("otype", ""))
    return out


def vsx_cone(ra, dec, radius_arcsec=5.0):
    """List of (Name, Type, Period) from AAVSO VSX (VizieR B/vsx/vsx); None on failure."""
    q = ('SELECT "Name", "Type", "Period" FROM "B/vsx/vsx" WHERE 1=CONTAINS('
         f"POINT('ICRS', RAJ2000, DEJ2000), CIRCLE('ICRS', {ra}, {dec}, {radius_arcsec / 3600.0}))")
    try:
        rows = tap_csv(VIZIER_TAP, q, timeout=60, tries=2)
    except Exception as exc:
        log("vsx failed", exc)
        return None
    return [(r.get("Name", ""), r.get("Type", ""), r.get("Period", "")) for r in rows]


# ---------------------------------------------------------------- main
COLS = ["source_id", "class", "reasons", "transit_period", "transit_depth", "transit_duration",
        "phot_g_mean_mag", "grvs_mag", "m1_used", "nss_type", "nss_period", "nss_match",
        "m2_from_k1", "m2_from_k1_lo2", "m2_from_k1_hi2", "rv_method_used", "rv_nb_transits",
        "rv_amplitude_robust", "rv_variable", "rv_sigma_obs", "k_lower", "k_planet_max_any_p",
        "k_planet_max_at_p", "m2_min_rv_at_p", "accel", "ruwe", "ra", "dec",
        "simbad_main_id", "simbad_otype", "vsx"]


def run(rows, sigma_noise):
    out = []
    for row in rows:
        r = screen_row(row, sigma_noise=sigma_noise)
        for k in ("transit_period", "transit_depth", "transit_duration", "phot_g_mean_mag",
                  "grvs_mag", "rv_method_used", "rv_nb_transits", "rv_amplitude_robust",
                  "ruwe", "ra", "dec"):
            r[k] = row.get(k, "")
        out.append(r)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--schema", default="gaiadr3")
    ap.add_argument("--table", default="vari_planetary_transit")
    ap.add_argument("--sigma-noise", type=float, default=7.0,
                    help="RV noise ceiling per epoch, km/s (conservative for G_RVS <= 12)")
    ap.add_argument("--input-csv", default="", help="use a saved query result (offline)")
    ap.add_argument("--no-catalogues", action="store_true")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    if a.input_csv:
        with open(a.input_csv, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    else:
        q = screen_adql(a.schema, a.table)
        with open(os.path.join(a.out_dir, "screen_query.adql"), "w") as fh:
            fh.write(q + "\n")
        rows = tap_csv(GAIA_TAP[0], q)
        with open(os.path.join(a.out_dir, "screen_input.csv"), "w", newline="", encoding="utf-8") as fh:
            if rows:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
    log("rows", len(rows))
    res = run(rows, a.sigma_noise)
    # empirical noise check: scatter of bright-method stars that Gaia does not flag variable
    quiet = sorted(r["rv_sigma_obs"] for r in res
                   if r["rv_sigma_obs"] == r["rv_sigma_obs"] and not r["rv_variable"])
    noise = {"n_quiet": len(quiet)}
    if quiet:
        noise["median"] = quiet[len(quiet) // 2]
        noise["p90"] = quiet[min(len(quiet) - 1, int(0.9 * len(quiet)))]
        noise["max"] = quiet[-1]
    flagged = [r for r in res if r["class"] not in ("RV_QUIET", "NO_RV")]
    if not a.no_catalogues and flagged:
        sim = simbad_lookup([r["source_id"] for r in flagged],
                            release="DR3" if a.schema == "gaiadr3" else "DR4")
        for r in flagged:
            mid, ot = sim.get(str(r["source_id"]), ("", ""))
            r["simbad_main_id"], r["simbad_otype"] = mid, ot
            try:
                v = vsx_cone(float(r["ra"]), float(r["dec"]))
            except (TypeError, ValueError):
                v = None
            r["vsx"] = "failed" if v is None else "; ".join("|".join(x) for x in v)
    with open(os.path.join(a.out_dir, "transit_rv_screen.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in res:
            w.writerow(r)
    counts = {}
    for r in res:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    summary = {"version": VERSION, "schema": a.schema, "table": a.table, "n": len(res),
               "sigma_noise": a.sigma_noise, "classes": counts, "quiet_scatter_kms": noise,
               "flagged": [{k: r.get(k, "") for k in ("source_id", "class", "reasons",
                                                        "simbad_main_id", "simbad_otype", "vsx")}
                           for r in flagged]}
    with open(os.path.join(a.out_dir, "transit_rv_screen_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=str)
    print(json.dumps({"n": len(res), "classes": counts, "quiet_scatter_kms": noise}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
