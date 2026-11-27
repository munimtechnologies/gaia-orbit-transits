# SPDX-License-Identifier: Apache-2.0
# MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name.
# https://github.com/munimtechnologies/gaia-orbit-transits
"""sb1_tess_fold 0.1.0: fold every TESS light curve of a Gaia DR3 single-lined binary on
Gaia's OWN period and conjunction times (nothing is fitted to the period or the phase) and
grade pre-registered predictions.

Pre-registration: findings/2026-11-27-sb1-tier2-prereg.md (written before any TESS data of
these stars were looked at).

Per star:
  * conjunction times from the Gaia DR3 orbit (Kepler's equation; conj0: true anomaly
    90 deg - omega, the visible star behind its companion; conj1: 270 deg - omega);
  * all TESS products (SPOC 2-min, TESS-SPOC, QLP) are joined; a least-squares model with
    one offset and slope per product plus two orbital harmonics
        cos(2 pi phi), sin(2 pi phi), cos(4 pi phi), sin(4 pi phi)
    is fitted OUTSIDE two windows of half-width w (phase) around the conjunctions;
  * residuals are binned (bin width = bin_phase); the eclipse depth at a conjunction is minus
    the lowest binned residual within +-w of it, its noise the scatter of binned residuals
    outside the windows; its time is the centre of that bin;
  * the deepest bin of the full folded signal (harmonics + residuals) is reported.
Grading labels are defined in grade_star(); thresholds come from targets.json.
"""
import argparse
import csv
import json
import math
import os
import re
import sys
import time

import numpy as np

VERSION = "0.1.0"
AUTHORS = ("SPOC", "TESS-SPOC", "QLP")
MAX_PRODUCTS = 12
GAIA_REF_BTJD = 389.0   # Gaia DR3 reference epoch 2016.0 = Gaia time 2191.5 = BTJD 389.0


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        x = float(o)
        return x if math.isfinite(x) else None
    return o


def dumps(o, **kw):
    return json.dumps(clean(o), **kw)


def fnum(v, default=float("nan")):
    try:
        x = float(str(v).strip())
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- orbit geometry

def conj_times(P, Tp, e, omega_deg):
    """BTJD of the two conjunctions from Gaia DR3 SB1 elements.
    Tp: t_periastron in days from 2016.0 (BTJD 389.0). conj0 = true anomaly 90 - omega
    (visible star behind its companion), conj1 = 270 - omega; conj1 placed in (t0, t0 + P)."""
    out = []
    for nu_deg in (90.0 - omega_deg, 270.0 - omega_deg):
        nu = math.radians(nu_deg)
        E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0),
                             math.sqrt(1.0 + e) * math.cos(nu / 2.0))
        M = E - e * math.sin(E)
        out.append(GAIA_REF_BTJD + Tp + M / (2.0 * math.pi) * P)
    t0, t1 = out
    t1 = t0 + ((t1 - t0) % P)
    return t0, t1


def phase_dist(phi, centre):
    """Signed phase distance of phi from centre, in [-0.5, 0.5)."""
    return ((np.asarray(phi, float) - centre + 0.5) % 1.0) - 0.5


def clip_high(f, nsig=5.0):
    med = np.median(f)
    mad = 1.4826 * np.median(np.abs(f - med))
    if not mad > 0:
        return np.ones(f.size, bool)
    return f < med + nsig * mad


# ---------------------------------------------------------------- analysis

