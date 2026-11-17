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
only the ground can see, before the data exist. From 0.9.0 it also uses Kepler's four
years of photometry for stars in the Kepler field.

From 0.5.0 it also works in the other direction. It starts from Gaia's own photometric
transit candidates (`vari_planetary_transit`: 214 in DR3, 1,007 in DR4) and asks what
Gaia's own radial velocities and orbits say about them (`transit_rv_screen.py`).

From 0.6.0 it joins Gaia's single-lined spectroscopic orbits to Gaia's own eclipsing
binaries at the same period (`eblm_screen.py`). The result is a Gaia-only mass, radius,
conjunction and ellipsoidal check for every low-mass companion seen to eclipse. It also
flags the commonest trap: near-equal eclipses with a tiny mass function, which signal a
diluted SB1 amplitude.

From 0.7.0 it uses the eclipses to test Gaia itself (`calib_eclipse_rate.py`): an orbit
within (R1 + R2)/a of edge-on must eclipse, so the eclipses TESS does and does not see
measure how good Gaia DR3's inclinations and their errors really are.

From 0.10.0 it asks a stellar-physics question with those systems: **are M dwarfs in
0.5-5-day orbits larger than stellar models predict?** `eblm_fit.py` fits a physical
eclipse model to the TESS light curve of every Gaia-weighed eclipsing low-mass companion.
`eblm_infl.py` (0.11.0) compares the radii with the Baraffe et al. (2015) models. It tests
the claim of Swayne et al. (2024) that M dwarfs in binaries with P < 5 d are inflated by
about 6%, a claim that rests on five systems. EBLM XIX (2026) left that period range out.

**Prior work (corrected 2026-11-17).** Earlier versions of this README said we had found
no systematic search that starts from Gaia astrometric orbits and predicts TESS eclipses.
That was wrong. **Théo Chopard-Vilhem published one on 2026-10-13**: *"Eclipsing binaries
at the conjunctions predicted by near-edge-on Gaia DR3 astrometric orbits"* (Zenodo,
doi:10.5281/zenodo.23342416, the data and code of an AAS Research Note). It covers 1,726
DR3 orbits with G < 14 and inclination within 1° of 90°, and reports seven new eclipsing
binaries with periods of 26 to 242 days, plus forecasts. The idea and its first results
are his. This project differs in sample size (24,157 orbits out to |cos i| < 0.2, about
11.5° from edge-on), in pre-registering its predictions, in using Gaia RVs to say which
conjunction is the transit, in its brown-dwarf focus and, from 0.7.0, in using the
eclipses to calibrate Gaia's inclination errors. Other earlier work went the other way:
Holl et al. 2023 matched a few TESS Objects of Interest to Gaia orbits, and
arXiv:2310.12380 used Gaia spectroscopic orbits to reject transit candidates.

Gaia DR4 is due on 2 December 2026. It will publish millions of orbits over a 5.5-year
baseline, including 638,966 RVS SB1 orbits (`rvs_two_body_orbit`), plus Gaia's first
exoplanet catalogue. The pipeline is built to run on DR4 on release day
(`--schema gaiadr4`).

**Why it matters if it works.**
- A companion that both transits and has an astrometric orbit has a measured true mass
  (from astrometry) and radius (from the transit). That pairing is very rare and
  valuable for a long-period brown dwarf or giant planet.
- A long-period eclipsing binary with a Gaia astrometric orbit is also a strong mass and
  radius benchmark.
- A Gaia transit or eclipse with a Gaia orbit at the same period gives a mass, a radius
  and a period from one mission.
- Eclipses are ground truth for Gaia's inclinations. If DR3's errors near 90° are too
  small, every eclipse or transit forecast made from them (DR4 included) needs the
  correction.
- Gaia SB1 orbits plus TESS eclipses weigh and size M dwarfs without new spectroscopy.
  DR4 can turn the few dozen short-period systems known today into hundreds, enough to
  settle whether close orbits inflate M dwarfs.

Long-period transits are mostly single events in TESS, so the usual TOI process, which
looks for repeating transits, tends to miss them. A Gaia orbit tells you when to look.

## Status (2026-11-17, 0.11.0)

- **0.11.0: the short-period inflation test, against real models, pre-registered.**
  - **Prior-art correction.** The 0.10.0 pre-registration said the short-period regime
    was untested. EBLM XIX (Davis et al. 2026) did leave out every P < 5 d binary, but
    **Swayne et al. 2024 (EBLM XI)** had already reported about 6% inflation for P < 5 d,
    from 5 systems with P = 2.8-4.3 d. Our sample is mostly 0.5-3 d, so it is a larger,
    shorter-period test of their claim, not a first look.
  - **Reference model.** The rough main-sequence table used by eblm_screen and eblm_fit
    is 3.2-3.7% larger than the BHAC15 5-Gyr isochrone at 0.2-0.4 M☉, as large as the
    effect being tested. `eblm_infl.py` re-scores every radius against BHAC15 (1, 5 and
    10 Gyr).
  - Tests H1 (median inflation; INFLATED if the 95% lower bound > +3%) and H2 (Spearman
    trend with period) are fixed in
    `findings/2026-11-17-short-period-inflation-prereg.md`, before any eblm_fit result
    exists.
- **0.10.0: EBLM v1 graded; eblm_fit.**
  - The TESS stage of the Gaia-only EBLM screen is graded
    (`findings/2026-11-17-eblm-v1-results.md`). **E2 fails as run:** eblm_screen 0.1.0
    called BoxLeastSquares without flux errors, so its SNR was 1-3 even for 10% eclipses,
    and all 19 stars got NO_ECLIPSE although 17 show clear eclipses. E1, E3 and E8 pass.
    E7 very probably fails, because VSX has imported Gaia DR3's eclipsing binaries, so
    these systems are known variables. What is new is the Gaia-weighed masses and radii.
  - `eblm_fit.py` replaces that stage with a limb-darkened eclipse model and measures the
    primary's radius from the light curve. Its predictions G1-G6 are in
    `findings/2026-11-17-eblm-fit-prereg.md`. The job is queued.
  - The Sector 69 dip on TIC 41898425 is rejected as a PDC artefact
    (`findings/2026-11-17-vet-41898425-results.md`).
