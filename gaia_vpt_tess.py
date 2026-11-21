# SPDX-License-Identifier: Apache-2.0
"""gaia_vpt_tess 0.1.0: do Gaia's own photometric transit candidates transit in TESS?

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Pre-registration: findings/2026-11-21-vpt-tess-prereg.md (runbook step g).
Written 2026-11-21, eleven days before Gaia DR4, with no DR4 data seen.

Gaia DR3 published 214 photometric transit candidates (vari_planetary_transit: 173 known
systems, 41 new, of which Gaia-1b and Gaia-2b were confirmed; Panahi et al. 2022, A&A 663,
A101). Gaia DR4 (2 Dec 2026) publishes 1,007 (ESA DR4 content page, 14 Sep 2026). This
module folds every candidate's TESS light curves at the Gaia period and asks:

  G0  validity: are KNOWN planets in the list recovered (>= 80 % of sensitive ones), and do
      the control periods stay quiet (control rate <= 0.08 per trial)?
  G1  what fraction of the NEW candidates (no known planet, no TOI at the Gaia period) show
      the transit in TESS, after subtracting control false alarms?
  G2  which NEW candidates show a planet-like transit (no secondary, no odd/even difference,
      no strong modulation at P, companion radius <= 2 R_Jup)? A list, not a test.
  G3  what share of the NEW signals seen look like eclipsing binaries? (descriptive)
  G4  among candidates missed at P, how many hit at P/2 or 2P? (exploratory)

The TESS search is sb1_transit 0.1.0's, imported unchanged: SPOC 120 s > TESS-SPOC > QLP, up
to --max-sectors sectors, running-median detrending, a phase-free box fold at the trial
period (box width max(0.6 T14, 1 h); here T14 = Gaia's transit_duration), the fixed hit rule
(SNR >= 7, local ratio >= 0.7, >= 3 transits, drop-one SNR >= 3), two non-harmonic control
periods (0.8541 P, 0.9137 P) after masking the best box, and N_INJ = 4 injections at
0.8 x Gaia's depth. Sensitivity s = injections recovered / injections tried; s >= 0.5 puts
a candidate in the rate sample.

Exit codes: 0 ok; 2 archive unavailable (re-file unchanged); 3 self-test failed;
4 a table or column is missing (vpt_schema_error.json says what failed).
"""
import argparse
import csv
import io
import json
import math
import os
import random
import shutil
import sys
import tempfile
import time
import traceback

VERSION = "0.1.0"
SEED = 20261121

# ---- pre-registered constants (findings/2026-11-21-vpt-tess-prereg.md) ----
GAIA_TO_BTJD = 2455197.5 - 2457000.0   # Gaia time (BJD_TCB - 2455197.5) -> BTJD; TCB-TDB ~20 s ignored
RJUP_PER_RSUN = 9.731
INJ_FACTOR = 0.8                        # injected depth = 0.8 x Gaia depth (as sb1_transit)
SENS_MIN = 0.5
SEC_SNR_MIN = 4.0                       # secondary eclipse flag: SNR >= 4 ...
SEC_RATIO_MIN = 0.10                    # ... and depth >= 10 % of the primary
ODDEVEN_Z = 3.0
ODDEVEN_MIN_BINS = 3
MOD_FACTOR = 0.5                        # modulation semi-amplitude at P > 0.5 x depth
R2_STELLAR_RJ = 2.0
PERIOD_TOL = 0.01                       # relative period match tolerance
MATCH_FACTORS = (1.0, 0.5, 2.0)         # catalogue period / Gaia period ratios accepted
ALIAS_FACTORS = (0.5, 2.0)              # G4 trial periods (x Gaia P), only for stars missed at P
G0_MIN_RECOVERY = 0.80
G0_MIN_N = 10
CTRL_MAX = 0.08
G1_HI, G1_LO = 0.5, 0.2
G1_MIN_N = 10
KNOWN_DISP = ("CP", "KP")
FP_DISP = ("FP", "FA")
EXOARCH_URL = ("https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query="
               "select+pl_name,tic_id,pl_orbper+from+pscomppars+where+tic_id+is+not+null"
               "&format=csv")
