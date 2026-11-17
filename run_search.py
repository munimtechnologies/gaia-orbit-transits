# SPDX-License-Identifier: Apache-2.0
"""Search TESS for eclipses/transits of companions on Gaia astrometric orbits.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0.

Steps
 1. Download the Gaia nss_two_body_orbit solutions that have Thiele-Innes
    constants, are brighter than --gmax and are near edge-on (|cos i| below
    --cosi-server, computed by the archive itself), with their correlation
    vectors (cached in --data-dir). DR3 now; DR4 (--schema gaiadr4) on release day.
 2. For each orbit run a Monte Carlo over the catalogue errors and correlations:
    probability that the companion can eclipse/transit, predicted conjunction
    times (and the next ones after --predict-from), rough masses (dark companion).
    For AstroSpectroSB1 solutions the spectroscopic C/H constants say which
    conjunction is the transit (0.3.0, see gaia_orbits.transit_label).
 3. Rank and, for the top targets, find the TIC ID, download TESS light curves
    (SPOC 2-min, TESS-SPOC, QLP), run a single-event dip search, and score each
    dip against the predicted conjunction windows.
 4. Write CSVs, plots of the best events (and, with --window-plots, of every
    predicted window that TESS covered) and a report.

0.4.0: the Gaia TAP result download is retried (a dropped connection killed the
first full DR3 run), and the astroquery fallback writes array columns such as
corr_vec as '(a, b, ...)' strings instead of crashing (table_to_csv).

0.4.1: since October 2026 the Gaia ESA Archive gives anonymous users 1 minute per
query (sync and async) and at most 50,000 rows; the second full DR3 run was aborted
by that limit. Large queries are now split into source_id ranges (--tap-chunks); a
range that times out or comes back with the row cap is split again, four ways,
up to four levels deep. Each range is tried on the ESA archive, then on the ARI
Heidelberg Gaia TAP mirror (DR3 tables, same schema), then through astroquery.
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
import traceback

import numpy as np

import dipsearch as ds
import gaia_orbits as go

VERSION = "0.4.1"
TAP = "https://gea.esac.esa.int/tap-server/tap"
TAP_MIRRORS = [TAP, "https://gaia.ari.uni-heidelberg.de/tap"]
# Gaia source_id = HEALPix level-12 index * 2^35 + ..., so every id is below this
SOURCE_ID_MAX = 12 * 4 ** 12 * 2 ** 35
ANON_ROW_CAP = 50000
CHUNK_RE = re.compile(r"/\*CHUNK:([A-Za-z_][\w.]*)\*/")

NSS_QUERY = """
SELECT n.source_id, n.nss_solution_type, n.bit_index, n.corr_vec, n.period, n.period_error,
 n.t_periastron, n.t_periastron_error, n.eccentricity, n.eccentricity_error,
 n.a_thiele_innes, n.a_thiele_innes_error, n.b_thiele_innes, n.b_thiele_innes_error,
 n.f_thiele_innes, n.f_thiele_innes_error, n.g_thiele_innes, n.g_thiele_innes_error,
 n.c_thiele_innes, n.c_thiele_innes_error, n.h_thiele_innes, n.h_thiele_innes_error,
 n.parallax AS nss_parallax, n.parallax_error AS nss_parallax_error,
 n.significance, n.goodness_of_fit,
 g.ra, g.dec, g.phot_g_mean_mag, g.bp_rp, g.ruwe, g.ref_epoch
FROM {schema}.nss_two_body_orbit AS n
JOIN {schema}.gaia_source AS g ON g.source_id = n.source_id
WHERE n.a_thiele_innes IS NOT NULL AND g.phot_g_mean_mag < {gmax}
 AND ABS({cosi}) < {cosi_server}{extra}/*CHUNK:n.source_id*/
