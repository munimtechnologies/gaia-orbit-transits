# SPDX-License-Identifier: Apache-2.0
"""Do Gaia DR3 astrometric orbits predict as many eclipses as TESS sees?

An external test of Gaia DR3 orbit inclinations with TESS eclipses.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0. Pre-registration: findings/2026-11-17-inclination-calibration-prereg.md

Inputs: the published outputs of the full DR3 search (job gaia-orbit-tess-v4) in
data/dr3-full-search-v4/ of this repository: tess_targets.csv, events.csv,
covered_windows.csv and gaia_edge_on_priors.csv. They are downloaded from GitHub
unless --offline is given.

What it does
  1. A detection rule that does not depend on the window-match Bayes factor. The BF
     used by the search cannot exceed about P / (2.5 sigma_t). A 10-d orbit with a
     1-d timing error can therefore never reach BF > 10, even with a 7.7%-deep
     eclipse at every conjunction (HD 75767 = TIC 459056725). Here an eclipse counts
     if a clean dip (SNR >= 10, depth >= 500 ppm, not at a segment edge, not seen in
     another target at the same time) lies within 3 sigma (+ half its duration) of a
     covered predicted conjunction.
  2. For every target, the probability that TESS should have seen an eclipse:
     cos i ~ N(cos i_Gaia, (k sigma)^2) with the Monte Carlo sigma, the eclipse
     limit at each conjunction lim_k = q g_k / (1 - e^2), q = (R1 + R2) / a,
     g_k = 1 + e cos f_k (recovered from the central durations the search wrote),
     and the TESS coverage of each conjunction.
  3. Maximum-likelihood fits: k (Gaia's cos i errors are too small by k), f (a
     fraction f of orbits is wrong and oriented at random), s (all radii scaled by s).
  4. A false-alarm control: the same rule at the two phases half-way between the
     conjunctions.
  5. Timing: z = offset / sigma of each detected eclipse.
"""
import argparse
import csv
import json
import math
import os
import sys
import urllib.request

import numpy as np

VERSION = "0.7.0"
RSUN_AU = 0.00465047
YEAR_D = 365.25
RAW = ("https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/"
       "data/dr3-full-search-v4/")
FILES = ("tess_targets.csv", "events.csv", "covered_windows.csv", "gaia_edge_on_priors.csv")

# ---- the pre-registered rule (do not change after the data are read) ----
MIN_SNR = 10.0
MIN_DEPTH_PPM = 500.0
WINDOW_NSIGMA = 3.0
MIN_EXP_SNR = 15.0
MIN_COVERAGE = 0.05
# events vetted by eye in 0.6.2 as data artefacts (tic, BTJD)
ARTEFACTS = (("219744709", 2707.400), ("152964265", 2165.371))
ARTEFACT_TOL_D = 0.5
# old "strong match" rule of the v4 grading, for comparison
STRONG_BF = 10.0
STRONG_SNR = 10.0

K_GRID = np.exp(np.linspace(math.log(0.5), math.log(20.0), 160))
F_GRID = np.linspace(0.0, 0.95, 96)
S_GRID = np.exp(np.linspace(math.log(0.1), math.log(3.0), 160))
DLNL_95 = 1.92


# ------------------------------------------------------------------ small helpers
def fnum(x, default=float("nan")):
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "" or s.lower() in ("nan", "none", "null", "--"):
            return default
        return float(s)
    except ValueError:
        return default


def truthy(x):
    return str(x).strip().lower() in ("true", "1", "yes", "t")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def read_priors(path, wanted):
    """Rows of gaia_edge_on_priors.csv for the wanted source_ids (streamed)."""
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sid = str(row.get("source_id", "")).strip()
            if sid in wanted:
                out.setdefault(sid, []).append(row)
    return out


def pick_prior(rows, solution_type):
    if not rows:
        return None
    for r in rows:
        if str(r.get("solution_type", "")).strip() == str(solution_type).strip():
            return r
    return rows[0]


def norm_cdf(x):
    """Standard normal CDF (Abramowitz & Stegun 7.1.26, |error| < 1.5e-7)."""
    x = np.asarray(x, dtype=float)
    z = np.abs(x) / math.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * z)
    poly = ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t
            + 0.254829592) * t
    erf = np.sign(x) * (1.0 - poly * np.exp(-z * z))
    return 0.5 * (1.0 + erf)


