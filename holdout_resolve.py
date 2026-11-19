# SPDX-License-Identifier: Apache-2.0
"""holdout_resolve 0.1.0 -- freeze the EBLM holdout control set for eblm_fit 0.2.0, by rule.

Part of gaia-orbit-transits by MV2 of Munim, Inc.; made with AI agents working in his name.
Apache-2.0. Rules: findings/2026-11-19-eblm-holdout-prereg.md (written before this job ran and
before eblm_fit 0.2.0 exists).

For every row of eblmxix_sample1_p13.csv (EBLM XIX, Davis et al. 2026, arXiv:2610.18338,
Sample 1, P <= 13 d) this finds Gaia DR3 nss_two_body_orbit solutions whose period is within
+-0.3% of the published period and whose gaia_source position lies in the box the EBLM name
(Jhhmm+dd) allows. Exactly one SB1 match -> MATCH; more than one -> AMBIGUOUS (excluded); none
-> NO_SB1 (other solution types in the box are reported). Nothing is fitted here.

Resolver check RC1: the two rows marked resolver_control must resolve to the Gaia DR3 ids the
earlier control job used (J0123+38 -> 323261744326472832, J0719+25 -> 870991952855398656).

Outputs: /out/holdout_ids.csv, /out/holdout_resolve.json, /out/holdout_resolve.md.
Exit codes: 0 ok; 2 Gaia archive unavailable for some row (re-file unchanged); 3 RC1 failed.
"""
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

VERSION = "0.1.0"
GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
SIMBAD_TAP = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
P_TOL = 0.003
RA_PAD_LO, RA_PAD_HI = 0.25, 0.50      # degrees around 15*(hh + mm/60)
DEC_PAD_LO, DEC_PAD_HI = 1.0, 2.0      # degrees around the name's truncated declination
RC1_EXPECT = {"J0123+38": "323261744326472832", "J0719+25": "870991952855398656"}


# ------------------------------------------------------------------ pure helpers
def parse_name(name):
    """'J0011+63' -> (hh, mm, sign, dd). Accepts a unicode minus."""
    s = name.strip().replace("−", "-")
    if s.upper().startswith("EBLM"):
        s = s[4:].strip()
    if not s.startswith("J") or len(s) != 8 or s[5] not in "+-":
        raise ValueError("bad EBLM name %r" % name)
    hh, mm, dd = int(s[1:3]), int(s[3:5]), int(s[6:8])
    if not (0 <= hh < 24 and 0 <= mm < 60 and 0 <= dd <= 90):
        raise ValueError("bad EBLM name %r" % name)
    return hh, mm, (1 if s[5] == "+" else -1), dd


def name_box(name):
    """(ra_lo, ra_hi, dec_lo, dec_hi) in degrees; ra_lo may exceed ra_hi when the box wraps."""
    hh, mm, sign, dd = parse_name(name)
    ra0 = 15.0 * (hh + mm / 60.0)
    ra_lo = (ra0 - RA_PAD_LO) % 360.0
    ra_hi = (ra0 + RA_PAD_HI) % 360.0
    if sign > 0:
        dec_lo, dec_hi = dd - DEC_PAD_LO, dd + DEC_PAD_HI
    else:
        dec_lo, dec_hi = -dd - DEC_PAD_HI, -dd + DEC_PAD_LO
    return ra_lo, ra_hi, max(dec_lo, -90.0), min(dec_hi, 90.0)


def ra_in(ra, lo, hi):
    if lo <= hi:
        return lo <= ra <= hi
    return ra >= lo or ra <= hi


def period_window(P):
    return P * (1 - P_TOL), P * (1 + P_TOL)


def box_adql(name, P):
    lo, hi = period_window(P)
    _, _, dlo, dhi = name_box(name)
    return ("SELECT n.source_id, n.nss_solution_type, n.period, n.period_error, n.eccentricity, "
            "n.semi_amplitude_primary AS k1, g.ra, g.dec, g.phot_g_mean_mag "
            "FROM gaiadr3.nss_two_body_orbit AS n "
            "JOIN gaiadr3.gaia_source AS g ON g.source_id = n.source_id "
            "WHERE n.period BETWEEN %.7f AND %.7f AND g.dec BETWEEN %.4f AND %.4f"
            % (lo, hi, dlo, dhi))


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def choose(name, P, rows):
    """Apply the pre-registered rule to the TAP rows of one system."""
    ra_lo, ra_hi, _, _ = name_box(name)
    inbox = [r for r in rows if fnum(r.get("ra")) is not None and ra_in(float(r["ra"]), ra_lo, ra_hi)]
    sb1 = [r for r in inbox if str(r.get("nss_solution_type", "")).strip() == "SB1"]
    other = sorted({str(r.get("nss_solution_type", "")).strip() for r in inbox} - {"SB1"})
    if len(sb1) == 1:
        r = sb1[0]
        return {"status": "MATCH", "source_id": str(r["source_id"]).strip(),
                "gaia_P": fnum(r.get("period")), "gaia_e": fnum(r.get("eccentricity")),
                "gaia_K": fnum(r.get("k1")), "G": fnum(r.get("phot_g_mean_mag")),
                "dP_frac": (fnum(r.get("period")) - P) / P if fnum(r.get("period")) else None,
                "other_types_in_box": other}
    if len(sb1) > 1:
        return {"status": "AMBIGUOUS", "source_id": "",
                "candidates": [str(r["source_id"]).strip() for r in sb1],
                "other_types_in_box": other}
    return {"status": "NO_SB1", "source_id": "", "other_types_in_box": other,
            "n_rows_in_box": len(inbox)}


