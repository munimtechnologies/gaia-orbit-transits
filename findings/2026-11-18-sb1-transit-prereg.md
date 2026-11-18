# Pre-registration: do Gaia DR3's brown-dwarf-mass spectroscopic orbits transit as often as they must?

2026-11-18. MV2 of Munim, Inc.; made with AI agents working in his name. Text CC BY 4.0,
code Apache-2.0 (`sb1_transit.py` 0.1.0). Written and published **before any light curve
was searched**. Jobs: `gaia-sb1tr-c0-v1`, `gaia-sb1tr-c1-v1` (two random halves).

## The question

Gaia DR3 published 181,327 single-lined spectroscopic orbits (SB1). Thousands of them
have mass functions that put the unseen companion in the brown-dwarf or very-low-mass-star
range: a live Gaia archive query on 2026-11-18 gives **21,130 SB1/SB1C orbits with
P = 1–1000 d, G ≤ 13 and K³P < 15,440** (mass function below ~1.6 × 10⁻³ M☉), and 18,796
over all magnitudes with f(M) < 6 × 10⁻⁴ M☉. Stevenson et al. (2023, AJ 166, 225,
arXiv:2310.07936) counted 2,490 Sun-like primaries with minimum companion masses below
78.5 M_Jup and found **three** transiting companions by matching them to the TESS TOI
list (TOI-2533 b, a 72 M_Jup brown dwarf; TOI-1712 b and TOI-5427 b, very-low-mass stars).

If those orbits were real and the companions really were that light, geometry alone
says how many must transit: a fraction (R₁ + R₂)/r, about 12 % at P = 3 d around a Sun-like
star and 5–20 % over P = 1–13 d. That is ~200 transiting systems among Stevenson's 2,490,
not three. Either the TOI list misses most of them (possible: TOIs exclude many
eclipsing binaries and faint targets), or most low-K Gaia SB1 solutions are not what they
seem (spurious orbits from pulsation, activity or blends, or companions on near-face-on
orbits that are really heavier). **No published study has measured the transit rate
of these orbits directly in TESS light curves** (searches of arXiv, ADS-indexed journals
and the web on 2026-11-18; the closest work is Stevenson et al. 2023, which used the TOI
list, and arXiv:2310.12380, which used Gaia SB1 orbits to reject TOIs).

**Why it matters.** Gaia DR3 SB1 orbits are used in population studies of the brown-dwarf
desert, and Gaia DR4 (2 December 2026) will publish ~639,000 RVS SB1 orbits. A direct,
calibrated measurement of how many low-mass DR3 SB1 orbits are real tells everyone how to
weight them. Every transiting one is also a companion with a true mass (sin i ≈ 1) and a
radius: new transiting brown dwarfs are rare (a few dozen are known).

## Method (fixed before the data are read)

1. **Sample.** Gaia DR3 `nss_two_body_orbit` SB1 and SB1C, 1 ≤ P < 13 d, G ≤ 13,
   K³P < 15,440 on the server; then m₂ sin i (iterated with M₁ from FLAME, else a
   main-sequence relation in absolute G) between 0.005 and 0.10 M☉; R₁ ≤ 2.5 R☉ and
   log g ≥ 3.5 where known; e < 0.9. Seeded random order (seed 20261118), two halves.
   Each job processes stars in that order for 165 minutes.
   *Why P < 13 d:* with fewer than three transits per TESS sector, a phase-free fold is a
   single-event search, and period-shifted controls cannot calibrate its false alarms.
2. **TESS data.** Up to three sectors per star (SPOC 120 s, else TESS-SPOC, else QLP;
   most recent first), quality-masked, 30-min bins, cadences within 0.25 d of gaps > 0.1 d
   and of the ends dropped (dipsearch 0.4.4 DR4 options), detrended per segment with a
   running median of window max(3D, 0.5 d).
3. **Search.** Each sector is folded at the Gaia period with the **phase left free**.
   (Gaia's period error makes the predicted transit time drift by 0.2–1 d by the TESS
   years for P ≈ 3.5–6.7 d: for TOI-1712, TOI-2533 and TOI-5427 the 3σ windows exceed
   P/8. Within one sector the drift is negligible.) Box width D = max(0.6 T₁₄, 1 h), with
   T₁₄ the central duration for R₂ = 0.10 R☉ (m₂ < 0.08) or m₂^0.9.
4. **Sector hit** (all must hold): SNR ≥ 7, where SNR is the smaller of the white-noise
   SNR and the empirical SNR across all trial phases; ≥ 70 % of the depth survives
   against the neighbouring phases (1–3 box widths away); the box holds ≥ 3 separate
   transits; and removing the strongest single transit leaves SNR ≥ 3. **Star hit:** any
   used sector hits.
5. **Sensitivity.** The expected transit (depth 0.8 (R₂/R₁)², duration T₁₄) is injected
   into the raw flux at 4 random phases (the real best box masked unless overlapping);
   s = fraction recovered within one box width of the injected phase. The **rate sample**
   is every processed star with s ≥ 0.5.
6. **Control.** The same fold search at 0.8541 P and 0.9137 P (near P, so the same number
   of cycles, but non-harmonic), after masking the best box at P so a real transit cannot
   leak into them. Controls get the same depth and modulation classes as real hits.
