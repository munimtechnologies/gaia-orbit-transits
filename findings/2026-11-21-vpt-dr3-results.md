# Step-g DR3 rehearsal: results on all 214 Gaia DR3 transit candidates

Written 2026-11-21 (~17:00 UTC). By MV2 of Munim, Inc.; made with AI agents working in his name,
not yet checked by a human expert. Text CC BY 4.0.

- Pre-registration: `findings/2026-11-21-vpt-tess-prereg.md` (code `gaia_vpt_tess.py` 0.1.0).
- Amendment 1 (written after chunk 0 and before chunk 1 ran): `findings/2026-11-21-vpt-amendment-1.md`.
- Chunk 0 interim: `findings/2026-11-21-vpt-dr3-c0-interim.md`, data `data/vpt-dr3-v1/c0/`.
- **Chunk 1 (new): data `data/vpt-dr3-v1/c1/`** (job gaia-vpt-dr3-c1-v1, 0.1.0, ran on the Blade
  21 Nov 15:05-15:48 UTC; 107 candidates, 102 OK, 5 NO_TESS because no TIC lay within 5″).

**How these numbers were made.** Every count below is read from the two chunk files
(`vpt_summary.json`, `vpt_stars.csv`) written by the registered code; the combined values are sums
of the two chunks, and the intervals are Wilson (proportions) or Garwood (counts) 95% intervals
computed by hand with the formulas in `gaia_vpt_tess.py`. Job **gaia-vpt-dr3-comb-v1** recomputes
everything with 0.1.1 (`--combine c0 c1 --rvs-file`) plus a fresh Gaia RVS query; its output goes
to `data/vpt-dr3-v1/comb/` and replaces this note wherever the two differ.

The DR3 rehearsal is **not blind**: the 173 known systems are known, and Panahi et al. (2022)
checked the 41 new candidates with TESS images up to 2021. It calibrates the test for Gaia DR4's
1,007 candidates (2 December 2026).

## Graded labels and our predictions

| test | chunk 0 | chunk 1 | all 214 | our prediction | |
|---|---|---|---|---|---|
| G0a known planets recovered at Gaia's period | 10/11 | 4/4 | **14/15 = 0.93 (0.70-0.99): PIPELINE_OK** | PIPELINE_OK 75% | held |
| G0b control rate (all stars) | 23/172 | 23/158 | **46/330 = 0.139: CONTROLS_NOISY** | CONTROLS_OK 75% | **wrong** |
| G1 NEW seen (as registered) | 6/11 | 1/8 | **7/19; f = 0.23 (0.01-0.62): MIXED, not valid** (G0b noisy) | UNTESTABLE 45%, MIXED 15% | **wrong** |
| G2 planet-like NEW hits | 2 | 1 | **3** | 0: 55%; 1-3: 40% | **wrong** (most likely bin) |
| G3 EB-like share of NEW hits | 6/8 | 3/4 | 9/12 = 0.75 | (DR4 only) | |
| G4 missed at P, hit at P/2 or 2P | 11/73 | 7/74 | 18/147 | (exploratory) | |

Amendment 1's held-out predictions for chunk 1 (fixed before chunk 1 ran):

| test (chunk 1 alone) | result | prediction | |
|---|---|---|---|
| G5 Gaia period reliability | **4 of 86 known systems match = 0.047 (0.018-0.114): PERIODS_MOSTLY_WRONG** | MOSTLY_WRONG 85% | **held** |
| G0b_kp known-planet control rate | 0 of 8 trials, but only 4 known planets: **UNTESTABLE** | CONTROLS_OK 70%, UNTESTABLE 25% | **wrong** (less likely branch) |

## 1. Gaia DR3's transit periods are mostly not the planets' periods

A candidate is KNOWN_PLANET when Gaia's `transit_period` is within 1% of a known period (NASA
Exoplanet Archive planet, or a confirmed/known TOI on the same TIC) at ratio 1, 1/2 or 2, and
KNOWN_SYSTEM_OTHER_P when the star has a known planet or TOI but no period matches.

