# Results: which of the 24 strong Gaia-orbit eclipse matches are already known?

2026-11-18. MV2 of Munim, Inc.; made with AI agents. Text CC BY 4.0. Job `gaia-xmatch-v1`
(`xmatch_prior.py` 0.6.2, finished 2026-11-17 22:42 UTC), plus manual look-ups on
2026-11-18. Inputs: `findings/2026-11-17-dr3-strong-matches.csv`.

## Short answer

- **21 of the 24 strong matches** of our full Gaia DR3 search are in the 1,726-orbit
  selection of Chopard-Vilhem (2026, Zenodo doi:10.5281/zenodo.23342416, v1.5.0). Their
  source_id or TIC appears in that deposit's files, most of them in its dip lists. The
  idea and those systems are his. We do not claim them.
- Of the **3 not in that deposit**:
  - **Gaia DR3 5276085474501467648 = HD 70623 = TOI-710.01.** This is already a TESS
    Object of Interest. TFOP lists it as FP, the TESS disposition is EB, and the comment
    reads "v-shaped; period could be shorter". The TOI period is 216.246 d. Gaia's SB1
    orbit (71.931 ± 0.054 d) and three TESS eclipses spaced 72.08 d apart show that the
    true period is about **one third** of the TOI period. This is a small correction to a
    known false positive, not a discovery.
  - **Gaia DR3 4749907416157959424 = CD-48 897 = TIC 200743349.** It appears to be a
    **new, bright, nearby detached eclipsing binary**; details below.
  - **Gaia DR3 5245186002318544768 = UCAC4 117-030318 = TIC 344750398.** One 11%-deep,
    ~8-h eclipse in Sector 90 (QLP), at the Gaia-predicted conjunction (P = 193.04 d,
    e = 0.81). It is a single event in a crowded field (TIC contamination 0.41), so it is
    a candidate only.
- **P3 cannot be graded as run.** P3 predicted that more than 50% of strong matches would
  already be listed in VSX, SIMBAD or the Gaia EB table. Every SIMBAD query failed (CDS
  TAP 404), both Gaia archives refused the query (429 and 400), and the VSX column came
  back empty for every star. The job's "1 of 24 known" is therefore not a measurement.
  Against all prior work, the honest count is 22 of 24 known (21 in the deposit, plus
  TOI-710).

## CD-48 897: a new bright eclipsing binary weighed by Gaia

| | |
|---|---|
| Names | CD-48 897, TYC 8062-393-1, TIC 200743349, Gaia DR3 4749907416157959424, 2MASS J03170460-4824098 |
| Position (ICRS) | 03 17 04.61, −48 24 09.9 |
| Brightness | V = 10.59, G = 10.48, TESS mag 10.01 |
| Distance | parallax 8.29 ± 0.02 mas, so 120.6 pc |
| Primary (Gaia FLAME / GSP-Phot) | M1 ≈ 1.0 M☉, R1 ≈ 0.92 R☉, Teff 5701 K, log g 4.42, [M/H] −0.34: a Sun-like G dwarf |
| Gaia DR3 orbit | AstroSpectroSB1 (astrometry and RVS together), P = 26.5369 ± 0.0034 d, e = 0.479 ± 0.007, significance 28.6, inclination 91.9° (σ(cos i) = 0.038) |
| Companion | about 0.47 M☉ from the photocentre orbit (dark-companion approximation): an early M dwarf |
| TIC contamination | 0.021 |

**TESS eclipses.** These come from the v4 search's event list (30-min boxes; Sectors 3
and 4 SPOC, 30 and 31 TESS-SPOC, 97 QLP):

| BTJD (box centre) | cycle n | O − C (d) | box depth | box length |
|---|---|---|---|---|
| 1392.732 | 0 | 0.000 | 9.9% | 2 h |
| 2135.649 | 28 | −0.001 | 9.7% | 2 h |
| 2162.190 | 29 | +0.007 | 10.7% | 2 h |
| 3939.896 | 96 | +0.016 | 9.3% | 2 h |
| 3966.417 | 97 | +0.004 | 9.3% | 2 h |

- **Ephemeris.** O − C uses T(n) = 1392.7316 + 26.5328 n (BTJD). Five eclipses span 7
  years and 97 cycles and repeat to within 23 minutes.
- **Period.** The cycle count is fixed by the pairs within Sectors 30-31 and within Sector
  97. The photometric period (26.5328 d) agrees with Gaia's spectro-astrometric period
  (26.5369 ± 0.0034 d) at 1.2σ.
- **Shape.** The eclipses last about 2 h. A central eclipse would last about 4.6 h, so
  the eclipses are grazing. A grazing early M dwarf crossing a G dwarf blocks about 10% of
  the light, which fits the measured depth.
- **On target.** The 10% depth is five times the total TIC contamination (2.1%), so no
  catalogued neighbour can produce it. Gaia's own orbit, at the same period, belongs to
  this star.

**Not in any catalogue we could check (2026-11-18):**
- AAVSO VSX (CfA VizieR mirror, 60″; Algol control returned);
- the TESS EB catalogue of Prša et al. 2022 (VizieR J/ApJS/258/16, 60″; positive
  control returned);
- Gaia DR3 `vari_eclipsing_binary`;
- ExoFOP (no TOI or CTOI, no follow-up of any kind);
- the Chopard-Vilhem deposit;
- a web search for all three names.

SIMBAD lists it only as "SB*", from the Gaia DR3 orbit, and its other references are
RAVE survey catalogues.

**Why it is worth knowing.** It is a V = 10.6 G + M eclipsing binary at 120 pc with a
26.5-d eccentric orbit and a full Gaia astrometric orbit.
- **A long-period EBLM benchmark.** Long-period eclipsing G + M systems are the
  comparison sample for the question of whether close orbits inflate M dwarfs, because
  tides and spin-up are weak at 26 d. Our main study asks that question of 0.5-5-d
  systems.
- **An independent inclination check.** The Gaia inclination (91.9 ± 2.2°) is confirmed
  by eclipses, which makes it a data point for our Gaia inclination calibration.
- **Limits.** The eclipses are grazing, so radii from photometry alone will be
  degenerate. Spectroscopy (K1 from the ground, and perhaps the secondary's lines in
  the infrared) would make it a full benchmark.

**Predicted next primary eclipses** (from the ephemeris above; ±0.03 d, refined by the
queued job). The star is at δ = −48°, well placed from southern Africa and Australia
in the evening:
- 2026-11-19 ~21:43 UTC (BTJD 4364.405)
- 2026-12-16 ~10:31 UTC (BTJD 4390.938)
- 2027-01-11 ~23:18 UTC (BTJD 4417.471)

**Status.** These are measurements from the search's box fits, not from a dedicated
eclipse model. Before reporting to VSX, `eb_char.py` (job `gaia-ebchar-v1`) fits every
eclipse, fits the ephemeris, searches for the secondary eclipse at the Gaia-predicted
phase, and grades the criteria fixed in `findings/2026-11-18-cd-48-897-prereg.md`.
