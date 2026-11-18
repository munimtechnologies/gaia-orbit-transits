# Results: vetting the 19 white-dwarf self-lensing "pulses" (gaia-selflens-vet-v1)

By MV2 of Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Graded 2026-11-18 against `findings/2026-11-18-selflens-vet-prereg.md` (written before any
vetting data were read). Code: `selflens_vet.py` 0.1.0. Job: `gaia-selflens-vet-v1`
(finished 2026-11-18 11:31 UTC, 31 min, 0.29 GB). Outputs: `data/selflens-vet-v1/`.

## Bottom line
**No self-lensing candidate survives.** Under the pre-registered rules, 13 of the 19
events are rejected, 4 cannot be measured and 2 survive. Both survivors then fail simple
physical checks that use only numbers already in hand. We did not pre-register those
checks, and they are reported as such below. The first search for white-dwarf
self-lensing pulses at Gaia-predicted conjunction times therefore ends as a null result.
Only 1.87 detectable pulses were expected at most, and probably fewer, so the null is not
surprising and constrains little.

## Grades
| # | prediction | result | grade |
|---|---|---|---|
| V1 | ≥ 15 of the 17 candidate events REJECTED | 11 rejected, 4 unresolved, 2 survive | **FAIL** |
| V2 | every near-edge candidate REJECTED | 7 of 8 (the 8th could not be measured) | **FAIL** |
| V3 | neither independent control event SURVIVES | both REJECTED | **PASS** |
| V4 | at most one event SURVIVES | 2 | **FAIL** |
| V5 | injected predicted pulse recovered at SNR ≥ 5 in ≥ 70% of events | 53% | **FAIL** |

**What the V5 failure means.** The box test against a ±1.5-d linear baseline recovers an
injected pulse of the predicted size in only about half of the light curves, because the
red noise and curvature of 200–1800-s QLP light curves are large. The vet is therefore
weak at saying that something is *not* there. No rejection here rests on low SNR alone:
every event rejected as "not significant" also failed a systematics, flare, edge or
off-target test. The rejections stand.

The 13 rejections (11 candidates, 2 controls) cite background jumps (9 events), many
neighbour stars brightening at the same time (7), flags (3), segment edges (3),
asymmetric flare-like shapes (5) and off-target difference images (4). These are the usual scattered-light and systematics
signatures of inverted TESS light curves.

## The two survivors, and why neither is a self-lensing pulse (post-hoc checks)
### TIC 15761587 (Gaia DR3 52122761031936256), BTJD 3243.345, Sector 71
A brightening of about 0.9% lasting about 4 h. It is seen in QLP (SNR 13.5) and in a
TESScut aperture (SNR 13.4), is centred on the target (difference image 0.4 px), and no
neighbour shows it (plots in `data/selflens-vet-v1/plots/`). The star is a K dwarf
(T_eff ≈ 5,000 K; G = 13.27), with a Gaia DR3 astrometric orbit of P = 515.6 ± 3.3 d,
e = 0.11 and i = 89.18 ± 0.43°. A dark companion of about 0.57 M☉ would fit the
2.54-mas photocentre orbit, a typical white-dwarf mass.

The orbit fixes how large a self-lensing pulse can be. The amplitude is about
2(R_E/R★)², where the Einstein radius R_E depends only on the lens mass and the
star-lens separation:
- with M₂ = 0.57 M☉, separation 297 R☉ and R★ = 0.73 R☉, R_E = 0.038 R☉, and the
  **largest possible pulse (a central crossing) is about 5,100–5,400 ppm lasting about
  11 h**;
- a 4-h pulse must be a grazing crossing (impact parameter about 0.93), where limb
  darkening lowers the pulse to about 3,300–3,800 ppm;
- the measured amplitude is **9,500 ± 700 ppm (QLP) and 7,500 ± 560 ppm (TESScut)**. That
  is 3.7–5.8σ above even the central-crossing ceiling, and 6.7–8σ above what a 4-h
  crossing allows.

A companion heavy enough to make such a pulse (about 1.5 M☉ or more) would produce a
photocentre orbit about twice as large as Gaia measured. The same search also found two
further brightenings in this 11-day stretch, at BTJD 3242.51 (SNR 7.1, 8 h) and 3235.12
(SNR 6.7, at a segment edge). So the light curve has several features of this kind. The
event also falls 46 d (2.8 Gaia σ) from the predicted conjunction. **Verdict: not a
self-lensing pulse by the Gaia companion.** Its cause (stellar activity or an instrumental
feature) is not pursued. A K2 Campaign 4 light curve exists for this star (EPIC
210858075). We note it, but given the amplitude mismatch it is not worth a dedicated test.

### TIC 425703690 (Gaia DR3 5795606707192913536), BTJD 4130.514, Sector 102
A 3,000-ppm, 8-h excess on top of a broad, curved trend in the QLP light curve.
- In the same self-lensing search windows of this star, the original box search found
  **14 other brightenings with SNR 6–34**, twelve of them deeper than 1%. Most coincide
  with brightenings in other targets (systematics), but not all. The candidate is
  unremarkable for this light curve.
- It sits at the top of a downward-curving stretch. A straight baseline fitted over ±1.5 d
  on both sides of a maximum produces a positive "excess" by itself. The injected
  predicted pulse, 3 d away on the falling part of the curve, was not recovered (SNR 2.0).

**Verdict: intrinsic variability or systematics, not a pulse.**

## Lessons carried into the DR4 version (pre-registered before DR4 data exist)
1. A **physical amplitude ceiling** from the Gaia orbit becomes a hard rule. Reject any
   event whose amplitude exceeds 2(R_E/R★)² by more than 3σ, using a ±30% band for M₂
   and R★.
2. A **per-star uniqueness test**: the event must be the strongest brightening of its
   duration in all of the star's TESS data, after the same filters.
3. A **quadratic local baseline** next to the linear one. An event must pass with both.
4. Injection recovery is reported per star, so a null at a star with poor sensitivity is
   not counted as a real null.

## Limits
These physical checks were done after the vet, by hand, from the job's measured
amplitudes and the Gaia DR3 orbit parameters (VizieR I/357, TIC 8). They were not
pre-registered. They are simple enough to check from the numbers above, and they can
only reject, not promote, a candidate.
