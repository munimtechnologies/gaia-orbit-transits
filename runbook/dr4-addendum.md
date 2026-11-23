# Gaia DR4 release-day runbook: addendum 1 (steps g4b, g5, pixel; step i pinned)

MV2, Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.
Written 2026-11-23 (~01:45 UTC), nine days before Gaia DR4 (2 December 2026, 12:00 CET).
This file adds to `runbook/dr4-release-day.md` and does not change any step written there.
Where the two differ on the steps below, this file holds.

## Order on release day

a1, a2, a5, b, c, g (6 chunks) + g2 + g2c + i -> a3, a4, c2, g combine -> g3 -> **G6**
(`vpt_pf.py` at 9bf97042, `--n-chunks 5`) -> g4 -> **g4b** -> **g5** -> d, f, h.
After G6: Gaia RVS and duration-versus-density vetting of robust PF2 stars, then the **pixel
step** on the survivors.

## Step (i): pinned and rehearsed

`dr4_rows.py` / `run_search_dr4.py` at commit **b6ae340a25f92c2d16dbcc5212cf9f26f6369951**.
Rehearsal job gaia-dr4-astro-adapter-v1 PASSED on 22 Nov (R1: 400 of 400 DR3 orbits converted to
DR4's Campbell form and back; S1-S5 passed; `data/dr4-astro-adapter-v1/`). Exit 4 = gate G0
(DR4 conventions differ from our assumptions): write an amendment, re-file as -v2. TAP 503 on
day 1: re-file unchanged.

## Step g4b: a period-reliability flag from Gaia's own photometry (pre-registered here)

**Why:** in DR3, N_comp (box-search peaks in Gaia's own G epochs at least 0.9 times as strong as
the peak at Gaia's period) separated right from wrong transit periods with AUC 0.858
(p = 2.4 × 10⁻⁶; `findings/2026-11-22-vpt-epochs-results.md`, `data/vpt-epochs-v2/`). Gaia DR4
publishes epoch photometry for every source, so every DR4 transit candidate can carry the flag.

**Code:** `vpt_epochs.periodogram_fields` (with `freq_grid`, `box_snr`, `count_competitors`)
from `vpt_epochs.py` 0.1.0 at commit f868df8e101aee2c360d9a7b176c3d2356b462b5, imported
unchanged (the 0.1.1 and 0.1.2 patches do not touch it). A thin reader turns DR4's G-band
epoch photometry (format known only on release day) into (t, flux) per candidate and passes
DR4's period and transit duration as `P_gaia` and `dur_gaia`. Epochs flagged as rejected by
DR4 are dropped; nothing else is filtered.

**Flag:** FLAG_UNIQUE if N_comp ≤ 10, FLAG_AMBIGUOUS if N_comp > 10, FLAG_NONE if the
periodogram cannot run (fewer than NIN_MIN + 3 epochs). The cut of 10 comes from the DR3
exploratory bins (7 of 9 right at 0-10; 8 of 163 right above 10) and is now fixed for DR4.

**Registered DR4 test R-g4b (out of sample):** among DR4 candidates that are known transiting
planets (NASA Exoplanet Archive pscomppars on release day; a period is "right" by
`vpt_epochs.period_match` with the DR3 tolerance and factors), compute the AUC of N_comp
(lower = right) and a one-sided Mann-Whitney p. **REPLICATES** if AUC ≥ 0.70 and p ≤ 0.01 with
at least 5 right and 5 wrong periods; **FAILS** if AUC < 0.60 with the same counts;
otherwise **WEAK**; **UNTESTABLE** below the counts.

**Predictions:** REPLICATES 65%, WEAK 15%, FAILS 10%, UNTESTABLE 10%. Share of right periods
among known planets in DR4 at most 0.30: 60% (DR3: 15 of 176). Among FLAG_UNIQUE known planets
at least half right: 55%.

**Use:** FLAG_UNIQUE candidates are also folded at Gaia's period; every candidate still goes
through the period-free search (G6). The flag is published with the DR4 candidate list.

## Step g5: the edge-on double-lined screen on DR4

`sb2_screen.py` 0.1.0 at commit 0a8883c902143934f2ca9933affb57cc01a851b1 (pre-registered for DR3
in `findings/2026-11-22-sb2-screen-prereg.md`; DR3 job sb2-edgeon-screen-v1 queued). On DR4 it
reads DR4's double-lined orbit table with the same selection (P < 8 d; M1 sin³i within 0.95-1.10
of the mass estimate) and the same TESS and catalogue checks, adding the TESS Ten Thousand
catalogue (VizieR J/ApJS/279/50, tables 2-4; reachable through the CfA mirror). If DR4 renames
columns, a dated adapter is written first, as for step (i). Prediction: at least 5 double-lined
eclipsing binaries with Gaia masses that are in no catalogue we check: 50%.

## Pixel step on G6 survivors

Only if job tic93622019-pixel-011-v1 (`pws_amend_011.py`, pixel_which_star 0.1.1;
`findings/2026-11-23-pixel-which-star-amendment-1.md`) ends **CONTROLS_PASS**: run it unchanged,
at the commit that publishes it, on every robust PF2 survivor that passes the RVS and duration
checks, with that survivor's three newest TESS sectors and the two nearest rule-chosen control
planets. If the controls fail again, survivors are published with "pixel test pending" and
the next step is a TESS PRF model, not more tuning.
