# sb2_rvfit.py -- fit per-transit double-lined radial velocities of an eclipsing binary
# with the orbit's timing fixed by its eclipses (step g7 of gaia-orbit-transits).
#
# MV2, Munim, Inc. Made with AI agents working in his name. Apache-2.0.
#
# Pure standard library. Given epoch velocities of both stars (for example Gaia DR4
# rvs_epoch_parameters_double) and an eclipse ephemeris (TESS), it
#   * builds the Keplerian velocity curve with P, e, omega fixed and the time of
#     periastron tied to the eclipse (conjunction) time,
#   * assigns each epoch's two velocities to star 1 / star 2 (labels can swap between
#     transits), dropping epochs where the two lines are too close to separate,
#   * solves the linear least-squares problem for gamma, K1, K2,
#   * scans a time offset of the conjunction to test whether the velocities put
#     conjunction where the eclipses are, and
#   * turns K1, K2 (and an inclination from an eclipse fit) into absolute masses.
#
# Conventions: v1 = gamma + K1 [cos(nu + w) + e cos w], v2 = gamma - K2 [cos(nu + w) + e cos w],
# w = argument of periastron of star 1 (degrees in the API). Star 1 is farthest from the
# observer (behind, i.e. eclipsed) when nu + w = 90 deg.

import math

VERSION = "sb2_rvfit.py 0.1.0"

# M sin^3 i [M_sun] = MASS_CONST * (1 - e^2)^1.5 * (K1 + K2)^2 * K_other [km/s] * P [d]
MASS_CONST = 1.036149e-7
# a sin i [R_sun] = ASINI_CONST * sqrt(1 - e^2) * (K1 + K2) [km/s] * P [d]
# (86400 / 2 pi km per km/s per day, divided by the IAU 2015 nominal solar radius 695,700 km)
ASINI_CONST = 0.0197657


# ---------------------------------------------------------------- orbit geometry

def solve_kepler(M, e, tol=1e-13):
    """Eccentric anomaly E from mean anomaly M (radians), 0 <= e < 1."""
    if not 0.0 <= e < 1.0:
        raise ValueError("eccentricity must be in [0, 1)")
    M = math.fmod(M, 2.0 * math.pi)
    if M < 0:
        M += 2.0 * math.pi
    E = M if e < 0.8 else math.pi
    for _ in range(200):
        d = (E - e * math.sin(E) - M) / (1.0 - e * math.cos(E))
        E -= d
        if abs(d) < tol:
            break
    return E


def true_anomaly(t, P, e, tp):
    M = 2.0 * math.pi * (t - tp) / P
    E = solve_kepler(M, e)
    return 2.0 * math.atan2(math.sqrt(1.0 + e) * math.sin(E / 2.0),
                            math.sqrt(1.0 - e) * math.cos(E / 2.0))


def rv_shape(t, P, e, omega_deg, tp):
    """cos(nu + w) + e cos w at time t (dimensionless, star 1)."""
    w = math.radians(omega_deg)
    nu = true_anomaly(t, P, e, tp)
    return math.cos(nu + w) + e * math.cos(w)


def tperi_from_conjunction(t_conj, P, e, omega_deg, star1_behind=True):
    """Time of periastron given a conjunction time.

    star1_behind=True: at t_conj star 1 is behind star 2 (star 1 eclipsed).
    For e = 0, omega = 0 this gives tp = t_conj - P/4."""
    w = math.radians(omega_deg)
    nu = (math.pi / 2.0 - w) if star1_behind else (1.5 * math.pi - w)
    E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0),
                         math.sqrt(1.0 + e) * math.cos(nu / 2.0))
    M = E - e * math.sin(E)
    return t_conj - M / (2.0 * math.pi) * P


# ---------------------------------------------------------------- linear algebra

def _solve(A, b):
    """Solve A x = b (small dense, Gauss-Jordan with partial pivoting)."""
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-300:
            raise ValueError("singular system")
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        M[c] = [x / piv for x in M[c]]
        for r in range(n):
            if r != c and M[r][c] != 0.0:
                f = M[r][c]
                M[r] = [xr - f * xc for xr, xc in zip(M[r], M[c])]
    return [M[i][n] for i in range(n)]


def _inverse(A):
    n = len(A)
    cols = []
    for j in range(n):
        e = [0.0] * n
        e[j] = 1.0
        cols.append(_solve(A, e))
    return [[cols[j][i] for j in range(n)] for i in range(n)]


