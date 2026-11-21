# Pre-registration: do Gaia's own transit candidates transit in TESS? (runbook step g)

Written 2026-11-21 (~10:00 UTC), eleven days before Gaia DR4 (2 December 2026), with no DR4
data seen. By MV2 of Munim, Inc.; made with AI agents working in his name, not yet checked by
a human expert. Code: `gaia_vpt_tess.py` 0.1.0 (stdlib unit tests `test_gaia_vpt_tess.py`;
TESS search imported unchanged from `sb1_transit.py` 0.1.0, `dipsearch.py` 0.4.4 and
`vet_event.py` 0.1.0, pinned by commit in `vpt/fetch_deps.py`). Text CC BY 4.0, code Apache-2.0.

## Why

Gaia finds transiting planets on its own: its sparse photometry was searched for periodic
dips, and DR3 published **214** candidates in `vari_planetary_transit` (173 known systems and 41
new ones; Panahi et al. 2022, A&A 663, A101; Eyer et al. 2023). Two of the 41 became the first
planets Gaia found, Gaia-1b and Gaia-2b. As of the most recent overview we found (Gaia variable
sources in the archive, arXiv:2412.02744, December 2024) the other 39 were still unconfirmed,
and we found no published TESS check of them since 2022, although TESS has observed most of the
sky again since then.

**Gaia DR4 publishes 1,007 such candidates** (ESA DR4 content page, table list of
14 September 2026: `vari_planetary_transit`, 1,007 rows). That is about five times DR3's list,
from a 66-month baseline. Nobody can have checked them in TESS yet, because the list is not
public until 2 December.

**The wow if it works:** on the day DR4 appears, an open, rule-fixed check of every Gaia transit
candidate in TESS, measuring how many of Gaia's new candidates are real transit signals and
naming the new planet-like ones (not known planets, not TOIs) that TESS confirms photometrically.
Each would be a new transiting giant-planet candidate found first by Gaia. A clear negative
(Gaia's new candidates mostly do not show up in TESS) would also be useful: it would tell DR4
users how far to trust that table.

## What is tested

For every candidate: Gaia's period P, reference time T0 (BJD_TCB − 2455197.5; converted to BTJD
by subtracting 1802.5 d, the ~20 s TCB−TDB difference ignored), depth (mmag → flux fraction)
and box duration. TESS light curves, the fold search, the hit rule, the controls and the
injections are those of `sb1_transit.py` 0.1.0, unchanged:

- Up to 3 sectors per star (SPOC 120 s > TESS-SPOC > QLP), 30-min binning, running-median
  detrending (window max(3 D, 0.5 d)).
- Phase-free box fold at P, box width D = max(0.6 × Gaia duration, 1 h).
- Sector hit: SNR ≥ 7 (smaller of white and empirical), local ratio ≥ 0.7, ≥ 3 transits in the
  box, drop-one SNR ≥ 3. A star hits if any used sector hits.
- Controls: the same search at 0.8541 P and 0.9137 P after masking the best box at P.
  Control rate = control hits / (2 × rate-sample size).
- Sensitivity: 4 injections per sector at 0.8 × Gaia depth, Gaia duration; s = found / tried.
  **Rate sample: s ≥ 0.5.**

**Categories** (fixed order), from the NASA Exoplanet Archive `pscomppars` table and the ExoFOP
TOI list, both by TIC (the TIC of the TESS light curve), with a period match within 1% at
ratio 1, 1/2 or 2:
1. KNOWN_PLANET: an archive planet at the period, or a TOI with disposition CP/KP at the period.
2. TOI_FP: a TOI with disposition FP/FA at the period.
3. TOI_PC: any other TOI at the period.
4. KNOWN_SYSTEM_OTHER_P: an archive planet or TOI on this TIC, none at the period.
5. NEW: none of the above. (NO_TIC / NO_TESS / BAD_EPHEMERIS / ERROR are counted, not graded.)

**Vetting flags for every hit** (best-SNR hit sector): SECONDARY (box at phase 0.5 with SNR ≥ 4
and depth ≥ 10% of the primary), ODD_EVEN (odd vs even transit depth |z| ≥ 3), MODULATED
(sinusoid at P with semi-amplitude > 0.5 × depth), STELLAR_SIZE (companion radius
√max(TESS depth, Gaia depth) × R1 > 2 R_Jup; R1 from FLAME, else a main-sequence value from
absolute G). **Planet-like = no flag.**

Reported for every hit, not graded: the offset of the TESS transit from the Gaia ephemeris, the
cycle count and the implied period correction; TESS depth / Gaia depth.

