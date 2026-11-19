# SPDX-License-Identifier: Apache-2.0
"""dr4_d3_a1.py 0.1.0 -- the D3 (TESS) grade of the Gaia DR4 SB1-reality test, with the
amendment-1 radius rule. MV2 of Munim, Inc.; made with AI agents working in his name.
Apache-2.0. Standard library only.

Why this file exists
--------------------
findings/2026-11-19-sb1-robust-amendment-1.md, item 5, promised before Gaia DR4 (2 Dec 2026):
  - stars whose primary radius cannot be trusted (sb1_combine.radius_flag: 'clamped',
    'giant_cmd', 'no_distance') are excluded from the TESS grade (D3) of dr4_sb1_reality.py;
  - the rho_DR3 passed to D3 is the amendment-1 (A1) combined value of sb1_combine.
dr4_sb1_reality.py 0.1.0 (pinned, unchanged) has a `grade-tess` subcommand without the rule.
This wrapper calls its grade_d3() unchanged, twice:
  - D3_A1 (the grade): flagged stars removed, rho_DR3 = A1 combined rho_substellar_size;
  - D3_without_radius_rule (reported only): all stars, rho_DR3 = primary combined value.
Both use sb1_combine.rate_summary (tested to reproduce sb1_transit.rate_summary) so no
sb1_transit / numpy import is needed. The radius rule is imported from sb1_combine, never
copied, so the DR4 grade uses exactly the rule that graded DR3.

Usage (release day, after `dr4_sb1_reality.py run --schema dr4` and sb1_combine):
  python dr4_d3_a1.py --records OUT/sb1_reality_records.csv \
      --combined data/sb1comb/combined_summary.json \
      --fetch https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/data/sb1rob-v1 \
      --chunks 0-7 --reality-summary OUT/sb1_reality_summary.json --out-dir OUT
Exit codes: 0 ok; 3 no chunk rows or no records; 4 the combined summary lacks the A1 block.
"""
import argparse
import csv
import json
import math
import os
import sys

import dr4_sb1_reality as R
import sb1_combine as sc

VERSION = "0.1.0"
RULE = ("amendment 1 item 5 (findings/2026-11-19-sb1-robust-amendment-1.md): stars with "
        "sb1_combine.radius_flag != '' removed before D3; rho_DR3 = A1 combined value")


def rate_adapter(rows):
    """sb1_combine.rate_summary in the flat shape grade_d3 reads."""
    s = sc.rate_summary(rows)
    r, a = s["rho_substellar_size"], s["rho_all"]
    return {"n_rate_sample": s["n_rate_sample"],
            "expected_if_all_real": s["expected_if_all_real"],
            "n_hit_substellar_size": s["n_hit_substellar_size"],
            "rho_substellar_size": r["rho"], "rho_substellar_size_ci95": r["ci95"],
            "rho_all": a["rho"], "rho_all_ci95": a["ci95"]}


def drop_flagged(rows):
    """(kept rows, {reason: n}) -- every row with a radius flag is removed; reasons are
    counted over distinct source_ids in the rate sample (what changes E)."""
    kept, reasons, seen = [], {}, set()
    for r in rows:
        f = sc.radius_flag(r)
        if not f:
            kept.append(r)
            continue
        sid = str(r.get("source_id", "")).strip()
        if sc.in_rate_sample(r) and sid not in seen:
            seen.add(sid)
            reasons[f] = reasons.get(f, 0) + 1
    return kept, reasons


def rho_from_combined(comb):
    """(rho_A1, rho_primary) from sb1_combine's combined_summary.json; KeyError if absent."""
    a1 = comb["amendment1"]["summary"]["rho_substellar_size"]["rho"]
    pr = comb["primary"]["summary"]["rho_substellar_size"]["rho"]
    return a1, pr


def grade(recs, rows, rho_a1, rho_primary=None):
    kept, reasons = drop_flagged(rows)
    d3 = R.grade_d3(recs, kept, rate_adapter, rho_a1)
    d3.update({"rule": RULE, "removed_by_reason": reasons,
               "n_removed": sum(reasons.values())})
    raw = R.grade_d3(recs, rows, rate_adapter,
                     rho_primary if rho_primary is not None else rho_a1)
    raw["note"] = "reported only; the grade is D3_A1"
    return {"version": VERSION, "D3_A1": d3, "D3_without_radius_rule": raw,
            "agree": d3.get("pass") == raw.get("pass")}


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    return o


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--records", required=True, help="sb1_reality_records.csv of a finished run")
    ap.add_argument("--combined", required=True, help="sb1_combine combined_summary.json")
    ap.add_argument("--chunk-dir", action="append", default=[])
    ap.add_argument("--fetch", default="")
    ap.add_argument("--chunks", default="0-7")
    ap.add_argument("--reality-summary", default="", help="sb1_reality_summary.json (for D1)")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)

    with open(a.records, newline="") as fh:
        recs = list(csv.DictReader(fh))
    with open(a.combined) as fh:
        comb = json.load(fh)
    try:
        rho_a1, rho_pr = rho_from_combined(comb)
    except (KeyError, TypeError) as exc:
        print("combined summary lacks the amendment-1 block:", exc)
        return 4
    loaded, missing = sc.load_chunks(a.chunk_dir, a.fetch or None,
                                     sc.parse_chunks(a.chunks) if a.fetch else ())
    rows = [r for _, rs, _ in loaded for r in rs]
    if not recs or not rows:
        print("no records or no chunk rows; missing chunks:", missing)
        return 3
    res = grade(recs, rows, rho_a1, rho_pr)
    res.update({"chunks_used": [n for n, _, _ in loaded], "chunks_missing": missing,
                "rho_dr3_a1": rho_a1, "rho_dr3_primary": rho_pr})
    if a.reality_summary:
        with open(a.reality_summary) as fh:
            g = dict(json.load(fh).get("grades", {}))
        g["D3"] = res["D3_A1"]
        res["reading"] = R.reading(g)
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "d3_a1_grade.json"), "w") as fh:
        json.dump(_clean(res), fh, indent=1)
    print(json.dumps(_clean({k: res.get(k) for k in ("chunks_used", "chunks_missing", "agree",
                                                      "reading")})))
    print("D3_A1 pass:", res["D3_A1"].get("pass"), "| without rule:",
          res["D3_without_radius_rule"].get("pass"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