TAP_TIMEOUT = 180

# rough main-sequence radius from absolute G (fallback when FLAME is missing; = sb1_transit)
_MG = [0.5, 1.5, 2.5, 3.5, 4.4, 5.0, 5.6, 6.2, 6.9, 7.6, 8.4, 9.2, 10.0, 10.8, 11.6]
_RAD = [1.9, 1.6, 1.35, 1.15, 1.0, 0.9, 0.82, 0.75, 0.68, 0.62, 0.55, 0.48, 0.40, 0.31, 0.25]

STAR_KEYS = [
    "source_id", "status", "category", "category_detail", "G", "bp_rp", "parallax", "ruwe",
    "ra", "dec", "P", "t0_btjd", "depth_gaia_mmag", "depth_gaia", "dur_d", "num_in_transit",
    "r1", "r1_src", "tic", "n_sectors_available", "n_sectors_used", "n_sectors_hit",
    "star_hit", "n_inj", "n_inj_found", "sensitivity", "in_rate_sample",
    "ctrl_0.8541_hit", "ctrl_0.9137_hit", "best_sector", "best_author", "depth_tess",
    "snr_best", "n_ep_best", "local_ratio_best", "snr_drop1_best", "t_found", "mod_amp",
    "sec_depth", "sec_snr", "oddeven_z", "r2_rj", "phase_offset_d", "n_cycles",
    "implied_dP", "flags", "planet_like", "alias_hit", "alias_factor", "error"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ================================================================ pure helpers (stdlib)
def fval(row, key, default=float("nan")):
    try:
        v = row.get(key, default)
        if v is None or (isinstance(v, str) and v.strip() in ("", "null", "NaN", "nan", "--")):
            return default
        v = float(v)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            f = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + f * (ys[i] - ys[i - 1])
    return ys[-1]


def mmag_to_frac(mmag):
    """Gaia transit_depth (mmag) -> fractional flux drop."""
    if not (isinstance(mmag, (int, float)) and math.isfinite(mmag)):
        return float("nan")
    return 1.0 - 10.0 ** (-0.4 * mmag / 1000.0)


def gaia_to_btjd(t):
    return t + GAIA_TO_BTJD


def stellar_radius(row):
    """(R1 in R_sun, source): FLAME radius, else a main-sequence guess from absolute G."""
    r = fval(row, "radius_flame")
    if math.isfinite(r) and r > 0:
        return r, "flame"
    g = fval(row, "phot_g_mean_mag")
    plx = fval(row, "parallax")
    if math.isfinite(g) and math.isfinite(plx) and plx > 0:
        absg = g + 5.0 * math.log10(plx / 100.0)
        return interp(absg, _MG, _RAD), "absG"
    return 1.0, "default"


def companion_radius_rj(depth, r1):
    if not (math.isfinite(depth) and math.isfinite(r1)) or depth <= 0:
        return float("nan")
    return math.sqrt(depth) * r1 * RJUP_PER_RSUN


def period_match(p_gaia, p_cat, tol=PERIOD_TOL, factors=MATCH_FACTORS):
    """Factor f in factors with |p_cat / (f p_gaia) - 1| <= tol, else None."""
    if not (math.isfinite(p_gaia) and math.isfinite(p_cat)) or p_gaia <= 0 or p_cat <= 0:
        return None
    for f in factors:
        if abs(p_cat / (f * p_gaia) - 1.0) <= tol:
            return f
    return None


def parse_exoarch(text):
    """NASA Exoplanet Archive pscomppars CSV -> {tic: [(pl_name, period)]}."""
    out = {}
    if not text:
        return out
    for r in csv.DictReader(io.StringIO(text)):
        tic = str(r.get("tic_id", "") or "").replace("TIC", "").strip().lstrip("0")
        if not tic:
            continue
        out.setdefault(tic, []).append((r.get("pl_name", ""), fval(r, "pl_orbper")))
    return out


def classify_known(tic, P, planets, tois):
    """Category of a candidate from the planet archive and the TOI list (both keyed by TIC
    without leading zeros). Order: KNOWN_PLANET, TOI_FP, TOI_PC, KNOWN_SYSTEM_OTHER_P, NEW.
    Returns (category, detail)."""
    tic = str(tic or "").strip().lstrip("0")
    if not tic:
        return "NO_TIC", ""
    pl = planets.get(tic, []) if planets else []
    to = tois.get(tic, []) if tois else []
    for name, per in pl:
        f = period_match(P, per)
        if f is not None:
            return "KNOWN_PLANET", "%s (x%g)" % (name, f)
    matched = []
    for t in to:
        f = period_match(P, fval(t, "period"))
        if f is not None:
            matched.append((t, f))
    for t, f in matched:
        if str(t.get("disp", "")).strip().upper() in KNOWN_DISP:
            return "KNOWN_PLANET", "TOI-%s %s (x%g)" % (t.get("toi", ""), t.get("disp", ""), f)
    for t, f in matched:
        if str(t.get("disp", "")).strip().upper() in FP_DISP:
            return "TOI_FP", "TOI-%s %s (x%g)" % (t.get("toi", ""), t.get("disp", ""), f)
    if matched:
        t, f = matched[0]
        return "TOI_PC", "TOI-%s %s (x%g)" % (t.get("toi", ""), t.get("disp", ""), f)
    if pl or to:
        names = [n for n, _ in pl] + ["TOI-%s" % t.get("toi", "") for t in to]
        return "KNOWN_SYSTEM_OTHER_P", ";".join(names)
    return "NEW", ""


def phase_offset(t_found, t0_btjd, P):
    """Offset (d) of a found transit from the Gaia ephemeris, the cycle count, and the
    period change that would remove it."""
    if not (math.isfinite(t_found) and math.isfinite(t0_btjd) and math.isfinite(P)) or P <= 0:
        return float("nan"), 0, float("nan")
    n = int(round((t_found - t0_btjd) / P))
    off = t_found - t0_btjd - n * P
    dP = off / n if n != 0 else float("nan")
    return off, n, dP


def vet_flags(depth_tess, sec_depth, sec_snr, oddeven_z, mod_amp, r2_rj):
    """Fixed vetting flags for a hit. planet_like = no flag."""
    flags = []
    if (math.isfinite(sec_snr) and sec_snr >= SEC_SNR_MIN and math.isfinite(sec_depth)
            and depth_tess > 0 and sec_depth >= SEC_RATIO_MIN * depth_tess):
        flags.append("SECONDARY")
    if math.isfinite(oddeven_z) and oddeven_z >= ODDEVEN_Z:
        flags.append("ODD_EVEN")
    if math.isfinite(mod_amp) and depth_tess > 0 and mod_amp > MOD_FACTOR * depth_tess:
        flags.append("MODULATED")
    if math.isfinite(r2_rj) and r2_rj > R2_STELLAR_RJ:
        flags.append("STELLAR_SIZE")
    return flags, len(flags) == 0


def chunk_order(ids, n_chunks, chunk, seed=SEED):
    ids = sorted(str(i) for i in ids)
    random.Random(seed).shuffle(ids)
    return [x for i, x in enumerate(ids) if i % n_chunks == chunk]


def poisson_cdf(n, mu):
    if n < 0:
        return 0.0
    term = math.exp(-mu)
    s = term
    for k in range(1, n + 1):
        term *= mu / k
        s += term
    return min(1.0, s)


def garwood(n, cl=0.95):
    """Exact (Garwood) central interval for a Poisson mean given n counts."""
    a = (1.0 - cl) / 2.0

    def bisect(fn, lo, hi):
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if fn(mid):
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)
    hi_b = 10.0 + 10.0 * n
    lower = 0.0 if n == 0 else bisect(lambda mu: 1.0 - poisson_cdf(n - 1, mu) >= a, 0.0, hi_b)
    upper = bisect(lambda mu: poisson_cdf(n, mu) <= a, 0.0, hi_b)
    return lower, upper


