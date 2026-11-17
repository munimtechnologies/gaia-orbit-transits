# Are M dwarfs in short orbits inflated? A Gaia-weighed test (pre-registration, eblm_fit 0.1.0)

2026-11-17, written before any eblm_fit model was fitted to any light curve. MV2 of
Munim, Inc.; made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.
Job: `gaia-eblm-fit-v1`.

**What we had seen before writing this.** The 19 fold plots and numbers of gaia-eblm-v1
(`findings/2026-11-17-eblm-v1-results.md`), for the 19 lowest-mass of the 167 systems. G5
and G6 below are informed by them, and are marked that way. Nothing from the other 148
systems had been seen.

## 1. Question and why it matters

M dwarfs in eclipsing binaries have long looked 5-15% larger than stellar models predict
("radius inflation"). The leading explanation is magnetic activity in fast-rotating,
tidally locked stars, which predicts that inflation grows at short orbital periods.

The newest homogeneous test, EBLM XIX (Davis, Triaud et al. 2026, arXiv:2610.18338,
accepted by MNRAS), finds **no inflation (0.3 ± 1.6%)** in 50 high-quality low-mass
eclipsing binaries. All 50 have **P > 5 d** (SOPHIE RVs plus TESS).

**The short-period regime, where magnetic inflation should be strongest, is the one they
did not test.** Gaia DR3 gives SB1 orbits and Gaia's own eclipse classification for a set
of mostly 0.5-3-d systems with F/A primaries and 0.1-0.4 M☉ companions. With TESS light
curves:
- the mass comes from Gaia's K and the inclination;
- the radius comes from the eclipse.

No new spectroscopy is needed. Gaia DR4 (2 December 2026: 638,966 RVS SB1 orbits) can
grow this sample by orders of magnitude.

**The wow if it works:** the first Gaia-weighed sample of short-period M dwarfs, which
either shows that inflation turns on at short periods, where EBLM XIX could not look, or
extends their null result there. DR4 scales it from tens to thousands of systems.

## 2. Method (eblm_fit.py 0.1.0)

1. **Sample.** Same Gaia query and classes as eblm_screen 0.1.0. All `eblm_like` systems
   with f(M) < 0.3 (167), from the lowest m2 sin i up.
2. **TESS.** Up to 4 sectors (SPOC > TESS-SPOC > QLP), running-median detrend over
   max(2 d, 3P), 10-min bins.
3. **Eclipse phase.** BLS within ±0.1% of the SB1 period, with real errors (the v1 bug
   fixed).
4. **Model.** Fitted to 1,000 phase bins:
   - circular orbit;
   - quadratic limb darkening (approximate TESS-band coefficients from Teff);
   - exact ring-integrated occultation of the primary by a disc of radius k R1 at impact
     parameter b;
   - the companion's occultation (depth Ds, which also dilutes the transit);
   - harmonics to 3rd order (ellipsoidal, reflection, beaming);
   - smoothing over the exposure time.
   - The fit has free parameters dphi, k, b and a/R1, with the linear part solved exactly
     at each step (Nelder-Mead, three starting b).
5. **Detection.** snr_fit = √(Δχ² / max(1, χ²_red)) against the harmonics-only model.
6. **Physics.**
   - i from b and a/R1. m2 from the SB1 mass function divided by sin³ i, with M1 = FLAME
     (1.3 M☉ if missing, flagged).
   - a from Kepler; R1,lc = a / (a/R1); R2 = k R1,lc.
   - Inflation = R2 / R_MS(m2) − 1, with R_MS from the approximate 5-Gyr Baraffe et al.
     (2015) relation in eblm_screen.
   - The same with R1 = FLAME as a cross-check.
   - k is refitted with u1 + 0.1 to give the limb-darkening sensitivity.

## 3. Verdict rules (in order; `verdict()`)

1. snr_fit < 10 → **NO_ECLIPSE**.
2. Odd and even transit amplitudes differ by > 3σ **and** > 10% → **TWIN_AT_2P**.
3. TESS ellipsoidal − 3σ > 2 × the prediction (from fitted m2, a/R1, i) →
   **MASS_TENSION_HEAVIER**. TESS ellipsoidal + 3σ < 0.5 × the prediction →
   **MASS_TENSION_LIGHTER**.
