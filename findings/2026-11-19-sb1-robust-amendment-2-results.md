# sb1_robust, amendment 2 graded: face-on stars cannot explain the missing transits

2026-11-19 (graded about 23:15 UTC). By MV2 of Munim, Inc.; made with AI agents working in his
name, **not yet checked by a human expert**. Text CC BY 4.0, code Apache-2.0.

- Rules: `findings/2026-11-19-sb1-robust-amendment-2-inclination.md` (written about 13:40 UTC,
  before any population-weighted number existed).
- Code: `inclination_floor.py` 0.1.0 (tests `test_inclination_floor.py` passed as the job's first
  step), job **gaia-incfloor-v1** (19 Nov, 22:56–22:59 UTC). It read the eight public chunk
  outputs `data/sb1rob-v1/k0` … `k7`, the same inputs as the combined grade.
- Outputs, unedited: `data/incfloor-v1/incfloor_report.md`, `incfloor_summary.json`,
  `incfloor_bd_stars.csv` (per-star minimum mass, primary mass, weight and face-on factor c),
  `job_summary.json`.
- The combined grade it interprets: `findings/2026-11-19-sb1-robust-combined-results.md`.

## The question

In the combined grade, Gaia DR3's single-lined orbits whose minimum companion mass is a brown
dwarf (2,180 stars at P = 1–13 d with sensitive TESS data) should have shown **407.7** transits if
every orbit were real and every companion had its minimum mass. TESS showed **3** of substellar
size (all known TOIs), with 0.5 expected false alarms. Two explanations were open:

1. the orbits are wrong (wrong period or amplitude), or
2. the orbits are right, but most companions are heavier stars seen nearly face-on, which have
   brown-dwarf minimum masses and can never transit.

Amendment 2 computes, star by star, how much explanation 2 can absorb under a population grid
fixed in advance, and grades φ, the fraction of orbits that are right (right P and K, whatever
the companion is): φ = (n_sub − fa_sub) / E_pop.

## Reproduction check RC: pass

n_sub = 3, fa_sub = 0.50, E_iso = 407.70 for the brown-dwarf class: identical to the combined
grade. No row lacked a usable mass (skipped_no_mass = 0).

## Result (brown-dwarf class, primary sample)

| population | F_star | F_BD | BD masses | γ | mean c | E_pop | φ (95%) |
|---|---|---|---|---|---|---|---|
| isotropic, minimum mass (the combined grade) | – | – | – | – | 1 | 407.7 | 0.006 (0.0003–0.020) |
| **central** | 4% | 0.2% | flat | 0 | 0.591 | 241.1 | **0.010 (0.0005–0.034)** |
| **floor** (most generous to "real") | 8% | 0.05% | log-flat | −1 | 0.063 | 25.7 | **0.097 (0.005–0.322)** |
| most generous grid point | 8% | 0.05% | flat | −1 | 0.054 | 22.0 | 0.114 (0.005–0.376) |

- **I1** (floor upper 95% bound < 0.5): 0.322, **pass**.
- **I2** (central upper 95% bound < 0.5): 0.034, **pass**.
- **Label: MOSTLY_SPURIOUS.** All **36 of 36** grid scenarios have an upper bound below 0.5.

Worded as fixed in advance: **"Even if brown dwarfs are as rare as any published rate allows and
every face-on star is counted, most of Gaia DR3's brown-dwarf-mass SB1 orbits at 1–13 days must
be wrong."** Within the pre-registered grid, at most about a third of these orbits (95% upper
bound 0.32 at the floor, 0.38 at the most generous grid point) can be right; under the central
population, at most about 3%.

### r\*: how dry the brown-dwarf desert would have to be

The largest ratio F_BD / F_star for which "every brown-dwarf-class orbit is real" survives at 95%:

| BD mass law, stellar slope | r\* | drier than the central literature ratio (0.05) | drier than the floor ratio (0.00625) |
|---|---|---|---|
| flat, γ = 0 | 0.00058 | 87× | 11× |
| log-flat, γ = −1 | 0.0018 | 28× | 3.5× |

So for every orbit to be real, close brown dwarfs would have to be at least 3.5 times rarer,
relative to close low-mass stars, than the driest population in our grid, which already sits a
factor of about 4 below the published short-period rates (about 0.2% at P < 10 d, Csizmadia et
al. 2015; 0.29 ± 0.17% at P < 400 d, Santerne et al. 2016).

