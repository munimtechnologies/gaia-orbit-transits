# Gaia-only masses for eclipsing companions: Gaia DR3 SB1 orbits × Gaia eclipsing binaries

2026-11-17. MV2 of Munim, Inc.; made with AI agents working in his name. Text CC BY 4.0,
code Apache-2.0 (`eblm_screen.py`). Status: **Gaia-stage results (hand-run archive
queries) plus a pre-registration of the TESS test.** The predictions and rules in sections
5 and 6 were written before any TESS light curve of these stars was read. The job
`gaia-eblm-v1` reproduces every Gaia number below and runs the TESS test.

## 1. Question

Gaia DR3 measured two things independently:
- single-lined spectroscopic orbits (`nss_two_body_orbit`, SB1, from RVS);
- eclipsing-binary light curves (`vari_eclipsing_binary`, from G photometry).

When a star has both at the **same period**, and its light curve shows a **single shallow
eclipse**, Gaia alone gives:
- the companion's minimum mass, from K and the FLAME primary mass;
- its size, from the eclipse depth;
- which conjunction the eclipse is, from the RV argument of periastron;
- an independent mass check, from the ellipsoidal amplitude, which scales as
  q (R1/a)³.

So it gives a Gaia-only catalogue of low-mass companions eclipsing hotter stars. This is
the class the EBLM project uses to measure M-dwarf radii. If a companion below
0.075 M☉ turned up, it would be a transiting brown dwarf weighed by Gaia alone.

Gaia DR4 (2 December 2026) adds `rvs_two_body_orbit` (638,966 SB1 orbits) and full epoch
photometry, so the same code scales by orders of magnitude.

## 2. Two Gaia-internal facts (checked here)

1. **What the eclipse depth includes.** `derived_primary_ecl_depth` = Gaussian depth +
   2 × `geom_model_cosine_half_period_amplitude`, exactly, for all 5 single-eclipse stars
   tested. For example, 0.021211 + 2 × 0.012665 = 0.046541 mag for HIP 2964.
   - The Gaia DR3 datamodel does not say from which level the depth is measured.
   - The eclipse-only depth is therefore the Gaussian depth. Using the derived depth
     would overstate the companion's radius by up to 2×.
2. **Which conjunction is the eclipse.** The deeper eclipse falls at true anomaly
   f = π/2 − ω (RV convention: companion in front). This was verified on 18 Gaia
   EclipsingSpectro systems (`2026-11-17-sb1-transit-convention.md`).

## 3. Results (Gaia DR3, hand-run queries, 2026-11-17)

**Sample.** We took SB1 orbits with a Gaia eclipsing-binary period within 1% of the SB1
period (P_SB1 × f_EB = 1). Among those with two measured eclipses (f(M) here omits the
small (1 − e²)^1.5 factor):

| SB1 mass function f(M) | systems | near-equal eclipses (d2 ≥ 0.7 d1) | fraction |
|---|---|---|---|
| < 0.003 M☉ | 142 | 74 | **52%** |
| 0.003 – 0.03 M☉ | 555 | 121 | 22% |
| > 0.03 M☉ | 711 | 173 | 24% |

### 3a. A Gaia-internal flag for diluted SB1 amplitudes

- **Why near-equal eclipses matter.** They mean near-equal surface brightness, and on the
  main sequence that means near-equal masses. Two ~1 M☉ stars have f(M) ≈ 0.25 M☉ for an
  edge-on orbit.
- **What the table shows.** Near-equal eclipses are twice as common among the smallest
  mass functions as anywhere else. For those 74 systems, Gaia's SB1 K must be diluted by
  a factor of about 3–5: a blended double-lined spectrum was fitted as single-lined.
  - Most are short-period (0.3–1 d) contact or near-contact binaries.
- **What is already known.** That Gaia SB1 solutions of double-lined binaries underestimate
  K is known (El-Badry 2024, arXiv:2403.12146; Merle et al. 2023; Tokovinin 2023).
- **What is new here.** The Gaia-internal flag: an eclipse-depth ratio ≥ 0.7 together with
  f(M) < 0.003 M☉.
