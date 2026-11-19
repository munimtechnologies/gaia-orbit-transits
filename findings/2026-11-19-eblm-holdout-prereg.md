# Pre-registration: a fresh, rule-chosen holdout check for eblm_fit 0.2.0

Written 2026-11-19 (about 20:30 UTC), **before** `eblm_fit` 0.2.0 exists and before any of the
systems below has been fitted by us. By MV2 of Munim, Inc.; made with AI agents working in his
name, not checked by a human expert. Text CC BY 4.0, code Apache-2.0.

## Why
Our Gaia + TESS EBLM pipeline (`eblm_fit` 0.1.0) failed its first outside check: 2 of 6
published systems passed (`findings/2026-11-19-eblm-control-results.md`). The radii agreed
(median −0.9%), but the ellipsoidal mass-consistency step used white-noise error bars that
are far too small at 5.5-8 days. Eccentric orbits were also not modelled. Those six systems
shaped the fix, so they **cannot validate it**. This note fixes, in advance, a new control
set and the rule that will grade the fixed pipeline. Gaia DR4 (2 December 2026) will add
thousands of new SB1 orbits. No DR4 EBLM result will be published until the fixed pipeline
passes this check.

## The holdout set (chosen by rule)
**Source:** EBLM XIX (Davis et al. 2026, MNRAS accepted, arXiv:2610.18338), Table 4. It gives
SOPHIE + TESS masses and radii for 66 northern low-mass eclipsing binaries.

**Rule:**
1. Sample 1 (the paper's 50-system high-quality subset).
2. P ≤ 13 d, the period range of our Gaia SB1 search.
3. Not one of the six systems of the failed first control set. J0123+38 and J0719+25 are in
   EBLM XIX; they are kept only as **resolver controls** (RC1 below) and are never graded.
4. A Gaia DR3 `nss_two_body_orbit` solution of type **SB1** (the only type `eblm_fit` uses).
   Its period must lie within ±0.3% of the published period, and its `gaia_source` position
   must lie inside the box the EBLM name allows: RA from 15·(hh + mm/60) − 0.25° to + 0.50°;
   Dec from the name's degrees −1° to +2° (north) or −2° to +1° (south). Exactly one SB1
   match: kept. More than one: **excluded** as ambiguous. None: excluded (other solution types
   in the box are reported).

That leaves 26 candidate holdouts: J0011+63, J0040+01, J0128+39, J0211+36, J0316+40, J0410+37,
J0503+41, J0507+29, J0641+28, J0719+21, J0942+05, J0955+36, J1624+34, J1626+57, J1640+49,
J1646+38, J1741+21, J1850+50, J1909+29, J2046+06, J2106+02, J2200+17, J2207+25, J2233+43,
J2303+39 and J2315+23. The published P, e, M₂ and R₂ (with errors) are in
`data/eblm-holdout/eblmxix_sample1_p13.csv`, transcribed from Table 4 of the arXiv HTML. Seven
rows were re-checked against the table verbatim before this note was written. Before grading,
every R₂ used will be re-checked against the published table. Any transcription error found
will be corrected and reported, never silently changed.

**Resolution job:** `gaia-eblm-holdout-resolve-v1` runs `holdout_resolve.py` 0.1.0, which
applies step 4 through Gaia's archive and fits nothing. **RC1:** the job must resolve J0123+38
to Gaia DR3 323261744326472832 and J0719+25 to 870991952855398656, the ids the first control
job used. If RC1 fails, the rule is not applied: the job exits 3 and the resolver is fixed
first. Its output `holdout_ids.csv` will be committed **before** any holdout is fitted. Gaia's
archive is closed from 25 November to 2 December 2026, so if the job misses the window, it
runs after 2 December on the DR3 tables.

## What eblm_fit 0.2.0 must change (planned before any holdout fit)
These follow from the first control failure, not from these systems:
- (a) The ellipsoidal amplitude's error includes red noise. It is estimated from the
  sector-to-sector scatter of the amplitude (eclipse shape fixed) or from a binned-residual β
  factor, whichever is larger.
- (b) The occultation phase comes from Gaia's e and ω (φ₂ ≈ 0.5 + (2/π)·e·cos ω), or is free
  within ±0.15 of that phase. It is no longer fixed at 0.5.
- (c) A grazing check runs before the mass-consistency check, and both are reported.
- (d) Unit tests on stdlib + numpy, run as the job's first step.

## Grades (the same rules as the first control check)
For each holdout that resolved to a single Gaia SB1 orbit:
- **testable** unless its label is UNTESTED (no TIC, no TESS data, error) or G (grazing).
- **pass** if its label is **C_NORMAL_COMPANION** (EBLM_CONSISTENT or EBLM_SMALL_RADIUS)
  **and** the fitted companion radius `r2` (light-curve primary radius) is within **±10%** of
  the published R₂.

Overall:
- **PIPELINE_VALIDATED** if at least 4 holdouts are testable and at least 80% of them pass.
- **PIPELINE_FAILED** if at least 4 are testable and fewer than 80% pass.
- **INCONCLUSIVE** if fewer than 4 are testable.

Also reported, not graded: the median radius offset, median(r2/R₂ − 1); m₂/M₂ for each
system; how many labels change if the mass check is dropped; and every label.

## What each outcome means (fixed now)
- **PIPELINE_VALIDATED:** 0.2.0 may be used for the Gaia DR4 EBLM inflation step (STATUS
  step 5). The DR3 inflation grade (+6.3%, n = 28) is re-run with 0.2.0 and reported next to
  the 0.1.0 result. BD+65 286 is re-fitted with 0.2.0, and its label may be adopted.
- **PIPELINE_FAILED:** no EBLM result from this pipeline is published from DR4. The inflation
  note keeps its caveat.
- **INCONCLUSIVE:** nothing changes until more holdouts exist (for example from DR4 orbits of
  EBLM XIX systems without a DR3 SB1 orbit).
- In every case, a median radius offset beyond ±3% gets a public addendum to the inflation
  note.

## Our predictions (written now)
- Resolution: 8–16 of the 26 holdouts get a single SB1 match (70%). RC1 passes (90%).
- With 0.2.0: PIPELINE_VALIDATED 50%, PIPELINE_FAILED 35%, INCONCLUSIVE 15%.
- Median radius offset within ±5%: 75%.
- The eccentric systems (J1624+34, e = 0.36; J2046+06, e = 0.34; J1909+29, e = 0.29) are the
  most likely to fail if fix (b) is wrong.

## Limits stated in advance
All holdouts have P = 5.6–12.8 d and G/K primaries; the inflation sample is 0.9–3.5 d around
hotter F/A primaries. This checks the radius and mass scales, not the period dependence. The
published masses and radii are known to us now (they are the answer key). The fix is
specified above, before any holdout is fitted, so that knowledge cannot shape it.
