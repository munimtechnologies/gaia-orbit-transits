# Pre-registration: does SuperWASP (2006-2008) see TYC 6340-23-1's eclipse, and on which star?

Written 2026-11-20 (about 10:00 UTC), **before any SuperWASP data for this star was analysed**.
By MV2 of Munim, Inc.; made with AI agents working in his name, not checked by a human expert.
Text CC BY 4.0, code Apache-2.0. Code: `wasp_tyc.py` 0.1.0 with tests `test_wasp_tyc.py`.

## Why

TYC 6340-23-1 (TIC 71945261, Gaia DR3 6853008555751131648; V = 10.7) is the new 2.3287-day
eclipsing system from our Gaia SB1 search (`findings/2026-11-19-tic71945261-fit-results.md`).
Its companion appears to be 1.9 times the expected size for Gaia's 0.097 M_sun. Everything so far
rests on **one TESS sector** (S92, 2025) and one Gaia orbit. Three things are still unchecked:

1. Has any **independent instrument** ever seen the eclipse?
2. The period is known only to ±0.00014 d (Gaia), so the eclipse times cannot be predicted
   a few years ahead. Spectroscopists and Gaia DR4 analyses need a precise ephemeris.
3. Is the eclipse on the target at all? The SuperWASP DR1 archive lists a **V ≈ 11.25 star 38″
   away** (1SWASP J202215.96-220458.7), less than two TESS pixels from the target. Two fainter
   stars lie 73-75″ away.

The public SuperWASP DR1 archive (Butters et al. 2010; served by CERIT-SC, wasp.cerit-sc.cz) has
a light curve of the target, **1SWASP J202214.65-220425.1** (9,236 points, May 2006 to May 2008),
and separate light curves of the three neighbours. Before writing this note we looked only at the
archive's search page (object names, magnitudes, point counts, dates) and the first five rows of
the target CSV, to learn the format. No folding, periodogram or plot was made.

## Rule (fixed now; `wasp_tyc.py` 0.1.0 implements it)

Data: the CSV light curves from `https://wasp.cerit-sc.cz/csv?object=<1SWASP name>` for the
target and the three neighbours. Times are HJD (UTC); we add 65.184 s to put them on the TDB
scale of the TESS epoch (the < 4 s HJD-BJD difference is ignored).

Cleaning: keep points with 0 < error ≤ 0.1 mag. Within each (camera, season) group of at least
20 points (seasons are split at gaps > 60 d), subtract the median and drop points brighter than
−5σ_MAD or fainter than max(10σ_MAD, 0.3 mag). Weights are 1/max(error, 0.005)², rescaled so
χ²_red = 1.

Eclipse template: a trapezoid fixed from the TESS fit geometry (k 0.243, b 0.675, a/R 7.87): total
duration T14 = 0.0990 d and flat part T23 = 0.0324 d. Depth is fitted linearly, in magnitudes.

1. **Controls first.** 300 control periods are drawn uniformly in 1.5-3.5 d (seed 20261120). We
   exclude periods within 0.3% of P_Gaia × {1/2, 2/3, 3/4, 1, 4/3, 3/2}, within 0.02 d of a
   multiple of half a day, and within 0.01 d of 2.6 d. The box statistic (a box 0.06 d wide,
   1,000 phase bins, depth/σ) is taken at its maximum over phase for each control period.
   `control_max` is the largest of these.
2. **Injection control.** A 0.03 mag trapezoid eclipse at P = 2.6 d is added to the real target
   light curve and searched for over 2.6 ± 0.0009 d. It **passes** if the found period is within
   1e-4 d of 2.6 and its box statistic is ≥ 7 and above `control_max`.