"""

EB_QUERY = """
SELECT v.source_id FROM {schema}.vari_eclipsing_binary AS v
JOIN {schema}.nss_two_body_orbit AS n ON n.source_id = v.source_id
WHERE n.a_thiele_innes IS NOT NULL AND ABS({cosi}) < {cosi_server}/*CHUNK:v.source_id*/
"""


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def ref_epoch_to_btjd(ref_epoch_jyr):
    """Julian-year epoch (e.g. 2016.0) -> BTJD (BJD - 2457000)."""
    return (float(ref_epoch_jyr) - 2000.0) * 365.25 + 2451545.0 - 2457000.0


# ---------------------------------------------------------------- Gaia TAP
def tap_async(query, timeout_s=3600, download_tries=4, base=TAP):
    import requests
    data = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "PHASE": "RUN",
            "QUERY": query}
    if base != TAP:
        data["MAXREC"] = 3000000   # mirrors may default to a small row limit
    r = requests.post(base + "/async", data=data, allow_redirects=False, timeout=120)
    loc = r.headers.get("Location")
    if loc and loc.startswith("/"):
        loc = base.split("/", 3)[0] + "//" + base.split("/", 3)[2] + loc
    if not loc:
        raise RuntimeError(f"TAP async: no job location (HTTP {r.status_code}): {r.text[:500]}")
    t0 = time.time()
    while True:
        ph = requests.get(loc + "/phase", timeout=60).text.strip()
        if ph == "PENDING":
            requests.post(loc + "/phase", data={"PHASE": "RUN"}, timeout=60)
        elif ph == "COMPLETED":
            break
        elif ph in ("ERROR", "ABORTED"):
            err = requests.get(loc + "/error", timeout=60).text
            raise RuntimeError(f"TAP job {ph}: {err[:1000]}")
        if time.time() - t0 > timeout_s:
            raise RuntimeError("TAP job timed out")
        time.sleep(3)
    # 0.4.0: the finished job's result stays on the server, so a dropped
    # connection (IncompleteRead) is retried instead of failing the whole run
    last = None
    for attempt in range(download_tries):
        try:
            res = requests.get(loc + "/results/result", timeout=900)
            res.raise_for_status()
            return res.text
        except Exception as exc:
            last = exc
            log("TAP result download failed, attempt", attempt + 1, exc)
            time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"TAP result download failed {download_tries} times: {last}")


def _num(x):
    x = float(x)
    return "NaN" if not np.isfinite(x) else repr(x)


def _cell(v):
    """One table cell as CSV text: masked/None -> '', arrays -> '(a, b, ...)'."""
    if v is None or v is np.ma.masked:
        return ""
    if isinstance(v, bytes):
        v = v.decode("utf-8", "replace")
    if isinstance(v, (np.ndarray, list, tuple)) and np.ndim(v) > 0:
        try:
            arr = np.ma.filled(np.ma.asarray(v, dtype=float), np.nan).ravel()
        except (TypeError, ValueError):
            return str(list(np.asarray(v).ravel()))
        return "(" + ", ".join(_num(x) for x in arr) + ")"
    if isinstance(v, (bool, np.bool_)):
        return str(bool(v))
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return "" if not np.isfinite(v) else repr(float(v))
    return str(v)


def table_to_csv(tbl):
    """CSV text from an astropy Table (or any object with .colnames and row access)
    that tolerates masked values and array-valued columns such as corr_vec."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    names = list(tbl.colnames)
    w.writerow(names)
    for row in tbl:
        w.writerow([_cell(row[c]) for c in names])
    return buf.getvalue()


def tap_query(query):
    """One ADQL query: ESA archive, then the ARI mirror (DR3 only), then astroquery."""
    errors = []
    for base in TAP_MIRRORS:
        if base != TAP and "gaiadr3." not in query:
            continue  # the mirror serves DR3; DR4 only from ESA until it is mirrored
        try:
            return tap_async(query, base=base)
        except Exception as exc:
            errors.append(f"{base}: {str(exc)[:300]}")
            log("TAP failed at", base, str(exc)[:300])
    try:
        from astroquery.gaia import Gaia
        Gaia.ROW_LIMIT = -1
        tbl = Gaia.launch_job_async(query).get_results()
        return table_to_csv(tbl)
    except Exception as exc:
        errors.append(f"astroquery: {str(exc)[:300]}")
    raise RuntimeError("all TAP routes failed: " + " | ".join(errors))


def chunk_bounds(n, lo=0, hi=SOURCE_ID_MAX):
    """n contiguous inclusive source_id ranges covering [lo, hi)."""
    n = max(1, int(n))
    edges = [lo + (hi - lo) * k // n for k in range(n + 1)]
    return [(edges[k], edges[k + 1] - 1) for k in range(n) if edges[k + 1] > edges[k]]


def _csv_split(text):
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return (lines[0] if lines else None), lines[1:]


SPLIT_HINTS = ("execution time", "row cap", "aborted", "timed out", "timeout", "quota")


def _splittable(exc):
    """Errors that a smaller source_id range can cure (time or row limits)."""
    msg = str(exc).lower()
    return any(h in msg for h in SPLIT_HINTS)


def chunked_query(query, n_chunks=1, query_fn=None, row_cap=ANON_ROW_CAP, max_depth=4,
                  lo=0, hi=SOURCE_ID_MAX, _depth=0):
    """Run a query that carries a /*CHUNK:<id column>*/ marker over source_id ranges.

    A range that fails (e.g. the 60-s anonymous limit) or returns row_cap rows (the
    archive truncates silently) is split four ways and retried, max_depth levels deep.
    Returns one CSV text with a single header line.
    """
    query_fn = query_fn or tap_query
    m = CHUNK_RE.search(query)
    if m is None:
        return query_fn(query)
    col = m.group(1)
    header, rows = None, []
    for a, b in chunk_bounds(n_chunks, lo, hi):
        clause = "" if (a == 0 and b >= SOURCE_ID_MAX - 1) else f"\n AND {col} BETWEEN {a} AND {b}"
        q = CHUNK_RE.sub(clause, query)
        try:
            h, rr = _csv_split(query_fn(q))
            if len(rr) >= row_cap:
                raise RuntimeError(f"row cap {row_cap} reached")
        except Exception as exc:
            if _depth >= max_depth or b - a < 4 or not _splittable(exc):
                raise
            log(f"range {a}-{b}: {str(exc)[:160]} - splitting")
            h, rr = _csv_split(chunked_query(query, 4, query_fn, row_cap, max_depth,
                                             a, b + 1, _depth + 1))
        if header is None and h:
            header = h
        rows += rr
    return "\n".join([header or ""] + rows) + "\n"


STRING_COLS = ("nss_solution_type", "corr_vec")


def read_csv_text(text):
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        d = {}
        for k, v in r.items():
            if k is None:
                continue
            k = k.strip().lower()
            v = "" if v is None else v
            if k in ("source_id",):
                d[k] = int(float(v)) if "e" in v.lower() else int(v)
            elif k in STRING_COLS:
                d[k] = v.strip().strip('"')
            else:
                try:
                    d[k] = float(v) if v not in ("", "null", "--") else np.nan
                except ValueError:
                    d[k] = v
        out.append(d)
    return out


def cached_query(path, query, chunks=1, query_fn=None):
    if os.path.exists(path) and os.path.getsize(path) > 100:
        log("cache hit", path)
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    log("querying Gaia archive ...", f"({chunks} source_id ranges)")
    text = chunked_query(query, chunks, query_fn)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)
    return text


