# SPDX-License-Identifier: Apache-2.0
"""g8_dr3_blind 0.1.0 - blind Gaia DR3 run of the frozen g8 rule (sb2_ecl_dr4 0.1.0): eclipses of
Gaia DR3 double-lined binaries found in Gaia's own epoch photometry at Gaia's own spectroscopic
conjunctions, for EVERY DR3 SB2/SB2C orbit with 0.4 <= P <= 15 d that has DR3 epoch photometry
(927 stars on 25 Nov 2026). Data from the AIP Gaia TAP mirror (the ESA archive is closed until DR4).

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.
Pre-registration: findings/2026-11-25-g8-dr3-blind-prereg.md (written before this job ran).

The rule itself is imported unchanged from sb2_ecl_dr4.py 0.1.0 (classify, usable, NULL_SHIFT).
Epochs: G transit times and magnitudes; an epoch is dropped when variability_flag_g_reject is True
or its magnitude is not finite (the same choice the DR4 adapter makes: rejected_by_variability).
Orbit time: Gaia time = 2191.5 + t_periastron (DR3 reference epoch J2016.0).

  python g8_dr3_blind.py --self-test
  python g8_dr3_blind.py --out-dir /out
Exit codes: 0 ok; 2 data unavailable or sample count mismatch (re-file unchanged); 3 self-test failed.
Stdlib only.
"""
import argparse
import csv
import gzip
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "repo"), os.path.join(os.getcwd(), "repo")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import sb2_ecl_dr4 as g8  # noqa: E402

VERSION = "0.1.0"
AIP_TAP = "https://gaia.aip.de/tap/sync"
UA = "gaia-orbit-transits/g8_dr3_blind (MV2, Munim, Inc.; open research)"
P_MIN, P_MAX = 0.4, 15.0
DR3_REF = 2191.5
EPOCH_CHUNK = 25
ID_CHUNK = 100
PAUSE = 1.0

WHERE = ("o.nss_solution_type LIKE 'SB2%' AND o.period >= 0.4 AND o.period <= 15.0 "
         "AND g.has_epoch_photometry = 'True'")
COUNT_QUERY = ("SELECT COUNT(*) AS n FROM gaiadr3.nss_two_body_orbit AS o JOIN gaiadr3.gaia_source "
               "AS g ON o.source_id = g.source_id WHERE " + WHERE)
SAMPLE_QUERY = (
    "SELECT o.source_id, o.nss_solution_type, o.period, o.t_periastron, o.eccentricity, "
    "o.arg_periastron, o.semi_amplitude_primary, o.semi_amplitude_secondary, "
    "g.phot_g_mean_mag, g.bp_rp, g.ra, g.dec "
    "FROM gaiadr3.nss_two_body_orbit AS o JOIN gaiadr3.gaia_source AS g "
    "ON o.source_id = g.source_id WHERE " + WHERE)
EPOCH_QUERY = ("SELECT source_id, g_transit_time, g_transit_mag, variability_flag_g_reject "
               "FROM gaiadr3.epoch_photometry WHERE source_id IN ({ids})")
EB_QUERY = "SELECT source_id FROM gaiadr3.vari_eclipsing_binary WHERE source_id IN ({ids})"
CLS_QUERY = ("SELECT source_id, best_class_name FROM gaiadr3.vari_classifier_result "
             "WHERE source_id IN ({ids})")
NSS_QUERY = ("SELECT source_id, nss_solution_type FROM gaiadr3.nss_two_body_orbit "
             "WHERE source_id IN ({ids})")

