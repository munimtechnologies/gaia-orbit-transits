# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""hd125386a_asas3.py 0.1.0 -- do HD 125386A's eclipses, predicted from Gaia DR3 alone, show up
in the independent ASAS-3 V-band light curve of 2000-2009?

HD 125386A = Gaia DR3 5854558019550047872 = TYC 9006-2161-1 = TIC 1021067547 (blended TIC
337318750) = ASAS 142119-6138.9, an Am star (HD 125386: A2mA5-A6) with a single-lined Gaia DR3
orbit (P = 3.6734 d, K1 = 48.5 km/s). The blind Gaia DR3 SB1 eclipse search (rule g8, job
g8-dr3-sb1-v1) flagged it from four faint Gaia G epochs, all at the conjunction where the visible
star is behind its companion. This script takes that conjunction from Gaia DR3 alone (nothing is
fitted to ASAS) and asks whether ASAS-3's faint points fall there, about 627 to 1,492 orbits
before Gaia's reference conjunction.

Rule (findings/2026-11-26-hd125386a-asas3-rule.md, written before the ASAS-3 data were fetched):
grade A and B rows of the 142119-6138.9 series only; aperture MAG_3; drop points fainter than
median + 0.40; baseline = median; faint = V >= baseline + 0.07; one window |phi| <= 0.12 around
Gaia's conjunction 0 (chance 0.24). Pass = at least half of the faint points in the window and
one-sided binomial p < 1e-4. Reported, not graded: a through-origin fit of O-C against cycle
number for the in-window points (a period correction).

Data: data/hd125386a-asas3/hd125386a_asas3_v.csv, transcribed (HJD - 2450000, MAG_3, GRADE, file
order) from the 142119-6138.9 block (field F1400-64_050) of
http://www.astrouw.edu.pl/cgi-asas/asas_cgi_get_data?142119-6138.9,asas3 on 26 Nov 2026.
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
ORBIT = {  # Gaia DR3 nss_two_body_orbit, source_id 5854558019550047872, SB1
    "period": 3.6734168626602712,
    "period_error": 0.00016818658,
    "t_periastron": -0.5645021006927092,
    "eccentricity": 0.015763200623999076,
    "arg_periastron": 301.40526948833156,
}
BAD = 0.40
FAINT = 0.07
WIN = 0.12
CHANCE = 2 * WIN  # one window of half-width WIN around conjunction 0
P_MAX = 1e-4


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
T0_HJD = T0 + GAIA_MINUS_HJD


def cycle_and_phase(hjd):
    """Nearest cycle number n of conjunction 0, O-C in days and signed phase in [-0.5, 0.5)."""
    p = ORBIT["period"]
    n = round((hjd - T0_HJD) / p)
    oc = hjd - T0_HJD - n * p
    return n, oc, oc / p


def find_csv(name="hd125386a_asas3_v.csv"):
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.getcwd()):
        for root, _dirs, files in os.walk(base):
            if name in files:
                return os.path.join(root, name)
    raise FileNotFoundError(name)


def load(path=None):
    with open(path or find_csv(), newline="") as fh:
        return [{"hjd": float(r["hjd_minus_2450000"]), "mag": float(r["v_mag3"]),
                 "grade": r["grade"].strip()} for r in csv.DictReader(fh)]


def binom_tail(k, n, p):
    return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))


def analyse(rows):
    ab = [r for r in rows if r["grade"] in ("A", "B") and r["mag"] < 29.0]
    med0 = statistics.median(r["mag"] for r in ab)
    good = [r for r in ab if r["mag"] <= med0 + BAD + 1e-9]
    base = statistics.median(r["mag"] for r in good)
    faint = []
    for r in sorted((r for r in good if r["mag"] >= base + FAINT - 1e-9), key=lambda r: r["hjd"]):
        n, oc, ph = cycle_and_phase(r["hjd"])
        faint.append({"hjd": r["hjd"], "mag": r["mag"], "dmag": round(r["mag"] - base, 4),
                      "cycle": n, "o_minus_c_d": oc, "phi": ph, "in_window": abs(ph) <= WIN + 1e-12})
    inw = [f for f in faint if f["in_window"]]
    nights = {math.floor(f["hjd"] + 0.5) for f in inw}
    p_bin = binom_tail(len(inw), len(faint), CHANCE)
    passed = len(faint) > 0 and 2 * len(inw) >= len(faint) and p_bin < P_MAX
    sxy = sum(f["cycle"] * f["o_minus_c_d"] for f in inw)
    sxx = sum(f["cycle"] ** 2 for f in inw)
    d_p = sxy / sxx if sxx else None
    span = (min(r["hjd"] for r in good), max(r["hjd"] for r in good))
    cycles = [(T0_HJD - t) / ORBIT["period"] for t in span]
    near_half = [f for f in faint if abs(abs(f["phi"]) - 0.5) <= 0.1]
    return {
        "version": VERSION, "t_conj0_gaia": T0, "t_conj0_hjd": T0_HJD, "conj1_phase": D1,
        "n_ab": len(ab), "n_dropped_bad": len(ab) - len(good), "n_good": len(good),
        "baseline_mag3": base, "faint_threshold": base + FAINT, "n_faint": len(faint),
        "n_faint_in_window": len(inw), "chance_fraction": CHANCE, "p_binomial": p_bin,
        "passed": passed, "n_nights_in_window": len(nights),
        "max_abs_phi_in_window": max(abs(f["phi"]) for f in inw) if inw else None,
        "median_phi_in_window": statistics.median(f["phi"] for f in inw) if inw else None,
        "period_correction_d": d_p,
        "period_correction_sigma": (d_p / ORBIT["period_error"]) if d_p is not None else None,
        "n_faint_within_0.1_of_phase_0.5": len(near_half),
        "orbits_before_gaia_conj0": cycles,
        "phase_sigma_from_period": [c * ORBIT["period_error"] / ORBIT["period"] for c in cycles],
        "faint": faint,
    }


def write_faint_csv(res, path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hjd_minus_2450000", "v_mag3", "dmag", "cycle", "o_minus_c_d", "phi",
                    "in_window"])
        for f in res["faint"]:
            w.writerow([f"{f['hjd']:.5f}", f"{f['mag']:.3f}", f"{f['dmag']:.3f}", f["cycle"],
                        f"{f['o_minus_c_d']:.5f}", f"{f['phi']:.5f}", int(f["in_window"])])


def main(path=None):
    res = analyse(load(path))
    print(json.dumps(res, indent=1))
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