def wilson(k, n, z=1.96):
    if n <= 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def _b(x):
    return str(x).strip().lower() in ("1", "true", "yes")


def grade(recs):
    """Pre-registered grades G0-G4 from per-star records (dicts; values may be strings)."""
    done = [r for r in recs if str(r.get("status", "")) == "OK"]
    rate = [r for r in done if _b(r.get("in_rate_sample"))]
    n_rate = len(rate)
    ctrl_hits = sum(int(_b(r.get("ctrl_0.8541_hit"))) + int(_b(r.get("ctrl_0.9137_hit")))
                    for r in rate)
    ctrl_rate = ctrl_hits / (2.0 * n_rate) if n_rate else float("nan")
    status_counts = {}
    for r in recs:
        s = str(r.get("status", ""))
        status_counts[s] = status_counts.get(s, 0) + 1
    out = {"version": VERSION, "n_candidates_processed": len(recs), "n_ok": len(done),
           "status_counts": status_counts,
           "n_rate_sample": n_rate, "control_hits": ctrl_hits, "control_rate": ctrl_rate}
    cats = {}
    for r in done:
        c = r.get("category", "")
        d = cats.setdefault(c, {"n": 0, "n_sens": 0, "n_hit_sens": 0})
        d["n"] += 1
        if _b(r.get("in_rate_sample")):
            d["n_sens"] += 1
            d["n_hit_sens"] += int(_b(r.get("star_hit")))
    out["by_category"] = cats
    # G0
    kp = [r for r in rate if r.get("category") == "KNOWN_PLANET"]
    k_hit = sum(int(_b(r.get("star_hit"))) for r in kp)
    rec = k_hit / len(kp) if kp else float("nan")
    if len(kp) < G0_MIN_N:
        g0a = "UNTESTABLE"
    else:
        g0a = "PIPELINE_OK" if rec >= G0_MIN_RECOVERY else "PIPELINE_FAILS"
    g0b = ("UNTESTABLE" if not n_rate else
           ("CONTROLS_OK" if ctrl_rate <= CTRL_MAX else "CONTROLS_NOISY"))
    out["G0"] = {"known_sensitive": len(kp), "known_hits": k_hit, "recovery": rec,
                 "recovery_ci95": wilson(k_hit, len(kp)), "label_a": g0a, "label_b": g0b}
    # G1
    nw = [r for r in rate if r.get("category") == "NEW"]
    n_new = len(nw)
    h_new = sum(int(_b(r.get("star_hit"))) for r in nw)
    fa = (ctrl_rate if math.isfinite(ctrl_rate) else 0.0) * n_new
    if n_new:
        lo, hi = garwood(h_new)
        f = max(0.0, (h_new - fa) / n_new)
        ci = (max(0.0, (lo - fa) / n_new), min(1.0, max(0.0, (hi - fa) / n_new)))
    else:
        f, ci = float("nan"), (float("nan"), float("nan"))
    if n_new < G1_MIN_N:
        g1 = "UNTESTABLE"
    elif f >= G1_HI:
        g1 = "MOSTLY_SEEN"
    elif f >= G1_LO:
        g1 = "MIXED"
    else:
        g1 = "MOSTLY_NOT_SEEN"
    if g0a == "PIPELINE_FAILS" or g0b == "CONTROLS_NOISY":
        g1_valid = False
    else:
        g1_valid = True
    out["G1"] = {"new_sensitive": n_new, "new_hits": h_new, "false_alarms_expected": fa,
                 "fraction_seen": f, "fraction_seen_ci95": ci, "label": g1,
                 "valid": g1_valid}
    # G2 / G3
    new_hits = [r for r in done if r.get("category") == "NEW" and _b(r.get("star_hit"))]
    pl = [r for r in new_hits if _b(r.get("planet_like"))]
    out["G2"] = {"n_new_hits_all": len(new_hits), "n_planet_like": len(pl),
                 "planet_like": [{"source_id": r.get("source_id"), "tic": r.get("tic"),
                                  "P": r.get("P"), "depth_tess": r.get("depth_tess"),
                                  "r2_rj": r.get("r2_rj"), "G": r.get("G")} for r in pl]}
    eb = [r for r in new_hits if not _b(r.get("planet_like"))]
    out["G3"] = {"n_new_hits_all": len(new_hits), "n_eb_like": len(eb),
                 "eb_share": (len(eb) / len(new_hits)) if new_hits else float("nan")}
    # G4
    miss = [r for r in done if not _b(r.get("star_hit"))]
    out["G4"] = {"n_missed_at_P": len(miss),
                 "n_alias_hits": sum(int(_b(r.get("alias_hit"))) for r in miss)}
    return out


