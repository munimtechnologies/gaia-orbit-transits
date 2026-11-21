# SPDX-License-Identifier: Apache-2.0
# Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents working in his name).
"""run_search_dr4 0.1.0: run the pinned DR3 search (run_search.py 0.4.1, unchanged) on Gaia DR4.

It patches three names in run_search at run time and nothing else:
  NSS_QUERY      -> dr4_rows.DR4_NSS_QUERY (DR4 column names, cut on DR4's own inclination)
  EB_QUERY       -> dr4_rows.DR4_EB_QUERY
  read_csv_text  -> the original, then dr4_rows.convert_row on every row
and adds pre-registered gate G0 (findings/2026-11-21-dr4-astro-tess-prereg.md): when the NSS
rows are read, if under 95% of the rows that carry catalogue Thiele-Innes constants pass the
convention check, or under 50% have a usable DR4 correlation vector, it writes
dr4_adapter_gate.json and exits 4 before any TESS download.

Usage
  python run_search_dr4.py --self-test [--data-dir /data] [--out-dir /out]
      offline checks (exit 3 on failure) + the DR3 real-data round trip (R1) when DR3 rows are
      cached on the data volume or the Gaia archive answers (SKIPPED otherwise, not a failure)
  python run_search_dr4.py <run_search.py options>
      release day; --schema gaiadr4 is added when no --schema is given
"""
import argparse
import glob
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

import dr4_rows

VERSION = "0.1.0"
_STATE = {"out_dir": "/out", "summary": None}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def patch(rs):
    """Patch run_search in place (idempotent)."""
    if getattr(rs, "_dr4_patched", False):
        return rs
    orig = rs.read_csv_text

    def read_csv_text_dr4(text):
        rows = orig(text)
        if not any("semi_major_axis" in r or "corr_vec_dr4" in r for r in rows[:5]):
            return rows
        rows = [dr4_rows.convert_row(r) for r in rows]
        summ = dr4_rows.summarise(rows)
        _STATE["summary"] = summ
        os.makedirs(_STATE["out_dir"], exist_ok=True)
        with open(os.path.join(_STATE["out_dir"], "dr4_adapter_summary.json"), "w") as fh:
            json.dump(summ, fh, indent=1)
        reason = dr4_rows.gate(summ)
        if reason:
            with open(os.path.join(_STATE["out_dir"], "dr4_adapter_gate.json"), "w") as fh:
                json.dump({"gate": "G0", "stopped": True, "reason": reason, "summary": summ},
                          fh, indent=1)
            log("GATE G0 STOP:", reason)
            raise SystemExit(4)
        log("dr4 adapter:", json.dumps(summ))
        return rows

    rs._dr4_orig_read_csv_text = orig
    rs.read_csv_text = read_csv_text_dr4
    rs.NSS_QUERY = dr4_rows.DR4_NSS_QUERY
    rs.EB_QUERY = dr4_rows.DR4_EB_QUERY
    if "corr_vec_dr4" not in rs.STRING_COLS:
        rs.STRING_COLS = tuple(rs.STRING_COLS) + ("corr_vec_dr4",)
    rs._dr4_patched = True
    return rs


