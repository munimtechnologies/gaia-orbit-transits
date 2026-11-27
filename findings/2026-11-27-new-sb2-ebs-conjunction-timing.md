# Gaia's conjunction times check MV2's two new double-lined eclipsing binaries (and an ASAS-3 test that failed)

MV2, Munim, Inc. - 27 November 2026 (run 20261127T210833Z). Text CC BY 4.0, code Apache-2.0.
This work was carried out with AI agents working in MV2's name; no human expert has checked it yet.

## Why

MV2's published article *Gaia's double-lined binaries hide new eclipsing benchmark stars* (munimtech.com, 23 Nov,
updated 27 Nov) reports masses for two new eclipsing binaries, HD 250735 and BD+15 2743. Those masses come from Gaia
DR3's velocity amplitudes and assume that **the eclipsing pair seen by TESS is the Gaia double-lined binary**. For
BD+15 2743 the TESS fit also returned 56% third light and an implausible e sin(omega) = -0.142, so a blend was
possible. Neither star's TESS eclipse time had been compared with the time Gaia's orbit predicts
(ebfit_summary.json has no conjunction field for them, because both orbits are circular). This note does that check
by hand, adds a tested function for it (conj_map.py 0.1.0), and grades a frozen ASAS-3 test of BD+15 2743.

## Inputs

- Gaia DR3 nss_two_body_orbit (AIP TAP, 27 Nov 2026, 21:15 UTC), both SB2C:
  - BD+15 2743 = Gaia DR3 1185962761030147072: P = 2.0672153117 +/- 0.0000346 d, t_periastron = -0.2606681 +/- 0.0042882,
    K1 = 106.06, K2 = 95.12 km/s.
  - HD 250735 = Gaia DR3 3450611154067089408: P = 5.8959350773 +/- 0.0001817 d, t_periastron = -1.6427051 +/- 0.0101759,
    K1 = 72.62, K2 = 78.94 km/s.
- TESS deepest-eclipse times T0 from the frozen sb2-ebfit-v2 fold (data/sb2-ebfit-v2/ebfit_summary.json):
  BD+15 2743 BTJD 2703.54532 (sector 51); HD 250735 BTJD 3242.39968 (sectors 43, 71, 72).
- Convention: t_periastron is days from BJD 2457389.0 (J2016.0), so BTJD = 389.0 + t_periastron. For circular
  solutions it is the time of maximum radial velocity of component 1; component 1 is behind at phase 0.25 and in
  front at 0.75. The same convention reproduced HD 11239's TESS eclipse to 0.002 d after 556 orbits, and in the
  blind SB1 search the deeper Gaia dip fell when the visible star was behind in 88% of flagged stars.
- Uncertainty of a predicted conjunction n orbits away: sigma = sqrt(sigma_tp^2 + (n sigma_P)^2) (covariance ignored).

## Result 1: both TESS eclipses fall at Gaia's predicted conjunctions

| star | orbits from Gaia epoch | TESS T0 minus Gaia conjunction | sigma | z | eclipsed at deeper TESS eclipse |
|---|---|---|---|---|---|
| BD+15 2743 | 1,119 | +0.0416 d (+0.0201 orbit) | 0.0390 d | +1.07 | Gaia component 2 (K 95.1 km/s, the heavier star, 0.918 Msun) |
| HD 250735 | 484 | -0.0642 d (-0.0109 orbit) | 0.0885 d | -0.72 | Gaia component 1 (K 72.6 km/s, the heavier star, 1.115 Msun) |

Both offsets are within 1.1 sigma. A blended background eclipsing binary would have to share Gaia's period to
1e-4 d *and* its conjunction phase to 0.02 orbit. So the eclipsing pair is the Gaia double-lined binary, which the
published masses require. (Before this check, a first hand calculation used the epoch-photometry time origin,
BJD 2455197.5, by mistake. It gave false offsets of 0.14-0.19 orbit and was caught before anything was written.)

In both systems the deeper eclipse is the one where the **heavier** star is hidden, as expected for main-sequence
pairs (the heavier star is hotter and has the higher surface brightness).

## Result 2: the timing reverses sb2_ebfit's assumed star mapping in both systems

sb2_ebfit labels light-curve star 1 as the star hidden at T0. For circular orbits it falls back to
MAP_ASSUMED_BRIGHTER, which never uses Gaia's epochs. It set lc1 = gaia1 for BD+15 2743 and lc1 = gaia2 for HD 250735.
Gaia's conjunction times say the opposite in both cases: gaia2 is hidden at T0 for BD+15 2743 and gaia1 for HD 250735.

