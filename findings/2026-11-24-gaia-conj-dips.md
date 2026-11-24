# Two edge-on Gaia double-lined binaries dim in Gaia's own photometry at the conjunction their Gaia orbit predicts (exploratory)

> **Update, 24 Nov 2026 ~21:00 UTC: these candidates are not new.** Both stars (TIC 349572805 and
> TIC 371839648) are in the TESS OBAF eclipsing-binary catalogue of IJspeert et al. (2024, A&A 691,
> A242; VizieR J/A+A/691/A242/obaf-eb1, summed score 4.0 each), which the checks below had not
> reached. We withdraw them as candidates for new eclipsing binaries. The Gaia-epoch dips at Gaia's
> conjunctions stay as an independent confirmation from Gaia's own photometry. See
> `findings/2026-11-24-acv-batch2-and-ijspeert-vet.md`.

2026-11-24, gaia-orbit-transits. By MV2 of Munim, Inc.; made with AI agents working in his name.
No human expert has checked this yet. Text and data CC BY 4.0, code Apache-2.0.

**Status: exploratory.** Hand analysis, machine-checked by `test_gaia_conj_dips.py` (the publish
lane ran it before this commit). The dip thresholds were chosen while looking at the data. The
registered test is the TESS full-frame fold in `findings/2026-11-24-gaia-conj-dips-prereg.md`
(job gaia-dip-ffi-v1, queued).

## Why look

Our pre-registered screen of 183 edge-on Gaia DR3 double-lined (SB2) orbits
(`findings/2026-11-23-sb2-screen-results.md`) found TESS pipeline detections for 66 of them. The
rest either had no pipeline detection (95 stars, queued for a full-frame fold in job
sb2-ffiscan-v1) or no TIC match at all (22 stars, status NO_TIC, which no job covers yet). Gaia
publishes epoch photometry only for stars its variability pipeline classified. ESA's Gaia archive
closes on 25 November until DR4, so we read the Gaia DR3 G-band epochs of every star in those two
groups that Gaia had classified as a non-eclipsing variable, and compared each faint epoch with the
conjunction times of the star's own Gaia orbit.

## Data

- 19 stars, all those in the two groups with a non-eclipsing Gaia variability class: 13 with no TESS
  pipeline detection and 6 with no TIC match. Gaia classes: SOLAR_LIKE (13), ACV (3), DSCT|GDOR (2),
  RS (1). Epochs from ESA's DataLink service, 24 Nov 2026, saved in
  `data/gaia-conj-dips/<source_id>_g.csv` (time to 1e-7 d, magnitude to 1e-6). Of 978 listed
  transits, 4 have no G value and 22 are flagged as rejected by Gaia's photometry or variability
  processing, which leaves 952 usable epochs.
- Orbits: `gaiadr3.nss_two_body_orbit` (AIP TAP mirror, 24 Nov), copied into `gaia_conj_dips.py`.
  Reference time in epoch units is 2191.5 + t_periastron. For circular (SB2C) solutions the
  conjunctions are at phases 0.25 and 0.75, the convention of `sb2_ffiscan.py`.
- A dip is an epoch at least 0.025 mag and at least 4 robust standard deviations (1.4826 x MAD)
  fainter than the star's median.

| Star | TIC | G | Gaia class | P (d) | usable epochs | dips |
|---|---|---|---|---|---|---|
| CD-63 310 (Gaia DR3 5288669213282803328) | 349572805 | 9.94 | ACV | 5.41063 (SB2C) | 75 | **2** |
| CD-72 1603 (Gaia DR3 6374372070227419008) | 371839648 | 9.91 | ACV | 4.56693 (SB2C) | 55 | **1** |
| Gaia DR3 6025454428973694464 | 212031970 | 7.97 | ACV | 1.05959 (e 0.17) | 34 | 0 |
| Gaia DR3 6370053605166404992 | 311430361 | 7.80 | DSCT/GDOR | 2.22995 | 54 | 0 |
| Gaia DR3 3043555010111094400 | 32399700 | 10.65 | DSCT/GDOR | 4.90691 (SB2C) | 55 | 0 |
| Gaia DR3 2995056243702062080 | 317413770 | 9.38 | SOLAR_LIKE | 4.74173 (SB2C) | 35 | 0 |
| Gaia DR3 3419201066092932992 | 356984148 | 10.03 | SOLAR_LIKE | 4.34798 | 39 | 0 |
| Gaia DR3 6547214134176807808 | 214875017 | 10.19 | SOLAR_LIKE | 6.68075 | 35 | 0 |
| 11 more (SOLAR_LIKE 10, RS 1; 5 with no TIC match) | | 10.3-11.2 | | 4.6-7.7 | 28-98 each, 570 in all | 0 |

The 11 others are Gaia DR3 3024112659531165568, 5512207383273412864, 5871568499564025472,
1734078000491716224, 1615317447472056448, 6668966900715757312, and (no TIC match)
3323030323068415744, 6705693548324328960, 5442901385802064000, 5448988969368351616 and
3944246249499094272. Their slow spot modulation stays below the dip threshold.

**Only 2 of the 19 stars show any dip, and all three dips found fall at a conjunction of the
star's own Gaia orbit. Two of them fall within 0.01 of a conjunction in phase.** Both stars are
ones Gaia's classifier labelled ACV, the class for rotating chemically peculiar stars.

