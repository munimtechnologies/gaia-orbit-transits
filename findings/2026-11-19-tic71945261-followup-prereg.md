# Pre-registration: is TIC 71945261 young, and does an archival RV support Gaia's K?

Written 2026-11-19 (about 11:40 UTC), **before** job gaia-tic71945261-followup-v1 ran. By MV2
of Munim, Inc.; made with AI agents working in his name, not yet checked by a human expert.
Text CC BY 4.0, code Apache-2.0 (`youth_rv_check.py` 0.1.0, in this commit).

## Why
The pre-registered fit (`findings/2026-11-19-tic71945261-fit-results.md`) labelled the system
**B_OVERSIZED_COMPANION**. The companion's radius is 0.224 R☉ at a Gaia mass of 0.097 M☉, about
1.9 times the main-sequence value. `findings/2026-11-18-tic71945261-prereg.md` says nothing is
called "inflated" until a youth check and a test of Gaia's K have been made. This is that
check, as far as public data allow.

## What the job does
1. Reads the target's Gaia DR3 astrometry and SB1 orbit, and AU Mic's astrometry (a
   β Pictoris moving-group member, used as the positive control).
2. Runs BANYAN Σ (Gagné et al. 2018; current GitHub models) with the parallax, with and
   without the systemic velocity γ = −17.57 ± 0.39 km/s from the SB1 orbit.
3. Computes heliocentric UVW.
4. Cone-searches (10″) RAVE DR6, GALAH DR3, APOGEE DR17, ROSAT 2RXS, eROSITA eRASS1, GALEX
   GUVcat, VSX and the TIC through VizieR. Each search also counts rows within 0.3° as a
   control, so "no rows" means "not observed", not "service down".
5. Compares every archival RV that has an epoch with the Gaia orbit under two hypotheses:
   K = 16.16 km/s (Gaia), and K = 32.4 km/s (what a normal-size ~0.21 M☉ companion needs).
   It propagates Gaia's period error and adds 2 km/s of systematics.

## Readings, fixed now
**Youth** (`youth_reading`, using the run with RV):
| Reading | Rule |
|---|---|
| CONTROL_FAILED | AU Mic does not come out as β Pic MG with probability ≥ 0.8. Nothing is read. |
| YOUNG_KINEMATIC | total young-association probability ≥ 0.8 |
| FIELD_KINEMATIC | young-association probability < 0.2 |
| AMBIGUOUS | in between |

- **YOUNG_KINEMATIC** makes youth the leading explanation. A note would then say "a young
  eclipsing system with a pre-main-sequence companion near the hydrogen-burning limit",
  not "inflated". The best association's age would be compared with the age that
  pre-main-sequence models need for 0.22 R☉ at 0.1 M☉.
- **FIELD_KINEMATIC** does *not* prove the system is old: many young stars belong to no
  known group. It only removes the easiest explanation. Any public text must still say that
  youth is not excluded without lithium spectroscopy.

**Archival RV** (per RV with an epoch known to better than 0.05 d):
| Verdict | Rule (z = residual / combined error) |
|---|---|
| SUPPORTS_GAIA_K | abs(z) ≤ 3 with Gaia's K, and > 3 with K = 32.4 |
| SUPPORTS_HEAVY_K | the reverse |
| UNINFORMATIVE | both ≤ 3 |
| FITS_NEITHER | both > 3 (possibly a third body or a bad epoch) |

An RV whose epoch is known only to the night is reported, not graded.
If no archival RV exists, the K question stays open. The only evidence then is the two
ungraded facts already reported: Gaia's `rv_amplitude_robust` of 32.5 km/s matches
2K = 32.3 km/s, and the ellipsoidal amplitude is small.

## What would come next
- **"Inflated"** is used only if the youth reading is FIELD_KINEMATIC, no archival RV
  supports a heavy K, and a human-led spectrum shows no lithium. Before that, the strongest
  public statement is "a companion twice the expected size for its Gaia mass; young age or a
  wrong mass not yet excluded".
- **Exit codes:** 0 always, unless the script crashes. A Gaia TAP outage shows up as
  `gaia_target_error` and is re-filed unchanged. The Gaia archive is closed from 25 November
  12:00 CET to 2 December 2026.