- **0.9.0: forecast graded; deep eclipses and Kepler.**
  - The pre-registered forecast (job gaia-forecast-v2) is graded in
    `findings/2026-11-17-forecast-results.md`. **F1, F2, F3 and F5 pass; F4 fails**:
    359 DR3 orbits with G < 14.5, |cos i| < 0.2 and a dark-companion mass below 0.1 M☉,
    where we guessed 5-30. At face value, Gaia's probabilities give 1.6 transits or
    eclipses in TESS Years 9-10 across all 359.
  - Two stars pass the monitoring rule. **Gaia DR3 5440672572654653696** (a K7/M0 dwarf
    at ~111 pc, P = 135.2 d) has its two conjunctions very probably inside TESS Sectors
    110 and 111, which are being observed now (October-December 2026). **Gaia DR3
    2102618458287057920** (an M dwarf at 68 pc, P = 165.7 d) is KIC 6436291, observed by
    Kepler for four years.
  - **A problem found in archival.py:** it drops residuals deeper than 8% as outliers,
    which would throw away a 10-20% M-dwarf eclipse while injected test eclipses were
    still "recovered". `deepcheck.py` keeps residuals up to 60% deep, adds Kepler data
    and lists the deepest dips anywhere in the data. Its test of the 16 best targets is
    pre-registered in `findings/2026-11-17-deepcheck-prereg.md` (K1-K4).
  - One of those targets is the known brown-dwarf host LHS 1610. Radial velocities plus
    Gaia give i = 114.5° there (Fitzmaurice et al. 2023), where Gaia alone gives about
    93°.
- **Full DR3 search done** (`findings/2026-11-17-dr3-full-search-results.md`). Real
  eclipses land where Gaia's orbits predict them, some repeating at Gaia's period to
  within 0.03–0.07 d. The pre-registered rate test fails narrowly (24 strong matches, 25
  needed). **No brown dwarf or planet transits** at a predicted conjunction in DR3.
- **Correction (0.7.0).** The v4 "strong match" rule needed a window-match Bayes factor
  above 10. That factor cannot exceed about P / (2.5 σ_t), so short-period systems with
  timing errors of a day could never count. HD 75767 (P = 10.25 d; 7.7% eclipses known
  since STEREO) and TIC 272540685 (P = 82.2 d; 14% eclipses) were missed this way. Our
  earlier statement that DR3 orbits predict "about three times more eclipses than TESS
  shows" is withdrawn until `calib_eclipse_rate.py` reports; its predictions are
  pre-registered in `findings/2026-11-17-inclination-calibration-prereg.md`.
- **0.7.1:** the 15 MB prior table could not be published (our publish pipeline accepts at
  most 2 MB), so the calibration job now rebuilds it bit for bit and checks it before
  grading (`calib_support.py`, `findings/2026-11-17-calib-v2-amendment.md`). The
  watch-list re-run with dipsearch 0.4.3 is graded: W2 passes, W1 and W3 fail, and a third
  TESS artefact type (dips next to short data gaps) is documented
  (`findings/2026-11-17-watchlist-v3-results.md`).
- **0.8.0, new question: white-dwarf self-lensing at Gaia-predicted times.** About 3,145
  Gaia DR3 astrometric orbits probably hold white dwarfs (Shahaf et al. 2024). When such
  a white dwarf passes in front of its star, it magnifies it by a few thousand ppm for
  hours to a day. `selflens.py` predicts when that should happen and searches TESS for
  brightenings there. Pre-registered in `findings/2026-11-17-selflens-prereg.md`. The
  wow if it works: the first self-lensing white dwarf found from a Gaia orbit, with its
  mass measured both by lensing and by astrometry.
- **0.8.1:** dipsearch 0.4.4 removes dips next to short data gaps, as an opt-in
  (`DR4_GAP_OPTIONS`) so that the queued pre-registered jobs keep their 0.4.3 rules. No
  known self-lensing binary has a usable Gaia DR3 orbit so far: KOI-3278's photocentre
  orbit is only ~0.24 mas (RUWE 1.02, no solution)
  (`findings/2026-11-17-dipsearch-044-and-selflens-control.md`).
- Which eclipsing systems are new is being checked against the Chopard-Vilhem deposit,
  SIMBAD, VSX and the TESS EB catalogue (`xmatch_prior.py`). None is called new until
  then.
- Next: the queued jobs (inclination calibration, eblm_fit, self-lensing, deepcheck,
  cross-match), then Gaia DR4 on 2 December 2026.

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
   - Each source's draws are seeded by the run seed and its source_id alone, so a
     rerun with the same arguments reproduces the prior table exactly.
4. **Which conjunction is the transit (0.3.0).** For `AstroSpectroSB1` solutions,
   ω_RV = atan2(C, H) has no π ambiguity, and the companion passes in front of the star
   at f = π/2 − ω_RV. `transit_label()` names that conjunction (`transit_conj`).
   - A label is only given when σ(ω_RV) < 0.6 rad. For circular solutions it is given
     when H > 0 at 2σ or more.
   - The convention was checked against the eclipses of Gaia's own eclipsing
     spectroscopic binaries (see Findings).
5. **TESS light curves.** Look up the TIC ID (MAST) and download TESS light curves:
   SPOC 2-min first, then TESS-SPOC, then QLP, one per sector.
6. **Dip search** (`dipsearch.py`).
   - **0.4.2:** first drop cadences below half the median flux. In the watch-list run,
     QLP light curves of Sector 104 fall to about 10% at the start and end of each orbit,
     and those cadences are not quality-flagged.
   - **0.4.3:** also drop every cadence within 0.5 d of such a cadence, because the flux
     ramps down to the floor and back up over ~0.3 d and the ramps still made 3–22%
     "dips". Drop **incoherent boxes**: coherence = in-box scatter / box-mean depth,
     which is sqrt((1−p)/p) for a dip filling a fraction p of the box and sqrt(k−1) for
     a one-bin spike. Boxes above 0.75 whose scatter is also > 3× the per-bin noise are
     dropped before de-duplication, so the box that sits inside a real dip still wins.
     Dips shorter than ~1.3 h are no longer reported.
   - **0.4.4 (opt-in):** with `search(t, f, **DR4_GAP_OPTIONS)`, every cadence within
     0.25 d of a gap longer than 0.1 d (and of the series ends) is dropped, and every such
     gap counts as an edge for `near_edge` (events get `edge_dist_d`). This removes the
     dips seen right after and right before short gaps on TIC 322271767 and
     TIC 231290240. The defaults are those of 0.4.3, so jobs registered with 0.4.3 run
     unchanged; the DR4 search opts in.
   - Bin the light curves to 30 min and split them at gaps.
   - Detrend each piece with a running median three times as wide as the trial
     duration.
   - Run box searches for durations of 2 to 24 h.
7. **Score each dip** with a window match: the probability under the Gaia orbit that a
   conjunction falls within one duration of the dip, divided by the same probability for
   a random time. This score is capped at about P / (2.5 σ_t), so it ranks dips but must
   not be used alone to decide whether a short-period system eclipses (see 0.7.0).
