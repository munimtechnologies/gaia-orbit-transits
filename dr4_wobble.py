# SPDX-License-Identifier: Apache-2.0
"""dr4_wobble.py 0.1.0 -- photocentre wobble at the Gaia DR3 period in Gaia DR4 epoch astrometry.

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents working in his name;
not yet checked by a human expert). Apache-2.0.

Implements findings/2026-11-19-dr4-wobble-prereg.md (+ amendment 1, 2026-11-19):
for each target, fit DR4 along-scan (AL) epoch astrometry with
  single-star model : [sin t, cos t, parallax_factor_al, T*sin t, T*cos t] (+ colour_factor_al)
  orbit model       : single + [X sin t, Y sin t, X cos t, Y cos t]  -> (B, G, A, F)
where t = scan_pos_angle, T = Julian years from J2017.5 (TCB), X = cos E - e,
Y = sqrt(1-e^2) sin E, E from the DR3 P, e, t_periastron (held fixed).
Detected = dchi2 > 30; edge-on = |cos i| - 2 sigma(cos i) <= 0.2.

Conventions follow ESA's gaia-supdate (github.com/esa/gaia-supdate, read 2026-11-19):
T [yr] = 2010.0 + (obs_time_tcb + obs_time_bary_corr)[ns] / (365.25 d) - 2017.5;
dependent variable centroid_pos_al [mas]; AGIS excess noise added in quadrature.

The numerical core is standard-library Python (no numpy) so the tests run anywhere.
Reading the VOTable pre-release file needs astropy (imported only there).

Modes:
  rehearse : ESA's 12-source DR4 pre-release (zip of XML). Pass = HD 114762 dchi2 > 30 at
             its DR3 orbit and all three QSOs dchi2 < 30 at that same orbit. Exit 2 if not.
  release  : the 162 calib-window targets on Gaia DR4 release day (needs dr4_fetch.py).
Exit codes: 0 ok, 2 rehearsal failed, 3 no data / download failed, 4 schema problem,
            6 DataLink refused the retrieval type or release name.
"""
import argparse
import csv
import io
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

VERSION = "0.1.0"

# --- pre-registered constants (findings/2026-11-19-dr4-wobble-prereg.md) ---
DCHI2_DET = 30.0
EDGE_COS = 0.2
N_DRAWS = 300
N_BOOT = 10000
SEED = 20261202
W0_MIN = 0.80
W1_MAX = 0.60
W2_MIN = 0.85
W3_FACTOR = 0.6

# --- time conventions (gaia-supdate constants.py) ---
JYEAR_TCB0 = 2010.0              # 2010-01-01T00:00:00 TCB as a Julian year
JD_TCB0 = 2455197.5
REF_JYEAR = 2017.5               # DR4 reference epoch (TCB)
NS_PER_DAY = 86400.0e9
NS_PER_JYEAR = 365.25 * NS_PER_DAY
JD_J2016 = 2457389.0             # DR3 t_periastron is in days from J2016.0
MIN_TRANSITS = 15

REQUIRED = ("obs_time_tcb", "obs_time_bary_corr", "scan_pos_angle", "parallax_factor_al",
            "colour_factor_al", "centroid_pos_al", "centroid_pos_error_al", "used_by_agis_al",
            "agis_source_excess_noise")
# Amendment 1: transit_id is required only when rows are per CCD (exploded layout).

PRERELEASE_URL = ("https://anonftp.cosmos.esa.int/pub/GAIA_PUBLIC_DATA/Gaia_DR4/dr4-prerelease/"
                  "gaia-dr4-prerelease-epoch-astrometry_2026-06-26.zip")
# Fallback: the same VOTable, committed unmodified by EXOZIPPy (merge 722a880, 2026-11-04).
PRERELEASE_MIRROR = ("https://raw.githubusercontent.com/jdeast/EXOZIPPy/"
                     "722a880aa7cb8598767bfc8d9ad3ed95a71c3026/examples/GaiaBH3/"
                     "GAIA_DR4_PRERELEASE_EPOCH_ASTROMETRY_RAW.xml")
DATALINK_URL ="https://gea.esac.esa.int/data-server/data"
HD114762 = "3937211745905473024"
QSOS = ("2237987199365376", "60730287810150016", "10973744521070720")
PRERELEASE_GROUPS = {
    "4181040337841125632": "parallax", "3926186255616949504": "parallax",
    "435469040545191680": "parallax", "1663617687609809280": "magnitude",
    "2309425390592896": "magnitude", "20694084440761600": "magnitude",
    "2237987199365376": "qso", "60730287810150016": "qso", "10973744521070720": "qso",
    "3937211745905473024": "orbit", "1457486023639239296": "orbit",
    "4318465066420528000": "orbit"}


