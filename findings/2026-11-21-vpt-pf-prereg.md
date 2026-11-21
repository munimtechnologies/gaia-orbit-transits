# Pre-registration: step G6, a period-free TESS search of every Gaia transit candidate

Fixed 2026-11-21 (~23:45 UTC), before any output of the job below exists. MV2 of Munim, Inc.
Made with AI agents working in his name; not yet checked by a human expert. Text CC BY 4.0,
code Apache-2.0.

Code: `vpt_pf.py` 0.1.0 with tests (`test_vpt_pf.py`); set-up helper `runbook/pf/fetch_deps.py`
(every module and the input table pinned by full commit SHA). DR3 rehearsal job:
**gaia-vpt-pf-dr3-v1**.

## The question

In the DR3 rehearsal of step g (`findings/2026-11-21-vpt-dr3-results.md`), Gaia's published
transit period matched the known period for only **15 of 176** known systems. Our registered DR4
test (step g) folds TESS at Gaia's period, so if DR4's periods are like DR3's it will miss most
real transiting companions. Two questions follow:

1. **Can a period-free TESS search recover the true period where Gaia's is wrong?** If yes, the
   1,007 DR4 candidates can be checked without trusting Gaia's period, and a period-reliability
   fix for Gaia's list exists on day one.
2. **Do any of Gaia DR3's own new candidates show a planet-like transit in TESS at a period other
   than Gaia's?** That would be a transiting-companion candidate first flagged by Gaia that both
   Gaia's period and our step-g fold missed.

We found no published period-free TESS search of all 214 Gaia DR3 candidates. Panahi et al.
(2022, A&A 663, A101) checked the 41 new ones in TESS images up to 2021; Gaia-1b and Gaia-2b
were confirmed by radial velocities.

## What runs

`vpt_pf.py` calls `vpt_followup.py` 0.1.0 (commit d1805bf07a146795e004e384057d5f9c8e6a3c3f)
**unchanged** for each star: TESS light curves (SPOC 120 s > TESS-SPOC > QLP) through
`sb1_transit.light_curves`, at most **6 sectors** per star (the follow-up of the two survivors
uses all sectors), 30-min bins and running-median detrending, a box search of 0.3-15 d in each
sector alone, fine scans (±1%) around Gaia's P, 2P, P/2 and up to 8 sector peaks with
S/N ≥ 7, then depth, odd/even, secondary and per-sector depths at the strongest peak.
vpt_followup's own labels are kept: NOT_DETECTED (S/N < 7), EB_LIKE (ODD_EVEN, SECONDARY or
STELLAR_SIZE > 2 R_Jup), SURVIVES (TESS period within 1% of Gaia's), SURVIVES_OTHER_P.

**Input:** all 214 rows of `gaiadr3.vari_planetary_transit` with the gaia_source/FLAME columns,
exactly as written by gaia_vpt_tess 0.1.0 in the step-g rehearsal
(`data/vpt-dr3-v1/c0/vpt_candidates.csv`, commit 9d8db1a9e6c37a931c6ca44a2f11f81901303e09). The
job stops with exit 4 if the table does not have 214 rows. Stars are processed in a seeded random
order (seed 20261122), two at a time, with a 200-minute budget; each finished star is
checkpointed so a re-run (-v2) continues where the budget stopped.

**Known periods:** for the star's TIC, every planet in the NASA Exoplanet Archive (pscomppars)
and every TOI (any disposition, since an eclipsing-binary TOI still has a real period), fetched
by the job itself through gaia_vpt_tess 0.1.1's `load_catalogues`.

## Classes (fixed)

- Known systems (at least one known period): **KNOWN_NOT_DETECTED** (S/N < 7),
  **KNOWN_RECOVERED** (TESS period within 1% of any known period), **KNOWN_HARMONIC** (within 1%
  of 1/2, 2, 1/3 or 3 times one), **KNOWN_OTHER_P** (anything else).
- No known period: **NEW_** + vpt_followup's label.
- NO_TESS, ERROR.
- **Gaia right** = Gaia's period within 1% of a known period or of half or twice it (the G5 rule
  of step g).

## Tests and labels (fixed)

- **PF1:** among known systems with at least one known period in 0.3-15 d, the share
  KNOWN_RECOVERED. **PF1b (primary):** the same among those whose Gaia period is wrong.
  Labels for both: **PF_RECOVERS** ≥ 0.60, **PF_PARTIAL** 0.30-0.60, **PF_FAILS** < 0.30;
  UNTESTABLE if n < 20. 95% Wilson intervals are reported.
- **PF_WRONG:** among detected known systems (RECOVERED + HARMONIC + OTHER_P), the share
  KNOWN_OTHER_P. If it is above 0.25, the PF2 list is reported as **unreliable**.
- **PF2:** NEW stars labelled NEW_SURVIVES or NEW_SURVIVES_OTHER_P, sorted by S/N; **robust** if
  the final TESS period is also the best period of at least 2 sectors searched alone. Every
  robust PF2 star gets, before anything is claimed, the catalogue vetting of
  `findings/2026-11-21-vpt-survivors-vetting.md` (Gaia neighbours and the flux argument, Gaia's
  duration against the host's density, ExoFOP/VSX/TESS-EB/literature) and an all-sector run of
  vpt_followup. Nothing is called a planet.
- Descriptive: counts of every class; the list of known systems where the period-free search
  found the known period although Gaia's was wrong; PF classes against the step-g categories.

## Predictions (DR3 rehearsal)

- PF1: PF_RECOVERS 65%, PF_PARTIAL 30%, PF_FAILS 5%.
- **PF1b: PF_RECOVERS 55%, PF_PARTIAL 35%, PF_FAILS 10%.**
- PF_WRONG ≤ 0.25: 70%.
- PF2: at least one robust NEW planet-like star 55% (the two step-g survivors count if robust);
  at least one robust **NEW_SURVIVES_OTHER_P** 25%.

**Not blind:** we know which known systems exist, which NEW candidates step g saw at Gaia's
period, and the two step-g survivors. We have not seen any output of this period-free search.

## Gaia DR4 (2 December 2026): step G6

Run after step g has written DR4's `vpt_candidates.csv` (commit it to `data/vpt-dr4-v1/c0/`
first), with `vpt_pf.py` 0.1.0 unchanged: `--n-chunks 5`, one job per chunk, `--max-sectors 6`,
`--workers 2`, `--ckpt-dir /data/vpt_pf_dr4_v010`, `--expect-n` equal to the row count of DR4's
table. Same classes, labels and vetting. Any change after the DR3 rehearsal is graded is a dated
amendment committed before **2 December 12:00 CET**; if the rehearsal's PF1b is PF_FAILS, G6 on
DR4 still runs but is reported as exploratory.

DR4 predictions: PF1b PF_RECOVERS 50%; at least 3 robust NEW planet-like stars 40%; at least one
robust NEW_SURVIVES_OTHER_P 45%.

## What would count

- **PF1b = PF_RECOVERS:** a period-free TESS search fixes most of Gaia's wrong periods, so Gaia's
  transit list becomes usable without trusting its periods. A measured result we found nowhere in
  print.
- **A robust NEW_SURVIVES_OTHER_P that passes the vetting:** a giant-planet-sized transit
  candidate first flagged by Gaia, at a period Gaia did not report, ready for an ExoFOP CTOI.
- **PF1b = PF_FAILS:** an honest negative: TESS alone (6 sectors, this search) cannot recover
  Gaia's systems, and step g's DR4 result must be read with that limit.
