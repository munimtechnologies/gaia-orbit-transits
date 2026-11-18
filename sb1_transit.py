# SPDX-License-Identifier: Apache-2.0
"""sb1_transit.py -- do Gaia DR3 brown-dwarf-mass SB1 companions transit as often as they must?

Part of gaia-orbit-transits 0.15.0 by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0. Pre-registration: findings/2026-11-18-sb1-transit-prereg.md

Gaia DR3 published ~21,000 single-lined spectroscopic orbits (SB1/SB1C, P = 1-1000 d,
G <= 13) whose mass function allows a companion below ~0.1 Msun. If those orbits are real
and the companions really are brown dwarfs or very-low-mass stars, a fraction
(R1 + R2) / r of them (5-20 % at P = 1-10 d) must transit at the Gaia period.
Stevenson et al. (2023, AJ 166, 225) found three transiting companions among ~2,490
Sun-like brown-dwarf-mass SB1 orbits, through the TOI list. This script measures the
transit rate directly in TESS light curves:

  1. Gaia TAP: SB1/SB1C orbits, 1 <= P < 13 d, G <= 13, m2 sin i 0.005-0.10 Msun,
     dwarfs (R1 <= 2.5 Rsun). Seeded random order, split into chunks. (Longer periods
     give < 3 transits per sector, where a phase-free fold is a single-event search that
     period-shifted controls cannot calibrate; they need Gaia timing and are left for a
     separate, timed study.)
  2. TESS (SPOC 120 s > TESS-SPOC > QLP), up to --max-sectors sectors per star.
     Each sector is detrended (running median, window max(3 D, 0.5 d), gaps and ends
     masked as in dipsearch 0.4.4 DR4 options) and FOLDED AT THE GAIA PERIOD with a free
     phase. (Within one sector the Gaia period error is negligible; across the years
     since 2016 it is not: for P ~ 5 d the predicted transit time drifts by 0.2-1 d, so
     the phase is left free and only checked afterwards.)
  3. A sector HITS when the best box (width D = max(0.6 T14, 1 h)) has SNR >= 7
     (the smaller of the white-noise and the empirical across-phase SNR), at least 70 %
     of its depth survives against the neighbouring phases, the box holds >= 3 separate
     transits, and removing the strongest single transit leaves SNR >= 3. A star hits
     when any used sector hits.
  4. Sensitivity: the predicted transit (depth 0.8 (R2/R1)^2, duration T14) is injected
     at N_INJ random phases into the raw flux and the same pipeline run; s = fraction
     recovered at the injected phase. Stars with s >= 0.5 form the rate sample.
  5. Control: the same fold search at two unrelated trial periods, 0.8541 P and 0.9137 P
     (close to P, so they hold as many cycles per sector, but non-harmonic), after
     masking the best box at P (so a real transit cannot leak into the controls).
  6. Reality fraction rho = (hits - control hits) / sum(p_transit * s) over the rate
     sample, with a Garwood 95 % interval.
  7. Independent check for every hit: where Gaia still times the transit (3 sigma <
     P/4), the found phase is compared with the predicted one (f = pi/2 - omega; this
     convention reproduces WASP-18 b's TESS epoch to 0.022 d after 2,991 orbits).
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
GAIA_REF_BTJD = 389.0          # J2016.0 = JD 2457389.0
RSUN_AU = 0.00465047
MJUP_MSUN = 9.5458e-4
FM_CONST = 1.0361e-7           # f(M) [Msun] = FM_CONST (1 - e^2)^1.5 K^3 [km/s] P [d]
BD_MAX = 0.075                 # Msun (78.5 M_Jup)
BIN_W = 1.0 / 48

# ---- pre-registered constants (findings/2026-11-18-sb1-transit-prereg.md) ----
P_MIN, P_MAX = 1.0, 13.0
MIN_EPOCHS = 3
G_MAX = 13.0
M2_MIN, M2_MAX = 0.005, 0.10
R1_MAX = 2.5
KP_SERVER_MAX = 15440.0        # K^3 P server-side cut (f < 1.6e-3 Msun before (1-e^2))
SNR_MIN = 7.0
LOCAL_MIN = 0.7
DROP1_MIN = 3.0
BOX_FRAC = 0.6
BOX_MIN_D = 1.0 / 24
MAX_BOX_PHASE = 0.2
INJ_DEPTH_FACTOR = 0.8
N_INJ = 4
SENS_MIN = 0.5
CONTROL_RATIOS = (0.8541, 0.9137)   # near 1 (same number of cycles), non-harmonic
TOO_DEEP_FACTOR = 3.0
MOD_FACTOR = 0.5
TIMED_SIG = 3.0
SEED = 20261118
POSITIVE_CONTROLS = {
    "4955371367334610048": "WASP-18 b (10.4 M_Jup, P 0.941 d)",
    "1259922196651254272": "TOI-2533 b (72 M_Jup BD, P 6.68 d)",
    "917823348536224768": "TOI-1712 b (82 M_Jup, P 3.57 d)",
    "3341401062125577088": "TOI-5427 b (93 M_Jup, P 5.24 d)",
}
AUTHORS = ("SPOC", "TESS-SPOC", "QLP")
ORBIT_TIMES_URL = "https://tess.mit.edu/public/files/TESS_orbit_times.csv"
TOI_URL = "https://exofop.ipac.caltech.edu/tess/download_toi.php?sort=toi&output=csv"
TAP_URLS = ("https://gea.esac.esa.int/tap-server/tap/sync",
            "https://gaia.ari.uni-heidelberg.de/tap/sync")

# rough main-sequence relations from absolute G (fallback when FLAME is missing)
_MG = [0.5, 1.5, 2.5, 3.5, 4.4, 5.0, 5.6, 6.2, 6.9, 7.6, 8.4, 9.2, 10.0, 10.8, 11.6]
_MASS = [2.2, 1.7, 1.4, 1.15, 1.0, 0.92, 0.85, 0.78, 0.70, 0.62, 0.55, 0.48, 0.40, 0.32, 0.25]
_RAD = [1.9, 1.6, 1.35, 1.15, 1.0, 0.9, 0.82, 0.75, 0.68, 0.62, 0.55, 0.48, 0.40, 0.31, 0.25]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ================================================================ pure helpers (no numpy)
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
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            w = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + w * (ys[i] - ys[i - 1])
    return ys[-1]


def true_to_mean(f, e):
    E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(f / 2.0),
                         math.sqrt(1.0 + e) * math.cos(f / 2.0))
    return (E - e * math.sin(E)) % (2.0 * math.pi)


def transit_phase(e, omega_deg):
    """Phase after periastron (0..1) of the transit (companion in front of the primary);
    omega_deg is the primary's spectroscopic argument of periastron (Gaia arg_periastron)."""
    return true_to_mean(math.pi / 2.0 - math.radians(omega_deg), e) / (2.0 * math.pi)


