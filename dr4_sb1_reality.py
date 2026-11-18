# SPDX-License-Identifier: Apache-2.0
"""dr4_sb1_reality.py -- do Gaia DR3's brown-dwarf-mass SB1 orbits survive into Gaia DR4?

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Pre-registration: findings/2026-11-18-dr4-sb1-reality-prereg.md, amendment 1 (epoch RVs
through DataLink) and amendment 2 (the implementation rules of this file). Written
2026-11-18, two weeks before Gaia DR4 (2 December 2026), with no DR4 data seen.

What it does (stdlib only, network through dr4_fetch.tap_query and urllib):
  1. S3: the full eligible DR3 pool of sb1_robust 0.2.0 (same ADQL, same eligibility via
     the pinned sb1_transit 0.1.0, no fallback). Must reproduce 6,434 stars (exit 3).
  2. DR3 -> DR4 identifiers from gaiadr4.dr3_neighbourhood (dr4_fetch rules).
  3. DR4 orbits with P and K from nss_two_body_orbit, then rvs_two_body_orbit, then
     nss_two_body_orbit_supp (amendment 2 section 1), K from C/H for
     AstroSpectroSB1. Per-source label CONFIRMED / ALIAS / CHANGED / DROPPED / UNTESTABLE.
  4. Epoch RVs through the Gaia DataLink service (batches of <= 500), counted with the
     amendment-1 rules, and an independent circular fit at P3 (EPOCH_OK / FLAT / ...).
  5. Grades R0, D1, D2, D4 from the tables; D3 from sb1_robust's sb1_stars.csv files
     (`grade-tess` subcommand).
`--schema dr3` is the dress rehearsal on DR3 itself (identity match, DR3 orbits): every S3
orbit must come back CONFIRMED, and the DataLink plumbing is smoke-tested on DR3 epoch
photometry (DR3 has no epoch RVs, so the epoch step is suspended there by design).

Exit codes: 0 ok; 2 archive unavailable (re-file unchanged); 3 S3 pool not reproduced;
4 a table/column the rules need is missing (schema_found.json / datalink_found.json list
what exists); 6 the DataLink epoch-RV retrieval type is not uniquely identified (rerun with
--retrieval-type X, or --suspend-epochs to apply amendment 1 rule 4 explicitly).
"""
import argparse
import csv
import gzip
import io
import json
import math
import os
import re
import sys
import tarfile
import time
import urllib.parse
import urllib.request
import zipfile

import dr4_fetch as df

VERSION = "0.1.0"
EXPECTED_POOL = 6434
MIN_EPOCHS = 10
ALIAS_BASE_PERIODS = (1.0, 365.25, 63.0)     # 1 day, 1 year, Gaia scan precession
ALIAS_TOL = 0.005
P_FLOOR = 0.002
K_FLOOR = 0.3
K_SPLIT = 3.0                                 # km/s, D2
EPOCH_BATCH = 500
AU_KM = 1.495978707e8
DAY_S = 86400.0
DATA_URL = "https://gea.esac.esa.int/data-server/data"
LINKS_URL = "https://gea.esac.esa.int/data-server/datalink/links"
RELEASE = {"dr3": "Gaia DR3", "dr4": "Gaia DR4"}
P_EDGES = (1, 1.5, 2, 3, 5, 8, 13)

# Spectroscopic solution types in order of preference when one source has several rows
# (never chosen by period or by agreement with DR3). Any other type with finite P and K
# also counts, after these, ordered by significance.
RV_PREF = ("sb1", "sb1c", "astrospectrosb1", "eclipsingspectro", "sb2", "sb2c")
SB1_REQUIRED = ("source_id", "nss_solution_type", "period", "period_error",
                "semi_amplitude_primary", "semi_amplitude_primary_error")
SB1_OPTIONAL = ("eccentricity", "eccentricity_error", "c_thiele_innes",
                "c_thiele_innes_error", "h_thiele_innes", "h_thiele_innes_error",
                "significance", "bit_index")
EPOCH_REQUIRED = ("radial_velocity", "radial_velocity_error", "outlier_status",
                  "emission_lines")
RV_TYPE_RE = re.compile(r"(RV|RADIAL).*EPOCH|EPOCH.*(RV|RADIAL)", re.I)
LABELS = ("CONFIRMED", "ALIAS", "CHANGED", "DROPPED", "UNTESTABLE")


class EpochSchemaError(RuntimeError):
    def __init__(self, msg, columns=None):
        super().__init__(msg)
        self.columns = columns or []


class RvTypeError(RuntimeError):
    """The DataLink epoch-RV retrieval type is not uniquely identified (exit 6)."""


# ================================================================== pure helpers
fnum = df.fnum


