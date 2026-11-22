# SPDX-License-Identifier: Apache-2.0
"""vpt_epochs 0.1.2 = vpt_epochs 0.1.1 (patch_vpt_epochs_011, commit 824cbe54) + amendment 2.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Amendment: findings/2026-11-22-vpt-epochs-amendment-2.md.

Why: in job gaia-vpt-epochs-v2 (22 Nov 2026) the validity test T1 failed (TIME_BAD, 1 of 13
controls with purity >= 0.5), but every control's real-transit epochs were inside Gaia's
in-transit set (coverage 1.0 for all 13). The cause is the definition of that set: 0.1.0 took
the `num_in_transit` epochs nearest Gaia's transit centres, and Gaia DR3's `num_in_transit` is
about 2.5 times the number of epochs inside Gaia's own `transit_duration` (median share inside:
0.46). Purity was therefore capped near 0.3-0.5 even for correct periods.

The change: Gaia's in-transit set S_g is the set of epochs within transit_duration / 2 of a
transit centre of Gaia's own ephemeris (the branch 0.1.0 already used when num_in_transit was
missing). Done by calling the pinned 0.1.0 analyse_epochs with num_in_transit set to 0 and then
restoring the catalogue value in the record. Nothing else changes: constants, T1/WHY/T3 rules,
the periodogram (T3 does not use S_g) and all outputs are the pinned ones.
"""
import math
import random
import sys

import patch_vpt_epochs_011 as p11

ve = p11.ve

VERSION = "0.1.2"

if not hasattr(ve, "_analyse_epochs_010"):
    ve._analyse_epochs_010 = ve.analyse_epochs
_ORIG = ve._analyse_epochs_010


def analyse_epochs_box(target, t, fl, ephs):
    """0.1.0 analyse_epochs with S_g = epochs inside Gaia's own box (transit_duration / 2)."""
    nin = target.get("num_in_transit")
    tg = dict(target)
    tg["num_in_transit"] = 0
    rec = _ORIG(tg, t, fl, ephs)
    rec["num_in_transit"] = nin
    return rec


def apply():
    p11.apply()
    ve.VERSION = VERSION
    ve.analyse_epochs = analyse_epochs_box
    return ve


apply()


def _synthetic(seed=5):
    rng = random.Random(seed)
    visits = sorted(rng.uniform(0.0, 1000.0) for _ in range(200))
    t = sorted(visits + [v + 0.0739 for v in visits])
    P, T0, dur, dep = 2.0, 10.0, 0.2, 0.01
    intr = [abs(((x - T0) / P - round((x - T0) / P)) * P) <= dur / 2 for x in t]
    fl = [1e5 * (1.0 + rng.gauss(0.0, 0.001) - (dep if i else 0.0)) for i in intr]
    return t, fl, P, T0, dur, intr


def box_check():
    """S_g must equal the epochs inside Gaia's box even when num_in_transit is 3x larger."""
    t, fl, P, T0, dur, intr = _synthetic()
    n_in = sum(intr)
    tgt = {"source_id": "1", "category": "KNOWN_PLANET", "category_detail": "", "tic": "1",
           "G": 12.0, "P_gaia": P, "T0_gaia": T0, "dur_gaia": dur, "num_in_transit": 3 * n_in}
    eph = ve._mk_eph("X b", "archive", P, 1e-6, T0 + ve.GAIA_T_OFFSET, 1e-4, dur * 24)
    rec = ve.analyse_epochs(tgt, t, fl, [eph])
    old = _ORIG(tgt, t, fl, [eph])
    ok = (rec["status"] == "OK" and rec["n_g"] == n_in and rec["purity"] == 1.0
          and rec["why_label"] == "ALIAS" and rec["num_in_transit"] == 3 * n_in
          and old["n_g"] == 3 * n_in and old["purity"] < 0.5)
    ve.log("box check", "OK" if ok else "FAILED", "n_in", n_in, "n_g", rec.get("n_g"),
           "purity", rec.get("purity"), "0.1.0 purity", old.get("purity"))
    return ok


def self_test():
    """The pinned 0.1.0 self-test (with the 0.1.0 analyse_epochs), then the box check."""
    ve.analyse_epochs = _ORIG
    try:
        ok1 = ve.self_test()
    finally:
        ve.analyse_epochs = analyse_epochs_box
    ok2 = box_check()
    return bool(ok1 and ok2)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--self-test" in argv:
        return 0 if self_test() else 3
    return ve.main(argv)


if __name__ == "__main__":
    sys.exit(main())
