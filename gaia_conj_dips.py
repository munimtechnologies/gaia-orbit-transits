# SPDX-License-Identifier: Apache-2.0
"""gaia_conj_dips 0.1.0 - do faint Gaia DR3 G-band epochs of edge-on double-lined binaries fall at the
conjunctions that Gaia's own spectroscopic orbit predicts?

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0,
data CC BY 4.0 (Gaia DR3 epoch photometry and orbits: ESA/Gaia/DPAC).

EXPLORATORY. Thresholds (DIP_MIN_MAG, DIP_MIN_SIGMA) were chosen while looking at the data. The
registered test of these stars is the TESS full-frame fold in gaia_dip_ffi.py
(findings/2026-11-24-gaia-conj-dips-prereg.md).

Sample: all 19 stars of the sb2-edgeon-screen-v1 table (commit 80be282) with no TESS pipeline
detection (tce_class NONE, or status NO_TIC) that Gaia DR3 classified as a non-eclipsing variable
(gaia_class not empty and not ECL), so that Gaia published their epoch photometry. Epochs were read from ESA's DataLink service on
2026-11-24 (time rounded to 1e-7 d, magnitude to 1e-6). Orbits from gaiadr3.nss_two_body_orbit
(AIP TAP mirror, 2026-11-24).

Time systems: Gaia epoch times are BJD(TCB) - 2455197.5; t_periastron is days from JD 2457389.0,
so the reference in epoch-time units is 2191.5 + t_periastron. Phase 0 is periastron; for circular
solutions (SB2C) Gaia fixes omega = 0, so phase 0 is the ascending node and the conjunctions are at
0.25 and 0.75 (same convention as sb2_ffiscan.conjunction_phases).

Stdlib only. Usage: python gaia_conj_dips.py [--out results.json]
"""
import argparse
import csv
import json
import math
import os

VERSION = "0.1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data", "gaia-conj-dips")
GAIA_REF = 2191.5          # JD 2457389.0 in Gaia epoch-photometry time (BJD - 2455197.5)
DIP_MIN_MAG = 0.025        # a dip is at least this much fainter than the star's median ...
DIP_MIN_SIGMA = 4.0        # ... and at least this many robust standard deviations
WINDOW = 0.035             # half-width (phase) of the listing window around each conjunction

