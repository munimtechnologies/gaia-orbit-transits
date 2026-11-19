# sb1_robust 0.2.0: the combined, pre-registered grade (all 8 chunks)

2026-11-19 (graded about 19:50 UTC). By MV2 of Munim, Inc.; made with AI agents working in his
name, **not yet checked by a human expert**. Text CC BY 4.0, code Apache-2.0.

- Rules: `findings/2026-11-18-sb1-robust-prereg.md` (primary grade) and
  `findings/2026-11-19-sb1-robust-amendment-1.md` (secondary grade A1), both written before the
  numbers below existed.
- Code: `sb1_combine.py` 0.1.0, job **gaia-sb1comb-v2** (19 Nov, 19:04–19:08 UTC; its unit tests
  passed first). It reads the eight public chunk outputs `data/sb1rob-v1/k0` … `k7`.
- Outputs, unedited: `data/sb1comb-v2/combined_report.md`, `combined_summary.json`,
  `job_summary.json`.
- **Interpretation is limited by amendment 2** (`findings/2026-11-19-sb1-robust-amendment-2-inclination.md`).
  Its face-on calculation (job gaia-incfloor-v1) has **not run yet**. Until it is graded, nothing
  here says that Gaia's orbits are wrong.

## The question

Gaia DR3 published thousands of single-lined spectroscopic (SB1) orbits whose minimum companion
mass is a brown dwarf or a very-low-mass star, at periods of 1–13 days. If such an orbit is real
and the companion has about its minimum mass, a known fraction of them must transit, and TESS
would see it. We measured how many do.

ρ = (N_hit − N_control) / E, where E = Σ p_transit × sensitivity is the number of transits
expected **if every orbit were real and every companion had its minimum mass**. Sensitivity
comes from injecting transits into each star's own TESS light curve. N_control is the mean hit
count of two control folds at wrong periods, so it measures false alarms.

## Result

All eight chunks finished (6,434 eligible stars each, as required). **3,113 stars** had TESS
data sensitive enough to enter the rate sample.

| | rate sample | E (expected if all real) | robust hits | substellar-size hits | ρ_sub (95%) |
|---|---|---|---|---|---|
| **all** | 3,113 | 558.0 | 25 | 9 | **0.013 (0.005–0.028)** |
| brown-dwarf class | 2,180 | 407.7 | 11 | **3** | **0.006 (0.0003–0.020)** |
| very-low-mass-star class | 801 | 124.0 | 14 | 6 | 0.040 (0.010–0.097) |
| planet class | 132 | 26.3 | 0 | 0 | 0.000 (0.000–0.141) |
| A1 (trusted dwarf radii only), all | 2,225 | 391.8 | 21 | 9 | 0.019 (0.007–0.040) |
| A1, brown-dwarf class | 1,517 | 282.6 | 8 | 3 | 0.009 (0.0004–0.029) |

**In the brown-dwarf-mass class, 408 transits were expected and 3 were seen.** All three are
already TESS Objects of Interest (TOI-6218.01, TOI-5427.01, TOI-5882.01). The control folds
give 0.5 substellar-size false alarms expected in this class; the overall control-hit rate is
0.27%.

## Pass/fail, as pre-registered

| test | rule | primary | A1 |
|---|---|---|---|
| R0 | eligible = 6,434 in every job | 6,434 × 8, **pass** | pass |
| C1 | ≥ 3 of 4 known transiting companions found, per job | 4/4 in all 8, **pass** | pass |
| C2 | control-hit rate ≤ 3% | 0.27%, **pass** | 0.18%, pass |
| C3 | ≥ 150 stars in each job's rate sample | **fail**: chunk 5 has 141 | fail (chunk 5: 108) |
| **H1** | upper 95% of ρ_sub < 0.5 | 0.028, **pass** | 0.040, pass |
| **H1b** | upper 95% of ρ_sub < 0.2 | 0.028, **pass** | 0.040, pass |
| H2 (expl.) | ρ_all(P ≥ 5 d) > ρ_all(P < 5 d) | 0.129 > 0.015, **pass** | 0.201 > 0.022, pass |
| H3 | > 50% of Gaia-timed hits phase-match (≥ 3 timed) | 3 of 4, **pass** | 3 of 4, pass |
| H4 (expl.) | ρ_all(m₁ ≥ 1.5) < ρ_all(m₁ < 1.2) | 0.008 < 0.027 (pass) | **0.091 > 0.027, fail** |
| R1 (descr.) | share of 0.1.0-rule hits the median rule rejects | 87.8% (180 of 205) | 80.0% (84 of 105) |

