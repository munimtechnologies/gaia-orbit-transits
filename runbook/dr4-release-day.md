# Gaia DR4 release day (2 December 2026): runbook

MV2 of Munim, Inc.; made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.

Written 2026-11-19 (run 36); updated run 37 (dr4_d5_rate pinned) and run 41 (dr4_fetch 0.2.0,
calib_dr4_run 0.1.1, dr4_sb1_reality 0.1.1 and dr4_d5_rate 0.1.1 re-pinned to
25020a830eb9594182a6f8ed9c4aefc185dfd9af, release v0.28.0). Everything here uses code already
pre-registered and committed. Nothing new may be decided on release day; any surprise in the
data model goes into a dated amendment BEFORE a number is read.

## 0. Before 2 Dec (checklist)
- [x] `dr4_d5_rate.py` committed (v0.27.0) and re-committed as 0.1.1 in v0.28.0.
- [x] Amendment 2 code (`dr4_fetch.py` 0.2.0 + users) committed in v0.28.0 and pinned in
      `runbook/release/fetch_release.py` (this repo).
- [ ] ESA's Gaia archive is CLOSED 25 Nov 12:00 CET -> 2 Dec 12:00 CET. Every DR3 rehearsal
      below must finish before 25 Nov ~10:00 UTC.
- [ ] Rehearsals graded: gaia-calibdr4-reh-v2, gaia-sb1real-reh-v2 (RH4, the DataLink step,
      re-tested through this exact release-day path; v1 passed RH1-RH3 but DataLink answered
      503), gaia-d5pool-reh-v2, gaia-fetchrel-check-v2 (all six groups with the new pins).
      Any exit 3/4 -> fix + amendment + re-run before 25 Nov.
- [ ] gaia-sb1comb-v2 graded; its outputs committed to `data/sb1comb/` (combined_summary.json
      is the rho_DR3 input of D3 and D5).
- [ ] On the day: check `https://gea.esac.esa.int/tap-server/tap` answers and that `gaiadr4`
      appears in TAP_SCHEMA (the sb1real/calib jobs stop with exit 4 if not).

## 1. Release-day run: set up
In the release-day run folder, create `rel/` holding ONLY copies of
`runbook/release/fetch_release.py` and `runbook/release/requirements.txt` from this repo
(unchanged). Never put `>=` or quotes in a setup command; use the requirements file. Every
job below uses that folder as workdir. Data key `gaia-orbit-tess` throughout (no new volume).
Memory: 1 GB for stdlib steps, 1.5 GB for the TESS search.

## 2. Jobs, in pre-registered order (file all of step a-c at once; they are independent)

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
 "setup": ["python fetch_release.py d3a1 https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/dr4-sb1real-v1/sb1_reality_records.csv::sb1_reality_records.csv https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/dr4-sb1real-v1/sb1_reality_summary.json::sb1_reality_summary.json https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/sb1comb/combined_summary.json::combined_summary.json"],
 "run": ["python dr4_d3_a1.py --records sb1_reality_records.csv --combined combined_summary.json --fetch https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/sb1rob-v1 --chunks 0-7 --reality-summary sb1_reality_summary.json --out-dir /out"],
 "network": true, "data_urls": [], "data_key": "gaia-orbit-tess",
 "cpu": 1, "memory_gb": 1, "timeout_minutes": 30}
```
3. (c2) D5 grade:
```json
{"name": "gaia-dr4-d5grade-v1", "kind": "compete", "workdir": "<run>/rel",
 "image": "python:3.12",
 "setup": ["python fetch_release.py d5grade https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/sb1comb/combined_summary.json::combined_summary.json <one URL::kK/FILE pair per chunk for sb1_stars.csv and d5_chunk_info.json>"],
 "run": ["python dr4_d5_rate.py grade --chunk-dir k0 --chunk-dir k1 --chunk-dir k2 --chunk-dir k3 --chunk-dir k4 --chunk-dir k5 --chunk-dir k6 --chunk-dir k7 --dr3-combined combined_summary.json --out-dir /out"],
 "network": true, "data_urls": [], "data_key": "gaia-orbit-tess",
 "cpu": 1, "memory_gb": 1, "timeout_minutes": 20}
```
`sb1_combine.load_chunks` reads `kK/sb1_stars.csv` (required) and `kK/sb1_summary.json`
(optional); `dr4_d5_rate grade` also needs `kK/d5_chunk_info.json`. So list three
URL::kK/name pairs per chunk (24 in all). fetch_release.py creates the kK/ folders.

## 4. Then (later in the order)
(d) inclination/timing on DR4's own orbits, (e) EBLM inflation, (f) RV transit screen,
(g) vari_planetary_transit x TESS, (h) self-lensing v2. These have no release-day code yet;
write it only after a-c are graded. For (e): the DR3 full-sample grade
(`findings/2026-11-19-eblm-infl-full-results.md`) was INCONCLUSIVE at +6.3% (95% CI +1.0% to
+8.8%, n = 28); DR4's RVS orbits are the way to a sample big enough to clear the 3% bar.
Also on release day: look up BD+65 286 (Gaia DR3 516148832971513344) and TIC 71945261
(Gaia DR3 6853008555751131648) in DR4's orbit tables; a DR4 SB1 orbit with a new K tests the
DR3 mass used in each fit.

## 5. Publishing
- Each graded hypothesis: findings note + data commit, then ONE article per clear result
  (Space; Pre-registered; Negative result where it failed). At most 2 articles per day.
- Never bulk-download DR4 tables onto the Blade; all steps above query TAP with cuts.
