# Gaia's own spectrograph on all 214 Gaia DR3 transit candidates: most testable new candidates are binaries

Written 2026-11-22 (~01:45 UTC). By MV2 of Munim, Inc.; made with AI agents working in his name,
not yet checked by a human expert. Text CC BY 4.0.

- Code: `gaia_vpt_tess.py` 0.1.1 (commit 945ad9850ca0837a93050d77f121c788a5db58e3), `--rvs-screen
  --schema gaiadr3`, the RVS screen fixed in amendment 1 (`findings/2026-11-21-vpt-amendment-1.md`).
- Job **gaia-vpt-rvs-dr3-v1** (Dell, 22 Nov 00:32-00:37 UTC; all steps exit 0). Output committed to
  `data/vpt-dr3-v1/rvs/`: `vpt_rvs.csv` (all 214 rows, one Gaia archive query),
  `vpt_rvs_summary.json`, `comb_c0_vpt_summary.json` (chunk 0 re-graded with 0.1.1 and the RVS file)
  and `job_summary.json`.
- Status: **exploratory, not blind.** The screen was added in amendment 1 after chunk 0 had been
  seen, and the categories of the flagged stars were already listed in
  `findings/2026-11-21-vpt-dr3-results.md` section 4. What is new here is the full, machine-made
  RVS file and therefore the denominators (how many stars in each category Gaia's spectrograph can
  test). No prediction was registered for DR3; the registered prediction is for DR4 (at least 25%
  of RVS-testable NEW candidates RV_VARIABLE, 60%).

## Criterion

Katz et al. (2023, A&A 674, A5), conservative: `rv_chisq_pvalue` <= 0.01 and
`rv_renormalised_gof` > 4 and `rv_nb_transits` >= 10 and `rv_template_teff` in 3900-8000 K ->
**RV_VARIABLE**; statistics present but criterion failed -> **RV_QUIET**; no statistics (Gaia DR3
gives them only for G_RVS <= 12) or outside the ranges -> **RV_UNTESTED**. A hot Jupiter moves its
star by about 0.1-0.3 km/s, far below what this test can see, so RV_VARIABLE means a stellar or
brown-dwarf companion, or an RVS systematic.

Whole table (from `vpt_rvs_summary.json`): **RV_QUIET 113, RV_UNTESTED 89, RV_VARIABLE 12**;
125 of 214 are testable. This equals the hand query of 21 Nov (126 with statistics, minus
WASP-178, whose 9000 K template is outside the range).

## By category

Categories are those of the step-g rehearsal (`data/vpt-dr3-v1/c0/vpt_stars.csv`,
`data/vpt-dr3-v1/c1/vpt_stars.csv`). Chunk 0 is counted by the code (`comb_c0_vpt_summary.json`,
block `RVS`); chunk 1 is counted by hand by joining `vpt_rvs.csv` to chunk 1's `vpt_stars.csv` on
`source_id`. The hand count reproduces the code's whole-table totals exactly (113 / 89 / 12).
Job gaia-vpt-dr3-comb-v1 (queued) recomputes chunk 1 with the code.

