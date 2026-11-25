# SPDX-License-Identifier: Apache-2.0
"""gaia_chroma 0.2.0 - is a transit the same depth in Gaia's blue (BP) and red (RP) light?

MV2, Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.
Repository: https://github.com/munimtechnologies/gaia-orbit-transits

0.2.0 (25 Nov 2026): adds the third Gaia transit candidate, TIC 93622019 (Gaia DR3
5345417757181174144, TESS ephemeris from findings/2026-11-24-tic93622019-gaia-rv-limit.md).
Rules and the two 0.1.0 targets are unchanged. Its epoch table was transcribed from the AIP Gaia
TAP mirror with fluxes rounded to 0.1 e/s (times in full) and has no flux-error columns; the code
does not use them.

Exploratory vetting step (not pre-registered; the windows below were chosen after the data of the
first two stars had been looked at, and applied unchanged to the third). For each candidate it
reads Gaia DR3 per-transit epoch photometry (one row per Gaia field-of-view transit, G, BP and RP
fluxes measured within about a minute of each other), phases every row on the TESS ephemeris and
compares the dip depth in the three bands.

A transit of a planet or of any body across the target itself is nearly colour-neutral (only limb
darkening makes it a few per cent deeper in the blue). An eclipse on an unresolved source of a
different colour gives depths that differ between BP and RP: in the limit where that source adds
little light, depth(BP) / depth(RP) ~ 10 ** (-0.4 * dC), dC = its BP-RP colour minus the
target's.

Rules (fixed in this file):
  * time = g_transit_time (Gaia time, BJD_TCB - 2455197.5); rows without it are not used;
  * residual r = t - (T0 + n P), n = round((t - T0) / P), T0 = T0_BTJD + 1802.5;
  * in transit: |r| < 0.05 d; out of transit: |r| > 0.10 d; rows in between are not used;
  * per band: baseline = median of the out-of-transit fluxes after dropping gross outliers
    (|flux / median - 1| > 0.05; the median is first computed with them); scatter = 1.4826 MAD;
  * depth = 1 - flux / baseline for every in-transit flux that is not a gross outlier;
  * Gaia's photometric rejection flags are NOT applied (in these stars they mark mostly the
    in-transit BP/RP values; see the flag counts in the output);
  * comparison only on epochs where G, BP and RP all have a depth; mean depth per band, error =
    scatter / sqrt(k); BP/RP ratio of the means with first-order error; leave-one-epoch-out
    (jackknife) ratios; median over epochs of depth(BP) - depth(RP).

Usage: python gaia_chroma.py --data-dir data/gaia-chroma [--out results.json]
"""
import argparse
import csv
import json
import math
import os
import statistics

VERSION = "0.2.0"
BTJD_TO_GAIA = 1802.5          # Gaia epoch time = BTJD + 1802.5
IN_HALF = 0.05                 # d
OUT_MIN = 0.10                 # d
GROSS = 0.05
MAD_TO_SIGMA = 1.4826

TARGETS = {
    "5432318139709900160": {"tic": "TIC 44997521", "P": 3.54941, "T0_btjd": 1546.48145},
    "5431056347037926784": {"tic": "TIC 4638108", "P": 2.20828, "T0_btjd": 1517.88102},
    "5345417757181174144": {"tic": "TIC 93622019", "P": 2.1238933, "T0_btjd": 3706.08685},
}
BANDS = (("G", "g_transit_flux", "variability_flag_g_reject"),
         ("BP", "bp_flux", "photometry_flag_bp_reject"),
         ("RP", "rp_flux", "photometry_flag_rp_reject"))
NAN = float("nan")


def fnum(v):
    try:
        x = float(str(v).strip())
    except (TypeError, ValueError):
        return NAN
    return x if math.isfinite(x) else NAN


def truthy(v):
    return str(v).strip().lower() in ("true", "1", "t", "yes")


def load_rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def residual(t, P, T0g):
    n = round((t - T0g) / P)
    return t - (T0g + n * P)


def mad_sigma(xs):
    m = statistics.median(xs)
    return MAD_TO_SIGMA * statistics.median([abs(x - m) for x in xs])