# ------------------------------------------------------------------ geometry
def conj_limits(P, m1, m2, r1, r2, e, dur1_h, dur2_h):
    """(lim1, lim2, q): |cos i| below which conjunction 1 / 2 eclipses.

    run_search wrote the median central durations dur_k = (P/pi) q sqrt(1-e^2) / g_k
    with q = (r1 + r2) R_sun / a and g_k = 1 + e cos f_k. Solving for g_k (clipped
    to its physical range [1-e, 1+e]) gives lim_k = q g_k / (1 - e^2), the same limit
    gaia_orbits.eclipse_geometry() uses. A missing duration means g_k = 1.
    """
    a_au = ((m1 + m2) * (P / YEAR_D) ** 2) ** (1.0 / 3.0)
    q = (r1 + r2) * RSUN_AU / a_au
    e = min(max(float(e) if np.isfinite(e) else 0.0, 0.0), 0.97)
    lims = []
    for dur_h in (dur1_h, dur2_h):
        if dur_h is not None and np.isfinite(dur_h) and dur_h > 0:
            g = (P / math.pi) * q * math.sqrt(1.0 - e * e) / (dur_h / 24.0)
        else:
            g = 1.0
        g = min(max(g, 1.0 - e), 1.0 + e)
        lims.append(min(q * g / (1.0 - e * e), 1.0))
    return lims[0], lims[1], q


def p_inside(c, sd, lim):
    """P(|x| < lim) for x ~ N(c, sd^2)."""
    c = np.asarray(c, float)
    sd = np.maximum(np.asarray(sd, float), 1e-12)
    lim = np.asarray(lim, float)
    return np.clip(norm_cdf((lim - c) / sd) - norm_cdf((-lim - c) / sd), 0.0, 1.0)


def p_detect(c, sd, lim1, lim2, cov1, cov2, k=1.0, s=1.0, f=0.0):
    """Probability that TESS caught at least one eclipse.

    Both conjunctions share one inclination: with L_lo <= L_hi the two limits and
    c_lo, c_hi their coverages, |cos i| < L_lo eclipses at both and
    L_lo <= |cos i| < L_hi only at the 'hi' conjunction, so
      D = P(<L_lo) [1 - (1-c_lo)(1-c_hi)] + [P(<L_hi) - P(<L_lo)] c_hi.
    k inflates sigma(cos i); s scales the radii (the limits); a fraction f of the
    orbits is wrong and seen at a random (isotropic) orientation, P(<L) = L.
    """
    c, sd = np.asarray(c, float), np.asarray(sd, float)
    l1 = np.minimum(s * np.asarray(lim1, float), 1.0)
    l2 = np.minimum(s * np.asarray(lim2, float), 1.0)
    cov1, cov2 = np.asarray(cov1, float), np.asarray(cov2, float)
    lo1 = l1 <= l2
    l_lo, l_hi = np.where(lo1, l1, l2), np.where(lo1, l2, l1)
    c_lo, c_hi = np.where(lo1, cov1, cov2), np.where(lo1, cov2, cov1)
    either = 1.0 - (1.0 - c_lo) * (1.0 - c_hi)

    def comb(p_lo, p_hi):
        return p_lo * either + np.clip(p_hi - p_lo, 0.0, 1.0) * c_hi

    gaia = comb(p_inside(c, k * sd, l_lo), p_inside(c, k * sd, l_hi))
    iso = comb(l_lo, l_hi)
    return (1.0 - f) * gaia + f * iso


def loglike(p, det, fa=0.0):
    p = np.asarray(fa, float) + (1.0 - np.asarray(fa, float)) * np.asarray(p, float)
    p = np.clip(p, 1e-9, 1.0 - 1e-9)
    det = np.asarray(det, bool)
    return float(np.sum(np.where(det, np.log(p), np.log1p(-p))))


def fit_1d(fun, grid):
    ll = np.array([fun(g) for g in grid])
    i = int(np.argmax(ll))
    ok = ll >= ll[i] - DLNL_95
    return {"best": float(grid[i]), "lo95": float(grid[ok].min()),
            "hi95": float(grid[ok].max()), "lnL": float(ll[i]),
            "ci_hits_grid_edge": bool(ok[0] or ok[-1])}


def poisson_binomial_cdf(ps, n):
    """P(N <= n) for N a sum of independent Bernoulli(p_i)."""
    ps = np.asarray(ps, float)
    dist = np.zeros(len(ps) + 1)
    dist[0] = 1.0
    for p in ps:
        dist[1:] = dist[1:] * (1.0 - p) + dist[:-1] * p
        dist[0] *= (1.0 - p)
    if n < 0:
        return 0.0
    return float(min(1.0, dist[: n + 1].sum()))


# ------------------------------------------------------------------ windows and events
def match_window(t, dur_h, wins, P):
    """Nearest covered window that contains t (|t - centre| <= 3 sd + dur/2 and the
    half-width <= P/4). Returns (offset_d, sd_d, z) or None."""
    best = None
    for centre, sd in wins:
        hw = WINDOW_NSIGMA * sd + dur_h / 48.0
        if hw > P / 4.0:
            continue
        off = t - centre
        if abs(off) <= hw:
            z = off / sd if sd > 0 else 0.0
            if best is None or abs(z) < abs(best[2]):
                best = (off, sd, z)
    return best


REPEAT_TOL_D = 0.2
TESS_ORBIT_D = 13.7


