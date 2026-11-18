# SPDX-License-Identifier: Apache-2.0
"""Pure-Python tests for sb1_transit (no numpy needed). MV2 of Munim, Inc.; made with AI agents.

Expected values were worked by hand (see findings/2026-11-18-sb1-transit-prereg.md)."""
import math
import unittest

import sb1_transit as st

# Gaia DR3 4955371367334610048 (WASP-18), SB1 solution as served by the Gaia archive
WASP18 = {"source_id": "4955371367334610048", "nss_solution_type": "SB1",
          "period": "0.9414684606070756", "eccentricity": "0.1233766991234055",
          "arg_periastron": "142.72697663690195", "t_periastron": "-0.3399625641074499",
          "semi_amplitude_primary": "1.9382581841901922"}
# ExoFOP TOI-185.01 (WASP-18 b): epoch BJD 2460205.353322, P 0.9414525 d
TOI185_EPOCH_BTJD = 3205.353322
TOI185_P = 0.9414525


def wasp18_t0():
    r = WASP18
    return st.transit_time_btjd(float(r["t_periastron"]), float(r["period"]),
                                float(r["eccentricity"]), float(r["arg_periastron"]))


class TestEphemeris(unittest.TestCase):
    def test_wasp18_transit_time(self):
        self.assertAlmostEqual(wasp18_t0(), 389.4914, delta=0.002)

    def test_wasp18_matches_tess_after_2991_orbits(self):
        t = wasp18_t0()
        k = round((TOI185_EPOCH_BTJD - t) / TOI185_P)
        self.assertEqual(k, 2991)
        self.assertLess(abs(t + k * TOI185_P - TOI185_EPOCH_BTJD), 0.04)

    def test_circular_quarter_phase(self):
        # SB1C: t_periastron is the RV maximum (ascending node) -> transit P/4 later
        self.assertAlmostEqual(st.transit_time_btjd(0.0, 4.0, 0.0, 0.0), 390.0, places=9)
        self.assertAlmostEqual(st.secondary_time_btjd(0.0, 4.0, 0.0, 0.0), 392.0, places=9)

    def test_omega_90_transit_at_periastron(self):
        self.assertAlmostEqual(st.transit_phase(0.4, 90.0) % 1.0, 0.0, places=9)

    def test_wrap(self):
        self.assertAlmostEqual(st.wrap(7.5, 10.0), -2.5)
        self.assertAlmostEqual(st.wrap(-5.0, 10.0), -5.0)
        self.assertAlmostEqual(st.wrap(4.9, 10.0), 4.9)


class TestMasses(unittest.TestCase):
    def test_mass_function(self):
        self.assertAlmostEqual(st.mass_function(10.0, 1.0, 0.0), 1.0361e-4, places=12)

    def test_toi2533_like(self):
        # K 7.39 km/s, P 6.6847 d, circular, 1 Msun -> m2 sin i ~ 0.0683 Msun (~72 M_Jup)
        self.assertAlmostEqual(st.m2_min(7.39, 6.6847, 0.0, 1.0), 0.0683, delta=0.0003)

    def test_transit_probability_sunlike(self):
        a = st.semi_major_axis_rsun(1.0, 0.05, 3.0)
        self.assertAlmostEqual(a, 8.897, delta=0.02)
        self.assertAlmostEqual(st.transit_probability(1.0, 0.1, a, 0.0, 0.0), 0.1236, delta=0.002)

    def test_duration_and_box(self):
        a = st.semi_major_axis_rsun(1.0, 0.05, 3.0)
        d = st.duration_days(3.0, 1.0, 0.1, a, 0.0, 0.0)
        # P/pi * asin(1.1/a) = 0.9549 * 0.1239 = 0.1183 d (2.84 h)
        self.assertAlmostEqual(d, 0.1183, delta=0.001)
        self.assertAlmostEqual(st.box_width(d), 0.6 * d)
        self.assertAlmostEqual(st.box_width(0.01), 1.0 / 24)

    def test_companion_radius(self):
        self.assertEqual(st.companion_radius(0.05), 0.10)
        self.assertAlmostEqual(st.companion_radius(0.09), 0.09 ** 0.9)


