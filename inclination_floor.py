# SPDX-License-Identifier: Apache-2.0
"""inclination_floor 0.1.0: how much of the missing-transit shortfall can face-on stars explain?

MV2 of Munim, Inc.; made with AI agents working in his name. Apache-2.0. Standard library only.
Pre-registration: findings/2026-11-19-sb1-robust-amendment-2-inclination.md.

The question
------------
sb1_robust 0.2.0 / sb1_combine 0.1.0 compare the substellar-size transits seen in TESS with
E = sum(p_transit * sensitivity), the number expected if every Gaia DR3 SB1 orbit were real AND
every companion had its minimum mass (inclination isotropic, companion mass = m2 sin i). But an
orbit whose minimum mass is brown-dwarf-like can be a real orbit of a heavier star seen nearly
face-on, and such a star never transits. Given the minimum mass, the chance that the orbit is
near edge-on (true mass close to the minimum mass) depends on how common brown dwarfs are
compared with low-mass stars: the brown-dwarf desert.

This module computes, for each star, c = P(edge-on configuration | mass function, m1,
population) / P_isotropic, i.e. the factor by which a realistic companion population changes the
transit probability, and so E_pop = sum(p_transit * sensitivity * c). If a fraction phi of the
orbits are real (right P and K, companion drawn from the population) and the rest are wrong,
the expected substellar-size transits are phi * E_pop, so phi = (n_sub - fa_sub) / E_pop.

The maths
---------
Gaia gives the mass function fm = m^3 sin^3 i / (m1 + m)^2; sb1_transit solves it with sin i = 1
for the minimum mass mu, so g(mu) = fm with g(m) = m^3 / (m1 + m)^2. A companion of true mass m
then has sin i = (g(mu) / g(m))^(1/3). With isotropic orientations (cos i uniform) and a
companion mass density f(m) per primary, the posterior density of cos i given fm is proportional
to f(m) / (g'(m) sin^3 i). Near edge-on (sin i -> 1, m -> mu) it is f(mu) / g'(mu); integrated
over all cos i it is D = integral over m from mu to m1 of f(m) / (3 g(m) s c) dm, with
s = sin i, c = cos i. So c_star = [f(mu) / g'(mu)] / D. The integral is done in u, m = mu + u^2,
which removes the 1/sqrt singularity at m = mu (midpoint rule, N_STEPS nodes per piece).
For m1 -> infinity this reduces to the textbook f(mu) / integral f(m) mu / (m sqrt(m^2 - mu^2)) dm.

Population (fixed in the pre-registration, a grid)
--------------------------------------------------
- Brown dwarfs: total F_BD per primary at P = 1-13 d between 13 M_Jup and 0.075 M_sun, flat in
  m ("flat") or flat in log m ("logflat").
- Stars: dN/dq proportional to q^gamma (gamma 0 or -1), normalised so that q = 0.1-1 holds F_star,
  and extended with the same law from 0.075 M_sun up to q = 1 (an extension that only adds
  face-on contaminants, i.e. it is generous to "the orbits are real").
- Planets (< 13 M_Jup) are not in the population, so planet-class orbits get c = 0 and are not
  graded.
Because c depends on F_BD / F_star only, the module also solves for r* = F_BD / F_star at which
"every BD-class orbit is real" just reaches the 95 % bound.
"""
import argparse
import csv
import json
import math
import os
import sys

import sb1_combine as sc

VERSION = "0.1.0"
MJUP = 9.5458e-4
M_BD_LO = 13.0 * MJUP      # sb1_transit: planet below 13 M_Jup
M_BD_HI = 0.075            # sb1_transit.BD_MAX
Q_NORM = (0.1, 1.0)
N_STEPS = 100

F_STAR = (0.02, 0.04, 0.08)
F_BD = (0.0005, 0.002, 0.005)
BD_SHAPES = ("flat", "logflat")
GAMMAS = (0.0, -1.0)
CENTRAL = {"f_star": 0.04, "f_bd": 0.002, "bd_shape": "flat", "gamma": 0.0}
FLOOR = {"f_star": 0.08, "f_bd": 0.0005, "bd_shape": "logflat", "gamma": -1.0}
PHI_BAR = 0.5
LIT_RATIO_CENTRAL = CENTRAL["f_bd"] / CENTRAL["f_star"]
LIT_RATIO_FLOOR = FLOOR["f_bd"] / FLOOR["f_star"]


