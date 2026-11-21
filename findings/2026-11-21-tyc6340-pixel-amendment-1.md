# Amendment 1 to the TYC 6340-23-1 pixel pre-registration: the 38″ neighbour is too faint to matter

Written 2026-11-21 (~17:30 UTC) by MV2 of Munim, Inc.; made with AI agents working in his name,
not checked by a human expert. Text CC BY 4.0, code Apache-2.0.
Amends `findings/2026-11-20-tyc6340-pixel-prereg.md`. Code: `tyc_pixel.py` 0.1.1, made from
0.1.0 (commit c16e7a2) by `patch_tyc_pixel_011.py`; tests `test_tyc_pixel_011.py`. Job:
`tyc6340-pixel-v2`.

## What happened

Job `tyc6340-pixel-v1` ran on 2026-11-21 (16:31-16:37 UTC). Its unit tests and self-test passed.
It downloaded the TESScut cutout and the Gaia field (72 stars), then stopped with exit 4,
`38 arcsec neighbour not in Gaia field`, **before any pixel was analysed**. Nobody has looked at
the cutout. The only output is `tyc_pixel_summary.json` with that error.

## Why

The pre-registration named the neighbour as "the Gaia star with G < 13 nearest to (305.566500,
−22.082972) within 5″", because the SuperWASP DR1 archive lists the star there
(1SWASP J202215.96-220458.7) at **V ≈ 11.25**. Gaia DR3 (anonymous TAP query, 2026-11-21) has
exactly one star at that position: **Gaia DR3 6853008487031438080, G = 14.39, RP = 13.75**, 38″
from the target. SuperWASP's ~48″ photometric aperture most likely took in much of the target's
light (G = 10.53, 38″ away), so the archive magnitude was inflated. The rule "G < 13" therefore
matched nothing.

## What the correct magnitude already settles (a simple flux argument, not the pixel test)

A blended star can remove at most its own light. In Gaia RP the 38″ star is 3.78 mag fainter
than the target (flux ratio 0.031). To remove 6.09% of the target's light it would have to lose
**198% of its own light**, which is impossible. So **the 38″ star cannot be the source of the
eclipse.** The worry that drove Part A of the pre-registration came from the wrong magnitude.
(TESS's band is not exactly Gaia RP. A 0.75 mag slack would still need the star to lose all of
its light, which a stellar eclipse does not do.)

Within about 2.5′ of the target, Gaia DR3 has one star bright enough in principle:
**Gaia DR3 6853008452671699328, G = 12.55, RP = 12.08, 94″ away** (about 4.5 TESS pixels). It
would have to lose about 43% of its own light. Every other star with RP < 13.2 in a box of
±4.5′ around the target is more than 230″ (11 pixels) away.

| Gaia DR3 | sep (″) | G | RP | ΔRP | own depth needed for 6.09% |
|---|---|---|---|---|---|
| 6853008487031438080 | 38 | 14.39 | 13.75 | 3.78 | 198% (impossible) |
| 6853008452671699328 | 94 | 12.55 | 12.08 | 2.11 | 43% |
| 6853015771295989504 | ~286 | 12.29 | 11.81 | 1.84 | 36% |

## The amendment (fixed now, before any pixel is analysed)

1. **The neighbour N tested in Part A becomes Gaia DR3 6853008452671699328** (305.549994,
   −22.097618; G 12.55, 94″): the nearest star bright enough to mimic the eclipse. The selection
   rule is unchanged in form (Gaia star with G < 13 nearest to these coordinates within 5″).
2. **Nothing else changes.** Every label (L0-L4, C, B), threshold, control (C1-C4), injection
   amplitude, bootstrap count, seed and prediction of the original pre-registration stands. The
   38″ star stays in the PSF model as a free-flux star (RP 13.75 < 14), as before.
3. **New, reported and not graded:** a blend screen over every Gaia star in the 0.075° field:
   separation, ΔRP, and the fraction of its own light it would have to lose. "Capable" means a
   flux ratio of at least 0.0609; "marginal" means at least half that.
4. If L1 = PIX_ON_NEIGHBOUR, it now means the eclipse is on the 94″ star, and the oversized
   companion is withdrawn exactly as pre-registered.

The 94″ star is easier to separate than the 38″ one (4.5 pixels rather than 1.8), so the test
is now stronger, but it also answers a smaller question: the main blend worry already falls to
the flux argument above. Stars closer than about one TESS pixel (21″) are still not excluded
by this test. Gaia DR3 lists no star with G < 16 within 20″ of the target.

## Predictions (unchanged numbers, restated for N = the 94″ star)

L0 SENSITIVE 80%; L1 ON_TARGET 82%, UNRESOLVED 10%, ON_NEIGHBOUR 3%; L2 ON_TARGET 75%; L3 (if
on target) CONSISTENT 55%, DEEPER 25%, SHALLOWER 20%; L4 SURVIVES 75%; C TIMING_OK 90%;
B LINK_UNIQUE 70%.

## Mistake noted

We carried SuperWASP's catalogue magnitude for a blended neighbour through three
pre-registrations (WASP, period, pixel) without checking it against Gaia. Rule added to our
playbook: check every neighbour's brightness in Gaia before building a test around it.
