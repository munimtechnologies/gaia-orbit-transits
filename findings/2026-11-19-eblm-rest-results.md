# M-dwarf inflation, full Gaia DR3 sample: the remaining 97 EBLM-like systems are fitted

2026-11-19. MV2 of Munim, Inc.; made with AI agents working in his name, not yet checked by a
human expert. Text CC BY 4.0, code Apache-2.0.

This note reports the two fitting jobs pre-registered in section 5 of
`findings/2026-11-18-eblm-fit-results.md`. It also files the confirmatory grade that section
5 defines (H1-full, H2-full). **The grade has not run yet.** Nothing below is a graded
result. The hand preview in section 3 is exploratory.

## 1. What ran

| job | host | systems | time | code |
|---|---|---|---|---|
| gaia-eblm-rest-a-v1 | Tango | 49 (part 0 of 2) | 62 min | eblm_fit 0.1.0 at 10b5aeb, unchanged |
| gaia-eblm-rest-b-v1 | Tango | 48 (part 1 of 2) | 44 min | same |

Both jobs drew the same 167 "EBLM-like" systems as gaia-eblm-fit-v1. They matched all 70
systems of v1 and fitted the other 97, split alternately in mass order. **All 97 were vetted,
so no system is missing** (n_todo = n_vetted in both summaries). The raw outputs are published
unchanged in `data/eblm-rest-v1/a/` and `data/eblm-rest-v1/b/`: the results CSV, the report and
the summary.

Verdicts:

| verdict | rest-a | rest-b |
|---|---|---|
| EBLM_CONSISTENT | 17 | 16 |
| EBLM_LARGE_RADIUS | 0 | 3 |
| EBLM_GRAZING | 24 | 20 |
| TWIN_AT_2P | 0 | 5 |
| MASS_TENSION (lighter / heavier) | 1 / 0 | 2 / 1 |
| NO_ECLIPSE | 3 | 0 |
| TOO_LUMINOUS | 2 | 0 |
| NO_TESS_DATA | 2 | 1 |

The per-part grades are descriptive only, because the pre-registered grade pools all three
parts:
- G1: 44 of 47 and 47 of 47 detected.
- G2: the median R1,lc / R1,FLAME is 0.998 (n = 15) and 1.027 (n = 11).
- E5: the median TESS/Gaia depth ratio is 0.81 and 0.82.
- G4 on the rough mass-radius table gives INCONCLUSIVE in both parts: +5.7% [+0.6%, +11.9%]
  (n = 17) and +7.9% [+1.5%, +11.7%] (n = 19).

The two TOO_LUMINOUS systems in rest-a (Gaia DR3 4106994895582423808 and 2007119482512999168)
are flagged, not claimed. The run-23 lesson is that such systems have so far been blends or
triples.

## 2. Fits we opened before writing this

We opened the plots of the three largest positive values in the likely main set and of the
shortest-period system:
- **Gaia DR3 5437005667017284864** (TIC 5089368, P 1.072 d): a clean 8% primary eclipse
  and a flat-bottomed 2% secondary eclipse, with flat residuals. Its value is +10%.
- **Gaia DR3 1005906599428386176** (TIC 71101636, P 2.126 d): a clean, flat-bottomed
  secondary eclipse 1.5% deep. The residuals are flat. Its rough-table value is +15%.
- **Gaia DR3 429036553928083840** (TIC 83620405, P 2.662 d): a clean primary eclipse 4% deep,
  with ellipsoidal and reflection variation. Its value is +12%.
- **Gaia DR3 6750919828825203328** (TIC 114053589, P 0.888 d): a near-contact system
  (a/R1 = 2.3) with 3-4% ellipsoidal variation and visible sector-to-sector offsets in the
  residuals. The spherical-star model is only approximate here, so its −11% is
  model-dependent.

All four are real eclipses. None is an ellipsoidal wiggle mistaken for a transit (the
failure mode of the three k-at-bound fits found in v1).

## 3. Hand preview (exploratory; NOT the grade)

Applying the pre-registered main-set cuts of eblm_infl 0.1.0 by hand to the 97 new rows
leaves **14 systems** (8 from rest-a, 6 from rest-b). The cuts are: a clean verdict,
b < 0.8, snr_fit ≥ 30, a FLAME M1, 0.08 ≤ m2 ≤ 0.6 M☉, a FLAME R2, and R1,lc/R1,FLAME in
0.8-1.2. These 14 have m2 = 0.43-0.60 M☉ and P = 0.89-3.52 d.

On eblm_fit's rough mass-radius table (**not** BHAC15), their values are −11, −7, +2, +4,
+4, +5, +6, +6, +6, +7, +8, +10, +12 and +15%, with a median of about +6%. The 14 v1 main-set
systems gave a median of +2.2% against BHAC15 (`findings/2026-11-18-eblm-infl-results.md`).
The two numbers use different references, so they cannot be compared directly here. The job
puts all 28 on the BHAC15 scale.

**One thing to watch:** section 5 predicted that the heavier companions would pull the
median *down*. On the rough table, the new 14 sit above the v1 rough-table values. If the
BHAC15 grade confirms this, the prediction failed, and we will say so.

## 4. The confirmatory grade (filed now, exactly as section 5 defined it)

Job **gaia-eblm-infl-full-v1** (1 GB, about 10 min):
1. `combine_eblm_full.py` 0.1.0 concatenates three inputs into one `eblm_fit_results.csv`:
   - v1's 70 rows, pinned at commit 179d6e4;
   - `data/eblm-rest-v1/a/eblm_fit_results.csv`, 49 rows;
   - `data/eblm-rest-v1/b/eblm_fit_results.csv`, 48 rows.

   It checks that the 63-column headers are identical (exit 4 if not) and that no source_id
   repeats (exit 5). It prints every input's SHA-256 and publishes the combined file and
   `combine_info.json`.
2. `eblm_infl.py` 0.1.0 then runs **unchanged** (pinned at 87f190f) on the 167 rows, with
   the same cuts, seeds and thresholds:
   - H1: INFLATED if the lower 95% bound of the median exceeds 3%; NOT_INFLATED if the upper
     bound is below 3%; INCONCLUSIVE otherwise.
   - H2: a one-sided Spearman permutation test of inflation against period, PERIOD_TREND if
     p < 0.05.

Our probabilities stand as written on 18 Nov: H1-full INFLATED 20%, NOT_INFLATED 30%,
INCONCLUSIVE 50%; H2-full PERIOD_TREND 10%. The hand preview above was seen after those
numbers were fixed, and they are not changed.

If H1-full is INFLATED, we inspect every main-set plot and write a systematics budget
(metallicity, Gaia K bias for hot primaries (Fitzpatrick et al. 2025), ages, selection)
before any claim. An expert-check email is drafted and held for approval, as section 5
requires.

## Why this matters

Low-mass stars in eclipsing binaries are often a few per cent larger than models predict,
and whether close orbits make this worse (through tidally spun-up magnetic activity) is
still open. Recent samples (Swayne et al. 2024; EBLM XIV; Davis et al. 2026) have few
systems below about 2.5 days. This sample weighs short-period M dwarfs with Gaia's own
spectroscopic orbits and TESS eclipses. If it scales, Gaia DR4's ~640k RVS orbits could
weigh hundreds of such stars.
