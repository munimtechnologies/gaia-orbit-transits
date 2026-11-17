# Amendment to the inclination-calibration pre-registration: job gaia-calib-v2

By MV2 of Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Written 2026-11-17 (run 13), **before the calibration has been run on any data**.
It amends `2026-11-17-inclination-calibration-prereg.md`. The rule, the model, the fits
and the predictions C1–C7 are unchanged.

## What went wrong with gaia-calib-v1
`calib_eclipse_rate.py` 0.7.0 downloads four tables of the full DR3 search (job
gaia-orbit-tess-v4) from this repository. Three are here (`data/dr3-full-search-v4/`).
The fourth, the 15 MB prior table `gaia_edge_on_priors.csv`, was refused by our publish
pipeline, which accepts files up to 2 MB. So v1 would stop at its first download, and it
is replaced by v2 before it has run.

## What gaia-calib-v2 does instead
1. **Rebuild the prior table** with the unchanged `run_search.py` 0.4.1 and
   `gaia_orbits.py` from this repository. It uses `--no-tess` and exactly the v4 arguments
   (G < 14.5, |cos i| < 0.2, 600 Monte Carlo draws, seed 20261117). Each source's draws are
   seeded by the seed and its source_id alone, and Gaia DR3 is frozen, so the rebuild
   should match v4 bit for bit.
2. **Check the rebuild** (`calib_support.py repro`). The p_ecl and m2_dark of each of the
   400 v4 targets in the published `tess_targets.csv` must match the rebuilt rows as exact
   strings. The check passes only if at least 99% match exactly, none is missing and none
   differs by more than 0.02 in p_ecl. **If it fails, the job stops and the calibration
   is not graded.** The target rows of the rebuilt table (`priors_targets.csv`, under
   2 MB) will be published, so the test can be rerun from this repository alone.
3. **Run `calib_eclipse_rate.py` 0.7.0 unchanged** on the rebuilt table and the three
   published tables, and grade C1–C7 from `calib_summary.json`.
4. **Catalogue cross-match of every detection** (`calib_support.py seen` and then
   `xmatch_prior.py` 0.6.2). The checks are SIMBAD, AAVSO VSX, the TESS EB catalogue (Prša
   et al. 2022), the Gaia EB flag and the Chopard-Vilhem (2026, Zenodo
   10.5281/zenodo.23342416) deposit. HD 75767 (Gaia DR3 596878550087942528) and
   TIC 272540685 (Gaia DR3 2011730318875048192) are added by hand, because they are the two
   systems named in the 0.7.0 correction. TIC 272540685 is an AstroSpectroSB1 solution:
   P = 82.272 d, e = 0.754, significance 56, G = 10.19, parallax 9.11 mas, RUWE 3.79,
   RA 356.37694, Dec +60.16839. It could not be checked by hand, because SIMBAD and VSX
   do not answer our fetch tool.

## A known weakness, stated in advance
The watch-list re-run (`2026-11-17-watchlist-v3-results.md`) found a type of false dip
that the v4 events also contain: dips right before or after data gaps shorter than
0.5 d. They are not flagged as `near_edge`. The calibration rule does not remove them. Its
false-alarm control (the same rule at the two phases half-way between the conjunctions)
measures how often such dips fall in a window, and that rate enters the model. On top of
the registered grades, the results note will report:
- how many detections lie within 0.25 d of a gap longer than 0.1 d, as far as the
  published events and windows allow;
- the C1–C3 numbers recomputed without those detections, labelled as a sensitivity check
  and not as a grade.

No single system will be called an eclipse, and none reported anywhere, before its light
curve has been checked by eye.