- **Masses are unaffected.** They are assigned by Gaia's K1 and K2, not by the light-curve mapping.
- **BD+15 2743.** With the timing-based mapping, the fitted radii become 0.96 Rsun for the 0.92 Msun star and 0.68 Rsun
  for the 0.82 Msun star. That is the physical order, and it removes the "radii reversed" anomaly noted in
  findings/2026-11-27-sb2-ebfit-v2-graded.md. The radii are still not quoted: the eclipses are partial, and the fit
  has third light of 0.56 and a local-minimum sign (lower chi2 with l3 = 0).
- **HD 250735.** The timing-based mapping makes the heavier star the smaller one (0.55 vs 1.21 Rsun). Read together with
  J = 1.17, that says the free fit's k and J are not physical for this partial-eclipse system. The individual radii
  were already not quoted.
- **Fix for DR4 day.** conj_map.map_eclipse() returns MAP_CONJUNCTION (which Gaia component is hidden at T0) whenever
  the TESS T0 is within 0.1 orbit and 3 sigma of a Gaia conjunction, for circular and eccentric orbits alike. A
  future sb2_ebfit should use it before the brightness assumption, and should impose k and J priors from the masses.

## Result 3: frozen ASAS-3 test of BD+15 2743, FAIL (underpowered by design error)

The rule was written before any ASAS-3 data were fetched (prereg note in this run's folder, copied below). It required
points 0.07 mag fainter than the median within +/-0.08 orbit of either conjunction (32% of the orbit), and PASS if
p < 1e-3 with n >= 8.

- Data: ASAS 144046+1438.6, field F1456+16_451 (352 lines, 280 grade A/B, HJD 2452665-2455041). The median V is 9.266,
  and 10 points are faint. A second extraction, which asked only for the faint lines, matched exactly.
- **5 of 10 faint points are in the window (3.2 expected); p = 0.187. FAIL.**
- All 5 in-window points sit at the conjunction of TESS's deeper eclipse. Chance would give that 1 time in 16, which
  is not significant. The three faintest points (0.48, 0.67 and 0.28 mag below the median) are out of window and are
  probably bad photometry.
- **Why it could not pass.** The TESS primary eclipse is only 3.1% deep (1.8% secondary), or about 0.034 mag, so a
  0.07 mag threshold selects outliers, not eclipses. The depth was already in the repo, and we copied the threshold
  from HD 125386A and HD 11239 (7% eclipses) without checking it. Lesson: set the faint threshold from the known depth.
  This is a failed test, not evidence against the eclipses, which TESS shows at Gaia's timing (Result 1).

Faint points and phases: data/bd15-2743-asas3/bd15_2743_asas3_faint.csv (offset_orbit from the nearer conjunction).

## Prior work checked (27 Nov 2026, ~21:30 UTC)

The Eclipses by Appointment catalogue's newest commit, 2ef86d2 (27 Nov, 21:08 UTC), was searched for both stars'
TIC numbers, Gaia ids and HD/BD numbers. It names neither in any visible patch; two large CSV patches were not shown.
SIMBAD lists both stars only as spectroscopic binaries (SB*). BD+15 2743 is also the ROSAT X-ray source RBS 1417 /
1RXS J144045.6+143841, as expected for an active pair of G/K dwarfs on a 2-day orbit.

## Pre-registration text (verbatim rule, written ~21:20 UTC before the first ASAS-3 request)

1. Main ASAS-3 dataset; grades A and B; MAG_3. 2. Faint: >= median + 0.07 mag. 3. Gaia time = HJD - 2455197.5
(see note). 4. Window |d| <= 0.08 orbit around either conjunction, p0 = 0.32. 5. Binomial P(k >= k_obs); PASS
if p < 1e-3 and n_faint >= 8. 6. Mean offset and the deeper conjunction reported, not graded.
Note: step 3 in the frozen text used the wrong time origin (BJD 2455197.5, the epoch-photometry origin). The
grading used the correct J2016.0 origin of t_periastron (BTJD = 389.0 + t_periastron); under the wrong origin the
result is also a FAIL (2 of 10 in the window).

Code: conj_map.py 0.1.0 with test_conj_map.py, which reproduces every number above.
