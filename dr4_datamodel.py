# SPDX-License-Identifier: Apache-2.0
"""dr4_datamodel.py -- extract the tables we need from ESA's Gaia DR4 draft data model.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Licence: Apache-2.0.

ESA published a draft DR4 data model on 2026-06-26 (a zip). Our DR4 release-day code
(2 December 2026) needs the exact column names of nss_two_body_orbit, the order of its
corr_vec, and the columns of rvs_two_body_orbit, nss_masses, vari_eclipsing_binary,
vari_planetary_transit, vari_compact_companion and the exoplanet-candidate table.
This script downloads the zip, lists it, extracts the members for those tables (HTML is
also converted to plain text, PDFs to text with pypdf when available), and writes the
lines around every mention of the key fields to grep_context.txt.
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

URL = ("https://anonftp.cosmos.esa.int/pub/GAIA_PUBLIC_DATA/Gaia_DR4/dr4-prerelease/"
       "gaia-dr4-prerelease-draft-data-model_2026-06-26.zip")
TABLES = ["nss_two_body_orbit", "rvs_two_body_orbit", "nss_masses", "nss_acceleration_astro",
          "nss_multiple_orbits", "vari_eclipsing_binary", "vari_planetary_transit",
          "vari_compact_companion", "vari_microlensing", "gaia_exoplanet_candidates",
          "epoch_astrometry", "epoch_photometry", "rv_combined_orbital_solutions",
          "nss_two_body_orbit_supp"]
KEYS = ["corr_vec", "bit_index", "t_periastron", "inclination", "nss_solution_type",
        "conjunction", "reference epoch", "J2017.5", "2457936.875", "a_thiele_innes",
        "semi_amplitude_primary", "eclipse", "transit"]
TEXT_EXT = (".html", ".htm", ".txt", ".xml", ".csv", ".json", ".tex", ".md", ".vot", ".rst")
MAX_COPY = 2_000_000


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
            if len(out) >= limit:
                break
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


def run(zbytes, out_dir):
    os.makedirs(os.path.join(out_dir, "dm"), exist_ok=True)
    zf = zipfile.ZipFile(io.BytesIO(zbytes))
    infos = zf.infolist()
    with open(os.path.join(out_dir, "listing.txt"), "w", encoding="utf-8") as fh:
        for zi in infos:
            fh.write("%10d  %s\n" % (zi.file_size, zi.filename))
    grep, picked, nested = [], [], []
    for zi in infos:
        if zi.is_dir():
            continue
        name = zi.filename
        if name.lower().endswith(".zip"):
            nested.append(name)
        data = zf.read(zi)
        text = to_text(name, data)
        if wanted(name):
            picked.append(name)
            if len(data) <= MAX_COPY and not name.lower().endswith((".html", ".htm")):
                with open(os.path.join(out_dir, "dm", safe(name)), "wb") as fh:
                    fh.write(data)
            if text is not None:
                with open(os.path.join(out_dir, "dm", safe(name) + ".txt"), "w", encoding="utf-8") as fh:
                    fh.write(text[:MAX_COPY])
        if text is not None:
            for c in contexts(text, KEYS if not wanted(name) else ["corr_vec", "bit_index"]):
                grep.append("=== %s\n%s" % (name, c))
    with open(os.path.join(out_dir, "grep_context.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n\n".join(grep)[:MAX_COPY])
    summary = {"members": len(infos), "picked": picked, "nested_zips": nested,
               "grep_blocks": len(grep)}
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
        return 1
    print("downloaded", len(data), "bytes", flush=True)
    s = run(data, a.out_dir)
    # one level of nested zips (the data model may ship as a zip of zips)
    if s["nested_zips"]:
        zf = zipfile.ZipFile(io.BytesIO(data))
        for k, name in enumerate(s["nested_zips"][:10]):
            sub = os.path.join(a.out_dir, "nested%d" % k)
            os.makedirs(sub, exist_ok=True)
            try:
                print("nested", name, json.dumps(run(zf.read(name), sub)))
            except Exception as exc:
                print("nested failed", name, exc)
    print(json.dumps(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
