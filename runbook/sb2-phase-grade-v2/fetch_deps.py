# SPDX-License-Identifier: Apache-2.0
"""fetch_deps 0.2.0 for sb2-phase-grade (MV2, Munim, Inc.; made with AI agents; Apache-2.0).

Downloads, into the current folder:
  sb2_ffiscan.py      - the frozen 0.1.0 code at tag v0.57.0 (pre-registered 24 Nov 2026)
  v1_stars.jsonl      - the per-star records of job sb2-ffiscan-v1 (committed 27 Nov 2026, v0.83.0)
  orbits.csv          - Gaia DR3 nss_two_body_orbit rows for every source_id in v1_stars.jsonl,
                        from the AIP Potsdam TAP mirror (the ESA archive is closed until Gaia DR4)
  fetch_meta.json     - URLs, sha256 of each file, row counts

0.2.0 (job sb2-phase-grade-v2): the AIP mirror answers with a VOTABLE (TABLEDATA) whether the request
is GET or POST and whether FORMAT=csv or RESPONSEFORMAT=csv is given (checked by hand 27 Nov 2026,
17:35Z), which is what failed job sb2-phase-grade-v1. parse_tap() now reads either CSV or a VOTABLE,
and raises on a TAP ERROR status instead of treating it as zero rows.
"""
import csv
import hashlib
import io
import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

VERSION = "0.2.0"
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


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_votable(text):
    """VOTABLE (TABLEDATA) -> list of dicts keyed by FIELD name. Raises on QUERY_STATUS=ERROR."""
    root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    for el in root.iter():
        if _local(el.tag) == "INFO" and el.get("name") == "QUERY_STATUS" and el.get("value") == "ERROR":
            raise RuntimeError("TAP error: %s" % ((el.text or "").strip() or el.get("value")))
    names = [el.get("name") for el in root.iter() if _local(el.tag) == "FIELD"]
    rows = []
    for tr in root.iter():
        if _local(tr.tag) != "TR":
            continue
        tds = [(td.text or "").strip() for td in tr if _local(td.tag) == "TD"]
        rows.append(dict(zip(names, tds)))
    return rows


def parse_tap(text):
    """CSV or VOTABLE text -> orbit rows (dicts with the COLS keys, all strings)."""
    t = text.lstrip()
    if t.startswith("<"):
        raw = parse_votable(t)
    else:
        raw = list(csv.DictReader(io.StringIO(text)))
    rows = []
    for r in raw:
        sid = str(r.get("source_id", "")).strip().strip('"')
        if sid.isdigit():
            rows.append({k: str(r.get(k, "") or "").strip().strip('"') for k in COLS})
    return rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    stars_url = argv[0] if argv else STARS_URL  # e.g. the per-star jsonl of sb2-ffiscan-t2-v1 later
    meta = {"fetch_deps_version": VERSION, "code_url": CODE_URL, "stars_url": stars_url, "orbit_tap": AIP,
            "files": {}}
    code = http(CODE_URL)
    open("sb2_ffiscan.py", "wb").write(code)
    stars = http(stars_url)
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
        got = parse_tap(text)
        if not got:
            raise RuntimeError("AIP returned no rows for chunk %d: %s" % (i, text[:300]))
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