# Pre-registered thresholds (findings/2026-11-25-g8-dr3-blind-prereg.md)
P1_MIN_SHARE_KNOWN = 0.40    # flagged (ECL_GAIA or SHALLOW) share among Gaia-known eclipsing stars
P2_MAX_NULL_SHARE = 0.02     # null (quadrature) flags / classified stars
P3_MAX_MEDIAN_DPHASE = 0.015  # median |dphase| of in-window dips of ECL_GAIA stars
P4_MIN_NEW_ECL = 10          # strict ECL_GAIA stars that Gaia itself does not call eclipsing


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- VOTable (TABLEDATA) parsing
def _local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_votable(text):
    """Rows of the first TABLE as dicts of raw strings. Raises on QUERY_STATUS ERROR or a
    non-TABLEDATA serialisation."""
    if isinstance(text, str):
        text = text.encode("utf-8")
    root = ET.fromstring(text)
    for el in root.iter():
        if _local(el.tag) == "INFO" and el.get("name") == "QUERY_STATUS" and \
                str(el.get("value", "")).upper() == "ERROR":
            raise RuntimeError("TAP error: %s" % ((el.text or "").strip()[:300]))
    for table in root.iter():
        if _local(table.tag) != "TABLE":
            continue
        names = [f.get("name") for f in table if _local(f.tag) == "FIELD"]
        if not names:
            continue
        rows = []
        found_data = False
        for data in table:
            if _local(data.tag) != "DATA":
                continue
            found_data = True
            kids = list(data)
            if kids and _local(kids[0].tag) != "TABLEDATA":
                raise RuntimeError("VOTable serialisation %s not supported" % _local(kids[0].tag))
            for td_block in kids:
                for tr in td_block:
                    if _local(tr.tag) != "TR":
                        continue
                    vals = [(td.text or "") for td in tr if _local(td.tag) == "TD"]
                    rows.append(dict(zip(names, vals)))
        if found_data or names:
            return rows
    return []


def fnum(s):
    try:
        v = float(str(s).strip())
        return v
    except (TypeError, ValueError):
        return float("nan")


def parse_bool_token(tok):
    return str(tok).strip().lower() in ("true", "t", "1")


def epochs_from_row(row):
    """(t, mag, rej) tuples from one epoch_photometry row with whitespace-separated arrays."""
    ts = str(row.get("g_transit_time", "")).split()
    ms = str(row.get("g_transit_mag", "")).split()
    rs = str(row.get("variability_flag_g_reject", "")).split()
    if len(ms) != len(ts):
        raise ValueError("time/mag array lengths differ: %d vs %d" % (len(ts), len(ms)))
    if rs and len(rs) != len(ts):
        raise ValueError("time/reject array lengths differ: %d vs %d" % (len(ts), len(rs)))
    out = []
    for i, (t, m) in enumerate(zip(ts, ms)):
        tv, mv = fnum(t), fnum(m)
        rej = parse_bool_token(rs[i]) if rs else False
        if not (math.isfinite(tv) and math.isfinite(mv)):
            rej = True
        out.append((tv, mv, rej))
    return out


# ---------------------------------------------------------------- network
def tap(query, maxrec=200000, tries=4):
    params = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "votable",
                                     "MAXREC": str(maxrec), "QUERY": query})
    url = AIP_TAP + "?" + params
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return parse_votable(raw)
        except Exception as exc:  # noqa: BLE001
            last = exc
            log("TAP retry", a + 1, repr(exc)[:200])
            time.sleep(5 * (a + 1))
    raise RuntimeError("TAP failed: %r" % (last,))


def chunks(xs, k):
    for i in range(0, len(xs), k):
        yield xs[i:i + k]


# ---------------------------------------------------------------- pure analysis
def known_label(in_eb, ecl_sol, cls):
    return bool(in_eb or ecl_sol or (cls or "").strip().upper() == "ECL")


