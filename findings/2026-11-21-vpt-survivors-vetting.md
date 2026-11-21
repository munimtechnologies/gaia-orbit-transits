# Which star, and is it already known? Catalogue vetting of the two surviving Gaia DR3 transit candidates

Date: 2026-11-21 (~23:15 UTC). MV2 of Munim, Inc. Made with AI agents working in his name; not
yet checked by a human expert. Text CC BY 4.0.

**Status: exploratory vetting, not a pre-registered test.** It is done while the pre-registered
period-free TESS follow-up (`findings/2026-11-21-vpt-followup-prereg.md`, job gaia-vpt-followup-v1)
is still waiting for compute. Nothing here changes that pre-registration: its labels, thresholds
and predictions (CONTROLS_PASS 80%; TIC 4638108 SURVIVES 55%; TIC 44997521 SURVIVES 45%) stay as
registered. All values are from public archives queried on 21 Nov 2026; the queries and
transcribed values are in `data/vpt-survivors-vetting/catalogue_values.md`.

## Why

The full DR3 rehearsal (`findings/2026-11-21-vpt-dr3-results.md`) left two of Gaia's own new
transit candidates planet-like in TESS with no TOI: TIC 4638108 and TIC 44997521. Our playbook
rule is to check every neighbour's brightness in Gaia (the flux argument) and the prior art before
any pixel test or report. This note does both.

## TIC 44997521 (Gaia DR3 5432318139709900160)

**Star.** G = 13.81, BP-RP = 1.39, parallax 3.562 ± 0.014 mas (about 281 pc), M_G = 6.57 (no
extinction correction), TIC Teff 4563 K, TIC radius 0.80 R_sun (we used 0.71 R_sun before; with
0.80 the 2.2% depth implies 1.15 R_Jup instead of 1.03). RUWE 1.055, ipd_frac_multi_peak 0,
ipd_gof_harmonic_amplitude 0.007, non_single_star 0: no astrometric or image sign of a resolved
or partly resolved companion. Gaia RV 23.3 ± 1.5 km/s from 32 transits; Gaia publishes no RV
amplitude for it (G_RVS = 12.72 is fainter than the 12.0 limit), so **Gaia's spectrograph cannot
screen it**, unlike the 8 candidates it flagged.

**Gaia's transit.** vari_planetary_transit: P = 3.5497497 d, depth 24.38 mmag (2.22%), duration
0.0877 d (2.10 h), 12 in-transit points. The DR4 data model confirms the units (mmag, day).

**Is the duration that of a dwarf host?** For a K dwarf of about 0.72 M_sun (our assumption from
the colour and absolute magnitude) a = 0.0408 AU, so a/R* = 12.4 (R* 0.71) to 11.0 (R* 0.80).
A central transit would last about 2.5-2.8 h; Gaia's 2.10 h implies an impact parameter of about
0.6-0.8. **Consistent with a non-grazing transit of a dwarf.** A giant host or a diluted
background binary would usually need a much longer or a V-shaped event; this does not test shape.

**Neighbours (Gaia DR3 within 2 arcmin, G < 18.2: 45 stars besides the target).** The nearest is
18.8" away (G 17.80, 4.0 mag fainter, 2.5% of the target's flux). The brightest is **G = 10.59 at
28.2"** (5432318135411891968; BP-RP 0.53, Teff about 7100 K). It is a **background star, not a
companion**: parallax 1.155 ± 0.035 mas against 3.562 ± 0.014, proper motion (-15.8, +6.2) against
(-28.7, +20.3) mas/yr. In the TESS band it is about 2.8 mag (13 times) brighter than the target
and only 1.3 TESS pixels away, so it dominates the TESS aperture. The TIC gives no contamination
ratio for this target.

**Which star dims?** Gaia found the 2.22% dip **in its own photometry of this source**, which
separates stars a few arcseconds apart, and the TESS fold at Gaia's period gave 2.19%. The 28"
star cannot produce a dip in Gaia's photometry of the target. A neighbour could mimic it only if
it lay inside Gaia's resolution and were no more than about 4.1 mag fainter (for a total eclipse).
Gaia DR3 lists none within 18.8", and RUWE and the image statistics show no sign of one. **The dip
is on the target, or on an unresolved companion closer than Gaia can separate.** Caveat: the
agreement of the TESS depth with Gaia's depends on how the TESS light curve corrected for the 28"
star. The pre-registered follow-up measures per-sector depths, and a pixel test would settle it.

**Prior art.** ExoFOP-TESS: no TOI, no CTOI, no imaging, spectroscopy, time series or comments.
AAVSO VSX (via the VizieR copy B/vsx): one entry, OID 4110424, type EP, period 3.54975 d, which is
Gaia DR3's own candidate imported into VSX, not an independent detection. Gaia DR3
vari_classifier_result: EP (score 1.0); no vari_eclipsing_binary entry. TESS EB catalogue
(Prša et al. 2022, J/ApJS/258/16): no entry within 2'. Web search for the TIC and Gaia IDs: no
literature.

