# SPDX-License-Identifier: Apache-2.0
"""Fit named Gaia DR3 SB1 systems with the UNCHANGED eblm_fit 0.1.0 code.

Part of gaia-orbit-transits by MV2 of Munim, Inc.; made with AI agents working in his name.
Apache-2.0.

Why: sb1_robust 0.2.0 (chunk 7) found a clean, deep eclipse at the Gaia DR3 SB1 period of
Gaia DR3 6853008555751131648 (TIC 71945261), a star that is not a TOI and not in VSX or the
TESS EB catalogue. Its box depth (~5 %) is about three times what Gaia's minimum companion
mass (0.097 M_sun) predicts for a normal M dwarf. The pre-registered reading of each outcome
is in findings/2026-11-18-tic71945261-prereg.md, written before this job ran.

What this wrapper does, and nothing more:
  1. fetches eblm_fit.py and eblm_screen.py pinned to commit 10b5aeb (release v0.10.0),
     the code gaia-eblm-fit-v1 ran on 167 systems;
  2. queries Gaia DR3 for the named source_ids with the same columns as
     eblm_screen.sample_adql, except that vari_eclipsing_binary is a LEFT JOIN (these stars
     are not Gaia eclipsing binaries), and records whether each star is in that table;
  3. runs eblm_screen.classify and eblm_fit.vet_fit on each, unchanged;
  4. maps the eblm_fit verdict to the pre-registered outcome labels (outcome()).
Exit codes: 0 ok; 2 Gaia archive unavailable (re-file unchanged); 4 a named star has no
DR3 SB1 row (the input is wrong; stop).
"""
import argparse
import json
import math
import os
import sys
import time
import traceback
import urllib.request

VERSION = "0.1.0"
SHA = "10b5aeb917c9c52492e7435de93ff1843fcf0999"   # release v0.10.0 (eblm_fit 0.1.0)
BASE = f"https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/{SHA}/"
MODULES = ["eblm_fit.py", "eblm_screen.py"]

DEFAULT_IDS = ["6853008555751131648",   # TIC 71945261: the D1 survivor of sb1rob chunk 7
               "2160710158704303360"]   # TIC 233120979 = TOI-1251.01: comparison system

# r1 from the light-curve density must agree with Gaia FLAME within this range before a
# large companion radius is read as a property of the companion (pre-registered).
R1_RATIO_OK = (0.8, 1.25)


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


def fetch_modules():
    for f in MODULES:
        if os.path.exists(f) and os.path.getsize(f) > 0:
            log("have", f)
            continue
        data = fetch(BASE + f)
        with open(f, "wb") as fh:
            fh.write(data)
        log("fetched", f, len(data))


def clean_ids(ids):
    """Source ids as canonical decimal strings, order kept, duplicates dropped."""
    out = []
    for s in ids:
        v = str(int(str(s).strip()))
        if v not in out:
            out.append(v)
    if not out:
        raise ValueError("no source_id given")
    return out


