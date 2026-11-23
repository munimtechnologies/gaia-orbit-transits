#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# pws_amend_011.py -- pixel_which_star amendment 0.1.1: non-negative star fluxes and merged
# close stars in the mean-image PSF fit. By MV2 of Munim, Inc.; made with AI agents working in
# his name. License: Apache-2.0.
# Rules: findings/2026-11-23-pixel-which-star-amendment-1.md (written before this job ran).
#
# Imports pixel_which_star 0.1.0 (commit bfbff5f27e523478c5be9f6ee1cc0905f0fb644a) and
# tyc_pixel 0.1.0 (commit c16e7a2a6a13cce476f73153483cc59ad8443362) unchanged and replaces ONE
# function, tyc_pixel.fit_mean_image, with fit_mean_image_011 below. Everything else (windows,
# difference images, controls C1-C4, centroids, labels, thresholds) is the pinned 0.1.0 code.
#
# What changes and why (job tic93622019-pixel-v1, 22 Nov 2026):
#  M1  A star within MERGE_PX (0.6 px, the 0.1.0 constant) of a free star is merged into that
#      star's PSF column, weighted by Gaia RP flux. In 0.1.0 such a star went into the shared
#      faint-group column; for HATS-58 A (companion 0.74 arcsec away, nearly as bright) that column
#      sat on the target and the two traded flux (target flux -1385 and -233 e/s).
#  M2  Star and faint-group fluxes are constrained to be >= 0 (Lawson-Hanson NNLS on the normal
#      equations), both inside the PSF-shape search and in the final solve. Background terms
#      stay free. In 0.1.0 TIC 93622019's neighbour (RP 13.49, 2 px away) came out at -520 to
#      +963 e/s across six sectors.
#  M3  If the neighbour's flux is pinned at 0 by M2 while the target's is positive, the
#      neighbour flux used to turn amplitudes into fractional depths (and to scale the C2
#      injection) is the target flux times the Gaia RP flux ratio of the two merged groups.
#      Flagged N_FLUX_GAIA_TIED. A target pinned at 0 still ends as NEGATIVE_FLUX.
"""Usage:
  python pws_amend_011.py --self-test
  python pws_amend_011.py --config targets.json --data-dir /data/pws --out-dir /out
Exit codes as pixel_which_star 0.1.0 (0 ok; 3 self-test failed; 4 main target not fetched);
5 = pinned module versions do not match.
"""
import json
import math
import random
import sys

import tyc_pixel as tp
import pixel_which_star as pws

VERSION = "0.1.1"
PINNED_PWS = "0.1.0"
PINNED_TP = "0.1.0"
MERGE_PX = 0.6
GTOL = 1e-10          # relative tolerance on the NNLS gradient
_LAST = {}            # flags of the latest mean-image fit (attached to the sector output)
_ORIG = {}


# ---------------------------------------------------------------- NNLS
def nnls_normal(A, b, cons, max_iter=None):
    """Minimise 0.5 x'Ax - b'x with x_k >= 0 for k in `cons` (other entries free).
    Lawson-Hanson active set on the normal equations; A symmetric positive definite.
    Raises ValueError if a sub-problem is singular."""
    K = len(b)
    cons = set(cons)
    passive = set(range(K)) - cons
    scale = max([abs(v) for v in b] + [1e-300])
    gtol = GTOL * scale

    def sub(P):
        idx = sorted(P)
        z = [0.0] * K
        if idx:
            sol = tp.solve([[A[i][j] for j in idx] for i in idx], [b[i] for i in idx])
            for i, v in zip(idx, sol):
                z[i] = v
        return z

    x = sub(passive)
    if max_iter is None:
        max_iter = 3 * K + 30
    for _ in range(max_iter):
        grad = [b[k] - sum(A[k][j] * x[j] for j in range(K)) for k in range(K)]
        cand = [k for k in cons if k not in passive and grad[k] > gtol]
        if not cand:
            break
        passive.add(max(cand, key=lambda k: grad[k]))
        for _inner in range(K + 5):
            z = sub(passive)
            neg = [k for k in passive if k in cons and z[k] < 0.0]
            if not neg:
                x = z
                break
            kmin = min(neg, key=lambda k: x[k] / (x[k] - z[k]))
            alpha = x[kmin] / (x[kmin] - z[kmin])
            x = [xi + alpha * (zi - xi) for xi, zi in zip(x, z)]
            x[kmin] = 0.0
            for k in list(passive):
                if k in cons and x[k] <= 0.0:
                    passive.discard(k)
                    x[k] = 0.0
    return [max(v, 0.0) if k in cons else v for k, v in enumerate(x)]


