# SPDX-License-Identifier: Apache-2.0
"""sb2_screen 0.1.0: which of Gaia DR3's edge-on double-lined binaries eclipse in TESS, and which
of those are new?

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Pre-registration: findings/2026-11-22-sb2-screen-prereg.md (written before this job ran; the
pilot of 20 stars is in findings/2026-11-22-tic400170926-eclipsing-twin.md section 6).

Sample (the pilot's rule): Gaia DR3 nss_two_body_orbit SB2 solutions with binary_masses method
SB2+M1, P < 8 d, and M1 sin^3 i = 1.036149e-7 (1 - e^2)^1.5 (K1 + K2)^2 K2 P between 0.95 and
1.10 times binary_masses.m1 (e = 0 when not fitted). The pilot found 184.

For every star: Gaia DR3 -> TIC (ExoFOP), the SPOC TCE list and each TCE's period, depth and S/N
(exo.MAST DV), and for stars with a TCE at P or P/2: VSX, the Villanova live TESS EB catalogue,
ExoFOP TOIs, SIMBAD (Harvard mirror), and Gaia DR3's own eclipsing tables.

Exit codes: 0 ok; 2 data unavailable (re-file unchanged); 3 self-test failed.
"""
import argparse
import csv
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "0.1.0"

# ---- pre-registered constants (findings/2026-11-22-sb2-screen-prereg.md) ----
P_MAX = 8.0
S3_LO, S3_HI = 0.95, 1.10
MASS_CONST = 1.036149e-7
MATCH_TOL = 0.005                   # |P_tce / (m P_gaia) - 1| <= 0.5 %
MATCH_FACTORS = (0.5, 1.0)
MIN_TSNR = 7.1
EXPECTED_N = 184
S1_MIN_N = 10
S1_HI, S1_LO = 0.80, 0.50
S3_CTRL_MIN = 0.80
VSX_RADIUS_DEG = 30.0 / 3600.0
SIMBAD_RADIUS_ARCSEC = 10
PILOT_IDS = (
    "426458577120017280", "6075172729866344320", "1606282829146245248", "2227350905632198656",
    "609041794391364992", "5697475844169557248", "5607593418598052992", "231465069010376320",
    "5508748010453477760", "5829949510529000192", "1094968140790112128", "1907779946960802944",
    "5191259080130349056", "1117556164072536192", "3560730099741500928", "1226781889693185408",
    "3450611154067089408", "5306298301712596992", "2995056243702062080", "4301711773362344192")

TAP_URL = "https://gea.esac.esa.int/tap-server/tap/sync"
EXOFOP_TIC = "https://exofop.ipac.caltech.edu/tess/gototicid.php?target=Gaia%%20DR2%%20%s&json"
EXOFOP_TARGET = "https://exofop.ipac.caltech.edu/tess/target.php?id=%s&json"
TCE_LIST = "https://exo.mast.stsci.edu/api/v0.1/dvdata/tess/%s/tces/"
TCE_INFO = "https://exo.mast.stsci.edu/api/v0.1/dvdata/tess/%s/info/?tce=%s&sector=%s"
VSX_URL = "https://vsx.aavso.org/index.php?view=api.list&ra=%.6f&dec=%.6f&radius=%.6f&format=json"
VILLANOVA = "http://tessebs.villanova.edu/%010d"
SIMBAD = ("https://simbad.cfa.harvard.edu/simbad/sim-coo?Coord=%.6f%%20%+.6f&Radius=%d"
          "&Radius.unit=arcsec&output.format=ASCII")
UA = "gaia-orbit-transits/sb2_screen (MV2, Munim, Inc.; open research)"
HTTP_TIMEOUT = 90
PAUSE = 0.3

ORBIT_QUERY = (
    "SELECT o.source_id, o.nss_solution_type, o.period, o.period_error, o.eccentricity, "
    "o.semi_amplitude_primary, o.semi_amplitude_primary_error, o.semi_amplitude_secondary, "
    "o.semi_amplitude_secondary_error, b.m1, b.m2, g.phot_g_mean_mag, g.ra, g.dec "
    "FROM {s}.nss_two_body_orbit AS o "
    "JOIN {s}.binary_masses AS b ON o.source_id = b.source_id "
    "JOIN {s}.gaia_source AS g ON o.source_id = g.source_id "
    "WHERE o.nss_solution_type LIKE 'SB2%' AND b.combination_method = 'SB2+M1' "
    "AND o.period < 8")