def secondary_phase(e, omega_deg):
    return true_to_mean(1.5 * math.pi - math.radians(omega_deg), e) / (2.0 * math.pi)


def transit_time_btjd(T, P, e, omega_deg, ref=GAIA_REF_BTJD):
    return ref + T + transit_phase(e, omega_deg) * P


def secondary_time_btjd(T, P, e, omega_deg, ref=GAIA_REF_BTJD):
    return ref + T + secondary_phase(e, omega_deg) * P


def wrap(x, P):
    """x modulo P into [-P/2, P/2)."""
    return (x + P / 2.0) % P - P / 2.0


def mass_function(K, P, e=0.0):
    return FM_CONST * (1.0 - e * e) ** 1.5 * K ** 3 * P


def m2_min(K, P, e, m1):
    fm = mass_function(K, P, e)
    m2 = (fm * m1 * m1) ** (1.0 / 3.0)
    for _ in range(100):
        m2 = (fm * (m1 + m2) ** 2) ** (1.0 / 3.0)
    return m2


def semi_major_axis_rsun(m1, m2, P):
    return ((m1 + m2) * (P / 365.25) ** 2) ** (1.0 / 3.0) / RSUN_AU


def companion_radius(m2):
    """Rsun; brown dwarfs and the lowest-mass stars ~0.1 Rsun (~1 R_Jup)."""
    return 0.10 if m2 < 0.08 else max(0.10, m2 ** 0.9)


def transit_separation(a, e, omega_deg):
    return a * (1.0 - e * e) / (1.0 + e * math.sin(math.radians(omega_deg)))


def transit_probability(r1, r2, a, e, omega_deg):
    return min(1.0, (r1 + r2) / transit_separation(a, e, omega_deg))


def duration_days(P, r1, r2, a, e, omega_deg):
    """Central (b = 0) total duration (Winn 2010 eq. 14 and 16)."""
    x = min(1.0, (r1 + r2) / a)
    return P / math.pi * math.asin(x) * math.sqrt(1.0 - e * e) / \
        (1.0 + e * math.sin(math.radians(omega_deg)))


def box_width(t14):
    return max(BOX_FRAC * t14, BOX_MIN_D)


def sb1_param_names(solution_type):
    st = str(solution_type or "").strip().strip('"').upper()
    if st == "SB1":
        return ["period", "center_of_mass_velocity", "semi_amplitude_primary",
                "eccentricity", "arg_periastron", "t_periastron"]
    if st == "SB1C":
        return ["period", "center_of_mass_velocity", "semi_amplitude_primary", "t_periastron"]
    return None


def parse_corr_vec(x):
    if x is None:
        return None
    if isinstance(x, (list, tuple)):
        return [float(v) for v in x]
    s = str(x).strip().strip('"').strip()
    if not s or s.lower() in ("null", "nan", "--"):
        return None
    s = s.strip("()[]{}")
    out = []
    for p in s.replace(";", ",").replace(" ", ",").split(","):
        p = p.strip()
        if not p:
            continue
        try:
            out.append(float(p))
        except ValueError:
            out.append(float("nan"))
    return out


