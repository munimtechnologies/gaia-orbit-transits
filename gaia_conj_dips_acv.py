# SPDX-License-Identifier: Apache-2.0
"""gaia_conj_dips_acv 0.1.0 - Gaia DR3 double-lined binaries that Gaia's classifier called rotating
chemically peculiar stars (class ACV|CP|MCP|ROAM|ROAP|SXARI): do their faint G-band epochs fall at
the conjunctions of their own Gaia orbit?

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0,
data CC BY 4.0 (Gaia DR3 epoch photometry and orbits: ESA/Gaia/DPAC).

EXPLORATORY, same dip rule as gaia_conj_dips 0.1.0 (thresholds chosen on 24 Nov while looking at
two other stars). New here: epochs that Gaia's variability processing flagged as rejected are kept
in a separate list ("rejected_faint") instead of being dropped, because some of them are eclipses.

Sample: Gaia DR3 nss_two_body_orbit SB2/SB2C solutions whose vari_classifier_result best class is
ACV|CP|MCP|ROAM|ROAP|SXARI (98 stars, AIP TAP 2026-11-24): all 15 with 3.0 <= P <= 4.02 d, plus
Gaia DR3 5409717025365557504 (P 2.03 d), read first to test the service -> the 16 stars below.
Three more of the 98 were analysed in gaia_conj_dips 0.1.0; the other 79 are not read yet.
Epochs: ESA DataLink (RETRIEVAL_LEVEL=RAW, CSV), 2026-11-24, G band only, time truncated to 1e-7 d
and magnitude to 1e-6. Columns: time, mag, rp (rejected_by_photometry), rv (rejected_by_variability).

Time systems as in gaia_conj_dips: epoch time = BJD(TCB) - 2455197.5; reference = 2191.5 + Tp.
Conjunctions at true anomaly nu = 90 - omega and 270 - omega (0.25/0.75 for SB2C).

Stdlib only. Usage: python gaia_conj_dips_acv.py [--out results.json]
"""
import argparse
import csv
import json
import math
import os

VERSION = "0.1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data", "gaia-conj-dips-acv")
GAIA_REF = 2191.5
DIP_MIN_MAG = 0.025
DIP_MIN_SIGMA = 4.0
WINDOW = 0.035

# source_id: (name, P, P_err, Tp, Tp_err, e, omega)  - gaiadr3.nss_two_body_orbit via AIP TAP
ORBITS = {
    "5409717025365557504": ("Gaia DR3 5409717025365557504", 2.026034252942195, 1.656458e-05, -0.009667206846785468, 0.0024476002, None, None),
    "5448354070122614400": ("Gaia DR3 5448354070122614400", 3.038381549236562, 7.277312e-05, 0.5699116020501014, 0.13346158, 0.045961534102825906, 0.26846398480916916),
    "1934924724387752832": ("HD 218299", 3.051283767729989, 2.189682e-05, -0.4685628521009657, 0.2770239, 0.006005845998197501, 344.77862698263635),
    "3479008554410838656": ("HD 101167", 3.0836443383497594, 3.6278656e-05, 0.26754640091710385, 0.013707602, 0.1760230375326379, 304.1770795699877),
    "5322036676774951808": ("Gaia DR3 5322036676774951808", 3.0908684351002034, 5.906901e-05, -0.8348669619254377, 0.08786456, 0.08915916952994926, 80.34260918127652),
    "2562554132208861568": ("Gaia DR3 2562554132208861568", 3.3431959994487874, 0.00020130262, 0.6393297641447097, 0.02477226, 0.34363250131444567, 81.19164714800331),
    "5866041495122321280": ("V1202 Cen", 3.3496895170251126, 0.000107897016, -0.9513930605365528, 0.05055127, 0.15074655040150808, 265.7491413552791),
    "427015307960557952": ("Gaia DR3 427015307960557952", 3.36966767623444, 2.364819e-05, 1.3701676137459482, 0.010515779, 0.20603861222047296, 10.619705605625638),
    "6702507988262437248": ("Gaia DR3 6702507988262437248", 3.4546616061514053, 0.00012828266, 1.3965145216093364, 0.0066354615, None, None),
    "5967067986401035008": ("Gaia DR3 5967067986401035008", 3.4972850913152462, 0.0003537939, -0.5227118904817804, 0.025261853, None, None),
    "1907116872732089216": ("Gaia DR3 1907116872732089216", 3.5204730654296337, 9.6253614e-05, -0.5529637736778122, 0.009862248, 0.5080786907448399, 337.50693289048274),
    "4490721395569773184": ("Gaia DR3 4490721395569773184", 3.5368861004293146, 2.6315161e-05, 0.8414780184100177, 0.06883437, 0.03076836095080055, 37.8410811250598),
    "2304516276636844800": ("Gaia DR3 2304516276636844800", 3.5977872026684192, 6.8049565e-05, -1.5980238285846198, 0.17123719, 0.027378234376392422, 82.66394323351655),
    "3231626306540378112": ("Gaia DR3 3231626306540378112", 3.849185275891331, 0.000114949544, 0.8254668250473934, 0.90662867, 0.005182464275828894, 16.7372397576635),
    "5759012181375799296": ("Gaia DR3 5759012181375799296", 3.915633914610029, 0.000103168866, -0.8477853801651181, 0.020936003, 0.2188559125993265, 80.89608946231343),
    "4297719103037032832": ("HD 187301", 4.015069743010301, 0.00015661815, 1.7524008240215443, 0.18337747, 0.0323837231038458, 17.684141016514925),
}


