# TYC 6340-23-1 (TIC 71945261) in the TESS pixels: the eclipse is on the target, 11% deeper, and an 18-year period

Graded 2026-11-22 (~16:00 UTC) by MV2 of Munim, Inc.; made with AI agents working in his name,
not checked by a human expert. Text CC BY 4.0, code Apache-2.0.
Pre-registration: `findings/2026-11-20-tyc6340-pixel-prereg.md`, amended before any pixel was
analysed by `findings/2026-11-21-tyc6340-pixel-amendment-1.md`. Code `tyc_pixel.py` 0.1.1, made
from commit c16e7a2 by `patch_tyc_pixel_011.py`. Job `tyc6340-pixel-v2` (blade,
2026-11-22 11:10-11:21 UTC): unit tests, self-test and the full run all passed (exit 0).
Outputs in `data/tyc6340-pixel-v2/`: `tyc_pixel_summary.json`, `tyc_pixel_report.md`,
`pixel_depth_map.csv`, `tess_eclipse_times.csv`, `wasp_link.csv`, `job_summary.json`, and the
exact code that ran, `tyc_pixel.py`.

## Result in one paragraph

The TESS sector 92 pixels place the 6.8% eclipse on TYC 6340-23-1 itself. The PSF fit gives
99.85% of the lost light to the target (95%: 99.73-100.01%). The free-position centroid of the
eclipse signal lies 0.023 px (0.5″) from the target's Gaia position, 0.15σ, and 29.6σ from the
G = 12.55 star 94″ away, the nearest star bright enough to make the eclipse. All three
controls passed. The deblended depth is 0.0679 ± 0.0004, 11% deeper than the QLP depth the
companion's radius was based on. That is inside the pre-registered "consistent" band, and it
makes the companion slightly *larger*, not smaller. SuperWASP's 2006-2008 eclipses join the
2025 TESS eclipses at a unique cycle count (N = 2862). This gives an 18-year period of
**2.3287747 ± 0.0000003 d**, which agrees with Gaia DR3's spectroscopic period within 1.1σ.
**All eight registered predictions came true.**

## Graded labels

| label | result | registered prediction | came true |
|---|---|---|---|
| L0 sensitivity (C1-C3) | PIX_SENSITIVE | SENSITIVE 80% | yes |
| L1 which star (PSF amplitudes) | PIX_ON_TARGET | ON_TARGET 82% | yes |
| L2 centroid of the eclipse signal | CENTROID_ON_TARGET | ON_TARGET 75% | yes |
| L3 deblended depth | DEPTH_CONSISTENT (ratio 1.114) | CONSISTENT 55% | yes |
| L4 oversized companion | OVERSIZE_SURVIVES | SURVIVES 75% | yes |
| C TESS timing | TIMING_OK (10 eclipses) | TIMING_OK 90% | yes |
| B SuperWASP-TESS link | LINK_UNIQUE | LINK_UNIQUE 70% | yes |
| B Gaia period | GAIA_PERIOD_OK (z = −1.11) | GAIA_PERIOD_OK 85% | yes |

## Numbers (all from `data/tyc6340-pixel-v2/tyc_pixel_summary.json`)

- **Data:** TESScut 15 × 15, sector 92, 9,953 good cadences. The PSF model has 42 Gaia stars;
  the mean-image fit has PSF σ 0.48 × 0.53 px and a halo fraction of 0.38.
- **Controls:** C1 nulls at phase 0.25 (z_t −0.55, z_n 0.99) and 0.75 (z_t 0.70, z_n −0.03)
  pass. C2: a 10% dip injected on the 94″ star is recovered as δ_N = 0.1003, PIX_ON_NEIGHBOUR,
  CENTROID_ON_NEIGHBOUR. C3: a 3% dip injected on the target is recovered as δ_T = 0.0302,
  PIX_ON_TARGET, CENTROID_ON_TARGET. C4: no isolated bright control star, so the systematic
  floor is the registered default, 0.15 px.