def corr_matrix(vec, n):
    """Full n x n correlation (list of lists) from Gaia's column-major upper triangle:
    (0,1), (0,2), (1,2), (0,3), ... NaN -> 0."""
    if vec is None or len(vec) != n * (n - 1) // 2:
        raise ValueError("corr_vec length %s, expected %d" % (None if vec is None else len(vec),
                                                              n * (n - 1) // 2))
    R = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    k = 0
    for j in range(1, n):
        for i in range(j):
            c = vec[k]
            c = c if math.isfinite(c) else 0.0
            R[i][j] = R[j][i] = c
            k += 1
    return R


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


def utc_to_btjd(s):
    import datetime as _dt
    d = _dt.datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S")
    jd = (d - _dt.datetime(1858, 11, 17)).total_seconds() / 86400.0 + 2400000.5
    return jd - 2457000.0


def sector_hit(res):
    """Fixed per-sector rule on a fold_search result dict."""
    if not res:
        return False
    if not (res.get("depth", 0) > 0 and res.get("snr", 0) >= SNR_MIN):
        return False
    if res.get("local_ratio", 0) < LOCAL_MIN:
        return False
    if res.get("n_ep", 0) < MIN_EPOCHS or res.get("snr_drop1", 0) < DROP1_MIN:
        return False
    return True


def phase_check(t_found, t_pred, sigma, P):
    """Compare a found transit time with the Gaia prediction: (offset_d, z, label)."""
    off = wrap(t_found - t_pred, P)
    if not (sigma > 0) or TIMED_SIG * sigma >= P / 4.0:
        return off, float("nan"), "UNTIMED"
    z = off / sigma
    return off, z, ("PHASE_MATCH" if abs(z) < TIMED_SIG else "PHASE_MISMATCH")


def star_physics(row):
    """m1, r1 (Rsun), m2 sin i, a, transit probability, duration, expected depth."""
    P = fval(row, "period")
    K = fval(row, "semi_amplitude_primary")
    circ = str(row.get("nss_solution_type", "")).strip().upper() == "SB1C"
    e = 0.0 if circ else fval(row, "eccentricity", 0.0)
    w = 0.0 if circ else fval(row, "arg_periastron", 0.0)
    G = fval(row, "phot_g_mean_mag")
    plx = fval(row, "parallax")
    absg = G + 5.0 * math.log10(plx / 100.0) if (math.isfinite(G) and plx > 0) else float("nan")
    m1 = fval(row, "mass_flame")
    m1_src = "flame"
    if not (m1 > 0):
        m1 = interp(absg, _MG, _MASS) if math.isfinite(absg) else 1.0
        m1_src = "absG" if math.isfinite(absg) else "default"
    r1 = fval(row, "radius_flame")
    if not (r1 > 0):
        r1 = fval(row, "radius_gspphot")
    if not (r1 > 0):
        r1 = interp(absg, _MG, _RAD) if math.isfinite(absg) else 1.0
    m2 = m2_min(K, P, e, m1) if (K > 0 and P > 0) else float("nan")
    r2 = companion_radius(m2) if math.isfinite(m2) else 0.1
    a = semi_major_axis_rsun(m1, m2 if math.isfinite(m2) else 0.0, P)
    ptr = transit_probability(r1, r2, a, e, w)
    t14 = duration_days(P, r1, r2, a, e, w)
    return {"P": P, "K": K, "e": e, "omega_deg": w, "circular": circ, "abs_g": absg,
            "m1": m1, "m1_src": m1_src, "r1": r1, "m2sini": m2, "r2": r2, "a_rsun": a,
            "p_transit": ptr, "t14_d": t14, "depth_exp": (r2 / r1) ** 2,
            "m2_class": ("planet" if m2 < 13 * MJUP_MSUN else "BD" if m2 < BD_MAX else "VLMS")
            if math.isfinite(m2) else "unknown"}


def eligible(row, phys):
    if not (P_MIN <= phys["P"] < P_MAX):
        return False, "period"
    G = fval(row, "phot_g_mean_mag")
    if not (G <= G_MAX):
        return False, "G"
    if not (M2_MIN <= phys["m2sini"] <= M2_MAX):
        return False, "m2sini"
    if not (phys["r1"] <= R1_MAX):
        return False, "evolved"
    lg = fval(row, "logg_gspphot")
    if math.isfinite(lg) and lg < 3.5:
        return False, "evolved"
    if phys["e"] >= 0.9:
        return False, "ecc"
    return True, ""


def chunk_order(ids, n_chunks, chunk, seed=SEED):
    """Seeded random order of ids, then every n_chunks-th starting at chunk."""
    ids = sorted(ids)
    rnd = random.Random(seed)
    rnd.shuffle(ids)
    return [x for i, x in enumerate(ids) if i % n_chunks == chunk]


def classify_hit(depth_obs, depth_exp, mod_amp=0.0):
    if not (depth_obs > 0):
        return ""
    if mod_amp > MOD_FACTOR * depth_obs:
        return "MODULATED"
    return "TOO_DEEP" if depth_obs > TOO_DEEP_FACTOR * depth_exp else "SUBSTELLAR_SIZE"


# ================================================================ numpy parts
def sample_ephemeris(row, n, rng):
    """Central transit / secondary times and the variance terms needed for sigma(k)."""
    import numpy as np
    st = str(row.get("nss_solution_type", "")).strip().upper()
    circ = st == "SB1C"
    P = fval(row, "period")
    T = fval(row, "t_periastron")
    e = 0.0 if circ else fval(row, "eccentricity", 0.0)
    w = 0.0 if circ else fval(row, "arg_periastron", 0.0)
    t0 = transit_time_btjd(T, P, e, w)
    t2 = secondary_time_btjd(T, P, e, w)
    keys = ["period", "t_periastron"] if circ else \
        ["period", "eccentricity", "arg_periastron", "t_periastron"]
    mu = np.array([P, T] if circ else [P, e, w, T], float)
    sd = np.array([max(0.0, fval(row, k + "_error", 0.0)) for k in keys], float)
    names = sb1_param_names(st)
    used_corr = False
    R = np.eye(len(keys))
    try:
        vec = parse_corr_vec(row.get("corr_vec"))
        if names is not None and vec is not None:
            full = np.array(corr_matrix(vec, len(names)))
            idx = [names.index(k) for k in keys]
            R = full[np.ix_(idx, idx)]
            used_corr = True
    except (ValueError, IndexError):
        pass
    C = R * np.outer(sd, sd)
    C = 0.5 * (C + C.T)
    ev, V = np.linalg.eigh(C)
    L = V * np.sqrt(np.clip(ev, 0.0, None))
    X = mu + rng.standard_normal((n, len(keys))) @ L.T
    Ps = np.abs(X[:, 0])
    Ts = X[:, -1]
    if circ:
        es = np.zeros(n)
        ws = np.zeros(n)
    else:
        es = np.clip(X[:, 1], 0.0, 0.95)
        ws = X[:, 2]
    ph1 = np.array([transit_phase(a, b) for a, b in zip(es, ws)])
    ph2 = np.array([secondary_phase(a, b) for a, b in zip(es, ws)])
    d1 = wrap(GAIA_REF_BTJD + Ts + ph1 * Ps - t0, P)
    d2 = wrap(GAIA_REF_BTJD + Ts + ph2 * Ps - t2, P)
    cv1 = np.cov(np.vstack([d1, Ps]))
    cv2 = np.cov(np.vstack([d2, Ps]))
    return {"t0": t0, "t2": t2, "P": P, "used_corr": used_corr,
            "v1": (float(cv1[0, 0]), float(cv1[1, 1]), float(cv1[0, 1])),
            "v2": (float(cv2[0, 0]), float(cv2[1, 1]), float(cv2[0, 1]))}


def sigma_k(v, k):
    vd, vp, c = v
    return math.sqrt(max(0.0, vd + k * k * vp + 2.0 * k * c))


def detrend(t, f, D):
    """Binned (30 min) residuals r = f / trend - 1 after the dipsearch floor and DR4 gap
    masks; trend = running median per segment with window max(3 D, 0.5 d)."""
    import numpy as np
    import dipsearch as ds
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    drop, _ = ds.floor_mask(t, f, 0.5, 0.5)
    o = ds.DR4_GAP_OPTIONS
    gdrop, _ = ds.gap_mask(t, o["gap_min"], o["gap_pad"], o["pad_ends"])
    keep = ~(drop | gdrop)
    bt, bf, _ = ds.bin_lc(t[keep], f[keep], BIN_W)
    r = np.full(bt.size, np.nan)
    for i0, i1 in ds.segments(bt, 0.5):
        if i1 - i0 < 6:
            continue
        tr = ds.running_median(bt[i0:i1], bf[i0:i1], max(3 * D, 0.5))
        r[i0:i1] = bf[i0:i1] / tr - 1.0
    ok = np.isfinite(r)
    return bt[ok], r[ok], bf[ok]


def _box_stats(ph, r, phi, w):
    import numpy as np
    d = np.abs((ph - phi + 0.5) % 1.0 - 0.5)
    inb = d < w / 2.0
    return inb, d


def fold_search(bt, r, P, D, tref):
    """Best box (phase-free) in residuals folded at P. Returns a dict or None."""
    import numpy as np
    import dipsearch as ds
    if bt.size < 50 or P <= 0:
        return None
    w = D / P
    if w > MAX_BOX_PHASE:
        return None
    ph = ((bt - tref) / P) % 1.0
    ep = np.floor((bt - tref) / P).astype(int)
    sd_bin = ds.robust_sd(r)
    if not np.isfinite(sd_bin) or sd_bin <= 0:
        return None
    n_need = max(3, int(0.5 * D / BIN_W))
    grid = np.arange(0.0, 1.0, w / 4.0)
    depth = np.full(grid.size, np.nan)
    nin = np.zeros(grid.size, int)
    for i, phi in enumerate(grid):
        inb, _ = _box_stats(ph, r, phi, w)
        n = int(inb.sum())
        nin[i] = n
        if n >= n_need:
            depth[i] = -float(np.mean(r[inb]))
    ok = np.isfinite(depth)
    if ok.sum() < 8:
        return None
    white = depth / (sd_bin / np.sqrt(np.maximum(nin, 1)))
    med = np.median(depth[ok])
    emp_sd = ds.robust_sd(depth[ok])
    emp = (depth - med) / emp_sd if emp_sd > 0 else white
    snr = np.where(ok, np.minimum(white, emp), -np.inf)
    j = int(np.argmax(snr))
    phi = float(grid[j])
    inb, dist = _box_stats(ph, r, phi, w)
    near = (dist >= 1.0 * w) & (dist <= 3.0 * w)
    local = float(np.median(r[near])) if near.sum() >= 3 else 0.0
    dj = float(depth[j])
    local_ratio = (local + dj) / dj if dj > 0 else 0.0
    eps = np.unique(ep[inb])
    drop1 = float("inf")
    if eps.size >= 3:
        vals = []
        for e_ in eps:
            m = inb & (ep != e_)
            n = int(m.sum())
            if n >= 2:
                vals.append(-float(np.mean(r[m])) / (sd_bin / math.sqrt(n)))
        drop1 = min(vals) if vals else 0.0
    # time of one in-box transit (the epoch nearest the middle of the data)
    k_mid = int(np.round(np.median(ep)))
    t_found = tref + (k_mid + phi) * P
    return {"phase": phi, "depth": dj, "snr": float(snr[j]), "snr_white": float(white[j]),
            "snr_emp": float(emp[j]), "n_in": int(nin[j]), "n_ep": int(eps.size),
            "snr_drop1": drop1, "local_ratio": float(local_ratio), "t_found": t_found,
            "box_d": D}


def modulation_amp(bt, bf, P):
    """Semi-amplitude of a sinusoid at P fitted to the normalised (undetrended) flux."""
    import numpy as np
    if bt.size < 20:
        return float("nan")
    y = bf / np.median(bf) - 1.0
    x = 2 * np.pi * bt / P
    A = np.vstack([np.ones_like(x), np.sin(x), np.cos(x)]).T
    c, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(math.hypot(c[1], c[2]))


def inject(t, f, t_first, P, t14, depth):
    import numpy as np
    g = np.array(f, float, copy=True)
    ph = ((t - t_first) / P + 0.5) % 1.0 - 0.5
    g[np.abs(ph * P) < t14 / 2.0] *= (1.0 - depth)
    return g


def measure_sector(t, f, P, t14, depth_inj, rng, tref=None):
    """Real fold search, controls and injections for one sector."""
    import numpy as np
    D = box_width(t14)
    tref = float(np.min(t)) if tref is None else tref
    bt, r, bf = detrend(t, f, D)
    real = fold_search(bt, r, P, D, tref)
    out = {"real": real, "hit": sector_hit(real), "mod_amp": modulation_amp(bt, bf, P),
           "controls": {}, "inj": [], "n_bins": int(bt.size)}
    # controls must not see the Gaia-period signal: the best box at P is masked first
    # (for every star, hit or not), so a real transit cannot leak into the control folds
    keep = np.ones(bt.size, bool)
    if real is not None:
        ph = ((bt - tref) / P - real["phase"] + 0.5) % 1.0 - 0.5
        keep = np.abs(ph) >= D / P
    out["n_masked_for_controls"] = int((~keep).sum())
    for c in CONTROL_RATIOS:
        rc = fold_search(bt[keep], r[keep], P * c, D, tref)
        out["controls"][str(c)] = {"res": rc, "hit": sector_hit(rc),
                                   "mod_amp": modulation_amp(bt, bf, P * c)}
    for j in range(N_INJ):
        phi = float(rng.uniform(0.0, 1.0))
        g = inject(t, f, tref + phi * P, P, t14, depth_inj)
        bti, ri, _ = detrend(t, g, D)
        # the real best box is masked here too (unless the injection overlaps it), so a
        # star that really transits stays sensitive to a second, injected signal
        if real is not None and abs((phi - real["phase"] + 0.5) % 1.0 - 0.5) > 2 * D / P:
            phi_i = ((bti - tref) / P - real["phase"] + 0.5) % 1.0 - 0.5
            ki = np.abs(phi_i) >= D / P
            bti, ri = bti[ki], ri[ki]
        ri_res = fold_search(bti, ri, P, D, tref)
        found = bool(sector_hit(ri_res) and
                     abs((ri_res["phase"] - phi + 0.5) % 1.0 - 0.5) <= D / P)
        out["inj"].append({"phase": phi, "found": found})
    return out


# ================================================================ network parts
def tap_query(query, timeout=120):
    import requests
    last = None
    for base in TAP_URLS:
        for attempt in range(3):
            try:
                r = requests.post(base, data={"REQUEST": "doQuery", "LANG": "ADQL",
                                              "FORMAT": "csv", "QUERY": query}, timeout=timeout)
                if r.ok and r.text.lstrip().lower().startswith("source_id"):
                    return list(csv.DictReader(io.StringIO(r.text)))
                last = "HTTP %s %s" % (r.status_code, r.text[:300])
            except Exception as exc:
                last = repr(exc)
            log("TAP retry", base, attempt + 1, last)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("TAP failed: %s" % last)


COLS = ("o.source_id, o.nss_solution_type, o.period, o.period_error, o.eccentricity, "
        "o.eccentricity_error, o.arg_periastron, o.arg_periastron_error, o.t_periastron, "
        "o.t_periastron_error, o.semi_amplitude_primary, o.semi_amplitude_primary_error, "
        "o.significance, o.goodness_of_fit, o.bit_index, o.corr_vec, s.ra, s.dec, "
        "s.phot_g_mean_mag, s.bp_rp, s.parallax, s.parallax_error, s.ruwe")
AP_COLS = ", a.mass_flame, a.radius_flame, a.radius_gspphot, a.logg_gspphot, a.teff_gspphot"
FROM = ("FROM gaiadr3.nss_two_body_orbit AS o JOIN gaiadr3.gaia_source AS s "
        "ON s.source_id = o.source_id")
AP_JOIN = (" LEFT OUTER JOIN gaiadr3.astrophysical_parameters AS a "
           "ON a.source_id = o.source_id")


def query_sample(p_edges=(1, 1.5, 2, 3, 5, 8, 13)):
    rows = []
    for lo, hi in zip(p_edges[:-1], p_edges[1:]):
        where = ("WHERE o.nss_solution_type IN ('SB1','SB1C') AND o.period >= %g AND "
                 "o.period < %g AND s.phot_g_mean_mag <= %g AND o.semi_amplitude_primary*"
                 "o.semi_amplitude_primary*o.semi_amplitude_primary*o.period < %g"
                 % (lo, hi, G_MAX, KP_SERVER_MAX))
        try:
            part = tap_query("SELECT " + COLS + AP_COLS + " " + FROM + AP_JOIN + " " + where)
        except RuntimeError as exc:
            log("with astrophysical_parameters failed, retrying without:", exc)
            part = tap_query("SELECT " + COLS + " " + FROM + " " + where)
        log("Gaia P %g-%g: %d rows" % (lo, hi, len(part)))
        rows.extend(part)
    return rows


def query_ids(ids):
    where = "WHERE o.source_id IN (%s) AND o.nss_solution_type IN ('SB1','SB1C')" % ",".join(ids)
    try:
        return tap_query("SELECT " + COLS + AP_COLS + " " + FROM + AP_JOIN + " " + where)
    except RuntimeError:
        return tap_query("SELECT " + COLS + " " + FROM + " " + where)


def fetch_text(url, timeout=120):
    import requests
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=timeout)
            if r.ok:
                return r.text
        except Exception as exc:
            log("fetch retry", url, exc)
        time.sleep(5 * (attempt + 1))
    return None


def toi_table():
    txt = fetch_text(TOI_URL)
    if not txt:
        return None
    out = {}
    for r in csv.DictReader(io.StringIO(txt)):
        tic = str(r.get("TIC ID", "")).strip()
        if tic:
            out.setdefault(tic, []).append({"toi": r.get("TOI", ""),
                                            "disp": r.get("TFOPWG Disposition", ""),
                                            "period": r.get("Period (days)", "")})
    return out


# ================================================================ one star
def light_curves(row, tmp, max_sectors):
    """Up to max_sectors TESS products, one per sector (SPOC 120 s > TESS-SPOC > QLP,
    most recent sectors first). Returns (tic, [(sector, author, t, f)], n_sectors)."""
    import numpy as np
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    import lightkurve as lk
    import vet_event as ve
    coord = SkyCoord(fval(row, "ra"), fval(row, "dec"), unit="deg")
    sr = None
    for attempt in range(3):
        try:
            sr = lk.search_lightcurve(coord, radius=5 * u.arcsec, mission="TESS")
            break
        except Exception as exc:
            log("search retry", attempt, exc)
            time.sleep(5 * (attempt + 1))
    if sr is None or len(sr) == 0:
        return "", [], 0
    tab = sr.table
    cand = []
    for i in range(len(sr)):
        au = str(tab["author"][i])
        if au not in AUTHORS:
            continue
        try:
            ex = float(tab["exptime"][i]) if "exptime" in tab.colnames else float("nan")
        except (TypeError, ValueError):
            ex = float("nan")
        if au == "SPOC" and ex < 100:
            continue
        try:
            dist = float(tab["distance"][i]) if "distance" in tab.colnames else 0.0
        except (TypeError, ValueError):
            dist = 0.0
        tn = str(tab["target_name"][i]).strip().lstrip("0") if "target_name" in tab.colnames else ""
        cand.append((i, au, ex, dist, tn, ve.sector_of(tab, i)))
    if not cand:
        return "", [], 0
    tic = min(cand, key=lambda c: c[3])[4]
    cand = [c for c in cand if c[4] == tic]
    rank = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}
    best = {}
    for c in cand:
        if c[5] is None:
            continue
        if c[5] not in best or rank[c[1]] < rank[best[c[5]][1]]:
            best[c[5]] = c
    order = sorted(best.values(), key=lambda c: (rank[c[1]], -c[5]))
    out = []
    for c in order:
        if len(out) >= max_sectors:
            break
        try:
            lc = sr[c[0]].download(download_dir=tmp, quality_bitmask="default")
        except Exception as exc:
            log("download failed", tic, c[5], exc)
            continue
        if lc is None:
            continue
        t = np.asarray(getattr(lc.time, "value", lc.time), float)
        f = ve._col(lc, ["pdcsap_flux", "kspsap_flux", "flux"])
        if f is None:
            continue
        t, f, _ = ve.clean(t, f)
        if t.size > 100:
            out.append((c[5], c[1], t, f))
    return tic, out, len(best)


