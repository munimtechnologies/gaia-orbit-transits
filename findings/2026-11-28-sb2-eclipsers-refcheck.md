# Which of the deep, already-catalogued SB2 eclipsers from the tier-2 scan lack published masses? A first screen

2026-11-28 ~07:10 UTC, AI agents working in MV2's name (Munim, Inc.). Preparation for the "Gaia + TESS mass benchmarks" lane, not a result. CC BY 4.0.

The tier-2 scan (data/sb2-ffiscan-t2-v1/hand_vetting.csv) found 29 eclipsers with Gaia DR3 SB2 orbits and TESS eclipses at Gaia's conjunction phase that are already listed as eclipsing in a TESS catalogue (IJspeert et al. 2021/2024, Prsa et al. 2022) or in Eclipses by Appointment. Each has K1, K2 and P from Gaia and a TESS light curve, so a light-curve fit gives masses. The question is which have no published masses yet. This screen uses SIMBAD reference lists (28 Nov 2026) and arXiv title/abstract search for the 15 with TESS eclipse depth >= 3.5%, where a fit is easiest.

| TIC | SIMBAD name | Sp | G | depth | listed where | SIMBAD refs | screen |
|---|---|---|---|---|---|---|---|
| 273792220 | HD 12695 | F9V | 7.88 | 4.1% | Prsa 2022 | 42 | CHECK: well-studied SB (Tokovinin 2014AJ 147 87 etc.); arXiv 0 hits for the HD name; masses may exist |
| 6653255 | HD 243253 | F2 | 9.32 | 6.2% | IJspeert 2024 | 6 | catalogue refs only |
| 157469799 | BD+45 2574 | - | 9.33 | 16.6% | EbA A98 | 6 | visual double (WDS); old refs only |
| 21189379 | HD 234650 | A2 | 9.41 | 7.8% | IJspeert 2021+2024 | 12 | CHECK: 2024A&A 683 A252T unidentified |
| 423530755 | HD 107454 | G6/8IV | 9.45 | 4.6% | Prsa 2022 | 8 | catalogue refs only |
| 267811506 | HD 239127 | F0 | 9.49 | 11.4% | IJspeert 2024 | 4 | catalogue refs only |
| 239649487 | TYC 2747-436-1 | - | 9.53 | 11.6% | EbA A108 | 1 | Gaia only |
| 397680054 | BD+32 4452 | F2 | 9.82 | 3.6% | EbA A107 | 3 | catalogue refs only |
| 155268582 | TYC 6563-1974-1 | - | 10.18 | 6.8% | IJspeert 2024 | 2 | Gaia + one survey ref |
| 115770034 | HD 339241 | G0 | 10.67 | 22.2% | IJspeert 2024 | 5 | catalogue refs only |
| 136095837 | TYC 3588-11822-1 | - | 10.71 | 4.6% | IJspeert 2024 | 1 | Gaia only |
| 220397947 | CD-58 963 | - | 10.76 | 3.9% | Prsa 2022 | 15 | **HAS MASSES**: Borkovits et al. 2020 (arXiv:2002.06902), compact hierarchical triple, P_in 3.55 d, P_out 77 d, photodynamical masses. Use as a validation target, not a benchmark |
| 254926416 | (not in SIMBAD by TIC) | - | 10.97 | 5.8% | IJspeert 2024 | - | look up by Gaia id 5988003688559983744 |
| 270648838 | TYC 232-1494-1 | G7 | 11.18 | 28.9% | Prsa 2022 | 6 | CHECK: 2025AJ 170 322E and 2025AJ 170 356T unidentified; arXiv 0 hits for TYC/TIC |
| 173207470 | HD 218299 | A0 | 8.29 | 3.7% | IJspeert 2021+2024 | 7 | catalogue refs only |

Reading: 10 of 15 have only catalogue or survey references (Gaia DR3 NSS 2023A&A 674 A34, TESS input/EB catalogues, Hipparcos/Tycho photometry), one (TIC 220397947) has a full published dynamical solution, three need a closer look at specific papers, one needs a Gaia-id lookup. Reference counts are a screen, not proof: a mass could sit in a paper that does not name the star in its abstract. Before any benchmark is claimed, each star gets an ADS full-text or Google Scholar check and a DEBCat check.

Also noted: 2023A&A 674 A34 (Gaia NSS) and 2019MNRAS 490 3158 (Chontos et al., TESS candidate catalogue) recur in nearly every row; neither publishes eclipse masses.

Next: when compute frees, an sb2_ebfit run on the 10 "catalogue refs only" stars with the Gaia conjunction mapping fixed (MAP_CONJUNCTION) and k/J priors, pre-registered; TIC 220397947 as the validation case against Borkovits et al. 2020.
