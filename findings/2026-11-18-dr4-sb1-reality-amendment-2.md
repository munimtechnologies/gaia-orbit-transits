# Amendment 2 to the DR4 SB1-reality pre-registration: the implementation rules of `dr4_sb1_reality.py` 0.1.0

2026-11-18, before Gaia DR4 (2 December 2026). No DR4 data have been seen. MV2 of Munim, Inc.;
made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0. This amends
`findings/2026-11-18-dr4-sb1-reality-prereg.md` and its amendment 1. Everything else there
stands. Each rule below is a choice the pre-registration left open; it is fixed now, in code
and in this text, so that it cannot be tuned after the DR4 orbits are seen.

## 1. Where DR4 orbits are read from

ESA's DR4 contents page (read again 2026-11-18) lists **two** tables of orbits that carry an
RV semi-amplitude:

- `gaiadr4.nss_two_body_orbit` (10.08, 5,901,111 rows): astrometric, spectroscopic and
  eclipsing two-body solutions and their combinations;
- `gaiadr4.rvs_two_body_orbit` (17.06, 638,966 rows): spectroscopic-binary solutions from
  the Line Integral Analysis modules (epoch RVS spectra cross-correlated with templates,
  combined with astrometric orbits).

The page does not say how they overlap. Reading only the first table could label real
orbits DROPPED. The rules are:

1. Tables are used in this order: `nss_two_body_orbit`, then `rvs_two_body_orbit`, then
   `nss_two_body_orbit_supp`. A later table is used for a source only when no earlier
   table has an RV orbit for it. Which table decided is recorded per source (`table4`) and
   counted in the summary.
2. Any of these tables that **exists** but lacks `source_id`, `period` and a
   semi-amplitude (`semi_amplitude_primary`, or both `c_thiele_innes` and
   `h_thiele_innes`) **stops the run** (exit 4) with the real column list. A table that
   does not exist is skipped and recorded.
3. Within one table, several rows for a source are ordered SB1, SB1C, AstroSpectroSB1,
   EclipsingSpectro, SB2, SB2C, then any other type, then by larger `significance`. A
   solution is **never** chosen by its period or by its agreement with DR3.

## 2. The DR4 semi-amplitude

- `semi_amplitude_primary` is used when it is finite and positive.
- Otherwise (AstroSpectroSB1 in DR3's data model) K is computed from the Thiele-Innes C and
  H elements, which are in AU: a₁ sin i = √(C² + H²) and
  K₁ = 2π a₁ sin i / (P √(1 − e²)). Its error propagates σ_C and σ_H only. Such sources are
  counted (`k_from_ch`).
- In the P and K rules, a missing published error counts as zero. The 0.2% (P) and 30% (K)
  floors then apply.

## 3. Which comes first, the orbit or the epoch count

A source with a DR4 RV orbit gets CONFIRMED, ALIAS or CHANGED from the orbit rules,
whatever its counted epoch number, because an orbit implies the epochs it was fitted to.
The "≥ 10 DR4 RV epochs" rule decides only between **DROPPED** and **UNTESTABLE** for
matched sources **without** a DR4 RV orbit. Unmatched or ambiguous sources are UNTESTABLE.
With the epoch step suspended (amendment 1, rule 4), every matched source without an orbit
is DROPPED. The report says so.

## 4. Finding the epoch RVs in DataLink

- DR3 has no epoch RVs, so the DR4 retrieval type cannot be known in advance. On release
  day the code asks the archive's own DataLink *links* service for one matched source. It
  takes the **only** listed `RETRIEVAL_TYPE` that matches `(RV|RADIAL).*EPOCH` or
  `EPOCH.*(RV|RADIAL)`.
- If none or several match, the run **stops** (exit 6) and records the list. It is then
  re-run with `--retrieval-type X` naming the type that ESA's documentation gives for
  `rvs_epoch_parameters_single`. If DataLink has no epoch RVs at all, it is re-run with
  `--suspend-epochs`, which is amendment 1 rule 4. Either flag is written into the output.
- Epoch rows must carry `source_id`, `radial_velocity`, `radial_velocity_error`,
  `outlier_status` and `emission_lines`, or the run stops (exit 4).
- The time column is the only column whose name contains "time" (excluding `_error` and
  `_flag`). If there are several, it is the only one that also contains "obs". Anything
  else stops the run.
- Requests carry at most 500 source_ids (ESA's limit is 5,000).

## 5. The epoch-RV fit

- The model is v = γ + a cos(2πt/P₃) + b sin(2πt/P₃), a weighted linear least-squares fit
  over the counted epochs (at least 4). K = √(a² + b²).
- σ_K comes from the covariance and is multiplied by √χ²_ν when χ²_ν > 1. It is never
  shrunk.
- Labels:
  - EPOCH_OK: K/σ_K ≥ 5 and |K − K₃| ≤ 3√(σ_K² + σ_K₃²);
  - EPOCH_DIFF: K/σ_K ≥ 5 but not consistent with K₃;
  - EPOCH_WEAK: 3 ≤ K/σ_K < 5;
  - EPOCH_FLAT: K/σ_K < 3;
  - EPOCH_NOFIT: fewer than 4 usable epochs.
- As pre-registered, disagreements with the table label are reported
  (`CONFIRMED_but_FLAT`, `DROPPED_but_OK`). The table label is used for the hypotheses.

## 6. D3 statistic

- ρ is sb1_robust 0.2.0's `rho_substellar_size`, the statistic its H1 uses, with its
  Garwood interval, computed by sb1_transit 0.1.0's `rate_summary`, unchanged.
- ρ_conf uses the sb1_robust rows (k0–k7, deduplicated by source_id, controls excluded)
  whose source is CONFIRMED. ρ_all uses all the rows. ρ_DR3 is the combined 0.2.0 point
  estimate.
- Pass: ρ_conf > ρ_all and ρ_conf's lower 95% bound > ρ_DR3 (`grade-tess` subcommand).

## 7. Sample check and the DR3 dress rehearsal

- S3 must reproduce sb1_robust 0.2.0's 6,434-star pool. Otherwise the run stops (exit 3),
  and archive trouble gives exit 2. The same ADQL and sb1_transit 0.1.0's eligibility are
  used, pinned to their published commits.
- Before 2 December, the same code runs with DR3 as the "new" release (job
  gaia-sb1real-reh-v1). It must pass:
  - **RH1**: the pool is 6,434;
  - **RH2**: every S3 source is matched (identity);
  - **RH3**: every S3 orbit comes back CONFIRMED;
  - **RH4**: the DataLink links service answers, and a 3-source epoch-photometry batch
    parses with a `source_id` column. This tests the transport only, since DR3 has no
    epoch RVs.
- If any check fails, the fix goes into a dated amendment 3 before release day.

## 8. Deferred, not changed

D5 compares DR4-new low-mass RV orbits with DR3's. It needs the sb1_robust query rewritten
for the DR4 tables once their columns are confirmed. The cuts and rules stay the 0.2.0 ones.
That code is still owed. No D5 rule changes.