class TestCorrAndStats(unittest.TestCase):
    def test_param_names(self):
        self.assertEqual(st.sb1_param_names("SB1"),
                         ["period", "center_of_mass_velocity", "semi_amplitude_primary",
                          "eccentricity", "arg_periastron", "t_periastron"])
        self.assertEqual(len(st.sb1_param_names("SB1C")), 4)
        self.assertIsNone(st.sb1_param_names("Orbital"))

    def test_corr_matrix_order(self):
        R = st.corr_matrix([0.1, 0.2, 0.3], 3)
        self.assertEqual(R[0][1], 0.1)
        self.assertEqual(R[0][2], 0.2)
        self.assertEqual(R[1][2], 0.3)
        self.assertEqual(R[2][1], 0.3)
        with self.assertRaises(ValueError):
            st.corr_matrix([0.1], 3)

    def test_parse_corr_vec(self):
        self.assertEqual(st.parse_corr_vec("[0.1, -0.2, 0.3]"), [0.1, -0.2, 0.3])
        self.assertEqual(st.parse_corr_vec("(0.5 0.25)"), [0.5, 0.25])
        self.assertIsNone(st.parse_corr_vec(""))

    def test_garwood(self):
        lo, hi = st.garwood(0)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, math.log(40.0), places=3)
        lo, hi = st.garwood(5)
        self.assertAlmostEqual(lo, 1.6235, delta=0.002)
        self.assertAlmostEqual(hi, 11.6683, delta=0.002)
        lo, hi = st.garwood(1)
        self.assertAlmostEqual(lo, 0.0253, delta=0.0005)
        self.assertAlmostEqual(hi, 5.5716, delta=0.002)

    def test_utc_to_btjd(self):
        self.assertAlmostEqual(st.utc_to_btjd("2018-07-25 19:35:00"), 1325.315972, delta=1e-5)


class TestRules(unittest.TestCase):
    GOOD = {"depth": 0.004, "snr": 12.0, "local_ratio": 0.95, "n_ep": 5, "snr_drop1": 9.0}

    def test_sector_hit(self):
        self.assertTrue(st.sector_hit(self.GOOD))
        self.assertFalse(st.sector_hit(None))
        self.assertFalse(st.sector_hit(dict(self.GOOD, snr=6.9)))
        self.assertFalse(st.sector_hit(dict(self.GOOD, depth=-0.001)))
        self.assertFalse(st.sector_hit(dict(self.GOOD, local_ratio=0.5)))
        self.assertFalse(st.sector_hit(dict(self.GOOD, n_ep=2)))         # single/double event
        self.assertFalse(st.sector_hit(dict(self.GOOD, snr_drop1=2.0)))  # one transit dominates

    def test_phase_check(self):
        off, z, lab = st.phase_check(10.05, 10.0, 0.02, 5.0)
        self.assertAlmostEqual(off, 0.05)
        self.assertAlmostEqual(z, 2.5)
        self.assertEqual(lab, "PHASE_MATCH")
        self.assertEqual(st.phase_check(10.2, 10.0, 0.02, 5.0)[2], "PHASE_MISMATCH")
        self.assertEqual(st.phase_check(10.0, 10.0, 1.0, 5.0)[2], "UNTIMED")
        off, z, lab = st.phase_check(14.9, 10.0, 0.05, 5.0)   # wraps to -0.1 d
        self.assertAlmostEqual(off, -0.1)
        self.assertEqual(lab, "PHASE_MATCH")

    def test_chunks_disjoint_and_complete(self):
        ids = [str(i) for i in range(101)]
        a = st.chunk_order(ids, 2, 0)
        b = st.chunk_order(ids, 2, 1)
        self.assertEqual(len(set(a) & set(b)), 0)
        self.assertEqual(sorted(a + b), sorted(ids))
        self.assertEqual(a, st.chunk_order(list(reversed(ids)), 2, 0))

    def test_classify_hit(self):
        self.assertEqual(st.classify_hit(0.01, 0.01), "SUBSTELLAR_SIZE")
        self.assertEqual(st.classify_hit(0.05, 0.01), "TOO_DEEP")
        self.assertEqual(st.classify_hit(0.01, 0.01, mod_amp=0.006), "MODULATED")
        self.assertEqual(st.classify_hit(float("nan"), 0.01), "")

    def test_star_physics_and_eligibility(self):
        row = {"nss_solution_type": "SB1", "period": "6.6847", "semi_amplitude_primary": "7.39",
               "eccentricity": "0.0", "arg_periastron": "0.0", "phot_g_mean_mag": "11.0",
               "parallax": "5.0", "mass_flame": "1.0", "radius_flame": "1.0"}
        ph = st.star_physics(row)
        self.assertEqual(ph["m2_class"], "BD")
        self.assertAlmostEqual(ph["depth_exp"], 0.01, places=6)
        ok, why = st.eligible(row, ph)
        self.assertTrue(ok, why)
        self.assertEqual(st.eligible(row, dict(ph, r1=5.0)), (False, "evolved"))
        self.assertEqual(st.eligible(row, dict(ph, P=20.0)), (False, "period"))


if __name__ == "__main__":
    unittest.main()