3. **Search.** Box statistic over P = 2.3280 to 2.3298 d (Gaia's period ± about 6σ) in steps of
   5e-6 d.
4. **Fit.** A trapezoid grid fit (P ± 1.5e-4, T0 ± 0.03 d) is followed by per-night detrending:
   each (camera, night) has the median of its points more than 0.1 d from a predicted eclipse
   subtracted, if there are at least 10 such points. A finer fit then sets the WASP ephemeris
   (P_W, T_W), with T_W at the cycle nearest the weighted centre of the in-eclipse data.
5. **Errors.** A bootstrap over observing nights (150 draws; grid P ± 3e-5, T0 ± 0.006 d) gives
   σ(P_W), σ(T_W) and σ(depth). The depth's S/N is depth/σ_boot. An eclipse night is a night
   with a point at template value > 0.5.

### Label 1: detection

- **WASP_DETECTED** if depth > 0, box statistic ≥ 7, box statistic > `control_max`, depth S/N ≥
  5 and at least 5 eclipse nights.
- Otherwise **WASP_NOT_DETECTED** if the injection control passed, else **WASP_INSENSITIVE**.

### Label 2: ephemeris (graded only if WASP_DETECTED)

With the TESS primary eclipse T_TESS = BJD_TDB 2460803.0299 and a fixed, conservative σ = 0.001 d,
let x = (T_TESS − T_W)/P_W, N = round(x), and σ_x = √(σ_TESS² + σ(T_W)² + (N·σ(P_W))²)/P_W.
- **EPHEMERIS_UNIQUE** if σ_x < 0.1 and |x − N| ≤ 3σ_x. The combined period is then
  P = (T_TESS − T_W)/N with σ = √(σ_TESS² + σ(T_W)²)/N.
- **EPHEMERIS_AMBIGUOUS** if σ_x ≥ 0.1. **EPHEMERIS_INCONSISTENT** if σ_x < 0.1 and |x − N| > 3σ_x.
  **EPHEMERIS_UNTESTABLE** if the errors are not finite.
- Reported: whether the combined period agrees with Gaia's 2.3289298 ± 0.00014 d (|z| ≤ 3).

### Label 3: which star (graded only if WASP_DETECTED)

Each neighbour's light curve is cleaned and detrended in the same way and fitted at the WASP
ephemeris. A paired night bootstrap (the same night draws for target and neighbour) gives
σ_diff for the depth difference d_target − d_neighbour, and z = (d_target − d_neighbour)/σ_diff.
The aperture centred on the eclipsing star always shows the larger fractional depth.
- **ON_TARGET** if z > 3 for every neighbour with a usable light curve (≥ 500 points).
- **ON_NEIGHBOUR** if some z < −3 (the most negative one is named).
- **BLEND_UNRESOLVED** otherwise. **BLEND_UNTESTABLE** if no neighbour is usable.

### Reported, not graded

Odd/even depths at the WASP ephemeris, the secondary-phase depth, the WASP/TESS depth ratio
(WASP's 14″ pixels blend more light, so the ratio is expected below 1 and **says nothing about
the companion's radius**), the eclipse times per season, the phase-folded light curves, and a
VizieR position search (10″, plus the EBLM IV table at 60″) as a prior-art check.

## What each outcome means (fixed now)

- **WASP_DETECTED + EPHEMERIS_UNIQUE:** the eclipse is confirmed by an independent instrument
  17-19 years before TESS. We publish the combined ephemeris (expected σ_P around 1e-6 d, about
  100 times better than Gaia's) for spectroscopic follow-up and Gaia DR4 work. This does **not**
  confirm the companion's radius.
- **EPHEMERIS_INCONSISTENT:** the TESS eclipse does not lie on the WASP linear ephemeris. That
  points to a period change (for example a third body) or a timing error. A second TESS sector
  is needed before any claim.
- **WASP_NOT_DETECTED** (with the injection passed): a 6% eclipse missing in 2006-2008 would be
  extraordinary, for example a changing orbital inclination. It would be reported as a puzzle,
  not a discovery, until checked against other data (ASAS-SN, other WASP cameras).
- **WASP_INSENSITIVE:** nothing is learned.
- **ON_TARGET:** none of the three catalogued neighbours within 75″ is the eclipse source. A blend
  with an unresolved star closer than WASP's resolution is not excluded.
- **ON_NEIGHBOUR:** the eclipse belongs to the named neighbour. The B_OVERSIZED_COMPANION label is
  **withdrawn** in STATUS, the findings and the article, and the match with Gaia's period becomes
  a coincidence to explain.
- **BLEND_UNRESOLVED / BLEND_UNTESTABLE:** nothing changes.
- The pre-registered Gaia DR4 K test (`findings/2026-11-20-tyc6340-dr4-k-prereg.md`) keeps its
  fixed period. The phase shift a better period would make is reported, not used.

## Predictions (written now)

- Detection: WASP_DETECTED 80%, WASP_NOT_DETECTED 6%, WASP_INSENSITIVE 14%.
- Ephemeris, if detected: UNIQUE 85%, AMBIGUOUS 7%, INCONSISTENT 5%, UNTESTABLE 3%. Combined
  period consistent with Gaia's: 95%.
- Which star, if detected: ON_TARGET 70%, BLEND_UNRESOLVED 22%, ON_NEIGHBOUR 3%, UNTESTABLE 5%.
- WASP/TESS depth ratio (reported): between 0.5 and 0.95, 70%.

## Job

```json
{"name": "tyc6340-wasp-v1", "kind": "compete", "workdir": "<run>/wasp", "image": "python:3.12",
 "setup": [], "run": ["python -m unittest -v test_wasp_tyc", "python wasp_tyc.py --self-test",
 "python wasp_tyc.py --data-dir /data/wasp-tyc6340 --out-dir /out"],
 "network": true, "data_key": "gaia-orbit-tess", "cpu": 1, "memory_gb": 0.5,
 "timeout_minutes": 60}
```
Exit 2 = the archive was unreachable (re-file unchanged); 3 = self-test failed (fix, bump to
0.1.1 with a dated note, no rule change).

## Limits

WASP DR1 photometry is ground-based, with 14″ pixels and correlated noise. The night bootstrap and
the control periods are meant to handle that, but a strong systematic at exactly this period
could still pass. The depth test can only rule out the catalogued neighbours. The TESS epoch's
error is assumed (0.001 d), not measured. The result says nothing direct about the companion's
mass or radius.