KEYS = ["source_id", "in_pilot", "G", "ra", "dec", "P_gaia", "P_gaia_err", "ecc", "K1", "K2",
        "m1", "m2", "m1sin3i", "s3_ratio", "tic", "n_tce", "tce_class", "tce_best_id",
        "tce_best_period", "tce_best_factor", "tce_best_dev_pct", "tce_best_depth_ppm",
        "tce_best_snr", "tce_best_dur_h", "vsx_names", "vsx_types", "vsx_eclipsing",
        "villanova", "toi", "simbad_eb", "simbad_main", "gaia_eb", "gaia_ecl_sb2", "gaia_class",
        "status", "error"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ================================================================ pure helpers
def fnum(v, default=float("nan")):
    try:
        if v is None:
            return default
        s = str(v).strip().strip('"')
        if s in ("", "null", "NULL", "NaN", "nan", "None", "--"):
            return default
        x = float(s)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def m1sin3i(k1, k2, period, ecc):
    """Minimum primary mass (M_sun) of a double-lined orbit; K in km/s, P in days."""
    e = ecc if (ecc is not None and math.isfinite(ecc)) else 0.0
    return MASS_CONST * (1.0 - e * e) ** 1.5 * (k1 + k2) ** 2 * k2 * period


def select_rows(rows):
    """The pilot's rule. One row per source (first kept). Adds m1sin3i and s3_ratio."""
    out, seen = [], set()
    for r in rows:
        sid = str(r.get("source_id", "")).strip()
        if not sid or sid in seen:
            continue
        P, k1, k2 = fnum(r.get("period")), fnum(r.get("semi_amplitude_primary")), \
            fnum(r.get("semi_amplitude_secondary"))
        m1 = fnum(r.get("m1"))
        if not (P < P_MAX and k1 > 0 and k2 > 0 and m1 > 0):
            continue
        ms = m1sin3i(k1, k2, P, fnum(r.get("eccentricity")))
        ratio = ms / m1
        if S3_LO <= ratio <= S3_HI:
            seen.add(sid)
            rr = dict(r)
            rr["source_id"] = sid
            rr["m1sin3i"] = ms
            rr["s3_ratio"] = ratio
            out.append(rr)
    return out


def parse_tic(text):
    m = re.search(r'"TIC"\s*:\s*"?(\d+)', text or "")
    return m.group(1) if m else None


def parse_tce_list(text):
    """'{"TCE":["s0002-s0072:TCE_1", ...]}' -> [(sector_range, tce_number)]."""
    out = []
    for m in re.finditer(r"(s\d{4}-s\d{4}):TCE_?(\d+)", text or ""):
        out.append((m.group(1), int(m.group(2))))
    return out


def parse_tce_info(obj):
    h = obj.get("DV Data Header", {}) if isinstance(obj, dict) else {}
    return {"period": fnum(h.get("TPERIOD")), "depth_ppm": fnum(h.get("TDEPTH")),
            "snr": fnum(h.get("TSNR")), "epoch": fnum(h.get("TEPOCH")),
            "dur_h": fnum(h.get("TDUR"))}


def match_factor(p_tce, p_gaia, tol=MATCH_TOL):
    """-> (factor, deviation) for the closest of MATCH_FACTORS within tol, else (None, dev)."""
    best = (None, float("inf"))
    if not (p_tce > 0 and p_gaia > 0):
        return best
    for m in MATCH_FACTORS:
        dev = p_tce / (m * p_gaia) - 1.0
        if abs(dev) < abs(best[1]):
            best = (m, dev)
    return best if abs(best[1]) <= tol else (None, best[1])


def classify_tces(tces, p_gaia):
    """tces: list of dicts (id, period, depth_ppm, snr, dur_h). -> (class, best tce, factor, dev).
    HALF: some TCE (S/N >= MIN_TSNR) at P/2; FULL: none at P/2 but one at P; OTHER: TCEs, none
    matching; NONE: no TCE with S/N >= MIN_TSNR. A TCE whose DV header gives no S/N is kept
    (SPOC only makes a TCE above its own threshold). Best = highest-S/N matching TCE."""
    def snr_of(t):
        s = t.get("snr", float("nan"))
        return s if (s is not None and math.isfinite(s)) else None

    good = [t for t in tces if snr_of(t) is None or snr_of(t) >= MIN_TSNR]
    if not good:
        return "NONE", None, None, None
    matched = []
    for t in good:
        f, dev = match_factor(t["period"], p_gaia)
        if f is not None:
            matched.append((f, -(snr_of(t) or 0.0), t, dev))
    if not matched:
        return "OTHER", None, None, None
    halves = [m for m in matched if m[0] == 0.5]
    pool = halves if halves else matched
    pool.sort(key=lambda m: m[1])
    f, _, t, dev = pool[0]
    return ("HALF" if halves else "FULL"), t, f, dev


def villanova_status(html):
    if not html:
        return None
    if "No associated EB entries found" in html:
        return False
    if re.search(r"In catalog.{0,600}?True", html, re.S):
        return True
    return None


def vsx_objects(obj):
    if not isinstance(obj, dict):
        return []
    v = obj.get("VSXObjects", {})
    v = v.get("VSXObject", []) if isinstance(v, dict) else v
    if isinstance(v, dict):
        v = [v]
    return [x for x in (v or []) if isinstance(x, dict)]


def is_eclipsing_type(vt):
    for tok in re.split(r"[+|/:\s,()]+", str(vt or "").upper()):
        if tok.startswith("E") and tok not in ("EP", "ELL", ""):
            return True
    return False


def simbad_flags(text):
    """-> (has an EB* object, main identifier or '')."""
    if not text:
        return None, ""
    eb = bool(re.search(r"(^|[\s|])EB\*", text))
    m = re.search(r"^Object\s+(.+?)\s+---", text, re.M)
    return eb, (m.group(1).strip() if m else "")


def is_new(r):
    """Eclipsing at P or P/2 and in none of the catalogues checked (None counts as not checked)."""
    if r.get("tce_class") not in ("HALF", "FULL"):
        return False
    known = (r.get("vsx_eclipsing") is True or r.get("villanova") is True or bool(r.get("toi"))
             or r.get("simbad_eb") is True or r.get("gaia_eb") is True
             or r.get("gaia_ecl_sb2") is True
             or str(r.get("gaia_class", "")).upper().startswith("ECL"))
    return not known


def wilson(k, n, z=1.959964):
    if n <= 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def grade(recs, n_selected, pilot_present):
    tested = [r for r in recs if r.get("status") == "OK"]
    with_tce = [r for r in tested if r.get("tce_class") in ("HALF", "FULL", "OTHER")]
    half = [r for r in with_tce if r["tce_class"] == "HALF"]
    full = [r for r in with_tce if r["tce_class"] == "FULL"]
    s1n, s1k = len(with_tce), len(half)
    share = s1k / s1n if s1n else float("nan")
    if s1n < S1_MIN_N:
        s1 = "UNTESTABLE"
    elif share >= S1_HI:
        s1 = "HALF_DOMINANT"
    elif share >= S1_LO:
        s1 = "MIXED"
    else:
        s1 = "NOT_DOMINANT"
    ctrl = [r for r in with_tce if r.get("vsx_eclipsing") is True]
    ctrl_ok = [r for r in ctrl if r["tce_class"] in ("HALF", "FULL")]
    c_share = len(ctrl_ok) / len(ctrl) if ctrl else float("nan")
    s3 = ("UNTESTABLE" if len(ctrl) < 3 else
          "CONTROLS_OK" if c_share >= S3_CTRL_MIN else "CONTROLS_FAIL")
    new = [r for r in tested if is_new(r)]
    new_x = [r for r in new if not r.get("in_pilot")]
    return {
        "S0": {"n_selected": n_selected, "expected": EXPECTED_N,
               "pilot_present": pilot_present, "pilot_n": len(PILOT_IDS),
               "label": ("REPLICATES" if n_selected == EXPECTED_N
                         and pilot_present == len(PILOT_IDS) else "DIFFERS")},
        "S1": {"n_with_tce": s1n, "n_half": s1k, "n_full": len(full),
               "n_other": s1n - s1k - len(full), "share_half": share,
               "share_half_ci95": wilson(s1k, s1n), "label": s1},
        "S2": {"n_new": len(new), "n_new_excl_pilot": len(new_x),
               "new": [{"source_id": r["source_id"], "tic": r.get("tic"), "G": r.get("G"),
                        "P_gaia": r.get("P_gaia"), "tce_class": r.get("tce_class"),
                        "depth_ppm": r.get("tce_best_depth_ppm"),
                        "snr": r.get("tce_best_snr"), "in_pilot": r.get("in_pilot")}
                       for r in new],
               "label_ge3": "YES" if len(new_x) >= 3 else "NO",
               "label_ge1": "YES" if len(new_x) >= 1 else "NO"},
        "S3": {"n_controls": len(ctrl), "n_ok": len(ctrl_ok), "share": c_share, "label": s3},
        "counts": {"tested": len(tested), "no_tic": sum(1 for r in recs if r.get("status") == "NO_TIC"),
                   "errors": sum(1 for r in recs if r.get("status") == "ERROR"),
                   "tce_none": sum(1 for r in tested if r.get("tce_class") == "NONE")},
    }


# ================================================================ network
def http_get(url, timeout=HTTP_TIMEOUT, tries=3, data=None, accept_404=False):
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA},
                                         method="POST" if data is not None else "GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            if accept_404 and exc.code == 404:
                return b""
            last = exc
        except Exception as exc:
            last = exc
        log("HTTP retry", url[:100], a + 1, repr(last)[:160])
        time.sleep(5 * (a + 1))
    raise RuntimeError("HTTP failed %s: %r" % (url[:100], last))


