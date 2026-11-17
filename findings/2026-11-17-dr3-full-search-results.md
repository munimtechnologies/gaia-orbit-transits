# Results: the full Gaia DR3 astrometric-orbit × TESS search (job gaia-orbit-tess-v4)

Graded 2026-11-17 (16:15–17:00 UTC) against `2026-11-17-prereg.md` (with the v2 and v4
amendments), written before any data were seen. gaia-orbit-transits 0.4.1 search code;
this note ships with 0.6.2. MV2 of Munim, Inc.; made with AI agents. CC BY 4.0.

## First, a correction about prior art

Our README said we had found no systematic search that starts from Gaia astrometric
orbits and predicts TESS eclipses. **That was wrong.** On 2026-10-13 Théo Chopard-Vilhem
published exactly such a search: *"Eclipsing binaries at the conjunctions predicted by
near-edge-on Gaia DR3 astrometric orbits"* (Zenodo, doi:10.5281/zenodo.23342416, data
and code for an AAS Research Note). He selected 1,726 Gaia DR3 astrometric orbits with
G < 14 and a best-fit inclination within 1° of 90°, propagated the orbit errors to both
conjunctions, searched SPOC, TESS-SPOC and QLP light curves there, and reports **seven new
eclipsing binaries with periods of 26 to 242 days** (false-alarm probability < 3 × 10⁻⁴
each), two further candidates, artefact vetting calibrated on 256 known eclipses,
injection–recovery limits and forecast eclipse times. Our prior-art search missed it (we
searched arXiv and journals, not Zenodo). The idea of predicting eclipses from Gaia
astrometric orbits, and its first results, are his. We credit it here and in the README.

What this search adds, and only that, is what we claim below: a **14× larger sample**
(24,157 orbits with |cos i| < 0.2, i.e. up to ~11.5° from edge-on, and G < 14.5), a
**pre-registered** calibration test of the predicted eclipse rate, the RV-based labelling
of which conjunction is the transit, and the brown-dwarf focus. Which of our eclipsing
systems are already in his deposit, SIMBAD, VSX or the TESS EB catalogue is being checked
by job **gaia-xmatch-v1** (`xmatch_prior.py`); until it reports, **no system below is
called new.**

## What ran

- 24,157 near-edge-on DR3 orbits (6,677 AstroSpectroSB1, 17,254 Orbital, 226 other),
  93 of substellar class. 600 correlated Monte Carlo draws each.
- 400 targets ranked (substellar first, then eclipse probability); the 200-minute budget
  stopped the TESS stage at target **287**. 277 had TESS light curves.
- 2,505 dips found (SNR ≥ 7, 2–24 h), 123 with window-match Bayes factor (BF) > 10.
- Pre-registered expectation for the processed targets: **74.0 eclipses** inside covered
  windows (91.1 counting both conjunctions); 1,079 predicted windows covered.

## Grades

| # | prediction | result | grade |
|---|---|---|---|
| P1 | ≥ half of Gaia-EB targets with a covered conjunction show BF > 3 | only **one** Gaia-EB target was processed (Gaia DR3 4552787933606840448). Its BF 13.6 dip is an eclipse of its ~2.8-d inner binary falling inside a ±5-d window, not the outer conjunction. | **uninformative** (n = 1) |
| P2 | strong matches within a factor 3 of 74.0, i.e. ≥ 24.7 | **24** targets meet the strong-match rule (BF > 10, SNR > 10, not at a segment edge, no simultaneous event in ≥ 2 other targets) | **fail, narrowly** (24 < 24.7) |
| P3 | > 50% of strong matches already listed in VSX, SIMBAD or the Gaia EB table | needs catalogue look-ups; job gaia-xmatch-v1 grades it with fixed rules | **pending** |
| P4 | 0–2 substellar-class targets with strong matches; any are more likely luminous binaries | **0**. The best substellar-class dip (TIC 438849103, BF 8.4) is a flux jump at a data gap; two others fail SNR or the edge rule. | **pass** |

P2 counts dips, and three of the 24 are not eclipses at the outer conjunction (below), so
the eclipse rate is lower still: about 21 eclipsing systems against 74 expected. Possible
reasons, not yet separated: eclipse probabilities overstated (the rough main-sequence
radii, or Gaia inclination errors larger than quoted), shallow eclipses of faint
companions missed at SNR 10, and windows only partly covered. That is a real limit on
how well DR3 orbits predict eclipses, and it matters for the DR4 forecasts.

## The method works where it can be timed exactly

The clearest test was not pre-registered, so we report it as an observation: several
systems show **eclipses that repeat at Gaia's astrometric period and land where Gaia said**.

- **Gaia DR3 6360777231720947328 (TIC 398402989, G 9.97, P = 58.733 d).** Four 5.3%-deep
  eclipses (BTJD 1666.21, 2371.00, 3134.49, 3839.28), 12, 13 and 12 orbits apart, each
  within 0.03–0.07 d of the predicted transit conjunction (σ = 0.17–0.42 d), and at the
  conjunction that Gaia's RVs name as the transit.
