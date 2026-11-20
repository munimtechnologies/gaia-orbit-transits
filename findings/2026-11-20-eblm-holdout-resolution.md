# EBLM XIX holdout set resolved to Gaia DR3 (before any fit)

Written 2026-11-20 (about 02:30 UTC) by MV2 of Munim, Inc.; made with AI agents working in his
name, not checked by a human expert. Text and data CC BY 4.0, code Apache-2.0.
Rules: `findings/2026-11-19-eblm-holdout-prereg.md`. **No holdout has been fitted.** This note and
`data/eblm-holdout/holdout_ids.csv` are committed before the fit job may start: the job's setup
step checks that the file is on `main` and identical to its own copy, and stops otherwise.

## Result of job gaia-eblm-holdout-resolve-v1 (holdout_resolve 0.1.0)
Ran 20 Nov 00:56–01:05 UTC against the Gaia DR3 archive. Outputs: `data/eblm-holdout/holdout_ids.csv`,
`holdout_resolve.json`, `holdout_resolve.md`.

- **RC1 passed:** J0123+38 → Gaia DR3 323261744326472832 and J0719+25 → 870991952855398656,
  the ids the first control job used. (Predicted: RC1 passes, 90%. Held.)
- Of the 26 candidate holdouts: **14 MATCH** (exactly one SB1 orbit within ±0.3% of the
  published period inside the name box), **1 AMBIGUOUS**, **11 NO_SB1**, 0 errors.
  (Predicted: 8–16 match, 70%. Held.)
  - **Fitted (14):** J0011+63, J0040+01, J0316+40, J0507+29, J0719+21, J0955+36, J1624+34,
    J1626+57, J1640+49, J1741+21, J1850+50, J2106+02, J2233+43, J2315+23.
  - **AMBIGUOUS, excluded:** J2303+39 (two SB1 orbits in the box, Gaia DR3 1930227262819125376
    and 1929904972769370752).
  - **NO_SB1, excluded:** J0128+39, J0211+36, J0410+37, J0503+41, J0641+28, J0942+05, J1646+38,
    J1909+29, J2046+06, J2200+17, J2207+25.
- `holdout_ids.csv` has 16 rows: the 14 holdouts plus the 2 resolver controls (role
  `resolver_control`), which the fit wrapper never grades.
- Of the three eccentric systems named in the pre-registration, only J1624+34 (e = 0.364) is in;
  J2046+06 and J1909+29 have no DR3 SB1 orbit.
- Noted now, before any fit: Gaia's eccentricity differs from the published one for J1850+50
  (Gaia 0.26 vs 0.107). eblm_fit 0.2.0 takes the occultation phase from Gaia's e and ω and lets
  it float ±0.15 in phase, as pre-registered, so this system tests fix (b).
- The resolver's optional SIMBAD cross-check failed for every row (HTTP 404 from the SIMBAD TAP
  endpoint it called). That check was informational and not part of the rule.

## Published values re-checked before grading
As the pre-registration requires, every M₂, R₂ (with errors) and e of the 14 holdouts was
re-read from Table 4 of the arXiv HTML of EBLM XIX (arXiv:2610.18338) on 20 Nov 2026 with an
automated page reader. All agree with `data/eblm-holdout/eblmxix_sample1_p13.csv`; nothing was
corrected.

## Next
Job `gaia-eblm-holdout-fit-v1` fetches eblm_fit 0.2.0, eblm_screen and `eblm_holdout_fit.py`
0.1.0 pinned at 996ced14d2f4ddd431616b0f2d72d49619bc8095 (release v0.31.0) and checks that
`holdout_ids.csv` is committed. It then runs the unit tests, and fits and grades the 14 holdouts
by the pre-registered rule: PIPELINE_VALIDATED needs ≥ 4 testable systems with ≥ 80% passing;
otherwise PIPELINE_FAILED, or INCONCLUSIVE if fewer than 4 are testable. If all 14 are testable,
VALIDATED needs 12 passes. Our pre-registered predictions: VALIDATED 50%, FAILED 35%,
INCONCLUSIVE 15%; median radius offset within ±5%, 75%.
