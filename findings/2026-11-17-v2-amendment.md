# Amendment: version 0.2.0 replaces the first search job before it ran

Written 2026-11-17, before any TESS light curve was downloaded for this project.
By MV2 of Munim, Inc.; made with AI agents. CC BY 4.0.

The first search job (`gaia-orbit-tess-v1`, see `2026-11-17-prereg.md`) was still
waiting in the compute queue when a code review against the live Gaia archive found
three problems in the Monte Carlo. Version 0.2.0 fixes them, and job
`gaia-orbit-tess-v2` replaces v1. **The four predictions and every setting stay the
same** (G < 14.5, |cos i| < 0.2, 600 draws, 400 targets, BF > 10 match, SNR > 10 for a
strong match). `expected_eclipses_covered` keeps its pre-registered definition (p_ecl x
the better of the two coverages). The run also reports a second version that counts
both conjunctions, under a new name.

## What was wrong and what changed

1. **Circular orbits.** For circular solutions Gaia DR3 does not fit G or the
   eccentricity (bit_index 8179 for `Orbital`, 65435 for `AstroSpectroSB1`). It sets
   ω = 0, so the served G equals −A·F/B. We checked this on Gaia DR3
   393581461455623296: G = −0.00649125533317565, and −A·F/B = −0.006491255333175651.
   v1 held G fixed while it varied A, B and F, which spread ω, and with it the
   predicted conjunction times, for no physical reason. v2 imposes G = −A·F/B in every
   draw. Conjunctions then fall exactly at Tp + P/4 and Tp + 3P/4, with the timing
   error coming only from Tp and P, as it should.
2. **Labels of the two conjunctions.** Astrometry fixes ω only modulo π. Draws that
   cross the Ω = 0/π boundary had ω shifted by π, so "t1" in some draws was "t2" in
   others. That blurred both timing windows. v2 aligns every draw's ω with the central
   ω (modulo π).
3. **Correlations.** v1 drew independent errors. v2 builds the full correlation matrix
   from `corr_vec`: the column-major upper triangle in the solution type's parameter
   order, with NaN for parameters that were not fitted, exactly as the DR3 datamodel
   describes. It samples (A, B, F, G, e, P, Tp) jointly. We checked the format live:
   for 393581461455623296, `corr_vec` has 105 = 15·14/2 entries, 66 finite
   (12 fitted parameters).

New in 0.2.0 for Gaia DR4 (2 December 2026):
- The archive applies the near-edge-on cut itself (`ABS(cos i) < x`, with cos i
  computed from A, B, F and G in ADQL). The square root is written in a form that
  cannot go negative through rounding. Run live on DR3 on 2026-11-17, both forms of
  the cut return **28,685** orbits with |cos i| < 0.2. DR4 has about 5.9 million
  two-body solutions, so this keeps the download small.
- The reference epoch is read from `gaia_source.ref_epoch` for every row (J2016.0 →
  BTJD 389.0; J2017.5 → BTJD 936.875).
- `--targets-table gaiadr4.gaia_exoplanet_candidates` restricts the search to Gaia's
  first exoplanet catalogue.
- For every orbit, the next conjunctions after 2026-12-01, with Monte Carlo
  uncertainties (`next1_btjd`, `next1_sd_d`, ...).
- `--no-tess` stops after the Gaia ranking and writes only the watch list.

## Independent check of the conjunction maths

For four real DR3 orbits we computed the conjunction times in the Gaia archive
itself, with a separate ADQL implementation (ω from the two `ATAN2` terms and
Kepler's equation in closed form). The Python code reproduces them to better than
0.002 d modulo P (`test_gaia_orbits.TestAgainstGaiaArchive`). For one of them we
also redid the calculation by hand, and it agrees to 2e-4 d.

## Substellar near-edge-on watch list (DR3), and a TOI cross-check

`2026-11-17-dr3-substellar-edge-on-watchlist.csv` lists the **26 DR3 solutions (25
stars)** with Thiele-Innes constants, |cos i| < 0.3, and a Gaia `binary_masses`
upper companion mass below 0.1 M☉ (19 AstroSpectroSB1+M1, 4 Orbital+SB1+M1, 3
Orbital+M1). The conjunction times are central values only (BTJD; the uncertainties
come with the v2 Monte Carlo). Periods run from 73 to 2,400 d.

**None of the 25 is a TESS Object of Interest host.** We searched the NASA Exoplanet
Archive `toi` table around each position (±0.006° in Dec) on 2026-11-17. A positive
control, TOI-700, was found in the same query. The TOI process mostly finds repeating
transits, while companions on 73 to 2,400-day orbits transit at most once or twice in
TESS data. That gap is the one this project aims at. If |cos i| is uniform below 0.3,
the chance that a given companion of this kind transits is about (R★/a)/0.3, roughly
1 to 5%, so we expect about 0.3 to 1 transiting system among the 25, and only if TESS
happened to observe the conjunction. Gaia DR4 should add many more of these companions.

## Limits

- The binary_masses companion masses assume the photocentre traces the primary. A
  luminous companion would make the true mass larger.
- Only one of the two conjunctions is a transit. For AstroSpectroSB1 solutions the
  radial velocities break the ω ambiguity, but we have not yet checked Gaia's sign
  convention, so both conjunctions are still kept.
