# Blind TESS test of the three ZTF eclipse candidates (pre-registration)

MV2, Munim, Inc. (mv2@munimtech.com), 2026-11-28 ~16:50 UTC. CC BY 4.0. Made with AI agents working in his
name; no human expert has checked it. Frozen before any TESS data of these stars was looked at by anyone
working for MV2. Job: `runbook/ztf-cands-tess-v1/` (vpt_followup 0.1.0 at pinned commit 0d8d4c5, unchanged;
targets in `fu_targets.csv`). Context: `findings/2026-11-28-ztf-shallow-flags-graded.md`.

## Frozen ephemerides (from ZTF only; BTJD = BJD - 2457000; Gaia time = BTJD + 1802.5)

| star | Gaia DR3 | TIC | T_min (BTJD) | P (d) | TESS sectors (TESScut) |
|---|---|---|---|---|---|
| UCAC4 583-070217 | 4535010166315168640 | 358858602 | 2929.0475 (= 389.7945 + 819 P) | 3.100431 | 26, 53, 54, 74, 80, 81 |
| TYC 2091-796-1 | 4576721896566803072 | 135364450 | 395.4568 | 12.421463 | 26, 40, 53, 79, 80 |
| UCAC4 677-002225 | 391817260687992960 | 440168538 | 395.2982 | 11.363060 | 57, 84 |

Exploratory (reported, not graded): Gaia DR3 4497399653101181184 (TIC 150450235; Gaia conjunction BTJD
393.1949, P 6.5640588) and Gaia DR3 4229808420168374400 (TIC 212684258; 395.1442, P 13.6706619). Controls: BN Scl
and HD 157949 (catalogued eclipsing binaries, expected periods 3.6505249 and 3.041 d), as in job sb1-new-ebs-tess-v1.

## Tests (per graded star)

- **T1 (detection at the ZTF period).** vpt_followup label is SURVIVES, EB_LIKE or SURVIVES_OTHER_P with
  period_factor 1 and |P_tess - P| / P <= 0.001.
- **T2 (timing).** gaia_offset_d (TESS epoch minus the frozen T_min, reduced modulo P, wrapped to (-P/2, P/2])
  satisfies |offset| <= max(0.06 d, 0.02 P): 0.062 d, 0.248 d and 0.227 d respectively.
- **CONFIRMED** = T1 and T2 and the job grade CONTROLS_PASS. T1 without T2 = "periodic at the ZTF period but
  off the ZTF timing" (reported as a failure of the ephemeris). NOT_DETECTED = failure for that star. NO_TESS
  or ERROR = untested.
- Reported, not graded: TESS depth, the depth at phase 0.5, odd/even depths, per-sector depths. For TYC
  2091-796-1 the folded plot is inspected for the secondary at +0.394 (Gaia's orbit: +0.383); vpt_followup
  measures the secondary only at phase 0.5, so this is a reported observation.

## Known limits of the tool, stated before the run

vpt_followup's box durations stop at 6 h and its detrending window is 0.75 d. Expected central eclipse lengths
are ~4.4 h (UCAC4 583-070217), ~7 h (UCAC4 677-002225) and ~9-10 h (TYC 2091-796-1), so for the two long
-period stars the measured depth will be biased low; detection should still exceed S/N 7 if the ZTF depths
(0.04-0.13 mag) are right. A NOT_DETECTED for a long-period star will be re-examined with a longer-duration
search before it is called a failure, and that re-examination will be labelled post hoc.

## Also in the job

`ztf_recheck.py` recomputes every hand-computed ZTF phase in `data/ztf-shallow-flags/ztf_faint_points.csv`
(mismatches > 0.0006 of an orbit are listed) and refits the ephemerides; `eba_scan.py` 0.2.0 searches every
text file of the Eclipses by Appointment catalogue at its HEAD commit, and IJspeert et al. (2024), for the
five stars' TIC and Gaia ids (with three positive controls each).