# ------------------------------------------------------------------ population
def g(m, m1):
    return m ** 3 / (m1 + m) ** 2


def gprime(m, m1):
    return m * m * (3.0 * m1 + m) / (m1 + m) ** 3


def bd_norm(shape):
    if shape == "flat":
        return M_BD_HI - M_BD_LO
    if shape == "logflat":
        return math.log(M_BD_HI / M_BD_LO)
    raise ValueError(shape)


def bd_unit_density(m, shape):
    """dN/dm of the brown-dwarf part for F_BD = 1 (zero outside 13 M_Jup - 0.075 M_sun)."""
    if not (M_BD_LO <= m < M_BD_HI):
        return 0.0
    return (1.0 if shape == "flat" else 1.0 / m) / bd_norm(shape)


def q_norm(gamma):
    lo, hi = Q_NORM
    if abs(gamma + 1.0) < 1e-12:
        return math.log(hi / lo)
    return (hi ** (gamma + 1.0) - lo ** (gamma + 1.0)) / (gamma + 1.0)


def star_unit_density(m, m1, gamma):
    """dN/dm of the stellar part for F_star = 1: q^gamma on 0.075 M_sun <= m <= m1."""
    if not (M_BD_HI <= m <= m1):
        return 0.0
    return (m / m1) ** gamma / m1 / q_norm(gamma)


def nodes(mu, m1, n=N_STEPS):
    """Midpoint nodes (m, w) so that D = sum(w * f(m)) for any companion density f."""
    if not (mu > 0 and m1 > mu):
        return []
    gm = g(mu, m1)
    ladder = [M_BD_LO, M_BD_HI, m1]
    b = 2.0 * M_BD_HI
    while b < m1:              # geometric breaks keep each piece well resolved for any m1
        ladder.append(b)
        b *= 2.0
    bounds = sorted(set([mu] + [x for x in ladder if mu < x <= m1]))
    out = []
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        ulo, uhi = math.sqrt(lo - mu), math.sqrt(hi - mu)
        h = (uhi - ulo) / n
        if h <= 0:
            continue
        for k in range(n):
            u = ulo + (k + 0.5) * h
            m = mu + u * u
            gmm = g(m, m1)
            s = (gm / gmm) ** (1.0 / 3.0)
            c2 = 1.0 - s * s
            if c2 <= 0.0:
                continue
            out.append((m, h * 2.0 * u / (3.0 * gmm * s * math.sqrt(c2))))
    return out


def star_terms(mu, m1, n=N_STEPS):
    """Per-star sums, independent of F_BD and F_star.

    Returns {'S': {component: D for unit F}, 'N': {component: edge-on numerator for unit F}}
    with components bd_flat, bd_logflat, star_0, star_-1.
    """
    S = {"bd_" + s: 0.0 for s in BD_SHAPES}
    S.update({"star_%g" % gm_: 0.0 for gm_ in GAMMAS})
    N = dict((k, 0.0) for k in S)
    if not (mu > 0 and m1 > mu):
        return {"S": S, "N": N}
    for m, w in nodes(mu, m1, n):
        for s in BD_SHAPES:
            S["bd_" + s] += w * bd_unit_density(m, s)
        for gm_ in GAMMAS:
            S["star_%g" % gm_] += w * star_unit_density(m, m1, gm_)
    gp = gprime(mu, m1)
    for s in BD_SHAPES:
        N["bd_" + s] = bd_unit_density(mu, s) / gp
    for gm_ in GAMMAS:
        N["star_%g" % gm_] = star_unit_density(mu, m1, gm_) / gp
    return {"S": S, "N": N}


def c_factor(terms, f_star, f_bd, bd_shape, gamma):
    """P(edge-on | fm, population) / P_isotropic for one star."""
    kb, ks = "bd_" + bd_shape, "star_%g" % gamma
    num = f_bd * terms["N"][kb] + f_star * terms["N"][ks]
    den = f_bd * terms["S"][kb] + f_star * terms["S"][ks]
    return (num / den) if den > 0 else 0.0


# ------------------------------------------------------------------ sample
def class_rows(rows, cls):
    return [r for r in rows if sc.in_rate_sample(r) and r.get("m2_class") == cls]


