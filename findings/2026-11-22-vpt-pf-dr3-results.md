# Results: step G6 rehearsal, a period-free TESS search of all 214 Gaia DR3 transit candidates

Graded 2026-11-22 (~11:00 UTC) by MV2 of Munim, Inc. Made with AI agents working in his name; not
yet checked by a human expert. Text CC BY 4.0, code Apache-2.0.

- Pre-registration: `findings/2026-11-21-vpt-pf-prereg.md` (fixed 21 Nov ~23:45 UTC, before the job
  ran). Predictions N1-N4: `findings/2026-11-22-vpt-nss-crossmatch.md` section 5.
- Code: `vpt_pf.py` 0.1.0 (commit 9bf9704211bd129204bb4de091f38021ec76d301), calling
  `vpt_followup.py` 0.1.0 unchanged.
- Job **gaia-vpt-pf-dr3-v1** ran on 22 Nov, 07:16-08:56 UTC: unit tests and self-test passed, then
  all 214 stars were done in 92.5 min (budget 200 min, not reached; peak memory 0.48 GB).
- Data: `data/vpt-pf-dr3-v1/` (`pf_summary.json`, `pf_targets_out.csv`, `pf_sectors.csv`,
  `job_summary.json`, folded light curves `pf_fold_<source_id>.png`).

## 1. Registered tests, graded as registered

| test | result | label | our prediction | came true? |
|---|---|---|---|---|
| PF1: known systems with a known period in 0.3-15 d that the search recovers | 176 / 181 = 0.972 (95% Wilson 0.937-0.988) | PF_RECOVERS | PF_RECOVERS 65% | yes |
| **PF1b (primary): the same, among those whose Gaia period is wrong** | **156 / 160 = 0.975 (0.937-0.990)** | **PF_RECOVERS** | PF_RECOVERS 55% | yes |
| PF_WRONG: detected known systems at an unrelated period | 4 / 181 = 0.022 | PF2 list reliable (≤ 0.25) | ≤ 0.25: 70% | yes |
| PF2: at least one robust NEW planet-like star | 4 robust (8 planet-like) | | 55% | yes |
| PF2: at least one robust NEW_SURVIVES_OTHER_P | 2 (TIC 93622019, TIC 248569057) | | 25% | yes |
| N1: TIC 400170926 at 5.8959 or 2.9480 d (±0.5%) | 2.947871 d | match | 75% | yes |
| N2: TIC 470993218 at 7.0623 or 3.5311 d | 11.6984 d | no match | 30% | no |
| N3: TOI-1991 at 6.6571 or 3.3285 d | 6.657095 d | match | 85% | yes |
| N4: TIC 207399049 at 0.4602, 0.9205 or 0.2301 d | 7.0914 d (S/N 7.4) | no match | 25% | no |

Notes on the grading:
- PF_WRONG's code counts the 181 detected known systems with a known period in 0.3-15 d. The
  registered wording ("detected known systems") also includes Kepler-1513 (known periods 161 and
  841 d only); counted that way it is 5 / 182 = 0.027. Both are far below 0.25.
- All 21 known systems whose Gaia period is right were detected: 20 at the known period and one
  (WASP-54, a SPOC/QLP mix) at twice it (KNOWN_HARMONIC). The four failures of PF1b are all at an
  unrelated period with eclipsing-binary flags or short periods (HATS-62 13.667 d, HAT-P-53
  0.305 d, Kepler-490 8.785 d, HATS-29 0.632 d). The most likely cause is another variable star in
  the TESS aperture, which we have not checked.
- The known systems are mostly bright hot Jupiters with deep transits, the easiest case for TESS.
  The recovery rate for Gaia DR4's fainter and shallower candidates may be lower.

**What this means for Gaia DR4 (2 December):** where Gaia's transit period is wrong (161 of 176
known systems in DR3), a period-free TESS search finds the real period for 97.5% of them in this
rehearsal. Step G6 therefore runs on DR4 as registered (not exploratory), and its PF2 list can be
read as reliable at DR3's error rate.

## 2. What the search says about Gaia DR3's new candidates

32 of the 214 stars have no known planet or TOI period ("NEW"): 5 have no TESS light curve. Of the
27 with TESS data, **18 are eclipsing-binary-like** (odd/even, secondary or a companion larger
than 2 R_Jup), **8 are planet-like** (4 robust, meaning at least two sectors searched alone agree)
and 1 is not detected.

The robust planet-like stars, with the vetting the pre-registration requires before anything is
claimed:

| star (Gaia DR3) | class | Gaia P (d) | TESS P (d) | TESS depth | R2 (R_Jup) | sectors agreeing | vetting |
|---|---|---|---|---|---|---|---|
| **TIC 93622019** (5345417757181174144) | NEW_SURVIVES_OTHER_P | 2.83166 | **2.12388** | 0.88% | 1.29 | 6 of 6 | **passes**: section 3 |
| TIC 4638108 (5431056347037926784) | NEW_SURVIVES | 2.20863 | 2.20828 | 1.41% | 1.66 | 4 of 6 | vetted 21 Nov (Gaia duration suggests grazing) |
| TIC 248569057 (2685725036820337408) | NEW_SURVIVES_OTHER_P | 1.94655 | 1.05593 | 0.21% | 0.67 | 2 of 2 | **fails**: see below |
| TIC 44997521 (5432318139709900160) | NEW_SURVIVES | 3.54975 | 3.54941 | 2.07% | 1.00 | 3 of 6 | vetted 21 Nov (weak, S/N 19.6) |

**TIC 248569057 fails.** The TESS box lasts 6 h, but a central transit of this star (TIC v8.2:
1.70 R_sun, 1.21 M_sun, density 0.345 g/cm³) at 1.0559 d cannot last longer than about 3.0 h
(a/R* ≈ 2.73). The TESS depth is 0.17 times Gaia's 13.2 mmag. Gaia DR3 also flags the star:
RUWE 3.41, non_single_star = 1, radial velocity variable (rv_chisq_pvalue 0.0, rv_amplitude_robust
43.4 km/s over 19 visits). It is most likely a binary, and the 1.056 d signal is not a transit of
this star.

Two non-robust planet-like stars: **TIC 435052739** (Gaia DR3 4136481216073713280) is at Gaia's
period (1.81630 d, S/N 59.6, 1.87 R_Jup) in one QLP sector, but Gaia DR3 sees large velocity changes
(rv_chisq_pvalue 0.0, rv_amplitude_robust 46.3 km/s, 13 visits), so it is very likely a stellar
binary. TIC 260619023, TIC 207399049 and TIC 38814673 are single-sector signals with S/N 7.0-9.4.

The search also confirms the two step-g survivors at Gaia's period without assuming it (TIC
4638108 and TIC 44997521), and it shows TIC 400170926's two eclipses are unequal: odd 3.92% and even
4.59% deep in the half-period fold (z = 197). So 5.8959 d, Gaia's orbital period, is the true
period: an eclipsing binary with a primary and a secondary eclipse.

## 3. TIC 93622019: a giant-planet-sized transit candidate that Gaia flagged at the wrong period

**Star.** TIC 93622019 = Gaia DR3 5345417757181174144 = 2MASS J11423052-5237386 (RA 175.62700,
Dec -52.62741; Centaurus). G 12.57, BP-RP 0.715, TESS mag 12.20, parallax 1.677 ± 0.012 mas
(about 590 pc). TIC v8.2: Teff 6502 K, R 1.357 R_sun, M 1.33 M_sun, density 0.75 g/cm³ (an F star);
FLAME radius 1.41 R_sun. RUWE 0.90, ipd_frac_multi_peak 0: no sign of a close companion in Gaia's
astrometry. TIC contamination ratio 0.187.

**TESS (QLP, sectors 10, 37, 64, 90, 99, 100; all six available sectors were used, so the
pre-registered all-sector run is this run).**
- Combined period **2.123885 d**, S/N 124, box depth 0.883% ± 0.007%, duration about 3 h (1-6 h
  grid), companion radius 1.29 R_Jup for R* 1.41 R_sun. The folded light curve
  (`data/vpt-pf-dr3-v1/pf_fold_5345417757181174144.png`) has a flat bottom near 1.05% with short
  ingress and egress. A box depth averages over ingress and egress, so 1.3-1.4 R_Jup is the
  plausible range.
- **Every sector alone finds the same period:** 2.12299 (S10), 2.12424 (S37), 2.12291 (S64),
  2.12433 (S90), 2.12614 (S99), 2.12250 d (S100), S/N 39-60 each. Per-sector depths 0.908, 0.931,
  0.977, 0.907, 0.890, 0.756% (DEPTH_VARIES note, χ² p 5e-27; QLP's blending correction differs
  between sectors, and sector 100 is the low one).
- Odd 0.902% ± 0.010% vs even 0.865% ± 0.010% (2.7σ, below the 3σ flag). Depth half a period later
  0.028% ± 0.007% (3.9σ, but 3% of the primary, below the 10% flag). Not flagged EB_LIKE under the
  registered rules. **This possible secondary is the main warning sign** (section 4).

**Gaia's period is a 4:3 alias.** Gaia's 2.831658 d is 1.33324 times the TESS period (4/3 =
1.33333, 0.007% apart). Gaia's reference epoch (BTJD 399.849) lies 551.693 TESS periods before the
TESS epoch (BTJD 1571.581). For a 4:3 alias the reference epoch need not be a transit, but it must
sit a third of a period from one: it sits 0.307 periods from a transit, 1.3 h away from the
expected third, inside Gaia's 4.5 h duration. Gaia's own depth, 11.9 mmag (1.09%) from 24 in-transit
points, matches the TESS flat-bottom depth.

