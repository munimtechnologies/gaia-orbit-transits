# Pre-registration: which star eclipses in the TESS pixels, how deep, and a 19-year period for TYC 6340-23-1

Written 2026-11-20 (~20:00 UTC), **before any TESS pixel data (TESScut) or Gaia field catalogue
for this star was downloaded or looked at**. By MV2 of Munim, Inc.; made with AI agents working
in his name, not checked by a human expert. Text CC BY 4.0, code Apache-2.0.
Code: `tyc_pixel.py` 0.1.0, tests `test_tyc_pixel.py`; Part B imports `tyc_period.py` pinned at
commit 40e96d4 (v0.38.0). Job: `tyc6340-pixel-v1`.

## Why

TYC 6340-23-1 (TIC 71945261) is the new 2.33-day eclipsing system from our Gaia SB1 search.
Its companion's fitted radius (0.224 R☉, 1.9 times the main-sequence value for Gaia's 0.097 M☉)
rests on one TESS sector (92), using the QLP light curve's 6.09% model depth. Two things in that
chain have never been checked:

1. **Which star dims.** A V = 11.25 star sits 38″ away, about 1.8 TESS pixels. Our SuperWASP and
   ASAS-SN tests could not separate the two (`findings/2026-11-20-tyc6340-period-results.md`).
   If the eclipse is on the neighbour, the oversized-companion label falls.
2. **How deep the eclipse is on the target.** QLP's sector-92 light curves are aperture
   photometry with a catalogue-based dilution correction. If that correction is wrong, the depth,
   the radius ratio and the companion's radius are wrong too. Even at b = 0 the 6.09% depth needs
   R₂ ≈ 0.20 R☉, so the depth is what carries the "oversized" claim.

A PSF model fitted to the sector-92 pixels answers both questions. It also gives eclipse times,
and with them a test of the 2006-2008 SuperWASP to 2025 TESS cycle count that our part-C scan
pointed to.

## Data

- **TESScut** (MAST) 15 × 15 pixel cutout of sector 92 (camera 2, CCD 1; the only sector), 200 s
  full-frame images. Cadences with QUALITY ≠ 0 or any non-finite pixel are dropped. TIME is BTJD
  (TDB).
- **Gaia DR3** stars within 0.075° with RP < 17 (anonymous TAP), positions propagated with proper
  motions to 2025.35 and placed on the cutout with its WCS. The target is Gaia DR3
  6853008555751131648. The neighbour is the Gaia star with G < 13 nearest to (305.566500,
  −22.082972) within 5″.
- **SuperWASP DR1** target light curve (already cached from earlier jobs) for Part B.

## Method (fixed)

- **PSF:** pixel-integrated (4 × 4 subsamples) rotated elliptical Gaussian core plus a circular
  Gaussian halo (fraction h, width 3 × the mean core σ).
- **Mean image** (all frames more than 0.08 d from a primary or secondary eclipse): fit the free
  parameters global offset (dx, dy), σx, σy, ρ, h by Nelder-Mead (two passes). The fluxes are
  linear: one free flux per star with RP < 14 (the target and neighbour always free; a star within
  0.6 px of a brighter free star joins the faint group), one shared scale for the faint group
  (RP 14-17, relative fluxes from Gaia RP), and a background plane. Pixel weights are
  1/max(M, median(M), 10⁻³·max(M), 1).
- **Eclipse windows** at P = 2.3287 d, T0 = BTJD 3803.0299: in-eclipse |Δt| ≤ 0.012 d (inside
  the flat bottom); out-of-eclipse 0.065-0.15 d on each side, averaged side by side. An eclipse
  is usable with ≥ 5 in-frames and ≥ 5 frames on each side; at least 4 usable eclipses are needed.
  Each eclipse gives a difference image D = out − in (positive where light is lost).
- **Two-source fit:** the mean D is fitted with the target's and the neighbour's PSFs at their
  fitted positions plus a constant. The fractional depths are δ_T = a_T/F_T and δ_N = a_N/F_N,
  and the lost-light fraction from the target is f_T = a_T/(a_T + a_N). Errors come from 500
  bootstrap resamplings of eclipses. Reported, not graded: the same fit with free amplitudes for
  every other free star within 5 px of the target.
- **Free-position fit:** one PSF at a free position (plus a constant) fitted to the mean D. Its
  error is the bootstrap scatter over 200 resamples, combined in quadrature with the astrometric
  floor σ_sys from control C4.

## Controls (run first; they decide sensitivity)

- **C1 nulls:** the same two-source fit at phases 0.25 and 0.75. Each passes if |δ_T|/σ < 3
  and |δ_N|/σ < 3.