def evaluate_star(sectors_meas, phys, eph):
    """Star-level results from the per-sector measurements (pure bookkeeping)."""
    n = len(sectors_meas)
    hits = [m for m in sectors_meas if m["hit"]]
    res = {"n_sectors_used": n, "n_sectors_hit": len(hits), "star_hit": len(hits) >= 1}
    n_inj = N_INJ
    found = 0
    for j in range(n_inj):
        if any(m["inj"][j]["found"] for m in sectors_meas if len(m["inj"]) > j):
            found += 1
    res["sensitivity"] = found / float(n_inj) if n else 0.0
    for c in CONTROL_RATIOS:
        ch = [m["controls"][str(c)] for m in sectors_meas if m["controls"][str(c)]["hit"]]
        res["ctrl_%s_hit" % c] = bool(ch)
        if ch:
            cb = max(ch, key=lambda x: x["res"]["snr"])
            res["ctrl_%s_class" % c] = classify_hit(cb["res"]["depth"], phys["depth_exp"],
                                                    cb["mod_amp"])
        else:
            res["ctrl_%s_class" % c] = ""
    if hits:
        best = max(hits, key=lambda m: m["real"]["snr"])
        rb = best["real"]
        res.update({"depth_obs": rb["depth"], "snr_best": rb["snr"], "n_ep_best": rb["n_ep"],
                    "local_ratio_best": rb["local_ratio"], "snr_drop1_best": rb["snr_drop1"],
                    "best_sector": best.get("sector"), "mod_amp": best["mod_amp"]})
        P = eph["P"]
        grid_sd = rb.get("box_d", 0.0) / 4.0       # phase-grid resolution, added in quadrature
        k = int(round((rb["t_found"] - eph["t0"]) / P))
        s1 = math.hypot(sigma_k(eph["v1"], k), grid_sd)
        off, z, lab = phase_check(rb["t_found"], eph["t0"] + k * P, s1, P)
        k2 = int(round((rb["t_found"] - eph["t2"]) / P))
        s2 = math.hypot(sigma_k(eph["v2"], k2), grid_sd)
        off2, z2, lab2 = phase_check(rb["t_found"], eph["t2"] + k2 * P, s2, P)
        res.update({"phase_offset_d": off, "phase_z": z, "phase_label": lab,
                    "sigma_pred_d": s1, "sec_offset_d": off2, "sec_z": z2, "sec_label": lab2})
        res["hit_class"] = classify_hit(rb["depth"], phys["depth_exp"], best["mod_amp"])
    else:
        res["hit_class"] = ""
    return res


