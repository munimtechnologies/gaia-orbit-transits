# SPDX-License-Identifier: Apache-2.0
"""sb2_tier2 0.1.0: amendment 2 to runbook step g5, a registered second tier of the edge-on
double-lined (SB2) screen, calibrated on an independent set of eclipsing SB2s.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Pre-registration: findings/2026-11-24-g5-amendment-2-tier2.md (written before this ran).

Why: the tier-1 window 0.95 <= m1 sin^3 i / m1(binary_masses) <= 1.10 picked 11 of the 27
eclipsing SB2s with P < 8 d and a binary_masses m1 in Rowan et al. (2023, MNRAS 523, 2641; ASAS-SN
light-curve inclinations). 15 of the 16 it missed lie BELOW 0.95: Gaia's photometric m1 runs high.
Tier 2 = 0.85 <= r < 0.95 or 1.10 < r <= 1.15 (disjoint from tier 1, so no star is screened twice).

Reuses, unchanged: sb2_screen 0.1.0 (commit 0a8883c9; selection maths, TCE classification, VSX,
SIMBAD, ExoFOP) and sb2_screen_dr4 0.2.0 (commit f282d097; Villanova/VizieR lookups with controls,
UNVETTED-not-NEW rule, DR4 schema gate). This file only swaps the selection, optionally reads the
orbit rows from a saved CSV (DR3: data/sb2-edgeon-screen-v1/gaia_sb2_m1_p8.csv) and sends Gaia's
own-table lookups to ESA first, then the AIP mirror (CSV or VOTable replies).

Modes: --self-test; --orbits-csv FILE --schema gaiadr3 (DR3 tier 2, no ESA archive needed);
--schema gaiadr4 (release day). Exit: 0 ok; 2 data unavailable (re-file unchanged); 3 self-test FAIL.
"""
import argparse
import csv
import io
import json
import math
import os
import statistics
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

import sb2_screen as s0
import sb2_screen_dr4 as d4

VERSION = "0.1.0"
T2_LO, T1_LO, T1_HI, T2_HI = 0.85, 0.95, 1.10, 1.15
TAP_URLS = ("https://gea.esac.esa.int/tap-server/tap/sync", "https://gaia.aip.de/tap/sync")
TIER1_HALF_FULL, TIER1_TESTED = 56, 161     # sb2-edgeon-screen-v1 (S1: 46 HALF + 10 FULL of 161)

# Rowan et al. (2023) public table, https://asas-sn.osu.edu/binaries/mass-radius (61 rows, read
# 2026-11-24). All are eclipsing SB2s, so all count as KNOWN eclipsing systems here.
ROWAN2023_IDS = frozenset("""
1812688099719481600 1829977404695074048 1883645116973900160 40041022325608704 1927062769572959744
1930082990574022784 1966205727123049984 2034342875051663488 1431176943768690816 1486248285748866688
2272197682824665984 2909846325933123840 1861502430274947200 2920857385134567680 2964189378900408704
3034137456807305984 3079774920290246528 3090627649814362752 3144287734258258944 2300774058747886208
3305032211071549568 3388596533594327296 3467250755019227392 3666287029937549184 3043598651279075456
4265039659004076928 4330787980381097472 428267308105062528 4486661994344201344 4550480466716665856
4551624409786334720 4555294644020972288 4555928826016343936 4749481492841185792 4786545995454165504
453147263375440384 4955891883011009536 5347923063144824448 5410117178887541120 5521627135610064896
5554607884532225792 5626609437844737920 5627090233664416896 533425940213217920 5779038308211078656
5921911426116769536 509431332327692032 5339144356205089408 5380580890642502144 6085164060740783744
681609355666984192 690885522954174080 5990114407279275904 154197232963101568 6872490080733322112
947509303493752832 1204875013864088576 1272930282497618048 1387290280744129152 1762094209603752192
2020319428856066432
""".split())

