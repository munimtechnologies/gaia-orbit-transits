# SPDX-License-Identifier: Apache-2.0
"""g8_dr3_sb1 0.1.0 - blind Gaia DR3 run of the frozen g8 rule (sb2_ecl_dr4 0.1.0) on every Gaia DR3
SINGLE-lined spectroscopic orbit (SB1/SB1C) with 0.4 <= P <= 15 d that has DR3 epoch photometry
(7,978 stars counted on the AIP mirror on 25 Nov 2026): eclipses found in Gaia's own photometry at
the conjunctions of Gaia's own radial-velocity orbit, for stars Gaia does not call eclipsing.

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.
Pre-registration: findings/2026-11-25-g8-dr3-sb1-prereg.md (written before this job ran).

The rule, the VOTable parser, the epoch handling and the counting of P1-P4 are imported unchanged
from sb2_ecl_dr4.py 0.1.0 (commit af65d7b) and g8_dr3_blind.py 0.1.0 (commit f0e1fb6). New here:
the SB1 sample, the SB1 thresholds, prediction P6 (the deeper in-window dip falls at the conjunction
where the visible star is behind its companion, true anomaly 90 deg - omega), the mass function,
per-star retries for epoch chunks (at most 1% of stars may stay missing), and compact outputs.

  python g8_dr3_sb1.py --self-test
  python g8_dr3_sb1.py --out-dir /out
Exit codes: 0 ok; 2 data unavailable / sample mismatch / >1% epochs missing (re-file unchanged);
3 self-test failed. Stdlib only.
"""
import argparse
import collections
import csv
import gzip
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "repo"), os.path.join(os.getcwd(), "repo")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import g8_dr3_blind as b  # noqa: E402

g8 = b.g8
VERSION = "0.1.0"
UA = "gaia-orbit-transits/g8_dr3_sb1 (MV2, Munim, Inc.; open research)"
N_PREREG = 7978
EPOCH_CHUNK = 25
ID_CHUNK = 100
PAUSE = 0.5
MAX_MISSING_SHARE = 0.01

WHERE = ("o.nss_solution_type LIKE 'SB1%' AND o.period >= 0.4 AND o.period <= 15.0 "
         "AND g.has_epoch_photometry = 'True'")
COUNT_QUERY = ("SELECT COUNT(*) AS n FROM gaiadr3.nss_two_body_orbit AS o JOIN gaiadr3.gaia_source "
               "AS g ON o.source_id = g.source_id WHERE " + WHERE)
SAMPLE_QUERY = (
    "SELECT o.source_id, o.nss_solution_type, o.period, o.t_periastron, o.eccentricity, "
    "o.arg_periastron, o.semi_amplitude_primary, "
    "g.phot_g_mean_mag, g.bp_rp, g.ra, g.dec "
    "FROM gaiadr3.nss_two_body_orbit AS o JOIN gaiadr3.gaia_source AS g "
    "ON o.source_id = g.source_id WHERE " + WHERE)

# Pre-registered thresholds (findings/2026-11-25-g8-dr3-sb1-prereg.md)
P1_MIN_SHARE_KNOWN = 0.25
P2_MAX_NULL_SHARE = 0.02
P3_MAX_MEDIAN_DPHASE = 0.015
P4_MIN_NEW_ECL = 30
P6_MIN_C1_SHARE = 0.65
P6_MIN_N = 20

FLAGGED = ("ECL_GAIA", "ECL_GAIA_SHALLOW")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def tap(query, maxrec=200000, tries=8):
    params = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "votable",
                                     "MAXREC": str(maxrec), "QUERY": query})
    url = b.AIP_TAP + "?" + params
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return b.parse_votable(raw)
        except Exception as exc:  # noqa: BLE001
            last = exc
            log("TAP retry", a + 1, repr(exc)[:200])
            time.sleep(min(60, 5 * (a + 1)))
    raise RuntimeError("TAP failed: %r" % (last,))


def mass_function(k1, period, ecc):
    """Spectroscopic mass function in solar masses (K1 km/s, P days)."""
    e = ecc if (ecc is not None and math.isfinite(ecc)) else 0.0
    return g8.MASS_CONST * (1.0 - e * e) ** 1.5 * k1 ** 3 * period


def deep_conj(c):
    """Conjunction index (0 = true anomaly 90 - omega, visible star behind its companion;
    1 = the other) of the largest in-window dip, or None."""
    ins = [d for d in c.get("dips", []) if abs(d["dphase"]) <= g8.WINDOW]
    if not ins:
        return None
    return max(ins, key=lambda d: d["resid"])["conj"]


