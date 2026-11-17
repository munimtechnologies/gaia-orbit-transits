# Which Gaia conjunction is the transit? Settled for AstroSpectroSB1 orbits

2026-11-17. By MV2 of Munim, Inc. Made with AI agents working in his name.
Text CC BY 4.0, code Apache-2.0. Every number here came from live queries on the ESA Gaia
archive (TAP, gaiadr3) on 2026-11-17. The queries are listed at the end, so anyone can
repeat them.

## The problem

An astrometric orbit fixes ω and Ω only modulo π. So for every near-edge-on Gaia orbit,
gaia-orbit-transits 0.2.0 predicted **two** conjunction times per period:
- the time when the companion passes in front of the star (a transit, or for a dark
  companion the only visible event);
- the time when it passes behind (an occultation, invisible for a brown dwarf).

That doubles the time a follow-up campaign must watch.

Gaia DR3 `AstroSpectroSB1` solutions (astrometry + single-lined radial velocities) also
publish the spectroscopic Thiele-Innes constants C = a1 sin ω sin i and H = a1 cos ω sin i
(AU). These fix ω of the primary *without* the π ambiguity. In the usual RV convention
(v = K[cos(ω+f) + e cos ω]), the primary is farthest from us, with the companion in front,
at true anomaly f = π/2 − ω.

## Test of the convention on real eclipses (Gaia-internal, independent pipelines)

The NSS pipeline's `EclipsingSpectro` solutions fit eclipses and RVs together and report
an RV-convention ω (`arg_periastron`) and `t_periastron`. Gaia's *variability* pipeline
separately measures the eclipse times (`vari_eclipsing_binary`: `reference_time` +
`derived_primary_ecl_phase` / `frequency`, in BJD − 2455197.5). All 155 EclipsingSpectro
systems are in both tables.

Result for the 19 systems read out:
- **Circular (10 of 10 checked):** the deeper eclipse falls 0.245 to 0.253 of a period
  after `t_periastron`. Gaia fixes ω = 0 here, so f = π/2 − ω predicts 0.25.
- **Eccentric (8 of 9):** the deeper eclipse falls within 0.007 in phase of f = π/2 − ω,
  for ω values of 25°, 75°, 88°, 110°, 243°, 269°, 270° and 272°.
- The ninth system (Gaia DR3 1963575553568406528) has two equally deep eclipses (0.458
  and 0.440 mag), so "primary" is arbitrary there. Its other eclipse matches to 0.0006 in
  phase.
- The opposite sign convention (f = π/2 + ω) misses by 0.13 to 0.5 in phase in all 8
  eccentric systems.

This also confirms that `t_periastron` counts days from J2016.0 (Gaia time 2191.5,
BTJD 389.0). These rows are now a unit test (`TestTransitConvention` in
test_gaia_orbits.py).

**Caveat.** This verifies the RV ω convention of Gaia's NSS pipeline. It assumes that the
AstroSpectroSB1 C/H use the same convention, which is what the Gaia DR3 documentation
states (Halbwachs et al. 2023). A known transiting companion with an AstroSpectroSB1
solution would close the loop. We have not found one yet.

## Side result: no DR3 astrometric orbit has a same-period Gaia eclipse

478 sources have both an astrometric orbit with Thiele-Innes constants and an entry in
`vari_eclipsing_binary`:
- 455 Orbital;
- 21 AstroSpectroSB1;
- 1 OrbitalTargetedSearch;
- 1 OrbitalAlternative.

In **none** of them is the eclipse period close to the astrometric period. The ratio
P_orbit / P_eclipse runs from 9.1 to 8,565, and the orbital periods run from 134 to
2,468 d. All 478 are therefore candidate hierarchical triples (an inner eclipsing pair
plus an outer astrometric orbit) or misclassified variables, never "the astrometric
companion eclipses". This matches the triple-candidate work of Czavalinga et al. 2023
(A&A 670, A75). It is not a new class of object, but it means **Gaia DR3 itself contains
no example of an astrometric companion seen to eclipse**: the transit-from-astrometry
idea has to be tested with TESS, as this project does.

## The substellar watch list, now with the transit identified

The 18 AstroSpectroSB1 rows on the 2026-11-17 watch list
(findings/2026-11-17-dr3-substellar-edge-on-watchlist.csv):
- t_RV is the transit time from ω_RV (BTJD, any epoch).
- "Transit" names which watch-list column (t_conj_a or t_conj_b) holds the transit.
- Offset is the gap between the RV and astrometric times, modulo P.
- σω is the uncertainty of ω_RV from the C/H errors.

