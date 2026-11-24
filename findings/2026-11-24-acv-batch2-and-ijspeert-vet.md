# Gaia's own photometry finds eclipsing double-lined binaries, but the bright ones were already TESS candidates: batch 2 and the IJspeert (2024) check

2026-11-24 (~20:00-21:00 UTC), gaia-orbit-transits. By MV2 of Munim, Inc.; made with AI agents
working in his name. No human expert has checked this yet. Text and data CC BY 4.0, code Apache-2.0.

## Summary

1. **Out-of-sample test passed.** With the dip rule frozen (`gaia_conj_dips_acv` 0.1.0, public since
   v0.62.0) and the batch fixed in `findings/2026-11-24-acv-batch2-prereg.md`, we read Gaia DR3 G
   epochs of all 15 remaining ACV-labelled double-lined binaries with 2 < P < 3 d (724 rows, in
   `data/gaia-conj-dips-acv2/`). Two stars have dips (B1: at least 2, **passed**) and **all 4 unflagged
   dips fall within 0.035 in phase of a conjunction** of the star's own Gaia orbit (B2: more than half,
   **passed**; about 14% expected by chance for each dip).
2. **But none of the Gaia-epoch candidates is new.** The VizieR CfA mirror served the catalogue of
   IJspeert et al. (2024, A&A 691, A242; 69,058 TESS OBAF eclipsing-binary candidates) today. **All
   five candidates we flagged from Gaia epochs earlier today (CD-63 310, CD-72 1603, HD 218299,
   HD 101167, HD 187301) and the new batch-2 star CD-44 6966 are in its EB catalogue.** We withdraw
   them as candidates for new eclipsing binaries. No article was published about them.
3. **The two eclipsing binaries we did publish as new (HD 250735, CD-28 7251) are not in it.**
   HD 250735 is outside their sample; CD-28 7251 is in their parent sample without a score (its only
   TESS pipeline detection is from sector 62, after their years 1-4) and not in the EB catalogue.
   Neither is in the accepted-systems list of Eclipses by Appointment at its newest commit (19fadae,
   24 Nov 19:44 UTC), read in full.
4. **What the method is worth.** Against that TESS catalogue, Gaia's sparse photometry plus Gaia's
   own orbit is a clean eclipse detector: in the 31 ACV-labelled SB2s read so far, every star with
   rule dips is a TESS eclipsing binary (6 of 6), and the Gaia dip times agree with TESS eclipse
   ephemerides to 0.0002-0.034 d. It found 5 of the 7 IJspeert EBs whose TESS period matches Gaia's.
   So the method works; the bright, TESS-covered end of the sample is simply already mined. The
   place where Gaia alone can find new eclipsing binaries is where TESS cannot: faint (G > 13) and
   crowded SB2s, which Gaia DR4 (2 December) will publish with epochs for every source.

## Batch 2 (rule unchanged)

| Star | Gaia DR3 | G | P (d) | Dips (epoch time: mag below median, phase; conjunction phase) | TESS status |
|---|---|---|---|---|---|
| **CD-44 6966** (F2, TIC 178414920) | 5387577190509272832 | 9.90 | 2.38722 | 2103.4121: 0.051, 0.0627; 2313.4859: 0.053, 0.0621 (c2 = 0.0557). Variability-flagged: 2620.6687: 0.032, 0.7403 | IJspeert EB candidate (their P = 1.1938 = P/2) |
| **V1229 Tau** (HD 23642, Pleiades) | 66729880383767168 | 6.82 | 2.46119 | 1709.1015: 0.034, 0.3501; 2577.8869: 0.030, 0.3448 (c2 = 0.3607) | known eclipsing binary (positive control) |

The other 13 stars have no dips and no faint flagged epochs. Notes:
- CD-44 6966: the two dips are 210 days (88 orbits) apart and land 0.0006 in phase from each other.
  Gaia's conjunction time is poorly fixed here (t_periastron error 0.52 d, 0.22 in phase), so the
  agreement with the conjunction is partly luck; the agreement with TESS (below) is the real test.
  One more epoch (1689.1946, 0.024 mag, phase 0.548, c1 = 0.557) sits just under the threshold.
- Gaia DR3 911500121588495744 (TIC 188378024, an IJspeert EB) has no rule dip, but its three
  faintest epochs (0.013-0.016 mag) fall at phases 0.131-0.135, on conjunction c1 = 0.1346:
  a shallow eclipse below our 0.025-mag floor.
