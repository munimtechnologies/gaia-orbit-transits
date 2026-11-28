# SPDX-License-Identifier: Apache-2.0
"""pix_vet 0.1.0 - which star in the TESS pixels makes the eclipse?

gaia-orbit-transits, MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name.
Apache-2.0. Pre-registration: findings/2026-11-28-tier2-pixel-prereg.md (written before this job ran).

For each configured star and TESS sector: download a 15x15 TESScut full-frame cutout, cut out the frames
inside each eclipse (|t - tc| < 0.35 dur) and next to it (0.75 dur < |t - tc| < 0.75 dur + 0.5 d, on both
sides), and form the mean difference image D = out - in over all events. A Gaussian-PSF model of the
direct image (target + listed neighbours + constant; common WCS offset and PSF width fitted on a grid)
gives each star's footprint. D is then fitted with the target alone (model T), the neighbour alone
(model N) and both (model J), weighted by the event-to-event pixel scatter.
dchi2 = chi2_N - chi2_T, summed over sectors (> 0 favours the target).

Verdict (frozen):
  ON_TARGET     dchi2 >= 9 and the target-only amplitude >= 3 sigma
  ON_NEIGHBOUR  dchi2 <= -9 and the neighbour-only amplitude >= 3 sigma
  NO_SIGNAL     neither amplitude >= 3 sigma
  UNRESOLVED    otherwise;  INSUFFICIENT if fewer than 3 usable events.
Controls: the same code on the same cubes with a synthetic eclipse injected on the neighbour (expect
ON_NEIGHBOUR) and on the target (expect ON_TARGET) at a fake phase 0.23, and a catalogued eclipsing
binary with a fake neighbour position (expect ON_TARGET).

Usage: python pix_vet.py --config pix_targets.json --data-dir /data/pix --out-dir /out
"""
import argparse
import io
import json
import math
import os
import sys
import time
import urllib.request
import zipfile

import numpy as np

VERSION = "0.1.0"
UA = "gaia-orbit-transits-pix-vet/0.1 (open research script)"
TESSCUT = "https://mast.stsci.edu/tesscut/api/v0.1"
CUT = 15
DCHI2 = 9.0
ZSIG = 3.0
FIT_RADIUS = 3.5
S_GRID = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.35, 1.5, 1.7]
D_GRID = [round(-1.0 + 0.1 * i, 2) for i in range(21)]
SHIFTS = [round(-0.15 + 0.01 * i, 3) for i in range(31)]
FAKE_PHASE = 0.23


def fetch(url, timeout=600):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def sectors_for(ra, dec):
    js = json.loads(fetch("%s/sector?ra=%.6f&dec=%.6f&radius=0m" % (TESSCUT, ra, dec), 120))
    return sorted({int(r["sector"]) for r in js.get("results", [])})


def load_cutout(ra, dec, sector, data_dir):
    """-> (t, flux cube [n, ny, nx], quality, wcs). Cached as the TESScut zip under data_dir."""
    from astropy.io import fits
    from astropy.wcs import WCS
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "cut_%.5f_%+.5f_s%04d.zip" % (ra, dec, sector))
    if not os.path.exists(path):
        blob = fetch("%s/astrocut?ra=%.6f&dec=%.6f&y=%d&x=%d&sector=%d"
                     % (TESSCUT, ra, dec, CUT, CUT, sector), 1800)
        tmp = path + ".part"
        with open(tmp, "wb") as fh:
            fh.write(blob)
        os.replace(tmp, path)
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".fits")]
        if not names:
            raise RuntimeError("no FITS in TESScut zip for sector %d" % sector)
        raw = zf.read(names[0])
    with fits.open(io.BytesIO(raw)) as hd:
        d = hd[1].data
        t = np.array(d["TIME"], dtype=float)
        f = np.array(d["FLUX"], dtype=float)
        q = np.array(d["QUALITY"], dtype=int)
        w = WCS(hd[2].header)
    return t, f, q, w


def clean(t, f, q):
    """Good frames only, each frame minus a robust background (15th percentile of its pixels)."""
    f = f.copy()
    dead = ~np.any(np.isfinite(f), axis=0)          # pixels off the CCD in every frame
    f[:, dead] = 0.0
    good = (q == 0) & np.isfinite(t) & np.all(np.isfinite(f.reshape(len(t), -1)), axis=1)
    t, f = t[good], f[good]
    bkg = np.nanpercentile(f.reshape(len(t), -1), 15, axis=1)
    return t, f - bkg[:, None, None]


