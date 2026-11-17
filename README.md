# gaia-orbit-transits

**Do Gaia's astrometric orbits predict eclipses and transits that TESS can see?**

Gaia DR3 published about 170,000 astrometric orbits of unresolved binaries. They are in
the `nss_two_body_orbit` table, as `Orbital`, `OrbitalTargetedSearch*`,
`OrbitalAlternative*` and `AstroSpectroSB1` solutions.

An orbit seen nearly edge-on should show an eclipse, at a time the Gaia orbit predicts:
the conjunction. For a dark brown-dwarf or giant-planet companion, that eclipse is a
transit. This project turns each near-edge-on Gaia orbit into predicted conjunction
windows and checks TESS light curves at those times.

Earlier work mostly went the other way:
- Holl et al. 2023 matched a few TESS Objects of Interest to Gaia orbits.
- arXiv:2310.12380 used Gaia spectroscopic orbits to reject transit candidates.

We have not found a systematic search that starts from the Gaia astrometric orbits and
predicts TESS eclipses for the whole catalogue (see *Prior art* below).

Gaia DR4 is due on 2 December 2026. It will publish millions of orbits over a 5.5-year
baseline, plus Gaia's first exoplanet catalogue. The pipeline is built to run on DR4 on
release day (`--schema gaiadr4`).

**Why it matters if it works.** A companion that both transits and has an astrometric
orbit has a measured true mass (from astrometry) and radius (from the transit). That
pairing is very rare and valuable for a long-period brown dwarf or giant planet. A
long-period eclipsing binary with a Gaia astrometric orbit is also a strong mass and
radius benchmark.

Long-period transits are mostly single events in TESS, so the usual TOI process, which
looks for repeating transits, tends to miss them. A Gaia orbit tells you when to look.

## Method

1. **Gaia query.** Download every orbit that has Thiele-Innes constants, G < 14.5 and
   |cos *i*| below a cut. The archive applies the cut itself, with cos *i* computed in
   ADQL by `gaia_orbits.cosi_adql()`. The download includes the correlation vector, the
   reference epoch and, from 0.3.0, the spectroscopic constants C and H.
2. **Orbit elements.** Convert the Thiele-Innes constants to *a0*, *i*, ω (modulo π)
   and Ω.
3. **Monte Carlo over the catalogue errors.**
   - Draw (A, B, F, G, e, P, Tp) jointly from Gaia's full correlation matrix.
   - For circular solutions, impose G = −A·F/B.
   - Align each draw's ω with the central ω, modulo π.
   - From each draw compute:
     - both conjunction times;
     - the eclipse probability, from a rough main-sequence mass and radius for the
       primary;
     - the expected duration;
     - the next conjunctions after 2026-12-01.
4. **Which conjunction is the transit (0.3.0).** For `AstroSpectroSB1` solutions,
   ω_RV = atan2(C, H) has no π ambiguity, and the companion passes in front of the star
   at f = π/2 − ω_RV. `transit_label()` names that conjunction (`transit_conj`).
   - A label is only given when σ(ω_RV) < 0.6 rad. For circular solutions it is given
     when H > 0 at 2σ or more.
   - The convention was checked against the eclipses of Gaia's own eclipsing
     spectroscopic binaries (see Findings).
5. **TESS light curves.** Look up the TIC ID (MAST) and download TESS light curves:
   SPOC 2-min first, then TESS-SPOC, then QLP, one per sector.
6. **Dip search.**
   - Bin the light curves to 30 min and split them at gaps.
   - Detrend each piece with a running median three times as wide as the trial
     duration.
   - Run box searches for durations of 2 to 24 h.
7. **Score each dip** with a window match: the probability under the Gaia orbit that a
   conjunction falls within one duration of the dip, divided by the same probability for
   a random time.
8. **Outputs.**
   - `gaia_edge_on_priors.csv` (next-conjunction and next-transit predictions);
   - `substellar_edge_on_candidates.csv`;
   - `tess_targets.csv`;
   - `covered_windows.csv` (0.3.0: every predicted window TESS covered; a covered
     window with no dip is a constraint);
   - `events.csv`, plots, `windows/*.png` (with `--window-plots`) and `report.md`.

## Checks (all run as unit tests)

- The conjunction times equal the minima of the projected separation (brute force).
- Elements → Thiele-Innes → elements round-trips exactly.
- The ADQL cos *i* expression equals the Python formula.
- For four real DR3 orbits, conjunction times computed independently in ADQL on the Gaia
  archive match to better than 0.002 d. RV transit times match ADQL to better than
  0.05 d.
