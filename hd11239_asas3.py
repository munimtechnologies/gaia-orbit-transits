# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""hd11239_asas3.py 0.1.0 -- do HD 11239's eclipses, predicted from Gaia DR3 alone, show up in
the independent ASAS-3 V-band light curve of 2000-2009?

HD 11239 = TIC 115321276 = Gaia DR3 4961129715887496320 = ASAS 014936-3944.5. The blind Gaia DR3
eclipse search (rule g8) flagged it from five faint Gaia epochs at the conjunctions of Gaia's own
double-lined orbit. This script takes the conjunction ephemeris from Gaia DR3 alone (nothing is
fitted to ASAS) and asks whether ASAS-3's faint points fall at those conjunctions, about 715 to
1,769 orbits before Gaia's reference conjunction.

Rule (findings/2026-11-26-hd11239-asas3-rule.md, written before any ASAS point was phased):
grade A and B rows only; aperture MAG_3; baseline = median MAG_3; faint = MAG_3 >= baseline +
0.07; window |dphase| <= 0.06 from the nearer Gaia conjunction (both windows cover 24% of the
orbit). A1: >= 5 faint points and >= 60% of them in a window. A2: in-window faint points near
both conjunctions and on >= 3 different nights.

Data: data/hd11239-asas3/hd11239_asas3_v.csv, transcribed (HJD - 2450000, MAG_3, GRADE, file
order, duplicates kept as in the file) from
http://www.astrouw.edu.pl/cgi-asas/asas_cgi_get_data?014936-3944.5,asas3 on 26 Nov 2026.
Pure Python, no network.
"""
import csv
import json
import math
import os
import statistics
import sys

VERSION = "0.1.0"
T_REF = 2191.5  # Gaia time of J2016.0 (Gaia time = BJD - 2455197.5)
GAIA_MINUS_HJD = 5197.5  # t_gaia = (HJD - 2450000) - 5197.5; HJD vs BJD_TCB < 0.002 d
ORBIT = {  # Gaia DR3 nss_two_body_orbit, source_id 4961129715887496320, SB2
    "period": 3.1208263847011897,
    "period_error": 0.0000391,
    "t_periastron": -0.7883709012326293,
    "eccentricity": 0.004279305956709024,
    "arg_periastron": 324.6817399437995,
}
FAINT = 0.07
WIN = 0.06
CHANCE = 4 * WIN  # two windows of half-width WIN
OUTLIER = 0.20  # robustness check: drop points more than this fainter than the baseline


def mean_anomaly_from_true(nu_rad, e):
    e_anom = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu_rad / 2.0),
                              math.sqrt(1.0 + e) * math.cos(nu_rad / 2.0))
    return (e_anom - e * math.sin(e_anom)) % (2.0 * math.pi)


def conjunctions(orbit=ORBIT):
    """Gaia time of conjunction 0 (nu + omega = 90 deg) and the phase of conjunction 1."""
    p, e, w = orbit["period"], orbit["eccentricity"], orbit["arg_periastron"]
    out = []
    for which in (0, 1):
        nu = math.radians((90.0 + 180.0 * which - w) % 360.0)
        m = mean_anomaly_from_true(nu, e)
        out.append(T_REF + orbit["t_periastron"] + p * m / (2.0 * math.pi))
    return out[0], ((out[1] - out[0]) / p) % 1.0


T0, D1 = conjunctions()


def dphase(hjd):
    """Signed phase from the nearer Gaia conjunction, and which one (0 or 1)."""
    ph = ((hjd - GAIA_MINUS_HJD - T0) / ORBIT["period"]) % 1.0
    cands = [(ph, 0), (ph - 1.0, 0), (ph - D1, 1)]
    return min(cands, key=lambda c: abs(c[0]))


def find_csv(name="hd11239_asas3_v.csv"):
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.getcwd()):
        for root, _dirs, files in os.walk(base):
            if name in files:
                return os.path.join(root, name)
    raise FileNotFoundError(name)


def load(path=None):
    with open(path or find_csv(), newline="") as fh:
        return [{"hjd": float(r["hjd"]), "mag": float(r["mag3"]), "grade": r["grade"].strip()}
                for r in csv.DictReader(fh)]


def binom_tail(k, n, p):
    return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))


def analyse(rows):
    good = [r for r in rows if r["grade"] in ("A", "B") and r["mag"] < 29.0]
    base = statistics.median(r["mag"] for r in good)
    faint = []
    for r in sorted((r for r in good if r["mag"] >= base + FAINT - 1e-9), key=lambda r: r["hjd"]):
        d, which = dphase(r["hjd"])
        faint.append({"hjd": r["hjd"], "mag": r["mag"], "dmag": round(r["mag"] - base, 4),
                      "dphase": d, "conj": which, "in_window": abs(d) <= WIN})
    inw = [f for f in faint if f["in_window"]]
    nights = {math.floor(f["hjd"] + 0.5) for f in inw}
    robust = [f for f in faint if f["dmag"] <= OUTLIER]
    robust_in = [f for f in robust if f["in_window"]]
    a1 = len(faint) >= 5 and len(inw) >= 0.6 * len(faint)
    a2 = {0, 1} <= {f["conj"] for f in inw} and len(nights) >= 3
    span = (min(r["hjd"] for r in good), max(r["hjd"] for r in good))
    cycles = [(T0 + GAIA_MINUS_HJD - t) / ORBIT["period"] for t in span]
    return {
        "version": VERSION, "t_conj0_gaia": T0, "t_conj0_hjd": T0 + GAIA_MINUS_HJD,
        "conj1_phase": D1, "n_good": len(good), "baseline_mag3": base,
        "faint_threshold": base + FAINT, "n_faint": len(faint), "n_faint_in_window": len(inw),
        "chance_fraction": CHANCE,
        "p_binomial": binom_tail(len(inw), len(faint), CHANCE),
        "n_in_window_conj0": sum(1 for f in inw if f["conj"] == 0),
        "n_in_window_conj1": sum(1 for f in inw if f["conj"] == 1),
        "n_nights_in_window": len(nights),
        "A1": a1, "A2": a2,
        "robust_n_faint": len(robust), "robust_n_in_window": len(robust_in),
        "robust_median_dphase": statistics.median(f["dphase"] for f in robust_in) if robust_in else None,
        "orbits_before_gaia_conj0": cycles,
        "phase_sigma_from_period": [c * ORBIT["period_error"] / ORBIT["period"] for c in cycles],
        "faint": faint,
    }


def write_faint_csv(res, path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hjd", "mag3", "dmag", "dphase", "conjunction", "in_window"])
        for f in res["faint"]:
            w.writerow([f"{f['hjd']:.5f}", f"{f['mag']:.3f}", f"{f['dmag']:.3f}",
                        f"{f['dphase']:.4f}", f["conj"], int(f["in_window"])])


def main(path=None):
    res = analyse(load(path))
    print(json.dumps(res, indent=1))
    return 0 if (res["A1"] and res["A2"]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