| | known systems | Gaia period matches | share (95%) |
|---|---|---|---|
| chunk 0 | 90 | 11 | 0.122 (0.07-0.21) |
| chunk 1 (held out) | 86 | 4 | 0.047 (0.018-0.114) |
| **all** | **176** | **15** | **0.085 (0.052-0.136)** |

So for **161 of 176** known systems in Gaia DR3's transit table (the current, corrected table,
`solution_id` 375523436409132247), Gaia's period is not the known period, nor half or twice it.
Examples from chunk 1 (Gaia period from `data/vpt-dr3-v1/c1/vpt_candidates.csv`; known period
from the NASA Exoplanet Archive `pscomppars`, queried 21 Nov 2026):

| planet | Gaia DR3 period (d) | known period (d) |
|---|---|---|
| HD 189733 b | 1.66141 | 2.21858 |
| HD 209458 b | 0.89901 | 3.52475 |
| WASP-17 b | 2.51408 | 3.73543 |
| WASP-39 b | 0.51254 | 4.05529 |
| WASP-4 b | 1.30859 | 1.33823 |
| HAT-P-7 b | 0.62954 | 2.20474 |
| Kepler-7 b | 0.93266 | 4.88549 |
| WASP-69 b | 2.29174 | 3.86814 |
| HAT-P-1 b | 32.85151 | 4.46530 |
| WASP-65 b | 30.06615 | 2.31142 |
| WASP-18 b (a match) | 0.94148 | 0.94145 |
| HATS-52 b (a match) | 1.36655 | 1.36665 |

Prior art. The Gaia DR3 documentation (section 10.10.1) says only that the parameters of the
known planets "do not necessarily match the known, nominal parameters", because they come from
Gaia photometry alone. Panahi et al. (2022, A&A 663, A101) built the training set by searching the
known planets within ±3σ of their published parameters, so their pipeline paper reports no blind
period comparison. We found no published count. Caveat fixed in amendment 1: a multi-planet system
where Gaia found a different real planet counts as "not matching" (2 of the 79 in chunk 0 list more
than one planet). We did not test other simple ratios (1/3, 3, 2/3).

## 2. The noisy controls come from the wrong periods

Control trials fold each star at 0.8541 and 0.9137 × Gaia's period after masking the best box at
Gaia's period. Control hits by category (rate sample; chunk 1 counted from `vpt_stars.csv`; the
chunk-1 total of 23 equals the job's own `control_hits`):

| category | chunk 0 | chunk 1 | all | rate |
|---|---|---|---|---|
| KNOWN_SYSTEM_OTHER_P (real signal at another period) | 20/124 | 23/128 | **43/252** | **0.171** |
| NEW | 3/22 | 0/16 | 3/38 | 0.079 |
| KNOWN_PLANET (Gaia period right) | 0/22 | 0/8 | **0/30** | **0.000** (95% upper 0.123) |
| TOI_PC | 0/4 | 0/6 | 0/10 | 0.000 |

Chunk 1 confirms amendment 1 on data it had not seen: controls fire on stars whose real transit
sits at a period other than Gaia's, and never on known planets where Gaia's period is right. On
the combined 214, G0b_kp has 15 known planets and 0 of 30 control trials: **CONTROLS_OK** (reported;
it is graded only on DR4). With that rate, G1b (reported, not graded, because it was designed after
chunk 0) is 7/19 = **0.37 (0.15-0.76): MIXED**; with the 95% upper control rate it is 0.25, MIXED.
Chunk 0 alone had suggested MOSTLY_SEEN (0.55); the full sample does not.

## 3. A hit at the wrong period is nearly always flagged

24 of the 126 sensitive KNOWN_SYSTEM_OTHER_P stars still "hit" at Gaia's wrong period (10 of 62 in
chunk 0, 14 of 64 in chunk 1). In chunk 1 **all 14 carry an eclipsing-binary flag** (all 14 ODD_EVEN,
3 also SECONDARY, 1 also STELLAR_SIZE): folding a real transit at a wrong period makes alternate
epochs disagree. In chunk 0, 8 of 10 were flagged. So **22 of 24** wrong-period hits are flagged,
and 2 (TOI-150, WASP-113) look planet-like. For DR4 this is the measured rate at which a
wrong-period fold passes as planet-like: 2 of 126 sensitive known systems (1.6%). The flags also
cost a little on real planets: in chunk 1, 1 of the 4 known planets at the right period (WASP-18 b,
odd/even z = 3.1 at S/N 61) was flagged ODD_EVEN.

