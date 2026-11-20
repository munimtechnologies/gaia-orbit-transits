# Results: SuperWASP 2006-2008 check of TYC 6340-23-1 (job tyc6340-wasp-v1)

Graded 2026-11-20 (~14:00 UTC) under `findings/2026-11-20-tyc6340-wasp-prereg.md`, which was
committed before the job ran (commit 15977ff). Code `wasp_tyc.py` 0.1.0 (commit 36c5e11, release
v0.37.0). Job ran 2026-11-20 12:22-12:24 UTC; unit tests and the self-test passed first.
Outputs: `data/tyc6340-wasp-v1/` (`wasp_tyc_summary.json`, `wasp_tyc_report.md`,
`wasp_tyc_folded.csv`, `job_summary.json`).
By MV2 of Munim, Inc.; made with AI agents working in his name; not checked by a human expert.
Text CC BY 4.0.

## Pre-registered labels

| Question | Label | Our prediction | Verdict |
|---|---|---|---|
| Detection | **WASP_INSENSITIVE** | DETECTED 80%, NOT_DETECTED 6%, INSENSITIVE 14% | most likely outcome **wrong** |
| Ephemeris | not graded (only if DETECTED) | UNIQUE 85% | - |
| Which star | not graded (only if DETECTED) | ON_TARGET 70% | - |
| WASP/TESS depth ratio (reported) | 1.09 | 0.5-0.95, 70% | **wrong** |

**Why INSENSITIVE.** The injection control failed: a 0.03 mag eclipse planted at 2.6 d was found
at the right period (2.60078 d) but with box statistic 19.68, below the largest of the 300
control periods (22.41). The target itself also failed two detection conditions: box statistic
22.21 (not above 22.41) and bootstrap depth S/N 3.79 (below 5). It passed the other two: depth
> 0 and 9 eclipse nights (≥ 5). Under the rule, nothing is learned about the detection, and the
ephemeris and blend labels are not graded. **The eclipse is not replicated by this test.** The
label B_OVERSIZED_COMPANION and every other statement about the system stay as they were.

## Why the test could not succeed (design errors, recorded so they are not repeated)

1. **The detection statistic ran on un-detrended data.** SuperWASP's night-to-night offsets
   make χ²_red = 33.6 before the per-night detrending and 2.84 after it. The box statistic
   (controls, injection and search) was computed before detrending, so every control period
   scored high (median 11.1, 95th percentile 16.3, max 22.4) and the injection could not pass.
2. **The search window was too narrow.** The box search stopped at 2.3298 d, and its best period
   (2.329795 d) sat at that edge. The later trapezoid fit, whose window reached 2.32995 d, found
   an interior best period of 2.329777 d (coarse) and 2.329743 d (fine).
3. **The bootstrap grid was too narrow.** 53% of the 150 night-bootstrap fits ended on the edge
   of their ±3e-5 d period grid, so σ_P = 2.0e-5 d and σ_depth = 0.0196 mag are not reliable.

## Reported diagnostics (not graded; they shape the next test)

- **A dip is visible in the fold.** At the fitted WASP ephemeris (P = 2.329743 d, T0 = BJD_TDB
  2453944.8073), the binned target light curve dips smoothly to 0.077 mag at phase 0 over about
  ±0.025 in phase (`wasp_tyc_folded.csv`), close to the 0.099-day TESS eclipse duration. The
  trapezoid depth is 0.074 mag; odd 0.080 and even 0.069 (consistent); no secondary
  (−0.0013 ± 0.0006 mag).
- **The same dip appears in the neighbours' light curves.** At the same ephemeris the 38″
  neighbour (V 11.25) shows 0.064 mag, the 75″ neighbour (V 12.68) 0.018 mag (fold minimum
  0.029), and the 73″ neighbour (V 13.84) 0.009 ± 0.066 mag. The 38″ star sits inside the
  target's WASP aperture, so its dip is expected if the eclipse is on the target. A dip in the 75″
  star could be light leaking from the target or a systematic common to the whole field. v1
  could not tell these apart.
- **The WASP period disagrees with Gaia's.** WASP's own period, 2.32974 d, is 5.8σ from Gaia
  DR3's 2.3289298 ± 0.00014 d (Gaia's σ only). Projected 2,944 cycles forward, the WASP
  ephemeris misses the TESS sector 92 eclipse by 0.23 in phase (σ 0.026). With a whole number
  of cycles between the WASP and TESS epochs, the mean period must be 2.33035 (2,943 cycles),
  2.32956 (2,944) or **2.32877 d (2,945)**. Only the last agrees with Gaia (z = −1.15) and with the
  one-sector TESS period (2.3287 d).
- Three readings remain open: (a) the WASP dip is the eclipse and the true period is near
  2.3297 d, so Gaia's period would be about 6σ off; (b) the WASP dip is the eclipse but its
  local period is biased by red noise, and the true period is 2.32877 d; (c) the dip is wholly
  or partly a field systematic that the fit locked onto. Per-season eclipse times (2006: −0.0004
  d; 2007: −0.0154 d; 2008: 415 points only) do not decide between them.

## Prior art

The job's two VizieR queries failed (HTTP 404), so it added no prior-art information. Separately,
on 20 Nov at about 13:40 UTC the AAVSO VSX API (cone of 0.05°, i.e. 3′) returned **no
variable** around the target. As a control, the same API call around Algol returned β Per
(EA/SD, 2.87 d). The "new eclipsing system" statement is unchanged.

## What follows

A new, separately pre-registered test (`findings/2026-11-20-tyc6340-period-prereg.md`) does
what v1 could not:
1. **ASAS-SN Sky Patrol (2013-2025)** gives an independent light curve that overlaps the TESS
   epoch. Its 8″ pixels also separate the 38″ neighbour. It decides the period branch: Gaia's
   (2.3289 d) or WASP's (2.3297 d).
2. **A common-mode test** folds 12 WASP comparison stars 4.8-7.0′ away (outside the target's
   aperture) at the v1 ephemeris. If they show the dip too, v1's dip was a systematic.

Lessons recorded: **run the detection statistic on detrended data, so the injection can pass;
make a search window wider than the prior allows, and report edge hits; never accept a
bootstrap in which most draws end on the grid edge.**
