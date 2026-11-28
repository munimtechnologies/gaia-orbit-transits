# Pre-registration: which star makes the eclipse of TYC 7628-1267-1? (pix_vet 0.1.0, eba_scan 0.1.0)

MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in his name. Text CC BY 4.0, code Apache-2.0.
Written 2026-11-28 ~00:15 UTC, before job `tier2-pixvet-v1` has run and before any TESS pixel of these stars
was looked at. Code: pix_vet.py, eba_scan.py and their tests (runbook/tier2-pixvet-v1/).

## Why

sb2-ffiscan-t2-v1 (graded in findings/2026-11-28-sb2-ffiscan-t2-v1-graded.md) left three unlisted eclipse
detections. The credible one, TYC 7628-1267-1 (TIC 148478890, G 10.86, Gaia DR3 SB2, P 7.2486 d, 4.1% dip),
has a G = 11.46 neighbour 31 arcsec away (Gaia DR3 5576469817825978240), inside the same TESS pixels, and its
timing test is weak. Before anything is claimed we ask which star dims.

## Method (fixed)

1. eba_scan 0.1.0: every text file of github.com/Snowstar38/eclipses-by-appointment at HEAD (one codeload
   zip) and IJspeert et al. 2024 OBAF_EB.csv (Zenodo 20123193) searched for the TIC and Gaia ids of
   TYC 7628-1267-1, its neighbour, TIC 172260153 and TIC 74104445, as whole digit tokens. Controls that
   must be found: HD 171459, TIC 157469799, TYC 3330-286-1 (catalogue), HIP 27672 and RS Cha (IJspeert).
2. pix_vet 0.1.0, per star, up to 4 TESScut 15x15 cutouts (preferred sectors 61, 87, 88, 34, then others):
   per-frame background (15th percentile) removed; eclipse windows |t - tc| < 0.35 dur, comparison frames
   0.75 dur < |t - tc| < 0.75 dur + 0.5 d on both sides; eclipse time refined per sector within +-0.15 d
   in a 3-px aperture holding both stars; difference image D = mean over events of (out - in).
   Direct image fitted with Gaussian PSFs at the Gaia positions of target and neighbour plus a constant
   (common offset +-1 px and width 0.6-1.7 px on a grid). D fitted with target-only (T) and
   neighbour-only (N) models, weighted by event-to-event pixel scatter; dchi2 = chi2_N - chi2_T summed
   over sectors.
3. Verdict: ON_TARGET if dchi2 >= 9 and target amplitude >= 3 sigma; ON_NEIGHBOUR if dchi2 <= -9 and
   neighbour amplitude >= 3 sigma; NO_SIGNAL if neither amplitude >= 3 sigma; UNRESOLVED otherwise;
   INSUFFICIENT with fewer than 3 events.
4. Controls on the same code: C1 a box eclipse injected on the neighbour at phase 0.23 with a depth that
   gives the observed 4.1% blended dip (expect ON_NEIGHBOUR); C2 the same injected on the target (expect
   ON_TARGET); C3 the catalogued eclipsing binary TIC 270648838 (Prsa et al. 2022) with a fake neighbour at
   the same 31-arcsec offset (expect ON_TARGET).

Ephemeris of TYC 7628-1267-1 from the frozen fold: T0 = 2590.83739 BTJD, P = 7.248555 d, duration 0.290 d.

## Predictions

| ID | Prediction | Probability |
|----|------------|-------------|
| E0 | all catalogue controls found and the scan complete | 85% |
| E1 | TYC 7628-1267-1 and its neighbour named nowhere in the catalogue or IJspeert 2024 | 65% |
| Q1 | C1 = ON_NEIGHBOUR | 85% |
| Q2 | C2 = ON_TARGET | 85% |
| Q3 | C3 = ON_TARGET | 80% |
| M  | TYC 7628-1267-1 = ON_TARGET (if Q1-Q3 hold) | 45% |
| M' | TYC 7628-1267-1 = ON_NEIGHBOUR | 35% |

Why only 45%: the TESS period sits 4.9 sigma from Gaia's and the secondary's phase (0.465) differs from the
0.508 Gaia's e and omega imply, both hints that the eclipsing star may not be the Gaia binary.

## What follows

- ON_TARGET with E1: TYC 7628-1267-1 is reported as a new double-lined eclipsing binary with Gaia masses
  to be derived (sb2_ebfit with conj_map mapping), and goes to VSX when MV2 has an AAVSO login.
- ON_NEIGHBOUR: the Gaia binary is not the eclipser; TYC 7628-1335-1 becomes the candidate, vetted like
  any other star before any claim.
- Any failed control: no verdict on the target; the method is fixed and re-registered first.
TIC 172260153 and TIC 74104445 are not tested here; they stay weak, unclaimed detections.
