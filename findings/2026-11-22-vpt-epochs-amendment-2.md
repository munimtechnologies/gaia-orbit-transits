# Amendment 2 to the Gaia epoch test: Gaia's in-transit set from Gaia's own box (not blind)

MV2, Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.
Written 2026-11-22 (~23:00 UTC), before job gaia-vpt-epochs-box-v1 runs.
Pre-registration: `findings/2026-11-21-vpt-epochs-prereg.md`. Results that prompted this:
`findings/2026-11-22-vpt-epochs-results.md`.

## Why

In job gaia-vpt-epochs-v2, T1 came out TIME_BAD, and so WHY was INVALID, as registered. The cause
was how Gaia's in-transit set S_g was defined. We took it as the `num_in_transit` epochs nearest
Gaia's transit centres, but that column counts about 2.6 times more epochs than lie inside Gaia's
own `transit_duration`. The pre-registration says a TIME_BAD result is fixed in a dated version.

## What we have seen (so this is not blind)

From the 0.1.1 run: T1, WHY and T3 grades; for every star, coverage, purity, n_t, n_g,
`gaia_within_frac`, the real-transit S/N and N_comp; and the raw epochs (`data/vpt-epochs-v2/`).
We have **not** computed purity, coverage or WHY labels with the new S_g. The 0.1.1 coverage
column (mostly 1.0 for wrong-period systems too) and the 110 of 118 real-transit detections lead
us to expect ALIAS-like results. The predictions below are made knowing that.

## The change (vpt_epochs 0.1.2, `patch_vpt_epochs_012.py`)

**S_g** = the Gaia epochs within `transit_duration` / 2 of a transit centre of Gaia's own
ephemeris (`transit_reference_time`, `transit_period`). This branch was already in 0.1.0 for stars
without `num_in_transit`; 0.1.2 uses it for every star. Everything else is unchanged: the pinned
0.1.0 code (f868df8e) with the 0.1.1 file fix (824cbe54); the constants, T1, WHY and T3 rules;
S_t; the ephemeris choice; and the periodogram. T3 does not use S_g, so its numbers must
reproduce exactly. That serves as a check. The epochs are the ones job -v2 saved; the job copies
them into its cache from the repo, so no ESA service is needed. Ephemerides are fetched again.

## Grades (registered rules, new S_g)

- **T1:** TIME_OK if at least 80% of the controls (at least 8 needed) have purity ≥ 0.5.
- **WHY** (only if T1 is TIME_OK; otherwise INVALID again and the question stays open):
  ALIAS_DOMINATED if the lower Wilson 95% bound of the ALIAS share is above 0.5;
  SPURIOUS_DOMINATED if the upper bound is below 0.5; MIXED otherwise.
- **T3 check:** AUC 0.858 and the PREDICTIVE label must reproduce exactly (same epochs, same code).

**Exploratory, reported but not graded** (`vpt_epochs_extras.py coverage`), for both the 0.1.1 and
the 0.1.2 sets: the overlap of real-transit epochs with S_g, observed against chance, where each of
a star's n_t real-transit epochs falls in S_g with probability n_g / N. We report the summed
overlap, the expectation, z, and how many stars overlap at all.

## New pre-registered test: does Gaia see TIC 93622019's dip at the TESS ephemeris?

TIC 93622019 (Gaia DR3 5345417757181174144) has a 1.3% transit in TESS every 2.1238933 d
(ephemeris refined in job tic93622019-pixel-v1: T0 = BTJD 3706.08685 ± 0.00068, σ_P = 3.0 × 10⁻⁶ d).
Gaia lists it at 2.83166 d, a 4:3 alias. The TESS pixel test could not exclude one faint star 2.4″
away (`findings/2026-11-22-tic93622019-pixel-results.md`), but Gaia's photometry resolves that star.
**Nobody has looked at Gaia's epochs at the TESS ephemeris.**

Method (`vpt_epochs_extras.py tess`): the star's cleaned Gaia G epochs, normalised by the median.
In-window set = epochs within 0.0625 d (D/2, D = 0.125 d) of a TESS-predicted transit centre,
converted to Gaia time with BJD = BTJD + 2457000 (Gaia time = BTJD + 1802.5). Depth and S/N are
computed as in vpt_epochs (`set_depth_snr`, robust scatter). The null is the same statistic at 1,000
random phase shifts, uniform in [D, P − D] with seed 20261122; empirical p = (1 + n_null ≥ obs) /
(1 + n_valid). The ephemeris must be good to 0.25 D when propagated to the middle of Gaia's baseline
(expected about 0.005 d).

- **GAIA_SEES_TESS_EPHEMERIS** if S/N ≥ 3 and p ≤ 0.01 (at least 2 in-window epochs).
- **NOT_SEEN** otherwise. **UNTESTABLE** if there are fewer than 2 in-window epochs, fewer than 15
  epochs, or the ephemeris is too imprecise.
- What follows: GAIA_SEES means the TESS transit is the dip Gaia recorded on the target itself.
  Gaia separates every star that Gaia DR3 lists near it, including the 2.4″ one, so that counts as
  independent on-target evidence. NOT_SEEN means the TESS signal and Gaia's dip may not be the same
  event, and the candidate is held back until that is understood.

Exploratory, not graded: the phase-free box S/N at the TESS period and at Gaia's period, and the
best period within ±0.05% of the TESS period, for TIC 93622019, TIC 4638108 (2.20828 d), TIC
44997521 (3.54941 d) and HD 250735 = TIC 400170926 (5.895742 d).

## Predictions

- T1 TIME_OK 80%. T3 reproduces exactly 95%.
- WHY, if T1 is OK: ALIAS_DOMINATED 35%, MIXED 45%, SPURIOUS_DOMINATED 20%.
- Coverage above chance for wrong-period systems (z ≥ 3) with the 0.1.2 set: 80%.
- TIC 93622019 GAIA_SEES_TESS_EPHEMERIS 75%, NOT_SEEN 20%, UNTESTABLE 5%.

## Job

**gaia-vpt-epochs-box-v1** (1 GB, CPU only). Steps: fetch the pinned code; the 0.1.0 tests and the
0.1.1 tests, each in its own process; the 0.1.2 and extras tests; the self-test (the pinned 0.1.0
self-test plus a box check); seeding the cache from `data/vpt-epochs-v2/`; the run; the coverage
statistics; the TESS-ephemeris check.