8. **Outputs.**
   - `gaia_edge_on_priors.csv` (next-conjunction and next-transit predictions);
   - `substellar_edge_on_candidates.csv`;
   - `tess_targets.csv`;
   - `covered_windows.csv` (0.3.0: every predicted window TESS covered; a covered
     window with no dip is a constraint);
   - `events.csv`, plots, `windows/*.png` (with `--window-plots`) and `report.md`.

### Gaia inclinations against TESS eclipses (`calib_eclipse_rate.py`, 0.7.0)

Pre-registered in `findings/2026-11-17-inclination-calibration-prereg.md`, amended
(inputs only) in `findings/2026-11-17-calib-v2-amendment.md`.
1. **Detection without the Bayes factor.** A dip counts as an eclipse if it has SNR ≥ 10
   and depth ≥ 500 ppm, is not at a segment edge or simultaneous with a dip in another
   target, and lies within 3σ + half its duration of a covered predicted conjunction
   (when that half-width is ≤ P/4). Short-period systems whose windows are wider than
   that count when two clean dips repeat at n·P within 0.2 d + 3nσ_P.
2. **Expected detections.** cos i ~ N(cos i_Gaia, (kσ)²); each conjunction eclipses
   below lim = q (1 + e cos f) / (1 − e²), q = (R1 + R2)/a (recovered exactly from the
   durations the search wrote). Both conjunctions share one inclination and are weighted
   by their TESS coverage.
3. **Fits.** k (σ(cos i) too small by k), f (a fraction of orbits wrong and randomly
   oriented), s (radii scaled by s); profile-likelihood 95% intervals; the exact
   Poisson-binomial probability of seeing so few eclipses if Gaia is right.
4. **False-alarm control** half-way between the conjunctions, and **timing** z-scores of
   every detected eclipse.
5. **Bins** by solution type, period, G, significance, eccentricity and RUWE, and two
   lists: eclipses predicted with p ≥ 0.8 but not seen (suspect inclinations), and
   eclipses the old BF rule missed.
6. **Outputs:** `calib_report.md`, `calib_summary.json` (grades C1–C7) and
   `calib_targets.csv`.

`calib_support.py` (0.7.1) checks that a rebuilt prior table reproduces the v4 targets
(`repro`: exact p_ecl and m2_dark for at least 99% of them, none missing, none off by more
than 0.02), writes the target rows as a small table, and turns the detections into a
cross-match list for `xmatch_prior.py` (`seen`).

### White-dwarf self-lensing pulses (`selflens.py`, 0.8.0)

1. **Sample.** The Gaia DR3 astrometric binaries with probable white-dwarf companions of
   Shahaf et al. (2024; updated Table A1, Zenodo 10.5281/zenodo.14799795, CC BY 4.0) that
   have G < 15 and |cos i| < 0.2.
2. **Pipeline.** The unchanged `run_search.py`, with three substitutions: only these stars
   get priors; the companion radius is a white-dwarf radius (Nauenberg 1972), so the
   crossing probability and duration are those of the pulse; and the TESS flux is
   inverted (2 − f) so the box search finds brightenings. Strong original dips
   (eclipses) are clipped instead of upward outliers, and the plots show 2 − f.
3. **Prediction.** A = 2 (R_E/R1)² − (R_wd/R1)², with R_E² = 4 G M_wd a / c², at the
   conjunction where the white dwarf is in front (Gaia's RV label for AstroSpectroSB1
   solutions; both conjunctions otherwise).
4. **Rule.** SNR ≥ 8, amplitude within a factor of 3 of A, duration within a factor of 3
   of the prediction, not at an edge, not simultaneous with another target, inside
   3σ + D/2 of a covered window. A control half a period away. Predictions L1–L4.
5. **Outputs.** `selflens_targets.csv`, `selflens_candidates.csv`,
   `selflens_control.csv`, `selflens_summary.json` and `shahaf_info.json`, plus the usual
   run_search outputs.

### What is already known (`xmatch_prior.py`, 0.6.2)

For every strong match of the full search (`findings/2026-11-17-dr3-strong-matches.csv`):
- whether it is in the 1,726-orbit selection of Chopard-Vilhem (2026), and in which
  files of that Zenodo deposit (newest version) its Gaia DR3 source_id or TIC appears;
- the Gaia DR3 inclination of each of its solutions and |i − 90°|;
- SIMBAD main identifier, object types and number of references;
- AAVSO VSX and TESS EB catalogue (Prša et al. 2022) entries within 15″, and every
  VizieR table with a source within 3″.

It grades pre-registered prediction P3 and lists the systems found in none of the
sources. Only those can be reported as new.

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

### Deep eclipses and Kepler (`deepcheck.py`, 0.9.0)

archival.py drops every residual deeper than max(8σ, 8%). That is right for the ~1%
transits expected around FGK stars, but a 0.1 M☉ companion in front of an M dwarf blocks
10-20% of the light, and the injected test eclipses (added after the clip) would still
be "recovered". deepcheck keeps archival.py's prior, posterior, search, null and
injection steps unchanged, and:
1. keeps residuals up to 60% deep (`prepare_deep`);
2. adds Kepler long-cadence PDCSAP light curves (2009-2013) when the star was a Kepler
   target (match within 5″, or within 10″ with Kp within 1 mag of G; BKJD → BTJD is
   −2167 d), and runs a Kepler-only search as well as the combined one;
3. lists the 8 deepest box dips anywhere in the data (`deepest_dips`), with each dip's
   offset in σ from the predicted conjunction (`conj_offset`), so an eclipse at the
   wrong phase, an unrelated eclipsing binary or an artefact is seen as well;
4. looks Kepler targets up in the Kepler EB catalogue (Kirk et al. 2016, VizieR
   J/AJ/151/68).

Outputs: `deepcheck_results.csv`, `deepcheck_report.md`, `kepler_meta.json`, and
`deepcheck/<id>_<conj>.json` with `_best.png` and `_fold.png`.

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

### Gaia SB1 orbits × Gaia eclipsing binaries (`eblm_screen.py`, 0.6.0)

1. **Sample.** SB1 orbits whose `vari_eclipsing_binary` period agrees within 1%, with
   FLAME mass and radius (one archive query).
2. **Eclipse-only depth.** Gaia's `derived_primary_ecl_depth` includes twice the
   ellipsoidal amplitude, so the eclipse depth is the Gaussian depth (checked to 10⁻⁶ mag
   on five stars).
3. **Classes.**
   - `twin_blend_suspect`: secondary ≥ 0.7 × primary and f(M) < 0.003 M☉, a diluted SB1 K.
   - `eblm_like`: a single shallow eclipse (< 0.1 mag; secondary < 0.15 × primary or
     none).
   - `twin` and `other` for the rest.
