# DR4 wobble test: the rehearsal on ESA's DR4 pre-release passed

2026-11-19. MV2 of Munim, Inc.; made with AI agents working in his name, not yet checked by a
human expert. Text CC BY 4.0. The rehearsal is pre-registered in
`findings/2026-11-19-dr4-wobble-prereg.md` and amendment 1. Code: `dr4_wobble.py` 0.1.0
(release 0.25.0), unchanged. Outputs: `data/wobble-reh-v1/`.

This is a check of release-day code, **not a result about Gaia DR3's orbits**. That test runs
on Gaia DR4 (2 December 2026).

## What ran
Job gaia-wobble-reh-v1 ran on the Dell, finishing 19 Nov 09:18 UTC.
- **Data:** it downloaded ESA's DR4 pre-release of epoch astrometry
  (`gaia-dr4-prerelease-epoch-astrometry_2026-06-26.zip`, 625,651 bytes,
  SHA-256 `07f0e8d9…5fa0b`). The VOTable's release tag is "Gaia DR4_RC3". It holds 1,008
  field-of-view transits of 12 sources, 54–93 transits each.
- **Fits:** it fitted every source with the pre-registered linear model (amendment 1 layout).
  The DR3 period, eccentricity and periastron time were held fixed.

## Pre-registered rule and result
| check | rule | value | pass |
|---|---|---|---|
| HD 114762 (Gaia DR3 3937211745905473024) at its own DR3 orbit | Δχ² > 30 | **60.5** | yes |
| QSO 2237987199365376 at HD 114762's orbit | Δχ² < 30 | 1.19 | yes |
| QSO 60730287810150016 at HD 114762's orbit | Δχ² < 30 | 0.64 | yes |
| QSO 10973744521070720 at HD 114762's orbit | Δχ² < 30 | 2.07 | yes |

**The rehearsal passes.** The six single stars, fitted at HD 114762's orbit (descriptive), give
Δχ² between 1.1 and 5.7. All 9 null fits are far below 30.

## Orbits recovered from DR4 epoch astrometry (descriptive)
| source | DR3 solution | P (d) | a₀ DR3 (mas) | a₀ DR4 fit (mas) | ratio | cos i DR3 | cos i DR4 fit | Δχ² |
|---|---|---|---|---|---|---|---|---|
| HD 114762 | OrbitalTargetedSearchValidated | 83.74 | 1.797 | 1.895 | 1.05 | 0.946 | 0.955 ± 0.162 | 60.5 |
| Gaia-4 (1457486023639239296) | Orbital | 564.0 | 0.313 | 0.254 | 0.81 | −0.429 | −0.530 ± 0.145 | 82.8 |

- Both residual plots (`data/wobble-reh-v1/wobble_*.png`) lie along y = x.
- Gaia-4 hosts the 11–13 M_Jup planet Gaia-4b (Stefansson et al. 2024, arXiv:2410.05654).
  A joint fit of this same pre-release astrometry with radial velocities already exists
  (arXiv:2611.15537). Our recovery is only a check of our code, not a new measurement.
- Gaia BH3 (4318465066420528000) has no DR3 orbit, so it was fitted only at HD 114762's orbit.
  As expected, it was not detected there.

## Two things learned for release day
1. **What the pre-registered statistic measures.** AGIS excess noise is added in quadrature to
   each transit's error. For HD 114762, that noise (1.23 mas) is mostly the orbit itself: the
   orbit fit leaves χ² = 0.62 on 53 degrees of freedom. Without the excess noise, Δχ² would
   be 53,191.
   - With it, Δχ² is close to N_transits × (the fraction of the excess-noise variance that the
     DR3-period orbit explains). That makes the statistic insensitive to how large the noise
     is, which is what the test wants: a spurious DR3 orbit explains nothing, a real one
     explains most of the excess noise.
   - **It also sets a floor on power.** A source needs roughly N_transits ≳ 35 for a perfect
     orbit to pass Δχ² > 30, and a real orbit that explains less than ~30/N of the excess
     noise is missed.
   - The W0 control on the eclipsers measures this power directly. If W0 fails, nothing is
     interpreted, as pre-registered. We will also report the distribution of N_transits in
     both groups, which the release-day output already lists per target. **No rule changes.**
2. **The DataLink server answered HTTP 503 at 09:18 UTC** for both the DR3 epoch-photometry
   smoke request and the DR4 epoch-astrometry request ("temporarily unable to service your
   request due to maintenance downtime or capacity problems"). The rehearsal does not grade
   on these. On release day, a 503 means exit 3 (no data), and the job is re-filed unchanged.

## Next
On 2 December: `dr4_wobble.py release` on the 162 calib-window targets (W0–W4).
