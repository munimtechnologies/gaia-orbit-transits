# Gaia-only EBLM screen, TESS stage v1: graded (E1-E8), and a bug that hid every eclipse

2026-11-17. MV2 of Munim, Inc.; made with AI agents working in his name. Text CC BY 4.0.
Job `gaia-eblm-v1` (eblm_screen.py 0.1.0), finished 2026-11-17 21:19 UTC, 15 min, 0.21 GB.
Pre-registration: `findings/2026-11-17-gaia-only-eblm.md` (sections 5-6). Raw outputs:
`data/eblm-v1/`.

## 1. What the job did

- **Gaia stage (reproduced).** It reproduced the Gaia stage: 1,605 Gaia DR3 SB1 orbits
  with a same-period (within 1%) Gaia eclipsing binary.
  - Classes: 78 `twin_blend_suspect`, 290 `twin`, 169 `eblm_like` (167 with f(M) < 0.3), 1,068
    `other`.
  - The twin fraction by mass function is 52% / 21% / 25%, which reproduces the hand-run
    table (52% / 22% / 24%).
  - The job's `eblm_like` count (169) is larger than the 73 of the hand-run queries. The
    code applies the depth rules to the Gaussian (eclipse-only) depths for every row; the
    hand query used derived depths for part of the sample. The code's number is the one we
    use from now on.
- **TESS stage.** It ran on the 20 lowest-mass `eblm_like` systems.
  - 19 have TESS light curves.
  - **All 19 got the verdict NO_ECLIPSE.**

## 2. The bug

`vet_tess()` called `BoxLeastSquares(t, flux)` without `dy`, so astropy took every flux
error to be 1. Its `depth_snr` is then about depth × √N_in, which gave 1-3 for eclipses
1-11% deep, below the pre-registered SNR ≥ 10. The fold plots (`data/eblm-v1/plots/`)
show deep, clean eclipses in most of the 19. An example is Gaia DR3 4604416051842553216
(TIC 332545690): an 11% primary eclipse and a 2.5% secondary, both labelled "NO_ECLIPSE".

The measured depths were also not eclipse depths. They were box averages over BLS
durations that are often shorter or longer than the eclipse. That affected E5 and every
radius.

The unit tests did not catch it. They test `verdict()` on hand-made numbers, not the BLS
call. The new `eblm_fit.py` (0.1.0) passes real errors to BLS and replaces the box depths
with a physical eclipse model (section 4).

## 3. Grades (as pre-registered; nothing re-defined after the fact)

| | Prediction | Outcome | Grade |
|---|---|---|---|
| E1 | ≥ 18 of 20 have TESS data | 19 of 20 | **pass** |
| E2 | ≥ 80% show an eclipse at SNR ≥ 10 | 0 of 19 by the coded rule | **fail as run (code bug)** |
| E3 | median TESS ellipsoidal / Gaia-SB1 prediction in 0.7-1.3 | 1.01 (14 with a FLAME radius) | **pass** |
| E4 | ≤ 2 HOT_ or LUMINOUS_COMPANION | no verdict was reached; by the coded thresholds applied to the measured numbers, 0 | **pass on numbers, but see note** |
| E5 | median TESS / Gaia depth < 1 | 0.49, but box-average depths | **pass as coded, uninformative** |
| E6 | ≤ 2 of 5 EBLM_LARGE_RADIUS | no verdict reached | **not testable; re-tested in v2** |
| E7 | ≥ half have no EB entry in SIMBAD, VSX or the TESS EB catalogue | automated lookups failed (SIMBAD TAP and the CDS VizieR mirror returned 404); by hand, 4 of 4 checked are in VSX | **fail (very probably)** |
| E8 | no BD_ verdict | none (lowest m2 sin i upper 2σ bound 0.135 M☉) | **pass** |

**E2 by eye (post hoc, not a grade).** In 17 of the 19 fold plots an eclipse at the SB1
period is plain to see. The exceptions are Gaia DR3 1866019155321938560 and
3094854481749076736, where the light curve is ellipsoidal with slightly unequal minima.