def process_star(row, phys, args, rng, plt, plot_dir, control_label=""):
    sid = str(row["source_id"]).strip()
    rec = {"source_id": sid, "control": control_label, "status": "",
           "solution": str(row.get("nss_solution_type", "")).strip(),
           "G": fval(row, "phot_g_mean_mag"), "bp_rp": fval(row, "bp_rp"),
           "ruwe": fval(row, "ruwe"), "significance": fval(row, "significance"),
           "ra": fval(row, "ra"), "dec": fval(row, "dec")}
    rec.update(phys)
    eph = sample_ephemeris(row, args.mc, rng)
    rec.update({"t0_btjd": eph["t0"], "t2_btjd": eph["t2"], "used_corr": eph["used_corr"],
                "sigma_t0_btjd2500": sigma_k(eph["v1"], int(round((2500.0 - eph["t0"]) / eph["P"])))})
    t14 = max(phys["t14_d"], 1.0 / 24.0)
    tmp = tempfile.mkdtemp(prefix="sb1_", dir=args.tmp_dir)
    sec_rows = []
    try:
        tic, lcs, n_av = light_curves(row, tmp, args.max_sectors)
        rec.update({"tic": tic, "n_sectors_available": n_av})
        if not tic:
            rec["status"] = "NO_TESS"
            return rec, []
        if not lcs:
            rec["status"] = "NO_USABLE_LC"
            return rec, []
        depth_inj = INJ_DEPTH_FACTOR * phys["depth_exp"]
        meas = []
        for sec, au, t, f in lcs:
            m = measure_sector(t, f, phys["P"], t14, depth_inj, rng)
            m["sector"], m["author"] = sec, au
            meas.append(m)
            rr = m["real"] or {}
            sec_rows.append({"source_id": sid, "tic": tic, "sector": sec, "author": au,
                             "n_bins": m["n_bins"], "hit": m["hit"], "mod_amp": m["mod_amp"],
                             **{"real_" + k: v for k, v in rr.items()},
                             **{"ctrl_%s_hit" % c: m["controls"][str(c)]["hit"] for c in CONTROL_RATIOS},
                             "inj_found": sum(1 for x in m["inj"] if x["found"])})
            if plt is not None and (m["hit"] or control_label):
                plot_fold(plt, plot_dir, sid, sec, t, f, phys["P"], t14, m, control_label)
        rec.update(evaluate_star(meas, phys, eph))
        rec["status"] = "OK"
        return rec, sec_rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def plot_fold(plt, plot_dir, sid, sec, t, f, P, t14, m, label=""):
    import numpy as np
    D = box_width(t14)
    bt, r, _ = detrend(t, f, D)
    rr = m["real"]
    if rr is None or bt.size == 0:
        return
    tref = float(np.min(t))
    ph = ((bt - tref) / P - rr["phase"] + 0.5) % 1.0 - 0.5
    fig, axs = plt.subplots(1, 2, figsize=(10, 3))
    axs[0].plot(ph, r, ".", ms=2, color="k")
    axs[0].axvspan(-D / P / 2, D / P / 2, color="orange", alpha=0.3)
    axs[0].set_xlabel("phase at Gaia P (best box at 0)")
    z = np.abs(ph * P) < 3 * D
    axs[1].plot(ph[z] * P * 24, r[z], ".", ms=3, color="k")
    axs[1].set_xlabel("hours from box centre")
    fig.suptitle("Gaia DR3 %s s%s P=%.4f d SNR %.1f depth %.0f ppm %s %s" % (
        sid, sec, P, rr["snr"], rr["depth"] * 1e6, "HIT" if m["hit"] else "", label), fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(plot_dir, "%s_s%s.png" % (sid, sec)), dpi=80)
    plt.close(fig)


