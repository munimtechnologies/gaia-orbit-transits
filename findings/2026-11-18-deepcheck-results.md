# Archival and Kepler test of the best Gaia-forecast targets: results

Graded 2026-11-18 (about 01:45 UTC) against `2026-11-17-deepcheck-prereg.md`, which was
written before any light curve was read. Job gaia-deepcheck-v1 (deepcheck.py 0.9.0,
68 minutes, finished 2026-11-18 01:12 UTC). MV2 of Munim, Inc.; made with AI agents.
Code Apache-2.0, text CC BY 4.0.

## Short answer

None of the 16 Gaia DR3 orbits that were most likely to show eclipses in TESS or Kepler
shows an eclipse at the predicted depth. Two cases are clean exclusions:

- **KIC 6436291 (Gaia DR3 2102618458287057920)**, an M dwarf (0.46 M☉) at 68 pc. Its
  Gaia Orbital solution (P = 165.67 ± 0.24 d) has a 0.096 M☉ companion, which should
  block about 7% of the light for 6–8 h at one of the two conjunctions. Kepler observed
  the star in long cadence for all 17 quarters (64,797 points, about nine conjunctions of
  each kind). The Kepler-only search finds nothing at the predicted depth. Injected 7%
  eclipses are recovered 100% of the time, and the eclipse probability falls from 0.25
  to 0.000 at the first conjunction and from 0.31 to 0.002 at the second.
- **Gaia DR3 577478114092768384**, an M dwarf at 23.8 pc whose OrbitalTargetedSearch
  solution (P = 19.72 d, e = 0.84) gives one of the highest eclipse probabilities in DR3
  (p = 0.97). In four TESS sectors (8, 34, 61 and 88; point scatter 0.03–0.05%), injected
  6.1% eclipses are recovered 99–100% of the time and none is seen. The posterior is
  0.003 at the first conjunction and 0.19 at the second. The 16–18% "dips" listed for
  this star are a ramp at the end of the sector-99 QLP light curve (scatter 0.73%,
  15 times worse than the other sectors), 1.7 d before the predicted window. We checked
  this by eye. It is an artefact, not an eclipse.

For a nearby M dwarf with a ~0.1 M☉ companion, any eclipse is deep and obvious. So the
misses mean that these near-edge-on Gaia DR3 inclinations (and their |cos i| errors) are
too optimistic. That is the same direction as the full DR3 search, where about 21
eclipsing systems were seen and about 74 were expected.

## Grades

| Prediction | Result | Grade |
|---|---|---|
| K1: KIC 6436291 has Kepler data; the Kepler-only search finds no candidate at either conjunction and p falls below 0.05 at both | Kepler verdict "no detection" at both conjunctions; Kepler p_post 0.000 and 0.002 | **PASS** |
| K2: at most 2 of the 16 stars get the verdict "candidate" in the combined search | 3 (2102618458287057920 t2, 1712614124767394816 t1, 1270263417048771456 t1) | **FAIL** |
| K3: at least one of 577478114092768384 / 6478328150150225664 is not seen to eclipse although covered (p_post < 0.3 at every searched conjunction) | 577478114092768384: 0.003 and 0.188 | **PASS** |
| K4: at most 3 of the 16 already listed as eclipsing binaries | the catalogue step failed (VizieR/CDS returned 404 for the Kepler EB catalogue; SIMBAD/VSX were not reached) | **NOT GRADED** |

**About K2.** It fails as written, and we count it as a failure. None of the three
"candidates" is the predicted eclipse, though. Their box depths are 0.067%, 0.081% and
0.115%, against predicted depths of 7.0%, 2.2% and 1.9%. That is 16–100 times too
shallow, so the pre-registered rule ("depth within a factor 2 of (R2/R1)²") sends none of
them to vetting. Each one is barely above its threshold: SNR 19.3 vs 18.5, 20.5 vs 19.9
and 7.0 vs 6.5. They are noise peaks of the shuffled-null kind, and the null threshold
from 30 runs is too low by a small margin. A larger null set (n_null ≥ 100) would fix
this before Gaia DR4.