# ---------------------------------------------------------------- ranking
def prior_for_row(row, n, rng, predict_from=None):
    plx = row.get("nss_parallax", np.nan)
    if not np.isfinite(plx) or plx <= 0:
        return None
    absg = row["phot_g_mean_mag"] + 5 * np.log10(plx / 100.0)
    m1, r1 = go.ms_mass_radius(absg)
    s = go.sample_orbit(row, n, rng)
    G = row["g_thiele_innes"]
    if go.is_circular_fixed(row) and abs(row["b_thiele_innes"]) > 0:
        G = -row["a_thiele_innes"] * row["f_thiele_innes"] / row["b_thiele_innes"]
    el = go.thiele_innes_to_elements(row["a_thiele_innes"], row["b_thiele_innes"],
                                     row["f_thiele_innes"], G)
    m2 = float(go.companion_mass_dark(float(el["a"]), plx, row["period"], m1))
    r2 = float(go.companion_radius(m2))
    g = go.eclipse_geometry(s, float(m1), float(r1), m2, r2)
    p_ecl = float(np.mean(g["ecl1"] | g["ecl2"]))
    t1c, t2c = go.central_conjunctions(row)
    out = {
        "abs_g": float(absg), "m1": float(m1), "r1": float(r1), "m2_dark": m2,
        "r2": r2, "class": go.classify(m2), "cosi": float(el["cosi"]),
        "inc_deg": float(el["inc_deg"]),
        "cosi_sd": float(np.std(s["cosi"])), "a0_mas": float(el["a"]),
        "p_ecl": p_ecl,
        "p_ecl1": float(np.mean(g["ecl1"])), "p_ecl2": float(np.mean(g["ecl2"])),
        "dur1_h": float(np.median(g["dur_central1"]) * 24),
        "dur2_h": float(np.median(g["dur_central2"]) * 24),
        "t_conj1_btjd": t1c, "t_conj2_btjd": t2c,
        "used_corr": bool(s["used_corr"]), "circular": bool(s["circular"]),
    }
    # 0.3.0: which conjunction is the transit (AstroSpectroSB1 only)
    out.update(go.transit_label(row))
    if predict_from is not None:
        for key, tc in (("t1", t1c), ("t2", t2c)):
            tn, sig = go.predict_next(s, key, tc, float(row["period"]), predict_from)
            out[f"next{key[1]}_btjd"] = tn
            out[f"next{key[1]}_sd_d"] = sig
        if out["transit_conj"]:
            k = out["transit_conj"][1]
            out["next_transit_btjd"] = out[f"next{k}_btjd"]
            out["next_transit_sd_d"] = out[f"next{k}_sd_d"]
    return out, s, g


# ---------------------------------------------------------------- TESS
def find_tic(ra, dec, gmag, source_id):
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astroquery.mast import Catalogs
    for attempt in range(3):
        try:
            t = Catalogs.query_region(SkyCoord(ra, dec, unit="deg"), radius=12 * u.arcsec,
                                      catalog="TIC")
            break
        except Exception as exc:
            log("TIC query retry", attempt, exc)
            time.sleep(5 * (attempt + 1))
    else:
        return None
    if len(t) == 0:
        return None
    best, best_score, gaia_match = None, 1e9, False
    for r in t:
        gid = str(r["GAIA"]).strip() if "GAIA" in t.colnames else ""
        if gid and gid == str(source_id):
            return {"tic": int(r["ID"]), "tmag": float(r["Tmag"]), "ra": float(r["ra"]),
                    "dec": float(r["dec"]), "gaia_match": True,
                    "dist_arcsec": float(r["dstArcSec"])}
        try:
            tm = float(r["Tmag"])
            tm = tm if np.isfinite(tm) else 99.0
        except Exception:
            tm = 99.0
        score = float(r["dstArcSec"]) + 3 * abs(tm - (gmag - 0.5))
        if score < best_score:
            best, best_score = r, score
    if best is None:
        return None
    return {"tic": int(best["ID"]), "tmag": float(best["Tmag"]), "ra": float(best["ra"]),
            "dec": float(best["dec"]), "gaia_match": gaia_match,
            "dist_arcsec": float(best["dstArcSec"])}


AUTHOR_RANK = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}


def _arr(x):
    """Plain float ndarray with NaN where masked (numpy or astropy masked arrays)."""
    x = getattr(x, "value", x)
    if hasattr(x, "unmasked"):
        d = np.array(x.unmasked, dtype=float)
        d[np.asarray(x.mask, dtype=bool)] = np.nan
        return d
    if np.ma.isMaskedArray(x):
        return np.ma.filled(x.astype(float), np.nan)
    return np.asarray(x, dtype=float)


