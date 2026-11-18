# Results: do Gaia DR3's brown-dwarf-mass spectroscopic orbits transit as often as they must? (sb1_transit 0.1.0)

2026-11-18. MV2 of Munim, Inc.; made with AI agents working in his name. Text CC BY 4.0,
code Apache-2.0. Grades the pre-registration `findings/2026-11-18-sb1-transit-prereg.md`
(release v0.15.0). Jobs `gaia-sb1tr-c0-v1` and `gaia-sb1tr-c1-v1` (165 min each). The outputs
are in `data/sb1tr-v1/`. A follow-up with a robust hit rule is pre-registered in
`findings/2026-11-18-sb1-robust-prereg.md`.

## Short version

- Among **512 randomly chosen Gaia DR3 SB1 orbits** (P = 1–13 d, G ≤ 13, minimum
  companion mass 5–105 M_Jup, dwarf primaries) that TESS could test, the pre-registered
  rule found **17 substellar-size transit hits**. Geometry predicts **91.6** if every orbit
  were real and the companions really that light. The control periods predict 7.5 false
  alarms.
- Reality fraction **ρ = 0.10, 95% interval 0.03–0.22**. **H1 passes**: at most about a
  fifth of these orbits are both real and truly substellar. The bound stays below 0.30
  even with no false-alarm subtraction at all.
- **But the hit rule was not clean.** The false-alarm check (C2) failed: the control rate
  was 5.0% against ≤ 3%. The timing check (H3) failed too, with 2 of 5 timed hits at Gaia's
  predicted phase. Looking at the plots shows why. Nearly every new "hit" comes from 1–3
  outlying 30-minute bins (−3% to −30%) that drag the box mean down while the rest of the
  box is flat.
- The only clean new transit in the random sample is **TOI-6218.01** (Gaia DR3
  392652614647892736, a 71 M_Jup minimum-mass companion of a K dwarf, P = 5.155 d). It sits
  at Gaia's predicted phase (z = 2.0). **No new transiting brown dwarf is claimed.**
- Since the artefacts can only add hits, the real ρ is lower than 0.10. The upper bound
  stands. A re-run with an outlier-proof rule, a fresh order and about 2,600 stars is
  pre-registered and queued (8 jobs).

## How the two halves were combined

| | chunk 0 | chunk 1 | duplicates removed | combined |
|---|---|---|---|---|
| eligible pool | 6,769 | 6,434 | | |
| stars processed | 319 | 351 | 15 | 655 |
| rate sample (sensitivity ≥ 0.5) | 251 | 271 | 10 | **512** |
| Σ p_transit × s ("expected if all real") | 48.06 | 45.97 | 2.45 | **91.58** |
| hits, all classes | 21 | 16 | 0 | **37** |
| control hits expected, all | 15.5 | 10.0 | 0 | **25.5** |
| substellar-size hits | 9 | 8 | 0 | **17** |
| control hits expected, substellar-size | 5.5 | 2.0 | 0 | **7.5** |

**Why the pools differ.** In chunk 0 the Gaia archive timed out on the 1–1.5 d query, and
0.1.0 fell back to the query without `astrophysical_parameters`. For that period bin it
therefore had no FLAME masses and no log g cut, so more stars passed (fewer rejected as
evolved: 1,421 against 1,701).

**Why there are duplicates.** The two "halves" were shuffles of different pools, so they
are not an exact partition. 15 stars were processed by both jobs (found by matching
source_id). None was a hit in chunk 0. One, Gaia DR3 6027843599040116864 (P = 1.089 d),
is a marginal hit in chunk 1 (SNR 7.3), where it had FLAME parameters and so a different
box width. We kept chunk 1's records, which have the full parameters, and subtracted the
10 duplicates in chunk 0's rate sample. Their sum of p × s is 2.453, and they had no hits
and no control hits. `sb1_robust.combine()` reproduces every number below, and
`test_sb1_robust.py` checks them.

## Grades

| | rule | value | grade |
|---|---|---|---|
| C1 | ≥ 3 of WASP-18 b, TOI-2533 b, TOI-1712 b, TOI-5427 b hit | 4 of 4 in both jobs | **pass** (but see note 1) |
| C2 | control hit rate ≤ 3% | 25.5 / 512 = **5.0%** (6.2% and 3.7%) | **fail** |
| C3 | ≥ 150 in the rate sample per job | 251 and 271 | pass |
| **H1** | upper 95% of ρ (substellar-size) < 0.5 | ρ = 0.104, 95% [0.026, **0.215**] (straight sum without dedup: 0.210) | **pass** |
| H2 | (exploratory) ρ_all(P ≥ 5 d) > ρ_all(P < 5 d) | 0.56 (12 hits, 5.0 control, E 12.5) vs 0.057 (25 hits, 20.5 control, E 79.1) | pass, low weight (note 3) |
| H3 | > 50% of Gaia-timed hits at the predicted phase | 2 of 5 | **fail** |
| D1 | substellar-size hits not on the TOI list → vetting | 19 stars (9 + 10) | see below |

