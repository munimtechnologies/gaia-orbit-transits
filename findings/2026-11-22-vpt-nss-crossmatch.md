# Gaia's own orbit catalogue against Gaia's own transit list (DR3): one more new candidate is a double-lined binary

Written 2026-11-22 (~03:00 UTC). By MV2 of Munim, Inc.; made with AI agents working in his name,
not yet checked by a human expert. Text and data CC BY 4.0.

Status: **exploratory, not blind** (the categories of these stars were known from the step-g
rehearsal, `findings/2026-11-21-vpt-dr3-results.md`). Sections 5 and 6 are **registered before the
outcome**: predictions for the queued period-free TESS job (gaia-vpt-pf-dr3-v1, not yet run when
this was written) and amendment 2 for Gaia DR4 day (2 December 2026).

## 1. The question

Gaia DR3 published two catalogues that can speak about the same stars: the photometric transit
candidates (`gaiadr3.vari_planetary_transit`, 214 stars) and the orbits fitted to Gaia's own
radial velocities and astrometry (`gaiadr3.nss_two_body_orbit`). Our RVS screen of 22 November
(`findings/2026-11-22-vpt-rvs-full.md`) used only the velocity-variability statistics in
`gaia_source`. Which of the 214 transit candidates also have a Gaia orbit, and what do those
orbits say?

## 2. Queries (ESA Gaia archive TAP, 22 Nov 2026, ~02:30 UTC)

```
SELECT n.source_id, n.nss_solution_type, n.period, n.period_error, n.semi_amplitude_primary,
       n.eccentricity, n.significance, n.goodness_of_fit, v.transit_depth,
       v.transit_reference_time, v.num_in_transit
FROM gaiadr3.nss_two_body_orbit AS n JOIN gaiadr3.vari_planetary_transit AS v
     ON n.source_id = v.source_id
```
returned **7 rows** (one solution per star). Follow-up queries on the same 7 source_ids:
`SELECT * FROM gaiadr3.vari_planetary_transit WHERE source_id IN (...)`;
`nss_two_body_orbit` columns t_periastron, center_of_mass_velocity, semi_amplitude_secondary(_error),
mass_ratio, flags; `SELECT * FROM gaiadr3.binary_masses WHERE source_id IN (...)` (5 rows);
`vari_classifier_result` (all 7: EP, score 1.0). A join of `vari_eclipsing_binary` with
`vari_planetary_transit` returned 0 rows (the query ran with valid columns).

All values are in `data/vpt-nss-dr3/vpt_nss_dr3.csv`, transcribed from the TAP responses (full
precision as returned); categories, TIC IDs and RVS labels come from `data/vpt-dr3-v1/c0`, `c1`
and `rvs`. Anyone can re-run the queries above.

## 3. Results

| star | category | Gaia transit P (d) | Gaia orbit | orbit P (d) | K1 (km/s) | companion mass | reading |
|---|---|---|---|---|---|---|---|
| WASP-18 | known planet, Gaia P right | 0.941478 | SB1 | 0.941468 ± 0.000026 | 1.94 ± 0.14 | m2 sin i ≈ 0.0100 M_sun (10.5 M_Jup); Gaia lower bound 0.0093 | **positive control**: Gaia's spectrograph recovers WASP-18 b (published K ≈ 1.82 km/s) |
| HATS-26 | known planet, Gaia P right | 3.302619 | astrometric (OTS) | 193.5 ± 2.9 | - | not in binary_masses | not interpreted |
| TOI-1991 | TOI, Gaia P wrong | 3.746301 | SB1 | 6.65906 ± 0.00119 | 9.57 ± 0.28 | m2 sin i ≈ 0.096 M_sun (m1 1.12) | orbit period = the TOI's TESS period 6.6570835 (1.7σ); TFOP already retired it as a false positive ("SEB1"); the Gaia SB1 match was first noted by Tarrants & Mendes (2023, arXiv:2310.12380) |
| WASP-2 | known planet, Gaia P wrong | 0.668025 | astrometric (OTS) | 38.04 ± 0.10 | - | 0.24-1.13 M_sun (Gaia) | a stellar companion at 38 d would swing this well-studied host by many km/s; most likely spurious (WASP-2 has a close resolved companion); not interpreted |
| **TIC 400170926** (TYC 2423-351-1) | **NEW** | 0.884783 | **SB2C (double-lined)** | **5.895935 ± 0.000182** | **72.62 ± 0.40; K2 78.94 ± 1.01** | **M1 sin³i 1.108, M2 sin³i 1.019 M_sun; Gaia m1 1.054, m2 0.970** | **a near-twin pair of Sun-like stars seen nearly edge-on** |
| TIC 470993218 | NEW | 2.597875 | SB1 | 7.06226 ± 0.00107 | 22.40 ± 1.14 | m2 sin i ≈ 0.283 M_sun (m1 1.39); Gaia lower bound 0.263 | stellar companion (already RVS-flagged) |
| TIC 207399049 | NEW | 0.851375 | SB1 | 0.460231 ± 0.000006 | 19.70 ± 1.31 | m2 sin i ≈ 0.075 M_sun (m1 1.03); Gaia lower bound 0.068 | e = 0.20 at 0.46 d is implausible for so short an orbit and the solution carries a flag (16777216); already RVS-flagged and refuted as a planet candidate earlier |

