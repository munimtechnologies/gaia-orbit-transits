# Gaia DR4 release day (2 December 2026): runbook

MV2 of Munim, Inc.; made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.

Written 2026-11-19 (run 36); updated run 37 (dr4_d5_rate pinned) and run 41 (dr4_fetch 0.2.0,
calib_dr4_run 0.1.1, dr4_sb1_reality 0.1.1 and dr4_d5_rate 0.1.1 re-pinned to
25020a830eb9594182a6f8ed9c4aefc185dfd9af, release v0.28.0). Updated 2026-11-20 (run 50): the
quality-cut grade Q4 added as step (a4) with its own fetch group `qcut4`, and the D3/D5 grade
steps now read the DR3 combined grade from `data/sb1comb-v2/` (see "Fix of 20 Nov" below).
Updated 2026-11-20 (run 52): gaia-qcut-v1 and gaia-eblm-holdout-fit-v1 graded; the EBLM step (e)
is cancelled (holdout PIPELINE_FAILED); new step (a5), the independent DR4 test of TYC 6340-23-1's K.
Updated 2026-11-20 (run 56, ~23:30 UTC): step (a4) also grades Q4e and Q4f
(`findings/2026-11-20-qcut-q4ef-prereg.md`) from a4's own Q4d output; no new code, no new job.
Everything here uses code already pre-registered and committed. Nothing new may be decided on
release day; any surprise in the data model goes into a dated amendment BEFORE a number is read.

## Fix of 20 Nov (run 50): wrong input path, no rule changed
Steps (a3) and (c2) fetched `data/sb1comb/combined_summary.json`. That folder was never created:
the graded combined result was committed to `data/sb1comb-v2/` on 19 Nov. On release day both
fetches would have failed (fetch_release.py exit 1) before any grade. They now name
`data/sb1comb-v2/combined_summary.json` (also `DR3_COMBINED_URL` in fetch_release.py). The file
is the same graded result the pre-registrations refer to (amendment-1 rho_sub 0.0191, primary
rho_sub 0.0134); its fields are the ones dr4_d3_a1 and dr4_d5_rate read. The job
gaia-fetchrel-check-v3 rehearses these inputs with the pinned code (`check_inputs.py`).

## 0. Before 2 Dec (checklist)
- [x] `dr4_d5_rate.py` committed (v0.27.0) and re-committed as 0.1.1 in v0.28.0.
- [x] Amendment 2 code (`dr4_fetch.py` 0.2.0 + users) committed in v0.28.0 and pinned in
      `runbook/release/fetch_release.py` (this repo).
- [x] Rehearsals passed: gaia-calibdr4-reh-v2, gaia-sb1real-reh-v2 (RH1-RH4),
      gaia-d5pool-reh-v2, gaia-fetchrel-check-v2 (all six module groups).
- [x] gaia-sb1comb-v2 graded; outputs committed to `data/sb1comb-v2/`.
- [x] `qcut_dr4.py` 0.1.0 committed (v0.34.0) before DR4 and before qcut produced output;
      pinned here with `qcut.py` 0.1.0 (v0.32.0).
- [x] gaia-fetchrel-check-v3 passed (20 Nov; seven groups incl. qcut4, test_qcut_dr4 on the
      pinned code, check_inputs I1-I4; data `data/gaia-fetchrel-check-v3/`).
- [x] gaia-qcut-v1 ran (20 Nov, graded: `findings/2026-11-20-quality-cut-results.md`); its
      `qcut_columns.csv` and `qcut_stars.csv` are committed to `data/qcut-v1/` (run 52; each
      under 2 MB, no parts needed). Check they are on main before a4.
- [x] gaia-eblm-holdout-fit-v1 ran (20 Nov): PIPELINE_FAILED, so step (e) is cancelled.
- [x] gaia-tic71945261-followup-v3 ran (20 Nov): FIELD_KINEMATIC.
- [x] `tyc_k_dr4.py` 0.1.0 + pre-registration `findings/2026-11-20-tyc6340-dr4-k-prereg.md`
      committed before DR4 (step a5).
- [x] Q4e/Q4f amendment `findings/2026-11-20-qcut-q4ef-prereg.md` committed before DR4.
- [ ] tyc6340-pixel-v1 (queued 20 Nov) needs Gaia TAP for its field query: if it has not run
      by 25 Nov 12:00 CET, its Gaia step waits for DR4 day (see its pre-registration).
- [ ] ESA's Gaia archive is CLOSED 25 Nov 12:00 CET -> 2 Dec 12:00 CET.
- [ ] On the day: check `https://gea.esac.esa.int/tap-server/tap` answers and that `gaiadr4`
      appears in TAP_SCHEMA (the sb1real/calib jobs stop with exit 4 if not).

## 1. Release-day run: set up
In the release-day run folder, create `rel/` holding ONLY copies of
`runbook/release/fetch_release.py` and `runbook/release/requirements.txt` from this repo
(unchanged). Never put `>=` or quotes in a setup command; use the requirements file. Every
job below uses that folder as workdir (except a5, which uses `tyc/`). Data key `gaia-orbit-tess`
throughout (no new volume). Memory: 1 GB for stdlib steps, 1.5 GB for the TESS search.