- **Eclipse (10 eclipses):** δ_T = 0.0679 ± 0.0004 (z = 194). δ_N = 0.0007 ± 0.0003 (z = 2.1;
  the 94″ star would need δ_N ≈ 0.43 to make the eclipse). f_T = 0.9985 (0.9973-1.0001). The
  ten eclipses alone give δ_T between 0.0666 and 0.0695. With the two nearby free stars added
  to the model, δ_T = 0.0668.
- **Centroid:** 0.023 px from the target (0.15σ), 4.45 px from the 94″ star (29.6σ); σ = 0.150
  px per axis, almost all of it the systematic floor (bootstrap 0.009-0.010 px).
- **Depth and size:** depth ratio 1.114 against QLP's 0.0609. Scaling the fitted radius by
  √ratio gives about 0.236 R_sun, against 0.224 R_sun from the light-curve fit and 0.117 R_sun
  for a normal 0.097 M_sun star. This is a simple scaling, not a refit.
- **Timing (Part C, 3 × 3 aperture):** T_ref = BJD_TDB 2460817.00291 ± 0.00012 (BTJD
  3817.00291); one-sector P = 2.328778 ± 0.000036 d. χ²_red is 26, so the per-eclipse errors
  were too small. The quoted errors are already scaled by √χ²_red.
- **SuperWASP link (Part B):** SuperWASP epoch T_W = BJD 2454152.04984 ± 0.00090 (2,862
  cycles before T_ref). The eclipse signal at N = 2862 has S/N 68.0, against −4.1 and −0.9 at
  N ± 1. No bootstrap fit hit the grid edge. **P = 2.3287747 ± 0.0000003 d.** Gaia DR3 gives
  2.3289298 ± 0.00014 d (z = −1.11).
- **Blend screen (amendment 1, reported, not graded):** of 71 Gaia stars in the field, only two
  are bright enough in RP to make a 6.09% eclipse at all. These are the 94″ star (it would have
  to lose 43% of its light), now excluded by the pixels, and a star 237″ away (79%). The 38″
  star would have to lose 198%. The nearest stars, at 16.6″ and 24.2″ (RP 16.6 and 16.5),
  would each have to lose more than 25 times their own light.

## What this changes (the actions the pre-registration fixed for these outcomes)

1. **ON_TARGET + CENTROID_ON_TARGET:** the eclipse is on TYC 6340-23-1. No star that Gaia DR3
   resolves can make it: those within one TESS pixel are far too faint, and the only capable
   star near enough to matter is excluded by the pixels. An unresolved companion closer than
   about 1″ is not tested here.
2. **DEPTH_CONSISTENT, OVERSIZE_SURVIVES:** the label stays **B_OVERSIZED_COMPANION**. The
   deblended depth is 11% deeper than the depth behind the 0.224 R_sun radius, so if anything
   the companion is a little larger. We still **do not call it inflated**: its mass rests on
   Gaia's velocity amplitude, which only Gaia DR4 or a spectrum can check (step a5 of the DR4
   runbook).
3. **LINK_UNIQUE + GAIA_PERIOD_OK:** the follow-up ephemeris is
   **T0 = BJD_TDB 2460817.00291 ± 0.00012, P = 2.3287747 ± 0.0000003 d**. As registered, the
   DR4 velocity-amplitude test (`findings/2026-11-20-tyc6340-dr4-k-prereg.md`) keeps its
   pre-registered period. The new period appears there only as a sensitivity note.

## Limits

The PSF is a Gaussian core plus halo, not the TESS PRF, and the injection controls use the
same model. There is one TESS sector. The depth window samples the flat eclipse bottom
(±0.012 d), so the depth ratio is not a light-curve refit. The SuperWASP link assumes no
period change over 18 years. Nothing here measures the companion's mass.
