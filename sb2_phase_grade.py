# SPDX-License-Identifier: Apache-2.0
"""sb2_phase_grade 0.1.0 - finish the pre-registered Gaia conjunction-time test of job sb2-ffiscan-v1.

MV2, Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.
Addendum: findings/2026-11-27-sb2-ffiscan-v1-graded.md in
https://github.com/munimtechnologies/gaia-orbit-transits

sb2-ffiscan-v1 (sb2_ffiscan 0.1.0, frozen 24 Nov 2026) ran its light-curve search on 27 Nov but could
not download any Gaia orbit (ESA archive closed until DR4; the AIP mirror answered its POST with a
VOTABLE), so every conjunction test came out UNTESTABLE. This script applies the SAME frozen test,
using the 0.1.0 functions unchanged (predict_conj, grade, Z_PHASE, NB), to the dip times and box
widths that v1 measured, with orbits fetched by fetch_deps.py. No light curve is re-read.

One documented change: v1 kept only the LAST orbit row per source_id, so a star with two Gaia
solutions (e.g. an astrometric 'Orbital' outer orbit plus the SB2 inner one) could lose its SB2 row
to the anchor check. Here every row is kept and the row whose period anchors to v1's P_gaia (1e-9
relative, as in 0.1.0) is used.
"""
import argparse
import csv
import json
import math
import os
import shutil
import sys

import sb2_ffiscan as F

VERSION = "0.1.0"


def load_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_orbits(path):
    rows = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            rows.setdefault(str(r["source_id"]).strip(), []).append(r)
    return rows


def pick_orbit(rows, P_gaia):
    """-> (orbit dict, solution type) for the row whose period anchors to P_gaia, else (None, reason)."""
    if not rows:
        return None, "NO_ORBIT_ROW"
    for r in rows:
        orb = F.orbit_from_row(r)
        if F.anchor_ok(orb, P_gaia):
            return orb, orb["type"]
    return None, "ANCHOR_FAILED"


def phase_test(rec, orb):
    """The conjunction block of sb2_ffiscan 0.1.0 analyse(), on v1's stored measurements.
    Returns the fields analyse() would have added. rec must be DETECTED."""
    P = float(rec["P_best"])
    T1 = float(rec["T_dip1"])
    w = int(rec["box_w"])
    out = {}
    sig_obs1 = P * max(w / (4.0 * F.NB), 0.5 / F.NB)
    pr = F.predict_conj(orb, T1)
    zs = {}
    for c in ("c1", "c2"):
        zs[c] = pr["oc_%s" % c] / math.hypot(pr["sd_%s" % c], sig_obs1)
    bestc = min(zs, key=lambda c: abs(zs[c]))
    cover = sum(2.0 * F.Z_PHASE * math.hypot(pr["sd_%s" % c], sig_obs1) for c in ("c1", "c2")) / P
    out.update({"circular": pr["circular"], "oc1_d": pr["oc_c1"], "sd1_d": pr["sd_c1"],
                "oc2_d": pr["oc_c2"], "sd2_d": pr["sd_c2"], "z_c1": zs["c1"], "z_c2": zs["c2"],
                "phase_map": bestc, "phase_z": zs[bestc], "p_chance": float(min(1.0, cover)),
                "cycles_from_gaia": pr["cycles_c1"],
                "phase": "PHASE_MATCH" if abs(zs[bestc]) <= F.Z_PHASE else "PHASE_MISMATCH"})
    if rec.get("sec") == "SEC_DETECTED" and F.finite(rec.get("sep_obs")) and F.finite(rec.get("box2_w")):
        sig_ph1 = sig_obs1 / P
        sig_ph2 = max(int(rec["box2_w"]) / (4.0 * F.NB), 0.5 / F.NB)
        sd = math.sqrt(pr["sep_sd"] ** 2 + sig_ph1 ** 2 + sig_ph2 ** 2)
        so = float(rec["sep_obs"])
        za = (so - pr["sep_mean"]) / sd
        zb = (so - (1.0 - pr["sep_mean"])) / sd
        zsep = za if abs(za) <= abs(zb) else zb
        out.update({"sep_gaia": pr["sep_mean"], "sep_gaia_sd": pr["sep_sd"], "sep_z": zsep,
                    "sep": "SEP_MATCH" if abs(zsep) <= F.Z_PHASE else "SEP_MISMATCH"})
    else:
        out["sep"] = "UNTESTABLE"
    return out


