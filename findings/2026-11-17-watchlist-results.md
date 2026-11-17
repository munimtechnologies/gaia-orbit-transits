# Results: TESS check of the 25-star substellar watch list (job gaia-watchlist-tess-v1)

By MV2 of Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Graded 2026-11-17 against findings/2026-11-17-watchlist-prereg.md (written before the
job ran). Code: gaia-orbit-transits 0.3.0. Run time 24 min.

## What ran
- 26 near-edge-on Gaia DR3 orbit solutions for the 25 stars: 18 AstroSpectroSB1, 4
  Orbital, 3 OrbitalTargetedSearchValidated, 1 OrbitalTargetedSearch. All 26 Monte
  Carlos used the catalogue correlation vectors.
- 24 of 25 stars have TESS light curves. 176 dips at SNR ≥ 7 were found in 19 stars.
- 66 predicted conjunction windows (±3σ) contain TESS data; 25 of them are the transit
  window that the radial-velocity orbit identifies.
- Summed geometric probability of a transit inside covered data: 0.18 (0.18 with both
  conjunctions). So the honest expectation was "about one chance in six of any real
  transit in the data".

## Grades

| # | Prediction | Result | Grade |
|---|---|---|---|
| 1 | ≥ 20 of 25 stars have usable TESS data | 24 of 25 | **PASS** |
| 2a | < 10 RV-identified transit windows have > 10 binned points within 1σ | 14 | **FAIL** |
| 2b | 393581461455623296: no RV transit window covered within 1σ | none covered (only its non-transit conjunction, twice) | **PASS** |
| 3 | zero dips with BF > 3 at an RV-identified transit window | 7 such dips in 2 stars | **FAIL as written** (see below) |

Notes on 2a. Several of the 14 "covered" windows are not real tests: for
6042099591901745408 the 1σ window is 56 to 143 days wide, and a 27-day sector inside
it tests only a fraction of the allowed times. Coverage counts are not test power; the
archival job (gaia-archival-v2) does the proper posterior-weighted version.

## The BF > 3 dips: what they are
- **Six of the seven are broken data, not dips.** TIC 41898425 (Gaia DR3
  4984264505688458112) and TIC 100106544 (4955501899980809088) were both observed in
  Sector 104, where the only product is QLP. In that product the flux falls to about 10%
  of normal for ~0.7 d at the start and end of each orbit (BTJD ~4179 and ~4192), and
  these cadences are not removed by the default quality mask. "Depths" of 30-90% at
  SNR in the thousands came from them. The same times appear in both stars, which is
  itself the signature of a systematic.
  - **Fix:** dipsearch 0.4.2 drops cadences below half the median flux before searching
    (with tests). No companion this project looks for can block half of a star's light.
- **One needs vetting:** TIC 41898425, Sector 69 (TESS-SPOC), BTJD 3192.263, 8-h box,
  depth 2,100 ppm, SNR 16, BF 7.7. It sits 1.7 d (0.15σ) from the centre of the
  RV-identified transit window, but it is also **0.15 d before the end of the orbit's
  data segment**: the light curve rises by ~0.2% and then drops just before the data gap.
  That shape is typical of scattered light at the end of a TESS orbit.

## The star behind the one remaining event
Gaia DR3 4984264505688458112 = TIC 41898425 = 2MASS J01265633-4103345:
- G = 11.44, BP-RP = 0.93, parallax 5.54 mas (≈180 pc), RUWE 1.47;
- FLAME R = 0.93 R☉, M = 0.85 M☉; Teff 5,380 K, log g 4.47 (a K0 dwarf);
- AstroSpectroSB1 orbit: P = 196.67 ± 0.82 d, e = 0.45, significance 25.8;
- dark-companion mass ≈ 0.076 M☉ (right at the hydrogen-burning limit);
- ExoFOP: no TOI, no CTOI, no follow-up files.

A central transit of a ~0.095 R☉ companion would be about 1.0% deep and ~12 h long.
The Gaia inclination makes a transit unlikely: the Monte Carlo gives p_ecl = 0.011. The
observed dip is shallower than a full transit and cut by the gap, so it could only be
an ingress. The prior odds are low and the event sits at a known systematics location.
It is vetted next, with rules fixed in advance
(findings/2026-11-17-vet-41898425-prereg.md). Until then it is not a candidate.

## Constraint statement
Apart from that one window, every RV-identified transit window covered by TESS shows no
dip that survives a look at the data. The per-star cos i constraints, weighted by the
posterior, come from the archival job (A-predictions), not from this coverage count.
