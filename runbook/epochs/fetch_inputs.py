# SPDX-License-Identifier: Apache-2.0
"""Download the step-g DR3 rehearsal tables (pinned by full commit SHA) into inputs/."""
import os
import sys
import time
import urllib.request

BASE = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/"
FILES = {
    "c0_candidates.csv": "9d8db1a9e6c37a931c6ca44a2f11f81901303e09/data/vpt-dr3-v1/c0/vpt_candidates.csv",
    "c0_stars.csv": "9d8db1a9e6c37a931c6ca44a2f11f81901303e09/data/vpt-dr3-v1/c0/vpt_stars.csv",
    "c1_candidates.csv": "08b854f1c9a8240b00eaad209a5a5f00f3b300f8/data/vpt-dr3-v1/c1/vpt_candidates.csv",
    "c1_stars.csv": "08b854f1c9a8240b00eaad209a5a5f00f3b300f8/data/vpt-dr3-v1/c1/vpt_stars.csv",
}


def main(out="inputs"):
    os.makedirs(out, exist_ok=True)
    for name, path in FILES.items():
        for attempt in range(4):
            try:
                with urllib.request.urlopen(BASE + path, timeout=60) as r:
                    data = r.read()
                if not data.startswith(b"source_id"):
                    raise ValueError("unexpected content for %s" % name)
                with open(os.path.join(out, name), "wb") as fh:
                    fh.write(data)
                print("fetched", name, len(data), "bytes", data.count(b"\n"), "lines", flush=True)
                break
            except Exception as exc:
                print("retry", name, attempt + 1, repr(exc)[:200], flush=True)
                time.sleep(10 * (attempt + 1))
        else:
            print("FAILED", name, flush=True)
            return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