- **C2 neighbour injection:** a 10% dip of the neighbour (its fitted flux × its PSF) added to
  the phase-0.25 difference images. Passes if the star label is PIX_ON_NEIGHBOUR, δ_N lies
  within ±30% of 0.10, and the centroid label is CENTROID_ON_NEIGHBOUR.
- **C3 target injection:** a 3% dip of the target added at phase 0.75. Passes if PIX_ON_TARGET,
  δ_T is within ±30% of 0.03, and the centroid label is CENTROID_ON_TARGET.
- **C4 astrometric floor:** free-position fits in the mean image (all other modelled light
  subtracted) of every free star with RP < 12.5, at least 2 px from the edges, with no Gaia star
  brighter than RP + 3 within 3 px. Fits that move more than 1.5 px are excluded and counted.
  σ_sys = max(RMS offset per axis, 0.05 px) if 3 or more stars are used, else 0.15 px.
- **L0 = PIX_SENSITIVE** if C1, C2 and C3 all pass; otherwise **PIX_INSENSITIVE**, and L1-L4
  are reported but not graded. **PIX_UNTESTABLE** if fewer than 4 usable windows exist at
  any of the three phases.

## Part A labels (graded if L0 = PIX_SENSITIVE)

- **L1 which star:** **PIX_ON_TARGET** if the 2.5th percentile of f_T ≥ 0.7 and δ_T/σ ≥ 5;
  **PIX_ON_NEIGHBOUR** if the 97.5th percentile of f_T ≤ 0.3 and δ_N/σ ≥ 5; otherwise
  **PIX_UNRESOLVED** (also if f_T is undefined in more than 10% of draws).
- **L2 centroid:** distances in σ from the target and from the neighbour: **CENTROID_ON_TARGET**
  (target < 3, neighbour > 3), **CENTROID_ON_NEIGHBOUR** (the reverse), **CENTROID_AMBIGUOUS**
  (both < 3), **CENTROID_ELSEWHERE** (both > 3).
- **L3 depth** (only if L1 = PIX_ON_TARGET), against the QLP model depth 0.0609:
  **DEPTH_CONSISTENT** if 0.85 ≤ δ_T/0.0609 ≤ 1.15 or |δ_T − 0.0609| ≤ 2σ; otherwise
  **DEPTH_SHALLOWER** or **DEPTH_DEEPER**. The window measures the eclipse bottom. With b = 0.675
  and limb darkening, the window mean can lie a few per cent below the model's maximum depth; the
  15% band allows for that.
- **L4 oversized companion** (only if L1 = PIX_ON_TARGET). The companion radius scales as
  √(depth) at fixed geometry, R₂ ≈ 0.224 √(δ_T/0.0609). **OVERSIZE_SURVIVES** if
  (δ_T − 2σ)/0.0609 ≥ 0.614 (R₂ stays ≥ 1.5 × the main-sequence 0.117 R☉);
  **OVERSIZE_WITHDRAWN** if (δ_T + 2σ)/0.0609 < 0.461 (R₂ < 1.3×); otherwise
  **OVERSIZE_WEAKENED**. If L1 = PIX_ON_NEIGHBOUR, L4 = OVERSIZE_WITHDRAWN.

## Part C: TESS eclipse times (graded as a measurement)

A 3 × 3 aperture is centred on the target's brightest model pixel. Each eclipse is normalised by
a straight line through its two out-of-eclipse windows. A joint trapezoid fit (T14 0.0990 d, T23
0.0324 d) gives the depth. Each eclipse's time is the χ² minimum over ±0.015 d in 5 × 10⁻⁵ d
steps, with an error from Δχ² = 1; times on the grid edge are dropped. A weighted line through
the times (errors scaled by √χ²_red if it exceeds 1) gives T_ref at the median cycle and the
sector-92 period. **TIMING_OK** if at least 4 eclipses are usable, else TIMING_UNTESTABLE.

## Part B: the SuperWASP-TESS cycle link (graded)

The anchor is the Part C epoch (T_ref + 2457000, σ_T) if TIMING_OK, else BJD_TDB 2460803.0299
± 0.001. SuperWASP is detrended without an ephemeris (per camera-night medians, tyc_period
0.1.0) and box-scanned over 2.3280-2.3296 d in 5 × 10⁻⁶ d steps (box reference = the anchor).
The best peak's epoch nearest the data's median time is refined by a T0-only trapezoid grid
(±0.03 d, then recentred on the in-eclipse weighted centre, then ±0.006 d in 10⁻⁴ steps) to
T_W. T_W's error comes from 200 night-bootstrap fits (±0.012 d, 2 × 10⁻⁴ steps); the edge
fraction is reported. N = round((T_anchor − T_W)/P_best). For k = N − 1, N, N + 1:
P_k = (T_anchor − T_W)/k, and the SuperWASP depth S/N at the fixed ephemeris (P_k, T_anchor) is
computed with tyc_period's `depth_fit`.

