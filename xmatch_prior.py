# SPDX-License-Identifier: Apache-2.0
"""xmatch_prior.py -- what is already known about the eclipses that the full Gaia DR3
search (job gaia-orbit-tess-v4) found at Gaia-predicted conjunctions.

gaia-orbit-transits 0.6.2. MV2 of Munim, Inc.; made with AI agents. Results CC BY 4.0.

For every target in the strong-match table it records:
1. Prior work. Whether the star is in the 1,726-orbit selection of Chopard-Vilhem
   (2026, Zenodo 10.5281/zenodo.23342416, "Eclipsing binaries at the conjunctions
   predicted by near-edge-on Gaia DR3 astrometric orbits"), and in which files of that
   deposit its Gaia DR3 source_id or TIC appears (flagged windows, events, literature
   checks, predictions). The newest Zenodo version is used if there is one.
2. The Gaia DR3 inclination of every two-body solution of the star, and |i - 90 deg|
   (the selection above kept |i - 90 deg| < 1 deg).
3. SIMBAD: main identifier, object types, number of references.
4. VizieR within 15 arcsec: AAVSO VSX (B/vsx/vsx) and the TESS EB catalogue
   (Prsa et al. 2022, J/ApJS/258/16), plus the list of every VizieR table with a source
   within 3 arcsec (so other variable-star catalogues can be read off by hand).

It then grades prediction 3 of findings/2026-11-17-prereg.md: "most strong matches
(> 50%) will be stellar eclipsing binaries already listed in VSX, SIMBAD or the Gaia EB
table", and lists the systems found in none of the sources.

Usage: python xmatch_prior.py --targets findings/2026-11-17-dr3-strong-matches.csv \
           --data-dir /data --out-dir /out
"""
import argparse
import csv
import io
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

VERSION = "0.6.2"
ZENODO_RECORD = "23342416"
ZENODO_ZIP = "gaia-dr3-edge-on-orbits-tess-eclipses-v1.0.0.zip"
GAIA_TAP = ["https://gea.esac.esa.int/tap-server/tap/sync",
            "https://gaia.ari.uni-heidelberg.de/tap/sync"]
SIMBAD_TAP = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
UA = {"User-Agent": "gaia-orbit-transits/0.6.2 (MV2 of Munim, Inc.; mv2@munimtech.com)"}

# A Gaia DR3 source_id has 15-19 digits; refuse digit runs that touch a decimal point,
# so the decimals of a float such as 0.18794660757309373 are not read as an id.
GAIA_ID_RE = re.compile(r"(?<![\d.])(\d{15,19})(?![\d.])")
TIC_TEXT_RE = re.compile(r"TIC[ _-]?(\d{4,10})(?!\d)")
ECLIPSING_OTYPES = {"EB*", "EB?", "Al*", "bL*", "WU*", "EP*"}


# ---------------------------------------------------------------- pure helpers
def gaia_ids_in_text(text):
    return set(GAIA_ID_RE.findall(text))


def tic_ids_in_text(text):
    """TIC ids written as 'TIC 123' anywhere, plus every value of a tic/tic_id column."""
    out = {str(int(x)) for x in TIC_TEXT_RE.findall(text)}
    try:
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
    except (StopIteration, csv.Error):
        return out
    idx = [i for i, h in enumerate(header)
           if h.strip().lower().replace(" ", "").replace("_", "") in ("tic", "ticid")]
    if not idx:
        return out
    try:
        for row in reader:
            for i in idx:
                if i < len(row):
                    v = re.sub(r"\D", "", row[i].split(".")[0])
                    if v:
                        out.add(str(int(v)))
    except csv.Error:
        pass
    return out


def rows_with_value(text, value, limit=5, width=60):
    """CSV rows (as dicts) in which some cell equals value; long cells are cut."""
    out = []
    try:
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            cells = [str(v).strip() for v in row.values() if v is not None]
            norm = {c.split(".")[0] if re.fullmatch(r"\d+\.0+", c) else c for c in cells}
            if value in norm or ("TIC " + value) in norm:
                out.append({k: (str(v)[:width] if v is not None else "")
                            for k, v in row.items() if k is not None})
                if len(out) >= limit:
                    break
    except csv.Error:
        pass
    return out


def inclination_deg(A, B, F, G):
    """Inclination from the Thiele-Innes constants (same formula as gaia_orbits.py)."""
    u = 0.5 * (A * A + B * B + F * F + G * G)
    v = A * G - B * F
    disc = 0.5 * math.sqrt(((A - G) ** 2 + (B + F) ** 2) * ((A + G) ** 2 + (B - F) ** 2))
    a2 = u + disc
    if a2 <= 0:
        return float("nan")
    return math.degrees(math.acos(max(-1.0, min(1.0, v / a2))))


