# BD+65 286: remaining catalogue checks, and a prior-art correction

Written 2026-11-19 (about 09:30 UTC). Job gaia-bd65286-v1 has **not run yet**, so nothing here
grades the pre-registered fit (`findings/2026-11-19-bd65-286-prereg.md`), whose predictions
and rules are unchanged. By MV2 of Munim, Inc.; made with AI agents working in his name, and
not checked by a human expert. Text CC BY 4.0.

## Correction first
The pre-registration said the star's variability was in no catalogue. **That was wrong.**
**Green et al. 2023** (MNRAS 522, 29; arXiv:2211.06194; VizieR J/MNRAS/522/29) lists TIC
50453242 among its 15,779 *selected ellipsoidal binary candidates*, measured from the
2019-2020 TESS full-frame images (Quick-Look Pipeline, sectors 14-26):

| Green et al. 2023, table3 / table2 | value |
|---|---|
| Score (selection threshold 0.6) | 0.808 |
| Porb | 1.646408 ± 0.0000049 d |
| T0 | JD 2458867.714267 ± 0.0053 (BTJD 1867.7143) |
| a2c (ellipsoidal, cos 2φ) | −2.026 × 10⁻³ ± 1.4 × 10⁻⁵ |
| a3c | −9.8 × 10⁻⁵ ± 1.4 × 10⁻⁵ |
| a1c, a1s | −1.15 × 10⁻⁴ ± 1.08 × 10⁻⁴, +1.31 × 10⁻⁴ ± 6.7 × 10⁻⁵ |
| P(contact) | 0.000 |

Green et al. kept eclipsing systems in their sample without flagging them, so their entry
says nothing about the eclipse. Our own STATUS page already named Green et al. 2023 as a
source we check for every eclipsing system, but this source was skipped in the
pre-registration check. The lesson is now in STATUS.

So three independent things were published in 2022–2023, each on its own:
1. the Gaia DR3 SB1 orbit (P = 1.6464947 ± 0.0000341 d, K = 13.08 ± 0.39 km/s);
2. the NASA SPOC sector-52 threshold-crossing event (P = 1.6465081 d, depth 3,753 ppm);
3. Green et al.'s ellipsoidal candidate (P = 1.646408 d, a2 ≈ 2,030 ppm).

**The narrowed claim:** no catalogue or paper we can find identifies BD+65 286 as an
*eclipsing* system, or ties the eclipse, the ellipsoidal signal and the Gaia orbit to one
companion of about 0.1 M☉. That link, and the radius and mass the fit will give, are the part
that would be ours.

## Remaining checks (all done today; the CfA VizieR mirror was up again)
| Source | Query | Result |
|---|---|---|
| ASAS-SN variable stars (II/366, catv2021) | 120″ cone | no row |
| ZTF periodic variables (Chen+ 2020, J/ApJS/249/18) | 120″ cone | no row. Not informative: at G = 9.2 the star is far brighter than ZTF's saturation limit. |
| TESS Ten Thousand EB catalogue (Kostov+ 2025, J/ApJS/279/50): new EBs, known EBs and the ~900,000 unvetted machine-learning flags | 60″ cone and TIC = 50453242 | no row in any table. A control query on the same table returns rows. |
| Gaia DR3 `vari_classifier_result`; `phot_variable_flag` | source_id | no row; NOT_AVAILABLE |
| Chopard-Vilhem eclipsing-SB1 survey (Zenodo 10.5281/zenodo.22998328, v1.2.0 and v1.3.0) | record description | covers only P = 13-119 d, so it cannot contain a 1.65-d system |
| Chopard-Vilhem near-edge-on astrometric orbits (10.5281/zenodo.23342416) | sample definition | astrometric orbits only; this star has an SB1 orbit, not an astrometric one |
| SPOC TCE list (MAST DV API) | TIC 50453242 | still only s0052-s0052:TCE_1 |
| Web search on "TIC 50453242", "BD+65 286", "SAO 12389" | | nothing about the star |

Gaia's orbit has `flags` = 0, significance 33.7 and goodness of fit 2.97. Its eccentricity
(0.047 ± 0.033) is consistent with zero.

## Do the three periods and epochs agree?
- Gaia minus SPOC: −1.3 × 10⁻⁵ d, 0.4σ of Gaia's error.
- Green minus Gaia: −8.7 × 10⁻⁵ d, 2.5σ of Gaia's error. Green's quoted error (4.9 × 10⁻⁶ d)
  is 7 times smaller than Gaia's and comes from one TESS year, so we do not read the
  difference as real yet.
- Green's T0 (an ellipsoidal minimum) is 517 cycles before SPOC's eclipse epoch (BTJD
  2718.92035). Propagated with Gaia's period it falls 0.032 d (1.9% of the orbit) from the
  eclipse; with SPOC's period, 0.039 d; with Green's, 0.013 d. If Green's phase zero is the
  T0 they list, the deeper ellipsoidal minimum (a3c < 0) falls at the eclipse. That is
  expected, because at that conjunction we see the gravity-darkened side of the F star that
  faces its companion. All three signals fit one orbit.
- The pre-registered fit (BLS within ±0.1% of Gaia's period, up to 8 sectors from 2019 to
  2025) gives the ephemeris we will use.

## An outside check of the mass, by hand (not the pre-registered measurement)
The simple ellipsoidal formula A ≈ α (m₂/M₁)(R₁/a)³ sin²i, with α ≈ 1.2-1.35 for an F star in
the TESS band, gives about 2,450-3,050 ppm for Gaia's companion (FLAME or TIC primary mass and
radius). Green et al. measured 2,026 ± 14 ppm in raw QLP flux. That is 0.66-0.83 of the rough
prediction, inside the pre-registered window for `ell_ratio_fit` (0.5-2), but **this is a hand
estimate on someone else's measurement, not the grade**. The fit computes its own amplitude
and ratio. With the eclipse, sin i ≈ 0.98 (SPOC's b = 0.66), so the companion's true mass is
about 0.093-0.100 M☉ (±3% from K) for primary masses 1.31-1.48 M☉: a star just above the
hydrogen-burning limit, not a brown dwarf.

## What changes
- Nothing in the pre-registered predictions or rules.
- **VSX:** BD+65 286 is still not in VSX, so the planned submission (after a C, or any label
  except D/E) stands. The remarks will credit Gaia DR3 (SB1 orbit), Green et al. 2023
  (ellipsoidal candidate and period) and the SPOC sector-52 TCE (first detection of the dip),
  and the type will be EA+ELL.
- Every public description of BD+65 286 now uses the narrowed claim above.