# The 27 Rowan systems with P < 8 d that are in the saved DR3 SB2+M1 sample:
# source_id -> (Rowan incl_binary in deg, r computed BY HAND on 2026-11-24 for cross-checking).
ROWAN_CAL = {
    "1966205727123049984": (88.2816665163082, 0.886),
    "2964189378900408704": (84.558411998425, 0.975),
    "2034342875051663488": (89.5863477295785, 0.989),
    "1762094209603752192": (81.0740096897683, 0.242),
    "1431176943768690816": (89.0613780734221, 0.701),
    "428267308105062528": (83.9750809760216, 0.944),
    "690885522954174080": (84.7746391013844, 0.985),
    "1486248285748866688": (80.9947203991213, 0.953),
    "1930082990574022784": (83.3486949092954, 0.757),
    "681609355666984192": (79.8925051801866, 0.914),
    "2272197682824665984": (88.7295338352118, 0.918),
    "4265039659004076928": (84.2881486703236, 1.056),
    "3144287734258258944": (89.392474852146, 1.022),
    "5627090233664416896": (84.650877589546, 1.160),
    "3079774920290246528": (78.7160232903614, 0.932),
    "6872490080733322112": (75.4314459828846, 0.812),
    "4550480466716665856": (89.4227735953555, 0.991),
    "533425940213217920": (87.4288598797837, 0.923),
    "2020319428856066432": (82.0007028660954, 0.893),
    "3305032211071549568": (88.8374157017597, 0.862),
    "453147263375440384": (84.3133015800807, 0.889),
    "1387290280744129152": (87.2510275007522, 1.055),
    "1829977404695074048": (74.7001520904908, 0.865),
    "4749481492841185792": (89.8223750048997, 0.990),
    "5554607884532225792": (85.3813227034731, 1.002),
    "6085164060740783744": (85.4611293130916, 1.039),
    "4786545995454165504": (84.1617792483506, 0.825),
}
HAND_TOL = 0.005
# Registered expectation (from the hand values): exactly these 10 fall in tier 2.
ROWAN_TIER2_EXPECTED = frozenset(k for k, (_, r) in ROWAN_CAL.items()
                                 if T2_LO <= r < T1_LO or T1_HI < r <= T2_HI)

log = s0.log
fnum = s0.fnum


# ================================================================ pure helpers
def ratio_of(row):
    """r = m1 sin^3 i / m1 for one orbit row, or nan."""
    P, k1, k2 = fnum(row.get("period")), fnum(row.get("semi_amplitude_primary")), \
        fnum(row.get("semi_amplitude_secondary"))
    m1 = fnum(row.get("m1"))
    if not (P < s0.P_MAX and k1 > 0 and k2 > 0 and m1 > 0):
        return float("nan")
    return s0.m1sin3i(k1, k2, P, fnum(row.get("eccentricity"))) / m1


def tier_of(r):
    if not math.isfinite(r):
        return 0
    if T1_LO <= r <= T1_HI:
        return 1
    if T2_LO <= r < T1_LO or T1_HI < r <= T2_HI:
        return 2
    return 0


def select_tier2(rows):
    """Drop-in for sb2_screen.select_rows: one row per source, tier 2 only, adds m1sin3i/s3_ratio."""
    out, seen = [], set()
    for r in rows:
        sid = str(r.get("source_id", "")).strip()
        if not sid or sid in seen:
            continue
        ratio = ratio_of(r)
        if tier_of(ratio) != 2:
            continue
        seen.add(sid)
        rr = dict(r)
        rr["source_id"] = sid
        rr["m1sin3i"] = ratio * fnum(r.get("m1"))
        rr["s3_ratio"] = ratio
        out.append(rr)
    return out