## All targets

| Gaia DR3 | P (d) | pred. depth | recovery at pred. depth | p prior → post (t1; t2) | note |
|---|---|---|---|---|---|
| 2102618458287057920 (KIC 6436291) | 165.66 | 7.0% | 1.00; 1.00 | 0.248 → 0.001; 0.311 → 0.000 | Kepler Q1–Q17: excluded |
| 577478114092768384 | 19.72 | 6.1% | 1.00; 0.99 | 0.446 → 0.003; 0.972 → 0.188 | excluded (non-grazing) |
| 6478328150150225664 | 597.21 | 16.4% | 0.83; 1.00 | 0.947 → 0.754; 0.555 → 0.000 | t1 still open (one epoch) |
| 5859356292621344640 | 194.17 | 7.0% | 0.00; 0.96 | 0.155 → 0.155; 0.286 → 0.015 | |
| 1094180924823720832 | 165.83 | 1.5% | 0.88; 0.12 | 0.122 → 0.016; 0.098 → 0.087 | |
| 1905661394212548224 | 145.43 | 9.3% | 0.35; 0.74 | 0.199 → 0.139; 0.077 → 0.022 | |
| 1538418974318927488 | 199.52 | 4.3% | 0.56; 0.38 | 0.082 → 0.038; 0.147 → 0.097 | |
| 1712614124767394816 | 297.64 | 2.2% | 0.66; 0.13 | 0.041 → 0.014; 0.108 → 0.096 | K2 "candidate" at 0.08% |
| 1509074593817942400 | 541.34 | 5.5% | 0.58; 0.27 | 0.367 → 0.195; 0.194 → 0.149 | |
| 1270263417048771456 | 238.09 | 1.9% | 0.03 | 0.087 → 0.085 | K2 "candidate" at 0.12% |
| 5440672572654653696 | 135.17 | 2.8% | 0.00; 0.00 | unchanged | noisy data, uninformative |
| 1117674258493434624 | 118.37 | 3.4% | 0.00; 0.00 | unchanged | noisy data, uninformative |
| 2255242560688999040 | 712.78 | 2.3% | 0.00; 0.00 | unchanged | |
| 2981815100045965440 | 295.25 | 2.9% | 0.00; 0.00 | unchanged | |
| 1369929267019238144 | 596.27 | 17.2% | – | unchanged | no conjunction covered |
| 43574131143039104 (LHS 1610) | 10.59 | – | – | – | no light curve retrieved (see below) |

## Limits, stated plainly

- The injections use a box at the full predicted depth. A grazing eclipse would be
  shallower; for 577478114092768384, recovery at half depth is only 0.22. So the
  exclusions apply to non-grazing eclipses.
- **LHS 1610** (9.7 pc, the brown dwarf whose published joint fit says it does not
  transit) got no light curve. The likely cause is the TIC cross-match of a nearby,
  high-proper-motion star, but we have not confirmed it. It stays on the Gaia DR4 list.
- The catalogue check (K4) did not run, because the CDS VizieR/SIMBAD endpoints returned
  404. The DR4 code will use the CfA mirrors.

## What this means for Gaia DR4 (2 December 2026)

The high-confidence end of Gaia DR3's near-edge-on orbits is not reliable enough to
predict eclipses. The formal calibration of how far the probabilities are off is job
gaia-calib-v3 (`2026-11-18-calib-v3-amendment.md`). DR4 forecasts should be scaled by
that calibration, not taken at face value.

Data: `compete-results/gaia-deepcheck-v1` (deepcheck_report.md, deepcheck_results.csv,
kepler_meta.json, per-target JSON and plots); the code is deepcheck.py 0.9.0 in this
repository.
