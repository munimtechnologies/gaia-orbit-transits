#!/usr/bin/env python3
# patch_tyc_pixel_011.py -- turns tyc_pixel.py 0.1.0 (commit c16e7a2) into 0.1.1.
# Amendment 1 (findings/2026-11-21-tyc6340-pixel-amendment-1.md), written after job
# tyc6340-pixel-v1 stopped at the Gaia step and BEFORE any TESS pixel was analysed:
#   * the pre-registered "V = 11.25 star 38 arcsec away" is Gaia DR3 6853008487031438080,
#     G = 14.39 / RP = 13.75 (the 11.25 was SuperWASP's blended catalogue magnitude), so the
#     rule "G < 13 within 5 arcsec" found nothing (exit 4);
#   * the neighbour N tested in the pixels becomes the brightest star near the target that
#     could make the eclipse: Gaia DR3 6853008452671699328, G = 12.55, RP = 12.08, 94 arcsec;
#   * a blend screen (reported, not graded) lists every Gaia star in the field with the
#     fraction of its own light it would have to lose to make the 6.09% eclipse.
# Every label, threshold, control and prediction of the original pre-registration is unchanged.
# By MV2 of Munim, Inc.; made with AI agents working in his name. License: Apache-2.0.
"""Usage: python patch_tyc_pixel_011.py [--src tyc_pixel.py] [--out-dir /out]
Exit 0 patched (or already 0.1.1); 5 the source is not the expected 0.1.0 text."""
import argparse
import os
import shutil
import sys

BLEND_FUNC = '''def blend_screen(rows, depth=D_REF):
    """Amendment 1 (reported, not graded): for every Gaia star in the field, the fraction of
    its own RP light it would have to lose to remove `depth` of the target's light.
    capable: flux ratio to the target >= depth; marginal: >= BLEND_MARGIN x depth (slack for
    the TESS band versus Gaia RP). A needed own depth above 1 is impossible in RP."""
    rp_t = None
    for r in rows:
        if str(r.get("source_id")) == GAIA_T:
            try:
                rp_t = float(r["phot_rp_mean_mag"])
            except (TypeError, ValueError, KeyError):
                rp_t = None
    if rp_t is None:
        return {"error": "target not in Gaia rows"}
    stars = []
    for r in rows:
        sid = str(r.get("source_id"))
        if sid == GAIA_T:
            continue
        try:
            rp, ra, de = float(r["phot_rp_mean_mag"]), float(r["ra"]), float(r["dec"])
        except (TypeError, ValueError, KeyError):
            continue
        ratio = 10.0 ** (-0.4 * (rp - rp_t))
        stars.append({"id": sid, "sep_arcsec": round(ang_sep_arcsec(RA_T, DEC_T, ra, de), 2),
                      "rp": rp, "d_rp": round(rp - rp_t, 3), "flux_ratio": ratio,
                      "needed_own_depth": depth / ratio,
                      "capable": ratio >= depth,
                      "marginal": BLEND_MARGIN * depth <= ratio < depth})
    stars.sort(key=lambda s: s["sep_arcsec"])
    cap = [s for s in stars if s["capable"]]
    mar = [s for s in stars if s["marginal"]]
    star38 = [s for s in stars if abs(s["sep_arcsec"] - 38.0) < 3.0]
    return {"rp_target": rp_t, "depth_ref": depth, "dm_max": -2.5 * math.log10(depth),
            "n_stars": len(stars), "n_capable": len(cap), "n_marginal": len(mar),
            "capable": cap, "marginal": mar, "star_38_arcsec": star38[:1],
            "nearest": stars[:8]}


def clean_json(o):'''

REPLACEMENTS = [
    ('VERSION = "0.1.0"', 'VERSION = "0.1.1"'),
    ("# tyc_pixel.py 0.1.0 -- TYC 6340-23-1", "# tyc_pixel.py 0.1.1 -- TYC 6340-23-1"),
    ("(the target or the V = 11.25 star 38 arcsec away),",
     "(the target or the G = 12.55 star 94 arcsec away;\n"
     "#           amendment 1, 2026-11-21: the 38 arcsec star is G = 14.39, too faint to mimic it),"),
    ("RA_N, DEC_N = 305.566500, -22.082972      # the 38 arcsec neighbour (V = 11.25)",
     "RA_N, DEC_N = 305.549994, -22.097618      # amendment 1: Gaia DR3 6853008452671699328, G 12.55, 94\"\n"
     "RA_N38, DEC_N38 = 305.566500, -22.082972  # the 38\" star, Gaia DR3 6853008487031438080, G 14.39\n"
     "BLEND_MARGIN = 0.5                        # blend screen: 'marginal' if flux ratio >= 0.5 x depth"),
    ('raise RuntimeError("38 arcsec neighbour not in Gaia field")',
     'raise RuntimeError("94 arcsec neighbour not in Gaia field")'),
    ("def clean_json(o):", BLEND_FUNC),
    ('    out["target_rp"] = tg["rp"]\n',
     '    out["target_rp"] = tg["rp"]\n    out["blend_screen"] = blend_screen(grows)\n'),
    ('             "- L0 sensitivity: **%s**" % A.get("L0"),',
     '             "- Blend screen (amendment 1, not graded): %s capable, %s marginal" % (\n'
     '                 out.get("blend_screen", {}).get("n_capable"),\n'
     '                 out.get("blend_screen", {}).get("n_marginal")),\n'
     '             "- L0 sensitivity: **%s**" % A.get("L0"),'),
]


class PatchError(Exception):
    pass


def apply(src):
    """Apply every replacement; each old text must occur exactly once."""
    for old, new in REPLACEMENTS:
        n = src.count(old)
        if n != 1:
            raise PatchError("expected 1 occurrence, found %d: %r" % (n, old[:60]))
        src = src.replace(old, new)
    return src


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="tyc_pixel.py")
    ap.add_argument("--out-dir", default="")
    a = ap.parse_args(argv)
    with open(a.src, "r", encoding="utf-8") as f:
        src = f.read()
    if 'VERSION = "0.1.1"' in src:
        print("ALREADY_0.1.1")
        return 0
    try:
        new = apply(src)
    except PatchError as exc:
        print("PATCH_FAILED", exc)
        return 5
    shutil.copyfile(a.src, os.path.splitext(a.src)[0] + "_010.py")
    with open(a.src, "w", encoding="utf-8") as f:
        f.write(new)
    if a.out_dir:
        os.makedirs(a.out_dir, exist_ok=True)
        shutil.copyfile(a.src, os.path.join(a.out_dir, "tyc_pixel.py"))
    print("PATCHED_0.1.1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