def parse_tap_reply(text):
    """CSV or VOTable (TABLEDATA) -> list of dicts. Raises ValueError if neither."""
    t = (text or "").lstrip()
    if t.startswith("<"):
        if "QUERY_STATUS" in t and 'value="ERROR"' in t:
            raise ValueError("TAP error reply")
        root = ET.fromstring(t)
        names = [el.get("name") for el in root.iter() if el.tag.split("}")[-1] == "FIELD"]
        if not names:
            raise ValueError("VOTable without FIELDs")
        rows = []
        for tr in root.iter():
            if tr.tag.split("}")[-1] != "TR":
                continue
            vals = [(td.text or "").strip() for td in tr if td.tag.split("}")[-1] == "TD"]
            rows.append(dict(zip(names, vals)))
        return rows
    if not t or "," not in t.splitlines()[0]:
        raise ValueError("not CSV: %r" % t[:80])
    return list(csv.DictReader(t.splitlines()))


def make_tap(urls, orbit_query=None, orbit_rows=None):
    """A replacement for sb2_screen.tap: the orbit query is answered from orbit_rows (if given);
    every other query goes to each URL in turn until one gives a parsable reply."""
    def tap(query):
        if orbit_rows is not None and query == orbit_query:
            return [dict(r) for r in orbit_rows]
        last = None
        for url in urls:
            body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                           "RESPONSEFORMAT": "csv", "QUERY": query}).encode()
            try:
                text = s0.http_get(url, timeout=300, tries=2, data=body).decode("utf-8", "replace")
                return parse_tap_reply(text)
            except Exception as exc:
                last = "%s: %r" % (url, exc)
                log("TAP endpoint failed", last[:200])
        raise RuntimeError("all TAP endpoints failed: %s" % (last or "")[:300])
    return tap


def full_cols():
    return {"nss_two_body_orbit": set(d4.REQ_NSS), "gaia_source": set(d4.REQ_GS),
            "binary_masses": set(d4.REQ_BM)}


def rowan_calibration(orbit_rows):
    """Recompute r for the 27 Rowan systems from the orbit rows; compare with the hand values."""
    by_id = {}
    for r in orbit_rows:
        by_id.setdefault(str(r.get("source_id", "")).strip(), r)
    out = []
    for sid, (incl, hand) in sorted(ROWAN_CAL.items()):
        row = by_id.get(sid)
        r = ratio_of(row) if row else float("nan")
        s3 = math.sin(math.radians(incl)) ** 3
        out.append({"source_id": sid, "rowan_incl_deg": incl, "sin3i": s3, "r_code": r,
                    "r_hand": hand, "hand_agrees": (abs(r - hand) <= HAND_TOL) if math.isfinite(r)
                    else False, "tier": tier_of(r), "mdyn_over_m1": r / s3 if math.isfinite(r)
                    else float("nan")})
    return out


def summarize_cal(cal):
    ok = [c for c in cal if math.isfinite(c["r_code"])]
    good = [c["mdyn_over_m1"] for c in ok if c["source_id"] != "1762094209603752192"]
    tiers = [c["tier"] for c in ok]
    return {"n": len(cal), "n_found": len(ok),
            "n_hand_agrees": sum(1 for c in cal if c["hand_agrees"]),
            "label": "CAL_OK" if ok and all(c["hand_agrees"] for c in cal) else "CAL_DIFFERS",
            "n_tier1": tiers.count(1), "n_tier2": tiers.count(2), "n_outside": tiers.count(0),
            "n_below_t1": sum(1 for c in ok if c["r_code"] < T1_LO),
            "median_mdyn_over_m1_excl_badK": statistics.median(good) if good else float("nan"),
            "mean_mdyn_over_m1_excl_badK": statistics.mean(good) if good else float("nan"),
            "note": "1762094209603752192 excluded from the median/mean: Gaia K2 = 28 vs K1 = 144 "
                    "km/s (q = 5.1), an implausible double-lined solution"}


def read_rows(src):
    text = d4.read_text(src)
    return list(csv.DictReader(io.StringIO(text)))