def analyse(lcs, star):
    P = float(star["P"])
    t0, t1 = float(star["t_conj0"]), float(star["t_conj1"])
    phi1 = ((t1 - t0) / P) % 1.0
    w = float(star["window_phase"])
    bw = float(star["bin_phase"])
    T, F, G = [], [], []
    k = 0
    for lc in lcs:
        t, f = np.asarray(lc["t"], float), np.asarray(lc["f"], float)
        ok = clip_high(f)
        if ok.sum() < 100:
            continue
        T.append(t[ok])
        F.append(f[ok])
        G.append(np.full(int(ok.sum()), k))
        k += 1
    if k == 0:
        return {"status": "NO_DATA"}
    t, f, g = np.concatenate(T), np.concatenate(F), np.concatenate(G)
    phi = ((t - t0) / P) % 1.0
    d0 = phase_dist(phi, 0.0)
    d1 = phase_dist(phi, phi1)
    oot = (np.abs(d0) > w) & (np.abs(d1) > w)
    cols = []
    for j in range(k):
        s = (g == j).astype(float)
        tm = float(np.mean(t[g == j]))
        cols += [s, s * (t - tm) / 10.0]
    harm = [np.cos(2 * np.pi * phi), np.sin(2 * np.pi * phi),
            np.cos(4 * np.pi * phi), np.sin(4 * np.pi * phi)]
    A = np.column_stack(cols + harm)
    if oot.sum() < A.shape[1] + 20:
        return {"status": "TOO_FEW_OOT"}
    coef, _, _, _ = np.linalg.lstsq(A[oot], f[oot], rcond=None)
    resid = f - A @ coef
    r_oot = resid[oot]
    s_pt = 1.4826 * float(np.median(np.abs(r_oot - np.median(r_oot))))
    cov = np.linalg.pinv(A[oot].T @ A[oot]) * s_pt ** 2
    hc = coef[2 * k:2 * k + 4]
    he = np.sqrt(np.clip(np.diag(cov)[2 * k:2 * k + 4], 0, None))
    signal = (np.column_stack(harm) @ hc) + resid   # product trends removed, orbit kept

    nb = int(round(1.0 / bw))
    edges = np.linspace(0.0, 1.0, nb + 1)
    idx = np.clip(np.digitize(phi, edges) - 1, 0, nb - 1)
    cnt = np.bincount(idx, minlength=nb)
    with np.errstate(invalid="ignore", divide="ignore"):
        rb = np.bincount(idx, weights=resid, minlength=nb) / cnt
        sb = np.bincount(idx, weights=signal, minlength=nb) / cnt
    centres = 0.5 * (edges[:-1] + edges[1:])
    good = cnt >= 5
    bd0 = phase_dist(centres, 0.0)
    bd1 = phase_dist(centres, phi1)
    boot = good & (np.abs(bd0) > w) & (np.abs(bd1) > w)
    s_bin = float(np.std(rb[boot])) if boot.sum() >= 5 else float("nan")

    def dip(bd):
        sel = good & (np.abs(bd) <= w)
        if sel.sum() < 3:
            return None
        j = np.nonzero(sel)[0][int(np.argmin(rb[sel]))]
        depth = -float(rb[j])
        return {"depth": depth, "snr": depth / s_bin if s_bin > 0 else float("nan"),
                "dt_d": float(bd[j]) * P, "phase_off": float(bd[j]), "n_in_bin": int(cnt[j])}

    e0, e1 = dip(bd0), dip(bd1)
    jd = int(np.nonzero(good)[0][int(np.argmin(sb[good]))])
    deep_phase = float(centres[jd])
    near = min(abs(float(phase_dist(deep_phase, 0.0))), abs(float(phase_dist(deep_phase, phi1))))
    ratio = (e1["depth"] / e0["depth"]) if (e0 and e1 and e0["depth"] > 0) else float("nan")
    rows = [[round(float(c), 5), int(n), float(a), float(b)]
            for c, n, a, b in zip(centres, cnt, sb, rb) if n > 0]
    return {"status": "OK", "n_products": k, "n_points": int(t.size), "phi_conj1": phi1,
            "s_point": s_pt, "s_bin": s_bin,
            "a1": float(hc[0]), "b1": float(hc[1]), "a2": float(hc[2]), "b2": float(hc[3]),
            "a1_err": float(he[0]), "b1_err": float(he[1]), "a2_err": float(he[2]),
            "b2_err": float(he[3]), "ecl0": e0, "ecl1": e1, "sec_prim_ratio": ratio,
            "deepest_phase": deep_phase, "deepest_dist_to_conj": near,
            "_rows": rows}


