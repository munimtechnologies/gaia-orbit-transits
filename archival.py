# SPDX-License-Identifier: Apache-2.0
"""Archival photometry test of transits predicted by Gaia astrometric orbits.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0.

For each star, the Gaia DR3 orbit (Monte Carlo over the catalogue errors and
correlations, gaia_orbits.sample_orbit) gives a joint posterior of the period P and
of the transit time T at a reference epoch in the middle of the archival data. Every
archival light curve that can be fetched without a login is then searched for a
transit inside that posterior, and the same data tell how much of the posterior
they have already excluded:

  * Gaia DR3 epoch photometry (G, BP, RP; 2014-2017, the epochs of the orbit itself)
  * ZTF (IRSA light-curve service; g, r, i; 2018-)
  * ASAS-SN Sky Patrol v2 (V, g; 2012-)
  * TESS (SPOC / TESS-SPOC / QLP via lightkurve, binned to 30 min)

Search. Residuals d = 1 - flux/trend (trend: running median that skips +-D around
each point, so a transit is not removed with the trend), weighted by each light
curve's robust scatter. For a box of duration D centred on (P, T) the statistic is
SNR = sum(w d) / sqrt(sum w) over in-transit points. The grid spans P within
3.5 sigma and, at each P, T within 3.5 conditional sigma of the Gaia posterior.
Durations searched: the predicted central duration D0 and 0.6 D0.

Calibration. The same search is repeated on data whose residuals were cyclically
shifted within each light curve (keeps the noise and its time structure, breaks the
link with the ephemeris). The detection threshold is the larger of 6 and the maximum
of these null runs; FAP = (1 + #null >= observed) / (1 + n_null).

Sensitivity. Box transits of several depths are injected at (P, T) drawn from the
Gaia posterior (impact parameter uniform in 0..0.9) and counted as recovered when
the nearest grid cells reach the threshold. The recovery fraction R at the
predicted depth turns the prior transit probability p into a posterior
p (1 - R) / (1 - p R).

0.4.1: (a) scan() pre-selected points within h + D/2 of the window centre, but its
T grid reaches ceil(h/dT) dT >= h, so boxes at the grid edge lost points; dropping
points with negative residuals raised their SNR above the true value (caught by the
brute-force test). The pre-selection now spans the whole grid. (b) The Gaia ESA
Archive renamed the DataLink structure INDIVIDUAL to DATAMODEL_STANDARD (October
2026); both names are tried, and VOTable answers are converted.
"""
import argparse
import csv
import io
import json
import os
import subprocess
import sys
import time
import zipfile

import numpy as np

import gaia_orbits as go

VERSION = "0.4.1"
GAIA_TIME_TO_BTJD = 2455197.5 - 2457000.0   # Gaia epoch-photometry time (BJD-2455197.5)
ZTF_URL = "https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves"
GAIA_DATALINK = "https://gea.esac.esa.int/data-server/data"
# (DATA_STRUCTURE, FORMAT) tried in order; INDIVIDUAL is the pre-October-2026 name
DATALINK_TRIES = (("DATAMODEL_STANDARD", "CSV"), ("INDIVIDUAL", "CSV"),
                  ("DATAMODEL_STANDARD", "votable"))
SNR_FLOOR = 6.0
MIN_PTS = 3
NSIG = 3.5
# (half window, minimum excluded half width) of the running-median trend, days;
# None = no detrending (only a median normalisation)
DETREND = {"tess": (1.5, 0.3), "ztf": (5.0, 0.5), "asassn": (5.0, 0.5),
           "gaia": None, "synthetic": None}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- parsers
def parse_ztf_csv(text, min_points=10):
    """IRSA ZTF light-curve CSV -> list of segments (one per filter/field/ccd/quadrant/oid).

    Keeps catflags == 0 and, per segment, the most common exposure time (long
    exposures of bright stars saturate and read fainter). Time: hjd - 2457000.
    """
    groups = {}
    for raw in csv.DictReader(io.StringIO(text)):
        r = {str(k).strip(): (v or "").strip() for k, v in raw.items() if k is not None}
        try:
            if int(float(r.get("catflags", "0") or 0)) != 0:
                continue
            mag = float(r["mag"])
            hjd = float(r["hjd"])
            exp = float(r.get("exptime") or 30.0)
        except (KeyError, ValueError):
            continue
        if not (np.isfinite(mag) and np.isfinite(hjd)):
            continue
        key = (r.get("filtercode", "z?"), r.get("field", ""), r.get("ccdid", ""),
               r.get("qid", ""), r.get("oid", ""))
        groups.setdefault(key, []).append((hjd - 2457000.0, mag, exp))
    segs = []
    for key, pts in sorted(groups.items()):
        a = np.array(pts, dtype=float)
        vals, cnt = np.unique(a[:, 2], return_counts=True)
        a = a[a[:, 2] == vals[np.argmax(cnt)]]
        if len(a) < min_points:
            continue
        a = a[np.argsort(a[:, 0])]
        f = 10 ** (-0.4 * (a[:, 1] - np.median(a[:, 1])))
        segs.append({"name": "ztf-%s-f%s-c%s-q%s-%s" % key, "survey": "ztf",
                     "t": a[:, 0], "f": f})
    return segs


