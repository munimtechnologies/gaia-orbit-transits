# Pre-registration (Gaia DR4, 2 December 2026): why do so few of Gaia DR3's brown-dwarf-mass spectroscopic orbits transit?

2026-11-18. MV2 of Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0, code
Apache-2.0. Written and published **14 days before Gaia DR4 is released**, with no DR4
catalogue data seen. The analysis code (`dr4_sb1_reality.py`) will be written after the DR4
column names are known (job gaia-dr4dm-v1 or the release itself). It must follow the rules
below. Any rule that the real DR4 tables force us to change gets logged as a dated amendment
before any DR4 orbit is matched.

## The question

The DR3 TESS test (`findings/2026-11-18-sb1-transit-results.md`) covered 512 random Gaia DR3
SB1 orbits with P = 1–13 d, G ≤ 13, dwarf primaries and m₂ sin i = 5–105 M_Jup. It found the
reality fraction (real **and** truly low-mass, so it must transit at the geometric rate)
to be ρ = 0.10 (95% CI 0.03–0.22). The outlier-proof repeat (sb1_robust 0.2.0, ~2,600 stars)
is queued. A small ρ has two very different explanations:

- **(S) Spurious orbit.** The period and amplitude are noise or aliasing in Gaia's ~34-month,
  sparsely sampled RV series. There is no companion at that period.
- **(N) Real orbit, wrong nature.** A periodic RV signal is really there, but the companion
  is not a small dark body at that mass. Possible reasons: the primary mass is wrong; a
  luminous companion dilutes or blends the signal; the system is a hierarchical triple; or
  the "orbit" is coherent stellar variability (pulsation, spots).

TESS alone cannot tell (S) from (N). Gaia DR4 can. Its orbits use ~66 months of data with
about twice as many epochs, and DR4 publishes the **epoch radial velocities** (G_RVS ≤ 14,
which covers our whole G ≤ 13 sample). A spurious DR3 orbit should not reappear in DR4
at the same period and amplitude. A real one should.

## Prior art (searched 2026-11-18)

- Stevenson et al. 2023 (arXiv:2310.07936) matched DR3 SB1 brown-dwarf-mass orbits against the TOI list
  and verified three.
- arXiv:2310.12380 uses DR3 SB1 orbits to reject transit candidates.
- arXiv:2608.06453 found that about half of the high-mass-function SB1 candidates fail in
  RV follow-up, and arXiv:2609.08590 found 13 impostor binaries among 20 astrometric
  substellar candidates. Both used targeted RV follow-up of small samples.
- No published work measures the reality fraction of low-mass DR3 SB1 orbits from their
  transit rate, or splits it into (S) and (N) with the next Gaia release.

## Sample (fixed now)

**S3** is the full eligible DR3 pool of sb1_robust 0.2.0. It uses the same Gaia DR3 query
as `sb1_robust.py` 0.2.0 at this release: SB1/SB1C, P = 1–13 d, G ≤ 13, dwarf primaries,
m₂ sin i = 5–105 M_Jup, astrophysical_parameters required, no fallback. 0.1.0 chunk 1
counted 6,434 stars. DR3 → DR4 identifiers come from the official DR4 cross-match table
(the best-match row). Sources without a unique best match are UNMATCHED and reported.

## Per-orbit outcome (fixed now)

Let P₃, K₃ be the DR3 values and P₄, K₄ the DR4 values. σ is the published uncertainty.

| label | rule |
|---|---|
| CONFIRMED | DR4 has a two-body orbit with an RV component (any solution type with P and K) and \|P₄ − P₃\| ≤ max(3·√(σ₃² + σ₄²), 0.002·P₃) and \|K₄ − K₃\| ≤ max(3·√(σK₃² + σK₄²), 0.3·K₃) |
| ALIAS | DR4 orbit with a period that fails the P rule but sits within 0.5% of a 1-day, 1-year or 63-day (Gaia precession) alias of P₃, or of 2P₃ or P₃/2 |
| CHANGED | DR4 orbit that fails the rules above |
| DROPPED | no DR4 orbit, but the source has ≥ 10 DR4 RV epochs |
| UNTESTABLE | fewer than 10 DR4 RV epochs, or UNMATCHED |

