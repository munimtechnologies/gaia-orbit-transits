# SPDX-License-Identifier: Apache-2.0
"""sb2_ffiscan_t2 0.1.0 - the full-frame TESS fold of sb2_ffiscan 0.1.0, run on tier 2 of the
edge-on Gaia DR3 double-lined (SB2) sample.

Part of gaia-orbit-transits by MV2 of Munim, Inc. Made with AI agents working in his name.
Apache-2.0. Pre-registration: findings/2026-11-24-sb2-ffiscan-t2-prereg.md (written before any run).

Why: tier 2 (0.85 <= m1 sin^3 i / m1 < 0.95 or 1.10 < r <= 1.15; sb2_tier2 0.1.0) is screened by
sb2-tier2-dr3-v1 only against TESS pipeline (SPOC) detections, which exist only for 2-minute targets.
Stars seen only in full-frame images fall through. Example found by hand on 2026-11-24: HD 35131
(Gaia DR3 262216446435606016, TIC 309683389, G 9.11, P 4.0623 d, r = 0.869): no TCE, no TOI, no VSX
entry, no Gaia variability class.

Reused UNCHANGED, fetched at pinned commits by fetch_pinned.py:
  sb2_screen 0.1.0 (0a8883c9), sb2_screen_dr4 0.2.0 (f282d097), sb2_tier2 0.1.0 (ee76c7ff: tier
  selection, VOTable-capable TAP), sb2_ffiscan 0.1.0 (b53e2b3c: light curves, cleaning, box search,
  nulls, Gaia conjunction test, grading thresholds).
What this file adds: tier-2 sample from the saved orbit table (80be282), roles fixed BLIND from
catalogues before any light curve is read (control = VSX eclipsing, Gaia vari_eclipsing_binary,
Gaia classifier ECL*, or Rowan et al. 2023 member; toi = TESS Object of Interest; else target),
Gaia orbits from the AIP mirror first (the ESA archive closes 25 Nov 2026 for DR4), and a period
anchor tolerance of 1e-7 (relative) because mirror replies may round.
Exit: 0 ok; 2 data unavailable (re-file unchanged); 3 self-test FAIL.
"""
import argparse
import csv
import json
import math
import os
import shutil
import sys
import tempfile
import time

import sb2_screen as s0
import sb2_tier2 as t2
import sb2_ffiscan as F

VERSION = "0.1.0"
ORBITS_CSV = ("https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/"
              "80be282773812acc69c0e5d190abc25687de1f5a/data/sb2-edgeon-screen-v1/gaia_sb2_m1_p8.csv")
TAP_ORDER = ("https://gaia.aip.de/tap/sync", "https://gea.esac.esa.int/tap-server/tap/sync")
ANCHOR_REL = 1e-7
HD35131_SID, HD35131_TIC = "262216446435606016", 309683389
EXPECTED_N = (120, 300)
CHUNK = 100
log = s0.log
fnum = s0.fnum

EXTRA_COLS = ["s3_ratio", "gaia_eb", "gaia_class", "in_rowan", "toi"]