- **Why it matters for this project.** The 74 systems are the largest false-positive
  population for any "Gaia-only brown dwarf" search. In DR4 the code flags them as
  `twin_blend_suspect`.

### 3b. Single shallow eclipses: 73 Gaia-only EBLM-like systems

- **Selection:** primary eclipse < 0.1 mag, and no secondary eclipse (or one below 0.15
  of the primary).
- **Result:** 73 systems remain (`eblm_like`).
- **The lowest-mass ones.** The masses use FLAME M1 and sin i = 1. "ell ratio" is Gaia's
  observed ellipsoidal amplitude divided by the amplitude predicted from the SB1 mass
  (Morris 1985, α = 1.30). "Δφ" is the offset of the eclipse from the transit
  conjunction, in phase.

| Gaia DR3 (TIC) | G | P (d) | K (km/s) | M1, R1, Teff | m2 sin i (2σ) M☉ | eclipse (Gaussian) | R2 from depth | R2 / R_MS | ell ratio | R1 / Roche lobe | Δφ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4531797363284853888 (TIC 346363735) | 10.71 | 0.51473 | 23.2 ± 1.7 | 1.43, 1.69, 6780 K | **0.117** (0.100–0.134) | 1.60% | 0.21 R☉ | 1.5 | **1.00** | 0.91 | +0.03 |
| 1458828115020019328 | 10.41 | 0.59697 | 27.4 ± 1.5 | 1.75, 2.12, 7470 K | 0.166 | 2.35% | 0.33 | 1.7 | **1.01** | 0.98 | +0.03 |
| 1866019155321938560 (TIC 236093590) | 10.94 | 1.31930 | 21.2 ± 1.0 | 1.75, 3.03, 6480 K | 0.166 (0.150–0.182) | 0.52% | 0.22 | 1.14 | 0.88 | 0.83 | +0.03 |
| 2346634757461218816 (HIP 2964, TIC 246895672) | 8.47 | 1.25894 | 31.78 ± 0.32 | 1.64, 2.49, 6570 K | 0.2455 (0.241–0.250) | 1.93% | 0.35 | 1.31 | 0.86 | 0.75 | +0.002 |
| 4865466912871027200 | 10.83 | 1.10527 | 35.9 ± 1.6 | 1.90, 2.86, 7160 K | 0.293 | 2.28% | 0.43 | 1.42 | 0.92 | – | +0.02 |
| 6431159410558514432 | 10.58 | 3.2493 | 18.1 ± 0.9 | 2.25, 3.89, 7430 K | 0.23 | unconstrained (±0.1 mag) | – | – | 2.7 | – | +0.01 |

- **Masses: Gaia agrees with itself.** For five of the six, the ellipsoidal amplitude
  measured by Gaia photometry agrees with the one predicted from the Gaia RVS mass and the
  FLAME radius, to 0–14%.
  - The two pipelines are independent, so this checks the SB1 masses and the FLAME
    radii together.
  - The exception is 6431159410558514432, at 2.7×. Either its companion is heavier than
    the SB1 says, or its eclipse fit is poor: its eclipse depth is unconstrained.
- **Eclipse phase: always the transit.** For all 16 eblm_like systems checked by hand
  (the 16 lowest mass functions), the eclipse falls within 0.035 in phase of the transit
  conjunction. The exceptions are three with e ≥ 0.29, where our first-order hand formula
  is inexact. None falls at the occultation.
  - So the eclipsed object is the RV star, and the companion is fainter per unit area:
    a cool companion.
  - This argues against hot pre-helium white dwarfs (EL CVn binaries). In those, the
    deeper eclipse is usually the occultation of the hot companion.
- **Radii look too large.** Taken at face value, Gaia's eclipse depths give companion radii
  1.1–1.7× a main-sequence M dwarf of the SB1 mass.
  - Grazing geometry and sin i < 1 cannot fix this: grazing makes the eclipse shallower,
    and sin i > 0.8 for any eclipse here.
  - Limb darkening can account for about 10%.
  - Three explanations remain: Gaia's sparse-sampling Gaussian depth overestimates the
    true depth; the companions are inflated or young; or extra light or contamination
    (but extra light makes eclipses shallower, not deeper). TESS decides.
