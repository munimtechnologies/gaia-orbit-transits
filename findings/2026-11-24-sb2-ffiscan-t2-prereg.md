# Pre-registration: full-frame TESS fold of tier-2 Gaia DR3 double-lined orbits (sb2_ffiscan_t2 0.1.0)

MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.
Written 2026-11-24 ~13:40 UTC, before the job `sb2-ffiscan-t2-v1` has run and before any tier-2 light curve
was looked at by us. Repository: https://github.com/munimtechnologies/gaia-orbit-transits

## Why this step

- The edge-on SB2 screen (tier 1: 0.95 <= r <= 1.10, r = m1 sin^3 i / m1 from binary_masses) found two bright
  eclipsing binaries in no catalogue (HD 250735, CD-28 7251).
- Amendment 2 (findings/2026-11-24-g5-amendment-2-tier2.md) showed on Rowan et al. (2023) eclipsing SB2s that
  the tier-1 window misses most of them (Gaia's photometric m1 runs high), and registered tier 2
  (0.85 <= r < 0.95 or 1.10 < r <= 1.15). Its job `sb2-tier2-dr3-v1` uses only TESS SPOC pipeline detections,
  which exist only for stars observed at 2-minute cadence.
- A spot check by hand on 2026-11-24 shows the gap: **HD 35131** (Gaia DR3 262216446435606016, TIC 309683389,
  G 9.11, SB2, P 4.06235 d, e 0.052, K1 96.1 / K2 85.0 km/s, m1 1.347) has r = 0.869 (tier 2), yet no SPOC TCE,
  no TOI, no VSX entry within 3 arcmin, no Gaia variability class and no Gaia epoch photometry. SIMBAD lists it
  only as a spectroscopic binary. Only full-frame images can say whether it eclipses.
- `sb2_ffiscan 0.1.0` (pre-registered in findings/2026-11-24-sb2-ffiscan-prereg.md, commit b53e2b3) already folds
  SPOC, TESS-SPOC and QLP light curves at Gaia's period and tests the dip against Gaia's predicted conjunction
  times. This step runs it, with every threshold unchanged, on tier 2.

## Method (fixed)

1. Sample: every row of data/sb2-edgeon-screen-v1/gaia_sb2_m1_p8.csv (commit 80be282) that sb2_tier2 0.1.0
   `select_tier2` keeps (one row per source), sorted by Gaia G, brightest first.
2. Catalogue pass, BEFORE any light curve is read: TIC (ExoFOP by Gaia ID), VSX (30 arcsec), ExoFOP TOIs,
   Gaia DR3 vari_eclipsing_binary and vari_classifier_result (AIP mirror first, then ESA). Roles:
   control = VSX eclipsing type, or in Gaia's EB table, or Gaia class ECL*, or one of the 61 Rowan et al. 2023
   systems; toi = a TOI; target = all others. Written to ffiscan_t2_roles.csv before the light-curve pass.
3. Gaia orbit (period, e, omega, T_peri with errors) from nss_two_body_orbit, AIP mirror first. Anchor: the
   mirror's period must equal the saved table's within 1e-7 (relative); otherwise the conjunction test is
   UNTESTABLE for that star (the fold still runs at the saved period).
4. Per star, `sb2_ffiscan.analyse` unchanged: up to 6 sectors (SPOC 2-min > TESS-SPOC > QLP), detrend,
   2-harmonic removal, box search within +-5 sigma of Gaia's period, 12 null periods.
   DETECTED: S/N >= 10, >= 1.5 x the best null, >= 2 cycles. PHASE_MATCH: dip within 3 sigma of a Gaia
   conjunction. Secondary dip and dip separation vs Gaia's e, omega as in 0.1.0.
5. Grades: `sb2_ffiscan.grade` unchanged (F0 controls, F1 Gaia phases, F2 candidates), F3 marked
   NOT_APPLICABLE, plus T2F_sample and the HD 35131 record. Time limit 400 min; if truncated, the faintest
   stars are the ones not reached and the summary says so.

## Predictions (made before the run)

| ID | Prediction | Probability |
|----|------------|-------------|
| P0 | Tier-2 sample size in 120-300 (same range as amendment 2's T2_0) | 70% |
| P0R | All 10 Rowan tier-2 systems (hand values) are in the sample | 85% |
| P1 | F0 CONTROLS_OK: >= 80% of controls with TESS data are DETECTED | 70% |
| P2 | F1 GAIA_PHASES_OK: >= 80% of detected controls with a testable orbit are PHASE_MATCH | 65% |
| P3a | F2: >= 1 target DETECTED + PHASE_MATCH and not VSX-eclipsing | 75% |
| P3b | F2: >= 3 such targets | 45% |
| P3c | F2: >= 5 such targets | 25% |
| P4 | HD 35131 DETECTED with PHASE_MATCH | 30% |

Base rates: tier 1 gave pipeline eclipse detections for 66 of 161 tested stars (41%); tier 2 has lower
typical inclinations, so fewer and shallower eclipses are expected. P4 is a single star with r = 0.869.
If Gaia's m1 were exact, sin i = 0.869^(1/3) = 0.954, i = 72.6 deg. With R1 ~ 2.1 R_sun (TIC 8.2), R2 ~ 1.5 R_sun
and a ~ 14.5 R_sun (P 4.06 d, M1 + M2 ~ 2.5 M_sun), eclipses need cos i < ~0.25, i > ~75.6 deg, i.e. Gaia's m1
must run high by >= ~5% (Mdyn/m1 <= ~0.954). Rowan's calibration (median Mdyn/m1 0.976, mean 0.955, spread to
0.70) makes that plausible but not likely; shallow grazing eclipses may also fall below S/N 10.

## What counts as a discovery

A target in F2 is only a **candidate**. Before anything is called new, each is hand-vetted against: Eclipses by
Appointment (accepted-systems.csv at its newest commit), Rowan 2023 table, VizieR CfA Prša 2022 and TESS Ten
Thousand, VSX, SIMBAD, ExoFOP, Gaia DR3 EB tables, a web and arXiv search for its names, and a look at the fold
(ffiscan_t2_folds.csv) for blends (a brighter star within 1 arcmin -> pixel check before any claim).
A negative result (no candidate, or controls failing) is published as such.

## Not changed

No threshold of sb2_ffiscan 0.1.0 is changed. The tier-2 boundaries are those of sb2_tier2 0.1.0.
