# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""tyc1316_asas3.py 0.1.0 -- do TYC 1316-1554-1's eclipses, predicted from Gaia DR3 alone, show
up in the independent ASAS-3 V-band light curve of 2003-2009?

TYC 1316-1554-1 = Gaia DR3 3350075697770930304 = ASAS 055236+1741.3 has a single-lined Gaia DR3
orbit (P = 1.62628 d, K1 = 95.2 km/s, e = 0.078). The blind Gaia DR3 SB1 eclipse search (rule g8,
job g8-dr3-sb1-v1) flagged it from five faint Gaia G epochs: three at the conjunction where the
visible star is behind its companion (conjunction 0) and two at the other one. This script takes
both conjunctions from Gaia DR3 alone (nothing is fitted to ASAS) and asks whether ASAS-3's faint
points fall there, about 1,560 to 2,460 orbits before Gaia's reference conjunction.

Rule (findings/2026-11-26-tyc1316-asas3-rule.md, written before the ASAS-3 data were fetched):
grade A and B rows of the first 055236+1741.3 dataset (field F0552+16_434); aperture MAG_2; drop
points fainter than median + 0.50; baseline = median; sigma = 1.4826 x MAD; faint = V >= baseline
+ max(0.07, 3 sigma); two windows of half-width 0.08 around conjunction 0 and conjunction 1
(chance 0.32). Pass = at least half of the faint points in the windows and one-sided binomial
p < 1e-4. Reported, not graded: which conjunction the in-window points sit at, and a
through-origin fit of O-C against cycle number for the conjunction-0 points (a period correction).

Data: data/tyc1316-asas3/tyc1316_asas3_v.csv, transcribed (HJD - 2450000, MAG_2, GRADE, file
order) from dataset 1 (field F0552+16_434, 351 rows) of
http://www.astrouw.edu.pl/cgi-asas/asas_cgi_get_data?055236+1741.3,asas3 on 26 Nov 2026.
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
ORBIT = {  # Gaia DR3 nss_two_body_orbit, source_id 3350075697770930304, SB1
    "period": 1.6262843323377891,
    "period_error": 1.4146652e-05,
    "t_periastron": -0.7543342295632256,
    "eccentricity": 0.07761222785612452,
    "arg_periastron": 153.43430758134832,
}
BAD = 0.50
FAINT_MIN = 0.07
NSIG = 3.0
WIN = 0.08
CHANCE = 4 * WIN  # two windows of half-width WIN
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
    """Nearest cycle n of conjunction 0, O-C in days and signed phase in [-0.5, 0.5)."""
    p = ORBIT["period"]
    n = round((hjd - T0_HJD) / p)
    oc = hjd - T0_HJD - n * p
    return n, oc, oc / p


def which_window(ph):
    """0 or 1 if the signed phase lies in the window of that conjunction, else None."""
    if abs(ph) <= WIN + 1e-12:
        return 0
    d1 = ((ph % 1.0) - D1 + 0.5) % 1.0 - 0.5
    if abs(d1) <= WIN + 1e-12:
        return 1
    return None


def find_csv(name="tyc1316_asas3_v.csv"):
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.getcwd()):
        for root, _dirs, files in os.walk(base):
            if name in files:
                return os.path.join(root, name)
    raise FileNotFoundError(name)


def load(path=None):
    with open(path or find_csv(), newline="") as fh:
        return [{"hjd": float(r["hjd_minus_2450000"]), "mag": float(r["v_mag2"]),
                 "grade": r["grade"].strip()} for r in csv.DictReader(fh)]


def binom_tail(k, n, p):
    return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))


def analyse(rows):
    ab = [r for r in rows if r["grade"] in ("A", "B") and r["mag"] < 29.0]
    med0 = statistics.median(r["mag"] for r in ab)
    good = [r for r in ab if r["mag"] <= med0 + BAD + 1e-9]
    base = statistics.median(r["mag"] for r in good)
    mad = statistics.median(abs(r["mag"] - base) for r in good)
    sigma = 1.4826 * mad
    thr = base + max(FAINT_MIN, NSIG * sigma)
    faint = []
    for r in sorted((r for r in good if r["mag"] >= thr - 1e-9), key=lambda r: r["hjd"]):
        n, oc, ph = cycle_and_phase(r["hjd"])
        faint.append({"hjd": r["hjd"], "mag": r["mag"], "dmag": round(r["mag"] - base, 4),
                      "cycle": n, "o_minus_c_d": oc, "phi": ph, "window": which_window(ph)})
    inw = [f for f in faint if f["window"] is not None]
    in0 = [f for f in inw if f["window"] == 0]
    p_bin = binom_tail(len(inw), len(faint), CHANCE)
    passed = len(faint) > 0 and 2 * len(inw) >= len(faint) and p_bin < P_MAX
    sxy = sum(f["cycle"] * f["o_minus_c_d"] for f in in0)
    sxx = sum(f["cycle"] ** 2 for f in in0)
    d_p = sxy / sxx if sxx else None
    span = (min(r["hjd"] for r in good), max(r["hjd"] for r in good))
    cycles = [(T0_HJD - t) / ORBIT["period"] for t in span]
    return {
        "version": VERSION, "t_conj0_gaia": T0, "t_conj0_hjd": T0_HJD, "conj1_phase": D1,
        "n_ab": len(ab), "n_dropped_bad": len(ab) - len(good), "n_good": len(good),
        "baseline_mag2": base, "mad": mad, "sigma": sigma, "faint_threshold": thr,
        "n_faint": len(faint), "n_faint_in_windows": len(inw), "n_in_conj0": len(in0),
        "n_in_conj1": len(inw) - len(in0), "chance_fraction": CHANCE, "p_binomial": p_bin,
        "passed": passed,
        "phi_all_faint": [f["phi"] for f in faint],
        "period_correction_conj0_d": d_p,
        "period_correction_conj0_sigma": (d_p / ORBIT["period_error"]) if d_p is not None else None,
        "orbits_before_gaia_conj0": cycles,
        "phase_sigma_from_period": [c * ORBIT["period_error"] / ORBIT["period"] for c in cycles],
        "faint": faint,
    }


def posthoc_all_faint_fit(res):
    """NOT pre-registered (vetting only): through-origin O-C fit using all faint points, each
    taken at its nearest conjunction-0 cycle."""
    f = res["faint"]
    sxy = sum(x["cycle"] * x["o_minus_c_d"] for x in f)
    sxx = sum(x["cycle"] ** 2 for x in f)
    return sxy / sxx if sxx else None


def write_faint_csv(res, path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hjd_minus_2450000", "v_mag2", "dmag", "cycle", "o_minus_c_d", "phi",
                    "window"])
        for f in res["faint"]:
            w.writerow([f"{f['hjd']:.5f}", f"{f['mag']:.3f}", f"{f['dmag']:.3f}", f["cycle"],
                        f"{f['o_minus_c_d']:.5f}", f"{f['phi']:.5f}",
                        "" if f["window"] is None else f["window"]])


def main(path=None):
    res = analyse(load(path))
    res["posthoc_period_correction_all_faint_d"] = posthoc_all_faint_fit(res)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