4. **Gaia-only physics.**
   - m2 sin i (with its ±2σ range from K);
   - R2 from the depth, and its ratio to an approximate main-sequence radius;
   - the predicted ellipsoidal amplitude (Morris 1985) against Gaia's measured one;
   - Roche-lobe filling (Eggleton 1983);
   - the offset of the eclipse from the transit and occultation conjunctions (exact
     Kepler, RV convention).
5. **TESS test** of the N lowest-mass eblm_like systems:
   - BLS within ±0.1% of the SB1 period;
   - a harmonic out-of-eclipse model, with primary, secondary, odd and even depths;
   - the companion's brightness temperature from the occultation;
   - a pre-registered `verdict()`: NO_ECLIPSE, TWIN_AT_2P, HOT_COMPANION,
     LUMINOUS_COMPANION, MASS_TENSION_HEAVIER/LIGHTER, or
     [BD_]EBLM_{CONSISTENT, LARGE_RADIUS, SMALL_RADIUS}.
   - **0.1.0 has a bug here** (no flux errors passed to BLS); use `eblm_fit.py`.
6. **Catalogues.** SIMBAD, VSX and the TESS EB catalogue (Prša et al. 2022).
7. **Outputs.** `sb1_eb_classified.csv`, `eblm_like.csv`, `eblm_tess_vet.csv` / `.json`,
   `eblm_summary.json` and `eblm_plots/`.

### Eclipse-model fits (`eblm_fit.py`, 0.10.0)

Same Gaia sample and TESS light curves as eblm_screen, with a new TESS stage:
1. BLS with real flux errors, used only to find the phase of the primary eclipse.
2. A physical model fitted to 1,000 phase bins:
   - circular orbit;
   - quadratic limb darkening (approximate TESS-band coefficients from Teff);
   - exact ring-integrated occultation of the primary;
   - the companion's occultation, whose depth also dilutes the transit;
   - harmonics to 3rd order (ellipsoidal, reflection, beaming);
   - exposure smoothing.
   - The free parameters (phase, k, b, a/R1) are fitted by Nelder-Mead, with the linear
     part solved exactly at each step.
3. Detection from the χ² gain over a harmonics-only model (`snr_fit`).
4. The inclination from b and a/R1. The true companion mass from the SB1 mass function.
   R1 from a/R1 and Kepler's law, with FLAME R1 as a cross-check. R2 = k R1.
5. Odd/even transit amplitudes, the ellipsoidal amplitude against the prediction, and the
   companion's brightness temperature against an irradiation-aware ceiling.
6. Pre-registered verdicts and grades G1-G6.

### Inflation against stellar models (`eblm_infl.py`, 0.11.0)

Post-processing of `eblm_fit_results.csv`:
1. Downloads the BHAC15 isochrones (Baraffe et al. 2015, `BHAC15_iso.2mass`) and records
   the source. A transcribed fallback is flagged if the download fails.
2. Inflation = R2 / R_BHAC15(m2) − 1 at 1, 5 and 10 Gyr, with R1 from FLAME (primary) or
   from the light curve.
3. A pre-registered main set: clean EBLM verdicts, b < 0.8, snr_fit ≥ 30, a FLAME mass,
   0.08-0.6 M☉, and light-curve and FLAME R1 within 20% of each other.
4. **H1:** the median with a bootstrap 95% interval (INFLATED if the lower bound is above
   +3%). **H2:** the Spearman correlation with period, with a one-sided permutation p.
   Also period bins, confounders and a plot.
5. Outputs: `infl_summary.json`, `infl_table.csv`, `infl_report.md` and
   `infl_vs_period.png`.

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
- `dipsearch.py`:
  - 0.4.2: broken cadences at 10% flux are dropped and counted. Without the floor they
    dominate the search.
  - 0.4.3: a floor with linear 0.3-d ramps (as on TIC 41898425 in Sector 104) gives a
    > 1% "dip" without the pad and nothing with it.
  - 0.4.3: one scattered 30-min bin at 0.8 (as on TIC 322271767) is an event without
    the coherence cut and is rejected with it.
  - 0.4.3: coherence values worked by hand (0, 1, √3, and 0.84 for the TIC 322271767
    box). A 3-h flat dip and an 8-h V-shaped grazing dip are still recovered.
  - 0.4.4: the gap pad on exact binary fractions (10 cadences around one gap, 20 with
    the series ends). A 2-h 8% step after a 0.3-d gap and a 4-h 0.7% ramp before a
    0.17-d gap are found with the 0.4.3 defaults and gone with `DR4_GAP_OPTIONS`; a 6-h
    2,000-ppm transit 1 d from the gap survives; a transit 0.3 d after a 0.2-d gap is
    flagged near an edge only with `edge_gap`.
- `deepcheck.py` (0.9.0), on exact binary-fraction times:
  - a 25% dip is lost by archival.prepare (495 of 500 points left) and kept by
    prepare_deep (500);
  - for shallow data, prepare_deep gives exactly what archival.prepare gives;
  - a 1/16-deep, 15-point dip is found by `deepest_dips` at exactly t = 10, with the
    depth worked by hand (0.0617 against 0.0625 after normalisation);
  - conjunction offsets and their σ with and without the P–T correlation (3.25 and 0.75,
    worked by hand);
  - BKJD → BTJD = −2167 d and the Kepler match rule.
- `calib_eclipse_rate.py` (0.7.0):
  - the eclipse limits of HD 75767 worked by hand from the v4 table (lim = 0.05385 and
    0.08653), and its eclipse probability 0.979 against the Monte Carlo's 0.983;
  - circular limits equal (R1 + R2)/a exactly; out-of-range durations are clipped;
  - the two-conjunction detection probability for every coverage case, the isotropic
    limit, σ inflation and radius scaling (worked by hand);
  - the exact Poisson-binomial CDF and the likelihood with a false-alarm rate;
  - a simulated sample with σ inflated 2.5× is recovered (95% interval contains 2.5 and
    excludes 1);
  - window matching, control phases, the repeat rule (HD 75767's 10.2488-d spacing; no
    TESS-orbit periods) and the artefact veto;
  - an offline end-to-end run on four synthetic targets.
- `calib_support.py` (0.7.1): exact and near matches, a missing target, the 99% and 0.02
  thresholds, the choice of solution type, the detection list with extra systems, and a
  file round trip.
- `selflens.py` (0.8.0), worked by hand: the white-dwarf radius (0.012445 R☉ at
  0.6 M☉), Kepler's law (1 AU = 215.032 R☉), the Einstein radius (0.0405 R☉ for 0.6 M☉
  at 322 R☉) and the pulse amplitude (3,126 ppm for a 1 R☉ star); window matching and
  control shifts; and the full pulse rule on a synthetic target, where one event passes
  and events that are too bright, too short, at an edge or at the wrong conjunction do not.
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
- `eblm_screen.py` (0.6.0), worked by hand on HIP 2964 (Gaia DR3 2346634757461218816):
  - the mass function 4.1857 × 10⁻³ M☉ and m2 sin i = 0.2455 M☉;
  - a = 6.056 R☉ and the ellipsoidal prediction 0.01357, against the 0.0117 Gaia measures;
  - the eclipse 0.0022 in phase from the transit conjunction;
  - the eclipse-only depth;
  - the circular and eccentric conjunction limits;
  - the Roche lobe, the Planck ratio and its inverse;
  - the twin flag, the population statistics and every verdict rule.
