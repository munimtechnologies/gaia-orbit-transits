# TIC 93622019: Gaia's own faint epochs sit in the TESS transits, and the 4:3 alias picked up three low outliers (exploratory)

2026-11-24, gaia-orbit-transits. By MV2 of Munim, Inc.; made with AI agents working in his name.
No human expert has checked this yet. Text CC BY 4.0, code Apache-2.0.

**Status: exploratory.** This is not the pre-registered test. The registered test of whether Gaia's
photometry shows TIC 93622019's dip at the TESS ephemeris is `vpt_epochs_extras.py tess`
(`findings/2026-11-22-vpt-epochs-amendment-2.md`, job gaia-vpt-epochs-box-v1, still waiting for
compute). Nothing here grades it, and its thresholds are unchanged. Our hand reading of what it will
find is given below as a stated expectation, so the job can prove us wrong.

## Why look now

TIC 93622019 (Gaia DR3 5345417757181174144, Tmag 12.20) has a flat-bottomed transit of about 1.3%
(deblended) every 2.1238933 ± 0.0000030 d in all six TESS sectors we searched (10 to 100;
`findings/2026-11-22-vpt-pf-dr3-results.md`, `findings/2026-11-22-tic93622019-pixel-results.md`).
Gaia DR3 lists it as a transit candidate with P = 2.8316579 d, which is 4/3 of the TESS period
(ratio 1.33324). ESA's Gaia archive closes on 25 November until DR4, so we read Gaia's
transit row again (AIP TAP mirror) and checked, by hand, every Gaia epoch against both ephemerides.

## Data

- Epochs: the 67 Gaia DR3 G-band rows that job gaia-vpt-epochs-v2 saved in
  `data/vpt-epochs-v2/epochs_g_2.csv` (identical to ESA DataLink, re-read 24 Nov). Two have no G
  value and five are rejected by Gaia's variability processing, which leaves 60, the same set the
  registered test uses.
- Gaia transit solution (vari_planetary_transit, AIP mirror, 24 Nov): reference time 2202.348946
  (Gaia time), P 2.8316579357 d, duration 0.18627 d, depth 11.90 mmag, num_in_transit 24.
- TESS ephemeris: T0 = BTJD 3706.08685 ± 0.00068, P = 2.1238933 ± 0.0000030 d (job
  tic93622019-pixel-v1). Gaia time = BTJD + 1802.5. Going back about 1,560 cycles to the middle of
  Gaia's data costs only ±0.0048 d (7 minutes) of timing uncertainty.
- Code: `tic93622019_gaia_epochs.py` 0.1.0 (stdlib). `test_tic93622019_gaia_epochs.py` asserts every
  set and count below. The publish lane ran those tests before committing this note, so the hand
  numbers have been machine-checked.

## What the epochs show

Window definitions: a TESS window is |t − transit| ≤ 0.0625 d (the registered test's 0.125-d
window), and the TESS core is |t − transit| ≤ 0.045 d. A Gaia box is |t − Gaia transit| ≤ half of
Gaia's 0.18627-d duration. Fluxes are relative to the median of the 60 epochs.

| Gaia time | BTJD | flux vs median | offset from TESS transit (d) | in Gaia's 2.83-d box? |
|---|---|---|---|---|
| 2029.6527 | 227.153 | −1.89% | +0.003 | yes |
| 2097.5920 | 295.092 | −1.26% | −0.022 | yes |
| 2097.6660 | 295.166 | −1.07% | +0.052 | yes |
| 2106.0961 | 303.596 | −1.25% | −0.014 | yes |
| 2106.1701 | 303.670 | −0.18% | +0.060 (egress) | no |
| 2258.9890 | 456.489 | −0.95% | −0.041 | yes |
| 2333.3100 | 530.810 | +0.17% | −0.056 (ingress) | no |
| 2409.0161 | 606.516 | −1.02% | TESS phase 0.618 | yes |
| 2544.8976 | 742.398 | −0.66% | TESS phase 0.596 | yes |
| 2578.8714 | 776.371 | −0.77% | TESS phase 0.592 | yes |

1. **All four epochs in the TESS transit core are faint by 0.95-1.89%.** The five epochs inside
   both the TESS windows and Gaia's box average 1.28% deep. That matches the deblended TESS depth of
   1.28% from the pixel job, measured with Gaia's ~0.4-arcsecond images rather than TESS's
   21-arcsecond pixels. The two other epochs in TESS windows sit 0.056 and 0.060 d from mid-transit,
   at ingress and egress, and are at normal brightness.
2. **Gaia's 2.83-d box holds the same five transit epochs plus three more**, at TESS phases
   0.59-0.62, which are 0.66-1.02% low. TESS rules out a 1% transit at 2.83 d: six sectors show the
   2.124-d signal alone, and our earlier fold at Gaia's period found nothing. So these three are not
   transits. Outside the TESS windows, 6 of the 53 epochs are 0.6% or more below the median (the
   other three are at Gaia times 1696.77, 2202.82 and 2373.79; the last is 0.071 d after a TESS
   transit and may be late egress). Gaia's period search, run over many trial periods, found the
   alias that keeps all five real transit epochs and adds three of these six low points. That is how
   a 4:3 alias can beat the true period on about 60 epochs.
3. **What we expect the registered test to report.** It uses the same 60 epochs and the same 7
   in-window epochs, so we expect a mean dip of about 0.9% (seven epochs, including the two
   edge epochs at normal brightness), S/N near 8 against a robust scatter of about 0.29%, and the
   label GAIA_SEES_TESS_EPHEMERIS. If it reports NOT_SEEN or UNTESTABLE, the job is right and this
   note is wrong.

## What this adds, and limits

- Gaia's DR3 transit detection of this star was already on-target at Gaia's resolution. What is new
  is that Gaia's faint epochs line up with the **TESS** ephemeris, carried back about 1,560 cycles
  (2014-2017), and that the alias can be traced to three specific low outliers. This is a
  necessary check before calling TIC 93622019 a TESS candidate that Gaia found first. It
  says nothing about the companion's mass. Gaia RVS shows no significant velocity change (p = 0.51),
  which leaves hot Jupiters, brown dwarfs and the lowest-mass stars open.
- Hand calculation, machine-checked by the unit tests but not by an independent pipeline. Window
  sizes are the registered test's. The 0.6% "low" threshold and the 0.045-d core are exploratory
  choices made while looking at the data.
- It is still a candidate, not a planet. It has no TOI or CTOI (ExoFOP checked 24 Nov), and it is
  not in the open Eclipses by Appointment catalogue (accepted-systems.csv and
  period-free-review.csv read in full at commit 3a46591, 24 Nov). Panahi et al. (2022,
  arXiv:2205.10197) say they found TESS full-frame signals for 21 of Gaia's 41 new candidates and
  refined their parameters, but they did not publish per-star periods. So their team may have seen
  this signal before us without reporting it.