def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        raise ValueError("empty")
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def robust_sd(xs):
    m = median(xs)
    return 1.4826 * median([abs(x - m) for x in xs])


def true_to_phase(nu, e):
    E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0), math.sqrt(1.0 + e) * math.cos(nu / 2.0))
    M = E - e * math.sin(E)
    return (M / (2.0 * math.pi)) % 1.0


def conjunction_phases(e, omega_deg):
    e = e or 0.0
    w = math.radians(omega_deg or 0.0)
    return true_to_phase(math.pi / 2.0 - w, e), true_to_phase(3.0 * math.pi / 2.0 - w, e)


def dphase(a, b):
    return (a - b + 0.5) % 1.0 - 0.5


def load_epochs(source_id, data_dir=DATA_DIR):
    """All listed G rows: (t or None, mag or None, rejected_by_photometry, rejected_by_variability)."""
    rows = []
    with open(os.path.join(data_dir, "%s_g.csv" % source_id), newline="") as fh:
        for r in csv.DictReader(fh):
            t = None if r["time"].strip() in ("", "NA") else float(r["time"])
            m = None if r["mag"].strip() in ("", "NA") else float(r["mag"])
            rows.append((t, m, r["rp"].strip() in ("1", "true", "True"), r["rv"].strip() in ("1", "true", "True")))
    return rows


def analyse_star(source_id, data_dir=DATA_DIR):
    name, P, P_err, Tp, Tp_err, e, omega = ORBITS[source_id]
    rows = load_epochs(source_id, data_dir)
    valid = [r for r in rows if r[0] is not None and r[1] is not None and not r[2]]
    used = [r for r in valid if not r[3]]
    vrej = [r for r in valid if r[3]]
    med = median([r[1] for r in used])
    sd = robust_sd([r[1] for r in used])
    thr = max(DIP_MIN_MAG, DIP_MIN_SIGMA * sd)
    c1, c2 = conjunction_phases(e, omega)
    ref = GAIA_REF + Tp

    def describe(t, mag):
        ph = ((t - ref) / P) % 1.0
        d1, d2 = dphase(ph, c1), dphase(ph, c2)
        which, dd = ("c1", d1) if abs(d1) <= abs(d2) else ("c2", d2)
        n_cyc = (t - ref) / P
        return {"t": t, "mag": mag, "dmag": mag - med, "dmag_sigma": (mag - med) / sd if sd else None,
                "phase": ph, "nearest_conj": which, "dphase": dd, "offset_d": dd * P,
                "conj_time_sigma_d": math.hypot(Tp_err, abs(n_cyc) * P_err)}

    out = {"source_id": source_id, "name": name, "P": P, "e": e, "omega": omega,
           "n_listed": len(rows), "n_used": len(used), "n_rejected_by_variability": len(vrej),
           "median_mag": med, "robust_sd": sd, "dip_threshold_mag": thr, "conj_phases": [c1, c2],
           "conj_phase_sigma": Tp_err / P,
           "dips": [describe(t, m) for t, m, _, _ in used if m - med >= thr],
           "rejected_faint": [describe(t, m) for t, m, _, _ in vrej if m - med >= thr]}
    return out


def analyse_all(data_dir=DATA_DIR):
    stars = [analyse_star(s, data_dir) for s in ORBITS]
    dips = [d for s in stars for d in s["dips"]]
    rej = [d for s in stars for d in s["rejected_faint"]]
    return {"version": VERSION,
            "params": {"DIP_MIN_MAG": DIP_MIN_MAG, "DIP_MIN_SIGMA": DIP_MIN_SIGMA, "WINDOW": WINDOW},
            "stars": stars,
            "summary": {"n_stars": len(stars), "n_listed": sum(s["n_listed"] for s in stars),
                        "n_dips": len(dips),
                        "n_dips_in_window": sum(1 for d in dips if abs(d["dphase"]) <= WINDOW),
                        "stars_with_dips": sorted(s["name"] for s in stars if s["dips"]),
                        "n_rejected_faint": len(rej),
                        "n_rejected_faint_in_window": sum(1 for d in rej if abs(d["dphase"]) <= WINDOW)}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    res = analyse_all()
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(res, fh, indent=1)
    print(json.dumps(res["summary"], indent=1))
    for s in res["stars"]:
        print(s["name"], s["n_used"], "thr %.4f" % s["dip_threshold_mag"],
              "dips", [(round(d["t"], 4), round(d["dmag"], 3), round(d["phase"], 4), round(d["dphase"], 4)) for d in s["dips"]],
              "rej", [(round(d["t"], 4), round(d["dmag"], 3), round(d["phase"], 4), round(d["dphase"], 4)) for d in s["rejected_faint"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
