# Runbook step g7 (Gaia DR4 day, 2 Dec 2026 after 12:00 CET): eclipse-locked per-transit RV fits

MV2, Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Registered in `findings/2026-11-24-g7-prereg.md`; ephemerides as amended in
`findings/2026-11-24-g7-amendment-1.md` (24 Nov, before DR4).

1. Before reading any DR4 velocity, finish `runbook/g7/targets.json`:
   - Controls (ZZ Boo, CW Eri, EY Cep, BK Peg): already filled from their published ephemerides.
     Do not change them.
   - Targets: if sb2-new-ebs-timing-v1 ended CONTROLS_OK, replace P, t_conj and eph_sigma of
     HD 250735, CD-28 7251 and TYC 3616-2395-1 with its joint ephemeris (family A time moved to the
     cycle nearest BTJD 866; eph_sigma = its propagated 1σ at BTJD 866, minimum 0.001 d). If it did not,
     keep the amendment-1 fallback values already in the file. For CD-28 7251 on the fallback,
     the conjunction grade C is not graded.
   - Inclinations: from sb2-ebfit-v1 if CONTROLS_OK, else leave FILL (minimum masses only).
   Commit the finished file first.
2. File job **g7-rvfit-dr4-v1**: workdir with `sb2_rvfit.py`, `test_sb2_rvfit.py`,
   `runbook/g7/g7_run.py`, `runbook/g7/targets.json` (all flat in the workdir); image python:3.12;
   no pip needed; run steps:
   - `python -m unittest -v test_sb2_rvfit`
   - `python g7_run.py --targets targets.json --out-dir /out`
   - memory 1 GB, network true, timeout 60 min.
3. Exit 4: read `stars[].table.header` in `/out/g7_summary.json`, then write a schema amendment
   (new names in `map_columns`, with a test), and file -v2. A DataLink 5xx on day 1: re-file unchanged.
4. Grade from `g7_summary.json`: self_test.pass, controls.CONTROLS_OK, then for each target
   conj_grade (not for CD-28 7251 on the fallback), vs_dr4_orbit.K_OK and masses. Save
   `rv_pairs_*.csv` to `data/g7-rvfit-dr4-v1/`. Gaia data are CC BY-SA 3.0 IGO; credit ESA/Gaia/DPAC.
