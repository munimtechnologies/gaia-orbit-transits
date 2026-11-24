# SPDX-License-Identifier: Apache-2.0
"""sb2_screen_dr4_nssm 0.1.0 - amendment 3 to runbook step g5 (edge-on double-lined screen on DR4).

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Apache-2.0.
Amendment: findings/2026-11-24-g5-amendment-3-nss-masses.md (written 24 Nov 2026, before DR4).

ESA's DR4 content page lists the binary-mass table as `nss_masses` (4,323,300 rows), not DR3's
`binary_masses`. sb2_screen_dr4 0.2.0 looks only for `binary_masses`; on DR4 it would silently
fall to arm B (brightest 800 SB2s, no edge-on cut). This wrapper changes nothing else: if
`binary_masses` lacks the required columns but `nss_masses` has them (source_id, m1,
combination_method), the screen uses `nss_masses` with combination_method LIKE 'SB2%' (DR3 used the
single value 'SB2+M1'; DR4's labels are not known yet). Selection rule, lookups, grades: unchanged.

Usage: python sb2_screen_dr4_nssm.py [any sb2_screen_dr4 arguments]
"""
import sys

import sb2_screen_dr4 as g5

s0 = g5.s0
VERSION = "0.1.0"
ORBIT_QUERY_BM = s0.ORBIT_QUERY
ORBIT_QUERY_NSSM = (ORBIT_QUERY_BM.replace("{s}.binary_masses", "{s}.nss_masses")
                    .replace("b.combination_method = 'SB2+M1'", "b.combination_method LIKE 'SB2%'"))


def adapt(cols):
    """-> (cols, masses table used). Aliases nss_masses as binary_masses when only it is complete,
    and switches the orbit query to it."""
    bm, nm = cols.get("binary_masses", set()), cols.get("nss_masses", set())
    if all(c in bm for c in g5.REQ_BM):
        s0.ORBIT_QUERY = ORBIT_QUERY_BM
        return cols, "binary_masses"
    if all(c in nm for c in g5.REQ_BM):
        out = dict(cols)
        out["binary_masses"] = set(nm)
        s0.ORBIT_QUERY = ORBIT_QUERY_NSSM
        return out, "nss_masses"
    s0.ORBIT_QUERY = ORBIT_QUERY_BM
    return cols, None


def discover(schema):
    q = ("SELECT table_name, column_name FROM tap_schema.columns WHERE table_name IN "
         "('{s}.nss_two_body_orbit', '{s}.binary_masses', '{s}.nss_masses', '{s}.gaia_source')"
         ).format(s=schema)
    cols = {}
    for r in s0.tap(q):
        t = str(r.get("table_name", "")).split(".")[-1].strip().lower()
        cols.setdefault(t, set()).add(str(r.get("column_name", "")).strip().lower())
    cols, used = adapt(cols)
    g5.log("masses table:", used)
    return cols


def main(argv=None):
    g5.discover = discover
    return g5.main(argv)


if __name__ == "__main__":
    sys.exit(main())
