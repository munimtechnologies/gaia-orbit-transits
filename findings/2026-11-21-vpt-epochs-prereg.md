# Pre-registration: why are Gaia DR3's transit periods wrong? A test in Gaia's own epoch photometry

Written 2026-11-21 (~20:00 UTC), before this project has downloaded any Gaia epoch photometry of
these stars and before job gaia-vpt-epochs-v1 has run. By MV2 of Munim, Inc.; made with AI agents
working in his name, not yet checked by a human expert. Code `vpt_epochs.py` 0.1.0 (Apache-2.0);
text CC BY 4.0.

## Why

The step-g DR3 rehearsal (`findings/2026-11-21-vpt-dr3-results.md`) found that for **161 of 176**
known systems in Gaia DR3's transit table (`vari_planetary_transit`), Gaia's published
`transit_period` is not the known period, nor half or twice it. Gaia's documentation (section
10.10.1) and Panahi et al. (2022, A&A 663, A101) say only that the known planets' parameters "do
not necessarily match" the literature; we found no published test of *why*. Two explanations make
opposite predictions:

- **ALIAS**: Gaia saw the real transits, but its sparse, scanning-law sampling (typically a few
  in-transit epochs over 34 months) lets many periods pass through the same few dips, and the
  pipeline picked a wrong one. Then Gaia's own in-transit epochs are real transit epochs.
- **SPURIOUS**: Gaia's in-transit epochs are not the real transits (noise, systematics, or
  another signal), so the period is wrong because the detection is.

This matters for Gaia DR4 (2 December 2026), whose transit table has **1,007** candidates: if the
errors are aliases, DR4's candidates are mostly real dips with unreliable periods, and a
period-free search in TESS is the right follow-up; if they are spurious, many DR4 candidates are
not real at all. ESA's archive closes on 25 November 12:00 CET until DR4 opens, so this test has
to run now; the job saves every epoch it downloads.

## Data

- The 214 candidates and their categories exactly as graded in the rehearsal (pinned:
  `data/vpt-dr3-v1/c0/` at 9d8db1a9e6c37a931c6ca44a2f11f81901303e09, `data/vpt-dr3-v1/c1/` at
  08b854f1c9a8240b00eaad209a5a5f00f3b300f8).
- Gaia DR3 G-band field-of-view epoch photometry (ESA DataLink; for any source DataLink does not
  return, ESA's bulk files on cdn.gea.esac.esa.int). Epochs flagged `rejected_by_variability` or
  `rejected_by_photometry` (bulk: `variability_flag_g_reject`) and non-positive fluxes are dropped.
  Stars with fewer than 15 epochs are FEW_EPOCHS.
- Known ephemerides: NASA Exoplanet Archive `pscomppars` (period, its error, mid-transit time, its
  error, duration) and the ExoFOP TOI table (TOIs that are not FP/FA and whose period no archive
  planet already has), both fetched by the job.

## Definitions (fixed now)

- **Gaia's in-transit set S_g**: the `num_in_transit` epochs closest in time to a transit centre of
  Gaia's own ephemeris (`transit_reference_time`, `transit_period`). This reproduces Gaia's count
  without depending on how `transit_duration` is defined.
- **Real-transit set S_t**: epochs within half the catalogue duration of a transit predicted by the
  known ephemeris, propagated to Gaia's times (BJD − 2455197.5; the ~20 s TCB–TDB difference is
  ignored). The ephemeris is **usable** only if the propagated 1σ timing error at the middle of the
  Gaia baseline is ≤ 0.25 × the duration.
- Which ephemeris: for a KNOWN_PLANET star, the one whose period matches Gaia's; for any other
  star, among usable ephemerides, the one whose S_t window shows the deepest S/N dip in Gaia's
  epochs (this choice never looks at S_g).