7. **Classes of a hit.** MODULATED if a sinusoid at P in the undetrended flux has a
   semi-amplitude > 0.5 × the box depth (spots or pulsation at P, i.e. a spurious RV
   orbit); else TOO_DEEP if the depth exceeds 3 × (R₂/R₁)² (a diluted or stellar
   companion); else SUBSTELLAR_SIZE.
8. **Reality fraction.** ρ = (N_hit − N_control) / Σ(p_transit × s) over the rate sample,
   for all hits and for SUBSTELLAR_SIZE hits. 95 % interval from the Garwood interval of
   N_hit.
9. **Independent timing check.** For each hit, the found transit time is compared with
   Gaia's own prediction (transit at true anomaly f = π/2 − ω; transit-time error from a
   400-draw Monte Carlo over Gaia's correlation matrix, plus a quarter box width for the
   phase grid). PHASE_MATCH if |z| < 3, PHASE_MISMATCH otherwise, UNTIMED if 3σ ≥ P/4.

## Hand-worked checks (in the tests)

- **WASP-18 (positive control for the transit convention).** Gaia DR3 4955371367334610048
  has an SB1 solution with P = 0.9414685 d, e = 0.123, ω = 142.73°, T = −0.33996 d from
  J2016.0. f = π/2 − ω gives transit phase 0.88307 after periastron, so BTJD 389.4914.
  Carried 2,991 orbits forward at the TESS period, that lands **0.022 d** from the TOI-185
  epoch (BTJD 3205.3533). At Gaia's own period it is off by 0.070 d, about 0.9σ, with
  k·σ_P = 0.079 d.
- TOI-2533-like orbit (K 7.39 km/s, P 6.6847 d, circular, 1 M☉): m₂ sin i = 0.0683 M☉.
- P = 3 d, 1 M☉ + 0.05 M☉: a = 8.897 R☉, p_transit = 0.1236, T₁₄ = 0.1183 d.
- Garwood 95 %: n = 0 → [0, 3.689]; n = 1 → [0.0253, 5.572]; n = 5 → [1.624, 11.668].
- A synthetic sector (P 3.1 d, 1 % dips, 500 ppm noise, a mid-sector gap) gives a hit at
  the right phase, no control hits, PHASE_MATCH, sensitivity ≥ 0.75. The same sector
  without dips gives no hit, and a single dip gives no hit. A Gaia timing 0.5 d off gives
  PHASE_MISMATCH.

## Predictions and pass rules (graded per job and combined)

| | prediction | pass rule |
|---|---|---|
| C1 | the method sees known transiting companions | ≥ 3 of WASP-18 b, TOI-2533 b, TOI-1712 b, TOI-5427 b hit at the Gaia period (untestable if < 3 have TESS data) |
| C2 | false alarms are rare | control hit rate ≤ 3 % of the rate sample |
| C3 | enough stars | ≥ 150 in the rate sample per job |
| **H1** | **most DR3 low-mass SB1 orbits at P = 1–13 d do not show the transits a real low-mass companion must give** | upper 95 % bound of ρ (SUBSTELLAR_SIZE) < 0.5 |
| H2 | (exploratory) longer periods are more often real (short-period low-K "orbits" include pulsators) | ρ_all(P ≥ 5 d) > ρ_all(P < 5 d) |
| H3 | the hits are real orbital transits, not unrelated dips | > 50 % of the hits that Gaia still times are PHASE_MATCH |
| D1 | (report only) | SUBSTELLAR_SIZE hits not on the TOI list go to vetting (pixels, centroids, odd/even, secondary, SIMBAD/VSX). None is called a brown dwarf before that. |

My honest expectation: ρ ≈ 0.02–0.2. Stevenson et al.'s 3-in-2,490 implies ρ ≈ 0.015
if the TOI list were complete, so H1 passes. If H1 **fails**, most of these orbits are
real and TESS holds dozens of untabulated transiting brown dwarfs and M dwarfs. That
would be the bigger surprise, and it would be checked first against the controls and
the timing test.

## What would make this a "wow"

Either way the result is a first: the first direct, injection-calibrated measurement of
how many Gaia DR3 brown-dwarf-mass spectroscopic orbits are real, made one data release
before DR4 multiplies the sample by thirty. If ρ is high, there are also new transiting
brown dwarfs with masses from Gaia alone.

## Limits stated in advance

- p_transit assumes isotropic orientations. Orbits picked for a low m₂ sin i are biased
  toward face-on heavier companions, so ρ measures "real **and** truly low-mass", not
  "real" alone. The m₂ sin i distribution of the hits and the TOO_DEEP class bound this.
- Injected transits are boxes at the central duration and 0.8 × the full depth, which
  is optimistic for grazing geometries. That makes Σ(p·s) a slight overestimate, so ρ
  is a slight underestimate.
- Periodic systematics at P (for example momentum dumps) would not show in the
  near-P controls. H3, the vetting and the plots address this.
- Only up to three sectors per star; dilution from neighbours is not corrected (TESS
  pixels are 21″).
- QLP fluxes (KSPSAP) are already detrended by their pipeline.

## Data and code

ESA Gaia DR3 (Gaia Collaboration 2023, Arenou et al. 2023) via the ESA Gaia archive; TESS
SPOC, TESS-SPOC and QLP light curves via MAST and lightkurve; TESS TOI list via ExoFOP.
Code: `sb1_transit.py`, `test_sb1_transit.py` (pure Python),
`synthetic_check_sb1_transit.py` (numpy, run in the job), with `dipsearch.py` and
`vet_event.py` pinned at v0.13.1.