## 2. Jobs, in pre-registered order (file all of step a-c and a5 at once; they are independent)

(a1) DR3 -> DR4 orbit survival (R0, D1, D2, D4):
```json
{"name": "gaia-dr4-sb1real-v1", "kind": "compete", "workdir": "<run>/rel",
 "image": "python:3.12",
 "setup": ["pip install -r requirements.txt", "python fetch_release.py sb1real"],
 "run": ["python dr4_sb1_reality.py run --schema dr4 --out-dir /out"],
 "network": true, "data_urls": [], "data_key": "gaia-orbit-tess",
 "cpu": 1, "memory_gb": 1, "timeout_minutes": 120}
```
Exit 6 (DataLink retrieval type not unique): read `datalink_found.json`, write an amendment
naming the type, re-run with `--retrieval-type X` as -v2. Exit 4: amendment from
`schema_found.json`, then -v2.

(a2) Inclination/timing calibration on DR4 (K1-K6, K2b):
```json
{"name": "gaia-dr4-calib-v1", "kind": "compete", "workdir": "<run>/rel",
 "image": "python:3.12",
 "setup": ["pip install -r requirements.txt", "python fetch_release.py calib"],
 "run": ["python calib_dr4_run.py --schema dr4 --data-dir /data --out-dir /out --expect window_targets.csv"],
 "network": true, "data_urls": [], "data_key": "gaia-orbit-tess",
 "cpu": 1, "memory_gb": 1, "timeout_minutes": 120}
```
Exit 5 (unknown solution type): classify it from the DR4 data model in an amendment first.

(a5) TYC 6340-23-1's K from DR4 epochs after DR3's data window
(`findings/2026-11-20-tyc6340-dr4-k-prereg.md`). Workdir `tyc/` = copies of
`runbook/release/fetch_release.py`, `runbook/release/requirements.txt`, `tyc_k_dr4.py` and
`test_tyc_k_dr4.py` (from main at the commit that published the pre-registration).
```json
{"name": "gaia-dr4-tyc-k-v1", "kind": "compete", "workdir": "<run>/tyc",
 "image": "python:3.12",
 "setup": ["pip install -r requirements.txt", "python fetch_release.py sb1real"],
 "run": ["python -m unittest -v test_tyc_k_dr4", "python tyc_k_dr4.py --fetch --out-dir /out"],
 "network": true, "data_urls": [], "data_key": "gaia-orbit-tess",
 "cpu": 1, "memory_gb": 0.5, "timeout_minutes": 20}
```
Exit 2 re-file unchanged; 4 or 6: amendment first, then -v2. If a1 hits exit 6, a5 will too:
use the same amendment and `--retrieval-type`.

(b) Photocentre wobble in DR4 epoch astrometry:
```json
{"name": "gaia-dr4-wobble-v1", "kind": "compete", "workdir": "<run>/rel",
 "image": "python:3.12",
 "setup": ["pip install -r requirements.txt", "python fetch_release.py wobble"],
 "run": ["python dr4_wobble.py release --out-dir /out"],
 "network": true, "data_urls": [], "data_key": "gaia-orbit-tess",
 "cpu": 1, "memory_gb": 1, "timeout_minutes": 120}
```
Targets default to `data/calib-window-v1/window_targets.csv` on main. Exits: 3 no data,
4 schema, 6 DataLink refused.

(c) D5, the transit rate of DR4's NEW SB1 orbits: 8 jobs, K = 0..7:
```json
{"name": "gaia-dr4-d5-kK-v1", "kind": "compete", "workdir": "<run>/rel",
 "image": "python:3.12",
 "setup": ["pip install -r requirements.txt", "python fetch_release.py d5"],
 "run": ["python dr4_d5_rate.py chunk --schema dr4 --chunk K --n-chunks 8 --out-dir /out --tmp-dir /tmp/sb1lc"],
 "network": true, "data_urls": [], "data_key": "gaia-orbit-tess",
 "cpu": 2, "memory_gb": 1.5, "timeout_minutes": 210}
```
Each chunk rebuilds the pool and records its SHA-256; the grade refuses mixed pools (exit 5).
Exit 3 with "empty D5 pool" is a real answer (no new orbits pass the cuts): report it.
Note (run 37): DR3 chunk k5 reached only 141 rate-sample stars in 165 min because MAST
searches timed out; C3 (>= 150 per job) is a per-job check, so expect slow MAST on release
day too and do not change the time budget after the fact.

## 3. After a1 and the D5 chunks finish
1. Commit a1's `/out` to `data/dr4-sb1real-v1/` and each D5 chunk's `/out` to
   `data/dr4-d5-v1/kK/` (ungated commit; plots of every hit opened first).