def fetch_tess(tic, ra, dec, data_dir, max_lcs):
    import astropy.units as u
    import lightkurve as lk
    from astropy.coordinates import SkyCoord
    sr = None
    for attempt in range(3):
        try:
            sr = lk.search_lightcurve(SkyCoord(ra, dec, unit="deg"), radius=3 * u.arcsec,
                                      mission="TESS")
            break
        except Exception as exc:
            log("search retry", attempt, exc)
            time.sleep(5 * (attempt + 1))
    if sr is None or len(sr) == 0:
        return [], []
    tab = sr.table
    pick = {}
    for i in range(len(sr)):
        author = str(tab["author"][i])
        if author not in AUTHOR_RANK:
            continue
        if "target_name" in tab.colnames:
            tn = str(tab["target_name"][i]).strip().lstrip("0")
            if tn and tn.isdigit() and tn != str(tic):
                continue
        exptime = float(tab["exptime"][i]) if "exptime" in tab.colnames else 0
        if author == "SPOC" and exptime < 100:
            continue  # skip 20-s data, use the 120-s version
        sector = None
        for key in ("sequence_number", "sector"):
            if key in tab.colnames:
                try:
                    sector = int(tab[key][i])
                    break
                except Exception:
                    pass
        if sector is None:
            digits = "".join(ch for ch in str(tab["mission"][i]) if ch.isdigit())
            sector = int(digits) if digits else -i
        rank = AUTHOR_RANK[author]
        if sector not in pick or rank < pick[sector][0]:
            pick[sector] = (rank, i, author)
    sectors = sorted(pick)[:max_lcs]
    times, fluxes, meta = [], [], []
    for sec in sectors:
        rank, i, author = pick[sec]
        try:
            lc = sr[i].download(download_dir=data_dir, quality_bitmask="default")
            if lc is None:
                continue
            t = _arr(lc.time.value)
            f = _arr(lc.flux)
            ok = np.isfinite(t) & np.isfinite(f)
            if ok.sum() < 100:
                continue
            t, f = t[ok], f[ok]
            f = f / np.nanmedian(f)
            # clip strong upward outliers only (flares, cosmic rays)
            sd = ds.robust_sd(f)
            keep = f < 1 + 6 * sd
            times.append(t[keep])
            fluxes.append(f[keep])
            meta.append({"sector": int(sec), "author": author, "n": int(keep.sum())})
        except Exception as exc:
            log("download failed", tic, sec, author, exc)
    return list(zip(times, fluxes)), meta


# ---------------------------------------------------------------- plotting
def plot_event(path, title, binned, raw, ev, windows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(10, 7))
    bt, bf = binned["t"], binned["f"]
    tc = ev["t_center"]
    sel = (bt > ev["seg_start"] - 1) & (bt < ev["seg_end"] + 1)
    ax[0].plot(bt[sel], bf[sel], ".", ms=2, color="k")
    for (lo, hi, lab) in windows:
        if hi > bt[sel].min() - 5 and lo < bt[sel].max() + 5:
            ax[0].axvspan(lo, hi, color="orange" if lab == "c1" else "cyan", alpha=0.3)
    ax[0].axvline(tc, color="r", lw=0.8)
    ax[0].set_title(title, fontsize=9)
    ax[0].set_ylabel("binned flux (30 min)")
    half = max(3 * ev["duration_h"] / 24, 1.0)
    rt, rf = raw
    m = np.abs(rt - tc) < half
    ax[1].plot(rt[m], rf[m], ".", ms=1, color="0.6")
    mb = np.abs(bt - tc) < half
    ax[1].plot(bt[mb], bf[mb], "o", ms=3, color="k")
    ax[1].axvspan(tc - ev["duration_h"] / 48, tc + ev["duration_h"] / 48, color="r", alpha=0.15)
    ax[1].set_xlabel("BTJD")
    ax[1].set_ylabel("flux")
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


def covered_windows(bt, s, p, nsig=3.0, min_points=10):
    """Predicted conjunction windows that fall in the binned TESS times bt.

    Returns a list of dicts: conj ('t1'/'t2'), centre (BTJD, MC median), sd (d),
    n_in_1sd (binned points within 1 sigma), n_in_3sd, is_rv_transit.
    """
    out = []
    if bt.size == 0:
        return out
    P = float(p["period_d"])
    for key, tc in (("t1", p["t_conj1_btjd"]), ("t2", p["t_conj2_btjd"])):
        k0 = int(np.floor((bt.min() - tc) / P)) - 1
        k1 = int(np.ceil((bt.max() - tc) / P)) + 1
        for k in range(k0, k1 + 1):
            tn = tc + k * P
            off = go.phase_offsets(s, key, tn)
            med = float(np.median(off))
            c = tn - med
            sd = max(float(1.4826 * np.median(np.abs(off - med))), 0.05)
            if sd > P / 4:
                continue  # phase unconstrained there
            n3 = int(np.sum(np.abs(bt - c) < nsig * sd))
            if n3 < min_points:
                continue
            out.append({"conj": key, "centre": c, "sd": sd,
                        "n_in_1sd": int(np.sum(np.abs(bt - c) < sd)), "n_in_3sd": n3,
                        "is_rv_transit": key == p.get("transit_conj", "")})
    return out