- **Gaia DR3 1342074239441776256 (TIC 18178958, G 7.43, P = 64.018 d, e = 0.53).** Both
  conjunctions eclipse: 3.8% at t2 and 3.4% at t1, 12.83 d apart, each within 0.26 d
  (≈ 2σ) of prediction, seen again 23 orbits later.
- **Gaia DR3 4749907416157959424 (TIC 200743349, P = 26.537 d).** Five ~10% eclipses over
  97 orbits, all within 0.1–0.5 d of prediction. Its Gaia inclination is 91.9°, outside a
  1° edge-on cut.
- **Gaia DR3 1364450812894866688 (TIC 356346086, P = 85.153 d).** Six 1.2–1.5% eclipses at
  both conjunctions over 14 orbits.
- Two systems repeat at a period slightly off Gaia's, measuring the true period: Gaia DR3
  4923979554446754432 (P = 69.98 d against Gaia's 70.07 d) and 5276085474501467648
  (P = 72.08 d against 71.93 d).

Long-period single systems, each a clean eclipse at a predicted conjunction (plots checked):

- **Gaia DR3 5267683998775216256 (TIC 453080115, G 12.16, P = 554.06 d, e = 0.68,
  i = 90.35°).** **Both** eclipses in TESS year 1: ~26% deep at t1 (BTJD 1521.83;
  Gaia-predicted duration 8.6 h, best-fitting box 8 h) and 10% deep at t2 (BTJD 1649.43; a
  1.3-d-long eclipse, against a Gaia-predicted 30.4 h). Gaia's eccentricity and ω
  predicted the 4× difference in eclipse length. A 10% occultation cannot come from a
  0.41 M☉ M dwarf (it gives a few per cent of the light at most), so the companion is
  luminous and the dark-companion mass is a lower limit. If not already known, a
  554-day, doubly eclipsing binary with an astrometric and RV orbit is a mass–radius
  benchmark.
- **Gaia DR3 5840649029966569088 (TIC 342194997, K dwarf at 47 pc, P = 550.75 d,
  e = 0.84).** A 14%, 4.6-h eclipse at BTJD 4091.05 (Sector 100), 2.4 ± 3.3 d from the
  predicted transit conjunction. **Already reported** (Chopard-Vilhem 2026; also listed in
  github.com/alejandrozarco/tess-candidates-2026 with a 16.9% model depth and the next
  eclipse on 2027-08-24). Our search recovers it independently, as a check.
- Gaia DR3 5245186002318544768 (TIC 344750398, P = 193.0 d, 22%, i = 91.6°), Gaia DR3
  6422855314628263168 (TIC 371840569, P = 436.8 d, 15%), Gaia DR3 5225202618992066176
  (TIC 454718065, P = 158.5 d, 2.2%), Gaia DR3 1726670143978052992 (TIC 154872354,
  P = 163.4 d, 7%, spotted primary), Gaia DR3 6373132272083904896 (TIC 404264731,
  P = 94.0 d, 2.4%, 16 h), Gaia DR3 6345896578791113472 (TIC 451599528, G 7.97,
  P = 170.8 d, 0.85%, twice; this star is in the Chopard-Vilhem files) and Gaia DR3
  275228582433787904 (TIC 267694283, P = 74.2 d, 0.6%, twice).

The full list, with times, depths, offsets and our vetting status, is in
`2026-11-17-dr3-strong-matches.csv`.

## Not eclipses

- TIC 219744709 (BF 30): the flux falls to zero for half a day, which is a data artefact.
- TIC 152964265 (BF 22): a single bad cadence.
- TIC 298605890 (the Gaia-EB target): its inner-binary eclipses, as above.
- TIC 438849103 (the only brown-dwarf-class event in the top 60): a jump at a data gap.
- Six strong matches have no plot yet (TIC 85506388, 258349366, 231015406, 235666667,
  142944895, 69911347); two of them show several events within days, which is suspicious.

## What this means for the project

1. The DR3 test of "Gaia orbits predict eclipses" is done twice now: by Chopard-Vilhem
   within 1° of edge-on, and here, pre-registered, out to ~11.5°. Both find real
   long-period eclipses where Gaia predicts them. Our pre-registered rate test fails
   narrowly: DR3 orbits predict about three times more eclipses than TESS shows.
2. **No brown dwarf or planet transits at a Gaia-predicted conjunction in DR3.** The
   substellar goal moves to Gaia DR4 (2 December 2026), with its 5.5-year orbits and
   ~6 million solutions. The rate shortfall above should be used to temper the DR4
   expectations, and is worth understanding before release day.
3. Next job: **gaia-xmatch-v1** grades P3 and says which of the ~21 eclipsing systems
   (especially those beyond 1° from edge-on, or with P > 242 d) are not in the
   Chopard-Vilhem deposit, SIMBAD, VSX or the TESS EB catalogue. Only those can be
   reported as new (to AAVSO VSX), with credit to his earlier method.
