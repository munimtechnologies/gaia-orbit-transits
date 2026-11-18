# Are M dwarfs in 1-2-day orbits inflated? Gaia-weighed EBLM fits, graded (eblm_fit 0.1.0)

2026-11-18. MV2 of Munim, Inc.; made with AI agents working in his name. Text CC BY 4.0,
code Apache-2.0. Pre-registration: `findings/2026-11-17-eblm-fit-prereg.md` (eblm_fit
grades) and `findings/2026-11-17-short-period-inflation-prereg.md` (the sharper BHAC15
test, job gaia-eblm-infl-v1, filed today and not yet run). Data:
`data/eblm-fit-v1/` (results table, report, summary, selected fit plots).

## What ran

Job `gaia-eblm-fit-v1` (Dell, 5.4 h, 0.29 GB). It ran the same Gaia DR3 query as before:
SB1 orbits of stars that Gaia also classifies as eclipsing, with f(M) < 0.3. That gave
167 "EBLM-like" systems. They were fitted in order of increasing m2 sin i, with TESS
(SPOC, then TESS-SPOC, then QLP; up to 4 sectors).

**The job stopped on its time budget after 70 of the 167 systems**, the 70 with the
lightest companions (m2 sin i up to about 0.39 M☉). Everything below covers those 70.
The other 97 are now being fitted with the identical code (jobs gaia-eblm-rest-a-v1 and
-b-v1; section 5).

Verdicts: 29 grazing, 22 consistent, 5 twins at twice the period, 5 mass tension
(4 heavier, 1 lighter), 3 small radius, 1 large radius, 2 no eclipse, 2 no TESS data,
1 no TIC.

## Grades (as pre-registered; nothing re-defined)

| test | prediction (our prob.) | result | grade |
|---|---|---|---|
| G1 | ≥ 80% of systems with data have snr_fit ≥ 10 (85%) | 65 / 67 | **pass** |
| G2 | median R1,lc / R1,FLAME in 0.85-1.15 (65%) | 0.988 (n = 17) | **pass** |
| G3 | ≥ 10 clean EBLM fits (60%) | 26 | **pass** |
| G4 | inflation outcome: INFLATED 40%, CONSISTENT 25%, INCONCLUSIVE 30%, DEFLATED 5% | median −0.5%, 95% CI [−5.2%, +3.4%] (n = 26) | **CONSISTENT** |
| G5 | ≥ 3 TOO_LUMINOUS (50%) | 0 | **fail** |
| G6 | ≥ 15 of the 19 v1 systems detected (90%) | 18 / 19 | **pass** |
| E6 | ≤ 2 of 5 named systems EBLM_LARGE_RADIUS (55%) | 0 | **pass** |
| E5 | median TESS model depth / Gaia depth < 1 (60%) | 0.75 (n = 65) | **pass** |

G4 variants (reported, not graded): with FLAME radii, median −2.7% [−7.4%, +3.3%] (n = 17,
CONSISTENT). By period: P < 1.5 d, −11.9% [−57%, −2.8%] (n = 12); P ≥ 1.5 d, +5.8%
[+0.1%, +12.6%] (n = 14). Both are INCONCLUSIVE because their intervals are wider than 0.2.

**Reading.** At the eblm_fit level (the rough mass-radius table, all 26 clean fits),
the companions show no large inflation. The +5-15% that the "magnetic inflation" picture
predicts for tidally locked M dwarfs at 1-2 days is not seen as a population median. This
is the outcome we gave 25%.

The rough table is itself 3-4% larger than the BHAC15 isochrone (see the inflation
pre-registration). Measured against BHAC15, the same radii would therefore sit about 3%
higher. That is why the sharper BHAC15 test (below) matters.

G5 failed: none of the 70 companions is hotter than an irradiated M dwarf can be. So
there is no stripped-companion (EL CVn) candidate among them, which matches the run-23
finding that the two earlier "too luminous" systems were blends or triples.

## Checks after grading (post hoc; they can only weaken a claim)

1. **Three "clean" fits are not eclipses.** Gaia DR3 1866019155321938560,
   4430814504528950912 and 2871827790822497920 have k at or near the 0.005 lower bound
   and R2 = 0.015-0.033 R☉ (inflation −92% to −97%). Their snr_fit of 10.6-19.8 comes
   from small wiggles in an ellipsoidal light curve, not from an eclipse; see the
   2871827790822497920 plot. The verdict rules let them through as EBLM_SMALL_RADIUS.
   - They are all at P < 1.5 d. They explain the "deflated" short-period bin, which
     should not be read as physics.
   - Without them the median of the remaining 23 is about 0%. G4 does not change.
   - The pre-registered main set of the sharper test (snr_fit ≥ 30) already excludes
     all three.
   - **Rule for DR4:** a fit with k within 20% of its lower bound is NO_ECLIPSE.