# ================================================================ pure helpers
def chunks(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def select(rows):
    """Tier-2 stars (sb2_tier2.select_tier2, unchanged), brightest first."""
    out = []
    for r in t2.select_tier2(rows):
        sid = r["source_id"]
        out.append({"source_id": sid, "name": "Gaia DR3 " + sid,
                    "G": fnum(r.get("phot_g_mean_mag")), "ra": fnum(r.get("ra")),
                    "dec": fnum(r.get("dec")), "P_screen": fnum(r.get("period")),
                    "P_screen_err": fnum(r.get("period_error")), "s3_ratio": r["s3_ratio"],
                    "vetted": "", "tce_class": ""})
    out.sort(key=lambda s: (s["G"] if math.isfinite(s["G"]) else 99.0, s["source_id"]))
    return out


def anchor_ok(orb, P_screen, rel=ANCHOR_REL):
    return bool(orb is not None and F.finite(orb.get("P")) and F.finite(P_screen)
                and abs(orb["P"] - P_screen) <= rel * P_screen and F.finite(orb.get("Tp")))


def role_of(s):
    """Fixed from catalogue flags only (no light curve has been read when this is called)."""
    if (s.get("vsx_eclipsing") is True or s.get("gaia_eb") is True
            or str(s.get("gaia_class", "") or "").upper().startswith("ECL") or s.get("in_rowan")):
        return "control"
    if s.get("toi"):
        return "toi"
    return "target"


def tois_from(obj):
    if not isinstance(obj, dict):
        return None
    tois = obj.get("tois") or []
    if not isinstance(tois, list):
        tois = [tois]
    return "|".join((str(x.get("toi", x.get("TOI", ""))) if isinstance(x, dict) else str(x)) or "TOI"
                    for x in tois)


def extras(recs, stars, meta):
    by = {r.get("source_id"): r for r in recs}
    h = by.get(HD35131_SID)
    keys = ("name", "tic", "role", "label", "snr", "null_max", "P_best", "depth_rel", "n_cycles",
            "phase", "phase_z", "sec", "sep", "authors", "n_sectors")
    return {
        "T2F_sample": {"n_selected": meta.get("n_selected"), "predicted": "%d-%d" % EXPECTED_N,
                       "in_range": (EXPECTED_N[0] <= (meta.get("n_selected") or 0) <= EXPECTED_N[1]),
                       "rowan_tier2_selected": meta.get("rowan_tier2_selected"),
                       "rowan_tier2_expected": len(t2.ROWAN_TIER2_EXPECTED),
                       "hd35131_selected": meta.get("hd35131_selected")},
        "HD35131": ({k: h.get(k) for k in keys} if h else {"label": "NOT_REACHED"}),
        "roles": {k: sum(1 for s in stars if s.get("role") == k) for k in ("control", "toi", "target")},
        "control_sources": {"vsx": sum(1 for s in stars if s.get("vsx_eclipsing") is True),
                            "gaia_eb": sum(1 for s in stars if s.get("gaia_eb") is True),
                            "gaia_class_ecl": sum(1 for s in stars if str(s.get("gaia_class", "")).upper()
                                                  .startswith("ECL")),
                            "rowan": sum(1 for s in stars if s.get("in_rowan"))},
        "vsx_unchecked": sum(1 for s in stars if s.get("vsx_eclipsing") is None),
        "no_tic": sum(1 for s in stars if not s.get("tic")),
    }


# ================================================================ network
def fetch_orbits(tap, ids):
    out = {}
    cols = "source_id, " + ", ".join(F.ORBIT_COLS)
    for part in chunks(list(ids), CHUNK):
        q = ("SELECT %s FROM gaiadr3.nss_two_body_orbit WHERE source_id IN (%s)"
             % (cols, ",".join(str(int(i)) for i in part)))
        for r in tap(q):
            sid = str(r.get("source_id", "")).strip().strip('"')
            if sid and (sid not in out or str(r.get("nss_solution_type", "")).strip('"').startswith("SB2")):
                out[sid] = r
    return out


def gaia_tables(tap, ids):
    eb, cls = set(), {}
    for part in chunks(list(ids), CHUNK):
        lst = ",".join(str(int(i)) for i in part)
        for r in tap("SELECT source_id FROM gaiadr3.vari_eclipsing_binary WHERE source_id IN (%s)" % lst):
            eb.add(str(r.get("source_id", "")).strip().strip('"'))
        for r in tap("SELECT source_id, best_class_name FROM gaiadr3.vari_classifier_result "
                     "WHERE source_id IN (%s)" % lst):
            cls[str(r.get("source_id", "")).strip().strip('"')] = str(r.get("best_class_name", "")).strip()
    return eb, cls


def lookup_tic(sid):
    try:
        return s0.parse_tic(s0.http_get(s0.EXOFOP_TIC % sid).decode("utf-8", "replace"))
    except Exception as exc:
        log("TIC lookup failed", sid, repr(exc)[:160])
        return None


# ================================================================ self-test
def self_test():
    checks = []
    ok_t2, bad = t2.self_test()
    checks.append(bool(ok_t2))                                                   # 0
    ms = s0.m1sin3i(100.0, 100.0, 3.0, 0.0)
    base = {"period": "3.0", "period_error": "0.0001", "semi_amplitude_primary": "100",
            "semi_amplitude_secondary": "100", "eccentricity": "", "ra": "10", "dec": "20"}
    rows = [dict(base, source_id=str(10 + i), m1=repr(ms / r), phot_g_mean_mag=repr(9.5 - i))
            for i, r in enumerate((0.80, 0.90, 1.00, 1.12))]
    sel = select(rows)
    checks.append([s["source_id"] for s in sel] == ["13", "11"])                 # 1 tier 2 only, by G
    row = {"source_id": HD35131_SID, "period": "4.062349795949258",
           "eccentricity": "0.052425326530381615", "semi_amplitude_primary": "96.12954958426585",
           "semi_amplitude_secondary": "85.04996780935767", "m1": "1.3467268"}
    r = t2.ratio_of(row)
    checks.append(abs(r - 0.869) < 0.005 and t2.tier_of(r) == 2)               # 2 hand value
    checks.append(anchor_ok({"P": 4.0623498, "Tp": 1.0}, 4.062349795949258))   # 3
    checks.append(not anchor_ok({"P": 4.0624, "Tp": 1.0}, 4.062349795949258))  # 4
    checks.append(not anchor_ok({"P": 4.062349795949258, "Tp": float("nan")}, 4.062349795949258))  # 5
    checks.append(not anchor_ok(None, 4.0))                                      # 6
    checks.append(role_of({"vsx_eclipsing": True}) == "control")                 # 7
    checks.append(role_of({"gaia_class": "ECL"}) == "control")                   # 8
    checks.append(role_of({"in_rowan": True, "toi": "5.01"}) == "control")       # 9
    checks.append(role_of({"vsx_eclipsing": False, "toi": "1234.01"}) == "toi")  # 10
    checks.append(role_of({"vsx_eclipsing": None, "toi": ""}) == "target")       # 11
    checks.append(tois_from({"tois": [{"toi": "101.01"}]}) == "101.01" and tois_from({"tois": []}) == ""
                  and tois_from(None) is None)                                   # 12
    ok_f = F.self_test()
    checks.append(bool(ok_f))                                                    # 13
    return all(checks), [i for i, c in enumerate(checks) if not c]


# ================================================================ driver
def run(a):
    os.makedirs(a.out_dir, exist_ok=True)
    t_start = time.time()
    meta = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "orbits_csv": a.orbits_csv, "anchor_rel": ANCHOR_REL, "tap_order": TAP_ORDER}
    summ_path = os.path.join(a.out_dir, "ffiscan_t2_summary.json")
    try:
        rows = t2.read_rows(a.orbits_csv)
    except Exception as exc:
        json.dump({"error": "orbits csv unavailable: %r" % exc, "meta": meta}, open(summ_path, "w"), indent=1)
        return 2
    stars = select(rows)
    ids = [s["source_id"] for s in stars]
    meta.update({"n_orbit_rows": len(rows), "n_selected": len(stars),
                 "hd35131_selected": HD35131_SID in set(ids),
                 "rowan_tier2_selected": len(t2.ROWAN_TIER2_EXPECTED & set(ids))})
    log("tier-2 selected", len(stars), "HD 35131 in:", meta["hd35131_selected"],
        "Rowan tier-2:", meta["rowan_tier2_selected"])
    if not stars:
        json.dump({"error": "no tier-2 rows", "meta": meta}, open(summ_path, "w"), indent=1)
        return 2
    if a.limit:
        stars = stars[:a.limit]
        ids = [s["source_id"] for s in stars]
    tap = t2.make_tap(TAP_ORDER)
    try:
        orbits = fetch_orbits(tap, ids)
    except Exception as exc:
        orbits = {}
        meta["orbit_error"] = repr(exc)[:300]
    meta["n_orbits"] = len(orbits)
    try:
        eb, cls = gaia_tables(tap, ids)
        meta["gaia_tables_ok"] = True
    except Exception as exc:
        eb, cls = set(), {}
        meta["gaia_tables_ok"] = False
        meta["gaia_tables_error"] = repr(exc)[:300]
    meta.update({"n_gaia_eb": len(eb), "n_gaia_class": len(cls)})
    log("orbits", len(orbits), "gaia eb", len(eb), "classified", len(cls))

    # ---- catalogue pass: roles fixed before any light curve is read
    for i, s in enumerate(stars):
        sid = s["source_id"]
        s["gaia_eb"] = sid in eb
        s["gaia_class"] = cls.get(sid, "")
        s["in_rowan"] = sid in t2.ROWAN2023_IDS
        tic = lookup_tic(sid)
        time.sleep(s0.PAUSE)
        s["tic"] = int(tic) if tic else None
        v = F.vsx_lookup(s["ra"], s["dec"])
        time.sleep(s0.PAUSE)
        if v is None:
            s["vsx_eclipsing"] = None
        else:
            s.update(v)
        s["toi"] = (tois_from(s0.get_json(s0.EXOFOP_TARGET % s["tic"])) or "") if s["tic"] else ""
        time.sleep(s0.PAUSE)
        s["role"] = role_of(s)
        if (i + 1) % 25 == 0:
            log("catalogue pass", i + 1, "/", len(stars))
    roles_path = os.path.join(a.out_dir, "ffiscan_t2_roles.csv")
    F.write_csv(roles_path, stars, ["source_id", "tic", "G", "s3_ratio", "P_screen", "role", "vsx_eclipsing",
                                    "vsx_names", "vsx_types", "gaia_eb", "gaia_class", "in_rowan", "toi"])
    meta["roles_written"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    log("roles", json.dumps({k: sum(1 for s in stars if s["role"] == k) for k in ("control", "toi", "target")}))

    # ---- light-curve pass (sb2_ffiscan.analyse, unchanged)
    recs, folds, truncated = [], [], False
    jl = open(os.path.join(a.out_dir, "ffiscan_t2_stars.jsonl"), "w")
    for i, s in enumerate(stars):
        if (time.time() - t_start) / 60.0 > a.max_minutes:
            truncated = True
            log("time limit reached; stopping before star", i)
            break
        if not s.get("tic"):
            rec = {k: s.get(k) for k in ("name", "source_id", "tic", "G", "role", "vetted", "tce_class")}
            rec.update({"label": "NO_TIC", "n_sectors": 0})
            fold, n_av, orb, anc = [], 0, None, False
        else:
            row = orbits.get(s["source_id"])
            orb = F.orbit_from_row(row) if row else None
            anc = anchor_ok(orb, s["P_screen"])
            P0 = orb["P"] if anc else s["P_screen"]
            sigP = orb["P_err"] if anc else s["P_screen_err"]
            tmp = tempfile.mkdtemp(prefix="lk_")
            try:
                try:
                    lcs, n_av = F.tess_lightcurves(s["tic"], tmp)
                except Exception as exc:
                    log("lightkurve failed", s["name"], repr(exc)[:200])
                    lcs, n_av = [], 0
                try:
                    rec, fold = F.analyse(s, orb if anc else None, P0, sigP, lcs)
                except Exception as exc:
                    log("analysis failed", s["name"], repr(exc)[:300])
                    rec = {k: s.get(k) for k in ("name", "source_id", "tic", "G", "role", "vetted", "tce_class")}
                    rec.update({"label": "ERROR", "error": repr(exc)[:300], "n_sectors": 0})
                    fold = []
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        rec.update({"orbit_type": orb["type"] if orb else "", "orbit_anchor": bool(anc),
                    "e_gaia": orb["e"] if orb else None, "omega_gaia": orb["omega"] if orb else None,
                    "n_sectors_available": n_av})
        for k in ("vsx_eclipsing", "vsx_names", "vsx_types") + tuple(EXTRA_COLS):
            rec[k] = s.get(k)
        recs.append(rec)
        folds += fold
        jl.write(json.dumps(F.jclean(rec)) + "\n")
        jl.flush()
        log("[%d/%d]" % (i + 1, len(stars)), s["name"], s.get("tic"), s["role"], rec.get("label"),
            json.dumps(F.jclean({k: rec.get(k) for k in ("snr", "null_max", "phase", "phase_z", "sec",
                                                          "depth_rel", "authors")})))
    jl.close()
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    grades = F.grade(recs, truncated)
    grades["F3"] = {"label": "NOT_APPLICABLE", "note": "no hand-vetted new EBs are in tier 2"}
    grades.update(extras(recs, stars, meta))
    summary = {"meta": meta, "grades": grades, "params": {
        "NB": F.NB, "WIDTHS": F.WIDTHS, "MIN_PTS": F.MIN_PTS, "SHAPE_MIN": F.SHAPE_MIN, "ZCLIP": F.ZCLIP,
        "SNR_MIN": F.SNR_MIN, "NULL_RATIO": F.NULL_RATIO, "SNR_SEC": F.SNR_SEC, "Z_PHASE": F.Z_PHASE,
        "MAX_LC": F.MAX_LC, "MAX_STEPS": F.MAX_STEPS, "N_HARM": F.N_HARM, "NULL_FACTORS": F.NULL_FACTORS}}
    with open(summ_path, "w") as fh:
        json.dump(F.jclean(summary), fh, indent=1)
    F.write_csv(os.path.join(a.out_dir, "ffiscan_t2_stars.csv"), recs, F.STAR_COLS + EXTRA_COLS)
    F.write_csv(os.path.join(a.out_dir, "ffiscan_t2_folds.csv"), folds, ["name", "tic", "phase", "rel_flux", "n"])
    short = {k: v for k, v in grades.items() if k not in ("known_hand", "toi")}
    if "F2" in short:
        short["F2"] = {kk: vv for kk, vv in short["F2"].items() if kk != "detected_phase_not_matched"}
    print(json.dumps(F.jclean(short)), flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--orbits-csv", default=ORBITS_CSV)
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--max-minutes", type=float, default=400.0)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    ok, bad = self_test()
    print("SELF_TEST", "PASS" if ok else "FAIL", bad, flush=True)
    if a.self_test or not ok:
        return 0 if ok else 3
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
