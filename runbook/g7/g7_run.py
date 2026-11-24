# g7_run.py -- Gaia DR4 day, step g7: per-transit double-lined velocities of eclipsing binaries,
# fitted with the eclipse timing fixed (sb2_rvfit.py). MV2, Munim, Inc. Made with AI agents working
# in his name. Apache-2.0. Registered in findings/2026-11-24-g7-prereg.md.
#
# Exit codes: 0 done; 4 schema gate (no star had readable per-transit velocities, or no DR3->DR4
# neighbours); 5 self-test failed; 6 bad targets file.
import argparse
import csv
import io
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
import zipfile

import sb2_rvfit as rf

VERSION = "g7_run.py 0.1.0"
TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
DL = "https://gea.esac.esa.int/data-server/data"
UA = {"User-Agent": "MV2-Munim-gaia-orbit-transits/0.1 (mv2@munimtech.com)"}


def http_get(url, tries=4, timeout=180):
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as ex:  # network errors are retried, then raised
            last = ex
            time.sleep(5 * (k + 1))
    raise last


def parse_table(raw):
    """CSV or ECSV bytes (or a zip of them) -> (header, rows)."""
    texts = []
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for n in z.namelist():
                if n.lower().endswith((".csv", ".ecsv", ".txt")):
                    texts.append(z.read(n).decode("utf-8", "replace"))
    else:
        texts.append(raw.decode("utf-8", "replace"))
    header, rows = None, []
    for t in texts:
        lines = [ln for ln in t.splitlines() if ln.strip() and not ln.startswith("#")]
        if not lines:
            continue
        rd = csv.DictReader(lines)
        if header is None:
            header = list(rd.fieldnames or [])
        rows.extend(rd)
    return header or [], rows