def repeat_match(times, P, P_err):
    """Two clean dips n*P apart (n >= 1) within 0.2 d + 3 n sigma_P, for targets whose
    timing windows are too wide to be informative (3 sigma_t + dur/2 > P/4). Pairs whose
    tolerance reaches P/10 are not used, nor periods within 0.5 d of one or two TESS
    orbits (13.7 d), where scattered-light systematics repeat. Returns (t_a, t_b, n)."""
    if not (np.isfinite(P) and P > 0):
        return None
    if any(abs(P - TESS_ORBIT_D * m) < 0.5 for m in (1, 2)):
        return None
    pe = P_err if np.isfinite(P_err) and P_err > 0 else 0.0
    ts = sorted(t for t in times if np.isfinite(t))
    for i in range(len(ts)):
        for j in range(i + 1, len(ts)):
            dt = ts[j] - ts[i]
            n = int(round(dt / P))
            if n < 1:
                continue
            tol = REPEAT_TOL_D + 3.0 * n * pe
            if tol >= P / 10.0:
                continue
            if abs(dt - n * P) <= tol:
                return (ts[i], ts[j], n)
    return None


def repeat_applicable(P, P_err):
    """The repeat rule can only work if two conjunctions fit in one TESS sector
    (P <= 25 d), the one-cycle tolerance is below P/10, and P is not a TESS orbit."""
    if not (np.isfinite(P) and 0 < P <= 25.0):
        return False
    if any(abs(P - TESS_ORBIT_D * m) < 0.5 for m in (1, 2)):
        return False
    pe = P_err if np.isfinite(P_err) and P_err > 0 else 0.0
    return REPEAT_TOL_D + 3.0 * pe < P / 10.0


def control_phases(t1, t2, P):
    """The two times half-way between the conjunctions (mod P): t1 + D/2 and
    t2 + (P - D)/2 with D = (t2 - t1) mod P."""
    d = (t2 - t1) % P
    return [t1 + d / 2.0, t2 + (P - d) / 2.0], d


def phase_distance(t, t0, P):
    return abs(((t - t0 + P / 2.0) % P) - P / 2.0)


def is_artefact(tic, t):
    return any(str(tic).strip() == a and abs(t - b) <= ARTEFACT_TOL_D for a, b in ARTEFACTS)


def event_quality(ev):
    snr = fnum(ev.get("snr"), 0.0)
    depth = fnum(ev.get("depth_ppm"), 0.0)
    n_other = fnum(ev.get("n_other_targets_same_time"), 0.0)
    t = fnum(ev.get("t_center"))
    return (snr >= MIN_SNR and depth >= MIN_DEPTH_PPM and n_other == 0
            and not truthy(ev.get("near_edge")) and np.isfinite(t)
            and not is_artefact(ev.get("tic", ""), t))


def tess_noise_fallback(gmag):
    """Rough 2-h box noise (ppm) when a target has no dips at all."""
    g = gmag if np.isfinite(gmag) else 12.0
    return max(30.0, 60.0 * 10 ** (0.2 * (g - 10.0)))


def sol_group(st):
    s = str(st).strip().lower()
    if s.startswith("astrospectrosb1"):
        return "AstroSpectroSB1"
    if s.startswith("orbitaltargetedsearch"):
        return "OrbitalTargetedSearch*"
    if s.startswith("orbitalalternative"):
        return "OrbitalAlternative*"
    return "Orbital"


