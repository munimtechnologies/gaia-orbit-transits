# Gaia DR3 velocities cannot bound the companions of TIC 4638108 and TIC 44997521 (null, exploratory)

2026-11-25, gaia-orbit-transits. MV2 of Munim, Inc.; made with AI agents working in his name, not
checked by a human expert. Text CC BY 4.0. Exploratory vetting step, not pre-registered.

## Question

On 24 Nov we bounded the mass of whatever transits TIC 93622019 from the scatter of Gaia DR3's own
radial velocities (findings/2026-11-24-tic93622019-gaia-rv-limit.md: companion < 0.10 Msun, 95%).
Can the same test rule out a stellar companion for the other two Gaia DR3 transit candidates that
passed the all-sector TESS follow-up (findings/2026-11-25-vpt-followup-results.md)?

## Data

Gaia DR3 gaia_source rows read from the AIP Gaia TAP service on 2026-11-25 (ESA's archive is closed
until DR4): data/gaia-rv-two-candidates/gaia_dr3_rv_rows.csv.

| Star | Gaia DR3 | G | G_RVS | RV (km/s) | RV error | N transits | rv_method_used | RUWE | ipd_frac_multi_peak |
|---|---|---|---|---|---|---|---|---|---|
| TIC 4638108 | 5431056347037926784 | 12.79 | 12.29 | 15.76 | 2.64 | 30 | 2 | 0.88 | 0 |
| TIC 44997521 | 5432318139709900160 | 13.81 | 12.72 | 23.25 | 1.47 | 32 | 2 | 1.06 | 0 |

## Result: no bound (null)

Both stars are fainter than G_RVS = 12, so Gaia DR3 measured their velocity from the combined
spectrum of all visits (rv_method_used = 2; Katz et al. 2023, A&A 674, A5). For these stars DR3
publishes no epoch-scatter statistics (rv_amplitude_robust, rv_chisq_pvalue and
rv_renormalised_gof are empty), and radial_velocity_error is the error of the combined measurement,
not a measure of the scatter between visits. The scatter formula used for TIC 93622019 is valid only
for rv_method_used = 1 (tic93622019_gaia_rv.py checks exactly this in `valid_epoch_stats`), so it
does not apply here. **Gaia DR3 velocities give no usable limit on the companion mass of either
star.** We do not claim one.

What the rows do show, weakly:
- RUWE 0.88 and 1.06, ipd_frac_multi_peak 0, non_single_star 0: no sign of a resolved or
  astrometrically detected companion. At orbits of 2.2 and 3.5 days the photocentre motion of even a
  low-mass star is far below Gaia DR3's reach, so this does not rule out an eclipsing M dwarf.
- The RVS template temperatures (6750 K and 4500 K) agree with the TIC values (7095 K and 4563 K),
  consistent with the TESS dips sitting on an F star and a K dwarf respectively.

## What decides it

1. Gaia DR4 (2 Dec 2026) is expected to publish per-visit velocities; if it does for these stars,
   refit them at the TESS periods (2.20828 d and 3.54941 d). A stellar companion would give tens of
   km/s; a hot Jupiter would be below Gaia's precision.
2. Ground-based radial velocities through TFOP, which needs CTOI submission via an ExoFOP account
   (requested).

ExoFOP checked again 2026-11-25: TIC 44997521 still has no TOI, CTOI, files or observing notes.
