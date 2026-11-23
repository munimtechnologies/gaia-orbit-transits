# Results: which of Gaia DR3's edge-on double-lined binaries eclipse in TESS?

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0, code Apache-2.0. Written 2026-11-23 (~10:00 UTC) after job
**sb2-edgeon-screen-v1** (`sb2_screen.py` 0.1.0, commit 0a8883c9) ran on 23 Nov, 06:27-07:29 UTC.
Pre-registration: `findings/2026-11-22-sb2-screen-prereg.md`. Data: `data/sb2-edgeon-screen-v1/`
(job outputs, unchanged) and `data/sb2-new-ebs/` (vetting after the run).

## In short

- The screen ran on **183** edge-on Gaia DR3 double-lined (SB2) orbits with P < 8 d. **66** have a
  qualifying TESS SPOC detection (TCE). **46** of them are at half the Gaia period, 10 at the
  period and 10 at neither.
- After vetting, **two more Gaia binaries join HD 250735 as eclipsing binaries we found in no
  catalogue: CD-28 7251 (TIC 189269584, an A3m star, G 8.86) and TYC 3616-2395-1 (TIC 384284045,
  G 10.47).** Each is a double-lined eclipsing binary whose two masses Gaia's orbit already
  constrains, which makes them candidate benchmark stars.
- For CD-28 7251 the eclipses are also in **Gaia's own resolved photometry**: two dips of 0.27 and
  0.19 mag, 7.004 d apart (one orbit is 6.961 d), both close to one of the two conjunctions that
  Gaia's own spectroscopic orbit predicts. So the 46″ brighter neighbour cannot be their source.
- Two of our predictions failed (S0, S1), and the screen's own "new" list was too long: 3 of its 8
  "new" stars are in the TESS EB catalogue, because every lookup of that catalogue failed (HTTP 400).

## Grades (as registered)

| test | result | label | prediction |
|---|---|---|---|
| S0 replication | 183 selected (184 expected); 18 of 20 pilot stars | **DIFFERS** | REPLICATES 80%: **wrong** |
| S1 twin eclipses | 46 of 66 at P/2 = 0.70 (95% 0.58-0.79) | **MIXED** | HALF_DOMINANT 75%: **wrong** |
| S2 new, outside pilot | 6 by the job's rule; **2 after vetting** | ≥ 1: YES; ≥ 3: YES by the rule, **no after vetting** | ≥ 1: 75% (right); ≥ 3: 45% |
| S3 positive control | 44 of 44 VSX eclipsing stars with a TCE are at P or P/2 | **CONTROLS_OK** | 85% (right) |
| pilot | TIC 400170926 (HD 250735) comes out NEW | yes | 85% (right) |

Source: `data/sb2-edgeon-screen-v1/sb2_screen_summary.json`. 161 stars were tested, 22 had no TIC
match and 95 had no qualifying TCE (SPOC only searches 2-minute targets, so "no TCE" does not mean
"no eclipse").

**Why S0 differs (traced after the run):** the two missing pilot stars (Gaia DR3
2227350905632198656, e = 0.318, and 5191259080130349056, e = 0.287) are the two most eccentric
pilot stars. The registered rule includes the factor (1 − e²)^1.5 in M1 sin³i; the pilot had left
it out. With the factor their ratios fall to about 0.83 and 0.89, below the 0.95 cut. The screen
applied the registered rule correctly; the pilot sample was slightly wrong.

**S1:** a fifth of the matched stars eclipse at the Gaia period instead of half of it (unequal
eclipses, or eccentric orbits where only one eclipse is seen). Only 10 of 66 show TCEs at neither,
so Gaia's SB2 periods are almost always right for eclipsing systems (S3 is 44 of 44).

## Vetting of the 8 stars the job called NEW

The job's prior-art check of the Villanova TESS EB catalogue failed for every star (HTTP 400 on
all 56 matched stars; the log shows three retries each), and by the registered rule an unreachable
source counts as "not found". We therefore checked all 8 again by hand on 23 Nov (`data/sb2-new-ebs/vetting.csv`):
the TESS EB catalogue (Prša et al. 2022) and the TESS Ten Thousand catalogue (Kostov et al. 2025)
through VizieR's CfA mirror (both queries returned control rows), SIMBAD's Harvard mirror, VSX, the
ASAS-SN variable-star catalogue (II/366, control row found), ExoFOP and a web search.

