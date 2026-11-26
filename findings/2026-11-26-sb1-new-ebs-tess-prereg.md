# Pre-registration: TESS check of the six Gaia SB1 eclipse candidates that no catalogue lists

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked it yet.
Text CC BY 4.0; code Apache-2.0. Written 2026-11-26 ~14:40 UTC, **before** job
`sb1-new-ebs-tess-v1` ran and before any TESS light curve of these six stars was looked at by us.

## Why
The pre-registered blind run of rule g8 on all 7,978 short-period Gaia DR3 single-lined orbits
(findings/2026-11-26-g8-dr3-sb1-results.md) flagged 111 stars Gaia does not call eclipsing. Of
the 46 we vetted, 31 were already known eclipsing binaries, 9 other variable types and **6 listed
as eclipsing nowhere**. HD 125386A was then confirmed in ASAS-3 (p = 1.8e-8,
findings/2026-11-26-hd125386a-asas3.md); TYC 1316-1554-1's ASAS-3 test was inconclusive (p = 0.29,
findings/2026-11-26-tyc1316-asas3.md); the other four are too far north or too faint for ASAS-3.
TESS settles all six.

## Job (code unchanged)
`vpt_followup.py` 0.1.0 at commit 0d8d4c5 with the same pinned helpers as jobs vpt-followup-v1
and hd11239-tess-v1 (period-free BLS over all TESS sectors from SPOC, TESS-SPOC or QLP; fine scans
at Gaia's P, 2P and P/2). Targets: tessfu/fu_targets.csv (committed as
data/sb1-new-ebs-tess-v1/fu_targets.csv). Positive controls: BN Scl (Prsa et al. 2022,
P = 3.6505249 d) and HD 157949 (VSX ED, P = 3.041 d), as in hd11239-tess-v1.

Gaia conjunction 0 (visible star behind its companion), from Gaia DR3 alone, in BTJD
(= Gaia time - 1802.5):

| Star | Gaia DR3 | G | P_Gaia (d) | sigma_P (d) | conj. 0 (BTJD) |
|---|---|---|---|---|---|
| HD 125386A | 5854558019550047872 | 9.49 | 3.6734169 | 0.00017 | 389.94204 |
| TYC 1316-1554-1 | 3350075697770930304 | 10.58 | 1.6262843 | 0.000014 | 389.62038 |
| TYC 3384-347-1 | 968093290740779008 | 11.47 | 4.0011609 | 0.00020 | 389.44621 |
| UCAC4 544-021692 | 3350386649103238016 | 12.20 | 7.2472787 | 0.0011 | 392.28328 |
| UCAC4 468-115332 | 4289848214689460736 | 12.12 | 5.3592781 | 0.00052 | 393.11624 |
| UCAC4 194-101841 | 5900468269330031744 | 12.62 | 8.2737480 | 0.0039 | 390.83885 |

## Predictions (graded by hand from out/fu_summary.json)
| # | Prediction | Confidence |
|---|---|---|
| C | Both controls: combined S/N >= 7 and TESS period within 0.1% of the catalogue period or half of it | 85% |
| T1 | **At least 4 of the 6** candidates: combined S/N >= 7 and TESS period within 1% of Gaia's P, 2P or P/2 | 65% |
| T2 | HD 125386A: S/N >= 7 and TESS period within 1% of Gaia's P (the eclipse ASAS-3 already showed) | 85% |
| T3 | For the three with small period errors (HD 125386A, TYC 1316-1554-1, TYC 3384-347-1), where the job reports gaia_offset_d (TESS at Gaia's P): abs(offset) <= 0.06 x P for every one reported | 60% |
| T4 | Every candidate that passes T1 has TESS depth >= 0.5% | 70% |

Reported, not graded: for TYC 1316-1554-1, P_tess - P_Gaia (an ASAS-3 pattern found after the
fact hints that the true period is ~3-6e-5 d shorter than Gaia's; vpt_followup's period
resolution may not be fine enough to test it), and the EB_LIKE flags (secondary eclipse, odd-even)
of each star.

If C fails, T1-T4 are not graded. Stars that pass T1 are reported as new eclipsing binaries with
Gaia single-lined orbits and queued for the AAVSO VSX index; stars that fail are reported as
unconfirmed Gaia-only flags, and the measured purity of the blind search is revised with them. A
data-access failure is re-filed unchanged; a code failure is fixed and the version bumped.
