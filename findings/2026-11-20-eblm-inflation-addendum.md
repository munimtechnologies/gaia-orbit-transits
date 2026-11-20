# Addendum to the M-dwarf inflation note (pre-registered trigger)

Written 2026-11-20 by MV2 of Munim, Inc.; made with AI agents working in his name, not checked by
a human expert. Text CC BY 4.0.

Applies to: `findings/2026-11-19-eblm-infl-full-results.md` (28 M dwarfs at 0.89-3.52 d sit
+6.3%, 95% CI +1.0% to +8.8%, above BHAC15 5-Gyr radii; label INCONCLUSIVE).

The holdout pre-registration (`findings/2026-11-19-eblm-holdout-prereg.md`) says: "In every case, a
median radius offset beyond ±3% gets a public addendum to the inflation note." The holdout check
of eblm_fit 0.2.0 found a median offset of **-5.3%** over 14 published EBLM XIX systems and
graded **PIPELINE_FAILED** (6 of 14 passed; `findings/2026-11-20-eblm-holdout-results.md`).

What this means for the +6.3%:
- The inflation sample was fitted with eblm_fit 0.1.0, which treats every orbit as circular
  (expected at 0.9-3.5 d, where tides circularise such orbits). For circular orbits 0.1.0 and
  0.2.0 use the same formulas. On the circular holdouts the median
  offset is -1.6% (7 systems; exploratory, computed after the grade). The first outside check of
  0.1.0 gave -0.9% (6 systems).
- All of the holdout's large radius misses go the same way: our radii come out too small. If
  that applied to the inflation sample, the true offset above the models would be larger, not
  smaller. But the holdout systems have longer periods (5.6-10.6 d) and cooler primaries than the
  inflation sample, so the bias cannot be transferred with confidence.
- The pipeline failed its pre-registered check, so **the +6.3% stays a caveated, INCONCLUSIVE
  measurement**. As pre-registered, no Gaia DR4 inflation result will come from this pipeline.
