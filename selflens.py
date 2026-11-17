# SPDX-License-Identifier: Apache-2.0
"""selflens.py -- self-lensing pulses of white dwarfs at Gaia-predicted conjunctions.

Part of gaia-orbit-transits 0.8.0 by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0. Pre-registration: findings/2026-11-17-selflens-prereg.md

A white dwarf on an AU-scale orbit that passes in front of its main-sequence companion
magnifies it by about 2 (R_E / R1)^2, where R_E^2 = 4 G M_wd r / c^2 is its Einstein
radius at separation r. The star brightens by a few thousand ppm for a few hours to a
day (Kruse & Agol 2014; Yamaguchi, El-Badry et al. 2024). Shahaf et al. (2024, MNRAS
529, 3729; updated Table A1, Zenodo 10.5281/zenodo.14799795, CC BY 4.0) list about 3,200
Gaia DR3 astrometric orbits whose dark companion is probably a white dwarf. For the
near-edge-on ones a Gaia orbit predicts *when* that pulse must happen. This script:

  1. reads the Shahaf et al. source_ids;
  2. runs the unchanged run_search.py pipeline (Gaia query, Monte Carlo over the
     catalogue errors, TESS light curves, box search) with three substitutions:
     - only the listed stars get a prior;
     - the companion radius is a white-dwarf radius (Nauenberg 1972), so the
       "eclipse" probability and duration are those of the white dwarf crossing the
       star's disc;
     - the TESS flux is inverted (2 - f) and strong *downward* outliers are clipped
       instead of upward ones, so the box search finds brightenings; plots show 2 - f;
  3. predicts each target's pulse amplitude and duration, and applies the
     pre-registered pulse rule at the conjunction where the white dwarf is in front
     (Gaia's RV label for AstroSpectroSB1 solutions, either conjunction otherwise),
     with a false-alarm control half a period away.
"""
import argparse
import csv
import json
import math
import os
import sys
import urllib.request

import numpy as np

VERSION = "0.8.0"
SHAHAF_URL = "https://zenodo.org/api/records/14799795/files/table_I_20250126.fits/content"
RE2_CONST = 8.4900e-6      # 4 G Msun / c^2 in units of Rsun
AU_RSUN = 215.032
YEAR_D = 365.25
M_CH = 1.44

# ---- the pre-registered pulse rule (do not change after the data are read) ----
MIN_SNR = 8.0
AMP_FACTOR = 3.0           # observed amplitude within [A/3, 3A]
DUR_FACTOR = 3.0           # observed duration within [D/3, 3D] (D >= 2 h)
WINDOW_NSIGMA = 3.0
MIN_DETECT_SNR = 10.0      # a pulse counts as detectable if A / noise >= 10


# ------------------------------------------------------------------ physics
def wd_radius_rsun(m):
    """Nauenberg (1972) white-dwarf radius in Rsun; clipped to [0.003, 0.02]."""
    x = min(max(float(m), 0.05), M_CH * 0.999) / M_CH
    r = 0.0112 * math.sqrt(x ** (-2.0 / 3.0) - x ** (2.0 / 3.0))
    return min(max(r, 0.003), 0.02)


def semi_major_axis_rsun(m1, m2, period_d):
    return ((m1 + m2) * (period_d / YEAR_D) ** 2) ** (1.0 / 3.0) * AU_RSUN


def einstein_radius_rsun(m2, r_rsun):
    return math.sqrt(RE2_CONST * m2 * r_rsun)


def pulse_amplitude(m2, a_rsun, r1):
    """Fractional brightening at the centre of the pulse (R_E << R1): lensing
    2 (R_E/R1)^2 minus the white dwarf's own occultation (R_wd/R1)^2."""
    re = einstein_radius_rsun(m2, a_rsun)
    return 2.0 * (re / r1) ** 2 - (wd_radius_rsun(m2) / r1) ** 2


# ------------------------------------------------------------------ helpers
def fnum(x, default=float("nan")):
    try:
        s = str(x).strip()
        return float(s) if s not in ("", "nan", "None", "--") else default
    except ValueError:
        return default


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def to_id(x):
    try:
        return int(str(x).strip().split(".")[0])
    except ValueError:
        return None


