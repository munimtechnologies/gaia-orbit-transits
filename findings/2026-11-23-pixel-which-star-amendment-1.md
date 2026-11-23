# pixel_which_star amendment 1 (0.1.1): non-negative fluxes and merged close stars

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked it yet.
Text CC BY 4.0, code Apache-2.0. Written 2026-11-23 (~01:30 UTC), **before** job
`tic93622019-pixel-011-v1` ran. Code: `pws_amend_011.py`, `test_pws_amend_011.py`,
`runbook/pixel2/` (fetch_pinned.py, targets.json).

## Why

The 0.1.0 pixel test (`findings/2026-11-22-tic93622019-pixel-results.md`) ended CONTROLS_FAIL.
The failures all came from the mean-image PSF fit, which gave stars **negative fluxes**:

| Star | Sector | Target flux (e/s) | Neighbour flux (e/s) | Cause found in the outputs |
|---|---|---|---|---|
| HATS-58 A | 100 | -1385 | -20 | companion 0.74″ (0.04 px) away was put in the shared faint-group column, which then sat on the target and traded flux with it |
| HATS-58 A | 101 | -233 | -42 | same |
| TIC 93622019 | 10, 37, 90, 100 | 1320-1700 | -520 to -20 | the free flux of the RP 13.49 neighbour 2 px away swung between -520 and +963 across sectors; with no sign constraint, poor PSF wings were absorbed by the neighbour column |

Source: `data/tic93622019-pixel-v1/pws_summary.json` (mean_fit blocks).

## What changes (only the mean-image fit; one function replaced)

`pws_amend_011.py` imports `pixel_which_star.py` 0.1.0 (commit bfbff5f2) and `tyc_pixel.py`
0.1.0 (commit c16e7a2a) unchanged and replaces `tyc_pixel.fit_mean_image` only:

- **M1, merge:** a Gaia star within 0.6 px (the 0.1.0 MERGE_PX) of a free star joins that
  star's PSF column, weighted by Gaia RP flux, instead of the shared faint-group column. The
  "target flux" then means the flux of the merged group (for HATS-58 A, the pair).
- **M2, non-negative fluxes:** star and faint-group fluxes are constrained to be ≥ 0
  (Lawson-Hanson NNLS) both inside the PSF-shape search and in the final solve. Background terms
  stay free.
- **M3, tied neighbour flux:** if M2 pins the neighbour's flux at 0 while the target's is
  positive, the neighbour flux used to turn amplitudes into fractional depths (and to scale the
  C2 injection) is the target's flux times the Gaia RP flux ratio of the two groups. Flagged
  `N_FLUX_GAIA_TIED` per sector. A target pinned at 0 still ends NEGATIVE_FLUX.

Unchanged: windows, difference images, nulls, injections, the C1-C4 sensitivity controls,
free-position centroids, sky offsets, every label and threshold, the WS rule, the controls and
their selection rule, the target's sectors, and CONTROLS_PASS (both controls WS_ON_TARGET or
WS_UNRESOLVED). Each sector's output gains a `fit_011` block (fitted fluxes before M3, merged
stars, stars pinned at 0).

## Not blind

We have seen the 0.1.0 results for all three stars: TIC 93622019 came out PIX_ON_TARGET in its
two sensitive sectors, WS_UNRESOLVED (0.47″ ± 2.23″), with one Gaia source 2.39″ away that the
centroid cannot exclude. The fix was designed after seeing the failures, from their causes, not
from the target's labels. The rule and predictions below are fixed before the re-run.

## Targets

The three 0.1.0 targets, unchanged. Two **exploratory** Gaia DR3 transit candidates that survived
the period-free TESS search (`findings/2026-11-22-vpt-pf-dr3-results.md`) and have no TOI or
CTOI (ExoFOP, checked 2026-11-23): **TIC 4638108** (Gaia DR3 5431056347037926784; P 2.20828 d,
TESS depth 1.41%; TIC contamination ratio 1.26, so a neighbour test matters) and **TIC 44997521**
(Gaia DR3 5432318139709900160; P 3.54941 d, depth 2.07%, K dwarf R ≈ 0.80 R_sun). Their
ephemerides come from that search (duration on a 1-hour grid); they are reported, not graded.

## Predictions

- CONTROLS_PASS: **60%**. HATS-67 b WS_ON_TARGET 85%. HATS-58 A b WS_UNRESOLVED or ON_TARGET
  55%, WS_UNTESTABLE 35% (sector 99 has only 3 transit windows, so it needs both 100 and 101).
- No sector of any star ends NEGATIVE_FLUX: 75%.
- TIC 93622019: at least 4 of 6 sectors sensitive 50%. WS_UNRESOLVED 75%, WS_ON_TARGET 10%,
  WS_OFF_TARGET 5%, WS_UNTESTABLE 10%. (The 2.39″ source is 0.11 px from the target, so no TESS
  centroid can exclude it while it counts as capable.) PIX_ON_TARGET in every sensitive sector
  80%. Deblended depth within 15% of 0.1.0's 1.284%: 70%. N_FLUX_GAIA_TIED in at least one
  target sector: 60%.
- Exploratory: TIC 4638108 WS_ON_TARGET/UNRESOLVED 55%, OFF_TARGET 25%, UNTESTABLE 20%.
  TIC 44997521 ON_TARGET/UNRESOLVED 60%, OFF_TARGET 15%, UNTESTABLE 25%.

## What follows

- **CONTROLS_PASS:** TIC 93622019's labels are graded under the 0.1.0 outcome rules. If WS is
  UNRESOLVED only because of Gaia DR3 5345417757181557248 (the 2.39″ source whose BP/RP fluxes
  are dominated by the target, excess factor 10.0, G = 19.56), that star is judged by Gaia's
  own photometry, as the 0.1.0 rules say: job gaia-vpt-epochs-box-v1 tests whether Gaia's
  epochs show the dip on the target at the TESS ephemeris. *This link between the two tests is
  written after the 0.1.0 result.* WS_OFF_TARGET withdraws the candidate.
- **CONTROLS_FAIL again:** no grade. The next step is a TESS PRF model in place of the Gaussian
  PSF, not more tuning of this one.
- The fixed module is what the Gaia DR4 runbook uses after 2 December to vet survivors.

## Limits

Gaussian PSF, not the TESS PRF. Gaia RP stands in for the TESS band in the merge weights and
in M3. M3 assumes the Gaia RP ratio is right; for a neighbour with a bad RP (as for the 2.39″
source) the tied flux is wrong, but it only scales the neighbour's fractional depth, not the
centroid.
