# TIC 71945261: youth and archival-RV check, graded (job gaia-tic71945261-followup-v3)

By MV2 of Munim, Inc. Made with AI agents working in his name; not yet checked by a human
expert. Text CC BY 4.0, code Apache-2.0.

Rules: `findings/2026-11-19-tic71945261-followup-prereg.md` (written 19 Nov ~11:40 UTC, before
any version of the job ran). Code: `youth_rv_check.py` 0.1.2 (0.1.1 fixed a date parser, 0.1.2
added timeouts and partial saves; no rule changed). Raw output: `data/tic71945261-followup-v3/`
(`youth_rv_check.json`, `youth_rv_report.md`, `job_summary.json`). Job ran 20 Nov 02:55-03:50 UTC,
exit 0, self-test passed.

Target: TIC 71945261 = TYC 6340-23-1 = Gaia DR3 6853008555751131648 (G 10.53, parallax
9.016 ± 0.018 mas, 110.9 pc). The earlier pre-registered fit
(`findings/2026-11-19-tic71945261-fit-results.md`) found a new 2.3287-day eclipsing system whose
companion is 0.224 R☉ at Gaia's 0.097 M☉, 1.9 times the main-sequence radius (label
B_OVERSIZED_COMPANION). This check asks whether the two easiest explanations, a young system or a
wrong Gaia semi-amplitude K, can already be decided from public data.

## Grade

| Step | Pre-registered rule | Result | Verdict |
|---|---|---|---|
| Control | AU Mic must get β Pic MG probability ≥ 0.8 | BPMG 0.927 (with RV), 0.986 (without) | **passed** |
| Youth (with γ = −17.57 ± 0.39 km/s) | ≥ 0.8 young, < 0.2 field | young-association probability **0.0041** (FIELD 0.9959; best group Argus 0.0031) | **FIELD_KINEMATIC** |
| Youth (no RV) | same | 0.037 (FIELD 0.963) | FIELD_KINEMATIC |
| Archival RVs | grade each RV with epoch error < 0.05 d against K = 16.16 vs 32.4 km/s | **none found** (RAVE DR6, GALAH DR3, APOGEE DR17: 0 rows within 10″) | no verdicts; **K question stays open** |

Heliocentric UVW = (−19.6, −14.8, −6.3) km/s, |v| = 25.3 km/s: ordinary thin-disk motion.

## What this means (as fixed in the pre-registration)

- FIELD_KINEMATIC removes only the easiest form of the youth explanation: membership of a known
  young moving group. It does not prove the system is old. Young stars outside known groups
  exist, so **youth is not excluded without a lithium spectrum.**
- "Inflated" needs all three of: FIELD_KINEMATIC (met), no RV supporting the heavy K (met only
  because there is no RV at all), and a human-led spectrum showing no lithium (not done). **So
  we still do not call the companion inflated.** Allowed wording: a companion "twice the
  expected size for its Gaia mass", with youth or a wrong mass not yet excluded.
- The label stays **B_OVERSIZED_COMPANION**.

## Ungraded facts (named in the pre-registration as ungraded)

- Gaia's `rv_amplitude_robust` (max-min of 15 epoch RVs after outlier rejection) is
  **32.54 km/s**. 2K from Gaia's orbit is 32.32 km/s; the heavy hypothesis (a normal-size
  0.21 M☉ companion) needs 2K = 64.8 km/s. This favours Gaia's K but is **not independent**: the
  orbit was fitted to the same epochs.
- Ellipsoidal amplitude in the one TESS sector: −198 ± 206 ppm (predicted +304 ppm for 0.097 M☉,
  ~660 ppm for 0.21 M☉). Single-sector, white-noise error bar: weak evidence.

## Limits of this run

- **The 0.3° control cones were skipped for the time budget** (`control_0p3deg_n:
  skipped_budget`). The pre-registration added them so that an empty answer means "not observed"
  rather than "service down". The empty RAVE/GALAH/APOGEE answers came from the
  vizier.cfa.harvard.edu mirror (the Strasbourg server returned HTTP 404 for every catalogue);
  the same mirror returned rows for GALEX GUVcat and the TIC for this star within the same
  minute, so an outage is unlikely, but it is not formally excluded.
- X-ray: no ROSAT 2RXS source within 10″. eRASS1 (the German eROSITA release) covers only
  Galactic longitude 180-360°; this star is at l = 21.6°, so its empty eRASS1 answer carries no
  information. Neither X-ray result was graded.
- A GALEX AIS source lies 0.8″ away (NUV 16.26 ± 0.02, FUV 21.2 ± 0.2). No NUV-excess test was
  pre-registered, so we do not interpret it.

- TESS coverage: MAST TESScut lists only sector 92 (camera 2, CCD 1) for this position (checked
  20 Nov), so the radius cannot yet be refitted on a second TESS sector.

## What would settle it

One or two high-resolution spectra: Li I 6708 Å (age), a measured K (mass), and any second set
of lines (a blend or triple). That needs a human-led observing request; we have asked for it to
be offered to a team that observes such systems.

## Prediction check

The pre-registration made no outcome predictions, so there is none to report as held or failed.