def _truthy(v):
    return str(v).strip().lower() in ("true", "1", "t", "yes")


def parse_gaia_epoch_csv(text, min_points=5):
    """Gaia DR3 epoch photometry (DataLink, one row per observation, CSV) -> segments.

    One segment per band (G, BP, RP). Rows rejected_by_photometry are dropped.
    Time: Gaia 'time' (BJD - 2455197.5) -> BTJD.
    """
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    by_band = {}
    for raw in csv.DictReader(lines):
        r = {str(k).strip().lower(): (v or "").strip() for k, v in raw.items() if k is not None}
        if _truthy(r.get("rejected_by_photometry", "false")):
            continue
        try:
            t = float(r["time"]) + GAIA_TIME_TO_BTJD
        except (KeyError, ValueError):
            continue
        flux = np.nan
        try:
            flux = float(r.get("flux", "nan") or "nan")
        except ValueError:
            pass
        if not np.isfinite(flux) or flux <= 0:
            try:
                flux = 10 ** (-0.4 * float(r["mag"]))
            except (KeyError, ValueError):
                continue
        if not (np.isfinite(t) and np.isfinite(flux) and flux > 0):
            continue
        band = r.get("band", "G").upper() or "G"
        by_band.setdefault(band, []).append((t, flux))
    segs = []
    for band, pts in sorted(by_band.items()):
        a = np.array(pts, dtype=float)
        if len(a) < min_points:
            continue
        a = a[np.argsort(a[:, 0])]
        segs.append({"name": f"gaia-{band}", "survey": "gaia", "t": a[:, 0],
                     "f": a[:, 1] / np.median(a[:, 1])})
    return segs


def parse_asassn_csv(text, min_points=10):
    """ASAS-SN Sky Patrol v2 light curves (lcs.data written as CSV) -> segments.

    Keeps the asas_sn_id with most points, good-quality rows (quality 'G' when the
    column exists) with positive flux; one segment per filter and camera.
    Time: jd (HJD) - 2457000.
    """
    rows = []
    for raw in csv.DictReader(io.StringIO(text)):
        r = {str(k).strip().lower(): (v or "").strip() for k, v in raw.items() if k is not None}
        if "quality" in r and r["quality"] and r["quality"].upper() != "G":
            continue
        try:
            jd = float(r["jd"])
            flux = float(r["flux"])
            ferr = float(r.get("flux_err", "1") or 1)
        except (KeyError, ValueError):
            continue
        if not (np.isfinite(jd) and np.isfinite(flux) and flux > 0 and ferr > 0):
            continue
        cam = r.get("camera") or r.get("cam") or ""
        filt = r.get("phot_filter") or r.get("filter") or ""
        rows.append((r.get("asas_sn_id", ""), filt, cam, jd - 2457000.0, flux))
    if not rows:
        return []
    ids, counts = np.unique([x[0] for x in rows], return_counts=True)
    best = ids[np.argmax(counts)]
    groups = {}
    for sid, filt, cam, t, fl in rows:
        if sid == best:
            groups.setdefault((filt, cam), []).append((t, fl))
    segs = []
    for (filt, cam), pts in sorted(groups.items()):
        a = np.array(pts, dtype=float)
        if len(a) < min_points:
            continue
        a = a[np.argsort(a[:, 0])]
        segs.append({"name": f"asassn-{filt or 'x'}-{cam or 'x'}", "survey": "asassn",
                     "t": a[:, 0], "f": a[:, 1] / np.median(a[:, 1])})
    return segs


# ---------------------------------------------------------------- fetchers
def _cached_text(path, fetch):
    if path and os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    text = fetch()
    if path and text:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return text


def fetch_ztf(ra, dec, cache_dir, sid, radius_deg=0.0005):
    import requests
    segs = []
    for band in ("g", "r", "i"):
        url = (f"{ZTF_URL}?POS=CIRCLE%20{ra:.7f}%20{dec:.7f}%20{radius_deg}"
               f"&BANDNAME={band}&FORMAT=CSV&BAD_CATFLAGS_MASK=32768")

        def get(url=url):
            for attempt in range(3):
                try:
                    r = requests.get(url, timeout=300)
                    r.raise_for_status()
                    return r.text
                except Exception as exc:
                    log("ZTF retry", attempt, exc)
                    time.sleep(10 * (attempt + 1))
            return ""
        text = _cached_text(os.path.join(cache_dir, f"{sid}_ztf_{band}.csv"), get)
        segs += parse_ztf_csv(text)
    return segs


def datalink_payload_to_text(content):
    """DataLink answer (raw, or a ZIP of one file per product) -> CSV text.
    VOTable members are converted with astropy."""
    blobs = []
    if content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            for name in z.namelist():
                blobs.append(z.read(name))
    else:
        blobs.append(content)
    out = []
    for b in blobs:
        head = b[:400].lstrip()
        if head.startswith(b"<?xml") or b"<VOTABLE" in head:
            try:
                from astropy.io.votable import parse_single_table
                import run_search as rs
                tbl = parse_single_table(io.BytesIO(b)).to_table()
                out.append(rs.table_to_csv(tbl))
            except Exception as exc:
                log("VOTable conversion failed:", exc)
        else:
            out.append(b.decode("utf-8", "replace"))
    return "\n".join(out)