Our minimum masses use the mass function with sin i = 1 and Gaia's `binary_masses` m1 (TIC
mass for TOI-1991); Gaia's `m2_lower` is a lower confidence bound, so ours are somewhat higher.

### TIC 400170926 in more detail

- G 9.33, BP-RP 0.76, parallax 7.86 mas (128 pc), RUWE 1.00; TIC Teff 5992 K, R 1.41 R_sun
  (a single-star fit to the combined light of two stars).
- Gaia's double-lined circular orbit: mass ratio K1/K2 = 0.920; (M1+M2) sin³i = 2.127 M_sun;
  a sin i = 17.7 R_sun. Gaia's own isochrone masses (1.054 and 0.970 M_sun) are at or slightly
  below M sin³i, so sin i is close to 1 (i ≳ 80°). Two Sun-like stars 17.7 R_sun apart eclipse
  when i ≳ 83°, so eclipses are likely, and both Gaia (2.1% dip) and TESS (below) see the star dim.
- In our step-g rehearsal, TESS (SPOC, sector 72 best; 3 of 3 sectors used show it) gave a dip at
  Gaia's 0.8848 d period, 0.70% deep at S/N 14.5, flagged ODD_EVEN. A strong real signal at another
  period leaks into any fold (amendment 1), so this hit does not confirm Gaia's period.
- Gaia's transit period is not a simple fraction of the orbit: 5.895935 / 0.884783 = 6.664.
- **The RVS screen missed it:** Gaia DR3 gives no combined radial velocity (and so no variability
  statistics) for this star, so the screen labelled it RV_UNTESTED. The double-lined orbit is
  Gaia's own evidence that it is a binary of two similar stars, not a planet host.
- Prior art (22 Nov): ExoFOP lists no TOI, CTOI or follow-up; the live TESS EB catalogue page
  (Villanova) has no entry (positive control CM Dra, TIC 199574208, found); AAVSO VSX lists only
  Gaia's own EP import "Gaia DR3 3450611154067089408" at 0.88478 d; no paper found under its TYC,
  2MASS or TIC names; Tarrants & Mendes (2023) matched only TOIs and K2 candidates, and only SB1
  orbits. VizieR (CfA and CDS) was unreachable, so the ZTF and ASAS-SN variable catalogues were not
  checked.

## 4. What it means

1. **Gaia's orbit catalogue adds a ninth new candidate with Gaia's own evidence against a planet.**
   With the 8 RVS-flagged stars of 22 November, 9 of Gaia DR3's 39 unconfirmed new transit
   candidates now have Gaia data showing a stellar companion. (TIC 470993218 and TIC 207399049 are
   in both lists; TIC 400170926 is new here.)
2. **Where Gaia's transit period is wrong, Gaia's spectroscopic orbit can be right.** For TOI-1991
   the SB1 period matches the TESS period, while the transit table's period is off by a factor of
   1.78. For the three new candidates the orbit periods (5.896, 7.062, 0.460 d) are not 1, 1/2 or 2
   times the transit periods.
3. **For DR4,** where many more stars get spectroscopic orbits and epoch velocities, an NSS screen
   costs one query and catches double-lined binaries that the variability screen cannot test
   (amendment 2 below).

## 5. Predictions registered for job gaia-vpt-pf-dr3-v1 (queued, not yet run)