def clean_json(o):
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): clean_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_json(v) for v in o]
    return o


def write_csv(path, rows, keys):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in keys})


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def candidate_adql(schema, with_ap=True):
    s = schema
    cols = ("v.source_id, v.transit_reference_time, v.transit_period, v.transit_depth, "
            "v.transit_duration, v.num_in_transit, g.ra, g.dec, g.phot_g_mean_mag, g.bp_rp, "
            "g.parallax, g.ruwe")
    if with_ap:
        return ("SELECT %s, p.radius_flame FROM %s.vari_planetary_transit AS v "
                "JOIN %s.gaia_source AS g ON g.source_id = v.source_id "
                "LEFT JOIN %s.astrophysical_parameters AS p ON p.source_id = v.source_id "
                "ORDER BY v.source_id" % (cols, s, s, s))
    return ("SELECT %s FROM %s.vari_planetary_transit AS v "
            "JOIN %s.gaia_source AS g ON g.source_id = v.source_id ORDER BY v.source_id"
            % (cols, s, s))


# ================================================================ numpy / network parts
def extra_vet(t, f, P, t14, t_found):
    """Secondary-eclipse depth/SNR at phase 0.5 and odd/even depth z on one sector."""
    import numpy as np
    import sb1_transit as st
    import dipsearch as ds
    D = st.box_width(t14)
    bt, r, _ = st.detrend(t, f, D)
    if bt.size < 50 or not math.isfinite(t_found):
        return float("nan"), float("nan"), float("nan")
    w = D / P
    x = (bt - t_found) / P
    ph0 = (x + 0.5) % 1.0 - 0.5
    sd = ds.robust_sd(r)
    if not (np.isfinite(sd) and sd > 0):
        return float("nan"), float("nan"), float("nan")
    sec = np.abs(np.abs(ph0) - 0.5) < w / 2.0
    n2 = int(sec.sum())
    if n2 >= 3:
        d2 = -float(np.mean(r[sec]))
        s2 = d2 / (sd / math.sqrt(n2))
    else:
        d2, s2 = float("nan"), float("nan")
    inb = np.abs(ph0) < w / 2.0
    ep = np.round(x).astype(int)
    odd = inb & (ep % 2 == 1)
    even = inb & (ep % 2 == 0)
    no, ne = int(odd.sum()), int(even.sum())
    if no >= ODDEVEN_MIN_BINS and ne >= ODDEVEN_MIN_BINS:
        do = -float(np.mean(r[odd]))
        de = -float(np.mean(r[even]))
        z = abs(do - de) / (sd * math.sqrt(1.0 / no + 1.0 / ne))
    else:
        z = float("nan")
    return d2, s2, z