- **C3 fails** on chunk 5 alone (141 < 150, disclosed in the interim notes). The combined
  sample is 3,113 stars, so the failure does not limit the combined grade. We report it as a
  failed check.
- **H4 is read from A1** (amendment 1, point 4), **so H4 fails.** The primary "pass" came from
  the 479 clamped-radius stars that all sat in the m₁ ≥ 1.5 bin and inflated its E, which is
  what amendment 1 predicted. Without them, the hot-primary bin has only 151 stars, 3 hits and
  no substellar-size hit (ρ_all 0.091, 95% 0.019–0.27). The exploratory idea that spurious
  orbits concentrate on hot pulsating primaries is not supported.
- **D1** (substellar-size hits not on the TOI list): TIC 324597856, TIC 135050395 and
  TIC 71945261. These were vetted in the interim notes. TIC 324597856 was rejected as a brown
  dwarf (secondary eclipse half as deep as the primary; RUWE 26.5). TIC 135050395 is the known
  EBLM J1219-39 (Triaud et al. 2013). **TIC 71945261 (TYC 6340-23-1) is new**: an eclipsing
  system whose companion is 1.9 times the main-sequence size for its Gaia mass
  (`findings/2026-11-19-tic71945261-fit-results.md`). Its youth check is re-queued (below).

## Our predictions, scored

From the pre-registration (written before any 0.2.0 data):
- C2 passes, at 1–3%: **passed, but the rate (0.27%) was below the predicted range.**
- H3 passes: **held.** H1b passes: **held.**
- ρ_sub ≈ 0.02–0.08: **wrong.** It is 0.013 (A1: 0.019), below the range.
- R1: more than half of the 0.1.0-rule hits rejected: **held** (87.8%).

From amendment 1 (written before any A1 number):
- E falls by about 15–20%: **wrong**. It fell by 29.8% (558.0 → 391.8).
- No robust substellar-size hit is removed: **held** (9 → 9).
- ρ rises by about 20%: **direction held, size wrong**. It rose by 42% (0.0134 → 0.0191).
- H1 and H1b do not change: **held.**

## What this does and does not show

**Shown:** among Gaia DR3 SB1 orbits with brown-dwarf minimum masses at 1–13 days, the number of
companions that are both real *and* close to their minimum mass is at most about 2% of what the
orbits imply (95% upper bound 0.020 in the BD class, 0.029 in A1). The very-low-mass-star class
does better, at about 4% (1–10%), and longer periods do better than shorter ones (H2).

**Not shown:** that the orbits are wrong. A right orbit whose companion is a heavier star seen
nearly face-on also gives a brown-dwarf minimum mass and no transit. Amendment 2 computes how far
that can go, under a population grid fixed in advance, and assigns one of three labels:
MOSTLY_SPURIOUS, SPURIOUS_UNLESS_DRY_DESERT or FACE_ON_SUFFICIENT. Its job (gaia-incfloor-v1)
reads the same eight chunks and is queued. **Reproduction check RC:** that job must find
n_sub = 3, fa_sub = 0.5 and E_iso = 407.70 for the BD class, the values in this grade. If it
does not, these values stand and amendment 2 is re-run on them.

## Limits

Isotropic orientations are assumed; transit shapes in the injections are boxes; dilution by
nearby stars is not corrected; up to three TESS sectors per star are used; primary radii for
about a quarter of the pool come from a main-sequence table (A1 removes the untrustworthy ones).
The median hit rule can reject a real grazing transit. The planet class is too small to grade.

## Other jobs graded in this run

- **gaia-calibdr4-reh-v2** (the Gaia DR4 inclination/timing test rehearsed on DR3, with the
  `dr4_fetch.py` 0.2.0 column fix of amendment 2): **RH1–RH4 all pass.** All 162 targets were
  confirmed through the DR2 → DR3 cross-match path (`dr3_source_id`), cos i and its error were
  reproduced (99.4% within 0.1σ; median error ratio 1.003), and the timing scatter was
  reproduced (rms z 2.62 vs 2.67 in DR3). The printed K-grades are rehearsal artefacts, not
  results. Outputs: `data/calibdr4-reh-v2/`.
- **gaia-tic71945261-followup-v1** stopped at its own built-in self-test before touching any
  data: `to_bjd()` treated an 8-digit calendar date ("20000101") as a Julian date. Fixed in
  `youth_rv_check.py` 0.1.1 (date parsing only; more self-test cases added). The pre-registered
  rules are unchanged. Re-filed as gaia-tic71945261-followup-v2, which must run before ESA's Gaia
  archive closes on 25 November.
