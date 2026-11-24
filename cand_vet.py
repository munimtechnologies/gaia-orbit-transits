# SPDX-License-Identifier: Apache-2.0
"""cand_vet 0.1.0 - are MV2's eclipsing-binary candidates already listed in two catalogues our
earlier vetting could not read?

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Apache-2.0.

1. IJspeert et al. (2024, A&A 691, A242), 69,058 TESS O-F-type eclipsing-binary candidates, as
   re-published with the same TIC column by Vrancken et al. (2026) on Zenodo record 20123193
   (OBAF_EB.csv, 38 MB). The parent sample (OBAF_full.csv, 723 MB, 3.3 million O-F stars) is
   streamed too, so a miss can be told apart from "never in their sample".
2. Every .csv file of the open Eclipses by Appointment catalogue
   (github.com/Snowstar38/eclipses-by-appointment) at the commit that is HEAD when the job runs,
   searched for each TIC number and Gaia DR3 source_id as whole tokens.

Controls (registered in findings/2026-11-24-acv-sb2-conj-dips.md before the job ran):
  C1 Eclipses by Appointment lists TIC 384284045 (TYC 3616-2395-1, its row A179) -> must be found.
  C2 at least one of RS Cha (TIC 323292655) and ZZ Boo (TIC 357358259), bright O-F eclipsing
     binaries with 2-minute TESS data, is in OBAF_EB.csv.
If a control fails, the job reports CONTROL_FAIL and its 'not found' results mean nothing.

Stdlib only. Usage: python cand_vet.py --out-dir /out [--skip-parent]
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
import urllib.request

VERSION = "0.1.0"
UA = "gaia-orbit-transits-cand-vet/0.1 (open research script)"
OBAF_EB_URL = "https://zenodo.org/api/records/20123193/files/OBAF_EB.csv/content"
OBAF_FULL_URL = "https://zenodo.org/api/records/20123193/files/OBAF_full.csv/content"
EBA_REPO = "Snowstar38/eclipses-by-appointment"

# TIC -> (label, Gaia DR3 source_id or None, role)
TARGETS = {
    400170926: ("HD 250735", "3450611154067089408", "claimed new EB (published 23 Nov)"),
    189269584: ("CD-28 7251", None, "claimed new EB (published 23 Nov)"),
    349572805: ("CD-63 310", "5288669213282803328", "Gaia-epoch candidate (24 Nov)"),
    371839648: ("CD-72 1603", "6374372070227419008", "Gaia-epoch candidate (24 Nov)"),
    173207470: ("HD 218299", "1934924724387752832", "ACV-SB2 Gaia-epoch candidate (24 Nov)"),
    57791790: ("HD 101167", "3479008554410838656", "ACV-SB2 Gaia-epoch candidate (24 Nov)"),
    325802598: ("HD 187301", "4297719103037032832", "ACV-SB2 Gaia-epoch candidate (24 Nov)"),
    71945261: ("TYC 6340-23-1", "6853008555751131648", "EB reported 19-20 Nov"),
    93622019: ("TIC 93622019", "5345417757181174144", "Gaia transit candidate"),
    384284045: ("TYC 3616-2395-1", None, "control C1 (listed in EbA, row A179)"),
    323292655: ("RS Cha", "5209024611054646272", "control C2"),
    357358259: ("ZZ Boo", "1450355965609917568", "control C2"),
}


def fetch(url, timeout=300):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout)


def scan_tic_csv(lines, tics):
    """Stream CSV lines (iterable of str); return (header, {tic: [row dict, ...]}, n_rows).
    The TIC column is the column named 'TIC' (case-insensitive)."""
    reader = csv.reader(lines)
    header = next(reader)
    col = [h.strip().lower() for h in header].index("tic")
    hits = {}
    n = 0
    for row in reader:
        if not row:
            continue
        n += 1
        try:
            t = int(float(row[col]))
        except (ValueError, IndexError):
            continue
        if t in tics:
            hits.setdefault(t, []).append(dict(zip(header, row)))
    return header, hits, n


def token_hits(text, tokens):
    """Return {token: [line numbers]} for whole-token matches of digit strings."""
    out = {}
    for tok in tokens:
        pat = re.compile(r"(?<!\d)" + re.escape(tok) + r"(?!\d)")
        lines = [i + 1 for i, ln in enumerate(text.splitlines()) if pat.search(ln)]
        if lines:
            out[tok] = lines
    return out


def stream_lines(url):
    resp = fetch(url, timeout=600)
    return io.TextIOWrapper(resp, encoding="utf-8", errors="replace", newline="")


def eba_check(tokens):
    meta = json.load(fetch("https://api.github.com/repos/%s/commits?per_page=1" % EBA_REPO))
    sha = meta[0]["sha"]
    tree = json.load(fetch("https://api.github.com/repos/%s/git/trees/%s?recursive=1" % (EBA_REPO, sha)))
    files = [t["path"] for t in tree.get("tree", []) if t.get("type") == "blob" and t["path"].lower().endswith(".csv")]
    res = {"sha": sha, "n_csv": len(files), "truncated_tree": bool(tree.get("truncated")), "hits": {}, "errors": {}}
    for p in files:
        url = "https://raw.githubusercontent.com/%s/%s/%s" % (EBA_REPO, sha, urllib.request.quote(p))
        try:
            text = fetch(url).read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 - record and continue
            res["errors"][p] = repr(exc)
            continue
        for tok, lines in token_hits(text, tokens).items():
            snippet = [text.splitlines()[i - 1][:300] for i in lines[:3]]
            res["hits"].setdefault(tok, []).append({"file": p, "lines": lines[:20], "snippet": snippet})
        time.sleep(0.2)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--skip-parent", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    tics = set(TARGETS)
    out = {"version": VERSION, "targets": {str(k): list(v) for k, v in TARGETS.items()}}

    try:
        _, hits, n = scan_tic_csv(stream_lines(OBAF_EB_URL), tics)
        out["obaf_eb"] = {"n_rows": n, "hits": {str(k): v for k, v in hits.items()}}
    except Exception as exc:  # noqa: BLE001
        out["obaf_eb"] = {"error": repr(exc)}
    if not a.skip_parent:
        try:
            _, hits, n = scan_tic_csv(stream_lines(OBAF_FULL_URL), tics)
            out["obaf_full"] = {"n_rows": n, "in_parent": sorted(hits)}
        except Exception as exc:  # noqa: BLE001
            out["obaf_full"] = {"error": repr(exc)}

    tokens = [str(t) for t in TARGETS] + [v[1] for v in TARGETS.values() if v[1]]
    try:
        out["eba"] = eba_check(tokens)
    except Exception as exc:  # noqa: BLE001
        out["eba"] = {"error": repr(exc)}

    eb_hits = out.get("obaf_eb", {}).get("hits", {})
    eba_hits = out.get("eba", {}).get("hits", {})
    c1 = "384284045" in eba_hits
    c2 = "323292655" in eb_hits or "357358259" in eb_hits
    out["controls"] = {"C1_eba_finds_TYC3616": c1, "C2_obaf_eb_finds_RSCha_or_ZZBoo": c2}
    verdict = {}
    for t, (label, gid, role) in TARGETS.items():
        verdict[label] = {
            "tic": t,
            "in_ijspeert2024_eb": str(t) in eb_hits,
            "in_ijspeert2024_parent": (t in out.get("obaf_full", {}).get("in_parent", [])) if "in_parent" in out.get("obaf_full", {}) else None,
            "in_eba": (str(t) in eba_hits) or (gid in eba_hits if gid else False),
            "role": role,
        }
    out["verdict"] = verdict
    out["status"] = "OK" if (c1 and c2) else "CONTROL_FAIL"
    with open(os.path.join(a.out_dir, "cand_vet.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({"status": out["status"], "controls": out["controls"], "verdict": verdict}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