Graded from that job's per-star output (the strongest TESS period `vpt_pf.py` 0.1.0 reports for the
star). "Matches" means within 0.5% of the listed period or of the listed alternatives. If the job
reports no period for a star, that prediction is ungradable, not failed.

| ID | star | TESS period matches | probability |
|---|---|---|---|
| N1 | TIC 400170926 | 5.8959 d or 2.9480 d (half, if the two eclipses look alike) | 75% |
| N2 | TIC 470993218 | 7.0623 d or 3.5311 d | 30% |
| N3 | TOI-1991 | 6.6571 d or 3.3285 d | 85% |
| N4 | TIC 207399049 | 0.4602, 0.9205 or 0.2301 d | 25% |

If N1 holds, the next step is an eclipse fit (depths, durations, secondary phase) to confirm the
inclination and give the system's radii; it would then be reported to VSX once an AAVSO login exists.

## 6. Amendment 2 for Gaia DR4 day: the NSS screen (step g2c)

Fixed before DR4 (2 December 2026). It adds a screen; no registered test, label or threshold of
step g or amendment 1 changes.

- After step g's RVS screen (g2), join every DR4 `vari_planetary_transit` candidate with DR4
  `nss_two_body_orbit` (and `binary_masses` if DR4 has it). Read DR4's TAP_SCHEMA first; if the
  orbit table or its period, K1 and K2 columns are renamed, map them and record the mapping before
  any label is set.
- Labels per star: **NSS_STELLAR** if a double-lined solution (any type whose name contains "SB2"),
  or a spectroscopic solution whose minimum companion mass (mass function, sin i = 1, m1 = Gaia's
  m1 or FLAME mass, else 1.0 M_sun) is at least 0.08 M_sun; **NSS_SUBSTELLAR** if a spectroscopic
  solution with minimum mass below 0.08 M_sun (reported as a lead, never a veto); **NSS_NO_K**
  for solutions without a primary velocity amplitude, i.e. astrometric or photometric only
  (reported, not used); **NSS_NONE** otherwise. When a star has several solutions the most severe
  label wins. For every orbit we report the ratio of the orbit period to the transit period.
- Applied to the seven DR3 rows, the rule gives NSS_STELLAR for TIC 400170926, TIC 470993218 and
  TOI-1991 (m1 defaulted to 1.0 M_sun: 0.089 M_sun), NSS_SUBSTELLAR for WASP-18 (0.010 M_sun) and
  TIC 207399049 (0.075 M_sun, just under the line; a minimum mass, and a doubtful solution), and
  NSS_NO_K for HATS-26 and WASP-2.
- **G2c** = step g's planet-like list after both the RVS screen (G2b) and removal of NSS_STELLAR.
  Step g3 (period-free follow-up) runs on G2c instead of G2b.
- DR4 predictions: among DR4 NEW candidates with a spectroscopic orbit, at least 70% are
  NSS_STELLAR (75%); the NSS screen removes at least one NEW candidate that the RVS screen left
  RV_UNTESTED (60%); at least one NEW candidate is NSS_SUBSTELLAR with an orbit period within 1% of
  its transit period or of the TESS period (15%).
- Code: `vpt_nss.py` 0.1.0 (this commit) holds the labels and the mass function; its tests use the
  seven DR3 rows above (`data/vpt-nss-dr3/vpt_nss_dr3.csv`).

## Limits

Exploratory; the stars' categories were known. Seven rows, transcribed by hand from the archive's
responses (the queries are listed for anyone to re-run). Minimum masses assume sin i = 1 and the
primary masses listed. Gaia's DR3 orbit catalogue contains some spurious solutions (ESA's DR3 known
issues); the TIC 400170926 solution is double-lined with significance 180, but we have not checked
its flags field bit by bit. That TIC 400170926 eclipses is an inference from its orbit and from
Gaia's and TESS's dips; it is not yet shown by an eclipse fit. Nothing here is a catalogue
submission.

## References

- Gaia Collaboration, Arenou et al. 2023, A&A 674, A34 (DR3 non-single stars).
- Panahi et al. 2022, A&A 663, A101 (Gaia DR3 transit candidates).
- Katz et al. 2023, A&A 674, A5 (RVS variability criterion).
- Tarrants & Mendes 2023, arXiv:2310.12380 (Gaia DR3 NSS SB1 orbits against TOI and K2 candidates).
