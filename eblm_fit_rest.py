# SPDX-License-Identifier: Apache-2.0
"""Finish the eblm_fit 0.1.0 run on the Gaia DR3 SB1 x eclipsing-binary systems that job
gaia-eblm-fit-v1 did not reach (it stopped on its time budget after 70 of 167).

Part of gaia-orbit-transits by MV2 of Munim, Inc.; made with AI agents working in his name.
Apache-2.0.

The fitting code is NOT changed: eblm_fit.py and eblm_screen.py are fetched from the
repository at commit 10b5aeb (release v0.10.0), the same code gaia-eblm-fit-v1 ran. This
wrapper only (1) skips the source_ids already fitted in gaia-eblm-fit-v1 (read from the
published data/eblm-fit-v1/eblm_fit_results.csv), and (2) splits the rest into
interleaved parts (by companion mass order) so two jobs can run side by side.
The combined analysis is pre-registered in findings/2026-11-18-eblm-fit-results.md.
"""
import argparse
import csv
import io
import json
import os
import sys
import time
import traceback
import urllib.request

VERSION = "0.1.0"
SHA = "10b5aeb917c9c52492e7435de93ff1843fcf0999"   # release v0.10.0 (eblm_fit 0.1.0)
BASE = f"https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/{SHA}/"
MODULES = ["eblm_fit.py", "eblm_screen.py"]
DONE_URL = ("https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/main/"
            "data/eblm-fit-v1/eblm_fit_results.csv")


def fetch(url, attempts=4, wait_s=5.0):
    """Bytes at url, retrying; raises the last error."""
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gaia-orbit-transits"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            print("fetch failed", url, i + 1, exc, flush=True)
            if i + 1 < attempts:
                time.sleep(wait_s)
    raise last


def fetch_modules():
    for f in MODULES:
        if os.path.exists(f):
            print("have", f)
            continue
        data = fetch(BASE + f)
        with open(f, "wb") as fh:
            fh.write(data)
        print("fetched", f, len(data))


def done_ids_from_csv(text):
    """Set of source_id strings in an eblm_fit_results.csv text."""
    rows = csv.DictReader(io.StringIO(text))
    return {str(r["source_id"]).strip() for r in rows if r.get("source_id")}


def select(eblm, done, part, n_parts):
    """Systems not yet fitted, in the given (mass-sorted) order, interleaved into n_parts;
    returns part number `part` (0-based)."""
    if not (0 <= part < n_parts):
        raise ValueError("part out of range")
    rest = [c for c in eblm if str(c["source_id"]).strip() not in done]
    return rest[part::n_parts]


def load_done(path_or_url, attempts, wait_s):
    if os.path.exists(path_or_url):
        with open(path_or_url, newline="") as fh:
            text = fh.read()
    else:
        text = fetch(path_or_url, attempts=attempts, wait_s=wait_s).decode("utf-8")
    return done_ids_from_csv(text), text


def run(a):
    import eblm_fit as ef
    es = ef.es
    t_start = time.time()
    os.makedirs(a.out_dir, exist_ok=True)
    os.makedirs(a.data_dir, exist_ok=True)
    plot_dir = os.path.join(a.out_dir, "fit_plots")
    os.makedirs(plot_dir, exist_ok=True)

    done, text = load_done(a.done, a.done_attempts, a.done_wait_s)
    with open(os.path.join(a.out_dir, "done_v1_ids.txt"), "w") as fh:
        fh.write("\n".join(sorted(done)) + "\n")
    print("done in v1:", len(done), flush=True)

    raw = None
    for i in range(a.tap_attempts):
        try:
            raw = es.tap_csv(es.GAIA_TAP, es.sample_adql(a.schema))
            break
        except Exception as exc:  # noqa: BLE001
            print("Gaia TAP failed", i + 1, exc, flush=True)
            time.sleep(a.tap_wait_s)
    if raw is None:
        print("Gaia TAP unavailable; stopping")
        return 2
    rows = [es.classify(r) for r in raw]
    eblm = sorted([r for r in rows if r["cls"] == "eblm_like" and r["fm"] < 0.3], key=lambda r: r["m2"])
    matched = done & {str(c["source_id"]).strip() for c in eblm}
    summary = {"version": ef.VERSION, "wrapper": VERSION, "code_sha": SHA, "schema": a.schema,
               "n_sample": len(rows), "n_eblm_like": len(eblm), "n_done_v1": len(done),
               "n_done_matched": len(matched), "part": a.part, "n_parts": a.n_parts}
    if len(done) == 0 or len(matched) < 0.9 * len(done):
        summary["error"] = "v1 systems not found in the re-queried sample; the sample changed"
        ef.write_outputs(a.out_dir, [], summary)
        print(json.dumps(summary))
        return 3
    todo = select(eblm, done, a.part, a.n_parts)
    summary["n_todo"] = len(todo)
    ef.log("part", a.part, "of", a.n_parts, "todo", len(todo))
    vets = []
    for c in todo:
        if (time.time() - t_start) / 60.0 > a.time_budget_min:
            summary["stopped_by_time_budget"] = True
            break
        ef.log("fit", c["source_id"], f"P={c['period']:.5f} m2sini={c['m2']:.3f}")
        try:
            v = ef.vet_fit(c, a.data_dir, a.max_sectors, plot_dir)
        except Exception:  # noqa: BLE001
            v = {"source_id": c["source_id"], "verdict": "ERROR", "reasons": [traceback.format_exc()[-400:]]}
        v.update(ef.catalogues(c["ra"], c["dec"]))
        ef.log("->", v.get("verdict"), v.get("reasons"))
        vets.append(v)
        if len(vets) % 10 == 0:
            ef.write_outputs(a.out_dir, vets, summary)
    summary["n_vetted"] = len(vets)
    summary["verdicts"] = {}
    for v in vets:
        summary["verdicts"][v.get("verdict", "?")] = summary["verdicts"].get(v.get("verdict", "?"), 0) + 1
    summary["grades_this_part_descriptive"] = ef.grade(vets)
    summary["minutes"] = (time.time() - t_start) / 60.0
    ef.write_outputs(a.out_dir, vets, summary)
    with open(os.path.join(a.out_dir, "eblm_fit_report.md"), "w") as fh:
        fh.write(ef.report(vets, summary))
    print(json.dumps(summary, default=str)[:4000])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch-only", action="store_true")
    ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--n-parts", type=int, default=2)
    ap.add_argument("--done", default=DONE_URL, help="path or URL of gaia-eblm-fit-v1's results CSV")
    ap.add_argument("--done-attempts", type=int, default=40)
    ap.add_argument("--done-wait-s", type=float, default=60.0)
    ap.add_argument("--tap-attempts", type=int, default=6)
    ap.add_argument("--tap-wait-s", type=float, default=300.0)
    ap.add_argument("--schema", default="gaiadr3")
    ap.add_argument("--max-sectors", type=int, default=4)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--time-budget-min", type=float, default=320.0)
    a = ap.parse_args(argv)
    if a.fetch_only:
        fetch_modules()
        return 0
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
