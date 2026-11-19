# SPDX-License-Identifier: Apache-2.0
"""Fit the pre-registered EBLM XIX holdouts with eblm_fit 0.2.0 and grade the pipeline.

Part of gaia-orbit-transits by MV2 of Munim, Inc.; made with AI agents working in his name.
Apache-2.0.

Rules: findings/2026-11-19-eblm-holdout-prereg.md (written before eblm_fit 0.2.0 existed and
before any holdout fit) and findings/2026-11-19-eblm-fit-020-build.md.

What this wrapper does, and nothing more:
  1. fetches eblm_fit.py (0.2.0) and eblm_screen.py pinned to the commit given by --sha;
  2. reads holdout_ids.csv (output of holdout_resolve 0.1.0, committed before any fit) and
     keeps role == holdout rows (resolver controls are never graded);
  3. queries Gaia DR3 for those source_ids (eblm_screen.sample_adql columns plus
     eccentricity_error; vari_eclipsing_binary LEFT JOINed);
  4. runs eblm_screen.classify and eblm_fit.vet_fit on each;
  5. grades: testable unless UNTESTED or G (grazing); pass = C_NORMAL_COMPANION and
     |r2 / R2_pub - 1| <= 0.10; PIPELINE_VALIDATED if >= 4 testable and >= 80% pass,
     PIPELINE_FAILED if >= 4 testable and < 80%, else INCONCLUSIVE.
Exit codes: 0 ok; 2 Gaia archive unavailable (re-file unchanged); 4 a holdout has no DR3 SB1
row (the input is wrong; stop); 5 the fetched eblm_fit is not 0.2.0.
"""
import argparse
import csv
import json
import math
import os
import sys
import time
import traceback
import urllib.request

VERSION = "0.1.0"
MODULES = ["eblm_fit.py", "eblm_screen.py"]
R2_TOL = 0.10
PASS_SHARE = 0.80
MIN_TESTABLE = 4
UNTESTED_VERDICTS = ("", "NO_TIC", "NO_TESS_DATA", "ERROR")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def fetch(url, attempts=4, wait_s=5.0):
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gaia-orbit-transits"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            log("fetch failed", url, i + 1, exc)
            if i + 1 < attempts:
                time.sleep(wait_s)
    raise last


def fetch_modules(sha):
    base = f"https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/{sha}/"
    for f in MODULES:
        if os.path.exists(f) and os.path.getsize(f) > 0:
            log("have", f)
            continue
        data = fetch(base + f)
        with open(f, "wb") as fh:
            fh.write(data)
        log("fetched", f, len(data))


def num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def read_holdouts(path):
    with open(path, newline="") as fh:
        rows = [r for r in csv.DictReader(fh)]
    out = [r for r in rows if (r.get("role") or "").strip() == "holdout"]
    for r in out:
        r["gaia_dr3"] = str(int(str(r["gaia_dr3"]).strip()))
    return out


def adql(ids, schema="gaiadr3"):
    s = schema
    return (
        "SELECT n.source_id, n.nss_solution_type, n.period, n.period_error, n.t_periastron, "
        "n.eccentricity, n.eccentricity_error, n.arg_periastron, n.semi_amplitude_primary AS k1, "
        "n.semi_amplitude_primary_error AS k1_error, "
        "n.significance, v.frequency, v.reference_time, v.model_type, "
        "v.derived_primary_ecl_phase, v.derived_primary_ecl_depth, "
        "v.derived_secondary_ecl_phase, v.derived_secondary_ecl_depth, "
        "v.geom_model_gaussian1_phase, v.geom_model_gaussian1_depth, "
        "v.geom_model_gaussian1_depth_error, "
        "v.geom_model_gaussian2_phase, v.geom_model_gaussian2_depth, "
        "v.geom_model_cosine_half_period_amplitude AS ell_mag, "
        "v.geom_model_cosine_half_period_amplitude_error AS ell_mag_error, "
        "g.ra, g.dec, g.phot_g_mean_mag, g.bp_rp, g.ruwe, g.parallax, g.non_single_star, "
        "p.mass_flame, p.radius_flame, p.teff_gspphot "
        f"FROM {s}.nss_two_body_orbit AS n "
        f"JOIN {s}.gaia_source AS g ON g.source_id = n.source_id "
        f"LEFT JOIN {s}.vari_eclipsing_binary AS v ON v.source_id = n.source_id "
        f"LEFT JOIN {s}.astrophysical_parameters AS p ON p.source_id = n.source_id "
        f"WHERE n.nss_solution_type = 'SB1' AND n.source_id IN ({', '.join(ids)})"
    )


