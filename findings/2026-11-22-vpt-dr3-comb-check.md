# The step-g DR3 rehearsal recomputed by code: every hand-made count holds

MV2, Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0.
Written 2026-11-22 (~19:15 UTC). Job **gaia-vpt-dr3-comb-v1** (blade, 16:02-16:07 UTC), code
`gaia_vpt_tess.py` 0.1.1 at commit 945ad9850ca0837a93050d77f121c788a5db58e3, inputs the two
committed chunk files `data/vpt-dr3-v1/c0/` and `c1/`, plus a fresh Gaia RVS query. Outputs:
`data/vpt-dr3-comb-v1/`.

The full results of 21 Nov (`findings/2026-11-21-vpt-dr3-results.md`) were counted by hand from
the two chunk files. This job recomputes them with the code's own `--combine` step:

| quantity | by hand (21-22 Nov) | by code (22 Nov) | file |
|---|---|---|---|
| G5: Gaia period = known period | 15 of 176 | 15 of 176 (0.085, 95% 0.052-0.136) | `comb/vpt_summary.json` |
| G0a: known planets recovered | 14 of 15 | 14 of 15 (PIPELINE_OK) | same |
| G0b: control hits | 46 of 330 | 46 of 330 (43/252 other-period, 0/30 known planets) | same |
| G1b: new candidates seen | 7 of 19 | 7 of 19 (MIXED) | same |
| G2: planet-like new hits | 3 | 3 | same |
| G2b: survivors after RVS | TIC 4638108, TIC 44997521 | same two | same |
| RVS, NEW candidates variable | 8 of 12 | 8 of 12 | `rvs/vpt_rvs_summary.json`, `comb/vpt_summary.json` |
| RVS, known planets variable | 2 of 10 | 2 of 10 | same |
| RVS, known systems at other periods | 2 of 100 | 2 of 100 | same |

No difference, so no correction is needed. The held-out chunk alone (`comb_c1/`) and chunk 0
alone (`comb_c0/`) are also in the data folder. Status counts: 209 of 214 with TESS data, 5 with
none.