def tap(query):
    body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                   "QUERY": query}).encode()
    text = http_get(TAP_URL, timeout=300, tries=3, data=body).decode("utf-8", "replace")
    return list(csv.DictReader(text.splitlines()))


def tap_ids(query_fmt, ids, schema, chunk=150):
    out = []
    for i in range(0, len(ids), chunk):
        lst = ",".join(ids[i:i + chunk])
        out += tap(query_fmt.format(s=schema, ids=lst))
    return out


def get_json(url):
    try:
        return json.loads(http_get(url).decode("utf-8", "replace"))
    except Exception as exc:
        log("json failed", url[:100], repr(exc)[:120])
        return None


# ================================================================ main
def run(args):
    os.makedirs(args.out_dir, exist_ok=True)
    meta = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "schema": args.schema}
    try:
        rows = tap(ORBIT_QUERY.format(s=args.schema))
    except Exception as exc:
        log("TAP failed", repr(exc)[:200])
        json.dump({"error": "Gaia TAP unavailable: %r" % exc, "meta": meta},
                  open(os.path.join(args.out_dir, "sb2_screen_summary.json"), "w"), indent=1)
        return 2
    log("orbit rows", len(rows))
    with open(os.path.join(args.out_dir, "gaia_sb2_m1_p8.csv"), "w", newline="") as fh:
        if rows:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    sel = select_rows(rows)
    sel.sort(key=lambda r: fnum(r.get("phot_g_mean_mag"), 99))
    ids = [r["source_id"] for r in sel]
    pilot_present = sum(1 for p in PILOT_IDS if p in set(ids))
    log("selected", len(sel), "pilot present", pilot_present)
    if not sel:
        json.dump({"error": "no rows selected (orbit rows %d)" % len(rows), "meta": meta},
                  open(os.path.join(args.out_dir, "sb2_screen_summary.json"), "w"), indent=1)
        return 2
    if args.limit:
        sel = sel[:args.limit]
    # Gaia's own eclipsing information
    eb_ids, ecl_sb2, gclass = set(), set(), {}
    try:
        eb_ids = {r["source_id"] for r in tap_ids(
            "SELECT source_id FROM {s}.vari_eclipsing_binary WHERE source_id IN ({ids})",
            ids, args.schema)}
        ecl_sb2 = {r["source_id"] for r in tap(
            "SELECT source_id FROM %s.binary_masses WHERE combination_method = "
            "'Eclipsing+SB2'" % args.schema)}
        for r in tap_ids("SELECT source_id, best_class_name FROM {s}.vari_classifier_result "
                         "WHERE source_id IN ({ids})", ids, args.schema):
            gclass[r["source_id"]] = r.get("best_class_name", "")
    except Exception as exc:
        log("Gaia eclipse tables failed", repr(exc)[:200])
        meta["gaia_tables_error"] = repr(exc)[:200]
    meta.update({"n_gaia_eb": len(eb_ids), "n_ecl_sb2_all": len(ecl_sb2)})
    recs = []
    for n, r in enumerate(sel):
        sid = r["source_id"]
        rec = {k: "" for k in KEYS}
        rec.update({"source_id": sid, "in_pilot": sid in PILOT_IDS,
                    "G": fnum(r.get("phot_g_mean_mag")), "ra": fnum(r.get("ra")),
                    "dec": fnum(r.get("dec")), "P_gaia": fnum(r.get("period")),
                    "P_gaia_err": fnum(r.get("period_error")), "ecc": fnum(r.get("eccentricity")),
                    "K1": fnum(r.get("semi_amplitude_primary")),
                    "K2": fnum(r.get("semi_amplitude_secondary")), "m1": fnum(r.get("m1")),
                    "m2": fnum(r.get("m2")), "m1sin3i": r["m1sin3i"], "s3_ratio": r["s3_ratio"],
                    "gaia_eb": sid in eb_ids, "gaia_ecl_sb2": sid in ecl_sb2,
                    "gaia_class": gclass.get(sid, "")})
        try:
            tic = parse_tic(http_get(EXOFOP_TIC % sid).decode("utf-8", "replace"))
            time.sleep(PAUSE)
            if not tic:
                rec["status"] = "NO_TIC"
                recs.append(rec)
                continue
            rec["tic"] = tic
            lst = parse_tce_list(http_get(TCE_LIST % tic, accept_404=True)
                                 .decode("utf-8", "replace"))
            time.sleep(PAUSE)
            tces = []
            for sector, num in lst[:args.max_tces]:
                info = get_json(TCE_INFO % (tic, num, sector))
                time.sleep(PAUSE)
                d = parse_tce_info(info or {})
                d["id"] = "%s:TCE_%d" % (sector, num)
                tces.append(d)
            rec["n_tce"] = len(lst)
            cls, best, f, dev = classify_tces(tces, rec["P_gaia"])
            rec["tce_class"] = cls
            if best:
                rec.update({"tce_best_id": best["id"], "tce_best_period": best["period"],
                            "tce_best_factor": f, "tce_best_dev_pct": 100.0 * dev,
                            "tce_best_depth_ppm": best["depth_ppm"],
                            "tce_best_snr": best["snr"], "tce_best_dur_h": best["dur_h"]})
            if cls in ("HALF", "FULL"):
                v = get_json(VSX_URL % (rec["ra"], rec["dec"], VSX_RADIUS_DEG))
                objs = vsx_objects(v) if v is not None else None
                if objs is not None:
                    rec["vsx_names"] = "|".join(o.get("Name", "") for o in objs)
                    rec["vsx_types"] = "|".join(o.get("VariabilityType", "") for o in objs)
                    rec["vsx_eclipsing"] = any(is_eclipsing_type(o.get("VariabilityType"))
                                               for o in objs)
                else:
                    rec["vsx_eclipsing"] = None
                time.sleep(PAUSE)
                try:
                    rec["villanova"] = villanova_status(
                        http_get(VILLANOVA % int(tic), accept_404=True).decode("utf-8", "replace"))
                except Exception:
                    rec["villanova"] = None
                time.sleep(PAUSE)
                t = get_json(EXOFOP_TARGET % tic)
                tois = (t or {}).get("tois") or []
                if not isinstance(tois, list):
                    tois = [tois]
                rec["toi"] = "|".join((str(x.get("toi", x.get("TOI", ""))) if isinstance(x, dict)
                                       else str(x)) or "TOI" for x in tois)
                time.sleep(PAUSE)
                try:
                    eb, main = simbad_flags(http_get(SIMBAD % (rec["ra"], rec["dec"],
                                                              SIMBAD_RADIUS_ARCSEC))
                                            .decode("utf-8", "replace"))
                except Exception:
                    eb, main = None, ""
                rec["simbad_eb"], rec["simbad_main"] = eb, main
                time.sleep(PAUSE)
            rec["status"] = "OK"
        except Exception as exc:
            rec["status"] = "ERROR"
            rec["error"] = repr(exc)[:300]
        recs.append(rec)
        log("[%d/%d]" % (n + 1, len(sel)), sid, rec.get("tic"), rec.get("status"),
            rec.get("tce_class"), "NEW" if is_new(rec) else "")
        if (n + 1) % 20 == 0:
            write_csv(os.path.join(args.out_dir, "sb2_screen.csv"), recs)
    write_csv(os.path.join(args.out_dir, "sb2_screen.csv"), recs)
    ok = sum(1 for r in recs if r.get("status") == "OK")
    g = grade(recs, len(ids), pilot_present)
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    json.dump(clean({"grades": g, "meta": meta}),
              open(os.path.join(args.out_dir, "sb2_screen_summary.json"), "w"), indent=1)
    print(json.dumps(clean({k: g[k].get("label", g[k].get("label_ge3")) for k in
                            ("S0", "S1", "S2", "S3")})))
    if ok < 0.5 * len(sel):
        return 2
    return 0


def write_csv(path, recs):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=KEYS)
        w.writeheader()
        for r in recs:
            w.writerow({k: fmt(r.get(k, "")) for k in KEYS})


def fmt(v):
    if isinstance(v, float):
        return "" if not math.isfinite(v) else repr(v)
    if v is None:
        return ""
    return v


def clean(o):
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--schema", default="gaiadr3")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-tces", type=int, default=40)
    a = ap.parse_args(argv)
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