def analyse_star(o, epochs):
    """Run the frozen rule and its quadrature null on one star. o: orbit dict with floats."""
    t, m = g8.usable(epochs)
    tp = DR3_REF + o["t_periastron"]
    e = o["eccentricity"] if math.isfinite(o["eccentricity"]) else None
    w = o["arg_periastron"] if math.isfinite(o["arg_periastron"]) else None
    c = g8.classify(t, m, o["period"], tp, e, w)
    cn = g8.classify(t, m, o["period"], tp, e, w, shift=g8.NULL_SHIFT)
    return c, cn


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return float("nan")
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def grade(stars):
    flagged = ("ECL_GAIA", "ECL_GAIA_SHALLOW")
    cls = [s for s in stars if s["label"] != "FEW_EPOCHS"]
    known = [s for s in cls if s["gaia_known"]]
    unknown = [s for s in cls if not s["gaia_known"]]
    kflag = [s for s in known if s["label"] in flagged]
    nulls = [s for s in cls if s["null_label"] in flagged]
    ecl = [s for s in cls if s["label"] == "ECL_GAIA"]
    dph = [abs(d["dphase"]) for s in ecl for d in s["dips"] if abs(d["dphase"]) <= g8.WINDOW]
    new_ecl = [s for s in unknown if s["label"] == "ECL_GAIA"]
    new_sh = [s for s in unknown if s["label"] == "ECL_GAIA_SHALLOW"]
    null_unknown = [s for s in unknown if s["null_label"] in flagged]
    share_known = (len(kflag) / len(known)) if known else float("nan")
    null_share = (len(nulls) / len(cls)) if cls else float("nan")
    med_dph = median(dph)
    return {
        "n_stars": len(stars), "n_classified": len(cls),
        "labels": {lab: sum(1 for s in stars if s["label"] == lab)
                   for lab in ("ECL_GAIA", "ECL_GAIA_SHALLOW", "NONE", "FEW_EPOCHS")},
        "null_labels": {lab: sum(1 for s in stars if s["null_label"] == lab)
                        for lab in ("ECL_GAIA", "ECL_GAIA_SHALLOW", "NONE", "FEW_EPOCHS")},
        "gaia_known": {"n": len(known), "n_flagged": len(kflag), "share_flagged": share_known},
        "gaia_unknown": {"n": len(unknown), "n_ecl": len(new_ecl), "n_shallow": len(new_sh),
                         "n_null_flags": len(null_unknown)},
        "median_dphase_ecl": med_dph, "n_dips_in_window_ecl": len(dph),
        "predictions": {
            "P1_known_share_ge_0.40": bool(known) and share_known >= P1_MIN_SHARE_KNOWN,
            "P2_null_share_le_0.02": bool(cls) and null_share <= P2_MAX_NULL_SHARE,
            "P3_median_dphase_le_0.015": bool(dph) and med_dph <= P3_MAX_MEDIAN_DPHASE,
            "P4_new_ecl_ge_10": len(new_ecl) >= P4_MIN_NEW_ECL,
        },
        "null_share": null_share,
        "new_candidates": [s["source_id"] for s in sorted(new_ecl, key=lambda s: -s["depth"])],
        "new_shallow": [s["source_id"] for s in sorted(new_sh, key=lambda s: -s["depth"])],
    }


def clean(o):
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


