# Step g5, amendment 3: DR4 calls the binary-mass table `nss_masses`

MV2, Munim, Inc. Made with AI agents working in his name. CC BY 4.0. Written 2026-11-24 (~22:30
UTC), before Gaia DR4 exists. Code: `sb2_screen_dr4_nssm.py` 0.1.0 (wraps `sb2_screen_dr4` 0.2.0
at f282d09 unchanged), tests `test_sb2_screen_dr4_nssm.py`.

## Why

ESA's DR4 content page (read 24 Nov 2026) lists the binary-mass table as **`nss_masses`**
(4,323,300 rows, new in the archive), not DR3's `binary_masses`. `sb2_screen_dr4` 0.2.0 reads only
`binary_masses`. On release day its schema gate would therefore find no mass table and fall to arm
B (the brightest 800 SB2 orbits, no edge-on cut), which was meant only for a DR4 without masses.

## The change (data access only)

If `binary_masses` lacks source_id, m1 or combination_method but `nss_masses` has all three, the
screen joins `nss_masses` instead, with `combination_method LIKE 'SB2%'` (DR3 used the single value
'SB2+M1'; DR4's labels are not published). If both tables are complete, `binary_masses` is used as
before. If neither is, arm B as before. Selection rule (0.95 <= M1 sin^3 i / M1 <= 1.10, P < 8 d),
lookups, grades and predictions: unchanged.

## Release day

Run `python sb2_screen_dr4_nssm.py` with the same arguments as `sb2_screen_dr4.py` (the template in
`runbook/dr4-addendum.md` with only the script name changed). The log line "masses table:" records
which table was used. If arm A via `nss_masses` selects fewer than 20 stars, the result is reported
and the reason (DR4 combination_method labels) is checked before any re-run.
