# SPDX-License-Identifier: Apache-2.0
"""vpt_pf 0.1.0: period-free TESS search of every Gaia transit candidate (step G6).

By MV2 of Munim, Inc.; made with AI agents working in his name (not yet checked by a human
expert). Code Apache-2.0. Repository: munimtechnologies/gaia-orbit-transits.
Pre-registration: findings/2026-11-21-vpt-pf-prereg.md.

Why: in the Gaia DR3 rehearsal of step g, Gaia's published transit period matched the known
period for only 15 of 176 known systems, so folding TESS at Gaia's period misses most real
signals. This module runs vpt_followup 0.1.0's per-star analysis UNCHANGED (every TESS sector up
to --max-sectors, period-free box search 0.3-15 d per sector, fine scans around Gaia's P, 2P,
P/2 and every sector peak with S/N >= 7, odd/even, secondary, per-sector depths) on every row
of a Gaia vari_planetary_transit table, then compares the TESS period with the known planet and
TOI periods of the same TIC.

Classes (fixed in the pre-registration):
  known systems (any planet-archive or TOI period for the TIC):
    KNOWN_NOT_DETECTED (S/N < 7), KNOWN_RECOVERED (TESS period within 1% of a known period),
    KNOWN_HARMONIC (within 1% of 1/2, 2, 1/3 or 3 times a known period), KNOWN_OTHER_P;
  no known period: NEW_<vpt_followup label> (NEW_NOT_DETECTED, NEW_EB_LIKE, NEW_SURVIVES,
    NEW_SURVIVES_OTHER_P); NO_TESS; ERROR.
Grades: PF1 (all known systems with a known period in 0.3-15 d), PF1b (the subset whose Gaia
period is wrong), PF_WRONG (share of detected known systems at an unrelated period), PF2 (NEW
planet-like list; robust = the TESS period found in >= 2 sectors alone).

Top level is stdlib only; vpt_followup, gaia_vpt_tess, numpy and matplotlib load lazily.
Exit codes: 0 done, 2 catalogues unavailable (re-file unchanged), 3 self-test failed,
4 input row count differs from --expect-n.
"""
import argparse
import csv
import json
import math
import os
import random
import sys
import time

VERSION = "0.1.0"
SEED = 20261122
SNR_DETECT = 7.0
PERIOD_TOL = 0.01
PMIN, PMAX = 0.3, 15.0
HARMONICS = (0.5, 2.0, 1.0 / 3.0, 3.0)
GAIA_MATCH = (1.0, 0.5, 2.0)
PF_HI, PF_LO = 0.60, 0.30
PF_MIN_N = 20
WRONG_MAX = 0.25
ROBUST_MIN_SECTORS = 2

EXTRA_KEYS = ["pf_class", "known_periods", "tess_match", "tess_match_factor", "gaia_right",
              "has_known_in_range", "dr3_category", "seconds"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ================================================================ pure helpers (stdlib)
def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def fval(row, key, default=float("nan")):
    try:
        v = row.get(key, default)
        if v is None or (isinstance(v, str) and v.strip() in ("", "null", "NaN", "nan", "--")):
            return default
        v = float(v)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError, AttributeError):
        return default


def ival(x, default=0):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return default


def norm_tic(tic):
    s = str(tic if tic is not None else "").strip()
    if s.upper().startswith("TIC"):
        s = s[3:].strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.lstrip("0")


def known_periods(tic, planets, tois):
    """[(label, period)] for a TIC from the planet archive {tic: [(name, P)]} and the TOI
    table {tic: [row dicts with toi, disp, period]}; all TOI dispositions are kept because an
    eclipsing-binary TOI still has a real period."""
    t = norm_tic(tic)
    out = []
    if not t:
        return out
    for name, per in (planets or {}).get(t, []):
        if finite(per) and per > 0:
            out.append((str(name), float(per)))
    for row in (tois or {}).get(t, []):
        per = fval(row, "period")
        if finite(per) and per > 0:
            out.append(("TOI-%s %s" % (row.get("toi", ""), row.get("disp", "")), per))
    return out


def match_period(p, kps, factors, tol=PERIOD_TOL):
    """First (label, period, f) with |p / (f period) - 1| <= tol, i.e. p = f x period."""
    if not (finite(p) and p > 0):
        return None
    for f in factors:
        for label, per in kps:
            if finite(per) and per > 0 and abs(p / (f * per) - 1.0) <= tol:
                return label, per, f
    return None


def has_in_range(kps):
    return any(PMIN <= per <= PMAX for _, per in kps)