# ---------------------------------------------------------------- main run
def run(a):
    os.makedirs(a.out_dir, exist_ok=True)
    n_expect = int(fnum(tap(COUNT_QUERY)[0].get("n")))
    rows = tap(SAMPLE_QUERY)
    log("sample", len(rows), "expected", n_expect)
    if len(rows) != n_expect or n_expect == 0:
        log("SAMPLE COUNT MISMATCH")
        return 2
    orbits = {}
    for r in rows:
        sid = str(r["source_id"]).strip()
        orbits[sid] = {k: fnum(r.get(k)) for k in (
            "period", "t_periastron", "eccentricity", "arg_periastron", "semi_amplitude_primary",
            "semi_amplitude_secondary", "phot_g_mean_mag", "bp_rp", "ra", "dec")}
        orbits[sid]["type"] = str(r.get("nss_solution_type", "")).strip()
    ids = sorted(orbits)
    in_eb, cls, ecl_sol = set(), {}, set()
    for ch in chunks(ids, ID_CHUNK):
        q = ", ".join(ch)
        in_eb |= {str(r["source_id"]).strip() for r in tap(EB_QUERY.format(ids=q))}
        for r in tap(CLS_QUERY.format(ids=q)):
            cls[str(r["source_id"]).strip()] = str(r.get("best_class_name", "")).strip()
        for r in tap(NSS_QUERY.format(ids=q)):
            if "clipsing" in str(r.get("nss_solution_type", "")):
                ecl_sol.add(str(r["source_id"]).strip())
        time.sleep(PAUSE)
    log("gaia lookups: EB table", len(in_eb), "EclipsingSpectro", len(ecl_sol), "classified", len(cls))
    epochs = {}
    for i, ch in enumerate(chunks(ids, EPOCH_CHUNK)):
        for r in tap(EPOCH_QUERY.format(ids=", ".join(ch))):
            epochs[str(r["source_id"]).strip()] = epochs_from_row(r)
        if i % 5 == 0:
            log("epochs", len(epochs), "of", len(ids))
        time.sleep(PAUSE)
    with gzip.open(os.path.join(a.out_dir, "g8_dr3_blind_epochs.csv.gz"), "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source_id", "t", "g_mag", "rej"])
        for sid in ids:
            for t, m, rej in epochs.get(sid, []):
                w.writerow([sid, repr(t), repr(m), "1" if rej else "0"])
    stars = []
    for sid in ids:
        o = orbits[sid]
        ep = epochs.get(sid, [])
        c, cn = analyse_star(o, ep)
        k1, k2 = o["semi_amplitude_primary"], o["semi_amplitude_secondary"]
        m1 = g8.m1sin3i(k1, k2, o["period"], o["eccentricity"]) if all(
            math.isfinite(x) for x in (k1, k2)) else float("nan")
        m2 = g8.m1sin3i(k2, k1, o["period"], o["eccentricity"]) if all(
            math.isfinite(x) for x in (k1, k2)) else float("nan")
        stars.append({
            "source_id": sid, "type": o["type"], "P": o["period"], "Tp": o["t_periastron"],
            "e": o["eccentricity"], "omega": o["arg_periastron"], "K1": k1, "K2": k2,
            "m1sin3i": m1, "m2sin3i": m2, "G": o["phot_g_mean_mag"], "bp_rp": o["bp_rp"],
            "ra": o["ra"], "dec": o["dec"], "n_epochs_raw": len(ep),
            "in_gaia_eb": sid in in_eb, "gaia_ecl_solution": sid in ecl_sol,
            "gaia_class": cls.get(sid, ""),
            "gaia_known": known_label(sid in in_eb, sid in ecl_sol, cls.get(sid, "")),
            "label": c["label"], "null_label": cn["label"], "n": c["n"], "n_dips": c["n_dips"],
            "n_in": c["n_in"], "n_out": c["n_out"], "n_events": c["n_events"], "depth": c["depth"],
            "sd": c["sd"], "thr": c["thr"], "model": c["model"], "dips": c["dips"]})
    summary = grade(stars)
    summary.update({"version": VERSION, "rule": "sb2_ecl_dr4 %s classify (frozen)" % g8.VERSION,
                    "n_epochs_rows": len(epochs), "n_in_gaia_eb": len(in_eb),
                    "n_ecl_solution": len(ecl_sol)})
    with open(os.path.join(a.out_dir, "g8_dr3_blind.json"), "w") as fh:
        json.dump(clean({"summary": summary, "stars": stars}), fh, indent=1)
    cols = ["source_id", "type", "P", "Tp", "e", "omega", "K1", "K2", "m1sin3i", "m2sin3i", "G",
            "bp_rp", "ra", "dec", "n_epochs_raw", "n", "in_gaia_eb", "gaia_ecl_solution",
            "gaia_class", "gaia_known", "label", "null_label", "n_dips", "n_in", "n_out",
            "n_events", "depth", "sd", "thr", "model"]
    with open(os.path.join(a.out_dir, "g8_dr3_blind_stars.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for s in stars:
            w.writerow([s[c] if not isinstance(s[c], float) else ("%.8g" % s[c]) for c in cols])
    flagged_dir = os.path.join(a.out_dir, "flagged_epochs")
    os.makedirs(flagged_dir, exist_ok=True)
    for s in stars:
        if s["label"] in ("ECL_GAIA", "ECL_GAIA_SHALLOW") and not s["gaia_known"]:
            with open(os.path.join(flagged_dir, "%s_g.csv" % s["source_id"]), "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["t", "g_mag", "rej"])
                for t, m, rej in epochs.get(s["source_id"], []):
                    w.writerow([repr(t), repr(m), "1" if rej else "0"])
    print(json.dumps(clean(summary), indent=1))
    return 0


# ---------------------------------------------------------------- self-test
SAMPLE_VOT = """<?xml version="1.0" encoding="utf-8"?>
<VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
<RESOURCE type="results"><INFO name="QUERY_STATUS" value="OK"/>
<TABLE><FIELD name="source_id" datatype="long"/>
<FIELD name="g_transit_time" datatype="double" arraysize="*"/>
<FIELD name="g_transit_mag" datatype="double" arraysize="*"/>
<FIELD name="variability_flag_g_reject" datatype="boolean" arraysize="*"/>
<DATA><TABLEDATA>
<TR><TD>42</TD><TD>1707.5  1707.57  1800.25</TD><TD>8.30  NaN  8.27</TD><TD>False  False  True</TD></TR>
</TABLEDATA></DATA></TABLE></RESOURCE>
<RESOURCE type="meta" utype="adhoc:service"><PARAM name="accessURL" datatype="char" arraysize="*" value="x"/></RESOURCE>
</VOTABLE>"""

ERROR_VOT = """<?xml version="1.0"?><VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
<RESOURCE type="results"><INFO name="QUERY_STATUS" value="ERROR">bad query</INFO></RESOURCE></VOTABLE>"""


def self_test():
    checks = []
    rows = parse_votable(SAMPLE_VOT)
    checks.append(len(rows) == 1 and rows[0]["source_id"] == "42")
    ep = epochs_from_row(rows[0])
    checks.append(ep[0] == (1707.5, 8.30, False))
    checks.append(ep[1][2] is True and ep[2][2] is True)
    checks.append(g8.usable(ep) == ([1707.5], [8.30]))
    try:
        parse_votable(ERROR_VOT)
        checks.append(False)
    except RuntimeError:
        checks.append(True)
    checks.append(known_label(False, False, "ECL") and not known_label(False, False, "RS"))
    # synthetic eclipsing double-lined star through the frozen rule (DR3 reference shift)
    t, m = g8.synth(11, P=3.0, depth1=0.20, depth2=0.10)
    o = {"period": 3.0, "t_periastron": -DR3_REF, "eccentricity": float("nan"),
         "arg_periastron": float("nan")}
    c, cn = analyse_star(o, [(ti, mi, False) for ti, mi in zip(t, m)])
    checks.append(c["label"] == "ECL_GAIA" and cn["label"] == "NONE")
    t, m = g8.synth(12, P=3.0)
    c, cn = analyse_star(o, [(ti, mi, False) for ti, mi in zip(t, m)])
    checks.append(c["label"] == "NONE")
    st = [{"source_id": "1", "label": "ECL_GAIA", "null_label": "NONE", "gaia_known": False,
           "depth": 0.1, "dips": [{"dphase": 0.01}, {"dphase": -0.005}]},
          {"source_id": "2", "label": "NONE", "null_label": "NONE", "gaia_known": True,
           "depth": float("nan"), "dips": []},
          {"source_id": "3", "label": "FEW_EPOCHS", "null_label": "FEW_EPOCHS",
           "gaia_known": False, "depth": float("nan"), "dips": []}]
    gr = grade(st)
    checks.append(gr["n_classified"] == 2 and gr["gaia_unknown"]["n_ecl"] == 1
                  and abs(gr["median_dphase_ecl"] - 0.0075) < 1e-12
                  and gr["gaia_known"]["share_flagged"] == 0.0
                  and gr["new_candidates"] == ["1"])
    ok, bad = g8.self_test()
    checks.append(ok)
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
