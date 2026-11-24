# SPDX-License-Identifier: Apache-2.0
"""tic93622019_gaia_epochs 0.1.0: where do TIC 93622019's faint Gaia epochs fall?

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.

EXPLORATORY. This is not the pre-registered test. The registered test of whether Gaia's own
G-band photometry shows TIC 93622019's dip at the TESS ephemeris is `vpt_epochs_extras.py tess`
(findings/2026-11-22-vpt-epochs-amendment-2.md, job gaia-vpt-epochs-box-v1, still queued).
This script neither replaces nor grades it. It lists, for every Gaia DR3 G epoch of
TIC 93622019 (Gaia DR3 5345417757181174144):
  * its offset from the nearest transit of the TESS ephemeris (job tic93622019-pixel-v1),
  * its offset from the nearest transit of Gaia DR3's own vari_planetary_transit solution
    (P = 2.8316579 d, a 4:3 alias of the TESS period),
  * its flux relative to the median,
and summarises the epochs inside each set of windows.

Epochs: copied verbatim from data/vpt-epochs-v2/epochs_g_2.csv (job gaia-vpt-epochs-v2):
time = BJD(TCB) - 2455197.5, G flux (e-/s), flux error, rejected (1 = rejected by Gaia's
variability processing). Two epochs with no G value are left out. Stdlib only.
"""
import argparse
import json
import math
import sys

VERSION = "0.1.0"
SOURCE_ID = "5345417757181174144"
TIC = "93622019"
GAIA_MINUS_BTJD = 1802.5      # Gaia epoch time = BTJD + 1802.5 (TCB - TDB, ~20 s, ignored)

# TESS ephemeris: job tic93622019-pixel-v1 (same numbers as vpt_epochs_extras.CANDIDATES[0])
P_TESS = 2.123893332667055
SIGMA_P_TESS = 3.044815104421753e-06
T0_TESS_BTJD = 3706.0868496452117
SIGMA_T0_TESS = 0.0006764471524484674
HALF_TESS = 0.0625            # half of the 0.125-d window of the registered test
CORE_TESS = 0.045             # well inside the transit (exploratory choice)

# Gaia DR3 vari_planetary_transit row (AIP TAP mirror gaia.aip.de, read 2026-11-24)
P_GAIA = 2.8316579357213647
T0_GAIA = 2202.348946244045   # Gaia epoch time
DUR_GAIA = 0.18627085
DEPTH_GAIA_MMAG = 11.902716
NUM_IN_TRANSIT_GAIA = 24

LOW = -0.006                  # "low" epoch: at least 0.6% below the median (exploratory)
N_NULL = 2000                 # deterministic phase shifts for an exploratory empirical p
NULL_MIN_IN = 2

EPOCHS = [  # (time, G flux, rejected)
    (1696.6984987, 176391.4, 0), (1696.7724808, 175686.5, 0),
    (1730.6319817, 177440.1, 1), (1730.8081355, 176376.2, 1), (1730.8821417, 177607.6, 1),
    (1775.9899559, 177343.9, 0), (1776.0639929, 176441.7, 0), (1788.3184463, 177346.7, 0),
    (1826.9527442, 176649.7, 0), (1854.6928718, 176556.3, 0), (1854.7668840, 176607.4, 0),
    (1882.0134542, 176885.2, 0), (1934.1787325, 177193.3, 0), (1934.2527039, 178076.2, 0),
    (1934.4288756, 177470.0, 0), (1934.6790329, 177113.2, 0), (1934.7530572, 177357.6, 0),
    (1950.0105853, 177382.5, 0), (1950.1867378, 177220.9, 0), (1950.4368980, 177613.4, 0),
    (1996.6695573, 176297.3, 0), (1996.7435605, 176502.3, 0), (2029.6526950, 173785.9, 0),
    (2054.1467827, 176260.2, 0), (2097.4158026, 177495.7, 0), (2097.5919583, 174888.1, 0),
    (2097.6659635, 175227.3, 0), (2106.0960637, 174922.7, 0), (2106.1700830, 176809.5, 0),
    (2106.3462250, 177503.5, 0), (2106.4202319, 177327.8, 0), (2151.1043005, 176862.9, 0),
    (2166.5338371, 176193.7, 0), (2166.6078292, 177030.2, 0), (2202.8237160, 175409.6, 0),
    (2258.8128364, 177188.3, 0), (2258.9890010, 175454.0, 0), (2312.9788583, 177488.6, 0),
    (2313.0528650, 177594.3, 0), (2313.2290203, 177389.7, 0), (2313.3029975, 177561.7, 0),
    (2333.0598207, 177376.6, 0), (2333.2359697, 176879.4, 0), (2333.3100488, 177433.0, 0),
    (2333.4861264, 177334.7, 0), (2373.7911766, 175649.4, 0), (2409.0160864, 175323.7, 0),
    (2430.1902722, 176928.3, 1), (2430.2642757, 176470.7, 1), (2474.9537290, 177358.2, 0),
    (2475.1298857, 177242.0, 0), (2482.2076737, 177946.1, 0), (2482.3838325, 176882.3, 0),
    (2526.3963192, 176429.9, 0), (2544.8236088, 176355.6, 0), (2544.8975992, 175953.0, 0),
    (2578.8714160, 175757.6, 0), (2614.8393091, 177112.2, 0), (2614.9133191, 177144.1, 0),
    (2635.9197157, 178333.9, 0), (2636.0958754, 177517.4, 0), (2636.1698844, 177873.7, 0),
    (2636.3460005, 177712.6, 0), (2691.0856977, 177278.9, 0), (2691.1597299, 177873.6, 0),
]


