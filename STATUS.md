# gaia-orbit-transits: current status (2026-11-18, v0.19.0)

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0, text and
data CC BY 4.0. This page is newer than the long README. Where the two differ, this page
holds.

## Leads
1. **Are Gaia DR3's brown-dwarf-mass spectroscopic orbits real?** First results in
   0.19.0: `findings/2026-11-18-sb1-transit-results.md`.
   - TESS was searched at the Gaia period for 512 random DR3 SB1 orbits (P = 1–13 d,
     G ≤ 13, minimum companion mass 5–105 M_Jup).
   - It found 17 substellar-size hits, against 91.6 expected if every orbit were real and
     7.5 expected false alarms.
   - The reality fraction is **ρ = 0.10 (95% CI 0.03–0.22)**. The pre-registered H1 passes:
     most of these orbits are not both real and truly that light.
   - The hit rule was fooled by outlying data points. The false-alarm check (C2) and the
     timing check (H3) failed, and every new candidate we inspected was outlier-driven.
     The true ρ is therefore lower still, and **no new brown dwarf is claimed**.
   - The only clean transit in the random sample is the known TOI-6218.01.
   - A re-run with an outlier-proof median rule on ~2,600 stars is pre-registered
     (`findings/2026-11-18-sb1-robust-prereg.md`, `sb1_robust.py`, jobs
     gaia-sb1rob-k0…k7-v1, queued). The numpy checks of the median rule are in
     `synthetic_check_sb1_robust.py`.
   - **Gaia DR4 test, pre-registered 14 days before the release**
     (`findings/2026-11-18-dr4-sb1-reality-prereg.md`). It asks *why* so few of these orbits
     transit: are they noise orbits (they should vanish in DR4's 66-month data and epoch
     RVs), or real signals from something other than a brown dwarf (they should persist in
     DR4 and still not transit)?
2. **Do Gaia DR3 inclinations hold up against real eclipses?**
   - Graded in 0.16.0: `findings/2026-11-18-calib-v3-results.md`.
   - Of 162 near-edge-on DR3 orbits that TESS covered, 50 eclipse, where Gaia's published
     errors predict 69 (p = 1.4 × 10⁻⁴).
   - The detected eclipses also scatter in time about 2–2.5 times more than Gaia's
     propagated errors allow. That scatter can push real eclipses outside our ±3σ windows
     and explain much of the deficit, so the "k = 2.3" inflation of the inclination errors
     is **not yet claimed**.
   - A joint fit of both effects is pre-registered
     (`findings/2026-11-18-calib-window-prereg.md`, job gaia-calibw-v1, queued).
3. **Are M dwarfs in 1–2-day orbits inflated?** First results in 0.18.0:
   `findings/2026-11-18-eblm-fit-results.md`.
   - The sample: Gaia DR3 SB1 orbits of stars that Gaia also sees eclipse. Companion masses
     come from Gaia and radii from TESS fits. 70 of 167 systems were fitted.
   - The pre-registered population test came out **CONSISTENT**: median −0.5%,
     95% CI [−5.2%, +3.4%], 26 clean fits, against our rough mass-radius table. There is
     no large inflation at P ≈ 1–2 d.
   - The sharper BHAC15 test (gaia-eblm-infl-v1) and the fits of the other 97 systems
     (gaia-eblm-rest-a/b-v1) are queued.

## Closed with a null result
- **White-dwarf self-lensing at Gaia-predicted conjunctions (DR3)**
  (`findings/2026-11-18-selflens-vet-results.md`).
  - Of 19 brightenings, the pre-registered vet rejected 13, could not measure 4 and
    passed 2. Both survivors fail physical checks (an amplitude ceiling and uniqueness),
    so no candidate is claimed.
  - Four rule changes are written down for the DR4 repeat.

## Corrected
- **CD-48 897 (TIC 200743349) is not a new discovery of ours.** The open working paper
  *Eclipses by Appointment* (github.com/Snowstar38/eclipses-by-appointment) listed it
  first (claim Q031). Its ephemeris and next eclipses are in
  `findings/2026-11-18-ebchar-results.md`.
- TOI-710.01 was already a TFOP false positive. Its eclipses repeat every 72.082 d, a third
  of the TOI period, and match Gaia's SB1 orbit within 2.8σ.

## Refuted or closed
- TIC 207399049: refuted.
- Archival dips for the 25-star watch list: 0 found, where 0.28 were expected.
- Two "stripped companion" candidates are more likely blends or triples.

## Lessons the pipeline now encodes
- **A box depth is a mean, so a few outliers can fake a transit.** Every fold search now
  requires the in-box median to agree with the mean (`sb1_robust.py`). The DR4 versions of
  the other searches still need the same check.
- A query that silently drops columns changes the sample. Jobs now stop instead.

## Prior-art sources we check for every eclipsing system
AAVSO VSX, the TESS EB catalogue (Prša et al. 2022), Gaia DR3 vari_eclipsing_binary,
ExoFOP, SIMBAD, the Chopard-Vilhem Zenodo deposits (10.5281/zenodo.22998328 and
10.5281/zenodo.23342416) and the *Eclipses by Appointment* claim tables.

## Gaia DR4 (2 December 2026)
- ESA's draft DR4 data model (2026-06-26) lists:
  - 5,901,111 rows in nss_two_body_orbit, about 13 times DR3;
  - 638,966 RVS orbits;
  - 2,392,500 eclipsing binaries;
  - 1,007 transit candidates;
  - 6,224 compact-companion candidates.
- DR4 also publishes epoch radial velocities (G_RVS ≤ 14).
- The exact columns and corr_vec order are being extracted (job gaia-dr4dm-v1).
- Pre-registered order:
  1. the DR3 → DR4 orbit-survival test plus the SB1 transit-rate test (0.2.0 rules), on
     DR3's low-mass SB1 orbits and on DR4's new RVS SB1 orbits;
  2. EBLM inflation on DR4 SB1 × eclipsing binaries, with the k-at-bound rule;
  3. the inclination and timing calibration on DR4 orbits;
  4. the RV transit screen;
  5. exoplanet candidates;
  6. self-lensing with the four new rules;
  7. the Kepler self-lensing positive controls.
