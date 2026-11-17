# gaia-orbit-transits

**Do Gaia's astrometric orbits predict eclipses and transits that TESS can see?**
**And can Gaia alone weigh the things it sees transiting?**

Gaia DR3 published about 170,000 astrometric orbits of unresolved binaries. They are in
the `nss_two_body_orbit` table, as `Orbital`, `OrbitalTargetedSearch*`,
`OrbitalAlternative*` and `AstroSpectroSB1` solutions.

An orbit seen nearly edge-on should show an eclipse, at a time the Gaia orbit predicts:
the conjunction. For a dark brown-dwarf or giant-planet companion, that eclipse is a
transit. This project turns each near-edge-on Gaia orbit into predicted conjunction
windows and checks TESS light curves at those times. From 0.4.0 it also checks archival
ground-based and Gaia photometry (ZTF, ASAS-SN, Gaia DR3 epoch photometry), and it
publishes forecasts of future transit windows, both those TESS will observe and those
only the ground can see, before the data exist.

From 0.5.0 it also works in the other direction. It starts from Gaia's own photometric
transit candidates (`vari_planetary_transit`: 214 in DR3, 1,007 in DR4) and asks what
Gaia's own radial velocities and orbits say about them (`transit_rv_screen.py`).

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
radius benchmark. A Gaia transit with a Gaia orbit at the same period gives a mass, a
radius and a period from one mission.

Long-period transits are mostly single events in TESS, so the usual TOI process, which
looks for repeating transits, tends to miss them. A Gaia orbit tells you when to look.

## Method

1. **Gaia query.** Download every orbit that has Thiele-Innes constants, G < 14.5 and
   |cos *i*| below a cut. The archive applies the cut itself, with cos *i* computed in
   ADQL by `gaia_orbits.cosi_adql()`. The download includes the correlation vector, the
   reference epoch and, from 0.3.0, the spectroscopic constants C and H.
   - From 0.4.0 a dropped connection while downloading the result is retried. The
     astroquery fallback also writes array columns (`corr_vec`) correctly; before, it
     crashed on them, and that is what stopped the first full DR3 run.
   - **0.4.1:** since October 2026 the Gaia ESA Archive gives anonymous users 60 s and
     at most 50,000 rows per query, and that limit stopped the second full DR3 run. Large
     queries are now split into source_id ranges (`--tap-chunks`, default 16). A range
     that times out or hits the row cap is split four ways again. Each range goes to the
     ESA archive, then to the ARI Heidelberg Gaia mirror (DR3), then to astroquery.
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
   - **0.4.2:** first drop cadences below half the median flux. In the watch-list run,
     QLP light curves of Sector 104 fall to about 10% at the start and end of each orbit,
     and those cadences are not quality-flagged.
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

### Archival test (`archival.py`)

This stage searches all public photometry that needs no login: Gaia DR3 epoch photometry,
ZTF (IRSA), ASAS-SN Sky Patrol v2 and TESS. It looks for a transit **inside the joint
(period, transit time) posterior of the Gaia orbit**, and measures how much of that
posterior the data already exclude.

1. **Posterior.** The Monte Carlo draws are carried to a reference epoch in the middle of
   the data, which gives the means, widths and P–T correlation.
2. **Detrending.** A running median that skips ±D around each point, so a transit is not
   removed along with the trend. Each light curve is weighted by its robust scatter.
3. **Box search.** Over ±3.5σ in P and ±3.5 conditional σ in T, for durations D0 (the
   predicted central duration) and 0.6 D0. SNR = Σ w·d / √Σ w.