| category | chunk 0 var / quiet / untested | chunk 1 var / quiet / untested | testable | RV_VARIABLE | share |
|---|---|---|---|---|---|
| NEW (Gaia's own new candidates with a TIC) | 4 / 2 / 8 | 4 / 2 / 7 | 12 | **8** | **0.67** (95% 0.39-0.86) |
| KNOWN_PLANET (Gaia period right) | 1 / 6 / 4 | 1 / 2 / 1 | 10 | 2 | 0.20 |
| KNOWN_SYSTEM_OTHER_P (known planet or TOI, Gaia period wrong) | 0 / 49 / 30 | 2 / 49 / 31 | 100 | 2 | 0.02 |
| all known systems | 1 / 55 / 34 | 3 / 51 / 32 | **110** | **4** | **0.036** (95% 0.014-0.090) |
| TOI_PC | 0 / 1 / 2 | 0 / 0 / 3 | 1 | 0 | |
| NO_TESS (no TIC within 5") | - | 0 / 2 / 3 | 2 | 0 | |
| **all** | 5 / 58 / 44 | 7 / 55 / 45 | **125** | **12** | 0.096 |

Intervals are Wilson 95%. **NEW against all known systems: 8 of 12 against 4 of 110; one-sided
Fisher exact p ≈ 2 × 10⁻⁷** (hypergeometric sum computed by hand: P(X = 8) = 2.20 × 10⁻⁷,
P(X = 9) = 3.7 × 10⁻⁹, higher terms smaller).

### The four flagged known systems

| star | Gaia DR3 source_id | companion | range (km/s) | p | gof | reading |
|---|---|---|---|---|---|---|
| KELT-1 | 2881784280929695360 | KELT-1 b, ~27 M_Jup brown dwarf | 17.4 | 4e-16 | 8.85 | correct flag |
| WASP-18 | 4955371367334610048 | WASP-18 b, ~10 M_Jup | 5.1 | 0 | 11.09 | correct flag (K ≈ 1.8 km/s; bright star) |
| WASP-163 | 4334991786994866304 | WASP-163 b, ~1.9 M_Jup | 23.5 | 6e-9 | 5.10 | RVS false positive or an unknown companion |
| TOI-1991 | 5348534425968598400 | TOI-1991.01 (TESS candidate) | 20.4 | 0 | 32.83 | the TOI may have a stellar companion |

So among known hosts of companions below 10 Jupiter masses the flag fires on at most 2 of 108
testable stars (WASP-163 and TOI-1991), an upper bound on the false-flag rate of about 2%.

### The eight flagged new candidates

| Gaia DR3 source_id | TIC | G | G_RVS | robust range (km/s) | gof | RVS transits | TESS at Gaia's period (step g) |
|---|---|---|---|---|---|---|---|
| 4136481216073713280 | 435052739 | 12.56 | 11.51 | 46.3 | 8.6 | 13 | planet-like hit (removed by this flag) |
| 4535127268607000320 | 470993218 | 12.58 | 11.95 | 54.5 | 20.2 | 63 | no planet-like hit |
| 2685725036820337408 | 248569057 | 11.87 | 11.23 | 43.4 | 11.6 | 19 | no hit; RUWE 3.41 |
| 6081267254094015616 | 169468881 | 12.56 | 11.99 | 31.7 | 7.3 | 24 | no hit |
| 1622997463177004928 | 207399049 | 12.31 | 11.65 | 38.6 | 14.0 | 20 | no hit |
| 2015499135507395328 | 279773873 | 12.54 | 11.87 | 54.1 | 7.7 | 23 | hit, STELLAR_SIZE |
| 4677436783705094912 | 38814673 | 12.44 | 11.81 | 42.3 | 10.9 | 18 | no hit |
| 4895643593611507584 | 179080553 | 12.32 | 11.69 | 132.3 | 34.5 | 42 | hit, ODD_EVEN; STELLAR_SIZE |

`rv_amplitude_robust`
is a peak-to-peak range of epoch velocities and includes noise; at G_RVS 11.5-12 quiet known hosts
show ranges of about 10-25 km/s, so the range alone is not the test; p and gof are.

## What it means

1. **Two thirds of the Gaia DR3 new transit candidates that Gaia's spectrograph can test are
   radial-velocity variable at the km/s level, against under 4% of known planet hosts.** For a
   planet-sized transit on these stars, that means a stellar companion: an eclipsing binary, or a
   triple or blend. Panahi et al. (2022) wrote that the 39 unconfirmed new candidates "contain some
   other actual planetary systems, which are just awaiting RV confirmation"; at least 8 of them
   now have Gaia's own evidence against a planet. We found no published RVS screen of these
   candidates (searched 22 Nov: Panahi et al. 2022a, 2022b, the Gaia DR3 variability papers and
   later citations we could reach).
2. **For DR4:** amendment 1's screen stands as registered. If DR4's new candidates behave like
   DR3's, the screen removes most bright false positives before any TESS work, and the remaining
   planet-like list is concentrated in stars too faint for the screen (G_RVS > 12), where DR4's
   epoch RVs (step f) are the next test.
3. **The two surviving candidates are both untestable here.** TIC 4638108 (5431056347037926784,
   G_RVS 12.29, 30 RVS transits) and TIC 44997521 (5432318139709900160, G_RVS 12.72, 32 RVS transits)
   have no variability statistics. Neither the screen nor its absence says anything about them.

## Addendum to the vetting of the two survivors (22 Nov ~01:30 UTC)

- **ExoFOP** (target.php?id=<TIC>&json): still no TOI, CTOI, planet parameters, observing notes or
  files for either star. TIC 4638108's TIC contamination ratio is 1.26 (as in the vetting note).
- **ASAS-SN variable-star catalogue** (VizieR II/366/catv2021, CfA mirror, 60" cone): no entry for
  either star. No positive control was run on this mirror tonight, so this is weak evidence.
- **SIMBAD:** still unreachable from our host (HTTP 404 on both the web and TAP endpoints).

## Limits

Not blind (see Status). The chunk-1 category join is by hand; the queued combine job recomputes it.
The Fisher p treats the known systems as a fair reference, but they are bright, well-studied
planet hosts, and the new candidates were selected by Gaia's pipeline; the comparison shows that
the flag rarely fires on real planet hosts, not that the two groups are alike in every other way.
An RVS systematic (for example a blended spectrum) can also raise the flag. Nothing here is
called a binary by name in a catalogue submission; these are leads for spectroscopic follow-up.