- **Two systems near Roche-lobe filling.** 1458828115020019328 (an A/F star of 7,470 K
  with 0.17 M☉ at 14.3 h) fills ~98% of its Roche lobe. TIC 346363735 (an F star with
  0.12 M☉ at 12.4 h) fills ~91%.
  - If confirmed, these are rare near-contact F + M systems, close to the onset of mass
    transfer. Their ellipsoidal amplitudes (1.7% and 2.4%) are what the SB1 masses
    predict.
- **Known?**
  - ExoFOP: none of TIC 346363735, TIC 236093590 or TIC 246895672 (HIP 2964, V ≈ 8.5,
    F0V) is a TOI or CTOI, and none has any follow-up.
  - Web searches found no eclipsing-binary entry for HIP 2964 or TYC 1595-38-1.
  - SIMBAD, VSX and the TESS EB catalogue (Prša et al. 2022) could not be reached from
    our tools; the job checks them. Until then these are **candidates, not discoveries.**
- **Brown dwarfs.** No eblm_like system has m2 sin i < 0.10 M☉. So **Gaia DR3 holds no
  single-eclipse SB1 system with a companion of brown-dwarf mass.** This is a negative
  result for the "Gaia-only transiting brown dwarf" question in DR3. The DR4 run on
  2 December is the real test.
- **TIC 207399049 (Gaia DR3 1622997463177004928), the lead object from run 8,** is not in
  `vari_eclipsing_binary`. Gaia classifies it only as a transit candidate (EP, nTransits
  5+). It passes the same depth–mass check: 1.2% depth → R2 ≈ 0.13 R☉ at m2 ≈ 0.071 M☉.

## 4. What is new (prior art checked 2026-11-17)

- **arXiv:2310.07936.** Gaia DR3 SB1s with brown-dwarf-mass companions matched to the TOI
  list and the TESS EB catalogue: three systems. That selection starts from TESS, not
  from Gaia's own eclipse table.
- **Rowan et al. 2022 (arXiv:2212.02509).** Masses and radii of Gaia spectroscopic
  binaries that are ASAS-SN eclipsing binaries: 70 systems, fitted with PHOEBE. They used
  ground-based eclipse catalogues and did not study the twin-dilution or the
  single-eclipse low-mass class.
- **Jayasinghe et al. 2022 (arXiv:2207.05086).** Vetted the *high*-mass-function SB1s.
- **El-Badry 2024 review and Merle et al. 2023.** The diluted K in blended SB2s fitted as
  SB1.
- **The EBLM project** (e.g. EBLM XVIII, arXiv:2511.23430) finds its targets in WASP
  photometry plus CORALIE RVs.
- **What we did not find:** a Gaia-internal SB1 × Gaia-EB catalogue of single-eclipse
  low-mass companions with Gaia-only mass, radius, conjunction and ellipsoidal checks, or
  the derived-depth decomposition in section 2.

## 5. Pre-registered TESS test (`gaia-eblm-v1`; written before any TESS data were read)

`eblm_screen.py` 0.1.0 runs these steps on the 20 lowest-mass eblm_like systems:
1. Resolve the TIC ID.
2. Download up to 6 TESS sectors (SPOC > TESS-SPOC > QLP).
3. Detrend with a running median of max(2 d, 3P) and bin to 10 min.
4. Run BLS within ±0.1% of the SB1 period.
5. Fit a harmonic out-of-eclipse model and measure the primary, secondary (phase 0.5),
   odd and even depths.
6. Derive R2 = R1·√depth and the companion's TESS-band brightness temperature from the
   occultation depth (Planck, 0.8 µm).

**Fixed rules (`verdict()`), applied in order:**
1. SNR < 10 or depth < 3σ → **NO_ECLIPSE**.
2. Odd and even depths differ by > 3σ → **TWIN_AT_2P**.
3. Occultation/transit ≥ 0.3 or T2 ≥ 0.8 T1 → **HOT_COMPANION** (T2 > T1; EL CVn-like) or
   **LUMINOUS_COMPANION**.
