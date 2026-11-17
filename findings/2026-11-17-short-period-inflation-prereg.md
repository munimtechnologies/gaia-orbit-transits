# Are M dwarfs in 0.5-5-day orbits inflated? A replication of Swayne et al. (2024) with Gaia-weighed binaries (pre-registration, eblm_infl 0.1.0)

2026-11-17 22:40 UTC. MV2 of Munim, Inc.; made with AI agents working in his name. Text
CC BY 4.0, code Apache-2.0.

**Written before any result of job `gaia-eblm-fit-v1` exists.** That job (eblm_fit 0.1.0,
pre-registered in `findings/2026-11-17-eblm-fit-prereg.md`) was still queued when this was
written. Nothing from it has been seen. This file adds a sharper test and a better
reference model on top of it. It does not change any of eblm_fit's own grades (G1-G6,
E5, E6).

## 1. A prior-art correction

The eblm-fit pre-registration said the short-period regime "is the one they did not test",
meaning EBLM XIX (Davis et al. 2026, arXiv:2610.18338). That is true of EBLM XIX, which
removed every binary with P < 5 d because synchronised rotation can raise magnetic
activity and inflate the companion. **But the question itself has already been asked:**

- **Swayne et al. 2024** (EBLM XI, MNRAS 528, 5703; arXiv:2312.11339) measured 23 M dwarfs
  with CHEOPS and TESS. They report that M dwarfs in EBLM binaries with P < 5 d are clearly
  inflated, by about 6% against MIST models, versus about 3% or less at longer periods. They
  warn that such systems may not suit calibrating single-star relations. Their short-period
  group is **5 systems, P = 2.78-4.30 d**.
- Fitzpatrick et al. 2025 (EBLM XIV, arXiv:2502.09267) find 2.6 ± 1.1% in 19 systems.
  Only two have P < 3 d (2.54 and 2.69 d), and they did not test a trend with period.
- Çakırlı et al. 2025 (MNRAS 544, 4336) studied 8 systems with P = 4.2-25.6 d and found no
  clear inflation.

So what MV2's sample adds is not a first look. It is **a test of Swayne et al.'s
short-period inflation with many more systems, at shorter periods (mostly 0.5-3 d, where
no EBLM paper has a sample), using masses from Gaia's SB1 orbits.** That is still a
question the EBLM authors would care about: their own papers disagree on whether short
periods matter.

## 2. Why a new reference model

eblm_fit 0.1.0 compares R2 with a rough table (`eblm_screen.MS_TABLE`). Compared with the
BHAC15 5-Gyr solar-metallicity isochrone (Baraffe et al. 2015), the table is
- +3.2% at 0.2 M☉ (0.225 vs 0.218 R☉),
- +3.7% at 0.3 M☉ (0.31 vs 0.299 R☉),
- +3.4% at 0.4 M☉ (0.39 vs 0.377 R☉),

which is as large as the effect under test. `eblm_infl.py` re-scores every eblm_fit radius
against BHAC15. At run time it downloads `BHAC15_iso.2mass` from the authors' site and
records which source it used. A transcribed fallback is used only if the download fails,
and that is flagged.

## 3. Sample and estimator (fixed now)

Input: `eblm_fit_results.csv` from `gaia-eblm-fit-v1`.

**Main set:** rows whose verdict ends in EBLM_CONSISTENT, EBLM_LARGE_RADIUS or
EBLM_SMALL_RADIUS (BD_ prefix allowed), and all of these:
- b < 0.8 (k and b are degenerate in grazing geometry; EBLM XIV excluded b ≳ 0.8 too);
- snr_fit ≥ 30;
- a FLAME primary mass (no 1.3 M☉ default);
- 0.08 ≤ m2 ≤ 0.6 M☉;
- a FLAME primary radius;
- R1 from the light curve within 0.8-1.2 of R1 from FLAME. Larger disagreement points to
  dilution, eccentricity or a bad fit.

