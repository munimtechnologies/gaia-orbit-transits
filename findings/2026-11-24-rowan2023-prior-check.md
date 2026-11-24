# Prior-work check: HD 250735 and CD-28 7251 against Rowan et al. (2023)

MV2, Munim, Inc. Made with AI agents working in his name. CC BY 4.0. Checked 2026-11-24 ~10:40 UTC.

[Rowan et al. (2023), "The Value-Added Catalog of ASAS-SN Eclipsing Binaries III: Masses and Radii of
Gaia Spectroscopic Binaries", MNRAS 523, 2641](https://arxiv.org/abs/2212.02509) is the closest
published work to our screen. They cross-matched all 5,376 Gaia DR3 SB2 orbits with ASAS-SN eclipsing
binaries, inspected ASAS-SN light curves of all 5,376 folded at Gaia's period, and fitted masses and
radii. Our 23 November vetting had checked the ASAS-SN variable-star catalogue (II/366) but not this
paper's own list, so we checked it now.

- The arXiv full text (HTML) does not contain HD 250735, CD-28 7251, TIC 400170926, TIC 189269584,
  Gaia DR3 3450611154067089408 or 5633392634307163776.
- Their public table (https://asas-sn.osu.edu/binaries/mass-radius, CSV export, 61 systems) does not
  contain either Gaia source_id, and has no row within several degrees of either star.
- Their sample keeps only stars fainter than V = 11, where ASAS-SN does not saturate. HD 250735
  (G 9.33) and CD-28 7251 (G 8.86) are brighter than that, which explains the absence.
- Their ~200 extra eclipsing SB2s found by eye are not published as a list; only 11 were used. We
  cannot check that list.
- Eclipses by Appointment (github.com/Snowstar38/eclipses-by-appointment) has had no commit since
  3a46591 (24 Nov 03:52 UTC), which our 24 Nov full read already covered.

**Result:** HD 250735 and CD-28 7251 remain absent from every catalogue, paper and open project we
could reach. 11 of Rowan's 61 systems are in our 183-star tier-1 screen, and their light-curve
inclinations (81-89.8°) confirm that those 11 are edge-on. That led to
`findings/2026-11-24-g5-amendment-2-tier2.md`.
