# sb1_robust 0.2.0, chunk 0 of 8, and chunks 0 + 7 together: interim, descriptive only

2026-11-19. By MV2 of Munim, Inc.; made with AI agents working in his name, and not yet
checked by a human expert. Text and data CC BY 4.0.

**This is not the graded result.** The pre-registered grade
(`findings/2026-11-18-sb1-robust-prereg.md`, plus amendment 1 of today) combines all eight
chunks. Chunks k1–k6 are still running or waiting for compute. This note puts chunk 0's
outputs (`data/sb1rob-v1/k0/`) on record and sums chunks 0 and 7 by hand. When
`sb1_combine.py` runs (job gaia-sb1comb-v1), it recomputes everything and supersedes these
sums.

## Chunk 0 in numbers
- 641 stars processed from the pre-registered pool of 6,434 (pool reproduced exactly). 633
  have usable TESS data, and 501 are in the rate sample (injection sensitivity ≥ 0.5).
- **Robust hits: 7, against 87.8 expected if every orbit were real.** The control periods
  give 1.5 expected false hits (0.30%).
- Only 1 of the 7 is SUBSTELLAR_SIZE. The other 6 are MODULATED.
- **The old 0.1.0 rule would have flagged 46 hits in the same 501 stars.** The median rule
  removed 39 of them.
- Checks: C1 4 of 4 known companions recovered; C2 0.30% ≤ 3%; C3 501 ≥ 150; H1 holds in
  this chunk (upper bound 0.063).

## Chunks 0 and 7 summed by hand (944 stars)

| Sample | Rate sample | Expected if all real | Robust hits | Substellar-size hits | ρ, substellar size (95%) |
|---|---|---|---|---|---|
| All | 944 | 170.0 | 9 | 3 | **0.018 (0.004–0.052)** |
| Brown-dwarf mass (BD) | 679 | 127.1 | 2 | **0** | **0 (0–0.029)** |
| Very-low-mass star (VLMS) | 225 | 34.5 | 7 | 3 | 0.087 (0.018–0.254) |
| P < 5 d | 727 | 150.5 | 3 | 2 | 0.013 (0.002–0.048) |
| P ≥ 5 d | 217 | 19.5 | 6 | 1 | 0.051 (0.001–0.286) |

ρ_all = (9 − 3.0 control) / 170.0 = 0.035 (0.007–0.083). The control-hit rate is 3.0/944 =
0.32%. Of the 74 hits the 0.1.0 rule would have made, the median rule rejects 65 (88%).

**If the other six chunks look like these two, H1 and H1b both pass.** Among 679
brown-dwarf-mass DR3 SB1 orbits with sensitive TESS data, 127 transits would be expected if
every orbit were real and that light. **Not one substellar-size transit is seen.** At 95%,
fewer than 3% of these orbits are both real and brown-dwarf mass. The very-low-mass-star
orbits behave differently, at about 9% (2–25%).

**Caution, found in this chunk:** about 17.6% of each rate sample are luminous stars that
entered with a clamped radius (amendment 1). They inflate the expected count, so the ρ values
above are biased low, probably by about 20%. The A1 grade will give the corrected numbers.
The exploratory H2 (P ≥ 5 d) and H4 (primary mass) splits are not interpreted here. Four of
the five P ≥ 5 d hits in chunk 0 look like systematics near data gaps (below), and the clamped
stars all sit in the m₁ ≥ 1.5 M☉ bin.

## Every chunk-0 hit plot was opened

| Gaia DR3 | TIC | Class | What the plot shows | Status |
|---|---|---|---|---|
| 1981244984618336000 | 324597856 | SUBSTELLAR_SIZE (D1) | A clear 0.8–1% primary eclipse in all three sectors (77, 83, 84). The fold at Gaia's period also shows a ~0.5% dip at phase 0.5 and brightening near quadrature. | **Not a brown dwarf: a stellar eclipsing binary.** See below |
| 4605954852723545088 | 76420654 | MODULATED | A 0.2–0.3% dip in 3 sectors | Known: TOI-4462.01, a TFOP false positive |
| 3461121939767538688 | 134757149 | MODULATED | Deep spikes and dips at the edges of a data gap (sector 101) | Systematics |
| 3461886340866392704 | 134814843 | MODULATED | A ramp at a gap edge | Systematics |
| 4243271184138254720 | 421864836 | MODULATED | Scatter near a gap, no transit shape | Systematics |
| 5856380498760906752 | 326034580 | MODULATED | A few low points in a noisy box | Systematics |
| 5591637370276050432 | 112106746 | MODULATED | A shallow, noisy depression | Not a transit |

### TIC 324597856 (TYC 3969-1538-1, Gaia DR3 1981244984618336000)
- **Gaia DR3** gives an SB1 orbit with P = 2.0244 d, K = 13.2 km/s and e = 0.46, so
  m₂ sin i = 0.086 M☉, around a G = 11.7, M_G ≈ 3.0 primary. RUWE is 26.5.
- **TESS (QLP)** shows an eclipse ~0.8% deep at that period in all three sectors.
- **A secondary eclipse at phase 0.5, about half the primary's depth,** needs a companion
  whose surface brightness is comparable to the primary's. A 0.086 M☉ dwarf next to an F/G
  star would give a secondary far below 0.1% in the TESS band. So the companion is a luminous
  star, not a brown dwarf or late-M dwarf.
- **A secondary at phase 0.5, plus brightening near quadrature, also suggests a near-circular
  orbit.** Gaia's e = 0.46 is then most likely spurious.
- The most likely reading is a double-lined (or triple) system whose blended RVS lines make
  Gaia's K far too small. This is one of the "real signal, not a light companion" outcomes
  that the Gaia DR4 test (`findings/2026-11-18-dr4-sb1-reality-prereg.md`) is built to count.
- **Prior art, checked 2026-11-19:**
  - Not in AAVSO VSX (positional query; the service returned other stars nearby).
  - Not in Gaia DR3 vari_eclipsing_binary (the service returned rows for a positive control).
  - Not in the TESS EB catalogue (Prša et al. 2022), the Villanova TESS EB search, the ZTF
    periodic-variable catalogue (Chen et al. 2020) or the ASAS-SN variable-star catalogue.
  - No TOI or CTOI, and SIMBAD lists only the Gaia multiplicity paper.
  - **Green et al. (2023, MNRAS 522, 29) list it as a TESS ellipsoidal-variable candidate with
    P = 2.0232 d.** So the variability itself is known. We know of no earlier report of its
    eclipses.
- Status: **rejected as a brown-dwarf or VLMS transit** (D1). It is recorded as a probable new
  eclipsing binary. We do not claim it as a discovery on this evidence alone.

## What happens next
- k1–k6: grade each as it lands.
- gaia-sb1comb-v1: runs `sb1_combine.py` on every chunk in the repo, for the primary and A1
  grades.
- gaia-tic71945261-v1: the pre-registered fit of the chunk-7 survivor. It is still waiting for
  compute.
