# Gaia's own radial velocities test Gaia's own transit candidates (DR3 pilot for DR4)

2026-11-17. MV2 of Munim, Inc.; made with AI agents. Text CC BY 4.0, code Apache-2.0.
Status: **preliminary**. The numbers below come from Gaia archive queries run by hand
today (ESA Gaia TAP, `gaiadr3`) and from ExoFOP target pages. The `gaia-transit-rv-v1`
job reproduces them with `transit_rv_screen.py` and adds SIMBAD and VSX lookups.

## Question

Gaia DR3 published 214 photometric transit candidates (`vari_planetary_transit`): 173
known planets and 41 new candidates (Panahi et al. 2022, A&A 663, A101; Eyer et al. 2023).
The new candidates were vetted with TESS full-frame images, not with Gaia's own RVS radial
velocities (we found no RV-based vetting in Panahi et al.). Gaia DR4 (2 December 2026)
publishes 1,007 transit candidates, plus epoch radial velocities and many more orbits.

What do Gaia's own RV statistics and two-body orbits say about Gaia's transit
candidates? And can Gaia alone give the mass of a transiting companion?

## Method

`transit_rv_screen.py` joins `vari_planetary_transit` to `gaia_source`,
`astrophysical_parameters` (FLAME mass), `nss_two_body_orbit` and
`nss_acceleration_astro`. It then applies fixed rules:
- **Gaia mass.** If an SB1 orbit has the transit period (ratio n:m with n, m ≤ 3, within
  0.2%), m2 sin i follows from K and the FLAME mass. It is classed as planet, brown dwarf
  or star using K ± 2σ.
- **RV scatter.** This uses bright stars only (`rv_method_used` = 1). The per-epoch
  scatter σ comes from the DR3 error model, ε = √(π/2N)·σ + 0.11 km/s. The bound is
  K ≥ √(2(σ² − σn²)), with a conservative noise ceiling σn = 7 km/s.
  - A planet of at most 13 M_Jup cannot move a ~1 M☉ star by more than about 3.3 to
    4.2 km/s at any period above 0.25 d.
  - So K above that bound excludes a planet-only system, whatever the period.
- An astrometric acceleration marks an outer companion.

## Results (DR3)

- **Overlaps.** Seven candidates have a two-body orbit and one has an acceleration
  solution. Twelve are RV-variable by the Katz et al. (2023) criteria (p ≤ 0.01,
  renormalised GoF > 4, N ≥ 10). 135 of the 214 have RV statistics.

