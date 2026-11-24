# SPDX-License-Identifier: Apache-2.0
"""gaia_conj_dips_acv2 0.1.0 - batch 2 of the ACV-labelled Gaia DR3 double-lined binaries
(2.0 < P < 3.0 d), run with the UNCHANGED dip rule of gaia_conj_dips_acv 0.1.0, plus a timing check
of Gaia's own faint epochs against the TESS eclipse ephemerides of IJspeert et al. (2024).

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0,
data CC BY 4.0 (Gaia DR3 epoch photometry and orbits: ESA/Gaia/DPAC; TESS ephemerides: IJspeert
et al. 2024, A&A 691, A242, VizieR J/A+A/691/A242/obaf-eb1, read 2026-11-24).

Selection (fixed in findings/2026-11-24-acv-batch2-prereg.md before any epoch was read): every
Gaia DR3 SB2/SB2C orbit whose vari_classifier best class is ACV|CP|MCP|ROAM|ROAP|SXARI with
2.0 < P < 3.0 d not read before -> 15 stars. Epochs: ESA DataLink, 2026-11-24, G band.
Columns: time, mag, rp (rejected_by_photometry), rv (variability_flag_g_reject).

Rule (copied, not changed): dip = unflagged epoch >= max(0.025 mag, 4 robust SD) fainter than the
median of unflagged epochs; window +/-0.035 in phase around the two conjunctions (true anomaly
90 - omega and 270 - omega; 0.25/0.75 for SB2C). Time: Gaia epoch time = BJD(TCB) - 2455197.5;
orbit reference = 2191.5 + Tp. TESS BTJD = BJD - 2457000 = Gaia time - 1802.5.

Stdlib only. Usage: python gaia_conj_dips_acv2.py [--out results.json]
"""
import argparse
import csv
import json
import math
import os

VERSION = "0.1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data", "gaia-conj-dips-acv2")
GAIA_REF = 2191.5
GAIA_TO_BTJD = -1802.5
DIP_MIN_MAG = 0.025
DIP_MIN_SIGMA = 4.0
WINDOW = 0.035

# source_id: (name, P, P_err, Tp, Tp_err, e, omega) - gaiadr3.nss_two_body_orbit via AIP TAP, 24 Nov
ORBITS = {
    "6158619786886806016": ("Gaia DR3 6158619786886806016", 2.1251430518078536, 6.1587643e-06, 0.07619815848190196, 0.014157625, 0.05975571230529917, 297.25008865549927),
    "355656522274764288": ("Gaia DR3 355656522274764288", 2.142539139498957, 0.00083591876, -0.745350730026118, 0.054252293, None, None),
    "3032388065085357440": ("Gaia DR3 3032388065085357440", 2.1800160226214196, 2.2622748e-05, -0.826587513842343, 0.020270508, 0.2046098554577127, 308.1467554156924),
    "4211060509978414208": ("Gaia DR3 4211060509978414208", 2.292463032994547, 1.3163258e-05, 0.8232061779156884, 0.0017169638, None, None),
    "5387577190509272832": ("CD-44 6966", 2.3872179377467266, 4.309846e-05, 0.0894674244919104, 0.5208173, 0.005265189206883529, 249.73806961518443),
    "66729880383767168": ("V1229 Tau (HD 23642)", 2.461185529609541, 1.6674667e-05, -0.8677796199970627, 0.13842371, 0.015445646291139647, 138.8023362402148),
    "4945020530510815360": ("Gaia DR3 4945020530510815360", 2.463289227440211, 3.4339522e-05, 0.23282029289507067, 0.0660285, 0.051147918705078926, 275.79973873040524),
    "265213581990291840": ("Gaia DR3 265213581990291840", 2.5867331441449353, 2.3606455e-05, -1.2550384507044257, 0.021081729, 0.14713257344311695, 355.9824917172001),
    "911500121588495744": ("Gaia DR3 911500121588495744", 2.666836608075459, 2.8220999e-05, -0.31351789969765287, 0.39475316, 0.009319771083045079, 40.73834145463707),
    "3347294105150514688": ("Gaia DR3 3347294105150514688", 2.705785687593372, 5.687677e-05, -0.311420071152013, 0.28330082, 0.01856632145658544, 351.14049012055045),
    "4582483440569725184": ("Gaia DR3 4582483440569725184", 2.8375541039611054, 9.09131e-06, -1.3707244617961036, 0.21676075, 0.004844315345928164, 31.093110148772833),
    "1853022343761824768": ("Gaia DR3 1853022343761824768", 2.849078197506438, 9.389364e-05, -1.1288809821208363, 0.0623601, 0.14077510379939906, 279.93543594595144),
    "5645527428755291648": ("Gaia DR3 5645527428755291648", 2.91561467482392, 1.6609189e-05, -0.9530413480813058, 0.0015790411, None, None),
    "5305914640875063424": ("Gaia DR3 5305914640875063424", 2.98178503209443, 1.7936512e-05, 0.5722986188345704, 0.0031274273, 0.5919801867949734, 7.013988053272882),
    "6879998061518438400": ("Gaia DR3 6879998061518438400", 2.9866636047580712, 5.1122784e-05, -0.26911126885820075, 0.27747035, 0.01997941504332546, 358.7818330769508),
}

