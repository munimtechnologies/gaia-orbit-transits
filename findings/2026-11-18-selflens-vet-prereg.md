# Pre-registration: vetting the 19 brightenings of gaia-selflens-v1

By MV2 of Munim, Inc. Made with AI agents working in his name. CC BY 4.0.
Written 2026-11-18, **before any vetting data were read** (only the selflens-v1 event
table and its top-event plots had been seen). Code: `selflens_vet.py` 0.1.0 (tests:
`test_selflens_vet.py`). Events: `data/selflens-vet-v1/events.json`. Job:
`gaia-selflens-vet-v1`, which fetches `dipsearch.py` and `vet_event.py` pinned at v0.13.1.

## Events
The 17 events that passed the self-lensing pulse rule (15 stars), plus the two control
events that are not copies of candidates (TIC 272090787 at BTJD 3676.29; TIC 357891418 at
2924.99). Eight candidates are marked `near_edge_list`: their centre is within 1.7 d of
a segment start or end, or just before a gap, in the selflens-v1 segment list.

## Checks (per event, all fluxes inverted so a brightening is positive)
A. every SPOC (≥ 120 s), TESS-SPOC and QLP light curve of the target that covers the
   event: box amplitude and SNR against a local linear baseline (± 1.5 d), SAP flux,
   background, centroids, flagged fraction, and the distance to the nearest gap
   (> 0.5 d) or segment end;
B. shape: mean excess in the first and second half of the box against one baseline;
C. up to 8 nearest other TESS stars of that sector (same box);
D. TESScut 15×15 stamp: 3×3 background-subtracted aperture, the background, and the
   in-minus-out difference-image centroid;
E. positive control: the predicted symmetric pulse injected 3 d from the event.

## Verdict rules (fixed now; `verdict()`)
**REJECTED** if any of:
- EDGE: centre < 1.0 d from a gap or segment end in the measuring product;
- NOT SIGNIFICANT: product box SNR < 5;
- SAP: product SNR ≥ 5 but SAP SNR < 3 and SAP amplitude < ⅓ of the product's;
- NOT REPRODUCED: another product covering ≥ half the box shows SNR < 3;
- BACKGROUND: |background box SNR| ≥ 5;
- NEIGHBOURS: ≥ 30% of ≥ 5 neighbours brighten at > 3σ in the same box;
- FLARE-LIKE: the halves differ by > 3σ and the weaker is < 0.5× the stronger;
- FLAGS: > 50% of in-box cadences flagged;
- OFF-TARGET: difference-image centroid > 1 px from the target with TESScut SNR ≥ 3.

**UNRESOLVED** (no hard reason, but) TESScut SNR < 3, TESScut amplitude not within 3× of
the product's, or nothing measurable. **SURVIVES** otherwise. A survivor is only a
*candidate*: next come SIMBAD/VSX, a repeat-epoch check and the Gaia DR4 orbit.

## Predictions
| # | prediction |
|---|---|
| V1 | at least 15 of the 17 candidate events are REJECTED |
| V2 | every candidate marked near_edge_list is REJECTED |
| V3 | neither independent control event SURVIVES |
| V4 | at most one event SURVIVES |
| V5 | the injected predicted pulse is recovered at SNR ≥ 5 in ≥ 70% of measured events |

V5 checks that the vet could see a real pulse. If V5 fails, rejections for "not
significant" say little.

## Limits stated in advance
The 1.0 d edge rule would also reject a real pulse near a segment end. That loss is
accepted: TESS cannot tell such a pulse from a ramp. Neighbour light curves come from a
mix of pipelines. QLP background and centroid columns may be missing, and then those
checks are skipped (not failed).