def alias_search(sectors, P, t14):
    """G4: any sector hit at P x 0.5 or P x 2 (no injections; exploratory)."""
    import numpy as np
    import sb1_transit as st
    D = st.box_width(t14)
    for fac in ALIAS_FACTORS:
        for (_, _, t, f) in sectors:
            bt, r, _ = st.detrend(t, f, D)
            res = st.fold_search(bt, r, P * fac, D, float(np.min(t)))
            if st.sector_hit(res):
                return True, fac
    return False, ""


def process_candidate(row, cat_tables, args, rng):
    import sb1_transit as st
    rec = {k: "" for k in STAR_KEYS}
    rec["source_id"] = str(row.get("source_id", ""))
    P = fval(row, "transit_period")
    dur = fval(row, "transit_duration")
    dmm = fval(row, "transit_depth")
    dep = mmag_to_frac(dmm)
    r1, r1src = stellar_radius(row)
    rec.update({"G": fval(row, "phot_g_mean_mag"), "bp_rp": fval(row, "bp_rp"),
                "parallax": fval(row, "parallax"), "ruwe": fval(row, "ruwe"),
                "ra": fval(row, "ra"), "dec": fval(row, "dec"), "P": P,
                "t0_btjd": gaia_to_btjd(fval(row, "transit_reference_time")),
                "depth_gaia_mmag": dmm, "depth_gaia": dep, "dur_d": dur,
                "num_in_transit": row.get("num_in_transit", ""), "r1": r1, "r1_src": r1src})
    if not (math.isfinite(P) and P > 0 and math.isfinite(dur) and dur > 0
            and math.isfinite(dep) and dep > 0):
        rec["status"] = "BAD_EPHEMERIS"
        return rec
    tmp = tempfile.mkdtemp(prefix="vpt_", dir=args.tmp_dir)
    try:
        tic, secs, nav = st.light_curves(row, tmp, args.max_sectors)
        rec["tic"] = tic
        rec["n_sectors_available"] = nav
        rec["n_sectors_used"] = len(secs)
        planets, tois = cat_tables
        cat, det = classify_known(tic, P, planets, tois)
        rec["category"], rec["category_detail"] = cat, det
        if not secs:
            rec["status"] = "NO_TESS"
            return rec
        meas = []
        for (sec, au, t, f) in secs:
            m = st.measure_sector(t, f, P, dur, INJ_FACTOR * dep, rng)
            meas.append((sec, au, t, f, m))
        n_inj = sum(len(m["inj"]) for *_, m in meas)
        n_found = sum(sum(int(i["found"]) for i in m["inj"]) for *_, m in meas)
        sens = n_found / n_inj if n_inj else 0.0
        hits = [(sec, au, t, f, m) for (sec, au, t, f, m) in meas if m["hit"]]
        rec.update({"n_sectors_hit": len(hits), "star_hit": bool(hits), "n_inj": n_inj,
                    "n_inj_found": n_found, "sensitivity": sens,
                    "in_rate_sample": sens >= SENS_MIN})
        for c in st.CONTROL_RATIOS:
            rec["ctrl_%s_hit" % c] = any(m["controls"][str(c)]["hit"] for *_, m in meas)
        if hits:
            sec, au, t, f, m = max(hits, key=lambda h: h[4]["real"]["snr"])
            res = m["real"]
            d2, s2, z = extra_vet(t, f, P, dur, res["t_found"])
            depth_t = res["depth"]
            r2 = companion_radius_rj(max(depth_t, dep), r1)
            flags, plike = vet_flags(depth_t, d2, s2, z, m["mod_amp"], r2)
            off, ncy, dP = phase_offset(res["t_found"], rec["t0_btjd"], P)
            rec.update({"best_sector": sec, "best_author": au, "depth_tess": depth_t,
                        "snr_best": res["snr"], "n_ep_best": res["n_ep"],
                        "local_ratio_best": res["local_ratio"],
                        "snr_drop1_best": res["snr_drop1"], "t_found": res["t_found"],
                        "mod_amp": m["mod_amp"], "sec_depth": d2, "sec_snr": s2,
                        "oddeven_z": z, "r2_rj": r2, "phase_offset_d": off,
                        "n_cycles": ncy, "implied_dP": dP, "flags": ";".join(flags),
                        "planet_like": plike})
        else:
            ah, fac = alias_search(secs, P, dur)
            rec["alias_hit"], rec["alias_factor"] = ah, fac
        rec["status"] = "OK"
        return rec
    except Exception as exc:
        rec["status"] = "ERROR"
        rec["error"] = repr(exc)[:300]
        traceback.print_exc()
        return rec
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_catalogues():
    import sb1_transit as st
    planets = parse_exoarch(st.fetch_text(EXOARCH_URL))
    tois = st.toi_table() or {}
    tois = {str(k).strip().lstrip("0"): v for k, v in tois.items()}
    if not planets:
        raise RuntimeError("planet archive empty")
    if not tois:
        raise RuntimeError("TOI table empty")
    return planets, tois