# ------------------------------------------------------------------ per-target records
def build_records(targets, priors, events, windows):
    ev_by = {}
    for ev in events:
        ev_by.setdefault(str(ev.get("source_id", "")).strip(), []).append(ev)
    recs = []
    for t in targets:
        sid = str(t.get("source_id", "")).strip()
        rec = {"source_id": sid, "tic": str(t.get("tic", "")).strip(),
               "solution_type": str(t.get("solution_type", "")).strip(),
               "group": sol_group(t.get("solution_type", "")),
               "class": t.get("class", ""), "gmag": fnum(t.get("gmag")),
               "period_d": fnum(t.get("period_d")),
               "cov1": fnum(t.get("cov1"), 0.0), "cov2": fnum(t.get("cov2"), 0.0),
               "gaia_eb": truthy(t.get("gaia_eb")), "status": t.get("status", ""),
               "n_sectors": int(fnum(t.get("n_sectors"), 0.0)),
               "p_ecl_mc": fnum(t.get("p_ecl")), "excluded": ""}
        pr = pick_prior(priors.get(sid, []), rec["solution_type"])
        evs = ev_by.get(sid, [])
        if rec["status"] != "ok" or rec["n_sectors"] <= 0:
            rec["excluded"] = "no_tess"
        elif pr is None:
            rec["excluded"] = "no_prior"
        if pr is not None:
            P = fnum(pr.get("period_d"), rec["period_d"])
            rec["period_d"] = P
            for key in ("cosi", "cosi_sd", "m1", "m2_dark", "r1", "r2", "ecc", "dur1_h",
                        "dur2_h", "p_ecl1", "p_ecl2", "significance", "ruwe",
                        "t_conj1_btjd", "t_conj2_btjd", "next1_sd_d", "next2_sd_d"):
                rec[key] = fnum(pr.get(key))
            rec["transit_conj"] = str(pr.get("transit_conj", "") or "")
            rec["lim1"], rec["lim2"], rec["q"] = conj_limits(
                P, rec["m1"], rec["m2_dark"], rec["r1"], rec["r2"], rec["ecc"],
                rec["dur1_h"], rec["dur2_h"])
            rec["p1_analytic"] = float(p_inside(rec["cosi"], rec["cosi_sd"], rec["lim1"]))
            rec["p2_analytic"] = float(p_inside(rec["cosi"], rec["cosi_sd"], rec["lim2"]))
            # windows: covered ones from the search, else the forward-predicted sd
            wins = {}
            hw_ok = True
            for k in ("t1", "t2"):
                w = windows.get((sid, k), [])
                wins[k] = w
                cov = rec["cov1"] if k == "t1" else rec["cov2"]
                if cov >= MIN_COVERAGE:
                    sds = [sd for _, sd in w] or [rec["next1_sd_d" if k == "t1" else "next2_sd_d"]]
                    sd_med = float(np.nanmedian(sds)) if len(sds) else float("nan")
                    dur = rec["dur1_h" if k == "t1" else "dur2_h"]
                    dur = dur if np.isfinite(dur) else 4.0
                    hw = WINDOW_NSIGMA * sd_med + dur / 48.0
                    rec["hw_" + k] = hw
                    if not (np.isfinite(hw) and hw <= P / 4.0):
                        hw_ok = False
            rec["timeable"] = hw_ok
            # expected depth and noise
            depth = min((rec["r2"] / rec["r1"]) ** 2, 1.0) * 1e6 if rec["r1"] > 0 else float("nan")
            noise = [fnum(e.get("box_noise_ppm")) for e in evs]
            noise = [x for x in noise if np.isfinite(x) and x > 0]
            sig = float(np.median(noise)) if noise else tess_noise_fallback(rec["gmag"])
            rec["exp_depth_ppm"] = depth
            rec["noise_ppm"] = sig
            rec["exp_snr"] = depth / sig if sig > 0 else float("nan")
            # detections at the conjunctions, and in the control windows
            det = {"t1": None, "t2": None}
            strong = False
            ctrl_hit = False
            q_times, dsep = control_phases(rec["t_conj1_btjd"], rec["t_conj2_btjd"], P) \
                if np.isfinite(rec["t_conj1_btjd"]) and np.isfinite(rec["t_conj2_btjd"]) \
                else ([], float("nan"))
            all_sd = [sd for k in ("t1", "t2") for _, sd in wins[k]]
            sd_typ = float(np.median(all_sd)) if all_sd else float("nan")
            dur_typ = np.nanmean([rec["dur1_h"], rec["dur2_h"]])
            dur_typ = dur_typ if np.isfinite(dur_typ) else 4.0
            hw_c = WINDOW_NSIGMA * sd_typ + dur_typ / 48.0
            ctrl_valid = bool(q_times) and np.isfinite(hw_c) and \
                min(dsep, P - dsep) / 2.0 >= 2.0 * hw_c
            rec["control_valid"] = ctrl_valid and hw_ok
            rec["period_err"] = fnum(pr.get("period_err"))
            clean = []
            for ev in evs:
                if not event_quality(ev):
                    continue
                tt = fnum(ev.get("t_center"))
                dh = fnum(ev.get("duration_h"), 4.0)
                clean.append((tt, fnum(ev.get("snr"), 0.0), fnum(ev.get("depth_ppm")), dh))
                if fnum(ev.get("bf"), 0.0) > STRONG_BF and fnum(ev.get("snr"), 0.0) > STRONG_SNR:
                    strong = True
                if not hw_ok:
                    continue
                for k in ("t1", "t2"):
                    m = match_window(tt, dh, wins[k], P)
                    if m is None:
                        continue
                    snr = fnum(ev.get("snr"), 0.0)
                    if det[k] is None or snr > det[k]["snr"]:
                        det[k] = {"t": tt, "snr": snr, "depth_ppm": fnum(ev.get("depth_ppm")),
                                  "dur_h": dh, "offset_d": m[0], "sd_d": m[1], "z": m[2]}
                if rec["control_valid"] and any(phase_distance(tt, qt, P) <= hw_c
                                                for qt in q_times):
                    ctrl_hit = True
            rec["det_mode"] = "window" if hw_ok else "repeat"
            rec["repeat"] = None
            if not hw_ok:
                rm = repeat_match([c[0] for c in clean], P, rec["period_err"])
                if rm is not None:
                    rec["repeat"] = rm
                    ev_a = max((c for c in clean if c[0] in (rm[0], rm[1])), key=lambda c: c[1])
                    det["t1"] = {"t": ev_a[0], "snr": ev_a[1], "depth_ppm": ev_a[2],
                                 "dur_h": ev_a[3], "offset_d": float("nan"),
                                 "sd_d": float("nan"), "z": float("nan")}
            rec["det_t1"] = det["t1"] is not None and hw_ok
            rec["det_t2"] = det["t2"] is not None and hw_ok
            rec["detected"] = det["t1"] is not None or det["t2"] is not None
            best = max([d for d in det.values() if d is not None], key=lambda d: d["snr"],
                       default=None)
            rec["best"] = best
            if best is None:
                rec["best_conj"] = ""
            elif not hw_ok:
                rec["best_conj"] = "repeat"
            else:
                rec["best_conj"] = "t1" if best is det["t1"] else "t2"
            rec["strong_rule"] = strong
            rec["control_hit"] = ctrl_hit
            if not rec["excluded"]:
                if rec["gaia_eb"]:
                    rec["excluded"] = "gaia_eb"
                elif rec["group"] == "OrbitalAlternative*":
                    rec["excluded"] = "alternative_solution"
                elif max(rec["cov1"], rec["cov2"]) < MIN_COVERAGE:
                    rec["excluded"] = "not_covered"
                elif not rec["timeable"] and not repeat_applicable(P, rec["period_err"]):
                    rec["excluded"] = "untimeable"
                elif not (rec["exp_snr"] >= MIN_EXP_SNR):
                    rec["excluded"] = "low_exp_snr"
                elif not (np.isfinite(rec["cosi"]) and np.isfinite(rec["cosi_sd"])
                          and np.isfinite(rec["lim1"])):
                    rec["excluded"] = "bad_prior"
        recs.append(rec)
    return recs


