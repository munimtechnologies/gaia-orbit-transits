# Results: TESS eclipse fits of CD-48 897, TOI-710 and UCAC4 117-030318 (job gaia-ebchar-v1)

2026-11-18. MV2 of Munim, Inc.; made with AI agents. Text CC BY 4.0, code Apache-2.0.
Pre-registration: `findings/2026-11-18-cd-48-897-prereg.md`. Code `eb_char.py` 0.1.0,
`eb_ephem.py` 0.1.0. Outputs: `data/ebchar-v1/`.

## Correction first: CD-48 897 was not ours to discover

In release 0.12.0 we called CD-48 897 (TIC 200743349, Gaia DR3 4749907416157959424) "a new
bright eclipsing binary". **That was wrong on priority.** The open working paper
*Eclipses by Appointment* (github.com/Snowstar38/eclipses-by-appointment, also made with AI
agents) lists it as claim Q031, "CONFIRMED", in `claim-adjudication.csv`. Its source report
is dated 2026-11-05, and the repository published its 1,031 claims on 2026-11-06. That is
twelve days before our report. Our prior-art check (VSX, the TESS EB catalogue, Gaia DR3
eclipsing binaries, ExoFOP and the Chopard-Vilhem Zenodo deposits) did not include that
repository. The project credits the method itself to Théo Chopard-Vilhem (Zenodo
10.5281/zenodo.22998328 and 23342416).

Consequences:
- We will **not** report CD-48 897 to AAVSO VSX as our discovery, and we withdraw the
  word "new" from 0.12.0 and from STATUS.md.
- What stays is an independent re-measurement in a separate pipeline. Their own "next
  check" for Q031 asks for exactly that ("remeasure the eclipses in another pipeline"). The
  numbers are below, for anyone to use.
- From now on, the prior-art check for any eclipsing system includes the *Eclipses by
  Appointment* claim tables and the Chopard-Vilhem deposits.

## CD-48 897: graded

| # | prediction | result | pass |
|---|---|---|---|
| E1 | ≥ 4 good primary eclipses deeper than 5% | 5 (sectors 3, 30, 31, 97, 97) | yes |
| E2 | rms O−C < 30 min; \|P_fit − P_Gaia\| ≤ 3σ | rms 0.33 min; 1.15σ | yes |
| E3 | depth spread ≤ 0.25 | 0.14 | yes |
| E4 | shallowest depth > 3 × contamination (0.063) | 0.114 | yes |
| — | fitted P within 0.002 d of 26.5328 (80%) | 26.532907 | yes |
| S1 | no secondary with SNR ≥ 7 within ±0.04 of phase 0.7398 (60%) | 225 ± 26 ppm at phase 0.7525 (SNR 8.8, 0.5-d box) | **no** |
| S2 | if a secondary exists, depth ≤ 3% | 0.022% | yes |

**Ephemeris (BJD_TDB):** T_min = 2458392.73244(50) + 26.5329072(79) E. The five timings fit a
straight line with χ² = 0.53 (4 d.o.f.) and rms 20 s. Fitted total duration 0.132 d
(3.2 h, not the ~2 h we wrote before), ingress fraction ~0.80 (V-shaped, grazing).
Depths are 12.7–13.2% in SPOC/TESS-SPOC and 11.4% in QLP (Sector 97); the difference
is consistent with different dilution corrections.

**Next eclipses** (mid-times; the formal error is ≤ 2 min, and the UTC times include the
light-time correction for this star's direction, about −4 to −1 min):
- 2026-11-19 ~21:58 UTC (BJD_TDB 2461364.4181), E = 112
- 2026-12-16 ~10:47 UTC (BJD_TDB 2461390.9510), E = 113
- 2027-01-11 ~23:36 UTC (BJD_TDB 2461417.4839), E = 114

**Secondary (S1 failed):** a 225-ppm box dip at phase 0.7525 near the Gaia-predicted far
conjunction (0.7398) reaches SNR 8.8 in white noise. We do not claim it: the scan tried
many phases and widths, and red noise is not included. A secondary of this depth is
physically possible for an early M dwarf behind a G dwarf, so it remains open.

**Four extra deep dips in Sector 97 are artefacts.** The dip census found four 5–12%
dips that are not at either conjunction (BTJD 3934.45, 3947.95, 3961.51, 3975.59; fold
phases 0.30–0.35 and 0.79–0.82). Each one begins 12–18 h after the start of one of
Sector 97's four TESS orbits (orbit starts 2025-09-15 03:50, 09-28 13:55, 10-12 06:10
and 10-26 11:15, from TESS_orbit_times.csv). Spacings of
13.50, 13.56 and 14.08 d follow the spacecraft orbit, not any one period. They are a
scattered-light or background problem in the QLP light curve, not a third body.
They do not touch the primary-eclipse fits, which use ±0.5 d around each eclipse.

## TOI-710.01 (HD 70623, TIC 309402106)

| # | prediction | result | pass |
|---|---|---|---|
| T1 | a good eclipse at a cycle n with n mod 3 ≠ 0 | n = 10 and 14 (sectors 28 and 38) | yes |
| T2 | P_fit agrees with Gaia SB1 (71.931 ± 0.054 d) within 3σ | 72.08204 d, 2.8σ | yes |

Six eclipses, each 0.53–0.60% deep and ~1.1–1.3 h long, fit
T = BTJD 1343.94287(45) + 72.082042(25) E. The TOI period (216.246 d) is three times the
true one or more. ExoFOP already lists TOI-710.01 as a TFOP false positive with the note
"v-shaped; period could be shorter". These fits give the shorter period, and its
agreement with Gaia's SB1 orbit (2.8σ) ties the eclipses to the star's own stellar or
substellar companion. The short, V-shaped events mean a grazing geometry. This is a vetting
detail, not a discovery.

## UCAC4 117-030318 (TIC 344750398)

| # | prediction | result | pass |
|---|---|---|---|
| U1 | the Sector 90 event refits with depth > 5% and duration 4–12 h | 22.2%, 6.9 h | yes |
| U2 | no other predicted epoch (P = 193.04 d) has TESS data | none had data | yes |

One event at BTJD 3756.508 that matches the Gaia SB1 conjunction. The TIC contamination
ratio is 0.41, and there is only one event, so it is not attributed to this star.

## Summary

The fits themselves passed as pre-registered. The scientific claim that mattered, that
CD-48 897 is a *new* eclipsing binary, fails on prior art. We were second, and we say so.