def fetch_gaia_epoch(sid, cache_dir, release="Gaia DR3"):
    """Epoch photometry through Gaia DataLink. DR4 (2026-12-02) publishes epoch
    photometry for all sources; check its time origin before trusting BTJD."""
    def get():
        import requests
        for structure, fmt in DATALINK_TRIES:
            params = {"RETRIEVAL_TYPE": "EPOCH_PHOTOMETRY", "ID": str(sid), "FORMAT": fmt,
                      "RELEASE": release, "DATA_STRUCTURE": structure}
            try:
                r = requests.get(GAIA_DATALINK, params=params, timeout=600)
                r.raise_for_status()
                text = datalink_payload_to_text(r.content)
                if "band" in text[:5000].lower() and "time" in text[:5000].lower():
                    log("Gaia DataLink ok:", structure, fmt)
                    return text
                log("Gaia DataLink", structure, fmt, "unexpected content:", text[:200])
            except Exception as exc:
                log("Gaia DataLink", structure, fmt, "failed:", exc)
        for structure in ("DATAMODEL_STANDARD", "INDIVIDUAL"):   # astroquery fallback
            try:
                from astroquery.gaia import Gaia
                res = Gaia.load_data(ids=[str(sid)], data_release=release,
                                     retrieval_type="EPOCH_PHOTOMETRY",
                                     data_structure=structure, format="csv")
                out = []
                for _, tables in res.items():
                    for tb in tables:
                        tb = tb.to_table() if hasattr(tb, "to_table") else tb
                        buf = io.StringIO()
                        tb.write(buf, format="ascii.csv")
                        out.append(buf.getvalue())
                if out:
                    return "\n".join(out)
            except Exception as exc:
                log("astroquery Gaia epoch photometry", structure, "failed:", exc)
        return ""
    tag = release.replace(" ", "").lower()
    text = _cached_text(os.path.join(cache_dir, f"{sid}_{tag}_epoch.csv"), get)
    return parse_gaia_epoch_csv(text) if text else []


def fetch_asassn(ra, dec, cache_dir, sid):
    def get():
        try:
            import pyasassn  # noqa: F401
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "skypatrol"],
                           check=False)
        try:
            from pyasassn.client import SkyPatrolClient
            client = SkyPatrolClient()
            lcs = None
            for kw in ({"radius": 5.0 / 3600}, {"radius": 5.0, "units": "arcsec"}):
                try:
                    lcs = client.cone_search(ra_deg=ra, dec_deg=dec, catalog="master_list",
                                             mode="download_curves", threads=1, **kw)
                except TypeError:
                    continue
                if lcs is not None and getattr(lcs, "data", None) is not None and len(lcs.data):
                    break
            if lcs is None or getattr(lcs, "data", None) is None:
                return ""
            return lcs.data.to_csv(index=False)
        except Exception as exc:
            log("ASAS-SN failed:", exc)
            return ""
    text = _cached_text(os.path.join(cache_dir, f"{sid}_asassn.csv"), get)
    return parse_asassn_csv(text) if text else []


def fetch_tess_segments(ra, dec, gmag, sid, lk_dir, max_lcs=20):
    import dipsearch as ds
    import run_search as rs
    tic = rs.find_tic(ra, dec, gmag, sid)
    if tic is None:
        return [], None
    lcs, meta = rs.fetch_tess(tic["tic"], tic["ra"], tic["dec"], lk_dir, max_lcs)
    segs = []
    for (t, f), m in zip(lcs, meta):
        bt, bf, _ = ds.bin_lc(t, f, 1.0 / 48)
        if bt.size >= 10:
            segs.append({"name": f"tess-s{m['sector']}-{m['author']}", "survey": "tess",
                         "t": bt, "f": bf / np.median(bf)})
    return segs, tic["tic"]


# ---------------------------------------------------------------- preparation
def detrend(t, f, half_window, exclude):
    """f / running median over |dt| <= half_window, skipping |dt| <= exclude."""
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    gmed = np.median(f)
    lo = np.searchsorted(t, t - half_window, side="left")
    hi = np.searchsorted(t, t + half_window, side="right")
    trend = np.empty_like(f)
    for i in range(t.size):
        st = t[lo[i]:hi[i]]
        m = np.abs(st - t[i]) > exclude
        trend[i] = np.median(f[lo[i]:hi[i]][m]) if m.sum() >= 3 else gmed
    return f / trend


