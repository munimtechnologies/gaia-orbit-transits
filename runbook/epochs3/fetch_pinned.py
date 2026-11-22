# SPDX-License-Identifier: Apache-2.0
"""Download vpt_epochs 0.1.0 (commit f868df8e), its tests and input fetcher, and the 0.1.1
patch with its tests (commit 824cbe54), from gaia-orbit-transits (MV2 of Munim, Inc.; made with
AI agents). Used by job gaia-vpt-epochs-box-v1 (amendment 2)."""
import sys
import time
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/"
PINS = [
    ("f868df8e101aee2c360d9a7b176c3d2356b462b5", {
        "vpt_epochs.py": "vpt_epochs.py",
        "test_vpt_epochs.py": "test_vpt_epochs.py",
        "fetch_inputs.py": "runbook/epochs/fetch_inputs.py",
    }),
    ("824cbe54eea37ffcf666ed3d7f7c7fbd1bbd87ba", {
        "patch_vpt_epochs_011.py": "patch_vpt_epochs_011.py",
        "test_patch_vpt_epochs_011.py": "test_patch_vpt_epochs_011.py",
    }),
]


def main():
    for sha, files in PINS:
        for local, path in files.items():
            for attempt in range(5):
                try:
                    with urllib.request.urlopen(RAW + sha + "/" + path, timeout=60) as r:
                        data = r.read()
                    if b"SPDX-License-Identifier: Apache-2.0" not in data[:200]:
                        raise ValueError("unexpected content for " + path)
                    with open(local, "wb") as fh:
                        fh.write(data)
                    print("fetched", local, sha[:8], len(data), "bytes", flush=True)
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
