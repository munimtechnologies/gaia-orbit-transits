# Pre-registration: TESS check of the 25-star substellar watch list (job gaia-watchlist-tess-v1)

Written 2026-11-17, before the job ran and before any TESS light curve of these stars
was looked at. By MV2 of Munim, Inc. Made with AI agents working in his name. CC BY 4.0.

## What runs

gaia-orbit-transits 0.3.0, with these arguments:

```
run_search.py --source-ids <25 watch-list stars> --gmax 17 --cosi-max 0.3 --min-p-ecl 0
              --mc 1000 --max-lcs 40 --window-plots
```

- The 25 stars are those in findings/2026-11-17-dr3-substellar-edge-on-watchlist.csv.
- For each star the job downloads every TESS light curve (SPOC, TESS-SPOC, QLP) and runs
  the single-event dip search.
- It lists every predicted conjunction window covered by TESS data
  (covered_windows.csv, ±3σ).
- It plots each covered window, marking the transit window identified from the
  radial-velocity orbit where there is one (findings/2026-11-17-sb1-transit-convention.md).

## Predictions

1. **Coverage.** At least 20 of the 25 stars have at least one usable TESS light curve.
2. **Few real tests so far.**
   - Fewer than 10 RV-identified transit windows fall inside TESS data at 1σ
     (`n_in_1sd` > 10 binned points).
   - For Gaia DR3 393581461455623296, no RV-identified transit window has more than 10
     binned points within 1σ of its centre. All three predicted transits fell 1.8 to
     3.2σ after its sectors ended.
3. **Detections.** The expected number of covered transits is small: the summed
   geometric transit probability is well under 1 for long periods. The most likely
   outcome is **zero** dips with BF > 3 at an RV-identified transit window.
4. **If a dip does match an RV-identified transit window, it is a candidate only.** The
   vetting list:
   - depth versus the expected (R2/R1)²;
   - a duration consistent with P and the stellar density;
   - no matching dip at the occultation time;
   - TESScut centroids and neighbours;
   - VSX, SIMBAD and the TOI/CTOI lists.

A "no transit in the covered windows" result is reported as a constraint on cos i for
each star, not as a failure.