def prepare(segments, d0):
    """Segments -> arrays t, d (1 - detrended flux), w (1/sd^2), g (segment index),
    survey (per point) and a per-segment summary."""
    T, D, W, G, S, info = [], [], [], [], [], []
    for gi, sg in enumerate(segments):
        t = np.asarray(sg["t"], float)
        f = np.asarray(sg["f"], float)
        ok = np.isfinite(t) & np.isfinite(f) & (f > 0)
        t, f = t[ok], f[ok]
        if t.size < 10:
            continue
        o = np.argsort(t)
        t, f = t[o], f[o]
        par = DETREND.get(sg.get("survey"), None)
        if par is not None:
            half, ex = par
            ex = max(ex, d0)
            r = detrend(t, f, ex + half, ex)
        else:
            r = f / np.median(f)
        d = 1.0 - r
        d = d - np.median(d)
        sd = 1.4826 * np.median(np.abs(d))
        sd = max(sd, 1e-4)
        keep = (d > -5 * sd) & (d < max(8 * sd, 0.08))
        t, d = t[keep], d[keep]
        if t.size < 10:
            continue
        T.append(t)
        D.append(d)
        W.append(np.full(t.size, 1.0 / sd ** 2))
        G.append(np.full(t.size, gi))
        S.append(np.full(t.size, sg.get("survey", "?"), dtype=object))
        info.append({"name": sg["name"], "survey": sg.get("survey", "?"), "n": int(t.size),
                     "sd": float(sd), "t_min": float(t.min()), "t_max": float(t.max())})
    if not T:
        return None
    t = np.concatenate(T)
    o = np.argsort(t)
    return {"t": t[o], "d": np.concatenate(D)[o], "w": np.concatenate(W)[o],
            "g": np.concatenate(G)[o], "survey": np.concatenate(S)[o], "segments": info}


# ---------------------------------------------------------------- ephemeris posterior
def ephemeris(P_s, T_s, tc_central, P_central, t_ref):
    """Joint (P, T at the epoch nearest t_ref) posterior summary from MC samples.

    T_s are conjunction times of one label (t1 or t2) near tc_central; each is first
    wrapped to the cycle of tc_central, then carried n cycles with its own period.
    """
    P_s = np.abs(np.asarray(P_s, float))
    T_s = np.asarray(T_s, float)
    ok = np.isfinite(P_s) & np.isfinite(T_s) & (P_s > 0)
    P_s, T_s = P_s[ok], T_s[ok]
    T_s = tc_central + np.mod(T_s - tc_central + P_s / 2, P_s) - P_s / 2
    n = float(np.round((t_ref - tc_central) / P_central))
    T_r = T_s + n * P_s
    pm, tm = float(np.median(P_s)), float(np.median(T_r))
    psd = float(1.4826 * np.median(np.abs(P_s - pm)))
    tsd = float(1.4826 * np.median(np.abs(T_r - tm)))
    psd = max(psd, 1e-7)
    tsd = max(tsd, 1e-5)
    core = (np.abs(P_s - pm) < 5 * psd) & (np.abs(T_r - tm) < 5 * tsd)
    rho = 0.0
    if core.sum() > 10 and np.std(P_s[core]) > 0 and np.std(T_r[core]) > 0:
        rho = float(np.corrcoef(P_s[core], T_r[core])[0, 1])
        rho = float(np.clip(rho, -0.999, 0.999))
    return {"P_mu": pm, "P_sd": psd, "T_mu": tm, "T_sd": tsd, "rho": rho,
            "n_cycles": n, "t_ref": float(t_ref), "P_s": P_s, "T_s": T_r}


def t_mean_given_p(eph, P):
    return eph["T_mu"] + eph["rho"] * eph["T_sd"] / eph["P_sd"] * (P - eph["P_mu"])


def t_sd_given_p(eph):
    return eph["T_sd"] * np.sqrt(max(1.0 - eph["rho"] ** 2, 1e-6))


def wrap(x, P):
    return np.mod(x + P / 2, P) - P / 2


# ---------------------------------------------------------------- statistic
def snr_at(t, d, w, P, T, D):
    """(snr, depth, n_in, n_epochs) of a box of duration D centred on T + k P."""
    x = wrap(t - T, P)
    m = np.abs(x) < D / 2
    n = int(m.sum())
    if n == 0:
        return 0.0, 0.0, 0, 0
    sw = float(w[m].sum())
    swd = float((w[m] * d[m]).sum())
    cyc = np.round((t[m] - T) / P)
    return swd / np.sqrt(sw), swd / sw, n, int(np.unique(cyc).size)


def grid(eph, span, D, max_np=1201):
    dT = D / 4.0
    ncyc = max(1.0, span / eph["P_mu"])
    dP = dT / ncyc
    half = NSIG * eph["P_sd"]
    K = int(np.ceil(half / dP))
    kmax = (max_np - 1) // 2
    if K > kmax:
        K = kmax
        dP = half / K
    K = max(K, 0)
    return {"D": D, "dT": dT, "dP": dP, "K": K,
            "Ps": eph["P_mu"] + dP * np.arange(-K, K + 1)}


def t_halfwidth(eph, P, D):
    return min(max(NSIG * t_sd_given_p(eph), D), P / 2)