def prepare(rows, n=N_STEPS):
    """[(weight, terms, row)] for rate-sample rows; weight = p_transit * sensitivity."""
    out, skipped = [], 0
    for r in rows:
        if not sc.in_rate_sample(r):
            continue
        w = sc.num(r.get("p_transit"), 0.0) * sc.num(r.get("sensitivity"), 0.0)
        mu, m1 = sc.num(r.get("m2sini")), sc.num(r.get("m1"))
        if not (math.isfinite(mu) and math.isfinite(m1) and 0 < mu < m1):
            skipped += 1       # counted with c = 0 (generous to "real")
            terms = {"S": {}, "N": {}}
        else:
            terms = star_terms(mu, m1, n)
        out.append((w, terms, r))
    return out, skipped


def expected(prepared, scen):
    E = 0.0
    for w, terms, _ in prepared:
        if terms["S"]:
            E += w * c_factor(terms, **scen)
    return E


def phi(n, fa, E):
    return sc.rho(n, fa, E)


def scenarios():
    for fs in F_STAR:
        for fb in F_BD:
            for sh in BD_SHAPES:
                for gm_ in GAMMAS:
                    yield {"f_star": fs, "f_bd": fb, "bd_shape": sh, "gamma": gm_}


def solve_ratio(prepared, target, bd_shape, gamma, f_star=0.04, lo=1e-6, hi=1.0, iters=60):
    """r* = F_BD/F_star at which E_pop equals target (E_pop rises with r for BD-class stars)."""
    def E_of(r):
        return expected(prepared, {"f_star": f_star, "f_bd": r * f_star, "bd_shape": bd_shape, "gamma": gamma})
    if target <= 0:
        return {"r_star": None, "note": "target <= 0"}
    if E_of(lo) >= target:
        return {"r_star": lo, "note": "below search range"}
    if E_of(hi) <= target:
        return {"r_star": hi, "note": "above search range"}
    a, b = math.log(lo), math.log(hi)
    for _ in range(iters):
        mid = 0.5 * (a + b)
        if E_of(math.exp(mid)) < target:
            a = mid
        else:
            b = mid
    return {"r_star": math.exp(0.5 * (a + b)), "note": ""}


def analyse_class(rows, cls, n=N_STEPS, solve=True):
    cr = class_rows(rows, cls)
    base = sc.rate_summary(cr)
    prep, skipped = prepare(cr, n)
    n_sub = base["n_hit_substellar_size"]
    fa = base["n_control_hits_substellar_size"]
    E_iso = base["expected_if_all_real"]
    grid = []
    for scen in scenarios():
        E = expected(prep, scen)
        grid.append(dict(scen, E_pop=E, mean_c=(E / E_iso) if E_iso > 0 else None, phi=phi(n_sub, fa, E)))
    res = {"class": cls, "n_rate_sample": base["n_rate_sample"], "n_sub": n_sub, "fa_sub": fa,
           "E_iso": E_iso, "rho_iso": base["rho_substellar_size"], "skipped_no_mass": skipped,
           "grid": grid}
    for name, scen in (("central", CENTRAL), ("floor", FLOOR)):
        E = expected(prep, scen)
        res[name] = dict(scen, E_pop=E, mean_c=(E / E_iso) if E_iso > 0 else None, phi=phi(n_sub, fa, E))
    if solve:
        lo_hi = sc.garwood(int(n_sub))
        target = lo_hi[1] - fa
        res["r_star"] = {}
        for sh, gm_ in (("flat", 0.0), ("logflat", -1.0)):
            r = solve_ratio(prep, target, sh, gm_)
            r["lit_central"] = LIT_RATIO_CENTRAL
            r["lit_floor"] = LIT_RATIO_FLOOR
            r["drier_than_central_by"] = (LIT_RATIO_CENTRAL / r["r_star"]) if r.get("r_star") else None
            r["drier_than_floor_by"] = (LIT_RATIO_FLOOR / r["r_star"]) if r.get("r_star") else None
            res["r_star"]["%s_gamma%g" % (sh, gm_)] = r
    res["per_star"] = [{"source_id": row.get("source_id"), "tic": row.get("tic"), "m2sini": row.get("m2sini"),
                        "m1": row.get("m1"), "w": w,
                        "c_central": c_factor(t, **CENTRAL) if t["S"] else 0.0,
                        "c_floor": c_factor(t, **FLOOR) if t["S"] else 0.0,
                        "hit_sub": sc.truthy(row.get("star_hit")) and row.get("hit_class") == "SUBSTELLAR_SIZE"}
                       for w, t, row in prep]
    return res