def outcome(v):
    """Same mapping as eblm_single.outcome (findings/2026-11-18-tic71945261-prereg.md)."""
    verdict = str(v.get("verdict") or "")
    if verdict in UNTESTED_VERDICTS:
        return "UNTESTED"
    if verdict == "NO_ECLIPSE":
        return "E_NO_ECLIPSE"
    if verdict == "TWIN_AT_2P":
        return "D_TWIN_AT_2P"
    if verdict in ("MASS_TENSION_HEAVIER", "TOO_LUMINOUS"):
        return "A_COMPANION_HEAVIER_THAN_GAIA"
    if verdict == "MASS_TENSION_LIGHTER":
        return "A2_COMPANION_LIGHTER_THAN_GAIA"
    if verdict.endswith("EBLM_GRAZING"):
        return "G_GRAZING_RADIUS_UNMEASURED"
    if verdict.endswith("EBLM_LARGE_RADIUS"):
        r = num(v.get("r1_ratio"))
        return "B_OVERSIZED_COMPANION" if 0.8 <= r <= 1.25 else "B0_LARGE_BUT_PRIMARY_SCALE_DISAGREES"
    if verdict.endswith("EBLM_CONSISTENT") or verdict.endswith("EBLM_SMALL_RADIUS"):
        return "C_NORMAL_COMPANION"
    return "OTHER:" + verdict


def grade_one(v, r2_pub):
    """(testable, pass, offset) for one holdout."""
    lab = v.get("outcome", "")
    testable = lab not in ("UNTESTED", "G_GRAZING_RADIUS_UNMEASURED")
    r2 = num(v.get("r2"))
    off = r2 / r2_pub - 1.0 if r2 == r2 and r2_pub > 0 else float("nan")
    ok = testable and lab == "C_NORMAL_COMPANION" and off == off and abs(off) <= R2_TOL
    return testable, ok, off