def lstsq_nn(cols, y, w, cons, ridge=1e-12):
    """tyc_pixel.lstsq with coefficients in `cons` constrained to be >= 0."""
    K = len(cols)
    wc = [[wi * ci for wi, ci in zip(w, c)] for c in cols]
    A = [[0.0] * K for _ in range(K)]
    bv = [0.0] * K
    for k in range(K):
        wk = wc[k]
        bv[k] = sum(a * b for a, b in zip(wk, y))
        for m in range(k, K):
            v = sum(a * b for a, b in zip(wk, cols[m]))
            A[k][m] = v
            A[m][k] = v
    tr = sum(A[k][k] for k in range(K)) / max(K, 1)
    for k in range(K):
        A[k][k] += ridge * tr
    coef = nnls_normal(A, bv, cons)
    model = [0.0] * len(y)
    for k in range(K):
        ck = coef[k]
        if ck:
            model = [m + ck * c for m, c in zip(model, cols[k])]
    chi2 = sum(wi * (yi - mi) ** 2 for wi, yi, mi in zip(w, y, model))
    return coef, chi2


# ---------------------------------------------------------------- stars and columns
def split_groups(stars, merge_px=MERGE_PX):
    """Primaries (T, N, then every star with RP < FREE_RP farther than merge_px from all
    earlier primaries, brightest first), the stars merged into each primary, and the faint
    group (RP < FAINT_RP, not merged)."""
    prim = [s for s in stars if s.get("role") in ("T", "N")]
    prim.sort(key=lambda s: 0 if s["role"] == "T" else 1)
    groups = [[s] for s in prim]
    rest = sorted([s for s in stars if s.get("role") not in ("T", "N")], key=lambda s: s["rp"])
    faint = []
    for s in rest:
        best, bd = None, None
        for k, p in enumerate(prim):
            d = math.hypot(s["x"] - p["x"], s["y"] - p["y"])
            if d <= merge_px and (bd is None or d < bd):
                best, bd = k, d
        if best is not None:
            groups[best].append(s)
        elif s["rp"] < tp.FREE_RP:
            prim.append(s)
            groups.append([s])
        elif s["rp"] < tp.FAINT_RP:
            faint.append(s)
    return prim, groups, faint


def group_weights(group):
    rp0 = group[0]["rp"]
    ws = [10.0 ** (-0.4 * (s["rp"] - rp0)) for s in group]
    tot = sum(ws)
    return [v / tot for v in ws]


def group_flux_rel(group):
    """Total Gaia RP flux of a group, relative to RP = 0."""
    return sum(10.0 ** (-0.4 * s["rp"]) for s in group)


def design_011(groups, faint, par, dx, dy, ny, nx):
    cols = []
    for g in groups:
        col = [0.0] * (ny * nx)
        for s, wgt in zip(g, group_weights(g)):
            t = tp.psf_template(s["x"] + dx, s["y"] + dy, ny, nx, par)
            col = [a + wgt * v for a, v in zip(col, t)]
        cols.append(col)
    if faint:
        rp0 = min(s["rp"] for s in faint)
        fc = [0.0] * (ny * nx)
        for s in faint:
            wgt = 10.0 ** (-0.4 * (s["rp"] - rp0))
            t = tp.psf_template(s["x"] + dx, s["y"] + dy, ny, nx, par)
            fc = [a + wgt * v for a, v in zip(fc, t)]
        cols.append(fc)
    return cols + tp.bkg_cols(ny, nx)


def tie_neighbour(coef, groups, k_t, k_n):
    """M3. Returns (coef copy, source label)."""
    c = list(coef)
    if c[k_t] > 0 and c[k_n] <= 0:
        c[k_n] = c[k_t] * group_flux_rel(groups[k_n]) / group_flux_rel(groups[k_t])
        return c, "N_FLUX_GAIA_TIED"
    return c, "N_FLUX_FIT"


