# SPDX-License-Identifier: Apache-2.0
"""Single-event dip search for TESS light curves (box filter on binned data).

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0.

The search bins the light curve (default 30 min), splits it into segments at
gaps, detrends each segment with a running median whose window is three times
the trial duration (at least 0.5 d), and measures box depths. The noise of each
box length is measured empirically (MAD of all box means in the segment), so
red noise lowers the significance instead of producing false alarms.

0.4.2: cadences with normalised flux below `flux_floor` (default 0.5) are dropped
before binning (Sector 104 QLP light curves fall to ~10% at orbit edges without
quality flags).

0.4.3: the 0.4.2 re-run of the 25-star watch list (gaia-watchlist-tess-v2) showed
that the floor alone is not enough:
  * the flux ramps down to the floor and back up over ~0.3 d on each side, and
    those ramp cadences (50-99% of normal) still made 4-22% "dips" at SNR > 400.
    Fix: every cadence within `floor_pad` days (default 0.5) of a sub-floor
    cadence is dropped too.
  * single scattered cadences (one 30-min bin at 0.8, its neighbours at 1.0)
    made 2-h "dips" of 7-10%. Coherence = in-box standard deviation of the
    residuals / box-mean depth. For a flat-bottomed dip of depth d filling a
    fraction p of the box: mean p*d, sd d*sqrt(p(1-p)), so coherence =
    sqrt((1-p)/p): 0 when the box is inside the dip, 0.58 at p = 0.75, 1.0 at
    p = 0.5, and sqrt(k-1) for a one-bin spike in a k-bin box. A V-shaped
    (grazing) dip that fills its box gives 1/sqrt(3) = 0.58. Fix: a box with
    coherence above `coherence_max` (default 0.75, i.e. less than ~64% filled)
    whose in-box sd also exceeds three times the per-bin noise is dropped
    before the events are de-duplicated. Every dip lasting at least the
    shortest box (2 h) has a box that sits inside it (coherence ~0), so it
    still wins; dips shorter than ~1.3 h are no longer reported (no target of
    this project is that short: a brown dwarf on a > 10-day orbit transits for
    several hours).
"""
import numpy as np

VERSION = "0.4.3"
DEFAULT_DURATIONS_H = (2.0, 4.0, 8.0, 16.0, 24.0)


def bin_lc(t, f, width=1.0 / 48):
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    ok = np.isfinite(t) & np.isfinite(f)
    t, f = t[ok], f[ok]
    if t.size == 0:
        return np.empty(0), np.empty(0), np.empty(0, int)
    order = np.argsort(t)
    t, f = t[order], f[order]
    idx = np.floor((t - t[0]) / width).astype(np.int64)
    uniq, inv, counts = np.unique(idx, return_inverse=True, return_counts=True)
    bt = np.bincount(inv, weights=t) / counts
    bf = np.bincount(inv, weights=f) / counts
    return bt, bf, counts


def segments(t, gap=0.5):
    """Index ranges [(i0, i1), ...] (i1 exclusive) of sorted t split at gaps > gap days."""
    t = np.asarray(t, float)
    if t.size == 0:
        return []
    cuts = np.where(np.diff(t) > gap)[0] + 1
    edges = np.concatenate([[0], cuts, [t.size]])
    return [(int(edges[i]), int(edges[i + 1])) for i in range(len(edges) - 1)]


def running_median(t, y, window):
    t = np.asarray(t, float)
    y = np.asarray(y, float)
    lo = np.searchsorted(t, t - window / 2, side="left")
    hi = np.searchsorted(t, t + window / 2, side="right")
    out = np.empty_like(y)
    for i in range(y.size):
        out[i] = np.median(y[lo[i]:hi[i]])
    return out