# ================================================================ summary and grades
def rate_summary(recs):
    S = [r for r in recs if r.get("status") == "OK" and not r.get("control")
         and r.get("sensitivity", 0) >= SENS_MIN]
    n_hit = sum(1 for r in S if r.get("star_hit"))
    n_hit_cons = sum(1 for r in S if r.get("star_hit") and r.get("hit_class") == "SUBSTELLAR_SIZE")
    fa_all, fa_cons = 0.0, 0.0
    for r in S:
        vals = [bool(r.get("ctrl_%s_hit" % c)) for c in CONTROL_RATIOS]
        fa_all += sum(vals) / float(len(vals))
        cons = [r.get("ctrl_%s_class" % c) == "SUBSTELLAR_SIZE" for c in CONTROL_RATIOS]
        fa_cons += sum(cons) / float(len(cons))
    E = sum(r["p_transit"] * r["sensitivity"] for r in S)
    out = {"n_rate_sample": len(S), "n_hit": n_hit, "n_hit_substellar_size": n_hit_cons,
           "n_control_hits_expected": fa_all, "n_control_hits_substellar_size": fa_cons,
           "expected_if_all_real": E,
           "control_rate": fa_all / len(S) if S else float("nan"),
           "n_phase_match": sum(1 for r in S if r.get("star_hit") and r.get("phase_label") == "PHASE_MATCH"),
           "n_phase_mismatch": sum(1 for r in S if r.get("star_hit") and r.get("phase_label") == "PHASE_MISMATCH")}
    for key, n, fa in (("rho_all", n_hit, fa_all), ("rho_substellar_size", n_hit_cons, fa_cons)):
        if E > 0:
            lo, hi = garwood(n)
            out[key] = (n - fa) / E
            out[key + "_ci95"] = [max(0.0, (lo - fa) / E), max(0.0, (hi - fa) / E)]
        else:
            out[key] = float("nan")
            out[key + "_ci95"] = [float("nan"), float("nan")]
    return out


