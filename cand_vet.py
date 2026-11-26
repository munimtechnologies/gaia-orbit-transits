# SPDX-License-Identifier: Apache-2.0
"""cand_vet 0.2.0 - are MV2's eclipsing-binary claims and candidates already listed anywhere in the
open Eclipses by Appointment catalogue, or in IJspeert et al. (2024)?

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Apache-2.0.
Pre-registration: findings/2026-11-26-candidate-vet-v2-prereg.md

Changes from 0.1.0 (which found CD-28 7251 in the catalogue's CHECKCARD.csv, a file our hand vetting
had not read):
  * every text file of the catalogue (.csv .tsv .json .md .html .txt), not only .csv;
  * the whole HEAD commit is read from one codeload zip, so no file is missed silently (fallback:
    the git tree, with a truncated listing completed by walking sub-trees);
  * targets may have a TIC, a Gaia DR3 source_id, or both (single-lined candidates have no TIC here);
  * three catalogue controls that must be found: TYC 3616-2395-1 (accepted-systems row A179),
    CD-28 7251 (CHECKCARD row B7), HD 171459 (CHECKCARD row B6);
  * the 723 MB IJspeert parent sample is no longer streamed.

1. IJspeert et al. (2024, A&A 691, A242) O-F eclipsing-binary candidates, as re-published with the
   same TIC column on Zenodo record 20123193 (OBAF_EB.csv, 38 MB), searched by TIC.
2. Every text file of github.com/Snowstar38/eclipses-by-appointment at its HEAD commit, searched for
   each TIC and Gaia DR3 source_id as whole digit tokens.

Stdlib only. Usage: python cand_vet.py --out-dir /out [--skip-obaf]
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

VERSION = "0.2.0"
UA = "gaia-orbit-transits-cand-vet/0.2 (open research script)"
OBAF_EB_URL = "https://zenodo.org/api/records/20123193/files/OBAF_EB.csv/content"
EBA_REPO = "Snowstar38/eclipses-by-appointment"
TEXT_EXT = (".csv", ".tsv", ".json", ".md", ".html", ".txt")
MAX_BYTES = 60 * 1024 * 1024

# (label, TIC or None, Gaia DR3 source_id or None, role)
TARGETS = [
    ("HD 250735", 400170926, "3450611154067089408", "claimed new SB2 EB (23 Nov)"),
    ("BD+15 2743", 119613818, "1185962761030147072", "claimed new SB2 EB (25 Nov)"),
    ("HD 11239", 115321276, "4961129715887496320", "claimed new SB2 EB (26 Nov)"),
    ("HD 125386A", 1021067547, "5854558019550047872", "claimed new SB1 EB (26 Nov)"),
    ("HD 125386 blend", 337318750, None, "TIC of the blended pair HD 125386"),
    ("TYC 6340-23-1", 71945261, "6853008555751131648", "claimed EB (19-20 Nov)"),
    ("TYC 3330-286-1", 428977802, None, "weak SB2 EB candidate"),
    ("TIC 93622019", 93622019, "5345417757181174144", "Gaia transit candidate"),
    ("TIC 44997521", 44997521, "5432318139709900160", "Gaia transit candidate"),
    ("TIC 4638108", 4638108, "5431056347037926784", "Gaia transit candidate"),
    ("TYC 1316-1554-1", None, "3350075697770930304", "SB1 eclipse candidate"),
    ("TYC 3384-347-1", None, "968093290740779008", "SB1 eclipse candidate"),
    ("UCAC4 544-021692", None, "3350386649103238016", "SB1 eclipse candidate"),
    ("UCAC4 468-115332", None, "4289848214689460736", "SB1 eclipse candidate"),
    ("UCAC4 194-101841", None, "5900468269330031744", "SB1 eclipse candidate"),
    ("TYC 3616-2395-1", 384284045, None, "control E1 (EbA accepted-systems row A179)"),
    ("CD-28 7251", 189269584, "5633392634307163776", "control E2 (EbA CHECKCARD row B7)"),
    ("HD 171459", 464315748, "6436666383265499136", "control E3 (EbA CHECKCARD row B6)"),
    ("RS Cha", 323292655, "5209024611054646272", "control O1 (IJspeert 2024 EB)"),
    ("ZZ Boo", 357358259, "1450355965609917568", "control O1 (IJspeert 2024 EB)"),
]
EBA_CONTROLS = ("TYC 3616-2395-1", "CD-28 7251", "HD 171459")
OBAF_CONTROLS = ("RS Cha", "ZZ Boo")


def fetch(url, timeout=300):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout)


def get_json(url):
    return json.load(fetch(url, timeout=120))


def tokens_for(targets):
    """-> {token: label} for every TIC and Gaia id."""
    out = {}
    for label, tic, gid, _ in targets:
        if tic:
            out[str(tic)] = label
        if gid:
            out[str(gid)] = label
    return out


def token_hits(text, tokens):
    """Return {token: [line numbers]} for whole-token matches of digit strings."""
    out = {}
    lines = text.splitlines()
    for tok in tokens:
        if tok not in text:
            continue
        pat = re.compile(r"(?<!\d)" + re.escape(tok) + r"(?!\d)")
        found = [i + 1 for i, ln in enumerate(lines) if pat.search(ln)]
        if found:
            out[tok] = found
    return out


def scan_tic_csv(lines, tics):
    """Stream CSV lines; return (header, {tic: [row dict, ...]}, n_rows). TIC column named 'TIC'."""
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


def list_blobs(tree_sha, getj, prefix="", depth=0):
    """All blobs under a git tree as [(path, size)]. A truncated recursive listing is completed by
    listing the tree non-recursively and descending into each sub-tree. -> (blobs, n_api_calls)."""
    calls = 1
    base = "https://api.github.com/repos/%s/git/trees/%s" % (EBA_REPO, tree_sha)
    tree = getj(base + "?recursive=1")
    if not tree.get("truncated"):
        blobs = [(prefix + t["path"], int(t.get("size") or 0)) for t in tree.get("tree", [])
                 if t.get("type") == "blob"]
        return blobs, calls
    if depth > 6:
        raise RuntimeError("tree too deep at %r" % prefix)
    flat = getj(base)
    calls += 1
    blobs = []
    for t in flat.get("tree", []):
        if t.get("type") == "blob":
            blobs.append((prefix + t["path"], int(t.get("size") or 0)))
        elif t.get("type") == "tree":
            sub, c = list_blobs(t["sha"], getj, prefix + t["path"] + "/", depth + 1)
            blobs.extend(sub)
            calls += c
    return blobs, calls


def is_text(path):
    return path.lower().endswith(TEXT_EXT)


def scan_zip(zsrc, tokens):
    """Scan every text member of a zip archive (path or file object) for whole digit tokens.
    The archive's top folder (repo-sha/) is stripped from member names."""
    res = {"n_blobs": 0, "n_text": 0, "skipped_large": [], "hits": {}, "errors": {}, "n_scanned": 0}
    with zipfile.ZipFile(zsrc) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            res["n_blobs"] += 1
            name = info.filename.split("/", 1)[1] if "/" in info.filename else info.filename
            if not is_text(name):
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
            lines = None
            for tok, found in token_hits(text, tokens).items():
                if lines is None:
                    lines = text.splitlines()
                snippet = [lines[i - 1][:300] for i in found[:3]]
                res["hits"].setdefault(tok, []).append({"file": name, "lines": found[:20],
                                                        "snippet": snippet})
    return res


