# dr4_sb1_reality 0.1.1 (dr3)

S3 pool 6434 (expected 6434); sources 6434

| label | n |
|---|---|
| CONFIRMED | 6434 |
| ALIAS | 0 |
| CHANGED | 0 |
| DROPPED | 0 |
| UNTESTABLE | 0 |

Epoch step: suspended (DR3 has no epoch RVs; rehearsal)

- **R0** >= 70% of S3 testable: pass = True
- **D1** f_conf upper 95% < 0.8: pass = False
- **D2** f_conf(K3 >= 3 km/s) > f_conf(K3 < 3 km/s), 95% intervals not overlapping: pass = False
- **D4** (exploratory) f_conf(m1 >= 1.5) < f_conf(m1 < 1.2): pass = False

Reading: D1 fails: most DR3 orbits are real; small rho is (N) or a fault in the TESS test

Rehearsal: {"RH1_pool_reproduced": true, "RH2_all_matched": true, "RH3_all_confirmed": true, "RH4_datalink_plumbing": true}