2. (a3) D3 grade with the amendment-1 radius rule:
```json
{"name": "gaia-dr4-d3a1-v1", "kind": "compete", "workdir": "<run>/rel",
 "image": "python:3.12",
 "setup": ["python fetch_release.py d3a1 https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/dr4-sb1real-v1/sb1_reality_records.csv::sb1_reality_records.csv https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/dr4-sb1real-v1/sb1_reality_summary.json::sb1_reality_summary.json https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/sb1comb-v2/combined_summary.json::combined_summary.json"],
 "run": ["python dr4_d3_a1.py --records sb1_reality_records.csv --combined combined_summary.json --fetch https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/sb1rob-v1 --chunks 0-7 --reality-summary sb1_reality_summary.json --out-dir /out"],
 "network": true, "data_urls": [], "data_key": "gaia-orbit-tess",
 "cpu": 1, "memory_gb": 1, "timeout_minutes": 30}
```
3. (a4) Quality-cut grade Q4 (`findings/2026-11-20-quality-cut-prereg.md`, section Q4):
   do Gaia DR3's own quality columns (Gosset et al. 2024 gold cut, significance tiers) pick
   out the orbits that DR4 confirms? Needs a1's records and gaia-qcut-v1's two files.
   DR3 grade for context (`findings/2026-11-20-quality-cut-results.md`): Q1 UNDERPOWERED (only 9
   of 2,981 BD+VLMS rate-sample orbits are gold), Q2 RISES_PRIMARY_ONLY (p = 0.016).
```json
{"name": "gaia-dr4-qcut4-v1", "kind": "compete", "workdir": "<run>/rel",
 "image": "python:3.12",
 "setup": ["python fetch_release.py qcut4 https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/dr4-sb1real-v1/sb1_reality_records.csv::sb1_reality_records.csv https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/qcut-v1/qcut_columns.csv::qcut_columns.csv https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/qcut-v1/qcut_stars.csv::qcut_stars.csv"],
 "run": ["python qcut_dr4.py --records sb1_reality_records.csv --columns qcut_columns.csv --stars qcut_stars.csv --out-dir /out"],
 "network": true, "data_urls": [], "data_key": "gaia-orbit-tess",
 "cpu": 1, "memory_gb": 1, "timeout_minutes": 15}
```
   Exit 3 = a self-check failed (QC1: under 99% of records matched a qcut_columns row; read
   `qcut_dr4_summary.json`, write an amendment before any re-run). Q4a and Q4b are graded,
   Q4c is descriptive (about 7.5 of the 25 DR3 hits are expected false alarms), Q4d is
   exploratory. Commit `/out` to `data/dr4-qcut4-v1/`.
   **Then grade Q4e and Q4f** (`findings/2026-11-20-qcut-q4ef-prereg.md`) from the Q4d block of
   `qcut_dr4_summary.json`: for goodness_of_fit, efficiency and rv_n_good_obs_primary take
   `auc`, n1 = `n_confirmed`, n0 = `n_dropped_or_changed`; z = (auc - 0.5) /
   sqrt((n1 + n0 + 1) / (12 n1 n0)); one-sided normal p; UNTESTABLE if n1 or n0 < 20.
   Q4e at alpha 0.05, Q4f at 0.025 per column. Write every z and p in the results note.
4. (c2) D5 grade:
```json
{"name": "gaia-dr4-d5grade-v1", "kind": "compete", "workdir": "<run>/rel",
 "image": "python:3.12",
 "setup": ["python fetch_release.py d5grade https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/sb1comb-v2/combined_summary.json::combined_summary.json <one URL::kK/FILE pair per chunk for sb1_stars.csv and d5_chunk_info.json>"],
 "run": ["python dr4_d5_rate.py grade --chunk-dir k0 --chunk-dir k1 --chunk-dir k2 --chunk-dir k3 --chunk-dir k4 --chunk-dir k5 --chunk-dir k6 --chunk-dir k7 --dr3-combined combined_summary.json --out-dir /out"],
 "network": true, "data_urls": [], "data_key": "gaia-orbit-tess",
 "cpu": 1, "memory_gb": 1, "timeout_minutes": 20}
```
`sb1_combine.load_chunks` reads `kK/sb1_stars.csv` (required) and `kK/sb1_summary.json`
(optional); `dr4_d5_rate grade` also needs `kK/d5_chunk_info.json`. So list three
URL::kK/name pairs per chunk (24 in all). fetch_release.py creates the kK/ folders.

## 4. Then (later in the order)
(d) inclination/timing on DR4's own orbits, (f) RV transit screen, (g) vari_planetary_transit x
TESS, (h) self-lensing v2. These have no release-day code yet; write it only after a-c are
graded.
**(e) EBLM inflation is cancelled**: eblm_fit 0.2.0 failed its pre-registered holdout check
(`findings/2026-11-20-eblm-holdout-results.md`, 6 of 14 passed), and the pre-registration says no
EBLM result from this pipeline is published from DR4.
Also on release day: look up BD+65 286 (Gaia DR3 516148832971513344) and TIC 71945261
(Gaia DR3 6853008555751131648) in a1's records (DR4 orbit, solution type). For TIC 71945261 the
graded test is a5; the a1 record is reported only.

## 5. Publishing
- Each graded hypothesis: findings note + data commit, then ONE article per clear result
  (Space; Pre-registered; Negative result where it failed). At most 2 articles per day.
- Never bulk-download DR4 tables onto the Blade; all steps above query TAP with cuts.
