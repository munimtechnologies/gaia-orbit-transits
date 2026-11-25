# Tier-2 screen, prediction T2_3b graded: two new double-lined eclipsing binaries, and a weaker third

MV2, Munim, Inc. - 25 November 2026 (~11:00-11:40 UTC). Made with AI agents working in MV2's name;
no human expert has checked it yet. Text and data CC BY 4.0 (Gaia data ESA/Gaia/DPAC; TESS data
NASA/MAST). Data: `data/sb2-tier2-dr3-v1/t2_3b_vetting.csv`.

Follows `findings/2026-11-25-g5-tier2-results.md`, which left five of the seven would-be new
tier-2 stars OPEN because TESS Ten Thousand and IJspeert et al. (2024) could not be read (every
VizieR mirror failed on the morning of 25 Nov). The pre-registered prediction **T2_3b: at least
one star survives hand vetting as new (35%)** was undecided. The planned re-run of the lookup step
was done by hand instead, with a positive control for every catalogue query.

## Catalogue lookups (VizieR CfA mirror, answering again at ~11:00 UTC)

| Catalogue | Query | Control found | Result for the 5 OPEN stars |
|---|---|---|---|
| TESS Ten Thousand, Kostov et al. 2025, ApJS 279, 50 (J/ApJS/279/50: table3 new EBs, table4 known EBs, table2 ~900,000 unvetted) | TIC list | TIC 10507 (table4), TIC 1051 (table2) | none of the five in any table |
| IJspeert et al. 2024, A&A 691, A242 (tessobaf and obaf-eb1) | TIC list | both returned stars have full rows | **HD 72862** (obaf-eb1, P 1.33343 d) and **TYC 6563-1974-1** (obaf-eb1, P 7.0652 d) listed; the other three not in either table |
| Prsa et al. 2022, ApJS 258, 16 (tess-ebs) | zero-padded TIC list | TIC 0185259483 | none of the five |
| Villanova TESS EB catalogue (tessebs.villanova.edu search) | TIC | control TIC 10507 also returned 0 rows, so this lookup is **not** controlled | 0 rows for all three |
| Eclipses by Appointment `accepted-systems.csv`, commit a05372b (25 Nov 07:11 UTC, latest at 10:45 UTC), read in full (rows A1-R1867) | TIC and Gaia DR3 id | (A179 = TIC 384284045 found) | none of the three |
| Gaia DR3 vari_eclipsing_binary (AIP TAP) | source_id | - | none of the four queried |
| ExoFOP-TESS | TIC | - | no TOI, no CTOI (TIC 119613818 re-read 11:20 UTC) |
| Web search | names and TIC numbers | - | nothing on any of them as an eclipsing binary |

So **HD 72862 and TYC 6563-1974-1 are KNOWN** (IJspeert et al. 2024 list them as eclipsing-binary
candidates at half the Gaia period). **BD+15 2743, HD 171459 and TYC 3330-286-1 are in no
eclipsing-binary catalogue, paper or open project we could reach.**

## Are they eclipses? TESS SPOC pipeline statistics

Read from the public SPOC DV statistics files (MAST `tess*-s00NN-s00NN_dvr-tcestats.csv`, one
row per TCE; columns mapped by the file's header).

| Star | Sector | TCE P (d) | Gaia P/2 (d) | depth (ppm) | S/N | duration (h) | odd/even stat | centroid offset |
|---|---|---|---|---|---|---|---|---|
| BD+15 2743 | 51 | 1.03365 | 1.03361 | 20,391 | 200 | 2.14 | **2026** | 0.09" +- 2.50" |
| HD 171459 | 39 | 3.19777 | 3.19781 | 14,938 | 349 | 6.52 | **421** | 0.48" +- 2.50" |
| TYC 3330-286-1 | 59 | 1.38173 | 1.38169 | 3,351 | 28 | 1.50 | 1.6 | 4.09" +- 2.54" |

- **BD+15 2743 and HD 171459:** the TCE period equals half of Gaia's double-lined period to
  0.004% and 0.001%, and the odd/even depth statistic is huge: alternate dips have different
  depths. That is a primary and a secondary eclipse per Gaia orbit, not a pulsation or spot
  signal (which would not alternate) and not ellipsoidal variation (a 1.5-2% transit-shaped dip of
  2-6.5 h is far above what ellipsoidal light gives at these separations: q (R/a)^3 ~ 10^-3 for
  HD 171459). The difference-image centroids sit on the target. The nearest catalogued variable
  to BD+15 2743 (an M dwarf, G 13.7, ~33" away) is 4.6 mag fainter and would need a 139%-deep
  eclipse.
- **TYC 3330-286-1:** equal alternate dips at Gaia P/2 to 0.003% (twin eclipses, as Gaia's
  near-equal K1 and K2 suggest), but S/N 28, TIC contamination 0.45 and a 1.6-sigma centroid
  offset. A chance background eclipsing binary at exactly half the Gaia period is unlikely, but
  this one stays **NEW_WEAK**.
- HD 171459 (= HIP 91511, an Am star) has SPOC TCEs in four sectors (39, 101, 102, 104); Gaia
  DR3's variability classifier put it in the pulsator class DSCT|GDOR|SXPHE with a score of 0.03.

## Gaia minimum masses (hand-computed from the Gaia DR3 SB2 orbits, e = 0)

M sin^3 i = 1.036149e-7 (K1 + K2)^2 K_other P [M_sun; km/s, d]:

| Star | P (d) | K1, K2 (km/s) | M1 sin^3 i | M2 sin^3 i |
|---|---|---|---|---|
| BD+15 2743 | 2.0672153 | 106.06, 95.12 | 0.825 | 0.919 |
| HD 171459 | 6.3956124 | 89.31, 87.70 | 1.821 | 1.854 |
| TYC 3330-286-1 | 2.7633739 | 101.42, 97.89 +- 16.1 | 1.113 | 1.154 |

With eclipses, sin^3 i is close to 1. In BD+15 2743 Gaia's "primary" has the larger K, i.e. the
smaller mass; which star is brighter needs the light curve.

## Grade

**T2_3b (35%): YES.** Two stars survive hand vetting as new double-lined eclipsing binaries
(BD+15 2743, HD 171459), plus one weaker (TYC 3330-286-1). With the tier-1 pair (HD 250735,
CD-28 7251) that makes four bright Gaia double-lined eclipsing binaries in no catalogue we reached.
Tier 2 overall: 6 of 8 predictions true (T2_3 failed on unreachable catalogues, as recorded).

## Limits

The eclipse evidence is the TESS pipeline's own statistics, not our light-curve fit; the
eclipse depths are from a planet-transit model and are not eclipse-model depths. The Villanova
lookup had no working control. 'New' means absent from every catalogue, paper and open project we
could reach on 25 Nov 2026. Not pre-registered: the decision to check DV statistics as the
eclipse-vs-other test (the earlier note named light curves).

## Next

Add the three to the eclipse-timing and eclipse-fit jobs; on Gaia DR4 (2 Dec) refit with DR4
orbits. AAVSO VSX submission needs an AAVSO account for MV2.