def tolerance_d(star, t_mid):
    n = abs(t_mid - float(star["t_conj0"])) / float(star["P"])
    return 3.0 * n * float(star["sigma_P"]) + float(star.get("tol_extra_d", 0.10))


def grade_star(r, star, t_mid):
    """Labels per the pre-registration. kind 'eb': E1-E3; kind 'ell': L1-L3; 'control': C1."""
    out = {}
    if r.get("status") != "OK":
        return {"status": r.get("status")}
    tol = tolerance_d(star, t_mid)
    out["tol_d"] = tol
    e0, e1 = r["ecl0"], r["ecl1"]

    def ecl_ok(e, min_depth):
        return bool(e and e["snr"] >= 5.0 and e["depth"] >= min_depth and abs(e["dt_d"]) <= tol)

    kind = star["kind"]
    if kind in ("eb", "control"):
        p1 = ecl_ok(e0, star.get("min_depth", 0.0))
        out["E1_primary_at_conj0"] = "PASS" if p1 else "FAIL"
        lo, hi = star.get("ratio_range", [0.0, 1.0])
        p2 = bool(e1 and e1["snr"] >= 3.0 and abs(e1["dt_d"]) <= tol
                  and lo <= r["sec_prim_ratio"] <= hi)
        out["E2_secondary_at_conj1"] = "PASS" if p2 else "FAIL"
        out["E2_ratio"] = r["sec_prim_ratio"]
        out["E3_deepest_at_a_conjunction"] = "PASS" if r["deepest_dist_to_conj"] <= 0.03 else "FAIL"
        if kind == "control":
            c1 = ecl_ok(e0, 0.0) or ecl_ok(e1, 0.0)
            out["C1_control_eclipse_on_gaia_ephemeris"] = "PASS" if c1 else "FAIL"
    if kind == "ell":
        a2, a2e = r["a2"], r["a2_err"]
        l1 = a2 < 0 and abs(a2) >= 5 * a2e and abs(a2) >= star.get("min_ell_amp", 0.0)
        out["L1_ellipsoidal_minima_at_conjunctions"] = "PASS" if l1 else "FAIL"
        l2 = r["a1"] < 0 and abs(r["a1"]) >= 3 * r["a1_err"]
        out["L2_fainter_at_conj0"] = "PASS" if l2 else "FAIL"
        ecl = bool(e0 and e0["snr"] >= 5.0 and e0["depth"] >= 0.25 * abs(a2) and abs(e0["dt_d"]) <= tol)
        out["L3_eclipse_at_conj0"] = "ECLIPSE" if ecl else "NO_ECLIPSE_DETECTED"
        out["L3_depth_over_ell_amp"] = (e0["depth"] / abs(a2)) if (e0 and a2 != 0) else float("nan")
    return out


# ---------------------------------------------------------------- self-test

def synth(P, t0, phi1, days, exptime, noise, seed, ecl0=0.0, ecl1=0.0, fwhm_phase=0.04,
          a1=0.0, a2=0.0, shift_d=0.0, products=2):
    rng = np.random.default_rng(seed)
    lcs = []
    for p in range(products):
        start = t0 + 0.37 + p * 400.0
        t = np.arange(start, start + days, exptime / 86400.0)
        phi = ((t - t0 - shift_d) / P) % 1.0
        s = fwhm_phase / 2.3548200450309493
        f = 1.0 + a1 * np.cos(2 * np.pi * phi) + a2 * np.cos(4 * np.pi * phi)
        f -= ecl0 * np.exp(-0.5 * (phase_dist(phi, 0.0) / s) ** 2)
        f -= ecl1 * np.exp(-0.5 * (phase_dist(phi, phi1) / s) ** 2)
        f *= 1.0 + 0.001 * p + 0.0005 * (t - t.mean()) / days
        f += rng.normal(0, noise, t.size)
        lcs.append({"t": t, "f": f / np.median(f), "sector": p, "author": "SYN", "exptime": exptime})
    return lcs