## 4. Gaia's own spectrograph (exploratory, from the hand query of 21 Nov ~15:00 UTC)

Katz et al. (2023) criterion (p ≤ 0.01, renormalised gof > 4, ≥ 10 RVS transits). Flagged stars by
category, now that chunk 1's categories are known:

- **NEW: 8 flagged** (chunk 0: 4136481216073713280, 4535127268607000320, 2685725036820337408,
  6081267254094015616; chunk 1: 1622997463177004928, 2015499135507395328, 4677436783705094912,
  4895643593611507584). Chunk 0 had 6 RVS-testable NEW candidates; chunk 1's testable count comes
  from job gaia-vpt-dr3-comb-v1.
- **Known planet hosts: KELT-1 and WASP-18** (both companions are 10-27 Jupiter masses: correct
  flags) and **WASP-163** (1.9 Jupiter masses: an RVS false positive or an unknown companion).
- **TOI-1991** (5348534425968598400, KNOWN_SYSTEM_OTHER_P): flagged, so its TOI may have a
  stellar companion.

Two of chunk 1's three EB-like NEW hits are RV-variable (2015499135507395328, range not yet tabled;
4895643593611507584, 132 km/s), consistent with eclipsing binaries.

## 5. What survives: two planet-like NEW candidates with no TOI

Both are among Gaia's 41 DR3 candidates (Panahi et al. 2022): if they hold up, they are Gaia's
discoveries, and TESS's confirmation of the transit is the new part.

| | TIC 4638108 | TIC 44997521 (new this run) |
|---|---|---|
| Gaia DR3 source_id | 5431056347037926784 | 5432318139709900160 |
| G / G_RVS | 12.79 / 12.29 | 13.81 / 12.72 |
| Gaia P (d) | 2.20863 | 3.54975 |
| TESS sectors hit / used / available | 3 / 3 / 6 | 2 / 3 / 7 |
| injection sensitivity | 1.00 | 0.33 |
| best sector, S/N | QLP S89, 42.7 | QLP S89, 7.6 |
| depth TESS / Gaia | 1.79% / 1.57% | 2.19% / 2.22% |
| secondary S/N, odd/even z | -0.67, 0.56 | 0.14, n/a |
| star radius (R☉) | 1.44 (FLAME) | 0.71 (from absolute G) |
| companion radius | 1.87 R_Jup | 1.03 R_Jup |
| RVS test | untestable (G_RVS > 12) | untestable (no RV statistics) |
| ExoFOP TOI/CTOI (21 Nov) | none | none |
| other | Teff 6900 K; Gaia class EP | bp_rp 1.39 (K dwarf); RUWE 1.06; ipd_frac_multi_peak 0; not in the NASA Exoplanet Archive |

TIC 44997521 is the more interesting of the two: a 1.0 R_Jup companion at 3.55 d around a K dwarf
is the size of a hot Jupiter, and TESS sees the same depth as Gaia. But its TESS detection is weak
(S/N 7.6 in the best sector; the injection sensitivity was only 0.33 at 0.8 × Gaia's depth), and
in this rehearsal a hit at Gaia's period does not prove the period (section 3). Nothing is called
a planet. Next: the pre-registered all-sector, period-free TESS follow-up
(`findings/2026-11-21-vpt-followup-prereg.md`, job gaia-vpt-followup-v1), then a pixel-level
which-star test, then radial velocities (only a spectrograph can tell a hot Jupiter from a small
star).

## What this means for Gaia DR4

1. DR4's G1b, which subtracts the known-planet control rate, is the right primary test; the
   original G1 will again be ruined by wrong-period stars.
2. DR4's G5 (blind) measures whether the longer 66-month baseline fixes Gaia's periods. Our
   prediction stays as fixed in amendment 1 (MOSTLY_RIGHT 30%, MIXED 35%, MOSTLY_WRONG 30%).
3. Every DR4 planet-like NEW signal gets the period-free follow-up before it is listed, because a
   fold at Gaia's period can hit at a wrong period.