def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return float("nan")
    m = n // 2
    return s[m] if n % 2 else 0.5 * (s[m - 1] + s[m])


def robust_sd(xs):
    m = median(xs)
    return 1.4826 * median([abs(x - m) for x in xs])


def offset(t, t0, p):
    """Signed time from t to the nearest event of ephemeris (t0, p), in days."""
    c = (t - t0) / p
    return (c - round(c)) * p


def summarise(sel, sd):
    v = [r["rel"] for r in sel]
    out = {"n": len(v), "times": [r["time"] for r in sel], "rel": [round(x, 6) for x in v]}
    if v:
        mean = sum(v) / len(v)
        out["mean_rel"] = mean
        out["depth"] = -mean
        out["snr"] = -mean / (sd / math.sqrt(len(v))) if sd > 0 else float("nan")
    return out


def null_p(rows, t0g, sd, observed_snr, n_null=N_NULL):
    """Exploratory empirical p: shift the TESS windows by evenly spaced offsets in
    [2*HALF_TESS, P - 2*HALF_TESS] and count shifts whose window mean is at least as significant."""
    lo, hi = 2 * HALF_TESS, P_TESS - 2 * HALF_TESS
    n_valid = n_ge = 0
    best = -float("inf")
    for k in range(n_null):
        off = lo + (hi - lo) * (k + 0.5) / n_null
        v = [r["rel"] for r in rows if abs(offset(r["time"], t0g + off, P_TESS)) <= HALF_TESS]
        if len(v) < NULL_MIN_IN:
            continue
        snr = -(sum(v) / len(v)) / (sd / math.sqrt(len(v)))
        n_valid += 1
        best = max(best, snr)
        if snr >= observed_snr:
            n_ge += 1
    return {"n_null": n_valid, "n_null_ge": n_ge, "p_emp": (1 + n_ge) / (1 + n_valid),
            "best_null_snr": best}


def analyse():
    t0g = T0_TESS_BTJD + GAIA_MINUS_BTJD
    good = [(t, f) for t, f, rej in EPOCHS if not rej]
    med = median([f for _, f in good])
    rows = []
    for t, f in good:
        dt_t = offset(t, t0g, P_TESS)
        dt_g = offset(t, T0_GAIA, P_GAIA)
        rows.append({
            "time": t, "btjd": round(t - GAIA_MINUS_BTJD, 7), "rel": f / med - 1.0,
            "dt_tess": dt_t, "phase_tess": ((t - t0g) / P_TESS) % 1.0, "dt_gaia": dt_g,
            "in_tess": abs(dt_t) <= HALF_TESS, "core_tess": abs(dt_t) <= CORE_TESS,
            "in_gaia": abs(dt_g) <= DUR_GAIA / 2.0,
        })
    out_both = [r["rel"] for r in rows if not r["in_tess"] and not r["in_gaia"]]
    sd = robust_sd(out_both)
    t_mid = 0.5 * (rows[0]["time"] + rows[-1]["time"])
    ncyc = (t_mid - t0g) / P_TESS
    timing_sigma = math.sqrt((ncyc * SIGMA_P_TESS) ** 2 + SIGMA_T0_TESS ** 2)
    in_t = [r for r in rows if r["in_tess"]]
    res = {
        "version": VERSION, "source_id": SOURCE_ID, "tic": TIC,
        "n_epochs_listed": len(EPOCHS), "n_epochs_used": len(rows),
        "median_flux": med, "robust_sd_out_of_both": sd,
        "tess_timing_sigma_d": timing_sigma, "tess_cycles_back": ncyc,
        "in_tess": summarise(in_t, sd),
        "core_tess": summarise([r for r in rows if r["core_tess"]], sd),
        "in_gaia": summarise([r for r in rows if r["in_gaia"]], sd),
        "both": summarise([r for r in rows if r["in_tess"] and r["in_gaia"]], sd),
        "tess_only": summarise([r for r in rows if r["in_tess"] and not r["in_gaia"]], sd),
        "gaia_only": summarise([r for r in rows if r["in_gaia"] and not r["in_tess"]], sd),
    }
    res["gaia_only"]["phase_tess"] = [round(r["phase_tess"], 4) for r in rows
                                      if r["in_gaia"] and not r["in_tess"]]
    not_t = [r for r in rows if not r["in_tess"]]
    low = [r for r in not_t if r["rel"] < LOW]
    res["outside_tess_windows"] = {
        "n": len(not_t), "n_low": len(low), "n_low_in_gaia_box": sum(1 for r in low if r["in_gaia"]),
        "low_times": [r["time"] for r in low],
        "low_dt_tess": [round(r["dt_tess"], 4) for r in low],
    }
    res["null"] = null_p(rows, t0g, sd, res["in_tess"].get("snr", float("nan")))
    res["epochs"] = [{k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}
                     for r in rows]
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    res = analyse()
    text = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    short = {k: v for k, v in res.items() if k != "epochs"}
    print(json.dumps(short, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