ρ_all = 0.126, about [0.01, 0.28]. Without any control subtraction, the upper bound of
ρ (substellar-size) is 27.22 / 91.58 = **0.297**.

**Note 1.** TOI-2533 b counts as a hit through sector 23, where the transit is clean. Its
sector 50 "hit" is outlier-driven. The other three controls show clean, box-filling
transits in every plotted sector.

**Note 2. What the failed C2 and H3 mean.** The control folds see the same outliers as
the real folds, so subtracting the control rate is still unbiased on average. The
interval, however, does not include the control's own noise. That is why H1 is also quoted
with no subtraction at all, where it still passes. H3 failed because most of the timed
hits are not transits at all.

**Note 3.** The P ≥ 5 d hits are mostly TOO_DEEP or MODULATED, and some are outlier-driven
too. H2 is exploratory and is repeated with the robust rule.

## Post-hoc look at the hits (may only reject; labelled post-hoc)

We opened the fold plot of every substellar-size hit we could. The plots are in
`data/sb1tr-v1/plots/`.

- **Outlier-driven (1–3 isolated deep bins, the rest of the box flat): 9 of 9 checked.**
  Gaia DR3 2354310959234948608 (TIC 268731306), 5582537610183263104 (TIC 52641840),
  2370874419008106880 (TIC 92200123), 6912182209970818688 (TIC 248897979),
  3287717686073453568 (TIC 452792844), 3129886983796551936 (TIC 235405756),
  5043618067499817600 (TIC 441493643), 5974407638833034624 (TIC 197084132) and
  2021731407944247936 (TIC 451898434, a single bin). 5920493945158297728 (TIC 75154449)
  shows three deep bins plus a few −3% bins; it is not a credible transit either.
- **Clean, box-filling transits in the random sample:** TOI-6218.01 (above, PHASE_MATCH).
  TOI-1608.01 (Gaia DR3 125548289270234880, P = 2.473 d, a TFOP false positive) shows a
  0.3% dip at the Gaia period in three sectors at the predicted phase (z = −0.8). That
  orbit is real, but the 0.1.0 classes call it MODULATED.
- **Eclipse-like but not substellar:** 6068279509209727616 (a ~30% V-shaped eclipse in one
  sector, TOO_DEEP) and 3461121939767538688 (e = 0.72, MODULATED) look like stellar
  eclipses at the Gaia period. They are not pursued here.

**Why 0.1.0's rule let outliers through.** The box depth is a mean. Two or three bins at
−10% among ~30 flat ones give a "depth" of ~1% at a white-noise SNR in the hundreds. Each
outlier comes from a different epoch, so the three-epoch and drop-one-epoch tests pass
too. The empirical SNR did not help either, because the outliers make one phase stand out
just as a transit would. A transit fills the box, so its **median** depth matches its mean
depth. Outliers leave the median at zero. 0.2.0 adds exactly that test.

## What this does and does not show

- **Shows.** Gaia DR3 SB1 orbits that imply brown-dwarf or very-low-mass companions at
  P = 1–13 d around G ≤ 13 dwarfs mostly do **not** produce the transits such companions
  must produce. At most about 22% (95%) are both real and truly that light. With the
  outlier hits removed, the true value is probably a few percent. Stevenson et al.
  (2023) found 3 transiting companions among 2,490 via the TOI list. That count could
  have meant the TOI list misses most of them. Our direct light-curve search says it does
  not: the transits are not in the light curves.
- **Does not show which explanation holds.** A low ρ means each orbit is either spurious
  (pulsation, spots or blends imitating a small RV signal) or real but seen nearly face-on
  with a heavier companion. Orbits picked for low m₂ sin i are biased toward the face-on
  case (stated as a limit in the pre-registration). The robust re-run splits ρ by primary
  mass. Hot primaries, where pulsators live, should be the most spurious if pulsation is
  the main cause.
- **Prior art (searched 2026-11-18).** Stevenson et al. 2023 (AJ 166, 225) matched SB1 orbits
  to TOIs. arXiv:2310.12380 used SB1 orbits to reject TOIs. Studies of the high-mass end
  (e.g. arXiv:2608.06453, Gaia SB1 dark-companion follow-up) find luminous-companion
  contaminants. We found no direct, injection-calibrated measurement of the transit rate of
  low-mass DR3 SB1 orbits in TESS light curves.

## Data

`data/sb1tr-v1/c0/` and `c1/` hold `sb1_summary.json`, `sb1_report.md` and `sb1_stars.csv`
for each job, and `data/sb1tr-v1/plots/` holds the fold plots discussed above. ESA Gaia DR3
via the ESA and ARI Gaia archives. TESS SPOC, TESS-SPOC and QLP light curves via MAST and
lightkurve. TOI list via ExoFOP.
