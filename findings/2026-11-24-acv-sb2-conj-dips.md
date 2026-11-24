# Three bright double-lined binaries that Gaia called "Ap-type rotators" dim exactly when their Gaia orbits predict eclipses (exploratory)

> **Update, 24 Nov 2026 ~21:00 UTC: not new, and one check star withdrawn.** HD 218299
> (TIC 173207470), HD 101167 (TIC 57791790) and HD 187301 (TIC 325802598) are all in the TESS OBAF
> eclipsing-binary catalogue of IJspeert et al. (2024, A&A 691, A242; VizieR
> J/A+A/691/A242/obaf-eb1), with TESS periods equal to Gaia's P/2, 2P and about P/2. We withdraw
> them as candidates for new eclipsing binaries. The Gaia dips agree with IJspeert's TESS eclipse
> ephemerides (HD 218299 to within 0.001 d; HD 101167 to 0.02-0.03 d). V1202 Cen is no longer used
> as a check star: TESS and VSX put its eclipses on a ~15.56-day period, not Gaia's 3.35-day SB2
> period, and its two faint Gaia epochs are one event. See
> `findings/2026-11-24-acv-batch2-and-ijspeert-vet.md`, which also reports the out-of-sample batch 2.

2026-11-24, gaia-orbit-transits. By MV2 of Munim, Inc.; made with AI agents working in his name.
No human expert has checked this yet. Text and data CC BY 4.0, code Apache-2.0.

**Status: exploratory.** Hand analysis, machine-checked by `test_gaia_conj_dips_acv.py` (the publish
lane runs it before this commit). The dip rule is the one fixed in
`gaia_conj_dips.py` 0.1.0 earlier the same day; it was chosen while looking at two other stars.

## Why this sample

Earlier today (`findings/2026-11-24-gaia-conj-dips.md`) the only two edge-on double-lined (SB2)
binaries whose Gaia photometry dipped at a Gaia conjunction, CD-63 310 and CD-72 1603, were both
ones Gaia's variability classifier had labelled `ACV|CP|MCP|ROAM|ROAP|SXARI`, the class for
rotating, chemically peculiar (Ap/Bp) stars. Such stars are known to be rare in close binaries.
Gaia DR3 has 98 SB2/SB2C orbits with that label (AIP TAP mirror, 24 Nov 2026). If many are really
eclipsing binaries the classifier mistook for spotted rotators, their faint epochs should pile up
at the conjunctions of their own Gaia orbits.

We read the G-band epochs of **all 15 of those stars with 3.0 <= P <= 4.02 d** (plus one 2.03-day
star read first to test the service): 946 listed rows, saved in
`data/gaia-conj-dips-acv/<source_id>_g.csv` before ESA's archive closes for DR4 on 25 November.

## Rule

Same as `gaia_conj_dips` 0.1.0: a dip is an unflagged epoch at least 0.025 mag and at least 4 robust
standard deviations fainter than the star's median; conjunctions are at true anomaly 90 - omega and
270 - omega. New: epochs that Gaia's **variability** processing flagged as rejected are not
dropped but listed separately ("rejected_faint") with the same threshold.

## Result

**Four stars dim at a conjunction; every clear unflagged dip in them falls within 0.035 in phase of
one.** (V1202 Cen was meant as a check; see the update above.)

| Star | Gaia DR3 | TIC | G | P (d), e | Dips (epoch time: mag below median, phase; conjunction) |
|---|---|---|---|---|---|
| **HD 218299** (A0) | 1934924724387752832 | 173207470 | 8.29 | 3.05128, 0.006 | 1937.1285: 0.072, phase 0.7882; 2101.9710: 0.031, 0.8121 (c2 = 0.7941). Flagged by Gaia but at conjunction: 2237.6796: 0.069, 0.2880 (c1 = 0.2904); 1955.3870: 0.040, 0.7720 |
| **HD 101167** (F2V) | 3479008554410838656 | 57791790 | 9.52 | 3.08364, 0.176 | 1951.0272: 0.041, 0.9299; 2321.0710: 0.050, 0.9320 (c2 = 0.9334) |
| **HD 187301** (A2) | 4297719103037032832 | 325802598 | 9.77 | 4.01507, 0.032 | 2083.7525: 0.032, 0.7278; 2356.6859: 0.031, 0.7050 (c2 = 0.7108); 2354.6845: 0.030, 0.2065 (c1 = 0.1912) |
| V1202 Cen (B9V; known EA) | 5866041495122321280 | 326168892 | 8.48 | 3.34969, 0.151 | 2542.3332: 0.106, 0.0200; 2542.4072: 0.086, 0.0421 (c2 = 0.0086) |

- **HD 218299**: dips at both conjunctions, about 0.07 mag deep at each: two similar eclipses, as
  expected for its near-equal velocity amplitudes. Two of its four faint epochs had been flagged
  as rejected by Gaia's own variability processing.
- **HD 101167**: two epochs 370 days apart, both 0.04-0.05 mag faint, both within 0.004 in phase
  of the same conjunction. RAVE spectra showed it as a probable triple (Matijevic et al. 2010).
- **HD 187301**: three epochs about 0.03 mag faint, two at one conjunction and one at the other.
- **V1202 Cen**: VSX lists it as an Algol-type eclipsing binary with P = 15.5543 d; TESS
  (IJspeert et al. 2024) agrees (15.578 / 7.758 d). Gaia's two faint epochs, 0.07 d apart, are one
  event, so their position at a conjunction of Gaia's 3.35-day orbit may be chance.
- **Flagged epochs are mostly not eclipses.** Gaia's variability processing flagged 16 epochs that
  clearly pass the faintness threshold. Only the two in HD 218299 fall within 0.035 of a
  conjunction. Most of the others are 0.2-1.6 mag "dips" at random phases, e.g. four in the 7.6-mag
  star Gaia DR3 2562554132208861568 that alternate with normal measurements 0.07 d apart.
- **No dips** in 9 of the 16 stars. Three more have one borderline unflagged epoch each, within
  0.002 mag of the threshold and away from conjunction. The tests leave borderline epochs unasserted.

## Checked before writing (24 Nov 2026), and what it missed

- VSX, SIMBAD, the Villanova TESS EB catalogue, ExoFOP/exo.MAST and web searches: nothing.
- **Missed until later the same day:** IJspeert et al. (2024), which lists all three (update above).

## Limits

Few epochs per star; Gaia DR3 epoch photometry has outliers; thresholds and the window were chosen
after looking at other stars; the sample (15 of 98 by period) was read in one sitting by hand.
