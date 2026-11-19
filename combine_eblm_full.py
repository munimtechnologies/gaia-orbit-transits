# SPDX-License-Identifier: Apache-2.0
"""Build the full-DR3 EBLM input for eblm_infl 0.1.0 (MV2 of Munim, Inc.; made with AI agents).

Pre-registered in findings/2026-11-18-eblm-fit-results.md section 5 ("the full DR3 sample"):
concatenate the 70 rows of gaia-eblm-fit-v1 with the rows of gaia-eblm-rest-a-v1 and
gaia-eblm-rest-b-v1 into one eblm_fit_results.csv, list any system still missing, then run
eblm_infl 0.1.0 unchanged on it.

Usage (job set-up step):
    python combine_eblm_full.py --out eblm_fit_results.csv --report-dir /out

Every input is fetched from GitHub and its SHA-256 and row count are printed. The three
headers must be identical (else exit 4). Rows are deduplicated by source_id (a duplicate
is an error, exit 5: the parts were built to be disjoint). Exit 3 if an input is missing.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import sys
import time
import urllib.request

VERSION = "0.1.0"
REPO_RAW = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/"
INFL_SHA = "87f190f9d49b39e53bd738f2c8995d8cdfe2b194"      # eblm_infl 0.1.0 (v0.11.0)
V1_SHA = "179d6e4805c38f27c0cc8cda22e54c6ebde56467"        # data/eblm-fit-v1 (v0.18.0)
PARTS = [
    ("v1", V1_SHA + "/data/eblm-fit-v1/eblm_fit_results.csv", 70),
    ("rest-a", "main/data/eblm-rest-v1/a/eblm_fit_results.csv", 49),
    ("rest-b", "main/data/eblm-rest-v1/b/eblm_fit_results.csv", 48),
]
N_EBLM_LIKE = 167


def get(url, attempts=4, wait_s=5):
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gaia-orbit-transits"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            print("fetch failed", url, i + 1, exc, flush=True)
            if i + 1 < attempts:
                time.sleep(wait_s)
    return None


def parse(text):
    """Return (header, rows) of a CSV string; rows are lists."""
    rdr = csv.reader(io.StringIO(text))
    header = next(rdr)
    rows = [r for r in rdr if r]
    return header, rows


def combine(parts):
    """parts: list of (name, csv_text). Returns (header, rows, info) or raises ValueError.

    Headers must match exactly; source_id (first column) must be unique across parts."""
    header = None
    out = []
    seen = {}
    info = {"parts": {}, "duplicates": []}
    for name, text in parts:
        h, rows = parse(text)
        if header is None:
            header = h
            if not header or header[0] != "source_id":
                raise ValueError("first column is not source_id in " + name)
        elif h != header:
            raise ValueError("header of %s differs from the first part" % name)
        info["parts"][name] = len(rows)
        for r in rows:
            sid = r[0]
            if sid in seen:
                info["duplicates"].append([sid, seen[sid], name])
                continue
            seen[sid] = name
            out.append(r)
    if info["duplicates"]:
        raise ValueError("duplicate source_id across parts: %s" % info["duplicates"][:5])
    info["n_rows"] = len(out)
    return header, out, info


def to_csv(header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="eblm_fit_results.csv")
    ap.add_argument("--report-dir", default="out")
    ap.add_argument("--rest-attempts", type=int, default=40,
                    help="polls for the rest CSVs (committed right after the filing run)")
    a = ap.parse_args(argv)

    for f in ("eblm_infl.py", "test_eblm_infl.py"):
        if not os.path.exists(f):
            data = get(REPO_RAW + INFL_SHA + "/" + f)
            if data is None:
                return 3
            with open(f, "wb") as fh:
                fh.write(data)
        print("have", f, flush=True)

    texts = []
    hashes = {}
    for name, path, expected in PARTS:
        attempts = 4 if name == "v1" else a.rest_attempts
        data = get(REPO_RAW + path, attempts, 60)
        if data is None:
            print("missing input", name, flush=True)
            return 3
        text = data.decode("utf-8")
        hashes[name] = hashlib.sha256(data).hexdigest()
        n = len(parse(text)[1])
        print(name, "sha256", hashes[name], "rows", n, "expected", expected, flush=True)
        if n != expected:
            print("row count differs from the job outputs; stopping", flush=True)
            return 3
        texts.append((name, text))

    try:
        header, rows, info = combine(texts)
    except ValueError as exc:
        print("combine failed:", exc, flush=True)
        return 5 if "duplicate" in str(exc) else 4

    combined = to_csv(header, rows)
    with open(a.out, "w", encoding="utf-8", newline="") as fh:
        fh.write(combined)
    os.makedirs(a.report_dir, exist_ok=True)
    with open(os.path.join(a.report_dir, "eblm_fit_results_full.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write(combined)
    info.update({
        "version": VERSION,
        "eblm_infl_sha": INFL_SHA,
        "v1_sha": V1_SHA,
        "input_sha256": hashes,
        "combined_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        "n_eblm_like": N_EBLM_LIKE,
        "n_missing": N_EBLM_LIKE - info["n_rows"],
    })
    with open(os.path.join(a.report_dir, "combine_info.json"), "w") as fh:
        json.dump(info, fh, indent=1)
    print(json.dumps(info), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