def k_from_ch(C, H, P, e=0.0, sC=float("nan"), sH=float("nan")):
    """K1 [km/s] and its error from AstroSpectroSB1 Thiele-Innes C, H [AU]:
    a1 sin i = sqrt(C^2 + H^2); K1 = 2 pi a1 sin i / (P sqrt(1 - e^2)).
    The error propagates sC and sH only (no correlations, P and e errors neglected)."""
    C, H, P = fnum(C), fnum(H), fnum(P)
    e = fnum(e, 0.0)
    if not (math.isfinite(C) and math.isfinite(H) and P > 0 and 0.0 <= e < 1.0):
        return float("nan"), float("nan")
    a2 = C * C + H * H
    if a2 <= 0:
        return 0.0, float("nan")
    K = 2.0 * math.pi * math.sqrt(a2) * AU_KM / (P * DAY_S * math.sqrt(1.0 - e * e))
    sC, sH = fnum(sC), fnum(sH)
    if math.isfinite(sC) and math.isfinite(sH):
        sK = K * math.sqrt((C * sC) ** 2 + (H * sH) ** 2) / a2
    else:
        sK = float("nan")
    return K, sK


def rv_orbit(row):
    """{'P','sP','K','sK','K_src','type','significance'} for an NSS row with a finite
    period and RV semi-amplitude (direct, or from C/H), else None."""
    P = fnum(row.get("period"))
    if not (P > 0):
        return None
    K, sK, src = fnum(row.get("semi_amplitude_primary")), \
        fnum(row.get("semi_amplitude_primary_error")), "semi_amplitude_primary"
    if not (K > 0):
        K, sK = k_from_ch(row.get("c_thiele_innes"), row.get("h_thiele_innes"), P,
                          row.get("eccentricity"), row.get("c_thiele_innes_error"),
                          row.get("h_thiele_innes_error"))
        src = "thiele_innes_CH"
    if not (K > 0):
        return None
    return {"P": P, "sP": fnum(row.get("period_error")), "K": K, "sK": sK, "K_src": src,
            "type": str(row.get("nss_solution_type", "")).strip().strip('"'),
            "significance": fnum(row.get("significance"), 0.0),
            "table": row.get("_table", "")}


def _rv_rank(t):
    t = str(t).lower()
    return RV_PREF.index(t) if t in RV_PREF else len(RV_PREF)


def table_rank(table):
    """0 = nss_two_body_orbit, 1 = rvs_two_body_orbit (DR4 17.06), 2 = nss_two_body_orbit_supp."""
    t = str(table)
    if t.endswith("_supp"):
        return 2
    if "rvs_two_body_orbit" in t:
        return 1
    return 0


def pick_rv(rows):
    """Choose the DR4 RV orbit for one source. Tables in table_rank order: a later table is
    used only when no earlier one has an RV orbit for the source. Within a table: RV_PREF
    order, then larger significance. Never chosen by period or by agreement with DR3.
    Returns (orbit or None, n_rv_rows, from_supp)."""
    orbits = [o for o in (rv_orbit(r) for r in rows) if o]
    if not orbits:
        return None, 0, False
    best = min(table_rank(o["table"]) for o in orbits)
    use = [o for o in orbits if table_rank(o["table"]) == best]
    use.sort(key=lambda o: (_rv_rank(o["type"]), -o["significance"]))
    return use[0], len(orbits), best == 2


def _tol(a, sa, b, sb, floor):
    sa = fnum(sa, 0.0)
    sb = fnum(sb, 0.0)
    return max(3.0 * math.sqrt(sa * sa + sb * sb), floor)


def p_agrees(P3, sP3, P4, sP4):
    return abs(P4 - P3) <= _tol(P3, sP3, P4, sP4, P_FLOOR * P3)


def k_agrees(K3, sK3, K4, sK4):
    return abs(K4 - K3) <= _tol(K3, sK3, K4, sK4, K_FLOOR * K3)


def alias_periods(P3):
    """1-day, 1-year and 63-day aliases of P3 (|1/P3 +- 1/Pb|), plus 2 P3 and P3/2."""
    out = [2.0 * P3, P3 / 2.0]
    f = 1.0 / P3
    for Pb in ALIAS_BASE_PERIODS:
        for fa in (f + 1.0 / Pb, abs(f - 1.0 / Pb)):
            if fa > 0:
                out.append(1.0 / fa)
    return out


def is_alias(P3, P4, tol=ALIAS_TOL):
    return any(abs(P4 - Pa) <= tol * Pa for Pa in alias_periods(P3))


def orbit_label(dr3, dr4):
    """CONFIRMED / ALIAS / CHANGED for a DR4 RV orbit against the DR3 one."""
    if p_agrees(dr3["P"], dr3["sP"], dr4["P"], dr4["sP"]):
        return "CONFIRMED" if k_agrees(dr3["K"], dr3["sK"], dr4["K"], dr4["sK"]) else "CHANGED"
    return "ALIAS" if is_alias(dr3["P"], dr4["P"]) else "CHANGED"