class SchemaError(RuntimeError):
    pass


class LinAlgError(RuntimeError):
    pass


# ------------------------------------------------------------------ small helpers
def fnum(x, default=float("nan")):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def is_true(x):
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return x == 1
    return str(x).strip().lower() in ("true", "t", "1")


def parse_cell(s):
    """A DataLink CSV cell -> python value. '(a, b, ...)' -> list; numbers -> float."""
    if s is None:
        return None
    t = str(s).strip()
    if t.startswith("(") and t.endswith(")") or t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        if not inner:
            return []
        return [parse_cell(p) for p in inner.split(",")]
    tl = t.lower()
    if tl in ("true", "false"):
        return tl == "true"
    if t == "":
        return None
    try:
        return float(t)
    except ValueError:
        return t


def read_csv_rows(text):
    """ESA DataLink CSV (arrays as '(a, b, ...)') -> list of dicts. Duplicate column names
    keep the FIRST occurrence under the plain name, later ones get '.1', '.2'."""
    lines = [ln for ln in text.splitlines() if not ln.startswith("#")]
    rdr = csv.reader(io.StringIO("\n".join(lines)))
    header = next(rdr)
    names, seen = [], {}
    for h in header:
        h = h.strip()
        if h in seen:
            seen[h] += 1
            names.append(f"{h}.{seen[h]}")
        else:
            seen[h] = 0
            names.append(h)
    keep = ("source_id", "transit_id")
    return [{n: (v.strip() if n in keep else parse_cell(v)) for n, v in zip(names, row)}
            for row in rdr if row]


def _py(v):
    """numpy / masked values -> plain python (masked -> None)."""
    try:
        import numpy as np
    except ImportError:          # pragma: no cover
        return v
    if v is np.ma.masked:
        return None
    if isinstance(v, np.ma.MaskedArray):
        mask = np.ma.getmaskarray(v)
        data = v.data.tolist()
        return [None if m else d for d, m in zip(data, mask.tolist())]
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, bytes):
        return v.decode()
    return v


def read_votable_rows(fileobj, report=None):
    """VOTable (XML) -> list of dicts; field names/units/arraysizes go into report."""
    from astropy.io.votable import parse
    vot = parse(fileobj, verify="warn")
    rows = []
    for k, tab in enumerate(vot.iter_tables()):
        if report is not None:
            report.setdefault("tables", []).append({
                "index": k, "name": str(tab.name), "nrows": int(tab.array.shape[0]),
                "fields": [{"name": f.name, "unit": str(f.unit) if f.unit else "",
                            "datatype": f.datatype, "arraysize": f.arraysize,
                            "ucd": f.ucd or ""} for f in tab.fields],
                "params": [{"name": p.name, "value": str(p.value)[:80]} for p in tab.params]})
            for info in list(getattr(vot, "infos", []))[:20]:
                report.setdefault("infos", []).append(f"{info.name}={str(info.value)[:120]}")
            for ts in list(getattr(vot, "timesys", []) or [])[:5]:
                report.setdefault("timesys", []).append(
                    {"ID": ts.ID, "timescale": ts.timescale, "timeorigin": str(ts.timeorigin),
                     "refposition": ts.refposition})
        arr = tab.array
        names = arr.dtype.names
        for i in range(arr.shape[0]):
            rec = arr[i]
            rows.append({n: _py(rec[n]) for n in names})
    return rows


def rows_from_bytes(name, data, report=None):
    low = name.lower()
    if data[:2] == b"PK":
        out = []
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for m in zf.namelist():
                if m.endswith("/"):
                    continue
                if report is not None:
                    report.setdefault("zip_members", []).append(m)
                out += rows_from_bytes(m, zf.read(m), report)
        return out
    if low.endswith((".xml", ".vot", ".votable")) or data.lstrip()[:5] in (b"<?xml", b"<VOTA"):
        return read_votable_rows(io.BytesIO(data), report)
    if low.endswith((".csv", ".ecsv")):
        return read_csv_rows(data.decode("utf-8", "replace"))
    if report is not None:
        report.setdefault("skipped_members", []).append(name)
    return []


# ------------------------------------------------------------------ rows -> transits
def _at(v, k):
    if isinstance(v, list):
        return v[k] if k < len(v) else None
    return v


def check_columns(rows):
    have = set()
    for r in rows[:50]:
        have |= set(r.keys())
    missing = [c for c in REQUIRED if c not in have]
    if missing:
        raise SchemaError(f"missing epoch-astrometry columns: {missing}; found {sorted(have)}")
    return sorted(have)