def pf_class(rec, kps):
    lab = str(rec.get("label") or "")
    if lab == "ERROR":
        return "ERROR"
    if lab in ("", "NO_TESS"):
        return "NO_TESS"
    snr = rec.get("snr")
    det = finite(snr) and snr >= SNR_DETECT
    if kps:
        if not det:
            return "KNOWN_NOT_DETECTED"
        p = rec.get("P_tess")
        if match_period(p, kps, (1.0,)):
            return "KNOWN_RECOVERED"
        if match_period(p, kps, HARMONICS):
            return "KNOWN_HARMONIC"
        return "KNOWN_OTHER_P"
    return "NEW_" + lab


def annotate(rec, kps, dr3_category=""):
    """Add the catalogue comparison fields to a vpt_followup result dict (in place)."""
    rec["known_periods"] = ";".join("%s@%.6f" % (n, p) for n, p in kps)
    m = match_period(rec.get("P_tess"), kps, (1.0,) + HARMONICS)
    rec["tess_match"] = m[0] if m else ""
    rec["tess_match_factor"] = m[2] if m else None
    if kps:
        rec["gaia_right"] = match_period(rec.get("P_gaia"), kps, GAIA_MATCH) is not None
    else:
        rec["gaia_right"] = None
    rec["has_known_in_range"] = has_in_range(kps)
    rec["dr3_category"] = dr3_category
    rec["pf_class"] = pf_class(rec, kps)
    return rec


def wilson(k, n, z=1.96):
    if n <= 0:
        return [float("nan"), float("nan")]
    p = k / n
    den = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def ratio_label(k, n):
    if n < PF_MIN_N:
        return "UNTESTABLE"
    x = k / n
    if x >= PF_HI:
        return "PF_RECOVERS"
    if x >= PF_LO:
        return "PF_PARTIAL"
    return "PF_FAILS"


def grade(recs):
    """Pre-registered grades from annotated records."""
    cls = {}
    for r in recs:
        c = r.get("pf_class") or "NO_TESS"
        cls[c] = cls.get(c, 0) + 1
    known = [r for r in recs if str(r.get("pf_class", "")).startswith("KNOWN_")
             and r.get("has_known_in_range") is True]
    k1 = sum(1 for r in known if r.get("pf_class") == "KNOWN_RECOVERED")
    wrong = [r for r in known if r.get("gaia_right") is False]
    k1b = sum(1 for r in wrong if r.get("pf_class") == "KNOWN_RECOVERED")
    det = [r for r in known if r.get("pf_class") in
           ("KNOWN_RECOVERED", "KNOWN_HARMONIC", "KNOWN_OTHER_P")]
    kw = sum(1 for r in det if r.get("pf_class") == "KNOWN_OTHER_P")
    wrong_rate = kw / len(det) if det else float("nan")
    pl = [r for r in recs if r.get("pf_class") in ("NEW_SURVIVES", "NEW_SURVIVES_OTHER_P")]
    pf2 = []
    for r in sorted(pl, key=lambda q: -(q.get("snr") if finite(q.get("snr")) else 0.0)):
        pf2.append({"source_id": r.get("source_id"), "tic": r.get("tic"),
                    "class": r.get("pf_class"), "P_gaia": r.get("P_gaia"),
                    "P_tess": r.get("P_tess"), "period_factor": r.get("period_factor"),
                    "snr": r.get("snr"), "depth": r.get("depth"), "r2_rj": r.get("r2_rj"),
                    "duration_h": r.get("duration_h"),
                    "n_sector_agree": ival(r.get("n_sector_agree")),
                    "n_sectors_used": ival(r.get("n_sectors_used")),
                    "robust": ival(r.get("n_sector_agree")) >= ROBUST_MIN_SECTORS,
                    "notes": r.get("notes")})
    fixed = [{"source_id": r.get("source_id"), "tic": r.get("tic"), "P_gaia": r.get("P_gaia"),
              "P_tess": r.get("P_tess"), "match": r.get("tess_match")}
             for r in wrong if r.get("pf_class") == "KNOWN_RECOVERED"]
    return {
        "classes": cls,
        "PF1": {"n": len(known), "k": k1, "rate": (k1 / len(known)) if known else None,
                "ci95": wilson(k1, len(known)), "label": ratio_label(k1, len(known))},
        "PF1b": {"n": len(wrong), "k": k1b, "rate": (k1b / len(wrong)) if wrong else None,
                 "ci95": wilson(k1b, len(wrong)), "label": ratio_label(k1b, len(wrong))},
        "PF_WRONG": {"n_detected": len(det), "k_other_p": kw,
                     "rate": wrong_rate if det else None,
                     "pf2_reliable": bool(det) and wrong_rate <= WRONG_MAX},
        "PF2": {"n_planet_like": len(pf2), "n_robust": sum(1 for q in pf2 if q["robust"]),
                "list": pf2},
        "gaia_period_fixed": fixed,
    }