def fetch_candidates(schema):
    import sb1_transit as st
    try:
        return st.tap_query(candidate_adql(schema, True), timeout=TAP_TIMEOUT), True
    except RuntimeError as exc:
        log("query with astrophysical_parameters failed:", exc)
    return st.tap_query(candidate_adql(schema, False), timeout=TAP_TIMEOUT), False


def self_test():
    """Synthetic checks of the numpy path (needs sb1_transit, dipsearch, vet_event)."""
    import numpy as np
    import sb1_transit as st
    rng = np.random.default_rng(1)
    t = np.arange(0.0, 27.0, 2.0 / 1440.0)
    t = t[(t < 13.0) | (t > 14.0)]
    P, t14, t0 = 3.1, 0.12, 1.37
    base = 1.0 + rng.normal(0, 1e-3, t.size)
    ok = True

    def box(depth, tc, period):
        ph = ((t - tc) / period + 0.5) % 1.0 - 0.5
        return np.where(np.abs(ph * period) < t14 / 2.0, 1.0 - depth, 1.0)

    planet = base * box(0.01, t0, P)
    m = st.measure_sector(t, planet, P, t14, 0.008, np.random.default_rng(2))
    d2, s2, z = extra_vet(t, planet, P, t14, m["real"]["t_found"] if m["real"] else float("nan"))
    fl, pl = vet_flags(m["real"]["depth"] if m["real"] else 0.0, d2, s2, z, m["mod_amp"], 1.0)
    log("self-test planet: hit", m["hit"], "flags", fl, "sec_snr", s2, "z", z)
    ok &= bool(m["hit"]) and pl
    eb = base * box(0.01, t0, P) * box(0.004, t0 + P / 2.0, P)
    m = st.measure_sector(t, eb, P, t14, 0.008, np.random.default_rng(3))
    d2, s2, z = extra_vet(t, eb, P, t14, m["real"]["t_found"] if m["real"] else float("nan"))
    fl, pl = vet_flags(m["real"]["depth"] if m["real"] else 0.0, d2, s2, z, m["mod_amp"], 1.0)
    log("self-test EB secondary: hit", m["hit"], "flags", fl, "sec_snr", s2)
    ok &= bool(m["hit"]) and ("SECONDARY" in fl)
    # odd/even: true period 2P, eclipses 1.2 % and 0.6 % folded at P
    oe = base * box(0.012, t0, 2 * P) * box(0.006, t0 + P, 2 * P)
    m = st.measure_sector(t, oe, P, t14, 0.008, np.random.default_rng(4))
    d2, s2, z = extra_vet(t, oe, P, t14, m["real"]["t_found"] if m["real"] else float("nan"))
    fl, pl = vet_flags(m["real"]["depth"] if m["real"] else 0.0, d2, s2, z, m["mod_amp"], 1.0)
    log("self-test odd/even: hit", m["hit"], "flags", fl, "z", z)
    ok &= bool(m["hit"]) and ("ODD_EVEN" in fl)
    flat = base.copy()
    m = st.measure_sector(t, flat, P, t14, 0.008, np.random.default_rng(5))
    log("self-test flat: hit", m["hit"], "inj found", sum(int(i["found"]) for i in m["inj"]))
    ok &= (not m["hit"]) and sum(int(i["found"]) for i in m["inj"]) >= 3
    log("self-test", "PASS" if ok else "FAIL")
    return ok