def source_label(match_status, orbit_lab, n_epochs, epochs_active):
    """Final label. A DR4 RV orbit decides when there is one. Without one, a matched
    source is DROPPED if it has >= MIN_EPOCHS counted epochs (or, with the epoch step
    suspended under amendment 1 rule 4, simply if it is matched); else UNTESTABLE."""
    if match_status != "ok":
        return "UNTESTABLE"
    if orbit_lab:
        return orbit_lab
    if not epochs_active:
        return "DROPPED"
    return "DROPPED" if (n_epochs or 0) >= MIN_EPOCHS else "UNTESTABLE"


def _flag(v):
    s = str(v if v is not None else "").strip().strip('"').lower()
    return s not in ("", "0", "false", "f", "null", "none", "nan", "--")


def epoch_counts(row):
    """Amendment 1 rule 3: finite RV with a positive error, outlier_status not set,
    emission_lines false."""
    v, s = fnum(row.get("radial_velocity")), fnum(row.get("radial_velocity_error"))
    if not (math.isfinite(v) and s > 0):
        return False
    return not _flag(row.get("outlier_status")) and not _flag(row.get("emission_lines"))


def pick_time_col(columns, override=None):
    """The epoch-time column: --time-col if given; else the only column whose name
    contains 'time' (not '_error'/'_flag'); if several, the only one also containing 'obs'.
    Anything else raises EpochSchemaError (no guessing)."""
    cols = [c.strip().lower() for c in columns]
    if override:
        if override.lower() in cols:
            return override.lower()
        raise EpochSchemaError("time column %r not found" % override, cols)
    t = [c for c in cols if "time" in c and not c.endswith(("_error", "_flag"))]
    if len(t) == 1:
        return t[0]
    t2 = [c for c in t if "obs" in c]
    if len(t2) == 1:
        return t2[0]
    raise EpochSchemaError("epoch time column not unique: %s" % t, cols)


def _solve3(A, b):
    """Gauss-Jordan solve of a 3x3 system; returns (x, inverse) or (None, None)."""
    n = 3
    M = [list(A[i]) + [b[i]] + [1.0 if j == i else 0.0 for j in range(n)] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-300:
            return None, None
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        M[c] = [x / piv for x in M[c]]
        for r in range(n):
            if r != c and M[r][c] != 0.0:
                f = M[r][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n] for i in range(n)], [M[i][n + 1:] for i in range(n)]


def fit_circular(t, v, s, P):
    """Weighted fit v = g + a cos(2 pi t/P) + b sin(2 pi t/P) at fixed P.
    K = sqrt(a^2 + b^2); sigma_K from the covariance, scaled by sqrt(chi2_red) when
    chi2_red > 1 (never shrunk). Returns dict or None (fewer than 4 points / singular)."""
    pts = [(ti, vi, si) for ti, vi, si in zip(t, v, s)
           if math.isfinite(ti) and math.isfinite(vi) and si > 0]
    n = len(pts)
    if n < 4 or not (P > 0):
        return None
    A = [[0.0] * 3 for _ in range(3)]
    y = [0.0] * 3
    rows = []
    for ti, vi, si in pts:
        ph = 2.0 * math.pi * ti / P
        x = (1.0, math.cos(ph), math.sin(ph))
        w = 1.0 / (si * si)
        rows.append((x, vi, w))
        for i in range(3):
            y[i] += w * x[i] * vi
            for j in range(3):
                A[i][j] += w * x[i] * x[j]
    sol, cov = _solve3(A, y)
    if sol is None:
        return None
    g, a, b = sol
    chi2 = sum(w * (vi - sum(p * q for p, q in zip(x, sol))) ** 2 for x, vi, w in rows)
    chi2r = chi2 / (n - 3) if n > 3 else float("nan")
    scale = max(1.0, chi2r) if math.isfinite(chi2r) else 1.0
    K = math.hypot(a, b)
    if K > 0:
        varK = (a * a * cov[1][1] + b * b * cov[2][2] + 2 * a * b * cov[1][2]) / (K * K)
    else:
        varK = 0.5 * (cov[1][1] + cov[2][2])
    sK = math.sqrt(max(varK, 0.0) * scale)
    return {"n": n, "gamma": g, "K": K, "sK": sK, "chi2_red": chi2r}


