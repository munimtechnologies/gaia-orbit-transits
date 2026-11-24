# SPDX-License-Identifier: Apache-2.0
"""gaia_dip_ffi 0.1.0 - registered TESS test of two eclipse candidates found in Gaia DR3's own epoch
photometry: CD-63 310 (Gaia DR3 5288669213282803328, TIC 349572805) and CD-72 1603
(Gaia DR3 6374372070227419008, TIC 371839648).

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.
Pre-registration: findings/2026-11-24-gaia-conj-dips-prereg.md.

It runs the unchanged per-star analysis of sb2_ffiscan.py 0.1.0 (pinned at commit b53e2b3; fetched
in the job's setup step) on a fixed list of 10 stars: the two candidates, two positive controls
(the two eclipsing binaries this project found earlier, HD 250735 and CD-28 7251), and the six
other edge-on Gaia SB2s whose Gaia epochs showed no dip. CD-63 310 is not in the sb2-ffiscan-v1
sample because the screen found no TIC number for it (status NO_TIC).
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time

VERSION = "0.1.0"
# source_id, TIC, name, group, Gaia G, ra, dec, Gaia period (d), period error (d)
STARS = [
    ("5288669213282803328", 349572805, "CD-63 310", "candidate", 9.944624, 111.75250419678167,
     -63.73492917546819, 5.410625783263602, 0.0002401259),
    ("6374372070227419008", 371839648, "CD-72 1603", "candidate", 9.908084, 306.4673867679192,
     -71.70070984430552, 4.566931695393036, 0.00013138614),
    ("3450611154067089408", 400170926, "HD 250735", "control", 9.33441, 90.91649656866566,
     32.33759512286162, 5.895935077280673, 0.00018169096),
    ("5633392634307163776", 189269584, "CD-28 7251", "control", 8.860162, 141.43482404874516,
     -29.32698292140422, 6.96108580484263, 0.00015122705),
    ("6025454428973694464", 212031970, "Gaia DR3 6025454428973694464", "flat", 7.969438,
     248.41942598715016, -31.289176010688998, 1.059592647827001, 8.161422e-06),
    ("6370053605166404992", 311430361, "Gaia DR3 6370053605166404992", "flat", 7.8003016,
     317.22163822968287, -73.39645905311572, 2.2299478395230414, 1.2748673e-05),
    ("3043555010111094400", 32399700, "Gaia DR3 3043555010111094400", "flat", 10.652893,
     117.41212714280341, -7.09915768768597, 4.90690984742347, 0.0003543802),
    ("2995056243702062080", 317413770, "Gaia DR3 2995056243702062080", "flat", 9.38318,
     87.79901026537743, -15.985548954117975, 4.741729755883772, 0.00013839928),
    ("3419201066092932992", 356984148, "Gaia DR3 3419201066092932992", "flat", 10.030404,
     76.39926466149514, 24.867074479250146, 4.347980646942389, 0.00010929686),
    ("6547214134176807808", 214875017, "Gaia DR3 6547214134176807808", "flat", 10.189649,
     341.7524915996683, -39.37399765684506, 6.680747581467151, 0.00011896142),
]
GAIA_DIP_CONJ = {"CD-63 310": "c2", "CD-72 1603": "c1"}   # conjunction of the Gaia-epoch dip
DEPTH_MAX_GRAZING = 0.10


def star_dicts():
    out = []
    for sid, tic, name, grp, G, ra, dec, P, Pe in STARS:
        out.append({"source_id": sid, "tic": tic, "name": name, "group": grp, "G": G, "ra": ra,
                    "dec": dec, "P_screen": P, "P_screen_err": Pe,
                    # fields sb2_ffiscan.analyse() copies into its record
                    "role": "control" if grp == "control" else "target",
                    "vetted": "new_eb" if grp == "control" else "", "tce_class": ""})
    return out


def ok_match(r):
    return r is not None and r.get("label") == "DETECTED" and r.get("phase") == "PHASE_MATCH"


def grade(recs):
    by = {r["name"]: r for r in recs}
    ctrl = [by.get(s[2]) for s in STARS if s[3] == "control"]
    D0 = "CONTROLS_OK" if all(ok_match(r) for r in ctrl) else "CONTROLS_FAIL"
    out = {"D0": {"label": D0, "rows": [{"name": (r or {}).get("name"), "label": (r or {}).get("label"),
                                         "phase": (r or {}).get("phase")} for r in ctrl]}}
    for key, name in (("D1", "CD-63 310"), ("D2", "CD-72 1603")):
        r = by.get(name)
        if r is None or r.get("n_sectors", 0) == 0:
            lab = "NO_DATA"
        elif ok_match(r):
            lab = "CONFIRMED_AT_GAIA_CONJUNCTION"
        elif r.get("label") == "DETECTED":
            lab = "DETECTED_PHASE_MISMATCH" if r.get("phase") == "PHASE_MISMATCH" else "DETECTED_UNTESTABLE"
        else:
            lab = "NOT_DETECTED"
        d = (r or {}).get("depth_rel")
        out[key] = {"name": name, "label": lab,
                    "same_conjunction_as_gaia_dip": (r or {}).get("phase_map") == GAIA_DIP_CONJ[name]
                    if lab == "CONFIRMED_AT_GAIA_CONJUNCTION" else None,
                    "grazing_depth": (d is not None and d == d and abs(d) <= DEPTH_MAX_GRAZING)
                    if lab == "CONFIRMED_AT_GAIA_CONJUNCTION" else None,
                    "snr": (r or {}).get("snr"), "depth_rel": d, "phase_z": (r or {}).get("phase_z"),
                    "sec": (r or {}).get("sec"), "n_sectors": (r or {}).get("n_sectors", 0)}
    flat = [by.get(s[2]) for s in STARS if s[3] == "flat"]
    flat_ok = [r for r in flat if ok_match(r)]
    out["D3"] = {"n_flat_with_data": sum(1 for r in flat if r and r.get("n_sectors", 0) > 0),
                 "n_flat_detected_phase_match": len(flat_ok),
                 "names": [r["name"] for r in flat_ok],
                 "expectation_at_most_1": len(flat_ok) <= 1}
    if D0 != "CONTROLS_OK":
        verdict = "UNTESTABLE_CONTROLS_FAILED"
    else:
        n = sum(1 for k in ("D1", "D2") if out[k]["label"] == "CONFIRMED_AT_GAIA_CONJUNCTION")
        verdict = {2: "BOTH_CONFIRMED", 1: "ONE_CONFIRMED", 0: "NEITHER_CONFIRMED"}[n]
    out["verdict"] = verdict
    return out


def run(args):
    import sb2_ffiscan as F
    os.makedirs(args.out_dir, exist_ok=True)
    meta = {"version": VERSION, "ffiscan_version": F.VERSION,
            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    stars = star_dicts()
    tap, src, errs = F.fetch_orbits([s["source_id"] for s in stars])
    meta.update({"orbit_source": src, "orbit_errors": errs, "n_orbits": len(tap)})
    F.log("orbits", src, len(tap), errs)
    recs = []
    jl = open(os.path.join(args.out_dir, "gdf_stars.jsonl"), "w")
    for s in stars:
        row = tap.get(s["source_id"])
        orb = F.orbit_from_row(row) if row else None
        anc = F.anchor_ok(orb, s["P_screen"])
        P0 = orb["P"] if anc else s["P_screen"]
        sigP = orb["P_err"] if anc else s["P_screen_err"]
        tmp = tempfile.mkdtemp(prefix="lk_")
        try:
            try:
                lcs, n_av = F.tess_lightcurves(s["tic"], tmp, max_lc=args.max_lc)
            except Exception as exc:
                F.log("lightkurve failed", s["name"], repr(exc)[:200])
                lcs, n_av = [], 0
            try:
                rec, _ = F.analyse(s, orb if anc else None, P0, sigP, lcs)
            except Exception as exc:
                rec = {"name": s["name"], "label": "ERROR", "error": repr(exc)[:300], "n_sectors": 0}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rec.update({"group": s["group"], "orbit_anchor": bool(anc), "n_sectors_available": n_av,
                    "orbit_type": orb["type"] if orb else ""})
        recs.append(rec)
        jl.write(json.dumps(F.jclean(rec)) + "\n")
        jl.flush()
        F.log(s["name"], s["group"], rec.get("label"), rec.get("phase"), rec.get("snr"), rec.get("depth_rel"))
    jl.close()
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    g = grade(recs)
    with open(os.path.join(args.out_dir, "gdf_summary.json"), "w") as fh:
        json.dump(F.jclean({"meta": meta, "grades": g}), fh, indent=1)
    print(json.dumps(F.jclean(g)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--max-lc", type=int, default=8)
    a = ap.parse_args(argv)
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
