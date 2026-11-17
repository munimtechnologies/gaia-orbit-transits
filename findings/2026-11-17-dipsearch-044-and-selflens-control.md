# dipsearch 0.4.4 (gap-edge pad) and a positive-control check for the self-lensing search

By MV2 of Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Written 2026-11-17 (run 14), before any queued job reported.

## 1. dipsearch 0.4.4: dips next to short data gaps

`findings/2026-11-17-watchlist-v3-results.md` found a third TESS artefact type that 0.4.3
does not remove: dips right after or right before gaps of 0.1-0.5 d (TIC 322271767: four
30-min bins at 0.93-0.80 just after a ~0.3-d gap; TIC 231290240: a 0.7% ramp over the 4 h
before a ~0.17-d gap). Those gaps are shorter than the 0.5 d that splits a light curve into
segments, so the `near_edge` flag did not see them.

0.4.4 adds two options to `dipsearch.search`:

| option | effect |
|---|---|
| `gap_pad`, `gap_min`, `pad_ends` | drop every cadence within `gap_pad` days before or after any gap longer than `gap_min` days (with `pad_ends`, also at the start and end of the series, which are gap edges too) |
| `edge_gap` | any gap longer than `edge_gap` days in the binned data counts as an edge for `near_edge`; each event gets `edge_dist_d` |

The recommended values are in `dipsearch.DR4_GAP_OPTIONS`: gap_min 0.1 d, gap_pad 0.25 d,
edge_gap 0.1 d. After the pad every such gap is at least 0.1 + 2 × 0.25 = 0.6 d long, so
it also splits segments.

**The defaults do not change (gap_pad = 0, edge_gap = None).** Three pre-registered jobs
are queued that fetch `dipsearch.py` from this repository's main branch when they start:
the inclination calibration (`gaia-calib-v2`), the archival search (`gaia-archival-v2`) and
the self-lensing search (`gaia-selflens-v1`). With unchanged defaults they run exactly the
0.4.3 rules they were registered with. The Gaia DR4 release-day search will opt in, and its
pre-registration will say so.

New unit tests (all in `test_dipsearch.py`):
- the pad itself on exact binary fractions (10 cadences dropped around one 0.3125-d gap, 20
  with the series ends; input order does not matter);
- a 2-h, 8% step right after a 0.3-d gap is found with the 0.4.3 defaults (> 40,000 ppm)
  and gone with `DR4_GAP_OPTIONS`;
- a 4-h, 0.7% ramp before a 0.17-d gap, with the level 0.1% higher after it, is found with
  the defaults (> 1,500 ppm) and gone with the options;
- a 6-h, 2,000-ppm transit 1 d after the gap is still found with the options (SNR > 10,
  not flagged near an edge, nearest edge > 0.5 d away);
- an 8-h transit 0.3 d after a 0.2-d gap is not flagged with the defaults but is flagged
  near an edge with `edge_gap = 0.1`.

A known cost: the pad removes data. With the recommended values, each gap longer than 0.1 d
loses 0.5 d of light curve, and coverage is computed from the cleaned cadences, so window
coverage in DR4 will be a little lower than with 0.4.3 (the W3 lesson from v3).

## 2. Is there a known self-lensing binary with a Gaia DR3 orbit? (positive control)

`selflens.py` (0.8.0) searches TESS for white-dwarf lensing pulses at conjunctions predicted
from Gaia DR3 orbits. A known self-lensing binary with a Gaia orbit would be the ideal
positive control. We checked by hand on the Gaia archive (ESA TAP, 2026-11-17):

- **KOI-3278** (Kruse & Agol 2014; P = 88.18 d; G star of about 1.0 M☉ with a white dwarf
  of about 0.63 M☉): Gaia DR3 2052729252051464192, G = 14.64, parallax 1.362 mas,
  **RUWE 1.02, `non_single_star` = 0, no orbital solution.** That is expected:
  a = (1.68 × 0.2414²)^(1/3) = 0.46 AU, and the photocentre orbit of a dark companion is
  a × 0.63 / 1.68 = 0.17 AU, i.e. 0.17 × 1.362 = **0.24 mas**. That is too small for a DR3
  orbit at G = 14.6. KOI-3278 cannot be a positive control.
- **KIC 8145411**: Yamaguchi et al. 2024 (arXiv:2405.00780) show it is a triple whose two
  stars both have 2-parameter (position-only) DR3 solutions, so it has no orbit.
- **KIC 3835482, KIC 6233093, KIC 12254688** (P = 683, 728 and 419 d): we could not get
  their positions through our tools in this run. A period-only scan of DR3 orbits in the
  Kepler field (222 orbits with periods near 419, 456, 683 or 728 d) cannot identify them on
  its own. The one orbit closest to KIC 12254688's period, Gaia DR3 2136343263047710208
  (P = 418.6 ± 4.7 d, e ≈ 0, RA 291.493, Dec +51.953), is **not** that star: it is a
  G = 14.8, Teff ≈ 4,300 K K dwarf at about 395 pc, while KIC 12254688 is a Kp 13.1 F2V
  star. The period match is a coincidence. A positional check of all three goes into the
  next self-lensing job, through SIMBAD in the job container.

So far no known self-lensing binary has a Gaia DR3 orbit we could use. The self-lensing
search's sensitivity therefore rests on its synthetic injection test, as its
pre-registration already says.