# ----------------------------------------------------------------------------- self-test
def _synthetic_row(kind, rng, np, a=0.9, w_deg=40.0, W_deg=120.0, i_deg=88.0, e=0.3,
                   P=180.0, Tp=-20.0, K=1.2, circular=False):
    names = dr4_rows.DR4_ORDER[kind]
    n = len(names)
    M = rng.standard_normal((n, n))
    C = M @ M.T + n * np.eye(n)
    d = np.sqrt(np.diag(C))
    R = C / np.outer(d, d)
    vals = {"ra": 10.0, "dec": -5.0, "parallax": 20.0, "pmra": 1.0, "pmdec": 2.0,
            "semi_major_axis": a, "arg_periastron": 0.0 if circular else w_deg,
            "pos_ascending_node": W_deg, "inclination": i_deg,
            "eccentricity": 0.0 if circular else e, "period": P, "t_periastron": Tp,
            "semi_amplitude_primary": K, "center_of_mass_velocity": 5.0}
    errs = {"semi_major_axis": 0.01, "arg_periastron": 0.0 if circular else 1.5,
            "pos_ascending_node": 0.8, "inclination": 0.6,
            "eccentricity": 0.0 if circular else 0.02, "period": 0.3, "t_periastron": 1.0,
            "semi_amplitude_primary": 0.05, "center_of_mass_velocity": 0.1}
    sd = np.array([errs.get(k, 0.0) for k in names])
    vec = []
    for j in range(1, n):
        for i in range(j):
            vec.append("NaN" if (sd[i] == 0 or sd[j] == 0) else repr(float(R[i, j])))
    A, B, F, G = dr4_rows.campbell_to_ti(a, vals["arg_periastron"] * dr4_rows.DEG,
                                         W_deg * dr4_rows.DEG, i_deg * dr4_rows.DEG)
    row = {"source_id": 1234567890123, "nss_solution_type":
           "Orbital" if kind == "orbital" else "AstroSpectroSB1",
           "corr_vec_dr4": "(" + ", ".join(vec) + ")",
           "a_thiele_innes": A, "b_thiele_innes": B, "f_thiele_innes": F,
           "g_thiele_innes": G, "a_thiele_innes_error": 0.01, "b_thiele_innes_error": 0.01,
           "f_thiele_innes_error": 0.01, "g_thiele_innes_error": 0.01,
           "ref_epoch": 2017.5}
    for k in names:
        row[k] = vals[k]
        row[k + "_error"] = errs.get(k, float("nan")) if errs.get(k, 0) > 0 else float("nan")
    return row, R, sd


def _to_csv(rows, keys):
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(keys)
    for r in rows:
        w.writerow(["" if (isinstance(r.get(k), float) and not math.isfinite(r.get(k)))
                    else r.get(k, "") for k in keys])
    return buf.getvalue()


def _mod_dist(x, y, P):
    return abs(((x - y) + P / 2) % P - P / 2)