## CD-63 310 (TIC 349572805)

- Two consecutive Gaia measurements on 2014-09-08 (Gaia times 1672.6624 and 1672.7364, 106 minutes
  apart, one in each of Gaia's two fields of view) are 0.040 and 0.031 mag faint (6.8 and 5.3
  robust sigma; median G 9.9436, robust sd 0.0059). No other epoch is more than 0.022 mag faint.
- Their phases are **0.7503** and 0.7639. The conjunction is at 0.75: the deeper point is 0.0014 d
  from the predicted time, against a ±0.027-d uncertainty from Gaia's T0 and period carried over 96
  cycles.
- Around the same conjunction, epochs at phase 0.7177 and 0.7229 (0.17 and 0.15 d before it) and at
  0.7965 (0.25 d after) are normal, so the eclipse lasts less than about 0.43 d.
- Around the other conjunction (0.25), the epochs at phases 0.2386, 0.2417 and 0.2792 are within
  0.007 mag of the median. With two near-equal stars (K1 92.7, K2 94.6 km/s) a circular orbit
  should give two similar eclipses, so the second one is shallower or displaced. A small
  eccentricity, which Gaia's circular fit would not show, could displace it. This is the main open
  question for TESS.
- A 4% depth for two near-twin stars means a grazing eclipse.
- TESS has full-frame light curves of it from about 37 sectors (1-13, 27-39, 61-69, 87, 88; Villanova
  TESS EB site target page). It has no 2-minute data and no pipeline TCE. It is not in the
  sb2-ffiscan-v1 sample because our screen found no TIC number for it.

## CD-72 1603 (TIC 371839648)

- One measurement (Gaia time 2120.3603, 2016-10-21) is 0.052 mag faint, more than 20 robust sigma.
  Its partner measurement in the other field of view is missing. No other usable epoch is more than
  0.005 mag faint.
- Its phase is **0.2441**, 0.027 d before the 0.25 conjunction (Gaia's prediction is good to
  ±0.006 d). Because a single point can fall anywhere inside an eclipse, this says only that the
  eclipse lasts at least ±0.027 d around the conjunction.
- Five other epochs within ±0.035 in phase of that conjunction (0.2166, 0.2182, 0.2344, 0.2685,
  0.2779) are normal. The nearest, 0.072 d before and 0.084 d after the conjunction, bound the
  half-duration to below about 0.08 d, again a short, grazing eclipse. No usable epoch falls within
  ±0.035 of the other conjunction.

## How likely is chance?

A dip at a random phase lands as close to one of the two conjunctions as observed with probability
4|Δφ|: 0.1% for CD-63 310 (deeper point) and 2.4% for CD-72 1603. A looser test, which only asks
that a dip fall inside a plausible eclipse window (±0.035 in phase), gives 14% for each star and
2% for both. The 17 other stars, sampled the same way, showed no dip at all.

## Gaia DR3 6025454428973694464, a 1.06-day pair with no deep eclipse

The edge-on rule gives m1 sin³i ≈ Gaia's mass (2.41 vs 2.31 M☉) for this 1.06-day, e = 0.17 orbit.
At that separation, two 2.3 M☉ stars should eclipse deeply over a wide range of inclinations. Its
34 Gaia epochs vary by 0.05 mag but show no deep eclipse. The faintest epoch (G 7.999) lies 0.023 in
phase before a conjunction. We make no claim from this yet. A 1.06-day orbit with e = 0.17 is
unusual for stars this close, so Gaia's orbit, its mass, or both may be off. It is in the
registered TESS fold as a 'flat' star.

## Prior work checked (24 Nov 2026), and what it missed

- As first written: neither star is listed as eclipsing in VSX (only Gaia DR3's automatic
  'ACV|roAm|roAp|SXARI' class), SIMBAD (SB* only), the Villanova TESS EB catalogue (Prša et al. 2022
  and its live site), exo.MAST/ExoFOP (no TCE, TOI or CTOI), Gaia DR3's eclipsing-binary table, or
  the open Eclipses by Appointment catalogue (commit 3a46591; accepted-systems.csv,
  claim-adjudication.csv, period-free-review.csv, reviewed-extension.csv, batch-candidates.csv,
  bright-followup-review.csv). Web searches found nothing.
- **Missed:** the TESS OBAF eclipsing-binary catalogue of IJspeert et al. (2024), which lists both
  (see the update at the top). They are TESS eclipsing-binary candidates, not new discoveries.
- What remains of this note: Gaia's own sparse photometry, read against Gaia's own spectroscopic
  conjunctions, independently confirms eclipses in these double-lined binaries that Gaia's
  variability classifier labelled as rotating chemically peculiar stars.

## Limits

- Three faint epochs in two stars. Gaia DR3 epoch photometry has occasional outliers, and a single
  point (CD-72 1603) is weak evidence on its own.
- The 0.025-mag and 4-sigma thresholds and the ±0.035 window were chosen after looking. The
  sample (stars with Gaia epoch photometry) is biased toward stars Gaia found variable.
- Conjunction phases assume Gaia's circular fits. A small eccentricity would move both conjunctions.
- The eclipse explanation is the simplest one but not the only one; a blended or third star could
  also dim the light. Gaia's 0.4-arcsecond resolution makes a distant neighbour unlikely.
