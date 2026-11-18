# SPDX-License-Identifier: Apache-2.0
"""dr4_datamodel.py -- extract the tables we need from ESA's Gaia DR4 draft data model.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Licence: Apache-2.0.

ESA published a draft DR4 data model on 2026-06-26 (a zip). Our DR4 release-day code
(2 December 2026) needs the exact column names of nss_two_body_orbit, the order of its
corr_vec, the epoch-RV DataLink tables, the DR3->DR4 cross-match table, and the columns of
rvs_two_body_orbit, nss_masses, vari_eclipsing_binary, vari_planetary_transit and
vari_compact_companion.

0.2.0: job gaia-dr4dm-v1 showed the zip holds ONE ~2.9 MB PDF (plus a readme), so 0.1.0's
400-block keyword grep hit its cap long before the NSS chapter. 0.2.0 therefore
  * writes the full PDF text in parts of <= PART_CHARS characters (full_text_NN.txt),
  * lists every table in the table of contents (toc_tables.txt),
  * cuts the body section of each table into sections/<table>.txt,
  * greps a focused key list without the 400 cap (grep_context.txt, <= 1.9 MB).
"""
import argparse
import html
import io
import json
import os
import re
import sys
import time
import urllib.request
import zipfile

VERSION = "0.2.0"
URL = ("https://anonftp.cosmos.esa.int/pub/GAIA_PUBLIC_DATA/Gaia_DR4/dr4-prerelease/"
       "gaia-dr4-prerelease-draft-data-model_2026-06-26.zip")
TABLES = ["nss_two_body_orbit", "rvs_two_body_orbit", "nss_masses", "nss_acceleration_astro",
          "nss_multiple_orbits", "vari_eclipsing_binary", "vari_planetary_transit",
          "vari_compact_companion", "vari_microlensing", "gaia_exoplanet_candidates",
          "epoch_astrometry", "epoch_photometry", "rv_combined_orbital_solutions",
          "nss_two_body_orbit_supp", "rvs_epoch_parameters_single", "all_source_rvs",
          "rvs_transit_description", "vari_rad_vel_statistics"]
KEYS = ["corr_vec", "bit_index", "t_periastron", "nss_solution_type", "solution_type",
        "conjunction", "J2017.5", "2457936.875", "dr3_source_id", "dr2_source_id",
        "neighbourhood", "best_neighbour", "gaiadr3", "datalink", "epoch radial velocit",
        "semi_amplitude", "transit_time", "rv_obs_time", "obs_time"]
TEXT_EXT = (".html", ".htm", ".txt", ".xml", ".csv", ".json", ".tex", ".md", ".vot", ".rst")
MAX_COPY = 1_900_000
PART_CHARS = 1_500_000
TOC_RE = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+([a-z][a-z0-9_]+)\s*(?:\.\s*){3,}\s*(\d+)\s*$")
HEAD_RE = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+([a-z][a-z0-9_]+)\s*$")


def strip_html(s):
    """Plain text from an HTML string: drop scripts/styles, turn block tags into newlines."""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<\s*(br|/p|/tr|/li|/h\d|/div|/table)\s*/?>", "\n", s)
    s = re.sub(r"(?i)<\s*/t[dh]\s*>", " | ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def contexts(text, keys, width=3, limit=400):
    """Lines (with `width` lines around) that mention any key (case-insensitive)."""
    lines = text.splitlines()
    out, used = [], set()
    low = [ln.lower() for ln in lines]
    for i, ln in enumerate(low):
        if any(k.lower() in ln for k in keys):
            lo, hi = max(0, i - width), min(len(lines), i + width + 1)
            block = [j for j in range(lo, hi) if j not in used]
            if not block:
                continue
            used.update(block)
            out.append("\n".join(lines[j] for j in block))
            if limit and len(out) >= limit:
                break
    return out


def split_parts(text, size=PART_CHARS):
    """Split text into consecutive parts of at most `size` characters, breaking at a
    newline where possible. Joining the parts gives the text back exactly."""
    parts, i, n = [], 0, len(text)
    while i < n:
        j = min(i + size, n)
        if j < n:
            k = text.rfind("\n", i, j)
            if k > i:
                j = k + 1
        parts.append(text[i:j])
        i = j
    return parts


def toc_tables(text):
    """[(section number, table name, page)] from table-of-contents lines."""
    out, seen = [], set()
    for ln in text.splitlines():
        m = TOC_RE.match(ln)
        if m and m.group(2) not in seen:
            seen.add(m.group(2))
            out.append((m.group(1), m.group(2), int(m.group(3))))
    return out


def sections(text, names, bounds=None):
    """Body text of each named table: from its own heading line ('17.6 rvs_two_body_orbit')
    to the next heading line. TOC lines (with dot leaders) are not headings. Only names in
    `bounds` (default: `names`) count as headings, so a stray line like '3.4 mag' cannot cut
    a section short. If a heading occurs more than once, the longest section is kept."""
    bounds = set(bounds) if bounds else set(names)
    lines = text.splitlines()
    heads = []
    for i, ln in enumerate(lines):
        m = HEAD_RE.match(ln)
        if m and m.group(2) in bounds:
            heads.append((i, m.group(2)))
    out = {}
    for idx, (i, name) in enumerate(heads):
        if name not in names:
            continue
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        body = "\n".join(lines[i:end])
        if len(body) > len(out.get(name, "")):
            out[name] = body
    return out


def wanted(name):
    n = name.lower()
    return any(t in n for t in TABLES)


def to_text(name, data):
    n = name.lower()
    if n.endswith((".html", ".htm")):
        return strip_html(data.decode("utf-8", "replace"))
    if n.endswith(TEXT_EXT):
        return data.decode("utf-8", "replace")
    if n.endswith(".pdf"):
        try:
            import pypdf
            r = pypdf.PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in r.pages)
        except Exception as exc:
            return "PDF TEXT FAILED: %s" % exc
    return None