def order_ids(ids, n_chunks=1, chunk=0, seed=SEED):
    ids = sorted(set(str(i).strip() for i in ids if str(i).strip()))
    random.Random(seed).shuffle(ids)
    return [x for i, x in enumerate(ids) if i % max(1, n_chunks) == chunk]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, keys):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in keys})


def _jdefault(o):
    if hasattr(o, "item"):
        try:
            return o.item()
        except Exception:
            pass
    return str(o)


def clean(o):
    if hasattr(o, "item") and not isinstance(o, (list, tuple, dict, str)):
        try:
            o = o.item()
        except Exception:
            return str(o)
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


def dump_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(clean(obj), fh, indent=1, default=_jdefault)
    os.replace(tmp, path)


def load_ckpt(d):
    out = {}
    if not d or not os.path.isdir(d):
        return out
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                e = json.load(fh)
            sid = str(e.get("rec", {}).get("source_id", "")).strip()
            if sid and e.get("rec", {}).get("label") != "ERROR":
                out[sid] = e
        except Exception as exc:
            log("bad checkpoint", f, exc)
    return out


def save_ckpt(d, sid, entry):
    if not d:
        return
    try:
        os.makedirs(d, exist_ok=True)
        dump_json(os.path.join(d, "%s.json" % sid), entry)
    except Exception as exc:
        log("checkpoint not saved", sid, exc)


# ================================================================ worker (lazy imports)
def _work(payload):
    row, max_sectors, tmp_dir = payload
    t0 = time.time()
    try:
        import vpt_followup as vf
        ns = argparse.Namespace(max_sectors=max_sectors, tmp_dir=tmp_dir)
        rec, srows, _scans, fold = vf.analyse_star(row, ns)
        rec = clean(rec)
        rec["seconds"] = round(time.time() - t0, 1)
        return {"rec": rec, "sectors": clean(srows), "fold": fold}
    except Exception as exc:
        return {"rec": {"name": row.get("name", ""), "role": row.get("role", ""),
                        "source_id": str(row.get("source_id", "")), "label": "ERROR",
                        "error": repr(exc)[:300], "seconds": round(time.time() - t0, 1)},
                "sectors": [], "fold": None}


def self_test():
    ok = True
    planets = {"123": [("X b", 2.5)]}
    tois = {"123": [{"toi": "9.01", "disp": "KP", "period": "2.5"}], "77": [
        {"toi": "8.01", "disp": "FP", "period": "1.2"}]}
    kps = known_periods("TIC 0123", planets, tois)
    ok &= len(kps) == 2
    r = annotate({"label": "SURVIVES_OTHER_P", "snr": 12.0, "P_tess": 2.51, "P_gaia": 1.7}, kps)
    ok &= r["pf_class"] == "KNOWN_RECOVERED" and r["gaia_right"] is False
    r = annotate({"label": "SURVIVES", "snr": 9.0, "P_tess": 5.0, "P_gaia": 5.0}, kps)
    ok &= r["pf_class"] == "KNOWN_HARMONIC" and r["gaia_right"] is True
    r = annotate({"label": "SURVIVES", "snr": 9.0, "P_tess": 3.3, "P_gaia": 3.3}, [])
    ok &= r["pf_class"] == "NEW_SURVIVES"
    log("pure self-test", "PASS" if ok else "FAIL")
    try:
        import vpt_followup as vf
        ok &= bool(vf.self_test())
    except Exception as exc:
        log("vpt_followup self-test error", exc)
        ok = False
    log("self-test", "PASS" if ok else "FAIL")
    return bool(ok)


def write_outputs(out_dir, results, ids, meta):
    import vpt_followup as vf
    recs = [results[s]["rec"] for s in ids if s in results]
    secs = []
    for s in ids:
        if s in results:
            secs += results[s].get("sectors") or []
    g = grade(recs)
    write_csv(os.path.join(out_dir, "pf_targets_out.csv"), recs,
              list(vf.RESULT_KEYS) + EXTRA_KEYS)
    write_csv(os.path.join(out_dir, "pf_sectors.csv"), secs, list(vf.SECTOR_KEYS))
    summ = dict(meta)
    summ.update({"version": VERSION, "n_ids": len(ids), "n_done": len(recs),
                 "unreached": [s for s in ids if s not in results], "grade": g})
    dump_json(os.path.join(out_dir, "pf_summary.json"), summ)
    return g


