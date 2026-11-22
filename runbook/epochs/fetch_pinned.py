# SPDX-License-Identifier: Apache-2.0
"""Download vpt_epochs 0.1.0, its tests and its input fetcher at the pinned commit f868df8e
(gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents)."""
import sys
import time
import urllib.request

SHA = "f868df8e101aee2c360d9a7b176c3d2356b462b5"
BASE = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/" + SHA + "/"
FILES = {
    "vpt_epochs.py": "vpt_epochs.py",
    "test_vpt_epochs.py": "test_vpt_epochs.py",
    "fetch_inputs.py": "runbook/epochs/fetch_inputs.py",
}


def main():
    for local, path in FILES.items():
        for attempt in range(5):
            try:
                with urllib.request.urlopen(BASE + path, timeout=60) as r:
                    data = r.read()
                if b"SPDX-License-Identifier: Apache-2.0" not in data[:200]:
                    raise ValueError("unexpected content for " + path)
                with open(local, "wb") as fh:
                    fh.write(data)
                print("fetched", local, len(data), "bytes", flush=True)
                break
            except Exception as exc:
                print("retry", local, attempt + 1, repr(exc)[:200], flush=True)
                time.sleep(10 * (attempt + 1))
        else:
            print("FAILED", local, flush=True)
            return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
