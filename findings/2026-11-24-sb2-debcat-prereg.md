# Pre-registration: how accurate are Gaia DR3's double-lined orbits? A test against DEBCat

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0, code Apache-2.0. Written 2026-11-24 (~03:30 UTC), eight days before Gaia DR4,
before job **sb2-debcat-v1** ran and before any DEBCat row was matched to a Gaia orbit by us.
Code: `sb2_debcat.py` 0.1.0 with tests `test_sb2_debcat.py` (committed right after this file,
release v0.54.0, if its tests pass on the publish lane; the job runs the same files).

## The question

Gaia DR3 published 5,376 double-lined spectroscopic orbits (VizieR I/357/tbosb2, 4,630 rows;
I/357/tbosb2c, 746 circular rows). Their two velocity amplitudes K1 and K2 give each star's
M sin³i, so for an eclipsing system (sin i ≈ 1) they give dynamical masses directly. These orbits
are already being used for masses: Rowan et al. (2023, arXiv:2212.02509) for 122 stars, our own
three new eclipsing binaries (`findings/2026-11-23-sb2-ebfit-prereg.md`), and soon Gaia DR4's much
larger list. **How accurate are they?**

What we found before writing this (24 Nov):
- Gaia's own paper on the double-lined channel (Damerdji et al.) is listed by ESA as "expected with
  Gaia Data Release 4"; the SB1 paper (Gosset et al. 2024/25, arXiv:2410.14372) defers SB2
  validation to it. We found no published systematic comparison of Gaia DR3 SB2 orbits with DEBCat.
- Case-by-case checks disagree. Southworth (2025, arXiv:2504.16817) finds RZ Cha's Gaia K values
  (107.8 ± 0.4, 108.2 ± 0.4 km/s) consistent with ground-based ones; for CW CMa (arXiv:2611.25217)
  Gaia's masses are larger by 2.6σ; for V570 Per (arXiv:2309.15655) the Gaia orbit is in "moderate
  disagreement". An asteroseismic study of four eccentric SB2 eclipsing binaries (arXiv:2506.14395)
  finds Gaia masses 2-4% off for two stars and one Gaia orbit at a wrong period. Piccotti et al.
  (2023, arXiv:2307.16719) find one 5σ outlier among three SB9 systems.
- Rowan et al. (2023) note that circular (SB2C) solutions carry most of their large mass errors.

So the systematic answer is missing, and DR4 is eight days away. The wow, if the test finds a bias:
every mass derived from Gaia's double-lined orbits, including DR4's, needs a correction we can
state on release day. If it finds none: Gaia's dynamical masses can be trusted at a stated level,
with a measured error-inflation factor.

## Data and method (all in `sb2_debcat.py`)

1. **DEBCat** (Southworth 2015, live table at astro.keele.ac.uk/jkt/debcat): system name, period,
   both masses with errors, radii where given. The raw page is saved with the results. If fewer than
   100 systems parse, the job stops (exit 3) and saves sample rows; nothing is graded.
2. **Gaia orbits:** both VizieR tables in full (CfA mirror, then CDS). Controls: row counts against
   4,630 and 746, and the known row Gaia DR3 6030061691987260672 (K1 = 56.3477 km/s).
3. **Names to Gaia IDs:** SIMBAD sim-id (Harvard mirror, then CDS). Control first: RZ Cha must give
   Gaia DR3 5198334162577657984. **End-to-end control:** RZ Cha's matched Gaia K values must equal
   107.8 and 108.2 km/s within 0.5 km/s (PIPE_CONTROL_OK), as quoted by Southworth (2025).
4. Per matched system: **period status** (OK if Gaia's period is within 0.5% of DEBCat's; ALIAS at
   ½, 2, ⅓ or 3 times; otherwise BAD). Only PERIOD_OK systems form the sample **S**.
5. **Folded mass ratio** q′ = smaller/larger, from Gaia (K_small/K_large) and DEBCat
   (M_small/M_large): dq = q′_Gaia − q′_DEBCat, with z_q from Gaia's K errors and DEBCat's mass
   errors. This needs no inclination and no choice of which Gaia component is which.
6. **Mass scale** R = (M1+M2) sin³i from Gaia, divided by DEBCat's M1+M2. Because sin³i ≤ 1, a perfect
   Gaia orbit gives R slightly below 1; for detached eclipsing binaries (i ≳ 80°) R is expected
   between about 0.955 and 1.000, most near 0.99. R − 1 > 3σ is physically impossible
   ("impossible", Gaia amplitudes too large).

## Registered grades (minimum 15 systems in S; otherwise UNTESTABLE)

- **Q1 mass ratio:** median dq with a bootstrap 95% interval (2,000 resamples, seed 20261124).
  Q_UNBIASED if the interval contains 0, otherwise Q_LOW or Q_HIGH.
- **Q2 mass scale:** median R with a bootstrap 95% interval. MASS_SCALE_OK if the interval overlaps
  [0.97, 1.00]; GAIA_MASSES_LOW if it lies wholly below 0.97; GAIA_MASSES_HIGH if wholly above 1.00.
  Also reported: the number of "impossible" systems and the share with R < 0.93.
- **Q3 quoted errors:** robust standard deviation (1.4826 × MAD) of z_q. ERRORS_OK if ≤ 1.5,
  otherwise ERRORS_UNDERSTATED, with the factor.
- **Q4 line blending** (Gaia's RVS has resolving power ≈ 11,500, about 26 km/s per resolution
  element, so the two stars' lines overlap when K1 + K2 is small): BLEND_SIGNAL if Spearman's ρ
  between R and K1 + K2 is positive with permutation p < 0.01 (5,000 permutations). Also reported,
  exploratory: |z_q| against K1 + K2, against q′_DEBCat (twins), against period and against Gaia's
  goodness of fit; SB2 against SB2C medians.
- Reported, not graded: period failure rate (ALIAS + BAD among matched), per-star mass ratios
  R_heavy and R_light.

## Predictions (fixed now)

| prediction | probability |
|---|---|
| unit tests and self-test pass | 80% |
| DEBCat parses ≥ 250 systems | 65% |
| PIPE_CONTROL_OK (RZ Cha end to end) | 75% |
| sample S has 30-120 systems | 65% |
| period failure rate ≤ 10% of matched systems | 75% |
| Q1 Q_UNBIASED | 60% |
| Q2 MASS_SCALE_OK | 50% (GAIA_MASSES_LOW 25%, GAIA_MASSES_HIGH 25%) |
| at least one "impossible" system | 70% |
| Q3 ERRORS_UNDERSTATED | 65% |
| Q4 BLEND_SIGNAL | 30% |
| SB2C median \|z_q\| above SB2's | 60% |

## What follows

- The result feeds the masses of our three new eclipsing binaries (sb2-ebfit): a measured bias or
  error-inflation factor is applied to them as a stated systematic.
- On Gaia DR4 day (2 Dec), the same code re-runs on DR4's double-lined table (the VizieR names will
  change; the table loader is the only part to adapt), giving an outside accuracy check of DR4's
  dynamical masses within days of release.

## Limits

Not blind in every respect: we have read the case studies above, and the four sb2-ebfit control stars
(ZZ Boo, CW Eri, EY Cep, BK Peg) are DEBCat systems whose Gaia numbers we have seen; they are a few
of an expected 30-120. DEBCat is heterogeneous (different authors, epochs and methods) and lists no
inclinations, so Q2 rests on the sin³i argument above. A system can be matched to the wrong Gaia
source if SIMBAD's cross-identification is wrong; period agreement guards against most such errors.
The code was written without being run by us; unit tests and a synthetic self-test run first.