- **Transit convention:** for 18 Gaia DR3 `EclipsingSpectro` systems, the deeper eclipse
  measured by Gaia's variability pipeline falls at f = π/2 − ω, within 0.02 in phase.
  The opposite sign is rejected in every eccentric system.
- The correlated sampler reproduces the input correlations.
- An offline end-to-end run of the Gaia ranking stage, on a cached CSV.

## Limits (honest list)

- The masses and radii are rough, for ranking only.
- A small photocentre orbit can also come from a *luminous* near-twin companion. Many
  "substellar" rankings will be such binaries, so the eclipse depth, the colour and
  SIMBAD/VSX must be checked before any claim.
- The transit label assumes that AstroSpectroSB1 C/H follow the same RV convention as
  the EclipsingSpectro solutions used to test it, as the Gaia DR3 documentation states.
- A dip that matches a predicted window is a **candidate**, not a discovery. It still
  needs vetting: pixel-level centroids, nearby stars, known variables in VSX, SIMBAD and
  the TOI/CTOI lists, and the shape of the event.

## Run

```
pip install -r requirements.txt
python -m unittest -v test_gaia_orbits test_dipsearch test_run_search
python run_search.py --data-dir data --out-dir out                    # DR3
python run_search.py --data-dir data --out-dir out --no-tess          # watch list only
python run_search.py --source-ids 393581461455623296,2960647744567925632 --gmax 17 \
    --cosi-max 0.3 --min-p-ecl 0 --window-plots --data-dir data --out-dir out
python run_search.py --schema gaiadr4 --data-dir data --out-dir out   # DR4, from 2026-12-02
python run_search.py --schema gaiadr4 --targets-table gaiadr4.gaia_exoplanet_candidates \
    --cosi-max 1.0 --data-dir data --out-dir out                     # Gaia exoplanet candidates
```

(The DR4 table and column names come from the pre-release documentation. They will be
checked against the published datamodel on release day.)

## Findings

- `findings/2026-11-17-prereg.md`: pre-registered predictions for the first DR3 search.
- `findings/2026-11-17-v2-amendment.md`: the 0.2.0 fixes, made before any data was seen,
  and a TOI cross-check of the substellar watch list.
- `findings/2026-11-17-dr3-substellar-edge-on-watchlist.csv`: 26 near-edge-on DR3
  solutions (25 stars) with substellar companion masses, and their conjunction times.
  None is a TOI host.
- `findings/2026-11-17-sb1-transit-convention.md` (0.3.0):
  - The transit-time convention is verified on Gaia's eclipsing spectroscopic binaries.
  - The transit window is identified for 16 of the 18 AstroSpectroSB1 watch-list stars.
  - None of the 478 DR3 sources that have both an astrometric orbit and a Gaia eclipse
    period has matching periods, so Gaia DR3 holds no astrometric companion seen to
    eclipse.
  - For the best target (Gaia DR3 393581461455623296, P = 73.3 d), every predicted
    transit fell 1.8 to 3.2σ after a TESS sector ended, so TESS has not yet tested it.
    The next windows are 2026-11-16, 2027-01-28 and 2027-04-12 (±6.5 d).
- `findings/2026-11-17-watchlist-prereg.md`: predictions for the TESS check of the
  25-star watch list.

## Prior art checked (2026-11-17)

- Holl et al. 2023, A&A 674, A10 (arXiv:2206.05439): Gaia DR3 orbits and a few TOI
  coincidences.
- arXiv:2310.12380: rejects K2/TESS candidates using Gaia DR3 *spectroscopic* (SB1)
  orbits.
- Gaia Collaboration, Arenou et al. 2023 (arXiv:2206.05595): DR3 multiplicity overview.
- Halbwachs et al. 2023, A&A 674, A9: the DR3 astrometric binary solutions, including the
  C/H constants.
- Czavalinga et al. 2023, A&A 670, A75: close binaries with tertiary companions found in
  Gaia DR3 orbits (eclipsing pairs with outer orbits).
- Panahi et al. 2022 (arXiv:2205.10197): Gaia DR3 photometric transit candidates checked
  in TESS. That starts from Gaia photometry, not from astrometric orbits.
- github.com/coracle-us/gaia-dr4: searches DR4 epoch astrometry for outer companions of
  known transiting giant planets. That is the opposite direction to this project.

## Credits and licence

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name.
Code: Apache-2.0. Results and text: CC BY 4.0.
Data: ESA Gaia DR3 (Gaia Collaboration), NASA TESS via MAST (SPOC, TESS-SPOC and QLP
light curves), the TESS Input Catalog, and the NASA Exoplanet Archive TOI table. Uses
numpy, astropy, astroquery, lightkurve and matplotlib.