- **purity** = |S_g ∩ S_t| / |S_g|; coverage = |S_g ∩ S_t| / |S_t|.
- Per star (needs a usable ephemeris, |S_t| ≥ 2 and |S_g| ≥ 2, else UNTESTABLE): **ALIAS** if
  purity ≥ 0.5; **PARTIAL** if 0 < purity < 0.5; **UNRELATED** if purity = 0. SPURIOUS = PARTIAL +
  UNRELATED. By chance, purity is about |S_t| / N (a few per cent), which is reported per star.

## Tests (fixed now)

**T1, validity (times and ephemerides).** Controls: KNOWN_PLANET stars whose Gaia period is the
known period or twice it (ratio 1 or 1/2, where every Gaia in-transit epoch should be a real
transit), with a usable ephemeris, |S_t| ≥ 2 and |S_g| ≥ 2. **TIME_OK** if ≥ 80% have purity ≥ 0.5;
**TIME_BAD** otherwise; UNTESTABLE if fewer than 8 controls. If TIME_BAD, WHY is reported as
INVALID and the module is fixed in a dated 0.1.1.

**WHY, the main test.** Among testable KNOWN_SYSTEM_OTHER_P stars (wrong Gaia period), the ALIAS
share a with a Wilson 95% interval: **ALIAS_DOMINATED** if the lower bound > 0.5;
**SPURIOUS_DOMINATED** if the upper bound < 0.5; **MIXED** otherwise; UNTESTABLE if fewer than 10
testable stars.

**T3, can Gaia's own data flag a wrong period?** For every star, a phase-free box search of the
Gaia epochs (box = Gaia's `transit_duration` clipped to 0.04-0.25 d; at least 3 epochs in the box;
periods 0.2-40 d on a log grid with d ln f = box / (2.5 × baseline), at most 600,000 frequencies;
S/N = depth over white noise from the robust scatter). **N_comp** = the number of separate peaks
(clusters of grid points more than 5 steps apart) at least 0.9 × as strong as the S/N at Gaia's
period, not counting the cluster at Gaia's period. Right group: the 15 KNOWN_PLANET stars; wrong
group: KNOWN_SYSTEM_OTHER_P. AUC = P(N_comp right < N_comp wrong), one-sided Mann-Whitney p.
**PREDICTIVE** if AUC ≥ 0.70 and p ≤ 0.01; **NOT_PREDICTIVE** if AUC < 0.60; **WEAK** otherwise;
UNTESTABLE if either group has fewer than 8 stars. If PREDICTIVE, N_comp becomes a period-reliability
flag for every Gaia DR4 transit candidate (DR4 publishes epoch photometry for all sources),
computable on release day without TESS.

**Reported, not graded:** S/N of the real transit in Gaia's epochs (seen at S/N ≥ 3) by label;
whether the box search scores the true period above Gaia's period (if yes, Gaia's pipeline chose
against its own data, e.g. through its period range or model; if no, the data alone prefer the
wrong period); P_gaia / P_true; how many of S_g fall within Gaia's `transit_duration` / 2 (a check
of what that column means); AUCs of the fraction of the periodogram above Gaia's peak, Gaia's S/N
and `num_in_transit`; N_comp for the 41 NEW candidates, including TIC 4638108 and TIC 44997521.

## Predictions (fixed now)

- T1: TIME_OK 75%, TIME_BAD 15%, UNTESTABLE 10%.
- WHY: ALIAS_DOMINATED 55%, MIXED 25%, SPURIOUS_DOMINATED 15%, UNTESTABLE or INVALID 5%.
- T3: PREDICTIVE 30%, WEAK 35%, NOT_PREDICTIVE 30%, UNTESTABLE 5%.
- True period scores above Gaia's period in the box search for more than half of the wrong-period
  stars: 40%.

## Limits known in advance

The rehearsal is not blind: the known systems are known. A star whose Gaia signal is a different
real planet in a multi-planet system counts against ALIAS only if that planet is not the one
chosen; the choice rule favours the deepest real dip in Gaia's data. Ephemerides from the TESS era
propagated back to 2014-2017 are dropped when too imprecise, which removes some TOI-only systems.
Nearest-epoch selection can include an epoch that Gaia itself filtered out.
