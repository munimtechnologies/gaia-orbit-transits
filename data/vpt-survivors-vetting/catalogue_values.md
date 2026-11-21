# Catalogue values used in findings/2026-11-21-vpt-survivors-vetting.md

Queried 2026-11-21 between 23:00 and 23:15 UTC. Values transcribed from the archive responses.
CC BY 4.0. MV2 of Munim, Inc.; made with AI agents.

## Queries (ESA Gaia archive, TAP sync, https://gea.esac.esa.int/tap-server/tap/sync, ADQL, CSV)

Q1 (stars):
SELECT source_id,phot_g_mean_mag,bp_rp,parallax,parallax_error,pmra,pmdec,ruwe,radial_velocity,
radial_velocity_error,rv_amplitude_robust,rv_chisq_pvalue,rv_nb_transits,grvs_mag,teff_gspphot
FROM gaiadr3.gaia_source WHERE source_id IN (5432318139709900160,5432318135411891968,5431056347037926784)

Q2 (image/astrometry flags):
SELECT source_id,ra,dec,phot_variable_flag,non_single_star,phot_bp_rp_excess_factor,
ipd_frac_multi_peak,ipd_gof_harmonic_amplitude,visibility_periods_used,phot_g_n_obs
FROM gaiadr3.gaia_source WHERE source_id IN (5432318139709900160,5431056347037926784)

Q3 (Gaia transits): SELECT * FROM gaiadr3.vari_planetary_transit WHERE source_id IN (...same two...)

Q4 (classifier): SELECT source_id,classifier_name,best_class_name,best_class_score
FROM gaiadr3.vari_classifier_result WHERE source_id IN (...same two...)

Q5 (EB table): SELECT source_id,frequency,global_ranking,derived_primary_ecl_depth,model_type
FROM gaiadr3.vari_eclipsing_binary WHERE source_id IN (...same two...)  -> zero rows

Q6 (neighbours of TIC 44997521): SELECT source_id,phot_g_mean_mag,bp_rp,parallax,pmra,pmdec,ruwe,
DISTANCE(POINT(ra,dec),POINT(146.98835,-38.22915))*3600 AS sep FROM gaiadr3.gaia_source
WHERE 1=CONTAINS(POINT(ra,dec),CIRCLE(146.98835,-38.22915,0.0333)) AND phot_g_mean_mag<18.2 ORDER BY sep
-> 46 rows (target + 45)

Q7 (neighbours of TIC 4638108): same with centre (141.2785749,-36.5795230) and phot_g_mean_mag<17.5
-> 26 rows (target + 25)

## Q1 + Q2 values