- `eblm_infl.py` (0.11.0), worked by hand: the BHAC15 parser on a two-age excerpt; the
  interpolation (0.2585 R☉ at 0.25 M☉, 5 Gyr) and off-grid masses and ages; average
  ranks with ties and Spearman ρ = 2/√5; the permutation p for perfect trends; the
  bootstrap median; every H1 label, including the +3% boundary; every main-set cut; and
  an end-to-end summary whose median (0.11), ρ (−1) and period-bin counts are known.
- `xmatch_prior.py` (0.6.2):
  - Gaia ids are found in any text file but the decimals of a float are not;
  - TIC ids from `TIC 123` text and from tic columns;
  - inclinations from Thiele-Innes constants worked by hand (0°, 60°, 90°);
  - VSX and SIMBAD eclipsing types (ELL, EP and EXOR are not eclipsing);
  - the P3 grade (exactly half is not "more than half");
  - an offline end-to-end run with stubbed archives.
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
  SIMBAD/VSX must be checked before any claim. In the full DR3 search, the 554-d system
  Gaia DR3 5267683998775216256 shows a 10% occultation, so its companion is luminous.
- How well DR3 eclipse probabilities are calibrated is the open question of 0.7.0. Until
  `calib_eclipse_rate.py` reports, treat them as upper limits. One published case: for
  LHS 1610 (Gaia DR3 43574131143039104), Gaia alone gives i ≈ 93°, and Gaia plus radial
  velocities gives 114.5° (+7.4/−10.0) (Fitzmaurice et al. 2023).
- The window-match Bayes factor is capped at about P / (2.5 σ_t) (see 0.7.0). It ranks
  dips; it does not decide whether a short-period system eclipses.
- The transit label assumes that AstroSpectroSB1 C/H follow the same RV convention as
  the EclipsingSpectro solutions used to test it, as the Gaia DR3 documentation states.
- A dip that matches a predicted window is a **candidate**, not a discovery. It still
  needs vetting: pixel-level centroids, nearby stars, known variables in VSX, SIMBAD and
  the TOI/CTOI lists, and the shape of the event.
- Dips at the start or end of a TESS orbit are where scattered light is strongest. The
  search flags them (`near_edge`), but it does not remove them. 0.4.3 removes two
  artefact types (floor ramps and single-bin spikes), not smooth scattered-light trends
  or flux that falls to zero (seen on TIC 219744709). Dips right before or after data
  gaps shorter than 0.5 d (TIC 322271767, TIC 231290240) are removed only with the 0.4.4
  option `DR4_GAP_OPTIONS`; the DR3 runs registered with 0.4.3 do not use it. The pad
  costs 0.5 d of data per gap, which lowers window coverage a little.
- The dip search does not report dips shorter than ~1.3 h (0.4.3).
- The self-lensing search has no real positive control yet: no known self-lensing
  binary has a usable Gaia DR3 orbit so far (see
  `findings/2026-11-17-dipsearch-044-and-selflens-control.md`).
- The archival injections are added after detrending, so they slightly overstate the
  sensitivity. The trend skips ±D around each point, which keeps this effect small.
  Ground photometry of bright stars (G ≲ 12.5 in ZTF) can be affected by saturation.
- **archival.py drops residuals deeper than 8%** (found in 0.9.0). Its results are
  valid for predicted depths well below 8%. For deeper predicted eclipses (M-dwarf
  hosts) use `deepcheck.py`. The queued pre-registered watch-list job keeps archival.py
  0.4.1 unchanged; any star in it with a predicted depth above 8% will be re-checked
  with deepcheck.
- deepcheck's 60% clip still removes total eclipses deeper than 60%, and its Kepler
  match rule can, in a crowded field, accept a neighbour within 5″ (the distance is
  reported).
- The forecast ignores TESS's data gaps at perigee (about 7% of each sector). TESS
  pointings are provisional and can change.
- Anonymous Gaia archive access is limited to 60 s and 50,000 rows per query, 5 jobs at
  a time and 50 DataLink sources per request. Very large DR4 queries need many ranges and
  can be slow on release day.
- The RV-scatter bound assumes a single sinusoid and the DR3 bright-star error model. RV
  variability can come at any period, so it excludes a planet-only system; it does not
  prove that the transit signal itself is an eclipsing binary. Gaia's transit periods
  are often aliases.
- `eblm_screen.py`:
  - FLAME masses and radii assume a single star.
  - Short-period SB1 eccentricities are often spurious.
  - The main-sequence radius relation is approximate. It is 3-4% larger than BHAC15 at
    0.2-0.4 M☉; use `eblm_infl.py` for any inflation number.
  - Gaia's Gaussian eclipse depths come from sparse sampling. The TESS stage reports the
    TESS / Gaia depth ratio for that reason.
- `eblm_fit.py` / `eblm_infl.py`:
  - circular orbits only;
  - no metallicity (BHAC15 is solar; Swayne et al. 2024 find about −9% inflation per
    dex);
  - Gaia DR3 K for broad-lined F/A primaries can be biased (Fitzpatrick et al. 2025 found
    only 3 of 8 Gaia K values agreeing within 1σ);
  - no per-system parameter errors yet, so the tests use medians and ranks;
  - Gaia's sparse photometry favours deep eclipses, and so possibly large companions.
- `calib_eclipse_rate.py`: the v4 dip catalogue keeps about 20 dips per star, preferring
  dips inside windows, so its false-alarm control under-counts; coverage means a
  conjunction landed on data, not that the search would have found the eclipse there.

## Run