def to_transits(rows):
    """Rows (per-transit with per-CCD arrays, or exploded per CCD) -> {source_id: [transit]}.

    transit = dict(t_ns, theta, pf, colour, w, sigma, n_ccd, excess). Only CCDs with
    used_by_agis_al true, a finite centroid, a positive finite error and a time > 0 are used.
    Each transit's CCDs are combined into one weighted mean (sigma = combined formal error).
    """
    check_columns(rows)
    per_transit = any(isinstance(r.get("obs_time_tcb"), list) for r in rows[:50])
    groups = []
    if per_transit:
        groups = [[(r, k) for k in range(len(r["obs_time_tcb"])
                                         if isinstance(r.get("obs_time_tcb"), list) else 0)]
                  for r in rows]
    else:
        if not any("transit_id" in r for r in rows[:50]):
            raise SchemaError("per-CCD rows without transit_id: cannot form transits")
        by = {}
        for r in rows:
            by.setdefault((str(r.get("source_id")), str(r.get("transit_id"))), []).append((r, None))
        groups = list(by.values())
    out = {}
    for g in groups:
        sw = swy = st = ss = sc = spf = scol = 0.0
        n = ncol = 0
        sid = None
        excess = float("nan")
        for r, k in g:
            sid = str(r.get("source_id", "?")).strip()
            get = (lambda c: _at(r.get(c), k)) if k is not None else (lambda c: r.get(c))
            used = get("used_by_agis_al")
            t = fnum(get("obs_time_tcb"))
            w = fnum(get("centroid_pos_al"))
            e = fnum(get("centroid_pos_error_al"))
            th = fnum(get("scan_pos_angle"))
            bc = fnum(get("obs_time_bary_corr"))
            pf = fnum(get("parallax_factor_al"))
            if not (is_true(used) and math.isfinite(t) and t > 0 and math.isfinite(w)
                    and math.isfinite(e) and e > 0 and math.isfinite(th) and math.isfinite(bc)
                    and math.isfinite(pf)):
                continue
            wt = 1.0 / (e * e)
            sw += wt
            swy += wt * w
            st += t + bc
            ss += math.sin(math.radians(th))
            sc += math.cos(math.radians(th))
            spf += pf
            n += 1
            col = fnum(get("colour_factor_al"))     # scalar (DataLink CSV) or per CCD (VOTable)
            if math.isfinite(col):
                scol += col
                ncol += 1
            excess = fnum(get("agis_source_excess_noise"), 0.0)
        if n == 0:
            continue
        out.setdefault(sid, []).append({
            "t_ns": st / n, "theta": math.degrees(math.atan2(ss, sc)), "pf": spf / n,
            "colour": scol / ncol if ncol == n else float("nan"), "w": swy / sw,
            "sigma": math.sqrt(1.0 / sw), "n_ccd": n, "excess": excess})
    for sid in out:
        out[sid].sort(key=lambda d: d["t_ns"])
    return out


def t_years(t_ns):
    """Julian years from J2017.5 (TCB)."""
    return JYEAR_TCB0 + t_ns / NS_PER_JYEAR - REF_JYEAR


def t_dr3_days(t_ns):
    """Days from J2016.0 (DR3 t_periastron zero point). TCB vs TDB (~20 s) is ignored."""
    return JD_TCB0 + t_ns / NS_PER_DAY - JD_J2016


# ------------------------------------------------------------------ orbit geometry
def kepler_E(M, e, tol=1e-12):
    M = math.fmod(M, 2 * math.pi)
    E = M if e < 0.8 else math.pi
    for _ in range(100):
        f = E - e * math.sin(E) - M
        d = f / (1 - e * math.cos(E))
        E -= d
        if abs(d) < tol:
            break
    return E


def xy_elliptic(t_days, P, e, tp):
    E = kepler_E(2 * math.pi * (t_days - tp) / P, e)
    return math.cos(E) - e, math.sqrt(1 - e * e) * math.sin(E)


def campbell_to_ti(a, i_deg, omega_deg, Omega_deg):
    """(A, B, F, G) from a, i, omega, Omega (standard Thiele-Innes)."""
    i, w, W = (math.radians(x) for x in (i_deg, omega_deg, Omega_deg))
    A = a * (math.cos(w) * math.cos(W) - math.sin(w) * math.sin(W) * math.cos(i))
    B = a * (math.cos(w) * math.sin(W) + math.sin(w) * math.cos(W) * math.cos(i))
    F = a * (-math.sin(w) * math.cos(W) - math.cos(w) * math.sin(W) * math.cos(i))
    G = a * (-math.sin(w) * math.sin(W) + math.cos(w) * math.cos(W) * math.cos(i))
    return A, B, F, G