def summarise(recs, out_dir, meta):
    g = grade(recs)
    g["meta"] = meta
    with open(os.path.join(out_dir, "vpt_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(clean_json(g), fh, indent=1)
    write_csv(os.path.join(out_dir, "vpt_stars.csv"), recs, STAR_KEYS)
    return g


def run(args):
    os.makedirs(args.out_dir, exist_ok=True)
    if args.tmp_dir:
        os.makedirs(args.tmp_dir, exist_ok=True)
    t_start = time.time()
    if args.input_csv:
        rows, with_ap = read_csv(args.input_csv), True
    else:
        try:
            rows, with_ap = fetch_candidates(args.schema)
        except RuntimeError as exc:
            msg = str(exc)
            code = 4 if ("not found" in msg.lower() or "column" in msg.lower()
                         or "table" in msg.lower()) else 2
            with open(os.path.join(args.out_dir, "vpt_schema_error.json"), "w") as fh:
                json.dump({"error": msg[:2000], "exit": code}, fh, indent=1)
            log("candidate query failed, exit", code, msg[:300])
            return code
        write_csv(os.path.join(args.out_dir, "vpt_candidates.csv"), rows, list(rows[0].keys())
                  if rows else ["source_id"])
    log("candidates", len(rows), "astrophysical_parameters joined:", with_ap)
    try:
        cats = load_catalogues()
    except Exception as exc:
        log("catalogue fetch failed:", exc)
        return 2
    log("planet-archive TICs", len(cats[0]), "TOI TICs", len(cats[1]))
    by_id = {str(r["source_id"]): r for r in rows}
    ids = chunk_order(by_id.keys(), args.n_chunks, args.chunk)[:args.max_stars]
    import numpy as np
    rng = np.random.default_rng(SEED + args.chunk)
    meta = {"schema": args.schema, "chunk": args.chunk, "n_chunks": args.n_chunks,
            "n_candidates_total": len(rows), "n_in_chunk": len(ids),
            "max_sectors": args.max_sectors, "ap_joined": with_ap, "stopped_early": False}
    recs = []
    for k, sid in enumerate(ids):
        if (time.time() - t_start) / 60.0 > args.time_budget_min:
            meta["stopped_early"] = True
            log("time budget reached after", k, "stars")
            break
        rec = process_candidate(by_id[sid], cats, args, rng)
        recs.append(rec)
        if _b(rec.get("star_hit")):
            log("HIT", sid, "P=%.4f" % fval(rec, "P"), "tic", rec.get("tic"), rec.get("category"),
                rec.get("category_detail"), rec.get("flags") or "planet-like")
        if (k + 1) % 10 == 0:
            summarise(recs, args.out_dir, dict(meta, n_done=len(recs)))
            log("done", k + 1, "stars, %.1f min" % ((time.time() - t_start) / 60.0))
    meta["n_done"] = len(recs)
    g = summarise(recs, args.out_dir, meta)
    print(json.dumps(clean_json({"G0": g["G0"], "G1": g["G1"], "G2_n": g["G2"]["n_planet_like"],
                                 "G3": g["G3"], "G4": g["G4"],
                                 "by_category": g["by_category"]})))
    return 0


def combine(args):
    os.makedirs(args.out_dir, exist_ok=True)
    recs = []
    seen = set()
    for d in args.combine:
        for r in read_csv(os.path.join(d, "vpt_stars.csv")):
            if r["source_id"] in seen:
                continue
            seen.add(r["source_id"])
            recs.append(r)
    g = summarise(recs, args.out_dir, {"combined_from": args.combine})
    print(json.dumps(clean_json({"G0": g["G0"], "G1": g["G1"], "G3": g["G3"], "G4": g["G4"]})))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--schema", default="gaiadr3")
    p.add_argument("--out-dir", default="out")
    p.add_argument("--tmp-dir", default=None)
    p.add_argument("--chunk", type=int, default=0)
    p.add_argument("--n-chunks", type=int, default=1)
    p.add_argument("--max-sectors", type=int, default=3)
    p.add_argument("--time-budget-min", type=float, default=160.0)
    p.add_argument("--max-stars", type=int, default=100000)
    p.add_argument("--input-csv", default=None)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--combine", nargs="+", default=None)
    args = p.parse_args(argv)
    if args.self_test:
        return 0 if self_test() else 3
    if args.combine:
        return combine(args)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
