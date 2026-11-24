# sb2-debcat amendment 1: an anchored DEBCat parser, a loader rehearsal, and the DR4 test fixed in advance

MV2, Munim, Inc. Made with AI agents working in his name; no human expert has checked this yet.
Text CC BY 4.0, code Apache-2.0. Written 2026-11-24 (~05:00 UTC). **Job sb2-debcat-v1 never ran**
(it was still queued for memory when this was written), so no DEBCat row and no match has been seen.
This amends `findings/2026-11-24-sb2-debcat-prereg.md`; everything not changed here stands.
Code: `sb2_debcat.py` 0.2.0 with `test_sb2_debcat.py`. Job: **sb2-debcat-v2** replaces v1.

## Why

While preparing the Gaia DR4 version we checked what DEBCat's web table looks like. We still cannot
load the page ourselves, but a web-search summary of the page says that each column of the table
gives **both stars' values** ("Mass (Msun)": 1.1345 ± 0.0032 and 1.1241 ± 0.0045 for KX Cnc). If both
values sit in one cell, parser 0.1.0 would have taken the first ± value of each cell. It would have
read star A's radius as star B's mass, and the registered row-count gate (≥ 100 systems) would not
have caught it. Every grade would have been wrong. We also found that DEBCat publishes an ascii file,
`debs.dat` (whitespace columns including log(M1) and log(M2), with −9.99 for missing values), used by
a public teaching repository (University-at-Buffalo-SEDS/DEBCat-Exploration).

## Changes (no grade, threshold or prediction from the original registration changes)

1. **Every ± pair is read, in order**, from each cell and from the row that follows (for layouts with
   one row per star). A row whose "period" carries a ± is not a system.
2. **Anchoring.** `debs.dat` is downloaded as well. A system enters the analysis only if its
   web-table name matches a `debs.dat` name (case, spaces, underscores and Greek letters normalised)
   and the web table holds ± values equal to `debs.dat`'s two masses (within 0.5% + 0.0006 M☉). The
   masses and errors used are those web-table values. So the masses always come from two DEBCat
   files that agree, whatever the page layout.
3. **New gate (exit 3, nothing graded):** fewer than 100 systems in the web table or in
   `debs.dat`, or fewer than **100 anchored systems**. Reported but not graded: how often the 0.1.0
   positional reading agrees with the anchored masses (it tells us whether v1 would have been
   right).
4. **Loader rehearsal (control, not a grade):** after grading from VizieR, the job reads the same
   matched orbits from a Gaia TAP service (ESA, then AIP Potsdam) in `gaiadr3.nss_two_body_orbit`.
   LOADER_CONTROL_OK if every matched orbit agrees (P to 1e-4 relative, K1 and K2 to 0.01 km/s).
   This rehearses the DR4 code path on known data. If no TAP service answers (ESA's archive closes
   on 25 Nov 12:00 CET), the result is LOADER_CONTROL_UNAVAILABLE and the grades still stand.
5. Self-test extended to cell-per-value, stacked-cell and row-per-star layouts, `debs.dat`
   (log and linear masses), anchoring, TAP CSV and DR3→DR4 neighbour selection.

Predictions added now: unit tests and self-test pass 80%; ANCHOR_OK 70%; the 0.1.0 positional
reading agrees with the anchored masses for fewer than half the anchored systems, meaning v1 would
have been wrong, 60%; LOADER_CONTROL_OK given that a TAP service answers 85%.

## The DR4 test, fixed eight days before Gaia DR4 (runbook step g6)

ESA's DR4 contents page (read 24 Nov) lists `nss_two_body_orbit` (5,901,111 rows; astrometric,
spectroscopic and eclipsing binaries), a new `nss_masses` table (4,323,300 rows), double-lined epoch
velocities (`rvs_epoch_parameters_double`) and `dr3_neighbourhood`. It also says that DR4 source
identifiers must not be assumed equal to DR3's. On release day (2 Dec, after 12:00 CET) we file:

```
python -m unittest -v test_sb2_debcat
python sb2_debcat.py --gaia tap --schema gaiadr4 --tap-url https://gea.esac.esa.int/tap-server/tap/sync --out-dir /out
```

as job **sb2-debcat-dr4-v1** (same code, commit of this amendment). Rules:
- **Schema gate (exit 4):** `gaiadr4.nss_two_body_orbit` must have source_id, nss_solution_type,
  period, eccentricity and both semi-amplitudes with errors. Otherwise a schema amendment is written
  before anything is matched.
- **Which orbits:** every DR4 `nss_two_body_orbit` row with a non-null `semi_amplitude_secondary`,
  whatever its solution type name.
- **DR3 → DR4:** through `gaiadr4.dr3_neighbourhood`, taking the nearest candidate by angular
  distance. MAP_CONTROL_OK if RZ Cha's DR3 source has a DR4 counterpart.
- **End-to-end control:** if RZ Cha has a DR4 double-lined orbit, its period must be within 0.5% of
  2.832 d (PIPE_CONTROL_OK). The change in its K values from DR3 is reported.
- **Grades:** Q1-Q4 exactly as registered for DR3 (same thresholds, seeds and sample rule).
- **Exploratory, not graded:** Gaia's own `nss_masses` (m1 + m2) over DEBCat's total mass, if those
  columns exist.

DR4 predictions (fixed now):

| prediction | probability |
|---|---|
| schema gate passes without an amendment | 60% |
| more DEBCat systems with a PERIOD_OK double-lined orbit in DR4 than in DR3 | 80% |
| DR4 Q1 Q_UNBIASED | 65% |
| DR4 Q2 MASS_SCALE_OK | 60% |
| DR4 robust std of z_q lower than DR3's (Q3) | 55% |
| DR4 Q4 BLEND_SIGNAL | 25% |

The DR3 and DR4 runs share a sample definition, so the comparison also tests a claim no one has
yet checked from outside: whether 66 months of Gaia spectroscopy improved its double-lined orbits
over 34 months.

## Limits

The layout description came from a search summary, not from the page itself. The anchoring rule
is meant to be right whatever the layout, but it has been tested only on our own snippets. A system
with a mass that equals another of its own tabulated values within 0.5% could be anchored to the
wrong cell; this needs two near-equal masses or radii and should be rare. Systems that `debs.dat`
lacks or names differently are dropped, so the sample may be smaller than with 0.1.0. The DR4 column
names of `dr3_neighbourhood` are not yet known; the code accepts `dr3_source_id` with
`dr4_source_id` or `source_id`, and otherwise stops at the gate.