def self_test():
    checks = {}
    P, t0 = 3.36, 1000.0
    base = {"P": P, "t_conj0": t0, "t_conj1": t0 + 0.49 * P, "sigma_P": 0.0, "tol_extra_d": 0.05,
            "window_phase": 0.12, "bin_phase": 0.005}
    eb = dict(base, kind="eb", min_depth=0.02, ratio_range=[0.1, 0.6])
    lcs = synth(P, t0, 0.49, 27.0, 600.0, 0.002, 1, ecl0=0.06, ecl1=0.015, shift_d=0.02)
    r = analyse(lcs, eb)
    g = grade_star(r, eb, t0 + 200.0)
    checks["eb"] = {"ok": g.get("E1_primary_at_conj0") == "PASS" and g.get("E2_secondary_at_conj1") == "PASS"
                    and g.get("E3_deepest_at_a_conjunction") == "PASS"
                    and abs(r["ecl0"]["dt_d"] - 0.02) <= 0.02, "grade": g,
                    "dt0": r["ecl0"]["dt_d"], "ratio": r["sec_prim_ratio"]}
    flat = synth(P, t0, 0.49, 27.0, 600.0, 0.002, 2)
    r = analyse(flat, eb)
    g = grade_star(r, eb, t0 + 200.0)
    checks["flat"] = {"ok": g.get("E1_primary_at_conj0") == "FAIL", "grade": g}
    P2 = 2.0
    ell = {"P": P2, "t_conj0": t0, "t_conj1": t0 + 0.5 * P2, "sigma_P": 0.0, "tol_extra_d": 0.05,
           "window_phase": 0.17, "bin_phase": 0.005, "kind": "ell", "min_ell_amp": 0.001}
    lcs = synth(P2, t0, 0.5, 27.0, 120.0, 0.001, 3, ecl0=0.01, a1=-0.002, a2=-0.01, fwhm_phase=0.08)
    r = analyse(lcs, ell)
    g = grade_star(r, ell, t0 + 200.0)
    checks["ell_ecl"] = {"ok": g.get("L1_ellipsoidal_minima_at_conjunctions") == "PASS"
                         and g.get("L2_fainter_at_conj0") == "PASS"
                         and g.get("L3_eclipse_at_conj0") == "ECLIPSE"
                         and abs(r["a2"] + 0.01) < 0.002, "grade": g, "a2": r["a2"]}
    lcs = synth(P2, t0, 0.5, 27.0, 120.0, 0.001, 4, a2=-0.01)
    r = analyse(lcs, ell)
    g = grade_star(r, ell, t0 + 200.0)
    checks["ell_only"] = {"ok": g.get("L3_eclipse_at_conj0") == "NO_ECLIPSE_DETECTED"
                          and g.get("L2_fainter_at_conj0") == "FAIL", "grade": g}
    ok = all(c["ok"] for c in checks.values())
    log("self-test", "PASS" if ok else "FAIL", dumps(checks))
    return ok, checks


# ---------------------------------------------------------------- data