def rc1(results):
    out = {}
    for name, sid in RC1_EXPECT.items():
        got = results.get(name, {}).get("source_id", "")
        out[name] = {"expected": sid, "got": got, "pass": got == sid}
    out["pass"] = all(v["pass"] for k, v in out.items() if k in RC1_EXPECT)
    return out


def read_rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


# ------------------------------------------------------------------ network
def tap(url, adql, tries=4, wait=20):
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                   "QUERY": adql}).encode()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data,
                                         headers={"User-Agent": "gaia-orbit-transits"})
            with urllib.request.urlopen(req, timeout=240) as r:
                return list(csv.DictReader(io.StringIO(r.read().decode("utf-8", "replace"))))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(wait * (i + 1))
    raise RuntimeError("TAP failed: %r" % (last,))


def simbad_gaia_id(name):
    """Cross-check only: the Gaia DR3 id SIMBAD lists under 'EBLM <name>', if any."""
    q = ("SELECT i2.id FROM ident AS i1 JOIN ident AS i2 ON i1.oidref = i2.oidref "
         "WHERE i1.id = 'EBLM %s'" % name.replace("'", ""))
    rows = tap(SIMBAD_TAP, q, tries=2, wait=5)
    ids = [r.get("id", "") for r in rows]
    g = [s.split()[-1] for s in ids if s.startswith("Gaia DR3 ")]
    return {"known_to_simbad": bool(rows), "gaia_dr3": g[0] if g else ""}


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="eblmxix_sample1_p13.csv")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    rows = read_rows(a.csv)
    results, errors = {}, {}
    for row in rows:
        name, P = row["name"], float(row["P"])
        try:
            res = choose(name, P, tap(GAIA_TAP, box_adql(name, P)))
        except Exception as exc:  # noqa: BLE001
            errors[name] = repr(exc)
            res = {"status": "ERROR", "source_id": "", "error": repr(exc)}
        try:
            res["simbad"] = simbad_gaia_id(name)
            sg = res["simbad"]["gaia_dr3"]
            res["simbad_agrees"] = (None if not sg or not res.get("source_id")
                                    else sg == res["source_id"])
        except Exception as exc:  # noqa: BLE001
            res["simbad"] = {"error": repr(exc)}
        res.update({"role": row["role"], "P_pub": P})
        results[name] = res
        print(name, res["status"], res.get("source_id", ""), flush=True)

    check = rc1(results)
    holdout = [(n, r) for n, r in results.items() if r["role"] == "holdout"]
    summary = {"version": VERSION, "n_rows": len(rows), "rc1": check, "errors": errors,
               "counts": {s: sum(1 for _, r in holdout if r["status"] == s)
                          for s in ("MATCH", "AMBIGUOUS", "NO_SB1", "ERROR")},
               "results": results}
    with open(os.path.join(a.out_dir, "holdout_resolve.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    src = {r["name"]: r for r in rows}
    with open(os.path.join(a.out_dir, "holdout_ids.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "role", "gaia_dr3", "gaia_P", "gaia_K", "gaia_e", "G", "P_pub",
                    "e_pub", "M2_pub", "R2_pub", "R2_up", "R2_lo"])
        for n, r in results.items():
            if r["status"] != "MATCH":
                continue
            s = src[n]
            w.writerow([n, r["role"], r["source_id"], r["gaia_P"], r["gaia_K"], r["gaia_e"],
                        r["G"], s["P"], s["e"], s["M2"], s["R2"], s["R2_up"], s["R2_lo"]])
    lines = ["# holdout_resolve %s" % VERSION, "",
             "RC1 (resolver controls): **%s**" % ("PASS" if check["pass"] else "FAIL"), "",
             "Holdout counts: %s" % json.dumps(summary["counts"]), "",
             "| name | role | status | Gaia DR3 | Gaia P | P_pub | Gaia K | SIMBAD agrees |",
             "|---|---|---|---|---|---|---|---|"]
    for n, r in results.items():
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            n, r["role"], r["status"], r.get("source_id", ""), r.get("gaia_P", ""),
            r["P_pub"], r.get("gaia_K", ""), r.get("simbad_agrees", "")))
    with open(os.path.join(a.out_dir, "holdout_resolve.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps({"rc1": check["pass"], "counts": summary["counts"],
                      "errors": len(errors)}))
    if errors:
        return 2
    if not check["pass"]:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
