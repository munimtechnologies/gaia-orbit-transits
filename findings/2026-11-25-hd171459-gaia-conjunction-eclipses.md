# HD 171459: Gaia's own photometry dims at Gaia's own spectroscopic conjunctions

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked it yet.
Text and data CC BY 4.0 (Gaia data: ESA/Gaia/DPAC); code Apache-2.0. Written 2026-11-25 (~12:40 UTC).
Code `hd171459_gaia_conj.py` + `test_hd171459_gaia_conj.py`; data
`data/hd171459-gaia/hd171459_gaia_dr3_epochs.csv`.

## Why this check

On 25 November (`findings/2026-11-25-g5-tier2-t2-3b-graded.md`) we reported HD 171459 = HIP 91511 =
TIC 464315748 = Gaia DR3 6436666383265499136 (G 8.28, Am star) as a new double-lined eclipsing
binary: Gaia DR3 has a circular double-lined orbit (SB2C, P = 6.3956124 d, K1 89.3 and K2 87.7 km/s,
M sin^3 i = 1.82 and 1.85 M_sun), and the TESS SPOC pipeline sees 1.5% dips at exactly half that
period with alternating depths. The eclipse evidence was TESS's alone, and TESS pixels are 21"
wide. If the dips come from the double-lined pair itself, they must fall at the two conjunctions
of Gaia's orbit. Gaia measures the star separately from its neighbours (0.1" resolution), so its
own epoch photometry is an independent test, as it was for CD-28 7251.

## Method (fixed by rule g8 before looking at this star)

- Epochs: all 98 Gaia DR3 G-band epochs (AIP TAP mirror of `gaiadr3.epoch_photometry`, read
  25 Nov). Gaia's `variability_flag_g_reject` flags exactly two (indices 33 and 40: G 8.777 and
  8.446, G/sigma 4.3 and 8.3, BP and RP normal at the same moments); they are dropped. 96 remain.
- Phase from Gaia's orbit: phase = ((t - (2191.5 + 0.11847939)) / 6.39561241) mod 1, with
  conjunctions at 0.25 and 0.75 (g8's convention for circular solutions; it put every dip of the 5
  known eclipsing binaries flagged in the g8 rehearsal within 0.018 of conjunction).
- Windows: +-0.035 in phase around each conjunction (g8's frozen value). Null: same windows
  moved by +0.25 (quadrature). Baseline: median G of the 78 epochs outside the windows.
- Phases were computed by hand and are checked by the test against the code (agreement < 3e-4).

## Result

| Quantity | Value |
|---|---|
| Baseline G (median of 78 out-of-window epochs) | 8.27615 |
| Robust scatter (1.4826 x MAD) | about 0.004 mag |
| Epochs inside the conjunction windows | 18, **all 18 fainter** than the baseline (sign test p = 2^-18 = 3.8e-6) |
| Mean G residual inside the windows | +0.0116 mag |
| Epochs inside the quadrature (null) windows | 14, 1 fainter; mean -0.0038 mag (slightly brighter, as ellipsoidal light predicts) |
| BP and RP residuals inside the windows | both about +0.010 mag (computed by the code; colour-neutral within noise) |

The four faintest good epochs are the four closest to a conjunction, from four different
conjunction passages, at both conjunctions:

| Index | Gaia time (BJD - 2455197.5) | Phase | Offset from conjunction | G - baseline | BP | RP |
|---|---|---|---|---|---|---|
| 31 | 2167.6405 | 0.2509 | +0.0009 (+0.1 h) | +0.0208 | 8.4732 | 7.9772 |
| 1 | 1707.1916 | 0.2564 | +0.0064 (+1.0 h) | +0.0226 | 8.4678 | 7.9713 |
| 67 | 2388.2731 | 0.7484 | -0.0016 (-0.3 h) | +0.0234 | 8.4748 | 7.9780 |
| 25 | 2119.6903 | 0.7535 | +0.0035 (+0.5 h) | +0.0262 | 8.4784 | 7.9797 |

Typical out-of-eclipse BP and RP are 8.445-8.465 and 7.950-7.963. The ten epochs 0.008-0.022 in
phase from conjunction are 0.006-0.016 mag faint, and the four 0.026-0.033 away 0.002-0.009 mag:
an eclipse roughly 0.04 in phase (about 6 h) wide, consistent with the 6.52 h duration of the TESS
pipeline fit.

## What it means

The dips that TESS sees at half of Gaia's period happen, in Gaia's own resolved photometry, at
both conjunctions of Gaia's own double-lined orbit, within about an hour of the predicted times
(Gaia's t_periastron error is 0.0034 d). This ties the eclipses to the double-lined pair itself,
not to a blended background star, and confirms that HD 171459 is an eclipsing double-lined binary
with masses near 1.8 + 1.85 M_sun (M sin^3 i; with eclipses, sin i is close to 1).

In Gaia the two conjunctions give similar depths (0.021-0.023 and 0.023-0.026 mag at the deepest
epochs), while the TESS pipeline's odd/even statistic says the alternate TESS dips differ. Gaia
samples each eclipse once, at different offsets from mid-eclipse, so it cannot measure the depth
ratio well; a full light-curve fit of the TESS data will.

## Prior work (searched 25 Nov 2026)

Web search "HD 171459" OR "HIP 91511" eclipsing binary (12:30 UTC): nothing calls it eclipsing;
Wikidata lists it with no variability. Earlier the same day: TESS Ten Thousand (Kostov et al.
2025), IJspeert et al. (2024), Prsa et al. (2022), Eclipses by Appointment (checked again at its
newest commit 7bcc627, 25 Nov 11:46 UTC: TIC 464315748 absent), Gaia DR3 vari_eclipsing_binary
(absent; Gaia's classifier put it among DSCT/GDOR/SXPHE pulsators with score 0.03), VSX and
ExoFOP: none lists it. The Gaia-conjunction test of a TESS eclipsing binary has been done before
for single objects (e.g. arXiv:2310.12380 uses Gaia SB1 conjunctions to vet TESS transits); what
is new here is the object.

## Limits

One star; hand-picked because we already knew it eclipses in TESS, so this is a confirmation, not
a blind detection. The windows, null and conjunction convention were fixed earlier for rule g8,
but the decision to look at this star was not blind. Gaia epochs are sparse (one point per
eclipse), so eclipse depths and the exact eclipse width are poorly constrained. BD+15 2743, the
other new system from the same screen, has no Gaia DR3 epoch photometry (the AIP query returns no
row); Gaia DR4 (2 December) publishes epochs for all sources.