def scan(t, d, w, eph, gr):
    """Best on-window cell and the per-P maximum SNR for one duration grid."""
    D, dT = gr["D"], gr["dT"]
    best = {"snr": -np.inf}
    per_p = np.zeros(gr["Ps"].size)
    for i, P in enumerate(gr["Ps"]):
        Tm = t_mean_given_p(eph, P)
        h = t_halfwidth(eph, P, D)
        nT = int(np.ceil(h / dT))
        dg = dT * np.arange(-nT, nT + 1)
        x = wrap(t - Tm, P)
        # 0.4.1: every box (|x - dg| < D/2, |dg| <= nT dT) must see all its points
        reach = nT * dT + D / 2
        if reach < P / 2:
            sel = np.abs(x) <= reach * (1 + 1e-12) + 1e-12
            xs, ws, dd = x[sel], w[sel], d[sel]
        else:
            xs = np.concatenate([x - P, x, x + P])
            ws = np.tile(w, 3)
            dd = np.tile(d, 3)
        if xs.size == 0:
            continue
        o = np.argsort(xs)
        xs, ws, dd = xs[o], ws[o], dd[o]
        cw = np.concatenate([[0.0], np.cumsum(ws)])
        cwd = np.concatenate([[0.0], np.cumsum(ws * dd)])
        lo = np.searchsorted(xs, dg - D / 2, side="right")
        hi = np.searchsorted(xs, dg + D / 2, side="left")
        sw = cw[hi] - cw[lo]
        swd = cwd[hi] - cwd[lo]
        n = hi - lo
        snr = np.where(sw > 0, swd / np.sqrt(np.where(sw > 0, sw, 1.0)), 0.0)
        snr[n < MIN_PTS] = 0.0
        k = int(np.argmax(snr))
        per_p[i] = snr[k]
        if snr[k] > best["snr"]:
            best = {"snr": float(snr[k]), "P": float(P), "T": float(Tm + dg[k]), "D": D,
                    "n_in": int(n[k]), "depth": float(swd[k] / sw[k]) if sw[k] > 0 else 0.0}
    if not np.isfinite(best["snr"]):
        best = {"snr": 0.0, "P": eph["P_mu"], "T": eph["T_mu"], "D": D, "n_in": 0, "depth": 0.0}
    return best, per_p


