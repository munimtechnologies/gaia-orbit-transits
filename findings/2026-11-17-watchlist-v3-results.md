# Results: watch-list re-run with dipsearch 0.4.3 (job gaia-watchlist-tess-v3)

By MV2 of Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Graded 2026-11-17 (run 13). Code: run_search 0.4.1 with dipsearch 0.4.3 (flux floor
padded by 0.5 d, box-coherence cut). Same 25 Gaia DR3 stars as v1/v2. Run time 59 min.
The two plots named below are in `findings/plots/watchlist-v3/`.

## Grades of the predictions written in `2026-11-17-watchlist-v2-results.md`

| # | prediction | result | grade |
|---|---|---|---|
| W1 | no event deeper than 20,000 ppm remains on TIC 41898425, 274419322, 100106544 or 322271767 | deepest: TIC 41898425 5,532 ppm; TIC 274419322 3,552 ppm; TIC 100106544 884 ppm; **TIC 322271767 98,065 ppm** (BTJD 3856.395, 2 h, SNR 658) | **FAIL** (3 of 4 cleaned) |
| W2 | the Sector 69 event on TIC 41898425 (BTJD ~3192.3, ~2,100 ppm) is still reported | reported: BTJD 3192.346, 1,961 ppm, 4 h, SNR 13.4 (it passed the coherence cut; the coherence value itself is not written to events.csv) | **PASS** |
| W3 | coverage unchanged (66 windows, 0.177 expected eclipses) | 65 windows, 0.1766 expected eclipses | **FAIL** (narrow) |

### Why W3 failed
The reasoning behind W3 ("coverage does not depend on the dip search") was wrong. The
0.5-d pad around sub-floor cadences removes good-looking cadences too, and coverage is
computed from the cadences left after cleaning. One predicted window lost its coverage.
The effect on the expected number of eclipses is 0.2%.

### Why W1 failed: a third artefact type, dips next to short data gaps
The 0.4.3 fixes did what they were designed to do. The floor ramps on TIC 41898425 and
TIC 274419322 are gone (their deepest events fell from 221,197 and 76,091 ppm to 5,532 and
3,552 ppm), and so is the one-bin spike that W1 was written for. The event that survives
on TIC 322271767 is a different thing:

- **TIC 322271767, BTJD 3856.35–3856.45** (`plots/00_6345830951689788672.png`): the
  first four 30-min bins after a ~0.3-d gap sit at 0.93, 0.93, 0.92 and 0.80, and the
  flux is back to 1.0 an hour later. The box is filled, so its coherence is low (≈0.5)
  and it passes the cut.
- **TIC 231290240, BTJD 3967.33–3967.50** (`plots/02_4748772376561143424.png`; not part
  of W1): the flux falls by 0.7% over the 4 h before a ~0.17-d gap and comes back 0.1%
  *above* its old level after it. The same star also has a 2-h, 24% "dip" at BTJD
  3975.61, which is another gap-edge cadence group.

Neither looks like a companion transit. On TIC 322271767 the predicted duration is
10.5 h, and the dip starts exactly when the data start again. On TIC 231290240 the flux
level jumps across the gap. Both gaps are shorter than the 0.5 d that splits the light
curve into segments, so the `near_edge` flag (which marks dips at segment edges) does not
catch them. These are pointing and thermal settling around short interruptions, such as
momentum dumps and data downlinks.

## Fix planned: dipsearch 0.4.4
1. Any gap longer than 0.1 d counts as an edge for the `near_edge` flag, not only the
   0.5-d segment gaps.
2. Cadences within 0.25 d after any gap longer than 0.1 d are dropped, and so are those
   within 0.25 d before it, in the same way as the 0.4.3 floor pad.
3. New unit tests: a 2-h, 8% step down right after a 0.3-d gap, and a 4-h, 0.7% ramp
   before a 0.17-d gap. Both must disappear, while a 6-h flat transit placed 1 d from any
   gap must still be recovered.

0.4.4 will be used for the Gaia DR4 release-day search (2 December 2026). The full DR3
search (v4) and the pre-registered inclination calibration (`calib_eclipse_rate.py`) keep
their registered rules. The calibration measures this kind of false alarm with its
control phases half-way between conjunctions, and every detection it reports will be
checked by eye for gap-edge dips before any single system is named (see
`2026-11-17-calib-v2-amendment.md`).

## Honest summary
Two of three predictions failed. One failure came from wrong reasoning about the coverage
(W3), and the other from an artefact type we had not seen before (W1). The search found
no transit at a Gaia-predicted conjunction among these 25 stars. That is still the
answer of the v1 grading: the summed transit probability inside the TESS data is only
0.18.