# IJspeert et al. (2024) obaf-eb1 rows for stars whose Gaia epochs we compared with TESS
# (TIC, dataset, t0 [BTJD], Per [d]; Per is the orbital period or half of it).
IJSPEERT = {
    "HD 218299": (173207470, "SPOCy2", 1739.6032030690899, 1.52595149185236911),
    "HD 101167": (57791790, "SPOCy1", 1573.1513388872547, 6.16741930608519695),
    "CD-44 6966": (178414920, "SPOCy1", 1544.6185261500375, 1.19385607843981556),
    "CD-44 6966 y3": (178414920, "SPOCy3", 2282.2555949979683, 1.19381337619742434),
    "V1229 Tau (HD 23642)": (125754991, "SPOCy4", 2450.2189084595034, 2.461122789251443788),
    "Gaia DR3 911500121588495744": (188378024, "SPOCy4", 2581.2186111921169, 1.333434504724922309),
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


def tess_offset(t_gaia, t0_btjd, period):
    """Time (d) from the nearest predicted TESS eclipse (t0 + n*period) to a Gaia epoch time.
    Positive = the Gaia epoch is later than the predicted eclipse."""
    x = (t_gaia + GAIA_TO_BTJD - t0_btjd) / period
    return (x - round(x)) * period


def load_epochs(source_id, data_dir=DATA_DIR):
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
        return {"t": t, "mag": mag, "dmag": mag - med, "phase": ph, "nearest_conj": which,
                "dphase": dd, "offset_d": dd * P}

    faintest = sorted(used, key=lambda r: -r[1])[:3]
    return {"source_id": source_id, "name": name, "P": P, "e": e, "omega": omega,
            "n_listed": len(rows), "n_used": len(used), "n_rejected_by_variability": len(vrej),
            "median_mag": med, "robust_sd": sd, "dip_threshold_mag": thr, "conj_phases": [c1, c2],
            "conj_phase_sigma": Tp_err / P,
            "dips": [describe(t, m) for t, m, _, _ in used if m - med >= thr],
            "rejected_faint": [describe(t, m) for t, m, _, _ in vrej if m - med >= thr],
            "faintest3": [describe(t, m) for t, m, _, _ in faintest]}


def analyse_all(data_dir=DATA_DIR):
    stars = [analyse_star(s, data_dir) for s in ORBITS]
    dips = [d for s in stars for d in s["dips"]]
    return {"version": VERSION,
            "params": {"DIP_MIN_MAG": DIP_MIN_MAG, "DIP_MIN_SIGMA": DIP_MIN_SIGMA, "WINDOW": WINDOW},
            "stars": stars,
            "summary": {"n_stars": len(stars), "n_listed": sum(s["n_listed"] for s in stars),
                        "n_dips": len(dips),
                        "n_dips_in_window": sum(1 for d in dips if abs(d["dphase"]) <= WINDOW),
                        "stars_with_dips": sorted(s["name"] for s in stars if s["dips"])}}


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
              "dips", [(round(d["t"], 4), round(d["dmag"], 3), round(d["phase"], 4)) for d in s["dips"]],
              "rej", [(round(d["t"], 4), round(d["dmag"], 3), round(d["phase"], 4)) for d in s["rejected_faint"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