ID_NAMES = ("source_id", "gaia_source_id", "dr3_source_id", "gaia_dr3_source_id",
            "gaiadr3_source_id", "sourceid", "gaia_id", "dr3", "gaiadr3")


def pick_id_column(colnames):
    low = {c.lower(): c for c in colnames}
    for n in ID_NAMES:
        if n in low:
            return low[n]
    for c in colnames:
        if "source" in c.lower():
            return c
    return None


def load_shahaf(path):
    from astropy.table import Table
    t = Table.read(path)
    col = pick_id_column(t.colnames)
    if col is None:
        raise SystemExit("no source_id column in %s: %s" % (path, t.colnames))
    ids = {to_id(v) for v in t[col]}
    ids.discard(None)
    info = {"rows": len(t), "id_column": col, "columns": list(t.colnames)}
    flags = {}
    for c in t.colnames:
        if any(k in c.lower() for k in ("class", "excess", "flag", "prob")):
            vals = t[c]
            try:
                uniq = sorted({str(v) for v in vals})
            except Exception:
                uniq = []
            flags[c] = uniq[:10] if len(uniq) <= 10 else "%d distinct" % len(uniq)
    info["flag_columns"] = flags
    return ids, info


# ------------------------------------------------------------------ pulse rule
def lens_conjs(transit_conj):
    """Conjunctions at which the white dwarf may be in front of the star."""
    tc = str(transit_conj or "").strip()
    return [tc] if tc in ("t1", "t2") else ["t1", "t2"]


def in_window(t, wins, half_extra_d, P, shift=0.0):
    """True if t lies within 3 sd + half_extra of a window centre (+ shift)."""
    for centre, sd in wins:
        hw = WINDOW_NSIGMA * sd + half_extra_d
        if hw > P / 4.0:
            continue
        if abs(t - (centre + shift)) <= hw:
            return True
    return False


def passes_shape(ev, amp_ppm, dur_h):
    snr = fnum(ev.get("snr"), 0.0)
    depth = fnum(ev.get("depth_ppm"), 0.0)
    dh = fnum(ev.get("duration_h"), 0.0)
    d_pred = max(dur_h, 2.0)
    return (snr >= MIN_SNR and amp_ppm > 0
            and amp_ppm / AMP_FACTOR <= depth <= amp_ppm * AMP_FACTOR
            and d_pred / DUR_FACTOR <= dh <= d_pred * DUR_FACTOR
            and str(ev.get("near_edge", "")).strip().lower() not in ("true", "1")
            and fnum(ev.get("n_other_targets_same_time"), 0.0) == 0)