def shuffled(d, g, rng):
    """Residuals cyclically shifted within each light curve (time order kept)."""
    out = d.copy()
    for gi in np.unique(g):
        idx = np.where(g == gi)[0]
        n = idx.size
        if n < 10:
            continue
        out[idx] = np.roll(d[idx], int(rng.integers(max(1, n // 10), n - n // 10)))
    return out


def _cells(eph, gr, P_j, T_j):
    k0 = int(np.round((P_j - eph["P_mu"]) / gr["dP"])) if gr["dP"] > 0 else 0
    if abs(k0) > gr["K"] + 1:
        return []
    out = []
    for k in sorted({int(np.clip(k0 + dk, -gr["K"], gr["K"])) for dk in (-1, 0, 1)}):
        P = eph["P_mu"] + k * gr["dP"]
        Tm = t_mean_given_p(eph, P)
        h = t_halfwidth(eph, P, gr["D"])
        nT = int(np.ceil(h / gr["dT"]))
        m0 = int(np.round(wrap(T_j - Tm, P) / gr["dT"]))
        if abs(m0) > nT + 1:
            continue
        for m in sorted({int(np.clip(m0 + dm, -nT, nT)) for dm in (-1, 0, 1)}):
            out.append((P, Tm + m * gr["dT"]))
    return out


def injection_recovery(t, d, w, eph, grids, D0, depths, thr, n_inj, rng):
    """Recovery fraction per depth and data coverage over the Gaia posterior."""
    n_s = eph["P_s"].size
    if n_s == 0 or t.size == 0:
        return {"recovered": {f"{x:g}": 0.0 for x in depths}, "cov1": 0.0, "cov3": 0.0,
                "cov_2ep": 0.0, "n_inj": 0}
    idx = rng.integers(0, n_s, n_inj)
    depths = np.asarray(depths, float)
    rec = np.zeros(depths.size)
    c1 = c3 = c2e = 0
    for j in idx:
        P_j, T_j = eph["P_s"][j], eph["T_s"][j]
        b = rng.uniform(0.0, 0.9)
        Dj = D0 * np.sqrt(1 - b * b)
        inj = (np.abs(wrap(t - T_j, P_j)) < Dj / 2).astype(float)
        n_in = int(inj.sum())
        c1 += n_in >= 1
        c3 += n_in >= MIN_PTS
        if n_in:
            c2e += np.unique(np.round((t[inj > 0] - T_j) / P_j)).size >= 2
        if n_in == 0:
            continue
        best = np.full(depths.size, -np.inf)
        for gr in grids:
            for (P, T) in _cells(eph, gr, P_j, T_j):
                m = np.abs(wrap(t - T, P)) < gr["D"] / 2
                if m.sum() < MIN_PTS:
                    continue
                sw = w[m].sum()
                a = (w[m] * d[m]).sum()
                bb = (w[m] * inj[m]).sum()
                best = np.maximum(best, (a + depths * bb) / np.sqrt(sw))
        rec += best >= thr
    n = float(len(idx))
    return {"recovered": {f"{x:g}": float(r / n) for x, r in zip(depths, rec)},
            "cov1": c1 / n, "cov3": c3 / n, "cov_2ep": c2e / n, "n_inj": int(n)}


def analyse(data, eph, D0, pred_depth, p_prior, n_null=30, n_inj=300, rng=None,
            extra_depths=(0.005, 0.01)):
    """Search + null calibration + injection-recovery for one ephemeris posterior."""
    rng = rng if rng is not None else np.random.default_rng(1)
    t, d, w, g = data["t"], data["d"], data["w"], data["g"]
    span = float(t.max() - t.min()) if t.size else 0.0
    D0 = max(D0, 1.0 / 24)
    grids = [grid(eph, span, D0), grid(eph, span, 0.6 * D0)]
    obs, per_p = None, None
    for gr in grids:
        b, pp = scan(t, d, w, eph, gr)
        if obs is None or b["snr"] > obs["snr"]:
            obs = b
        if per_p is None:
            per_p = pp
    snr, depth, n_in, n_ep = snr_at(t, d, w, obs["P"], obs["T"], obs["D"])
    obs.update({"n_epochs": n_ep})
    # per-survey contribution at the best cell
    by_survey = {}
    for sv in sorted(set(data["survey"].tolist())):
        m = data["survey"] == sv
        by_survey[sv] = snr_at(t[m], d[m], w[m], obs["P"], obs["T"], obs["D"])[0]
    null = []
    for _ in range(n_null):
        ds_ = shuffled(d, g, rng)
        null.append(max(scan(t, ds_, w, eph, gr)[0]["snr"] for gr in grids))
    null = np.asarray(null, float)
    thr = float(max(SNR_FLOOR, null.max() if null.size else SNR_FLOOR))
    fap = float((1 + np.sum(null >= obs["snr"])) / (1 + null.size))
    depths = [0.5 * pred_depth, pred_depth, 2 * pred_depth] + list(extra_depths)
    inj = injection_recovery(t, d, w, eph, grids, D0, depths, thr, n_inj, rng)
    R = inj["recovered"][f"{pred_depth:g}"]
    p_post = p_prior * (1 - R) / (1 - p_prior * R) if p_prior < 1 else np.nan
    if obs["snr"] >= thr and obs["n_epochs"] >= 2:
        verdict = "candidate (needs vetting)"
    elif obs["snr"] >= thr:
        verdict = "single-event candidate (needs vetting)"
    else:
        verdict = "no detection"
    return {"obs": obs, "by_survey_snr": by_survey, "null_max": null.tolist(), "thr": thr,
            "fap": fap, "injection": inj, "recovery_at_pred_depth": R,
            "p_transit_prior": p_prior, "p_transit_post": float(p_post),
            "verdict": verdict, "per_p_max": per_p.tolist(),
            "grid_Ps": grids[0]["Ps"].tolist(), "D0_d": D0, "pred_depth": pred_depth,
            "span_d": span}


# ---------------------------------------------------------------- plotting
def plot_result(path, title, data, eph, res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(9, 7))
    ax[0].plot(np.asarray(res["grid_Ps"]), np.asarray(res["per_p_max"]), "k-", lw=0.8)
    ax[0].axhline(res["thr"], color="r", ls="--", lw=0.8, label="threshold (null max)")
    ax[0].axvline(eph["P_mu"], color="0.5", lw=0.5)
    ax[0].set_xlabel("period (d)")
    ax[0].set_ylabel("max SNR in window (D0)")
    ax[0].legend(fontsize=7)
    ob = res["obs"]
    t, d = data["t"], data["d"]
    x = wrap(t - ob["T"], ob["P"])
    m = np.abs(x) < max(4 * ob["D"], 1.0)
    colors = {"tess": "tab:blue", "ztf": "tab:green", "asassn": "tab:orange",
              "gaia": "tab:red"}
    for sv in sorted(set(data["survey"][m].tolist())):
        mm = m & (data["survey"] == sv)
        ax[1].plot(x[mm] * 24, 1 - d[mm], ".", ms=3, color=colors.get(sv, "k"), label=sv)
    ax[1].axvspan(-ob["D"] * 12, ob["D"] * 12, color="0.85", zorder=0)
    ax[1].set_xlabel("hours from best-cell transit time")
    ax[1].set_ylabel("detrended flux")
    ax[1].legend(fontsize=7)
    ax[1].set_title(f"best cell: P={ob['P']:.4f} d T={ob['T']:.3f} SNR={ob['snr']:.1f} "
                    f"depth={ob['depth'] * 100:.2f}% n={ob['n_in']} epochs={ob['n_epochs']}",
                    fontsize=8)
    fig.suptitle(title, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


# ---------------------------------------------------------------- main
def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items() if k not in ("P_s", "T_s")}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def main(argv=None):
    import run_search as rs
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--source-ids", required=True)
    ap.add_argument("--schema", default="gaiadr3")
    ap.add_argument("--gmax", type=float, default=17)
    ap.add_argument("--cosi-max", type=float, default=0.3)
    ap.add_argument("--mc", type=int, default=2000)
    ap.add_argument("--n-null", type=int, default=30)
    ap.add_argument("--n-inj", type=int, default=300)
    ap.add_argument("--surveys", default="gaia,ztf,asassn,tess")
    ap.add_argument("--max-lcs", type=int, default=20)
    ap.add_argument("--time-budget-min", type=float, default=200)
    ap.add_argument("--seed", type=int, default=20261117)
    args = ap.parse_args(argv)
    t0 = time.time()
    surveys = {s.strip() for s in args.surveys.split(",") if s.strip()}
    ids = [int(x) for x in args.source_ids.replace(" ", "").split(",") if x]
    order = list(dict.fromkeys(ids))           # keep the given order (best target first)
    src = sorted(set(ids))
    os.makedirs(args.out_dir, exist_ok=True)
    pdir = os.path.join(args.out_dir, "archival")
    os.makedirs(pdir, exist_ok=True)
    cache = os.path.join(args.data_dir, "archival")
    os.makedirs(cache, exist_ok=True)
    lk_dir = os.path.join(args.data_dir, "lk")
    os.makedirs(lk_dir, exist_ok=True)
    go.GAIA_REF_BTJD = 936.875 if args.schema.lower().endswith("dr4") else 389.0

    # same cache file name as run_search.py --source-ids (shared data_key)
    tag = f"{args.schema}_nss_ti_g{args.gmax:g}_c{args.cosi_max:g}"
    tag += f"_ids{len(src)}-{sum(src) % 1000003}"
    query = rs.build_nss_query(args.schema, args.gmax, args.cosi_max, None, src)
    text = rs.cached_query(os.path.join(args.data_dir, tag + "_v3.csv"), query)
    rows = rs.read_csv_text(text)
    log("Gaia rows:", len(rows))
    by_src = {}
    for r in rows:
        ep = r.get("ref_epoch", np.nan)
        r["ref_btjd"] = rs.ref_epoch_to_btjd(ep) if np.isfinite(ep) else go.GAIA_REF_BTJD
        lab = go.transit_label(r)
        r["_labelled"] = bool(lab["transit_conj"])
        old = by_src.get(r["source_id"])
        # prefer an RV-labelled (AstroSpectroSB1) solution when a star has two
        if old is None or (r["_labelled"] and not old["_labelled"]):
            by_src[r["source_id"]] = r

    results, summary = [], {"version": VERSION, "args": vars(args),
                            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for sid in order:
        if (time.time() - t0) / 60 > args.time_budget_min:
            log("time budget reached before", sid)
            summary["stopped_before"] = sid
            break
        r = by_src.get(sid)
        if r is None:
            log("no Gaia row for", sid)
            continue
        rng = np.random.default_rng([args.seed, sid % (2 ** 32), sid // (2 ** 32)])
        try:
            res = rs.prior_for_row(r, args.mc, rng, None)
        except Exception as exc:
            log("prior failed", sid, exc)
            res = None
        if res is None:
            log("no prior for", sid)
            continue
        pr, s, _ = res
        segs, tic = [], ""
        if "gaia" in surveys:
            try:
                rel = "Gaia DR4" if args.schema.lower().endswith("dr4") else "Gaia DR3"
                segs += fetch_gaia_epoch(sid, cache, rel)
            except Exception as exc:
                log("gaia epoch failed", sid, exc)
        if "ztf" in surveys and r["dec"] > -31:
            try:
                segs += fetch_ztf(r["ra"], r["dec"], cache, sid)
            except Exception as exc:
                log("ztf failed", sid, exc)
        if "asassn" in surveys:
            try:
                segs += fetch_asassn(r["ra"], r["dec"], cache, sid)
            except Exception as exc:
                log("asassn failed", sid, exc)
        if "tess" in surveys:
            try:
                ts, tic = fetch_tess_segments(r["ra"], r["dec"], r["phot_g_mean_mag"], sid,
                                              lk_dir, args.max_lcs)
                segs += ts
            except Exception as exc:
                log("tess failed", sid, exc)
        log(sid, "segments:", [(sg["name"], len(sg["t"])) for sg in segs])
        keys = [pr["transit_conj"]] if pr["transit_conj"] and pr["rv_consistent"] else ["t1", "t2"]
        for key in keys:
            D0 = pr[f"dur{key[1]}_h"] / 24.0
            if not np.isfinite(D0) or D0 <= 0:
                D0 = 0.25
            data = prepare(segs, D0)
            rec = {"source_id": sid, "key": key, "rv_labelled": key == pr["transit_conj"],
                   "tic": tic, "period_d": r["period"], "gmag": r["phot_g_mean_mag"],
                   "m2_dark": pr["m2_dark"], "class": pr["class"], "cosi": pr["cosi"]}
            if data is None:
                rec["verdict"] = "no data"
                results.append(rec)
                continue
            t_ref = float(np.median(data["t"]))
            tc = pr["t_conj1_btjd"] if key == "t1" else pr["t_conj2_btjd"]
            eph = ephemeris(s["P"], s[key], tc, float(r["period"]), t_ref)
            r2r1 = pr["r2"] / pr["r1"] if pr["r1"] > 0 else 0.15
            pred_depth = float(min(max(r2r1 ** 2, 0.002), 0.2))
            p_prior = pr[f"p_ecl{key[1]}"]
            try:
                out = analyse(data, eph, D0, pred_depth, p_prior, args.n_null, args.n_inj, rng)
            except Exception as exc:
                import traceback
                traceback.print_exc()
                rec["verdict"] = "error: " + str(exc)[:200]
                results.append(rec)
                continue
            counts = {}
            for sg in data["segments"]:
                counts[sg["survey"]] = counts.get(sg["survey"], 0) + sg["n"]
            rec.update({
                "n_points": int(data["t"].size), "points_by_survey": json.dumps(counts),
                "span_d": out["span_d"], "t_ref_btjd": eph["t_ref"],
                "P_mu": eph["P_mu"], "P_sd": eph["P_sd"], "T_ref_mu": eph["T_mu"],
                "T_ref_sd": eph["T_sd"], "rho_PT": eph["rho"], "D0_h": D0 * 24,
                "pred_depth": pred_depth, "best_snr": out["obs"]["snr"],
                "best_P": out["obs"]["P"], "best_T": out["obs"]["T"],
                "best_D_h": out["obs"]["D"] * 24, "best_depth": out["obs"]["depth"],
                "best_n_in": out["obs"]["n_in"], "best_n_epochs": out["obs"]["n_epochs"],
                "thr": out["thr"], "fap": out["fap"],
                "null_median": float(np.median(out["null_max"])) if out["null_max"] else np.nan,
                "cov_any": out["injection"]["cov1"], "cov_3pts": out["injection"]["cov3"],
                "cov_2epochs": out["injection"]["cov_2ep"],
                "recovery_pred_depth": out["recovery_at_pred_depth"],
                "recovery_by_depth": json.dumps(out["injection"]["recovered"]),
                "p_transit_prior": out["p_transit_prior"],
                "p_transit_post": out["p_transit_post"], "verdict": out["verdict"],
                "by_survey_snr": json.dumps({k: round(v, 2) for k, v in out["by_survey_snr"].items()}),
            })
            results.append(rec)
            with open(os.path.join(pdir, f"{sid}_{key}.json"), "w") as fh:
                json.dump(_jsonable({"record": rec, "ephemeris": eph, "result": out,
                                     "segments": data["segments"]}), fh, indent=1, default=str)
            try:
                plot_result(os.path.join(pdir, f"{sid}_{key}.png"),
                            f"Gaia DR3 {sid} ({key}{' RV transit' if rec['rv_labelled'] else ''}) "
                            f"P={eph['P_mu']:.3f}+-{eph['P_sd']:.3f} d  T_ref={eph['T_mu']:.2f}"
                            f"+-{eph['T_sd']:.2f}  pred depth {pred_depth * 100:.1f}%  "
                            f"R={rec['recovery_pred_depth']:.2f}", data, eph, out)
            except Exception as exc:
                log("plot failed", sid, exc)
            log(sid, key, rec["verdict"], f"snr={rec['best_snr']:.2f} thr={rec['thr']:.2f}",
                f"cov={rec['cov_any']:.2f} R={rec['recovery_pred_depth']:.2f}",
                f"p {rec['p_transit_prior']:.3f}->{rec['p_transit_post']:.3f}")
        fields = sorted({k for x in results for k in x})
        with open(os.path.join(args.out_dir, "archival_results.csv"), "w", newline="",
                  encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            wr.writeheader()
            for x in results:
                wr.writerow(x)

    summary.update({
        "stars": len({x["source_id"] for x in results}), "hypotheses": len(results),
        "candidates": sum(1 for x in results if "candidate" in str(x.get("verdict"))),
        "minutes": (time.time() - t0) / 60})
    with open(os.path.join(args.out_dir, "run_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=str)
    lines = ["# Archival photometry test of Gaia-predicted transits", "",
             "Made by AI agents working for MV2 of Munim, Inc. Apache-2.0 code, CC BY 4.0 results.",
             "", "```", json.dumps(summary, indent=1, default=str), "```", "",
             "| Gaia DR3 | conj | P (d) | points | span (d) | T_ref sd (d) | pred depth | best SNR | thr | FAP |"
             " epochs | coverage | R(pred) | p prior -> post | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for x in results:
        if "best_snr" not in x:
            lines.append(f"| {x['source_id']} | {x['key']} | {x['period_d']:.2f} | 0 | | | | | | | | | | | {x['verdict']} |")
            continue
        lines.append(
            f"| {x['source_id']} | {x['key']}{'*' if x['rv_labelled'] else ''} | {x['period_d']:.2f} | "
            f"{x['n_points']} | {x['span_d']:.0f} | {x['T_ref_sd']:.2f} | {x['pred_depth'] * 100:.2f}% | "
            f"{x['best_snr']:.2f} | {x['thr']:.2f} | {x['fap']:.3f} | {x['best_n_epochs']} | "
            f"{x['cov_any']:.2f} | {x['recovery_pred_depth']:.2f} | "
            f"{x['p_transit_prior']:.3f} -> {x['p_transit_post']:.3f} | {x['verdict']} |")
    lines += ["", "`*` = transit conjunction identified from the Gaia RV orbit (0.3.0)."]
    with open(os.path.join(args.out_dir, "archival_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log("done", json.dumps(summary, default=str)[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
