# Results: TYC 6340-23-1's period, ASAS-SN and the SuperWASP common-mode test (tyc6340-period-v1)

Graded 2026-11-20 (~19:30 UTC) under `findings/2026-11-20-tyc6340-period-prereg.md`, which was
written before any ASAS-SN or comparison-star data were looked at. By MV2 of Munim, Inc.; made
with AI agents working in his name, not checked by a human expert. Text CC BY 4.0.
Code: `tyc_period.py` 0.1.0 and `fetch_asassn.py` 0.1.0 (v0.38.0, commit 40e96d4). Job
`tyc6340-period-v1` ran on 20 Nov 14:20-14:27 UTC. Unit tests and self-test passed, and every
step exited 0. Outputs: `data/tyc6340-period-v1/`.

## Grades

| Part | Label | Our prediction | Verdict |
|---|---|---|---|
| A1 ASAS-SN detection | **ASASSN_INSENSITIVE** | DETECTED 65%, INSENSITIVE 20% | prediction **wrong** |
| A2-A5 period branch, TESS link, WASP link, blend | not graded (A1 not DETECTED) | | |
| B SuperWASP common mode | **COMMON_CLEAN** (0 of 12 comparison stars dip) | CLEAN 40% (our most likely) | prediction right |

### A1: ASAS-SN cannot test this star with our method

- Data: 2,451 target epochs from Sky Patrol v2 (ASAS-SN id 498216376042, 1.6″ from the TIC
  position); 1,644 kept after cleaning, 837 nights, 2014-04 to 2024-11, 14 camera/filter groups.
  The 38″ neighbour (id 506806230001) gave 2,458 epochs.
- **Injection failed:** the planted 0.03 mag eclipse at 2.6 d came back at 2.6006 d with box
  statistic 5.30, below both 7 and the control maximum (7.14 over 300 control periods). So the
  label is INSENSITIVE, not NOT_DETECTED.
- The target's own search: best box statistic 6.79 at 2.329208 d (depth 0.080 mag), below the
  threshold. The bootstrap depth S/N was 2.4, and 53% of bootstrap fits ended on the grid edge even
  after the pre-registered widening, so no ephemeris from ASAS-SN can be trusted.
- Why: after per-(camera, season) cleaning the residual χ²_red is **143.6**. ASAS-SN's quoted
  errors are far below the real scatter for this V = 10.65 star, which sits near ASAS-SN's
  saturation limit (our Limits section flagged this). The weights and the box statistic then
  track noise, and a 0.03 mag injection is lost.
- Reported, not graded: box statistic at the candidate periods: 2945-cycle WASP-TESS link
  (2.32877 d) 6.51, Gaia 4.82, 2944-cycle 3.83, WASP v1 3.74, 2943-cycle 3.37. The neighbour-vs-
  target blend statistic is z = 2.53 (target deeper), below the ±3 rule. The time-scale check
  shows no preference (Δχ² 44.8 for HJD, 46.0 for geocentric JD).

### B: the SuperWASP dip is not a field-wide systematic

- Reproduction check passed: target depth 0.07427 mag (v1: 0.07427), 38″ neighbour 0.06377
  (v1: 0.06377).
- All 12 comparison stars 4.7-7.1′ away had 8,400-8,700 points. **None dips**: the largest
  depth is 0.011 ± 0.021 mag; the median is 0.001 mag. Two stars show significant *brightening*
  at the v1 phase (−0.0064 and −0.0085 mag, z ≈ −4.4), the opposite sign of an eclipse.
- As pre-registered, v1's 0.074 mag dip at the SuperWASP ephemeris is therefore not a
  systematic shared by the field. It is either the target's eclipse (the 38″ star sits inside
  the SuperWASP aperture, so the two cannot be told apart) or something confined to these pixels.

## Reported, not graded: the SuperWASP wide scan (part C) settles the "period tension" as our artefact

After ephemeris-free per-night detrending (χ²_red 3.90), the scan of 2.32-2.34 d
(`data/tyc6340-period-v1/wasp_wide_scan.csv`) gives:

| Period (d) | Box statistic | Note |
|---|---|---|
| **2.328780** | **65.9** | best peak; depth 0.055 mag |
| 2.328575 | 51.3 | side peak |
| 2.328980 | 49.7 | side peak |
| 2.327895 | 40.3 | |
| 2.329720 | 40.1 | near v1's 2.32974 |
| controls (300 periods) | max 33.9, 95th pct 20.2 | |

At the candidate periods: the 2945-cycle WASP-TESS link (2.3287683 d) scores 65.8, Gaia's
2.3289298 d 56.6, v1's 2.329743 d 39.6, the 2944-cycle link 36.9 and the 2943-cycle link 26.2.

What this means, stated with care because part C was not graded:
- The strongest SuperWASP signal (about twice the largest control) sits at **2.32878 d**. That is
  the period that joins the 2006-2008 eclipses to the 2025 TESS eclipse in 2945 whole cycles. It
  agrees with Gaia DR3 (2.3289298 ± 0.00014 d, z = −1.07) and with the one-sector TESS period
  (2.3287 d).
- The v1 period of 2.32974 d, which we reported this afternoon as "5.8σ from Gaia", is only the
  fifth peak once the light curve is detrended without assuming an ephemeris. Detrending at v1's
  own coarse ephemeris pulled the fit there. **The period tension was very likely our
  artefact, not a property of the star.**
- The side peaks 0.0002 d either side are expected aliases of the multi-season SuperWASP
  sampling. A pre-registered measurement of the 19-year cycle link is needed before a period is
  published, and it is now registered (`findings/2026-11-20-tyc6340-pixel-prereg.md`, part B).

## What changes

- Nothing about the companion changes. The label stays **B_OVERSIZED_COMPANION**. The eclipse is
  still not replicated by an independent *graded* test: SuperWASP v1 and ASAS-SN were both
  insensitive. The SuperWASP evidence above is strong but was not graded.
- The open question of which star eclipses (target or the 38″ neighbour) is still open. ASAS-SN
  could not answer it, so we registered a TESS pixel-level test that can
  (`findings/2026-11-20-tyc6340-pixel-prereg.md`). It also measures the eclipse depth on the
  target with the neighbour modelled out. The companion's radius rests on that depth, and no
  earlier step checked it.

## Lessons

- **Check the photometric noise model before trusting a survey's error bars on a bright star.**
  A χ²_red of 144 means the weights are meaningless; a per-group error rescaling or a
  saturation cut should come first, and the injection depth should match the real signal's depth.
- **Ephemeris-free detrending first.** Detrending around an assumed eclipse time can drag the
  period toward the assumption. Our v1 period was 5.8σ off for that reason.
- Our detection prediction failed again: this is the second ground-based survey of this star
  (after SuperWASP v1) that came out INSENSITIVE when we predicted DETECTED. We are lowering our
  detection priors for ground-based archives of bright stars.