def robust_sd(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 3:
        return np.nan
    return 1.4826 * np.median(np.abs(x - np.median(x)))


def floor_mask(t, f, flux_floor=0.5, floor_pad=0.5):
    """Boolean mask of cadences to drop: f < flux_floor, and (if floor_pad > 0)
    every cadence within floor_pad days of such a cadence. Returns (drop, n_low)."""
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    drop = np.zeros(t.size, bool)
    if flux_floor is None or t.size == 0:
        return drop, 0
    low = np.isfinite(f) & (f < flux_floor)
    n_low = int(low.sum())
    if n_low == 0:
        return drop, 0
    drop |= low
    if floor_pad and floor_pad > 0:
        tl = np.sort(t[low])
        # distance from each cadence to the nearest sub-floor cadence
        pos = np.searchsorted(tl, t)
        left = np.abs(t - tl[np.clip(pos - 1, 0, tl.size - 1)])
        right = np.abs(tl[np.clip(pos, 0, tl.size - 1)] - t)
        near = np.minimum(left, right) <= floor_pad
        drop |= near & np.isfinite(t)
    return drop, n_low


def box_coherence(resid_in_box, depth):
    """In-box standard deviation of the residuals divided by the box-mean depth
    (both in relative flux). inf if depth <= 0."""
    r = np.asarray(resid_in_box, float)
    if depth <= 0 or r.size < 2:
        return float("inf") if depth <= 0 else 0.0
    return float(np.std(r) / depth)


def search(t, f, durations_h=DEFAULT_DURATIONS_H, bin_width=1.0 / 48, snr_min=7.0,
           gap=0.5, max_events=20, min_fill=0.75, flux_floor=0.5, floor_pad=0.5,
           coherence_max=0.75):
    """Return (events, binned) where events is a list of dicts sorted by snr.

    t in days, f normalised flux (median ~1). Cadences with f < flux_floor, and
    all cadences within floor_pad days of them, are dropped first
    (binned["n_below_floor"], binned["n_floor_dropped"] count them). Boxes whose
    in-box scatter is incoherent (see module doc) are dropped
    (binned["n_incoherent"]); pass coherence_max=None to keep them.
    """
    t = np.asarray(t, float)
    f = np.asarray(f, float)
    drop, n_floor = floor_mask(t, f, flux_floor, floor_pad)
    n_drop = int(drop.sum())
    t, f = t[~drop], f[~drop]
    bt, bf, bn = bin_lc(t, f, bin_width)
    events = []
    binned = {"t": bt, "f": bf, "n": bn, "segments": segments(bt, gap),
              "n_below_floor": n_floor, "n_floor_dropped": n_drop,
              "n_incoherent": 0}
    if bt.size < 10:
        return events, binned
    cands = []
    n_incoh = 0
    for (i0, i1) in binned["segments"]:
        st, sf = bt[i0:i1], bf[i0:i1]
        seg_len = st[-1] - st[0] if st.size else 0
        for dh in durations_h:
            D = dh / 24.0
            k = max(2, int(round(D / bin_width)))
            if st.size < 3 * k or seg_len < 2 * D:
                continue
            trend = running_median(st, sf, max(3 * D, 0.5))
            r = sf / trend - 1.0
            bin_sd = robust_sd(r)
            cs = np.concatenate([[0.0], np.cumsum(r)])
            means = (cs[k:] - cs[:-k]) / k
            spans = st[k - 1:] - st[:st.size - k + 1]
            valid = spans <= (k - 1) * bin_width / min_fill + 1e-9
            if valid.sum() < 5:
                continue
            sd = robust_sd(means[valid])
            if not np.isfinite(sd) or sd <= 0:
                continue
            center = np.median(means[valid])
            snr = (center - means) / sd
            snr[~valid] = -np.inf
            for j in np.where(snr >= snr_min)[0]:
                depth = center - means[j]
                coh = box_coherence(r[j:j + k], depth)
                if (coherence_max is not None and coh > coherence_max
                        and np.std(r[j:j + k]) > 3 * (bin_sd if np.isfinite(bin_sd) else 0)):
                    n_incoh += 1
                    continue
                tc = 0.5 * (st[j] + st[j + k - 1])
                edge = min(tc - st[0], st[-1] - tc)
                cands.append({
                    "t_center": float(tc), "duration_h": float(dh),
                    "depth_ppm": float(depth * 1e6),
                    "snr": float(snr[j]), "n_bins": int(k),
                    "box_noise_ppm": float(sd * 1e6),
                    "coherence": float(coh),
                    "near_edge": bool(edge < max(D, 0.5)),
                    "seg_start": float(st[0]), "seg_end": float(st[-1]),
                })
    binned["n_incoherent"] = n_incoh
    cands.sort(key=lambda c: -c["snr"])
    for c in cands:
        clash = False
        for e in events:
            tol = 0.5 * (c["duration_h"] + e["duration_h"]) / 24.0
            if abs(c["t_center"] - e["t_center"]) < tol:
                clash = True
                break
        if not clash:
            events.append(c)
        if len(events) >= max_events:
            break
    return events, binned
