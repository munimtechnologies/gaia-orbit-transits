#!/usr/bin/env python3
# fetch_asassn.py 0.1.0 -- download the ASAS-SN Sky Patrol v2 light curves of TYC 6340-23-1
# and of the V = 11.25 star 38 arcsec away (1SWASP J202215.96-220458.7), for tyc_period.py.
# By MV2 of Munim, Inc.; made with AI agents working in his name. License: Apache-2.0.
# Uses the public pyasassn client (pip install skypatrol); no login. Always exits 0 and writes
# fetch_status.json, so a failed download becomes the label ASASSN_UNAVAILABLE, not a crash.
"""Usage: python fetch_asassn.py --out-dir /data/asassn-tyc6340"""
import argparse
import json
import math
import os
import signal
import sys
import traceback

VERSION = "0.1.0"
TARGETS = {"target": (305.561052, -22.073651),
           "neighbour": (305.566500, -22.082972)}   # 20 22 15.96 -22 04 58.7
RADIUS_ARCSEC = 10.0
TIME_LIMIT_S = 1200


class _Timeout(Exception):
    pass


def _alarm(signum, frame):  # noqa: ARG001
    raise _Timeout("time limit")


def sep_arcsec(ra1, de1, ra2, de2):
    r = math.radians
    c = (math.sin(r(de1)) * math.sin(r(de2))
         + math.cos(r(de1)) * math.cos(r(de2)) * math.cos(r(ra1 - ra2)))
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 3600.0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="asassn")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    status = {"version": VERSION}
    st_path = os.path.join(a.out_dir, "fetch_status.json")
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(TIME_LIMIT_S)
    try:
        from pyasassn.client import SkyPatrolClient  # lazy: only in the job image
        client = SkyPatrolClient()
        status["client"] = "ok"
    except Exception as exc:  # noqa: BLE001
        status["client"] = "failed: %s" % str(exc)[:300]
        with open(st_path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=1)
        print(json.dumps(status))
        return 0
    for key, (ra, dec) in TARGETS.items():
        path = os.path.join(a.out_dir, key + ".csv")
        st = {}
        try:
            if os.path.exists(path) and os.path.getsize(path) > 1000:
                st["cached"] = True
            else:
                cat = client.cone_search(ra, dec, radius=RADIUS_ARCSEC, units="arcsec",
                                         catalog="master_list")
                if cat is None or len(cat) == 0:
                    st["status"] = "no source within %.0f arcsec" % RADIUS_ARCSEC
                    status[key] = st
                    continue
                rows = cat.to_dict("records")
                for r in rows:
                    try:
                        r["_sep"] = sep_arcsec(ra, dec, float(r.get("ra_deg")),
                                               float(r.get("dec_deg")))
                    except (TypeError, ValueError):
                        r["_sep"] = 999.0
                rows.sort(key=lambda r: r["_sep"])
                pick = rows[0]
                st["n_sources"] = len(rows)
                st["picked"] = {k: str(v) for k, v in pick.items()}
                sid = int(pick["asas_sn_id"])
                lcs = client.query_list([sid], catalog="master_list", id_col="asas_sn_id",
                                        download=True)
                df = lcs.data
                df.to_csv(path, index=False)
                st["columns"] = [str(c) for c in df.columns]
                st["n_rows"] = int(len(df))
            st["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            st["status"] = "failed"
            st["error"] = str(exc)[:300]
            st["trace"] = traceback.format_exc()[-1500:]
        status[key] = st
        print("[asassn] %s %s" % (key, st.get("status")))
    if hasattr(signal, "SIGALRM"):
        signal.alarm(0)
    with open(st_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=1, default=str)
    print(json.dumps({k: (v.get("status") if isinstance(v, dict) else v)
                      for k, v in status.items()}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except _Timeout:
        print("[asassn] time limit reached")
        sys.exit(0)