4. Ellipsoidal amplitude − 3σ > 2× predicted → **MASS_TENSION_HEAVIER**. Ellipsoidal
   amplitude + 3σ < 0.5× predicted → **MASS_TENSION_LIGHTER**.
5. R2 / R_MS > 1.3 → **EBLM_LARGE_RADIUS**; < 0.7 → **EBLM_SMALL_RADIUS**; otherwise
   **EBLM_CONSISTENT**.
   - The prefix **BD_** is added if m2 (K + 2σ) < 0.075 M☉.
   - R_MS is an approximate 5-Gyr M-dwarf relation (Baraffe et al. 2015 values, ±10%).

## 6. Predictions (probabilities ours)

- **E1.** At least 18 of the 20 have TESS light curves. (85%)
- **E2.** At least 80% of those with data show an eclipse at the SB1 period (SNR ≥ 10).
  (80%)
- **E3.** The median of TESS ellipsoidal / Gaia-SB1 prediction lies in 0.7–1.3. (70%)
- **E4.** At most 2 of the 20 are HOT_ or LUMINOUS_COMPANION. (70%)
- **E5.** The median of TESS primary depth / Gaia Gaussian depth (flux) is below 1: Gaia's
  sparse-sampling depths run high. (65%)
- **E6.** Of the five in the table with reliable depths, at most 2 end as
  EBLM_LARGE_RADIUS. (55%)
- **E7.** At least half of the 73 eblm_like systems have no eclipsing-binary entry in
  SIMBAD, VSX or the TESS EB catalogue. (60%)
- **E8 (certain from the Gaia stage).** No BD_ verdict, because the lowest m2 sin i is
  0.10 M☉ at 2σ.

**What follows.**
- **EBLM_CONSISTENT or EBLM_LARGE_RADIUS systems** that are not in the catalogues become a
  public candidate list in findings/. It goes with a suggestion of spectroscopic and
  photometric follow-up, sent to the EBLM team only after a human check (an "unsure"
  email, held for Sheehan).
- **An EBLM_LARGE_RADIUS verdict confirmed by TESS at a high SNR** would be a
  radius-inflation case worth a proper light-curve model.
- **HOT_COMPANION** would be an EL CVn candidate.
- **On DR4 release day,** the same code runs with `--schema gaiadr4` and adds
  `rvs_two_body_orbit`.

## 7. Limits

- The FLAME masses and radii assume a single star. The companion's light is negligible
  for an M dwarf, but not for a twin.
- Gaia's SB1 eccentricities at P < 3 d are often spurious; the hand phase formula is
  first order in e.
- `ms_radius` is approximate.
- The ellipsoidal α assumes u = 0.5, τ = 0.4. Gravity darkening differs for A/F stars by
  about 10%.
- Gaia's Gaussian eclipse model is fitted to about 40–70 sparse epochs. The job reports
  the TESS / Gaia depth ratio for that reason.

## 8. Queries (ESA Gaia archive, ADQL)

```
-- the sample (eblm_screen.sample_adql)
SELECT ... FROM gaiadr3.nss_two_body_orbit n JOIN gaiadr3.vari_eclipsing_binary v
  ON v.source_id = n.source_id JOIN gaiadr3.gaia_source g ON g.source_id = n.source_id
  LEFT JOIN gaiadr3.astrophysical_parameters p ON p.source_id = n.source_id
WHERE n.nss_solution_type = 'SB1' AND ABS(n.period * v.frequency - 1) < 0.01
-- twin counts: add  v.derived_secondary_ecl_depth > 0.7 * v.derived_primary_ecl_depth
--   AND 1.0361e-7 * n.period * POWER(n.semi_amplitude_primary, 3) < 0.003
-- depth decomposition: geom_model_gaussian1_depth, geom_model_cosine_half_period_amplitude,
--   derived_primary_ecl_depth for the five single-eclipse stars above
-- conjunction: (v.reference_time + v.derived_primary_ecl_phase / v.frequency - 2191.5
--   - n.t_periastron) / n.period, compared with f = pi/2 - omega
```

## Data

- ESA Gaia DR3 (Gaia Collaboration 2023), via the ESA Gaia Archive.
- ExoFOP-TESS.