def epoch_label(fit, K3, sK3):
    """EPOCH_OK (K/sK >= 5 and within 3 combined sigma of K3), EPOCH_DIFF (>= 5 but not
    consistent), EPOCH_WEAK (3 <= K/sK < 5), EPOCH_FLAT (< 3), EPOCH_NOFIT."""
    if not fit or not (fit["sK"] > 0):
        return "EPOCH_NOFIT"
    snr = fit["K"] / fit["sK"]
    if snr < 3.0:
        return "EPOCH_FLAT"
    if snr < 5.0:
        return "EPOCH_WEAK"
    comb = math.sqrt(fit["sK"] ** 2 + fnum(sK3, 0.0) ** 2)
    return "EPOCH_OK" if abs(fit["K"] - K3) <= 3.0 * comb else "EPOCH_DIFF"


def wilson(k, n, z=1.959964):
    if n <= 0:
        return [None, None]
    p = k / float(n)
    den = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4.0 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def frac(recs):
    """f_conf = CONFIRMED / testable with its Wilson 95 % interval."""
    test = [r for r in recs if r["label"] != "UNTESTABLE"]
    k = sum(1 for r in test if r["label"] == "CONFIRMED")
    n = len(test)
    return {"n_testable": n, "n_confirmed": k, "f_conf": (k / float(n)) if n else None,
            "ci95": wilson(k, n)}


def grade_tables(recs, n_pool):
    """R0, D1, D2, D4 (prereg table), from the per-source records."""
    g = {}
    allf = frac(recs)
    nt = allf["n_testable"]
    g["R0"] = {"prediction": ">= 70% of S3 testable", "value": [nt, n_pool],
               "pass": (nt >= 0.7 * n_pool) if n_pool else None}
    up = allf["ci95"][1]
    g["D1"] = {"prediction": "f_conf upper 95% < 0.8", "value": allf,
               "pass": (up < 0.8) if up is not None else None}
    hi = frac([r for r in recs if r["K3"] >= K_SPLIT])
    lo = frac([r for r in recs if r["K3"] < K_SPLIT])
    ok = hi["f_conf"] is not None and lo["f_conf"] is not None
    g["D2"] = {"prediction": "f_conf(K3 >= 3 km/s) > f_conf(K3 < 3 km/s), 95% intervals not "
               "overlapping", "value": {"K3>=3": hi, "K3<3": lo},
               "pass": (hi["f_conf"] > lo["f_conf"] and hi["ci95"][0] > lo["ci95"][1])
               if ok else None}
    hot = frac([r for r in recs if r["m1"] >= 1.5])
    cool = frac([r for r in recs if r["m1"] < 1.2])
    ok = hot["f_conf"] is not None and cool["f_conf"] is not None
    g["D4"] = {"prediction": "(exploratory) f_conf(m1 >= 1.5) < f_conf(m1 < 1.2)",
               "value": {"m1>=1.5": hot, "m1<1.2": cool},
               "pass": (hot["f_conf"] < cool["f_conf"]) if ok else None}
    return g


def grade_d3(recs, star_rows, rate_summary, rho_dr3, key="rho_substellar_size"):
    """D3: rho over CONFIRMED stars vs rho over all S3 stars in the same sb1_robust rows.
    Pass: rho_conf > rho_all and rho_conf's lower 95 % bound > rho_DR3 (the 0.2.0 point
    estimate). rate_summary is sb1_transit.rate_summary (passed in, so tests stay stdlib)."""
    conf = {r["source_id"] for r in recs if r["label"] == "CONFIRMED"}
    seen, rows = set(), []
    for r in star_rows:                       # dedupe by source_id (first occurrence)
        sid = str(r.get("source_id", "")).strip()
        if sid and sid not in seen and not r.get("control"):
            seen.add(sid)
            rows.append(r)
    s_all = rate_summary(rows)
    s_conf = rate_summary([r for r in rows if str(r.get("source_id")).strip() in conf])
    rc, ra = s_conf.get(key), s_all.get(key)
    lo = (s_conf.get(key + "_ci95") or [None])[0]
    ok = all(x is not None and math.isfinite(x) for x in (rc, ra, lo, rho_dr3))
    return {"prediction": "rho_conf > rho_all and rho_conf lower 95% > rho_DR3",
            "key": key, "rho_conf": rc, "rho_conf_ci95": s_conf.get(key + "_ci95"),
            "rho_all": ra, "rho_dr3": rho_dr3, "n_rate_conf": s_conf.get("n_rate_sample"),
            "n_rate_all": s_all.get("n_rate_sample"),
            "pass": (rc > ra and lo > rho_dr3) if ok else None}


def reading(g):
    """The pre-registered reading of D1 and D3."""
    d1, d3 = g.get("D1", {}).get("pass"), (g.get("D3") or {}).get("pass")
    if d1 is False:
        return "D1 fails: most DR3 orbits are real; small rho is (N) or a fault in the TESS test"
    if d1 and d3:
        return "D1 and D3 pass: explanation (S), spurious orbits (check rho_conf ~ 1)"
    if d1 and d3 is False:
        return "D1 passes, D3 fails: explanation (N), real periods, companions not small dark bodies"
    return "not yet decidable (D3 needs the TESS grade)"


