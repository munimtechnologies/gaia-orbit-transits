# SPDX-License-Identifier: Apache-2.0
"""Download ESA's draft Gaia DR4 data model (pre-release, 2026-06-26) and extract the
parts gaia-orbit-transits needs before release day (2 Dec 2026): the columns of
nss_two_body_orbit (corr_vec / bit_index parameter order, t_periastron reference,
spectroscopic C/H names), gaia_exoplanet_candidates, nss_masses,
vari_planetary_transit and epoch_photometry (time origin).

MV2 of Munim, Inc.; made with AI agents. Apache-2.0.
"""
import argparse
import html
import io
import json
import os
import re
import sys
import urllib.request
import zipfile

URL = ("https://anonftp.cosmos.esa.int/pub/GAIA_PUBLIC_DATA/Gaia_DR4/dr4-prerelease/"
       "gaia-dr4-prerelease-draft-data-model_2026-06-26.zip")
KEYS = ["nss_two_body_orbit", "gaia_exoplanet_candidates", "nss_masses",
        "vari_planetary_transit", "epoch_photometry", "nss_acceleration_astro",
        "rv_combined_orbital", "corr_vec", "bit_index", "t_periastron", "thiele_innes"]


def to_text(raw, name):
    s = raw.decode("utf-8", "replace")
    if name.lower().endswith((".html", ".htm", ".xml", ".xhtml")):
        s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
        s = re.sub(r"(?i)<br\s*/?>|</p>|</tr>|</li>|</h\d>", "\n", s)
        s = re.sub(r"(?s)<[^>]+>", " ", s)
        s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/out")
    ap.add_argument("--data-dir", default="/data")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    zpath = os.path.join(args.data_dir, os.path.basename(URL))
    if not os.path.exists(zpath):
        urllib.request.urlretrieve(URL, zpath)
    z = zipfile.ZipFile(zpath)
    names = z.namelist()
    with open(os.path.join(args.out_dir, "dm_files.txt"), "w", encoding="utf-8") as fh:
        for n in names:
            fh.write(f"{z.getinfo(n).file_size}\t{n}\n")
    rel = os.path.join(args.out_dir, "relevant")
    os.makedirs(rel, exist_ok=True)
    hits = {}
    for n in names:
        if n.endswith("/"):
            continue
        raw = z.read(n)
        low_name = n.lower()
        if low_name.endswith(".pdf"):
            if any(k in low_name for k in KEYS):
                with open(os.path.join(rel, os.path.basename(n)), "wb") as fh:
                    fh.write(raw)
            continue
        try:
            text = to_text(raw, n)
        except Exception:
            continue
        low = text.lower()
        found = [k for k in KEYS if k in low or k in low_name]
        if not found:
            continue
        hits[n] = found
        if any(k in low_name for k in KEYS[:6]) or ("nss_two_body_orbit" in low and "corr_vec" in low):
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", n)[-150:]
            with open(os.path.join(rel, safe + ".txt"), "w", encoding="utf-8") as fh:
                fh.write(text)
    with open(os.path.join(args.out_dir, "dm_hits.json"), "w") as fh:
        json.dump(hits, fh, indent=1)
    # focused excerpts printed to stdout as well
    for n, found in hits.items():
        if "corr_vec" in found and "nss_two_body_orbit" in found:
            text = to_text(z.read(n), n)
            for k in ("corr_vec", "bit_index", "t_periastron", "c_thiele_innes", "h_thiele_innes",
                      "ref_epoch", "nss_solution_type"):
                for m in re.finditer(k, text):
                    print(f"--- {n} :: {k}\n{text[max(0, m.start() - 300): m.start() + 1500]}\n")
                    break
    print("files:", len(names), "hits:", len(hits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
