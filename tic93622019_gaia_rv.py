# SPDX-License-Identifier: Apache-2.0
"""tic93622019_gaia_rv 0.1.0 - upper limit on the mass of whatever transits TIC 93622019, from the
scatter of Gaia DR3's own radial velocities of the star.

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Apache-2.0.
Exploratory vetting step (not pre-registered). Stdlib only, no network.

Method (Katz et al. 2023, A&A 674, A5; as used in arXiv:2401.11293): for rv_method_used = 1,
radial_velocity_error = sqrt(sigma_med^2 + 0.11^2) with sigma_med = sqrt(pi/2) * sigma / sqrt(N),
so the scatter of the N epoch velocities is sigma = sqrt((2N/pi) * (err^2 - 0.11^2)). If all of
that scatter were a circular orbit sampled at random phases, K = sqrt(2) * sigma. A one-sided 95%
upper bound on sigma uses the chi-square distribution with N - 1 degrees of freedom. The bound on
the companion mass then follows from the mass function with the star's TIC mass, and sin i from the
fact that it transits.

  python tic93622019_gaia_rv.py [--out results.json]
"""
import argparse
import json
import math
import sys

VERSION = "0.1.0"

# Gaia DR3 gaia_source row of Gaia DR3 5345417757181174144 (= TIC 93622019), read from the AIP
# Gaia TAP service on 24 Nov 2026; saved in data/tic93622019-gaia-rv/gaia_dr3_rv_row.csv.
GAIA = {
    "source_id": "5345417757181174144",
    "radial_velocity": -4.9032903,
    "radial_velocity_error": 1.6843823,
    "rv_nb_transits": 27,
    "rv_amplitude_robust": 16.166862,
    "rv_chisq_pvalue": 0.5143973,
    "rv_renormalised_gof": 4.0999575,
    "rv_method_used": 1,
    "rv_template_teff": 6000.0,
    "grvs_mag": 11.9599085,
    "ruwe": 0.90267724,
    "ipd_frac_multi_peak": 0,
    "non_single_star": 0,
}
FLOOR_KMS = 0.11                 # Katz et al. 2023 calibration floor, added in quadrature
P_DAYS = 2.1238933               # TESS period (this project, findings of 22-24 Nov 2026)
MSTAR = 1.33                     # TIC v8.2 mass (Msun)
RSTAR = 1.36                     # TIC v8.2 radius (Rsun)
DEPTH = 0.0128                   # deblended TESS depth (this project)

GM_SUN = 1.32712440018e20        # m^3 s^-2
GM_JUP = 1.26686534e17           # m^3 s^-2
R_SUN = 6.957e8                  # m
DAY = 86400.0


def epoch_sigma(err, n, floor=FLOOR_KMS):
    """Scatter of the epoch velocities (km/s) from radial_velocity_error and the transit count."""
    v = err * err - floor * floor
    if v <= 0 or n < 2:
        return 0.0
    return math.sqrt(2.0 * n / math.pi * v)


def norm_ppf(p):
    """Inverse standard normal CDF (Acklam's rational approximation, |error| < 1.2e-9)."""
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    lo = 0.02425
    if p < lo:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - lo:
        return -norm_ppf(1 - p)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def chi2_ppf(p, k):
    """Chi-square quantile, Wilson-Hilferty approximation (good to ~0.1% for k >= 10)."""
    z = norm_ppf(p)
    h = 2.0 / (9.0 * k)
    return k * (1.0 - h + z * math.sqrt(h)) ** 3


def sigma_upper(sigma, n, conf=0.95):
    """One-sided upper confidence bound on the true scatter, given the sample scatter of n points."""
    return sigma * math.sqrt((n - 1) / chi2_ppf(1.0 - conf, n - 1))


def k_of_m2(m2_mjup, p_days=P_DAYS, mstar=MSTAR, sini=1.0, ecc=0.0):
    """Primary's RV semi-amplitude (m/s) for a companion of m2_mjup Jupiter masses."""
    gm2 = m2_mjup * GM_JUP
    gmt = mstar * GM_SUN + gm2
    n = (2.0 * math.pi / (p_days * DAY)) ** (1.0 / 3.0)
    return n * gm2 * sini / gmt ** (2.0 / 3.0) / math.sqrt(1.0 - ecc * ecc)


def m2_of_k(k_ms, p_days=P_DAYS, mstar=MSTAR, sini=1.0):
    """Companion mass (Jupiter masses) giving semi-amplitude k_ms; bisection, K rises with m2."""
    lo, hi = 0.0, 5.0 * GM_SUN / GM_JUP
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if k_of_m2(mid, p_days, mstar, sini) < k_ms:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def semi_major_axis_rsun(p_days=P_DAYS, mstar=MSTAR):
    a3 = mstar * GM_SUN * (p_days * DAY) ** 2 / (4.0 * math.pi ** 2)
    return a3 ** (1.0 / 3.0) / R_SUN


def sini_min(p_days=P_DAYS, mstar=MSTAR, rstar=RSTAR, depth=DEPTH):
    """Smallest sin i that still allows a (grazing) transit: cos i <= (R* + Rp) / a."""
    a = semi_major_axis_rsun(p_days, mstar)
    rp = rstar * math.sqrt(depth)
    c = min(1.0, (rstar + rp) / a)
    return math.sqrt(1.0 - c * c)


def run(g=GAIA):
    n = int(g["rv_nb_transits"])
    s = epoch_sigma(g["radial_velocity_error"], n)
    s95 = sigma_upper(s, n)
    k_pt, k95 = math.sqrt(2.0) * s, math.sqrt(2.0) * s95
    si = sini_min()
    m_pt, m95 = m2_of_k(k_pt * 1000.0, sini=si), m2_of_k(k95 * 1000.0, sini=si)
    mj_per_msun = GM_SUN / GM_JUP
    return {
        "version": VERSION,
        "inputs": dict(g, floor_kms=FLOOR_KMS, period_d=P_DAYS, mstar_msun=MSTAR,
                       rstar_rsun=RSTAR, depth=DEPTH),
        "valid_epoch_stats": (g["rv_method_used"] == 1 and g["grvs_mag"] <= 12.0
                              and 3900 <= g["rv_template_teff"] <= 8000),
        "rv_variable_by_katz2023": (n > 10 and g["rv_chisq_pvalue"] <= 0.01
                                    and g["rv_renormalised_gof"] > 4),
        "sigma_epoch_kms": s,
        "sigma_epoch_95_kms": s95,
        "chi2_05_dof": chi2_ppf(0.05, n - 1),
        "K_all_scatter_kms": k_pt,
        "K_95_kms": k95,
        "K_per_mjup_ms": k_of_m2(1.0),
        "a_rsun": semi_major_axis_rsun(),
        "a_over_rstar": semi_major_axis_rsun() / RSTAR,
        "sini_min": si,
        "rp_rjup": RSTAR * math.sqrt(DEPTH) * R_SUN / 7.1492e7,
        "m2_max_all_scatter_mjup": m_pt,
        "m2_max_all_scatter_msun": m_pt / mj_per_msun,
        "m2_max_95_mjup": m95,
        "m2_max_95_msun": m95 / mj_per_msun,
        "K_equal_mass_twin_kms": k_of_m2(MSTAR * mj_per_msun) / 1000.0,
        "K_0p3msun_kms": k_of_m2(0.3 * mj_per_msun) / 1000.0,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    res = run()
    txt = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
