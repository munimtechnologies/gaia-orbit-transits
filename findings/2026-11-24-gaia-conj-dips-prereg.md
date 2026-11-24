# Pre-registration: TESS test of the two Gaia-epoch eclipse candidates CD-63 310 and CD-72 1603

2026-11-24 (~17:30 UTC), gaia-orbit-transits. By MV2 of Munim, Inc.; made with AI agents working in
his name. Text CC BY 4.0, code Apache-2.0. Registered before any TESS light curve of either star
was looked at by us.

## Question

`findings/2026-11-24-gaia-conj-dips.md` found that CD-63 310 (Gaia DR3 5288669213282803328, TIC
349572805) and CD-72 1603 (Gaia DR3 6374372070227419008, TIC 371839648), both edge-on Gaia DR3
double-lined binaries, dim in Gaia's own photometry at a conjunction of their Gaia orbit. Do TESS
light curves show eclipses at Gaia's period, at the conjunction times Gaia's orbit predicts?

## Method (fixed)

- Code: `gaia_dip_ffi.py` 0.1.0 runs the per-star analysis of `sb2_ffiscan.py` 0.1.0 **unchanged**,
  fetched in the job's setup from commit b53e2b3c0e0e1adfbd4ec2c41c9f2405e7e512a9 (its method,
  thresholds and conjunction test are in `findings/2026-11-24-sb2-ffiscan-prereg.md`). The only
  differences are the star list and up to 8 TESS sectors per star instead of 6 (`--max-lc 8`).
- Stars (10, fixed): the 2 candidates; 2 positive controls, the eclipsing binaries HD 250735 and
  CD-28 7251 found earlier in this project; and 6 'flat' stars whose Gaia epochs showed no dip
  (Gaia DR3 6025454428973694464, 6370053605166404992, 3043555010111094400, 2995056243702062080,
  3419201066092932992, 6547214134176807808).
- Orbits from Gaia DR3 nss_two_body_orbit (ESA TAP, else the AIP mirror; ESA's archive is closed
  25 Nov - 2 Dec). The period must equal the one in the star list (anchor).
- Job: gaia-dip-ffi-v1 (1 CPU, 1.5 GB). Run order: offline unit tests, sb2_ffiscan self-test, run.

## Predictions and grading (from `gaia_dip_ffi.grade`)

- **D0 (controls):** HD 250735 and CD-28 7251 are both DETECTED with PHASE_MATCH. If not, the
  verdict is UNTESTABLE_CONTROLS_FAILED and D1/D2 are not interpreted.
- **D1:** CD-63 310 is DETECTED with PHASE_MATCH (label CONFIRMED_AT_GAIA_CONJUNCTION). Secondary
  expectations, reported but not part of the verdict: the primary TESS box maps to the same
  conjunction as the Gaia dip (c2, phase 0.75), and the depth is grazing (≤ 0.10 in relative flux).
- **D2:** CD-72 1603 is DETECTED with PHASE_MATCH. Secondary: the box maps to c1 (phase 0.25),
  grazing depth.
- **Verdict:** BOTH_CONFIRMED / ONE_CONFIRMED / NEITHER_CONFIRMED (if D0 holds).
- **D3 (expectation):** at most 1 of the 6 flat stars is DETECTED with PHASE_MATCH.

What we will do with each outcome: BOTH or ONE confirmed: those stars become new double-lined
eclipsing binaries with Gaia masses, after the usual hand vetting (pixel neighbours, catalogue check
again on the day). NEITHER: we report that Gaia-epoch dips at conjunction did not predict TESS
eclipses here, and the Gaia dips stay unexplained. A failed control means the test says nothing.

## Limits known in advance

- sb2_ffiscan detrends with a 2-harmonic fit at Gaia's period. A very shallow grazing eclipse can
  be partly absorbed by it; that would push toward NOT_DETECTED, never toward a false detection.
- TESS pixels are 21 arcseconds. A TESS eclipse alone does not prove which star eclipses. Gaia's
  own dips, at 0.4-arcsecond resolution, point to the target.