def plot_windows(path, title, binned, wins, max_panels=8):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    wins = sorted(wins, key=lambda w: (not w["is_rv_transit"], -w["n_in_1sd"]))[:max_panels]
    if not wins:
        return False
    bt, bf = binned["t"], binned["f"]
    fig, axes = plt.subplots(len(wins), 1, figsize=(9, 2.3 * len(wins)), squeeze=False)
    for ax, w in zip(axes[:, 0], wins):
        m = np.abs(bt - w["centre"]) < 3 * w["sd"] + 1.0
        ax.plot(bt[m] - w["centre"], bf[m], ".", ms=2, color="k")
        ax.axvspan(-w["sd"], w["sd"], color="orange" if w["is_rv_transit"] else "cyan",
                   alpha=0.25)
        ax.axvspan(-3 * w["sd"], 3 * w["sd"], color="0.9", alpha=0.4, zorder=0)
        lab = " (RV-identified transit)" if w["is_rv_transit"] else ""
        ax.set_title(f"{w['conj']}{lab}: centre BTJD {w['centre']:.2f} +- {w['sd']:.2f} d",
                     fontsize=8)
        ax.set_ylabel("flux", fontsize=8)
    axes[-1, 0].set_xlabel("days from predicted conjunction")
    fig.suptitle(title, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)
    return True