def grade_sb1(stars):
    s = b.grade(stars)
    s.pop("predictions", None)
    cls = [x for x in stars if x["label"] != "FEW_EPOCHS"]
    unknown = [x for x in cls if not x["gaia_known"]]
    ecl = [x for x in cls if x["label"] == "ECL_GAIA"]
    dc = [x["deep_conj"] for x in ecl if x.get("deep_conj") is not None]
    dc_new = [x["deep_conj"] for x in ecl if not x["gaia_known"] and x.get("deep_conj") is not None]
    c1 = (dc.count(0) / len(dc)) if dc else float("nan")
    c1_new = (dc_new.count(0) / len(dc_new)) if dc_new else float("nan")
    share_known = s["gaia_known"]["share_flagged"]
    null_share = s["null_share"]
    med = s["median_dphase_ecl"]
    n_new = s["gaia_unknown"]["n_ecl"]
    n_null_unknown = s["gaia_unknown"]["n_null_flags"]
    new_cls = collections.Counter((x.get("gaia_class") or "none") for x in unknown
                                  if x["label"] == "ECL_GAIA")
    s.update({
        "deep_conj_c1_share_ecl": c1, "deep_conj_n_ecl": len(dc),
        "deep_conj_c1_share_new": c1_new, "deep_conj_n_new": len(dc_new),
        "purity_expected_false_share": (n_null_unknown / n_new) if n_new else float("nan"),
        "new_candidates_gaia_class": dict(new_cls),
        "predictions": {
            "P1_known_share_ge_0.25": math.isfinite(share_known) and share_known >= P1_MIN_SHARE_KNOWN,
            "P2_null_share_le_0.02": math.isfinite(null_share) and null_share <= P2_MAX_NULL_SHARE,
            "P3_median_dphase_le_0.015": math.isfinite(med) and med <= P3_MAX_MEDIAN_DPHASE,
            "P4_new_ecl_ge_30": n_new >= P4_MIN_NEW_ECL,
            "P6_deep_dip_at_c1_share_ge_0.65": len(dc) >= P6_MIN_N and c1 >= P6_MIN_C1_SHARE,
        },
    })
    return s


def fetch_epochs(ids):
    epochs, missing = {}, []
    for i, ch in enumerate(b.chunks(ids, EPOCH_CHUNK)):
        try:
            for r in tap(b.EPOCH_QUERY.format(ids=", ".join(ch))):
                epochs[str(r["source_id"]).strip()] = b.epochs_from_row(r)
        except (RuntimeError, ValueError) as exc:
            log("chunk failed, trying stars one by one:", repr(exc)[:200])
            for sid in ch:
                try:
                    for r in tap(b.EPOCH_QUERY.format(ids=sid), tries=3):
                        epochs[str(r["source_id"]).strip()] = b.epochs_from_row(r)
                except (RuntimeError, ValueError) as exc2:
                    log("missing", sid, repr(exc2)[:120])
                    missing.append(sid)
        if i % 20 == 0:
            log("epochs", len(epochs), "of", len(ids), "missing", len(missing))
        time.sleep(PAUSE)
    return epochs, missing


