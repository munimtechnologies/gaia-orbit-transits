# ACV-labelled Gaia SB2s, batch 2 (P 2.0-3.0 d): out-of-sample test, fixed before reading any epoch

2026-11-24 ~20:05 UTC, gaia-orbit-transits. By MV2 of Munim, Inc.; made with AI agents working in
his name. Written in the run's work folder BEFORE any batch-2 epoch was fetched; it is committed
together with the results (the publish lane commits after the run), so the order is recorded here
and in the run log, not by a separate earlier commit.

Rule: unchanged `gaia_conj_dips_acv` 0.1.0 (public since v0.62.0, 24 Nov 17:49Z): dip = unflagged
G epoch >= max(0.025 mag, 4 robust SD) fainter than the median; window +/-0.035 in phase around
the two conjunctions (true anomaly 90-omega, 270-omega; 0.25/0.75 for SB2C); variability-flagged
epochs listed separately.

Batch: every Gaia DR3 SB2/SB2C orbit whose vari_classifier best class is ACV|CP|MCP|ROAM|ROAP|SXARI
with 2.0 < P < 3.0 d not read before (AIP TAP list of 100 rows, 24 Nov ~20:00Z), i.e. 15 stars:
6158619786886806016, 355656522274764288, 3032388065085357440, 4211060509978414208,
5387577190509272832, 66729880383767168, 4945020530510815360, 265213581990291840,
911500121588495744, 3347294105150514688, 4582483440569725184, 1853022343761824768,
5645527428755291648, 5305914640875063424, 6879998061518438400.

Predictions (batch 1 rate: 4 of 16 stars with dips, all 9 clear unflagged dips in window):
- B1: at least 2 of the 15 stars show >= 1 unflagged dip.
- B2: of all unflagged dips in batch 2, more than half fall inside the window (chance ~0.14 each).
- B3 (null we try to reject): dips are spread evenly in phase (expected ~14% in window).
Stars already known as eclipsing (VSX/literature, checked only AFTER the dips are listed) count as
positive controls and are reported separately from candidates.
