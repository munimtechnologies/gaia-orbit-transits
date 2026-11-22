#!/usr/bin/env python3
# pixel_which_star.py 0.1.0 -- which star dims? A generic TESS pixel test for transit candidates.
# For each target and each TESS sector (TESScut 15x15 full-frame-image cutouts):
#   pass 1  aperture light curve, masked-median detrending and a per-sector transit epoch;
#           one linear ephemeris from all sectors;
#   pass 2  PSF model of the mean out-of-transit image with every Gaia DR3 star (RP < 17),
#           per-transit difference images, nulls at phases 0.25/0.75, injections on the target
#           and on the most dangerous neighbour, PSF amplitudes and a free-position centroid of
#           the transit signal, converted to an offset on the sky;
#   combine the sky offsets of all sensitive sectors and compare them with every Gaia star
#           within 120 arcsec that is bright enough to make the dip (WS label); the deblended
#           depth; secondary eclipse, odd/even and null-phase depths with event-to-event
#           (red-noise) errors.
# By MV2 of Munim, Inc.; made with AI agents working in his name. License: Apache-2.0.
# Rules: findings/2026-11-22-tic93622019-pixel-prereg.md (written before this job ran).
# The PSF and difference-image core is imported unchanged from tyc_pixel.py 0.1.0 (commit
# c16e7a2a6a13cce476f73153483cc59ad8443362), which ran on real data in job tyc6340-pixel-v2.
# The analysis is pure standard library; numpy/astropy are used only when reading TESScut files.
"""Usage:
  python pixel_which_star.py --self-test
  python pixel_which_star.py --config targets.json --data-dir /data/pws --out-dir /out
Exit codes: 0 ok; 3 self-test failed; 4 the main target could not be fetched (re-file unchanged).
"""
import argparse
import bisect
import csv
import io
import json
import math
import os
import random
import re
import sys
import urllib.parse
import zipfile

import tyc_pixel as tp

VERSION = "0.1.0"

BTJD_YEAR0 = 2014.9356            # Julian year of BTJD 0 (JD 2457000.0)
CUT = 15
GAIA_RADIUS_DEG = 0.075
LIST_RP_MAX = 18.5
NEAR_ARCSEC = 120.0               # Gaia stars compared with the transit centroid
CAPABLE_MARGIN = 0.5              # capable: RP flux ratio >= 0.5 x reference depth
N_RADIUS_PX = 3.0                 # neighbour N for the amplitude test: within 3 px ...
N_MIN_PX = 1.0                    # ... and at least 1 px from the target
Z_POS = 3.0
MIN_SECTORS = 2
CONTROL_OK = ("WS_ON_TARGET", "WS_UNRESOLVED")

TAU_FRAC = 0.12                   # ingress/egress as a fraction of the full duration
IN_FRAC, OUT_LO_FRAC, OUT_HI_FRAC = 0.4, 0.6, 1.4
MIN_PTS = 3
DETREND_CHUNK = 0.5
DETREND_MIN = 5
MASK_PAD = 0.08
REFINE_HALF = 0.06
REFINE_STEP = 0.0005
EPOCH_DCHI2 = 25.0
P_JUMP_MAX = 0.002

SEC_Z = 3.0
OE_Z = 3.0
EB_SEC_PPM = 150.0
DEPTH_TOL = 0.15
R_SUN_RJUP = 9.731

N_BOOT = 300
N_BOOT_POS = 100
SEED = 20261122

TESSCUT = "https://mast.stsci.edu/tesscut/api/v0.1/astrocut"
TESSCUT_SECTORS = "https://mast.stsci.edu/tesscut/api/v0.1/sector"
GAIA_TAPS = [("https://gea.esac.esa.int/tap-server/tap/sync", "gaiadr3.gaia_source"),
             ("https://dc.zah.uni-heidelberg.de/tap/sync", "gaia.dr3lite")]
NASA_TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
NAN = float("nan")


# ---------------------------------------------------------------- small helpers
def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def trap(dt, dur, tau=None):
    """Trapezoid transit shape: 1 on the flat bottom, 0 outside the full duration."""
    if tau is None:
        tau = TAU_FRAC * dur
    a = abs(dt)
    h = 0.5 * dur
    if a >= h:
        return 0.0
    if a <= h - tau:
        return 1.0
    return (h - a) / tau


def epoch_year(times):
    return BTJD_YEAR0 + tp.median(times) / 365.25


def sky_offset(ra0, de0, ra, de):
    """(east, north) offset in arcsec of (ra, de) from (ra0, de0)."""
    dra = ((ra - ra0 + 180.0) % 360.0) - 180.0
    return dra * math.cos(math.radians(de0)) * 3600.0, (de - de0) * 3600.0


def wmean(vals, sigs):
    pairs = [(v, s) for v, s in zip(vals, sigs) if finite(v) and finite(s) and s > 0]
    if not pairs:
        return NAN, NAN, 0
    w = [1.0 / (s * s) for _, s in pairs]
    sw = sum(w)
    return sum(wi * v for wi, (v, _) in zip(w, pairs)) / sw, 1.0 / math.sqrt(sw), len(pairs)


def summarize(vals):
    v = [x for x in vals if finite(x)]
    n = len(v)
    if n < 3:
        return {"n": n, "mean": NAN, "sigma": NAN, "z": NAN}
    m = sum(v) / n
    s = tp.std(v) / math.sqrt(n)
    return {"n": n, "mean": m, "sigma": s, "z": m / s if s > 0 else NAN}


def slug(name):
    return re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()


class FakeWCS:
    """Linear tangent-plane WCS used by the tests and the self-test (same call signature as
    astropy's all_world2pix / all_pix2world with a list of pairs and origin 0)."""

    def __init__(self, ra0, dec0, x0, y0, scale_arcsec, rot_deg):
        self.ra0, self.dec0, self.x0, self.y0 = ra0, dec0, x0, y0
        self.scale = scale_arcsec
        self.c = math.cos(math.radians(rot_deg))
        self.s = math.sin(math.radians(rot_deg))
        self.cosd = math.cos(math.radians(dec0))

    def all_world2pix(self, pts, origin=0):
        out = []
        for ra, de in pts:
            e = (ra - self.ra0) * self.cosd * 3600.0 / self.scale
            n = (de - self.dec0) * 3600.0 / self.scale
            out.append([self.x0 + (-e * self.c + n * self.s), self.y0 + (e * self.s + n * self.c)])
        return out

    def all_pix2world(self, pts, origin=0):
        out = []
        for x, y in pts:
            u, v = x - self.x0, y - self.y0
            e = -self.c * u + self.s * v
            n = self.s * u + self.c * v
            out.append([self.ra0 + e * self.scale / 3600.0 / self.cosd,
                        self.dec0 + n * self.scale / 3600.0])
        return out