def is_eclipsing_vsx(vtype):
    """VSX variability type of an eclipsing binary (EA, EB, EW, E, E/RS, EA+UV, ...).
    ELL (ellipsoidal) is not eclipsing."""
    if not vtype:
        return False
    for part in re.split(r"[+|/:,\s]+", str(vtype).strip()):
        p = part.strip().upper()
        if p.startswith("E") and not p.startswith(("ELL", "EP", "EX")):
            return True
    return False


def is_eclipsing_otypes(otypes):
    return bool(set(otypes) & ECLIPSING_OTYPES)


def grade_p3(rows):
    """Prediction 3: > 50% of strong matches already listed as eclipsing binaries in VSX,
    SIMBAD or the Gaia EB table. Returns (n_known, n, passed)."""
    n = len(rows)
    k = sum(1 for r in rows if r.get("known_eb"))
    return k, n, (n > 0 and k / n > 0.5)


def parse_table(raw):
    """CSV text, or a VOTable (parsed with astropy), into a list of dicts."""
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    if text.lstrip().startswith("<"):
        from astropy.io.votable import parse_single_table
        t = parse_single_table(io.BytesIO(text.encode())).to_table()
        rows = []
        for i in range(len(t)):
            d = {}
            for c in t.colnames:
                s = str(t[c][i])
                d[c] = "" if s == "--" else s
            rows.append(d)
        return rows
    return list(csv.DictReader(io.StringIO(text)))


# ---------------------------------------------------------------- network
def http_get(url, data=None, timeout=180, tries=3):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # network errors are retried, then reported
            last = exc
            time.sleep(5 * (k + 1))
    raise RuntimeError("GET %s failed: %s" % (url, last))


def tap(endpoint, adql, timeout=180):
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                   "QUERY": adql}).encode()
    return parse_table(http_get(endpoint, data=data, timeout=timeout))


# ---------------------------------------------------------------- stages
def load_zenodo(data_dir, log):
    """Download the newest version of the Chopard-Vilhem deposit; return {name: text}."""
    files = {}
    zdir = os.path.join(data_dir, "zenodo-" + ZENODO_RECORD)
    os.makedirs(zdir, exist_ok=True)
    info = {"record": ZENODO_RECORD}
    urls = []
    try:
        rec = json.loads(http_get("https://zenodo.org/api/records/%s/versions/latest"
                                  % ZENODO_RECORD))
        info["latest_id"] = rec.get("id")
        info["latest_version"] = rec.get("metadata", {}).get("version")
        info["latest_doi"] = rec.get("doi")
        for f in rec.get("files", []):
            key = f.get("key", "")
            link = f.get("links", {}).get("self") or f.get("links", {}).get("content")
            if link:
                urls.append((key, link))
    except Exception as exc:
        log("zenodo API failed: %s" % exc)
    if not urls:
        urls = [(ZENODO_ZIP, "https://zenodo.org/records/%s/files/%s?download=1"
                 % (ZENODO_RECORD, ZENODO_ZIP)),
                ("README.md", "https://zenodo.org/records/%s/files/README.md?download=1"
                 % ZENODO_RECORD)]
    info["files"] = [k for k, _ in urls]
    for key, link in urls:
        path = os.path.join(zdir, os.path.basename(key) or "file")
        if not os.path.exists(path):
            try:
                with open(path, "wb") as fh:
                    fh.write(http_get(link, timeout=300))
            except Exception as exc:
                log("download failed %s: %s" % (key, exc))
                continue
        if path.endswith(".zip"):
            try:
                with zipfile.ZipFile(path) as z:
                    for name in z.namelist():
                        if name.lower().endswith((".csv", ".txt", ".md", ".jsonl", ".json",
                                                  ".ics", ".tsv")):
                            files[name] = z.read(name).decode("utf-8", "replace")
            except zipfile.BadZipFile as exc:
                log("bad zip %s: %s" % (key, exc))
        else:
            with open(path, "rb") as fh:
                files[key] = fh.read().decode("utf-8", "replace")
    log("zenodo: %d text files" % len(files))
    return files, info


def prior_lookup(files, sid, tic):
    hits, rows = [], {}
    for name, text in files.items():
        if sid in gaia_ids_in_text(text) or (tic and tic in tic_ids_in_text(text)):
            hits.append(name)
            if name.endswith(".csv"):
                r = rows_with_value(text, sid) or (rows_with_value(text, tic) if tic else [])
                if r:
                    rows[name] = r
    in_sel = any(os.path.basename(h).startswith("track3_") for h in hits)
    return in_sel, sorted(hits), rows


