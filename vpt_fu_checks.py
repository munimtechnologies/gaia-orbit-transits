# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
"""vpt_fu_checks 0.1.0 -- exploratory sanity checks for the two Gaia DR3 transit candidates that
survived the pre-registered all-sector TESS follow-up (job gaia-vpt-followup-v1):
TIC 4638108 (Gaia DR3 5431056347037926784) and TIC 44997521 (Gaia DR3 5432318139709900160).

Not pre-registered. Simple textbook formulas, standard library only:
  * Kepler's third law for the orbit size;
  * the central-transit duration T14 = P/pi * asin((R*/a)(1+k));
  * the secondary-eclipse depth of a companion in a monochromatic (800 nm) blackbody approximation
    of the TESS band, for a zero-albedo, no-redistribution dayside (planet case) or a self-luminous
    body of given temperature, plus the reflected-light depth Ag k^2 (R*/a)^2;
  * the eclipse depth a resolved Gaia neighbour would need to fake the dip seen in Gaia's own
    photometry of the target (> 1 means impossible).

By MV2 of Munim, Inc.; made with AI agents. Not checked by a human expert.
"""
import math

__version__ = "0.1.0"

RSUN_PER_AU = 215.032
HC_OVER_K_UM_K = 14387.77  # second radiation constant, micron kelvin
DAYS_PER_YEAR = 365.25


def semi_major_axis_rsun(period_d, mass_msun):
    """Orbit size in solar radii (companion mass neglected)."""
    p_yr = period_d / DAYS_PER_YEAR
    return (mass_msun * p_yr ** 2) ** (1.0 / 3.0) * RSUN_PER_AU


def t14_central_hours(period_d, rstar_rsun, a_rsun, k):
    """Total duration of a central (b = 0) transit, hours."""
    x = (rstar_rsun / a_rsun) * (1.0 + k)
    return period_d * 24.0 / math.pi * math.asin(min(1.0, x))


def dayside_temp(teff, rstar_rsun, a_rsun):
    """Zero-albedo, no-redistribution dayside temperature (K)."""
    return teff * math.sqrt(rstar_rsun / a_rsun) * (2.0 / 3.0) ** 0.25


def planck_ratio(t_body, t_star, wavelength_um=0.8):
    """B_lambda(t_body) / B_lambda(t_star) at one wavelength."""
    xb = HC_OVER_K_UM_K / (wavelength_um * t_body)
    xs = HC_OVER_K_UM_K / (wavelength_um * t_star)
    return math.expm1(xs) / math.expm1(xb)


def thermal_secondary(depth, t_body, t_star, wavelength_um=0.8):
    """Secondary-eclipse depth from thermal emission; depth = (Rp/Rs)^2."""
    return depth * planck_ratio(t_body, t_star, wavelength_um)


def reflected_secondary(depth, rstar_rsun, a_rsun, albedo):
    """Secondary-eclipse depth from reflected light with geometric albedo `albedo`."""
    return albedo * depth * (rstar_rsun / a_rsun) ** 2


def flux_ratio(g_neighbour, g_target):
    return 10.0 ** (-0.4 * (g_neighbour - g_target))


def required_neighbour_depth(observed_depth, g_neighbour, g_target):
    """Eclipse depth a neighbour fully inside the target's window would need. > 1 is impossible."""
    return observed_depth / flux_ratio(g_neighbour, g_target)


# Inputs (sources in findings/2026-11-25-vpt-followup-results.md)
TIC4638108 = dict(period=2.2082803218243496, teff=7095.0, rstar=1.42469, mstar=1.57,
                  depth=0.014066311442613336, sec=0.0005073346779340366,
                  sec_err=0.00014474725726472447, g=12.788467, depth_gaia=0.01574097334964364)
TIC44997521 = dict(period=3.5494134813413276, teff=4563.0, rstar=0.79579, mstar=0.72,
                   depth=0.02037064986882855, g=13.809506, depth_gaia=0.02220147364713032)
# Gaia DR3 sources within 6 arcsec of TIC 4638108 (G mag, separation arcsec); none for TIC 44997521
NEIGHBOURS_4638108 = [(18.253727, 2.62), (20.290659, 4.87), (18.276094, 5.73)]


def report():
    out = {}
    for name, s in (("TIC 4638108", TIC4638108), ("TIC 44997521", TIC44997521)):
        a = semi_major_axis_rsun(s["period"], s["mstar"])
        k = math.sqrt(s["depth"])
        r = {"a_rsun": a, "a_over_rstar": a / s["rstar"],
             "t14_central_h": t14_central_hours(s["period"], s["rstar"], a, k)}
        if "sec" in s:
            td = dayside_temp(s["teff"], s["rstar"], a)
            r["t_dayside"] = td
            r["sec_thermal_planet"] = thermal_secondary(s["depth"], td, s["teff"])
            r["sec_reflected_ag05"] = reflected_secondary(s["depth"], s["rstar"], a, 0.5)
            r["sec_selfluminous_3100K"] = thermal_secondary(s["depth"], 3100.0, s["teff"])
            r["sec_observed"] = s["sec"]
            r["sec_observed_err"] = s["sec_err"]
        out[name] = r
    out["TIC 4638108"]["neighbour_required_depths"] = [
        required_neighbour_depth(TIC4638108["depth_gaia"], g, TIC4638108["g"])
        for g, _ in NEIGHBOURS_4638108]
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(report(), indent=1))