def load_windows(rows):
    w = {}
    for r in rows:
        key = (str(r.get("source_id", "")).strip(), str(r.get("conj", "")).strip())
        c, sd = fnum(r.get("centre")), fnum(r.get("sd"))
        if np.isfinite(c) and np.isfinite(sd):
            w.setdefault(key, []).append((c, sd))
    return w


# ------------------------------------------------------------------ analysis
def arrays(recs):
    return {k: np.array([r[k] for r in recs], dtype=float)
            for k in ("cosi", "cosi_sd", "lim1", "lim2", "cov1", "cov2")} | \
        {"det": np.array([r["detected"] for r in recs], dtype=bool)}


def analyse(recs, fa):
    A = arrays(recs)
    args = (A["cosi"], A["cosi_sd"], A["lim1"], A["lim2"], A["cov1"], A["cov2"])
    det = A["det"]
    p0 = p_detect(*args)
    pexp0 = fa + (1 - fa) * p0
    n_obs = int(det.sum())
    n_exp = float(pexp0.sum())
    out = {"n": len(recs), "n_obs": n_obs, "n_exp_m0": n_exp,
           "ratio": (n_obs / n_exp) if n_exp > 0 else float("nan"),
           "p_le_obs_m0": poisson_binomial_cdf(pexp0, n_obs),
           "lnL_m0": loglike(p0, det, fa)}
    if len(recs) >= 5:
        out["fit_k"] = fit_1d(lambda k: loglike(p_detect(*args, k=k), det, fa), K_GRID)
        out["fit_f"] = fit_1d(lambda f: loglike(p_detect(*args, f=f), det, fa), F_GRID)
        out["fit_s"] = fit_1d(lambda s: loglike(p_detect(*args, s=s), det, fa), S_GRID)
        best = (-np.inf, None, None)
        for k in K_GRID[::4]:
            for f in F_GRID[::3]:
                ll = loglike(p_detect(*args, k=k, f=f), det, fa)
                if ll > best[0]:
                    best = (ll, float(k), float(f))
        out["fit_kf"] = {"lnL": best[0], "k": best[1], "f": best[2]}
    return out, p0


def timing_stats(recs):
    zs = np.array([r["best"]["z"] for r in recs if r.get("best")], dtype=float)
    zs = zs[np.isfinite(zs)]
    if zs.size == 0:
        return {"n": 0}
    return {"n": int(zs.size), "rms_z": float(np.sqrt(np.mean(zs ** 2))),
            "median_abs_z": float(np.median(np.abs(zs))),
            "frac_abs_z_lt1": float(np.mean(np.abs(zs) < 1)),
            "frac_abs_z_lt2": float(np.mean(np.abs(zs) < 2)),
            "expected_truncated_normal": {"rms_z": 0.986, "frac_lt1": 0.685,
                                          "frac_lt2": 0.957}}