def run(args):
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    tmp = args.tmp_dir or "/tmp/vpf"
    os.makedirs(tmp, exist_ok=True)
    rows = read_csv(args.targets)
    if args.expect_n and len(rows) != args.expect_n:
        log("INPUT_COUNT", len(rows), "expected", args.expect_n)
        return 4
    byid = {str(r.get("source_id", "")).strip(): r for r in rows if r.get("source_id")}
    ids = order_ids(byid.keys(), args.n_chunks, args.chunk)
    if args.limit:
        ids = ids[:args.limit]
    try:
        import gaia_vpt_tess as gv
        planets, tois = gv.load_catalogues()
    except Exception as exc:
        log("CATALOGUES_UNAVAILABLE", exc)
        return 2
    done = load_ckpt(args.ckpt_dir)
    results = {s: done[s] for s in ids if s in done}
    todo = [s for s in ids if s not in results]
    log("vpt_pf", VERSION, "ids", len(ids), "from checkpoint", len(results), "to do", len(todo),
        "planets", len(planets), "toi tics", len(tois))

    def finish(entry):
        rec = entry["rec"]
        tic = rec.get("tic")
        kps = known_periods(tic, planets, tois)
        cat = ""
        if norm_tic(tic):
            try:
                cat = gv.classify_known(norm_tic(tic), fval(rec, "P_gaia"), planets, tois)[0]
            except Exception:
                cat = ""
        annotate(rec, kps, cat)
        return rec

    meta = {"targets": args.targets, "chunk": args.chunk, "n_chunks": args.n_chunks,
            "max_sectors": args.max_sectors, "seed": SEED, "snr_detect": SNR_DETECT,
            "n_planet_tics": len(planets), "n_toi_tics": len(tois)}
    plt = None
    import multiprocessing
    deadline = t_start + 60.0 * args.time_budget_min
    payloads = []
    for s in todo:
        row = dict(byid[s])
        row.update({"name": "Gaia DR3 %s" % s, "role": "candidate", "expect_period": ""})
        payloads.append((row, args.max_sectors, tmp))
    stopped = False
    if payloads:
        pool = multiprocessing.get_context("fork").Pool(max(1, args.workers),
                                                        maxtasksperchild=25)
        it = pool.imap_unordered(_work, payloads, chunksize=1)
        n = 0
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                stopped = True
                break
            try:
                res = it.next(timeout=remaining)
            except StopIteration:
                break
            except multiprocessing.TimeoutError:
                stopped = True
                break
            rec = res["rec"]
            sid = str(rec.get("source_id", "")).strip()
            entry = {"rec": rec, "sectors": res.get("sectors") or []}
            finish(entry)
            results[sid] = entry
            save_ckpt(args.ckpt_dir, sid, entry)
            n += 1
            log("[%d/%d]" % (n, len(payloads)), sid, rec.get("pf_class"), "P_gaia",
                rec.get("P_gaia"), "P_tess", rec.get("P_tess"), "snr", rec.get("snr"),
                "flags", rec.get("flags"), "%ss" % rec.get("seconds"))
            fold = res.get("fold")
            if fold is not None and str(rec.get("pf_class", "")).startswith("NEW_") and \
                    rec.get("pf_class") != "NEW_NOT_DETECTED":
                try:
                    if plt is None:
                        import matplotlib
                        matplotlib.use("Agg")
                        import matplotlib.pyplot as plt
                    import vpt_followup as vf
                    vf.plot_fold(plt, os.path.join(args.out_dir, "pf_fold_%s.png" % sid),
                                 "Gaia DR3 %s TIC %s: %s" % (sid, rec.get("tic"),
                                                             rec.get("pf_class")), fold)
                except Exception as exc:
                    log("plot failed", sid, exc)
            if n % 5 == 0:
                write_outputs(args.out_dir, results, ids, meta)
        if stopped:
            log("TIME_BUDGET reached; stopping workers")
            pool.terminate()
        else:
            pool.close()
        pool.join()
    for s in results:
        finish(results[s])
    meta["stopped_by_budget"] = stopped
    meta["minutes"] = round((time.time() - t_start) / 60.0, 1)
    g = write_outputs(args.out_dir, results, ids, meta)
    print(json.dumps(clean({k: g[k] for k in ("classes", "PF1", "PF1b", "PF_WRONG")}),
                     default=_jdefault))
    print(json.dumps(clean({"PF2_n": g["PF2"]["n_planet_like"],
                            "PF2_robust": g["PF2"]["n_robust"]})))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--targets", default="vpt_candidates.csv")
    p.add_argument("--expect-n", type=int, default=0)
    p.add_argument("--out-dir", default="out")
    p.add_argument("--tmp-dir", default=None)
    p.add_argument("--ckpt-dir", default=None)
    p.add_argument("--max-sectors", type=int, default=6)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--chunk", type=int, default=0)
    p.add_argument("--n-chunks", type=int, default=1)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--time-budget-min", type=float, default=200.0)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return 0 if self_test() else 3
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
