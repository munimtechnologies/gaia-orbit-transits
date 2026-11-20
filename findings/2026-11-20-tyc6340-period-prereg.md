# Pre-registration: TYC 6340-23-1's period, its eclipse in ASAS-SN, and the SuperWASP dip

Written 2026-11-20 (~14:30 UTC), **before any ASAS-SN data for this star or any SuperWASP
comparison-star light curve was downloaded or looked at**. By MV2 of Munim, Inc.; made with AI
agents working in his name, not checked by a human expert. Text CC BY 4.0, code Apache-2.0.
Code: `tyc_period.py` 0.1.0 and `fetch_asassn.py` 0.1.0, tests `test_tyc_period.py`.
Job: `tyc6340-period-v1`.

## Why

TYC 6340-23-1 (TIC 71945261) is the new 2.33-day eclipsing system with an apparently oversized
companion found in our Gaia SB1 search. The SuperWASP check (`findings/2026-11-20-tyc6340-wasp-results.md`)
came out **WASP_INSENSITIVE** because of design errors. Its reported diagnostics raise three
questions that matter for the object:

1. **Which period is right?** SuperWASP's own fit gives 2.32974 d, 5.8σ from Gaia DR3's
   2.3289298 ± 0.00014 d. Joining the WASP epoch to the TESS sector 92 eclipse with a whole number
   of cycles allows only 2.33035, 2.32956 or 2.32877 d. Only 2.32877 agrees with Gaia and with
   the one-sector TESS period (2.3287 d). A precise period is needed for spectroscopic follow-up
   and for Gaia DR4 work.
2. **Was the WASP dip real?** The same dip shape appears in a 75″ neighbour. That could be light
   leaking from the target or a systematic common to the whole field.
3. **Is the eclipse on the target?** The V = 11.25 star 38″ away blends with the target in
   both WASP (14″ pixels) and TESS (21″ pixels). ASAS-SN's 8″ pixels separate the two stars
   better.

## Data

- **ASAS-SN Sky Patrol v2** (Shappee et al. 2014; Kochanek et al. 2017; Hart et al. 2023), via
  the public `pyasassn` client (`pip install skypatrol`). The source nearest each position
  within 10″ in `master_list` is used: the target (305.561052, −22.073651) and the neighbour
  (305.566500, −22.082972). Points with quality G (if the column exists), 0 < mag_err ≤ 0.1 and
  mag < 50 are kept. The `jd` column is taken as HJD (UTC), the convention of the Sky Patrol
  tables, and 69.184 s is added to put it on TDB. A check reported but not graded refits as if
  `jd` were geocentric JD (see below).
- **SuperWASP DR1** CSVs (wasp.cerit-sc.cz) of the target, the 38″ neighbour and **12 comparison
  stars**. These are every DR1 star 4.7-7.1′ from the target (outside its photometric aperture)
  with V < 13 and more than 8,000 points, among the archive's 50 nearest objects within 20′:
  J202225.43-220021.0, J202227.26-215958.9, J202154.71-220127.7, J202226.81-215939.2,
  J202224.40-215920.3, J202154.46-220110.6, J202222.71-220952.0, J202150.34-220132.3,
  J202149.39-220650.1, J202225.33-215811.9, J202150.36-220042.7, J202147.79-220743.2. We saw
  only their names, magnitudes and point counts.

Cleaning, weights, trapezoid template (T14 0.0990 d, T23 0.0324 d) and box statistic are as in
`wasp_tyc.py` 0.1.0. Cleaning groups are (camera | filter, season) for ASAS-SN.

## Part A: ASAS-SN (graded)

1. **Controls first:** 300 control periods (1.5-3.5 d, seed 20261121, same exclusions as before);
   `control_max` = the largest box statistic.
2. **Injection:** 0.03 mag at 2.6 d (T0 2458000.3), searched over 2.6 ± 0.0009 d in steps of
   2e-6 d. It passes if the period is found within 1e-4 d with a box statistic ≥ 7 and
   > `control_max`.
3. **Search:** box statistic over **2.3260-2.3320 d** (all candidate periods ± about 1.7e-3 d) in
   steps of 2e-6 d. An edge hit is reported.