def single_adql(source_ids, schema="gaiadr3"):
    """The eblm_screen.sample_adql columns for named stars; vari_eclipsing_binary LEFT JOINed."""
    ids = clean_ids(source_ids)
    s = schema
    return (
        "SELECT n.source_id, n.nss_solution_type, n.period, n.period_error, n.t_periastron, "
        "n.eccentricity, n.arg_periastron, n.semi_amplitude_primary AS k1, "
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


def present(x):
    """True when a TAP CSV cell holds a value (not empty / None / NaN)."""
    if x is None:
        return False
    if isinstance(x, float):
        return x == x
    return str(x).strip() not in ("", "nan", "NaN", "null", "NULL")


def _num(v, key):
    try:
        x = float(v.get(key, ""))
        return x if math.isfinite(x) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def outcome(v):
    """Pre-registered outcome label (findings/2026-11-18-tic71945261-prereg.md) from an
    eblm_fit vet dict. Order matters and follows eblm_fit.verdict()."""
    verdict = str(v.get("verdict") or "")
    if verdict in ("", "NO_TIC", "NO_TESS_DATA", "ERROR"):
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
        r = _num(v, "r1_ratio")
        if R1_RATIO_OK[0] <= r <= R1_RATIO_OK[1]:
            return "B_OVERSIZED_COMPANION"
        return "B0_LARGE_BUT_PRIMARY_SCALE_DISAGREES"
    if verdict.endswith("EBLM_CONSISTENT") or verdict.endswith("EBLM_SMALL_RADIUS"):
        return "C_NORMAL_COMPANION"
    return "OTHER:" + verdict


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
    t0 = time.time()
    os.makedirs(a.out_dir, exist_ok=True)
    os.makedirs(a.data_dir, exist_ok=True)
    plot_dir = os.path.join(a.out_dir, "fit_plots")
    os.makedirs(plot_dir, exist_ok=True)
    ids = clean_ids(a.ids)
    summary = {"version": VERSION, "eblm_fit_version": getattr(ef, "VERSION", "?"),
               "code_sha": SHA, "schema": a.schema, "ids": ids, "max_sectors": a.max_sectors}
    query = single_adql(ids, a.schema)
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
        write_json(os.path.join(a.out_dir, "single_summary.json"), summary)
        return 2
    found = {}
    for r in rows:
        found.setdefault(str(r.get("source_id", "")).strip(), r)
    missing = [s for s in ids if s not in found]
    summary["n_rows"] = len(rows)
    if missing:
        summary["error"] = "no DR3 SB1 row for " + ",".join(missing)
        write_json(os.path.join(a.out_dir, "single_summary.json"), summary)
        log(summary["error"])
        return 4
    gaia_rows, classified, vets = [], [], []
    for sid in ids:
        row = found[sid]
        gaia_rows.append(row)
        c = es.classify(row)
        in_veb = present(row.get("frequency"))
        c["in_gaia_veb"] = in_veb
        classified.append(c)
        log("fit", sid, "P", c.get("period"), "m2sini", c.get("m2"), "m1_flame", c.get("m1_flame"),
            "r1_flame", c.get("r1_flame"), "in_gaia_veb", in_veb)
        try:
            v = ef.vet_fit(c, a.data_dir, a.max_sectors, plot_dir)
        except Exception:  # noqa: BLE001
            v = {"source_id": sid, "verdict": "ERROR", "reasons": [traceback.format_exc()[-600:]]}
        try:
            v.update(ef.catalogues(c["ra"], c["dec"]))
        except Exception as exc:  # noqa: BLE001
            v["catalogues_error"] = str(exc)[:200]
        v["in_gaia_veb"] = in_veb
        v["outcome"] = outcome(v)
        log("->", v.get("verdict"), v.get("outcome"), v.get("reasons"))
        vets.append(v)
    summary["outcomes"] = {str(v.get("source_id")): v.get("outcome") for v in vets}
    summary["minutes"] = (time.time() - t0) / 60.0
    ef.write_outputs(a.out_dir, vets, summary)
    write_json(os.path.join(a.out_dir, "single_summary.json"), summary)
    write_json(os.path.join(a.out_dir, "single_vets.json"), vets)
    write_json(os.path.join(a.out_dir, "single_classified.json"), classified)
    write_json(os.path.join(a.out_dir, "single_gaia_rows.json"), gaia_rows)
    try:
        with open(os.path.join(a.out_dir, "eblm_fit_report.md"), "w") as fh:
            fh.write(ef.report(vets, summary))
    except Exception as exc:  # noqa: BLE001
        log("report failed (outputs above are complete)", exc)
    print(json.dumps(jsonable(summary))[:4000])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch-only", action="store_true")
    ap.add_argument("--ids", nargs="+", default=DEFAULT_IDS)
    ap.add_argument("--schema", default="gaiadr3")
    ap.add_argument("--max-sectors", type=int, default=8)
    ap.add_argument("--tap-attempts", type=int, default=6)
    ap.add_argument("--tap-wait-s", type=float, default=300.0)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    if a.fetch_only:
        fetch_modules()
        return 0
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
