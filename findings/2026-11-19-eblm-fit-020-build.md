# eblm_fit 0.2.0: how the pre-registered fixes were built (before any holdout fit)

2026-11-19, about 23:40 UTC. By MV2 of Munim, Inc.; made with AI agents working in his name,
not checked by a human expert. Text CC BY 4.0, code Apache-2.0.

This note records exactly how `eblm_fit.py` 0.2.0 implements fixes (a)–(d) of
`findings/2026-11-19-eblm-holdout-prereg.md`. It was written **before** any holdout system
was fitted and **before** the holdout ids were resolved (job gaia-eblm-holdout-resolve-v1 has
not run). Nothing here was tuned on any holdout. The six systems of the failed first control
check motivated the fixes and are never used to validate them.

## The fixes as built
- **(a) Red noise in the ellipsoidal amplitude's error.** `err_a_ell` = the larger of
  (i) the white-noise error (as in 0.1.0) times a β factor and (ii) the segment-to-segment
  standard error of the amplitude.
  - β: residuals of the best model on the 10-minute time series, binned at P/16, P/8 and P/4;
    β = max over widths of rms(binned) / (rms(unbinned)/√n̄ · √(M/(M−1))), never below 1. Bins
    need at least 3 points and a width needs at least 8 bins.
  - Segments: TESS data split at gaps longer than 3 days, and any stretch longer than 30 days
    cut into equal parts of at most 27.4 days. A segment counts if it spans at least 1.5 orbits
    and has at least 200 points. The amplitude is refitted in each with the eclipse shape fixed;
    the standard error is the sample standard deviation over √n (needs 2 segments or more).
  - Both inputs are reported (`err_a_ell_white`, `beta_red`, `err_a_ell_seg`, `n_seg_amp`).
- **(b) Occultation phase.** The centre comes from Gaia's e and ω through the exact
  conjunction phases (transit at true anomaly π/2 − ω, occultation at 3π/2 − ω, the convention
  of `eblm_screen.conjunction_offset`; to first order 0.5 + (2/π)e cos ω). The occultation phase
  is then searched on a grid from −0.15 to +0.15 around that centre in steps of 0.0025 with the
  eclipse shape fixed, and the shape is refitted at the best phase. Reported: `phi2_center`,
  `phi2_fit`, `dchi2_phi2`. Searching for the best phase biases the occultation depth slightly
  upward, which can only make the TOO_LUMINOUS check stricter.
- **(c) Grazing before mass.** The verdict order is now: NO_ECLIPSE → TWIN_AT_2P → GRAZING →
  mass tension → TOO_LUMINOUS → radius classes. `mass_check` (MASS_OK, MASS_TENSION_HEAVIER,
  MASS_TENSION_LIGHTER, MASS_NA) is reported for every system, grazing or not.
- **(d) Tests.** `test_eblm_fit.py` (stdlib + numpy) runs as each job's first step.

## One addition the fixes require (e): eccentric geometry
Fix (b) moves the occultation for eccentric orbits, but an eccentric orbit also changes the
transit's chord speed and impact parameter, which 0.1.0 read as a circular a/R₁ and cos i. Fixing
the phase alone would leave the radius scale biased by (1 + e sin ω)/√(1 − e²). So 0.2.0 also:
- uses Gaia's eccentricity only when it is significant: e ≥ 3σ_e (or e ≥ 0.05 if σ_e is
  missing; e ≥ 0.95 is ignored); otherwise the orbit is treated as circular;
- converts the fitted chord-speed parameter A to a/R₁ = A √(1 − e²)/(1 + e sin ω) and the
  fitted impact parameter b to cos i = b (1 + e sin ω)/((a/R₁)(1 − e²));
- gives the occultation its own impact parameter b (1 + e sin ω)/(1 − e sin ω) and chord speed
  A (1 − e sin ω)/(1 + e sin ω).
With e = 0 every formula is 0.1.0's. This addition is written down here, before any holdout
fit, and is graded by the same pre-registered rule.

## Holdout wrapper
`eblm_holdout_fit.py` 0.1.0 (tests `test_eblm_holdout_fit.py`) fetches `eblm_fit.py` and
`eblm_screen.py` pinned to the commit that publishes 0.2.0, reads the committed
`holdout_ids.csv` (role = holdout only), adds Gaia's `eccentricity_error` and `arg_periastron`
to each row, fits, and applies the grade of the pre-registration unchanged: testable unless
UNTESTED or G; pass = C_NORMAL_COMPANION and |r2/R₂ − 1| ≤ 10%; PIPELINE_VALIDATED if at least 4
are testable and at least 80% pass. It also reports the median offset, m₂/M₂, and how many labels
change without the mass check.

## Order of work (unchanged)
1. gaia-eblm-holdout-resolve-v1 runs; its `holdout_ids.csv` and RC1 result are committed.
2. Only then is the holdout fit job filed, pinned to the 0.2.0 commit.
3. Every R₂ used in grading is re-checked against EBLM XIX Table 4 first.