def gauss(shape, x0, y0, s):
    yy, xx = np.indices(shape)
    return np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / (2.0 * s * s))


def fit_mask(shape, x0, y0, r=FIT_RADIUS):
    yy, xx = np.indices(shape)
    return (xx - x0) ** 2 + (yy - y0) ** 2 <= r * r


def fit_direct(img, pos, mask):
    """Least squares img = sum_i A_i G(pos_i + offset, s) + C over the mask, grid over offset and s.
    -> dict(dx, dy, s, coef, chi2)."""
    best = None
    y = img[mask]
    for s in S_GRID:
        for dx in D_GRID:
            for dy in D_GRID:
                cols = [gauss(img.shape, x + dx, yv + dy, s)[mask] for x, yv in pos]
                cols.append(np.ones(int(mask.sum())))
                m = np.vstack(cols).T
                coef = np.linalg.lstsq(m, y, rcond=None)[0]
                r = y - m @ coef
                c2 = float(r @ r)
                if best is None or c2 < best["chi2"]:
                    best = {"dx": dx, "dy": dy, "s": s, "coef": coef.tolist(), "chi2": c2}
    return best


def wls(cols, y, sd):
    """Weighted least squares -> (coef, sigma, chi2)."""
    m = np.vstack(cols).T
    w = 1.0 / sd
    mw = m * w[:, None]
    yw = y * w
    coef = np.linalg.lstsq(mw, yw, rcond=None)[0]
    r = yw - mw @ coef
    cov = np.linalg.pinv(mw.T @ mw)
    return coef, np.sqrt(np.clip(np.diag(cov), 0, None)), float(r @ r)


def events(t, f, t0, period, dur, shift=0.0):
    """-> list of (out_img, in_img) per usable eclipse event."""
    half_in, lo, hi = 0.35 * dur, 0.75 * dur, 0.75 * dur + 0.5
    k0 = int(math.floor((t.min() - t0) / period)) - 1
    k1 = int(math.ceil((t.max() - t0) / period)) + 1
    out = []
    for k in range(k0, k1 + 1):
        dt = t - (t0 + k * period + shift)
        ii = np.abs(dt) < half_in
        oo = (np.abs(dt) > lo) & (np.abs(dt) < hi)
        if ii.sum() < 3 or (oo & (dt < 0)).sum() < 3 or (oo & (dt > 0)).sum() < 3:
            continue
        out.append((np.median(f[oo], axis=0), np.median(f[ii], axis=0)))
    return out


def best_shift(t, f, t0, period, dur, ap):
    """Refine the eclipse time within +-0.15 d by the deepest mean fractional dip in an aperture that
    holds every listed star (so the choice does not favour one star)."""
    best = (0.0, -np.inf, 0)
    for sh in SHIFTS:
        ev = events(t, f, t0, period, dur, sh)
        if not ev:
            continue
        dip = np.mean([(o[ap].sum() - i[ap].sum()) / o[ap].sum() for o, i in ev])
        if dip > best[1]:
            best = (sh, float(dip), len(ev))
    return best


def inject(t, f, model_img, frac, t0, period, dur):
    """Box eclipse of depth frac * model_img at every event of the (fake) ephemeris."""
    ph = ((t - t0) / period + 0.5) % 1.0 - 0.5
    inside = np.abs(ph * period) < 0.5 * dur
    g = f.copy()
    g[inside] -= frac * model_img[None, :, :]
    return g