| star | verdict |
|---|---|
| HD 21273 (TIC 79548760) | known: Prša et al. 2022 (P 7.97197 d) |
| HIP 34208 (TIC 238162238) | known: Prša et al. 2022 (pilot; already known there) |
| BD+83 227 (TIC 137501278) | known: Prša et al. 2022, catalogued at 2.13539 d, half the true 4.2709 d period |
| BD+37 3347 (TIC 121083955) | known: Kepler object KOI-3161 |
| HD 144359 (TIC 17342647) | a known heartbeat star in VSX; its 304 ppm TCE is not an eclipse discovery |
| **HD 250735 (TIC 400170926)** | **new** (pilot; `findings/2026-11-22-tic400170926-eclipsing-twin.md`) |
| **CD-28 7251 (TIC 189269584)** | **new as an eclipsing binary** (VSX lists only Gaia's generic "VAR" import) |
| **TYC 3616-2395-1 (TIC 384284045)** | **new** (in no variable-star catalogue we reached) |

## The two new eclipsing binaries

**CD-28 7251** (Gaia DR3 5633392634307163776, TYC 6600-985-1, SAO 177435; RA 141.43487,
Dec −29.32699; spectral type A3m; 466 pc; ExoFOP: Teff 7942 K, R 4.4 R_sun by TIC).
- Gaia DR3 SB2 orbit: P = 6.96109 ± 0.00015 d, e = 0.076 ± 0.008, ω = 343° ± 7°,
  K1 = 79.8 ± 1.2 and K2 = 94.7 ± 0.9 km/s. M sin³i = 2.06 and 1.74 M_sun (our calculation from
  the orbit). Gaia's goodness of fit is high (11.1), so its errors may be underestimated.
- TESS SPOC (sector 62 only, 2-minute): TCE at 3.47917 d (P/2 within 0.04%), 8 events. The DV
  model fit did not converge (S/N not given), and the pipeline depth is 3.06%.
- **Gaia's own G-band photometry (47 epochs, none rejected) shows two dips:** 9.129 mag at BTJD
  233.384 (followed 1.8 h later by 8.983) and 9.050 at BTJD 240.388 (then 8.913), against a median of
  8.861. Data: `data/sb2-new-ebs/cd-28-7251_gaia_dr3_epoch_g.csv` (read from ESA's DataLink through
  a web reader on 23 Nov; the queued job downloads it again with code).
- **Exploratory hand calculation (not blind):** Gaia's orbit puts one conjunction (true anomaly
  270° − ω) at BTJD 393.670 + n × 6.96109 (t_periastron BTJD 387.961, phase 0.8201 after
  periastron) and the other at phase 0.2738. The two Gaia dips fall 0.18 d and 0.14 d before the
  first of these, against an uncertainty of about 0.19 d from Gaia's t_periastron and ω errors
  (correlations ignored). The other conjunction is 3.3 d away from both. Gaia's orbit predicts that
  the two eclipses are not half an orbit apart but 0.546 / 0.454 of it (e cos ω = 0.073). That may be why
  SPOC's fit at exactly P/2 did not converge and returned a shallow depth. The queued job tests this.
- Neighbour: Gaia DR3 5633392252052067968 (G 8.75, 46″, VSX type ACV|roAp from Gaia) dilutes
  TESS (ExoFOP contamination ratio 1.77). It cannot make dips in Gaia's resolved photometry of
  the target, and an eclipse on it would not fall at the target's spectroscopic period.

**TYC 3616-2395-1** (Gaia DR3 1980920834829359488; RA 327.54603, Dec +51.80021; 208 pc; ExoFOP:
Teff 5776 K, R 1.47 R_sun, contamination 0.09).
- Gaia DR3 SB2 orbit: P = 3.787087 ± 0.000049 d, circular (e = 0.002 ± 0.008), K1 = 91.5 ± 0.9,
  K2 = 85.3 ± 0.9 km/s. M sin³i = 1.05 and 1.12 M_sun: two Sun-like stars.
- TESS SPOC (sector 57): TCE at 1.893481 d = P/2 within 0.003%, 2.69% deep, S/N 228, 14 events,
  converged fit with impact parameter 0.95 (grazing in a planet model). No Gaia epoch photometry.
- The ROSAT source 1RXS J215010.4+514808 lies 9.4″ away (within ROSAT's position errors), as
  expected for an active short-period binary of Sun-like stars; we have not tested the association.

## What this means

Gaia DR3's double-lined orbits plus TESS's pipeline detections turn up bright eclipsing binaries
that are still uncatalogued: three among 183 edge-on systems (one per 61), at G 8.9-10.5. Each comes
with both stars' velocity amplitudes, so an eclipse fit gives both masses and radii. The same screen
runs on Gaia DR4's SB2 list on 2 December (runbook step g5), with the Villanova lookup replaced by
the VizieR copy of the TESS EB catalogue.

## Next (pre-registered separately)

`findings/2026-11-23-sb2-new-ebs-prereg.md`, job sb2-new-ebs-timing-v1: eclipse times of the
three new binaries and three control binaries in every TESS sector. Does the TESS period match
Gaia's? Is the secondary eclipse displaced as Gaia's e and ω predict? Do the conjunction times
match? Are Gaia's faint epochs inside the predicted eclipses?

## Limits

TCE depths and periods come from SPOC's planet-model fits. The CD-28 7251 phase argument is a hand
calculation that ignores the correlations between Gaia's orbital elements. Our list of catalogues
is long but not exhaustive (for example, no search of ASAS-SN's full light-curve database or of
non-English literature). VSX submissions need an AAVSO account, which MV2 does not have yet.