def grade(recs, summ, by_p):
    g = {}
    ctl = [r for r in recs if r.get("control") and r.get("status") == "OK"]
    nh = sum(1 for r in ctl if r.get("star_hit"))
    g["C1"] = {"prediction": ">= 3 of the 4 known transiting companions (WASP-18 b, TOI-2533 b, "
               "TOI-1712 b, TOI-5427 b) hit at the Gaia period (untestable if < 3 have TESS data)",
               "value": "%d of %d with data" % (nh, len(ctl)),
               "pass": (nh >= 3) if len(ctl) >= 3 else None}
    g["C2"] = {"prediction": "control-period hit rate <= 3 % of the rate sample",
               "value": summ["control_rate"],
               "pass": bool(summ["control_rate"] <= 0.03) if summ["n_rate_sample"] else None}
    g["C3"] = {"prediction": ">= 150 stars in the rate sample (sensitivity >= 0.5) in this job",
               "value": summ["n_rate_sample"], "pass": summ["n_rate_sample"] >= 150}
    up = summ.get("rho_substellar_size_ci95", [float("nan")] * 2)[1]
    g["H1"] = {"prediction": "rho (substellar-size hits) upper 95 % bound < 0.5: most DR3 low-mass SB1 "
               "orbits at P = 1-13 d do not show the transits a real low-mass companion must give",
               "value": up, "pass": bool(up < 0.5) if math.isfinite(up) else None}
    a, b = by_p.get("P<5", {}).get("rho_all"), by_p.get("P>=5", {}).get("rho_all")
    ok = a is not None and b is not None and math.isfinite(a) and math.isfinite(b)
    g["H2"] = {"prediction": "(exploratory) rho_all at P >= 5 d exceeds rho_all at P < 5 d",
               "value": [a, b], "pass": bool(b > a) if ok else None}
    hits = [r for r in recs if r.get("star_hit") and not r.get("control")]
    timed = [r for r in hits if r.get("phase_label") in ("PHASE_MATCH", "PHASE_MISMATCH")]
    nm = sum(1 for r in timed if r["phase_label"] == "PHASE_MATCH")
    g["H3"] = {"prediction": "of the hits that Gaia still times (3 sigma < P/4), most (> 50 %) sit at "
               "the predicted transit phase (|z| < 3); unrelated dips would match < 6 sigma / P "
               "< 50 % of the time",
               "value": "%d of %d timed hits" % (nm, len(timed)),
               "pass": (nm > 0.5 * len(timed)) if timed else None}
    new = [r for r in hits if r.get("hit_class") == "SUBSTELLAR_SIZE" and not r.get("toi")]
    g["D1"] = {"prediction": "(report) substellar-size hits not on the TOI list -> vetting, not claims",
               "value": [r["source_id"] for r in new], "pass": None}
    return g


def clean_json(o):
    if isinstance(o, dict):
        return {str(k): clean_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_json(v) for v in o]
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if hasattr(o, "item"):
        return clean_json(o.item())
    return o