def tess_products(tic, cache_dir, max_products=MAX_PRODUCTS):
    import lightkurve as lk
    sr = None
    for a in range(3):
        try:
            sr = lk.search_lightcurve("TIC %d" % int(tic), mission="TESS")
            break
        except Exception as exc:  # noqa: BLE001
            log("search retry", tic, repr(exc)[:160])
            time.sleep(10 * (a + 1))
    if sr is None or len(sr) == 0:
        return []
    tab = sr.table
    pick = {}
    for i in range(len(sr)):
        author = str(tab["author"][i])
        if author not in AUTHORS:
            continue
        exptime = fnum(np.asarray(tab["exptime"])[i])
        if author == "SPOC" and not (100 <= exptime <= 200):
            continue
        if not math.isfinite(exptime) or exptime <= 0:
            exptime = 600.0 if author != "SPOC" else 120.0
        m = re.search(r"(\d+)", str(tab["mission"][i]))
        if not m:
            continue
        sec = int(m.group(1))
        # one product per sector: SPOC 2-min first, then TESS-SPOC, then QLP
        if sec not in pick or AUTHORS.index(author) < AUTHORS.index(pick[sec][1]):
            pick[sec] = (i, author, exptime)
    out = []
    for sec in sorted(pick)[:max_products]:
        i, author, exptime = pick[sec]
        for a in range(3):
            try:
                lc = sr[i].download(download_dir=cache_dir, quality_bitmask="default")
                lc = lc.remove_nans()
                t = np.asarray(lc.time.value, float)
                f = np.asarray(lc.flux.value, float)
                ok = np.isfinite(t) & np.isfinite(f) & (f > 0)
                if ok.sum() >= 100:
                    out.append({"sector": sec, "author": author, "exptime": exptime,
                                "t": t[ok], "f": f[ok] / np.median(f[ok])})
                    log("TIC", tic, "sector", sec, author, exptime, int(ok.sum()), "points")
                break
            except Exception as exc:  # noqa: BLE001
                log("download retry TIC", tic, "sector", sec, repr(exc)[:160])
                time.sleep(10 * (a + 1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="targets.json")
    ap.add_argument("--data-dir", default="/data/fold")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--self-test-only", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    ok, checks = self_test()
    meta = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "self_test": "PASS" if ok else "FAIL", "self_test_checks": checks}
    if a.self_test_only:
        return 0 if ok else 3
    with open(a.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    summary = {"meta": meta, "stars": []}
    for star in cfg["stars"]:
        t0, t1 = conj_times(star["P"], star["Tp"], star["e"], star["omega_deg"])
        star = dict(star, t_conj0=t0, t_conj1=t1)
        log("star", star["name"], "TIC", star["tic"], "conj", round(t0, 5), round(t1, 5))
        lcs = tess_products(star["tic"], os.path.join(a.data_dir, "lk"))
        prods = [{"sector": lc["sector"], "author": lc["author"], "exptime": lc["exptime"],
                  "n": int(lc["t"].size), "t_min": float(lc["t"].min()), "t_max": float(lc["t"].max())}
                 for lc in lcs]
        r = analyse(lcs, star) if lcs else {"status": "NO_DATA"}
        t_mid = float(np.median(np.concatenate([lc["t"] for lc in lcs]))) if lcs else float("nan")
        g = grade_star(r, star, t_mid)
        rows = r.pop("_rows", [])
        if rows:
            fn = "fold_%s.csv" % re.sub(r"[^a-z0-9]+", "-", star["name"].lower()).strip("-")
            with open(os.path.join(a.out_dir, fn), "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["phase_from_conj0", "n", "signal_detrended", "residual"])
                w.writerows(clean(rows))
        st = {"name": star["name"], "role": star["role"], "kind": star["kind"], "tic": star["tic"],
              "gaia_dr3": star["gaia_dr3"], "t_conj0_btjd": t0, "t_conj1_btjd": t1,
              "t_mid_btjd": t_mid, "products": prods, "result": r, "grade": g}
        summary["stars"].append(st)
        log(star["name"], dumps({"grade": g, "ecl0": r.get("ecl0"), "ecl1": r.get("ecl1"),
                                 "a1": r.get("a1"), "a2": r.get("a2"), "a2_err": r.get("a2_err")}))
        with open(os.path.join(a.out_dir, "fold_summary.json"), "w", encoding="utf-8") as fh:
            fh.write(dumps(summary, indent=1))
    meta["complete"] = True
    meta["written"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(a.out_dir, "fold_summary.json"), "w", encoding="utf-8") as fh:
        fh.write(dumps(summary, indent=1))
    log("done")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
