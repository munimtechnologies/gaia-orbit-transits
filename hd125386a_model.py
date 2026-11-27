# SPDX-License-Identifier: Apache-2.0
"""Physical model of the new eclipsing Am binary HD 125386A from its Gaia DR3 SB1 orbit.

MV2 of Munim, Inc. Made with AI agents; not yet checked by a human expert.

Inputs are the Gaia DR3 nss_two_body_orbit row (P, K1, e) and three main-sequence scenarios
for the A star (mass, radius) consistent with its spectral type A2mA5-A6 and its temperature
(Gaia ESP-HS 8860 K, TIC 9669 K). Outputs: mass function, companion mass at i = 90 deg,
separation, minimum inclination for eclipses, central eclipse duration, expected primary
depth, secondary-to-primary depth ratio in V and TESS bands (black bodies), synchronous
rotation speed. Pure Python, no dependencies.

Usage: python hd125386a_model.py [--out model.json]
"""
import json
import math
import sys

__version__ = "0.1.0"

# Gaia DR3 5854558019550047872, nss_two_body_orbit (SB1), fetched 2026-11-27 from gaia.aip.de TAP
P_DAYS = 3.6734168626602712
P_ERR = 0.00016818658
K1 = 48.476813633327446
K1_ERR = 1.1142089
ECC = 0.015763200623999076
ECC_ERR = 0.019864528

R_SUN_KM = 695700.0
AU_RSUN = 215.032
C2 = 0.014388  # second radiation constant, m K

# A-star scenarios (main sequence A2-A5); companion radius taken as 0.65 Rsun for a ~0.65 Msun dwarf
SCENARIOS = [
    {"name": "low", "m1": 1.7, "r1": 1.6},
    {"name": "mid", "m1": 1.9, "r1": 1.8},
    {"name": "high", "m1": 2.1, "r1": 2.0},
]
R2 = 0.65
T1_RANGE = (8860.0, 9670.0)
T2_RANGE = (4100.0, 4700.0)
T1_MID, T2_MID = 9000.0, 4400.0
LAMBDA_V = 550e-9
LAMBDA_TESS = 800e-9


def mass_function(p_days, k_kms, e):
    """f(m) = 1.0361e-7 (1 - e^2)^1.5 K^3 P  [Msun; K in km/s, P in days]."""
    return 1.0361e-7 * (1.0 - e * e) ** 1.5 * k_kms ** 3 * p_days


def companion_mass(fm, m1, sin_i=1.0):
    """Solve m2^3 sin^3 i / (m1 + m2)^2 = fm for m2 by bisection."""
    lo, hi = 0.0, 50.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        g = (mid * sin_i) ** 3 / (m1 + mid) ** 2 - fm
        if g > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def separation_rsun(m_tot, p_days):
    """Kepler's third law in solar units."""
    a_au = (m_tot * (p_days / 365.25) ** 2) ** (1.0 / 3.0)
    return a_au * AU_RSUN


def planck_ratio(t_cool, t_hot, lam):
    """Surface-brightness ratio B(t_cool)/B(t_hot) at wavelength lam (black bodies)."""
    x = C2 / lam
    return (math.exp(x / t_hot) - 1.0) / (math.exp(x / t_cool) - 1.0)


def scenario(s, fm):
    m2 = companion_mass(fm, s["m1"])
    a = separation_rsun(s["m1"] + m2, P_DAYS)
    rsum = (s["r1"] + R2) / a
    i_min = math.degrees(math.acos(rsum))
    sin_imin = math.sin(math.radians(i_min))
    m2_at_imin = companion_mass(fm, s["m1"], sin_imin)
    t_central = P_DAYS / math.pi * math.asin(rsum)
    k2 = (R2 / s["r1"]) ** 2
    depth_mag = -2.5 * math.log10(1.0 - k2)
    v_sync = 2.0 * math.pi * s["r1"] * R_SUN_KM / (P_DAYS * 86400.0)
    return {
        "name": s["name"], "m1": s["m1"], "r1": s["r1"], "r2": R2,
        "m2_i90": round(m2, 4), "m2_at_i_min": round(m2_at_imin, 4),
        "a_rsun": round(a, 3), "rsum_over_a": round(rsum, 4),
        "i_min_deg": round(i_min, 2),
        "t_central_d": round(t_central, 4), "t_central_phase": round(t_central / P_DAYS, 4),
        "k2": round(k2, 4), "primary_depth_mag_central_noLD": round(depth_mag, 4),
        "v_sync_kms": round(v_sync, 2),
    }


def model():
    fm = mass_function(P_DAYS, K1, ECC)
    fm_err = fm * 3.0 * K1_ERR / K1
    rows = [scenario(s, fm) for s in SCENARIOS]
    k2_mid = (R2 / 1.8) ** 2
    j_v = planck_ratio(T2_MID, T1_MID, LAMBDA_V)
    j_t = planck_ratio(T2_MID, T1_MID, LAMBDA_TESS)
    j_t_lo = planck_ratio(T2_RANGE[0], T1_RANGE[1], LAMBDA_TESS)
    j_t_hi = planck_ratio(T2_RANGE[1], T1_RANGE[0], LAMBDA_TESS)
    # ellipsoidal semi-amplitude, order of magnitude: q (R1/a)^3
    mid = rows[1]
    ell = (mid["m2_i90"] / mid["m1"]) * (mid["r1"] / mid["a_rsun"]) ** 3
    return {
        "version": __version__,
        "source_id": 5854558019550047872,
        "inputs": {"P_d": P_DAYS, "P_err": P_ERR, "K1": K1, "K1_err": K1_ERR, "e": ECC,
                   "e_err": ECC_ERR, "r2": R2, "T1_mid": T1_MID, "T2_mid": T2_MID,
                   "T1_range": list(T1_RANGE), "T2_range": list(T2_RANGE)},
        "mass_function": round(fm, 5),
        "mass_function_err": round(fm_err, 5),
        "scenarios": rows,
        "secondary_light_ratio_V_mid": round(j_v * k2_mid, 5),
        "secondary_depth_mag_V_mid": round(2.5 * math.log10(1.0 + j_v * k2_mid), 4),
        "secondary_light_ratio_TESS_mid": round(j_t * k2_mid, 5),
        "sec_to_prim_ratio_TESS_mid": round(j_t, 4),
        "sec_to_prim_ratio_TESS_range": [round(j_t_lo, 4), round(j_t_hi, 4)],
        "ellipsoidal_semi_amplitude_mid": round(ell, 5),
    }


def main(argv):
    out = model()
    text = json.dumps(out, indent=1)
    if "--out" in argv:
        with open(argv[argv.index("--out") + 1], "w") as fh:
            fh.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