def safe(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[-150:]


def download(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return r.read()
        except Exception as exc:
            print("download failed", k + 1, exc, flush=True)
            time.sleep(10 * (k + 1))
    return None


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def run(zbytes, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    zf = zipfile.ZipFile(io.BytesIO(zbytes))
    infos = zf.infolist()
    with open(os.path.join(out_dir, "listing.txt"), "w", encoding="utf-8") as fh:
        for zi in infos:
            fh.write("%10d  %s\n" % (zi.file_size, zi.filename))
    grep, picked, nested, parts_written, toc_all, sec_all = [], [], [], [], [], {}
    for zi in infos:
        if zi.is_dir():
            continue
        name = zi.filename
        if name.lower().endswith(".zip"):
            nested.append(name)
        data = zf.read(zi)
        text = to_text(name, data)
        if text is None:
            continue
        stem = safe(os.path.splitext(name)[0])
        for k, part in enumerate(split_parts(text)):
            fn = "full_%s_%02d.txt" % (stem, k)
            _write(os.path.join(out_dir, "full", fn), part)
            parts_written.append(fn)
        if wanted(name):
            picked.append(name)
        toc = toc_tables(text)
        toc_all.extend((name,) + t for t in toc)
        names = set(TABLES) | {t[1] for t in toc}
        for tname, body in sections(text, names, names).items():
            if len(body) > len(sec_all.get(tname, "")):
                sec_all[tname] = body
        for c in contexts(text, KEYS, width=4, limit=0):
            grep.append("=== %s\n%s" % (name, c))
    for tname, body in sec_all.items():
        _write(os.path.join(out_dir, "sections", safe(tname) + ".txt"), body[:MAX_COPY])
    with open(os.path.join(out_dir, "toc_tables.txt"), "w", encoding="utf-8") as fh:
        for row in toc_all:
            fh.write("%s\t%s\t%s\tp%d\n" % row)
    _write(os.path.join(out_dir, "grep_context.txt"), "\n\n".join(grep)[:MAX_COPY])
    summary = {"version": VERSION, "members": len(infos), "picked": picked,
               "nested_zips": nested, "grep_blocks": len(grep),
               "full_text_parts": parts_written, "toc_tables": len(toc_all),
               "sections": sorted(sec_all),
               "wanted_sections_missing": sorted(t for t in TABLES if t not in sec_all)}
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--url", default=URL)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    data = download(a.url)
    if data is None:
        print("could not download", a.url)
        return 2
    print("downloaded", len(data), "bytes", flush=True)
    s = run(data, a.out_dir)
    if s["nested_zips"]:
        zf = zipfile.ZipFile(io.BytesIO(data))
        for k, name in enumerate(s["nested_zips"][:10]):
            sub = os.path.join(a.out_dir, "nested%d" % k)
            try:
                print("nested", name, json.dumps(run(zf.read(name), sub)))
            except Exception as exc:
                print("nested failed", name, exc)
    print(json.dumps(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
