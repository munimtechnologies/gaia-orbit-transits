# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""hd11239_gaia_bprp.py 0.1.0 -- are HD 11239's Gaia eclipse dips real in all three of Gaia's
photometers, and colour-neutral as a twin eclipsing binary's should be?

HD 11239 = TIC 115321276 = Gaia DR3 4961129715887496320 is the one eclipsing candidate of the
pre-registered blind Gaia DR3 search (rule g8, findings/2026-11-26-g8-dr3-blind-results.md) that
no catalogue lists. Rule g8 used only the G band. This script asks two questions the G band
cannot answer on its own:

1. Do the faint G epochs at Gaia's conjunctions also appear in BP and RP? BP and RP are separate
   prism photometers with their own CCDs and windows, so a G-only artefact (a cosmic ray, a bad
   window) would not appear there.
2. Are the dips the same depth in BP and RP? Gaia's double-lined orbit says the two stars have
   nearly equal masses (q = K1/K2 = 0.959), so an eclipse of one by the other should be nearly
   colour-neutral. A blended eclipsing star of a different colour would not be.

The conjunction times come from Gaia DR3's own SB2 orbit (nss_two_body_orbit, fetched from the
AIP Gaia DR3 TAP mirror on 26 Nov 2026). The epoch photometry (gaiadr3.epoch_photometry, same
mirror, same day) is in hd11239_gaia_dr3_epochs.csv, transcribed with times rounded to 0.001 d
and magnitudes to 0.0001 mag. Gaia time = BJD(TCB) - 2455197.5.

The window (|phase from a conjunction| <= 0.035) is the one used by rule g8 and by the HD 171459
check (hd171459_gaia_conj.py). Pure Python, no network.
"""
import csv
import json
import math
import os
import statistics
import sys

VERSION = "0.1.0"
T_REF = 2191.5  # Gaia time of J2016.0, the reference of t_periastron
ORBIT = {  # Gaia DR3 nss_two_body_orbit, source_id 4961129715887496320, SB2
    "period": 3.1208263847011897,
    "t_periastron": -0.7883709012326293,
    "eccentricity": 0.004279305956709024,
    "arg_periastron": 324.6817399437995,
    "k1": 91.95870550025899,
    "k2": 95.91630965416246,
}
WIN = 0.035
DEEP = 0.03  # a dip deeper than this in G is "deep" for the colour test


def mean_anomaly_from_true(nu_rad, e):
    e_anom = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu_rad / 2.0),
                              math.sqrt(1.0 + e) * math.cos(nu_rad / 2.0))
    return (e_anom - e * math.sin(e_anom)) % (2.0 * math.pi)


def conjunctions(orbit=ORBIT):
    """Gaia times of the two conjunctions (nu + omega = 90 and 270 deg) after periastron, and
    the phase of the second one counted from the first."""
    p, e, w = orbit["period"], orbit["eccentricity"], orbit["arg_periastron"]
    out = []
    for which in (0, 1):
        nu = math.radians((90.0 + 180.0 * which - w) % 360.0)
        m = mean_anomaly_from_true(nu, e)
        out.append(T_REF + orbit["t_periastron"] + p * m / (2.0 * math.pi))
    d1 = ((out[1] - out[0]) / p) % 1.0
    return out[0], d1


T0, D1 = conjunctions()


def phase(t):
    return ((t - T0) / ORBIT["period"]) % 1.0


def dphase(t):
    """Signed phase offset from the nearer conjunction (at phase 0 and at phase D1)."""
    ph = phase(t)
    cands = [ph, ph - 1.0, ph - D1]
    return min(cands, key=abs)


def find_csv(name="hd11239_gaia_dr3_epochs.csv"):
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.getcwd()):
        for root, _dirs, files in os.walk(base):
            if name in files:
                return os.path.join(root, name)
    raise FileNotFoundError(name)


def _num(s):
    s = s.strip()
    return float("nan") if s.lower() == "nan" else float(s)


def load(path=None):
    path = path or find_csv()
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append({
                "index": int(r["index"]), "t": float(r["g_transit_time"]),
                "g": _num(r["g_mag"]), "bp": _num(r["bp_mag"]), "rp": _num(r["rp_mag"]),
                "g_rej": r["g_reject"].strip() == "1",
                "bp_rej": r["bp_reject"].strip() == "1",
                "rp_rej": r["rp_reject"].strip() == "1",
            })
    return rows


def good(row, band):
    return not row[band + "_rej"] and not math.isnan(row[band])


def analyse(rows):
    for r in rows:
        r["dphase"] = dphase(r["t"])
        r["in_window"] = abs(r["dphase"]) <= WIN
    med = {}
    for band in ("g", "bp", "rp"):
        med[band] = statistics.median(r[band] for r in rows if good(r, band) and not r["in_window"])
    out_g = [r["g"] - med["g"] for r in rows if good(r, "g") and not r["in_window"]]
    mad = statistics.median(abs(x) for x in out_g)
    inw = [r for r in rows if r["in_window"] and good(r, "g")]
    in_rows = []
    for r in inw:
        in_rows.append({"index": r["index"], "t": r["t"], "dphase": r["dphase"],
                        "resid_g": r["g"] - med["g"], "resid_bp": r["bp"] - med["bp"],
                        "resid_rp": r["rp"] - med["rp"]})
    deep = [x for x in in_rows if x["resid_g"] > DEEP]
    ratios = [x["resid_bp"] / x["resid_rp"] for x in deep]
    good_g = sorted((r for r in rows if good(r, "g")), key=lambda r: -r["g"])
    faintest3 = [r["index"] for r in good_g[:3]]
    n_good, n_in = len(good_g), len(inw)
    p3 = math.comb(n_in, 3) / math.comb(n_good, 3) if all(
        r["in_window"] for r in good_g[:3]) else None
    out_max = max((r["g"] - med["g"], r["index"]) for r in rows if good(r, "g") and not r["in_window"])
    g_rejected = [r for r in rows if r["g_rej"]]
    return {
        "version": VERSION, "t_conj0_gaia": T0, "conj1_phase": D1,
        "n_epochs": len(rows),
        "g_rejected": [r["index"] for r in g_rejected],
        "bp_rejected": [r["index"] for r in rows if r["bp_rej"]],
        "rp_rejected": [r["index"] for r in rows if r["rp_rej"]],
        "median": med, "robust_sd_g": 1.4826 * mad,
        "in_window": in_rows,
        "n_in_window_fainter_all_bands": sum(
            1 for x in in_rows if x["resid_g"] > 0 and x["resid_bp"] > 0 and x["resid_rp"] > 0),
        "deep_indices": [x["index"] for x in deep],
        "bp_over_rp_deep": ratios,
        "bp_over_rp_mean": sum(ratios) / len(ratios) if ratios else None,
        "faintest3_g": faintest3, "n_good_g": n_good,
        "p_faintest3_in_window": p3,
        "max_out_of_window_resid_g": out_max[0], "max_out_of_window_index": out_max[1],
        "g_rejected_resids": [{"index": r["index"], "dphase": r["dphase"],
                               "resid_g": r["g"] - med["g"], "resid_bp": r["bp"] - med["bp"],
                               "resid_rp": r["rp"] - med["rp"]} for r in g_rejected],
    }


def main(path=None):
    res = analyse(load(path))
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