4. **Fit:** a coarse trapezoid grid (P ± 1e-5, T0 ± 0.02 d), then the epoch is recentred on the
   weighted centre of the in-eclipse data and a fine grid run (P ± 3e-6 in 1e-7 steps, T0 ± 0.004
   d) to give P_A and T_A.
5. **Errors:** a 150-draw bootstrap over nights (grid P ± 5e-6, T0 ± 0.006 d). If more than 20% of
   draws end on a grid edge, the bootstrap is rerun **once** with P ± 2e-5 and T0 ± 0.015 d. If
   still more than 20% end on the edge, the period labels are UNTESTABLE.

**A1 detection.** ASASSN_DETECTED if depth > 0, box statistic ≥ 7 and > `control_max`, depth
S/N (bootstrap) ≥ 5 and at least 5 eclipse nights. Otherwise ASASSN_NOT_DETECTED if the
injection passed, else ASASSN_INSENSITIVE. **ASASSN_UNAVAILABLE** if no light curve could be
downloaded. A2 to A5 are graded only if A1 = ASASSN_DETECTED.

**A2 period branch.** z_G = (P_A − 2.3289298)/√(σ_A² + 0.00014²) and z_W = (P_A − 2.329743)/√(σ_A²
+ 0.0001²). The WASP period's error is set conservatively to 1e-4 d, because v1's bootstrap was
unreliable. Labels: **GAIA_BRANCH** (|z_G| ≤ 3, |z_W| > 3), **WASP_BRANCH** (the reverse),
**BOTH_CONSISTENT**, **NEITHER**; BRANCH_UNTESTABLE as above.

**A3 TESS link.** The same rule as in v1, with T_TESS = BJD_TDB 2460803.0299 and σ fixed at
0.001 d: EPHEMERIS_UNIQUE / AMBIGUOUS / INCONSISTENT / UNTESTABLE. If UNIQUE, the combined
ASAS-SN + TESS period P_AT = (T_TESS − T_A)/N is published with its σ.

**A4 WASP link** (only if A3 = UNIQUE). x = (T_TESS − T_W1)/P_AT with the v1 WASP epoch T_W1 =
2453944.8073; residual r = (x − N)·P_AT in days; σ_r = √(0.005² + 0.001² + (N·σ_AT)²).
**WASP_ON_EPHEMERIS** if |r| ≤ 3σ_r, **WASP_OFF_EPHEMERIS** otherwise, and
WASP_LINK_UNTESTABLE if σ_r ≥ 0.1·P_AT.

**A5 which star** (38″ neighbour, ASAS-SN). The neighbour's depth at (P_A, T_A) and a paired
night bootstrap give z = (d_target − d_neighbour)/σ_diff: **ON_TARGET** if z > 3,
**ON_NEIGHBOUR** if z < −3, BLEND_UNRESOLVED otherwise, and BLEND_UNTESTABLE if the neighbour has
no light curve with at least 300 points.

## Part B: SuperWASP common-mode test (graded on its own)

The target is detrended exactly as in v1: per-night medians at v1's coarse ephemeris (P 2.329777,
T0 2454003.0539), with depth measured at v1's fine ephemeris (P
2.329743, T0 2453944.8073). **Reproduction check first:** the target's depth must come out within
0.002 mag of v1's 0.07427, and the 38″ neighbour's within 0.002 of 0.06377. If either fails, the
label is COMMON_REPRO_FAILED. Each comparison star is then detrended at the fine ephemeris and its
depth measured there. Its σ comes from a 150-draw bootstrap over the target's nights. A
comparison star "dips" if depth > 0.02 mag **and** depth/σ > 3. Of the stars with at least 500
points:
- **COMMON_MODE** if 4 or more dip; **COMMON_CLEAN** if at most 1 dips; **COMMON_MIXED**
  otherwise; COMMON_UNTESTABLE if fewer than 6 are usable.

## Part C: reported, not graded

- A wide SuperWASP scan (2.3200-2.3400 d) after ephemeris-free per-night detrending, with its own
  controls. It reports the top five peaks and the box statistic at each candidate period.
