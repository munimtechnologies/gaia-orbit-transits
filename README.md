# gaia-orbit-transits

**Do Gaia's astrometric orbits predict eclipses and transits that TESS can see?**

Gaia DR3 published about 170,000 astrometric orbits of unresolved binaries (the
`nss_two_body_orbit` table: `Orbital`, `OrbitalTargetedSearch*`, `OrbitalAlternative*`
and `AstroSpectroSB1` solutions). An orbit seen nearly edge-on should show eclipses,
or for a dark brown-dwarf or giant-planet companion a transit, at a time the Gaia
orbit predicts: the conjunction. This project turns each near-edge-on Gaia orbit
into predicted conjunction windows and checks TESS light curves at those times.

Earlier work mostly went the other way. Holl et al. 2023 matched a few TESS Objects
of Interest to Gaia orbits, and arXiv:2310.12380 used Gaia spectroscopic orbits to
reject transit candidates. We have not found a systematic search that starts from
the Gaia astrometric orbits and predicts TESS eclipses for the whole catalogue (see
*Prior art* below). Gaia DR4, due on 2 December 2026, will publish many more orbits
over a 5.5-year baseline, plus Gaia's first exoplanet catalogue. The pipeline is
built so it can be re-run on DR4 on release day.

**Why it matters if it works.** A companion that both transits and has an
astrometric orbit gives the companion's true mass (from astrometry) and its radius
(from the transit). For a long-period brown dwarf or giant planet that pairing is
very rare and valuable. A long-period eclipsing binary with a Gaia astrometric orbit
is also a strong mass and radius benchmark.

## Method

1. **Gaia query.** Download every DR3 orbit that has Thiele-Innes constants (G < 14.5).
2. **Orbit elements.** Convert the Thiele-Innes constants to *a0*, *i*, ω (mod π) and Ω,
   keeping only orbits with |cos *i*| < 0.2.
3. **Monte Carlo over the catalogue errors.** For each orbit, sample the errors as
   independent Gaussians (the correlations are not used yet) and compute:
   - both conjunction times. Astrometry fixes ω only modulo π, so the transit and the
     occultation cannot be told apart, and both times are kept.
   - the probability that the geometry allows an eclipse, |cos *i*| < (R1 + R2)/r_conj.
     R1 and M1 come from a rough main-sequence relation in absolute G, and M2 assumes a
     dark companion.
   - the expected eclipse duration.
4. **TESS light curves.** Look up the TIC ID (MAST) and download TESS light curves
   (SPOC 2-min, then TESS-SPOC, then QLP; one per sector).
5. **Dip search.** Bin the light curves to 30 min, split them at gaps, and detrend
   each piece with a running median three times as wide as the trial duration. Then
   run box searches for durations of 2 to 24 h. Box noise is measured empirically,
   which makes the search robust to red noise.
6. **Score each dip** with a window match: the probability, under the Gaia orbit, that
   a conjunction falls within one duration of the dip, divided by the same probability
   for a random time (2D/P). Dips at the same time in several targets (spacecraft
   systematics) and dips at segment edges are down-weighted.
7. **Outputs.** `gaia_edge_on_priors.csv`, `substellar_edge_on_candidates.csv`,
   `tess_targets.csv` (coverage of the predicted conjunctions; a covered conjunction
   with no dip is a constraint too), `events.csv`, plots and `report.md`.

## Limits (honest list)

- Catalogue correlations are ignored in the Monte Carlo, so the timing windows and
  eclipse probabilities are approximate.
- The masses and radii are rough, for ranking only.
- A small photocentre orbit can also come from a *luminous* near-twin companion. Many
  "substellar" rankings will be such binaries, so the eclipse depth, the colour and
  SIMBAD/VSX must be checked before any claim.
- A dip that matches a predicted window is a **candidate**, not a discovery. It still
  needs vetting: pixel-level centroids, nearby stars, known variables in VSX, SIMBAD
  and TOI/CTOI lists, and the shape of the event.

## Run

```
pip install -r requirements.txt
python -m unittest -v test_gaia_orbits test_dipsearch
python run_search.py --data-dir data --out-dir out
```

## Prior art checked (2026-11-17)

- Holl et al. 2023, A&A 674, A10 (arXiv:2206.05439): Gaia DR3 orbits and a few TOI coincidences.
- arXiv:2310.12380: rejects K2/TESS candidates using Gaia DR3 *spectroscopic* (SB1) orbits.
- Gaia Collaboration, Arenou et al. 2023 (arXiv:2206.05595): DR3 multiplicity overview.
- github.com/coracle-us/gaia-dr4: searches DR4 epoch astrometry for outer companions of
  known transiting giant planets. That is the opposite direction to this project.

## Credits and licence

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name.
Code: Apache-2.0. Results and text: CC BY 4.0.
Data: ESA Gaia DR3 (Gaia Collaboration), NASA TESS via MAST (SPOC, TESS-SPOC and QLP
light curves), and the TESS Input Catalog. Uses numpy, astropy, astroquery, lightkurve
and matplotlib.
