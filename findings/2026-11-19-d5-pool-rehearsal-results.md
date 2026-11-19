# D5 release-day code: DR3 dress rehearsal passed (job gaia-d5pool-reh-v2)

2026-11-19, graded about 13:30 UTC. By MV2 of Munim, Inc.; made with AI agents working in his
name. Text and data CC BY 4.0, code Apache-2.0. Rules: `findings/2026-11-19-dr4-sb1-reality-amendment-3.md`
(RH1–RH3). Code: `dr4_d5_rate.py` 0.1.0 with `fetch_d5_deps.py` (release v0.27.0). Outputs:
`data/d5pool-reh-v2/d5_pool_summary.json` (the pool CSV is empty by design, see below).

D5 asks whether Gaia DR4's *new* low-mass SB1 orbits (those with no DR3 orbit) are purer than
DR3's. Its pool builder was run against DR3 (`pool --schema dr3`) on 19 Nov, 12:55–13:02 UTC,
through ESA's live TAP service, so that the release-day path is exercised before the archive
closes on 25 Nov.

| Check | Rule | Found | Pass |
|---|---|---|---|
| RH1 | reproduce sb1_robust 0.2.0's eligible pool, 6,434 rows | 6,434 of 11,937 orbits (1,701 evolved, 3,802 outside the m₂ sin i window) | yes |
| RH2 | every unflagged eligible star is IN_DR3 | 4,366 of 4,366 | yes |
| RH3 | flagged counts add up | 1,132 clamped + 922 giant_cmd + 14 no_distance + 4,366 = 6,434 | yes |

- The D5 pool is **0 by construction** on DR3: every DR3 orbit is, of course, in DR3. Its
  checksum is that of an empty file. On 2 December the same command with `--schema dr4` keeps
  only orbits that DR3 did not have.
- The clamped count, 1,132 of 6,434 (17.6%), is the figure amendment 1 gave for luminous stars on
  the fallback radius. Together with the 922 red-giant-branch stars and 14 without a distance,
  amendment 1's rule removes 2,068 (32%) of the eligible DR3 pool.
- The periastron epoch's unit was read from TAP_SCHEMA (days), as the release-day code requires.

Release-day code still to be rehearsed before ESA's archive closes (25 Nov, 12:00 CET): the
DataLink step of `dr4_sb1_reality.py` (gaia-sb1real-reh-v2), the calibration path after
amendment 2 (gaia-calibdr4-reh-v2), and the full pinned fetch (gaia-fetchrel-check-v2). All are
queued.