# Gaia DR3 nss_two_body_orbit rows (AIP TAP, 2026-11-24). e/omega None for circular (SB2C) fits.
ORBITS = {
    "5288669213282803328": {"name": "CD-63 310", "tic": 349572805, "type": "SB2C",
                            "P": 5.410625783263602, "P_err": 0.0002401259,
                            "Tp": 1.9337617530558862, "Tp_err": 0.014801174, "e": None, "omega": None,
                            "K1": 92.72057990660561, "K2": 94.55847559555623},
    "6374372070227419008": {"name": "CD-72 1603", "tic": 371839648, "type": "SB2C",
                            "P": 4.566931695393036, "P_err": 0.00013138614,
                            "Tp": 0.8165975979109842, "Tp_err": 0.005994778, "e": None, "omega": None,
                            "K1": 90.44548852036775, "K2": 87.72602356686114},
    "6025454428973694464": {"name": "Gaia DR3 6025454428973694464", "tic": 212031970, "type": "SB2",
                            "P": 1.059592647827001, "P_err": 8.161422e-06,
                            "Tp": -0.41031767260035623, "Tp_err": 0.013155527,
                            "e": 0.16940352453282803, "omega": 335.7909680229006,
                            "K1": 182.59233286879405, "K2": 177.21136398460305},
    "6370053605166404992": {"name": "Gaia DR3 6370053605166404992", "tic": 311430361, "type": "SB2",
                            "P": 2.2299478395230414, "P_err": 1.2748673e-05,
                            "Tp": -0.6098968379508477, "Tp_err": 0.11357646,
                            "e": 0.01510055464865544, "omega": 97.53471842855362,
                            "K1": 103.05189439243637, "K2": 136.08252702599904},
    "3043555010111094400": {"name": "Gaia DR3 3043555010111094400", "tic": 32399700, "type": "SB2C",
                            "P": 4.90690984742347, "P_err": 0.0003543802,
                            "Tp": -1.8102362360337056, "Tp_err": 0.020095067, "e": None, "omega": None,
                            "K1": 78.4961162385882, "K2": 91.91322175294195},
    "2995056243702062080": {"name": "Gaia DR3 2995056243702062080", "tic": 317413770, "type": "SB2C",
                            "P": 4.741729755883772, "P_err": 0.00013839928,
                            "Tp": -2.3429120638987397, "Tp_err": 0.007745481, "e": None, "omega": None,
                            "K1": 77.85381077749506, "K2": 78.76882982282125},
    "3419201066092932992": {"name": "Gaia DR3 3419201066092932992", "tic": 356984148, "type": "SB2",
                            "P": 4.347980646942389, "P_err": 0.00010929686,
                            "Tp": 1.2945279441694633, "Tp_err": 0.505665,
                            "e": 0.009612749715390589, "omega": 337.21577695736187,
                            "K1": 83.90717713815128, "K2": 84.0529344817707},
    "6547214134176807808": {"name": "Gaia DR3 6547214134176807808", "tic": 214875017, "type": "SB2",
                            "P": 6.680747581467151, "P_err": 0.00011896142,
                            "Tp": -0.2489808284177655, "Tp_err": 0.099358216,
                            "e": 0.06847428277583262, "omega": 329.90684781940007,
                            "K1": 61.855715921137765, "K2": 73.78742123647956},
    "3024112659531165568": {"name": "Gaia DR3 3024112659531165568", "tic": 176476906, "type": "SB2C",
                            "P": 5.048339956613013, "P_err": 0.00014158417,
                            "Tp": 0.21688664728293178, "Tp_err": 0.0072538927, "e": None, "omega": None,
                            "K1": 78.2084999781681, "K2": 77.9171328122066},
    "5512207383273412864": {"name": "Gaia DR3 5512207383273412864", "tic": 60024366, "type": "SB2",
                            "P": 5.425975641024243, "P_err": 0.00016569246,
                            "Tp": 0.947569393661101, "Tp_err": 1.431799,
                            "e": 0.00632711108630002, "omega": 350.8116457424885,
                            "K1": 67.72788337628127, "K2": 78.25094421340228},
    "5871568499564025472": {"name": "Gaia DR3 5871568499564025472", "tic": 453601725, "type": "SB2",
                            "P": 5.5667404530670765, "P_err": 0.00015452717,
                            "Tp": 2.3824037688120994, "Tp_err": 0.5651078,
                            "e": 0.013587478411290157, "omega": 39.30315325487776,
                            "K1": 77.8736888609918, "K2": 76.02642698772608},
    "1734078000491716224": {"name": "Gaia DR3 1734078000491716224", "tic": 418376897, "type": "SB2",
                            "P": 6.886963081143411, "P_err": 0.0005136027,
                            "Tp": -0.6385478935489669, "Tp_err": 1.502132,
                            "e": 0.008975715893550843, "omega": 351.2646879733408,
                            "K1": 65.765855502471, "K2": 62.503332279546974},
    "1615317447472056448": {"name": "Gaia DR3 1615317447472056448", "tic": 311113785, "type": "SB2",
                            "P": 6.430356540723839, "P_err": 0.0001028001,
                            "Tp": 1.4421020398980222, "Tp_err": 0.14658992,
                            "e": 0.030273872077522516, "omega": 327.2022374255628,
                            "K1": 63.80158935546729, "K2": 67.22117799931057},
    "6668966900715757312": {"name": "Gaia DR3 6668966900715757312", "tic": 129479804, "type": "SB2",
                            "P": 5.860347458841086, "P_err": 0.00037390256,
                            "Tp": 1.1510217771344986, "Tp_err": 0.46380633,
                            "e": 0.029855106653592565, "omega": 12.151655592174945,
                            "K1": 72.58798938684086, "K2": 73.98688655363738},
    # the next five had no TIC match in the sb2-edgeon-screen-v1 table (status NO_TIC)
    "3323030323068415744": {"name": "Gaia DR3 3323030323068415744", "tic": None, "type": "SB2",
                            "P": 6.277634553103068, "P_err": 0.00019433314,
                            "Tp": -0.6420099523954649, "Tp_err": 2.0194912,
                            "e": 0.004805344395846196, "omega": 265.7622839055685,
                            "K1": 70.98111659832307, "K2": 70.57462252830366},
    "6705693548324328960": {"name": "Gaia DR3 6705693548324328960", "tic": None, "type": "SB2",
                            "P": 6.316071852777447, "P_err": 0.00022187257,
                            "Tp": -1.0916583515170104, "Tp_err": 0.15515631,
                            "e": 0.04200966566704314, "omega": 51.87953948365951,
                            "K1": 71.5955434670508, "K2": 72.04922613687539},
    "5442901385802064000": {"name": "Gaia DR3 5442901385802064000", "tic": None, "type": "SB2",
                            "P": 4.614297337470955, "P_err": 8.197105e-05,
                            "Tp": 0.26964530416564436, "Tp_err": 0.36646497,
                            "e": 0.009944842930130603, "omega": 66.03518467822903,
                            "K1": 76.80211471766683, "K2": 81.57218850509231},
    "5448988969368351616": {"name": "Gaia DR3 5448988969368351616", "tic": None, "type": "SB2",
                            "P": 7.684033601427606, "P_err": 0.00022985136,
                            "Tp": 2.6729331636524982, "Tp_err": 0.37485972,
                            "e": 0.022073103967628686, "omega": 84.69328407382211,
                            "K1": 64.97455703644756, "K2": 57.120665320754064},
    "3944246249499094272": {"name": "Gaia DR3 3944246249499094272", "tic": None, "type": "SB2",
                            "P": 7.390648716066103, "P_err": 0.00047580295,
                            "Tp": -2.6892557941097834, "Tp_err": 0.19649932,
                            "e": 0.10004819996810528, "omega": 273.2535098544623,
                            "K1": 67.66593804936576, "K2": 64.89986016036912},
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
    """True anomaly (rad) -> fraction of the period after periastron, in [0, 1)."""
    E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0), math.sqrt(1.0 + e) * math.cos(nu / 2.0))
    M = E - e * math.sin(E)
    return (M / (2.0 * math.pi)) % 1.0


