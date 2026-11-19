# sb1_robust, amendment 2: can face-on stars explain the missing transits? (pre-registered)

2026-11-19, about 13:40 UTC. By MV2 of Munim, Inc.; made with AI agents working in his name, **not
yet checked by a human expert**. Text CC BY 4.0, code Apache-2.0. Written **before**
`inclination_floor.py` 0.1.0 has computed any population-weighted number (job gaia-incfloor-v1).
It adds an interpretation test to `findings/2026-11-18-sb1-robust-prereg.md` and amendment 1. It
does not change the primary or amendment-1 grades, which come from sb1_combine 0.1.0
(gaia-sb1comb-v2, still queued).

## Why this amendment exists

The pre-registered quantity ρ compares the substellar-size TESS transits seen with
E = Σ p_transit × sensitivity. That is the number expected if every orbit were real **and every
companion had its minimum mass m₂ sin i**. Our interim notes said that ρ_BD ≈ 0.007 means
"fewer than about 2% of the orbits describe a real brown-dwarf-mass companion". That sentence
mixes up two explanations:

1. **The orbit is wrong** (spurious period or amplitude), so nothing at that period can transit.
2. **The orbit is right, but the companion is a heavier star seen nearly face-on.** Its minimum
   mass looks like a brown dwarf, but it can never transit.

Explanation 2 is well documented. Brown dwarfs are rare in close orbits (the "brown-dwarf
desert"), so an orbit with a brown-dwarf minimum mass is often a face-on star. Examples: 9 of 12
Gaia-updated candidates moved to the stellar regime in Stevenson et al. 2023 (MNRAS 526, 5155;
arXiv:2310.02695); 5 of 12 in Kiefer et al. 2019 (arXiv:1909.00739); 13 of 20 astrometric
candidates were binaries in arXiv:2609.08590. Before this result can be called "Gaia's orbits are
wrong", it has to be shown that explanation 2 cannot account for it. That is a pure calculation
and needs no new data.

**What we already know before running it** (honest disclosure): the interim hand sums are
3 substellar-size hits in the BD class against E = 407.7, with 2,180 stars in the rate sample. A
rough hand estimate at one typical star (m₂ sin i = 0.05 M☉, m₁ = 1 M☉) gave a mean factor
c ≈ 0.57 for the central population and ≈ 0.035 for the floor population below. The job computes
c for every star, using the exact mass function.

## Method (code: `inclination_floor.py` 0.1.0, tests `test_inclination_floor.py`)

For each rate-sample star, Gaia's mass function fm = m³ sin³ i / (m₁ + m)² and the primary mass m₁
fix the minimum mass μ (sb1_transit solves it with sin i = 1). A companion of true mass m then sits
at sin i = (g(μ)/g(m))^{1/3}, where g(m) = m³/(m₁+m)². Orientations are isotropic and companion
masses follow a population density f(m). The chance of the near-edge-on configuration (the only
one that can transit, with m ≈ μ) is then c × the isotropic chance, where

c = [f(μ)/g′(μ)] / ∫_μ^{m₁} f(m) / (3 g(m) sin i cos i) dm.

If a fraction φ of the orbits are real and the rest are wrong, the expected substellar-size hits
are φ × E_pop with E_pop = Σ p_transit × sensitivity × c. So

**φ = (n_sub − fa_sub) / E_pop**, with the same Garwood 95% interval on n_sub as the primary grade.

φ is the fraction of orbits that are right (right P and K), whatever the companion turns out to
be.

### Population grid (fixed now)
- **Brown dwarfs:** F_BD per primary between 13 M_Jup and 0.075 M☉ (sb1_transit's class limits)
  at P = 1–13 d, F_BD ∈ {0.05%, 0.2%, 0.5%}. The mass distribution is flat in m or flat in log m.
  Literature: about 0.2% at P < 10 d (Csizmadia et al. 2015), 0.29 ± 0.17% at P < 400 d
  (Santerne et al. 2016), and 0.6% adopted in a Gaia detection-rate forecast (arXiv:2109.02647).
- **Stars:** dN/dq ∝ q^γ with γ ∈ {0, −1}, normalised so that q = 0.1–1 holds
  F_star ∈ {2%, 4%, 8%}, and extended with the same law down to 0.075 M☉. Moe & Di Stefano (2017)
  give roughly 2–4% for solar-type primaries at these periods, more for A/F primaries. Their
  short-period small-q slope (about +0.3) puts fewer low-mass stars in than γ = 0 or −1 does.
- **Central:** F_star 4%, F_BD 0.2%, BD flat, γ = 0.
- **Floor** (the most generous to "the orbits are real" in the grid: few brown dwarfs, many stars,
  weighted to low q): F_star 8%, F_BD 0.05%, BD flat in log m, γ = −1.
- Every choice that is not settled by data was made to favour "real": the stellar law is extended
  below q = 0.1, light from face-on stars is ignored (it would turn some into SB2s and remove
  them), and rows without a usable mass get c = 0.

## Grades (BD class, primary sample)
- **I1:** φ upper 95% bound < 0.5 under the **floor** population.
- **I2:** φ upper 95% bound < 0.5 under the **central** population.
- **Label:** MOSTLY_SPURIOUS if I1; else SPURIOUS_UNLESS_DRY_DESERT if I2; else
  FACE_ON_SUFFICIENT.
- **r\*** (reported): the largest F_BD/F_star for which "every BD-class orbit is real" survives at
  95%, for (flat, γ = 0) and (log-flat, γ = −1). Reported as "x times drier than" the central
  (0.05) and floor (0.00625) literature ratios.
- **Reproduction check RC:** n_sub, fa_sub and E_iso must equal the sb1_combine primary grade for
  the BD class (3 hits; E ≈ 407.7 in the interim hand sums). If gaia-sb1comb-v2 differs, the
  sb1comb numbers stand and this test is re-run on them.
- **Descriptive only:** all 36 grid scenarios, the VLMS class, and the amendment-1 sample (label
  reported, not graded separately).

## Predictions (written before the job)
- Label: MOSTLY_SPURIOUS 35%, SPURIOUS_UNLESS_DRY_DESERT 55%, FACE_ON_SUFFICIENT 10%.
- Central φ: below 0.05 (80%).
- Floor φ: between 0.05 and 0.5 (70%).

## How each outcome will be worded
- **MOSTLY_SPURIOUS:** "Even if brown dwarfs are as rare as any published rate allows and every
  face-on star is counted, most of Gaia DR3's brown-dwarf-mass SB1 orbits at 1–13 days must be
  wrong."
- **SPURIOUS_UNLESS_DRY_DESERT:** "Either most of these orbits are wrong, or close brown dwarfs
  are at least r\*-times rarer than published rates. Gaia DR4's orbits (2 December 2026) can tell
  which."
- **FACE_ON_SUFFICIENT:** "Face-on stars can explain the shortfall. The interim wording 'fewer
  than 2% describe a real brown-dwarf companion' stands, but it says nothing about whether the
  orbits are wrong." We then withdraw any claim that the orbits are spurious.

## Limits fixed in advance
- The population is a model, not a measurement for these primaries (F/A stars are common in the
  pool). The grid and the floor bound the plausible range; they are not a posterior.
- Planet-mass companions (< 13 M_Jup) are not in the population. Planet-class orbits are not
  graded here.
- TESS sensitivity and the transit model are the pool's own (sb1_robust 0.2.0); this amendment
  only changes how E is interpreted.
- Chunk 5 fails the per-job size check C3 (141 < 150), as already disclosed.