def analyse(rows, P, T0_btjd):
    T0g = T0_btjd + BTJD_TO_GAIA
    recs = []
    for r in rows:
        t = fnum(r.get("g_transit_time"))
        if not math.isfinite(t):
            continue
        rec = {"t": t, "r": residual(t, P, T0g)}
        for b, col, flag in BANDS:
            rec[b] = fnum(r.get(col))
            rec[b + "_flag"] = truthy(r.get(flag, ""))
        recs.append(rec)
    out_recs = [x for x in recs if abs(x["r"]) > OUT_MIN]
    in_recs = [x for x in recs if abs(x["r"]) < IN_HALF]
    base = {}
    for b, _, _ in BANDS:
        xs = [x[b] for x in out_recs if math.isfinite(x[b])]
        med0 = statistics.median(xs)
        keep = [v for v in xs if abs(v / med0 - 1.0) <= GROSS]
        med = statistics.median(keep)
        base[b] = {"median": med, "sigma_rel": mad_sigma([v / med - 1.0 for v in keep]),
                   "n": len(keep), "n_gross_dropped": len(xs) - len(keep)}
    epochs = []
    for x in in_recs:
        e = {"t": x["t"], "r": x["r"]}
        for b, _, _ in BANDS:
            f = x[b]
            ok = math.isfinite(f) and abs(f / base[b]["median"] - 1.0) <= GROSS
            e["depth_" + b] = (1.0 - f / base[b]["median"]) if ok else NAN
            e["flag_" + b] = x[b + "_flag"]
        epochs.append(e)
    common = [e for e in epochs if all(math.isfinite(e["depth_" + b]) for b, _, _ in BANDS)]
    k = len(common)
    res = {"n_rows_timed": len(recs), "n_in": len(in_recs), "n_out": len(out_recs),
           "n_common": k, "baseline": base, "epochs": epochs}
    if k == 0:
        return res
    mean = {b: sum(e["depth_" + b] for e in common) / k for b, _, _ in BANDS}
    err = {b: base[b]["sigma_rel"] / math.sqrt(k) for b, _, _ in BANDS}
    ratio = mean["BP"] / mean["RP"]
    ratio_err = ratio * math.sqrt((err["BP"] / mean["BP"]) ** 2 + (err["RP"] / mean["RP"]) ** 2)
    diff = mean["BP"] - mean["RP"]
    diff_err = math.sqrt(err["BP"] ** 2 + err["RP"] ** 2)
    jack = []
    if k >= 2:
        for i in range(k):
            sub = common[:i] + common[i + 1:]
            jb = sum(e["depth_BP"] for e in sub)
            jr = sum(e["depth_RP"] for e in sub)
            jack.append({"dropped_t": common[i]["t"], "ratio": jb / jr})
    res.update({
        "mean_depth": mean, "mean_depth_err": err,
        "bp_rp_ratio": ratio, "bp_rp_ratio_err": ratio_err,
        "bp_minus_rp": diff, "bp_minus_rp_err": diff_err, "bp_minus_rp_z": diff / diff_err,
        "jackknife": jack,
        "jackknife_min": min(j["ratio"] for j in jack) if jack else NAN,
        "jackknife_max": max(j["ratio"] for j in jack) if jack else NAN,
        "median_epoch_bp_minus_rp": statistics.median(
            [e["depth_BP"] - e["depth_RP"] for e in common]),
    })
    return res


def flag_counts(rows, P, T0_btjd):
    """Gaia photometric rejection flags on finite BP/RP values, in and out of transit."""
    T0g = T0_btjd + BTJD_TO_GAIA
    c = {"in_n": 0, "in_flagged": 0, "out_n": 0, "out_flagged": 0}
    for r in rows:
        t = fnum(r.get("g_transit_time"))
        if not math.isfinite(t):
            continue
        rr = abs(residual(t, P, T0g))
        where = "in" if rr < IN_HALF else ("out" if rr > OUT_MIN else None)
        if where is None:
            continue
        for b, col, flag in BANDS[1:]:
            if math.isfinite(fnum(r.get(col))):
                c[where + "_n"] += 1
                c[where + "_flagged"] += int(truthy(r.get(flag, "")))
    return c


def find_file(data_dir, name):
    p = os.path.join(data_dir, name)
    if os.path.exists(p):
        return p
    for root, _dirs, files in os.walk(data_dir):
        if name in files:
            return os.path.join(root, name)
    raise FileNotFoundError(name)


def run(data_dir):
    out = {"version": VERSION, "rules": {"IN_HALF_d": IN_HALF, "OUT_MIN_d": OUT_MIN,
                                         "GROSS": GROSS}, "targets": {}}
    for sid, tg in TARGETS.items():
        rows = load_rows(find_file(data_dir, sid + "_epochs.csv"))
        res = analyse(rows, tg["P"], tg["T0_btjd"])
        res["flags"] = flag_counts(rows, tg["P"], tg["T0_btjd"])
        res.update({"tic": tg["tic"], "P": tg["P"], "T0_btjd": tg["T0_btjd"]})
        out["targets"][sid] = res
    return out


def clean(o):
    if isinstance(o, float):
        return None if not math.isfinite(o) else round(o, 7)
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join("data", "gaia-chroma"))
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    res = clean(run(a.data_dir))
    txt = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(txt)
    print(txt)


if __name__ == "__main__":
    main()
