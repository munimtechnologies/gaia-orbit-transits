# sb1_robust 0.2.0, chunk 1 of 8, and chunks 0 + 1 + 7 together: interim, descriptive only

2026-11-19. By MV2 of Munim, Inc.; made with AI agents working in his name, and not yet
checked by a human expert. Text and data CC BY 4.0.

**This is not the graded result.** The pre-registered grade
(`findings/2026-11-18-sb1-robust-prereg.md`, plus amendment 1) combines all eight chunks.
Chunks 2–6 are still waiting for compute. This note puts chunk 1's outputs
(`data/sb1rob-v1/k1/`) on record and adds them to the hand sums of chunks 0 and 7. Those sums
are superseded when `sb1_combine.py` runs on every chunk.

## Chunk 1 in numbers
- 452 stars processed: 437 with usable TESS data, 15 without. 349 are in the rate sample
  (injection sensitivity ≥ 0.5). The pre-registered pool of 6,434 was reproduced exactly.
- **Robust hits: 4, against 64.0 expected if every orbit were real.** The control periods
  give 0.5 expected false hits (0.14%).
- 2 of the 4 hits are SUBSTELLAR_SIZE, and both match Gaia's predicted transit phase. The
  other 2 are MODULATED.
- The old 0.1.0 rule would have flagged 16 hits in the same 349 stars. The median rule removed
  12 of them.
- Checks:
  - C1: 4 of 4 known companions recovered;
  - C2: 0.14% ≤ 3%;
  - C3: 349 ≥ 150;
  - H1 holds in this chunk (upper bound 0.113).
- By the text pattern m₁ = 2.2, about 67 of the 452 processed stars carry the clamped
  fallback mass (amendment 1). `sb1_combine.py` gives the exact A1 numbers.

## Every chunk-1 hit plot was opened

| Gaia DR3 | TIC | Gaia orbit | Class | What the plot shows | Status |
|---|---|---|---|---|---|
| 6150072630171194752 | 135050395 | P 6.760 d, K 10.9 km/s, m₂ sin i 0.094 M☉ | SUBSTELLAR_SIZE, phase match (z = 1.4) | A clean, flat-bottomed 1.7% transit, ~2.5 h long, in sectors 100 and 101 (SNR 189) | **Known EBLM J1219-39** (below) |
| 392652614647892736 | 202283090 | P 5.155 d, K 9.57 km/s, m₂ sin i 0.068 M☉ | SUBSTELLAR_SIZE, phase match (z = 1.9) | A clean 1.3% transit in sectors 57 and 84 | **TOI-6218.01**, a TESS planet candidate (below) |
| 6064105595597628288 | 413108016 | P 6.913 d, m₁ clamped at 2.2 M☉ | MODULATED | A ramp into a data gap, plus spikes elsewhere in the fold | Systematics |
| 1004949715073593984 | 444859043 | P 4.529 d | MODULATED, phase mismatch (z = −6.3) | Scattered low points next to large systematics | Systematics |

### TIC 135050395 = J1219-39 = TYC 7760-484-1 (D1: known, not new)
- It is the eclipsing M-dwarf companion published by Triaud et al. (2013, A&A 549, A18, "WASP-30
  and J1219-39"), with a mass of about 0.095 M☉ on a 6.76-day orbit. **Gaia DR3's SB1 orbit
  agrees on its own:** K = 10.9 km/s gives m₂ sin i = 0.094 M☉ around a 0.87 M☉ primary.
- So the pipeline recovered a real, RV-confirmed very-low-mass companion from Gaia's orbit
  alone, at the right period and phase. **We count it as a hit that is real and that light.**
  It is not a discovery.
- ExoFOP still lists the star as CTOI 135050395.01, a "PC" (Montalto et al. 2020), and DTARPS
  (Melton et al.) lists it as candidate DTARPS-S 145. Both treat it as a ~13 R⊕ planet
  candidate. Its stellar nature has been published since 2013.

### TIC 202283090 = TOI-6218.01 (BD class)
- It is a QLP faint-star TOI from sector 57: P = 5.157 d, depth 1.66%, R ≈ 12 R⊕. TFOP has
  photometry (MuSCAT2, LCO, two small telescopes), high-resolution imaging with no companion,
  and 12 TRES spectra, but no published mass. It is still a PC on ExoFOP.
- **Gaia DR3 has an SB1 orbit at the same period:** K = 9.57 km/s, e = 0.11, which gives
  m₂ sin i = 0.068 M☉ ≈ 71 M_Jup for a 0.76 M☉ primary. TESS's transit lands at Gaia's
  predicted phase (z = 1.9). RUWE is 2.7.
- Taken at face value, this is a transiting companion at the brown-dwarf/star boundary, and
  the only BD-class substellar-size hit so far. The TFOP team's TRES spectra should already
  show the orbit. We make no claim beyond pointing out that Gaia's orbit and TESS's transit
  agree.

## Chunks 0, 1 and 7 summed by hand (1,293 stars in the rate sample)

| Sample | Rate sample | Expected if all real | Robust hits | Substellar-size hits | ρ, substellar size (95%) |
|---|---|---|---|---|---|
| All | 1,293 | 234.0 | 13 | 5 | **0.021 (0.007–0.050)** |
| Brown-dwarf mass (BD) | 926 | 174.2 | 4 | **1** | **0.006 (0.0001–0.032)** |
| Very-low-mass star (VLMS) | 311 | 48.6 | 9 | 4 | 0.082 (0.022–0.211) |
| P < 5 d | 997 | 207.5 | 4 | 2 | 0.010 (0.001–0.035) |
| P ≥ 5 d | 296 | 26.5 | 9 | 3 | 0.11 (0.02–0.33) |

Intervals are exact Poisson (Garwood) on the substellar-size count, divided by the expected
count. ρ_all = (13 − 3.5 control) / 234.0 = 0.041. Of the 90 hits the 0.1.0 rule would have
made in these three chunks, the median rule rejects 77.

**Reading so far (interim, not a grade):**
- Among 926 brown-dwarf-mass Gaia DR3 SB1 orbits with sensitive TESS data, 174 transits would
  be expected if every orbit were real and that light. **One is seen**, and that one, at
  71 M_Jup, is at the boundary.
- The very-low-mass-star orbits do better, at ~8% (2–21%), and they include a published,
  RV-confirmed EBLM (J1219-39) that the pipeline recovered blind.
- The expected counts still carry the clamped-radius bias of amendment 1, which makes ρ about
  20% too low. The A1 grade will correct that.

## What happens next
- Chunks 2–6: grade each one as it lands.
- gaia-sb1comb: once all 8 chunks are in the repo, the combined primary grade and the A1
  grade.
- gaia-tic71945261-v1: the pre-registered fit of the chunk-7 survivor. It is still waiting
  for compute.