## Hypotheses and labels (fixed now)

- **G0a (validity):** recovery of KNOWN_PLANET candidates in the rate sample. PIPELINE_OK if
  ≥ 0.80 with at least 10 such stars; PIPELINE_FAILS if below; UNTESTABLE if fewer than 10.
- **G0b (validity):** CONTROLS_OK if the control rate ≤ 0.08 per trial, else CONTROLS_NOISY.
- **G1 (main):** fraction of NEW rate-sample candidates seen in TESS,
  f = (hits − control rate × n) / n, with a Garwood 95% interval on the hits minus the same
  expectation. MOSTLY_SEEN if f ≥ 0.5; MIXED if 0.2 ≤ f < 0.5; MOSTLY_NOT_SEEN if f < 0.2;
  UNTESTABLE if n < 10. **G1 is valid only if G0a is not PIPELINE_FAILS and G0b is
  CONTROLS_OK.**
- **G2 (discovery list, not a test):** NEW candidates that hit and are planet-like.
- **G3 (descriptive):** share of NEW hits with at least one flag (eclipsing-binary-like).
- **G4 (exploratory):** among candidates missed at P, the number that hit at P/2 or 2P
  (no injections or alias controls; never used for a claim on its own).

## Two runs

1. **DR3 rehearsal now** (`--schema gaiadr3`, 214 candidates, 2 chunks, jobs
   gaia-vpt-dr3-c0-v1 and -c1-v1; the Heidelberg DR3 mirror is the fallback after ESA closes on
   25 November). It checks the code on a real list and measures G0. It is **not blind**: the
   173 known systems are known, and Panahi et al. already checked the 41 new candidates with
   TESS full-frame images up to 2021. For the 39 unconfirmed DR3 candidates the result is a
   measurement on more TESS data, not a discovery claim.
2. **DR4 on release day** (`--schema gaiadr4`, 1,007 candidates, 6 chunks, then `--combine`).
   This is the blind test of G1-G4.

**Amendment rules.** If the rehearsal shows a code failure (crash, exit 3, a missing column), the
fix goes in 0.1.1 with a dated note before DR4. If the rehearsal gives PIPELINE_FAILS and we
change the search, the DR3 known planets have shaped the fix and cannot validate it: DR4's G0a
is then graded **only on KNOWN_PLANET candidates whose Gaia DR3 source is not in the DR3
list**, and G1 is valid only if that subset passes. If DR4 renames a column of
`vari_planetary_transit`, the job exits 4; a dated amendment that maps the names (and changes
nothing else) comes before any number is read.

## Predictions (fixed now)

DR3 rehearsal:
- G0a: PIPELINE_OK 75%, PIPELINE_FAILS 20%, UNTESTABLE 5%.
- G0b: CONTROLS_OK 75%.
- G1: UNTESTABLE 45% (most of the 41 are now TOIs, confirmed, or too faint for sensitive
  TESS data), MOSTLY_SEEN 25%, MIXED 15%, MOSTLY_NOT_SEEN 15%.
- G2: 0 planet-like NEW candidates 55%, 1-3 40%, more than 3 5%.

DR4 (blind):
- G0a: PIPELINE_OK 80%.
- G1: MOSTLY_SEEN 40%, MIXED 35%, MOSTLY_NOT_SEEN 15%, UNTESTABLE 10%.
- G2: 0 planet-like NEW candidates 10%, 1-5 35%, 6-20 35%, more than 20 20%.
- G3: eblike share below 25% 20%, 25-50% 40%, above 50% 40%.

## What happens to a planet-like NEW candidate

Nothing is called a planet. In order: (1) prior-art search (ExoFOP, SIMBAD, NASA Exoplanet
Archive, arXiv, TESS EB catalogues); (2) Gaia's own RVs and orbits (`transit_rv_screen.py`,
runbook step f) to rule out stellar companions; (3) a pixel-level which-star test on a TESS
cutout before any radius is quoted (as for TYC 6340-23-1). Only survivors are written up as
candidates. Reporting to ExoFOP as community TOIs needs a TFOP member, which goes to Sheehan.

## Limits known in advance

Gaia's duration is a box width, so injected transits are boxes and real ones are not. Up to 3
sectors per star are searched, not all. TESS pixels are 21″, so blended neighbours can produce
or dilute a dip; flags use the deeper of the Gaia and TESS depths for size. The secondary test
assumes a circular orbit. Candidates with P longer than about 8 d have fewer than 3 transits in a
sector and fall out of the rate sample.
