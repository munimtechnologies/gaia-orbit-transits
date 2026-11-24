# Why are Gaia DR3's transit periods wrong? Amendment 2 graded: aliases of real dips

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked it yet.
Text CC BY 4.0, code Apache-2.0. Written 2026-11-24 (~22:00 UTC).

- Pre-registration: `findings/2026-11-21-vpt-epochs-prereg.md` (21 Nov, before any epoch was read).
- First run and why it failed T1: `findings/2026-11-22-vpt-epochs-results.md` (job gaia-vpt-epochs-v2).
- Amendment 2 (fixed 22 Nov ~23:00 UTC, before this job ran; **not blind**, written after the v2
  results were seen): `findings/2026-11-22-vpt-epochs-amendment-2.md`.
- Job **gaia-vpt-epochs-box-v1** (Blade, 24 Nov 20:02-20:19 UTC, `vpt_epochs` 0.1.2 =
  pinned 0.1.0 + 0.1.1 file fix + `patch_vpt_epochs_012.py`). All unit tests, the 0.1.1 and 0.1.2
  tests and the self-test passed. Epochs: the 11,081 Gaia DR3 G epochs of all 214 stars saved by
  job -v2 (cache 214, DataLink 0, CDN 0: no ESA service was used).
- Outputs, unchanged: `data/vpt-epochs-box-v1/` (`vpt_epochs_summary.json`,
  `vpt_epochs_stars.csv`, `coverage_stats.json`, `tess_eph_check.json`).

## Grades (rules exactly as registered)

| Test | Result | Label | Our prediction |
|---|---|---|---|
| T1 validity: controls with purity >= 0.5 | **13 of 13** (share 1.00) | **TIME_OK** | TIME_OK 80%: came true |
| WHY: ALIAS share among testable wrong-period systems | **86 of 111 = 77.5%** (Wilson 95%: 68.9-84.3%); 25 PARTIAL, **0 UNRELATED** | **ALIAS_DOMINATED** | ALIAS_DOMINATED 35% (MIXED 45% was our favourite): the less likely of our two leading outcomes came true |
| T3 must reproduce exactly | AUC 0.8579617834394905, p = 2.41 x 10^-6, 15 right vs 157 wrong | **PREDICTIVE**, identical to -v2 | 95%: came true |
| Coverage above chance for wrong-period systems (z >= 3), 0.1.2 set | 277 real-transit epochs in Gaia's box vs 34.3 expected (8.1x), z = 44.4; all 111 stars overlap (29.2 expected) | above chance | 80%: came true |
| TIC 93622019 at the TESS ephemeris | 7 in-window epochs, depth 0.84%, S/N 5.57, empirical p = 0.00105 (0 of 947 shifted nulls as strong) | **GAIA_SEES_TESS_EPHEMERIS** | 75%: came true |

Four of four graded outcomes came true; for WHY we had put more weight on MIXED.

## What it means

**Gaia DR3's wrong transit periods are aliases of real transits, not spurious detections.** With
Gaia's in-transit set defined by Gaia's own transit box, for 86 of 111 testable known systems whose
Gaia period is wrong, at least half of Gaia's in-transit epochs fall inside the real transits
predicted by the NASA Exoplanet Archive or the TOI list. None of the 111 has a Gaia box that misses
the real transits entirely. The validity check that failed on 22 November now passes for all 13
control planets, so the timing and the ephemerides are right. The 25 PARTIAL systems also overlap
the real transits; their boxes just hold more out-of-transit epochs than in-transit ones.

For Gaia DR4 (2 December 2026, 1,007 transit candidates) this says: expect most candidates to be
real dips with unreliable periods. The right follow-up is a period-free search (our DR3 rehearsal
recovered the known period for 156 of 160 wrong-period systems), ranked by the N_comp flag from
Gaia's own epochs (T3, AUC 0.858).

The coverage statistic (exploratory, not graded) shows the same with the 0.1.1 nearest-epoch
set: 309 overlaps vs 101 expected (3.0x). The control planets behave the same way (0.1.2 set: 88
vs 10.8 expected), so Gaia's box catches real transit epochs about eight times more often than
chance, whether its period is right or wrong.

## TIC 93622019

The registered test confirms what our hand reading of 24 November expected
(`findings/2026-11-24-tic93622019-gaia-epochs-tess-ephemeris.md`): Gaia's own photometry, which
resolves the only TESS-unexcluded neighbour (G 19.56, 2.4 arcsec), dims at the times the TESS
ephemeris predicts, carried back about 1,560 cycles to 2014-2017. The depth over the 0.125-d window
is 0.84% (it includes the two ingress/egress epochs at normal brightness; we expected about 0.9%).
The S/N is 5.6, below our hand guess of about 8, because the job's robust scatter (0.38%) is larger
than ours (0.29%). In-window Gaia times: 2029.653, 2097.592, 2097.666, 2106.096, 2106.170,
2258.989, 2333.310. The candidate's dip is therefore on the target itself at Gaia's resolution.
It is still a candidate: Gaia RVS (27 visits, p = 0.51) leaves hot Jupiters, brown dwarfs and the
lowest-mass stars open.

Exploratory (not graded): phase-free box S/N on Gaia epochs is 6.6 at the TESS period and 7.0 at
Gaia's alias, with the best local period 2.12432 d (S/N 7.1). For TIC 4638108 and TIC 44997521 the
box S/N at the TESS period is 9.8 and 34.0 (Gaia's period is right for both). HD 250735 (not a
transit candidate; Gaia's transit period 0.885 d) gives no TESS-period box value.

## Limits

Amendment 2 was written after the T1 failure was seen, so this is not a blind test; the threshold
and labels are the registered ones, applied to a redefined in-transit set. The known systems were
known. Ephemerides were fetched live on 24 Nov. TCB-TDB (~20 s) ignored. The TIC 93622019 test
used the same 60 epochs our hand note had already examined.
