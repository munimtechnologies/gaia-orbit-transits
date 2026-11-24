# Pre-registration (step g8): can Gaia DR4 find eclipsing double-lined binaries by itself, where TESS cannot see them?

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked it yet.
Text CC BY 4.0, code Apache-2.0. Written 2026-11-24 (~22:30 UTC), eight days before Gaia DR4
(2 December 2026, 12:00 CET). No DR4 data exists yet, so every DR4 grade below is blind.
Code: `sb2_ecl_dr4.py` 0.1.0 with `test_sb2_ecl_dr4.py`; job templates in `runbook/g8/`.

## The question, and the wow if it works

Eclipsing double-lined binaries are the benchmarks of stellar physics: the velocities of both stars
and the eclipses together give masses and radii. Gaia DR4 will publish double-lined (SB2) orbits for
many more stars than DR3 and, for the first time, epoch photometry for essentially every source.

**Question:** among Gaia DR4's SB2 orbits with 0.4-15 d periods, how many eclipse in Gaia's own
photometry, at the conjunction times Gaia's own velocities predict, in stars that TESS cannot
resolve or measure well (G > 13, or Gaia neighbours within one TESS pixel holding at least half the
target's flux), and that no catalogue lists as eclipsing, including Gaia DR4's own
eclipsing-binary table?

**Wow:** hundreds of new eclipsing double-lined binaries, each with both stars' minimum masses
from Gaia and an inclination near 90 degrees, found by Gaia alone. A null or small result is also
informative: it would mean Gaia's own eclipsing-binary search already finds nearly all of them.

**Why it can work.** Gaia's photometric eclipsing-binary pipeline (Mowlavi et al. 2023 for DR3)
has to find a period in sparse epochs. For an SB2 the period and the conjunction times are already
known from the velocities, so two faint epochs at predicted conjunctions, in two different eclipses,
are enough. Our DR3 tests: among 31 bright ACV-class SB2s, all 6 stars that the earlier rule
(`gaia_conj_dips_acv` 0.1.0) flagged proved to be TESS eclipsing binaries already, and Gaia's dip
times matched the TESS ephemerides to 0.0002-0.034 d
(`findings/2026-11-24-acv-batch2-and-ijspeert-vet.md`). For bright stars TESS got there first. The
open ground is faint and crowded stars.

## Prior work searched (24 Nov 2026)

- Web search: Gaia double-lined spectroscopic binaries eclipses epoch photometry conjunction phase
  new eclipsing binaries masses 2026: no paper does this.
- Web search: Gaia DR4 EclipsingSpectro combined solutions, DR4 content: DR3 had 155 combined
  eclipsing + spectroscopic solutions (Arenou et al. 2023), made only where a photometric
  eclipsing-binary period and a spectroscopic period agreed. Nothing published on DR4's.
- ESA DR4 content page (cosmos.esa.int/web/gaia/dr4, read 24 Nov): `vari_eclipsing_binary`
  2,392,500 rows; `nss_two_body_orbit` 5,901,111; `nss_masses` 4,323,300; `rvs_two_body_orbit`
  638,966; `epoch_photometry` 121.8 billion rows via DataLink; reference epoch J2017.5.
- Closest work and how this differs:
  - Mowlavi et al. (2023), Gaia DR3 eclipsing-binary candidates (A&A 674, A16): photometry only,
    period searched blind. g8 uses Gaia's spectroscopic period and phase and counts Gaia's own
    eclipsing-binary table as "known", so only what that search missed can be new.
  - Rowan et al. (2023, arXiv:2212.02509): ASAS-SN eclipsing binaries matched with Gaia DR3
    SB2s, V > 11 only, and starting from ASAS-SN eclipses.
  - IJspeert et al. (2024, A&A 691, A242), Prša et al. (2022), Eclipses by Appointment (open
    GitHub project): TESS light curves, so bright and uncrowded stars.
  - arXiv:2310.12380 (Gaia SB1 conjunction times for transit vetting) and Beck et al. (2023,
    arXiv:2307.10812, Gaia epochs against TESS): use Gaia orbits or epochs to check TESS signals;
    neither searches Gaia's own photometry for eclipses at Gaia's own conjunctions.

## Sample (fixed now)

Every DR4 `nss_two_body_orbit` row with `nss_solution_type LIKE 'SB2%'`, 0.4 <= P <= 15 d and both
semi-amplitudes > 0 (first row per source). Split into 8 chunks by a fixed hash of source_id
(`chunk_of`); each chunk is processed in hash order. **TESS-blind** = G > 13, or (for G <= 13) the
summed G flux of all other Gaia DR4 sources within 21 arcsec is >= 0.5 of the target's. Stars with
G <= 13 whose crowding query failed are not TESS-blind (conservative).

## Rule (fixed now; `classify` in `sb2_ecl_dr4.py`)

1. Usable epochs: G-band epochs not flagged by Gaia (photometry or variability rejection).
   Fewer than 20: FEW_EPOCHS.
2. Phase from Gaia's orbit: phase = ((t - t_peri) / P) mod 1, t_peri = reference + t_periastron.
   Conjunctions at true anomaly 90 - omega and 270 - omega (0.25 and 0.75 when omega is not given).
3. Model: a 2-harmonic Fourier series in orbital phase fitted to the epochs more than 0.06 in phase
   from both conjunctions (one 5-sigma clip and refit); a median if fewer than 15 such epochs. This
   removes ellipsoidal and reflection variation, which also has minima at conjunction.
4. Dip: residual >= max(0.025 mag, 4 x robust SD of the fitted epochs' residuals).
5. **ECL_GAIA**: >= 2 dips within 0.035 in phase of a conjunction, from >= 2 different conjunction
   passages, and in-window dips >= 2 x out-of-window dips.
6. **ECL_GAIA_SHALLOW** (reported, not used in MAIN): the 3 largest residuals all within 0.02 of a
   conjunction, each >= 2.5 SD, from >= 2 passages.
7. **Null:** the same rule with both conjunction phases moved by +0.25 (quadrature).

## Known lists ("new" needs every lookup to answer, and all to say no)

Gaia DR4 `vari_eclipsing_binary`; any DR4 `nss_two_body_orbit` solution of the source whose type
contains "clipsing"; Gaia DR4 classifier best class starting with ECL; VSX eclipsing types within
30 arcsec; SIMBAD EB* within 10 arcsec; VizieR cones (10 arcsec) on the TESS eclipsing-binary
catalogue (J/ApJS/258/16) and TESS Ten Thousand (J/ApJS/279/50), each with a self-generated positive
control. Any lookup that cannot answer makes the star UNVETTED, never NEW.

## Grades (fixed now; `grade_all`)

- **G0 schema gate:** the orbit columns exist (source_id, nss_solution_type, period, t_periastron,
  eccentricity, arg_periastron, both semi-amplitudes) or exit 4 and write an adapter.
- **T0 time gate.** Controls: SB2s in Gaia's own eclipsing-binary table with >= 2 dips at any
  phase. TIME_OK if >= 20 controls and >= 50% of their pooled dips lie in the conjunction windows
  (chance: 14%). Tried first with reference J2017.5 (Gaia time 2739.375, DR4's documented epoch),
  then J2016.0 (2191.5, DR3's). The first that passes is used for every grade; the choice uses only
  controls. If neither passes: all grades are reported, not interpreted.
- **R1 recall:** share of SB2s in Gaia's eclipsing-binary table labelled ECL_GAIA or SHALLOW.
  RECALL_OK if >= 0.40 (>= 20 needed).
- **N1 null:** ECL_GAIA count against the null count. NULL_OK if real / max(1, null) >= 5.
- **B1 bright precision:** among ECL_GAIA stars with G < 11 that could be fully vetted, the share
  already known. PRECISION_OK if >= 0.70 (>= 10 needed).
- **M1 edge-on check (independent of photometry):** s3 = M1 sin^3 i (from the orbit) / M1 (from
  DR4 `nss_masses`). Eclipsing systems must be near edge-on. EDGE_ON_CONFIRMED if the ECL_GAIA
  stars' s3 exceeds the NONE stars' with AUC >= 0.6 and one-sided p <= 0.01; NOT_CONFIRMED if AUC
  < 0.55; WEAK otherwise; UNTESTABLE with < 10 in either group or no masses table.
- **MAIN:** number of TESS-blind ECL_GAIA stars vetted NEW. HUNDREDS (>= 100), DOZENS (20-99),
  FEW (1-19), NONE (0). UNVETTED ones are counted separately and checked by hand.

## Predictions (fixed now)

| Grade | Prediction |
|---|---|
| G0 passes | 85% |
| T0 | TIME_OK with J2017.5 70%; only with J2016.0 10%; neither / untestable 20% |
| R1 RECALL_OK | 55% |
| N1 NULL_OK | 75% |
| B1 PRECISION_OK | 60% (untestable 15%) |
| M1 EDGE_ON_CONFIRMED | 55% (untestable 25%) |
| MAIN | HUNDREDS 35%, DOZENS 30%, FEW 20%, NONE 15% |

## What we will do with the result

NEW stars go to a hand check of a random 20 (light curve folded at Gaia's period, both eclipse
windows, neighbours in Gaia), and the precision of that check is reported before any star is called
new in public. Masses: M sin^3 i of both stars, with i from the eclipse duration where possible
(step g7b). Submission of verified systems to AAVSO VSX needs an account (open item).

## Allowed changes after today

Data access only, as in earlier steps: the DataLink URL (chosen automatically from three templates,
with a control star, V1229 Tau, that must return >= 20 G epochs spanning > 1,500 d), TAP endpoints,
column names of the epoch files, and re-filing a chunk that stops at its deadline (the epoch cache
makes it continue). Any such change is written down, dated, before grading. The rule, the sample,
the thresholds and the predictions do not change. Grading happens when all 8 chunks have
processed their whole share, or on 9 December on what is done, whichever is first; the processed
fraction is reported.

## DR3 rehearsal (not blind; reported, not graded)

Job `g8-rehearsal-dr3-v1` runs the unit tests, the self-test and the rule on the 50 SB2s whose DR3
epochs are saved in this repository (`data/gaia-conj-dips*`; truth from
`data/ijspeert2024-check/ijspeert_check.csv`). It checks that the code runs on real Gaia epochs.
We have seen these stars, so its numbers say nothing about DR4. Expectations: at least 6 of the 11
stars that IJspeert et al. (2024) list as eclipsing are flagged (60%); at most 1 null flag (80%);
V1202 Cen (Gaia period 3.35 d, true 15.56 d) is not flagged as ECL_GAIA (70%). A crash, or a code
error found in it, is fixed in a dated 0.1.1 before DR4 without touching the rule's constants.

## Limits known now

DR4's SB2 count is not published; if it is very large, chunks may need several re-filings. Gaia's
eclipsing-binary table will contain many of the same stars, so "new" is the part its blind search
missed. Ellipsoidal variables with sharp minima, or very eccentric orbits with poorly measured
omega, can mimic or hide eclipses. The crowding measure uses Gaia sources only. The rule cannot see
eclipses shallower than about 0.025 mag except through the SHALLOW label, which is not graded.
