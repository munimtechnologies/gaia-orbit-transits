# DR4 SB1-reality test, amendment 3: how D5 builds its pool (radius_flag before sampling)

2026-11-19, thirteen days before Gaia DR4 (2 December 2026). By MV2 of Munim, Inc.; made with AI
agents working in his name and not yet checked by a human expert. Text CC BY 4.0, code
Apache-2.0.

**Data seen when this was written:** none from DR4. From DR3: the public sb1_robust 0.2.0
chunks k0, k1 and k7 (already described in the interim notes). Chunk k2 came in after this
was written (about 04:40 UTC) and before it was committed. It is described in
`findings/2026-11-19-sb1-robust-k2-interim.md` and changes none of the rules below. No D5
quantity has been computed on any data. A DR3 dress rehearsal of the pool step (job
`gaia-d5pool-reh-v2`) had not run when this was committed. It was first filed as `-v1` and
re-filed after a fix to the unit test; the module itself did not change.

## What D5 says (unchanged)

From `findings/2026-11-18-dr4-sb1-reality-prereg.md`:

- **D5 (exploratory):** DR4's own low-mass RV orbits are purer than DR3's.
- **Pass rule:** ρ_DR4-new (new DR4 orbits, same cuts, not in DR3) > ρ_DR3.
- **Expectation:** D5 passes.

Amendment 1 of the sb1_robust pre-registration (`findings/2026-11-19-sb1-robust-amendment-1.md`)
added that "the DR4 transit-rate test (D5) applies the rule before sampling". This amendment
says exactly how. None of it changes the pass rule or the expectation.

## Rules

1. **Tables.** The pool is read from every DR4 table that can hold an SB1 orbit:
   `gaiadr4.nss_two_body_orbit`, `gaiadr4.rvs_two_body_orbit` (amendment 2) and, if it exists,
   `gaiadr4.nss_two_body_orbit_supp`. Each table is joined to `gaiadr4.gaia_source` and
   `gaiadr4.astrophysical_parameters`.
2. **Same cuts.** The WHERE clause is sb1_robust 0.2.0's, unchanged: SB1/SB1C, 1 ≤ P < 13 d,
   G ≤ 13 and K³P < 15,440. After it come `sb1_transit` 0.1.0's `star_physics` and
   `eligible`, imported unchanged: m2 sin i 0.005–0.10 M☉, R1 ≤ 2.5 R☉, log g ≥ 3.5 where
   given, and e < 0.9.
3. **No silent losses.** The run stops with exit 4 and lists what exists if any of these is
   missing:
   - a table or a column the rules use, including FLAME `mass_flame` / `radius_flame`,
     `radius_gspphot`, `logg_gspphot`, and the orbit's `eccentricity` / `arg_periastron`;
   - any SB1/SB1C row in either required orbit table (for example, if DR4 renames the
     solution types).

   A period bin that comes back at the archive's row cap (50,000) is split in two and
   queried again. It is never truncated.
4. **One row per source.** When a source has several orbit rows, the order is: table
   (`nss_two_body_orbit`, then `rvs_two_body_orbit`, then `_supp`), then solution type (SB1
   before SB1C), then larger significance. This is the same order as `dr4_sb1_reality`, and
   the row is never chosen by period or K.
5. **radius_flag before sampling.** `sb1_combine.radius_flag` (amendment 1: `clamped`,
   `giant_cmd`, `no_distance`) is imported and applied to every eligible star. It runs on
   the values `sb1_transit` derives for that star. Flagged stars leave the pool before the
   in-DR3 test and before the seeded order, so they never use search time. They are counted
   by reason in `d5_pool_summary.json`.
6. **"Not in DR3".** A DR4 source is **IN_DR3** if any of its DR3 neighbours within 1 arcsec
   (`gaiadr4.dr3_neighbourhood`) has an SB1 or SB1C row in `gaiadr3.nss_two_body_orbit`, at
   any period. Otherwise it is **NEW**. NEW sources with and without a DR3 neighbour are
   both counted, and both are in the pool. The rule is deliberately conservative: an orbit
   that DR3 had at another period does not count as new.
7. **Sampling and search.** The NEW pool is put in sb1_robust's seeded order (seed 20261119)
   and split into 8 chunks. Each chunk runs the sb1_robust 0.2.0 TESS search unchanged: same
   light-curve sources, up to 3 sectors, the median rule, period-shifted controls,
   injections, the 160-minute budget and the four positive controls. Every chunk records
   the pool's SHA-256, and the grade refuses chunks that disagree (exit 5).
8. **Grade.** The chunks are combined with `sb1_combine` (deduplicated by source_id).
   - ρ_DR4-new is the combined `rho_substellar_size`.
   - ρ_DR3 is sb1_combine's **amendment-1 (A1)** combined `rho_substellar_size` over all 8
     DR3 chunks. It uses the same trusted-radius population rule as this pool, so the
     comparison is like for like. If the 8 DR3 chunks are not all graded by then, D5 waits.
   - D5 counts only if C1 (at least 3 of 4 positive controls hit in each chunk that has
     data for 3) and C2 (control hit rate ≤ 3%) pass on the D5 chunks. Otherwise it is
     reported as not interpretable.
   - D5 passes if ρ_DR4-new > ρ_DR3. We also report whether the lower 95% bound of
     ρ_DR4-new lies above ρ_DR3, along with the BD / VLMS split and the split by orbit table.
   - In a correct run, re-applying the A1 rule at grade time removes nobody (`A1_noop`).
9. **Phases are descriptive only.** The phase check of `sb1_transit` assumes DR3's
   t_periastron reference (J2016.0). The DR4 column's TAP description is recorded, and D5
   never grades on phase labels.

## Rehearsal (DR3, before release)

`python dr4_d5_rate.py pool --schema dr3 --out-dir OUT` runs the same code on DR3, matching
each source to itself. It must give:

- **RH1:** the sb1_robust 0.2.0 pool, 6,434 eligible rows;
- **RH2:** every unflagged eligible star IN_DR3 (so the in-DR3 query path works);
- **RH3:** flagged counts that add up.

A failure is fixed and re-run before 2 December.

## Release day

```
python fetch_d5_deps.py
python dr4_d5_rate.py chunk --schema dr4 --chunk K --n-chunks 8 --out-dir /out     # K = 0..7
python dr4_d5_rate.py grade --chunk-dir k0 ... --chunk-dir k7 \
       --dr3-combined <sb1_combine combined_summary.json> --out-dir OUT
```

Exit 2 (archive down): re-file unchanged. Exit 4: the archive's real columns go into an
amendment 4 before any D5 number is read.

## What we expect, and why it might not matter as much as in DR3

Our expectation is unchanged: D5 passes. One thing works against the flag's importance in
DR4. FLAME covers about 500 million sources in DR4 (Creevey et al. 2026, arXiv:2607.00264),
far more than in DR3, so fewer stars should fall back to the main-sequence radius table that
the flag targets. We will report the flagged fraction either way.

Code: `dr4_d5_rate.py` 0.1.0 and `test_dr4_d5_rate.py` (fake archive, no network). They are
committed separately, only after the unit tests pass. The first attempt (04:52 UTC) was
refused because one assertion in the test also caught the TAP_SCHEMA column lookup for
`dr3_neighbourhood`; the module was not at fault.
