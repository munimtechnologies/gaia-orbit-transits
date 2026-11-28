# SPDX-License-Identifier: Apache-2.0
"""eba_scan 0.2.0 - are the three ZTF eclipse candidates (and two Gaia-flagged machine targets) named
anywhere in the open Eclipses by Appointment catalogue (every text file at its HEAD commit) or in
IJspeert et al. (2024)?

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Apache-2.0.
Same search as eba_scan 0.1.0 (whole digit tokens, one codeload zip of HEAD); new candidate list,
same controls. Stdlib only. Context: findings/2026-11-28-ztf-shallow-flags-graded.md.
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
import zipfile

VERSION = "0.2.0"
UA = "gaia-orbit-transits-eba-scan/0.2 (open research script)"
EBA_REPO = "Snowstar38/eclipses-by-appointment"
OBAF_EB_URL = "https://zenodo.org/api/records/20123193/files/OBAF_EB.csv/content"
TEXT_EXT = (".csv", ".tsv", ".json", ".md", ".html", ".txt")
MAX_BYTES = 60 * 1024 * 1024

# (label, TIC or None, Gaia DR3 id or None, role)
TARGETS = [
    ("UCAC4 583-070217", 358858602, "4535010166315168640", "ZTF eclipse candidate"),
    ("UCAC4 677-002225", 440168538, "391817260687992960", "ZTF eclipse candidate"),
    ("TYC 2091-796-1", 135364450, "4576721896566803072", "ZTF eclipse candidate"),
    ("Gaia DR3 4497399653101181184", 150450235, "4497399653101181184", "Gaia-epoch flag (TESS 10K table 2)"),
    ("Gaia DR3 4229808420168374400", 212684258, "4229808420168374400", "Gaia-epoch flag (TESS 10K table 2)"),
    ("HD 171459", 464315748, "6436666383265499136", "EbA control (CHECKCARD B6)"),
    ("TIC 157469799", 157469799, "1345750246115251840", "EbA control (accepted A98)"),
    ("TYC 3330-286-1", 428977802, "249989572195889664", "EbA control (review files)"),
    ("HIP 27672", 306114087, "265213581990291840", "IJspeert 2024 control"),
    ("RS Cha", 323292655, "5209024611054646272", "IJspeert 2024 control"),
]
EBA_CONTROLS = ("HD 171459", "TIC 157469799", "TYC 3330-286-1")
OBAF_CONTROLS = ("HIP 27672", "RS Cha")
CANDIDATES = ("UCAC4 583-070217", "UCAC4 677-002225", "TYC 2091-796-1",
              "Gaia DR3 4497399653101181184", "Gaia DR3 4229808420168374400")


def fetch(url, timeout=300):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout)


def token_hits(text, tokens):
    out = {}
    for tok in tokens:
        if tok in text:
            pat = re.compile(r"(?<!\d)" + re.escape(tok) + r"(?!\d)")
            lines = [i + 1 for i, ln in enumerate(text.splitlines()) if pat.search(ln)]
            if lines:
                out[tok] = lines
    return out


def scan_zip(src, tokens):
    res = {"n_text": 0, "n_scanned": 0, "skipped_large": [], "errors": {}, "hits": {}}
    with zipfile.ZipFile(src) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename.split("/", 1)[1] if "/" in info.filename else info.filename
            if not name.lower().endswith(TEXT_EXT):
                continue
            res["n_text"] += 1
            if info.file_size > MAX_BYTES:
                res["skipped_large"].append([name, info.file_size])
                continue
            try:
                text = zf.read(info).decode("utf-8", "replace")
            except Exception as exc:  # noqa: BLE001
                res["errors"][name] = repr(exc)
                continue
            res["n_scanned"] += 1
            for tok, lines in token_hits(text, tokens).items():
                ls = text.splitlines()
                res["hits"].setdefault(tok, []).append(
                    {"file": name, "lines": lines[:20], "snippet": [ls[i - 1][:300] for i in lines[:3]]})
    return res


def scan_tic_csv(lines, tics):
    reader = csv.reader(lines)
    header = next(reader)
    col = [h.strip().lower() for h in header].index("tic")
    hits, n = {}, 0
    for row in reader:
        if not row:
            continue
        n += 1
        try:
            t = int(float(row[col]))
        except (ValueError, IndexError):
            continue
        if t in tics:
            hits.setdefault(str(t), []).append(dict(zip(header, row)))
    return hits, n


def verdicts(eba_hits, obaf_hits):
    v = {}
    for label, tic, gid, role in TARGETS:
        files = []
        for tok in (str(tic) if tic else None, gid):
            if tok and tok in eba_hits:
                files += [h["file"] for h in eba_hits[tok]]
        v[label] = {"tic": tic, "gaia": gid, "role": role, "in_eba": bool(files),
                    "eba_files": sorted(set(files)),
                    "in_ijspeert2024_eb": (str(tic) in obaf_hits) if (tic and obaf_hits is not None) else None}
    return v


def grade(v, eba, obaf_ok):
    e_ok = all(v[c]["in_eba"] for c in EBA_CONTROLS)
    o_ok = bool(obaf_ok) and all(v[c]["in_ijspeert2024_eb"] for c in OBAF_CONTROLS)
    complete = bool(eba) and not eba.get("errors") and \
        eba.get("n_scanned", 0) == eba.get("n_text", -1) - len(eba.get("skipped_large", []))
    return {"E0_eba_controls": e_ok, "E0_obaf_controls": o_ok,
            "E1_complete": "SCAN_COMPLETE" if complete else "SCAN_INCOMPLETE",
            "E2_listed": [c for c in CANDIDATES if v[c]["in_eba"] or v[c]["in_ijspeert2024_eb"]],
            "E2_unlisted": [c for c in CANDIDATES if not (v[c]["in_eba"] or v[c]["in_ijspeert2024_eb"])]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--data-dir", default="data")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    os.makedirs(a.data_dir, exist_ok=True)
    out = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    tokens = sorted({str(t[1]) for t in TARGETS if t[1]} | {t[2] for t in TARGETS if t[2]})
    obaf_hits = None
    try:
        resp = fetch(OBAF_EB_URL, timeout=900)
        obaf_hits, n = scan_tic_csv(io.TextIOWrapper(resp, encoding="utf-8", errors="replace", newline=""),
                                    {t[1] for t in TARGETS if t[1]})
        out["obaf_eb"] = {"n_rows": n, "hits": obaf_hits}
    except Exception as exc:  # noqa: BLE001
        out["obaf_eb"] = {"error": repr(exc)}
    try:
        sha = json.load(fetch("https://api.github.com/repos/%s/commits?per_page=1" % EBA_REPO, 120))[0]["sha"]
        path = os.path.join(a.data_dir, "eba-%s.zip" % sha)
        if not os.path.exists(path):
            with fetch("https://codeload.github.com/%s/zip/%s" % (EBA_REPO, sha), 1800) as r, \
                    open(path + ".part", "wb") as fh:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
            os.replace(path + ".part", path)
        out["eba"] = scan_zip(path, tokens)
        out["eba"]["sha"] = sha
    except Exception as exc:  # noqa: BLE001
        out["eba"] = {"error": repr(exc)}
    hits = out["eba"].get("hits", {}) if "error" not in out["eba"] else {}
    v = verdicts(hits, obaf_hits)
    out["verdict"] = v
    out["grade"] = grade(v, out["eba"] if "error" not in out["eba"] else {}, obaf_hits is not None)
    out["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(a.out_dir, "eba_scan_ztf.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out["grade"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
