# Results: watch-list re-run with the 0.4.2 flux floor (job gaia-watchlist-tess-v2)

By MV2 of Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Graded 2026-11-17. Code: run_search 0.4.1 with dipsearch 0.4.2. Run time 6.5 min.

## What was being tested
The first watch-list run (`2026-11-17-watchlist-results.md`) found that six of its seven
dips with Bayes factor > 3 were broken QLP cadences in Sector 104, where the flux falls to
~10% at the start and end of each orbit. dipsearch 0.4.2 drops cadences below half the
median flux. The re-run had one job: show that the Sector 104 artefacts are gone and that
nothing else changes.

## Result: partly fixed, not gone
| | v1 (0.3.0) | v2 (0.4.2) |
|---|---|---|
| events (SNR ≥ 7) | 176 in 19 stars | 174 in 18 stars |
| deepest TIC 41898425 event (S104) | 763,868 ppm, SNR 7,348 | 221,197 ppm, SNR 1,226 |
| deepest TIC 274419322 event | 909,991 ppm, SNR 8,985 | 76,091 ppm, SNR 707 |
| deepest TIC 100106544 event (S104) | 299,404 ppm, SNR 2,427 | 33,122 ppm, SNR 138 |
| events with BF > 10 | 1 | 1 |
| coverage numbers (0.177 expected eclipses, 66 windows) | unchanged | unchanged |

The floor removed the 10%-flux cadences themselves, as designed. But the light curve
ramps down to the floor and back up over ~0.3 d on each side (TIC 41898425, BTJD
4192.0–4192.2 and 4192.75–4193.0; plot `plots/01_4984264505688458112.png`). Those ramp
cadences sit between 50% and 99% of normal, pass the floor, and still make 3–22% "dips"
at SNR in the hundreds. The same happens at the orbit edges of TIC 274419322 (BTJD
4139, 4152, 4165, 4178: the four ends of two TESS orbits).

A second artefact type is now visible at the top of the list. On TIC 322271767 (Gaia DR3
6345830951689788672) the 2-h "dips" of 7–10% at BTJD 3856.4 and 3869.4 are one or two
scattered 30-min bins (one bin at 0.82, its neighbours at 0.93–1.0;
`plots/00_6345830951689788672.png`). A companion transit cannot look like that: a 2-h
box is far shorter than the ~10.5 h predicted duration, and the in-box values jump around
by about as much as the depth itself.

**Grade of the v2 goal ("the S104 artefacts are gone"): FAIL.** No real dip was lost
or gained. Every event above 20,000 ppm in v2 is one of the two artefact types.

## Fix: dipsearch 0.4.3
1. **Pad around the floor.** Every cadence within 0.5 d of a sub-floor cadence is dropped
   too. That covers both ramps seen on TIC 41898425 (each ~0.3 d).
2. **Box coherence.** Coherence = in-box standard deviation of the residuals / box-mean
   depth. For a flat dip that fills a fraction p of the box it is sqrt((1−p)/p): 0 when
   the box sits inside the dip, 1.0 when half filled, and sqrt(k−1) for a one-bin spike
   in a k-bin box. A fully filled V-shaped (grazing) dip gives 0.58. Boxes above 0.75
   (less than ~64% filled) whose in-box scatter is also more than three times the
   per-bin noise are dropped before the events are de-duplicated. Every dip lasting at
   least the shortest box (2 h) has a box inside it with coherence ~0, so real dips still
   come through. The TIC 322271767 box (bin deficits 0.18, 0, 0.07, 0.06) has
   coherence 0.84 and is dropped.
3. **Cost:** dips shorter than ~1.3 h are no longer reported. No target of this project is
   that short. A brown dwarf on a > 10-day orbit transits a dwarf star for several hours.

New unit tests reproduce both artefacts (a 0.6-d floor with linear 0.3-d ramps; a single
30-min bin at 0.8). They show that each artefact is found without the fix and gone with
it. A 3-h flat dip and an 8-h V-shaped grazing dip are still recovered.

## Next
- `gaia-watchlist-tess-v3` re-runs the same 25 stars with 0.4.3. Predictions, fixed now:
  - **W1.** No event deeper than 20,000 ppm remains on TIC 41898425, TIC 274419322,
    TIC 100106544 or TIC 322271767.
  - **W2.** The Sector 69 event on TIC 41898425 (BTJD 3192.26, ~2,100 ppm, 8 h) is still
    reported, with coherence ≤ 0.75. If 0.4.3 drops it instead, that by itself says the
    event is not transit-shaped: it would be recorded as a fail of W2, not hidden. Its
    vetting job (gaia-vet-41898425-v1) does not use this filter and is unchanged.
  - **W3.** The coverage numbers (66 windows, 0.177 expected eclipses) do not change,
    because they do not depend on the dip search.
- The full DR3 search (gaia-orbit-tess-v4, running) uses 0.4.1/0.4.2. Its top list must be
  read with these two artefact types in mind. The DR4 run on 2 December will use 0.4.3.
