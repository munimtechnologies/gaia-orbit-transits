# Are the two Gaia transit candidates the same depth in blue and red light? (exploratory)

MV2, Munim, Inc. - 25 November 2026. Made with AI agents working in MV2's name; not yet checked by
a human expert. Text and data CC BY 4.0 (Gaia data: ESA/Gaia/DPAC); code Apache-2.0.

Code: `gaia_chroma.py` 0.1.0 with `test_gaia_chroma.py` (the expected values in the test were
worked out by hand first, and the commit lands only if the code reproduces them).
Data: `data/gaia-chroma/<source_id>_epochs.csv`, Gaia DR3 `epoch_photometry` rows read on
25 Nov 2026 ~05:00 UTC from the AIP Gaia TAP mirror (https://gaia.aip.de/tap), because the ESA
Gaia archive closes on 25 Nov until Gaia DR4.

**Status: exploratory vetting step, not pre-registered.** The in- and out-of-transit windows were
chosen after the data had been looked at. Neither star is called a planet.

## Why this test

The two Gaia DR3 transit candidates that passed our all-sector TESS follow-up
(`findings/2026-11-25-vpt-followup-results.md`) are TIC 44997521 (Gaia DR3 5432318139709900160,
P = 3.54941 d, K dwarf) and TIC 4638108 (Gaia DR3 5431056347037926784, P = 2.20828 d, F star).
Gaia DR3 radial velocities cannot bound their companions
(`findings/2026-11-25-gaia-rv-two-candidates.md`). What Gaia *can* still say: at every
field-of-view transit it measures the star in G, in blue BP and in red RP within about a minute.
A transit across the target itself is nearly colour-neutral (limb darkening makes it only a
little deeper in the blue). An eclipse on an unresolved star of a different colour is not: when
that star adds little light, depth(BP)/depth(RP) is about 10^(-0.4 dC), with dC its BP-RP colour
minus the target's. An M dwarf behind or bound to a K dwarf (dC about +1 mag) would give a ratio
near 0.4.

## Rules (in the code)

Time = Gaia `g_transit_time`; phase residual r on the TESS ephemeris (T0 BTJD 1546.48145 and
1517.88102; Gaia time = BTJD + 1802.5). In transit |r| < 0.05 d, out of transit |r| > 0.10 d.
Per band: baseline = median of out-of-transit fluxes after dropping gross outliers (more than 5%
from the median), scatter = 1.4826 MAD. Depths compared only on epochs where G, BP and RP all
have a value. Gaia's photometric rejection flags are not applied (see the last section).

## Results

| | TIC 44997521 | TIC 4638108 |
|---|---|---|
| Gaia epochs in transit (all bands usable) | 4 (3) | 6 (6) |
| mean depth G | 2.56% | 1.53% |
| mean depth BP | 2.65% | 1.63% |
| mean depth RP | 2.35% | 1.22% |
| BP/RP depth ratio | 1.13 +- 0.17 | 1.34 +- 0.16 |
| leave-one-epoch-out ratio range | 1.03 - 1.19 | 1.00 - 1.49 |
| median over epochs of depth(BP) - depth(RP) | +0.12 points | -0.06 points |

Per-epoch depths (G / BP / RP, %):

- TIC 44997521: Gaia time 1790.806: 2.63 / 2.88 / 2.12; 2103.152: 2.67 / 2.63 / 2.51;
  2199.013: 2.37 / 2.44 / 2.42; (1822.714: G 2.14, BP 2.80, RP value unusable, 188,008 e/s).
- TIC 4638108: 1962.265: 2.37 / 2.76 / 0.24; 2032.958: 2.07 / 1.95 / 2.01;
  2103.575: 1.03 / 1.24 / 0.83; 2103.649: 0.30 / 0.55 / 0.62; 2198.590: 1.92 / 1.39 / 1.66;
  2262.586: 1.48 / 1.90 / 1.95.

## What it means

1. **TIC 44997521 dims by the same amount in blue and red light.** The ratio 1.13 +- 0.17 is
   what a transit across the K dwarf itself gives. In the small-light limit, an eclipse on an
   unresolved source whose BP-RP colour differs from the target's by more than about 0.4 mag
   falls outside the 2-sigma range (0.78-1.48); an M-dwarf source (ratio about 0.4) is
   excluded at about 4 sigma. Together with the earlier checks (no Gaia source within 18.8",
   the dip is on the target in Gaia's own photometry, no odd-even difference, no secondary
   eclipse, consistent depth across 7 TESS sectors), the remaining false-positive routes are a
   bound or chance-aligned companion of nearly the same colour closer than about 0.5", and a
   companion that is not a planet (a brown dwarf or very-low-mass star transiting the K dwarf
   itself, which is colour-neutral too). Only radial velocities settle the last one.
2. **TIC 4638108 is inconclusive.** The mean ratio 1.34 +- 0.16 is driven by one epoch
   (Gaia time 1962.265), where G and BP drop by 2.4% and 2.8% but RP by only 0.24%. Without that
   epoch the ratio is 1.00, and the median per-epoch difference is -0.06 points. A colour-neutral
   transit with one bad RP measurement fits; so might a bluer eclipsed source. This test does not
   change the earlier reading that TIC 4638108 leans stellar (V-shaped, grazing, 3.5-sigma signal
   at phase 0.5).

## Gaia's BP/RP rejection flags mark the transits

In these two stars Gaia's `photometry_flag_bp_reject` / `photometry_flag_rp_reject` are set on
7 of 20 in-transit BP/RP values but on 10 of 228 out-of-transit values. Out of transit the flagged
values are mostly gross brightenings (up to 2.8 times the median flux). In transit, six of the
seven flagged values are ordinary dips of 2.0-2.9%, comparable to the G depth at the same epoch (1.5-2.7%); the
seventh is a gross outlier (RP 188,008 e/s). Anyone who drops flagged
epoch photometry before looking for transits in Gaia BP/RP will lose some of the in-transit
points. This is two stars only; we have not checked it on a larger sample.

## Limits

Hand-chosen windows on a small number of epochs (3 and 6); the error bars use the out-of-transit
scatter and ignore the transit-shape differences between epochs (the bands are compared at the
same epoch, so this mostly cancels in the ratio). The colour argument assumes the eclipsed source
adds little light. BP/RP epoch fluxes come from 3.5" x 2.1" windows, which can include light from
sources closer than about 2"; no Gaia source is that close to either star except a G = 18.25
star 2.6" from TIC 4638108, about 5.5 magnitudes fainter.

## Next

- Gaia DR4 (2 Dec 2026) has about 66 months of epoch photometry instead of 34: repeat this test
  on both stars, and on TIC 93622019, with the same rules, as part of the release-day vpt
  follow-up.
- A CTOI for TIC 44997521 (and the other two) still needs an ExoFOP account for MV2.