# ================================================================== DataLink
def _http(url, data=None, timeout=300, tries=4):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data,
                                         headers={"User-Agent": "mv2-gaia-orbit-transits"})
            with urllib.request.urlopen(req, timeout=timeout) as fh:
                return fh.read()
        except Exception as exc:
            last = exc
            time.sleep(10 * (k + 1))
    raise df.TapError("DataLink failed after %d tries: %s" % (tries, last))


def link_types(release, sid, http=_http):
    """RETRIEVAL_TYPE values the links service lists for one source."""
    q = urllib.parse.urlencode({"ID": "%s %s" % (release, sid)})
    txt = http(LINKS_URL + "?" + q).decode("utf-8", "replace")
    return sorted(set(re.findall(r"RETRIEVAL_TYPE=([A-Za-z0-9_]+)", txt))), txt[:2000]


def choose_rv_type(types, override=None):
    """(type or None, reason). Unique regex match, or the override if it is listed."""
    if override:
        return (override, "override") if override in types else (None, "override not listed")
    m = [t for t in types if RV_TYPE_RE.search(t)]
    if len(m) == 1:
        return m[0], "unique match"
    return None, ("no epoch-RV type" if not m else "ambiguous: %s" % m)


def _members(blob):
    """(name, text) for every file in a DataLink answer: zip, tar(.gz), gzip or plain."""
    if blob[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(blob))
        for n in z.namelist():
            if not n.endswith("/"):
                yield from _members_named(n, z.read(n))
        return
    if blob[:2] == b"\x1f\x8b":
        raw = gzip.decompress(blob)
        try:
            t = tarfile.open(fileobj=io.BytesIO(raw))
            for m in t.getmembers():
                if m.isfile():
                    yield from _members_named(m.name, t.extractfile(m).read())
            return
        except tarfile.TarError:
            yield from _members_named("data", raw)
            return
    yield "data", blob.decode("utf-8", "replace")


def _members_named(name, data):
    if data[:2] in (b"PK", b"\x1f\x8b"):
        yield from _members(data)
    else:
        yield name, data.decode("utf-8", "replace")


def parse_table_text(text):
    """CSV or ECSV text -> list of dict rows (ECSV '#' header lines skipped)."""
    head = text.lstrip()[:200].lower()
    if head.startswith("<"):
        raise df.TapError("DataLink returned XML/HTML: " + text.strip()[:300])
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    return list(csv.DictReader(io.StringIO("\n".join(lines))))


def fetch_epoch_rows(release, rtype, ids, http=_http):
    """{source_id: [rows]} for a batch (<= EPOCH_BATCH ids). Rows lacking source_id
    raise EpochSchemaError."""
    if len(ids) > EPOCH_BATCH:
        raise ValueError("batch too large")
    data = urllib.parse.urlencode({"RETRIEVAL_TYPE": rtype, "ID": ",".join(map(str, ids)),
                                   "RELEASE": release, "FORMAT": "CSV",
                                   "VALID_DATA": "false"}).encode()
    out = {}
    for name, text in _members(http(DATA_URL, data=data)):
        rows = parse_table_text(text)
        for r in rows:
            r = {str(k).strip().lower(): v for k, v in r.items() if k is not None}
            sid = str(r.get("source_id", "")).strip()
            if not sid:
                raise EpochSchemaError("no source_id column in %s" % name, list(r.keys()))
            out.setdefault(sid, []).append(r)
    return out


# ================================================================== S3 (DR3) sample
def query_s3(st, query=df.tap_query):
    """sb1_robust 0.2.0's query_sample (same ADQL, no fallback) + sb1_transit eligibility."""
    rows = []
    for lo, hi in zip(P_EDGES[:-1], P_EDGES[1:]):
        where = ("WHERE o.nss_solution_type IN ('SB1','SB1C') AND o.period >= %g AND "
                 "o.period < %g AND s.phot_g_mean_mag <= %g AND o.semi_amplitude_primary*"
                 "o.semi_amplitude_primary*o.semi_amplitude_primary*o.period < %g"
                 % (lo, hi, st.G_MAX, st.KP_SERVER_MAX))
        rows += query("SELECT " + st.COLS + st.AP_COLS + " " + st.FROM + st.AP_JOIN + " " + where,
                      timeout=300)
    pool, why = [], {}
    for r in rows:
        ph = st.star_physics(r)
        ok, reason = st.eligible(r, ph)
        if ok:
            pool.append((r, ph))
        else:
            why[reason] = why.get(reason, 0) + 1
    return rows, pool, why