```
pip install -r requirements.txt
pip install "tess-point>=0.9.5"                                      # forecast only
python -m unittest -v test_gaia_orbits test_dipsearch test_run_search test_archival test_forecast test_vet_event test_transit_rv_screen test_vet_short_period test_eblm_screen test_eblm_fit test_eblm_infl test_xmatch_prior test_calib_eclipse_rate test_calib_support test_selflens test_deepcheck
python run_search.py --data-dir data --out-dir out                    # DR3
python run_search.py --data-dir data --out-dir out --no-tess          # watch list only
python run_search.py --source-ids 393581461455623296,2960647744567925632 --gmax 17 \
    --cosi-max 0.3 --min-p-ecl 0 --window-plots --data-dir data --out-dir out
python archival.py --source-ids 393581461455623296 --gmax 17 --cosi-max 0.3 \
    --data-dir data --out-dir out                                    # archival test
python deepcheck.py --source-ids 2102618458287057920,43574131143039104 --gmax 17 \
    --cosi-max 0.3 --data-dir data --out-dir out                     # deep eclipses + Kepler
python forecast.py --source-ids 393581461455623296 --gmax 17 --cosi-max 0.3 --m2-max 1 \
    --data-dir data --out-dir out                                    # forecast
python vet_event.py --tic 41898425 --ra 21.734801 --dec -41.059717 --t0 3192.263 \
    --dur-h 8 --pred-dur-h 11.68 --sector 69 --period 196.6738 --period-sd 0.8175 \
    --exp-depth 0.0105 --data-dir data --out-dir out                 # vet one event
python transit_rv_screen.py --schema gaiadr3 --out-dir out            # Gaia transits x Gaia RVs
python vet_short_period.py --tic 207399049 --gaia 1622997463177004928 --p-rv 0.46023065 \
    --k-rv 19.695569 --k-rv-err 1.3143485 --e-rv 0.2008897 --p-phot 0.8513754 \
    --m1 0.9556862 --r1 1.1634727 --data-dir data --out-dir out      # vet a short-period SB1
python eblm_screen.py --schema gaiadr3 --n-tess 20 --data-dir data --out-dir out  # SB1 x EB
python eblm_fit.py --schema gaiadr3 --n-tess 200 --data-dir data --out-dir out    # eclipse fits
python eblm_infl.py --results out/eblm_fit_results.csv --out-dir out  # inflation vs BHAC15
python xmatch_prior.py --targets findings/2026-11-17-dr3-strong-matches.csv \
    --data-dir data --out-dir out                                    # what is already known
# Gaia inclinations vs eclipses (0.7.1): rebuild the v4 prior table, check it, then test
python run_search.py --data-dir data --out-dir data/dr3-full-search-v4 --gmax 14.5 \
    --cosi-max 0.2 --mc 600 --max-targets 400 --tap-chunks 16 --no-tess
python calib_support.py repro --dir data/dr3-full-search-v4 --out-dir out
python calib_eclipse_rate.py --data-dir data --out-dir out
python selflens.py --data-dir data --out-dir out --gmax 15 --max-targets 250   # self-lensing
python run_search.py --schema gaiadr4 --tap-chunks 64 --data-dir data --out-dir out   # DR4
python run_search.py --schema gaiadr4 --targets-table gaiadr4.gaia_exoplanet_candidates \
    --cosi-max 1.0 --data-dir data --out-dir out                     # Gaia exoplanet candidates
python transit_rv_screen.py --schema gaiadr4 --out-dir out            # DR4's 1,007 candidates
python eblm_screen.py --schema gaiadr4 --no-tess --out-dir out        # DR4 SB1 x EB
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
- `findings/2026-11-17-watchlist-v2-results.md` (0.4.3): the re-run with the 0.4.2 floor.
  - The floor removed the 10%-flux cadences but not the ramps around them (3–22% "dips"
    remain), and single scattered bins made 7–10% 2-h "dips" on TIC 322271767. The goal
    "artefacts gone" fails.
  - 0.4.3 pads the floor by 0.5 d and drops incoherent boxes. Predictions W1–W3 for
    the v3 re-run are written down before it runs.
- `findings/2026-11-17-watchlist-v3-results.md` (0.7.1): the re-run with 0.4.3.
  - **W2 passes** (the Sector 69 event on TIC 41898425 is still reported).
  - **W1 fails:** the floor ramps are gone (deepest dips 5,532 and 3,552 ppm instead of
    221,197 and 76,091), but a 9.8% 2-h "dip" on TIC 322271767 survives. It starts the
    moment the data resume after a 0.3-d gap: a third artefact type.
  - **W3 fails narrowly:** the floor pad also removes some good cadences, so one window
    lost its coverage (65 instead of 66).
- `findings/2026-11-17-dipsearch-044-and-selflens-control.md` (0.8.1):
  - dipsearch 0.4.4's gap pad, why it is opt-in (three queued jobs were registered with
    0.4.3), and its tests;
  - KOI-3278 has no Gaia DR3 orbit (RUWE 1.02; its photocentre orbit is only ~0.24 mas),
    and KIC 8145411 has position-only solutions, so neither can test the self-lensing
    search. A 418.6-d DR3 orbit in the Kepler field is not KIC 12254688 (it is a K dwarf).
- `findings/2026-11-17-vet-41898425-prereg.md`: the fixed rules and predictions for
  vetting that event.
- `findings/2026-11-17-vet-41898425-results.md` (0.10.0): the event is rejected as a PDC
  artefact; V1-V3 pass.
- `findings/2026-11-17-archival-prereg.md`: predictions for the archival test.
  - TESS's Year 9 pointings (to September 2027) do not cover the best target, so only
    the ground can test its 2027 windows.
  - Gaia flags the star as VARIABLE (SOLAR_LIKE, 8.7 mmag scatter in 57 G epochs).
- `findings/2026-11-17-forecast-prereg.md`: what the forecast publishes and five
  predictions about it, written before it ran.
- `findings/2026-11-17-forecast-results.md` (0.9.0): **the graded forecast.**
  - F1, F2, F3 and F5 pass. F4 fails: run B kept 359 stars, not 5-30.
  - Across those 359, Gaia's probabilities at face value give 1.6 expected TESS
    transits or eclipses in Years 9-10. There are 861 ground windows in the year from
    2026-12-01, 92% of them constrained.
  - Gaia DR3 5440672572654653696 (P = 135.2 d) has both conjunctions very probably in
    TESS Sectors 110-111 (October-December 2026).
  - Gaia DR3 2102618458287057920 (KIC 6436291) can be tested with Kepler.
  - The archival.py 8% clip problem is described.
- `findings/2026-11-17-deepcheck-prereg.md` (0.9.0): the archival + Kepler test of the 16
  best forecast targets, with predictions K1-K4, written before any light curve was read.
  The notes added afterwards give the Gaia properties of six targets (all M dwarfs within
  115 pc), identify LHS 1610 and KIC 6436291, and record that KIC 6436291 is not in the
  Kepler EB catalogue.
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
- `findings/2026-11-17-gaia-only-eblm.md` (0.6.0; Gaia stage plus TESS pre-registration):
  - **Twin flag.** Among 1,408 Gaia DR3 SB1 orbits with a same-period Gaia eclipsing
    binary and two eclipses, near-equal eclipses make up 52% of those with
    f(M) < 0.003 M☉, against 22–24% at larger f(M). This is a Gaia-internal flag for
    diluted SB1 amplitudes.
  - **73 single-shallow-eclipse systems** are Gaia-only EBLM candidates (169 by the
    code's own rule in 0.10.0). In five of the six lowest-mass ones, Gaia's ellipsoidal
    amplitude matches the one predicted from the Gaia SB1 mass to 0–14%. Every eclipse
    checked by hand falls at the transit conjunction.
  - **Lowest masses:** m2 sin i = 0.12 M☉ (TIC 346363735, P = 0.515 d, an F star filling
    ~91% of its Roche lobe) and 0.17 M☉ (two systems).
  - **No brown dwarf.** No companion of brown-dwarf mass is seen to eclipse in DR3.
  - **Radii.** Gaia's depths imply radii 1.1–1.7× the main sequence; the TESS test is
    pre-registered.
- `findings/2026-11-17-eblm-v1-results.md` (0.10.0): the TESS stage graded. The BLS bug
  (E2 fails as run), the classic EBLM light curves (HIP 2964, TIC 35044762, TIC 426763538,
  TIC 276386308), six companions brighter than their mass suggests, and why these are
  known variables (E7).
- `findings/2026-11-17-eblm-fit-prereg.md` (0.10.0): eblm_fit's method, verdicts and
  predictions G1-G6.
- `findings/2026-11-17-short-period-inflation-prereg.md` (0.11.0): **are M dwarfs in
  0.5-5-day orbits inflated?** The prior-art correction (Swayne et al. 2024), the BHAC15
  reference, the main set and tests H1-H2, written before any eblm_fit result.
- `data/eblm-v1/`: outputs of the eblm_screen TESS stage (CC BY 4.0), including the
  classified SB1 × EB sample and six fold plots.
- `findings/2026-11-17-dr3-full-search-results.md` (0.6.2): **the graded full DR3
  search**, with the prior-art correction.
  - 24,157 near-edge-on orbits; 287 targets reached TESS, 277 with data.
  - P1 uninformative (one Gaia-EB target, a triple); **P2 fails narrowly** (24 strong
    matches, 24.7 needed); P3 pending; **P4 passes** (no substellar strong match).
  - Eclipses repeat at Gaia's period where Gaia predicts them, e.g. four eclipses of
    Gaia DR3 6360777231720947328 (P = 58.73 d), each within 0.07 d of prediction.
  - A 554-d doubly eclipsing binary (Gaia DR3 5267683998775216256) whose 4× different
    eclipse lengths match Gaia's eccentricity and ω. Whether it is new is being checked.
  - The 550-d K-dwarf system TIC 342194997 is recovered; it was reported first by
    Chopard-Vilhem (2026).
  - Its reading of the shortfall ("about three times more eclipses predicted than
    seen") is withdrawn in 0.7.0 (see below).
- `findings/2026-11-17-dr3-strong-matches.csv`: the 24 strong matches, with times,
  depths, offsets and vetting status.
- `findings/2026-11-17-inclination-calibration-prereg.md` (0.7.0): **are Gaia DR3
  inclinations good enough to predict eclipses?** The BF-cap correction (HD 75767 and
  TIC 272540685 were missed by the v4 rule), what we read before writing it, the fixed
  detection rule and model, and predictions C1–C7 (expected: σ(cos i) too small by
  2–3×, timing errors about right).
- `findings/2026-11-17-calib-v2-amendment.md` (0.7.1): the full prior table could not be
  published (over 2 MB), so the calibration job rebuilds it with the same code and seeds.
  The rebuild must reproduce the v4 targets exactly before anything is graded. Every
  detection is cross-matched with SIMBAD, VSX, the TESS EB catalogue and the
  Chopard-Vilhem deposit. A sensitivity check for gap-edge dips is stated in advance.
  Predictions unchanged.
- `findings/2026-11-17-selflens-prereg.md` (0.8.0): **can a Gaia orbit tell us when a
  white dwarf will lens its star?** The sample, the pulse rule, the control and
  predictions L1–L4 (expected: a few tenths of a detectable pulse in TESS, so most
  likely an honest null and an upper limit), written before any data were read.
- `data/dr3-full-search-v4/`: the raw outputs of that run (CC BY 4.0): every target with
  its eclipse probability and window coverage (`tess_targets.csv`), all 2,505 dips
  (`events.csv`), the 1,079 covered windows, the substellar list, the run summary and
  the report. The full prior table of all 24,157 orbits (`gaia_edge_on_priors.csv`,
  15 MB) is too large for this repository. Rebuild it with the `run_search.py --no-tess`
  command under Run; the target rows will be added as a small table once the calibration
  job has checked them.
- `data/forecast-v2/`: the forecast outputs (CC BY 4.0): run B (`dr3_g14.5_c0.2_*`, 359
  stars, their TESS sectors and ground windows) and the watch list (`watchlist_*`).

## Prior art checked (2026-11-17)

- **Chopard-Vilhem 2026, Zenodo doi:10.5281/zenodo.23342416** (AAS Research Note data and
  code): eclipsing binaries at the conjunctions predicted by near-edge-on (|i − 90°| < 1°)
  Gaia DR3 astrometric orbits; 1,726 orbits, seven new EBs with P = 26–242 d, forecasts.
  The first systematic search of this kind. Missed by our earlier prior-art checks and
  added on 2026-11-17.
- **Makarov 2025, ApJL (arXiv:2502.20553):** by Monte Carlo of the Thiele-Innes
  constants, a nearly edge-on high-SNR DR3 orbit has a strongly underestimated
  inclination error (3.65° against the quoted 1.6°) but no significant bias. A
  simulation; no eclipse test. The 0.7.0 calibration tests this with real eclipses.
- **Winters et al. 2018, AJ 155, 125** (arXiv:1801.07340) and **Fitzmaurice et al. 2023**
  (arXiv:2310.07827): LHS 1610 b, a 10.6-d brown dwarf around an M5 dwarf at 9.7 pc. The
  Gaia DR3 orbit plus TRES/HPF radial velocities give i = 114.5° (+7.4/−10.0) and 49.5
  M_Jup, and Gaia's eccentricity (0.52) disagrees with the RVs (0.370).
- **Kirk et al. 2016, AJ 151, 68:** the Kepler Eclipsing Binary Catalog (used to check
  Kepler targets; the Villanova online version).
- **Wraight et al. 2012, MNRAS 427, 2298; Griffin & Fuhrmann 2013, MNRAS 430, 1390:**
  STEREO eclipses of HD 75767 (~0.1 mag), which show its 10.25-d companion is an M dwarf,
  not a white dwarf. Used as a positive control in 0.7.0.
- github.com/alejandrozarco/tess-candidates-2026 (v1.3, 2026-10-19; not peer reviewed):
  lists TIC 342194997 (P = 550.75 d, one 16.9% eclipse, credited to Chopard-Vilhem) and
  other single eclipses at Gaia-predicted conjunctions.
- Holl et al. 2023, A&A 674, A10 (arXiv:2206.05439): Gaia DR3 orbits and a few TOI
  coincidences. Its validation notes that Kepler-16 and several transit or eclipse
  candidates got near-edge-on DR3 solutions; it does not measure an eclipse rate.
- arXiv:2310.12380: rejects K2/TESS candidates using Gaia DR3 *spectroscopic* (SB1)
  orbits.
- arXiv:2310.07936: Gaia DR3 SB1s with substellar-mass companions matched to TOIs and the
  TESS EB catalogue; three transiting low-mass secondaries confirmed.
- Rowan et al. 2022 (arXiv:2212.02509): masses and radii of Gaia spectroscopic binaries
  that are ASAS-SN eclipsing binaries (128 Gaia SB2 orbits, not SB1).
- Jayasinghe et al. 2022 (arXiv:2207.05086): vetting of high-mass-function Gaia SB1s.
- El-Badry 2024 (arXiv:2403.12146) and Merle et al. 2023: diluted K for double-lined
  binaries fitted with SB1 solutions.
- Gaia Collaboration, Arenou et al. 2023 (arXiv:2206.05595): DR3 multiplicity overview.
- Halbwachs et al. 2023, A&A 674, A9: the DR3 astrometric binary solutions, including the
  C/H constants.
- arXiv:2407.16760: validation of DR3 orbital and acceleration solutions with wide
  hierarchical triples (parallaxes and errors, not inclinations).
- Czavalinga et al. 2023, A&A 670, A75: close binaries with tertiary companions found in
  Gaia DR3 orbits (eclipsing pairs with outer orbits).
- Panahi et al. 2022 (arXiv:2205.10197): Gaia DR3 photometric transit candidates checked
  in TESS. That starts from Gaia photometry, not from astrometric orbits, and the
  candidates were not vetted with Gaia's RVS data.
- arXiv:2608.06453 (2026): spectroscopic follow-up of 227 Gaia DR3 binaries with high
  inferred companion masses. TESS light curves show some of them to be hierarchical
  triples (an inner eclipsing pair inside the astrometric orbit). That agrees with our
  finding that DR3 astrometric orbits with Gaia eclipses are triples.
- arXiv:2307.10812: oscillating red giants in Gaia DR3 binaries; used DR3 inclinations to
  find two new eclipsing giants; notes that Gaia's sampling rarely detects long-period
  eclipsing binaries itself.
- Yamaguchi, El-Badry et al. 2024 (arXiv:2410.13939, PASP): a TESS search for
  self-lensing white-dwarf binaries, using Gaia DR3 orbits to check candidates.
- Yamaguchi et al. 2024 (arXiv:2405.00780): KIC 8145411, a self-lensing binary, is a
  triple whose two stars have position-only Gaia DR3 solutions.
- Kruse & Agol 2014 (KOI-3278) and Kawahara et al. 2018 (arXiv:1801.07874; KIC 3835482,
  KIC 6233093, KIC 12254688, KIC 8145411): the five Kepler self-lensing binaries.
- arXiv:2512.04606 (A&A 2026): HD 128717 B / Gaia-6 B, a long-period brown dwarf found by
  Gaia astrometry and confirmed with radial velocities; no transit search.
- github.com/coracle-us/gaia-dr4: searches DR4 epoch astrometry for outer companions of
  known transiting giant planets. That is the opposite direction to this project.
- Long-period transiting brown dwarfs found by TESS and radial velocities (for example
  TOI-5575b, arXiv:2507.09461; the four new long-period ones in A&A 2026, aa58244-25)
  were not found from Gaia astrometric orbits.
- Transiting brown dwarfs with P < 1 d that we found all orbit M dwarfs: NGTS-7Ab
  (arXiv:1906.08219), TOI-263b (arXiv:2103.11150) and ZTF J2020+5033 (arXiv:2307.15729).
- The EBLM project (Maxted, Triaud & Martin 2023 review; EBLM XVIII, arXiv:2511.23430):
  M dwarfs eclipsing F/G/K stars, found in WASP photometry and CORALIE RVs.
- **M-dwarf radius inflation in EBLM binaries (checked for 0.10.0-0.11.0):**
  - Swayne et al. 2024, EBLM XI (MNRAS 528, 5703; arXiv:2312.11339): 23 M dwarfs with
    CHEOPS and TESS. About 6% inflation for P < 5 d (5 systems, 2.8-4.3 d) against ≤ 3%
    at longer periods, and a −9%/dex metallicity trend.
  - Fitzpatrick et al. 2025, EBLM XIV (arXiv:2502.09267): 19 systems with TESS, some with
    Gaia DR3 K; 2.6 ± 1.1% inflation; only two systems with P < 3 d; no period test.
  - Davis et al. 2026, EBLM XIX (arXiv:2610.18338): 66 systems, 50 high-quality ones, all
    with P > 5 d (shorter periods removed because of synchronised-rotation activity);
    0.3 ± 1.6%. EBLM XX (arXiv:2610.18339) validates the SB1 method.
  - Çakırlı, Özdarcan & Hoyman 2025 (MNRAS 544, 4336): 8 systems, P = 4.2-25.6 d, no
    clear inflation.
  - Baraffe et al. 2015 (A&A 577, A42): the BHAC15 models used as the reference.
- TESS EB catalogues: Prša et al. 2022 (sectors 1–26) and the TESS Ten Thousand catalogue
  (arXiv:2506.05631).

## Credits and licence

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name.
Code: Apache-2.0. Results and text: CC BY 4.0.
Data: ESA Gaia DR3 (Gaia Collaboration), including epoch photometry, served by the ESA
Gaia Archive and the ARI Heidelberg Gaia mirror; NASA TESS and Kepler via MAST (SPOC,
TESS-SPOC and QLP light curves, TESScut, Kepler PDCSAP light curves and the Kepler Input
Catalog); the TESS Input Catalog; ExoFOP-TESS and the NASA Exoplanet Archive TOI table;
the Villanova Kepler Eclipsing Binary Catalog; the Zwicky Transient Facility (IRSA);
ASAS-SN Sky Patrol; SIMBAD and VizieR (CDS) with the AAVSO VSX catalogue and the TESS EB
catalogue (Prša et al. 2022); TESS pointings from the TESS Science Center and tess-point
(tessgi); the Chopard-Vilhem (2026) Zenodo deposit (CC BY 4.0) for the prior-work
cross-match; the BHAC15 stellar models (Baraffe et al. 2015). Uses numpy, astropy,
astroquery, lightkurve, matplotlib, skypatrol (pyasassn) and tess-point.
