# Step-g DR3 rehearsal, chunk 0 of 2: interim results (not the final grade)

Written 2026-11-21 (~16:00 UTC). By MV2 of Munim, Inc.; made with AI agents working in his name,
not yet checked by a human expert. Pre-registration `findings/2026-11-21-vpt-tess-prereg.md`;
amendment `findings/2026-11-21-vpt-amendment-1.md` (written after reading this chunk, before DR4).
Data: `data/vpt-dr3-v1/c0/` (job gaia-vpt-dr3-c0-v1, `gaia_vpt_tess.py` 0.1.0, ran 21 Nov
11:58-13:12 UTC on the Dell). Text CC BY 4.0.

**This is half the rehearsal.** Chunk 1 (the other 107 candidates) has not run. The labels below
are chunk-0 values; the registered grade is made on the combined 214. The DR3 rehearsal is not
blind (the 173 known systems are known; Panahi et al. 2022 checked the 41 new candidates with
TESS images up to 2021).

## What the chunk gives

| | value |
|---|---|
| candidates processed | 107 (all status OK) |
| rate sample (injection sensitivity >= 0.5) | 86 |
| categories | KNOWN_PLANET 11, KNOWN_SYSTEM_OTHER_P 79, TOI_PC 3, NEW 14 |
| G0a known planets recovered | 10 of 11 (0.91; 95% 0.62-0.98) -> PIPELINE_OK (chunk) |
| G0b control rate | 23 of 172 trials = 0.134 -> CONTROLS_NOISY (chunk) |
| G1 NEW seen (as registered) | 6 of 11 sensitive; MIXED, **invalid** (controls noisy) |
| G2 planet-like NEW hits | 2 |
| G3 EB-like share of NEW hits | 6 of 8 (0.75) |
| G4 missed at P that hit at P/2 or 2P | 11 of 73 |

The one known planet missed at Gaia's period is Kepler-43 b (Gaia period half the known one;
it hits at 2P in G4).

## Two things the design did not expect (they led to amendment 1)

**1. Gaia's published period is usually not the known one.** 90 candidates sit on stars with a
known planet or TOI. Only 11 have a Gaia `transit_period` within 1% of a known period at ratio
1, 1/2 or 2; 79 do not (11/90 = 0.12, Wilson 95% 0.07-0.21). The 79 are mostly well-known hot
Jupiters, so the transits are real and the period is not. We confirmed the values are those of
the current, corrected table (`solution_id` 375523436409132247; the 13 June 2022 table was
withdrawn and replaced on 7 February 2023) on the ESA archive and the Heidelberg mirror. The Gaia
documentation (DR3 docs section 10.10.1) says the parameters of the known planets "do not
necessarily match the known, nominal parameters"; we found no published count. Examples (Gaia
period from `vpt_candidates.csv`; known period from the NASA Exoplanet Archive):

| planet | Gaia DR3 period (d) | known period (d) |
|---|---|---|
| WASP-121 b | 0.57089 | 1.27493 |
| WASP-12 b | 0.83537 | 1.09142 |
| WASP-43 b | 4.84919 | 0.81348 |
| WASP-48 b | 0.60145 | 2.14363 |
| HAT-P-36 b | 1.01728 | 1.32735 |
| WASP-22 b (a match) | 3.53220 | 3.53269 |

**2. The pooled control rate mixes two things.** Control hits by category (rate sample):

| category | trials | control hits | rate |
|---|---|---|---|
| KNOWN_SYSTEM_OTHER_P (Gaia period wrong, real transit elsewhere) | 124 | 20 | 0.161 |
| NEW | 22 | 3 | 0.136 |
| KNOWN_PLANET (Gaia period right) | 22 | 0 | 0.000 |
| TOI_PC | 4 | 0 | 0.000 |

Where Gaia's period is right, masking the best box removes the real signal and the controls are
quiet. Where a real deep signal sits at another period, the controls catch pieces of it. The
three NEW control hits are on two stars that Gaia's spectrograph shows are binaries (below).
Amendment 1 therefore measures the noise false-alarm rate on known planets only (G0b_kp, G1b)
for DR4. On chunk 0 that would give 0 of 22 trials and a NEW seen fraction of 6/11 = 0.55
(MOSTLY_SEEN), but G1b was designed after seeing this chunk, so on DR3 it is reported, not
graded.

