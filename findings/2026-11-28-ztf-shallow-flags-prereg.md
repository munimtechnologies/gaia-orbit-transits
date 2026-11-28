# ZTF test of the unvetted shallow Gaia-epoch eclipse flags (pre-registration)

MV2, Munim, Inc. (mv2@munimtech.com), 2026-11-28 ~15:10 UTC. CC BY 4.0. Made with AI agents working in
his name; no human expert has checked it. Written after the catalogue checks and after reading only the
row count and median magnitude of one ZTF g light curve (391817260687992960), before any faint ZTF point of
any target was looked at. It is published together with the result (same commit), so its timing rests on
this statement and on the run log, not on a separate timestamp.

## Sample (frozen)

`data/g8-dr3-sb1-v1` (pre-registered blind search of all 7,978 Gaia DR3 SB1 orbits of 0.4-15 d) flagged 111
stars that Gaia's eclipse tables do not contain. 46 were vetted on 26 Nov (the 10 deepest and all 36 deeper
than 0.10 mag with no Gaia variability class). This test takes the **unvetted** remainder that has no Gaia
variability class, G >= 12.0 (ZTF saturates brighter) and Dec > -28 (ZTF sky): eight stars.

Catalogue check today (VizieR CfA cone, 90", ten catalogues: TESS Ten Thousand tables 2-4, ASAS-SN II/366,
IJspeert+2024, GCVS/NSV, Prsa+2022, IJspeert+2021, VSX, ATLAS, ZTF periodic variables, ASAS-3):

| Gaia DR3 | G | P_Gaia (d) | listed as | role here |
|---|---|---|---|---|
| 1993895376986150272 | 12.46 | 2.88029 | IJspeert+2024 OBAF EB candidate (score 1.0) | KNOWN, not tested |
| 981348113867985920 | 12.43 | 3.65740 | ASAS-SN EA, P 3.6579 d | KNOWN, not tested |
| 4511109601032181504 | 12.28 | 3.50872 | IJspeert+2024 OBAF EB candidate (score 1.0) | KNOWN, not tested |
| 4535010166315168640 | 12.35 | 3.10003 | VSX "VAR" with spurious 0.0405 d period only | UNLISTED: test |
| 4576721896566803072 | 12.16 | 12.42320 | VSX "VAR" with spurious 0.0139 d period only | UNLISTED: test |
| 391817260687992960 | 12.33 | 11.36253 | VSX "VAR" with spurious 0.0193 d period only | UNLISTED: test |
| 4497399653101181184 | 12.28 | 6.56406 | TESS Ten Thousand table 2 (unvetted machine targets) | machine flag: test, not claimed as first |
| 4229808420168374400 | 12.34 | 13.67066 | TESS Ten Thousand table 2 (unvetted machine targets) | machine flag: test, not claimed as first |

So 3 of the 8 shallow flags are already catalogued eclipsers (a purity check of the flag, not a test).

## Gaia predictions (from I/357/tbosb1; BTJD = BJD - 2457000; Gaia Tp is relative to BTJD 389.0)

Primary conjunction = visible star behind its companion (true anomaly 90 deg - omega); this is where the
deeper eclipse must fall in a single-lined binary. Secondary = visible star in front (270 deg - omega).

| Gaia DR3 | P +- sigma (d) | e | omega | T_conj,primary (BTJD) | secondary phase |
|---|---|---|---|---|---|
| 4535010166315168640 | 3.10003166 +- 0.00018 | 0.070 +- 0.032 | 219 +- 34 | 389.858 | 0.465 |
| 4576721896566803072 | 12.4232023 +- 0.0016 | 0.231 +- 0.014 | 217.5 +- 3.9 | 395.487 | 0.383 |
| 391817260687992960 | 11.3625261 +- 0.0016 | 0.021 +- 0.029 | 330 +- 68 | 395.215 | 0.512 |
| 4497399653101181184 | 6.5640588 +- 0.00043 | 0.019 +- 0.020 | 27 +- 80 | 393.195 | ~0.5 |
| 4229808420168374400 | 13.6706619 +- 0.0027 | 0.069 +- 0.054 | 239 +- 22 | 395.144 | ~0.47 |

Carried 70-310 orbits to the ZTF years, Gaia's 1-sigma period errors move these times by 0.1-0.6 d (up to
0.13 of an orbit for 4535010166315168640), and Gaia DR3 SB1 period errors are known (our 28 Nov tests) to be
about 2x too small. A fixed window around Gaia's times therefore has little power; we use the two-stage
method that confirmed UCAC4 468-115332 and UCAC4 544-021692 on 28 Nov.

## Method (frozen)

Data: IRSA ZTF DR light-curve API, 2" cone, catflags = 0 rows only, one oid per band (the one with most rows).

**Stage 1 (find, ZTF g).** Faint points: mag >= median + 0.035 (g band). Group faint points by night. Look for
a linear ephemeris T0 + n P' with |P' - P_Gaia| <= 3 sigma_P x 2 that puts the faint nights on a common
phase; fit P' and T0 by least squares to the faint-night mid-times. Report how far T0 lies from Gaia's
predicted primary conjunction (in sigma of the propagated Gaia error) - reported, not graded.
If no ephemeris puts >= 4 faint nights within 0.03 of an orbit of each other: stage-1 verdict NOT_FOUND.

**Stage 2 (test, ZTF r; data not used in stage 1).** Faint points: mag >= median_r + 0.030. Window: +-w around
the frozen primary times, w = 0.6 x the full eclipse width seen in stage 1, at most 0.04 of an orbit; if a
secondary is seen in stage 1, its window is added with the same w and p doubles. p = total window fraction.
- PASS: >= 50% of faint r points in the windows, on >= 3 distinct nights, and binomial P(k >= k_obs | n, p) <= 1e-4.
- FAIL: otherwise. NO_DATA: fewer than 5 faint r points or no r light curve (saturation).
If r has no usable data, stage 2 falls back to ZTF g points from seasons not used in stage 1 (declared before
fitting: stage 1 uses g data with HJD < 2459500 only; the fallback test uses g with HJD >= 2459500).

**Order of work.** Highest power first: 4535010166315168640 (shortest period), then 391817260687992960,
4576721896566803072, then the two machine-flag stars if time allows. Untested stars are reported as untested.

**What a PASS means.** The star dims at a fixed period equal (within the stated tolerance) to Gaia's
spectroscopic period: an eclipsing binary (or, if the dip has the width of half the orbit, an ellipsoidal
variable, which we would report as such). A PASS for an UNLISTED star is a new eclipsing binary, subject to
the final prior-art search. Faint-point counting cannot measure depth or shape; TESS is needed for those.