- ASAS-SN: the top five box peaks and the statistic at each candidate, odd/even and secondary
  depths, the ASAS-SN depth (its 16″ aperture blends less than WASP's or TESS's), folded light
  curves at P_A and at Gaia's period, and a **time-scale check**: a refit with the times treated
  as geocentric JD, corrected to heliocentric. It reports the eclipse sharpness (Δχ²) under each
  assumption and the TESS-link label the alternative would give.

## What each outcome means (fixed now)

- **ASASSN_DETECTED:** the eclipse is confirmed by a second, independent instrument, and with it
  its existence before and after TESS. This does not confirm the companion's radius.
- **GAIA_BRANCH + UNIQUE:** we publish the ASAS-SN + TESS ephemeris (expected σ_P ~ 2e-6 d,
  about 70 times better than Gaia's) for spectroscopists and for the DR4 K test's phase. v1's
  WASP period was then biased.
- **WASP_BRANCH:** Gaia DR3's SB1 period for this star is wrong by about 6σ, and the one-sector
  TESS period too. We would report that as a measured Gaia period error.
- **NEITHER**, or **INCONSISTENT:** possible period change (for example a third body) or an error
  of ours. No claim is made until a second TESS sector exists.
- **WASP_ON_EPHEMERIS:** the 2006-2008 dip lines up with the modern ephemeris. With part B CLEAN,
  SuperWASP then supports the eclipse 19 years back, and P_19yr is reported.
- **WASP_OFF_EPHEMERIS + COMMON_MODE:** v1's dip was a field systematic and SuperWASP adds
  nothing. **WASP_OFF + COMMON_CLEAN:** a puzzle (period change?), reported as such.
- **ON_NEIGHBOUR:** the eclipse belongs to the 38″ star, and **B_OVERSIZED_COMPANION is
  withdrawn** in STATUS, the findings and the article. **ON_TARGET:** the 38″ star is excluded
  as the source (stars closer than ASAS-SN's resolution are not).
- The DR4 K test keeps its pre-registered fixed period. Its phase sensitivity to a better
  period is reported only.

## Predictions (written now)

- A1: DETECTED 65%, NOT_DETECTED 5%, INSENSITIVE 20%, UNAVAILABLE 10%.
- A2 (if detected): GAIA_BRANCH 75%, WASP_BRANCH 10%, BOTH 5%, NEITHER 10%.
- A3: UNIQUE 80%. A4 (if UNIQUE): ON 40%, OFF 55%, UNTESTABLE 5%.
- A5: ON_TARGET 70%, UNRESOLVED 20%, ON_NEIGHBOUR 3%, UNTESTABLE 7%.
- B: CLEAN 40%, MIXED 25%, COMMON_MODE 30%, UNTESTABLE or REPRO_FAILED 5%.

## Job

```json
{"name": "tyc6340-period-v1", "kind": "compete", "image": "python:3.12",
 "setup": ["pip install --no-cache-dir skypatrol"],
 "run": ["python -m unittest -v test_tyc_period", "python tyc_period.py --self-test",
         "python fetch_asassn.py --out-dir /data/asassn-tyc6340",
         "python tyc_period.py --data-dir /data/wasp-tyc6340 --asassn-dir /data/asassn-tyc6340 --out-dir /out"],
 "network": true, "data_key": "gaia-orbit-tess", "cpu": 1, "memory_gb": 1.5,
 "timeout_minutes": 120}
```
A self-test failure (exit 3) means: fix, bump to 0.1.1 with a dated note here, no rule change. A
pip or network failure of the ASAS-SN client gives ASASSN_UNAVAILABLE. Parts B and C still run,
and the job is re-filed once as -v2 for part A only.

## Limits

ASAS-SN photometry of a V = 10.7 star is close to saturation. The injection test measures
whether that matters. The time system of the client's `jd` column is assumed, not documented
(see the reported check). The TESS epoch's σ is assumed (0.001 d). Part B can only show a
systematic shared by the field, not one confined to the target's pixels. Nothing here measures
the companion's mass or radius.
