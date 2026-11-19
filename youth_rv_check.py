# SPDX-License-Identifier: Apache-2.0
"""youth_rv_check 0.1.1 -- pre-registered follow-up of TIC 71945261 (Gaia DR3 6853008555751131648).

MV2 of Munim, Inc.; made with AI agents working in his name. Apache-2.0.
Rules: findings/2026-11-19-tic71945261-followup-prereg.md (written before this job ran).

0.1.1 (2026-11-19): fixes to_bjd only. In 0.1.0 an 8-digit calendar date such as "20000101"
parsed as a float first and was returned as if it were a Julian date; the built-in self-test
caught this and the v1 job stopped before reading any data. Dates are now recognised before
the numeric branch, and only 2,400,000-2,600,000 is accepted as a JD. Nothing else changed.

Steps (each one records its own error and never stops the others):
  1. Gaia DR3 astrometry + SB1 orbit of the target, and of AU Mic (positive control, beta Pic MG).
  2. BANYAN Sigma (Gagne et al.) membership with and without the systemic RV.
  3. Heliocentric UVW (astropy).
  4. VizieR cone searches (10 arcsec) for archival spectroscopy / activity catalogues, each with a
     0.3 deg control cone so an empty answer is meaningful.
  5. Any archival RV with a usable epoch is compared with the Gaia orbit under two hypotheses:
     K = Gaia's 16.16 km/s, and K = 32.4 km/s (the amplitude a normal-size ~0.21 Msun companion
     would need).
Outputs: /out/youth_rv_check.json and /out/youth_rv_report.md.
"""
import argparse
import csv
import io
import json
import math
import os
import random
import subprocess
import sys
import time
import traceback
import urllib.parse
import urllib.request

VERSION = "0.1.1"
TARGET = 6853008555751131648
AUMIC = (311.2897, -31.3409)
GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
J2016_BJD = 2457389.0
K_HEAVY = 32.4
YOUNG_MAX_MYR = 200
CATALOGUES = [
    ("III/283", "RAVE DR6"),
    ("J/MNRAS/506/150", "GALAH DR3"),
    ("III/286", "APOGEE DR17"),
    ("J/A+A/588/A103", "ROSAT 2RXS"),
    ("J/A+A/682/A34", "eROSITA eRASS1 main"),
    ("II/335", "GALEX GUVcat AIS"),
    ("B/vsx", "AAVSO VSX (re-check)"),
    ("IV/39", "TESS Input Catalog v8.2"),
]
GAIA_COLS = ("g.source_id, g.ra, g.dec, g.parallax, g.parallax_error, g.pmra, g.pmra_error, "
             "g.pmdec, g.pmdec_error, g.radial_velocity, g.radial_velocity_error, "
             "g.rv_nb_transits, g.rv_amplitude_robust, g.phot_g_mean_mag, g.bp_rp, g.l, g.b")


# ------------------------------------------------------------------ pure helpers
def kepler_E(M, e):
    E = M if e < 0.8 else math.pi
    for _ in range(100):
        d = (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
        E -= d
        if abs(d) < 1e-12:
            break
    return E


def rv_model(t_bjd, P, T_rel, e, omega_deg, K, gamma):
    """Gaia DR3 SB1 convention: T_rel = t_periastron in days from J2016.0 (BJD 2457389.0)."""
    M = 2 * math.pi * (t_bjd - (J2016_BJD + T_rel)) / P
    M = math.fmod(M, 2 * math.pi)
    E = kepler_E(M, e)
    nu = 2 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2), math.sqrt(1 - e) * math.cos(E / 2))
    w = math.radians(omega_deg)
    return gamma + K * (math.cos(nu + w) + e * math.cos(w))


