# Amendment for 0.4.1: Gaia archive limits, a scan bug and a test fix

Written 2026-11-17 (about 11:30 UTC), before any of the affected jobs produced data.
gaia-orbit-transits 0.4.1. MV2 of Munim, Inc.; made with AI agents. CC BY 4.0.

None of the pre-registered predictions changes (`2026-11-17-prereg.md` with the v2
amendment, `2026-11-17-watchlist-prereg.md`, `2026-11-17-archival-prereg.md`,
`2026-11-17-forecast-prereg.md`). This note records only why the code changed and
which job names now carry each test.

## 1. The Gaia ESA Archive now limits anonymous queries to 60 s and 50,000 rows

The second full DR3 run (`gaia-orbit-tess-v3`, 10:35 UTC) stopped when the archive
aborted its query with "Maximum execution time (60 s) reached". The archive's October
2026 release changed the quotas. The current quota table
(cosmos.esa.int/web/gaia-users/archive/collaborate) gives anonymous users a 1-minute
time-out for synchronous and asynchronous queries, at most 50,000 rows per query and 50
DataLink sources per request. Registered users get 120 minutes and no row limit. Each
user may run at most 5 jobs at a time (ESA news, 2026-10-14).

0.4.1 splits a large query into source_id ranges. Gaia source_ids are HEALPix level-12
indices times 2^35, so every id is below 3 x 2^61. One sixteenth of that range holds
6,358 orbits with Thiele-Innes constants and G < 14.5. The ESA archive and the ARI
Heidelberg mirror both returned that count within seconds (checked live, 2026-11-17). A
range that times out or comes back with the row cap is split four ways again, up to
four levels deep. Each range goes to the ESA archive first, then to the ARI Heidelberg
Gaia TAP mirror (gaia.ari.uni-heidelberg.de/tap; same `gaiadr3` table and column names;
it writes `corr_vec` as `{...}`, which the parser already accepts), then to astroquery.

**This matters most for DR4 release day (2 December 2026).** DR4's nss_two_body_orbit
has 5.9 million rows, so an anonymous user needs at least 118 range queries for the full
table. The release-day plan uses `--tap-chunks 64` or more, with cuts on magnitude and
inclination made on the server.

## 2. The DataLink structure INDIVIDUAL was renamed DATAMODEL_STANDARD

The same archive release renamed the DataLink structures RAW and INDIVIDUAL to
DATAMODEL_GAIA and DATAMODEL_STANDARD. The archival test's Gaia epoch-photometry
download asked for INDIVIDUAL, so it would have come back empty. 0.4.1 tries
DATAMODEL_STANDARD first, then the old name, then a VOTable answer, then astroquery.

## 3. A bug in archival.scan(), found by its own brute-force test

The publish check of 0.4.0 failed `test_scan_matches_brute_force`: the fast scan gave
SNR 1.837 where the brute-force evaluation of the same cells gave 1.735.

The cause: before the cumulative sums, scan() kept only points within h + D/2 of the
window centre. But its transit-time grid runs to ceil(h/dT)·dT, which can be up to one
grid step (D/4) beyond h, so boxes at the grid edge lost some of their points. Dropping
points with negative residuals raises a box's SNR, so the scan could report an edge box
as stronger than it is. The pre-selection now covers the whole grid.

The bug never ran on real data: gaia-archival-v1 was still queued. That job is replaced
by **gaia-archival-v2**, which runs 0.4.1 with the same command and the same
pre-registered predictions A1-A7.

## 4. A wrong unit test in forecast.py

`test_interval` claimed that no conjunction of t = 1000 + 50k falls in [0, 10]; k = -20
gives t = 0. The function was right and the test was wrong. The test now uses [5, 10],
and its last case uses an interval whose edges do not fall on sample values.
**gaia-forecast-v2** replaces gaia-forecast-v1 with the same runs A and B and the same
predictions F1-F5.

## Job names from this amendment

| job | replaces | why |
|---|---|---|
| gaia-orbit-tess-v4 | v3 (failed: 60-s archive limit) | chunked Gaia query |
| gaia-archival-v2 | v1 (queued, not run) | scan fix, DataLink rename, chunk-aware query |
| gaia-forecast-v2 | v1 (queued, not run) | test fix, chunked Gaia query for run B |

gaia-watchlist-tess-v1 (25 source_ids, one small query) and gaia-dr4-dm-v1 are
unchanged.