def grade(bd):
    up_floor = bd["floor"]["phi"]["ci95"][1]
    up_central = bd["central"]["phi"]["ci95"][1]
    i1 = (up_floor is not None) and up_floor < PHI_BAR
    i2 = (up_central is not None) and up_central < PHI_BAR
    label = "MOSTLY_SPURIOUS" if i1 else ("SPURIOUS_UNLESS_DRY_DESERT" if i2 else "FACE_ON_SUFFICIENT")
    n_grid_below = sum(1 for s in bd["grid"] if s["phi"]["ci95"][1] is not None and s["phi"]["ci95"][1] < PHI_BAR)
    return {"I1_floor_upper_below_0.5": {"value": up_floor, "pass": i1},
            "I2_central_upper_below_0.5": {"value": up_central, "pass": i2},
            "label": label, "grid_scenarios_upper_below_0.5": "%d of %d" % (n_grid_below, len(bd["grid"]))}


# ------------------------------------------------------------------ report
def _f(x, nd=3):
    return "n/a" if x is None else ("%.*f" % (nd, x))


def report(res):
    p = res["primary"]
    bd = p["BD"]
    L = ["# inclination_floor %s: can face-on stars explain the missing transits?" % VERSION, "",
         "Chunks used: %s. Missing: %s. Duplicate rate-sample rows dropped: %d." % (
             ", ".join(res["chunks_used"]), ", ".join(res["chunks_missing"]) or "none", res["duplicates_dropped"]), "",
         "## Primary grade (BD class, primary sample)", "",
         "Reproduction: n_rate_sample %d, substellar-size hits %d, control false alarms %.2f, E_iso %.1f "
         "(rho_iso %s, 95%% %s-%s)." % (bd["n_rate_sample"], bd["n_sub"], bd["fa_sub"], bd["E_iso"],
                                        _f(bd["rho_iso"]["rho"]), _f(bd["rho_iso"]["ci95"][0]), _f(bd["rho_iso"]["ci95"][1])), ""]
    for name in ("central", "floor"):
        s = bd[name]
        L.append("- **%s** (F_star %.3f, F_BD %.4f, BD %s, gamma %g): mean c %s, E_pop %.1f, phi %s (95%% %s-%s)" % (
            name, s["f_star"], s["f_bd"], s["bd_shape"], s["gamma"], _f(s["mean_c"]), s["E_pop"],
            _f(s["phi"]["rho"]), _f(s["phi"]["ci95"][0]), _f(s["phi"]["ci95"][1])))
    gr = p["grade"]
    L += ["", "- **I1** floor upper bound < 0.5: %s, pass %s" % (_f(gr["I1_floor_upper_below_0.5"]["value"]),
                                                               gr["I1_floor_upper_below_0.5"]["pass"]),
          "- **I2** central upper bound < 0.5: %s, pass %s" % (_f(gr["I2_central_upper_below_0.5"]["value"]),
                                                              gr["I2_central_upper_below_0.5"]["pass"]),
          "- **Label: %s**" % gr["label"],
          "- Grid scenarios with upper bound < 0.5: %s" % gr["grid_scenarios_upper_below_0.5"], "",
          "### r*: the largest F_BD/F_star for which 'every BD-class orbit is real' survives at 95 %", ""]
    for k, v in bd.get("r_star", {}).items():
        L.append("- %s: r* = %s (%s); literature central %.4f -> %s x drier; floor %.4f -> %s x drier" % (
            k, _f(v.get("r_star"), 5), v.get("note") or "ok", v["lit_central"], _f(v.get("drier_than_central_by"), 1),
            v["lit_floor"], _f(v.get("drier_than_floor_by"), 1)))
    L += ["", "### Full grid (BD class)", "",
          "| F_star | F_BD | BD shape | gamma | mean c | E_pop | phi (95%) |", "|---|---|---|---|---|---|---|"]
    for s in bd["grid"]:
        L.append("| %.3f | %.4f | %s | %g | %s | %.1f | %s (%s-%s) |" % (
            s["f_star"], s["f_bd"], s["bd_shape"], s["gamma"], _f(s["mean_c"]), s["E_pop"],
            _f(s["phi"]["rho"]), _f(s["phi"]["ci95"][0]), _f(s["phi"]["ci95"][1])))
    for key, title in (("VLMS", "VLMS class (descriptive)"),):
        v = p.get(key)
        if v:
            L += ["", "## " + title, ""]
            for name in ("central", "floor"):
                s = v[name]
                L.append("- %s: n_sub %d, E_iso %.1f, mean c %s, E_pop %.1f, phi %s (95%% %s-%s)" % (
                    name, v["n_sub"], v["E_iso"], _f(s["mean_c"]), s["E_pop"], _f(s["phi"]["rho"]),
                    _f(s["phi"]["ci95"][0]), _f(s["phi"]["ci95"][1])))
    a1 = res.get("amendment1", {}).get("BD")
    if a1:
        L += ["", "## Secondary: amendment-1 sample (trusted dwarf radii only), BD class", ""]
        for name in ("central", "floor"):
            s = a1[name]
            L.append("- %s: n_sub %d, E_iso %.1f, E_pop %.1f, phi %s (95%% %s-%s)" % (
                name, a1["n_sub"], a1["E_iso"], s["E_pop"], _f(s["phi"]["rho"]),
                _f(s["phi"]["ci95"][0]), _f(s["phi"]["ci95"][1])))
        L.append("- Label on this sample: %s" % res["amendment1"]["grade"]["label"])
    return "\n".join(L) + "\n"