| Gaia DR3 | name | G | P_transit (Gaia) | Gaia evidence | class |
|---|---|---|---|---|---|
| 4955371367334610048 | WASP-18 | 9.17 | 0.94148 | SB1 P = 0.941468 d, K = 1.94 ± 0.14 km/s | **Gaia-only mass: m2 sin i = 10.5 M_Jup** (literature ≈ 10.4) |
| 2881784280929695360 | KELT-1 | 10.59 | 1.2175 | RV-variable, σ = 3.3 km/s | weak (true K = 4.2 km/s, 27 M_Jup brown dwarf) |
| 4334991786994866304 | WASP-163 | 12.24 | 0.5573 (true 1.609) | RV-variable, σ = 5.7 km/s | weak (a real hot Jupiter: the noise ceiling must stay ≥ 6 km/s at G ≈ 12.2) |
| 5348534425968598400 | TOI-1991 | 10.57 | 3.746 | SB1 P = 6.6591 d (= TOI period 6.657 d), K = 9.57 km/s | TOI-1991.01 is a ≈ 0.096 M☉ star (probably already known: arXiv:2310.12380 screened TOIs this way) |
| 1748596020745038208 | WASP-2 | 11.57 | 0.668 (true 2.152) | OrbitalTargetedSearch P = 38.0 d | astrometric orbit at another period (WASP-2 has a known close faint companion) |
| 5656896924435896832 | HATS-26 | 12.83 | 3.3026 | OrbitalTargetedSearch P = 193.5 d, significance 6.7 | needs a ≈ 0.4 M☉ companion and K ≈ 10 km/s; probably spurious (not checked against the discovery RVs) |
| 3450611154067089408 | (new) | 9.33 | 0.8848 | **SB2**, P = 5.896 d, K1/K2 = 72.6/78.9 km/s | two near-equal ~1 M☉ stars: not a planet host |
| 4535127268607000320 | (new) | 12.58 | 2.598 | SB1 P = 7.062 d, K = 22.4 km/s | m2 sin i ≥ 0.283 M☉: stellar |
| 1622997463177004928 | (new; TIC 207399049) | 12.31 | 0.8514 | SB1 **P = 0.46023 d**, K = 19.7 ± 1.3 km/s, e = 0.20 | m2 sin i = 0.071 (0.061–0.081, 2σ) M☉: **at the brown-dwarf / star boundary**; vetting pre-registered |
| 4895643593611507584 | (new) | 12.32 | 1.216 | σ = 31.4 km/s | K ≥ 43 km/s: stellar (and Gaia's 11-minute duration is unphysical) |
| 2015499135507395328 | (new) | 12.54 | 5.078 | σ = 15.2 km/s | K ≥ 19 km/s |
| 4136481216073713280 | (new) | 12.56 | 1.817 | σ = 16.1 km/s | K ≥ 20 km/s |
| 2685725036820337408 | (new; TIC 248569057) | 11.87 | 1.947 | σ = 10.6 km/s; **Acceleration9**, significance 28; RUWE 3.4 | K ≥ 11 km/s, plus an outer companion: likely an F + M eclipsing pair in a triple |
| 4677436783705094912 | (new) | 12.44 | 4.583 | σ = 12.2 km/s | K ≥ 14 km/s |
| 6081267254094015616 | (new) | 12.56 | 2.024 | σ = 7.4 km/s | K ≥ 3.6 km/s vs 3.3 allowed: marginal |

- **New candidates:** the "(new)" stars have no TOI, CTOI or confirmed planet on ExoFOP. So
  they are among the 41 new candidates; this was inferred, not read from Eyer et al.'s
  Table 2.
- **Headline:** Gaia's own RVS data show that 9 of the 41 new DR3 transit candidates
  (22%) carry a companion heavier than any planet. Eight are firm and one is marginal.
  Most are probably eclipsing binaries.
- **Positive control:** Gaia alone recovers the mass of the transiting WASP-18 b
  (10.5 ± 0.8 M_Jup, against about 10.4 in the literature), at the transit period to 1 part
  in 10⁵.
- **No Gaia-only new planet in DR3:** no new candidate has a same-period orbit of
  planetary mass.

## Why it matters, and what is new

- **What is known:** using Gaia orbits to reject TESS and K2 candidates is known
  (arXiv:2310.12380, about 130 eclipsing binaries).
- **What we have not found published:** applying Gaia's RV scatter and orbits to Gaia's
  own photometric transit candidates. The same rules are ready for DR4's 1,007
  candidates on release day.
- **The DR4 "wow" this sets up:** a new transiting planet or brown dwarf whose mass,
  radius and period all come from Gaia alone. That means a Gaia transit together with a
  Gaia SB1 or astrometric orbit at the same period.

## Limits

- **The RV bound** assumes one sinusoidal signal and the DR3 bright-star error model.
  - σn = 7 km/s is chosen from WASP-163's 5.7 km/s and is conservative for bright stars
    (KELT-1's real 4.2 km/s signal is not flagged).
  - The job also reports the empirical scatter of the non-variable stars.
- **The RV variability** may come at any period. For 2685725036820337408 it could come
  from the outer companion rather than the 1.95-d signal. "Excludes a planet-only
  system" is the claim, not "the transit is an eclipsing binary".
- **Gaia's transit periods** are often aliases (WASP-2, WASP-163).
- **Prior art:** a catalogue search (SIMBAD and VSX) was not possible from here; the job
  does it.

## Data

ESA Gaia DR3 (Gaia Collaboration 2023) via the ESA Gaia Archive; ExoFOP-TESS (NExScI).
