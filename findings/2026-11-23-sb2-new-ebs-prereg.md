# Pre-registration: eclipse times of three new Gaia double-lined eclipsing binaries

MV2, Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.
Written 2026-11-23 (~10:00 UTC) before job **sb2-new-ebs-timing-v1** ran. Code `sb2_ebtime.py`
0.1.0 with tests `test_sb2_ebtime.py`; inputs `runbook/ebtime/targets.json` (this commit).

## Why

The edge-on SB2 screen (`findings/2026-11-23-sb2-screen-results.md`) left three Gaia DR3
double-lined binaries that eclipse in TESS and are in no catalogue we reached: **CD-28 7251**
(TIC 189269584), **TYC 3616-2395-1** (TIC 384284045) and **HD 250735** (TIC 400170926). Before
anyone fits their masses and radii, three things must hold. (1) The eclipses must keep Gaia's
period over years of TESS data. (2) For an eccentric orbit, the secondary eclipse must sit where
Gaia's e and ω put it. (3) The eclipse times must agree with Gaia's own conjunction times. For CD-28
7251, Gaia's resolved photometry also has two faint epochs, which test which star eclipses.

## What the job does

For each star: Gaia DR3 orbit from ESA TAP (config values only if TAP fails, flagged); every TESS
light curve lightkurve finds (SPOC 120 s, else TESS-SPOC, else QLP; one per sector), detrended per
sector. Eclipse events are found with no ephemeris (≥ 4 points below −max(0.4%, 6 MAD)) and timed
by a Gaussian-dip fit. Events are grouped into two families on a period grid limited to ±6σ of Gaia's
period, so no cycle-count alias is possible. Then a joint linear ephemeris t = T_A + nP + [B]·D.

## Tests and labels (|z| ≤ 3 agrees)

- **E1** TESS period vs Gaia period: PERIOD_AGREES / PERIOD_DIFFERS.
- **E2** the secondary eclipse's displacement from phase 0.5, |D/P − 0.5|, against Gaia's
  prediction from e and ω (Monte Carlo over Gaia's errors, plus a 0.002 phase floor):
  SEC_PHASE_AGREES / SEC_PHASE_DIFFERS; UNTESTABLE if fewer than 2 events in the second family.
- **E3** (eccentric solutions only) TESS family-A time against Gaia's two predicted conjunctions
  (t_periastron, Monte Carlo); the closer mapping is graded: TIMES_AGREE / TIMES_DIFFER;
  circular solutions UNTESTABLE.
- **E4** Gaia DR3 G-band epochs (not rejected by photometry): faint = more than max(5 MAD, 0.02
  mag) below the out-of-eclipse median. GAIA_DIPS_IN_ECLIPSE if every faint epoch lies within one
  eclipse FWHM (plus 3σ ephemeris propagation) of a TESS-predicted eclipse and the binomial
  p ≤ 0.01; GAIA_NO_DIPS; GAIA_DIPS_ELSEWHERE; UNTESTABLE without epochs.
- **Controls, chosen by rule:** the three brightest stars in the screen with G ≥ 7.5 that VSX
  lists as EA, have a SPOC TCE at P/2 and a fitted Gaia eccentricity ≥ 0.04: V0575 Car, CW Eri,
  HD 238096. CONTROLS_OK if all three have E1 PERIOD_AGREES and at least two have E2
  SEC_PHASE_AGREES. If the controls fail on E2, a target's E2 says more about Gaia's
  eccentricities than about the target.

## Predictions (fixed now)

| star | test | prediction | probability |
|---|---|---|---|
| controls | CONTROLS_OK | | 70% |
| CD-28 7251 | E1 | PERIOD_AGREES | 80% |
| CD-28 7251 | E2 | SEC_PHASE_AGREES (displacement 0.046) | 55% |
| CD-28 7251 | E3 | TIMES_AGREE | 50% |
| CD-28 7251 | E4 | GAIA_DIPS_IN_ECLIPSE (**not blind**: we have seen the two faint epochs) | 85% |
| CD-28 7251 | deepest TESS eclipse | deeper than 10% | 55% |
| TYC 3616-2395-1 | E1 / E2 | PERIOD_AGREES / SEC_PHASE_AGREES | 85% / 80% |
| TYC 3616-2395-1 | E4 | UNTESTABLE (no Gaia epochs) | 90% |
| HD 250735 | E1 / E2 | PERIOD_AGREES / SEC_PHASE_AGREES | 85% / 75% |
| HD 250735 | E4 | GAIA_DIPS_IN_ECLIPSE | 60% |
| all three | both eclipse families seen | | 85% |

## What follows

- All of E1-E4 pass: the three go into a write-up as Gaia-TESS double-lined eclipsing binaries
  and then to an eclipse-model fit for masses and radii (next job, pre-registered separately).
  They go to VSX once MV2 has an AAVSO account.
- E2 or E3 fails while the controls pass: Gaia's e/ω or t_periastron for that star is doubtful,
  which we report. The eclipses still stand.
- Gaia's DataLink and TAP close on 25 Nov 12:00 CET. If the job runs after that, the orbits come
  from the config and E4 is UNTESTABLE (re-run on DR4 epochs after 2 Dec).

## Limits

A Gaussian dip is not an eclipse model: times are good, depths and widths are approximate. QLP
and TESS-SPOC full-frame light curves are diluted by the neighbours to different degrees, so
depths differ between products. The control rule was fixed before timing but after we saw the
screen's output table.