def self_test(rs, go, np, out_dir):
    res = {"version": VERSION, "dr4_rows": dr4_rows.VERSION, "checks": {}}
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        res["checks"][name] = {"pass": bool(cond), "detail": detail}
        ok = ok and bool(cond)
        log("SELF-TEST", "PASS" if cond else "FAIL", name, detail)

    check("S0 dr3 order equals gaia_orbits.PARAM_ORDER",
          dr4_rows.DR3_ORDER == go.PARAM_ORDER)
    rng = np.random.default_rng(20261121)
    # S1: orbital synthetic row through the patched CSV reader
    row, R4, sd4 = _synthetic_row("orbital", rng, np)
    keys = list(row.keys())
    patch(rs)
    rows = rs.read_csv_text(_to_csv([row], keys))
    r = rows[0]
    check("S1a convention check STANDARD", r.get("dr4_ti_check") == "STANDARD",
          str(r.get("dr4_ti_check")))
    check("S1b DR4 correlation used", bool(r.get("dr4_corr_used")))
    s = go.sample_orbit(r, 20000, np.random.default_rng(1), ref_btjd=936.875)
    check("S1c sample_orbit used the converted correlation", bool(s["used_corr"]))
    cos_true = math.cos(88.0 * dr4_rows.DEG)
    check("S1d median cos i", abs(float(np.median(s["cosi"])) - cos_true) < 0.01,
          f"{float(np.median(s['cosi'])):.4f} vs {cos_true:.4f}")
    # independent Monte Carlo in Campbell space
    names = dr4_rows.DR4_ORDER["orbital"]
    mu = np.array([row[k] for k in names], float)
    Cov = R4 * np.outer(sd4, sd4)
    X = rng.multivariate_normal(mu, Cov, 20000, method="eigh")
    ia, iw, iW, ii = (names.index(k) for k in dr4_rows.CAMPBELL_KEYS)
    A_mc = np.array([dr4_rows.campbell_to_ti(x[ia], x[iw] * dr4_rows.DEG, x[iW] * dr4_rows.DEG,
                                             x[ii] * dr4_rows.DEG)[0] for x in X])
    sd_lin = float(r["a_thiele_innes_error"])
    sd_mc = float(np.std(A_mc))
    check("S1e linear sigma(A) vs Campbell Monte Carlo (10%)",
          abs(sd_lin / sd_mc - 1) < 0.10, f"{sd_lin:.5f} vs {sd_mc:.5f}")
    cos_mc = np.cos(X[:, ii] * dr4_rows.DEG)
    check("S1f sigma(cos i) vs Campbell Monte Carlo (15%)",
          abs(float(np.std(s["cosi"])) / float(np.std(cos_mc)) - 1) < 0.15,
          f"{float(np.std(s['cosi'])):.5f} vs {float(np.std(cos_mc)):.5f}")
    t1, t2 = go.central_conjunctions(r, ref_btjd=936.875)
    P = 180.0
    tc = go.conjunction_times(-20.0 + 936.875, P, 0.3, 40.0 * dr4_rows.DEG)
    d = min(_mod_dist(t1, float(tc[0]), P) + _mod_dist(t2, float(tc[1]), P),
            _mod_dist(t1, float(tc[1]), P) + _mod_dist(t2, float(tc[0]), P))
    check("S1g central conjunctions equal those from DR4 omega", d < 1e-6, f"{d:.2e} d")
    # S2: AstroSpectroSB1: RV omega survives, transit label given
    row2, _, _ = _synthetic_row("astrospectrosb1", rng, np, w_deg=-70.0)
    r2 = dr4_rows.convert_row(dict(row2))
    w_rv, snr = go.rv_omega(r2)
    dw = abs(((w_rv - (-70.0 * dr4_rows.DEG)) + math.pi) % (2 * math.pi) - math.pi)
    check("S2a rv_omega equals DR4 arg_periastron", dw < 1e-9, f"{dw:.2e} rad, snr {snr:.1f}")
    lab = go.transit_label(r2, ref_btjd=936.875)
    check("S2b transit label given", lab["transit_conj"] in ("t1", "t2"), str(lab))
    t_exp = -20.0 + 936.875 + float(go.transit_phase(0.3, -70.0 * dr4_rows.DEG)) * 180.0
    check("S2c RV transit time", abs(lab["t_transit_rv_btjd"] - t_exp) < 1e-6,
          f"{lab['t_transit_rv_btjd']:.6f} vs {t_exp:.6f}")
    check("S2d RV transit consistent with astrometric conjunction",
          bool(lab["rv_consistent"]), f"offset {lab['rv_offset_d']:.3g} d")
    # S3: circular AstroSpectroSB1 (omega and e not fitted)
    row3, _, _ = _synthetic_row("astrospectrosb1", rng, np, circular=True)
    r3 = dr4_rows.convert_row(dict(row3))
    s3 = go.sample_orbit(r3, 2000, np.random.default_rng(2), ref_btjd=936.875)
    check("S3 circular row samples e = 0 and finite times",
          float(np.max(s3["e"])) < 1e-9 and bool(np.all(np.isfinite(s3["t1"]))))
    # S4: gate trips on flipped constants
    bad = []
    for _ in range(20):
        rb, _, _ = _synthetic_row("orbital", rng, np)
        for k in dr4_rows.TI_KEYS:
            rb[k] = -rb[k]
        bad.append(dr4_rows.convert_row(rb))
    summ = dr4_rows.summarise(bad)
    check("S4 gate stops on OMEGA_PLUS_PI", summ["checks"].get("OMEGA_PLUS_PI") == 20
          and dr4_rows.gate(summ) != "", json.dumps(summ["checks"]))
    # S5: query templates format with run_search's own builder and drop DR3-only columns
    q = rs.build_nss_query("gaiadr4", 14.5, 0.2, None, None)
    check("S5a DR4 query built by run_search.build_nss_query",
          "gaiadr4.nss_two_body_orbit" in q and "n.correlations" in q)
    check("S5b no DR3-only column selected",
          not any(t in q for t in dr4_rows.DR3_ONLY_SELECTS))
    res["R1"] = dr3_roundtrip(rs, go, np, out_dir)
    log("R1 DR3 round trip:", json.dumps({k: v for k, v in res["R1"].items()
                                          if k != "failures"}))
    check("R1 DR3 real-data round trip not FAIL", res["R1"]["status"] != "FAIL",
          res["R1"]["status"])
    res["self_test_ok"] = ok
    with open(os.path.join(out_dir, "dr4_selftest.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    return ok


# ------------------------------------------------------------ R1: DR3 real-data round trip
DR3_SAMPLE_QUERY = (
    "SELECT TOP 400 n.source_id, n.nss_solution_type, n.corr_vec, n.period, n.period_error, "
    "n.t_periastron, n.t_periastron_error, n.eccentricity, n.eccentricity_error, "
    "n.a_thiele_innes, n.a_thiele_innes_error, n.b_thiele_innes, n.b_thiele_innes_error, "
    "n.f_thiele_innes, n.f_thiele_innes_error, n.g_thiele_innes, n.g_thiele_innes_error "
    "FROM gaiadr3.nss_two_body_orbit AS n WHERE n.nss_solution_type = 'Orbital' "
    "AND n.eccentricity_error > 0 AND n.period < 1000")


def _dr3_rows(rs, data_dir):
    reader = getattr(rs, "_dr4_orig_read_csv_text", rs.read_csv_text)
    paths = sorted(glob.glob(os.path.join(data_dir, "gaiadr3_nss_ti_*_v3.csv")))
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                rows = reader(fh.read())
            if rows:
                return rows, "cache:" + os.path.basename(p)
        except Exception as exc:  # noqa: BLE001
            log("cache read failed", p, exc)
    url = ("https://gea.esac.esa.int/tap-server/tap/sync?" + urllib.parse.urlencode(
        {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": DR3_SAMPLE_QUERY}))
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            text = resp.read().decode("utf-8", "replace")
        rows = reader(text)
        return rows, "tap:gaiadr3 TOP 400"
    except Exception as exc:  # noqa: BLE001
        log("DR3 TAP sample failed", exc)
        return [], "unavailable"


def dr3_roundtrip(rs, go, np, out_dir, max_rows=400):
    """R1: DR3 Orbital rows -> DR4-shaped rows (Campbell elements, covariance by the inverse
    Jacobian) -> dr4_rows.convert_row -> must give back DR3's own corr_vec, errors and
    conjunction times. Tests the parameter ordering and packing on real Gaia covariances."""
    rows, src = _dr3_rows(rs, _STATE.get("data_dir", "/data"))
    out = {"source": src, "n_tested": 0, "n_pass": 0, "max_corr_diff": 0.0,
           "max_rel_sd_diff": 0.0, "max_conj_diff_d": 0.0, "failures": []}
    if not rows:
        out["status"] = "SKIPPED"
        return out
    n3 = dr4_rows.DR3_ORDER["orbital"]
    n4 = dr4_rows.DR4_ORDER["orbital"]
    for r in rows:
        if out["n_tested"] >= max_rows:
            break
        if str(r.get("nss_solution_type", "")).strip('"') != "Orbital":
            continue
        if go.is_circular_fixed(r):
            continue
        vec = go.parse_corr_vec(r.get("corr_vec"))
        if vec is None or vec.size != 66:
            continue
        c = {}
        err = ""
        try:
            R3 = go.corr_matrix(vec, 12)
            sd3 = np.array([dr4_rows._sd(r.get(k + "_error")) for k in n3])
            el = go.thiele_innes_to_elements(r["a_thiele_innes"], r["b_thiele_innes"],
                                             r["f_thiele_innes"], r["g_thiele_innes"])
            a = float(el["a"])
            w = math.degrees(float(el["omega"]))
            W = math.degrees(float(el["Omega"]))
            inc = float(el["inc_deg"])
            vals = {"semi_major_axis": a, "arg_periastron": w, "pos_ascending_node": W,
                    "inclination": inc}
            J = dr4_rows.build_jacobian("orbital", vals)
            Jinv = np.linalg.inv(J)
            S4 = Jinv @ (R3 * np.outer(sd3, sd3)) @ Jinv.T
            sd4 = np.sqrt(np.clip(np.diag(S4), 0, None))
            R4 = S4 / np.outer(np.where(sd4 > 0, sd4, 1), np.where(sd4 > 0, sd4, 1))
            fake = {"source_id": r["source_id"], "nss_solution_type": "Orbital",
                    "corr_vec_dr4": dr4_rows.vec_from_corr(R4.tolist(), sd4.tolist()),
                    "semi_major_axis": a, "arg_periastron": w, "pos_ascending_node": W,
                    "inclination": inc}
            for k in ("eccentricity", "period", "t_periastron"):
                fake[k] = r[k]
            for k, s in zip(n4, sd4.tolist()):
                fake[k + "_error"] = s if s > 0 else float("nan")
            for k in dr4_rows.TI_KEYS:
                fake[k] = r[k]
                fake[k + "_error"] = r.get(k + "_error")
            c = dr4_rows.convert_row(fake)
            R3b = go.corr_matrix(go.parse_corr_vec(c["corr_vec"]), 12)
            sd3b = np.array([dr4_rows._sd(c.get(k + "_error")) for k in n3])
            m = sd3 > 0
            mm = np.outer(m, m)
            dcorr = float(np.max(np.abs((R3b - R3)[mm]))) if mm.any() else 0.0
            dsd = float(np.max(np.abs(sd3b[m] / sd3[m] - 1))) if m.any() else 0.0
            ta = go.central_conjunctions(r, ref_btjd=389.0)
            tb = go.central_conjunctions(c, ref_btjd=389.0)
            P = float(r["period"])
            dt = min(_mod_dist(ta[0], tb[0], P) + _mod_dist(ta[1], tb[1], P),
                     _mod_dist(ta[0], tb[1], P) + _mod_dist(ta[1], tb[0], P))
            good = (c.get("dr4_ti_check") == "STANDARD" and dcorr < 1e-6 and dsd < 1e-6
                    and dt < 1e-6)
        except Exception as exc:  # noqa: BLE001
            good, dcorr, dsd, dt = False, float("nan"), float("nan"), float("nan")
            err = repr(exc)
        out["n_tested"] += 1
        out["n_pass"] += int(good)
        for key, v in (("max_corr_diff", dcorr), ("max_rel_sd_diff", dsd),
                       ("max_conj_diff_d", dt)):
            if math.isfinite(v):
                out[key] = max(out[key], v)
        if not good and len(out["failures"]) < 20:
            out["failures"].append({"source_id": r.get("source_id"), "dcorr": dcorr,
                                    "dsd": dsd, "dt": dt, "error": err,
                                    "check": c.get("dr4_ti_check")})
    out["status"] = ("PASS" if out["n_tested"] >= 50 and out["n_pass"] == out["n_tested"]
                     else ("TOO_FEW" if out["n_tested"] < 50 else "FAIL"))
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--data-dir", default="/data")
    known, _ = ap.parse_known_args(argv)
    _STATE["out_dir"] = known.out_dir
    _STATE["data_dir"] = known.data_dir
    os.makedirs(known.out_dir, exist_ok=True)
    import numpy as np
    import gaia_orbits as go
    import run_search as rs
    patch(rs)
    if known.self_test:
        ok = self_test(rs, go, np, known.out_dir)
        log("self-test", "OK" if ok else "FAILED")
        return 0 if ok else 3
    if "--schema" not in argv:
        argv += ["--schema", "gaiadr4"]
    rc = rs.main(argv)
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