## Secondary and descriptive results (not graded)

- **Amendment-1 sample** (trusted dwarf radii only; 1,517 BD-class stars, n_sub 3, E_iso 282.6):
  central φ 0.016 (0.001–0.053), floor φ 0.187 (0.009–**0.619**). On this sample I1 fails, so its
  label is **SPURIOUS_UNLESS_DRY_DESERT**; 34 of 36 grid scenarios have an upper bound below 0.5.
  The strongest wording therefore holds for the pre-registered primary sample, not for every
  subset: on the trusted-radius subset, "most are wrong" needs the floor population to be
  slightly less extreme than our driest grid point.
- **Very-low-mass-star class** (801 stars): φ 0.065 (0.016–0.157) central, 0.041 (0.010–0.099)
  floor. This counts only substellar-size hits, so it understates the class; its all-hit ρ is
  0.105 (0.054–0.181) in the combined grade. Descriptive only.
- **Period:** in the combined grade, orbits at P ≥ 5 d do much better than those below 5 d
  (ρ_all 0.129 vs 0.015, H2). The shortfall is concentrated at the shortest periods.

## The three hits

All three substellar-size hits are TOIs: TOI-6218.01 (Gaia DR3 392652614647892736),
TOI-5882.01 (1869489729418662528) and TOI-5427.01 (3341401062125577088; a Gaia SB1 orbit already
verified with TESS by Unger et al. 2023, AJ, arXiv:2310.07936). Their floor-population face-on
factors are 0.013, 0.108 and 0.014 (`data/incfloor-v1/incfloor_bd_stars.csv`).

## Our predictions, scored

Written in amendment 2 before the job ran:
- Label: MOSTLY_SPURIOUS 35%, SPURIOUS_UNLESS_DRY_DESERT 55%, FACE_ON_SUFFICIENT 10%. **Our most
  likely outcome was wrong**: the stronger label came out.
- Central φ below 0.05 (80%): **held** (0.010).
- Floor φ between 0.05 and 0.5 (70%): **held** (0.097).
- The amendment's one-star hand estimate of the mean face-on factor was c ≈ 0.57 (central) and
  ≈ 0.035 (floor). The per-star computation gives 0.591 and 0.063: the floor was less extreme
  than the hand estimate, yet still not enough.

## Prior work and why this is new

- Unger et al. 2023 (AJ; arXiv:2310.07936) verified three Gaia DR3 SB1 orbits with transiting
  low-mass companions found by cross-matching with TOIs. They did not estimate what fraction of
  the population is real.
- El-Badry et al. 2026 (arXiv:2608.06453) followed up DR3 compact-object candidates and report
  that about half of the SB1-based candidates have spurious solutions: the opposite, high-mass-
  function end of the same catalogue.
- Astrometric brown-dwarf candidates turn out to be stellar binaries in a large share of
  follow-ups (Stevenson et al. 2023; arXiv:2609.08590: 13 of 20), which is why explanation 2 had
  to be ruled out before any claim about orbits.
- As far as we found, this is the first population-level, pre-registered estimate of how many
  Gaia DR3 brown-dwarf-mass SB1 orbits can be real, with the face-on alternative modelled
  explicitly.

## Limits

- The population grid is a model, not a measurement for these primaries; many are F and A stars,
  whose close-companion statistics are less well known. The floor bounds the plausible range; it
  is not a posterior.
- Planet-mass companions are not in the population; the planet class is not graded.
- The TESS sensitivity and hit rules are sb1_robust 0.2.0's (box-shaped injections, up to three
  sectors, no dilution correction). The median rule can reject a real grazing transit. The known
  transiting companions in every chunk were recovered (C1, 4 of 4 in each of 8 jobs).
- Combined-grade checks that failed still apply: C3 (chunk 5 has 141 < 150 stars) and the
  exploratory H4 under amendment 1.
- "Wrong" means the published period or amplitude does not describe a real companion at that
  period. It does not say why (aliasing, stellar jitter or pulsation, blends). The pre-registered
  Gaia DR4 test (`dr4_sb1_reality.py`, 2 December 2026) checks which DR3 orbits survive.
- Made with AI agents; no human expert has checked this yet.