def weighted_lstsq(rows, y, sig):
    """Minimise sum(((y - rows.x)/sig)^2). Returns (x, cov, chi2)."""
    k = len(rows[0])
    N = [[0.0] * k for _ in range(k)]
    r = [0.0] * k
    for a, yy, s in zip(rows, y, sig):
        w = 1.0 / (s * s)
        for i in range(k):
            r[i] += w * a[i] * yy
            for j in range(k):
                N[i][j] += w * a[i] * a[j]
    x = _solve(N, r)
    cov = _inverse(N)
    chi2 = sum(((yy - sum(ai * xi for ai, xi in zip(a, x))) / s) ** 2
               for a, yy, s in zip(rows, y, sig))
    return x, cov, chi2


# ---------------------------------------------------------------- the fit

def _design(obs, P, e, omega_deg, tp):
    rows, y, sig = [], [], []
    for o in obs:
        f = rv_shape(o["t"], P, e, omega_deg, tp)
        if o.get("v1") is not None:
            rows.append([1.0, f, 0.0])
            y.append(o["v1"])
            sig.append(o["e1"])
        if o.get("v2") is not None:
            rows.append([1.0, 0.0, -f])
            y.append(o["v2"])
            sig.append(o["e2"])
    return rows, y, sig


def fit_fixed(obs, P, e, omega_deg, tp, err_floor=0.0):
    """Fit gamma, K1, K2 with the orbit's shape and timing fixed.

    obs: list of dicts with t, v1, e1, v2, e2 (v1 or v2 may be None).
    err_floor (km/s) is added in quadrature to every error."""
    obs2 = []
    for o in obs:
        o2 = dict(o)
        for k in ("e1", "e2"):
            if o2.get(k) is not None:
                o2[k] = math.sqrt(o2[k] ** 2 + err_floor ** 2)
        obs2.append(o2)
    rows, y, sig = _design(obs2, P, e, omega_deg, tp)
    if len(y) < 4:
        raise ValueError("need at least 4 velocities")
    x, cov, chi2 = weighted_lstsq(rows, y, sig)
    dof = len(y) - 3
    scale = math.sqrt(max(1.0, chi2 / dof)) if dof > 0 else 1.0
    return {
        "gamma": x[0], "K1": x[1], "K2": x[2],
        "gamma_err": math.sqrt(cov[0][0]) * scale,
        "K1_err": math.sqrt(cov[1][1]) * scale,
        "K2_err": math.sqrt(cov[2][2]) * scale,
        "K1_err_formal": math.sqrt(cov[1][1]), "K2_err_formal": math.sqrt(cov[2][2]),
        "chi2": chi2, "n_rv": len(y), "dof": dof, "err_scale": scale,
    }


def assign_components(pairs, P, e, omega_deg, tp, gamma, K1, K2, min_sep=20.0):
    """Assign each epoch's two velocities (va, vb) to star 1 / star 2.

    pairs: list of dicts t, va, ea, vb, eb (catalogue labels a/b).
    Epochs whose OBSERVED separation |va - vb| < min_sep km/s are dropped (lines blended,
    assignment ambiguous). Using the observed rather than the model separation keeps the
    epoch set identical across a conjunction scan, so chi2 values stay comparable.
    Returns (obs, n_swapped, n_blended)."""
    obs, n_sw, n_bl = [], 0, 0
    for p in pairs:
        if abs(p["va"] - p["vb"]) < min_sep:
            n_bl += 1
            continue
        f = rv_shape(p["t"], P, e, omega_deg, tp)
        m1 = gamma + K1 * f
        m2 = gamma - K2 * f
        keep = ((p["va"] - m1) / p["ea"]) ** 2 + ((p["vb"] - m2) / p["eb"]) ** 2
        swap = ((p["vb"] - m1) / p["eb"]) ** 2 + ((p["va"] - m2) / p["ea"]) ** 2
        if swap < keep:
            n_sw += 1
            obs.append({"t": p["t"], "v1": p["vb"], "e1": p["eb"], "v2": p["va"], "e2": p["ea"]})
        else:
            obs.append({"t": p["t"], "v1": p["va"], "e1": p["ea"], "v2": p["vb"], "e2": p["eb"]})
    return obs, n_sw, n_bl