**Duration and density.** With density 0.75 g/cm³ and P = 2.12388 d, a/R* ≈ 5.63. A central transit
lasts up to about 3.2 h, and TESS gives about 3 h, so the transit fits this star. (Gaia's 0.186 d is
an estimate made at its wrong period.)

**Which star.** Gaia's own photometry (about 0.4-2" resolution, far sharper than TESS's 21"
pixels) shows the same depth on this source. So no Gaia-resolved neighbour within the TESS aperture
can be the source in Gaia's data. 74 Gaia sources lie within 60". The target is the brightest; the
others are not used in this argument.

**Gaia's spectrograph.** G_RVS 11.96 (method 1), 27 visits, radial_velocity_error 1.68 km/s,
rv_chisq_pvalue 0.514, rv_renormalised_gof 4.10, rv_amplitude_robust 16.2 km/s. That is **not RV
variable** under the Katz et al. (2023) criterion (p ≤ 0.01 and gof > 4), and it was among the 4 of
12 RVS-testable new candidates that our 22 Nov screen did not flag. For method 1, radial_velocity_error
= sqrt(π/(2N) σ² + 0.11²), so the scatter of the 27 epoch velocities is σ ≈ 7.0 km/s. A circular orbit
of semi-amplitude K alone gives a scatter of K/√2, so **K ≲ 10 km/s** without even subtracting noise
(our rough estimate). For this star at 2.124 d that excludes companions heavier than about
0.08-0.1 M_sun (K ≈ 10.6 km/s at 0.08 M_sun, 13 km/s at 0.1 M_sun). It cannot tell a hot Jupiter
(K ≈ 0.1-0.2 km/s) from a brown dwarf.

**Prior art (22 Nov 2026).** No TOI or CTOI and no follow-up files on ExoFOP-TESS. No SPOC TCE
(exo.MAST TCE list empty: the star has no 2-minute data). Not in the TOI list at any disposition (the
job's own check). VSX: no variable within 2'. ASAS-SN variables: none within 0.5'. Gaia DR3
vari_eclipsing_binary: none. Gaia's classifier: EP (score 1.0). T16 Cycle 1 catalogue (Roth,
Hartman & Bakos 2026, ApJS; arXiv:2604.18579; candidate_table.tab, Harvard Dataverse
doi:10.7910/DVN/CWEUGW, 11,143 candidates): no row. The star falls in its sector 10 camera 2 CCD 2
block, which is ordered by Gaia ID, and Gaia DR3 5345319106064788352 and 5345988403728111616 sit
next to each other there with nothing between. That block is "roughly" ordered, so this check is
strong but not exhaustive. A web search under the TIC, Gaia and 2MASS names found nothing. **Not
checked:** SIMBAD and VizieR (CDS refused connections; the CfA VizieR mirror's database was down)
and the TESS Ten Thousand EB catalogue.

**Label.** Under the pre-registered rules: robust NEW_SURVIVES_OTHER_P, vetting passed. **A
giant-planet-sized transit candidate first flagged by Gaia, at a period Gaia did not report.** We do
not call it a planet.

## 4. Limits

- The possible secondary eclipse (277 ± 71 ppm) is deeper than we would expect from a hot
  Jupiter's own light in the TESS band. Our rough estimate is ≲ 120 ppm for a 2,000-2,500 K
  dayside at a/R* 5.6. A star of about 0.1 M_sun at about 3,000 K would give about 300 ppm. Gaia's
  spectrograph limit (about 0.08-0.1 M_sun) leaves the very lowest-mass stars and brown dwarfs open.
  Only radial velocities with ~0.1 km/s precision can decide. The secondary and the 2.7σ odd/even
  difference come from 30-min-binned QLP photometry with white-noise errors.
- The pixel-level which-star test has not been run in TESS. Gaia's own photometry is the
  which-star argument, and it cannot exclude a blend closer than Gaia resolves (≲ 0.4").
- Stellar parameters are TIC v8.2 and FLAME, not spectroscopic.
- The known-system recovery rate is measured on mostly bright hot Jupiters.
- One reported sector label for TIC 400170926 reads "1751:TESS-SPOC", a labelling slip in the
  output (at most 6 sectors were used). It does not affect the period.
- Not blind: we knew the known systems and the two step-g survivors. We had not seen any output of
  this search before the predictions were fixed.

## 5. Next

1. TIC 93622019: a pixel-level which-star test on TESScut images (all six sectors), then a CTOI on
   ExoFOP (needs an ExoFOP account; asked of Sheehan) so that TFOP can take radial velocities.
2. Gaia DR4 (2 December): step G6 runs as registered on all DR4 candidates.
3. TIC 400170926: eclipse fit; the unequal eclipses seen here are its first measured property
   beyond the period.