def analyse_sector(t, f, tpos, npos, t0, period, dur, fake_neighbour=False):
    """One sector -> dict with dchi2, amplitudes and their sigmas, or {'skip': reason}."""
    shape = f.shape[1:]
    mask = fit_mask(shape, tpos[0], tpos[1])
    direct = np.median(f, axis=0)
    dfit = fit_direct(direct, [tpos, npos], mask)
    dx, dy, s = dfit["dx"], dfit["dy"], dfit["s"]
    gt = gauss(shape, tpos[0] + dx, tpos[1] + dy, s)
    gn = gauss(shape, npos[0] + dx, npos[1] + dy, s)
    amp_t, amp_n = dfit["coef"][0], dfit["coef"][1]
    ap = fit_mask(shape, (tpos[0] + npos[0]) / 2.0, (tpos[1] + npos[1]) / 2.0, 3.0)
    sh, dip, _ = best_shift(t, f, t0, period, dur, ap)
    ev = events(t, f, t0, period, dur, sh)
    if len(ev) < 2:
        return {"skip": "fewer than 2 events", "n_events": len(ev)}
    dk = np.array([o - i for o, i in ev])
    dmean = dk.mean(axis=0)
    sd = dk.std(axis=0, ddof=1) / math.sqrt(len(ev))
    sdm = sd[mask]
    floor = 0.5 * float(np.median(sdm))
    sdm = np.maximum(sdm, floor if floor > 0 else 1e-9)
    y = dmean[mask]
    one = np.ones(int(mask.sum()))
    ct, st, c2t = wls([gt[mask], one], y, sdm)
    cn, sn, c2n = wls([gn[mask], one], y, sdm)
    cj, sj, c2j = wls([gt[mask], gn[mask], one], y, sdm)
    res = {
        "n_events": len(ev), "shift_d": sh, "shift_at_edge": abs(sh) >= 0.15 - 1e-9,
        "aperture_dip": dip, "psf_sigma_px": s, "offset_px": [dx, dy],
        "direct_amp_target": amp_t, "direct_amp_neighbour": amp_n,
        "chi2_T": c2t, "chi2_N": c2n, "chi2_J": c2j, "dchi2": c2n - c2t, "n_pix": int(mask.sum()),
        "a_T": float(ct[0]), "a_T_sig": float(st[0]), "b_N": float(cn[0]), "b_N_sig": float(sn[0]),
        "f_target_joint": float(cj[0] / amp_t) if amp_t > 0 else None,
        "f_neighbour_joint": (None if fake_neighbour or amp_n <= 0 else float(cj[1] / amp_n)),
    }
    return res


def verdict(secs):
    used = [r for r in secs if "skip" not in r]
    n_ev = sum(r["n_events"] for r in used)
    if n_ev < 3:
        return {"label": "INSUFFICIENT", "n_events": n_ev, "n_sectors": len(used)}
    dchi2 = sum(r["dchi2"] for r in used)

    def comb(key, skey):
        w = [1.0 / r[skey] ** 2 for r in used if r[skey] > 0]
        v = [r[key] / r[skey] ** 2 for r in used if r[skey] > 0]
        return (sum(v) / math.sqrt(sum(w))) if w else 0.0
    z_t, z_n = comb("a_T", "a_T_sig"), comb("b_N", "b_N_sig")
    if dchi2 >= DCHI2 and z_t >= ZSIG:
        lab = "ON_TARGET"
    elif dchi2 <= -DCHI2 and z_n >= ZSIG:
        lab = "ON_NEIGHBOUR"
    elif z_t < ZSIG and z_n < ZSIG:
        lab = "NO_SIGNAL"
    else:
        lab = "UNRESOLVED"
    return {"label": lab, "dchi2": dchi2, "z_target": z_t, "z_neighbour": z_n,
            "n_events": n_ev, "n_sectors": len(used)}


def offset_radec(ra, dec, d_ra_arcsec, d_dec_arcsec):
    return (ra + d_ra_arcsec / 3600.0 / math.cos(math.radians(dec)), dec + d_dec_arcsec / 3600.0)