def fit_pairs(pairs, P, e, omega_deg, tp, K1_0, K2_0, gamma_0=None, min_sep=20.0,
              err_floor=0.0, max_iter=10):
    """Iterate assignment and fit until the assignment is stable."""
    if gamma_0 is None:
        vals = sorted([p["va"] for p in pairs] + [p["vb"] for p in pairs])
        gamma_0 = vals[len(vals) // 2]
    g, k1, k2 = gamma_0, K1_0, K2_0
    prev = None
    res = None
    for it in range(max_iter):
        obs, n_sw, n_bl = assign_components(pairs, P, e, omega_deg, tp, g, k1, k2, min_sep)
        key = tuple((o["t"], o["v1"]) for o in obs)
        res = fit_fixed(obs, P, e, omega_deg, tp, err_floor)
        res.update({"n_swapped": n_sw, "n_blended": n_bl, "n_epochs_used": len(obs),
                    "iterations": it + 1})
        if key == prev:
            break
        prev = key
        g, k1, k2 = res["gamma"], abs(res["K1"]), abs(res["K2"])
    return res


def scan_conjunction(pairs, P, e, omega_deg, t_conj, K1_0, K2_0, star1_behind=True,
                     half_width_frac=0.05, n_grid=401, min_sep=20.0, err_floor=0.0):
    """Shift the conjunction time by dt over +-half_width_frac*P and refit at each step.

    Returns dict with dt_best, dt_lo, dt_hi (scaled delta-chi2 = 1 interval), dt_sigma,
    at_edge flag and the chi2 curve."""
    hw = half_width_frac * P
    curve = []
    for i in range(n_grid):
        dt = -hw + 2.0 * hw * i / (n_grid - 1)
        tp = tperi_from_conjunction(t_conj + dt, P, e, omega_deg, star1_behind)
        try:
            r = fit_pairs(pairs, P, e, omega_deg, tp, K1_0, K2_0, min_sep=min_sep,
                          err_floor=err_floor)
            curve.append((dt, r["chi2"], r["dof"]))
        except ValueError:
            curve.append((dt, float("inf"), 0))
    best = min(curve, key=lambda c: c[1])
    dt_b, chi_b, dof_b = best
    scale = max(1.0, chi_b / dof_b) if dof_b > 0 else 1.0
    lim = chi_b + scale
    inside = [c[0] for c in curve if c[1] <= lim]
    lo, hi = min(inside), max(inside)
    step = 2.0 * hw / (n_grid - 1)
    at_edge = lo <= -hw + 0.5 * step or hi >= hw - 0.5 * step
    sigma = max(0.5 * (hi - lo), 0.5 * step)
    return {"dt_best": dt_b, "dt_lo": lo, "dt_hi": hi, "dt_sigma": sigma,
            "chi2_min": chi_b, "dof": dof_b, "chi2_scale": scale, "at_edge": at_edge,
            "grid_step": step, "curve": curve}


def grade_conjunction(scan, eph_sigma=0.0, nsig=3.0):
    """CONJ_AGREES / CONJ_EARLY / CONJ_LATE / UNCONSTRAINED."""
    if scan["at_edge"]:
        return "UNCONSTRAINED"
    s = math.sqrt(scan["dt_sigma"] ** 2 + eph_sigma ** 2)
    z = scan["dt_best"] / s
    if abs(z) <= nsig:
        return "CONJ_AGREES"
    return "CONJ_EARLY" if z < 0 else "CONJ_LATE"


# ---------------------------------------------------------------- masses

def masses(K1, K1_err, K2, K2_err, P, e=0.0, inc_deg=90.0, inc_err_deg=0.0):
    """Absolute masses (M_sun) and a (R_sun) from K1, K2 (km/s), P (d), e and inclination."""
    s = math.sin(math.radians(inc_deg))
    q = (1.0 - e * e) ** 1.5
    S = K1 + K2
    m1 = MASS_CONST * q * S * S * K2 * P / s ** 3
    m2 = MASS_CONST * q * S * S * K1 * P / s ** 3
    # partial derivatives (relative)
    d1_k1 = 2.0 / S
    d1_k2 = 2.0 / S + 1.0 / K2
    d2_k1 = 2.0 / S + 1.0 / K1
    d2_k2 = 2.0 / S
    di = 3.0 / math.tan(math.radians(inc_deg)) * math.radians(inc_err_deg) if inc_err_deg else 0.0
    m1_err = m1 * math.sqrt((d1_k1 * K1_err) ** 2 + (d1_k2 * K2_err) ** 2 + di ** 2)
    m2_err = m2 * math.sqrt((d2_k1 * K1_err) ** 2 + (d2_k2 * K2_err) ** 2 + di ** 2)
    a = ASINI_CONST * math.sqrt(1.0 - e * e) * S * P / s
    return {"M1": m1, "M1_err": m1_err, "M2": m2, "M2_err": m2_err, "a_rsun": a,
            "q": K1 / K2}


# ---------------------------------------------------------------- DR4 table columns

def map_columns(names):
    """Guess time / velocity / error columns of a per-transit double-lined RV table.

    Returns dict(time, v1, e1, v2, e2, source_id) or None if not found. The job must
    still pass its controls, so a wrong guess fails loudly rather than silently."""
    low = {n.lower(): n for n in names}

    def pick(cands):
        for c in cands:
            if c in low:
                return low[c]
        return None

    def find(pred):
        hits = [n for n in names if pred(n.lower())]
        return hits[0] if len(hits) == 1 else (sorted(hits, key=len)[0] if hits else None)

    out = {"source_id": pick(["source_id"])}
    out["time"] = pick(["rv_obs_time", "obs_time", "transit_time", "rv_time", "time",
                        "epoch", "obs_time_tcb"]) or \
        find(lambda n: "time" in n and "error" not in n and "flag" not in n)

    bad = ("error", "flag", "time", "broad", "mag", "teff", "logg", "template", "snr",
           "chi", "amp", "fe_h", "method", "nb_", "n_", "_n", "number", "count", "quality")

    def is_rv(n):
        return ("radial_velocity" in n or n.startswith("rv")) and not any(b in n for b in bad)

    for k, tags in (("1", ("_1", "1", "primary", "comp1", "_a")),
                    ("2", ("_2", "2", "secondary", "comp2", "_b"))):
        v = find(lambda n, tags=tags: is_rv(n) and any(n.endswith(t) for t in tags))
        if v is None:
            v = find(lambda n, tags=tags: is_rv(n) and any(t in n for t in tags[2:]))
        out["v" + k] = v
        er = None
        if v is not None:
            vl = v.lower()
            er = pick([vl + "_error", vl + "_err", vl.replace("radial_velocity", "radial_velocity_error")])
            if er is None:
                er = find(lambda n, tags=tags: ("radial_velocity" in n or n.startswith("rv"))
                          and "error" in n and any(n.endswith(t) for t in tags))
        out["e" + k] = er
    if not all(out.get(k) for k in ("time", "v1", "e1", "v2", "e2")):
        return None
    if out["v1"] == out["v2"]:
        return None
    return out


# ---------------------------------------------------------------- self-test

def self_test(seed=7):
    """Synthetic eccentric SB2 with swapped labels, a blended epoch and a known
    conjunction offset. Returns dict with pass flag and the recovered numbers."""
    import random
    rnd = random.Random(seed)
    P, e, w = 6.9611, 0.076, 343.0
    t_conj = 1000.0
    true_dt = -0.03
    tp = tperi_from_conjunction(t_conj + true_dt, P, e, w, True)
    g, K1, K2 = 12.0, 79.8, 94.7
    pairs = []
    for i in range(60):
        t = 900.0 + 13.7 * i + rnd.random()
        f = rv_shape(t, P, e, w, tp)
        v1 = g + K1 * f + rnd.gauss(0, 2.0)
        v2 = g - K2 * f + rnd.gauss(0, 2.5)
        if i % 3 == 0:
            pairs.append({"t": t, "va": v2, "ea": 2.5, "vb": v1, "eb": 2.0})
        else:
            pairs.append({"t": t, "va": v1, "ea": 2.0, "vb": v2, "eb": 2.5})
    sc = scan_conjunction(pairs, P, e, w, t_conj, 75.0, 90.0, n_grid=241)
    tp_b = tperi_from_conjunction(t_conj + sc["dt_best"], P, e, w, True)
    fit = fit_pairs(pairs, P, e, w, tp_b, 75.0, 90.0)
    # Tolerances, not confidence intervals, so the self-test cannot fail by chance.
    ok = (abs(fit["K1"] - K1) < 4 * fit["K1_err"] + 0.5 and
          abs(fit["K2"] - K2) < 4 * fit["K2_err"] + 0.5 and
          abs(sc["dt_best"] - true_dt) < 4 * sc["dt_sigma"] + 0.005 and
          not sc["at_edge"])
    return {"pass": bool(ok), "K1": fit["K1"], "K1_err": fit["K1_err"], "K2": fit["K2"],
            "K2_err": fit["K2_err"], "dt_best": sc["dt_best"], "dt_sigma": sc["dt_sigma"],
            "grade": grade_conjunction(sc), "n_swapped": fit["n_swapped"],
            "n_blended": fit["n_blended"], "version": VERSION}


if __name__ == "__main__":
    import json
    print(json.dumps(self_test(), indent=1))