def query_gaia_orbits(sids, log):
    adql = ("SELECT n.source_id, n.solution_type, n.period, n.eccentricity, "
            "n.a_thiele_innes, n.b_thiele_innes, n.f_thiele_innes, n.g_thiele_innes, "
            "g.ra, g.dec, g.phot_g_mean_mag, g.parallax "
            "FROM gaiadr3.nss_two_body_orbit AS n JOIN gaiadr3.gaia_source AS g "
            "ON g.source_id = n.source_id WHERE n.source_id IN (%s)" % ",".join(sids))
    for ep in GAIA_TAP:
        try:
            rows = tap(ep, adql)
            log("gaia: %d solutions from %s" % (len(rows), ep))
            return rows
        except Exception as exc:
            log("gaia TAP failed at %s: %s" % (ep, exc))
    return []


def simbad(sids, tics, log):
    ids = ["Gaia DR3 %s" % s for s in sids] + ["TIC %s" % t for t in tics if t]
    inlist = ",".join("'%s'" % i for i in ids)
    out = {}
    for cols in ("b.main_id, b.otype, b.nbref", "b.main_id, b.otype"):
        try:
            for r in tap(SIMBAD_TAP, "SELECT i.id AS qid, %s FROM ident AS i "
                         "JOIN basic AS b ON b.oid = i.oidref WHERE i.id IN (%s)"
                         % (cols, inlist)):
                out.setdefault(str(r["qid"]), {}).update(
                    {"main_id": str(r["main_id"]), "otype": str(r["otype"]),
                     "nbref": str(r.get("nbref", ""))})
                out[str(r["qid"])].setdefault("otypes", set()).add(str(r["otype"]))
            break
        except Exception as exc:
            log("SIMBAD basic query failed (%s): %s" % (cols, exc))
    try:
        for r in tap(SIMBAD_TAP, "SELECT i.id AS qid, o.otype FROM ident AS i "
                     "JOIN otypes AS o ON o.oidref = i.oidref WHERE i.id IN (%s)" % inlist):
            out.setdefault(str(r["qid"]), {}).setdefault("otypes", set()).add(str(r["otype"]))
    except Exception as exc:
        log("SIMBAD otypes query failed: %s" % exc)
    return out


