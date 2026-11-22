# Amendment 1 to the Gaia epoch test (vpt_epochs): the bulk-file lookup fixed

MV2, Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.
Written 2026-11-22 (~19:00 UTC). Pre-registration: `findings/2026-11-21-vpt-epochs-prereg.md`.

## What happened

Job **gaia-vpt-epochs-v1** ran on 22 Nov 2026, 17:35-17:41 UTC. Its unit tests and self-test
passed. ESA's DataLink service (gea.esac.esa.int/data-server) answered HTTP 503 to all six
requests, so the module went to its fallback, ESA's bulk epoch-photometry files on
cdn.gea.esac.esa.int. It read the index (3,386 files) but assigned **none of the 214 stars to a
file**, and it stopped with exit 2 ("epoch photometry unavailable", 0 of 214). No epoch photometry
was downloaded or seen, so the test is still blind. Result files: `data/vpt-epochs-v1/`.

## Why

The bulk files are named by HEALPix **level-8** index ranges (`EpochPhotometry_000000-003111.csv.gz`
… up to 786,431). A Gaia source_id holds the level-12 index in its bits above 35, so the level-8
index is `source_id >> 43`. Version 0.1.0 used `source_id >> 35` (the level-12 index), which is
far above every file's range. Its unit test encoded the same mistake, so it passed.

## The change

`patch_vpt_epochs_011.py` imports `vpt_epochs.py` 0.1.0 unchanged from commit
f868df8e101aee2c360d9a7b176c3d2356b462b5 and replaces only `healpix8` (shift 43) and the version
string (0.1.1). New tests (`test_patch_vpt_epochs_011.py`) check the level-8 index of real Gaia
DR3 source_ids (for example Gaia DR3 5345417757181174144 → 607703), the file lookup, and a full
streamed read of synthetic bulk files (ECSV header, quoted arrays, nulls, early stop). The 0.1.0
tests still run unchanged in their own process.

**Nothing that affects a label changes:** every pre-registered constant, threshold, test (T1,
WHY, T3), prediction and output file is as registered. The bulk-file limits are raised for the
re-run (60 GB, 220 minutes, from 40 GB and 120 minutes), and every star found is cached on the
job's volume, so a later run resumes. Job **gaia-vpt-epochs-v2**.

## Lesson

A test written from the same misunderstanding as the code cannot catch it. Check a lookup
against the real file index before relying on it. Here, one real source_id against the CDN's
own `_MD5SUM.txt` would have shown it.
