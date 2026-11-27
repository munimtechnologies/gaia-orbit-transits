# Tier-2 vetting of the Gaia DR3 SB1 eclipse flags, two new candidates, and pre-registered TESS predictions

MV2, Munim, Inc. (mv2@munimtech.com), 27 November 2026, about 12:00-13:00 UTC. Made with AI agents
working in his name; not yet checked by a human expert. Text CC BY 4.0, code Apache-2.0.

**Status: pre-registration.** Everything below the line "Frozen predictions" was written before any
TESS light curve of TYC 3614-1907-1, BD+12 3880 or HD 76320 was downloaded or looked at. The job that
grades it is `sb1-tier2-tess-v1` (code `runbook/sb1-tier2-tess-v1/`: `sb1_tess_fold.py` 0.1.0,
`cand_vet.py` 0.3.0, `targets.json`).

## Where this comes from

The blind search `g8-dr3-sb1-v1` (findings/2026-11-26-g8-dr3-sb1-results.md) flagged 111 Gaia DR3
single-lined binaries (SB1, P = 0.4-15 d) with faint Gaia G epochs at Gaia's own conjunctions that
Gaia's eclipsing-binary tables do not contain. 46 were vetted by hand on 26 Nov (the 10 deepest and
all 36 deeper than 0.10 mag without a Gaia variability class). The other 65 were not.

This run vetted the **bright tier-2 flags** (G < 10.5, any depth, any Gaia class except LPV), the
stars ground-based archives can check. Data: `data/g8-dr3-sb1-v1/g8_dr3_sb1_new_candidates.csv`.

## Tier-2 vetting (VSX API by coordinates; VizieR CfA cones of TESS Ten Thousand tables 2-4, ASAS-SN
II/366, IJspeert et al. 2024 and 2021, Prsa et al. 2022, GCVS/NSV/EVS, ATLAS J/AJ/156/241, ZTF
J/ApJS/249/18; SIMBAD; web search)

| Gaia DR3 | name | G | Gaia P (d) | Gaia class | depth (mag) | verdict |
|---|---|---|---|---|---|---|
| 544437922821310976 | PMAK V74 | 8.62 | 0.9125539 | none | 0.096 | known: VSX EA+ROT, P 0.912552 d |
| 6630002824267447296 | V0405 Pav | 9.03 | 5.6479076 | ACV | 0.071 | known: VSX EA, P 5.64797 d |
| 5763596973065060096 | HD 76320 (A2m) | 8.98 | 7.7729441 | ACV | 0.066 | known: VSX EA, P 7.77292 d |
| 5537385924678035840 | HD 65356 (A3IV) | 9.13 | 9.4098719 | ACV | 0.045 | known: IJspeert et al. 2024 OBAF EB candidate (score 4) |
| 4318964656978448768 | BD+12 3880 | 8.92 | 1.9958003 | none | 0.060 | **no eclipsing listing**: VSX only Gaia "VAR", P 0.99786 d (= P_orb/2); IJspeert 2024 parent sample only (ECLIPSR score 0, "sinusoid-like") |
| 2000830001125603968 | TYC 3614-1907-1 | 9.94 | 3.3597641 | none | 0.094 | **no listing**: VSX only Gaia "VAR" with a spurious 0.0249 d period; no rows in any catalogue above |

Positive controls: the same VizieR query returned IJspeert rows for BD+12 3880 and HD 65356; VSX
returned the three known EAs.

**Lesson for the Gaia DR4 rule:** all three bright flags that Gaia classes as ACV (alpha2 CVn
rotational variables) are eclipsing binaries (two in VSX, one in IJspeert 2024). Gaia's ACV class
hides eclipsing binaries; the DR4 rule must drop only *pulsator* classes (LPV, RR, DSCT|GDOR|SXPHE,
CEP), never ACV. Two of the five bright tier-2 stars with a spectral type are Am/A stars (HD 76320
is A2m), like HD 125386A.

Not new, therefore, and not claimed: PMAK V74, V0405 Pav, HD 76320, HD 65356.

## Candidate 1: TYC 3614-1907-1 (Gaia DR3 2000830001125603968, TIC 430687563)

