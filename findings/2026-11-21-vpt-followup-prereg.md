# Pre-registration: all-sector, period-free TESS follow-up of Gaia's surviving transit candidates

Written 2026-11-21 (~17:00 UTC), before job gaia-vpt-followup-v1 has run. By MV2 of Munim, Inc.;
made with AI agents working in his name, not yet checked by a human expert. Code
`vpt_followup.py` 0.1.0 (Apache-2.0); text CC BY 4.0.

## Why

The step-g DR3 rehearsal (`findings/2026-11-21-vpt-dr3-results.md`) left two planet-like NEW
candidates from Gaia DR3's transit table with no TOI or CTOI: **TIC 4638108** (Gaia DR3
5431056347037926784, P 2.2086 d, 1.87 R_Jup on a 1.44 R☉ F star) and **TIC 44997521** (Gaia DR3
5432318139709900160, P 3.5497 d, 1.03 R_Jup on a 0.71 R☉ K dwarf). Both were found by folding at
most three TESS sectors at Gaia's period. The same rehearsal showed that Gaia's period is not the
known period for 161 of 176 known systems, and that 24 of 126 sensitive known systems still "hit"
at Gaia's wrong period. A hit at Gaia's period therefore does not prove the period.

## What the job does (no step is tuned after seeing these two stars' full data)

For each target, `vpt_followup.py` 0.1.0:
1. downloads **every** TESS sector (SPOC 120 s, else TESS-SPOC, else QLP; `sb1_transit.light_curves`
   with no sector cap) and detrends each with `sb1_transit.detrend` (30-min bins, running median
   window 0.75 d);
2. runs a **period-free** box search (astropy BoxLeastSquares, depth-S/N objective, 0.3-15 d,
   30,000 log-spaced periods, durations 1-6 h) on every sector alone;
3. on all sectors together, scans ±1% around Gaia's P, 2P and P/2 and around every sector peak with
   S/N ≥ 7, with steps fine enough for the full baseline; the strongest peak is the TESS period;
4. at that period measures depth, odd and even depths, the depth half a period later (secondary),
   per-sector depths (with a χ² consistency test), the companion radius (√depth × R1, R1 from
   FLAME or absolute G as in `gaia_vpt_tess`), and the offset from Gaia's ephemeris.

## Labels (fixed now)

- **NOT_DETECTED**: combined depth S/N < 7.
- **EB_LIKE**: any of ODD_EVEN (|odd − even| ≥ 3σ), SECONDARY (depth half a period later ≥ 3σ
  and ≥ 10% of the primary), STELLAR_SIZE (companion > 2 R_Jup).
- **SURVIVES**: detected, no flag, TESS period within 1% of Gaia's.
- **SURVIVES_OTHER_P**: detected, no flag, TESS period not within 1% of Gaia's (reported with the
  ratio).
- DEPTH_VARIES (per-sector χ² p < 0.001) is a note, not a flag: QLP and SPOC correct for blending
  differently.

## Controls (published answers, chosen before the run)

Three known hot Jupiters from the same Gaia table, chosen by hand for similar brightness and depth,
two of them where Gaia's period is wrong:
- **WASP-4 b** (Gaia 1.30859 d; known 1.338231 d), **WASP-17 b** (Gaia 2.51408 d; known 3.73543 d),
  **HATS-52 b** (Gaia 1.36655 d; known 1.36665 d). Known periods from the NASA Exoplanet Archive.
- **CONTROLS_PASS** if every control's TESS period is within 0.1% of its known period with S/N ≥ 7.
  The candidate labels count only if the controls pass; otherwise they are reported and the module
  is fixed in a dated 0.1.1.

## Predictions (fixed now)

- Controls: CONTROLS_PASS 80%.
- TIC 4638108: SURVIVES 55%, EB_LIKE 30% (STELLAR_SIZE alone 15%), SURVIVES_OTHER_P 10%,
  NOT_DETECTED 5%.
- TIC 44997521: SURVIVES 45%, EB_LIKE 25%, NOT_DETECTED 20%, SURVIVES_OTHER_P 10%.

## What follows

- A SURVIVES candidate next gets a pixel-level which-star test (the TIC lists contaminating flux
  1.26 times TIC 4638108's own in TESS pixels; Gaia's own photometry already sees the same depth on
  the Gaia source). Then a prior-art pass (TESS EB catalogues, VSX, SIMBAD, arXiv) and, if still
  clean, a CTOI on ExoFOP (needs an ExoFOP account) so that TFOP can take radial velocities. Only a
  spectrograph can tell a hot Jupiter from a low-mass star; we will not call either a planet.
- An EB_LIKE or NOT_DETECTED result is reported as such.