def run(loaded, missing, n=N_STEPS):
    rows, dups = sc.merge([(nm, rr) for nm, rr, _ in loaded])
    res = {"version": VERSION, "chunks_used": [nm for nm, _, _ in loaded], "chunks_missing": missing,
           "duplicates_dropped": dups, "n_steps": n,
           "population": {"F_STAR": F_STAR, "F_BD": F_BD, "BD_SHAPES": BD_SHAPES, "GAMMAS": GAMMAS,
                          "CENTRAL": CENTRAL, "FLOOR": FLOOR, "M_BD_LO": M_BD_LO, "M_BD_HI": M_BD_HI}}
    prim = {"BD": analyse_class(rows, "BD", n), "VLMS": analyse_class(rows, "VLMS", n, solve=False)}
    prim["grade"] = grade(prim["BD"])
    res["primary"] = prim
    kept = [r for r in rows if not (sc.in_rate_sample(r) and sc.radius_flag(r))]
    a1 = {"BD": analyse_class(kept, "BD", n, solve=False)}
    a1["grade"] = grade(a1["BD"])
    res["amendment1"] = a1
    return res


def write_outputs(res, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    per_star = res["primary"]["BD"].pop("per_star")
    for blk in (res["primary"]["VLMS"], res["amendment1"]["BD"]):
        blk.pop("per_star", None)
    with open(os.path.join(out_dir, "incfloor_summary.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    with open(os.path.join(out_dir, "incfloor_report.md"), "w") as fh:
        fh.write(report(res))
    with open(os.path.join(out_dir, "incfloor_bd_stars.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(per_star[0].keys()) if per_star else ["source_id"])
        wr.writeheader()
        for row in per_star:
            wr.writerow(row)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--chunk-dir", action="append", default=[])
    ap.add_argument("--fetch", default="")
    ap.add_argument("--chunks", default="0-7")
    ap.add_argument("--n-steps", type=int, default=N_STEPS)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    loaded, missing = sc.load_chunks(a.chunk_dir, a.fetch or None, sc.parse_chunks(a.chunks) if a.fetch else ())
    if not loaded:
        print("no chunks found; missing:", missing)
        return 3
    res = run(loaded, missing, a.n_steps)
    bd = res["primary"]["BD"]
    brief = {"label": res["primary"]["grade"]["label"], "n_sub": bd["n_sub"], "E_iso": bd["E_iso"],
             "central": {"E_pop": bd["central"]["E_pop"], "phi": bd["central"]["phi"]},
             "floor": {"E_pop": bd["floor"]["E_pop"], "phi": bd["floor"]["phi"]},
             "r_star": {k: v.get("r_star") for k, v in bd.get("r_star", {}).items()},
             "a1_label": res["amendment1"]["grade"]["label"], "missing": missing}
    write_outputs(res, a.out_dir)
    print(json.dumps(brief))
    return 0


if __name__ == "__main__":
    sys.exit(main())