def predict(t_bjd, orb, K, n=2000, seed=1):
    """Median and 1-sigma spread of the predicted RV, propagating the Gaia period error."""
    rnd = random.Random(seed)
    vals = []
    for _ in range(n):
        P = orb["period"] + rnd.gauss(0, orb["period_error"] or 0.0)
        vals.append(rv_model(t_bjd, P, orb["t_periastron"], orb["eccentricity"],
                             orb["arg_periastron"], K, orb["gamma"]))
    vals.sort()
    med = vals[n // 2]
    return med, 0.5 * (vals[int(0.8413 * n)] - vals[int(0.1587 * n)])


def _calendar_jd(y, m, d):
    """JD at noon UT of a calendar date (the night of observation, +-0.5 d)."""
    a = (14 - m) // 12
    yy, mm = y + 4800 - a, m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def _as_date(s):
    s = s.strip()
    if s.endswith(".0"):
        s = s[:-2]
    s = s.replace("-", "").replace("/", "")
    if len(s) == 8 and s.isdigit():
        y, m, d = int(s[:4]), int(s[4:6]), int(s[6:8])
        if 1800 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
            return y, m, d
    return None


def to_bjd(name, value):
    """Best-effort epoch parsing; returns (bjd, precision_days) or None."""
    if value is None:
        return None
    ymd = _as_date(str(value))
    if ymd:
        return float(_calendar_jd(*ymd)), 0.5
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(v):
        return None
    if 2400000 < v < 2600000:
        return v, 0.001
    if 40000 < v < 80000:
        return v + 2400000.5, 0.001
    return None


def self_test():
    o = {"period": 2.0, "period_error": 0.0, "t_periastron": 0.0, "eccentricity": 0.0,
         "arg_periastron": 0.0, "gamma": -5.0}
    assert abs(rv_model(J2016_BJD, 2.0, 0.0, 0.0, 0.0, 10.0, -5.0) - 5.0) < 1e-9
    assert abs(rv_model(J2016_BJD + 1.0, 2.0, 0.0, 0.0, 0.0, 10.0, -5.0) + 15.0) < 1e-9
    assert abs(predict(J2016_BJD + 0.5, o, 10.0, n=10)[0] + 5.0) < 1e-6
    assert abs(kepler_E(1.0, 0.5) - 0.5 * math.sin(kepler_E(1.0, 0.5)) - 1.0) < 1e-10
    assert to_bjd("MJD", 55000.0) == (2455000.5, 0.001)
    assert to_bjd("Obsdate", "20000101") == (2451545.0, 0.5)
    assert to_bjd("Obsdate", "2000-01-01") == (2451545.0, 0.5)
    assert to_bjd("Obsdate", 20000101.0) == (2451545.0, 0.5)
    assert to_bjd("HJD", "2455000.25") == (2455000.25, 0.001)
    assert to_bjd("x", "nan") is None and to_bjd("x", "abc") is None
    assert to_bjd("x", 12345678.0) is None
    return True


def reading_youth(target, control):
    if not control or control.get("error"):
        return "CONTROL_FAILED"
    cp = control.get("ALL", {}).get("BPMG", 0.0)
    if cp < 0.8:
        return "CONTROL_FAILED"
    if target.get("error"):
        return "UNTESTED"
    p = target.get("YA_PROB_float")
    if p is None:
        return "UNTESTED"
    if p >= 0.8:
        return "YOUNG_KINEMATIC"
    if p < 0.2:
        return "FIELD_KINEMATIC"
    return "AMBIGUOUS"


# ------------------------------------------------------------------ network helpers
def tap(adql, tries=4):
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                   "QUERY": adql}).encode()
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(GAIA_TAP, data=data, timeout=180) as r:
                return list(csv.DictReader(io.StringIO(r.read().decode("utf-8", "replace"))))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(15 * (i + 1))
    raise RuntimeError("Gaia TAP failed: %r" % (last,))