def dr3_record(r, ph):
    return {"source_id": str(r["source_id"]).strip(), "P3": ph["P"],
            "sP3": fnum(r.get("period_error")), "K3": ph["K"],
            "sK3": fnum(r.get("semi_amplitude_primary_error")), "m1": ph["m1"],
            "m2sini": ph["m2sini"], "G": fnum(r.get("phot_g_mean_mag")),
            "type3": str(r.get("nss_solution_type", "")).strip()}


# ================================================================== main
RVS_ORBIT = {"dr4": "gaiadr4.rvs_two_body_orbit", "dr3": None}


def rvs_table_ok(have):
    """An extra orbit table is usable only with source_id, period and a semi-amplitude
    (semi_amplitude_primary, or c_ and h_thiele_innes)."""
    return ("source_id" in have and "period" in have and
            ("semi_amplitude_primary" in have or
             ("c_thiele_innes" in have and "h_thiele_innes" in have)))


def check_nss_schema(schema, query=df.tap_query):
    """Every table/column the rules use. An orbit table that EXISTS but lacks the columns
    to read P and K stops the run (its orbits would otherwise be silently lost)."""
    s = df.SCHEMAS[schema]
    found, missing = {}, []
    need = {s["nss"]: SB1_REQUIRED}
    if schema != "dr3":
        need[s["xmatch"]] = (s["xmatch_new_id"], s["xmatch_old_id"]) + df.XMATCH_COLS
    for table, cols in need.items():
        have = df.table_columns(table, query)
        found[table] = have
        missing += ["%s.%s" % (table, c) for c in cols if c not in have]
    for extra in (RVS_ORBIT.get(schema), s.get("nss_supp")):
        if not extra:
            continue
        have = df.table_columns(extra, query)
        found[extra] = have
        if have and not rvs_table_ok(have):
            missing.append("%s.(source_id, period, semi_amplitude_primary or C/H)" % extra)
    if missing:
        raise df.SchemaError("missing: " + ", ".join(missing),
                             {t: sorted(c) for t, c in found.items()})
    return found


def fetch_rv_orbits(schema, new_ids, found, query=df.tap_query):
    s = df.SCHEMAS[schema]
    out = {}
    tables = [s["nss"]] + [t for t in (RVS_ORBIT.get(schema), s.get("nss_supp"))
                           if t and found.get(t)]
    for table in tables:
        have = found.get(table, {})
        cols = [c for c in SB1_REQUIRED + SB1_OPTIONAL if c in have]
        if "source_id" not in cols or "period" not in cols:
            continue
        for ch in df.chunks([i for i in new_ids if i]):
            for r in query(df.adql_nss(table, ch, cols)):
                r["_table"] = table
                out.setdefault(str(r.get("source_id", "")).strip(), []).append(r)
    return out


