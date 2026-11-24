# Three bright double-lined binaries that Gaia called "Ap-type rotators" dim exactly when their Gaia orbits predict eclipses (exploratory)

2026-11-24, gaia-orbit-transits. By MV2 of Munim, Inc.; made with AI agents working in his name.
No human expert has checked this yet. Text and data CC BY 4.0, code Apache-2.0.

**Status: exploratory candidates.** Hand analysis, machine-checked by `test_gaia_conj_dips_acv.py`
(the publish lane runs it before this commit). The dip rule is the one fixed in
`gaia_conj_dips.py` 0.1.0 earlier the same day; it was chosen while looking at two other stars.
Nothing here is confirmed by a second instrument yet.

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
The other 79 are not read yet (Gaia DR3 epochs also stay on ESA's CDN bulk files).

## Rule

Same as `gaia_conj_dips` 0.1.0: a dip is an unflagged epoch at least 0.025 mag and at least 4 robust
standard deviations fainter than the star's median; conjunctions are at true anomaly 90 - omega and
270 - omega. New: epochs that Gaia's **variability** processing flagged as rejected are not
dropped but listed separately ("rejected_faint") with the same threshold.

## Result

**Four stars dim at a conjunction; every clear unflagged dip in them falls within 0.035 in phase of
one.** One of the four, V1202 Cen, is already a known eclipsing binary and serves as a check.

| Star | Gaia DR3 | TIC | G | P (d), e | Dips (epoch time: mag below median, phase; conjunction) |
|---|---|---|---|---|---|
| **HD 218299** (A0) | 1934924724387752832 | 173207470 | 8.29 | 3.05128, 0.006 | 1937.1285: 0.072, phase 0.7882; 2101.9710: 0.031, 0.8121 (c2 = 0.7941). Flagged by Gaia but at conjunction: 2237.6796: 0.069, 0.2880 (c1 = 0.2904); 1955.3870: 0.040, 0.7720 |
| **HD 101167** (F2V) | 3479008554410838656 | 57791790 | 9.52 | 3.08364, 0.176 | 1951.0272: 0.041, 0.9299; 2321.0710: 0.050, 0.9320 (c2 = 0.9334) |
| **HD 187301** (A2) | 4297719103037032832 | 325802598 | 9.77 | 4.01507, 0.032 | 2083.7525: 0.032, 0.7278; 2356.6859: 0.031, 0.7050 (c2 = 0.7108); 2354.6845: 0.030, 0.2065 (c1 = 0.1912) |
| V1202 Cen (B9V; known EA) | 5866041495122321280 | - | 8.48 | 3.34969, 0.151 | 2542.3332: 0.106, 0.0200; 2542.4072: 0.086, 0.0421 (c2 = 0.0086) |

- **HD 218299**: dips at both conjunctions, about 0.07 mag deep at each: two similar eclipses, as
  expected for its near-equal velocity amplitudes. Two of its four faint epochs had been flagged
  as rejected by Gaia's own variability processing. Gaia's conjunction times are uncertain by about
  0.09 in phase (t_periastron error 0.28 d), so the agreement within 0.006 is partly luck.
- **HD 101167**: two epochs 370 days apart, both 0.04-0.05 mag faint, both within 0.004 in phase
  (0.004-0.011 d) of the same conjunction, whose time Gaia fixes to about 0.014 d. RAVE spectra
  showed it as a probable triple of three similar stars (Matijevic et al. 2010), so the eclipse
  depth may be diluted by the third star.
- **HD 187301**: three epochs about 0.03 mag faint, two at one conjunction and one at the other,
  consistent with two similar shallow (grazing) eclipses of near-twin stars (K = 99.8 and 96.5 km/s).
- **V1202 Cen**: VSX lists it as an Algol-type eclipsing binary with P = 15.5543 d from older data.
  Gaia's double-lined orbit gives 3.3497 d, and Gaia's two faint epochs fall at a conjunction of
  that 3.35-day orbit. We only use it as a positive check of the method here.
- **Flagged epochs are mostly not eclipses.** Gaia's variability processing flagged 16 epochs that
  clearly pass the faintness threshold (by our hand count; the tests assert each one's phase). Only
  the two in HD 218299 fall within 0.035 of a conjunction. A 17th, borderline (0.028 mag) in
  Gaia DR3 3231626306540378112, lies 0.008 from a conjunction whose time is uncertain by 0.24 in
  phase. Most of the others are 0.2-1.6 mag "dips" at
  random phases, e.g. four in the 7.6-mag star Gaia DR3 2562554132208861568 that alternate with
  normal measurements 0.07 d apart, the signature of a measurement problem rather than an eclipse.
- **No dips** in 9 of the 16 stars. Three more have one borderline unflagged epoch each, within
  0.002 mag of the threshold and away from conjunction: Gaia DR3 5322036676774951808 (phase
  offset 0.07), 5448354070122614400 (0.08) and 3231626306540378112 (conjunction time uncertain by
  0.24 in phase). HD 218299 has one more borderline epoch (2475.7563, 0.026 mag) 0.023 from a
  conjunction. The tests leave all four borderline epochs unasserted.

How surprising is this? A dip at a random phase lands within +/-0.035 of one of two conjunctions
with probability 0.14. The 9 clear unflagged dips in the four stars all do (0.14^9 ~ 2e-8, though
dips within one star are not independent, and the stars were picked after looking).

## Checked before writing (24 Nov 2026)

- VSX (cone 0.02 deg): HD 218299, HD 101167 and HD 187301 appear only as Gaia DR3's automatic
  "ACV|roAm|roAp|SXARI" variables, with no period and no eclipsing type. V1202 Cen is listed as EA/DM.
- SIMBAD: each is only "SB*" (spectroscopic binary, from Gaia).
- Villanova TESS EB catalogue (Prsa et al. 2022 and live site): "No associated EB entries" for
  TIC 173207470 (sectors 16, 17, 57, 83, 84) and TIC 57791790 (sectors 10, 63); TIC 325802598 is
  not in the catalogue.
- ExoFOP / exo.MAST: no TOI, CTOI or TCE for TIC 173207470.
- ASAS-SN variable-star database: no entry at CD-63 310 or CD-72 1603 (checked for the earlier pair).
- Web search for the three HD numbers with "eclipsing binary": nothing.
- **Not yet checked:** the IJspeert et al. (2024) catalogue of 69,058 TESS O-F-type eclipsing-binary
  candidates (VizieR J/A+A/691/A242; CDS hosts refused connections and the 38 MB Zenodo copy is too
  big for our tools) and the newest review files of the open Eclipses by Appointment catalogue.
  Job `candidate-vet-v1` (`cand_vet.py`) checks both, with registered controls: C1, Eclipses by
  Appointment must list TIC 384284045; C2, OBAF_EB.csv must list RS Cha or ZZ Boo. **Until it has
  run, these three are candidates, not new eclipsing binaries.**

## What would confirm them

TESS full-frame light curves exist for TIC 173207470 and TIC 57791790 (sectors above). A fold at
the Gaia period, with dips at the Gaia conjunction times, is the registered kind of test
(`gaia_dip_ffi.py`); it needs compute, which is queued.

## Limits

Few epochs per star; Gaia DR3 epoch photometry has outliers; thresholds and the window were chosen
after looking at other stars; the sample (15 of 98 by period) was read in one sitting by hand.
Prior-work checks above are incomplete until candidate-vet-v1 runs.
