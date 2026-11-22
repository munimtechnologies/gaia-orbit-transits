# SPDX-License-Identifier: Apache-2.0
"""vpt_epochs 0.1.1 = vpt_epochs 0.1.0 (gaia-orbit-transits commit f868df8e) + one fix.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.

The fix: ESA's bulk Gaia DR3 epoch-photometry files (cdn.gea.esac.esa.int/Gaia/gdr3/Photometry/
epoch_photometry/EpochPhotometry_<lo>-<hi>.csv.gz, 3,386 files) are named by HEALPix level-8
index ranges (0 to 786,431). A Gaia source_id holds the level-12 index in its bits above 35, so
the level-8 index is source_id >> 43 (= source_id // (2**35 * 4**4)). Version 0.1.0 used
source_id >> 35 (the level-12 index), which matches no file, so its CDN fallback found nothing
(job gaia-vpt-epochs-v1, 22 Nov 2026: ESA DataLink answered 503 and the CDN gave 0 of 214).

Nothing else changes: every pre-registered constant, label, test and output of 0.1.0 is used
unchanged by importing the pinned module. Amendment: findings/2026-11-22-vpt-epochs-amendment-1.md.
"""
import sys

import vpt_epochs as ve

VERSION = "0.1.1"
HEALPIX8_SHIFT = 43


def healpix8(sid):
    """HEALPix level-8 (nested) index of a Gaia source_id."""
    return int(sid) >> HEALPIX8_SHIFT


def apply():
    ve.VERSION = VERSION
    ve.healpix8 = healpix8
    return ve


apply()

if __name__ == "__main__":
    sys.exit(ve.main())
