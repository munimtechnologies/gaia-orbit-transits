# Amendment 1 to the DR4 test of the DR3 eclipse deficit (calib-dr4)

2026-11-18, 14 days before Gaia DR4 (2 December 2026). No DR4 catalogue data exist or have
been seen. MV2 of Munim, Inc.; made with AI agents working in his name. Text CC BY 4.0, code
Apache-2.0. This amends `findings/2026-11-18-calib-dr4-prereg.md`. Everything there still
holds unless changed below. The code that carries it out is `dr4_fetch.py` 0.1.0 and
`calib_dr4_run.py` 0.1.0 (with `calib_dr4.py` 0.1.0 unchanged).

## 1. Tables (from ESA's DR4 contents page, read 2026-11-18)

- DR3 → DR4 cross-match: **`gaiadr4.dr3_neighbourhood`** (table 07.03, TAP, 2,448,832,159
  rows). Its columns are assumed to follow DR3's `dr2_neighbourhood`: `source_id` (DR4),
  `dr3_source_id`, `angular_distance`, `magnitude_difference`. The unit of
  `angular_distance` is read from TAP_SCHEMA at run time.
- Orbits: **`gaiadr4.nss_two_body_orbit`** (10.08, TAP, 5,901,111 rows) and the bright-source
  `gaiadr4.nss_two_body_orbit_supp`. ESA notes that DR4's table is consolidated from several
  processing modules.
- The reference epoch of `t_periastron` is taken as `gaiadr4.gaia_source.ref_epoch`
  (expected J2017.5, BTJD 936.875). The TAP_SCHEMA description of `t_periastron` is saved
  with the run. If it names a different epoch, the run is repeated with `--t-ref-btjd`
  before anything is graded.
- Every table and column is checked in TAP_SCHEMA first. If one is missing, the run stops
  (exit 4) and lists what exists. There is no silent fallback.

## 2. Rules the pre-registration left open (fixed now)

- **Match.** The DR4 source nearest to the DR3 source within 1 arcsec. The match is
  **ambiguous** (UNTESTABLE) if a second DR4 source within 1 arcsec is within 1 mag of the
  DR3 source's brightness, or has no magnitude difference, or if two of our DR3 targets
  claim the same DR4 source.
- **Which DR4 solution.** Only astrometric or combined solutions count (Orbital*,
  AstroSpectroSB1). If a source has several, the choice follows a fixed order:
  AstroSpectroSB1, OrbitalTargetedSearchValidated, Orbital, OrbitalTargetedSearch,
  OrbitalAlternativeValidated, OrbitalAlternative. Ties go to the higher significance.
  **Never by period,** which would bias the result toward CONFIRMED.
- **Unknown solution types.** If any matched source carries a solution type not in that
  list or in the known non-astrometric list, the run stops before grading (exit 5). The
  type is then classified from the DR4 data model's description, not from its effect on
  the result.
- **cos i₄ and σ₄.** cos i₄ comes from the central Thiele–Innes constants, using the same
  circular-orbit rule as DR3. σ₄ is the standard deviation of 4,000 Monte Carlo draws from
  `gaia_orbits.sample_orbit` with the published correlation matrix. That is the same
  estimator as DR3's `cosi_sd`. The fraction of orbits whose `corr_vec` could not be used
  is reported.
- **lim₄** is the larger of the two conjunction limits (R₁ + R₂)/r_c. It uses the DR4 P, e
  and ω, and DR3's masses and radii (from the calib-v3 priors).
- **z₄** applies to E targets in window mode. Take the time of the 9σ TESS eclipse, found
  by the same rule as calib-window. Find the DR4 conjunction (t1 or t2) whose central
  prediction lies nearest it in phase. z₄ = median offset / (1.4826 × MAD) over the Monte
  Carlo draws. If that spread is ≥ P/4, the phase is lost: the target gets no z₄ and is
  counted.

## 3. Added test K2b (paired; graded alongside K1–K6, none of which change)

Our sample was cut at |cos i| ≤ 0.2, but the eclipse limits are only ~0.01–0.05. So many
targets may already look "not edge-on" (|cos i| > lim + 2σ) **in DR3 itself**. K2 could
then pass even if DR4 changed nothing. K2b measures the change.

- **K2b passes** if, among CONFIRMED targets, the fraction of N flagged not-edge-on rises
  from DR3 to DR4 by **≥ 0.20**, with exact one-sided McNemar p < 0.05, while E's fraction
  changes by ≤ 0.10.
- Reading (K) predicts this, because the less noisy DR4 positions should move the
  non-eclipsing orbits away from edge-on. Our expectation: 35%.
- If the DR3 rehearsal (below) shows that K2 already passes on DR3's own values, K2 is
  reported but **not used** in the reading. K2b takes its place.

## 4. DR3 dress rehearsal (job gaia-calibdr4-reh-v1, before release)

The same code runs with DR3 as the "new" release: identity cross-match and
`gaiadr3.nss_two_body_orbit`. It must pass:

- **RH1:** all 162 targets come back CONFIRMED.
- **RH2:** for ≥ 95%, |cos i − cos i_DR3| < 0.1 σ_DR3, and for ≥ 90%, the Monte Carlo σ is
  within 0.8–1.25 of DR3's.
- **RH3:** the rms of z over timed E targets is within 15% of calib-window's 2.665 at 9σ.
- **RH4:** no failures (K1 fail fractions both 0).

It also reports the DR3 baseline of K2 and runs the real cross-match code on DR3 ← DR2
(`gaiadr3.dr2_neighbourhood`) as a smoke test. If a rehearsal check fails, the code is
fixed and the rehearsal re-run before 2 December. Fixes to code are logged here; the
rules above do not change.

## 5. Known DR3 false positives

ESA's DR3 known issue "NSS: false-positive astrometric binary solutions" names four
sources whose orbits came from a software bug: 4698424845771339520, 5765846127180770432,
522135261462534528 and 1712614124767394816. **None is in the 162-target sample.**
1712614124767394816 (HIP 66074) was excluded as untimeable, 4698424845771339520 had no
TESS data, and the other two never entered it.
