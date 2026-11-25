# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Do Gaia DR3's own G-band epochs of HD 171459 dim at the conjunctions of
Gaia DR3's own double-lined orbit?

HD 171459 = HIP 91511 = TIC 464315748 = Gaia DR3 6436666383265499136.
Orbit: gaiadr3.nss_two_body_orbit, solution SB2C (circular),
P = 6.395612408681747 d, t_periastron = 0.11847938719828086 d relative to the
DR3 reference epoch (Gaia time 2191.5 = J2016.0). For circular solutions the
conjunctions are taken at phase 0.25 and 0.75, the same convention as rule g8
(`sb2_ecl_dr4.py`, conjunctions at true anomaly 90 and 270 deg when omega is
not given). Window half-width 0.035 in phase is g8's frozen value; the null
test moves both windows by +0.25 (quadrature), as in g8.

Epochs: gaiadr3.epoch_photometry read from the AIP TAP mirror on 2026-11-25.
Epochs with variability_flag_g_reject = True are dropped (Gaia flags exactly
two: indices 33 and 40, G/sigma 4.3 and 8.3).

Pure standard library. Run: python hd171459_gaia_conj.py [csv]
"""
import csv
import json
import math
import os
import statistics
import sys

P = 6.395612408681747
T_REF = 2191.5
T_PERI = 0.11847938719828086
T0 = T_REF + T_PERI
CONJ = (0.25, 0.75)
WIN = 0.035


def phase(t):
    return ((t - T0) / P) % 1.0


def dphase(ph):
    """Signed phase offset from the nearer conjunction (0.25 or 0.75)."""
    return ph - 0.25 if ph < 0.5 else ph - 0.75


def in_window(ph, shift=0.0):
    for c in CONJ:
        c2 = (c + shift) % 1.0
        d = abs(ph - c2)
        d = min(d, 1.0 - d)
        if d <= WIN:
            return True
    return False


def find_csv(name="hd171459_gaia_dr3_epochs.csv"):
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.getcwd()):
        for root, _dirs, files in os.walk(base):
            if name in files:
                return os.path.join(root, name)
    raise FileNotFoundError(name)


def load(path=None):
    path = path or find_csv()
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append({
                "index": int(r["index"]),
                "t": float(r["g_transit_time"]),
                "g": float(r["g_mag"]),
                "foe": float(r["g_flux_over_error"]),
                "bp": float(r["bp_mag"]),
                "rp": float(r["rp_mag"]),
                "reject": r["variability_flag_g_reject"].strip() == "True",
                "phase_hand": float(r["phase_hand"]),
                "dphase_hand": float(r["dphase_hand"]),
            })
    return rows


def analyse(rows):
    good = [r for r in rows if not r["reject"]]
    for r in good:
        r["phase"] = phase(r["t"])
        r["dphase"] = dphase(r["phase"])
    inw = [r for r in good if in_window(r["phase"])]
    nullw = [r for r in good if in_window(r["phase"], shift=0.25)]
    out = [r for r in good if not in_window(r["phase"])]
    base_g = statistics.median(r["g"] for r in out)
    mad = statistics.median(abs(r["g"] - base_g) for r in out)
    rsd = 1.4826 * mad
    base_bp = statistics.median(r["bp"] for r in out if not math.isnan(r["bp"]))
    base_rp = statistics.median(r["rp"] for r in out if not math.isnan(r["rp"]))
    res_in = [r["g"] - base_g for r in inw]
    res_null = [r["g"] - base_g for r in nullw]
    deepest = sorted(inw, key=lambda r: r["g"], reverse=True)[:4]
    passages = sorted({round((r["t"] - T0) / P * 2) for r in deepest})
    bp_in = [r["bp"] - base_bp for r in inw if not math.isnan(r["bp"])]
    rp_in = [r["rp"] - base_rp for r in inw if not math.isnan(r["rp"])]
    p_sign = 0.5 ** len(res_in) if all(x > 0 for x in res_in) else None
    return {
        "source_id": "6436666383265499136",
        "name": "HD 171459",
        "n_epochs": len(rows),
        "n_rejected_by_gaia": len(rows) - len(good),
        "rejected_indices": [r["index"] for r in rows if r["reject"]],
        "n_out_of_window": len(out),
        "baseline_g_median": base_g,
        "robust_sd_g": rsd,
        "n_in_window": len(inw),
        "n_in_window_fainter": sum(1 for x in res_in if x > 0),
        "mean_resid_in_window": statistics.mean(res_in),
        "p_all_in_window_fainter_sign_test": p_sign,
        "n_null_window": len(nullw),
        "n_null_window_fainter": sum(1 for x in res_null if x > 0),
        "mean_resid_null_window": statistics.mean(res_null),
        "mean_resid_bp_in_window": statistics.mean(bp_in),
        "mean_resid_rp_in_window": statistics.mean(rp_in),
        "deepest4": [{"index": r["index"], "t": r["t"], "phase": round(r["phase"], 6),
                      "dphase": round(r["dphase"], 6),
                      "dphase_hours": round(r["dphase"] * P * 24, 3),
                      "resid_g": round(r["g"] - base_g, 6),
                      "resid_bp": round(r["bp"] - base_bp, 6),
                      "resid_rp": round(r["rp"] - base_rp, 6)} for r in deepest],
        "deepest4_distinct_conjunction_passages": len(passages),
        "max_abs_phase_hand_error": max(
            min(abs(r["phase"] - r["phase_hand"]), 1 - abs(r["phase"] - r["phase_hand"]))
            for r in good),
    }


def main(argv):
    rows = load(argv[1] if len(argv) > 1 else None)
    res = analyse(rows)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
