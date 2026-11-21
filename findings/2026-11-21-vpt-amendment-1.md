# Amendment 1 to step g (Gaia's own transit candidates x TESS), fixed before Gaia DR4

Written 2026-11-21 (~16:00 UTC), eleven days before Gaia DR4 (2 December 2026), with no DR4
data seen. By MV2 of Munim, Inc.; made with AI agents working in his name, not yet checked by a
human expert. Amends `findings/2026-11-21-vpt-tess-prereg.md`. Code: `gaia_vpt_tess.py` 0.1.1
(no search step changed). Text CC BY 4.0, code Apache-2.0.

## Why an amendment

The pre-registration allowed a dated 0.1.1 after the DR3 rehearsal. Chunk 0 of that rehearsal
(job gaia-vpt-dr3-c0-v1, 107 of the 214 DR3 candidates; data `data/vpt-dr3-v1/c0/`, interim note
`findings/2026-11-21-vpt-dr3-c0-interim.md`) showed two things the design did not expect.
Chunk 1 (gaia-vpt-dr3-c1-v1) has not run yet; nothing from it has been seen.

1. **Gaia's published period is usually not the known period.** Of 90 known systems in chunk 0
   (planets in the NASA Exoplanet Archive or TOIs on the same TIC), only **11** carry a Gaia
   `transit_period` within 1% of a known period at ratio 1, 1/2 or 2 (KNOWN_PLANET); **79** do
   not (KNOWN_SYSTEM_OTHER_P). These are mostly well-known hot Jupiters (WASP-121 b, WASP-12 b,
   WASP-43 b, WASP-48 b, HAT-P-36 b ...), so the planet is real and the Gaia period is wrong. We checked that this is the current, corrected table
   (`solution_id` 375523436409132247, which replaced the erroneous 13 June 2022 table on
   7 February 2023), on both the ESA archive and the Heidelberg mirror. The Gaia DR3
   documentation (section 10.10.1) says only that the parameters of the 173 known planets "do
   not necessarily match the known, nominal parameters"; we found no published count.
2. **The pooled control rate measures the wrong thing.** Control hits were 23 of 172 trials
   (0.134 > 0.08: CONTROLS_NOISY, so G1 is invalid as registered). They come almost entirely
   from stars that have a real deep signal at a period other than Gaia's: 20 of 124 trials on
   KNOWN_SYSTEM_OTHER_P stars and 3 of 22 on NEW stars (two RV binaries), but **0 of 22** on
   KNOWN_PLANET stars, where Gaia's period is right and masking the best box removes the real
   signal. The pooled rate therefore mixes "a real signal is present at another period" with
   noise false alarms. Only the second belongs in G1's subtraction.

## What changes (0.1.1)

- **G0b_kp and G1b (new; G1b is the primary G1 for DR4).** The control false-alarm rate is
  measured only on rate-sample KNOWN_PLANET stars (control hits / 2n). G0b_kp = CONTROLS_OK if
  that rate is <= 0.08 with at least 10 such stars, else CONTROLS_NOISY (UNTESTABLE if fewer than
  10). G1b is G1's formula and labels with this rate, valid only if G0a = PIPELINE_OK and
  G0b_kp = CONTROLS_OK. Reported with it, not graded: the same fraction using the 95% Garwood
  upper bound of the known-planet control rate (`fraction_seen_conservative`). The original G0b
  and G1 are still computed and reported, unchanged.
- **G5 (new, descriptive): Gaia period reliability.** Among candidates in KNOWN_PLANET or
  KNOWN_SYSTEM_OTHER_P, the share whose Gaia period matches a known period (= KNOWN_PLANET),
  with a Wilson interval. Labels: PERIODS_MOSTLY_RIGHT >= 0.5, PERIODS_MIXED 0.2-0.5,
  PERIODS_MOSTLY_WRONG < 0.2, UNTESTABLE below 10 systems. Caveat fixed now: a multi-planet
  system where Gaia found a different real planet would count as "wrong"; in chunk 0 only two of
  the 79 (WASP-53 and Kepler-1513) list more than one known planet.
- **RVS screen (new; `--rvs-screen`, merged with `--combine ... --rvs-file`).** For every
  candidate, Gaia's own RVS variability test, the conservative criterion of Katz et al. 2023
  (A&A 674, A5): `rv_chisq_pvalue` <= 0.01, `rv_renormalised_gof` > 4, `rv_nb_transits` >= 10
  and `rv_template_teff` in 3900-8000 K -> RV_VARIABLE; statistics present but criterion
  failed -> RV_QUIET; no statistics (DR3 gives them only for G_RVS <= 12) or outside the
  ranges -> RV_UNTESTED. A hot Jupiter moves its star by about 0.1-0.3 km/s, far below RVS
  precision, so RV_VARIABLE means a stellar or brown-dwarf companion (or an RVS systematic).
  **G2b** = planet-like NEW hits that are not RV_VARIABLE. G2b is the list taken forward to
  prior-art search, step (f) and a pixel test.
- **Why a hit is not proof that Gaia's period is right** (no code change; reported): in chunk 0,
  10 of 62 sensitive KNOWN_SYSTEM_OTHER_P stars still "hit" at Gaia's wrong period (8 of them
  with eclipsing-binary flags, 2 planet-like: TOI-150 at one third of its period, WASP-113 at
  0.60 of it). Every G2b candidate's period is therefore checked by eye on the full TESS light
  curve before it is quoted.
- **G6, a period-free TESS search, is planned, not registered.** If its rules and code (0.2.0)
  are committed before 2 Dec 12:00 CET it runs on DR4; if not, it is dropped for DR4.

## What does not change

The TESS search, hit rule, injections, sensitivity cut, categories, vetting flags, G0a, G2, G3
and G4 are as registered. The DR3 rehearsal stays not blind. G1b was designed after seeing
chunk 0, so on DR3 it is reported, not graded; it is graded only on DR4.

## Predictions (fixed now)

DR3 chunk 1 (held out; its categories and TESS results are unseen):
- G5 on chunk 1 alone: PERIODS_MOSTLY_WRONG 85%, PERIODS_MIXED 13%, PERIODS_MOSTLY_RIGHT 2%.
- G0b_kp on chunk 1 alone: CONTROLS_OK 70% (UNTESTABLE if fewer than 10 known planets, 25%).

Gaia DR4 (blind; DR4 has a 66-month baseline against DR3's 34, which should help periods):
- G5: PERIODS_MOSTLY_RIGHT 30%, PERIODS_MIXED 35%, PERIODS_MOSTLY_WRONG 30%, UNTESTABLE 5%.
- G0b_kp: CONTROLS_OK 80%.
- G1b: MOSTLY_SEEN 35%, MIXED 35%, MOSTLY_NOT_SEEN 20%, UNTESTABLE 10%.
- RVS (if DR4 `gaia_source` carries the same statistics): at least 25% of the RVS-testable NEW
  candidates are RV_VARIABLE, 60%. If the columns are missing or renamed, the screen exits 4 and
  step (f) (`transit_rv_screen.py`, DR4 epoch RVs) replaces it; no number is read before a dated
  mapping note.

## Release day

Step g uses 0.1.1 (the commit that publishes this amendment). After the six chunks: run
`--rvs-screen --schema gaiadr4`, then `--combine k0 ... k5 --rvs-file <rvs>/vpt_rvs.csv`.
`runbook/dr4-release-day.md` is updated with the same commands.
