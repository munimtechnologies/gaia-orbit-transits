# SPDX-License-Identifier: Apache-2.0
"""Gaia-only masses for eclipsing companions: Gaia SB1 orbits x Gaia eclipsing binaries.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.

Question. Gaia DR3 measured, independently, (a) single-lined spectroscopic orbits
(nss_two_body_orbit, SB1) and (b) eclipsing-binary light curves (vari_eclipsing_binary).
When both exist at the same period and the eclipse is a single shallow dip, Gaia alone
gives the companion's minimum mass (from K), its size (from the eclipse depth), which
conjunction the eclipse is (from the RV argument of periastron) and an independent mass
check (from the ellipsoidal amplitude). That is a Gaia-only catalogue of M dwarfs (and
possibly brown dwarfs or pre-white dwarfs) eclipsing hotter stars, the class the EBLM
project uses to measure M-dwarf radii. DR4 (2 Dec 2026) adds rvs_two_body_orbit
(638,966 SB1 orbits) and full epoch photometry, so the same code scales up.

Two Gaia-internal facts this module relies on (checked by hand, 2026-11-17):
 * derived_primary_ecl_depth = Gaussian depth + 2 x geom_model_cosine_half_period_amplitude
   when the model has an ellipsoidal term; the eclipse-only depth is the Gaussian depth.
 * The deeper eclipse falls at true anomaly f = pi/2 - omega (RV convention, primary
   farthest, companion in front); see findings/2026-11-17-sb1-transit-convention.md.

A false-positive mode it flags: near-equal eclipses (secondary >= 0.7 x primary) mean
near-equal stars, whose true mass function is >~ 0.1 M_sun. If Gaia's SB1 then gives
f(M) < 0.003 M_sun, K is diluted (blended double-lined spectrum fitted as SB1).

Stage 1 (Gaia TAP, seconds): sample, classes, Gaia-only physics. Stage 2 (TESS, lightkurve):
depth, occultation, ellipsoidal and radius for the lowest-mass candidates, with the
pre-registered verdict() of findings/2026-11-17-eblm-prereg.md.
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

VERSION = "0.1.0"
K_SUN = 212.908            # km/s: (2 pi G M_sun / 1 day)^(1/3)
RSUN_PER_AU = 215.032
GAIA_EPOCH_TO_J2016 = 2191.5   # Gaia vari time (BJD - 2455197.5) minus this = d from J2016.0
J2016_TO_BTJD = 389.0
BD_MAX = 0.075
GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
SIMBAD_TAP = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
# Approximate main-sequence radius of a ~5 Gyr M dwarf (M_sun -> R_sun), rounded values of
# the Baraffe et al. (2015) models; good to ~10%. Used only for a consistency ratio.
MS_TABLE = [(0.075, 0.095), (0.08, 0.10), (0.09, 0.11), (0.10, 0.12), (0.12, 0.145),
            (0.15, 0.175), (0.20, 0.225), (0.30, 0.31), (0.40, 0.39), (0.50, 0.47),
            (0.60, 0.56), (0.70, 0.65), (0.80, 0.75)]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- physics (pure)
def mass_function(k, p_days, e=0.0):
    """m2^3 sin^3 i / (m1 + m2)^2 in M_sun, K in km/s."""
    return (1.0 - e * e) ** 1.5 * k ** 3 * p_days / K_SUN ** 3


def min_companion_mass(k, p_days, m1, e=0.0):
    """m2 (M_sun) for sin i = 1."""
    f = mass_function(k, p_days, e)
    if not (f > 0 and m1 > 0):
        return float("nan")
    lo, hi = 0.0, 100.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mid ** 3 / (m1 + mid) ** 2 < f:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def semi_major_axis_rsun(p_days, mtot):
    return RSUN_PER_AU * (mtot * (p_days / 365.25) ** 2) ** (1.0 / 3.0)


def ellipsoidal_alpha(u=0.5, tau=0.4):
    """Morris (1985): 0.15 (15 + u)(1 + tau) / (3 - u)."""
    return 0.15 * (15.0 + u) * (1.0 + tau) / (3.0 - u)


def ellipsoidal_pred(m2, m1, r1, a_rsun, sini=1.0):
    """Semi-amplitude (flux fraction) of the half-period ellipsoidal term."""
    return ellipsoidal_alpha() * (m2 / m1) * (r1 / a_rsun) ** 3 * sini ** 2


def mag_to_flux(dmag):
    """Fractional flux drop for a magnitude depth."""
    return 1.0 - 10.0 ** (-0.4 * dmag)


def mag_amp_to_flux(amp_mag):
    """Small-amplitude magnitude semi-amplitude -> flux semi-amplitude."""
    return amp_mag / 1.0857362


def ms_radius(m):
    """Approximate main-sequence radius (R_sun) for mass m (M_sun), linear interpolation."""
    if not (m > 0):
        return float("nan")
    if m <= MS_TABLE[0][0]:
        return MS_TABLE[0][1]
    for (m0, r0), (m1_, r1_) in zip(MS_TABLE, MS_TABLE[1:]):
        if m <= m1_:
            return r0 + (r1_ - r0) * (m - m0) / (m1_ - m0)
    return MS_TABLE[-1][1] * (m / MS_TABLE[-1][0]) ** 0.8


def roche_lobe_fraction(q_primary_over_secondary):
    """Eggleton (1983) r_L / a of the star whose mass ratio to the other is q."""
    q = q_primary_over_secondary
    q23, q13 = q ** (2.0 / 3.0), q ** (1.0 / 3.0)
    return 0.49 * q23 / (0.6 * q23 + math.log(1.0 + q13))


def mean_anomaly_at_true(f, e):
    E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(f / 2.0), math.sqrt(1.0 + e) * math.cos(f / 2.0))
    return E - e * math.sin(E)


def conjunction_offset(t_ecl, t_peri, p_days, omega_deg, e=0.0, which="transit"):
    """Phase offset in [-0.5, 0.5) of an eclipse time from a conjunction.

    'transit': companion in front (f = pi/2 - omega); 'occultation': behind (3 pi/2 - omega).
    omega is the RV argument of periastron of the primary (degrees); times in days."""
    e = 0.0 if not (e == e) else e
    f = (0.5 if which == "transit" else 1.5) * math.pi - math.radians(omega_deg)
    t_c = t_peri + mean_anomaly_at_true(f, e) / (2.0 * math.pi) * p_days
    x = (t_ecl - t_c) / p_days
    return (x + 0.5) % 1.0 - 0.5


def planck_ratio(t2, t1, lam_um=0.8):
    c = 14387.77 / lam_um        # h c / (lambda k) in K
    return (math.exp(c / t1) - 1.0) / (math.exp(c / t2) - 1.0)


def companion_teff(depth_occ, k, t1, lam_um=0.8):
    """Brightness temperature of the companion from the occultation depth (TESS band)."""
    if not (depth_occ > 0 and k > 0 and t1 > 0):
        return float("nan")
    s = depth_occ / (k * k)      # surface-brightness ratio B(T2) / B(T1)
    c = 14387.77 / lam_um
    return c / math.log(1.0 + (math.exp(c / t1) - 1.0) / s)


# ---------------------------------------------------------------- Gaia stage
def sample_adql(schema="gaiadr3", ratio_tol=0.01):
    s = schema
    return (
        "SELECT n.source_id, n.period, n.period_error, n.t_periastron, n.eccentricity, "
        "n.arg_periastron, n.semi_amplitude_primary AS k1, n.semi_amplitude_primary_error AS k1_error, "
        "n.significance, v.frequency, v.reference_time, v.model_type, "
        "v.derived_primary_ecl_phase, v.derived_primary_ecl_depth, "
        "v.derived_secondary_ecl_phase, v.derived_secondary_ecl_depth, "
        "v.geom_model_gaussian1_phase, v.geom_model_gaussian1_depth, v.geom_model_gaussian1_depth_error, "
        "v.geom_model_gaussian2_phase, v.geom_model_gaussian2_depth, "
        "v.geom_model_cosine_half_period_amplitude AS ell_mag, "
        "v.geom_model_cosine_half_period_amplitude_error AS ell_mag_error, "
        "g.ra, g.dec, g.phot_g_mean_mag, g.bp_rp, g.ruwe, g.parallax, g.non_single_star, "
        "p.mass_flame, p.radius_flame, p.teff_gspphot "
        f"FROM {s}.nss_two_body_orbit AS n "
        f"JOIN {s}.vari_eclipsing_binary AS v ON v.source_id = n.source_id "
        f"JOIN {s}.gaia_source AS g ON g.source_id = n.source_id "
        f"LEFT JOIN {s}.astrophysical_parameters AS p ON p.source_id = n.source_id "
        f"WHERE n.nss_solution_type = 'SB1' AND ABS(n.period * v.frequency - 1) < {ratio_tol}")


def tap_csv(url, query, timeout=180, tries=3):
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                   "QUERY": query}).encode()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "gaia-orbit-transits"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return list(csv.DictReader(io.StringIO(r.read().decode("utf-8", "replace"))))
        except Exception as exc:
            last = exc
            log("tap retry", i + 1, exc)
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"TAP failed: {last}")


def _f(row, key):
    try:
        x = float(row.get(key, ""))
        return x if math.isfinite(x) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def eclipse_only_depths(row):
    """(primary, secondary) Gaussian depths in mag; the primary is the Gaussian whose phase
    is closest to derived_primary_ecl_phase. NaN where absent."""
    ph1 = _f(row, "derived_primary_ecl_phase")
    gs = [(_f(row, "geom_model_gaussian1_phase"), _f(row, "geom_model_gaussian1_depth")),
          (_f(row, "geom_model_gaussian2_phase"), _f(row, "geom_model_gaussian2_depth"))]
    gs = [g for g in gs if g[1] == g[1] and g[1] > 0]
    if not gs:
        return float("nan"), float("nan")

    def dist(p):
        d = abs(p - ph1) % 1.0
        return min(d, 1.0 - d) if ph1 == ph1 else 0.0
    gs.sort(key=lambda g: dist(g[0]))
    prim = gs[0][1]
    sec = gs[1][1] if len(gs) > 1 else float("nan")
    return prim, sec


def classify(row, m1_default=1.3):
    """Gaia-only physics and class for one SB1 x EB row (dict of sample_adql columns)."""
    P, K, e = _f(row, "period"), _f(row, "k1"), _f(row, "eccentricity")
    e = 0.0 if e != e else e
    out = {"source_id": row.get("source_id", ""), "period": P, "k1": K, "e": e}
    fm = mass_function(K, P, e)
    out["fm"] = fm
    d1, d2 = _f(row, "derived_primary_ecl_depth"), _f(row, "derived_secondary_ecl_depth")
    g1, g2 = eclipse_only_depths(row)
    out.update({"d1_mag": d1, "d2_mag": d2, "ecl1_mag": g1, "ecl2_mag": g2})
    twin = d1 > 0 and d2 == d2 and d2 >= 0.7 * d1
    single_shallow = (g1 == g1 and g1 < 0.1 and (g2 != g2 or g2 < 0.15 * g1))
    out["cls"] = ("twin_blend_suspect" if twin and fm < 0.003 else
                  "twin" if twin else "eblm_like" if single_shallow else "other")
    m1 = _f(row, "mass_flame")
    r1 = _f(row, "radius_flame")
    out["m1_flame"] = m1
    out["r1_flame"] = r1
    m1u = m1 if m1 == m1 else m1_default
    m2 = min_companion_mass(K, P, m1u, e)
    k_err = _f(row, "k1_error")
    out["m2"] = m2
    out["m2_lo2"] = min_companion_mass(max(K - 2 * k_err, 1e-6), P, m1u, e) if k_err == k_err else float("nan")
    out["m2_hi2"] = min_companion_mass(K + 2 * k_err, P, m1u, e) if k_err == k_err else float("nan")
    a = semi_major_axis_rsun(P, m1u + m2)
    out["a_rsun"] = a
    ell_obs = mag_amp_to_flux(_f(row, "ell_mag"))
    out["ell_obs"] = ell_obs
    if r1 == r1:
        out["ell_pred"] = ellipsoidal_pred(m2, m1u, r1, a)
        out["ell_ratio"] = ell_obs / out["ell_pred"] if out["ell_pred"] > 0 else float("nan")
        out["r1_over_a"] = r1 / a
        out["roche_fill"] = (r1 / a) / roche_lobe_fraction(m1u / m2) if m2 > 0 else float("nan")
        out["r2_gaia"] = r1 * math.sqrt(mag_to_flux(g1)) if g1 == g1 else float("nan")
        out["r2_ratio_ms"] = out["r2_gaia"] / ms_radius(m2)
    else:
        for k in ("ell_pred", "ell_ratio", "r1_over_a", "roche_fill", "r2_gaia", "r2_ratio_ms"):
            out[k] = float("nan")
    # which conjunction is the primary eclipse?
    t_ecl = (_f(row, "reference_time") + _f(row, "derived_primary_ecl_phase") / _f(row, "frequency")
             - GAIA_EPOCH_TO_J2016)
    om = _f(row, "arg_periastron")
    om = 0.0 if om != om else om
    tp = _f(row, "t_periastron")
    if t_ecl == t_ecl and tp == tp:
        out["dph_transit"] = conjunction_offset(t_ecl, tp, P, om, e, "transit")
        out["dph_occult"] = conjunction_offset(t_ecl, tp, P, om, e, "occultation")
        out["t0_btjd_pred"] = t_ecl + J2016_TO_BTJD
    for k in ("ra", "dec", "phot_g_mean_mag", "bp_rp", "ruwe", "teff_gspphot", "significance",
              "model_type", "non_single_star", "parallax"):
        out[k] = row.get(k, "")
    return out


def population_stats(rows):
    """Twin fraction (secondary >= 0.7 primary) per mass-function bin, two-eclipse rows only."""
    bins = [("fm<0.003", 0, 0.003), ("0.003-0.03", 0.003, 0.03), ("fm>0.03", 0.03, 1e9)]
    out = {}
    for name, lo, hi in bins:
        sel = [r for r in rows if lo <= r["fm"] < hi and r["d1_mag"] > 0 and r["d2_mag"] == r["d2_mag"]
               and r["d2_mag"] > 0]
        tw = [r for r in sel if r["d2_mag"] >= 0.7 * r["d1_mag"]]
        out[name] = {"n": len(sel), "twin": len(tw),
                     "twin_frac": round(len(tw) / len(sel), 3) if sel else None}
    return out


# ---------------------------------------------------------------- TESS stage
def robust_sd(x):
    import numpy as np
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(1.4826 * np.median(np.abs(x - np.median(x)))) if x.size > 1 else float("nan")


def measure(t, f, P, t0, dur):
    """Harmonic out-of-eclipse model (1, cos/sin 2 pi phi, cos/sin 4 pi phi), then primary and
    secondary (phase 0.5) depths and odd/even primary depths against it."""
    import numpy as np
    ph = ((t - t0) / P + 0.5) % 1.0 - 0.5
    half = 0.5 * dur / P
    in_p = np.abs(ph) < half
    ph_s = (ph + 1.0) % 1.0 - 0.5
    in_s = np.abs(ph_s) < half
    oot = (np.abs(ph) > 1.5 * half) & (np.abs(ph_s) > 1.5 * half)
    res = {"P": P, "t0": t0, "dur": dur, "n_in_p": int(in_p.sum()), "n_in_s": int(in_s.sum())}
    if oot.sum() < 20:
        return res
    w = 2 * np.pi * ph
    X = np.vstack([np.ones_like(ph), np.cos(w), np.sin(w), np.cos(2 * w), np.sin(2 * w)]).T
    coef, *_ = np.linalg.lstsq(X[oot], f[oot], rcond=None)
    r = f - X @ coef
    sd = robust_sd(r[oot])
    cov = np.linalg.inv(X[oot].T @ X[oot]) * sd ** 2
    res.update({"a_ell": float(-coef[3] / coef[0]), "err_a_ell": float(math.sqrt(cov[3, 3])),
                "a_ref": float(-coef[1] / coef[0]), "a_beam": float(coef[2] / coef[0]),
                "oot_sd": sd})
    epoch = np.round((t - t0) / P).astype(np.int64)
    for name, m in (("p", in_p), ("s", in_s), ("odd", in_p & (np.abs(epoch) % 2 == 1)),
                    ("even", in_p & (np.abs(epoch) % 2 == 0))):
        n = int(m.sum())
        if n >= 3:
            xbar = X[m].mean(axis=0)
            res[f"depth_{name}"] = float(-np.mean(r[m]))
            res[f"err_{name}"] = float(math.sqrt(sd ** 2 / n + float(xbar @ cov @ xbar)))
    return res


def verdict(v):
    """Pre-registered rules (findings/2026-11-17-eblm-prereg.md). Keys: snr, depth_p, err_p,
    depth_s, err_s, depth_odd, err_odd, depth_even, err_even, t2, teff1, a_ell, err_a_ell,
    ell_pred, r2, r_ms, m2_hi2. Returns (label, reasons)."""
    g = lambda k: v.get(k, float("nan"))
    if not (g("snr") >= 10 and g("depth_p") >= 3 * g("err_p")):
        return "NO_ECLIPSE", [f"SNR {g('snr'):.1f}, depth {g('depth_p'):.5f} +- {g('err_p'):.5f}"]
    if abs(g("depth_odd") - g("depth_even")) > 3 * math.hypot(g("err_odd"), g("err_even")):
        return "TWIN_AT_2P", ["odd and even eclipses differ by > 3 sigma"]
    ds, dp = g("depth_s"), g("depth_p")
    if (ds / dp >= 0.3) or (g("t2") >= 0.8 * g("teff1")):
        lab = "HOT_COMPANION" if g("t2") > g("teff1") else "LUMINOUS_COMPANION"
        return lab, [f"occultation/transit {ds / dp:.3f}, T2 {g('t2'):.0f} K vs T1 {g('teff1'):.0f} K"]
    a, ea, pr = g("a_ell"), g("err_a_ell"), g("ell_pred")
    if a - 3 * ea > 2 * pr:
        return "MASS_TENSION_HEAVIER", [f"ellipsoidal {a:.5f} > 2 x predicted {pr:.5f}"]
    if a + 3 * ea < 0.5 * pr:
        return "MASS_TENSION_LIGHTER", [f"ellipsoidal {a:.5f} < 0.5 x predicted {pr:.5f}"]
    ratio = g("r2") / g("r_ms")
    reasons = [f"R2 {g('r2'):.3f} R_sun vs main sequence {g('r_ms'):.3f} (x{ratio:.2f}); "
               f"ellipsoidal {a:.5f} vs predicted {pr:.5f}; T2 {g('t2'):.0f} K"]
    pre = "BD_" if g("m2_hi2") < BD_MAX else ""
    if ratio > 1.3:
        return pre + "EBLM_LARGE_RADIUS", reasons
    if ratio < 0.7:
        return pre + "EBLM_SMALL_RADIUS", reasons
    return pre + "EBLM_CONSISTENT", reasons


def resolve_tic(source_id, ra, dec):
    from astroquery.mast import Catalogs
    try:
        t = Catalogs.query_criteria(catalog="Tic", GAIA=str(source_id))
        if len(t):
            return int(t["ID"][0]), float(t["Tmag"][0])
    except Exception as exc:
        log("tic by gaia failed", exc)
    try:
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        t = Catalogs.query_region(SkyCoord(float(ra), float(dec), unit="deg"), radius=3 * u.arcsec,
                                  catalog="TIC")
        if len(t):
            t.sort("Tmag")
            return int(t["ID"][0]), float(t["Tmag"][0])
    except Exception as exc:
        log("tic by cone failed", exc)
    return None, float("nan")


def load_tess(tic, data_dir, max_sectors):
    import numpy as np
    import lightkurve as lk
    rank = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}
    sr = None
    for i in range(3):
        try:
            sr = lk.search_lightcurve(f"TIC {tic}", mission="TESS")
            break
        except Exception as exc:
            log("search retry", exc)
            time.sleep(5 * (i + 1))
    if sr is None or len(sr) == 0:
        return None, []
    tab = sr.table
    best = {}
    for i in range(len(sr)):
        auth = str(tab["author"][i])
        if auth not in rank:
            continue
        try:
            sec = int(tab["sequence_number"][i])
        except Exception:
            continue
        if sec not in best or rank[auth] < best[sec][0]:
            best[sec] = (rank[auth], i, auth)
    ts, fs, info = [], [], []
    for sec in sorted(best)[:max_sectors]:
        _, i, auth = best[sec]
        try:
            lc = sr[i].download(download_dir=data_dir, quality_bitmask="default")
            t = np.asarray(lc.time.value, float)
            f = np.asarray(getattr(lc.flux, "value", lc.flux), float)
            f = np.ma.filled(f, np.nan) if np.ma.isMaskedArray(f) else f
            ok = np.isfinite(t) & np.isfinite(f)
            t, f = t[ok], f[ok]
            if t.size < 100:
                continue
            f = f / np.nanmedian(f)
            keep = f > 0.5
            sd = robust_sd(f[keep])
            keep &= f < 1 + 6 * sd
            ts.append(t[keep])
            fs.append(f[keep])
            info.append({"sector": sec, "author": auth, "n": int(keep.sum())})
        except Exception as exc:
            info.append({"sector": sec, "author": auth, "error": str(exc)[:160]})
    if not ts:
        return None, info
    t = np.concatenate(ts)
    f = np.concatenate(fs)
    o = np.argsort(t)
    return (t[o], f[o]), info


def detrend(t, f, window):
    """Divide each segment (gaps > 0.5 d) by its running median over `window` days."""
    import numpy as np
    out = np.full_like(f, np.nan)
    cuts = np.where(np.diff(t) > 0.5)[0] + 1
    for seg in np.split(np.arange(t.size), cuts):
        if seg.size < 20:
            continue
        ts, fs = t[seg], f[seg]
        if ts[-1] - ts[0] < window:
            out[seg] = fs / np.median(fs)
            continue
        grid = np.arange(ts[0], ts[-1] + window / 4, window / 4)
        med = np.array([np.median(fs[np.abs(ts - g) <= window / 2]) if np.any(np.abs(ts - g) <= window / 2)
                        else np.nan for g in grid])
        ok = np.isfinite(med)
        out[seg] = fs / np.interp(ts, grid[ok], med[ok])
    return out


def vet_tess(c, data_dir, max_sectors, plot_dir=None):
    """TESS vetting of one classified candidate c (dict from classify())."""
    import numpy as np
    from astropy.timeseries import BoxLeastSquares
    res = {"source_id": c["source_id"]}
    tic, tmag = resolve_tic(c["source_id"], c["ra"], c["dec"])
    res.update({"tic": tic, "tmag": tmag})
    if tic is None:
        res["verdict"] = "NO_TIC"
        return res
    lc, info = load_tess(tic, data_dir, max_sectors)
    res["sectors"] = info
    if lc is None:
        res["verdict"] = "NO_TESS_DATA"
        return res
    t, f = lc
    P0 = c["period"]
    fd = detrend(t, f, window=max(2.0, 3.0 * P0))
    ok = np.isfinite(fd)
    t, fd = t[ok], fd[ok]
    # bin to 10 min
    idx = np.floor((t - t[0]) / (10.0 / 1440)).astype(np.int64)
    u_, inv, cnt = np.unique(idx, return_inverse=True, return_counts=True)
    bt = np.bincount(inv, weights=t) / cnt
    bf = np.bincount(inv, weights=fd) / cnt
    a_over_r1 = c["a_rsun"] / c["r1_flame"] if c.get("r1_flame") == c.get("r1_flame") else 4.0
    dur_c = P0 / math.pi * math.asin(min(1.0, 1.0 / a_over_r1))
    durs = np.clip(np.array([0.5, 0.7, 0.85, 1.0, 1.2]) * dur_c, 0.02, 0.4 * P0)
    periods = np.linspace(P0 * (1 - 1e-3), P0 * (1 + 1e-3), 3001)
    r = BoxLeastSquares(bt, bf).power(periods, durs, objective="snr")
    j = int(np.argmax(r.power))
    P, t0, dur = float(r.period[j]), float(r.transit_time[j]), float(r.duration[j])
    res.update({"P_tess": P, "t0_btjd": t0, "dur_d": dur, "snr": float(r.depth_snr[j]),
                "n_bins": int(bt.size)})
    m = measure(bt, bf, P, t0, dur)
    res.update(m)
    k = math.sqrt(max(m.get("depth_p", 0.0), 0.0))
    teff1 = _f(c, "teff_gspphot")
    ds = m.get("depth_s", float("nan"))
    t2 = companion_teff(ds, k, teff1) if ds == ds and ds > 0 else float("nan")
    t2_up = companion_teff(max(ds, 0.0) + 3 * m.get("err_s", float("nan")), k, teff1)
    r2 = c["r1_flame"] * k if c.get("r1_flame") == c.get("r1_flame") else float("nan")
    res.update({"k": k, "r2": r2, "r_ms": ms_radius(c["m2"]), "t2": t2, "t2_3sig_upper": t2_up,
                "teff1": teff1, "ell_pred": c.get("ell_pred", float("nan")), "m2_hi2": c["m2_hi2"],
                "ell_ratio_tess": m.get("a_ell", float("nan")) / c["ell_pred"] if c.get("ell_pred") else float("nan"),
                "gaia_ecl_depth_flux": mag_to_flux(c["ecl1_mag"]) if c["ecl1_mag"] == c["ecl1_mag"] else float("nan")})
    v = dict(res)
    if not (v["t2"] == v["t2"]):
        v["t2"] = 0.0                       # no occultation detected: cool companion
    label, reasons = verdict(v)
    res["verdict"], res["reasons"] = label, reasons
    if plot_dir:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            ph = ((bt - t0) / P + 0.25) % 1.0 - 0.25
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(ph, bf, ",", color="0.6")
            edges = np.linspace(-0.25, 0.75, 201)
            ib = np.digitize(ph, edges) - 1
            med = [np.median(bf[ib == i]) if np.any(ib == i) else np.nan for i in range(200)]
            ax.plot(0.5 * (edges[1:] + edges[:-1]), med, "k-")
            lo, hi = np.nanpercentile(bf, [0.3, 99.7])
            ax.set_ylim(lo, hi)
            ax.set_title(f"Gaia DR3 {c['source_id']} = TIC {tic}, P = {P:.6f} d: {label}")
            ax.set_xlabel("phase (0 = transit)")
            fig.tight_layout()
            fig.savefig(os.path.join(plot_dir, f"eblm_{c['source_id']}.png"), dpi=100)
            plt.close(fig)
        except Exception as exc:
            res["plot_error"] = str(exc)[:200]
    return res


def simbad_lookup(source_ids):
    ids = ", ".join(f"'Gaia DR3 {s}'" for s in source_ids)
    q = ("SELECT i.id, b.main_id, b.otype FROM ident AS i JOIN basic AS b ON i.oidref = b.oid "
         f"WHERE i.id IN ({ids})")
    try:
        rows = tap_csv(SIMBAD_TAP, q, timeout=90, tries=2)
    except Exception as exc:
        log("simbad failed", exc)
        return {}
    return {(r.get("id") or "").split()[-1]: (r.get("main_id", ""), r.get("otype", "")) for r in rows}


def catalogue_hits(ra, dec):
    """VSX and the TESS EB catalogue (Prsa et al. 2022) within 5 arcsec, via astroquery Vizier."""
    out = {}
    try:
        from astroquery.vizier import Vizier
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        c = SkyCoord(float(ra), float(dec), unit="deg")
        for key, cat in (("vsx", "B/vsx/vsx"), ("tess_eb", "J/ApJS/258/16")):
            try:
                res = Vizier(columns=["*"], row_limit=5).query_region(c, radius=5 * u.arcsec, catalog=cat)
                out[key] = [{k: str(row[k]) for k in res[0].colnames[:8]} for row in res[0]] if len(res) else []
            except Exception as exc:
                out[key] = f"failed: {str(exc)[:120]}"
    except Exception as exc:
        out["error"] = str(exc)[:160]
    return out


# ---------------------------------------------------------------- main
def _clean(x):
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def write_csv(path, rows, cols):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


CLS_COLS = ["source_id", "cls", "period", "k1", "e", "fm", "m1_flame", "r1_flame", "m2", "m2_lo2",
            "m2_hi2", "d1_mag", "d2_mag", "ecl1_mag", "ecl2_mag", "ell_obs", "ell_pred", "ell_ratio",
            "r1_over_a", "roche_fill", "r2_gaia", "r2_ratio_ms", "dph_transit", "dph_occult",
            "t0_btjd_pred", "phot_g_mean_mag", "bp_rp", "teff_gspphot", "ruwe", "significance",
            "model_type", "ra", "dec", "simbad_main_id", "simbad_otype"]
VET_COLS = ["source_id", "tic", "tmag", "verdict", "P_tess", "t0_btjd", "dur_d", "snr", "depth_p",
            "err_p", "depth_s", "err_s", "depth_odd", "depth_even", "a_ell", "err_a_ell", "ell_pred",
            "ell_ratio_tess", "gaia_ecl_depth_flux", "k", "r2", "r_ms", "t2", "t2_3sig_upper",
            "teff1", "m2_hi2", "vsx", "tess_eb", "reasons"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--schema", default="gaiadr3")
    ap.add_argument("--n-tess", type=int, default=20, help="TESS-vet the N lowest-mass eblm_like rows")
    ap.add_argument("--max-sectors", type=int, default=6)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--no-tess", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    os.makedirs(a.data_dir, exist_ok=True)
    summary = {"version": VERSION, "schema": a.schema}
    raw = tap_csv(GAIA_TAP, sample_adql(a.schema))
    log("sample rows", len(raw))
    rows = [classify(r) for r in raw]
    summary["n_sb1_eb_same_period"] = len(rows)
    summary["classes"] = {k: sum(1 for r in rows if r["cls"] == k) for k in
                          ("twin_blend_suspect", "twin", "eblm_like", "other")}
    summary["twin_fraction_by_fm"] = population_stats(rows)
    eblm = sorted([r for r in rows if r["cls"] == "eblm_like" and r["fm"] < 0.3], key=lambda r: r["m2"])
    sim = simbad_lookup([r["source_id"] for r in eblm])
    for r in rows:
        r["simbad_main_id"], r["simbad_otype"] = sim.get(str(r["source_id"]), ("", ""))
    summary["eblm_like"] = len(eblm)
    summary["eblm_like_in_simbad"] = sum(1 for r in eblm if r["simbad_main_id"])
    off = [abs(r["dph_transit"]) for r in eblm if "dph_transit" in r]
    summary["eblm_like_transit_phase"] = {
        "n": len(off), "n_within_0.06": sum(1 for x in off if x < 0.06),
        "n_near_occultation": sum(1 for r in eblm if "dph_occult" in r and abs(r["dph_occult"]) < 0.06)}
    er = [r["ell_ratio"] for r in eblm if r.get("ell_ratio") == r.get("ell_ratio") and r.get("ell_ratio", 0) > 0]
    er.sort()
    summary["eblm_like_ell_ratio_median"] = er[len(er) // 2] if er else None
    write_csv(os.path.join(a.out_dir, "sb1_eb_classified.csv"), rows, CLS_COLS)
    write_csv(os.path.join(a.out_dir, "eblm_like.csv"), eblm, CLS_COLS)
    vets = []
    if not a.no_tess:
        plot_dir = os.path.join(a.out_dir, "eblm_plots")
        os.makedirs(plot_dir, exist_ok=True)
        for c in eblm[:a.n_tess]:
            log("vet", c["source_id"], f"m2={c['m2']:.3f}")
            try:
                v = vet_tess(c, a.data_dir, a.max_sectors, plot_dir)
            except Exception:
                v = {"source_id": c["source_id"], "verdict": "ERROR", "reasons": [traceback.format_exc()[-400:]]}
            try:
                hits = catalogue_hits(c["ra"], c["dec"])
                v["vsx"], v["tess_eb"] = json.dumps(hits.get("vsx")), json.dumps(hits.get("tess_eb"))
            except Exception as exc:
                v["vsx"] = f"failed: {exc}"
            log("->", v.get("verdict"), v.get("reasons"))
            vets.append(v)
            write_csv(os.path.join(a.out_dir, "eblm_tess_vet.csv"), vets, VET_COLS)
        summary["tess_verdicts"] = {}
        for v in vets:
            summary["tess_verdicts"][v.get("verdict", "?")] = summary["tess_verdicts"].get(v.get("verdict", "?"), 0) + 1
    with open(os.path.join(a.out_dir, "eblm_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=lambda x: _clean(x) if isinstance(x, float) else str(x))
    with open(os.path.join(a.out_dir, "eblm_tess_vet.json"), "w") as fh:
        json.dump(vets, fh, indent=1, default=str)
    print(json.dumps(summary, default=str)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