def regrade(recs, orbits):
    n_anchor = 0
    for rec in recs:
        rec["orbit_type"], rec["orbit_anchor"] = None, False
        orb, why = pick_orbit(orbits.get(str(rec.get("source_id", "")).strip()), F.fnum(rec.get("P_gaia")))
        if orb is not None:
            n_anchor += 1
            rec["orbit_type"], rec["orbit_anchor"] = why, True
        else:
            rec["orbit_type"] = why
        if rec.get("label") != "DETECTED":
            continue
        if orb is None:
            rec["phase"], rec["sep"] = "UNTESTABLE", "UNTESTABLE"
            continue
        rec.update(phase_test(rec, orb))
    return n_anchor


def control_rows(recs):
    rows = []
    for r in recs:
        if r.get("role") == "control" and r.get("label") == "DETECTED":
            rows.append({k: r.get(k) for k in ("name", "source_id", "tic", "G", "orbit_type", "P_gaia",
                                               "T_dip1", "box_w", "phase", "phase_map", "phase_z",
                                               "oc1_d", "sd1_d", "oc2_d", "sd2_d", "p_chance", "circular",
                                               "sec", "sep_obs", "sep_gaia", "sep_gaia_sd", "sep_z",
                                               "sep")})
    return rows


COLS = ["name", "source_id", "tic", "G", "role", "vetted", "orbit_type", "orbit_anchor", "P_gaia", "P_best",
        "label", "snr", "null_max", "T_dip1", "box_w", "phase", "phase_map", "phase_z", "oc1_d", "sd1_d",
        "oc2_d", "sd2_d", "p_chance", "circular", "sec", "sep_obs", "sep_gaia", "sep_gaia_sd", "sep_z",
        "sep", "vsx_eclipsing", "vsx_names", "vsx_types"]


def run(args):
    os.makedirs(args.out_dir, exist_ok=True)
    recs = load_jsonl(args.stars)
    orbits = load_orbits(args.orbits)
    n_anchor = regrade(recs, orbits)
    grades = F.grade(recs, False)
    ph = [r for r in recs if r.get("role") == "control" and r.get("phase") in ("PHASE_MATCH", "PHASE_MISMATCH")]
    sep = [r for r in recs if r.get("role") == "control" and r.get("sep") in ("SEP_MATCH", "SEP_MISMATCH")]
    sep_ecc = [r for r in sep if not r.get("circular")]
    zabs = sorted(abs(r["phase_z"]) for r in ph if F.finite(r.get("phase_z")))
    extra = {"control_phase_z_abs_median": zabs[len(zabs) // 2] if zabs else None,
             "control_phase_within_1sigma": sum(1 for z in zabs if z <= 1.0),
             "control_sep_eccentric": {"n": len(sep_ecc),
                                       "match": sum(1 for r in sep_ecc if r["sep"] == "SEP_MATCH")},
             "control_p_chance_median": (sorted(r["p_chance"] for r in ph)[len(ph) // 2] if ph else None)}
    meta = {"version": VERSION, "sb2_ffiscan_version": F.VERSION, "n_records": len(recs),
            "n_sources_with_orbit_rows": len(orbits), "n_orbit_anchored": n_anchor}
    if os.path.exists(args.fetch_meta):
        meta["fetch"] = json.load(open(args.fetch_meta))
    for src in (args.orbits, args.fetch_meta):
        if os.path.exists(src):
            shutil.copy(src, os.path.join(args.out_dir, os.path.basename(src)))
    summary = {"meta": meta, "grades": grades, "extra": extra}
    json.dump(F.jclean(summary), open(os.path.join(args.out_dir, "phase_grade_summary.json"), "w"), indent=1)
    F.write_csv(os.path.join(args.out_dir, "phase_grade_stars.csv"), recs, COLS)
    F.write_csv(os.path.join(args.out_dir, "phase_grade_controls.csv"), control_rows(recs), list(control_rows(recs)[0].keys()) if control_rows(recs) else ["name"])
    print(json.dumps(F.jclean({"meta": meta, "F0": grades["F0"], "F1": grades["F1"], "F2n": grades["F2"]["n_candidates"],
                               "F3": grades["F3"], "extra": extra}), indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stars", default="v1_stars.jsonl")
    ap.add_argument("--orbits", default="orbits.csv")
    ap.add_argument("--fetch-meta", default="fetch_meta.json")
    ap.add_argument("--out-dir", default="out")
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