def run_star(cfg, data_dir, max_sectors, log):
    ra, dec = cfg["ra"], cfg["dec"]
    if cfg.get("neighbour"):
        nra, ndec = cfg["neighbour"]["ra"], cfg["neighbour"]["dec"]
        fake = False
    else:
        nra, ndec = offset_radec(ra, dec, *cfg["fake_neighbour_offset_arcsec"])
        fake = True
    t0, period, dur = cfg["t0_btjd"], cfg["period_d"], cfg["dur_d"]
    out = {"name": cfg["name"], "role": cfg["role"], "fake_neighbour": fake, "sectors": {},
           "injections": {}}
    try:
        secs = sectors_for(ra, dec)
    except Exception as exc:  # noqa: BLE001
        out["error"] = "sector list: %r" % exc
        return out
    out["sectors_available"] = secs
    pref = [s for s in cfg.get("sectors_prefer", []) if s in secs]
    secs = pref + [s for s in secs if s not in pref]
    real, inj_n, inj_t = [], [], []
    used = 0
    for sec in secs:
        if used >= max_sectors:
            break
        try:
            t, f, q, w = load_cutout(ra, dec, sec, data_dir)
        except Exception as exc:  # noqa: BLE001
            out["sectors"][str(sec)] = {"skip": "download: %r" % exc}
            log("  %s s%d download failed: %r" % (cfg["name"], sec, exc))
            continue
        t, f = clean(t, f, q)
        if len(t) < 100:
            out["sectors"][str(sec)] = {"skip": "too few good frames"}
            continue
        tx, ty = [float(v) for v in w.all_world2pix([[ra, dec]], 0)[0]]
        nx, ny = [float(v) for v in w.all_world2pix([[nra, ndec]], 0)[0]]
        r = analyse_sector(t, f, (tx, ty), (nx, ny), t0, period, dur, fake)
        r["target_px"], r["neighbour_px"] = [tx, ty], [nx, ny]
        out["sectors"][str(sec)] = r
        if "skip" in r:
            continue
        used += 1
        real.append(r)
        log("  %s s%d: %d events, dchi2 %.1f, a_T %.3g+-%.2g, b_N %.3g+-%.2g"
            % (cfg["name"], sec, r["n_events"], r["dchi2"], r["a_T"], r["a_T_sig"], r["b_N"], r["b_N_sig"]))
        if cfg.get("inject") and not fake:
            shape = f.shape[1:]
            gt = gauss(shape, tx + r["offset_px"][0], ty + r["offset_px"][1], r["psf_sigma_px"])
            gn = gauss(shape, nx + r["offset_px"][0], ny + r["offset_px"][1], r["psf_sigma_px"])
            at, an = r["direct_amp_target"], r["direct_amp_neighbour"]
            depth = cfg["depth_obs"]
            t0f = t0 + FAKE_PHASE * period
            if an > 0:
                fn = min(0.5, depth * (at + an) / an)
                g = inject(t, f, an * gn, fn, t0f, period, dur)
                rn = analyse_sector(t, g, (tx, ty), (nx, ny), t0f, period, dur)
                rn["inj_frac"] = fn
                inj_n.append(rn)
                out["injections"].setdefault("neighbour", {})[str(sec)] = rn
            if at > 0:
                ft = min(0.5, depth * (at + an) / at)
                g = inject(t, f, at * gt, ft, t0f, period, dur)
                rt = analyse_sector(t, g, (tx, ty), (nx, ny), t0f, period, dur)
                rt["inj_frac"] = ft
                inj_t.append(rt)
                out["injections"].setdefault("target", {})[str(sec)] = rt
    out["verdict"] = verdict(real)
    if cfg.get("inject") and not fake:
        out["verdict_inject_neighbour"] = verdict(inj_n)
        out["verdict_inject_target"] = verdict(inj_t)
    return out


def grade(results):
    by = {r["name"]: r for r in results}
    g = {}
    for r in results:
        if r["role"] == "target":
            g["C1_inject_neighbour"] = r.get("verdict_inject_neighbour", {}).get("label")
            g["C2_inject_target"] = r.get("verdict_inject_target", {}).get("label")
            g["M_target"] = r.get("verdict", {}).get("label")
            g["target_name"] = r["name"]
        elif r["role"] == "control":
            g["C3_known_eb"] = r.get("verdict", {}).get("label")
    g["controls_ok"] = (g.get("C1_inject_neighbour") == "ON_NEIGHBOUR"
                        and g.get("C2_inject_target") == "ON_TARGET"
                        and g.get("C3_known_eb") == "ON_TARGET")
    g["n_stars"] = len(by)
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="pix_targets.json")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--max-sectors", type=int, default=4)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    with open(a.config) as fh:
        cfg = json.load(fh)

    def log(msg):
        print(msg, flush=True)
    res = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "stars": []}
    for star in cfg["stars"]:
        log("star %s (%s)" % (star["name"], star["role"]))
        try:
            res["stars"].append(run_star(star, a.data_dir, a.max_sectors, log))
        except Exception as exc:  # noqa: BLE001
            res["stars"].append({"name": star["name"], "role": star["role"], "error": repr(exc)})
    res["grade"] = grade(res["stars"])
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(a.out_dir, "pix_vet.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(json.dumps(res["grade"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
