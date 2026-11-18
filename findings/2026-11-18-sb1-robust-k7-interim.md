# sb1_robust 0.2.0, chunk 7 of 8: interim, descriptive only

2026-11-18. By MV2 of Munim, Inc.; made with AI agents working in his name, and not yet
checked by a human expert. Text and data CC BY 4.0.

**This is not the graded result.** The pre-registered grade
(`findings/2026-11-18-sb1-robust-prereg.md`) combines all eight chunks (k0–k7). Seven are still
waiting for compute. This note publishes chunk 7's outputs (`data/sb1rob-v1/k7/`) so the
numbers are on record before the others arrive. Nothing here changes the rules.

## Chunk 7 in numbers
- 573 stars processed from the pre-registered pool of 6,434 (pool reproduced exactly).
- 562 have TESS data. 443 are in the rate sample (injection sensitivity ≥ 0.5).
- **Robust hits: 2, against 82.1 expected if every orbit were real.** The control period
  gives a 0.34 % false-hit rate (1.5 expected).
- **The old (0.1.0) rule would have flagged 28 hits in the same 443 stars.** The median rule
  removed 26, exactly the outlier-driven hits that failed checks in 0.1.0.
- ρ (substellar-size hits) = **0.024, 95 % CI 0.003–0.088**.

| Class | Rate sample | Expected if all real | Hits | ρ (95 % CI) |
|---|---|---|---|---|
| Brown-dwarf mass (BD) | 322 | 61.3 | **0** | 0 (0–0.060) |
| Very-low-mass star (VLMS) | 99 | 16.1 | 2 | 0.12 (0.015–0.45) |
| P < 5 d | 353 | 73.7 | 1 | 0.014 (0.0003–0.076) |
| P ≥ 5 d | 90 | 8.4 | 1 | 0.12 (0.003–0.66) |

Checks on this chunk:
- C1 passes: 4 of 4 known transiting companions recovered (WASP-18 b, TOI-2533 b,
  TOI-1712 b, TOI-5427 b).
- C2 passes (0.34 % ≤ 3 %).
- C3 passes (443 ≥ 150).
- H1 holds in this chunk (upper bound 0.088 < 0.5).
- H2 (exploratory) is false.
- H3 cannot be tested: Gaia still times none of the hits.

**If the other chunks look like this one,** fewer than about one in ten DR3 SB1 orbits at
P = 1–13 d that imply a brown-dwarf or very-low-mass companion are both real and that light. No
brown-dwarf-mass orbit in this chunk shows a transit, where 61 were expected.

## Every hit plot was opened
| Gaia DR3 | TIC | In rate sample | What the plot shows | Status |
|---|---|---|---|---|
| 6853008555751131648 | 71945261 | yes | A clean flat-bottomed eclipse ~6 % deep and ~2.6 h long in sector 92, its only TESS sector. It sits 0.18 d from Gaia's predicted conjunction (z = −0.8). | **D1 survivor, not a TOI.** Pre-registered follow-up: `findings/2026-11-18-tic71945261-prereg.md` |
| 2160710158704303360 | 233120979 | yes | A clean 0.6–0.9 % flat-bottomed transit. RUWE 23.8. | Known: TOI-1251.01 (APC). Used as the comparison in the follow-up |
| 5963836693533111296 | 123504748 | no (sensitivity 0) | Two single dips at phases 0 and ~0.1 that do not repeat at the Gaia period. The star is a luminous red giant (M_G ≈ −3.0, BP−RP 4.6), on which a 0.04 M☉ companion could not make a percent-level transit. | Rejected. Also, the "evolved" cut should have removed this star; to be checked in the code before DR4 |
| 6437020803967617664 | 295597157 | no (sensitivity 0) | Two single dips at different phases (MODULATED class). | Rejected |

## The one survivor, TIC 71945261
The depth is the striking part. Gaia's orbit gives m₂ sin i = 0.097 M☉, so a normal companion
would be ~0.12 R☉ and make a 1.7 % eclipse. The observed 5–6 % implies R₂ ≈ 0.21–0.23 R☉. Either
Gaia's amplitude is too low (the companion is heavier), or the companion is far larger than a
star of its mass should be.
- The follow-up fit (job gaia-tic71945261-v1) will separate these using the ellipsoidal
  amplitude, the light-curve stellar density and the occultation temperature.
- The meaning of each possible outcome was written down before the job ran.
- No claim is made yet.