**Primary estimator:** inflation = k · R1,FLAME / R_BHAC15(m2, 5 Gyr) − 1. FLAME R1 is used
as the primary choice because it does not depend on the b-a/R1 degeneracy of shallow
eclipses. It follows EBLM XIX in taking R1 from Gaia rather than from the light curve.

## 4. Tests and predictions (our probabilities)

- **H1 (Swayne replication).** The median inflation of the main set, with a bootstrap 95%
  interval (2,000 resamples, seed 20261117).
  - **INFLATED** if the lower bound > +3%.
  - **NOT_INFLATED** if the upper bound < +3%.
  - **INCONCLUSIVE** otherwise; **TOO_FEW** if n < 8.
  - The +3% bar is our estimate of the model floor: BHAC15 vs MIST, ages 1-10 Gyr, and a
    10% FLAME mass error, which moves R2/R_MS by about 3%.
  - We also report whether the interval contains Swayne et al.'s +6%.
  - Probabilities: INFLATED 35%, NOT_INFLATED 20%, INCONCLUSIVE 35%, TOO_FEW 10%.
- **H2 (trend with period).** The Spearman correlation of inflation with orbital period in
  the main set, tested one-sided with 10,000 permutations (seed 20261117). The prediction
  is ρ < 0, meaning more inflation at shorter periods.
  - **PERIOD_TREND** if p < 0.05, otherwise **NO_TREND_DETECTED**; TOO_FEW if n < 8.
  - Probability of PERIOD_TREND: 25%.
  - We also report the confounders ρ(m2, P) and ρ(inflation, m2). If |ρ(m2, P)| > 0.3, a
    trend could come from the reference model's mass dependence rather than from period.
    It is then not claimed until it survives in mass bins.
- **Reported, not graded:**
  - medians in period bins 0-1, 1-2, 2-5 and ≥ 5 d;
  - every combination of {main set, all clean fits} × {FLAME R1, light-curve R1} ×
    {1, 5, 10 Gyr};
  - a plot of inflation against period with Swayne's +6% and EBLM XIX's +0.3% marked.

## 5. What follows

- **INFLATED and PERIOD_TREND.** A large Gaia-weighed confirmation that inflation turns on
  at short periods, extending Swayne et al. down to 0.5 d.
  - Before any claim: inspect every main-set fit plot, write a systematics budget
    (metallicity is not modelled; GSP-Phot [M/H] is not reliable enough), and send an
    expert-check email held for Sheehan's approval.
  - Then run it on Gaia DR4 on 2 December.
- **NOT_INFLATED.** Swayne et al.'s short-period inflation does not hold up in a larger
  sample. That is also worth reporting, with the same checks.
- **INCONCLUSIVE.** Report the interval honestly and move the test to DR4. Its 638,966 RVS SB1
  orbits are about 3.5 times DR3's roughly 181,000, and it adds epoch photometry and RVs.

## 6. Known limits (none tuned after seeing results)

- Metallicity is not modelled. Swayne et al. found a −9%/dex trend, so a sample offset of
  ±0.2 dex moves the median by about 2%.
- BHAC15 is solar-metallicity only. Swayne et al. used MIST interpolated in metallicity.
- Gaia DR3's SB1 K for short-period F/A stars with broad lines may be biased. Fitzpatrick et
  al. found only 3 of 8 Gaia K values agreed within 1σ with ground-based ones. m2 goes as
  K, and R_MS(m2) about linearly, so a 5% K error gives about a 5% inflation error in that
  system. This is a scatter term unless the bias is systematic.
- Selection: Gaia's sparse photometry favours deep eclipses, and so possibly large
  companions. A positive H1 must be checked against this before any claim.

## 7. Running it

The next run copies `compete-results/gaia-eblm-fit-v1/out/eblm_fit_results.csv` into its
work folder and runs
`python eblm_infl.py --results eblm_fit_results.csv --out-dir /out`
as job `gaia-eblm-infl-v1`. It needs about 0.3 GB and a few minutes, with network only
for the BHAC15 download.
