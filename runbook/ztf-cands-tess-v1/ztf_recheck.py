# SPDX-License-Identifier: Apache-2.0
"""ztf_recheck 0.1.0 - recompute in code what was computed by hand in
findings/2026-11-28-ztf-shallow-flags-graded.md (gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents
working in his name; Apache-2.0).

1. For every row of ztf_faint_points.csv: the Gaia cycle and phase relative to Gaia's predicted primary
   conjunction, compared with the hand value (modulo 1). Rows whose hand phase differs by more than TOL are
   listed as mismatches. Rows without a hand phase are phased and reported.
2. For each star: a least-squares linear ephemeris through every row assigned 'primary' (both ZTF fields),
   compared with the frozen ephemeris; for TYC 2091-796-1 also the mean secondary offset.
3. For TYC 2091-796-1: the fraction of post-split main-field faint points within +-0.02 of either frozen eclipse.

Report only (exit 0); stdlib only. BTJD = HJD - 2457000 (HJD-BJD differences of seconds are ignored).
"""
import argparse
import csv
import json
import math
import os
import sys

VERSION = "0.1.0"
TOL = 6e-4
# Gaia DR3 id -> (predicted primary conjunction, BTJD; Gaia period, d)
GAIA = {
    "4535010166315168640": (389.858, 3.10003166),
    "391817260687992960": (395.215, 11.36252605),
    "4576721896566803072": (395.48673, 12.42320227),
}
# frozen post-hoc ephemerides (T0 BTJD, P d) and secondary offset (fraction of P) where seen
FROZEN = {
    "4535010166315168640": (2929.0475, 3.100431, None),
    "391817260687992960": (395.2982, 11.363060, None),
    "4576721896566803072": (395.4568, 12.421463, 0.3936),
}


def wrap(x):
    """Map a phase difference to [-0.5, 0.5)."""
    return (x + 0.5) % 1.0 - 0.5


def cycle_phase(btjd, t0, p):
    """-> (nearest cycle, phase in [-0.5, 0.5))."""
    x = (btjd - t0) / p
    n = math.floor(x + 0.5)
    return n, x - n


def linfit(es, ts):
    """Least squares t = a + b e -> (a, b, sigma_a, sigma_b, rms)."""
    n = len(es)
    me = sum(es) / n
    mt = sum(ts) / n
    sxx = sum((e - me) ** 2 for e in es)
    sxy = sum((e - me) * (t - mt) for e, t in zip(es, ts))
    b = sxy / sxx
    a = mt - b * me
    res = [t - (a + b * e) for e, t in zip(es, ts)]
    dof = max(n - 2, 1)
    s2 = sum(r * r for r in res) / dof
    sb = math.sqrt(s2 / sxx)
    sa = math.sqrt(s2 * (1.0 / n + me * me / sxx))
    return a, b, sa, sb, math.sqrt(sum(r * r for r in res) / n)


def read_rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def recheck(rows):
    out = {"version": VERSION, "n_rows": len(rows), "mismatches": [], "phased_new": [], "stars": {}}
    for r in rows:
        gid = r["gaia_dr3"]
        if gid not in GAIA:
            continue
        t = float(r["hjd"]) - 2457000.0
        n, ph = cycle_phase(t, *GAIA[gid])
        if r.get("gaia_phase", "") not in ("", None):
            d = wrap(float(r["gaia_phase"]) - ph)
            if abs(d) > TOL:
                out["mismatches"].append({"star": r["star"], "hjd": r["hjd"], "hand": float(r["gaia_phase"]),
                                          "code": round(ph, 5), "diff": round(d, 5)})
        else:
            out["phased_new"].append({"star": r["star"], "oid": r["oid"], "hjd": r["hjd"], "cycle": n,
                                      "phase": round(ph, 5)})
    for gid, (t0, p, sec) in FROZEN.items():
        prim = [float(r["hjd"]) - 2457000.0 for r in rows if r["gaia_dr3"] == gid and r["assigned"] == "primary"]
        star = {"n_primary_points": len(prim)}
        es = [math.floor((t - t0) / p + 0.5) for t in prim]
        if len(prim) >= 3 and len(set(es)) >= 2:
            a, b, sa, sb, rms = linfit(es, prim)
            star.update({"fit_T0": a, "fit_P": b, "sig_T0": sa, "sig_P": sb, "rms_d": rms,
                         "frozen_T0": t0, "frozen_P": p,
                         "dP_over_sig": (b - p) / sb if sb > 0 else None})
        if sec is not None:
            ss = [wrap((float(r["hjd"]) - 2457000.0 - t0) / p) for r in rows
                  if r["gaia_dr3"] == gid and r["assigned"] == "secondary"]
            ss = [s % 1.0 for s in ss]
            if ss:
                m = sum(ss) / len(ss)
                sd = math.sqrt(sum((s - m) ** 2 for s in ss) / max(len(ss) - 1, 1))
                star.update({"n_secondary_points": len(ss), "secondary_offset_mean": m,
                             "secondary_offset_sd": sd, "frozen_secondary_offset": sec})
            post = [float(r["hjd"]) - 2457000.0 for r in rows
                    if r["gaia_dr3"] == gid and r["stage"] == "2"]
            inw = 0
            for t in post:
                ph = ((t - t0) / p) % 1.0
                if abs(wrap(ph)) <= 0.02 or abs(wrap(ph - sec)) <= 0.02:
                    inw += 1
            star.update({"post_split_points": len(post), "post_split_in_pm0.02": inw})
        out["stars"][gid] = star
    out["n_mismatches"] = len(out["mismatches"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="ztf_faint_points.csv")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    res = recheck(read_rows(a.csv))
    with open(os.path.join(a.out_dir, "ztf_recheck.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps({"n_rows": res["n_rows"], "n_mismatches": res["n_mismatches"], "stars": res["stars"]},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