def bins(recs, fa):
    defs = {
        "solution group": lambda r: r["group"],
        "period (d)": lambda r: "<30" if r["period_d"] < 30 else "30-100" if r["period_d"] < 100
        else "100-300" if r["period_d"] < 300 else ">=300",
        "G (mag)": lambda r: "<9" if r["gmag"] < 9 else "9-11" if r["gmag"] < 11 else ">=11",
        "significance": lambda r: "<20" if r["significance"] < 20 else "20-50"
        if r["significance"] < 50 else ">=50",
        "eccentricity": lambda r: "<0.3" if r["ecc"] < 0.3 else "0.3-0.6" if r["ecc"] < 0.6
        else ">=0.6",
        "RUWE": lambda r: "<2" if r["ruwe"] < 2 else "2-5" if r["ruwe"] < 5 else ">=5",
        "class": lambda r: r["class"],
        "Gaia p(eclipse seen) under M0": lambda r: "<0.3" if r["p0"] < 0.3 else "0.3-0.7"
        if r["p0"] < 0.7 else ">=0.7",
    }
    out = {}
    for name, fn in defs.items():
        groups = {}
        for r in recs:
            groups.setdefault(fn(r), []).append(r)
        rows = []
        for label in sorted(groups):
            g = groups[label]
            pe = np.array([fa + (1 - fa) * r["p0"] for r in g])
            n_obs = int(sum(r["detected"] for r in g))
            rows.append({"bin": label, "n": len(g), "n_obs": n_obs,
                         "n_exp_m0": float(pe.sum()),
                         "ratio": n_obs / float(pe.sum()) if pe.sum() > 0 else float("nan"),
                         "p_le_obs_m0": poisson_binomial_cdf(pe, n_obs)})
        out[name] = rows
    return out


def grade(res, timing, by_group, n_strong):
    """The pre-registered predictions C1-C7."""
    g = {}
    r = res["ratio"]
    g["C1"] = {"prediction": "0.45 <= N_obs / N_exp(M0) <= 0.85", "value": r,
               "pass": bool(0.45 <= r <= 0.85)}
    g["C2"] = {"prediction": "P(N <= N_obs | M0) < 0.01 (Gaia's errors as published are rejected)",
               "value": res["p_le_obs_m0"], "pass": bool(res["p_le_obs_m0"] < 0.01)}
    fk = res.get("fit_k", {})
    g["C3"] = {"prediction": "1.5 <= k_ML <= 5 and k = 1 outside the 95% interval",
               "value": fk, "pass": bool(fk and 1.5 <= fk["best"] <= 5 and fk["lo95"] > 1.0)}
    rz = timing.get("rms_z", float("nan"))
    g["C4"] = {"prediction": "0.6 <= rms(z) <= 1.4 for the detected eclipses", "value": rz,
               "pass": bool(0.6 <= rz <= 1.4)}
    sb1 = next((x for x in by_group if x["bin"] == "AstroSpectroSB1"), None)
    oth = [x for x in by_group if x["bin"] in ("Orbital", "OrbitalTargetedSearch*")]
    n_o, e_o = sum(x["n_obs"] for x in oth), sum(x["n_exp_m0"] for x in oth)
    r_o = n_o / e_o if e_o > 0 else float("nan")
    r_s = sb1["ratio"] if sb1 else float("nan")
    g["C5"] = {"prediction": "ratio(AstroSpectroSB1) >= 1.3 x ratio(Orbital + TargetedSearch)",
               "value": {"astrospectrosb1": r_s, "orbital_types": r_o},
               "pass": bool(np.isfinite(r_s) and np.isfinite(r_o) and r_s >= 1.3 * r_o)}
    if "fit_k" in res:
        d = res["fit_k"]["lnL"] - res["fit_s"]["lnL"]
        g["C6"] = {"prediction": "lnL(k model) - lnL(radius-scale model) >= 2", "value": d,
                   "pass": bool(d >= 2)}
    g["C7"] = {"prediction": "N_obs >= 1.3 x N(old strong-match rule) in the same sample",
               "value": {"n_obs": res["n_obs"], "n_strong_rule": n_strong},
               "pass": bool(res["n_obs"] >= 1.3 * n_strong)}
    return g


# ------------------------------------------------------------------ io
def fetch_inputs(data_dir, offline=False):
    sub = os.path.join(data_dir, "dr3-full-search-v4")
    os.makedirs(sub, exist_ok=True)
    paths = {}
    for name in FILES:
        p = os.path.join(sub, name)
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            if offline:
                raise FileNotFoundError(p)
            print(f"downloading {name}", flush=True)
            tmp = p + ".part"
            urllib.request.urlretrieve(RAW + name, tmp)
            os.replace(tmp, p)
        paths[name] = p
    return paths


def _fmt(x, nd=3):
    if isinstance(x, float):
        return "nan" if not np.isfinite(x) else f"{x:.{nd}f}"
    return str(x)