def fnum(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def banyan(row, use_rv, rv=None, erv=None):
    import numpy as np
    from banyan_sigma import membership_probability
    kw = dict(ra=np.array([row["ra"]]), dec=np.array([row["dec"]]),
              pmra=np.array([row["pmra"]]), pmdec=np.array([row["pmdec"]]),
              epmra=np.array([row["pmra_error"]]), epmdec=np.array([row["pmdec_error"]]),
              plx=np.array([row["parallax"]]), eplx=np.array([row["parallax_error"]]),
              use_plx=True, use_rv=bool(use_rv))
    if use_rv:
        kw.update(rv=np.array([rv]), erv=np.array([erv]))
    out = membership_probability(**kw)
    res = {}
    for key in ("BEST_HYP", "BEST_YA", "YA_PROB", "LIST_PROB_YAS"):
        try:
            res[key] = str(out[key].values.ravel()[0])
        except Exception as exc:  # noqa: BLE001
            res[key] = "error %r" % (exc,)
    res["YA_PROB_float"] = fnum(res.get("YA_PROB"))
    try:
        allp = out["ALL"].iloc[0]
        res["ALL"] = {str(k[-1] if isinstance(k, tuple) else k): round(float(v), 4)
                      for k, v in allp.items() if fnum(v) is not None and float(v) >= 0.001}
    except Exception as exc:  # noqa: BLE001
        res["ALL_error"] = repr(exc)
    return res


def uvw(row, rv):
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    c = SkyCoord(ra=row["ra"] * u.deg, dec=row["dec"] * u.deg,
                 distance=(1000.0 / row["parallax"]) * u.pc,
                 pm_ra_cosdec=row["pmra"] * u.mas / u.yr, pm_dec=row["pmdec"] * u.mas / u.yr,
                 radial_velocity=rv * u.km / u.s, frame="icrs")
    v = c.galactic.cartesian.differentials["s"]
    U, V, W = (float(x.to(u.km / u.s).value) for x in (v.d_x, v.d_y, v.d_z))
    return {"U": round(U, 2), "V": round(V, 2), "W": round(W, 2),
            "v_tot": round(math.sqrt(U * U + V * V + W * W), 2),
            "note": "heliocentric, U towards the Galactic centre, not corrected to the LSR"}


def vizier_cone(cat, ra, dec, radius_arcsec):
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astroquery.vizier import Vizier
    errs = []
    for server in ("vizier.cds.unistra.fr", "vizier.cfa.harvard.edu"):
        try:
            v = Vizier(columns=["**", "+_r"], row_limit=50)
            v.VIZIER_SERVER = server
            res = v.query_region(SkyCoord(ra, dec, unit="deg"), radius=radius_arcsec * u.arcsec,
                                 catalog=cat)
            tables = []
            for t in res:
                rows = []
                for r in t[:10]:
                    rows.append({c: str(r[c]) for c in t.colnames})
                tables.append({"table": t.meta.get("name", ""), "n": len(t), "rows": rows})
            return {"server": server, "tables": tables}
        except Exception as exc:  # noqa: BLE001
            errs.append("%s: %r" % (server, exc))
    return {"error": errs}


RV_NAMES = ("hrv", "rv", "vhelio_avg", "rv_galah", "rv_nogr_obst", "rv_obst", "vrad", "rv_sun")
ERV_NAMES = ("e_hrv", "e_rv", "vscatter", "e_rv_galah", "e_rv_nogr_obst", "e_rv_obst", "e_vrad")
EPOCH_NAMES = ("hjd", "bjd", "mjd", "jd", "obsdate", "dateobs", "date", "epoch")


def find_rvs(vz):
    found = []
    for cat, block in vz.items():
        for t in block.get("target", {}).get("tables", []):
            for r in t["rows"]:
                low = {k.lower(): v for k, v in r.items()}
                rvk = next((k for k in RV_NAMES if k in low and fnum(low[k]) is not None), None)
                if not rvk:
                    continue
                ek = next((k for k in ERV_NAMES if k in low and fnum(low[k]) is not None), None)
                tk = next((k for k in low if any(k.replace("_", "").startswith(n)
                                                 for n in EPOCH_NAMES)), None)
                found.append({"catalogue": cat, "table": t["table"], "rv_col": rvk,
                              "rv": fnum(low[rvk]), "erv": fnum(low[ek]) if ek else None,
                              "epoch_col": tk, "epoch_raw": low.get(tk) if tk else None})
    return found


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--install-banyan", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    R = {"version": VERSION, "target": str(TARGET), "started": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                            time.gmtime())}
    R["self_test"] = self_test()

    # 1. Gaia rows
    tgt = ctl = orb = None
    try:
        rows = tap("SELECT %s, n.center_of_mass_velocity, n.center_of_mass_velocity_error, "
                   "n.period, n.period_error, n.t_periastron, n.eccentricity, n.arg_periastron, "
                   "n.semi_amplitude_primary, n.semi_amplitude_primary_error "
                   "FROM gaiadr3.gaia_source AS g LEFT JOIN gaiadr3.nss_two_body_orbit AS n "
                   "ON n.source_id = g.source_id WHERE g.source_id = %d" % (GAIA_COLS, TARGET))
        tgt = {k: (fnum(v) if k != "source_id" else v) for k, v in rows[0].items()}
        orb = {"period": tgt["period"], "period_error": tgt["period_error"],
               "t_periastron": tgt["t_periastron"], "eccentricity": tgt["eccentricity"] or 0.0,
               "arg_periastron": tgt["arg_periastron"] or 0.0,
               "gamma": tgt["center_of_mass_velocity"], "K": tgt["semi_amplitude_primary"]}
        R["gaia_target"] = tgt
    except Exception as exc:  # noqa: BLE001
        R["gaia_target_error"] = repr(exc)
    try:
        rows = tap("SELECT TOP 1 %s FROM gaiadr3.gaia_source AS g WHERE 1 = CONTAINS("
                   "POINT('ICRS', g.ra, g.dec), CIRCLE('ICRS', %.4f, %.4f, 0.01)) "
                   "ORDER BY g.phot_g_mean_mag ASC" % ((GAIA_COLS,) + AUMIC))
        ctl = {k: (fnum(v) if k != "source_id" else v) for k, v in rows[0].items()}
        R["gaia_control_aumic"] = ctl
    except Exception as exc:  # noqa: BLE001
        R["gaia_control_error"] = repr(exc)

    # 2. BANYAN Sigma
    if a.install_banyan:
        p = subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                            "git+https://github.com/jgagneastro/banyan_sigma.git"],
                           capture_output=True, text=True)
        R["banyan_install"] = {"exit": p.returncode, "tail": (p.stdout + p.stderr)[-1500:]}
        q = subprocess.run([sys.executable, "-m", "pip", "show", "banyan_sigma"],
                           capture_output=True, text=True)
        R["banyan_version"] = q.stdout[-500:]
    bres = {}
    for label, row, rv, erv in (
            ("target_with_rv", tgt, orb and orb["gamma"],
             tgt and tgt.get("center_of_mass_velocity_error")),
            ("target_no_rv", tgt, None, None),
            ("control_aumic_with_rv", ctl, ctl and ctl.get("radial_velocity"),
             ctl and ctl.get("radial_velocity_error")),
            ("control_aumic_no_rv", ctl, None, None)):
        try:
            if not row:
                raise RuntimeError("no Gaia row")
            use_rv = rv is not None and erv is not None
            if label.endswith("with_rv") and not use_rv:
                raise RuntimeError("no RV")
            bres[label] = banyan(row, use_rv, rv, erv)
        except Exception as exc:  # noqa: BLE001
            bres[label] = {"error": repr(exc), "trace": traceback.format_exc()[-800:]}
    R["banyan"] = bres
    ctl_res = bres.get("control_aumic_with_rv")
    if not ctl_res or ctl_res.get("error"):
        ctl_res = bres.get("control_aumic_no_rv")
    R["youth_reading"] = reading_youth(bres.get("target_with_rv", {}), ctl_res)
    R["youth_reading_no_rv"] = reading_youth(bres.get("target_no_rv", {}), ctl_res)

    # 3. UVW
    try:
        R["uvw"] = uvw(tgt, orb["gamma"])
    except Exception as exc:  # noqa: BLE001
        R["uvw_error"] = repr(exc)

    # 4. VizieR
    vz = {}
    ra, dec = (tgt["ra"], tgt["dec"]) if tgt else (305.561178, -22.073752)
    for cat, name in CATALOGUES:
        vz[cat] = {"name": name, "target": vizier_cone(cat, ra, dec, 10.0)}
        c = vizier_cone(cat, ra, dec, 1080.0)
        vz[cat]["control_0p3deg_n"] = (sum(t["n"] for t in c.get("tables", []))
                                       if "tables" in c else c)
    R["vizier"] = vz

    # 5. archival RVs vs the Gaia orbit
    tests = []
    for f in find_rvs(vz):
        ep = to_bjd(f["epoch_col"], f["epoch_raw"]) if f["epoch_col"] else None
        f["epoch_bjd"] = ep
        if ep and orb and orb["period"]:
            if ep[1] > 0.05:
                f["note"] = "epoch known only to the night: phase uncertain, reported not graded"
            for lab, K in (("gaia_K", orb["K"]), ("heavy_K", K_HEAVY)):
                med, sd = predict(ep[0], orb, K)
                sig = math.sqrt((f["erv"] or 2.0) ** 2 + sd ** 2 + 2.0 ** 2)
                f[lab] = {"pred": round(med, 2), "pred_sd": round(sd, 2),
                          "z": round((f["rv"] - med) / sig, 2)}
            gz, hz = abs(f["gaia_K"]["z"]), abs(f["heavy_K"]["z"])
            if ep[1] > 0.05:
                f["verdict"] = "NOT_GRADED_EPOCH"
            elif gz <= 3 and hz > 3:
                f["verdict"] = "SUPPORTS_GAIA_K"
            elif hz <= 3 and gz > 3:
                f["verdict"] = "SUPPORTS_HEAVY_K"
            elif gz <= 3 and hz <= 3:
                f["verdict"] = "UNINFORMATIVE"
            else:
                f["verdict"] = "FITS_NEITHER"
        tests.append(f)
    R["archival_rv_tests"] = tests
    if tgt:
        amp = tgt.get("rv_amplitude_robust")
        R["gaia_rv_amplitude_check"] = {
            "rv_amplitude_robust": amp, "two_K_gaia": orb and orb["K"] and round(2 * orb["K"], 2),
            "two_K_heavy": 2 * K_HEAVY, "rv_nb_transits": tgt.get("rv_nb_transits"),
            "note": "max-min of the epoch RVs after outlier rejection; cannot exceed 2K by much"}
    R["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(a.out_dir, "youth_rv_check.json"), "w") as fh:
        json.dump(R, fh, indent=1, default=str)
    lines = ["# youth_rv_check %s: TIC 71945261" % VERSION, "",
             "- youth reading (with RV): **%s**; without RV: %s" % (R["youth_reading"],
                                                                 R["youth_reading_no_rv"]),
             "- BANYAN target: %s" % json.dumps(bres.get("target_with_rv", {}), default=str)[:600],
             "- BANYAN AU Mic control: %s" % json.dumps(ctl_res or {}, default=str)[:600],
             "- UVW: %s" % json.dumps(R.get("uvw", R.get("uvw_error")), default=str),
             "- Gaia RV amplitude check: %s" % json.dumps(R.get("gaia_rv_amplitude_check"),
                                                          default=str),
             "", "## VizieR", ""]
    for cat, b in vz.items():
        n = sum(t["n"] for t in b["target"].get("tables", [])) if "tables" in b["target"] else \
            "error"
        lines.append("- %s (%s): %s rows within 10\"; control 0.3 deg: %s" % (
            cat, b["name"], n, b["control_0p3deg_n"]))
    lines += ["", "## Archival RVs", ""] + ["- %s" % json.dumps(t, default=str) for t in tests]
    with open(os.path.join(a.out_dir, "youth_rv_report.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps({"youth_reading": R["youth_reading"], "uvw": R.get("uvw"),
                      "n_archival_rv": len(tests),
                      "verdicts": [t.get("verdict") for t in tests]}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