def eba_check_zip(tokens, data_dir, getj=get_json):
    """Primary route: one zip of the HEAD commit from codeload (no API rate limit, complete)."""
    meta = getj("https://api.github.com/repos/%s/commits?per_page=1" % EBA_REPO)
    sha = meta[0]["sha"]
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "eba-%s.zip" % sha)
    if not os.path.exists(path):
        tmp = path + ".part"
        with fetch("https://codeload.github.com/%s/zip/%s" % (EBA_REPO, sha), timeout=1800) as r, \
                open(tmp, "wb") as fh:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
        os.replace(tmp, path)
    res = scan_zip(path, tokens)
    res.update({"sha": sha, "route": "zip", "zip_bytes": os.path.getsize(path)})
    return res


def eba_check(tokens, getj=get_json, gettext=None, pause=0.1):
    """Fallback route: git tree listing + raw files."""
    if gettext is None:
        def gettext(url):
            return fetch(url).read().decode("utf-8", "replace")
    meta = getj("https://api.github.com/repos/%s/commits?per_page=1" % EBA_REPO)
    sha = meta[0]["sha"]
    commit = getj("https://api.github.com/repos/%s/git/commits/%s" % (EBA_REPO, sha))
    blobs, calls = list_blobs(commit["tree"]["sha"], getj)
    files = [(p, s) for p, s in blobs if is_text(p)]
    res = {"sha": sha, "route": "tree", "n_blobs": len(blobs), "n_text": len(files), "api_calls": calls,
           "skipped_large": [], "hits": {}, "errors": {}, "n_scanned": 0}
    for p, size in files:
        if size > MAX_BYTES:
            res["skipped_large"].append([p, size])
            continue
        url = "https://raw.githubusercontent.com/%s/%s/%s" % (EBA_REPO, sha, urllib.parse.quote(p))
        text = None
        for attempt in range(3):
            try:
                text = gettext(url)
                break
            except Exception as exc:  # noqa: BLE001 - retry, then record
                res["errors"][p] = repr(exc)
                time.sleep(2.0 * (attempt + 1))
        if text is None:
            continue
        res["errors"].pop(p, None)
        res["n_scanned"] += 1
        lines = None
        for tok, found in token_hits(text, tokens).items():
            if lines is None:
                lines = text.splitlines()
            snippet = [lines[i - 1][:300] for i in found[:3]]
            res["hits"].setdefault(tok, []).append({"file": p, "lines": found[:20], "snippet": snippet})
        if pause:
            time.sleep(pause)
    return res


