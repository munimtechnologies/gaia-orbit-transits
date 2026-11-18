# Results: archival photometry test of the Gaia-predicted transits (gaia-archival-v2)

2026-11-18. MV2 of Munim, Inc.; made with AI agents working in his name. Text CC BY 4.0,
code Apache-2.0. Graded against `findings/2026-11-17-archival-prereg.md` (predictions
A1–A7) and the 0.4.1 amendment (`findings/2026-11-17-v4-amendment.md`). Job:
`gaia-archival-v2` (archival.py 0.4.1), finished 2026-11-18 02:05 UTC after 38.6 min.
Raw output: `data/archival-v2/`.

## Bottom line

**No transit was found at the times the Gaia DR3 orbits predict, in any of the 23
watch-list stars with archival light curves.** Five of the 34 hypotheses crossed the
detection threshold. All five are artefacts: TESS segment-start ramps, a three-point dropout
just before a data gap, or "dips" 20–65 times shallower than the predicted depth. Five of
the seven pre-registered predictions pass. A5 (number of false alarms) and A6 (coverage at
short periods) fail.

Summed over the watch list, the expected number of transiting companions falls from 0.28
(Gaia DR3 geometric priors) to 0.19 after the archival data. Finding none is consistent
with both numbers. It also fits the growing evidence from this project that Gaia DR3's
edge-on probabilities are too high (deepcheck-v1: KIC 6436291 excluded by Kepler, and a
p = 0.97 star does not eclipse). The formal calibration (`gaia-calib-v3`) is still queued.

## Grades

| # | Prediction | Result | Grade |
|---|---|---|---|
| A1 | 393581461455623296: `cov_any` ≥ 0.8 | 0.95 | **PASS** |
| A2 | Recovery at the predicted depth between 0.2 and 0.8 | 0.45 | **PASS**, with a caveat (below) |
| A3 | No candidate for 393581461455623296 | best SNR 4.31 against a threshold of 7.92; FAP 0.74 | **PASS** |
| A4 | Transit probability falls from ~7% to 3–6% | 8.3% → 4.7% | **PASS** |
| A5 | 0–2 hypotheses cross the threshold, and any that do fail vetting | 5 crossed; all 5 fail vetting | **FAIL** (count) |
| A6 | Median `cov_any` < 0.5 for P > 300 d, and > 0.8 for P < 200 d | 0.22 (19 hypotheses) and 0.64 (5 hypotheses; 0.71 per star) | **FAIL** (the P < 200 d half) |
| A7 | ≥ 20 of 25 stars have at least one archival light curve | 23 of 25 | **PASS** |

**Caveat on A2.** The pre-registration expected a depth of about 1.5–2.5%, assuming a
brown-dwarf companion (~0.074 M☉). The job's own mass estimate came out at 0.139 M☉, so
its "predicted depth" for a low-mass star companion is 6.6%. Recovery is 0.45 at 6.6%,
0.03 at 3.3% and 0 at 1%. **For a brown-dwarf-sized transit, the archival data of this
star constrain almost nothing.** The new fall in transit probability rests almost entirely
on the stellar-companion case. ZTF r scatter at G = 12.7 (~1.5%) is the limit, as
predicted. Ground photometry at ~2 mmag in the 2027 windows remains the real test.

**On A6.** The P < 200 d group is small (four stars). One of them (4422729073976768640)
has only 19 days of data (TESS only; it lies south of ZTF), which drives the median down.
The P > 300 d half passed as predicted.

## Vetting of the five threshold crossings

| Gaia DR3 | conj | SNR / thr | fitted vs predicted depth | what it is |
|---|---|---|---|---|
| 2960647744567925632 | t1 | 42.09 / 42.00 | 1.87% (a ramp) vs 2.57% | Starts at the first cadence of TESS S98 QLP (t = 3988.51 BTJD). The flux ramps up from 0.981 over a day: a segment-start systematic. The same ramp set the null threshold in 9 of 30 null runs (null max 42.005 each time). The observed SNR beats it by 0.2%, which is a tie, not a detection. |
| 4955501899980809088 | t2 | 77.1 / 69.6 | 3.07% vs 3.16% | Three TESS points (0.93–0.97) right before a data gap, then a flat light curve. A pre-gap dropout. The matching depth is a coincidence: one epoch, n = 3. |
| 2744694491118490752 | t1, t2 | 10.64 / 10.40 and 10.13 / 9.91 | 0.05% vs 1.05% | A 0.08% downward ramp at the start of a TESS segment. 20× shallower than predicted, and a tie with the threshold. Both conjunction hypotheses hit the same feature. |
| 4858390078077441920 | t1 | 7.21 / 6.19 | 0.07% vs 4.56% | A broad 0.1% depression in TESS, at the −3.5σ edge of the period grid. 65× shallower than predicted. Recovery at this star is 0.00, so the search could not have seen the predicted transit anyway. |

None of these is a transit of the predicted companion. Nothing is reported to any
channel.

**393581461455623296 (the flagship star).** The best cell is a clump of 7 ZTF r points,
~3% low, across 4 epochs (SNR 4.3). That is below the median of the null runs (4.9), so
it is ordinary ZTF noise at this brightness.

## What this test taught us (fixes before the Gaia DR4 run on 2 December)

1. **Segment edges and gaps dominate false alarms in TESS.** Three of the four stars
   failed on an edge or pre-gap artefact. dipsearch 0.4.4 already has an opt-in gap-edge
   mask. archival.py needs the same: drop TESS points within 0.5 d of a segment start or
   end and within 0.25 d of a gap longer than 0.5 d.
2. **Ties with the null maximum are not detections.** When the observed peak and the
   null maximum come from the same feature, "obs > max(null)" is a coin toss, not a 1/31
   false-alarm probability. Require the observed SNR to beat the null maximum by a
   margin (≥ 10%), and use n_null ≥ 100.
3. **Depth consistency.** A candidate whose fitted depth is below 0.3× the predicted
   depth (for the companion's mass) should be labelled "inconsistent depth", not
   "candidate". Two of the five would have been removed this way.
4. **Empty-data crash.** For 2917589945811558144 (P = 2406 d) no light curve was found,
   and scan() crashed on an empty grid (`argmax of an empty sequence`) instead of
   reporting "no data". This is a one-line guard.
5. The predicted-depth calculation should report the brown-dwarf case as well as the
   companion-mass case when m2 is close to 0.08 M☉. That is the case the forecast cares
   about.

These are A5's lessons. The grade stays FAIL: the threshold was pre-registered, and the
fixes apply only to future runs, behind new options, so queued jobs are unchanged.

## Files

- `data/archival-v2/archival_report.md`, `archival_results.csv`, `run_summary.json`
- `data/archival-v2/plots/`: the five threshold crossings and the flagship star.