def evaluate(priors, targets, events, windows):
    """Per-target predictions, pulse candidates and control hits."""
    pri = {}
    for p in priors:
        pri.setdefault(str(p.get("source_id", "")).strip(), p)
    ev_by = {}
    for e in events:
        ev_by.setdefault(str(e.get("source_id", "")).strip(), []).append(e)
    win = {}
    for w in windows:
        key = (str(w.get("source_id", "")).strip(), str(w.get("conj", "")).strip())
        c, sd = fnum(w.get("centre")), fnum(w.get("sd"))
        if np.isfinite(c) and np.isfinite(sd):
            win.setdefault(key, []).append((c, sd))
    recs, cands, ctrl = [], [], []
    for t in targets:
        sid = str(t.get("source_id", "")).strip()
        p = pri.get(sid)
        if p is None:
            continue
        m1, m2, r1 = fnum(p.get("m1")), fnum(p.get("m2_dark")), fnum(p.get("r1"))
        P = fnum(p.get("period_d"))
        if not all(np.isfinite([m1, m2, r1, P])) or r1 <= 0 or P <= 0:
            continue
        a = semi_major_axis_rsun(m1, m2, P)
        amp = pulse_amplitude(m2, a, r1)
        conjs = lens_conjs(p.get("transit_conj"))
        evs = ev_by.get(sid, [])
        noise = [fnum(e.get("box_noise_ppm")) for e in evs]
        noise = [x for x in noise if np.isfinite(x) and x > 0]
        sig = float(np.median(noise)) if noise else float("nan")
        exp = 0.0
        for k in conjs:
            pk = fnum(p.get("p_ecl" + k[1]), 0.0)
            ck = fnum(t.get("cov" + k[1]), 0.0)
            exp += pk * ck
        detectable = bool(np.isfinite(sig) and amp * 1e6 / sig >= MIN_DETECT_SNR)
        rec = {"source_id": sid, "tic": t.get("tic", ""), "status": t.get("status", ""),
               "gmag": p.get("gmag"), "period_d": P, "ecc": p.get("ecc"),
               "solution_type": p.get("solution_type"), "m1": m1, "r1": r1, "m2": m2,
               "a_rsun": a, "r_e_rsun": einstein_radius_rsun(m2, a),
               "amp_ppm": amp * 1e6, "cosi": p.get("cosi"), "cosi_sd": p.get("cosi_sd"),
               "lens_conj": "/".join(conjs), "p_lens1": p.get("p_ecl1"),
               "p_lens2": p.get("p_ecl2"), "cov1": t.get("cov1"), "cov2": t.get("cov2"),
               "dur1_h": p.get("dur1_h"), "dur2_h": p.get("dur2_h"), "noise_ppm": sig,
               "detectable": detectable, "expected_in_data": exp,
               "expected_detectable": exp if detectable else 0.0, "n_candidates": 0,
               "n_control": 0}
        for e in evs:
            te = fnum(e.get("t_center"))
            if not np.isfinite(te):
                continue
            for k in conjs:
                dur = fnum(p.get("dur" + k[1] + "_h"), 4.0)
                if not passes_shape(e, amp * 1e6, dur):
                    continue
                wins = win.get((sid, k), [])
                if in_window(te, wins, dur / 48.0, P):
                    rec["n_candidates"] += 1
                    cands.append(dict(e, lens_conj=k, amp_pred_ppm=amp * 1e6,
                                      dur_pred_h=dur))
                elif in_window(te, wins, dur / 48.0, P, shift=P / 2.0) or \
                        in_window(te, wins, dur / 48.0, P, shift=-P / 2.0):
                    rec["n_control"] += 1
                    ctrl.append(dict(e, lens_conj=k))
        recs.append(rec)
    return recs, cands, ctrl


def grade(recs, cands, ctrl):
    with_tess = [r for r in recs if r["status"] == "ok"]
    e_det = float(sum(r["expected_detectable"] for r in recs))
    amps = [r["amp_ppm"] for r in recs if np.isfinite(r["amp_ppm"])]
    med_amp = float(np.median(amps)) if amps else float("nan")
    g = {
        "L1": {"prediction": "expected detectable pulses in the TESS data < 2",
               "value": e_det, "pass": bool(e_det < 2)},
        "L2": {"prediction": "no target passes the pulse rule (null result)",
               "value": len({c.get('source_id') for c in cands}),
               "pass": len(cands) == 0},
        "L3": {"prediction": "at most one control hit (false alarms half a period away)",
               "value": len(ctrl), "pass": len(ctrl) <= 1},
        "L4": {"prediction": "median predicted pulse amplitude 1,000-6,000 ppm",
               "value": med_amp, "pass": bool(1000 <= med_amp <= 6000)},
    }
    return g, {"n_targets": len(recs), "n_with_tess": len(with_tess),
               "n_detectable": sum(1 for r in recs if r["detectable"]),
               "expected_in_data": float(sum(r["expected_in_data"] for r in recs)),
               "expected_detectable": e_det, "median_amp_ppm": med_amp,
               "n_candidates": len(cands), "n_control": len(ctrl)}


# ------------------------------------------------------------------ pipeline
def no_clip_sd(_x):
    return float("inf")