Also: a hit at Gaia's period does not prove the period. 10 of 62 sensitive
KNOWN_SYSTEM_OTHER_P stars hit at Gaia's wrong period; 8 of the 10 carry eclipsing-binary flags,
2 look planet-like (TOI-150, where Gaia's period is about a third of TOI-150.01's, and WASP-113,
where it is 0.60 of WASP-113 b's 4.5422 d).

## Gaia's own spectrograph on the candidates (exploratory, not pre-registered)

Gaia DR3 gives RV variability statistics for stars with G_RVS <= 12. We queried them for all 214
candidates on the ESA archive (21 Nov ~15:00 UTC; `gaiadr3.vari_planetary_transit` joined to
`gaiadr3.gaia_source`). 126 of the 214 have statistics from at least 10 RVS transits. Katz et al.
(2023)'s criterion (p <= 0.01, renormalised gof > 4, >= 10 transits) flags 12 of them. A hot
Jupiter moves its star by 0.1-0.3 km/s, far below RVS precision, so a flag means a stellar or
brown-dwarf companion, or an RVS systematic. These numbers come from a hand-run query; job
gaia-vpt-rvs-dr3-v1 recomputes them with the code of amendment 1 (which also applies the
criterion's template-Teff range) and its output replaces this table.

In chunk 0:
- **Known planet hosts:** 56 testable, **1 flagged: KELT-1**, whose companion KELT-1 b is a
  27-Jupiter-mass brown dwarf, so the flag is correct.
- **NEW candidates:** 6 testable, **4 flagged**:

| Gaia DR3 source_id | G | RV range (km/s) | p | gof | RVS transits | TESS at Gaia P |
|---|---|---|---|---|---|---|
| 4136481216073713280 (TIC 435052739) | 12.56 | 46.3 | 0 | 8.6 | 13 | hit, planet-like |
| 4535127268607000320 | 12.58 | 54.5 | 0 | 20.2 | 63 | hit, ODD_EVEN; STELLAR_SIZE |
| 2685725036820337408 | 11.87 | 43.4 | 0 | 11.6 | 19 | no hit (sensitive) |
| 6081267254094015616 | 12.56 | 31.7 | 4e-13 | 7.3 | 24 | no hit (sensitive) |

  The other two testable NEW candidates (5345417757181174144, 5836096154165283712) are RV_QUIET.
- 4 of 6 against 1 of 56 (one-sided Fisher p = 1.3e-4). This is post hoc and on half the list;
  it is a lead for the combined grade, not a result.

Outside chunk 0 (categories not yet computed): two flagged stars are known planet hosts by
position in the NASA Exoplanet Archive, WASP-18 (WASP-18 b is 10.2 Jupiter masses: a correct
flag) and WASP-163 (WASP-163 b is 1.87 Jupiter masses, far too light for the 23 km/s range: an
RVS false positive or an unknown companion). Five more flagged stars are not in the archive:
1622997463177004928, 2015499135507395328, 4677436783705094912, 4895643593611507584,
5348534425968598400 (range 132 km/s for 4895643593611507584).

## The two planet-like NEW candidates

Both are among Gaia's 41 DR3 candidates (Panahi et al. 2022), so neither is our discovery.

1. **TIC 435052739** (Gaia DR3 4136481216073713280; G 12.56): Gaia P 1.8167 d, TESS depth 1.43%
   (QLP, sector 91 only), companion radius 1.93 R_Jup on a 1.66 R_sun star. **RV range
   46.3 km/s (p = 0): a stellar companion, not a planet.** It also had one control hit. Most
   likely an eclipsing binary with a low-mass star. No TOI or CTOI on ExoFOP (21 Nov).
2. **TIC 4638108** (Gaia DR3 5431056347037926784; G 12.79, Teff 6900 K from GSP-Phot, R 1.44
   R_sun from FLAME): Gaia P 2.2086 d; hit in all 3 TESS sectors used (QLP; best SNR 42.7, sector
   89); TESS depth 1.79% against Gaia's 1.57%; no secondary (SNR -0.67), odd/even z 0.56, no
   control hit; companion radius **1.87 R_Jup**. **RVS cannot test it** (G_RVS 12.29 > 12). No TOI
   or CTOI on ExoFOP (21 Nov); Gaia's classifier calls it EP (exoplanet transit); not in
   `vari_eclipsing_binary`. Gaia's sub-arcsecond photometry sees the same depth as TESS, so the
   dip is on this Gaia source even though the TIC lists contaminating flux 1.26 times the
   target's in TESS's large pixels (RUWE 0.88 and `ipd_frac_multi_peak` 0 show no resolved close
   companion). A 1.87 R_Jup object at 2.2 d around a hot F star could be an inflated hot Jupiter
   or a low-mass star; only spectroscopy can tell. The TESS fold puts the transit 0.52 d from
   Gaia's ephemeris after 1,500 cycles: if that is all period error, Gaia's period is about
   0.00035 d too long.

## Next

1. Chunk 1 and the RVS job; then the combined grade with 0.1.1 (`--combine c0 c1 --rvs-file`),
   G1 as registered (and G1b reported), G5 with the held-out-half prediction of amendment 1.
2. TIC 4638108: full TESS light curve by eye, period check, pixel-level which-star test before any
   radius is quoted.
