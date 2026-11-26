# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""tyc6340_gaia_conj.py 0.1.1 -- does the TESS eclipse of TYC 6340-23-1 fall at the conjunction
predicted by Gaia DR3's own single-lined orbit?

TYC 6340-23-1 = TIC 71945261 = Gaia DR3 6853008555751131648 has no Gaia DR3 epoch photometry
(gaia_source.has_epoch_photometry = False), so the dip test of g8_dr3_sb1.py cannot be applied in
DR3. This script instead propagates Gaia's orbit to the conjunction where the visible star is
behind its companion (true anomaly nu = 90 deg - omega; the primary eclipse for a faint
companion), with a linearised uncertainty from Gaia's own correlation vector, and compares it
with the measured TESS/SuperWASP ephemeris.

Inputs are transcribed by hand from the AIP Gaia DR3 TAP mirror (gaiadr3.nss_two_body_orbit,
fetched 25 Nov 2026) and from findings/2026-11-22-tyc6340-pixel-results.md (ephemeris). The
SB1 corr_vec order is P, gamma, K, e, omega, T_periastron (Gosset et al. 2024, arXiv:2410.14372,
App. H: SB1 bit_index 127, corr_vec length 15), upper triangle, column-major.
Pure Python, no network.

0.1.1 (26 Nov 2026): the self-test compared the (gamma, K) element with the (P, K) value; it now
checks both elements against the right entries. The computation itself is unchanged.
"""
import json
import math
import sys

VERSION = "0.1.1"
REF_EPOCH_BJD = 2457389.0  # J2016.0, Gaia DR3 reference epoch for t_periastron (TCB)

ORBIT = {  # Gaia DR3 nss_two_body_orbit, source_id 6853008555751131648, SB1
    "period": 2.3289298492522734, "period_error": 0.00014048208,
    "t_periastron": -0.5700115815593534, "t_periastron_error": 0.29357073,
    "eccentricity": 0.04048587359818022, "eccentricity_error": 0.031135598,
    "arg_periastron": 358.11326686203677, "arg_periastron_error": 45.746304,
    "semi_amplitude_primary": 16.15912885263879,
    "corr_vec": [-0.30027038, 0.38529134, -0.48674697, 0.21028686, -0.2868966, -0.087893374,
                 0.40104228, 0.15167798, 0.05606818, 0.19678, 0.4354885, 0.13946818,
                 0.080820315, 0.19881018, 0.9985261],
}
PARAMS = ["P", "gamma", "K", "e", "omega", "Tp"]

# TESS + SuperWASP ephemeris of the primary eclipse (pixel-results note, 22 Nov 2026)
T0_BJD_TDB = 2460817.00291
T0_ERR = 0.00012
P_ECL = 2.3287747
P_ECL_ERR = 0.0000003


def corr_matrix(vec, n=6):
    """Unpack an upper-triangle column-major correlation vector into a full n x n matrix:
    element k runs over (0,1), (0,2), (1,2), (0,3), (1,3), (2,3), ... ."""
    c = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    k = 0
    for j in range(1, n):
        for i in range(j):
            c[i][j] = c[j][i] = vec[k]
            k += 1
    if k != len(vec):
        raise ValueError("corr_vec length does not match n")
    return c


def mean_anomaly_from_true(nu_rad, e):
    e_anom = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu_rad / 2.0),
                              math.sqrt(1.0 + e) * math.cos(nu_rad / 2.0))
    m = e_anom - e * math.sin(e_anom)
    return m % (2.0 * math.pi)


def conjunction_time(p, e, omega_deg, tp_rel, which=0):
    """BJD of the conjunction nearest after periastron. which=0: nu = 90 - omega (the visible
    star is behind its companion); which=1: nu = 270 - omega (the companion is behind)."""
    nu = math.radians((90.0 + 180.0 * which - omega_deg) % 360.0)
    m = mean_anomaly_from_true(nu, e)
    return REF_EPOCH_BJD + tp_rel + p * m / (2.0 * math.pi)


def propagate(orbit=ORBIT):
    vals = {"P": orbit["period"], "gamma": 0.0, "K": orbit["semi_amplitude_primary"],
            "e": orbit["eccentricity"], "omega": orbit["arg_periastron"],
            "Tp": orbit["t_periastron"]}
    errs = {"P": orbit["period_error"], "gamma": 0.0, "K": 0.0, "e": orbit["eccentricity_error"],
            "omega": orbit["arg_periastron_error"], "Tp": orbit["t_periastron_error"]}

    def f(v):
        return conjunction_time(v["P"], v["e"], v["omega"], v["Tp"], 0)

    tc = f(vals)
    grad = {}
    for name in PARAMS:
        h = errs[name] * 1e-3
        if h == 0.0:
            grad[name] = 0.0
            continue
        up = dict(vals); up[name] += h
        dn = dict(vals); dn[name] -= h
        grad[name] = (f(up) - f(dn)) / (2.0 * h) * errs[name]  # scaled by sigma
    c = corr_matrix(orbit["corr_vec"])
    var = 0.0
    for i, a in enumerate(PARAMS):
        for j, b in enumerate(PARAMS):
            var += c[i][j] * grad[a] * grad[b]
    var_indep = sum(g * g for g in grad.values())
    return tc, math.sqrt(var), math.sqrt(var_indep), grad


def compare(tc, sigma_tc):
    n = round((T0_BJD_TDB - tc) / P_ECL)
    pred = tc + n * P_ECL
    offset = T0_BJD_TDB - pred  # positive: TESS eclipse after Gaia's predicted conjunction
    sig = math.sqrt(sigma_tc ** 2 + T0_ERR ** 2 + (n * P_ECL_ERR) ** 2)
    tc1 = conjunction_time(ORBIT["period"], ORBIT["eccentricity"], ORBIT["arg_periastron"],
                           ORBIT["t_periastron"], 1)
    n1 = round((T0_BJD_TDB - tc1) / P_ECL)
    off1 = T0_BJD_TDB - (tc1 + n1 * P_ECL)
    # distance (in days, modulo P) from the TESS eclipse to the OTHER conjunction
    return {"n_cycles": n, "offset_d": offset, "offset_phase": offset / P_ECL,
            "sigma_d": sig, "z": offset / sig,
            "other_conjunction_offset_d": off1, "other_conjunction_z": off1 / sig}


def self_test():
    c = corr_matrix(ORBIT["corr_vec"])
    ok = [abs(c[4][5] - 0.9985261) < 1e-12,    # (omega, Tp), element 14
          abs(c[0][3] - 0.21028686) < 1e-12,   # (P, e), element 3
          abs(c[3][4] - 0.19678) < 1e-12,      # (e, omega), element 9
          abs(c[0][2] - 0.38529134) < 1e-12,   # (P, K), element 1
          abs(c[1][2] + 0.48674697) < 1e-12]   # (gamma, K), element 2
    # circular orbit: M = nu
    ok.append(abs(mean_anomaly_from_true(1.0, 0.0) - 1.0) < 1e-12)
    # sigma_Tp ~ P sigma_omega / 360 (near-degenerate omega-Tp pair)
    ok.append(abs(ORBIT["period"] * ORBIT["arg_periastron_error"] / 360.0 / ORBIT["t_periastron_error"] - 1.0) < 0.01)
    return all(ok)


def main():
    if not self_test():
        print("self-test FAILED")
        return 3
    tc, s, s_ind, grad = propagate()
    res = compare(tc, s)
    out = {"version": VERSION, "gaia_conjunction0_bjd": tc, "sigma_conjunction_d": s,
           "sigma_if_uncorrelated_d": s_ind, "scaled_gradients_d": grad, **res}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