def run(a):
    os.makedirs(a.out_dir, exist_ok=True)
    n_expect = int(b.fnum(tap(COUNT_QUERY)[0].get("n")))
    rows = tap(SAMPLE_QUERY)
    log("sample", len(rows), "expected", n_expect, "pre-registered", N_PREREG)
    if len(rows) != n_expect or n_expect == 0:
        log("SAMPLE COUNT MISMATCH")
        return 2
    orbits = {}
    for r in rows:
        sid = str(r["source_id"]).strip()
        orbits[sid] = {k: b.fnum(r.get(k)) for k in (
            "period", "t_periastron", "eccentricity", "arg_periastron", "semi_amplitude_primary",
            "phot_g_mean_mag", "bp_rp", "ra", "dec")}
        orbits[sid]["type"] = str(r.get("nss_solution_type", "")).strip()
    ids = sorted(orbits)
    in_eb, cls, ecl_sol = set(), {}, set()
    for ch in b.chunks(ids, ID_CHUNK):
        q = ", ".join(ch)
        in_eb |= {str(r["source_id"]).strip() for r in tap(b.EB_QUERY.format(ids=q))}
        for r in tap(b.CLS_QUERY.format(ids=q)):
            cls[str(r["source_id"]).strip()] = str(r.get("best_class_name", "")).strip()
        for r in tap(b.NSS_QUERY.format(ids=q)):
            if "clipsing" in str(r.get("nss_solution_type", "")):
                ecl_sol.add(str(r["source_id"]).strip())
        time.sleep(PAUSE)
    log("gaia lookups: EB table", len(in_eb), "EclipsingSpectro", len(ecl_sol), "classified", len(cls))
    epochs, missing = fetch_epochs(ids)
    if len(missing) > MAX_MISSING_SHARE * len(ids):
        log("TOO MANY MISSING", len(missing))
        return 2
    with gzip.open(os.path.join(a.out_dir, "g8_dr3_sb1_epochs.csv.gz"), "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source_id", "t", "g_mag", "rej"])
        for sid in ids:
            for t, m, rej in epochs.get(sid, []):
                w.writerow([sid, repr(t), repr(m), "1" if rej else "0"])
    stars = []
    for sid in ids:
        if sid in missing:
            continue
        o = orbits[sid]
        ep = epochs.get(sid, [])
        c, cn = b.analyse_star(o, ep)
        k1 = o["semi_amplitude_primary"]
        fm = mass_function(k1, o["period"], o["eccentricity"]) if math.isfinite(k1) else float("nan")
        stars.append({
            "source_id": sid, "type": o["type"], "P": o["period"], "Tp": o["t_periastron"],
            "e": o["eccentricity"], "omega": o["arg_periastron"], "K1": k1, "f_mass": fm,
            "G": o["phot_g_mean_mag"], "bp_rp": o["bp_rp"], "ra": o["ra"], "dec": o["dec"],
            "n_epochs_raw": len(ep), "in_gaia_eb": sid in in_eb, "gaia_ecl_solution": sid in ecl_sol,
            "gaia_class": cls.get(sid, ""),
            "gaia_known": b.known_label(sid in in_eb, sid in ecl_sol, cls.get(sid, "")),
            "label": c["label"], "null_label": cn["label"], "n": c["n"], "n_dips": c["n_dips"],
            "n_in": c["n_in"], "n_out": c["n_out"], "n_events": c["n_events"], "depth": c["depth"],
            "sd": c["sd"], "thr": c["thr"], "model": c["model"], "deep_conj": deep_conj(c),
            "dips": c["dips"], "null_dips": cn["dips"]})
    summary = grade_sb1(stars)
    summary.update({"version": VERSION, "rule": "sb2_ecl_dr4 %s classify (frozen)" % g8.VERSION,
                    "n_sample": len(ids), "n_prereg": N_PREREG, "n_missing": len(missing),
                    "missing": missing, "n_epochs_rows": len(epochs), "n_in_gaia_eb": len(in_eb),
                    "n_ecl_solution": len(ecl_sol)})
    keep = [s for s in stars if s["label"] in FLAGGED or s["null_label"] in FLAGGED]
    with open(os.path.join(a.out_dir, "g8_dr3_sb1.json"), "w") as fh:
        json.dump(b.clean({"summary": summary, "flagged_stars": keep}), fh, indent=1)
    cols = ["source_id", "type", "P", "Tp", "e", "omega", "K1", "f_mass", "G", "bp_rp", "ra",
            "dec", "n_epochs_raw", "n", "in_gaia_eb", "gaia_ecl_solution", "gaia_class",
            "gaia_known", "label", "null_label", "n_dips", "n_in", "n_out", "n_events", "depth",
            "sd", "thr", "model", "deep_conj"]

    def write_csv(fh, rows_):
        w = csv.writer(fh)
        w.writerow(cols)
        for s in rows_:
            w.writerow([s[c] if not isinstance(s[c], float) else ("%.8g" % s[c]) for c in cols])

    with gzip.open(os.path.join(a.out_dir, "g8_dr3_sb1_stars.csv.gz"), "wt", newline="") as fh:
        write_csv(fh, stars)
    with open(os.path.join(a.out_dir, "g8_dr3_sb1_flagged.csv"), "w", newline="") as fh:
        write_csv(fh, keep)
    new = sorted([s for s in stars if s["label"] == "ECL_GAIA" and not s["gaia_known"]],
                 key=lambda s: -s["depth"])
    with open(os.path.join(a.out_dir, "g8_dr3_sb1_new_candidates.csv"), "w", newline="") as fh:
        write_csv(fh, new)
    flagged_dir = os.path.join(a.out_dir, "flagged_epochs")
    os.makedirs(flagged_dir, exist_ok=True)
    for s in stars:
        if s["label"] in FLAGGED and not s["gaia_known"]:
            with open(os.path.join(flagged_dir, "%s_g.csv" % s["source_id"]), "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["t", "g_mag", "rej"])
                for t, m, rej in epochs.get(s["source_id"], []):
                    w.writerow([repr(t), repr(m), "1" if rej else "0"])
    print(json.dumps(b.clean(summary), indent=1))
    return 0


# ---------------------------------------------------------------- self-test
def self_test():
    checks = []
    # 0: mass function, hand value 1.036149e-7 * 10**3 * 1 = 1.036149e-4
    checks.append(abs(mass_function(10.0, 1.0, None) - 1.036149e-4) < 1e-12)
    # 1: deep_conj ignores out-of-window dips and picks the largest in-window residual
    c = {"dips": [{"resid": 0.05, "dphase": 0.01, "conj": 1},
                  {"resid": 0.10, "dphase": -0.02, "conj": 0},
                  {"resid": 0.30, "dphase": 0.20, "conj": 1}]}
    checks.append(deep_conj(c) == 0)
    # 2: no in-window dip -> None
    checks.append(deep_conj({"dips": [{"resid": 0.3, "dphase": 0.2, "conj": 0}]}) is None)
    # 3: synthetic eclipsing binary through the frozen rule, deeper eclipse at conjunction 0
    t, m = g8.synth(11, P=3.0, depth1=0.20, depth2=0.10)
    o = {"period": 3.0, "t_periastron": -b.DR3_REF, "eccentricity": float("nan"),
         "arg_periastron": float("nan")}
    cc, cn = b.analyse_star(o, [(ti, mi, False) for ti, mi in zip(t, m)])
    checks.append(cc["label"] == "ECL_GAIA" and cn["label"] == "NONE" and deep_conj(cc) == 0)
    # 4: grading on hand-made stars (hand values in the comments)
    st = [{"source_id": "1", "label": "ECL_GAIA", "null_label": "NONE", "gaia_known": False,
           "depth": 0.1, "deep_conj": 0, "gaia_class": "",
           "dips": [{"dphase": 0.01, "resid": 0.1, "conj": 0},
                    {"dphase": -0.005, "resid": 0.05, "conj": 1}]},
          {"source_id": "2", "label": "ECL_GAIA", "null_label": "NONE", "gaia_known": True,
           "depth": 0.2, "deep_conj": 1, "gaia_class": "ECL",
           "dips": [{"dphase": 0.02, "resid": 0.2, "conj": 1}]},
          {"source_id": "3", "label": "NONE", "null_label": "ECL_GAIA", "gaia_known": False,
           "depth": float("nan"), "deep_conj": None, "gaia_class": "", "dips": []},
          {"source_id": "4", "label": "FEW_EPOCHS", "null_label": "FEW_EPOCHS",
           "gaia_known": False, "depth": float("nan"), "deep_conj": None, "gaia_class": "",
           "dips": []}]
    gr = grade_sb1(st)
    # classified 3; known 1 flagged 1 -> 1.0; null 1/3; in-window |dphase| 0.005, 0.01, 0.02 ->
    # median 0.01; new 1; null flags among unknown 1 -> purity 1.0; c1 share 1/2 = 0.5, n = 2.
    checks.append(gr["n_classified"] == 3 and gr["gaia_known"]["share_flagged"] == 1.0
                  and abs(gr["null_share"] - 1.0 / 3.0) < 1e-12
                  and abs(gr["median_dphase_ecl"] - 0.01) < 1e-12
                  and gr["gaia_unknown"]["n_ecl"] == 1
                  and gr["purity_expected_false_share"] == 1.0
                  and gr["deep_conj_c1_share_ecl"] == 0.5 and gr["deep_conj_n_ecl"] == 2
                  and gr["predictions"]["P1_known_share_ge_0.25"] is True
                  and gr["predictions"]["P2_null_share_le_0.02"] is False
                  and gr["predictions"]["P3_median_dphase_le_0.015"] is True
                  and gr["predictions"]["P4_new_ecl_ge_30"] is False
                  and gr["predictions"]["P6_deep_dip_at_c1_share_ge_0.65"] is False
                  and gr["new_candidates"] == ["1"]
                  and gr["new_candidates_gaia_class"] == {"none": 1})
    return all(checks), [i for i, x in enumerate(checks) if not x]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    if a.self_test:
        ok, bad = self_test()
        print("SELF_TEST", "PASS" if ok else "FAIL", bad)
        return 0 if ok else 3
    try:
        return run(a)
    except RuntimeError as exc:
        log("DATA UNAVAILABLE", repr(exc)[:300])
        return 2


if __name__ == "__main__":
    sys.exit(main())