def ti_to_a_cosi(A, B, F, G):
    """Standard inversion: u = (A^2+B^2+F^2+G^2)/2, v = AG - BF; a^2 = u + sqrt(u^2 - v^2);
    cos i = v / a^2."""
    u = 0.5 * (A * A + B * B + F * F + G * G)
    v = A * G - B * F
    a2 = u + math.sqrt(max(u * u - v * v, 0.0))
    if a2 <= 0:
        return 0.0, float("nan")
    return math.sqrt(a2), max(-1.0, min(1.0, v / a2))


# ------------------------------------------------------------------ linear algebra
def cholesky(M):
    n = len(M)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = M[i][j] - sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                if s <= 1e-14 * max(abs(M[i][i]), 1e-300):
                    raise LinAlgError(f"matrix not positive definite at {i}")
                L[i][i] = math.sqrt(s)
            else:
                L[i][j] = s / L[j][j]
    return L


def chol_solve(L, b):
    n = len(L)
    y = [0.0] * n
    for i in range(n):
        y[i] = (b[i] - sum(L[i][k] * y[k] for k in range(i))) / L[i][i]
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (y[i] - sum(L[k][i] * x[k] for k in range(i + 1, n))) / L[i][i]
    return x


def wls(A, y, sig):
    """Weighted least squares with column scaling. Returns (x, cov, chi2)."""
    n, p = len(A), len(A[0])
    if n <= p:
        raise LinAlgError("fewer data than parameters")
    w = [1.0 / (s * s) for s in sig]
    sc = []
    for j in range(p):
        s = math.sqrt(sum(A[i][j] ** 2 for i in range(n)) / n)
        if s == 0:
            raise LinAlgError(f"column {j} is all zero")
        sc.append(s)
    As = [[A[i][j] / sc[j] for j in range(p)] for i in range(n)]
    N = [[sum(w[i] * As[i][a] * As[i][b] for i in range(n)) for b in range(p)] for a in range(p)]
    rhs = [sum(w[i] * As[i][a] * y[i] for i in range(n)) for a in range(p)]
    L = cholesky(N)
    xs = chol_solve(L, rhs)
    inv = []
    for j in range(p):
        e = [0.0] * p
        e[j] = 1.0
        inv.append(chol_solve(L, e))
    x = [xs[j] / sc[j] for j in range(p)]
    cov = [[inv[a][b] / (sc[a] * sc[b]) for b in range(p)] for a in range(p)]
    chi2 = 0.0
    for i in range(n):
        r = y[i] - sum(A[i][j] * x[j] for j in range(p))
        chi2 += w[i] * r * r
    return x, cov, chi2


# ------------------------------------------------------------------ the fit
def design(transits, orbit=None, use_colour=True):
    rows = []
    for d in transits:
        th = math.radians(d["theta"])
        s, c = math.sin(th), math.cos(th)
        T = t_years(d["t_ns"])
        r = [s, c, d["pf"], T * s, T * c]
        if use_colour:
            r.append(d["colour"])
        if orbit is not None:
            X, Y = xy_elliptic(t_dr3_days(d["t_ns"]), orbit["P"], orbit["e"], orbit["tp"])
            r += [X * s, Y * s, X * c, Y * c]          # B, G, A, F
        rows.append(r)
    return rows


def fit_source(transits, orbit, excess=None, n_draws=N_DRAWS, seed=SEED):
    """Pre-registered fit of one source at a fixed (P, e, tp). Returns a dict."""
    tr = [d for d in transits if math.isfinite(d["w"]) and math.isfinite(d["sigma"])]
    res = {"n_transits": len(tr), "n_ccd": sum(d["n_ccd"] for d in tr)}
    if len(tr) < MIN_TRANSITS:
        res["status"] = "TOO_FEW_TRANSITS"
        return res
    eps = excess if excess is not None else fnum(tr[0].get("excess"), 0.0)
    res["excess_noise_mas"] = eps
    use_colour = all(math.isfinite(d["colour"]) for d in tr) and \
        len({round(d["colour"], 12) for d in tr}) > 1
    res["colour_column"] = use_colour
    sig = [math.sqrt(d["sigma"] ** 2 + eps ** 2) for d in tr]
    y = [d["w"] for d in tr]
    try:
        _, _, chi_s = wls(design(tr, None, use_colour), y, sig)
        x, cov, chi_o = wls(design(tr, orbit, use_colour), y, sig)
    except LinAlgError as exc:
        res["status"] = f"SINGULAR: {exc}"
        return res
    k = 6 if use_colour else 5
    B, G, A, F = x[k:k + 4]
    a0, cosi = ti_to_a_cosi(A, B, F, G)
    # sigma(cos i) from draws of the (B, G, A, F) covariance block
    sub = [[cov[k + a][k + b] for b in range(4)] for a in range(4)]
    rng = random.Random(seed)
    draws = []
    try:
        Lc = cholesky(sub)
        for _ in range(n_draws):
            z = [rng.gauss(0, 1) for _ in range(4)]
            d = [x[k + a] + sum(Lc[a][b] * z[b] for b in range(a + 1)) for a in range(4)]
            draws.append(ti_to_a_cosi(d[2], d[0], d[3], d[1])[1])
    except LinAlgError:
        draws = []
    if len(draws) > 1:
        m = sum(draws) / len(draws)
        sd = math.sqrt(sum((v - m) ** 2 for v in draws) / (len(draws) - 1))
    else:
        sd = float("nan")
    # descriptive: same fit without the excess noise
    try:
        sig0 = [d["sigma"] for d in tr]
        _, _, c0s = wls(design(tr, None, use_colour), y, sig0)
        _, _, c0o = wls(design(tr, orbit, use_colour), y, sig0)
        dchi_noexc = c0s - c0o
    except LinAlgError:
        dchi_noexc = float("nan")
    dchi = chi_s - chi_o
    res.update({
        "status": "OK", "chi2_single": chi_s, "chi2_orbit": chi_o, "dchi2": dchi,
        "dchi2_no_excess_noise": dchi_noexc, "dof_orbit": len(tr) - (k + 4),
        "B": B, "G": G, "A": A, "F": F, "a0_mas": a0, "cos_i": cosi,
        "sigma_cos_i": sd, "detected": dchi > DCHI2_DET,
        "edge_on": (abs(cosi) - 2 * sd <= EDGE_COS) if math.isfinite(sd) else False})
    return res