def patch_run_search(rs, ids):
    """Restrict priors to ids, use white-dwarf radii, and invert the TESS flux."""
    orig_prior = rs.prior_for_row
    orig_radius = rs.go.companion_radius

    def prior_for_row(row, n, rng, predict_from=None):
        if to_id(row.get("source_id")) not in ids:
            return None
        rs.go.companion_radius = wd_radius_rsun
        try:
            return orig_prior(row, n, rng, predict_from)
        finally:
            rs.go.companion_radius = orig_radius

    def fetch_tess(tic, ra, dec, data_dir, max_lcs):
        # run_search.fetch_tess clips points above 1 + 6 sd (flares). A lensing pulse is
        # upward too and, on a bright star, can exceed 6 sd per cadence, so the clip is
        # switched off while it runs (robust_sd -> inf) and the clip is applied below
        # to the inverted flux instead (i.e. to strong dips such as stellar eclipses).
        orig_sd = rs.ds.robust_sd
        rs.ds.robust_sd = no_clip_sd
        try:
            lcs, meta = orig_fetch(tic, ra, dec, data_dir, max_lcs)
        finally:
            rs.ds.robust_sd = orig_sd
        out = []
        for t, f in lcs:
            g = 2.0 - f
            sd = rs.ds.robust_sd(g)
            keep = g < 1 + 6 * sd          # clip what were strong dips (eclipses)
            out.append((t[keep], g[keep]))
        return out, meta

    orig_fetch = rs.fetch_tess
    rs.prior_for_row = prior_for_row
    rs.fetch_tess = fetch_tess


def write_csv(path, rows):
    if not rows:
        open(path, "w").close()
        return
    fields = sorted({k for r in rows for k in r})
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def analyse_dir(out_dir):
    recs, cands, ctrl = evaluate(read_csv(os.path.join(out_dir, "gaia_edge_on_priors.csv")),
                                 read_csv(os.path.join(out_dir, "tess_targets.csv")),
                                 read_csv(os.path.join(out_dir, "events.csv")),
                                 read_csv(os.path.join(out_dir, "covered_windows.csv")))
    grades, summ = grade(recs, cands, ctrl)
    recs.sort(key=lambda r: -r["expected_detectable"])
    write_csv(os.path.join(out_dir, "selflens_targets.csv"), recs)
    write_csv(os.path.join(out_dir, "selflens_candidates.csv"), cands)
    write_csv(os.path.join(out_dir, "selflens_control.csv"), ctrl)
    res = {"version": VERSION, "summary": summ, "grades": grades}
    with open(os.path.join(out_dir, "selflens_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(json.dumps(res, default=float))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--gmax", default="15")
    ap.add_argument("--cosi-max", default="0.2")
    ap.add_argument("--max-targets", default="250")
    ap.add_argument("--time-budget-min", default="210")
    ap.add_argument("--analyse-only", action="store_true")
    a = ap.parse_args(argv)
    if not a.analyse_only:
        os.makedirs(a.data_dir, exist_ok=True)
        os.makedirs(a.out_dir, exist_ok=True)
        fits = os.path.join(a.data_dir, "shahaf2024_table_I_20250126.fits")
        if not os.path.exists(fits):
            urllib.request.urlretrieve(SHAHAF_URL, fits + ".part")
            os.replace(fits + ".part", fits)
        ids, info = load_shahaf(fits)
        info["n_ids"] = len(ids)
        with open(os.path.join(a.out_dir, "shahaf_info.json"), "w", encoding="utf-8") as fh:
            json.dump(info, fh, indent=1, default=str)
        print("Shahaf et al. ids:", len(ids), "column", info["id_column"], flush=True)
        import run_search as rs
        patch_run_search(rs, ids)
        rs.main(["--data-dir", a.data_dir, "--out-dir", a.out_dir, "--gmax", a.gmax,
                 "--cosi-max", a.cosi_max, "--mc", "600", "--max-targets", a.max_targets,
                 "--min-p-ecl", "0.0005", "--max-lcs", "25", "--snr", "7",
                 "--time-budget-min", a.time_budget_min, "--plots", "40",
                 "--tap-chunks", "32"])
    analyse_dir(a.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