**What remains.** The main false-positive left is a K dwarf with a low-mass star companion: a star
of about 0.1 M_sun is about 1.0-1.2 R_Jup across, the same size as the signal implies. Only radial
velocities can tell. A 1 M_Jup companion would move the star by about 0.17 km/s; a 0.1 M_sun star
by about 16 km/s, which two epochs of medium-resolution spectra near quadrature would show.

## TIC 4638108 (Gaia DR3 5431056347037926784)

**Star.** G = 12.79, BP-RP = 0.57, parallax 1.216 ± 0.011 mas (about 822 pc), Gaia Teff 6911 K,
TIC Teff 7095 K, TIC radius 1.42 R_sun, mass 1.57 M_sun, Tmag 12.50, TIC contamination ratio 1.26.
RUWE 0.88, ipd_frac_multi_peak 0, non_single_star 0. Gaia RV 15.8 ± 2.6 km/s; no RV amplitude
(G_RVS 12.29 > 12.0), so no Gaia RVS screen either.

**Gaia's transit.** P = 2.2086269 d, depth 17.23 mmag (1.57%; TESS gave 1.8%), duration
0.0794 d (1.91 h), 15 in-transit points.

**Is the duration that of its host?** a = 0.0386 AU, a/R* = 5.8, so a central transit would last
about 3.3 h. Gaia's 1.91 h implies an impact parameter of about 0.92, **beyond 1 - k = 0.87: a
grazing geometry** at Gaia's depth. In a grazing transit the true companion is larger than the
depth suggests, which makes a stellar companion more likely. Gaia's durations come from 15 sparse
points and may be rough; the TESS duration from the follow-up decides. **We mark this as a warning
sign, not a rejection.**

**Neighbours (G < 17.5 within 2').** The brightest near the target is **G = 11.97 at 25.4"**
(5431056342737487488), 0.8 mag brighter than the target: a **foreground** star (parallax 3.75 mas)
that VSX lists as a Gaia rotational variable (ROT, G 11.94-12.00), which explains the TIC
contamination ratio. Others: G 15.19 at 24.8", G 14.81 at 29.3", G 17.32 at 26.4". As for TIC
44997521, Gaia saw the dip in its own resolved photometry, so none of these can be the source in
Gaia's data. A rotational modulation of 0.06 mag does not make 1.9-h box-shaped dips, but it can
add TESS systematics.

**Prior art.** ExoFOP: no TOI, no CTOI, no follow-up. VSX: only Gaia's own EP import (OID 4031565,
P 2.20863 d). Gaia classifier EP (1.0); no vari_eclipsing_binary entry. TESS EB catalogue: no
entry within 2'. Web search: no literature.

## Summary

| | TIC 44997521 | TIC 4638108 |
|---|---|---|
| Gaia depth / TESS depth | 2.22% / 2.19% | 1.57% / 1.8% |
| Gaia duration vs central expectation | 2.10 h vs 2.5-2.8 h (b ≈ 0.6-0.8) | 1.91 h vs 3.3 h (b ≈ 0.92, grazing) |
| Nearest Gaia neighbour | 18.8", 4.0 mag fainter | 24.8", 2.4 mag fainter |
| Brightest neighbour within 30" | G 10.59 at 28", background | G 11.97 at 25", foreground |
| Dip in Gaia's own resolved photometry | yes | yes |
| Gaia RVS screen possible | no (G_RVS 12.72) | no (G_RVS 12.29) |
| TOI / CTOI / published | none | none |

TIC 44997521 passes every catalogue check we can make without new data. TIC 4638108 carries a
grazing-geometry warning from Gaia's duration. Neither is called a planet.

## Not checked (and why)

SIMBAD (CDS servers refused connections and returned 404 tonight), the ASAS-SN variable catalogue
(VizieR mirror database down), the TESS Ten Thousand catalogue (Kostov et al. 2025) and the ZTF
variable catalogues (the targets are at Dec -38 and -37, mostly outside ZTF). To repeat when CDS
is back.

## Next

1. Grade gaia-vpt-followup-v1 as registered. If TIC 44997521 SURVIVES: a pixel test aimed at the
   28" G 10.59 star (TESS-band flux ratio about 13), then a CTOI on ExoFOP (needs an ExoFOP
   account) with these vetting facts.
2. If TIC 4638108 SURVIVES: compare its TESS duration with the 3.3-h central expectation before
   anything else; a TESS duration under about 2 h with a V shape would make it an EB candidate.
