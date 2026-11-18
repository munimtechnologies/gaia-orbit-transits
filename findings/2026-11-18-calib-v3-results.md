# Results: Gaia DR3 orbit inclinations against real TESS eclipses (job gaia-calib-v3)

2026-11-18. MV2 of Munim, Inc.; made with AI agents. Text CC BY 4.0, code Apache-2.0.
Pre-registration: `findings/2026-11-17-inclination-calibration-prereg.md`, amended in
`findings/2026-11-17-calib-v2-amendment.md` and `findings/2026-11-18-calib-v3-amendment.md`.
Code `calib_eclipse_rate.py` 0.7.0. Outputs: `data/calib-v3/`.

## The question

Gaia DR3 publishes an inclination with an error for each astrometric orbit. If an orbit is
within (R1 + R2)/a of edge-on, the stars *must* eclipse. TESS can therefore test, star by
star, whether Gaia's inclinations and their errors are right. Makarov (2025, ApJL,
arXiv:2502.20553) argued from simulations that DR3's errors on orbit size and inclination
are strongly underestimated for edge-on orbits. In his worked example the true inclination
error is 3.65° against a quoted 1.6°, 2.3 times larger. As far as we know this is the first
test of that claim with real eclipses.

## Input reproduction (gate)

The rebuilt Gaia priors reproduce the published v4 search for all 287 targets: none
missing, max |Δp_ecl| = 0.028 (limit 0.035), mean 3e-5 (limit 0.005), max relative Δm2 =
6.5e-8, max |ΔG| = 5e-7. **Pass.**

## Main result

Main sample: 162 orbits with |cos i| ≤ 0.2, G ≤ 14.5, TESS coverage of a predicted
conjunction, and an expected eclipse SNR ≥ 15. A target counts as "seen" if a clean dip
(SNR ≥ 10, ≥ 500 ppm, not at a segment edge, not seen in another star at the same time)
falls within 3σ_t + half its duration of Gaia's predicted conjunction. The false-alarm rate
at the half-way phases is 7 of 70 (10%), and it is included in the expectation.

- **Seen 50, expected 69.2** if Gaia's orbits and errors are right: ratio 0.72,
  P(N ≤ 50) = 1.4 × 10⁻⁴.
- Inflating σ(cos i) by **k = 2.31 (95%: 1.63–3.43)** fits (ΔlnL = +13.3). So does a
  fraction f = 0.40 (0.22–0.58) of wrong orbits (ΔlnL = +14.7), or radii scaled by
  s = 0.52 (0.37–0.67) (ΔlnL = +16.2).
- The deficit is in stars (44 seen vs 65.4 expected). The brown-dwarf-mass class has 6
  seen vs 3.8 expected, too few to say anything.

| # | prediction | value | pass |
|---|---|---|---|
| C1 | 0.45 ≤ N_obs/N_exp ≤ 0.85 | 0.72 | yes |
| C2 | P(N ≤ N_obs \| M0) < 0.01 | 1.4e-4 | yes |
| C3 | 1.5 ≤ k ≤ 5 and k = 1 excluded | 2.31 (1.63–3.43) | yes |
| C4 | 0.6 ≤ rms(z) ≤ 1.4 for detected eclipses | **1.62** | no |
| C5 | ratio(AstroSpectroSB1) ≥ 1.3 × ratio(other orbits) | 0.74 vs 0.69 | no |
| C6 | lnL(k) − lnL(radius scale) ≥ 2 | −2.8 | no |
| C7 | N_obs ≥ 1.3 × old strong-match count | 50 vs 19 | yes |

## Why we do not yet claim "k = 2.3"

The k we measured agrees with Makarov's simulated factor (2.3 vs 2.28). Even so, we
found a confound in our own design while grading C4, and it has to be removed first.

**C4 failed in a telling way.** Within the ±3σ_t windows, the detected dips' timing
offsets have rms z = 1.62. Only 39% lie within 1σ, where 68% were expected. A normal
distribution truncated at ±3 can only give rms 1.62 if its true width is about 3 times
Gaia's σ_t. Allowing for the ~10% of hits that are false alarms (uniform in the window),
the real eclipses need a width of about **2–2.5 × σ_t**. So Gaia DR3's propagated
conjunction times are also too optimistic, by about the same factor.

**This loses real eclipses.** If the true timing scatter is about 2.3 σ_t, then about 19% of
real eclipses fall outside a 3σ_t window and were never counted. A back-of-envelope
correction (Σp ≈ 58.9 real eclipses expected; 81% inside the windows; 10% false alarms)
gives ~59 expected against 50 seen. That is a ratio of ~0.85 and only ~1.7σ. **Most of
the 1.4 × 10⁻⁴ significance could come from the timing windows, not the inclinations.**
The k, f and s fits all ignore this loss, which is why they cannot be told apart (C6).

The result also depends on the false-alarm rate. At the lower end of its 95% interval
(4% instead of 10%), the plain deficit drops to roughly p ≈ 0.01 (normal approximation).

## What we can say now

1. Gaia DR3 orbits with |cos i| ≤ 0.2 show fewer eclipses in TESS than their published
   errors predict: 50 vs 69 (ratio 0.72).
2. Gaia's predicted conjunction times are off by more than their errors: the timing
   scatter of real eclipses is about 2–2.5 × the propagated σ_t, from 49 timed eclipses.
3. Whether the *inclination* errors are also too small, and by how much, is not yet
   decided. The re-analysis is pre-registered in
   `findings/2026-11-18-calib-window-prereg.md` (job gaia-calibw-v1). It fits the timing
   scale and k together and recounts with wider windows.

Why it matters: Gaia DR4 (2 December 2026) will publish many more orbits, including
companions of planetary and brown-dwarf mass whose true masses rest on sin i. If DR3-style
inclination and timing errors are too small by 2×, published mass ranges and
transit-time predictions built on them are too narrow by the same factor.
