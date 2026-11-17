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
*Prior art* below). Gaia DR4, due on 2 December 2026, will publish millions of
orbits over a 5.5-year baseline, plus Gaia's first exoplanet catalogue. The pipeline
is built to run on DR4 on release day (`--schema gaiadr4`).

**Why it matters if it works.** A companion that both transits and has an
astrometric orbit gives the companion's true mass (from astrometry) and its radius
(from the transit). For a long-period brown dwarf or giant planet that pairing is
very rare and valuable. A long-period eclipsing binary with a Gaia astrometric orbit
is also a strong mass and radius benchmark. Long-period transits are mostly single
events in TESS, so the usual TOI process, which looks for repeating transits, tends
to miss them. A Gaia orbit tells you when to look.

## Method

1. **Gaia query.** Download every orbit that has Thiele-Innes constants, G < 14.5 and
   |cos *i*| below a cut. The cut is applied by the archive itself, with cos *i*
   computed in ADQL by `gaia_orbits.cosi_adql()`. The download includes the
   correlation vector and the reference epoch.
2. **Orbit elements.** Convert the Thiele-Innes constants to *a0*, *i*, ω (modulo π)
   and Ω.
3. **Monte Carlo over the catalogue errors** (0.2.0):
   - Draw (A, B, F, G, e, P, Tp) jointly from the full Gaia correlation matrix
     (`corr_vec`, column-major upper triangle, in the solution type's parameter
     order).
   - For circular solutions, where Gaia did not fit G or e and fixed ω = 0, impose
     G = −A·F/B.
   - Align every draw's ω with the central ω (modulo π), so "t1" and "t2" always name
     the same conjunction.
   - From each draw compute:
     - both conjunction times (the transit and the occultation cannot be told apart
       from astrometry);
     - the probability that the geometry allows an eclipse, |cos *i*| < (R1 + R2)/r_conj,
       with R1 and M1 from a rough main-sequence relation in absolute G and M2 for a
       dark companion;
     - the expected duration;
     - the next conjunctions after 2026-12-01, with uncertainties.
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
7. **Outputs.** `gaia_edge_on_priors.csv` (with next-conjunction predictions),
   `substellar_edge_on_candidates.csv`, `tess_targets.csv` (coverage of the predicted
   conjunctions; a covered conjunction with no dip is a constraint too), `events.csv`,
   plots and `report.md`.

## Checks

- The conjunction times equal the minima of the projected separation, by brute force.
- Elements → Thiele-Innes → elements round-trips exactly.
- The ADQL cos *i* expression equals the Python formula, evaluated in Python on random
  orbits. Run live on DR3, both forms of the cut return 28,685 orbits with
  |cos *i*| < 0.2.
- For four real DR3 orbits, conjunction times computed independently in the Gaia
  archive (ADQL) match the Python code to better than 0.002 d.
- The correlated sampler reproduces the input correlations, and `corr_vec` is
  unpacked in the order the Gaia datamodel describes.
- An offline end-to-end run of the Gaia ranking stage, on a cached CSV.

## Limits (honest list)

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
python -m unittest -v test_gaia_orbits test_dipsearch test_run_search
python run_search.py --data-dir data --out-dir out                    # DR3
python run_search.py --data-dir data --out-dir out --no-tess          # watch list only
python run_search.py --schema gaiadr4 --data-dir data --out-dir out   # DR4, from 2026-12-02
python run_search.py --schema gaiadr4 --targets-table gaiadr4.gaia_exoplanet_candidates \
    --cosi-max 1.0 --data-dir data --out-dir out                     # Gaia exoplanet candidates
```

(The DR4 table and column names come from the pre-release documentation and will be
checked against the published datamodel on release day.)

## Findings

- `findings/2026-11-17-prereg.md`: pre-registered predictions for the first DR3 search.
- `findings/2026-11-17-v2-amendment.md`: the 0.2.0 fixes, made before any data was
  seen, and a TOI cross-check of the substellar watch list.
- `findings/2026-11-17-dr3-substellar-edge-on-watchlist.csv`: 26 near-edge-on DR3
  solutions (25 stars) with substellar companion masses, and their conjunction times.
  None is a TOI host.

## Prior art checked (2026-11-17)

- Holl et al. 2023, A&A 674, A10 (arXiv:2206.05439): Gaia DR3 orbits and a few TOI coincidences.
- arXiv:2310.12380: rejects K2/TESS candidates using Gaia DR3 *spectroscopic* (SB1) orbits.
- Gaia Collaboration, Arenou et al. 2023 (arXiv:2206.05595): DR3 multiplicity overview.
- Panahi et al. 2022 (arXiv:2205.10197): Gaia DR3 photometric transit candidates
  checked in TESS. That is a different input, Gaia photometry rather than astrometric
  orbits.
- github.com/coracle-us/gaia-dr4: searches DR4 epoch astrometry for outer companions of
  known transiting giant planets. That is the opposite direction to this project.

## Credits and licence

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name.
Code: Apache-2.0. Results and text: CC BY 4.0.
Data: ESA Gaia DR3 (Gaia Collaboration), NASA TESS via MAST (SPOC, TESS-SPOC and QLP
light curves), the TESS Input Catalog, and the NASA Exoplanet Archive TOI table. Uses
numpy, astropy, astroquery, lightkurve and matplotlib.