def write_csv(path, rows, keys=None):
    if not rows:
        open(path, "w").close()
        return
    keys = keys or sorted({k for r in rows for k in r.keys()})
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gaia DR3 low-mass SB1 orbits vs TESS transits")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tmp-dir", default=None)
    ap.add_argument("--chunk", type=int, default=0)
    ap.add_argument("--n-chunks", type=int, default=2)
    ap.add_argument("--max-sectors", type=int, default=3)
    ap.add_argument("--mc", type=int, default=400)
    ap.add_argument("--time-budget-min", type=float, default=160.0)
    ap.add_argument("--max-stars", type=int, default=100000)
    a = ap.parse_args(argv)
    t_start = time.time()
    os.makedirs(a.out_dir, exist_ok=True)
    plot_dir = os.path.join(a.out_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    if a.tmp_dir:
        os.makedirs(a.tmp_dir, exist_ok=True)
    import numpy as np
    rng = np.random.default_rng(SEED + a.chunk)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        plt = None
    toi = toi_table()
    log("TOI table TICs:", None if toi is None else len(toi))
    rows = query_sample()
    pool, why, phys_by = [], {}, {}
    for r in rows:
        ph = star_physics(r)
        ok, reason = eligible(r, ph)
        if ok:
            pool.append(r)
            phys_by[str(r["source_id"]).strip()] = ph
        else:
            why[reason] = why.get(reason, 0) + 1
    log("Gaia rows %d, eligible %d, rejected %s" % (len(rows), len(pool), why))
    elig_rows = []
    for r in pool:
        sid = str(r["source_id"]).strip()
        ph = phys_by[sid]
        elig_rows.append({"source_id": sid, "solution": r.get("nss_solution_type"),
                          "G": r.get("phot_g_mean_mag"),
                          **{k: ph[k] for k in ("P", "K", "e", "m1", "r1", "m2sini", "p_transit",
                                                "t14_d", "depth_exp")}})
    write_csv(os.path.join(a.out_dir, "sb1_eligible.csv"), elig_rows)
    by_id = {str(r["source_id"]).strip(): r for r in pool}
    order = chunk_order(list(by_id.keys()), a.n_chunks, a.chunk)
    recs, sec_rows = [], []
    try:
        ctl_rows = query_ids(list(POSITIVE_CONTROLS.keys()))
    except RuntimeError as exc:
        log("control query failed", exc)
        ctl_rows = []
    todo = [(r, POSITIVE_CONTROLS.get(str(r["source_id"]).strip(), "control")) for r in ctl_rows]
    todo += [(by_id[s], "") for s in order]
    n_done = 0
    for r, label in todo:
        if not label and ((time.time() - t_start) / 60.0 > a.time_budget_min or n_done >= a.max_stars):
            break
        sid = str(r["source_id"]).strip()
        try:
            rec, srows = process_star(r, phys_by.get(sid) or star_physics(r), a, rng, plt,
                                      plot_dir, control_label=label)
        except Exception as exc:
            traceback.print_exc()
            rec, srows = {"source_id": sid, "control": label, "status": "ERROR %r" % exc}, []
        tic = rec.get("tic", "")
        if toi is not None and tic:
            rec["toi"] = ";".join("%s(%s)" % (x["toi"], x["disp"]) for x in toi.get(tic, []))
        recs.append(rec)
        sec_rows.extend(srows)
        if label:
            log("CONTROL", sid, label, rec.get("status"), "hit", rec.get("star_hit"),
                "sens", rec.get("sensitivity"), rec.get("phase_label"))
            continue
        n_done += 1
        if rec.get("star_hit"):
            log("HIT", sid, "P=%.3f" % rec["P"], "tic", tic, rec.get("hit_class"),
                rec.get("phase_label"), rec.get("toi", ""))
        if n_done % 25 == 0:
            log("done %d stars, %.1f min" % (n_done, (time.time() - t_start) / 60.0))
    summ = rate_summary(recs)
    by_p = {"P<5": rate_summary([r for r in recs if (r.get("P") or 0) < 5]),
            "P>=5": rate_summary([r for r in recs if (r.get("P") or 0) >= 5])}
    by_class = {c: rate_summary([r for r in recs if r.get("m2_class") == c]) for c in ("BD", "VLMS")}
    grades = grade(recs, summ, by_p)
    status_counts = {}
    for r in recs:
        if not r.get("control"):
            s = str(r.get("status", "")).split(" ")[0]
            status_counts[s] = status_counts.get(s, 0) + 1
    keep = ("source_id", "tic", "toi", "P", "K", "e", "m1", "r1", "m2sini", "m2_class",
            "p_transit", "depth_exp", "depth_obs", "snr_best", "hit_class", "phase_label",
            "phase_z", "sigma_pred_d", "sec_label", "G", "ruwe", "sensitivity",
            "n_sectors_used", "n_sectors_hit", "mod_amp", "control", "status")
    out = {"version": VERSION, "args": vars(a), "gaia_rows": len(rows), "eligible": len(pool),
           "rejected": why, "stars_processed": n_done, "status_counts": status_counts,
           "summary": summ, "by_period": by_p, "by_class": by_class, "grades": grades,
           "controls": [{k: r.get(k) for k in keep} for r in recs if r.get("control")],
           "hits": [{k: r.get(k) for k in keep} for r in recs
                    if r.get("star_hit") and not r.get("control")],
           "minutes": (time.time() - t_start) / 60.0}
    out = clean_json(out)
    with open(os.path.join(a.out_dir, "sb1_summary.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    write_csv(os.path.join(a.out_dir, "sb1_stars.csv"), recs)
    write_csv(os.path.join(a.out_dir, "sb1_sectors.csv"), sec_rows)
    with open(os.path.join(a.out_dir, "sb1_report.md"), "w") as fh:
        fh.write("# sb1_transit %s, chunk %d of %d\n\n" % (VERSION, a.chunk, a.n_chunks))
        fh.write("Stars processed: %d (eligible %d). Status: %s\n\n" % (n_done, len(pool), status_counts))
        fh.write("Summary: %s\n\nBy period: %s\n\nBy class: %s\n\n" % (
            json.dumps(out["summary"]), json.dumps(out["by_period"]), json.dumps(out["by_class"])))
        for k, v in out["grades"].items():
            fh.write("- **%s** %s: value %s, pass %s\n" % (k, v["prediction"], v["value"], v["pass"]))
        fh.write("\n## Controls\n\n")
        for h in out["controls"]:
            fh.write("- %s\n" % json.dumps(h))
        fh.write("\n## Hits\n\n")
        for h in out["hits"]:
            fh.write("- %s\n" % json.dumps(h))
    print(json.dumps({"version": VERSION, "summary": out["summary"],
                      "grades": {k: v["pass"] for k, v in grades.items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
