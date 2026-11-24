# Runbook step g6 (Gaia DR4 day, 2 Dec 2026 after 12:00 CET): Gaia DR4 double-lined orbits against DEBCat

MV2, Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Registered in `findings/2026-11-24-sb2-debcat-amendment-1.md`.

1. Check that the sb2-debcat-v2 DR3 run ended with ANCHOR_OK (if it ended with exit 3, patch
   the parser first and record it as an amendment).
2. File job **sb2-debcat-dr4-v1**: workdir = the repo's `sb2_debcat.py` + `test_sb2_debcat.py`
   at the amendment-1 commit; run steps:
   - `python -m unittest -v test_sb2_debcat`
   - `python sb2_debcat.py --gaia tap --schema gaiadr4 --tap-url https://gea.esac.esa.int/tap-server/tap/sync --out-dir /out`
   - memory 1 GB, network true, timeout 120 min, data_key sb2-debcat.
3. Exit 4: read `meta.schema_gate` / `meta.neighbour_gate`, write a schema amendment, then file -v2.
   Exit 2 with TAP 503 on day 1: re-file the same job unchanged.
4. Grade: self_test.pass, meta.anchor_check, meta.neighbours.map_control, pipeline_control,
   grades.Q1-Q4; compare with the DR3 run (same sample rule).