def vizier(ra, dec, log):
    res = {"vsx": [], "tess_eb": [], "tables_3as": []}
    try:
        import astropy.units as u
        from astropy.coordinates import SkyCoord
        from astroquery.vizier import Vizier
        c = SkyCoord(ra, dec, unit="deg")
        v = Vizier(columns=["*"], row_limit=20, timeout=120)
        tl = v.query_region(c, radius=15 * u.arcsec, catalog=["B/vsx/vsx", "J/ApJS/258/16"])
        for key in tl.keys():
            t = tl[key]
            rows = [{k: str(t[k][i])[:40] for k in t.colnames} for i in range(len(t))]
            (res["vsx"] if key.startswith("B/vsx") else res["tess_eb"]).extend(rows)
        v3 = Vizier(columns=["_RAJ2000"], row_limit=3, timeout=180)
        tl3 = v3.query_region(c, radius=3 * u.arcsec)
        res["tables_3as"] = ["%s: %s" % (k, str(tl3[k].meta.get("description", ""))[:80])
                             for k in tl3.keys()]
    except Exception as exc:
        log("VizieR failed at %.5f %.5f: %s" % (ra, dec, exc))
        res["error"] = str(exc)[:200]
    return res


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default="findings/2026-11-17-dr3-strong-matches.csv")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--no-vizier", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    os.makedirs(a.data_dir, exist_ok=True)
    logs = []

    def log(msg):
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        logs.append(line)

    with open(a.targets, newline="") as fh:
        targets = list(csv.DictReader(fh))
    sids = [t["source_id"].strip() for t in targets]
    log("%d targets" % len(targets))

    files, zinfo = load_zenodo(a.data_dir, log)
    orbits = query_gaia_orbits(sids, log)
    sb = simbad(sids, [t.get("tic", "").strip() for t in targets], log)

    out_rows, detail = [], {}
    for t in targets:
        sid, tic = t["source_id"].strip(), t.get("tic", "").strip()
        in_sel, hits, zrows = prior_lookup(files, sid, tic)
        sols = [o for o in orbits if str(o.get("source_id")).split(".")[0] == sid]
        incs = []
        ra = dec = None
        for o in sols:
            try:
                inc = inclination_deg(float(o["a_thiele_innes"]), float(o["b_thiele_innes"]),
                                      float(o["f_thiele_innes"]), float(o["g_thiele_innes"]))
                incs.append((o.get("solution_type"), float(o["period"]), inc))
            except (TypeError, ValueError, KeyError):
                pass
            try:
                ra, dec = float(o["ra"]), float(o["dec"])
            except (TypeError, ValueError, KeyError):
                pass
        s_g = sb.get("Gaia DR3 %s" % sid) or sb.get("TIC %s" % tic) or {}
        otypes = sorted(s_g.get("otypes", set()))
        vz = vizier(ra, dec, log) if (ra is not None and not a.no_vizier) else {}
        vsx_eb = any(is_eclipsing_vsx(r.get("Type")) for r in vz.get("vsx", []))
        tess_eb = len(vz.get("tess_eb", [])) > 0
        gaia_eb = str(t.get("gaia_eb", "")).strip().lower() == "true"
        simbad_eb = is_eclipsing_otypes(otypes)
        row = {
            "source_id": sid, "tic": tic, "period_d": t.get("period_d"),
            "vet": t.get("vet"),
            "inc_deg": ";".join("%.2f" % i for _, _, i in incs),
            "min_abs_i_minus_90": ("%.2f" % min(abs(i - 90) for _, _, i in incs)) if incs else "",
            "in_chopard_vilhem_selection": in_sel,
            "chopard_vilhem_files": ";".join(os.path.basename(h) for h in hits),
            "simbad_main_id": s_g.get("main_id", ""), "simbad_otypes": "|".join(otypes),
            "simbad_nbref": s_g.get("nbref", ""),
            "vsx": "; ".join("%s %s P=%s" % (r.get("Name"), r.get("Type"), r.get("Period"))
                             for r in vz.get("vsx", [])),
            "tess_eb_cat": tess_eb, "gaia_eb": gaia_eb,
            "known_eb": bool(vsx_eb or simbad_eb or gaia_eb or tess_eb),
        }
        row["new_vs_all_sources"] = not row["known_eb"] and not hits
        out_rows.append(row)
        detail[sid] = {"row": row, "solutions": incs, "zenodo_rows": zrows, "vizier": vz}

    k, n, ok = grade_p3(out_rows)
    vetted = [r for r in out_rows if str(r.get("vet", "")).startswith(("eclipse", "repeats"))]
    kv, nv, okv = grade_p3(vetted)
    summary = {
        "version": VERSION, "zenodo": zinfo, "n_targets": n,
        "P3_known_eb": k, "P3_pass": ok, "P3_note": "pre-registered: > 50% of strong matches",
        "vetted_real_known_eb": kv, "vetted_real_n": nv, "vetted_real_pass": okv,
        "in_chopard_vilhem_selection": sum(1 for r in out_rows if r["in_chopard_vilhem_selection"]),
        "named_in_chopard_vilhem_files": sum(1 for r in out_rows if r["chopard_vilhem_files"]),
        "new_vs_all_sources": [r["source_id"] for r in out_rows if r["new_vs_all_sources"]
                               and str(r.get("vet", "")).startswith(("eclipse", "repeats"))],
        "log": logs,
    }
    with open(os.path.join(a.out_dir, "xmatch.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    with open(os.path.join(a.out_dir, "xmatch_detail.json"), "w") as fh:
        json.dump(detail, fh, indent=1, default=str)
    with open(os.path.join(a.out_dir, "zenodo_file_index.json"), "w") as fh:
        json.dump({k2: {"chars": len(v2), "first_line": v2.splitlines()[0][:300] if v2 else ""}
                   for k2, v2 in files.items()}, fh, indent=1)
    with open(os.path.join(a.out_dir, "xmatch_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=str)
    md = ["# Strong matches x prior work and catalogues (gaia-orbit-transits %s)" % VERSION, "",
          "Made by AI agents working for MV2 of Munim, Inc. CC BY 4.0.", "",
          "P3 (pre-registered): %d of %d known as eclipsing binaries -> %s" %
          (k, n, "PASS" if ok else "FAIL"),
          "Vetted real eclipses only: %d of %d known" % (kv, nv), "",
          "| Gaia DR3 | TIC | P (d) | vet | i (deg) | in C-V selection | C-V files | SIMBAD | VSX | TESS EB | known EB |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in out_rows:
        md.append("| %s | %s | %s | %s | %s | %s | %s | %s %s | %s | %s | %s |" % (
            r["source_id"], r["tic"], r["period_d"], r["vet"], r["inc_deg"],
            r["in_chopard_vilhem_selection"], r["chopard_vilhem_files"][:60],
            r["simbad_main_id"], r["simbad_otypes"], r["vsx"][:60], r["tess_eb_cat"],
            r["known_eb"]))
    with open(os.path.join(a.out_dir, "xmatch_report.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    print(json.dumps({k3: v3 for k3, v3 in summary.items() if k3 != "log"}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