| field | 5432318139709900160 (TIC 44997521) | 5432318135411891968 (28" neighbour) | 5431056347037926784 (TIC 4638108) |
|---|---|---|---|
| ra, dec | 146.98834516, -38.22915007 | | 141.27857493, -36.57952298 |
| G | 13.809506 | 10.591368 | 12.788467 |
| BP-RP | 1.3896008 | 0.5304413 | 0.57093334 |
| parallax (mas) | 3.5621292 ± 0.0141478 | 1.1549954 ± 0.0347758 | 1.2160974 ± 0.0107992 |
| pmra, pmdec (mas/yr) | -28.7347, 20.3342 | -15.8388, 6.1886 | -4.7894, 2.6733 |
| RUWE | 1.0553852 | 2.3370864 | 0.8817984 |
| RV (km/s) | 23.251856 ± 1.4661324 | 22.59143 ± 0.6980803 | 15.758625 ± 2.6394773 |
| rv_amplitude_robust | null | 11.423824 (p 0.4517) | null |
| rv_nb_transits | 32 | 30 | 30 |
| grvs_mag | 12.715166 | 10.109544 | 12.285032 |
| teff_gspphot | null | 7096.2 | 6910.5 |
| phot_variable_flag | VARIABLE | | VARIABLE |
| non_single_star | 0 | | 0 |
| ipd_frac_multi_peak | 0 | | 0 |
| ipd_gof_harmonic_amplitude | 0.007446906 | | 0.010253671 |
| visibility_periods_used | 27 | | 28 |
| phot_g_n_obs | 539 | | 564 |

## Q3 values (solution_id 375523436409132247)

| source_id | transit_reference_time | transit_period (d) | transit_depth (mmag) | transit_duration (d) | num_in_transit |
|---|---|---|---|---|---|
| 5432318139709900160 | 2259.3593713378414 | 3.5497497426431432 | 24.376554 | 0.08769723 | 12 |
| 5431056347037926784 | 2220.659417945117 | 2.2086268966583473 | 17.226484 | 0.07942385 | 15 |

Units confirmed in ESA's draft DR4 data model, section 18.12 (transit_depth mmag; transit_duration day).

## Q4: both sources nTransits:5+ classifier, best class EP, score 1.0. Q5: zero rows.

## Q6 nearest and brightest neighbours (TIC 44997521)

| source_id | G | BP-RP | parallax | sep (") |
|---|---|---|---|---|
| 5432318139709898240 | 17.804678 | 1.4621639 | 0.6273 | 18.81 |
| 5432318135411891968 | 10.591368 | 0.5304413 | 1.1550 | 28.25 |
| 5432318066692559488 | 17.762478 | 1.0321522 | 0.2715 | 29.10 |
| 5432318139709895424 | 17.130943 | 1.4235039 | 0.9577 | 32.10 |
No other source within 2' is brighter than G = 14.8 (5432318208429390976, G 14.81 at 95.0").

## Q7 nearest and brightest neighbours (TIC 4638108)

| source_id | G | BP-RP | parallax | sep (") |
|---|---|---|---|---|
| 5431056312678189952 | 15.190736 | 0.74815464 | 0.3042 | 24.79 |
| 5431056342737487488 | 11.965403 | 0.8661976 | 3.7518 | 25.42 |
| 5431056312672814720 | 17.315994 | 0.8795128 | 0.3421 | 26.42 |
| 5431056312678190592 | 14.806871 | 0.9681854 | 1.5555 | 29.33 |
Next brightest within 2': G 13.79 at 108.5" (5431056140879502464).

## Other sources

- ExoFOP-TESS target pages (TIC 44997521, TIC 4638108), JSON view: no TOI, no CTOI, no
  imaging/spectroscopy/time-series/comments. TIC 44997521: Tmag 13.119, Teff 4563 ± 122 K,
  R 0.79579 R_sun, d 279.564 pc, contamination ratio not given. TIC 4638108: Tmag 12.5039,
  Teff 7095 ± 140.5 K, R 1.42469 ± 0.0608 R_sun, M 1.57, d 804.757 pc, contamination ratio 1.256457.
- AAVSO VSX via VizieR B/vsx/vsx (CfA mirror), 60" cones: TIC 44997521 -> OID 4110424
  "Gaia DR3 5432318139709900160", EP, G 13.810-13.840, P 3.54975 d, Sp K. TIC 4638108 -> OID
  4031565 "Gaia DR3 5431056347037926784", EP, G 12.780-12.810, P 2.20863 d, Sp F; and OID 4031684
  "Gaia DR3 5431056342737487488", ROT, G 11.940-12.000, Sp G (the 25" neighbour).
- TESS EB catalogue J/ApJS/258/16 (CfA mirror), 120" cones: zero rows for both.
- Not reachable on 21 Nov: SIMBAD (CDS 404 / connection refused), ASAS-SN II/366 (mirror DB down).

## Derived numbers (formulas)

- Depth fraction = 1 - 10^(-mmag/2500): 24.38 mmag -> 2.22%; 17.23 mmag -> 1.57%.
- TESS magnitude of the 28" star from Stassun et al. (2019) G-to-T relation: T ≈ 10.31 (the same
  relation gives 13.12 for the target, matching TIC 13.119); flux ratio 10^(0.4 x 2.81) ≈ 13.
- a = (M P^2)^(1/3) AU with M in M_sun, P in yr: TIC 44997521 (M 0.72 assumed) 0.0408 AU;
  TIC 4638108 (M 1.57) 0.0386 AU. Central duration ≈ (P/π) asin((1+k)/(a/R*)); impact parameter
  from T/T_central = sqrt((1+k)^2 - b^2)/(1+k).
- RV semi-amplitude K = 28.43 m/s (m_c/M_Jup) ((M*+m_c)/M_sun)^(-2/3) (P/yr)^(-1/3).