def tap_query(tap, adql):
    q = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql})
    return parse_table(http_get(tap + "?" + q))


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def to_btjd(times):
    """Gaia convention (BJD_TCB - 2455197.5, values ~1600-4000) or JD/BJD -> BTJD."""
    med = sorted(times)[len(times) // 2]
    if 1000.0 < med < 5000.0:
        return [t - 1802.5 for t in times], "gaia_tcb_minus_2455197.5"
    if med > 2.4e6:
        return [t - 2457000.0 for t in times], "jd"
    return None, "unknown (median %.3f)" % med


def neighbours(tap, schema, dr3_ids):
    header, _ = tap_query(tap, "SELECT TOP 1 * FROM %s.dr3_neighbourhood" % schema)
    c3 = next((h for h in header if h.lower() in ("dr3_source_id", "dr3source_id")), None)
    c4 = next((h for h in header if h.lower() in ("dr4_source_id", "dr4source_id")), None)
    if c4 is None and "source_id" in header:
        c4 = "source_id"
    cd = "angular_distance" if "angular_distance" in header else None
    if not c3 or not c4:
        return {}, {"error": "neighbour columns not identifiable", "header": header}
    _, rows = tap_query(tap, "SELECT * FROM %s.dr3_neighbourhood WHERE %s IN (%s)"
                        % (schema, c3, ",".join(dr3_ids)))
    best = {}
    for r in rows:
        d = fnum(r.get(cd)) if cd else None
        key = (d if d is not None else 1e9)
        s3, s4 = str(r.get(c3)).strip(), str(r.get(c4)).strip()
        if s3 not in best or key < best[s3][0]:
            best[s3] = (key, s4, sum(1 for rr in rows if str(rr.get(c3)).strip() == s3))
    return ({k: {"dr4_id": v[1], "dist": v[0], "n_candidates": v[2]} for k, v in best.items()},
            {"dr3_col": c3, "dr4_col": c4, "dist_col": cd, "n_rows": len(rows)})


def dr4_orbits(tap, schema, ids):
    if not ids:
        return {}
    _, rows = tap_query(tap, "SELECT * FROM %s.nss_two_body_orbit WHERE source_id IN (%s)"
                        % (schema, ",".join(ids)))
    out = {}
    for r in rows:
        sid = str(r.get("source_id")).strip()
        if fnum(r.get("semi_amplitude_secondary")) is None:
            continue
        out[sid] = {k: fnum(r.get(k)) for k in (
            "period", "period_error", "eccentricity", "eccentricity_error", "arg_periastron",
            "arg_periastron_error", "semi_amplitude_primary", "semi_amplitude_primary_error",
            "semi_amplitude_secondary", "semi_amplitude_secondary_error")}
        out[sid]["nss_solution_type"] = r.get("nss_solution_type")
    return out


def star_pairs(dl, release, sid, out_dir, name):
    q = urllib.parse.urlencode({"RETRIEVAL_TYPE": "EPOCH_PARAMETERS_RVS_DOUBLE", "ID": sid,
                                "FORMAT": "CSV", "RELEASE": release, "VALID_DATA": "false"})
    raw = http_get(dl + "?" + q)
    header, rows = parse_table(raw)
    m = rf.map_columns(header)
    info = {"header": header, "n_rows": len(rows), "mapping": m}
    if m is None:
        return None, info
    pairs = []
    for r in rows:
        t, va, ea, vb, eb = (fnum(r.get(m[k])) for k in ("time", "v1", "e1", "v2", "e2"))
        if None in (t, va, ea, vb, eb) or ea <= 0 or eb <= 0:
            continue
        pairs.append({"t": t, "va": va, "ea": ea, "vb": vb, "eb": eb})
    if not pairs:
        return None, info
    bt, unit = to_btjd([p["t"] for p in pairs])
    info["time_unit"] = unit
    if bt is None:
        return None, info
    for p, b in zip(pairs, bt):
        p["t"] = b
    safe = "".join(c if c.isalnum() else "_" for c in name)
    with open(os.path.join(out_dir, "rv_pairs_%s.csv" % safe), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["btjd", "v_a", "e_a", "v_b", "e_b"])
        for p in pairs:
            w.writerow([p["t"], p["va"], p["ea"], p["vb"], p["eb"]])
    return pairs, info


def analyse(star, pairs, orb4, min_sep, err_floor):
    num = lambda x: x if isinstance(x, (int, float)) and not isinstance(x, bool) else None
    P = star["P"]
    e = num(star.get("e")) or 0.0
    w = num(star.get("omega")) or 0.0
    eph = num(star.get("eph_sigma")) or 0.0
    # Which Gaia component is behind at t_conj is not known in advance. omega is Gaia's (component
    # 1), so try both conjunction identities and keep the lower chi2. For circular orbits the two
    # are the same fit with the labels swapped.
    scans = {}
    for behind in (True, False):
        scans[behind] = rf.scan_conjunction(pairs, P, e, w, star["t_conj"], star["K1_prior"],
                                            star["K2_prior"], behind, 0.05, 401, min_sep, err_floor)
    behind = min(scans, key=lambda b: scans[b]["chi2_min"])
    sc = scans[behind]
    tp = rf.tperi_from_conjunction(star["t_conj"] + sc["dt_best"], P, e, w, behind)
    fit = rf.fit_pairs(pairs, P, e, w, tp, star["K1_prior"], star["K2_prior"], min_sep=min_sep,
                       err_floor=err_floor)
    res = {"n_pairs": len(pairs), "fit": fit,
           "scan": {k: v for k, v in sc.items() if k != "curve"},
           "behind_at_t_conj": "model star 1" if behind else "model star 2",
           "delta_chi2_other_identity": scans[not behind]["chi2_min"] - sc["chi2_min"],
           "conj_grade": rf.grade_conjunction(sc, eph),
           "labels_swapped_majority": fit["n_swapped"] > fit["n_epochs_used"] / 2.0}
    K1, K2 = abs(fit["K1"]), abs(fit["K2"])
    if orb4:
        # star 1 here is the star behind at t_conj; Gaia's component labels may be the other way
        g1, g2 = orb4.get("semi_amplitude_primary"), orb4.get("semi_amplitude_secondary")
        s1, s2 = orb4.get("semi_amplitude_primary_error") or 0.0, orb4.get("semi_amplitude_secondary_error") or 0.0
        if g1 and g2:
            z = lambda a, ea, b, eb: (a - b) / math.sqrt(ea * ea + eb * eb) if (ea or eb) else float("nan")
            direct = (z(K1, fit["K1_err"], g1, s1), z(K2, fit["K2_err"], g2, s2))
            swapped = (z(K1, fit["K1_err"], g2, s2), z(K2, fit["K2_err"], g1, s1))
            best = min((direct, "direct"), (swapped, "swapped"), key=lambda d: max(abs(d[0][0]), abs(d[0][1])))
            res["vs_dr4_orbit"] = {"z_K": best[0], "mapping": best[1],
                                   "K_OK": max(abs(best[0][0]), abs(best[0][1])) <= 3.0}
    inc = num(star.get("inc"))
    m = rf.masses(K1, fit["K1_err"], K2, fit["K2_err"], P, e, inc if inc else 90.0,
                  (num(star.get("inc_err")) or 0.0) if inc else 0.0)
    res["masses"] = m
    res["masses_are"] = "absolute" if inc else "minimum (M sin^3 i)"
    lit = star.get("literature")
    if lit and inc:
        # literature stars are matched to ours by the smaller relative difference over both mappings
        opts = []
        for a, b in (("M1", "M2"), ("M2", "M1")):
            za = (m["M1"] - lit[a]) / math.hypot(m["M1_err"], lit[a + "_err"])
            zb = (m["M2"] - lit[b]) / math.hypot(m["M2_err"], lit[b + "_err"])
            opts.append((max(abs(za), abs(zb)), za, zb, a + "/" + b))
        best = min(opts)
        res["vs_literature"] = {"z_M": [best[1], best[2]], "mapping": best[3], "M_OK": best[0] <= 3.0}
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--schema", default="gaiadr4")
    ap.add_argument("--release", default="Gaia DR4")
    ap.add_argument("--tap", default=TAP)
    ap.add_argument("--dl", default=DL)
    ap.add_argument("--min-sep", type=float, default=20.0)
    ap.add_argument("--err-floor", type=float, default=0.0)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    summary = {"version": VERSION, "fit_version": rf.VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    st = rf.self_test()
    summary["self_test"] = st
    if not st["pass"]:
        json.dump(summary, open(os.path.join(a.out_dir, "g7_summary.json"), "w"), indent=1)
        return 5
    try:
        targets = json.load(open(a.targets))["stars"]
    except Exception as ex:
        summary["error"] = "targets: %s" % ex
        json.dump(summary, open(os.path.join(a.out_dir, "g7_summary.json"), "w"), indent=1)
        return 6
    ids3 = [s["dr3_source_id"] for s in targets]
    nb, nb_meta = neighbours(a.tap, a.schema, ids3)
    summary["neighbours"] = {"meta": nb_meta, "map": nb}
    ids4 = [nb[i]["dr4_id"] for i in ids3 if i in nb]
    orbs = dr4_orbits(a.tap, a.schema, ids4) if ids4 else {}
    stars, n_read = [], 0
    for s in targets:
        rec = {"name": s["name"], "role": s["role"], "dr3_source_id": s["dr3_source_id"]}
        stars.append(rec)
        if s["dr3_source_id"] not in nb:
            rec["status"] = "NO_DR4_ID"
            continue
        sid = nb[s["dr3_source_id"]]["dr4_id"]
        rec["dr4_source_id"] = sid
        rec["dr4_orbit"] = orbs.get(sid)
        if not isinstance(s.get("t_conj"), (int, float)) or not isinstance(s.get("P"), (int, float)):
            rec["status"] = "NO_EPHEMERIS"
            continue
        try:
            pairs, info = star_pairs(a.dl, a.release, sid, a.out_dir, s["name"])
        except Exception as ex:
            rec["status"] = "FETCH_ERROR"
            rec["error"] = repr(ex)[:300]
            continue
        rec["table"] = info
        if pairs is None:
            rec["status"] = "SCHEMA_UNKNOWN" if info.get("mapping") is None else "NO_PAIRS"
            continue
        n_read += 1
        if len(pairs) < 6:
            rec["status"] = "TOO_FEW"
            rec["n_pairs"] = len(pairs)
            continue
        rec["status"] = "FITTED"
        rec.update(analyse(s, pairs, rec["dr4_orbit"], a.min_sep, a.err_floor))
        time.sleep(1.0)
    summary["stars"] = stars
    ctl = [r for r in stars if r["role"] == "control"]
    ok = [r for r in ctl if r.get("status") == "FITTED" and r["conj_grade"] == "CONJ_AGREES"
          and r.get("vs_dr4_orbit", {}).get("K_OK") and r.get("vs_literature", {}).get("M_OK", True)]
    summary["controls"] = {"n": len(ctl), "n_ok": len(ok),
                           "CONTROLS_OK": len(ok) >= max(1, len(ctl) - 1)}
    summary["n_stars_read"] = n_read
    json.dump(summary, open(os.path.join(a.out_dir, "g7_summary.json"), "w"), indent=1, default=str)
    print(json.dumps({"controls": summary["controls"],
                      "stars": [(r["name"], r.get("status"), r.get("conj_grade")) for r in stars]}))
    if not nb or n_read == 0:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
