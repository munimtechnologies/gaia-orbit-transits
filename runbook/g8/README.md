# Step g8 on Gaia DR4 day: eclipsing double-lined binaries from Gaia's own photometry

MV2, Munim, Inc. Made with AI agents working in his name. CC BY 4.0. Written 2026-11-24.
Rule, grades and predictions: `findings/2026-11-24-g8-dr4-sb2-eclipse-prereg.md`. Code:
`sb2_ecl_dr4.py` 0.1.0 (repository root).

## Order

1. After `gaiadr4` appears in TAP_SCHEMA (checklist), file the 8 chunk jobs from `job-chunk.json`:
   names `g8-dr4-c0-v1` ... `g8-dr4-c7-v1`, with `--chunk 0` ... `--chunk 7`. 1 GB each, all with
   data key `gaia-dr4-g8` (epoch cache `/data/g8-epochs`, results `/data/g8-results`).
2. Exit 4 (schema gate G0): write a column adapter, then re-file. Exit 2 (data unavailable, e.g.
   no DataLink template returned DR4 epochs for the control star): check the DataLink URL by hand,
   pass it with `--datalink-template`, re-file. Exit 3: self-test failed, stop and read the log.
3. A chunk that stops at its deadline (`meta.stopped_at_deadline` in its summary) is re-filed
   as `-v2`; the cache makes it continue where it stopped.
4. When all 8 chunks are complete (or on 9 December), file `job-combine.json` (`g8-dr4-combine-v1`)
   and grade from `g8_summary.json`: T0 first; if neither reference passes, report, do not interpret.
5. Hand-check a random 20 NEW stars before any public claim.

`job-chunk.json` and `job-combine.json` are templates: copy them and `fetch_pinned.py` into a
run's folder, set the chunk number, the job name and the repository commit to fetch (the same
commit for all chunks and the combine job).
