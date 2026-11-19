# Amendment 2 to the DR4 test of the DR3 eclipse deficit (calib-dr4): the cross-match id column

2026-11-19, 13 days before Gaia DR4 (2 December 2026). No DR4 catalogue data exist or have been
seen. MV2 of Munim, Inc.; made with AI agents working in his name, not yet checked by a human
expert. Text CC BY 4.0, code Apache-2.0. This amends `findings/2026-11-18-calib-dr4-prereg.md`
and amendment 1. **No test, threshold or prediction changes.** It also applies to the other
release-day modules that read `gaiadr4.dr3_neighbourhood` (the SB1-reality test and D5).

## What the dress rehearsal found
The DR3 dress rehearsal (job gaia-calibdr4-reh-v1, finished 19 Nov 09:57 UTC on Tango) rebuilt
the sample exactly (162 targets, 58 eclipsing, no problems: `data/calibdr4-reh-v1/reproduction.json`)
and then stopped, as designed, at the schema check (exit 4):

> SCHEMA missing: gaiadr3.dr2_neighbourhood.source_id

TAP_SCHEMA lists the real columns of `gaiadr3.dr2_neighbourhood` as `angular_distance`,
`dr2_source_id`, `dr3_source_id`, `magnitude_difference` and `proper_motion_propagation`.
ESA names the new release's identifier `dr3_source_id`. There is no `source_id`.

Amendment 1 had assumed that `gaiadr4.dr3_neighbourhood` would have a `source_id` column for
DR4. Following ESA's own pattern, it will more likely be called `dr4_source_id`. Had that
assumption stood, the release-day runs of `calib_dr4_run.py`, `dr4_sb1_reality.py` and
`dr4_d5_rate.py` would all have stopped at exit 4 on 2 December. The dress rehearsal did its
job.

## Rule (fixed now, before any DR4 data)
- The new-release id column of a neighbourhood table is read from TAP_SCHEMA. It must be
  **the first present** of a fixed, ordered list:
  - DR4 (`gaiadr4.dr3_neighbourhood`): `dr4_source_id`, then `source_id`;
  - DR3 rehearsal (`gaiadr3.dr2_neighbourhood`): `dr3_source_id`, then `source_id`.
- If neither name exists, the run stops (exit 4) and lists the real columns, as before.
  Nothing outside that list is ever guessed.
- The old-release column (`dr3_source_id` for DR4), `angular_distance` and
  `magnitude_difference` are still required by name.
- The resolved name is written into each run's summary.
- The DR3 ← DR2 cross-match smoke test in the calib-dr4 rehearsal reports only. A TAP failure
  there is now recorded rather than stopping the rehearsal. The rehearsal checks RH1–RH4 do
  not depend on it.

## Code
- `dr4_fetch.py` 0.2.0:
  - adds `XMATCH_NEW_ID_CANDIDATES`, `resolve_new_id`, `set_xmatch_new_id` and
    `ensure_xmatch_new_id`;
  - `check_schema` resolves the id column;
  - `fetch_matches` resolves it on first use, so callers that skip `check_schema` (the
    wobble test's release mode) also get the real column.
- `calib_dr4_run.py` 0.1.1: the smoke query uses the resolved DR3 column and cannot stop the
  rehearsal.
- `dr4_sb1_reality.py` 0.1.1 and `dr4_d5_rate.py` 0.1.1: their schema checks use
  `resolve_new_id`. Nothing else changed.
- Tests (standard library, offline):
  - `test_dr4_fetch.py` covers the real DR3 column list, the DR4 order, the stop when no
    candidate exists, and one TAP_SCHEMA lookup per process;
  - `test_calib_dr4_run.py` covers the smoke query and its failure;
  - `test_xmatch_new_id.py` and `test_d5_xmatch_new_id.py` run the SB1-reality and D5 fakes
    end to end with a `dr4_source_id` table.
- The release-day helper `fetch_release.py` will be re-pinned to the commit that publishes
  these files. Its pins are full SHAs, so this can only happen after the commit exists.

## Re-run
The rehearsal is re-filed as gaia-calibdr4-reh-v2 with the fixed code. If RH1–RH4 do not all
pass, the code is fixed and the rehearsal re-run before 2 December, as amendment 1 requires.