# ---------------------------------------------------------------- the replacement fit
def fit_mean_image_011(M, stars, ny, nx, maxiter=500, log=print):
    prim, groups, faint = split_groups(stars)
    w = tp.pixel_weights(M)
    n_star_cols = len(prim) + (1 if faint else 0)
    cons = list(range(n_star_cols))

    def f(p):
        dx, dy, sx, sy, rho, h = p
        if not (abs(dx) <= 1.5 and abs(dy) <= 1.5 and tp.par_ok((sx, sy, rho, h))):
            return 1e300
        try:
            _, chi2 = lstsq_nn(design_011(groups, faint, (sx, sy, rho, h), dx, dy, ny, nx),
                               M, w, cons)
        except ValueError:
            return 1e300
        return chi2

    x0 = [0.0, 0.0, 0.8, 0.8, 0.0, 0.15]
    best, val, it1 = tp.nelder_mead(f, x0, [0.3, 0.3, 0.2, 0.2, 0.2, 0.1], maxiter=maxiter)
    best, val, it2 = tp.nelder_mead(f, best, [0.1, 0.1, 0.05, 0.05, 0.05, 0.03], maxiter=maxiter)
    dx, dy, sx, sy, rho, h = best
    par = (sx, sy, rho, h)
    cols = design_011(groups, faint, par, dx, dy, ny, nx)
    coef_fit, chi2 = lstsq_nn(cols, M, w, cons)
    k_t = [k for k, s in enumerate(prim) if s["role"] == "T"][0]
    k_ns = [k for k, s in enumerate(prim) if s["role"] == "N"]
    if k_ns:
        coef, src = tie_neighbour(coef_fit, groups, k_t, k_ns[0])
    else:
        coef, src = list(coef_fit), "NO_NEIGHBOUR"
    pinned = [prim[k]["id"] for k in range(len(prim)) if coef_fit[k] <= 0.0]
    _LAST.clear()
    _LAST.update({
        "version": VERSION, "n_flux_source": src,
        "flux_target_fit": coef_fit[k_t],
        "flux_neighbour_fit": coef_fit[k_ns[0]] if k_ns else None,
        "faint_coef": coef_fit[len(prim)] if faint else None,
        "merged_into_target": [s["id"] for s in groups[k_t][1:]],
        "merged_into_neighbour": [s["id"] for s in groups[k_ns[0]][1:]] if k_ns else [],
        "n_merged_total": sum(len(g) - 1 for g in groups),
        "n_pinned_at_zero": len(pinned), "pinned_ids": pinned[:20],
        "chi2": chi2, "n_pix": len(M)})
    log("[mean011] dx %.3f dy %.3f sx %.3f sy %.3f rho %.3f h %.3f chi2 %.4g (it %d+%d) "
        "f_t %.1f f_n %.1f (%s) merged %d pinned %d" % (
            dx, dy, sx, sy, rho, h, chi2, it1, it2, coef[k_t],
            coef[k_ns[0]] if k_ns else float("nan"), src, _LAST["n_merged_total"], len(pinned)))
    fluxes = {s["id"]: coef[k] for k, s in enumerate(prim)}
    return {"dx": dx, "dy": dy, "par": par, "chi2": chi2, "fluxes": fluxes, "coef": coef,
            "free": prim, "faint": faint, "cols": cols, "w": w, "n_free": len(prim),
            "n_faint": len(faint), "groups": [[s["id"] for s in g] for g in groups]}


def analyse_sector_011(*a, **k):
    _LAST.clear()
    out, extra = _ORIG["analyse_sector"](*a, **k)
    if _LAST:
        out["fit_011"] = dict(_LAST)
    return out, extra


def install():
    if pws.VERSION not in (PINNED_PWS, VERSION) or tp.VERSION != PINNED_TP:
        raise RuntimeError("pinned versions differ: pixel_which_star %s, tyc_pixel %s" % (
            pws.VERSION, tp.VERSION))
    if "analyse_sector" not in _ORIG:
        _ORIG["analyse_sector"] = pws.analyse_sector
        _ORIG["fit_mean_image"] = tp.fit_mean_image
    tp.fit_mean_image = fit_mean_image_011
    pws.analyse_sector = analyse_sector_011
    pws.VERSION = VERSION


# ---------------------------------------------------------------- self-test
PAR_TRUE = (0.75, 0.68, 0.1, 0.1)