- Gaia DR3 3032388065085357440 (not in IJspeert's EB catalogue) varies smoothly by about 0.07 mag,
  faint near both conjunctions (e.g. 1802.4759 at phase 0.930 vs c2 0.930) and bright near
  quadrature: ellipsoidal variation or wide eclipses. The rule (threshold 0.11 mag for this scatter)
  does not count it. Not claimed.

## Timing against TESS (IJspeert et al. 2024 ephemerides; `tess_offset` in the code)

| Star | Gaia epoch | Offset from predicted TESS eclipse (d) | Period used |
|---|---|---|---|
| HD 218299 | 1937.1285 (0.072 mag) | +0.0006 | Gaia P/2 |
| HD 218299 | 2237.6796 (flagged, 0.069 mag) | +0.0002 | Gaia P/2 |
| HD 101167 | 1951.0272 / 2321.0710 | +0.020 / +0.026 | Gaia P |
| CD-44 6966 | 2103.4121 / 2313.4859 | +0.034 / +0.033 (Gaia P/2); +0.012 / +0.014 (TESS-only P/2 from their two t0) | |
| V1229 Tau | 1709.1015 / 2577.8869 | +0.018 / +0.005 from the secondary eclipse | Gaia P |
| 911500121588495744 | three faintest epochs | -0.032, -0.040, -0.044 | Gaia P/2 |

The propagation uncertainty is 0.01-0.03 d in each case. Gaia's G epochs and TESS see the same
eclipses, three to six years apart.

## Two problems found in earlier work

- **V1202 Cen is not a clean check star.** TESS (IJspeert: 15.578 d / 7.758 d) and VSX (15.5543 d)
  agree on a ~15.56-day eclipse period, not Gaia's 3.3497-d SB2 period, and Gaia's two faint epochs
  are a single event 0.07 d apart. Its 'dips at the Gaia conjunction' in batch 1 may be chance.
  We no longer use it as a control.
- **Gaia DR3 1853022343761824768** is an IJspeert EB at 5.763 d, which is 2.023 times its Gaia SB2
  period: the TESS signal is not at Gaia's period (a blend, a third star, or a wrong Gaia period).

## Precision and recall of the Gaia-only rule (31 ACV SB2s read, P 2.0-4.02 d)

- In IJspeert's EB catalogue: 9 of 31 (query of `obaf-eb1` by Gaia DR3 id, 24 Nov).
  The 22 others are not in it.
- Rule dips: 6 stars (HD 218299, HD 101167, HD 187301, V1202 Cen, CD-44 6966, V1229 Tau), all 6 in the
  catalogue. Precision 6/6 (3 borderline single epochs in other stars were not counted by the rule).
- Recall among the 7 catalogue EBs whose TESS period equals Gaia's P, P/2 or 2P: 5/7 (missed:
  911500121588495744, shallow; 265213581990291840, smooth 0.02-mag modulation).
- Small numbers; selected class (ACV); bright stars. It is a check of the method, not a census.

## Limits

- IJspeert's table on VizieR is labelled "TESS_OBAF_EB_catalogue (partial)". The queued job
  `candidate-vet-v1` reads their full Zenodo copy (OBAF_EB.csv) and every Eclipses by Appointment
  file, with controls; it will confirm or correct the 'not in it' results above.
- Epochs were transcribed from ESA DataLink through a text tool; row counts match ESA's listings.
  The unit tests (`test_gaia_conj_dips_acv2.py`) assert the hand-computed values.
- The ACV class was chosen after we saw two ACV stars with dips; batch 2 is the first out-of-sample
  test of that choice, and it passed, but on stars TESS had already caught.

## Closest prior work on the method (web search, 24 Nov)

- [arXiv:2310.12380](https://arxiv.org/abs/2310.12380) (refutation of K2-256b with Gaia DR3 NSS)
  predicts conjunction times from Gaia DR3 spectroscopic (SB1) orbits to vet transit candidates, and
  calls the timing match its least reliable test because of propagated errors.
- [Beck et al. 2023, arXiv:2307.10812](https://arxiv.org/abs/2307.10812) compare Gaia epoch
  photometry with TESS/Kepler for oscillating stars in Gaia DR3 binaries; they report a real
  secondary eclipse caught in Gaia epochs and an artefact 'eclipse' in another star.
- What this note adds: Gaia epochs scored against Gaia double-lined conjunctions as a detector, with
  a frozen rule tested out of sample, and its precision and timing measured against a TESS catalogue.

## Catalogue and data sources

IJspeert, L. W. et al. 2024, A&A 691, A242, doi:10.1051/0004-6361/202450507
(VizieR J/A+A/691/A242, tables `tessobaf` and `obaf-eb1`, CfA mirror, read 24 Nov 2026);
data/ijspeert2024-check/ijspeert_check.csv lists every row we used. Eclipses by Appointment:
github.com/Snowstar38/eclipses-by-appointment, accepted-systems.csv at 19fadae.
