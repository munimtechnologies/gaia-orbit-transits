# SPDX-License-Identifier: Apache-2.0
"""Download sb2_screen 0.1.0 and its tests at the pinned commit 0a8883c9
(gaia-orbit-transits, MV2 of Munim, Inc.; made with AI agents)."""
import sys
import time
import urllib.request

SHA = "0a8883c902143934f2ca9933affb57cc01a851b1"
BASE = "https://raw.githubusercontent.com/munimtechnologies/gaia-orbit-transits/" + SHA + "/"
FILES = {"sb2_screen.py": "sb2_screen.py", "test_sb2_screen.py": "test_sb2_screen.py"}


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