def synth_mean(stars_truth, seed, ny=11, nx=11, bkg=50.0, noise=True):
    rng = random.Random(seed)
    img = [bkg] * (ny * nx)
    for x, y, flux in stars_truth:
        t = tp.psf_template(x, y, ny, nx, PAR_TRUE)
        img = [a + flux * v for a, v in zip(img, t)]
    if noise:
        img = [v + rng.gauss(0.0, math.sqrt(max(v, 1.0))) for v in img]
    return img


def mk(sid, rp, x, y, role="other"):
    return {"id": sid, "rp": rp, "x": x, "y": y, "role": role, "g": rp + 0.4}


def self_test_own(log=print):
    q = lambda s: None  # noqa: E731
    checks = {}
    # 1. NNLS against a brute-force check on a 3-variable problem with a negative LS answer
    G = [[1.0, 0.9, 0.0], [0.0, 0.4, 1.0], [1.0, 1.0, 1.0], [0.2, 0.0, 0.3]]
    y = [1.0, -0.5, 0.3, 0.1]
    A = [[sum(G[r][i] * G[r][j] for r in range(4)) for j in range(3)] for i in range(3)]
    b = [sum(G[r][i] * y[r] for r in range(4)) for i in range(3)]
    x = nnls_normal(A, b, [0, 1, 2])

    def obj(v):
        return sum((sum(G[r][i] * v[i] for i in range(3)) - y[r]) ** 2 for r in range(4))
    grid_best = min((obj([i * 0.01, j * 0.01, k * 0.01]), (i, j, k))
                    for i in range(0, 121, 2) for j in range(0, 121, 2) for k in range(0, 61, 2))
    checks["nnls_nonneg"] = all(v >= 0 for v in x)
    checks["nnls_optimal"] = obj(x) <= grid_best[0] + 1e-9
    # 2. close companion (HATS-58 A-like): T + C 0.03 px apart, N 1.9 px away
    truth = [(5.1, 5.2, 100000.0), (5.13, 5.21, 80000.0), (7.0, 5.4, 30000.0),
             (2.0, 8.0, 150000.0), (8.5, 1.5, 4000.0)]
    M = synth_mean(truth, 7)
    stars = [mk("T", 10.0, 5.1, 5.2, "T"), mk("C", 10.2423, 5.13, 5.21),
             mk("N", 11.3077, 7.0, 5.4, "N"), mk("b", 9.5598, 2.0, 8.0),
             mk("f", 14.5, 8.5, 1.5)]
    mf = fit_mean_image_011(M, stars, 11, 11, maxiter=300, log=q)
    ft, fn = mf["coef"][0], mf["coef"][1]
    checks["merge_target_flux"] = abs(ft / 180000.0 - 1.0) < 0.1
    checks["merge_neighbour_flux"] = abs(fn / 30000.0 - 1.0) < 0.2
    checks["merge_flag"] = _LAST.get("merged_into_target") == ["C"]
    checks["cols_aligned"] = len(mf["cols"]) == mf["n_free"] + (1 if mf["n_faint"] else 0) + 3
    # 3. tie rule
    groups = [[mk("T", 10.0, 0, 0, "T")], [mk("N", 12.5, 2, 0, "N")]]
    c, src = tie_neighbour([1000.0, 0.0, 5.0], groups, 0, 1)
    checks["tie_value"] = src == "N_FLUX_GAIA_TIED" and abs(c[1] - 100.0) < 1e-6
    c2, src2 = tie_neighbour([1000.0, 50.0, 5.0], groups, 0, 1)
    checks["tie_untouched"] = src2 == "N_FLUX_FIT" and c2[1] == 50.0
    ok = True
    for k, v in checks.items():
        log("[self-test 0.1.1] %-22s %s" % (k, "ok" if v else "FAIL"))
        ok = ok and bool(v)
    return ok


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        install()
    except RuntimeError as exc:
        print("VERSION_MISMATCH", exc)
        return 5
    if "--self-test" in argv:
        ok_own = self_test_own()
        ok_pws = pws.self_test()
        ok = ok_own and ok_pws
        print(json.dumps({"own": ok_own, "pixel_which_star_self_test_with_0.1.1_fit": ok_pws}))
        print("SELF_TEST_OK" if ok else "SELF_TEST_FAILED")
        return 0 if ok else 3
    return pws.main(argv)


if __name__ == "__main__":
    sys.exit(main())
