# Gaia DR4 time origins for eclipse timing (read before release day, 2 December 2026)

MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name; no human expert has checked it.
Text CC BY 4.0, code Apache-2.0. Written 2026-11-28 ~02:00 UTC, before Gaia DR4 is public.

## Why this note exists

Our release-day steps time eclipses from Gaia orbits (conj_map.py, sb2_ebfit MAP_CONJUNCTION, runbook step 12,
the DR4 recovery test findings/2026-11-27-dr4-recovery-prereg.md). Everything so far used Gaia DR3, where
`t_periastron` counts days from J2016.0, i.e. BTJD = 389.0 + t_periastron. Our playbook had an open item:
check whether DR4 keeps that origin. It does not.

## What ESA's draft DR4 data model says

Source: ESA's draft DR4 data model (zip dated 2026-06-26, linked from https://www.cosmos.esa.int/web/gaia/dr4),
full text extracted by our job gaia-dr4dm-v2 (19 Nov 2026), section nss_two_body_orbit. The draft "may change
without notice"; re-check the final datamodel on release day.

1. **t_periastron**: "The epoch at periastron is given relative to gaia_source.ref_epoch, in the range
   [-period/2, +period/2]." DR4's ref_epoch is J2017.5 in TCB (ESA DR4 content page: "The reference epoch for
   Gaia DR4 is J2017.5"; "The time coordinate for Gaia DR4 results is the barycentric coordinate time (TCB)").
   So **BTJD = 936.875 + t_periastron** in DR4. The DR3 origin applied to a DR4 row is off by 547.875 d, which
   is not a whole number of orbits for almost any period, so it would put every predicted eclipse at a random
   phase. Independent support: Kanodia et al. (arXiv:2611.15537, Table 1) report Gaia-4b's time of periastron
   "as an offset from t_ref for Gaia DR4 = 2017.5 = 2457936.875".
2. **Null eccentricity**, per the same column description: for spectroscopic binaries the reference time is the
   maximum of the radial-velocity curve (as in DR3, so component 1 is behind at phase 0.25); **for
   EclipsingBinary and the combined eclipsing/spectroscopic solutions it is the time of primary eclipse**
   (phase 0). Treating a circular EclipsingSpectroSB2 row as a spectroscopic one would put the eclipse a
   quarter orbit off. eclipse_time_primary/secondary are "relative to the same reference epoch as the
   periastron epoch, i.e., gaia_source.ref_epoch".
3. **Epoch photometry time is unchanged**: g_obs_time is "Barycentric JD in TCB - 2 455 197.5", so
   BTJD = t_gaia - 1802.5 as in DR3.
4. **TCB vs TDB**: TESS times are BJD in TDB. TCB - TDB is 19.8 s (0.00023 d) in 2017 (IAU 2006 B3). This is
   far below Gaia's t_periastron errors (0.004 d or more for our stars) but is now available as an option.

## What changed in our code

- **conj_map 0.2.0**: `ref="dr4"` (or `from_row(row, "dr4")`, which reads ref_epoch when present and refuses
  a row whose ref_epoch disagrees with the release), the eclipsing-solution convention via `solution_type`,
  and `tdb=True`. DR3 defaults are unchanged, so every earlier result reproduces; 16 offline tests.
- **sb2_ecl_dr4 0.1.0** (step g8) already tries both J2017.5 and J2016.0 and grades the one whose
  conjunctions pass its time gate; it selects only `SB2%` solutions, whose circular convention is the same in
  DR3 and DR4. The draft confirms that J2017.5 (its reference "a") is the right one. No change needed.
- **Release-day rule**: any script that adds 389.0 or 2191.5 (J2016.0 in Gaia time) to a DR4 t_periastron is
  wrong; use conj_map.from_row(row, "dr4") or 936.875 / 2739.375. Re-check this note against the final
  DR4 datamodel before the first timing result is graded.

## Gaia DR3 orbit of the open candidate TYC 7628-1267-1

Recorded here so the pixel test (findings/2026-11-28-tier2-pixel-prereg.md, job tier2-pixvet-v1, still
queued) can be read against it. Gaia DR3 nss_two_body_orbit (VizieR I/357/tbosb2, fetched 28 Nov 2026):
SB2, P = 7.25085 +- 0.00046 d, e = 0.056 +- 0.012, omega = 283 +- 12 deg, K1 = 75.5 +- 1.3 km/s,
K2 = 79.2 +- 1.4 km/s, 22 epochs for each star. From these alone:
M1 sin^3 i = 1.0361e-7 (1 - e^2)^1.5 (K1 + K2)^2 K2 P = 1.42 solar masses and M2 sin^3 i = 1.35 solar masses,
mass ratio 0.954. If the TESS eclipses belong to this pair, i is near 90 deg and these are close to the true
masses of two F-type stars, consistent with its Gaia colour (BP-RP 0.68) and distance (parallax 1.44 mas).
Gaia DR3 has no epoch photometry for it or for its neighbour (Gaia DR3 5576469817825978240, G 11.46, 31.3
arcsec away, parallax 2.61 mas, so not a physical companion), so Gaia itself cannot say which star dims.
Its TESS fold (P 7.24855 d) is 4.9 sigma below Gaia's period; until the pixel test runs, the candidate stays
unclaimed.