4. **Threshold.** The larger of 6 and the maximum over 30 null runs. In each null run the
   residuals are cyclically shifted within each light curve. FAP = (1 + #null ≥ obs) / 31.
5. **Injection–recovery.** Transits are injected at (P, T) draws from the Gaia posterior,
   with impact parameter uniform in 0–0.9, at several depths. The recovery fraction R
   updates the transit probability: p (1 − R) / (1 − p R).
6. **Outputs.** `archival_results.csv`, `archival_report.md`, and
   `archival/<id>_<conj>.json` / `.png` (the SNR against period, and the folded data at
   the best cell).

0.4.1 makes two fixes here. Boxes at the edge of the transit-time grid now see all their
points (before, the fast scan could overstate their SNR; its brute-force test caught
this). The Gaia DataLink request uses the archive's new structure name,
`DATAMODEL_STANDARD` (formerly `INDIVIDUAL`).

### Forecast (`forecast.py`)

This stage publishes falsifiable predictions before the observations exist.

- **TESS sectors 108-134 (September 2026 to late 2028).**
  - It lists every sector in which the star lands on a CCD (tess-point 0.9.5 pointing
    table).
  - For each one it gives the Monte Carlo probability that the transit conjunction
    falls inside the sector, and the expected number of transits TESS will record.
  - Year 9 dates are the TESS Science Center's provisional dates. Year 10 boundaries
    are midpoints between the sector mid-times and are flagged as approximate.
- **Ground windows.** Every transit window from 2026-12-01 to 2027-12-01, with its
  centre, robust 1σ and 95% range.
- **Outputs.** `<prefix>_stars.csv`, `<prefix>_tess_sectors.csv`,
  `<prefix>_windows.csv`, `<prefix>_summary.json` and `<prefix>_report.md`.

### Vetting one event (`vet_event.py`, 0.4.2)

This stage vets a single dip with decision rules fixed in advance (`verdict()`):
- **Products.** For every light-curve product of the star that covers the event, it
  measures PDC, SAP, the background, both centroids and the quality flags in the same
  box, against a straight-line local baseline.
- **Systematics.** It measures the same box on the 15 nearest other SPOC / TESS-SPOC
  stars in that sector.
- **Pixels.** From a TESScut stamp it builds a background-subtracted 3×3 aperture light
  curve and a difference image, and compares the difference-image centroid with the
  star's position.
- **Positive control.** The expected transit is injected at the event time and away
  from it.
- **Repeat epochs.** It checks t0 + kP for P within ±3σ of the Gaia period, records the
  covered period range, and runs an injection check at each epoch.
- **Catalogues.** A Gaia DR3 cone, SIMBAD and VSX (through VizieR).

### Gaia transit candidates and Gaia radial velocities (`transit_rv_screen.py`, 0.5.0)

This stage joins `vari_planetary_transit` to `gaia_source`, `astrophysical_parameters`,
`nss_two_body_orbit` and `nss_acceleration_astro` in one archive query, then applies
fixed rules:
- **Same-period orbit.** An SB1 orbit at the transit period (n:m ≤ 3, within 0.2%) gives
  m2 sin i from K and the FLAME mass. It is classed as planet, brown dwarf, star or
  boundary from K ± 2σ.
- **RV scatter.** For bright stars (`rv_method_used` = 1), the DR3 error model
  ε = √(π/2N)·σ + 0.11 km/s gives the epoch scatter σ, and K ≥ √(2(σ² − σn²)).
  - The noise ceiling σn defaults to 7 km/s.
  - If K exceeds what 13 M_Jup can produce at P = 0.25 d, a planet-only system is
    excluded at any period.
- **Other orbits.** SB2 orbits and orbits at other periods are reported, and
  accelerations mark outer companions.
- **Catalogues.** SIMBAD (TAP) and VSX (VizieR TAP) lookups for every flagged star.
- **Release day.** `--schema gaiadr4` runs the same rules on DR4.

### Vetting a short-period SB1 / transit candidate (`vet_short_period.py`, 0.5.0)

This stage vets one candidate with pre-registered rules (`verdict()`):
1. **TESS light curves.** All sectors are used (SPOC > TESS-SPOC > QLP), detrended with a
   2-d running median and binned to 10 min.
2. **Period search.** Lomb–Scargle, then BLS. BLS refinement is run at the BLS best, 2×
   the BLS best, the SB1 period, 2× the SB1 period and Gaia's photometric period.
3. **Measurements.**
   - A harmonic out-of-eclipse model (ellipsoidal, reflection, beaming).
   - Primary, secondary, odd and even depths against that model. Their errors include the
     error of the model extrapolated into the eclipse.
4. **Physics checks.**
   - R2 from the depth;
   - m2 from K ± 2σ;
   - the predicted ellipsoidal amplitude (Morris 1985);
   - the central duration.
5. **Verdict:** one of NO_ECLIPSE, PERIOD_CONFLICT, STELLAR_EB, MASS_TENSION or
   TRANSITING_{BROWN_DWARF_CANDIDATE, BD_OR_VLM_BOUNDARY, VLM_STAR}.

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
- `table_to_csv` round-trips masked values and array columns such as `corr_vec` through
  `read_csv_text`.
- Chunked queries (0.4.1), against a fake archive that truncates at a row cap and aborts
  large ranges:
  - the ranges cover every source_id exactly once;
  - results merge under one header;
  - capped or aborted ranges are split and the answer is complete;
  - plain network errors are not split.
- `dipsearch.py` (0.4.2): broken cadences at 10% flux are dropped and counted. Without
  the floor they dominate the search.
- `vet_event.py`:
  - box depth with a sloped baseline;
  - repeat-epoch windows and covered period ranges, worked by hand;
  - the difference-image centroid;
  - neighbour statistics;
  - every verdict rule.
- `transit_rv_screen.py` (0.5.0):
  - the RV constant (212.908 km/s) from GM☉;
  - Earth's (0.0895 m/s) and Jupiter's (12.46 m/s) reflex velocities;
  - the mass function, and round trips between mass and K;
  - the DR3 error model;
  - period ratios;
  - WASP-18 b classed as a planet from Gaia's own SB1 (m2 sin i = 0.0100 M☉);
  - the real hot Jupiter WASP-163 b not flagged;
  - every class, and an offline end-to-end run.
- `vet_short_period.py` (0.5.0):
  - Kepler's law;
  - the ellipsoidal amplitude, duration and mass range, worked by hand;
  - the detrending and binning;
  - a synthetic brown-dwarf eclipse with ellipsoidal and reflection terms, recovered
    within its errors;
  - every verdict rule.
- `archival.py`:
  - parsers for the ZTF, Gaia epoch-photometry (raw or zipped DataLink answers) and
    ASAS-SN formats, including the time conversions and the rejection of flagged and
    saturated points;
  - the fast grid scan equals a brute-force evaluation of the same cells, for both the
    narrow-window and the full-phase branches, including a box at the grid edge;
  - an injected 3% transit in irregular ground-like data is found at the right period and
    phase, and pure noise gives no detection;
  - a 1% dip survives the detrending of a spotted-star light curve.
- `forecast.py`:
  - the sector table is contiguous and agrees with tess-point's mid-times;
  - the probability that a conjunction falls in a sector is exact on test cases;
  - forecast windows bracket the central predictions;
  - an offline end-to-end run with a stubbed pointing table.

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
- Dips at the start or end of a TESS orbit are where scattered light is strongest. The
  search flags them (`near_edge`), but it does not remove them.
- The archival injections are added after detrending, so they slightly overstate the
  sensitivity. The trend skips ±D around each point, which keeps this effect small.
  Ground photometry of bright stars (G ≲ 12.5 in ZTF) can be affected by saturation.
- The forecast ignores TESS's data gaps at perigee (about 7% of each sector). TESS
  pointings are provisional and can change.
- Anonymous Gaia archive access is limited to 60 s and 50,000 rows per query, 5 jobs at
  a time and 50 DataLink sources per request. Very large DR4 queries need many ranges and
  can be slow on release day.
- The RV-scatter bound assumes a single sinusoid and the DR3 bright-star error model. RV
  variability can come at any period, so it excludes a planet-only system; it does not
  prove that the transit signal itself is an eclipsing binary. Gaia's transit periods
  are often aliases.

## Run

```
pip install -r requirements.txt
pip install "tess-point>=0.9.5"                                      # forecast only
python -m unittest -v test_gaia_orbits test_dipsearch test_run_search test_archival test_forecast test_vet_event test_transit_rv_screen test_vet_short_period
python run_search.py --data-dir data --out-dir out                    # DR3
python run_search.py --data-dir data --out-dir out --no-tess          # watch list only
python run_search.py --source-ids 393581461455623296,2960647744567925632 --gmax 17 \
    --cosi-max 0.3 --min-p-ecl 0 --window-plots --data-dir data --out-dir out
python archival.py --source-ids 393581461455623296 --gmax 17 --cosi-max 0.3 \
    --data-dir data --out-dir out                                    # archival test
python forecast.py --source-ids 393581461455623296 --gmax 17 --cosi-max 0.3 --m2-max 1 \
    --data-dir data --out-dir out                                    # forecast
python vet_event.py --tic 41898425 --ra 21.734801 --dec -41.059717 --t0 3192.263 \
    --dur-h 8 --pred-dur-h 11.68 --sector 69 --period 196.6738 --period-sd 0.8175 \
    --exp-depth 0.0105 --data-dir data --out-dir out                 # vet one event
python transit_rv_screen.py --schema gaiadr3 --out-dir out            # Gaia transits x Gaia RVs
python vet_short_period.py --tic 207399049 --gaia 1622997463177004928 --p-rv 0.46023065 \
    --k-rv 19.695569 --k-rv-err 1.3143485 --e-rv 0.2008897 --p-phot 0.8513754 \
    --m1 0.9556862 --r1 1.1634727 --data-dir data --out-dir out      # vet a short-period SB1
python run_search.py --schema gaiadr4 --tap-chunks 64 --data-dir data --out-dir out   # DR4
python run_search.py --schema gaiadr4 --targets-table gaiadr4.gaia_exoplanet_candidates \
    --cosi-max 1.0 --data-dir data --out-dir out                     # Gaia exoplanet candidates
python transit_rv_screen.py --schema gaiadr4 --out-dir out            # DR4's 1,007 candidates
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
- `findings/2026-11-17-watchlist-results.md` (0.4.2): the graded watch-list check.
  - 24 of 25 stars have TESS data. Predictions 1 and 2b pass; 2a and 3 fail as written.
  - Six of the seven dips with Bayes factor > 3 are broken QLP cadences in Sector 104.
  - One edge-of-orbit dip on TIC 41898425 (Sector 69) is being vetted. It is not a
    candidate yet.
- `findings/2026-11-17-vet-41898425-prereg.md`: the fixed rules and predictions for
  vetting that event.
- `findings/2026-11-17-archival-prereg.md`: predictions for the archival test.
  - TESS's Year 9 pointings (to September 2027) do not cover the best target, so only
    the ground can test its 2027 windows.
  - Gaia flags the star as VARIABLE (SOLAR_LIKE, 8.7 mmag scatter in 57 G epochs).
- `findings/2026-11-17-forecast-prereg.md`: what the forecast publishes and five
  predictions about it, written before it ran.
- `findings/2026-11-17-v4-amendment.md` (0.4.1): the Gaia archive's new anonymous limits,
  the archival scan fix and the forecast test fix. No prediction changed.
- `findings/2026-11-17-dr3-transit-rv-screen.md` (0.5.0, preliminary):
  - Gaia's own RVS data show that 9 of the 41 new Gaia DR3 transit candidates carry a
    companion heavier than any planet (8 firm, 1 marginal). One is a double-lined
    binary of two near-equal ~1 M☉ stars.
  - Gaia alone recovers the mass of the transiting WASP-18 b: 10.5 ± 0.8 M_Jup.
  - One new candidate, Gaia DR3 1622997463177004928, has an SB1 orbit with P = 0.460 d
    and m2 sin i = 0.071 M☉, at the brown-dwarf / star boundary.
- `findings/2026-11-17-tic207399049-prereg.md`: fixed rules and predictions for the TESS
  vetting of that star, written before its light curves were read.

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
  in TESS. That starts from Gaia photometry, not from astrometric orbits, and the
  candidates were not vetted with Gaia's RVS data.
- arXiv:2608.06453 (2026): spectroscopic follow-up of 227 Gaia DR3 binaries with high
  inferred companion masses. TESS light curves show some of them to be hierarchical
  triples (an inner eclipsing pair inside the astrometric orbit). That agrees with our
  finding that DR3 astrometric orbits with Gaia eclipses are triples. It does not
  predict eclipses from the astrometric orbits.
- arXiv:2512.04606 (A&A 2026): HD 128717 B / Gaia-6 B, a long-period brown dwarf found by
  Gaia astrometry and confirmed with radial velocities; no transit search.
- github.com/coracle-us/gaia-dr4: searches DR4 epoch astrometry for outer companions of
  known transiting giant planets. That is the opposite direction to this project.
- Long-period transiting brown dwarfs found by TESS and radial velocities (for example
  TOI-5575b, arXiv:2507.09461; the four new long-period ones in A&A 2026, aa58244-25)
  were not found from Gaia astrometric orbits.
- Transiting brown dwarfs with P < 1 d that we found all orbit M dwarfs: NGTS-7Ab
  (arXiv:1906.08219), TOI-263b (arXiv:2103.11150) and ZTF J2020+5033 (arXiv:2307.15729).

## Credits and licence

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name.
Code: Apache-2.0. Results and text: CC BY 4.0.
Data: ESA Gaia DR3 (Gaia Collaboration), including epoch photometry, served by the ESA
Gaia Archive and the ARI Heidelberg Gaia mirror; NASA TESS via MAST (SPOC, TESS-SPOC and
QLP light curves, TESScut); the TESS Input Catalog; ExoFOP-TESS and the NASA Exoplanet
Archive TOI table; the Zwicky Transient Facility (IRSA); ASAS-SN Sky Patrol; SIMBAD and
VizieR (CDS) with the AAVSO VSX catalogue; TESS pointings from the TESS Science Center and
tess-point (tessgi). Uses numpy, astropy, astroquery, lightkurve, matplotlib, skypatrol
(pyasassn) and tess-point.