- **LINK_UNIQUE** if the bootstrap edge fraction ≤ 0.2, S/N(N) ≥ 10 and S/N(N) ≥ 2 × max
  S/N(N ± 1); else **LINK_AMBIGUOUS**; LINK_UNTESTABLE if no SuperWASP data.
- If UNIQUE: P_19yr = P_N with σ = √(σ_TW² + σ_T²)/N, and **GAIA_PERIOD_OK** if |P_19yr −
  2.3289298|/√(σ² + 0.00014²) ≤ 3, else **GAIA_PERIOD_OFF**.

**Honesty note:** the part-C scan of `tyc6340-period-v1` already showed SuperWASP's strongest
peak at 2.32878 d. Part B is therefore **not blind** to the period. It is a pre-specified
measurement of the cycle count and the 19-year period, not a discovery test.

## What each outcome means (fixed now)

- **PIX_ON_TARGET + CENTROID_ON_TARGET:** the 38″ star is excluded as the source. Stars within
  about one TESS pixel (21″) are not excluded; the summary lists every modelled Gaia star.
- **PIX_ON_NEIGHBOUR:** the eclipse belongs to the 38″ star. **B_OVERSIZED_COMPANION is
  withdrawn** in STATUS, the findings and the article, and Gaia's SB1 period match becomes a
  coincidence to explain.
- **DEPTH_DEEPER:** QLP's depth was diluted, and the companion is if anything larger (a refit is
  needed). **DEPTH_SHALLOWER:** QLP over-corrected, and L4 says how much of the claim survives.
- **OVERSIZE_WITHDRAWN:** we stop calling the companion oversized; **WEAKENED:** we say the
  size excess is smaller than 1.9× and uncertain.
- **LINK_UNIQUE + GAIA_PERIOD_OK:** we publish P_19yr ± σ and the Part-C epoch as the ephemeris
  for spectroscopic follow-up. The DR4 K test keeps its pre-registered fixed period; the new
  period is used only for a sensitivity note. **GAIA_PERIOD_OFF:** we report a measured Gaia
  DR3 SB1 period error beyond its quoted σ.
- PIX_INSENSITIVE or UNRESOLVED: no change to the labels. We say the blend question is open.

## Predictions (written now)

- L0: SENSITIVE 80%, INSENSITIVE 15%, UNTESTABLE 5%.
- L1: ON_TARGET 82%, UNRESOLVED 10%, ON_NEIGHBOUR 3% (remainder: not graded).
- L2: ON_TARGET 75%, ELSEWHERE 10%, AMBIGUOUS 8%, ON_NEIGHBOUR 3%.
- L3 (if on target): CONSISTENT 55%, DEEPER 25%, SHALLOWER 20%.
- L4 (if on target): SURVIVES 75%, WEAKENED 15%, WITHDRAWN 10%.
- C: TIMING_OK 90%. B: LINK_UNIQUE 70% (informed by v1's scan); if UNIQUE, GAIA_PERIOD_OK 85%.

## Job

```json
{"name": "tyc6340-pixel-v1", "kind": "compete", "image": "python:3.12",
 "setup": ["pip install --no-cache-dir numpy astropy"],
 "run": ["python -c \"import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/40e96d44de4523e73c7229f269210dbbbcc7b9bf/tyc_period.py', 'tyc_period.py')\"",
         "python -m unittest -v test_tyc_pixel", "python tyc_pixel.py --self-test",
         "python tyc_pixel.py --data-dir /data/pixel-tyc6340 --wasp-dir /data/wasp-tyc6340 --out-dir /out"],
 "network": true, "data_key": "gaia-orbit-tess", "cpu": 1, "memory_gb": 2, "timeout_minutes": 180}
```
A self-test failure (exit 3) means: fix, bump to 0.1.1 with a dated note here, no rule change.
A download failure (exit 4) means: re-file unchanged as -v2. The Gaia archive closes on 25
November; if the job has not run by then, the Gaia query moves to DR4 day with a dated note.

## Limits

The PSF is a Gaussian core plus halo, not the TESS PRF. The injections use the same model, so
they test noise and the pipeline, not PSF mismatch. The robustness fit with the other nearby stars
free, and the per-pixel depth map, are the checks on mismatch. There is one sector only. Stars
closer than about one pixel cannot be separated. The depth window samples the eclipse bottom,
not the model's maximum. SuperWASP times are HJD (UTC) shifted to TDB; HJD and BJD differ by
seconds. Nothing here measures the companion's mass.