| Gaia DR3 | P (d) | e | t_RV | transit | offset (d) | σω (rad) |
|---|---|---|---|---|---|---|
| 393581461455623296 | 73.34 | 0 (circ.) | 400.375 | **a** (400.375) | 0.0 | H > 0 at 3.5σ |
| 2960647744567925632 | 98.26 | 0.68 | 355.385 | **b** (453.034) | 0.6 | 0.17 |
| 4984264505688458112 | 196.67 | 0.45 | 638.597 | **b** (637.392) | 1.2 | 0.16 |
| 4422729073976768640 | 191.71 | 0.04 | 449.234 | none (ω_RV unconstrained) | 19.5 | 2.8 |
| 2744694491118490752 | 247.98 | 0.42 | 626.244 | **inconsistent**: keep both | 63.1 | 0.27 |
| 2214819118774573440 | 310.87 | 0.62 | 426.349 | **a** (427.580) | 1.2 | 0.14 |
| 4955501899980809088 | 337.30 | 0.55 | 800.471 | **b** (803.177) | 2.7 | 0.17 |
| 3008558963747978112 | 348.45 | 0.54 | 414.193 | **a** (416.257) | 2.1 | 0.30 |
| 4854976609869179648 | 406.50 | 0.48 | 890.437 | **a** (860.952) | 29.5 | 0.14 |
| 5981932494567274368 | 413.89 | 0.50 | 560.615 | **b** (971.368) | 3.1 | 0.23 |
| 6345830951689788672 | 484.99 | 0.35 | 754.789 | **a** (734.232) | 20.6 | 0.22 |
| 6071451157905853312 | 530.17 | 0.34 | 472.695 | **a** (473.836) | 1.1 | 0.15 |
| 1943482395189422720 | 539.94 | 0.59 | 298.805 | **b** (838.077) | 0.7 | 0.14 |
| 1390358021264524544 | 564.96 | 0.49 | 296.752 | **a** (303.508) | 6.8 | 0.15 |
| 1644373176107337344 | 591.46 | 0.54 | 394.344 | **b** (428.142) | 33.8 | 0.25 |
| 6042099591901745408 | 665.82 | 0.35 | 325.614 | **b** (−338.677) | 1.5 | 0.12 |
| 4858390078077441920 | 784.90 | 0.63 | 424.903 | **a** (430.358) | 5.5 | 0.17 |
| 4748772376561143424 | 1613.18 | 0.68 | 487.050 | **b** (−1121.277) | 4.9 | 0.08 |

Summary:
- **16 of 18** now have a single transit window.
- 13 of the 16 agree with an astrometric conjunction to within 7 d, and the other 3 to
  within 21 to 34 d. All 16 are within 0.1 P.
- One (2744694491118490752) has astrometric and spectroscopic ω values that disagree by
  about a quarter period. Both windows stay open for it, and the orbit itself deserves
  caution.
- One (4422729073976768640) has an unconstrained ω_RV and gets no label.

## The best target: Gaia DR3 393581461455623296

The orbit:
- G = 12.7, P = 73.340 ± 0.119 d, circular.
- Companion mass about 0.074 M☉ if dark, at the hydrogen-burning limit.
- cos i = −0.079 ± ~0.09.
- Transit ephemeris: T = BTJD 400.375 + n × 73.3403. The 1σ timing error grows as
  √(0.58² + (0.119 n)²) d (Tp–P correlation ignored here; the job uses Gaia's full
  correlation matrix).

How likely is a transit? Take a primary of about 0.67 M☉ and 0.65 R☉ with a companion
of about 0.1 R☉. Then:
- a ≈ 0.31 AU;
- a transit needs |cos i| < 0.011, which has about a 7% chance;
- it would last about 6 h and be about 2% deep, easy for TESS.

TESS coverage (TESScut sector list, MIT orbit times):

| Sector | Data (BTJD) | Nearest predicted transit | Outside the data by |
|---|---|---|---|
| 17 | 1764.7 – 1789.7 | 1793.8 ± 2.3 (n = 19) | 4.1 d = 1.8σ |
| 57 | 2853.4 – 2882.1 | 2893.9 ± 4.1 (n = 34) | 11.8 d = 2.9σ |
| 84 | 3584.6 – 3610.3 | 3627.3 ± 5.3 (n = 44) | 17.0 d = 3.2σ |

By chance, each predicted transit falls just after a sector ends. **TESS has therefore
not yet tested this companion for transits**; only the early tail of the S17 window is in
the data.

Next windows (1σ):
- BTJD 4360.8 ± 6.4 (centred 2026-11-16);
- BTJD 4434.1 ± 6.6 (2027-01-28);
- BTJD 4507.4 ± 6.7 (2027-04-12).

A literature search found no paper or catalogue that discusses this star (SIMBAD could not
be reached from our tools; to be checked).

## Queries (Gaia archive TAP, ADQL)

```
-- EclipsingSpectro x vari_eclipsing_binary (convention test)
SELECT n.source_id, n.period, n.eccentricity, n.arg_periastron, n.t_periastron,
  v.reference_time + v.derived_primary_ecl_phase/v.frequency - 2191.5 AS tp1,
  v.reference_time + v.derived_secondary_ecl_phase/v.frequency - 2191.5 AS tp2,
  v.derived_primary_ecl_depth AS d1, v.derived_secondary_ecl_depth AS d2
FROM gaiadr3.nss_two_body_orbit AS n
JOIN gaiadr3.vari_eclipsing_binary AS v ON v.source_id = n.source_id
WHERE n.nss_solution_type = 'EclipsingSpectro'

-- astrometric orbits x Gaia eclipsing binaries: period ratio
SELECT q.r, COUNT(*) AS n, MIN(q.p) AS pmin, MAX(q.p) AS pmax FROM
 (SELECT ROUND(n.period*v.frequency, 1) AS r, n.period AS p
  FROM gaiadr3.nss_two_body_orbit AS n
  JOIN gaiadr3.vari_eclipsing_binary AS v ON v.source_id = n.source_id
  WHERE n.a_thiele_innes IS NOT NULL) AS q GROUP BY q.r

-- RV transit times for the watch list: omega = ATAN2(c_thiele_innes, h_thiele_innes),
-- f = PI()/2 - omega, E = 2 ATAN2(SQRT(1-e) SIN(f/2), SQRT(1+e) COS(f/2)),
-- t = t_periastron + 389 + (E - e SIN(E)) / (2 PI()) * period
```