4. The companion's TESS brightness temperature at its 3σ lower bound is > 1.15 ×
   T_allow → **TOO_LUMINOUS** (a stripped or hot companion, or a wrong mass).
   T_allow = (T_MS(m2)⁴ + (T1 √(R1/a))⁴)^¼: the dwarf's own temperature plus
   substellar-point irradiation.
5. b > 1 − k → **EBLM_GRAZING** (k and b degenerate; excluded from the inflation test).
6. Otherwise **EBLM_LARGE_RADIUS** (inflation > +30%), **EBLM_SMALL_RADIUS** (< −30%), or
   **EBLM_CONSISTENT**. The prefix BD_ is added if m2's 2σ upper bound is < 0.075 M☉.

**Inflation test.** Over all EBLM_CONSISTENT / LARGE / SMALL systems (the "clean" set):
the median of R2/R_MS − 1 and its bootstrap 95% interval (2,000 resamples, seed
20261117).
- **INFLATED** if the lower bound > +0.05.
- **DEFLATED** if the upper bound < −0.05.
- **CONSISTENT** if the interval contains 0 and is narrower than 0.2.
- Otherwise **INCONCLUSIVE**.
- It is also reported for P < 1.5 d and P ≥ 1.5 d separately, and with FLAME radii.

## 4. Predictions (our probabilities)

- **G1.** ≥ 80% of systems with TESS data have snr_fit ≥ 10. (85%)
- **G2.** Median R1,lc / R1,FLAME over the clean set is within 0.85-1.15. (65%) A failure
  means either the FLAME radii or our model is off, and both inflation numbers are then
  suspect.
- **G3.** ≥ 10 clean EBLM fits. (60%)
- **G4.** The inflation-test outcome. INFLATED 40%, CONSISTENT 25%, INCONCLUSIVE 30%,
  DEFLATED 5%.
- **G5 (informed by v1).** ≥ 3 TOO_LUMINOUS. (50%)
- **G6 (tests the bug fix; informed by v1).** ≥ 15 of the 19 v1 systems have
  snr_fit ≥ 10. (90%)
- **E6 (re-test of v1's E6).** Of Gaia DR3 4531797363284853888, 1458828115020019328,
  1866019155321938560, 2346634757461218816 and 4865466912871027200, at most 2 are
  EBLM_LARGE_RADIUS. (55%)
- **E5 (re-test with model depths).** Median TESS model depth / Gaia Gaussian depth < 1
  among the detected. (60%)

## 5. What follows from each outcome

- **INFLATED with G2 passing.** Write it up with every system's fit plot and the
  systematics budget below. Then:
  - ask a human expert to check it before any claim (an "unsure" email, held for
    Sheehan's approval);
  - run the same code on DR4 on 2 December.
- **CONSISTENT.** An honest extension of the EBLM XIX null result to short periods, with
  lower precision. Publish it as such.
- **INCONCLUSIVE / TOO_FEW.** The DR3 sample is too small or too noisy. Say so, and move
  the test to DR4.
- **TOO_LUMINOUS systems with consistent ellipsoidal amplitudes.** These are candidate
  stripped companions (Algol / EL CVn progenitors) with Gaia masses. Check each against
  the EL CVn literature before calling any of them new.

## 6. Systematics we know about (none fixed after seeing results)

- **FLAME masses** assume a single star: about 5-10%. This enters m2 as M1^(2/3) and R2
  as M1^(1/3), so a 10% M1 error moves inflation by ~3%.
- **R_MS relation** is approximate, ±10%. It is the same for every system, so it shifts
  the median, not the scatter. Any INFLATED result must exceed it before it means
  anything physical. We will report it against both the table and the EBLM XIX
  calibration.
- **Limb darkening** (approximate, ±0.1): the k_ld_shift column shows the effect.
- **Circular orbits** are assumed. Gaia's short-period SB1 eccentricities are mostly
  spurious.
- **Third light.** Third light from neighbours is corrected only as far as the SPOC/QLP
  crowding correction does. Unresolved companions dilute the eclipse and bias R2 low, so
  they work against an inflation claim.
- **Young primaries.** If a primary is young, its companion can be pre-main-sequence and
  genuinely large. Ages are not modelled.
- **Selection.** Gaia's sparse photometry favours deep eclipses, which may favour large
  companions. This bias can only be removed with DR4's completeness information.
