# Amendment 1 to the DR4 SB1-reality pre-registration: epoch RVs come through DataLink

2026-11-18, before Gaia DR4 (2 December 2026). No DR4 data have been seen. MV2 of Munim, Inc.;
made with AI agents working in his name. Text CC BY 4.0. This amends
`findings/2026-11-18-dr4-sb1-reality-prereg.md`. Everything else there stands.

## What changed and why

The pre-registration assumed DR4 epoch radial velocities could be queried by TAP. ESA's
DR4 contents page (read 2026-11-18) shows they cannot.

- **`rvs_epoch_parameters_single`** (table 17.02; 6,910,423,894 rows, 323 GB) is served
  only through **DataLink**, per source. So is `rvs_epoch_parameters_double` (17.01, 787,312
  rows).
- The orbit tables (`nss_two_body_orbit`, `nss_non_linear_spectro`) and the cross-match
  (`dr3_neighbourhood`) are TAP tables.

## Rules (fixed now)

1. The cross-match, labels and hypotheses are unchanged. The match and solution rules are
   those of `dr4_fetch.py` 0.1.0 (see `findings/2026-11-18-calib-dr4-amendment-1.md`,
   section 2), except that any solution type with P and K counts here, as the
   pre-registration says.
2. **Epoch RVs** come from the Gaia archive's DataLink service, for testable S3 sources
   only. They are requested in batches of ≤ 500 source_ids, never as a bulk download. The
   DataLink retrieval type and the per-request limit are taken from the DR4 archive's own
   documentation on release day and recorded in the run's output.
3. **Counting epochs** (for the "≥ 10 DR4 RV epochs" rule): a transit counts if it is in
   `rvs_epoch_parameters_single` with a finite radial velocity, is not flagged in
   `outlier_status`, and has `emission_lines` false. The DR4 documentation says the
   published combined RV uses the same exclusions. Double-lined transits
   (`rvs_epoch_parameters_double`) do not count, and their number is reported.
4. If DataLink is unavailable or refuses the batches on release day, the epoch-RV check
   and the "≥ 10 epochs" rule are **suspended, not replaced**. A source is then testable if
   it is matched. R0 is graded on that basis, and the report says so. The hypotheses
   D1–D5 use the orbit tables alone, as the pre-registration's last limit already allows.