def post_grade(out_dir, schema):
    """Tier-2 grades from the files sb2_screen_dr4.screen wrote."""
    with open(os.path.join(out_dir, "g5_summary.json")) as fh:
        summ = json.load(fh)
    with open(os.path.join(out_dir, "g5_screen.csv"), newline="") as fh:
        recs = list(csv.DictReader(fh))
    meta = summ.get("meta", {})
    g = summ.get("grades", {})
    tested = [r for r in recs if r.get("status") == "OK"]
    hf = [r for r in tested if r.get("tce_class") in ("HALF", "FULL")]
    share = len(hf) / len(tested) if tested else float("nan")
    t1 = TIER1_HALF_FULL / TIER1_TESTED
    sel_ids = {r.get("source_id") for r in recs}
    rowan_sel = sorted(ROWAN_TIER2_EXPECTED & sel_ids) if schema == "gaiadr3" else []
    cands, known_rowan = [], []
    for r in tested:
        if r.get("new_v2") != "NEW_V2":
            continue
        if r.get("source_id") in ROWAN2023_IDS:
            known_rowan.append(r.get("source_id"))
            continue
        cands.append({k: r.get(k) for k in ("source_id", "tic", "G", "P_gaia", "s3_ratio",
                                            "tce_class", "tce_best_id", "tce_best_period",
                                            "tce_best_depth_ppm", "tce_best_snr", "ra", "dec")})
    unv = [r.get("tic") for r in tested if r.get("new_v2") == "UNVETTED"]
    res = {
        "version": VERSION, "schema": schema,
        "T2_0": {"n_selected": meta.get("n_selected"), "n_orbit_rows": meta.get("n_orbit_rows"),
                 "predicted": "120-300 (70%)"},
        "T2_R": ({"expected": len(ROWAN_TIER2_EXPECTED), "selected": len(rowan_sel),
                  "missing": sorted(ROWAN_TIER2_EXPECTED - set(rowan_sel)),
                  "label": "SELECTION_OK" if len(rowan_sel) == len(ROWAN_TIER2_EXPECTED)
                  else "SELECTION_DIFFERS"} if schema == "gaiadr3" else {"label": "NOT_APPLICABLE"}),
        "T2_1": {"controls": g.get("S3"), "label": (g.get("S3") or {}).get("label")},
        "T2_2": {"n_tested": len(tested), "n_half_full": len(hf), "share": share,
                 "share_ci95": s0.wilson(len(hf), len(tested)), "tier1_share": t1,
                 "label": ("UNTESTABLE" if len(tested) < 20 else
                           "LOWER" if share < t1 else "NOT_LOWER")},
        "T2_3": {"n_candidates": len(cands), "candidates": cands, "rowan_relabelled": known_rowan,
                 "n_unvetted": len(unv), "unvetted": unv,
                 "label": "YES" if cands else "NO"},
        "gaia_tables_error": meta.get("gaia_tables_error", ""),
    }
    if res["gaia_tables_error"]:
        res["T2_3"]["note"] = ("Gaia's own EB tables were unreachable, so candidates were not "
                               "checked against them; treat every candidate as UNVETTED.")
    return res


