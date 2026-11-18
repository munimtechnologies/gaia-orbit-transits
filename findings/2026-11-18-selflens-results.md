# Results: white-dwarf self-lensing pulses at Gaia-predicted conjunctions (gaia-selflens-v1)

By MV2 of Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Graded 2026-11-18 against `findings/2026-11-17-selflens-prereg.md` (written before the
data were read). Code: `selflens.py` 0.8.0. Job: `gaia-selflens-v1` (finished
2026-11-18 02:28 UTC, 84 min, 0.32 GB). Outputs: `data/selflens-v1/`.

## The question
Gaia DR3 astrometric orbits whose dark companion is probably a white dwarf (Shahaf et
al. 2024, updated table) predict *when* the white dwarf passes in front of its star. If
the orbit is close to edge-on, TESS should show a lensing **brightening** of a few
thousand ppm for hours to a day at that time. No such self-lensing binary has been found
in TESS (Yamaguchi, El-Badry et al. 2024, PASP), and no earlier work we found turns the
Gaia orbits into predicted pulse times.

## What ran
- 26,501 DR3 orbits read; the Shahaf et al. sources with G < 15 and |cos i| < 0.2 got
  Monte Carlo priors with white-dwarf radii; 250 targets, 133 with TESS light curves.
- The flux was inverted (2 − f) and searched with the unchanged box search.

## Grades
| # | prediction | result | grade |
|---|---|---|---|
| L1 | expected detectable pulses in the TESS data < 2 | 1.87 | **PASS** (barely) |
| L2 | no target passes the pulse rule (a clean null) | 15 targets, 17 events | **FAIL** |
| L3 | at most one control hit | 5 | **FAIL** |
| L4 | median predicted pulse amplitude 1,000–6,000 ppm | 4,578 ppm | **PASS** |

## What the failures mean
**The pulse rule is not specific enough for inverted TESS light curves.** With 1.87
detectable pulses expected at most (and probably far fewer, since Gaia's DR3 eclipse
probabilities look several times too high; see the calibration lead), 15 stars passing
means that almost all of the 17 events must be false alarms.
- **8 of the 17 events** sit within 1.7 d of the start or end of a data segment, or
  just before a gap (for example TIC 229706398 at 0.7 d before a segment end and TIC
  241197028 at 0.7 d). In inverted flux the ramps of scattered light and thermal
  settling at segment starts look like brightenings. The run's own plots (for example
  `data/selflens-v1/plots/04_13966000991651456.png`) show a ramp just before an orbit gap
  at the candidate time.
- **The control was not independent.** For orbits without an RV label, both conjunctions
  are searched. When the orbit is close to circular, the control window of one
  conjunction (shifted by P/2) lands on the other conjunction. So 3 of the 5 control
  hits are the *same events* that were counted as candidates. Only two control hits are
  independent: TIC 272090787 (Gaia DR3 5213080743808714112, an AstroSpectroSB1 whose RV
  label puts the white dwarf in front at the other conjunction) and a second event of
  TIC 357891418, 13 days from its candidate event.
- The 17-to-2 ratio of candidate to independent control hits is **not** evidence of real
  pulses: the targets were chosen for TESS coverage of the predicted windows, so the
  shifted control windows are covered much less often by construction.

## Status
No self-lensing candidate is claimed. The pre-registration requires every event that
passes the rule to go through the checks of `vet_event.py` plus a flare-shape test. That
vet is pre-registered in `findings/2026-11-18-selflens-vet-prereg.md` and queued as
`gaia-selflens-vet-v1` (`selflens_vet.py` 0.1.0), covering the 17 candidate events and
the two independent control events.

## A positive control that DR3 cannot give (checked 2026-11-18)
The five known Kepler self-lensing binaries would be the natural test of whether a Gaia
orbit predicts a pulse time. Through SIMBAD (CfA mirror) and the Gaia archive:
| system | Gaia DR3 source_id | G | RUWE | DR3 orbit? |
|---|---|---|---|---|
| KOI-3278 | 2052729252051464192 | 14.64 | 1.02 | no (non_single_star = 0) |
| KIC 3835482 | 2100012851946579584 | 13.28 | 2.80 | no |
| KIC 6233093 | 2075331706432389504 | 13.89 | 2.32 | no |
| KIC 12254688 | 2133138010555585024 | 12.97 | 1.53 | no |
| KIC 8145411 | (SIMBAD lists only DR2 2105324940515424896; not found in DR3 under that id) | | | |

None has a DR3 orbit, but three have RUWE 1.5–2.8, the excess expected from an
AU-scale white-dwarf orbit. **Gaia DR4 (2 December 2026) publishes epoch astrometry and
many more orbits.** If DR4 solves these three, we can do (a) the positive control
(do DR4 orbits predict the observed Kepler/TESS pulse times?) and (b) a mass test of
"Einstein vs Newton" for three more systems. So far only KOI-3278 has had this
(Yahalomi et al. 2019, arXiv:1904.11063). This is added to the DR4 release-day plan.

## Limits
Expected numbers use DR3 inclination errors taken at face value. The box search and
its artefact filters were designed for dips. Light curves are SPOC, TESS-SPOC or QLP
as found by lightkurve on 2026-11-18.