**E4 note.** The coded thresholds (occultation/transit ≥ 0.3, or T2 ≥ 0.8 T1) were too
loose to catch a companion that is too bright for its mass.
- Six systems have occultations 0.17-0.26 of the primary eclipse (box ratios). That puts
  their companions' TESS-band brightness temperatures at 4,250-5,900 K.
- These companions have SB1 masses of 0.23-0.29 M☉, where a main-sequence M dwarf is
  ~3,300 K.
- Strong irradiation can explain part of this: in several of these systems a/R1 is below
  2. The v2 rule compares T2 with a ceiling that includes the irradiation.

**E7 note.** VSX has imported Gaia DR3's eclipsing binaries, so systems taken from Gaia's
own EB table are in VSX by construction.
- Examples: Gaia DR3 5419029403516595200 (type E, P = 1.38028 d), 500430730131632128
  (E, 1.37846 d), 1967665569327097088 (E, 3.00278 d).
- HIP 2964 is in VSX as "VAR" with P = 0.62947 d, half the SB1 period, amplitude 0.019 V.
- None of these four is in the TESS EB catalogue of Prša et al. (2022, sectors 1-26)
  (checked through the CfA VizieR mirror).
- **So these are known variables, not new objects.** What Gaia plus TESS add is the
  companion's mass and radius, and a sample built without any ground survey.

## 4. What the light curves show (by eye, all 19)

- **Detached systems with flat-bottomed primaries and tiny secondaries (classic EBLM
  shape).**
  - HIP 2964 (TIC 246895672, V = 8.5, F0V, P = 1.259 d): ~1.6% primary, ~0.15-0.2%
    secondary.
  - TIC 35044762 (Gaia DR3 5419029403516595200, P = 1.380 d): ~2.0% flat primary, ~0.1%
    secondary.
  - TIC 426763538 (Gaia DR3 500430730131632128, P = 1.378 d): ~2.2% primary, ~0.2%
    secondary.
  - TIC 276386308 (Gaia DR3 1967665569327097088, P = 3.003 d): 4.7% primary, 0.3%
    secondary, flat out of eclipse.
  - For HIP 2964, Gaia's SB1 gives K = 31.78 ± 0.32 km/s and m2 sin i = 0.2455 M☉.
- **Detached systems with luminous secondaries** (secondary 0.17-0.35 of primary): the six
  of the E4 note.
  - Three have TESS ellipsoidal amplitudes 2.4-8.7 times the SB1 prediction (Gaia DR3
    4604416051842553216, 6431159410558514432, 2932426102885101184). The companion is
    heavier than the SB1 says, so K is probably diluted.
  - Two agree with the SB1 mass (0.79-0.85×): Gaia DR3 5976702667540821376 (T1 ≈ 10,500 K)
    and 5557223240440494080.
  - In those two, a low-mass but bright companion would be either a strongly irradiated M
    dwarf or a stripped star (Algol / EL CVn-type). The v2 fit decides between them with
    the fitted a/R1.
- **Short-period (0.5-0.66 d) ellipsoidal variables with unequal minima,** probably
  grazing eclipses or near-contact binaries: eight systems. Their ellipsoidal amplitudes
  agree with the SB1 mass prediction (0.9-1.4×), which with Gaia's FLAME radii would put
  the F/A primaries close to filling their Roche lobes. That is physically odd for a
  q ≈ 0.1 system and needs the model fit.

## 5. Next

The re-run is pre-registered as `gaia-eblm-fit-v1` (eblm_fit.py 0.1.0), with a new
question and predictions in `findings/2026-11-17-eblm-fit-prereg.md`.
- It fits a limb-darkened eclipse model to all 167 eblm_like systems.
- It measures the primary's radius from the light curve itself.
- It asks whether M dwarfs in 0.5-3-day orbits are inflated. EBLM XIX (Davis et al. 2026)
  found none in its 50 high-quality systems, all with P > 5 d.
