# Pre-registration: the low-mass Gaia DR3 SB1 transit-rate test with an outlier-proof hit rule (sb1_robust 0.2.0)

2026-11-18. MV2 of Munim, Inc.; made with AI agents working in his name. Text CC BY 4.0,
code Apache-2.0 (`sb1_robust.py` 0.2.0, which wraps the unchanged `sb1_transit.py` 0.1.0
pinned at v0.15.0). Written and published **before any 0.2.0 job has run**. Jobs
`gaia-sb1rob-k0-v1` … `gaia-sb1rob-k7-v1`.

## Why a second run

The 0.1.0 run (`findings/2026-11-18-sb1-transit-results.md`) passed H1, with an upper bound
of 0.22 on the reality fraction. But its hit rule was fooled by isolated outlying bins, so
C2 (false alarms) and H3 (timing) failed, and the candidate list was noise. 0.2.0 repeats
the same test on a fresh, larger random sample with three changes, all fixed here.

## Changes from 0.1.0 (nothing else changes)

1. **Median rule.** At the best box, compute the median of the binned residuals inside the
   box, `med_ratio = −median(r_in) / depth`. A sector hit additionally needs
   **med_ratio ≥ 0.5**. The rule sits inside `sector_hit`, so it applies equally to real
   folds, the two control folds and the four injections per sector. For a real transit,
   med_ratio ≈ 1 ± 1.25/SNR. For a few deep outliers in a flat box, it is ≈ 0.
2. **No fallback query.** The Gaia sample must come from the full query with
   `astrophysical_parameters`. That query is retried four times (timeout 300 s, 120 s
   apart), and otherwise the job stops with exit 2.
3. **Order.** The eligible pool is sorted by source_id, shuffled with seed 20261119 and
   split into 8 chunks (i mod 8). Each job works through its chunk for 165 minutes, about
   330 stars, so about 2,600 stars in all. Stars seen by 0.1.0 are not excluded. They are
   simply part of the random sample again.

## Predictions and pass rules (on the 8 jobs combined, unless "per job")

| | prediction | pass rule |
|---|---|---|
| R0 | the pool is the full-parameter pool of 0.1.0 chunk 1 | eligible = 6,434 in every job (otherwise reported, not fatal) |
| C1 | known transiting companions are still found (per job) | ≥ 3 of WASP-18 b, TOI-2533 b, TOI-1712 b, TOI-5427 b in every job |
| C2 | false alarms are now rare | combined control-hit rate ≤ 3% |
| C3 | enough stars (per job) | ≥ 150 in the rate sample |
| **H1** | most low-mass DR3 SB1 orbits at P = 1–13 d do not show the transits a real low-mass companion must give | upper 95% of ρ (SUBSTELLAR_SIZE) < 0.5 |
| **H1b** | and the sharper version | upper 95% of ρ (SUBSTELLAR_SIZE) < 0.2 |
| H2 | (exploratory) longer periods are more often real | ρ_all(P ≥ 5 d) > ρ_all(P < 5 d) |
| H3 | robust hits are real orbital transits | > 50% of the Gaia-timed hits are PHASE_MATCH (needs ≥ 3 timed hits) |
| H4 | (exploratory) spurious orbits concentrate on hot primaries (pulsators) | ρ_all(m₁ ≥ 1.5 M☉) < ρ_all(m₁ < 1.2 M☉) |
| R1 | (descriptive) how much the median rule removes | fraction of 0.1.0-rule hits in the same data that the median rule rejects, from `robust_extra.json` |
| D1 | (report only) | robust SUBSTELLAR_SIZE hits not on the TOI list go to vetting: fold plots, SIMBAD, VSX, ExoFOP, the TESS EB catalogue, Gaia vari_eclipsing_binary, then pixels and centroids. Nothing is called a brown dwarf before that. |

ρ = (N_hit − N_control) / Σ(p_transit × s), with the Garwood 95% interval of N_hit, as in
0.1.0. Chunks are summed with `sb1_robust.combine()`. If a job fails for infrastructure
reasons (Gaia archive down, exit 2), it is re-filed unchanged. The combined grade uses
the jobs that finished, and the report says which ones did.

**My expectation (written before the data):** C2 passes (1–3%), H3 passes, ρ (substellar)
≈ 0.02–0.08 and H1b passes. R1: more than half of the 0.1.0-rule hits are rejected. If
H1b fails with C2 passing, real transiting low-mass companions are more common than the
TOI list suggests, and the D1 list will contain new ones.

## The "wow" if it works

The first calibrated answer to how many of Gaia's brown-dwarf-mass spectroscopic orbits
are real, given one release before DR4 brings ~640,000 RVS orbits. Every robust
substellar hit that survives vetting is a transiting brown dwarf or very-low-mass star
with a Gaia mass. Only a few dozen transiting brown dwarfs are known.

## Limits stated in advance

These carry over from 0.1.0: isotropic p_transit, so ρ measures "real **and** truly low-mass";
box-shaped injections; up to three sectors per star; dilution not corrected. In addition,
the median rule can reject a real transit whose box is only partly in transit (grazing or
very short). The injections have the same box shape, so sensitivity accounts for that only
partly.