# ================================================================ self-test
def self_test():
    checks = []
    base = {"source_id": "1", "period": "3.0", "semi_amplitude_primary": "100",
            "semi_amplitude_secondary": "100", "eccentricity": ""}
    ms = s0.m1sin3i(100.0, 100.0, 3.0, 0.0)
    rows = []
    for i, rr in enumerate((0.80, 0.86, 0.94, 0.951, 1.00, 1.099, 1.12, 1.149, 1.16)):
        rows.append(dict(base, source_id=str(100 + i), m1=repr(ms / rr)))
    sel = select_tier2(rows + [dict(rows[1])])
    got = sorted(round(r["s3_ratio"], 4) for r in sel)
    checks.append(got == [0.86, 0.94, 1.12, 1.149])                        # 0
    checks.append(tier_of(0.95) == 1 and tier_of(1.10) == 1 and tier_of(0.85) == 2)  # 1
    checks.append(tier_of(float("nan")) == 0 and tier_of(1.151) == 0)      # 2
    checks.append(len(ROWAN2023_IDS) == 61 and len(ROWAN_CAL) == 27)       # 3
    checks.append(len(ROWAN_TIER2_EXPECTED) == 10)                         # 4
    checks.append(all(k in ROWAN2023_IDS for k in ROWAN_CAL))              # 5
    # the screen's published value for 2964189378900408704 (s3_ratio 0.974733) is reproduced
    row = {"source_id": "2964189378900408704", "period": "3.1221237290835075",
           "eccentricity": "0.007255955938045943", "semi_amplitude_primary": "94.52205411035436",
           "semi_amplitude_secondary": "96.0731126161363", "m1": "1.1581855"}
    checks.append(abs(ratio_of(row) - 0.9747326824832203) < 1e-6)          # 6
    vot = ('<?xml version="1.0"?><VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE>'
           '<INFO name="QUERY_STATUS" value="OK"/><TABLE><FIELD name="source_id" datatype="long"/>'
           '<FIELD name="best_class_name" datatype="char"/><DATA><TABLEDATA>'
           '<TR><TD>2034342875051663488</TD><TD>ECL</TD></TR><TR><TD>5</TD><TD>RS</TD></TR>'
           '</TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>')
    pr = parse_tap_reply(vot)
    checks.append(len(pr) == 2 and pr[0]["source_id"] == "2034342875051663488"
                  and pr[0]["best_class_name"] == "ECL")                   # 7
    pc = parse_tap_reply("source_id,best_class_name\n7,ECL\n")
    checks.append(pc == [{"source_id": "7", "best_class_name": "ECL"}])    # 8
    try:
        parse_tap_reply("<html>502</html>")
        checks.append(False)                                               # 9
    except Exception:
        checks.append(True)
    t = make_tap(("http://127.0.0.1:9/none",), orbit_query="Q", orbit_rows=[{"a": "1"}])
    checks.append(t("Q") == [{"a": "1"}])                                  # 10
    ok = all(checks)
    return ok, [i for i, c in enumerate(checks) if not c]


# ================================================================ main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--orbits-csv", default="")
    ap.add_argument("--schema", default="gaiadr4")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-tces", type=int, default=40)
    a = ap.parse_args(argv)
    ok, bad = self_test()
    print("SELF_TEST", "PASS" if ok else "FAIL", bad, flush=True)
    if a.self_test or not ok:
        return 0 if ok else 3
    os.makedirs(a.out_dir, exist_ok=True)
    orbit_rows = None
    if a.orbits_csv:
        try:
            orbit_rows = read_rows(a.orbits_csv)
        except Exception as exc:
            json.dump({"error": "orbits csv unavailable: %r" % exc},
                      open(os.path.join(a.out_dir, "tier2_summary.json"), "w"), indent=1)
            return 2
        cal = rowan_calibration(orbit_rows)
        with open(os.path.join(a.out_dir, "rowan_calibration.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cal[0].keys()))
            w.writeheader()
            for c in cal:
                w.writerow({k: s0.fmt(v) for k, v in c.items()})
        cal_sum = summarize_cal(cal)
        print("CALIBRATION", json.dumps(s0.clean(cal_sum)), flush=True)
        d4.discover = lambda schema: full_cols()
    else:
        cal_sum = {"label": "NOT_APPLICABLE"}
    s0.tap = make_tap(TAP_URLS, s0.ORBIT_QUERY.format(s=a.schema), orbit_rows)
    s0.select_rows = select_tier2
    rc = d4.screen(a)
    if not os.path.exists(os.path.join(a.out_dir, "g5_screen.csv")):
        return rc or 2
    res = post_grade(a.out_dir, a.schema)
    res["calibration"] = cal_sum
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    json.dump(s0.clean(res), open(os.path.join(a.out_dir, "tier2_summary.json"), "w"), indent=1)
    print(json.dumps(s0.clean({k: (v.get("label") if isinstance(v, dict) else v)
                               for k, v in res.items() if k.startswith("T2_")})), flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