# ---------------------------------------------------------------- main
def write_csv(path, rows, fields=None):
    if not rows:
        return
    fields = fields or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def build_nss_query(schema, gmax, cosi_server, targets_table=None, source_ids=None):
    extra = ""
    if targets_table:
        extra = f"\n AND n.source_id IN (SELECT source_id FROM {targets_table})"
    if source_ids:
        ids = ",".join(str(int(x)) for x in source_ids)
        extra += f"\n AND n.source_id IN ({ids})"
    return NSS_QUERY.format(schema=schema, gmax=gmax, cosi=go.cosi_adql("n."),
                            cosi_server=cosi_server, extra=extra)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--gmax", type=float, default=14.5)
    ap.add_argument("--cosi-max", type=float, default=0.2)
    ap.add_argument("--cosi-server", type=float, default=None,
                    help="server-side |cos i| cut (default: --cosi-max)")
    ap.add_argument("--mc", type=int, default=600)
    ap.add_argument("--max-targets", type=int, default=400)
    ap.add_argument("--min-p-ecl", type=float, default=0.002)
    ap.add_argument("--max-lcs", type=int, default=40)
    ap.add_argument("--snr", type=float, default=7.0)
    ap.add_argument("--time-budget-min", type=float, default=200)
    ap.add_argument("--plots", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20261117)
    ap.add_argument("--schema", default="gaiadr3",
                    help="Gaia archive schema (gaiadr3; gaiadr4 after 2026-12-02)")
    ap.add_argument("--ref-btjd", type=float, default=None,
                    help="force the BTJD of the t_periastron reference epoch (default: "
                         "from gaia_source.ref_epoch per row; 389.0 = J2016.0 for DR3)")
    ap.add_argument("--predict-from", type=float, default=4375.5,
                    help="BTJD after which to predict the next conjunctions "
                         "(default 4375.5 = 2026-12-01)")
    ap.add_argument("--targets-table", default=None,
                    help="only orbits whose source_id is in this archive table, e.g. "
                         "gaiadr4.gaia_exoplanet_candidates (DR4 release day)")
    ap.add_argument("--source-ids", default=None,
                    help="comma-separated Gaia source_ids (e.g. a watch list)")
    ap.add_argument("--tap-chunks", type=int, default=16,
                    help="split the Gaia query into this many source_id ranges (0.4.1)")
    ap.add_argument("--window-plots", action="store_true",
                    help="plot every predicted conjunction window covered by TESS")
    ap.add_argument("--no-tess", action="store_true",
                    help="stop after the Gaia ranking (watch list only)")
    args = ap.parse_args(argv)
    if args.cosi_server is None:
        args.cosi_server = args.cosi_max
    if args.ref_btjd is not None:
        go.GAIA_REF_BTJD = args.ref_btjd
    else:
        go.GAIA_REF_BTJD = 936.875 if args.schema.lower().endswith("dr4") else 389.0
    source_ids = None
    if args.source_ids:
        source_ids = sorted({int(x) for x in args.source_ids.replace(" ", "").split(",") if x})
    t_start = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(os.path.join(args.out_dir, "plots"), exist_ok=True)
    if args.window_plots:
        os.makedirs(os.path.join(args.out_dir, "windows"), exist_ok=True)
    lk_dir = os.path.join(args.data_dir, "lk")
    os.makedirs(lk_dir, exist_ok=True)
    summary = {"version": VERSION,
               "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "args": vars(args)}

    tag = f"{args.schema}_nss_ti_g{args.gmax:g}_c{args.cosi_server:g}"
    if args.targets_table:
        tag += "_" + args.targets_table.replace(".", "-")
    if source_ids:
        tag += f"_ids{len(source_ids)}-{sum(source_ids) % 1000003}"
    query = build_nss_query(args.schema, args.gmax, args.cosi_server, args.targets_table,
                            source_ids)
    with open(os.path.join(args.out_dir, "nss_query.adql"), "w", encoding="utf-8") as fh:
        fh.write(CHUNK_RE.sub("", query))
    chunks = 1 if source_ids else args.tap_chunks
    # _v3: the query gained the spectroscopic C/H columns in 0.3.0
    text = cached_query(os.path.join(args.data_dir, tag + "_v3.csv"), query, chunks)
    rows = read_csv_text(text)
    log("NSS rows (server-side near edge-on):", len(rows))
    try:
        ebtext = cached_query(os.path.join(args.data_dir, f"{args.schema}_nss_ti_vari_eb_c{args.cosi_server:g}.csv"),
                              EB_QUERY.format(schema=args.schema, cosi=go.cosi_adql("n."),
                                              cosi_server=args.cosi_server), args.tap_chunks)
        gaia_eb = {r["source_id"] for r in read_csv_text(ebtext)}
    except Exception as exc:
        log("EB query failed", exc)
        gaia_eb = set()
    summary["nss_rows"] = len(rows)
    summary["gaia_eb_overlap"] = len(gaia_eb)
    types = {}
    for r in rows:
        types[r["nss_solution_type"]] = types.get(r["nss_solution_type"], 0) + 1
    summary["solution_types"] = types

    priors, samples, by_id = [], {}, {}
    n_edge = 0
    n_corr = 0
    n_circ = 0
    n_rv = 0
    n_rv_consistent = 0

    def src_rng(sid):
        return np.random.default_rng([args.seed, int(sid) % (2 ** 32), int(sid) // (2 ** 32)])

    for r in rows:
        if args.ref_btjd is not None:
            r["ref_btjd"] = args.ref_btjd
        else:
            ep = r.get("ref_epoch", np.nan)
            r["ref_btjd"] = ref_epoch_to_btjd(ep) if np.isfinite(ep) else go.GAIA_REF_BTJD
        G = r["g_thiele_innes"]
        if go.is_circular_fixed(r) and abs(r["b_thiele_innes"]) > 0:
            G = -r["a_thiele_innes"] * r["f_thiele_innes"] / r["b_thiele_innes"]
        el = go.thiele_innes_to_elements(r["a_thiele_innes"], r["b_thiele_innes"],
                                         r["f_thiele_innes"], G)
        if not np.isfinite(float(el["cosi"])) or abs(float(el["cosi"])) >= args.cosi_max:
            continue
        if not np.isfinite(r.get("period", np.nan)) or not np.isfinite(r.get("t_periastron", np.nan)):
            continue
        n_edge += 1
        key = (r["source_id"], r["nss_solution_type"])
        try:
            res = prior_for_row(r, args.mc, src_rng(r["source_id"]), args.predict_from)
        except Exception as exc:
            log("prior failed", r.get("source_id"), exc)
            continue
        if res is None:
            continue
        pr = res[0]
        n_corr += int(pr["used_corr"])
        n_circ += int(pr["circular"])
        n_rv += int(bool(pr["transit_conj"]))
        n_rv_consistent += int(bool(pr["rv_consistent"]))
        by_id[key] = r
        rec = {"source_id": r["source_id"], "solution_type": r["nss_solution_type"],
               "ra": r["ra"], "dec": r["dec"], "gmag": r["phot_g_mean_mag"],
               "bp_rp": r.get("bp_rp"), "ruwe": r.get("ruwe"), "parallax": r["nss_parallax"],
               "period_d": r["period"], "period_err": r.get("period_error"),
               "ecc": r.get("eccentricity"), "significance": r.get("significance"),
               "ref_btjd": r["ref_btjd"], "gaia_eb": r["source_id"] in gaia_eb}
        rec.update(pr)
        priors.append(rec)
    summary["near_edge_on"] = n_edge
    summary["mc_used_correlations"] = n_corr
    summary["circular_solutions"] = n_circ
    summary["rv_transit_labelled"] = n_rv
    summary["rv_transit_consistent"] = n_rv_consistent
    rows = None
    text = None
    log("near edge-on:", n_edge, "with priors:", len(priors), "corr used:", n_corr,
        "RV-labelled:", n_rv)
    priors.sort(key=lambda p: -p["p_ecl"])
    write_csv(os.path.join(args.out_dir, "gaia_edge_on_priors.csv"), priors,
              sorted({k for p in priors for k in p}))

    # choose targets: substellar candidates first, then by eclipse probability;
    # one target per source (best solution)
    seen = set()
    sub, star = [], []
    for p in priors:
        if p["source_id"] in seen or p["p_ecl"] < args.min_p_ecl:
            continue
        seen.add(p["source_id"])
        (sub if p["class"] in ("planet", "brown-dwarf") else star).append(p)
    targets = (sub + star)[:args.max_targets]
    summary["n_substellar_candidates"] = len(sub)
    summary["n_targets"] = len(targets)
    log("targets:", len(targets), "substellar:", len(sub))
    write_csv(os.path.join(args.out_dir, "substellar_edge_on_candidates.csv"),
              [p for p in priors if p["class"] in ("planet", "brown-dwarf")],
              sorted({k for p in priors for k in p}))
    if args.no_tess:
        with open(os.path.join(args.out_dir, "run_summary.json"), "w") as fh:
            json.dump(summary, fh, indent=1, default=str)
        log("--no-tess: done")
        return 0

    # same seeds as the ranking pass -> identical Monte Carlo samples
    for p in targets:
        key = (p["source_id"], p["solution_type"])
        samples[p["source_id"]] = prior_for_row(by_id[key], args.mc, src_rng(p["source_id"]))[1]
    by_id.clear()

    per_target, all_events, all_windows = [], [], []
    store = {}
    expected = 0.0
    expected_both = 0.0
    for ti, p in enumerate(targets):
        if (time.time() - t_start) / 60 > args.time_budget_min:
            log("time budget reached at target", ti)
            summary["stopped_at_target"] = ti
            break
        sid = p["source_id"]
        rec = {"source_id": sid, "solution_type": p["solution_type"], "class": p["class"],
               "p_ecl": p["p_ecl"], "period_d": p["period_d"], "gmag": p["gmag"],
               "m2_dark": p["m2_dark"], "gaia_eb": p["gaia_eb"], "tic": "", "n_sectors": 0,
               "cov1": 0.0, "cov2": 0.0, "best_snr": 0.0, "best_t": "", "best_bf": "",
               "transit_conj": p.get("transit_conj", ""), "status": ""}
        try:
            tic = find_tic(p["ra"], p["dec"], p["gmag"], sid)
            if tic is None:
                rec["status"] = "no-tic"
                per_target.append(rec)
                continue
            rec["tic"] = tic["tic"]
            rec["tic_gaia_match"] = tic["gaia_match"]
            lcs, meta = fetch_tess(tic["tic"], tic["ra"], tic["dec"], lk_dir, args.max_lcs)
            rec["n_sectors"] = len(meta)
            rec["sectors"] = " ".join(f"{m['sector']}:{m['author']}" for m in meta)
            if not lcs:
                rec["status"] = "no-tess"
                per_target.append(rec)
                continue
            t = np.concatenate([x[0] for x in lcs])
            f = np.concatenate([x[1] for x in lcs])
            o = np.argsort(t)
            t, f = t[o], f[o]
            events, binned = ds.search(t, f, snr_min=args.snr)
            s = samples[sid]
            hw1 = max(p["dur1_h"] / 48.0, 1 / 48)
            hw2 = max(p["dur2_h"] / 48.0, 1 / 48)
            rec["cov1"] = go.coverage_fraction(s, "t1", binned["t"], hw1)
            rec["cov2"] = go.coverage_fraction(s, "t2", binned["t"], hw2)
            if rec["transit_conj"]:
                rec["cov_transit"] = rec["cov1"] if rec["transit_conj"] == "t1" else rec["cov2"]
            # pre-registered definition (v1): p_ecl x best coverage
            expected += p["p_ecl"] * max(rec["cov1"], rec["cov2"])
            expected_both += p["p_ecl1"] * rec["cov1"] + p["p_ecl2"] * rec["cov2"]
            wins = covered_windows(np.asarray(binned["t"]), s, p)
            rec["n_windows_covered"] = len(wins)
            for w in wins:
                all_windows.append(dict(w, source_id=sid, tic=tic["tic"], period_d=p["period_d"],
                                        class_=p["class"]))
            if args.window_plots and wins:
                try:
                    plot_windows(os.path.join(args.out_dir, "windows", f"{sid}.png"),
                                 f"Gaia {args.schema} {sid}  TIC {tic['tic']}  P={p['period_d']:.2f} d  "
                                 f"m2(dark)={p['m2_dark']:.3f} Msun  cos i={p['cosi']:.3f}",
                                 binned, wins)
                except Exception as exc:
                    log("window plot failed", sid, exc)
            for e in events:
                best = None
                for key, dkey in (("t1", "dur1_h"), ("t2", "dur2_h")):
                    wm = go.window_match(s, key, e["t_center"],
                                         max(e["duration_h"], p[dkey]) / 24.0)
                    if best is None or wm["bf"] > best["bf"]:
                        best = dict(wm, conj=key)
                e.update({"source_id": sid, "tic": tic["tic"], "class": p["class"],
                          "period_d": p["period_d"], "p_ecl": p["p_ecl"],
                          "gmag": p["gmag"], "m2_dark": p["m2_dark"], "gaia_eb": p["gaia_eb"],
                          "conj": best["conj"], "bf": best["bf"],
                          "frac_in_window": best["frac_in_window"],
                          "offset_d": best["median_offset_d"],
                          "offset_sd_d": best["offset_sd_d"],
                          "pred_dur_h": p["dur1_h"] if best["conj"] == "t1" else p["dur2_h"],
                          "at_rv_transit_conj": (best["conj"] == rec["transit_conj"])
                          if rec["transit_conj"] else ""})
                all_events.append(e)
            if events:
                top = max(events, key=lambda e: e["snr"])
                rec["best_snr"], rec["best_t"] = top["snr"], top["t_center"]
                rec["best_bf"] = max(e["bf"] for e in events)
            rec["n_events"] = len(events)
            rec["status"] = "ok"
            # keep memory bounded: binned data plus raw points near the top events only
            if events:
                near = np.zeros(t.size, dtype=bool)
                for e in sorted(events, key=lambda e: -e["snr"])[:5]:
                    near |= np.abs(t - e["t_center"]) < 3.0
                store[sid] = ({"t": binned["t"], "f": binned["f"]}, (t[near], f[near]), p)
        except Exception as exc:
            rec["status"] = "error: " + str(exc)[:200]
            log("target failed", sid, exc)
            traceback.print_exc()
        per_target.append(rec)
        if ti % 10 == 0:
            log(f"[{ti + 1}/{len(targets)}] {sid} {rec['status']} sectors={rec['n_sectors']} "
                f"events={rec.get('n_events', 0)} elapsed={(time.time() - t_start) / 60:.1f} min")
            write_csv(os.path.join(args.out_dir, "tess_targets_partial.csv"), per_target,
                      sorted({k for r in per_target for k in r}))

    # shared-time systematics flag: events in several targets at the same time
    times = np.array([e["t_center"] for e in all_events]) if all_events else np.empty(0)
    for e in all_events:
        e["n_other_targets_same_time"] = int(np.sum(np.abs(times - e["t_center"]) < 0.25)) - 1
        score = min(e["snr"], 50) * (1 + np.log10(max(e["bf"], 1e-3)) if e["bf"] > 1 else 1)
        if e["near_edge"]:
            score *= 0.5
        if e["n_other_targets_same_time"] >= 2:
            score *= 0.3
        e["score"] = float(score)
    all_events.sort(key=lambda e: -e["score"])

    fields_t = sorted({k for r in per_target for k in r})
    write_csv(os.path.join(args.out_dir, "tess_targets.csv"), per_target, fields_t)
    ev_fields = ["score", "source_id", "tic", "class", "gmag", "period_d", "m2_dark", "p_ecl",
                 "gaia_eb", "t_center", "duration_h", "pred_dur_h", "depth_ppm", "snr",
                 "box_noise_ppm", "near_edge", "n_other_targets_same_time", "conj", "bf",
                 "frac_in_window", "offset_d", "offset_sd_d", "at_rv_transit_conj",
                 "seg_start", "seg_end"]
    write_csv(os.path.join(args.out_dir, "events.csv"), all_events, ev_fields)
    write_csv(os.path.join(args.out_dir, "covered_windows.csv"), all_windows,
              ["source_id", "tic", "class_", "period_d", "conj", "is_rv_transit", "centre",
               "sd", "n_in_1sd", "n_in_3sd"])

    # plots for the best-scoring event per target
    done = set()
    n_plot = 0
    for e in all_events:
        if n_plot >= args.plots:
            break
        sid = e["source_id"]
        if sid in done or sid not in store:
            continue
        done.add(sid)
        binned, raw, p = store[sid]
        s = samples[sid]
        windows = []
        for key in ("t1", "t2"):
            off = go.phase_offsets(s, key, e["t_center"])
            c = e["t_center"] - np.median(off)
            sd = max(1.4826 * np.median(np.abs(off - np.median(off))), 0.05)
            for k in range(-40, 41):
                lo, hi = c + k * p["period_d"] - sd, c + k * p["period_d"] + sd
                windows.append((lo, hi, "c1" if key == "t1" else "c2"))
        title = (f"Gaia {args.schema} {sid}  TIC {e['tic']}  P={p['period_d']:.2f} d  class={p['class']} "
                 f"m2(dark)={p['m2_dark']:.3f} Msun  p_ecl={p['p_ecl']:.2f}\n"
                 f"event t={e['t_center']:.3f} dur={e['duration_h']:.0f} h depth={e['depth_ppm']:.0f} ppm "
                 f"snr={e['snr']:.1f} conj={e['conj']} BF={e['bf']:.1f} offset={e['offset_d']:.2f}+-{e['offset_sd_d']:.2f} d")
        try:
            plot_event(os.path.join(args.out_dir, "plots", f"{n_plot:02d}_{sid}.png"),
                       title, binned, raw, e, windows)
            n_plot += 1
        except Exception as exc:
            log("plot failed", sid, exc)

    ok = [r for r in per_target if r["status"] == "ok"]
    summary.update({
        "targets_processed": len(per_target),
        "targets_with_tess": len(ok),
        "events_total": len(all_events),
        "targets_with_events": len({e["source_id"] for e in all_events}),
        "events_bf_gt_10": sum(1 for e in all_events if e["bf"] > 10),
        "expected_eclipses_covered": expected,
        "expected_eclipses_covered_both_conj": expected_both,
        "covered_either_conj_gt_0.5": sum(1 for r in ok if max(r["cov1"], r["cov2"]) > 0.5),
        "windows_covered": len(all_windows),
        "rv_transit_windows_covered": sum(1 for w in all_windows if w["is_rv_transit"]),
        "minutes": (time.time() - t_start) / 60,
    })
    with open(os.path.join(args.out_dir, "run_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=str)

    lines = [f"# Gaia ({args.schema}) astrometric orbits x TESS: eclipse search", "",
             "Made by AI agents working for MV2 of Munim, Inc. Apache-2.0 code, CC BY 4.0 results.", "",
             "```", json.dumps(summary, indent=1, default=str), "```", "",
             "## Top events (score = SNR x conjunction-window match, penalised for edges and shared times)", "",
             "| score | Gaia source_id | TIC | class | P (d) | t (BTJD) | dur (h) | depth (ppm) | SNR | conj | RV transit? | BF | offset (d) | Gaia EB |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in all_events[:60]:
        lines.append(f"| {e['score']:.1f} | {e['source_id']} | {e['tic']} | {e['class']} | {e['period_d']:.2f} | "
                     f"{e['t_center']:.3f} | {e['duration_h']:.0f} | {e['depth_ppm']:.0f} | {e['snr']:.1f} | "
                     f"{e['conj']} | {e['at_rv_transit_conj']} | {e['bf']:.1f} | "
                     f"{e['offset_d']:.2f}+-{e['offset_sd_d']:.2f} | {e['gaia_eb']} |")
    with open(os.path.join(args.out_dir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log("done", json.dumps(summary, default=str)[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