def _write_csv(path, rows):
    keys = sorted({k for r in rows for k in r}) if rows else ["source_id"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    return o


def _dump(path, obj):
    with open(path, "w") as fh:
        json.dump(_clean(obj), fh, indent=1)


def epoch_step(schema, recs, new_id, args, out_dir, http=_http):
    """Discover the epoch-RV type, fetch, count and fit. Returns (active, info).
    Raises RvTypeError when the type is not uniquely identified (dr4)."""
    release = RELEASE[schema]
    probe = next((new_id[r["source_id"]] for r in recs if new_id.get(r["source_id"])), None)
    info = {"release": release, "probe": probe}
    if probe is None:
        info["status"] = "no matched source"
        return False, info
    try:
        types, head = link_types(release, probe, http)
    except df.TapError as exc:
        if schema != "dr3":
            raise
        types, head = [], "error: %r" % (exc,)
    info.update({"link_types": types, "links_head": head})
    if schema == "dr3":
        # Rehearsal: DR3 has no epoch RVs. Smoke-test the data endpoint on epoch photometry.
        ids = [new_id[r["source_id"]] for r in recs[:3] if new_id.get(r["source_id"])]
        try:
            got = fetch_epoch_rows(release, "EPOCH_PHOTOMETRY", ids, http)
            info["smoke"] = {"ids": ids, "rows": {k: len(v) for k, v in got.items()},
                             "columns": sorted(next(iter(got.values()))[0].keys()) if got else []}
        except (df.TapError, EpochSchemaError, ValueError, zipfile.BadZipFile) as exc:
            info["smoke"] = {"ids": ids, "error": repr(exc),
                             "columns": getattr(exc, "columns", [])}
        info["status"] = "suspended (DR3 has no epoch RVs; rehearsal)"
        return False, info
    if args.suspend_epochs:
        info["status"] = "suspended by --suspend-epochs (amendment 1 rule 4)"
        return False, info
    rtype, why = choose_rv_type(types, args.retrieval_type)
    info.update({"retrieval_type": rtype, "why": why})
    if rtype is None:
        _dump(os.path.join(out_dir, "datalink_found.json"), info)
        raise RvTypeError("DataLink epoch-RV type not identified: %s %s" % (why, types))
    by_new = {}
    for r in recs:
        if new_id.get(r["source_id"]):
            by_new.setdefault(new_id[r["source_id"]], []).append(r)
    time_col, n_batches = None, 0
    for ch in df.chunks(sorted(by_new), EPOCH_BATCH):
        got = fetch_epoch_rows(release, rtype, ch, http)
        n_batches += 1
        for sid, rows in got.items():
            cols = list(rows[0].keys())
            miss = [c for c in EPOCH_REQUIRED if c not in cols]
            if miss:
                raise EpochSchemaError("epoch columns missing: %s" % miss, cols)
            time_col = time_col or pick_time_col(cols, args.time_col)
            info.setdefault("columns", cols)
            for r in by_new.get(sid, []):
                use = [x for x in rows if epoch_counts(x)]
                r["n_epochs_all"] = len(rows)
                r["n_epochs"] = len(use)
                fit = fit_circular([fnum(x.get(time_col)) for x in use],
                                   [fnum(x.get("radial_velocity")) for x in use],
                                   [fnum(x.get("radial_velocity_error")) for x in use],
                                   r["P3"])
                r["epoch_K"] = fit["K"] if fit else None
                r["epoch_sK"] = fit["sK"] if fit else None
                r["epoch_chi2_red"] = fit["chi2_red"] if fit else None
                r["epoch_label"] = epoch_label(fit, r["K3"], r["sK3"])
        time.sleep(1.0)
    for r in recs:
        r.setdefault("n_epochs", 0)
    info.update({"status": "active", "time_col": time_col, "batches": n_batches})
    return True, info


def run(args, query=df.tap_query, http=_http):
    import sb1_transit as st
    out = args.out_dir
    os.makedirs(out, exist_ok=True)
    summ = {"version": VERSION, "schema": args.schema, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        rows, pool, why = query_s3(st, query)
    except df.TapError as exc:
        print("archive unavailable (S3 query):", exc)
        return 2
    summ.update({"gaia_rows": len(rows), "pool": len(pool), "rejected": why,
                 "expected_pool": EXPECTED_POOL})
    if len(pool) != EXPECTED_POOL and not args.allow_pool_change:
        _dump(os.path.join(out, "sb1_reality_summary.json"), summ)
        print("S3 pool not reproduced: %d vs %d" % (len(pool), EXPECTED_POOL))
        return 3
    recs = [dr3_record(r, ph) for r, ph in pool]
    if args.max_sources:
        recs = recs[:args.max_sources]
    try:
        found = check_nss_schema(args.schema, query)
    except df.SchemaError as exc:
        _dump(os.path.join(out, "schema_found.json"), exc.found)
        print("schema mismatch:", exc)
        return 4
    except df.TapError as exc:
        print("archive unavailable (schema):", exc)
        return 2
    _dump(os.path.join(out, "schema_found.json"),
          {t: sorted(c) for t, c in found.items()})
    s = df.SCHEMAS[args.schema]
    unit = found.get(s["xmatch"], {}).get("angular_distance", {}).get("unit", "mas") \
        if args.schema != "dr3" else "mas"
    try:
        matches, _ = df.fetch_matches(args.schema, [r["source_id"] for r in recs], unit, query)
        new_id = {o: n for o, (n, stt) in matches.items() if stt == "ok"}
        orbits = fetch_rv_orbits(args.schema, sorted(set(new_id.values())), found, query)
    except df.TapError as exc:
        print("archive unavailable (match/orbits):", exc)
        return 2
    for r in recs:
        m = matches.get(r["source_id"], (None, "none"))
        r["match_status"] = m[1]
        r["new_id"] = m[0] or ""
        o, n_rv, from_supp = pick_rv(orbits.get(m[0] or "", []))
        r["n_rv_rows"] = n_rv
        r["from_supp"] = from_supp
        if o:
            r.update({"P4": o["P"], "sP4": o["sP"], "K4": o["K"], "sK4": o["sK"],
                      "K4_src": o["K_src"], "type4": o["type"], "table4": o["table"]})
            r["orbit_label"] = orbit_label({"P": r["P3"], "sP": r["sP3"], "K": r["K3"], "sK": r["sK3"]}, o)
        else:
            r["orbit_label"] = ""
    try:
        active, dl = epoch_step(args.schema, recs, new_id, args, out, http)
    except RvTypeError as exc:
        print(exc)
        return 6
    except EpochSchemaError as exc:
        _dump(os.path.join(out, "datalink_found.json"), {"error": str(exc), "columns": exc.columns})
        print("epoch schema mismatch:", exc)
        return 4
    except df.TapError as exc:
        print("DataLink unavailable:", exc)
        return 2
    _dump(os.path.join(out, "datalink_found.json"), dl)
    for r in recs:
        r["label"] = source_label(r["match_status"], r["orbit_label"], r.get("n_epochs"), active)
    g = grade_tables(recs, len(recs))
    counts = {k: sum(1 for r in recs if r["label"] == k) for k in LABELS}
    summ.update({"n_sources": len(recs), "labels": counts, "epochs_active": active,
                 "match_status": {k: sum(1 for r in recs if r["match_status"] == k)
                                  for k in ("ok", "none", "ambiguous")},
                 "from_supp": sum(1 for r in recs if r["from_supp"]),
                 "orbit_table": {t: sum(1 for r in recs if r.get("table4") == t)
                                 for t in sorted({r.get("table4") for r in recs if r.get("table4")})},
                 "k_from_ch": sum(1 for r in recs if r.get("K4_src") == "thiele_innes_CH"),
                 "grades": g, "reading": reading(g)})
    if active:
        summ["epoch_labels"] = {}
        for r in recs:
            if r.get("epoch_label"):
                summ["epoch_labels"][r["epoch_label"]] = summ["epoch_labels"].get(r["epoch_label"], 0) + 1
        summ["table_vs_epoch"] = {"CONFIRMED_but_FLAT": sum(1 for r in recs if r["label"] == "CONFIRMED"
                                                            and r.get("epoch_label") == "EPOCH_FLAT"),
                                  "DROPPED_but_OK": sum(1 for r in recs if r["label"] == "DROPPED"
                                                        and r.get("epoch_label") == "EPOCH_OK")}
    if args.schema == "dr3":
        sm = dl.get("smoke", {})
        summ["rehearsal"] = {
            "RH1_pool_reproduced": len(pool) == EXPECTED_POOL,
            "RH2_all_matched": summ["match_status"]["ok"] == len(recs),
            "RH3_all_confirmed": counts["CONFIRMED"] == len(recs),
            "RH4_datalink_plumbing": bool(dl.get("link_types")) and len(sm.get("rows", {})) >= 1
            and "source_id" in sm.get("columns", [])}
    _write_csv(os.path.join(out, "sb1_reality_records.csv"), recs)
    with open(os.path.join(out, "confirmed_ids.txt"), "w") as fh:
        fh.write("\n".join(r["source_id"] for r in recs if r["label"] == "CONFIRMED") + "\n")
    summ["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _dump(os.path.join(out, "sb1_reality_summary.json"), summ)
    with open(os.path.join(out, "sb1_reality_report.md"), "w") as fh:
        fh.write("# dr4_sb1_reality %s (%s)\n\n" % (VERSION, args.schema))
        fh.write("S3 pool %d (expected %d); sources %d\n\n" % (len(pool), EXPECTED_POOL, len(recs)))
        fh.write("| label | n |\n|---|---|\n" + "".join("| %s | %d |\n" % kv for kv in counts.items()))
        fh.write("\nEpoch step: %s\n\n" % dl.get("status"))
        for k, v in g.items():
            fh.write("- **%s** %s: pass = %s\n" % (k, v["prediction"], v["pass"]))
        fh.write("\nReading: %s\n" % summ["reading"])
        if "rehearsal" in summ:
            fh.write("\nRehearsal: %s\n" % json.dumps(summ["rehearsal"]))
    print(json.dumps(_clean({k: summ.get(k) for k in ("pool", "labels", "epochs_active", "rehearsal",
                                                       "reading")})))
    return 0


def run_grade_tess(args):
    """D3 from sb1_robust chunk outputs and a finished run's records."""
    import sb1_transit as st
    import sb1_robust as sr
    with open(args.records, newline="") as fh:
        recs = list(csv.DictReader(fh))
    rows = []
    for p in args.sb1_stars:
        rows += sr.star_rows(p)
    d3 = grade_d3(recs, rows, st.rate_summary, args.rho_dr3)
    _dump(os.path.join(args.out_dir, "d3_grade.json"), d3)
    print(json.dumps(_clean(d3)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--schema", choices=("dr3", "dr4"), required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--retrieval-type", default=None)
    r.add_argument("--time-col", default=None)
    r.add_argument("--suspend-epochs", action="store_true")
    r.add_argument("--allow-pool-change", action="store_true")
    r.add_argument("--max-sources", type=int, default=0)
    t = sub.add_parser("grade-tess")
    t.add_argument("--records", required=True)
    t.add_argument("--sb1-stars", nargs="+", required=True)
    t.add_argument("--rho-dr3", type=float, required=True)
    t.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return run(a)
    if a.cmd == "grade-tess":
        os.makedirs(a.out_dir, exist_ok=True)
        return run_grade_tess(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