**Epoch-RV check (independent of DR4's own orbit fit).** Every testable source with
published epoch RVs gets a circular fit at P₃ fixed (free γ, K, phase). The result is
EPOCH_OK if K_fit is within 3σ of K₃ and the K_fit/σ_K ≥ 5. It is EPOCH_FLAT if K_fit/σ_K < 3.
If the DR4 table outcome and the epoch check disagree, both are reported. The table
outcome is used for the hypotheses.

## Hypotheses and pass rules

f_conf = CONFIRMED / (testable). Intervals are Wilson 95%. ρ is computed with the sb1_robust
0.2.0 rules **unchanged** (median rule, controls, injections, Garwood interval), on TESS data.

| | prediction | pass rule |
|---|---|---|
| R0 | the DR4 tables carry what we need | ≥ 70% of S3 is testable (otherwise reported; hypotheses run on what is testable) |
| **D1** | many low-mass DR3 SB1 orbits do not survive DR4 | f_conf upper 95% < 0.8 |
| **D2** | amplitude decides survival | f_conf(K₃ ≥ 3 km/s) − f_conf(K₃ < 3 km/s) > 0, with 95% intervals not overlapping |
| **D3** (decisive) | among CONFIRMED orbits, the transit rate rises toward the geometric expectation | ρ_conf > ρ_all-S3-sample, with ρ_conf's lower 95% above ρ_DR3's point estimate |
| D4 | (exploratory) hot primaries fail more | f_conf(m₁ ≥ 1.5 M☉) < f_conf(m₁ < 1.2 M☉) |
| D5 | (exploratory) DR4's own low-mass RV orbits are purer than DR3's | ρ_DR4-new (new DR4 orbits, same cuts, not in DR3) > ρ_DR3 (0.2.0 result) |
| D6 | (report only) | CONFIRMED orbits with a robust PHASE_MATCH TESS transit at substellar depth go to vetting (SIMBAD, VSX, ExoFOP, Prša 2022, DR4 vari_eclipsing_binary, pixels, centroids). DR4's longer baseline should give a sharper conjunction time than DR3, making phase matching stricter. The propagated σ is used as published, and the DR3 timing-scatter factor from LEAD 2 is reported alongside. |

**Reading the result (fixed now):**
- D1 passes and D3 passes with ρ_conf consistent with 1 → explanation (S): DR3's low-mass SB1
  catalogue is mostly spurious orbits, and DR4's confirmations are a clean brown-dwarf sample.
- D1 passes and D3 fails (ρ_conf stays < 0.5) → explanation (N): the periods are real but the
  companions are not small dark bodies of that mass. The next step is spectral and SED
  checks of the CONFIRMED-but-non-transiting stars.
- D1 fails (f_conf ≥ 0.8) → most DR3 orbits are real, so the small ρ must be (N) or a fault in
  our TESS test. We would then re-check the test against known transiting brown dwarfs
  before claiming anything.

**My expectation (written before the data):** f_conf ≈ 0.3–0.6 overall, much higher for
K₃ ≥ 3 km/s than below it. ρ_conf ≈ 0.3–0.7: both explanations contribute, (S) dominates at
small K and (N) at large K with hot primaries. D5 passes.

## Execution (fixed now)

- Anonymous Gaia TAP allows 60 s and 50,000 rows per query. Use batches of ≤ 500 source_ids,
  never a bulk download onto the shared machines. Epoch RVs are fetched only for testable S3
  sources (≤ 6,434 series).
- TESS: the same light-curve sources, sectors (≤ 3 per star), injections and controls as
  sb1_robust 0.2.0. Jobs are split into 8 chunks from the start.
- No silent fallback: if a query loses columns or rows, the job stops (exit 2) and is
  re-filed.

## The "wow" if it works

The first measurement of **why** most of Gaia's brown-dwarf-mass spectroscopic orbits fail
to transit: noise orbits, or real signals from something other than a brown dwarf. It is
made on release day, from one catalogue release to the next. The CONFIRMED-and-transiting
systems are transiting brown dwarfs and very-low-mass stars with masses from Gaia. Only a few
dozen transiting brown dwarfs are known, and every new one is a benchmark for substellar
evolution models.

## Limits stated in advance

- DR4 includes the DR3 epochs, so DR4 is not fully independent of DR3. A spurious DR3
  solution can survive if the new data are uninformative. The epoch-RV check and the K split
  (D2) are there to expose that.
- The CONFIRMED rule tolerates 30% in K, so a real orbit with a biased K₃ still counts.
- ρ assumes isotropic inclinations and is diluted by unresolved light (not corrected).
- If DR4 publishes epoch RVs only for a subset, R0 may fail. The hypotheses then use the
  orbit tables alone, and the report says so.