2. **Most of the large positive values come from primaries with an assumed mass.**
   Six clean fits are at +10% or more. Five of them have a primary with no FLAME mass
   (1.3 M☉ assumed, and no Teff), and each gives +10% to +16%. A heavier real primary
   lowers that number. The pre-registered main set requires a FLAME mass, so these drop
   out of it too.
3. **Mass and period are correlated in this sample.** Heavier companions sit at longer
   periods, so any "trend with period" here is partly a mass trend. This is the |ρ(m2,P)|
   > 0.3 caution that H2 already pre-registered.

## Hand preview of the sharper test (NOT the graded result)

Applying the pre-registered main-set cuts by hand leaves 14 systems: clean verdict,
b < 0.8, snr_fit ≥ 30, FLAME M1 and R1, R1,lc/R1,FLAME within 0.8-1.2, P = 0.91-2.20 d,
m2 = 0.24-0.41 M☉. Against the transcribed BHAC15 5-Gyr fallback grid, by hand:

- median inflation +2.2%;
- values from −13.6% to +24.8%; only Gaia DR3 5851944656586312448 is above +9%;
- Spearman ρ(inflation, P) ≈ +0.49, the opposite sign to the predicted ρ < 0;
- ρ(m2, P) ≈ +0.50 and ρ(inflation, m2) ≈ +0.23.

If the job reproduces this:
- H1 is most likely **INCONCLUSIVE**: a 14-system bootstrap interval spans both +3% and
  Swayne et al.'s +6%;
- H2 is **NO_TREND_DETECTED**.

The job (gaia-eblm-infl-v1) downloads the real BHAC15 file and computes the bootstrap. Its
output, not this preview, is the result. The outlier 5851944656586312448 (P 2.11 d,
a/R1 2.6, A-type primary with R1 ≈ 3.3-3.7 R☉, 2.7% ellipsoidal) is a near-contact
system. A more evolved primary than FLAME assumes would change its radius.

## What this means so far

- 1-2-day M dwarfs weighed by Gaia do not show the large (≳ 10%) inflation the
  magnetic-activity picture predicts at the shortest periods. With 14-26 systems we
  cannot separate EBLM XIX's 0.3% from Swayne et al.'s 6%.
- This is the first sample we know of that tests short-period M-dwarf inflation with
  masses taken from Gaia's own orbits, at P < 2.5 d. Swayne's short-period group is
  P = 2.78-4.30 d, and EBLM XIV has two systems below 3 d. The sample is still small, and
  Gaia's SB1 K values for hot, fast-rotating primaries can be biased (Fitzpatrick et al.
  2025).
- The wow, if it works at scale: Gaia DR4's 638,966 RVS SB1 orbits times its 2.4 million
  eclipsing binaries could turn this into hundreds of weighed short-period M dwarfs. That
  would settle whether short orbits inflate M dwarfs.

## 5. Pre-registration: the full DR3 sample (written before any of the 97 are fitted)

Jobs gaia-eblm-rest-a-v1 and -b-v1 run eblm_fit 0.1.0 unchanged (fetched at commit
10b5aeb). They cover the 97 systems that gaia-eblm-fit-v1 did not reach, split
alternately in mass order. Once both finish:

- **Input.** Concatenate v1 (70 rows), rest-a and rest-b into
  `data/eblm-fit-full/eblm_fit_results.csv`. Any system still missing (a time budget
  again) is listed. Then run eblm_infl 0.1.0 **unchanged** on it.
- **Status of the tests.** H1-full and H2-full use exactly the H1/H2 rules, cuts and seeds
  of `2026-11-17-short-period-inflation-prereg.md`. The 70-row run (gaia-eblm-infl-v1) is
  the primary pre-registered test. The full run is the confirmatory extension.
- **Our probabilities.**
  - H1-full: INFLATED 20%, NOT_INFLATED 30%, INCONCLUSIVE 50%.
  - H2-full: PERIOD_TREND 10%.
  - The 97 have heavier companions (m2 ≈ 0.4-0.6 M☉), where Swayne et al. and
    EBLM XIV find less inflation, so we expect the full median to fall, not rise.
- **Descriptive only.** The k-at-bound rule from check 1, applied to the full set.
- **If INFLATED.** We inspect every main-set plot and write a systematics budget
  (metallicity, Gaia K bias, ages, selection), and an expert-check email is drafted and
  held for Sheehan's approval before any claim. Nothing is claimed from DR3 alone.
