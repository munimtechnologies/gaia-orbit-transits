# SPDX-License-Identifier: Apache-2.0
"""fetch_deps for sb2-phase-grade (MV2, Munim, Inc.; made with AI agents; Apache-2.0).

Downloads, into the current folder:
  sb2_ffiscan.py      - the frozen 0.1.0 code at tag v0.57.0 (pre-registered 24 Nov 2026)
  v1_stars.jsonl      - the per-star records of job sb2-ffiscan-v1 (committed 27 Nov 2026)
  orbits.csv          - Gaia DR3 nss_two_body_orbit rows for every source_id in v1_stars.jsonl,
                        from the AIP Potsdam TAP mirror by HTTP GET (the ESA archive is closed until
                        Gaia DR4; v1's POST to AIP returned a VOTABLE instead of CSV)
  fetch_meta.json     - URLs, sha256 of each file, row counts
"""
import csv
import hashlib
import io
import json
import sys
import time
import urllib.parse
import urllib.request

REPO_RAW = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/"
CODE_URL = REPO_RAW + "v0.57.0/sb2_ffiscan.py"
STARS_URL = REPO_RAW + "main/data/sb2-ffiscan-v1/ffiscan_stars.jsonl"
AIP = "https://gaia.aip.de/tap/sync"
COLS = ["source_id", "period", "period_error", "eccentricity", "eccentricity_error", "arg_periastron",
        "arg_periastron_error", "t_periastron", "t_periastron_error", "nss_solution_type"]
UA = "gaia-orbit-transits/sb2_phase_grade (MV2, Munim, Inc.; open research)"
CHUNK = 40


def http(url, tries=4, timeout=180):
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # network hiccup: retry
            last = exc
            print("retry", a + 1, url[:100], repr(exc)[:160], flush=True)
            time.sleep(10 * (a + 1))
    raise RuntimeError("HTTP failed %s: %r" % (url[:100], last))


def orbit_query_url(ids):
    q = ("SELECT " + ", ".join(COLS) + " FROM gaiadr3.nss_two_body_orbit WHERE source_id IN (%s)"
         % ",".join(str(int(i)) for i in ids))
    return AIP + "?" + urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                               "MAXREC": "5000", "QUERY": q})


def parse_orbit_csv(text):
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        sid = str(r.get("source_id", "")).strip().strip('"')
        if sid.isdigit():
            rows.append({k: str(r.get(k, "")).strip().strip('"') for k in COLS})
    return rows


def main():
    meta = {"code_url": CODE_URL, "stars_url": STARS_URL, "orbit_tap": AIP, "files": {}}
    code = http(CODE_URL)
    open("sb2_ffiscan.py", "wb").write(code)
    stars = None
    for a in range(12):  # the v1 records are committed right after the run that filed this job
        try:
            stars = http(STARS_URL, tries=1)
            break
        except RuntimeError as exc:
            print("v1_stars.jsonl not reachable yet, waiting", a + 1, repr(exc)[:120], flush=True)
            time.sleep(120)
    if stars is None:
        raise RuntimeError("could not fetch " + STARS_URL)
    open("v1_stars.jsonl", "wb").write(stars)
    for name, blob in (("sb2_ffiscan.py", code), ("v1_stars.jsonl", stars)):
        meta["files"][name] = {"sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)}
    ids = []
    for line in stars.decode("utf-8").splitlines():
        line = line.strip()
        if line:
            sid = str(json.loads(line).get("source_id", "")).strip()
            if sid.isdigit() and sid not in ids:
                ids.append(sid)
    meta["n_source_ids"] = len(ids)
    rows = []
    for i in range(0, len(ids), CHUNK):
        text = http(orbit_query_url(ids[i:i + CHUNK])).decode("utf-8", "replace")
        got = parse_orbit_csv(text)
        if not got:
            raise RuntimeError("AIP returned no CSV rows for chunk %d: %s" % (i, text[:200]))
        rows.extend(got)
    with open("orbits.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    blob = open("orbits.csv", "rb").read()
    meta["files"]["orbits.csv"] = {"sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob),
                                   "rows": len(rows),
                                   "sources": len(set(r["source_id"] for r in rows))}
    json.dump(meta, open("fetch_meta.json", "w"), indent=1)
    print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
