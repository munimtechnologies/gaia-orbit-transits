# Amendment 1 to the sb1_robust 0.2.0 pre-registration: primary radii we cannot trust

2026-11-19. MV2 of Munim, Inc.; made with AI agents working in his name, not yet checked by a
human expert. Text CC BY 4.0, code Apache-2.0 (`sb1_combine.py` 0.1.0).

**When this was written:** chunks k0 and k7 of the eight `gaia-sb1rob-k*-v1` jobs had finished,
and their outputs are public (`data/sb1rob-v1/k0/`, `data/sb1rob-v1/k7/`). Chunks k1–k6 had not
been read: k1 was running and k2–k6 were still queued. The secondary-grade numbers defined
below had **not** been computed for any chunk.

## What went wrong

While vetting chunk 7 we found a luminous red giant (Gaia DR3 5963836693533111296, M_G ≈ −3.0,
BP−RP ≈ 4.6) that had passed the "evolved" cut. We traced the cause in `sb1_transit.py` 0.1.0,
which is pinned and unchanged:

- When Gaia DR3 gives neither a FLAME nor a GSP-Phot radius, `star_physics()` takes the
  primary's radius from a main-sequence M_G table (`_MG`, `_RAD`).
- The table starts at M_G = 0.5 (r1 = 1.9 R☉), and `interp()` clamps anything brighter to that
  first value.
- 1.9 R☉ is below the R1_MAX = 2.5 R☉ cut. With no GSP-Phot log g either, the log g < 3.5 cut
  cannot fire, so luminous stars without Gaia parameters passed with r1 = 1.9 R☉ and m1 = 2.2 M☉.

**Scale:** 1,132 of the 6,434 stars in the eligible pool (17.6%) carry exactly these clamped
values. In the rate samples they are 88 of 501 (k0) and 78 of 443 (k7).

**Why it matters:** for a giant, the real radius is several times 1.9 R☉. The expected depth
(r2/r1)² is then several to tens of times too large, so injections at that depth pass, and
these stars add to E (the expected number of transits if every orbit were real). A real
companion's transit on such a star would be far too shallow to detect. ρ = (N − N_ctrl)/E is
therefore **biased low**. All clamped stars also land in the m₁ ≥ 1.5 M☉ bin, which distorts
H4.

## The rule (fixed now)

`sb1_combine.radius_flag(row)` marks a star whose primary radius cannot be trusted. Rules (a)
and (b) only apply when r1 *is* the main-sequence table value for the star's M_G (to 10⁻⁹), i.e.
Gaia gave no FLAME or GSP-Phot radius. A Gaia radius is always kept.

- (a) **clamped**: M_G ≤ 0.5, where the table clamps to 1.9 R☉.
- (b) **giant_cmd**: BP−RP > 1.0 and M_G < 3.5. That is the red-giant branch and clump, where a
  main-sequence radius does not apply. M_G is not corrected for extinction, which only makes
  a dwarf look fainter, so a reddened dwarf is not flagged.
- (c) **no_distance**: no usable parallax, and r1 is the 1.0 R☉ default.

## What changes

1. **The primary grade is unchanged.** R0, C1–C3, H1, H1b, H2–H4, R1 and D1 are computed
   exactly as pre-registered, now by `sb1_combine.py` 0.1.0. That code re-implements
   `sb1_transit.rate_summary` and is tested to reproduce each chunk's own numbers exactly.
   The primary grade is reported first.
2. **A secondary grade, A1,** applies the same pass rules after removing flagged stars from the
   rate sample. Per-chunk C3 is recounted without them.
3. **Interpretation.** Where the primary and A1 disagree on any pass/fail, we describe the
   physics with A1, because the primary includes stars whose expected transits cannot be
   detected by construction. Both are always shown side by side.
4. **H4** is read from A1 only, since the clamped stars all sit in the m₁ ≥ 1.5 bin.
5. **Gaia DR4.** The rule carries over to the DR4 work:
   - Flagged stars are excluded from the TESS grade of `dr4_sb1_reality.py`.
   - The ρ_DR3 passed to it is the A1 combined value.
   - The DR4 run of the transit-rate test (D5) applies the rule before sampling.
   - The code change is owed before 2 December. If it is not made in time, the DR4 report
     says so.

## Prediction (written before any A1 number exists)

- Removing these stars lowers E by roughly their share of the rate sample (about 15–20%) and
  removes no robust substellar-size hit. Known hits: TIC 71945261 and TOI-1251 (k7), both with
  Gaia FLAME radii, and TIC 324597856 (k0). TIC 324597856 has a table radius but sits on the
  main sequence (M_G 3.0, BP−RP 0.66).
- ρ therefore rises by about 20%. H1 and H1b do not change.
- If A1 instead flips H1b, the fault was large enough to matter and we will say so plainly.