RA 333.69399, Dec +50.52870 (Lacerta; SIMBAD "Cl* NGC 7243 JFA 2530", a field star at 312 pc in
front of the cluster), G 9.94, BP-RP 0.81, TIC Teff 6084 K, R 2.70 Rsun, M 1.14 Msun (a slightly
evolved F/G star), TESS contamination ratio 0.24. A ROSAT source, 1RXS J221446.8+503136, lies
7.7 arcsec away (inside ROSAT's position error).

Gaia DR3 SB1: P = 3.3597641 ± 0.0000302 d, K1 = 68.62 ± 0.56 km/s, e = 0.021 ± 0.007,
f(m) = 0.112 Msun. Conjunctions (Kepler's equation; Gaia time = BJD - 2455197.5):
conj0 (visible star behind) = 2191.2102, conj1 = conj0 + 1.6455 d.

Gaia's epochs (`data/g8-dr3-sb1-v1/flagged_epochs/2000830001125603968_g.csv`, 54 epochs, median
G 9.942). Every epoch that Gaia did not reject and that is at least 0.035 mag faint lies at a
conjunction:

| Gaia time | G | below median | phase from nearest conjunction |
|---|---|---|---|
| 1685.5667 | 9.988 | 0.046 | +0.011 (conj1) |
| 1858.6428 | 10.007 | 0.065 | +0.015 (conj0) |
| 2029.8441 | 9.977 | 0.035 | -0.029 (conj0) |
| 2523.7799 | 10.048 | 0.106 | -0.014 (conj0) |

(2523.7059, 9.960, is 0.036 of an orbit before conj0, on the same transit as 2523.7799. Of the
rejected epochs, 1883.8191 (9.971) is +0.018 from conj1 and 1729.6800 (9.988) is not at a
conjunction.) If faint epochs fell at random, four within ±0.04 of an orbit of either conjunction
(16% of the orbit) has probability 0.16^4 = 7e-4. A candidate, not a confirmation.

Searched 27 Nov 2026 and not found as a variable: VSX, all VizieR catalogues above, SIMBAD (4 papers:
Gaia DR3, NGC 7243 membership), web search for every identifier, and Garai et al. (2016,
arXiv:1601.04562), the NGC 7243 variable-star survey, whose 37 new eclipsing binaries lie south of
+50 deg 20 arcmin (its field is centred on the cluster, 38 arcmin south of this star). Eclipses by
Appointment was not fully searched by hand (2 MB+ files); the job's cand_vet 0.3.0 does it.

**System model** (hand-computed; i near 90 deg because it eclipses): M1 = 1.14 Msun (TIC) gives
M2 = 0.73 Msun, a K dwarf; a = 11.6 Rsun; R1/a = 0.23; eclipses need i > 73 deg. A 0.70 Rsun K dwarf
in front of a 2.70 Rsun star blocks (0.70/2.70)^2 = 6.7% (about 7.7% with limb darkening), matching
Gaia's 0.065-0.106 mag; black-body light ratio in the TESS band 0.023, so the secondary eclipse is
about 2.2% and the predicted secondary/primary ratio about 0.29. Gaia's single conj1 epoch (0.046 mag)
suggests a larger ratio (about 0.5), i.e. a hotter or larger companion; TESS decides. A tidally
synchronised 2.7 Rsun star rotates at 41 km/s, fast enough for strong activity, which fits the ROSAT
source: the candidate is a **new eclipsing, probably active (RS CVn-like) binary**.

## Candidate 2: BD+12 3880 (Gaia DR3 4318964656978448768, TIC 300539729)

RA 289.91559, Dec +12.35796 (Aquila, Galactic plane), G 8.92, BP-RP 0.62, plx 3.17 mas; TIC Teff
7930 K, R 3.42 Rsun, M 1.9 Msun (an A-type subgiant); SIMBAD: SAO 104723, component B of the visual
pair S 717 whose A component is the 5.5 mag delta Scuti star V1208 Aql, 61 arcsec away. TESS
contamination ratio 1.90 (V1208 Aql). Gaia resolves the pair.

Gaia DR3 SB1: P = 1.99580035 ± 0.0000187 d, K1 = 59.68 ± 0.42 km/s, e = 0.010 ± 0.008,
f(m) = 0.0440 Msun. conj0 = Gaia time 2190.5457, conj1 = conj0 + 0.9961 d.

Gaia's epochs (`data/g8-dr3-sb1-v1/flagged_epochs/4318964656978448768_g.csv`, 67 epochs) include a
dense 3.5-day run (Gaia time 2352.35-2355.86) that shows a smooth double wave: maxima of G about
8.88 at quadratures, minima of 8.949-8.953 at conj1 and 9.000 at conj0. Gaia's own photometric
period in VSX, 0.99786 d, is half the orbital period to 4e-5 d. **All seven unrejected epochs
fainter than 8.98 lie within 0.035 of an orbit of conj0, none at conj1:**

| Gaia time | G | phase from conj0 |
|---|---|---|
| 1801.3407 | 9.003 | -0.012 |
| 1801.4148 | 9.001 | +0.025 |
| 1971.0615 | 9.012 | +0.027 |
| 2278.4020 | 9.004 | +0.021 |
| 2354.1779 | 9.000 | -0.012 |
| 2457.9773 | 9.006 | -0.003 |
| 2458.0512 | 9.006 | +0.034 |

(two rejected epochs, 8.996 and 8.988, are at -0.046 and +0.043.) Random placement: 0.07^7 = 8e-9.

**Reading:** an ellipsoidal variable (tidally distorted star, minima at both conjunctions) with an
extra 0.05 mag dip at conj0, when the companion is in front. **System model:** M1 = 1.9 Msun,
R1 = 3.42 Rsun (TIC) give M2 = 0.66 Msun at i = 90 deg (K dwarf), a = 9.14 Rsun, R1/a = 0.374,
0.79 of the A star's Roche lobe. Predicted ellipsoidal semi-amplitude
1.52 q (R1/a)^3 sin^2 i = 2.75% (observed in Gaia: about 3.2%). Eclipses happen if i > 63.6 deg; a
central transit of a 0.65 Rsun K dwarf blocks about 4.3% (Gaia's extra dip: about 5%). The K dwarf's
light is about 0.5% in the TESS band, so no measurable secondary eclipse. Evidence against an eclipse:
IJspeert et al. (2024) ran ECLIPSR on its TESS light curve and scored it 0 (no eclipses) and
"sinusoid-like". The TESS job decides.

## Frozen predictions (graded by sb1-tier2-tess-v1; labels as coded in sb1_tess_fold.py 0.1.0)

Method, fixed: all TESS products (one per sector: SPOC 2-min, else TESS-SPOC, else QLP), folded on
Gaia's P and conjunctions; per-product offset and slope plus two orbital harmonics fitted outside
windows of half-width w around both conjunctions; eclipse depth = minus the lowest binned residual
within ±w (bins of 0.005 in phase; 0.002 for HD 76320), significance against the scatter of
out-of-window bins; timing tolerance = 3 N sigma_P + 0.10 d (N = orbits from Gaia's epoch to the
median TESS time). Depth ratios are dilution-free; absolute depths may be diluted.

**TYC 3614-1907-1** (kind "eb", w = 0.15):
- E1: primary eclipse at conj0, S/N >= 5, depth >= 2%, within tolerance. **Predicted PASS.**
- E2: secondary at conj1, S/N >= 3, within tolerance, secondary/primary 0.10-0.60. **Predicted
  PASS** (model 0.29; a ratio above 0.45 would mean the companion is hotter than a 0.73 Msun dwarf).
- E3: the deepest folded bin lies within 0.03 of a conjunction. **Predicted PASS.**

**BD+12 3880** (kind "ell", w = 0.17):
- L1: cos(4 pi phi) coefficient negative, >= 5 sigma, |a2| >= 0.1%. **Predicted PASS.**
- L2: fainter at conj0 than conj1 (cos(2 pi phi) coefficient negative, >= 3 sigma). **Predicted PASS.**
- L3: an eclipse at conj0 beyond the harmonic model (S/N >= 5, depth >= 0.25 |a2|, within
  tolerance). **Predicted ECLIPSE**, with depth/|a2| between 0.5 and 2.0 (the model gives about
  1.6 for a central transit, Gaia about 1.4). NO_ECLIPSE_DETECTED would make the conj0 excess a
  gravity-darkening/reflection asymmetry and the system a non-eclipsing ellipsoidal binary; that
  outcome is also reported.

**HD 76320** (control, VSX EA): C1, an eclipse at conj0 or conj1 on Gaia's ephemeris with S/N >= 5.
**Must PASS** or the method (and its timing tolerance) is not trusted for this run.

**cand_vet 0.3.0:** V5_tier2_listed. **Predicted []** (neither star in Eclipses by Appointment or
in IJspeert et al. 2024's eclipsing table), with V0 controls OK.

Outcome handling: a star counts as a new eclipsing binary only if its E1 (or L3 = ECLIPSE) passes,
the control passes and V5 does not list it. Either way the graded result is published with this file.
