# Gaia DR4 day (2 Dec 2026, 12:00 CET): one ordered checklist

MV2, Munim, Inc. Made with AI agents working in his name. CC BY 4.0. Written 2026-11-24.
This page only puts the registered steps in one order. It changes no rule. The rules, job templates and
exit-code handling are in the files named for each step. Where this page and a step file differ, the
step file holds.

## Before 2 Dec

- [x] g7 ephemerides amended (`findings/2026-11-24-g7-amendment-1.md`): the controls use their published
      ephemerides, and the targets have rule-based fallbacks.
- [ ] Grade, when they land: sb2-new-ebs-timing-v1 (fixes the g7 target ephemerides if CONTROLS_OK),
      sb2-ebfit-v1 (g7 inclinations), sb2-debcat-v2 (g6 needs ANCHOR_OK), g5-lookup-rehearsal-v1
      (g5 lookups), gaia-vpt-epochs-box-v1, tic93622019-pixel-011-v1 (pixel step), gaia-vpt-followup-v1
      (g3 version).
- [ ] 2 Dec morning: before any job, check that `https://gea.esac.esa.int/tap-server/tap` answers and that
      `gaiadr4` is in TAP_SCHEMA. If it is not there by 14:00 CET, wait. Do not file jobs that will fail.

## Release day, in order

| # | step | file with the rule and job template | depends on |
|---|---|---|---|
| 1 | a1 sb1real, a2 calib, a5 TYC 6340-23-1 K, b wobble, c D5 chunks 0-7 | `runbook/dr4-release-day.md` §2 | none |
| 2 | g (6 chunks) + g2 RVS screen + i astrometric x TESS | `runbook/dr4-release-day.md` §4; `runbook/dr4-addendum.md` (i pinned at b6ae340a) | none |
| 3 | **g6** DEBCat test on DR4 SB2 orbits | `runbook/g6/README.md` | sb2-debcat-v2 ANCHOR_OK |
| 4 | **g7** eclipse-locked per-transit RV fits | `runbook/g7/README.md` + amendment 1 | targets.json finished first |
| 5 | **g5** edge-on SB2 screen on DR4 | `runbook/dr4-addendum.md` + `findings/2026-11-24-g5-amendment-1.md` | g5 rehearsal result |
| 6 | a3 D3, a4 Q4 (+Q4e/f), c2 D5 grade | `runbook/dr4-release-day.md` §3 | a1, c |
| 7 | g combine -> g3 follow-up -> G6 (`vpt_pf.py` 9bf97042) -> g4 / **g4b** flag | release-day §4, addendum | g chunks |
| 8 | **g7b** (exploratory): g7 fit on every new eclipsing SB2 from g5 | `findings/2026-11-24-g7-prereg.md` | g5, g7 controls |
| 9 | pixel step on G6 survivors | addendum | pixel-011 CONTROLS_PASS |
| 10 | d, f, h | release-day §4 (no code yet) | a-c graded |

Steps 1-5 are independent and can all be filed in the first hour. Use 1 GB memory jobs where the template
allows, so they start quickly. Data key `gaia-orbit-tess` for the release-day steps, and `sb2-debcat` for g6.

## Grading order (what is checked first)

Self-tests and unit tests first, then controls (g7 CONTROLS_OK, g6 anchor and pipeline control, g5 control
rows, g4b known planets), then the grades. A failed control means the targets' grades are reported, not
interpreted.

## Articles (at most 2 per day for the field)

Expected order: (1) g7 + g5, new eclipsing binaries with absolute masses from Gaia DR4 and TESS (the main
payoff); (2) g6, how accurate Gaia's double-lined masses are; (3) g4b replication; (4) step i, the
first transiting companion found from Gaia astrometry, if any.