# ------------------------------------------------------------------ grading
def _quantile(v, q):
    s = sorted(v)
    if not s:
        return float("nan")
    i = q * (len(s) - 1)
    lo = int(math.floor(i))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def grade(results, n_boot=N_BOOT, seed=SEED):
    """results: dicts with 'eclipsing' (bool), 'detected', 'edge_on', 'a0_ratio' (opt.),
    'status'. Only status OK rows count. Returns the W0-W4 grades and the outcome."""
    ok = [r for r in results if r.get("status") == "OK"]
    ecl = [r for r in ok if r["eclipsing"]]
    ne = [r for r in ok if not r["eclipsing"]]
    out = {"n_ok": len(ok), "n_eclipsing": len(ecl), "n_non_eclipsing": len(ne),
           "n_not_ok": len(results) - len(ok)}
    if not ecl or not ne:
        out["outcome"] = "NO_DATA"
        return out
    de = sum(r["detected"] for r in ecl) / len(ecl)
    dn = sum(r["detected"] for r in ne) / len(ne)
    det_e = [r for r in ecl if r["detected"]]
    det_n = [r for r in ne if r["detected"]]
    eo_e = sum(r["edge_on"] for r in det_e) / len(det_e) if det_e else float("nan")
    eo_n = sum(r["edge_on"] for r in det_n) / len(det_n) if det_n else float("nan")
    ratio = dn / de if de > 0 else float("nan")
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        be = sum(rng.random() < de for _ in range(len(ecl))) / len(ecl)
        bn = sum(rng.random() < dn for _ in range(len(ne))) / len(ne)
        if be > 0:
            boots.append(bn / be)
    ci = [_quantile(boots, 0.025), _quantile(boots, 0.975)]
    w0 = de >= W0_MIN and (eo_e >= W0_MIN if math.isfinite(eo_e) else False)
    w1 = ratio <= W1_MAX
    w2 = ratio >= W2_MIN
    w3 = (eo_n < W3_FACTOR * eo_e) if math.isfinite(eo_n) and math.isfinite(eo_e) else False
    w4 = {}
    for name, grp in (("eclipsing", ecl), ("non_eclipsing", ne)):
        v = [r["a0_ratio"] for r in grp if math.isfinite(fnum(r.get("a0_ratio")))]
        w4[name] = {"n": len(v), "median": _quantile(v, 0.5),
                    "range68": [_quantile(v, 0.16), _quantile(v, 0.84)]}
    out.update({
        "D_e": de, "D_ne": dn, "D_ratio": ratio, "D_ratio_ci95": ci,
        "edge_on_frac_detected_e": eo_e, "edge_on_frac_detected_ne": eo_n,
        "W0": w0, "W1": w1, "W2": w2, "W3": w3, "W4": w4})
    if not w0:
        out["outcome"] = "W0_FAILED_NOT_INTERPRETED"
    elif w1:
        out["outcome"] = "SPURIOUS_ORBITS"
    elif w2 and w3:
        out["outcome"] = "UNDERSTATED_INCLINATION_ERRORS"
    else:
        out["outcome"] = "MIXED_OR_INCONCLUSIVE"
    return out


