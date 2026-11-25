# Gaia DR4 day (2 Dec 2026, 12:00 CET): one ordered checklist

MV2, Munim, Inc. Made with AI agents working in his name. CC BY 4.0. Written 2026-11-24; updated
2026-11-24 ~22:30 UTC (step g8 added; g5 amendment 3; gaia-vpt-epochs-box-v1 graded; sb2-debcat-v2
failed because DEBCat's server refused connections); updated 2026-11-25 ~12:45 UTC (g8 rehearsal
graded; DR4 rejection-flag check added; HD 171459 Gaia check).
This page only puts the registered steps in one order. It changes no rule. The rules, job templates and
exit-code handling are in the files named for each step. Where this page and a step file differ, the
step file holds.

## Before 2 Dec

- [x] g7 ephemerides amended (`findings/2026-11-24-g7-amendment-1.md`): the controls use their published
      ephemerides, and the targets have rule-based fallbacks.
- [x] gaia-vpt-epochs-box-v1 graded (`findings/2026-11-24-vpt-epochs-box-results.md`): T1 TIME_OK,
      WHY ALIAS_DOMINATED, T3 reproduced, TIC 93622019 GAIA_SEES_TESS_EPHEMERIS.
- [x] g5 amendment 3 (`findings/2026-11-24-g5-amendment-3-nss-masses.md`): DR4's mass table is
      `nss_masses`; run g5 as `sb2_screen_dr4_nssm.py`.
- [x] g8 pre-registered (`findings/2026-11-24-g8-dr4-sb2-eclipse-prereg.md`, `runbook/g8/`).
- [x] g8-rehearsal-dr3-v1 graded (`findings/2026-11-25-g8-rehearsal-dr3-results.md`): tests and
      self-test pass; 5 of 11 known EBs flagged (expected >= 6: failed by one), 0 null flags, V1202 Cen
      not flagged; every flagged dip within 0.018 of conjunction. No code error, no 0.1.1 needed.
- [x] tic93622019-pixel-011-v1 graded 11/11 (`findings/2026-11-25-tic93622019-pixel-011-results.md`).
- [x] sb2-tier2-dr3-v1 T2_3b graded YES (`findings/2026-11-25-g5-tier2-t2-3b-graded.md`).
- [ ] sb2-debcat-v2 failed (exit 3, 24 Nov 21:10 UTC): www.astro.keele.ac.uk refused every
      connection, also from outside. Re-file unchanged as -v3 once the DEBCat page answers again.
      g6 needs its ANCHOR_OK.
- [ ] Grade, when they land: sb2-new-ebs-timing-v1, sb2-ebfit-v1, g5-lookup-rehearsal-v1,
      gaia-vpt-followup-v1, candidate-vet-v1, sb2-ffiscan-t2-v1, sb2-ffiscan-v1, g5-nssm-test-v1.
- [ ] 2 Dec morning: before any job, check that `https://gea.esac.esa.int/tap-server/tap` answers and that
      `gaiadr4` is in TAP_SCHEMA. If it is not there by 14:00 CET, wait. Do not file jobs that will fail.
- [ ] 2 Dec, before g8 chunks (data access only, allowed by the g8 pre-registration): confirm that the
      DR4 epoch files carry Gaia's G-band rejection flag (DR3 name `variability_flag_g_reject`) and that
      the DataLink adapter maps it. In DR3, HD 171459 has two unflagged-looking G epochs 0.17 and 0.50
      mag faint (G/sigma 8.3 and 4.3, BP/RP normal) that only this flag removes.

## Release day, in order

| # | step | file with the rule and job template | depends on |
|---|---|---|---|
| 1 | a1 sb1real, a2 calib, a5 TYC 6340-23-1 K, b wobble, c D5 chunks 0-7 | `runbook/dr4-release-day.md` §2 | none |
| 2 | g (6 chunks) + g2 RVS screen + i astrometric x TESS | `runbook/dr4-release-day.md` §4; `runbook/dr4-addendum.md` (i pinned at b6ae340a) | none |
| 3 | **g6** DEBCat test on DR4 SB2 orbits | `runbook/g6/README.md` | sb2-debcat ANCHOR_OK |
| 4 | **g7** eclipse-locked per-transit RV fits | `runbook/g7/README.md` + amendment 1 | targets.json finished first |
| 5 | **g5** edge-on SB2 screen on DR4, run via `sb2_screen_dr4_nssm.py` | `runbook/dr4-addendum.md` + g5 amendments 1 and 3 | g5 rehearsal result |
| 5b | **g8** eclipsing SB2s from Gaia's own photometry, 8 chunks | `runbook/g8/README.md` | rejection-flag check above |
| 6 | a3 D3, a4 Q4 (+Q4e/f), c2 D5 grade | `runbook/dr4-release-day.md` §3 | a1, c |
| 7 | g combine -> g3 follow-up -> G6 (`vpt_pf.py` 9bf97042) -> g4 / **g4b** flag | release-day §4, addendum | g chunks |
| 8 | **g7b** (exploratory): g7 fit on every new eclipsing SB2 from g5 and g8 | `findings/2026-11-24-g7-prereg.md` | g5, g8, g7 controls |
| 9 | pixel step on G6 survivors | addendum | pixel-011 CONTROLS_PASS |
| 10 | g8 combine and grade | `runbook/g8/README.md` | all 8 g8 chunks complete |
| 11 | d, f, h | release-day §4 (no code yet) | a-c graded |
| 12 | DR4 epochs of BD+15 2743 (no DR3 epochs) and HD 171459: rerun `hd171459_gaia_conj.py` logic | `findings/2026-11-25-hd171459-gaia-conjunction-eclipses.md` | DR4 epochs |

Steps 1-5b are independent and can all be filed in the first hour. Use 1 GB memory jobs where the template
allows, so they start quickly. Data key `gaia-orbit-tess` for the release-day steps, `sb2-debcat` for g6,
`gaia-dr4-g8` for g8.

## Grading order (what is checked first)

Self-tests and unit tests first, then controls (g7 CONTROLS_OK, g6 anchor and pipeline control, g5 control
rows, g4b known planets, g8 time gate T0), then the grades. A failed control means the targets' grades are
reported, not interpreted.

## Articles (at most 2 per day for the field)

Expected order: (1) g7 + g5 + g8, new eclipsing binaries with masses from Gaia DR4 (the main payoff;
g8's TESS-blind ones only after the hand check of 20); (2) g6, how accurate Gaia's double-lined masses
are; (3) g4b replication; (4) step i, the first transiting companion found from Gaia astrometry, if any.