def conjunction_phases(e, omega_deg):
    """Phases after periastron of the two conjunctions (nu + omega = 90 and 270 deg)."""
    e = e or 0.0
    w = math.radians(omega_deg or 0.0)
    c1 = true_to_phase(math.pi / 2.0 - w, e)
    c2 = true_to_phase(3.0 * math.pi / 2.0 - w, e)
    return c1, c2


def phase(t, orb):
    return ((t - (GAIA_REF + orb["Tp"])) / orb["P"]) % 1.0


def dphase(a, b):
    """Signed phase difference a - b wrapped to [-0.5, 0.5)."""
    return (a - b + 0.5) % 1.0 - 0.5


def load_epochs(source_id, data_dir=DATA_DIR):
    path = os.path.join(data_dir, "%s_g.csv" % source_id)
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            if not r["time"].strip() or not r["mag"].strip():
                continue          # transits with no G value (all such rows are flagged rejected)
            rows.append({"t": float(r["time"]), "mag": float(r["mag"]),
                         "rej": r["rejected_by_photometry"].strip().lower() == "true"
                         or r["rejected_by_variability"].strip().lower() == "true"})
    return rows


def analyse_star(source_id, data_dir=DATA_DIR):
    orb = ORBITS[source_id]
    rows = load_epochs(source_id, data_dir)
    used = [r for r in rows if not r["rej"]]
    mags = [r["mag"] for r in used]
    med = median(mags)
    sd = robust_sd(mags)
    c1, c2 = conjunction_phases(orb["e"], orb["omega"])
    out = {"source_id": source_id, "name": orb["name"], "tic": orb["tic"], "type": orb["type"],
           "P": orb["P"], "n_listed": len(rows), "n_used": len(used), "median_mag": med,
           "robust_sd": sd, "conj_phases": [c1, c2], "dips": [], "near_conj": {"c1": [], "c2": []}}
    thr = max(DIP_MIN_MAG, DIP_MIN_SIGMA * sd)
    out["dip_threshold_mag"] = thr
    for r in used:
        ph = phase(r["t"], orb)
        dm = r["mag"] - med
        d1, d2 = dphase(ph, c1), dphase(ph, c2)
        which, dd = ("c1", d1) if abs(d1) <= abs(d2) else ("c2", d2)
        if abs(d1) <= WINDOW:
            out["near_conj"]["c1"].append({"t": r["t"], "phase": ph, "dphase": d1, "dmag": dm})
        if abs(d2) <= WINDOW:
            out["near_conj"]["c2"].append({"t": r["t"], "phase": ph, "dphase": d2, "dmag": dm})
        if dm >= thr:
            n_cyc = (r["t"] - (GAIA_REF + orb["Tp"])) / orb["P"]
            sig_t = math.hypot(orb["Tp_err"], abs(n_cyc) * orb["P_err"])
            out["dips"].append({"t": r["t"], "mag": r["mag"], "dmag": dm, "dmag_sigma": dm / sd,
                                "phase": ph, "nearest_conj": which, "dphase": dd,
                                "offset_d": dd * orb["P"], "conj_time_sigma_d": sig_t,
                                "cycles_from_Tp": n_cyc})
    return out


def analyse_all(data_dir=DATA_DIR):
    res = {"version": VERSION, "params": {"DIP_MIN_MAG": DIP_MIN_MAG, "DIP_MIN_SIGMA": DIP_MIN_SIGMA,
                                          "WINDOW": WINDOW, "GAIA_REF": GAIA_REF},
           "stars": [analyse_star(s, data_dir) for s in ORBITS]}
    with_dips = [s for s in res["stars"] if s["dips"]]
    all_dips = [d for s in with_dips for d in s["dips"]]
    res["summary"] = {
        "n_stars": len(res["stars"]),
        "n_stars_with_dips": len(with_dips),
        "n_dips": len(all_dips),
        "n_dips_within_0p01_of_conj": sum(1 for d in all_dips if abs(d["dphase"]) <= 0.01),
        "stars_with_dips": [s["name"] for s in with_dips],
    }
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    res = analyse_all()
    text = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(text)
    print(json.dumps(res["summary"], indent=1))
    for s in res["stars"]:
        print(s["name"], "n_used", s["n_used"], "median %.5f sd %.5f" % (s["median_mag"], s["robust_sd"]),
              "dips", [(round(d["t"], 4), round(d["dmag"], 4), round(d["phase"], 4), d["nearest_conj"])
                       for d in s["dips"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