# ------------------------------------------------------------------ network
def http_get(url, timeout=300, tries=3):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mv2-gaia-orbit-transits"})
            with urllib.request.urlopen(req, timeout=timeout) as fh:
                return fh.read()
        except Exception as exc:
            last = exc
            time.sleep(10 * (k + 1))
    raise IOError(f"GET {url} failed: {last}")


def datalink(ids, release, retrieval_type, structure="RAW", fmt="votable", timeout=600):
    """POST to the Gaia DataLink server. Returns (bytes, content_type)."""
    data = urllib.parse.urlencode({
        "RETRIEVAL_TYPE": retrieval_type, "ID": ",".join(str(i) for i in ids),
        "FORMAT": fmt, "RELEASE": release, "DATA_STRUCTURE": structure,
        "VALID_DATA": "false", "USE_ZIP_ALWAYS": "true"}).encode()
    req = urllib.request.Request(DATALINK_URL, data=data,
                                 headers={"User-Agent": "mv2-gaia-orbit-transits"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as fh:
            return fh.read(), fh.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        body = exc.read()[:2000].decode("utf-8", "replace")
        raise IOError(f"HTTP {exc.code}: {body}")


def dr3_orbits(ids):
    """{source_id: orbit dict} for the astrometric DR3 solutions (dr4_fetch helpers)."""
    import dr4_fetch as f
    cols = ("source_id", "nss_solution_type", "period", "eccentricity", "t_periastron",
            "a_thiele_innes", "b_thiele_innes", "f_thiele_innes", "g_thiele_innes",
            "significance")
    rows = []
    for ch in f.chunks(ids):
        rows += f.tap_query(f.adql_nss("gaiadr3.nss_two_body_orbit", ch, cols))
    by = {}
    for r in rows:
        by.setdefault(str(r["source_id"]).strip(), []).append(r)
    out = {}
    for sid, rs in by.items():
        best, n_astro, _ = f.pick_solution(rs)
        status = "OK"
        if best is None:
            # no Thiele-Innes orbit: keep a P, e, T solution (rehearsal only; release
            # requires status OK)
            timed = [r for r in rs if math.isfinite(fnum(r.get("period")))
                     and math.isfinite(fnum(r.get("t_periastron")))]
            if not timed:
                out[sid] = {"status": "NO_DR3_ORBIT",
                            "types": sorted({str(r.get("nss_solution_type")) for r in rs})}
                continue
            best, status = timed[0], "OK_NON_ASTROMETRIC"
        e = fnum(best.get("eccentricity"), 0.0)
        o = {"status": status, "type": best.get("nss_solution_type"), "P": fnum(best["period"]),
             "e": e, "tp": fnum(best["t_periastron"])}
        A, B, F, G = (fnum(best.get(c)) for c in ("a_thiele_innes", "b_thiele_innes",
                                                    "f_thiele_innes", "g_thiele_innes"))
        if all(math.isfinite(v) for v in (A, B, F, G)):
            o["a0_dr3_mas"], o["cos_i_dr3"] = ti_to_a_cosi(A, B, F, G)
        if not (math.isfinite(o["P"]) and o["P"] > 0 and math.isfinite(o["tp"])):
            o["status"] = "BAD_DR3_ORBIT"
        out[sid] = o
    return out


# ------------------------------------------------------------------ modes
def write_json(path, obj):
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1, default=str)


def residual_plot(path, transits, orbit, fit, title):
    """Single-star residuals vs the fitted orbit's AL term (should lie on y = x)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("WARNING: matplotlib missing; plot not made:", path)
        return
    use_colour = fit.get("colour_column", False)
    eps = fit.get("excess_noise_mas", 0.0)
    sig = [math.sqrt(d["sigma"] ** 2 + eps ** 2) for d in transits]
    y = [d["w"] for d in transits]
    A1 = design(transits, None, use_colour)
    xs, _, _ = wls(A1, y, sig)
    res = [y[i] - sum(A1[i][j] * xs[j] for j in range(len(xs))) for i in range(len(y))]
    A2 = design(transits, orbit, use_colour)
    k = 6 if use_colour else 5
    orb = [sum(A2[i][k + j] * fit[n] for j, n in enumerate("BGAF")) for i in range(len(y))]
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.errorbar(orb, res, yerr=sig, fmt=".", ms=3, alpha=0.7)
    lim = max(max(abs(v) for v in orb + res), 1e-3)
    ax.plot([-lim, lim], [-lim, lim], "k--", lw=0.8)
    ax.set_xlabel("fitted orbit AL term at DR3 P, e, T (mas)")
    ax.set_ylabel("single-star residual (mas)")
    ax.set_title(title, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def rehearse(args):
    os.makedirs(args.out_dir, exist_ok=True)
    import hashlib
    report = {"version": VERSION, "mode": "rehearse"}
    data, name = None, ""
    sources = [(args.zip, "local")] if args.zip else [(PRERELEASE_URL, "prerelease.zip"),
                                                      (PRERELEASE_MIRROR, "prerelease.xml")]
    for src, nm in sources:
        try:
            got = open(src, "rb").read() if nm == "local" else http_get(src, tries=2)
            if not (got[:2] == b"PK" or got.lstrip()[:5] in (b"<?xml", b"<VOTA")):
                raise IOError("not a zip or VOTable: " + got[:200].decode("utf-8", "replace"))
            data = got
            name = src if nm == "local" else nm
            report["source"] = src
            break
        except Exception as exc:
            print("download failed:", src, exc)
            report.setdefault("download_errors", []).append(f"{src}: {str(exc)[:300]}")
    if data is None:
        write_json(os.path.join(args.out_dir, "wobble_rehearsal.json"), report)
        return 3
    report["bytes"] = len(data)
    report["sha256"] = hashlib.sha256(data).hexdigest()
    rows = rows_from_bytes(name, data, report)
    report["n_rows"] = len(rows)
    if rows:
        ex = rows[0]
        report["first_row"] = {k: (v[:10] if isinstance(v, list) else v) for k, v in ex.items()}
    print(json.dumps({k: report[k] for k in report if k != "first_row"}, indent=1,
                     default=str)[:20000])
    print("first row:", json.dumps(report.get("first_row"), default=str)[:4000])
    try:
        transits = to_transits(rows)
    except SchemaError as exc:
        print("SCHEMA:", exc)
        report["schema_error"] = str(exc)
        write_json(os.path.join(args.out_dir, "wobble_rehearsal.json"), report)
        return 4
    report["sources"] = {sid: {"group": PRERELEASE_GROUPS.get(sid, "?"), "n_transits": len(tr),
                               "t_yr_range": [t_years(tr[0]["t_ns"]), t_years(tr[-1]["t_ns"])]}
                         for sid, tr in transits.items()}
    for sid, info in report["sources"].items():
        lo, hi = info["t_yr_range"]
        if not (-4.0 < lo < 3.5 and -4.0 < hi < 3.5):
            report["schema_error"] = f"time out of range for {sid}: {lo}..{hi} yr from J2017.5"
            print("SCHEMA:", report["schema_error"])
            write_json(os.path.join(args.out_dir, "wobble_rehearsal.json"), report)
            return 4
    try:
        orbits = dr3_orbits(sorted(transits))
    except Exception as exc:
        print("DR3 orbit query failed:", exc)
        report["error"] = f"DR3 TAP: {exc}"
        write_json(os.path.join(args.out_dir, "wobble_rehearsal.json"), report)
        return 3
    report["dr3_orbits"] = orbits
    good = ("OK", "OK_NON_ASTROMETRIC")
    ref = orbits.get(HD114762, {})
    fits = {}
    if ref.get("status") in good:
        for sid, tr in transits.items():
            own = orbits.get(sid, {})
            entry = {"group": PRERELEASE_GROUPS.get(sid, "?")}
            if own.get("status") in good:
                fo = fit_source(tr, own)
                entry["own_orbit"] = fo
                if fo.get("status") == "OK":
                    if math.isfinite(fnum(own.get("a0_dr3_mas"))):
                        fo["a0_ratio"] = fo["a0_mas"] / own["a0_dr3_mas"]
                    residual_plot(os.path.join(args.out_dir, f"wobble_{sid}.png"), tr, own, fo,
                                  f"Gaia DR4 pre-release {sid} at DR3 orbit P={own['P']:.2f} d")
            entry["at_hd114762_orbit"] = fit_source(tr, ref)
            fits[sid] = entry
    report["fits"] = fits
    hd = fits.get(HD114762, {}).get("own_orbit", {})
    q = {s: fits.get(s, {}).get("at_hd114762_orbit", {}).get("dchi2") for s in QSOS}
    nulls = {s: f["at_hd114762_orbit"].get("dchi2") for s, f in fits.items()
             if f["group"] in ("parallax", "magnitude", "qso")}
    passed = (hd.get("status") == "OK" and hd["dchi2"] > DCHI2_DET and
              all(v is not None and math.isfinite(v) and v < DCHI2_DET for v in q.values()))
    report["rehearsal"] = {
        "rule": "HD 114762 dchi2 > 30 at its DR3 orbit; each QSO dchi2 < 30 at that orbit",
        "hd114762_dchi2": hd.get("dchi2"), "hd114762_status": hd.get("status"),
        "qso_dchi2": q, "null_dchi2_all_single_and_qso": nulls, "pass": passed}
    write_json(os.path.join(args.out_dir, "wobble_rehearsal.json"), report)
    print(json.dumps(report["rehearsal"], indent=1, default=str))
    # DataLink smoke tests (descriptive): DR3 epoch photometry works; DR4 astrometry not yet
    smoke = {}
    for label, rel, rt in (("dr3_epoch_photometry", "Gaia DR3", "EPOCH_PHOTOMETRY"),
                           ("dr4_epoch_astrometry", args.release, args.retrieval_type)):
        try:
            body, ctype = datalink([HD114762], rel, rt, structure="INDIVIDUAL"
                                   if rel == "Gaia DR3" else "RAW")
            info = {"bytes": len(body), "content_type": ctype, "zip": body[:2] == b"PK"}
            if info["zip"]:
                with zipfile.ZipFile(io.BytesIO(body)) as zf:
                    info["members"] = zf.namelist()[:10]
            else:
                info["head"] = body[:300].decode("utf-8", "replace")
        except Exception as exc:
            info = {"error": str(exc)[:500]}
        smoke[label] = info
    report["datalink_smoke"] = smoke
    print(json.dumps(smoke, indent=1, default=str))
    write_json(os.path.join(args.out_dir, "wobble_rehearsal.json"), report)
    return 0 if passed else 2


def load_targets(src):
    text = http_get(src).decode() if src.startswith("http") else open(src).read()
    rows = list(csv.DictReader(io.StringIO(text)))
    return [(str(r["source_id"]).strip(), is_true(r["det_9"])) for r in rows]


def release(args):
    import dr4_fetch as f
    os.makedirs(args.out_dir, exist_ok=True)
    targets = load_targets(args.targets)
    n_e = sum(e for _, e in targets)
    print(f"{len(targets)} targets, {n_e} eclipsing (expected 162 / 58)")
    old = [s for s, _ in targets]
    orbits = dr3_orbits(old)
    if args.schema == "dr4":
        matches, _ = f.fetch_matches("dr4", old, unit=args.xmatch_unit)
    else:
        matches = {o: (o, "ok") for o in old}
    new_ids = [m[0] for m in matches.values() if m[1] == "ok"]
    rows = []
    for ch in f.chunks(new_ids, 100):
        try:
            body, _ = datalink(ch, args.release, args.retrieval_type)
        except IOError as exc:
            msg = str(exc)
            print("DataLink:", msg)
            if any(s in msg.lower() for s in ("retrieval", "release", "not valid", "unknown")):
                return 6
            return 3
        rows += rows_from_bytes("dl.zip", body)
    if not rows:
        return 3
    try:
        transits = to_transits(rows)
    except SchemaError as exc:
        print("SCHEMA:", exc)
        return 4
    results = []
    for sid, ecl in targets:
        r = {"source_id": sid, "eclipsing": ecl}
        new, st = matches.get(sid, (None, "none"))
        o = orbits.get(sid, {})
        r["match"] = st
        if st != "ok" or o.get("status") != "OK" or new not in transits:
            r["status"] = "NO_MATCH" if st != "ok" else (
                "NO_DR3_ORBIT" if o.get("status") != "OK" else "NO_EPOCH_DATA")
            results.append(r)
            continue
        r.update(fit_source(transits[new], o))
        if r.get("status") == "OK" and math.isfinite(fnum(o.get("a0_dr3_mas"))):
            r["a0_ratio"] = r["a0_mas"] / o["a0_dr3_mas"]
        results.append(r)
    summary = grade(results)
    summary["version"] = VERSION
    write_json(os.path.join(args.out_dir, "wobble_summary.json"), summary)
    keys = ["source_id", "eclipsing", "match", "status", "n_transits", "dchi2", "a0_mas",
            "cos_i", "sigma_cos_i", "detected", "edge_on", "a0_ratio", "excess_noise_mas"]
    with open(os.path.join(args.out_dir, "wobble_targets.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)
    print(json.dumps(summary, indent=1, default=str))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=("rehearse", "release"))
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--zip", default="", help="local copy of the pre-release zip")
    ap.add_argument("--targets", default="https://raw.githubusercontent.com/munimtechnologies/"
                    "gaia-orbit-transits/main/data/calib-window-v1/window_targets.csv")
    ap.add_argument("--schema", default="dr4", choices=("dr4", "dr3"))
    ap.add_argument("--xmatch-unit", default="mas")
    ap.add_argument("--release", default="Gaia DR4")
    ap.add_argument("--retrieval-type", default="EPOCH_ASTROMETRY")
    args = ap.parse_args(argv)
    return rehearse(args) if args.mode == "rehearse" else release(args)


if __name__ == "__main__":
    sys.exit(main())
