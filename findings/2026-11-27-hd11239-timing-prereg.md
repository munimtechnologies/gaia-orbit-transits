# Pre-registration: hd11239-timing-v1, HD 11239's eclipse times sector by sector against Gaia's orbit

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0, code Apache-2.0. Written 27 November 2026 (~03:00 UTC), before job
`hd11239-timing-v1` ran and before any per-sector timing of these stars was measured.
Code: `ecl_timing.py` 0.1.0 with `test_ecl_timing.py`; inputs `runbook/hd11239-timing-v1/targets.json`.

## Why

`sb2-ebfit-v2` fitted HD 11239's two TESS sectors jointly and found P = 3.119557 +/- 0.000023 d,
28 sigma below Gaia DR3's 3.1208264 +/- 0.000039 d. In sector 30 the fitted eclipse lies 0.002 d from
Gaia's predicted conjunction; the fitted period implies the sector-3 eclipses are ~0.30 d late
(`findings/2026-11-27-sb2-ebfit-v2-graded.md`). Either the joint fit stopped in a local minimum in
period, or the sector-3 light curve's times are off, or something real shifts the eclipses.

## Method (fixed now)

For every TESS light curve of the star (each sector from each of SPOC 2-min, TESS-SPOC and QLP):
predicted eclipse times from a **fixed** reference ephemeris (HD 11239: Gaia DR3's two conjunctions,
BTJD 389.2946 and 390.8619 + n x 3.1208263847 d); every eclipse window of +/-0.75 d with at least half
its cadences and data on both sides is one event with its own linear baseline; a Gaussian template
(FWHM 0.086 d, averaged over each exposure) with one depth per conjunction is shifted by a common
offset dt over -0.45...+0.45 d in 0.002 d steps; dt_best from the chi2 minimum (parabola refined),
sigma from the curvature with chi2 rescaled to 1 per degree of freedom. The same scan is done for each
eclipse alone. Also reported: the scaled delta chi2 at dt = 0 (Gaia) and at the offset the
`sb2-ebfit-v2` ephemeris predicts for that sector, and the best rival local minimum more than one FWHM
from the best.

Controls, with references from the `sb2-ebfit-v2` fits to their SPOC 2-min light curves: **CW Eri**
(TIC 98853987, sectors 4 and 31) and **ZZ Boo** (TIC 357358259, sectors 23 and 50). Their FFI light
curves (TESS-SPOC, QLP) in the same sectors test the FFI pipelines' timing against SPOC.

Self-test (built in): synthetic 30-min and 10-min light curves with offsets +0.12, 0 and -0.30 d must
be recovered within 0.004 d with sigma < 0.01 d.

## Predictions

| id | prediction | probability |
|---|---|---|
| S | self-test PASS | 90% |
| C | every control product: SPOC |dt| <= 0.003 d and FFI (TESS-SPOC, QLP) |dt| <= 0.005 d | 80% |
| T1 | HD 11239 sector 30, every product: |dt| <= 0.03 d against Gaia | 85% |
| T2 | HD 11239 sector 3, TESS-SPOC: |dt| <= 0.05 d against Gaia | 55% |
| T2' | (alternative to T2) sector 3 TESS-SPOC dt between +0.25 and +0.35 d | 35% |
| T3 | if sector 3 has two or more products, their dt agree within 0.01 d | 85% |
| T4 | every other HD 11239 sector with data (not 3 or 30): |dt| <= 0.05 d (ungraded if none) | 80% |
| T5 | in every HD 11239 sector, at most one single-eclipse dt differs from the sector dt by > 0.03 d | 70% |

Gaia's period error alone allows 0.013 d of drift by sector 3 (322 orbits) and 0.022 d by sector 30
(556 orbits); the 0.03-0.05 d thresholds include the unknown error of Gaia's conjunction time.

## Decision rules

- S fails: nothing graded; fix and bump the version.
- C fails: HD 11239 rows ungraded; the method or an FFI pipeline is suspect.
- T2 holds (sector 3 on Gaia's ephemeris): the v2 period is a fit failure. The next `sb2_ebfit` adds a
  period scan started at Gaia's P before the light-curve parameters are fitted, and HD 11239's masses
  are re-fitted.
- T2' holds in every sector-3 product while T1 and C hold: an unexplained 7-hour shift confined to one
  sector. Before any astrophysical claim we time a second star in the same sector and camera; it is
  reported as a timing anomaly, not a discovery.
- Data-access failure: re-file unchanged under the same name.