def pix2world(wcs, x, y):
    r = wcs.all_pix2world([[x, y]], 0)[0]
    return float(r[0]), float(r[1])


def world2pix(wcs, ra, de):
    r = wcs.all_world2pix([[ra, de]], 0)[0]
    return float(r[0]), float(r[1])


def pixel_scale(wcs, x, y):
    r0 = pix2world(wcs, x, y)
    r1 = pix2world(wcs, x + 1.0, y)
    r2 = pix2world(wcs, x, y + 1.0)
    return 0.5 * (tp.ang_sep_arcsec(r0[0], r0[1], r1[0], r1[1])
                  + tp.ang_sep_arcsec(r0[0], r0[1], r2[0], r2[1]))


def configure_tp(dur, inj_t):
    """Window geometry of the imported difference-image core, scaled to this transit."""
    tp.IN_HALF = IN_FRAC * dur
    tp.OUT_LO = OUT_LO_FRAC * dur
    tp.OUT_HI = OUT_HI_FRAC * dur
    tp.MIN_IN = MIN_PTS
    tp.MIN_OUT_SIDE = MIN_PTS
    tp.MASK_HALF = max(dur, 0.06)
    tp.MIN_ECL = 4
    tp.INJ_T = inj_t


# ---------------------------------------------------------------- light curves
def detrend(times, flux, t0, p, dur, chunk=DETREND_CHUNK, pad=MASK_PAD):
    """Divide by a baseline made of medians of out-of-transit points in `chunk`-day bins,
    linearly interpolated. Times must be increasing. Returns normalised flux (NaN if no base)."""
    half = 0.5 * dur + pad
    keep = [i for i, t in enumerate(times)
            if finite(flux[i]) and abs(tp.fold_dt(t, t0, p)) > half]
    if len(keep) < 2 * DETREND_MIN:
        raise ValueError("too few out-of-transit points")
    t_lo = times[keep[0]]
    groups = {}
    for i in keep:
        groups.setdefault(int((times[i] - t_lo) // chunk), []).append(i)
    nt, nf = [], []
    for k in sorted(groups):
        idx = groups[k]
        if len(idx) >= DETREND_MIN:
            nt.append(tp.median([times[i] for i in idx]))
            nf.append(tp.median([flux[i] for i in idx]))
    if not nt:
        raise ValueError("no detrending nodes")
    out = []
    for t, f in zip(times, flux):
        if t <= nt[0]:
            b = nf[0]
        elif t >= nt[-1]:
            b = nf[-1]
        else:
            j = bisect.bisect_right(nt, t)
            t1, t2, f1, f2 = nt[j - 1], nt[j], nf[j - 1], nf[j]
            b = f1 + (f2 - f1) * (t - t1) / (t2 - t1) if t2 > t1 else f1
        out.append(f / b if (finite(f) and b > 0) else NAN)
    return out


def epoch_offset(times, fn, t0, p, dur, half=REFINE_HALF, step=REFINE_STEP):
    """Best shift of the trapezoid (fixed P, duration) on normalised flux, grid +-half."""
    win = 0.5 * dur + half + 0.05
    pts = []
    for t, f in zip(times, fn):
        if finite(f):
            d = tp.fold_dt(t, t0, p)
            if abs(d) <= win:
                pts.append((d, 1.0 - f))
    outs = [r for d, r in pts if abs(d) > 0.5 * dur + half]
    sig = tp.std(outs)
    if len(pts) < 20 or not (finite(sig) and sig > 0):
        return None
    nstep = int(round(half / step))
    grid = []
    for k in range(-nstep, nstep + 1):
        off = k * step
        num = den = 0.0
        for d, r in pts:
            s = trap(d - off, dur)
            if s:
                num += r * s
                den += s * s
        if den <= 0:
            continue
        dep = num / den
        grid.append((off, dep, num * num / den / (sig * sig) if dep > 0 else 0.0))
    if not grid:
        return None
    bo, bd, bc = max(grid, key=lambda g: g[2])
    within = [g[0] for g in grid if g[2] >= bc - 1.0]
    err = max(0.5 * (max(within) - min(within)), step)
    return {"offset": bo, "sigma": err, "depth": bd, "dchi2": bc, "sigma_white": sig,
            "n": len(pts), "edge": abs(bo) >= half - 0.5 * step}


def fit_ephemeris(epochs, p0, t00):
    """Weighted line T = T0 + P n through per-sector epochs. T0 is returned at the cycle
    nearest the weighted mean (any epoch serves for the windows)."""
    good = [e for e in epochs if e and finite(e.get("t")) and finite(e.get("sigma"))
            and e["sigma"] > 0]
    if not good:
        return {"P": p0, "T0": t00, "status": "UNREFINED", "n_epochs": 0}
    ws = [1.0 / e["sigma"] ** 2 for e in good]
    sw = sum(ws)
    if len({e["n"] for e in good}) < 2:
        off = sum(w * (e["t"] - (t00 + e["n"] * p0)) for w, e in zip(ws, good)) / sw
        return {"P": p0, "T0": t00 + off, "sigma_T0": 1.0 / math.sqrt(sw), "status": "SHIFTED",
                "n_epochs": len(good)}
    mx = sum(w * e["n"] for w, e in zip(ws, good)) / sw
    my = sum(w * e["t"] for w, e in zip(ws, good)) / sw
    sxx = sum(w * (e["n"] - mx) ** 2 for w, e in zip(ws, good))
    pp = sum(w * (e["n"] - mx) * (e["t"] - my) for w, e in zip(ws, good)) / sxx
    if abs(pp - p0) > P_JUMP_MAX:
        off = sum(w * (e["t"] - (t00 + e["n"] * p0)) for w, e in zip(ws, good)) / sw
        return {"P": p0, "T0": t00 + off, "status": "FIT_REJECTED", "P_fit": pp,
                "n_epochs": len(good)}
    res = [e["t"] - (my + pp * (e["n"] - mx)) for e in good]
    dof = len(good) - 2
    chi2r = sum(w * r * r for w, r in zip(ws, res)) / dof if dof > 0 else 1.0
    scale = math.sqrt(max(chi2r, 1.0))
    n_ref = int(round(mx))
    t_ref = my + pp * (n_ref - mx)
    s_t = scale * math.sqrt(1.0 / sw + (n_ref - mx) ** 2 / sxx)
    return {"P": pp, "sigma_P": scale / math.sqrt(sxx), "T0": t_ref, "sigma_T0": s_t,
            "n_ref": n_ref, "chi2_red": chi2r, "status": "REFINED", "n_epochs": len(good)}


def event_depths(times, fn, t0, p, dur, phase_off):
    """Depth of every event at phase `phase_off`: local line through 0.6-1.4 durations on
    both sides, minus the mean in-window flux (|dt| <= 0.4 duration)."""
    if not times:
        return []
    ih, lo, hi = IN_FRAC * dur, OUT_LO_FRAC * dur, OUT_HI_FRAC * dur
    n0 = int(math.floor((times[0] - t0) / p)) - 1
    n1 = int(math.ceil((times[-1] - t0) / p)) + 1
    out = []
    for n in range(n0, n1 + 1):
        tc = t0 + (n + phase_off) * p
        i0 = bisect.bisect_left(times, tc - hi)
        i1 = bisect.bisect_right(times, tc + hi)
        ins, side = [], []
        nl = nr = 0
        for i in range(i0, i1):
            f = fn[i]
            if not finite(f):
                continue
            d = times[i] - tc
            if abs(d) <= ih:
                ins.append((d, f))
            elif lo <= abs(d) <= hi:
                side.append((d, f))
                if d < 0:
                    nl += 1
                else:
                    nr += 1
        if len(ins) >= MIN_PTS and nl >= MIN_PTS and nr >= MIN_PTS:
            a, b = tp.linfit([d for d, _ in side], [f for _, f in side])
            dep = sum((a + b * d) - f for d, f in ins) / len(ins)
            out.append({"n": n, "depth": dep, "n_in": len(ins)})
    return out


def aperture_around(r0, c0, ny, nx):
    return [i * nx + j for i in range(max(r0 - 1, 0), min(r0 + 2, ny))
            for j in range(max(c0 - 1, 0), min(c0 + 2, nx))]


# ---------------------------------------------------------------- stars
def gaia_pos(r, year):
    ra, de = float(r["ra"]), float(r["dec"])
    try:
        pmra, pmde = float(r["pmra"]), float(r["pmdec"])
    except (TypeError, ValueError, KeyError):
        pmra = pmde = 0.0
    dt = year - 2016.0
    return ra + pmra * dt / 3.6e6 / math.cos(math.radians(de)), de + pmde * dt / 3.6e6


def build_stars(rows, wcs, ny, nx, target_id, year):
    stars = []
    tid = str(target_id)
    for r in rows:
        sid = str(r.get("source_id"))
        try:
            rp = float(r["phot_rp_mean_mag"])
            ra, de = gaia_pos(r, year)
        except (TypeError, ValueError, KeyError):
            continue
        if rp >= tp.FAINT_RP and sid != tid:
            continue
        x, y = world2pix(wcs, ra, de)
        if -tp.EDGE_PAD <= x <= nx - 1 + tp.EDGE_PAD and -tp.EDGE_PAD <= y <= ny - 1 + tp.EDGE_PAD:
            try:
                g = float(r.get("phot_g_mean_mag") or "nan")
            except ValueError:
                g = NAN
            stars.append({"id": sid, "ra": ra, "dec": de, "rp": rp, "g": g, "x": x, "y": y,
                          "role": "other"})
    tg = [s for s in stars if s["id"] == tid]
    if not tg:
        raise RuntimeError("target %s not in the cutout's Gaia list" % tid)
    tg[0]["role"] = "T"
    return stars, tg[0]


def choose_neighbour(stars, tgt, depth_ref, nx, ny):
    """N for the two-source amplitude test: the brightest star 1-3 px from the target that
    could make the dip; else the brightest within 6 px; else the brightest in the cutout."""
    def ratio(s):
        return 10.0 ** (-0.4 * (s["rp"] - tgt["rp"]))

    def sep(s):
        return math.hypot(s["x"] - tgt["x"], s["y"] - tgt["y"])
    inside = [s for s in stars if s is not tgt and 1.0 <= s["x"] <= nx - 2.0
              and 1.0 <= s["y"] <= ny - 2.0 and sep(s) >= N_MIN_PX]
    cap = [s for s in inside if sep(s) <= N_RADIUS_PX and ratio(s) >= CAPABLE_MARGIN * depth_ref]
    pool = cap or [s for s in inside if sep(s) <= 2.0 * N_RADIUS_PX] or inside
    if not pool:
        return None
    return max(pool, key=ratio)


def star_table(rows, target_id, depth_ref, year, radius=NEAR_ARCSEC):
    """Every Gaia star within `radius` of the target: sky offset, RP flux ratio, the fraction
    of its own light it would have to lose, and whether it is capable of the dip."""
    tid = str(target_id)
    trow = [r for r in rows if str(r.get("source_id")) == tid]
    if not trow:
        return []
    rp_t = float(trow[0]["phot_rp_mean_mag"])
    ra0, de0 = gaia_pos(trow[0], year)
    out = []
    for r in rows:
        sid = str(r.get("source_id"))
        if sid == tid:
            continue
        try:
            rp = float(r["phot_rp_mean_mag"])
            ra, de = gaia_pos(r, year)
        except (TypeError, ValueError, KeyError):
            continue
        e, n = sky_offset(ra0, de0, ra, de)
        sep = math.hypot(e, n)
        if sep > radius:
            continue
        ratio = 10.0 ** (-0.4 * (rp - rp_t))
        out.append({"id": sid, "east": e, "north": n, "sep_arcsec": sep, "rp": rp,
                    "flux_ratio": ratio, "needed_own_depth": depth_ref / ratio,
                    "capable": ratio >= CAPABLE_MARGIN * depth_ref})
    out.sort(key=lambda s: s["sep_arcsec"])
    return out


# ---------------------------------------------------------------- labels
def combine_offsets(secs):
    use = [s for s in secs if s.get("sensitive") and s.get("offset")
           and finite(s["offset"].get("sigma")) and s["offset"]["sigma"] > 0]
    if len(use) < MIN_SECTORS:
        return {"label": "WS_UNTESTABLE", "n_sectors": len(use)}
    w = [1.0 / s["offset"]["sigma"] ** 2 for s in use]
    sw = sum(w)
    e = sum(wi * s["offset"]["east"] for wi, s in zip(w, use)) / sw
    n = sum(wi * s["offset"]["north"] for wi, s in zip(w, use)) / sw
    chi2 = sum(wi * ((s["offset"]["east"] - e) ** 2 + (s["offset"]["north"] - n) ** 2)
               for wi, s in zip(w, use))
    dof = 2 * (len(use) - 1)
    chi2r = chi2 / dof if dof > 0 else 1.0
    sig = math.sqrt(max(chi2r, 1.0)) / math.sqrt(sw)
    return {"east": e, "north": n, "sigma": sig, "chi2_red": chi2r, "n_sectors": len(use)}


def ws_label(comb, table):
    if comb.get("label") == "WS_UNTESTABLE":
        return dict(comb)
    e, n, sg = comb["east"], comb["north"], comb["sigma"]
    d_t = math.hypot(e, n) / sg
    near = []
    for s in table:
        s["d_sigma"] = math.hypot(e - s["east"], n - s["north"]) / sg
        if s["capable"] and s["d_sigma"] <= Z_POS:
            near.append(s["id"])
    if d_t <= Z_POS and not near:
        lab = "WS_ON_TARGET"
    elif d_t <= Z_POS:
        lab = "WS_UNRESOLVED"
    else:
        lab = "WS_OFF_TARGET"
    cap = [s for s in table if s["capable"]]
    best = min(cap, key=lambda s: s["d_sigma"]) if cap else None
    return {"label": lab, "d_target_sigma": d_t, "offset_arcsec": math.hypot(e, n),
            "east": e, "north": n, "sigma_arcsec": sg, "chi2_red": comb.get("chi2_red"),
            "n_sectors": comb.get("n_sectors"), "capable_within_3sigma": near,
            "closest_capable": ({"id": best["id"], "sep_arcsec": best["sep_arcsec"],
                                 "d_sigma": best["d_sigma"], "rp": best["rp"]} if best else None)}


def sec_label(sec, n25, n75):
    for nz in (n25.get("z"), n75.get("z")):
        if finite(nz) and abs(nz) >= SEC_Z:
            return "SEC_UNRELIABLE"
    z = sec.get("z")
    if not finite(z):
        return "SEC_UNTESTABLE"
    return "SEC_DETECTED" if z >= SEC_Z else "SEC_NOT_DETECTED"


def oe_label(odd, even):
    if not (finite(odd.get("mean")) and finite(even.get("mean"))):
        return "OE_UNTESTABLE", NAN
    s = math.hypot(odd["sigma"], even["sigma"])
    z = abs(odd["mean"] - even["mean"]) / s if s > 0 else NAN
    if not finite(z):
        return "OE_UNTESTABLE", NAN
    return ("OE_DIFFER" if z >= OE_Z else "OE_CONSISTENT"), z


def eb_flag(slab, sec, olab):
    if olab == "OE_DIFFER":
        return "EB_SUSPECT"
    if slab == "SEC_DETECTED" and (sec["mean"] - 2.0 * sec["sigma"]) * 1e6 > EB_SEC_PPM:
        return "EB_SUSPECT"
    return "EB_NOT_INDICATED"


def depth_label(d, s, ref):
    if not (finite(d) and finite(s) and ref > 0):
        return "DEPTH_UNTESTABLE"
    r = d / ref
    if (1.0 - DEPTH_TOL) <= r <= (1.0 + DEPTH_TOL) or abs(d - ref) <= 2.0 * s:
        return "DEPTH_CONSISTENT"
    return "DEPTH_SHALLOWER" if d < ref else "DEPTH_DEEPER"


# ---------------------------------------------------------------- one sector
def analyse_sector(times, frames, wcs, info, rows, cfg, eph, n_boot=N_BOOT,
                   n_boot_pos=N_BOOT_POS, maxiter=500, log=print):
    ny, nx = info["ny"], info["nx"]
    P, T0, dur = eph["P"], eph["T0"], cfg["dur_d"]
    year = epoch_year(times)
    stars, tgt = build_stars(rows, wcs, ny, nx, cfg["gaia_id"], year)
    out = {"n_frames": len(times), "year": year, "stars_in_model": len(stars),
           "target_px": [tgt["x"], tgt["y"]]}
    nb = choose_neighbour(stars, tgt, cfg["depth_ref"], nx, ny)
    if nb is None:
        out["status"] = "NO_NEIGHBOUR"
        return out, None
    nb["role"] = "N"
    out["neighbour"] = {"id": nb["id"], "rp": nb["rp"], "g": nb["g"],
                        "sep_px": math.hypot(nb["x"] - tgt["x"], nb["y"] - tgt["y"])}
    scale = pixel_scale(wcs, tgt["x"], tgt["y"])
    configure_tp(dur, cfg["depth_ref"])
    midx = tp.mean_image_index(times, T0, P)
    M = tp.frame_mean(frames, midx)
    mf = tp.fit_mean_image(M, stars, ny, nx, maxiter=maxiter, log=log)
    free = mf["free"]
    k_t = [k for k, s in enumerate(free) if s["role"] == "T"][0]
    k_n = [k for k, s in enumerate(free) if s["role"] == "N"][0]
    f_t, f_n = mf["coef"][k_t], mf["coef"][k_n]
    out["mean_fit"] = {"dx": mf["dx"], "dy": mf["dy"], "psf": list(mf["par"]), "chi2": mf["chi2"],
                       "n_free": mf["n_free"], "n_faint": mf["n_faint"], "flux_target": f_t,
                       "flux_neighbour": f_n, "arcsec_per_px": scale}
    if not (f_t > 0 and f_n > 0):
        out["status"] = "NEGATIVE_FLUX"
        return out, None
    col_t, col_n = mf["cols"][k_t], mf["cols"][k_n]
    pos_t = (free[k_t]["x"] + mf["dx"], free[k_t]["y"] + mf["dy"])
    pos_n = (free[k_n]["x"] + mf["dx"], free[k_n]["y"] + mf["dy"])
    w = mf["w"]
    c4 = tp.astrometric_control(M, mf, stars, ny, nx, log=log)
    out["C4_astrometry"] = {"n_used": c4["n_used"], "sigma_sys_px": c4["sigma_sys_px"]}
    common = dict(sig_sys=c4["sigma_sys_px"], ny=ny, nx=nx, n_boot=n_boot,
                  n_boot_pos=n_boot_pos, seed=SEED, log=log)
    W0 = tp.eclipse_windows(times, T0, P)
    W25 = tp.eclipse_windows(times, T0, P, 0.25)
    W75 = tp.eclipse_windows(times, T0, P, 0.75)
    out["n_windows"] = {"transit": len(W0), "phase_0.25": len(W25), "phase_0.75": len(W75)}
    if min(len(W0), len(W25), len(W75)) < tp.MIN_ECL:
        out["status"] = "UNTESTABLE"
        return out, None
    D0, D25, D75 = tp.diff_images(frames, W0), tp.diff_images(frames, W25), tp.diff_images(frames, W75)
    c1 = {}
    for tag, Ds in (("0.25", D25), ("0.75", D75)):
        r = tp.analyse_diffs(Ds, w, col_t, col_n, f_t, f_n, mf["par"], pos_t, pos_n,
                             do_pos=False, tag=tag, **common)
        c1[tag] = {"z_t": r.get("z_t"), "z_n": r.get("z_n"),
                   "pass": abs(r["z_t"]) < tp.Z_NULL and abs(r["z_n"]) < tp.Z_NULL}
    c1["pass"] = c1["0.25"]["pass"] and c1["0.75"]["pass"]
    out["C1_null"] = c1
    injN = [[d + tp.INJ_N * f_n * c for d, c in zip(D, col_n)] for D in D25]
    r2 = tp.analyse_diffs(injN, w, col_t, col_n, f_t, f_n, mf["par"], pos_t, pos_n, tag="C2",
                          **common)
    c2_pass = (r2["label"] == "PIX_ON_NEIGHBOUR"
               and abs(r2["delta_n"] - tp.INJ_N) <= tp.INJ_TOL * tp.INJ_N
               and r2["centroid"]["label"] == "CENTROID_ON_NEIGHBOUR")
    out["C2_inject_neighbour"] = {"label": r2["label"], "delta_n": r2["delta_n"],
                                  "centroid": r2["centroid"]["label"], "pass": c2_pass}
    injT = [[d + tp.INJ_T * f_t * c for d, c in zip(D, col_t)] for D in D75]
    r3 = tp.analyse_diffs(injT, w, col_t, col_n, f_t, f_n, mf["par"], pos_t, pos_n, tag="C3",
                          **common)
    c3_pass = (r3["label"] == "PIX_ON_TARGET"
               and abs(r3["delta_t"] - tp.INJ_T) <= tp.INJ_TOL * tp.INJ_T
               and r3["centroid"]["label"] == "CENTROID_ON_TARGET")
    out["C3_inject_target"] = {"label": r3["label"], "delta_t": r3["delta_t"],
                               "centroid": r3["centroid"]["label"], "pass": c3_pass}
    out["sensitive"] = bool(c1["pass"] and c2_pass and c3_pass)
    r = tp.analyse_diffs(D0, w, col_t, col_n, f_t, f_n, mf["par"], pos_t, pos_n, tag="A", **common)
    cen = r["centroid"]
    cx, cy = cen["x"] - mf["dx"], cen["y"] - mf["dy"]
    ra_c, de_c = pix2world(wcs, cx, cy)
    east, north = sky_offset(tgt["ra"], tgt["dec"], ra_c, de_c)
    sig_arc = scale * math.sqrt(0.5 * (cen["sigma_x"] ** 2 + cen["sigma_y"] ** 2))
    out["offset"] = {"east": east, "north": north, "sigma": sig_arc,
                     "offset_target_px": cen["offset_target_px"],
                     "d_target_sigma_px": cen["d_target_sigma"],
                     "d_neighbour_sigma_px": cen["d_neighbour_sigma"]}
    out["A"] = {k: r.get(k) for k in ("n_eclipses", "delta_t", "sigma_delta_t", "delta_n",
                                      "sigma_delta_n", "z_t", "z_n", "f_t", "f_t_lo", "f_t_hi")}
    out["L1_star"] = r["label"]
    out["L2_centroid"] = cen["label"]
    pk = max(range(ny * nx), key=lambda p: col_t[p])
    ap = aperture_around(pk // nx, pk % nx, ny, nx)
    m_ap = sum(M[p] for p in ap)
    frac = sum(f_t * col_t[p] for p in ap) / m_ap if m_ap > 0 else NAN
    out["aperture"] = {"centre": [pk // nx, pk % nx], "target_fraction": frac}
    dbar = [sum(v) / len(D0) for v in zip(*D0)]
    out["status"] = "OK"
    return out, {"dbar": dbar, "M": M, "ap": ap, "frac": frac, "nx": nx, "ny": ny,
                 "col_t": col_t, "f_t": f_t}


# ---------------------------------------------------------------- one target
def analyse_target(cfg, sectors, load, rows, n_boot=N_BOOT, n_boot_pos=N_BOOT_POS,
                   maxiter=500, log=print, keep_maps=False):
    res = {"name": cfg["name"], "role": cfg.get("role"), "gaia_id": cfg.get("gaia_id"),
           "sectors_requested": list(sectors)}
    P0, T00, dur = cfg["period"], cfg["t0_btjd"], cfg["dur_d"]
    epochs, s_ok, errs = [], [], {}
    for s in sectors:
        try:
            times, frames, wcs, info = load(s)
            if len(times) < 200:
                raise ValueError("only %d good cadences" % len(times))
            stars, tgt = build_stars(rows, wcs, info["ny"], info["nx"], cfg["gaia_id"],
                                     epoch_year(times))
            ap = aperture_around(int(round(tgt["y"])), int(round(tgt["x"])), info["ny"], info["nx"])
            fn = detrend(times, tp.aperture_series(frames, ap), T00, P0, dur)
            eo = epoch_offset(times, fn, T00, P0, dur)
            s_ok.append(s)
            if eo and eo["depth"] > 0 and eo["dchi2"] >= EPOCH_DCHI2 and not eo["edge"]:
                n = int(round((tp.median(times) - T00) / P0))
                epochs.append({"sector": s, "n": n, "t": T00 + n * P0 + eo["offset"],
                               "sigma": eo["sigma"], "depth_ap": eo["depth"], "dchi2": eo["dchi2"]})
            else:
                errs[str(s)] = "no epoch: %s" % (json.dumps(tp.clean_json(eo)) if eo else "none")
        except Exception as exc:  # noqa: BLE001
            errs[str(s)] = str(exc)[:300]
    eph = fit_ephemeris(epochs, P0, T00)
    res.update({"pass1_notes": errs, "epochs": epochs, "ephemeris": eph})
    log("[%s] ephemeris %s P %.7f T0 %.5f (%d epochs)" % (cfg["name"], eph["status"], eph["P"],
                                                         eph["T0"], eph["n_epochs"]))
    secs, maps = [], {}
    events = {"p": [], "s": [], "n25": [], "n75": []}
    for s in s_ok:
        try:
            times, frames, wcs, info = load(s)
            o, extra = analyse_sector(times, frames, wcs, info, rows, cfg, eph, n_boot=n_boot,
                                      n_boot_pos=n_boot_pos, maxiter=maxiter, log=log)
            o["sector"] = s
        except Exception as exc:  # noqa: BLE001
            o, extra = {"sector": s, "status": "ERROR", "error": str(exc)[:300]}, None
        if extra is not None:
            try:
                fn = detrend(times, tp.aperture_series(frames, extra["ap"]), eph["T0"], eph["P"], dur)
                frac = extra["frac"]
                for key, ph in (("p", 0.0), ("s", 0.5), ("n25", 0.25), ("n75", 0.75)):
                    for e in event_depths(times, fn, eph["T0"], eph["P"], dur, ph):
                        e["sector"] = s
                        e["depth_deb"] = e["depth"] / frac if (finite(frac) and frac > 0) else NAN
                        events[key].append(e)
            except Exception as exc:  # noqa: BLE001
                o["event_error"] = str(exc)[:300]
            if keep_maps:
                maps[s] = extra
        secs.append(o)
        log("[%s] sector %s %s sensitive %s L1 %s L2 %s offset %s" % (
            cfg["name"], s, o.get("status"), o.get("sensitive"), o.get("L1_star"),
            o.get("L2_centroid"), json.dumps(tp.clean_json(o.get("offset")))))
    res["sectors"] = secs
    sens = [o for o in secs if o.get("status") == "OK" and o.get("sensitive")]
    years = [o["year"] for o in sens] or [o["year"] for o in secs if "year" in o] or [2022.0]
    table = star_table(rows, cfg["gaia_id"], cfg["depth_ref"], sum(years) / len(years))
    ws = ws_label(combine_offsets(secs), table)
    res["WS"] = ws
    res["star_table"] = table[:40]
    res["n_capable_within_120"] = sum(1 for s in table if s["capable"])
    dm, ds, dn = wmean([o["A"]["delta_t"] for o in sens], [o["A"]["sigma_delta_t"] for o in sens])
    res["depth_psf"] = {"mean": dm, "sigma": ds, "n_sectors": dn}
    l1 = [o.get("L1_star") for o in sens]
    res["L1_counts"] = {k: l1.count(k) for k in sorted(set(l1))}
    ev = {k: summarize([e["depth_deb"] for e in v]) for k, v in events.items()}
    odd = summarize([e["depth_deb"] for e in events["p"] if e["n"] % 2 == 1])
    even = summarize([e["depth_deb"] for e in events["p"] if e["n"] % 2 == 0])
    slab = sec_label(ev["s"], ev["n25"], ev["n75"])
    olab, oz = oe_label(odd, even)
    res["events"] = {"transit": ev["p"], "secondary": ev["s"], "null_0.25": ev["n25"],
                     "null_0.75": ev["n75"], "odd": odd, "even": even, "odd_even_z": oz,
                     "secondary_3sigma_upper_ppm": (ev["s"]["mean"] + 3.0 * ev["s"]["sigma"]) * 1e6
                     if finite(ev["s"]["mean"]) else NAN}
    res["event_list"] = {k: [{"sector": e["sector"], "n": e["n"], "depth_deb": e["depth_deb"]}
                             for e in v] for k, v in events.items()}
    rad = None
    if finite(dm) and dm > 0 and cfg.get("rstar"):
        k = math.sqrt(dm)
        rad = {"k": k, "r_rjup_lo": k * cfg["rstar"][0] * R_SUN_RJUP,
               "r_rjup_hi": k * cfg["rstar"][1] * R_SUN_RJUP}
    res["radius"] = rad
    res["labels"] = {"WS": ws.get("label"), "L1_majority": max(res["L1_counts"],
                     key=res["L1_counts"].get) if l1 else None,
                     "DEPTH": depth_label(dm, ds, cfg.get("depth_flat", cfg["depth_ref"])),
                     "SEC": slab, "OE": olab, "EB": eb_flag(slab, ev["s"], olab),
                     "n_sensitive_sectors": len(sens)}
    return res, maps


# ---------------------------------------------------------------- I/O (job only)
def nasa_ephem(name):
    q = ("select pl_name,ra,dec,pl_orbper,pl_tranmid,pl_trandur,pl_trandep from pscomppars "
         "where pl_name='%s'" % name.replace("'", ""))
    url = NASA_TAP + "?" + urllib.parse.urlencode({"query": q, "format": "csv"})
    rows = list(csv.DictReader(io.StringIO(tp.http_get(url, timeout=120).decode("utf-8", "replace"))))
    if not rows:
        raise RuntimeError("no archive row for %s" % name)
    r = rows[0]
    dep = float(r["pl_trandep"]) / 100.0
    return {"ra": float(r["ra"]), "dec": float(r["dec"]), "period": float(r["pl_orbper"]),
            "t0_btjd": float(r["pl_tranmid"]) - 2457000.0, "dur_d": float(r["pl_trandur"]) / 24.0,
            "depth_ref": dep, "depth_flat": dep}


def fetch_gaia_rows(ra, dec, path, log=print):
    if os.path.exists(path) and os.path.getsize(path) > 200:
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    last = None
    for url, tab in GAIA_TAPS:
        q = ("SELECT source_id, ra, dec, pmra, pmdec, phot_g_mean_mag, phot_rp_mean_mag FROM %s "
             "WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',%.6f,%.6f,%.4f)) "
             "AND phot_rp_mean_mag < %.1f" % (tab, ra, dec, GAIA_RADIUS_DEG, LIST_RP_MAX))
        body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                       "QUERY": q}).encode()
        try:
            text = tp.http_get(url, timeout=180, data=body).decode("utf-8", "replace")
            rows = list(csv.DictReader(io.StringIO(text)))
            if rows and "source_id" in rows[0]:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                log("[gaia] %d stars from %s" % (len(rows), url))
                return rows
            last = "empty answer from %s" % url
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError("Gaia query failed: %s" % last)


def resolve_gaia_id(rows, ra, dec, radius=5.0):
    best = None
    for r in rows:
        try:
            sep = tp.ang_sep_arcsec(ra, dec, float(r["ra"]), float(r["dec"]))
            rp = float(r["phot_rp_mean_mag"])
        except (TypeError, ValueError, KeyError):
            continue
        if sep <= radius and rp < 15.0 and (best is None or rp < best[1]):
            best = (str(r["source_id"]), rp)
    if best is None:
        raise RuntimeError("no Gaia star brighter than RP 15 within %.0f arcsec" % radius)
    return best[0]


def tesscut_sectors(ra, dec):
    url = TESSCUT_SECTORS + "?" + urllib.parse.urlencode({"ra": ra, "dec": dec, "radius": "0m"})
    js = json.loads(tp.http_get(url, timeout=120).decode("utf-8", "replace"))
    return sorted({int(r["sector"]) for r in js.get("results", [])})


def fetch_cutout(ra, dec, sector, data_dir, tag, log=print):
    path = os.path.join(data_dir, "%s_s%04d_%dx%d.fits" % (tag, sector, CUT, CUT))
    if os.path.exists(path) and os.path.getsize(path) > 100000:
        return path
    q = urllib.parse.urlencode({"ra": ra, "dec": dec, "y": CUT, "x": CUT, "sector": sector})
    blob = tp.http_get(TESSCUT + "?" + q)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = [n for n in z.namelist() if n.endswith(".fits")]
        if not names:
            raise RuntimeError("TESScut zip has no FITS file")
        with open(path, "wb") as f:
            f.write(z.read(names[0]))
    log("[fetch] %s sector %d (%d bytes)" % (tag, sector, os.path.getsize(path)))
    return path


def prepare_target(cfg, data_dir, log=print):
    tag = slug(cfg["name"])
    if cfg.get("nasa_name"):
        try:
            cfg.update(nasa_ephem(cfg["nasa_name"]))
            cfg["ephem_source"] = "NASA Exoplanet Archive pscomppars"
        except Exception as exc:  # noqa: BLE001
            cfg["ephem_source"] = "config fallback (%s)" % str(exc)[:200]
    rows = fetch_gaia_rows(cfg["ra"], cfg["dec"], os.path.join(data_dir, tag + "_gaia.csv"), log=log)
    if not cfg.get("gaia_id"):
        cfg["gaia_id"] = resolve_gaia_id(rows, cfg["ra"], cfg["dec"])
    sectors = cfg.get("sectors")
    if not sectors:
        sectors = tesscut_sectors(cfg["ra"], cfg["dec"])[-int(cfg.get("max_sectors", 3)):]
    paths = {}
    for s in sectors:
        try:
            paths[s] = fetch_cutout(cfg["ra"], cfg["dec"], s, data_dir, tag, log=log)
        except Exception as exc:  # noqa: BLE001
            cfg.setdefault("fetch_errors", {})[str(s)] = str(exc)[:300]
    if not paths:
        raise RuntimeError("no TESScut cutout for %s" % cfg["name"])
    cfg["_rows"] = rows
    cfg["_paths"] = paths
    cfg["sectors_used"] = sorted(paths)
    return cfg


# ---------------------------------------------------------------- self-test
ST_P, ST_T0, ST_DUR = 2.1, 1000.7, 0.125


def synth_sector(seed, dip_id, depth, rot_deg, sec_depth=0.0, days=12.0, cad=0.01,
                 t_start=1000.0, shift=(0.2, -0.15)):
    """Synthetic 11x11 cutout: target T, a neighbour N 1.9 px away (half as bright), a faint
    star and a bright star 3.9 px away; Poisson-like noise; WCS off by `shift` pixels."""
    rng = random.Random(seed)
    ny = nx = 11
    ra0, dec0 = 150.0, -40.0
    wcs = FakeWCS(ra0, dec0, 5.0, 5.0, 21.0, rot_deg)
    par = (0.75, 0.68, 0.1, 0.1)
    cosd = math.cos(math.radians(dec0))

    def at(e_px, n_px):
        return ra0 + e_px * 21.0 / 3600.0 / cosd, dec0 + n_px * 21.0 / 3600.0
    truth = [("T", at(0.1, 0.2), 200000.0, 10.0), ("N", at(2.0, 0.3), 100000.0, 10.7526),
             ("a", at(-0.9, -2.6), 8000.0, 13.5), ("b", at(-3.0, 2.5), 300000.0, 9.5598)]
    rows = [{"source_id": sid, "ra": "%.9f" % ra, "dec": "%.9f" % de, "pmra": "", "pmdec": "",
             "phot_g_mean_mag": "%.4f" % (rp + 0.4), "phot_rp_mean_mag": "%.4f" % rp}
            for sid, (ra, de), _, rp in truth]
    tmpl = {}
    for sid, (ra, de), _, _ in truth:
        x, y = world2pix(wcs, ra, de)
        tmpl[sid] = tp.psf_template(x + shift[0], y + shift[1], ny, nx, par)
    times, frames = [], []
    t = t_start
    while t < t_start + days:
        img = [50.0] * (ny * nx)
        for sid, _, f, _ in truth:
            ff = f
            if sid == dip_id:
                ff *= 1.0 - depth * trap(tp.fold_dt(t, ST_T0, ST_P), ST_DUR)
            if sid == "T" and sec_depth:
                ff *= 1.0 - sec_depth * trap(tp.fold_dt(t, ST_T0 + 0.5 * ST_P, ST_P), ST_DUR)
            img = [a + ff * b for a, b in zip(img, tmpl[sid])]
        img = [v + rng.gauss(0.0, math.sqrt(max(v, 1.0))) for v in img]
        times.append(t)
        frames.append(img)
        t += cad
    info = {"ny": ny, "nx": nx, "n_cadences": len(times), "n_good": len(times),
            "t_first": times[0], "t_last": times[-1]}
    return times, frames, wcs, info, rows


def self_test(log=print):
    q = lambda s: None  # noqa: E731
    checks = {}
    w = FakeWCS(150.0, -40.0, 5.0, 5.0, 21.0, 30.0)
    ra, de = pix2world(w, 7.3, 2.1)
    x, y = world2pix(w, ra, de)
    checks["wcs_roundtrip"] = abs(x - 7.3) < 1e-6 and abs(y - 2.1) < 1e-6
    checks["wcs_scale"] = abs(pixel_scale(w, 5.0, 5.0) - 21.0) < 0.01
    cfg = {"name": "synthetic", "role": "selftest", "gaia_id": "T", "period": ST_P,
           "t0_btjd": ST_T0, "dur_d": ST_DUR, "depth_ref": 0.01, "depth_flat": 0.01,
           "rstar": [1.0, 1.0]}
    cases = {}
    for case, dip, depth, sec in (("A", "T", 0.01, 0.004), ("B", "N", 0.08, 0.0)):
        data, rows = {}, None
        for k, (s, rot, t0s) in enumerate(((1, 0.0, 1000.0), (2, 90.0, 1100.0))):
            times, frames, wcs, info, rows = synth_sector(11 + 10 * len(cases) + k, dip, depth,
                                                          rot, sec_depth=sec, t_start=t0s)
            data[s] = (times, frames, wcs, info)
        res, _ = analyse_target(dict(cfg), [1, 2], lambda s, d=data: d[s], rows, n_boot=60,
                                n_boot_pos=15, maxiter=400, log=q)
        cases[case] = res
        log("[self-test] case %s labels %s depth %s ephem %s" % (
            case, json.dumps(tp.clean_json(res.get("labels"))),
            json.dumps(tp.clean_json(res.get("depth_psf"))),
            json.dumps(tp.clean_json(res.get("ephemeris")))))
    a, b = cases["A"], cases["B"]
    la, lb = a.get("labels", {}), b.get("labels", {})
    checks["A_two_sensitive_sectors"] = la.get("n_sensitive_sectors") == 2
    checks["A_on_target"] = la.get("WS") == "WS_ON_TARGET"
    checks["A_depth"] = finite(a["depth_psf"]["mean"]) and abs(a["depth_psf"]["mean"] - 0.01) < 0.0015
    checks["A_secondary"] = la.get("SEC") == "SEC_DETECTED"
    checks["A_odd_even"] = la.get("OE") == "OE_CONSISTENT"
    checks["A_ephem"] = abs(a["ephemeris"]["P"] - ST_P) < 1e-3
    checks["B_off_target"] = lb.get("WS") == "WS_OFF_TARGET"
    ok = True
    for k, v in checks.items():
        log("[self-test] %-24s %s" % (k, "ok" if v else "FAIL"))
        ok = ok and bool(v)
    return ok


# ---------------------------------------------------------------- main
def report(summary):
    lines = ["# pixel_which_star %s report" % VERSION, "",
             "- Controls: **%s**" % summary.get("controls"),
             "- Graded: **%s**" % summary.get("graded"), ""]
    for r in summary.get("targets", []):
        L = r.get("labels", {})
        ws = r.get("WS", {})
        lines.append("## %s (%s)" % (r.get("name"), r.get("role")))
        lines.append("- status: %s" % r.get("status", "ok"))
        lines.append("- WS: **%s**; offset %s arcsec, sigma %s arcsec, d_target %s sigma, "
                     "capable stars within 3 sigma: %s" % (
                         L.get("WS"), _f(ws.get("offset_arcsec")), _f(ws.get("sigma_arcsec")),
                         _f(ws.get("d_target_sigma")), ws.get("capable_within_3sigma")))
        lines.append("- L1 counts %s; DEPTH %s (%s +- %s); SEC %s; OE %s; EB %s" % (
            r.get("L1_counts"), L.get("DEPTH"), _f(r.get("depth_psf", {}).get("mean"), 5),
            _f(r.get("depth_psf", {}).get("sigma"), 5), L.get("SEC"), L.get("OE"), L.get("EB")))
        lines.append("- ephemeris: %s" % json.dumps(tp.clean_json(r.get("ephemeris"))))
        for o in r.get("sectors", []):
            lines.append("  - sector %s: %s sensitive %s L1 %s L2 %s offset %s" % (
                o.get("sector"), o.get("status"), o.get("sensitive"), o.get("L1_star"),
                o.get("L2_centroid"), json.dumps(tp.clean_json(o.get("offset")))))
        lines.append("")
    return "\n".join(lines) + "\n"


def _f(x, nd=2):
    return ("%." + str(nd) + "f") % x if finite(x) else str(x)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--config", default="targets.json")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args(argv)
    if a.self_test:
        ok = self_test()
        print("SELF_TEST_OK" if ok else "SELF_TEST_FAILED")
        return 0 if ok else 3
    with open(a.config, "r", encoding="utf-8") as f:
        conf = json.load(f)
    os.makedirs(a.data_dir, exist_ok=True)
    os.makedirs(a.out_dir, exist_ok=True)
    summary = {"version": VERSION, "tyc_pixel_version": tp.VERSION, "targets": [],
               "stage": "start"}
    path = os.path.join(a.out_dir, "pws_summary.json")

    def save():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tp.clean_json(summary), f, indent=1, default=str)

    for cfg in conf["targets"]:
        try:
            prepare_target(cfg, a.data_dir)
        except Exception as exc:  # noqa: BLE001
            summary["targets"].append({"name": cfg.get("name"), "role": cfg.get("role"),
                                       "status": "FETCH_FAILED", "error": str(exc)[:300]})
            save()
            print("FETCH_FAILED", cfg.get("name"), exc)
            continue
        paths = cfg["_paths"]
        res, maps = analyse_target(cfg, cfg["sectors_used"], lambda s, p=paths: tp.read_tesscut(p[s]),
                                   cfg["_rows"], keep_maps=(cfg.get("role") == "target"))
        res["config"] = {k: v for k, v in cfg.items() if not k.startswith("_")}
        summary["targets"].append(res)
        for s, m in maps.items():
            fn = os.path.join(a.out_dir, "pws_diffmap_%s_s%04d.csv" % (slug(cfg["name"]), s))
            with open(fn, "w", encoding="utf-8") as f:
                f.write("row,col,mean_flux,diff_flux,frac_depth,target_model_frac\n")
                for p in range(m["ny"] * m["nx"]):
                    mv, dv = m["M"][p], m["dbar"][p]
                    tf = m["f_t"] * m["col_t"][p] / mv if mv > 0 else NAN
                    f.write("%d,%d,%.3f,%.4f,%.6f,%.4f\n" % (p // m["nx"], p % m["nx"], mv, dv,
                                                            dv / mv if mv > 0 else NAN, tf))
        summary["stage"] = "after %s" % cfg["name"]
        save()
    ctrl = [r for r in summary["targets"] if r.get("role") == "control"]
    n_ctrl = sum(1 for c in conf["targets"] if c.get("role") == "control")
    # a control passes when the transit centroid does not exclude the known host
    summary["controls"] = ("CONTROLS_PASS" if ctrl and len(ctrl) == n_ctrl and all(
        r.get("labels", {}).get("WS") in CONTROL_OK for r in ctrl) else "CONTROLS_FAIL")
    tg = [r for r in summary["targets"] if r.get("role") == "target"]
    summary["graded"] = bool(summary["controls"] == "CONTROLS_PASS" and tg
                             and tg[0].get("labels", {}).get("WS") not in (None, "WS_UNTESTABLE"))
    summary["stage"] = "done"
    save()
    with open(os.path.join(a.out_dir, "pws_report.md"), "w", encoding="utf-8") as f:
        f.write(report(summary))
    print(json.dumps({"controls": summary["controls"], "graded": summary["graded"],
                      "labels": {r.get("name"): r.get("labels") for r in summary["targets"]}},
                     default=str))
    return 0 if (tg and tg[0].get("labels")) else 4


if __name__ == "__main__":
    sys.exit(main())