def verdicts(targets, eba_hits, obaf_hits):
    out = {}
    for label, tic, gid, role in targets:
        files = []
        for tok in (str(tic) if tic else None, gid):
            if tok and tok in eba_hits:
                files.extend(h["file"] for h in eba_hits[tok])
        out[label] = {
            "tic": tic, "gaia": gid, "role": role,
            "in_ijspeert2024_eb": (str(tic) in obaf_hits) if (tic and obaf_hits is not None) else None,
            "in_eba": bool(files),
            "eba_files": sorted(set(files)),
        }
    return out


def grade(v, eba, obaf_ok):
    """Controls and registered labels (prereg findings/2026-11-26-candidate-vet-v2-prereg.md)."""
    e_ok = all(v[c]["in_eba"] for c in EBA_CONTROLS)
    o_ok = obaf_ok and any(v[c]["in_ijspeert2024_eb"] for c in OBAF_CONTROLS)
    complete = bool(eba) and not eba.get("errors") and eba.get("n_scanned", 0) == eba.get("n_text", -1) - len(eba.get("skipped_large", []))
    claims = ["HD 250735", "BD+15 2743", "HD 11239", "HD 125386A", "HD 125386 blend", "TYC 6340-23-1"]
    listed = [c for c in claims if v[c]["in_eba"] or v[c]["in_ijspeert2024_eb"]]
    sb1 = ["TYC 1316-1554-1", "TYC 3384-347-1", "UCAC4 544-021692", "UCAC4 468-115332", "UCAC4 194-101841"]
    return {
        "V0_controls": "CONTROLS_OK" if (e_ok and o_ok) else "CONTROL_FAIL",
        "V0_eba_controls": e_ok, "V0_obaf_controls": o_ok,
        "V1_complete": "SCAN_COMPLETE" if complete else "SCAN_INCOMPLETE",
        "V2_claims": "CLAIMS_UNLISTED" if not listed else "CLAIM_LISTED",
        "V2_listed": listed,
        "V3_sb1_listed": [c for c in sb1 if v[c]["in_eba"]],
        "V4_transit_listed": [c for c in ("TIC 93622019", "TIC 44997521", "TIC 4638108")
                              if v[c]["in_eba"] or v[c]["in_ijspeert2024_eb"]],
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--skip-obaf", action="store_true")
    ap.add_argument("--data-dir", default="data")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"version": VERSION, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "targets": [list(t) for t in TARGETS]}
    tics = {t[1] for t in TARGETS if t[1]}
    obaf_hits = None
    if not a.skip_obaf:
        try:
            resp = fetch(OBAF_EB_URL, timeout=600)
            lines = io.TextIOWrapper(resp, encoding="utf-8", errors="replace", newline="")
            _, hits, n = scan_tic_csv(lines, tics)
            obaf_hits = {str(k): v for k, v in hits.items()}
            out["obaf_eb"] = {"n_rows": n, "hits": obaf_hits}
        except Exception as exc:  # noqa: BLE001
            out["obaf_eb"] = {"error": repr(exc)}
    tok = tokens_for(TARGETS)
    try:
        out["eba"] = eba_check_zip(list(tok), a.data_dir)
    except Exception as exc:  # noqa: BLE001
        zip_err = repr(exc)
        try:
            out["eba"] = eba_check(list(tok))
            out["eba"]["zip_error"] = zip_err
        except Exception as exc2:  # noqa: BLE001
            out["eba"] = {"error": repr(exc2), "zip_error": zip_err}
    eba_hits = out["eba"].get("hits", {}) if "error" not in out["eba"] else {}
    v = verdicts(TARGETS, eba_hits, obaf_hits)
    out["verdict"] = v
    out["grade"] = grade(v, out["eba"] if "error" not in out["eba"] else {}, obaf_hits is not None)
    out["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(a.out_dir, "cand_vet2.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({"grade": out["grade"],
                      "verdict": {k: [x["in_eba"], x["in_ijspeert2024_eb"], x["eba_files"][:5]]
                                  for k, x in v.items()}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
