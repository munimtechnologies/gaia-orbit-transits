# Pre-registration: does our Gaia + TESS EBLM fit recover published M-dwarf radii? (job gaia-eblmctl-v1)

Written 2026-11-19 (about 14:50 UTC), **before** job gaia-eblmctl-v1 runs. By MV2 of Munim,
Inc.; made with AI agents working in his name, and not checked by a human expert. Text CC BY
4.0, code Apache-2.0.

## Why
`eblm_fit` 0.1.0 turns a Gaia DR3 single-lined orbit and TESS light curves into a companion
mass and radius. Two results rest on it: the graded M-dwarf inflation test
(`findings/2026-11-19-eblm-infl-full-results.md`, +6.3% above models, n = 28), and the fit of
BD+65 286 (`findings/2026-11-19-bd65-286-fit-results.md`). The BD+65 286 job's only control,
TOI-1251.01, failed its prediction because it is itself a known eclipsing binary at twice the
period, so under that pre-registration BD+65 286's label is not graded. Neither result has yet
been checked against systems whose radii someone else has measured independently. This test
does that.

**What we already know, stated plainly:** BD+65 286's numbers are already public (label C,
R₂ = 0.122 R☉ at 0.100 M☉). This test cannot change them. It only decides whether the
pipeline that produced them can be trusted. The controls below were chosen by a fixed rule
before any of them was fitted.

## The control set (chosen by rule, not by hand)
Source: **Swayne et al. 2024, MNRAS 528, 5703 (EBLM XI; arXiv:2312.11339)**, which measured 23
M-dwarf companions of solar-type stars with CHEOPS and TESS light curves and ground-based
spectroscopic orbits (Table 4: M₂, R₂; Table 2: periods).

Rule: every Swayne et al. 2024 system with **P < 8 d** (13 systems) that has a **Gaia DR3
nss_two_body_orbit solution of type SB1** within ±0.3% of the published period, at the
position its EBLM name gives. We searched Gaia's archive (TAP) on 19 Nov; the query that
recovered BD+65 286 as a positive control used the same method. Six match:

| EBLM | Gaia DR3 | Gaia P (d) | Gaia K (km/s) | G | Published P (d) | Published M₂ (M☉) | **Published R₂ (R☉)** |
|---|---|---|---|---|---|---|---|
| J0941-31 | 5440085875822885888 | 5.54564 | 18.40 | 11.04 | 5.54563 | 0.2173 ± 0.0078 | **0.2365 ± 0.0036** |
| J0540-17 | 2970781118606872192 | 6.00635 | 16.28 | 11.42 | 6.004940 | 0.1633 ± 0.0058 | **0.1949 ± 0.0032** |
| J0719+25 | 870991952855398656 | 7.45590 | 14.63 | 11.15 | 7.456295 | 0.1584 ± 0.0055 | **0.1917 ± 0.0029** |
| J1522+42 | 1393971390134144640 | 7.66233 | 15.86 | 11.41 | 7.661343 | 0.1656 ± 0.0063 | **0.1915 ± 0.0043** |
| J1741+31 | 4600624489073375744 | 7.71237 | 36.59 | 11.40 | 7.71263 | 0.461 ± 0.015 | **0.377 ± 0.018** |
| J0123+38 | 323261744326472832 | 7.95003 | 26.98 | 11.94 | 7.952938 | 0.338 ± 0.012 | **0.3531 ± 0.0060** |

No Gaia DR3 SB1 orbit was found for J0057-19, J0239-20, J0546-18, J0955-39, J1013+01,
J1559-05 or J1934-42.

A seventh system, **EBLM J1219-39** (Gaia DR3 6150072630171194752, P = 6.7595 d, K = 10.86
km/s; a published ~0.1 M☉ companion like BD+65 286's), runs in the
same job **for description only**. It is not in Swayne et al. 2024, so it has no
pre-registered literature value here and is not graded.

## What the job does
Job `gaia-eblmctl-v1` runs the **unchanged** `eblm_single.py` 0.1.0 (fetched at commit 04c9387,
the same pin as gaia-bd65286-v1) with the unchanged `eblm_fit` 0.1.0 (commit 10b5aeb) on the
seven Gaia DR3 ids above, up to 8 TESS sectors each. Nothing about the code, cuts or settings
differs from the BD+65 286 job.

## Grades (fixed now)
For each of the six graded controls:
- **testable** unless its label is UNTESTED (no TIC, no TESS data, error) or G (grazing).
- **pass** if its label is **C_NORMAL_COMPANION** (eblm_fit EBLM_CONSISTENT or
  EBLM_SMALL_RADIUS) **and** the fitted companion radius `r2` (light-curve primary radius) is
  within **±10%** of the published R₂.

Overall:
- **PIPELINE_VALIDATED** if at least 4 controls are testable and at least 80% of the testable
  ones pass (4/4, 4/5, 5/5, 5/6 or 6/6).
- **PIPELINE_FAILED** if at least 4 are testable and fewer than 80% pass.
- **INCONCLUSIVE** if fewer than 4 are testable.

Also reported, not graded: for each control `r2_flame`/R₂, m₂/M₂ (which tests Gaia's K and
the FLAME primary mass together), the label, and the **median radius offset** of the testable
controls, median(r2/R₂ − 1).

## What each outcome means (fixed now)
- **PIPELINE_VALIDATED:** BD+65 286's label C (`findings/2026-11-19-bd65-286-fit-results.md`)
  is adopted. In public it is always described as *graded against a control set chosen after
  its first control failed*. The AAVSO VSX submission then goes ahead once MV2 has an AAVSO
  login, crediting Gaia DR3, the SPOC sector-52 TCE and Green et al. 2023.
- **PIPELINE_FAILED:** BD+65 286's label is not adopted. The M-dwarf inflation grade
  (+6.3%) gets a public caveat that the radius scale failed an outside check, and the fit is
  investigated before any DR4 run.
- **INCONCLUSIVE:** nothing changes; re-run after DR4.
- In every case: if the median radius offset is beyond ±3%, the inflation note gets an
  addendum saying the pipeline's own offset is that large. The controls (P = 5.5-8 d, mostly
  G/K primaries) do not test the 0.9-3.5 d, F/A-primary regime of the inflation sample; this is
  a check of the radius scale, not of the period dependence.

## Our predictions (written now)
- PIPELINE_VALIDATED: 65%. PIPELINE_FAILED: 25%. INCONCLUSIVE: 10%.
- Median radius offset within ±5%: 70%.
- The control most likely to fail is J1741+31 (the heaviest companion, 0.46 M☉, with a
  published R₂ uncertainty of ±5%).

## Rules
- Exit 2 (Gaia archive down): re-file unchanged as v1. The archive closes 25 Nov 12:00 CET, so
  this job must run before then; if it has not, it waits for 2 December.
- All fit plots are opened before any label is reported.
- A failed prediction is said plainly in the results note, in STATUS and in any article.