def grade_all(items):
    """items: list of (vet dict with 'outcome', published R2). Pre-registered overall label."""
    per = [grade_one(v, r2) for v, r2 in items]
    n_test = sum(1 for t, _, _ in per if t)
    n_pass = sum(1 for t, p, _ in per if t and p)
    if n_test < MIN_TESTABLE:
        label = "INCONCLUSIVE"
    elif n_pass >= PASS_SHARE * n_test:
        label = "PIPELINE_VALIDATED"
    else:
        label = "PIPELINE_FAILED"
    offs = sorted(o for t, _, o in per if t and o == o)
    med = float("nan")
    if offs:
        m = len(offs)
        med = offs[m // 2] if m % 2 else 0.5 * (offs[m // 2 - 1] + offs[m // 2])
    return {"n_items": len(items), "n_testable": n_test, "n_pass": n_pass,
            "pass_share": n_pass / n_test if n_test else float("nan"),
            "label": label, "median_r2_offset": med}


def outcome_without_mass(ef, v):
    """The label the system would get if the mass-consistency check were dropped."""
    w = dict(v)
    w["a_ell"] = float("nan")
    lab, _ = ef.verdict(w)
    w["verdict"] = lab
    return outcome(w)


def jsonable(x):
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {str(k): jsonable(val) for k, val in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(val) for val in x]
    if isinstance(x, (str, int, bool)) or x is None:
        return x
    try:
        f = float(x)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return str(x)


def write_json(path, obj):
    with open(path, "w") as fh:
        json.dump(jsonable(obj), fh, indent=1)


def run(a):
    import eblm_fit as ef
    es = ef.es
    if getattr(ef, "VERSION", "") != "0.2.0":
        log("eblm_fit is", getattr(ef, "VERSION", "?"), "not 0.2.0")
        return 5
    t0 = time.time()
    os.makedirs(a.out_dir, exist_ok=True)
    os.makedirs(a.data_dir, exist_ok=True)
    plot_dir = os.path.join(a.out_dir, "fit_plots")
    os.makedirs(plot_dir, exist_ok=True)
    hold = read_holdouts(a.ids_csv)
    ids = [h["gaia_dr3"] for h in hold]
    summary = {"version": VERSION, "eblm_fit_version": ef.VERSION, "code_sha": a.sha, "schema": a.schema,
               "n_holdouts": len(hold), "ids": ids, "max_sectors": a.max_sectors}
    query = adql(ids, a.schema)
    summary["adql"] = query
    rows = None
    for i in range(a.tap_attempts):
        try:
            rows = es.tap_csv(es.GAIA_TAP, query)
            break
        except Exception as exc:  # noqa: BLE001
            log("Gaia TAP failed", i + 1, exc)
            if i + 1 < a.tap_attempts:
                time.sleep(a.tap_wait_s)
    if rows is None:
        summary["error"] = "Gaia TAP unavailable"
        write_json(os.path.join(a.out_dir, "holdout_fit_summary.json"), summary)
        return 2
    found = {}
    for r in rows:
        found.setdefault(str(r.get("source_id", "")).strip(), r)
    missing = [s for s in ids if s not in found]
    if missing:
        summary["error"] = "no DR3 SB1 row for " + ",".join(missing)
        write_json(os.path.join(a.out_dir, "holdout_fit_summary.json"), summary)
        log(summary["error"])
        return 4
    vets, items = [], []
    for h in hold:
        sid = h["gaia_dr3"]
        row = found[sid]
        c = es.classify(row)
        c["e_err"] = num(row.get("eccentricity_error"))
        c["omega"] = num(row.get("arg_periastron"))
        log("fit", h["name"], sid, "P", c.get("period"), "e", c.get("e"), "+-", c["e_err"])
        try:
            v = ef.vet_fit(c, a.data_dir, a.max_sectors, plot_dir)
        except Exception:  # noqa: BLE001
            v = {"source_id": sid, "verdict": "ERROR", "reasons": [traceback.format_exc()[-600:]]}
        v["name"] = h["name"]
        v["outcome"] = outcome(v)
        v["outcome_without_mass"] = outcome_without_mass(ef, v) if v["outcome"] != "UNTESTED" else "UNTESTED"
        r2_pub, m2_pub = num(h.get("R2_pub")), num(h.get("M2_pub"))
        t, p, off = grade_one(v, r2_pub)
        v.update({"R2_pub": r2_pub, "M2_pub": m2_pub, "e_pub": num(h.get("e_pub")), "testable": t,
                  "pass": p, "r2_offset": off,
                  "m2_ratio": num(v.get("m2")) / m2_pub if m2_pub > 0 else float("nan")})
        log("->", h["name"], v.get("verdict"), v["outcome"], "pass" if p else "fail", off)
        vets.append(v)
        items.append((v, r2_pub))
    g = grade_all(items)
    g["n_labels_changed_without_mass"] = sum(1 for v in vets if v["outcome"] != v["outcome_without_mass"])
    summary["grade"] = g
    summary["per_system"] = {v["name"]: {k: v.get(k) for k in ("source_id", "verdict", "mass_check", "outcome",
                                                               "outcome_without_mass", "testable", "pass",
                                                               "r2", "R2_pub", "r2_offset", "m2", "M2_pub",
                                                               "m2_ratio", "e_used", "phi2_fit")}
                             for v in vets}
    summary["minutes"] = (time.time() - t0) / 60.0
    ef.write_outputs(a.out_dir, vets, summary)
    write_json(os.path.join(a.out_dir, "holdout_fit_summary.json"), summary)
    write_json(os.path.join(a.out_dir, "holdout_fit_vets.json"), vets)
    lines = [f"# EBLM holdout fit (eblm_holdout_fit {VERSION}, eblm_fit {ef.VERSION} @ {a.sha[:7]})", "",
             f"**{g['label']}**: {g['n_pass']} of {g['n_testable']} testable pass "
             f"(median r2 offset {g['median_r2_offset']:+.3f}); labels changed without the mass check: "
             f"{g['n_labels_changed_without_mass']}", "",
             "| name | Gaia DR3 | verdict | mass check | outcome | r2 | R2 pub | offset | m2/M2 | e used | pass |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in vets:
        lines.append("| %s | %s | %s | %s | %s | %.4f | %.4f | %+.3f | %.3f | %.3f | %s |" % (
            v["name"], v.get("source_id"), v.get("verdict"), v.get("mass_check", ""), v["outcome"],
            num(v.get("r2")), v["R2_pub"], v["r2_offset"], v["m2_ratio"], num(v.get("e_used")),
            "yes" if v["pass"] else ("no" if v["testable"] else "untestable")))
    with open(os.path.join(a.out_dir, "holdout_fit_report.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps(jsonable(g)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sha", required=True, help="commit that published eblm_fit 0.2.0")
    ap.add_argument("--fetch-only", action="store_true")
    ap.add_argument("--ids-csv", default="holdout_ids.csv")
    ap.add_argument("--schema", default="gaiadr3")
    ap.add_argument("--max-sectors", type=int, default=8)
    ap.add_argument("--tap-attempts", type=int, default=6)
    ap.add_argument("--tap-wait-s", type=float, default=300.0)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    if a.fetch_only:
        fetch_modules(a.sha)
        return 0
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
