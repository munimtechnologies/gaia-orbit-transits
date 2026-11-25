# g8 DR3 rehearsal: results (job g8-rehearsal-dr3-v1, 2026-11-25)

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked it yet.
Text CC BY 4.0. Pre-registration: `findings/2026-11-24-g8-dr4-sb2-eclipse-prereg.md` (section
"DR3 rehearsal (not blind; reported, not graded)"). Output: `data/g8-rehearsal-dr3-v1/g8_rehearsal_dr3.json`.

## What ran

Job `g8-rehearsal-dr3-v1` (Blade, 25 Nov 11:13-11:15 UTC, 107 s, 1 CPU, 1 GB) fetched the repo at
7d69dae, ran `test_sb2_ecl_dr4` (pass), `sb2_ecl_dr4.py --self-test` (SELF_TEST PASS) and the frozen
g8 rule 0.1.0 on the 50 Gaia DR3 double-lined orbits whose DR3 epochs are saved in this repository.
Truth for "known eclipsing" comes from `data/ijspeert2024-check/ijspeert_check.csv` (11 stars).
No crash, no code error found, so no 0.1.1 is needed before Gaia DR4.

## The three expectations written before the run

| Expectation (24 Nov) | Result | Verdict |
|---|---|---|
| >= 6 of the 11 IJspeert-listed eclipsing stars flagged ECL_GAIA (60%) | 5 of 11 (HD 218299, HD 101167, HD 187301, CD-44 6966, V1229 Tau) | **failed by one** |
| <= 1 null (quadrature) flag (80%) | 0 of 50 | true |
| V1202 Cen (Gaia P 3.35 d, true 15.56 d) not ECL_GAIA (70%) | NONE | true |

Two of three true. Every ECL_GAIA star is a known eclipsing binary (5 of 5); the null rule flagged
nothing; all 11 dips of the 5 flagged stars lie 0.0013-0.018 in phase from Gaia's predicted conjunction (window
0.035), and no flagged star has a dip outside the windows. So the timing convention (DR3 reference
epoch 2191.5 + t_periastron, conjunctions at 0.25/0.75 for circular solutions) is right on DR3 data.

## Why the six were missed (none is a code error)

| Star | What the rule saw | Reason |
|---|---|---|
| CD-63 310 | 2 dips, both in one eclipse (0.074 d apart) | needs >= 2 different passages; only one eclipse sampled |
| CD-72 1603 | 1 dip at conjunction | one eclipse sampled |
| V1202 Cen | 2 dips in one eclipse | Gaia period is wrong (3.35 d vs 15.56 d); correctly not flagged |
| Gaia DR3 1853022343761824768 | no dip >= 0.025 mag | TESS signal is at 5.763 d = 2.02 x Gaia P: not this orbit's eclipse |
| Gaia DR3 265213581990291840 | no dip >= 0.025 mag | eclipses shallower than the 0.025 mag floor in Gaia |
| Gaia DR3 911500121588495744 (HD 72862) | no dip >= 0.025 mag | its 3 faintest epochs (0.013-0.016 mag) sit at conjunction; below floor |

Among the 9 known eclipsing stars whose eclipses belong to Gaia's orbit (dropping V1202 Cen and
1853022343761824768), the rule flags 5 (56%); among the 7 with any Gaia dip >= 0.025 mag, it flags 5;
the 2 others had a single eclipse passage sampled. DR4 has about twice DR3's time span (66 vs 34
months), so more stars will have two sampled passages. The rule's choices (two passages, 0.025 mag
floor) trade recall for purity, as intended; they are frozen and are not changed.

## A check made on the side: Gaia's rejection flags matter

The rule drops epochs with `variability_flag_g_reject`. HD 171459 (see
`findings/2026-11-25-hd171459-gaia-conjunction-eclipses.md`) has two DR3 G epochs 0.17 and 0.50 mag
faint with G/sigma of 8.3 and 4.3 and normal BP and RP at the same moment; Gaia flags exactly these
two. If DR4's epoch files drop or rename this flag, the DataLink adapter must map it, or such
outliers would be read as dips. Added to the DR4-day checklist (data access, allowed by the
pre-registration).
