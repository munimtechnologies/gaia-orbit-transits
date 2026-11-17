# SPDX-License-Identifier: Apache-2.0
"""Single-event dip search for TESS light curves (box filter on binned data).

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents).
Licence: Apache-2.0.

The search bins the light curve (default 30 min), splits it into segments at
gaps, detrends each segment with a running median whose window is three times
the trial duration (at least 0.5 d), and measures box depths. The noise of each
box length is measured empirically (MAD of all box means in the segment), so
red noise lowers the significance instead of producing false alarms.
"""
import numpy as np

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


def search(t, f, durations_h=DEFAULT_DURATIONS_H, bin_width=1.0 / 48, snr_min=7.0,
           gap=0.5, max_events=20, min_fill=0.75):
    """Return (events, binned) where events is a list of dicts sorted by snr.

    t in days, f normalised flux (median ~1).
    """
    bt, bf, bn = bin_lc(t, f, bin_width)
    events = []
    binned = {"t": bt, "f": bf, "n": bn, "segments": segments(bt, gap)}
    if bt.size < 10:
        return events, binned
    cands = []
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
                tc = 0.5 * (st[j] + st[j + k - 1])
                edge = min(tc - st[0], st[-1] - tc)
                cands.append({
                    "t_center": float(tc), "duration_h": float(dh),
                    "depth_ppm": float((center - means[j]) * 1e6),
                    "snr": float(snr[j]), "n_bins": int(k),
                    "box_noise_ppm": float(sd * 1e6),
                    "near_edge": bool(edge < max(D, 0.5)),
                    "seg_start": float(st[0]), "seg_end": float(st[-1]),
                })
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