def write_outputs(out_dir, recs, main, res, ctrl, timing, bin_tab, grades, n_strong):
    os.makedirs(out_dir, exist_ok=True)
    cols = ["source_id", "tic", "solution_type", "group", "class", "gmag", "period_d", "ecc",
            "significance", "ruwe", "cosi", "cosi_sd", "lim1", "lim2", "p1_analytic",
            "p2_analytic", "p_ecl1", "p_ecl2", "cov1", "cov2", "p0", "exp_depth_ppm",
            "noise_ppm", "exp_snr", "excluded", "det_mode", "detected", "det_t1", "det_t2",
            "best_conj",
            "best_t", "best_depth_ppm", "best_snr", "best_offset_d", "best_sd_d", "best_z",
            "strong_rule", "control_valid", "control_hit", "transit_conj"]
    with open(os.path.join(out_dir, "calib_targets.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in recs:
            b = r.get("best") or {}
            row = dict(r)
            row.update({"best_t": b.get("t", ""), "best_depth_ppm": b.get("depth_ppm", ""),
                        "best_snr": b.get("snr", ""), "best_offset_d": b.get("offset_d", ""),
                        "best_sd_d": b.get("sd_d", ""), "best_z": b.get("z", "")})
            w.writerow([row.get(c, "") for c in cols])
    summary = {"version": VERSION, "rule": {
        "min_snr": MIN_SNR, "min_depth_ppm": MIN_DEPTH_PPM, "window_nsigma": WINDOW_NSIGMA,
        "min_exp_snr": MIN_EXP_SNR, "min_coverage": MIN_COVERAGE},
        "n_targets": len(recs), "n_main": len(main),
        "excluded": {k: sum(1 for r in recs if r["excluded"] == k)
                     for k in sorted({r["excluded"] for r in recs if r["excluded"]})},
        "control": ctrl, "main": res, "timing": timing, "bins": bin_tab,
        "n_strong_rule_main": n_strong, "grades": grades}
    with open(os.path.join(out_dir, "calib_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, default=float)
    L = [f"# Gaia DR3 orbit inclinations against TESS eclipses (calib_eclipse_rate {VERSION})",
         "", "MV2 of Munim, Inc.; made with AI agents. Code Apache-2.0, text CC BY 4.0.", "",
         f"Targets: {len(recs)}; main sample: {len(main)}. Excluded: "
         + ", ".join(f"{k} {v}" for k, v in summary["excluded"].items()), "",
         f"False-alarm control (phases half-way between conjunctions): {ctrl['hits']} hits "
         f"in {ctrl['valid']} valid targets, rate {_fmt(ctrl['rate'])}.", "",
         "## Main result", "",
         f"- Eclipsing targets seen: **{res['n_obs']}**; expected if Gaia's orbits and errors "
         f"are right (M0): **{_fmt(res['n_exp_m0'], 1)}**; ratio **{_fmt(res['ratio'])}**; "
         f"P(N <= seen | M0) = {res['p_le_obs_m0']:.3g}.",
         f"- Old strong-match rule (BF > 10) in the same sample: {n_strong}."]
    for key, lab in (("fit_k", "sigma(cos i) inflation k"), ("fit_f", "wrong-orbit fraction f"),
                     ("fit_s", "radius scale s")):
        if key in res:
            f = res[key]
            L.append(f"- {lab}: best {_fmt(f['best'], 2)} (95%: {_fmt(f['lo95'], 2)}-"
                     f"{_fmt(f['hi95'], 2)}), lnL {_fmt(f['lnL'], 2)} vs M0 "
                     f"{_fmt(res['lnL_m0'], 2)}")
    if "fit_kf" in res:
        L.append(f"- k and f together: k {_fmt(res['fit_kf']['k'], 2)}, f "
                 f"{_fmt(res['fit_kf']['f'], 2)}, lnL {_fmt(res['fit_kf']['lnL'], 2)}")
    L += ["", "## Timing of the detected eclipses", "", json.dumps(timing), "",
          "## Bins (M0 expectation includes the false-alarm rate)", ""]
    for name, rows in bin_tab.items():
        L += [f"### {name}", "", "| bin | n | seen | expected (M0) | ratio | P(<= seen) |",
              "|---|---|---|---|---|---|"]
        for x in rows:
            L.append(f"| {x['bin']} | {x['n']} | {x['n_obs']} | {_fmt(x['n_exp_m0'], 1)} | "
                     f"{_fmt(x['ratio'], 2)} | {x['p_le_obs_m0']:.3g} |")
        L.append("")
    L += ["## Grades", "", "| # | prediction | value | pass |", "|---|---|---|---|"]
    for k, v in grades.items():
        L.append(f"| {k} | {v['prediction']} | {json.dumps(v['value'], default=float)[:120]} "
                 f"| {'yes' if v['pass'] else 'no'} |")
    miss = sorted([r for r in main if not r["detected"] and r["p0"] >= 0.8],
                  key=lambda r: -r["p0"])
    L += ["", "## Predicted with p >= 0.8 but not seen", "",
          "| Gaia DR3 | TIC | type | G | P (d) | cos i +- sd | p0 | cov1/cov2 | exp. depth |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in miss:
        L.append(f"| {r['source_id']} | {r['tic']} | {r['solution_type']} | {_fmt(r['gmag'], 2)}"
                 f" | {_fmt(r['period_d'], 2)} | {_fmt(r['cosi'], 4)} +- {_fmt(r['cosi_sd'], 4)}"
                 f" | {_fmt(r['p0'], 2)} | {_fmt(r['cov1'], 2)}/{_fmt(r['cov2'], 2)} | "
                 f"{_fmt(r['exp_depth_ppm'] / 1e4, 2)}% |")
    new = [r for r in main if r["detected"] and not r["strong_rule"]]
    L += ["", "## Seen by the window rule but not by the old BF > 10 rule", "",
          "| Gaia DR3 | TIC | P (d) | conj | BTJD | depth (ppm) | SNR | z |",
          "|---|---|---|---|---|---|---|---|"]
    for r in new:
        b = r["best"]
        L.append(f"| {r['source_id']} | {r['tic']} | {_fmt(r['period_d'], 2)} | "
                 f"{r['best_conj']} | {_fmt(b['t'], 3)} | {_fmt(b['depth_ppm'], 0)} | "
                 f"{_fmt(b['snr'], 1)} | {_fmt(b['z'], 2)} |")
    L += ["", "Every detection here is a dip in the TESS search output, not a vetted eclipse; "
          "plots must be checked before any single system is reported."]
    with open(os.path.join(out_dir, "calib_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return summary


def run(data_dir, out_dir, offline=False):
    paths = fetch_inputs(data_dir, offline)
    targets = read_csv(paths["tess_targets.csv"])
    wanted = {str(t.get("source_id", "")).strip() for t in targets}
    priors = read_priors(paths["gaia_edge_on_priors.csv"], wanted)
    events = read_csv(paths["events.csv"])
    windows = load_windows(read_csv(paths["covered_windows.csv"]))
    recs = build_records(targets, priors, events, windows)
    for r in recs:
        if r["excluded"] in ("no_tess", "no_prior"):
            r["p0"] = float("nan")
            r.setdefault("detected", False)
            r.setdefault("strong_rule", False)
            r.setdefault("control_valid", False)
            r.setdefault("control_hit", False)
            r.setdefault("best", None)
    main = [r for r in recs if not r["excluded"]]
    cv = [r for r in main if r["control_valid"]]
    hits = sum(1 for r in cv if r["control_hit"])
    rate = hits / len(cv) if cv else 0.0
    ctrl = {"valid": len(cv), "hits": hits, "rate": rate}
    res, p0 = analyse(main, rate) if main else ({"n": 0, "n_obs": 0, "n_exp_m0": 0.0,
                                                 "ratio": float("nan"), "p_le_obs_m0": 1.0,
                                                 "lnL_m0": 0.0}, [])
    for r, p in zip(main, p0):
        r["p0"] = float(p)
    for r in recs:
        if "p0" not in r:
            try:
                r["p0"] = float(p_detect(r["cosi"], r["cosi_sd"], r["lim1"], r["lim2"],
                                         r["cov1"], r["cov2"]))
            except (KeyError, TypeError):
                r["p0"] = float("nan")
    d1 = [abs(r["p1_analytic"] - r["p_ecl1"]) for r in main if np.isfinite(r["p_ecl1"])]
    d2 = [abs(r["p2_analytic"] - r["p_ecl2"]) for r in main if np.isfinite(r["p_ecl2"])]
    res["analytic_vs_mc_median_abs_diff"] = {
        "conj1": float(np.median(d1)) if d1 else float("nan"),
        "conj2": float(np.median(d2)) if d2 else float("nan")}
    timing = timing_stats([r for r in main if r["detected"]])
    bin_tab = bins(main, rate) if main else {}
    n_strong = sum(1 for r in main if r["strong_rule"])
    grades = grade(res, timing, bin_tab.get("solution group", []), n_strong)
    summary = write_outputs(out_dir, recs, main, res, ctrl, timing, bin_tab, grades, n_strong)
    print(json.dumps({"n_main": len(main), "n_obs": res["n_obs"],
                      "n_exp_m0": res["n_exp_m0"], "ratio": res["ratio"],
                      "fit_k": res.get("fit_k"), "control": ctrl,
                      "grades": {k: v["pass"] for k, v in grades.items()}}, default=float))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--offline", action="store_true",
                    help="use files already in DATA_DIR/dr3-full-search-v4/")
    a = ap.parse_args(argv)
    run(a.data_dir, a.out_dir, a.offline)
    return 0


if __name__ == "__main__":
    sys.exit(main())
