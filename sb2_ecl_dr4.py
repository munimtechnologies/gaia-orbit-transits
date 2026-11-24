# SPDX-License-Identifier: Apache-2.0
"""sb2_ecl_dr4 0.1.0 - runbook step g8: eclipses of Gaia double-lined binaries found in Gaia's own
epoch photometry, phased on Gaia's own spectroscopic orbits. Built for Gaia DR4 (2 Dec 2026).

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.
Pre-registration: findings/2026-11-24-g8-dr4-sb2-eclipse-prereg.md (fixed before DR4 exists).

Why it can work: Gaia's photometric eclipsing-binary search has to find a period in about 100
sparse epochs. For a double-lined binary, Gaia's radial velocities already give the period and the
two conjunction times, so two faint epochs at predicted conjunctions, in two different eclipses,
are enough. This matters most where TESS cannot help: faint (G > 13) and crowded stars.

Rule (frozen in the pre-registration; derived from gaia_conj_dips_acv 0.1.0, plus a light-curve
model so that ellipsoidal variation at conjunction is not taken for an eclipse):
 1. Phase = ((t - t_peri) / P) mod 1. Conjunctions at true anomaly 90 - omega and 270 - omega
    (0.25 / 0.75 when omega is not given, Gaia's circular SB2C convention).
 2. Fit a 2-harmonic Fourier series in orbital phase to the epochs more than FIT_EXCLUDE (0.06) in
    phase from both conjunctions (one 5-sigma clip, refit). Fewer than MIN_FIT (15) such epochs:
    model = their median. Residual = mag - model (positive = fainter).
 3. sd = robust SD of the residuals of those epochs; dip = residual >= max(0.025 mag, 4 sd).
 4. ECL_GAIA: >= 2 dips within WINDOW (0.035) in phase of a conjunction, from >= 2 different
    eclipses (conjunction passages), and in-window dips >= 2 x out-of-window dips.
 5. ECL_GAIA_SHALLOW (if not ECL_GAIA): the 3 largest residuals all lie within 0.02 in phase of a
    conjunction, each >= 2.5 sd, from >= 2 different eclipses.
 6. Null: the same rule with both conjunction phases moved by +0.25 (quadrature).
Stars with fewer than MIN_EPOCHS (20) usable G epochs are FEW_EPOCHS.

Modes:
  --self-test
  --rehearse-dr3 REPO_DIR   run the rule on the DR3 epochs saved in the repository (not blind)
  --chunk I --n-chunks K    DR4 release day: one hash-chunk of the SB2 sample
  --combine                 DR4: grade all chunk files found in --results-dir
Exit codes: 0 ok; 2 data unavailable (re-file unchanged); 3 self-test failed; 4 schema gate G0.
Stdlib only.
"""
import argparse
import csv
import gzip
import io
import json
import math
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

VERSION = "0.1.0"

# ---------------------------------------------------------------- frozen rule constants
DIP_MIN_MAG = 0.025
DIP_MIN_SIGMA = 4.0
WINDOW = 0.035
FIT_EXCLUDE = 0.06
NHARM = 2
MIN_FIT = 15
CLIP_SIGMA = 5.0
MIN_EPOCHS = 20
SHALLOW_WINDOW = 0.02
SHALLOW_SIGMA = 2.5
NULL_SHIFT = 0.25

# ---------------------------------------------------------------- frozen sample / grading constants
P_MIN = 0.4
P_MAX = 15.0
G_FAINT = 13.0                 # TESS-blind by brightness: G > 13
CROWD_G_MAX = 13.0             # crowding is computed for G <= 13 only
CROWD_RADIUS_DEG = 21.0 / 3600.0   # one TESS pixel
CROWD_RATIO = 0.5              # TESS-blind by crowding: neighbours' flux / target flux >= 0.5
G_BRIGHT = 11.0                # bright-precision control
REFS = (("a", 2739.375), ("b", 2191.5))   # orbit reference: J2017.5 (DR4), J2016.0 (DR3), in Gaia time
T0_MIN_CONTROLS = 20
T0_MIN_SHARE = 0.5
R1_MIN = 0.4
N1_MIN_EXCESS = 5.0
B1_MIN_N = 10
B1_MIN_SHARE = 0.7
M1_MIN_N = 10
MAIN_BINS = ((100, "HUNDREDS"), (20, "DOZENS"), (1, "FEW"), (0, "NONE"))
CONTROL_SID = "66729880383767168"     # V1229 Tau (HD 23642), a known eclipsing SB2 (DR3 id)
CONTROL_MIN_EPOCHS = 20
CONTROL_MIN_SPAN_D = 1500.0          # DR3 spans ~1038 d; DR4 ~2000 d

TAP_BASE = "https://gea.esac.esa.int/tap-server/tap"
DATALINK_TEMPLATES = (
    "https://gea.esac.esa.int/data-server/data?RETRIEVAL_TYPE=EPOCH_PHOTOMETRY&ID={sid}"
    "&FORMAT=CSV&RELEASE=Gaia%20DR4&DATA_STRUCTURE=INDIVIDUAL&VALID_DATA=false",
    "https://gea.esac.esa.int/data-server/data?RETRIEVAL_TYPE=EPOCH_PHOTOMETRY&ID={sid}"
    "&FORMAT=CSV&VALID_DATA=false&RETRIEVAL_LEVEL=RAW&RELEASE=Gaia%20DR4",
    "https://gea.esac.esa.int/data-server/data?RETRIEVAL_TYPE=EPOCH_PHOTOMETRY&ID=Gaia%20DR4%20{sid}"
    "&FORMAT=CSV&VALID_DATA=false&RETRIEVAL_LEVEL=RAW",
)
UA = "gaia-orbit-transits/sb2_ecl_dr4 (MV2, Munim, Inc.; open research)"
HTTP_TIMEOUT = 120
PAUSE = 0.2

REQ_ORB = ("source_id", "nss_solution_type", "period", "t_periastron", "eccentricity",
           "arg_periastron", "semi_amplitude_primary", "semi_amplitude_secondary")
REQ_GS = ("source_id", "phot_g_mean_mag", "ra", "dec")
ORBIT_QUERY = (
    "SELECT o.source_id, o.nss_solution_type, o.period, o.t_periastron, o.eccentricity, "
    "o.arg_periastron, o.semi_amplitude_primary, o.semi_amplitude_secondary, "
    "g.phot_g_mean_mag, g.ra, g.dec "
    "FROM {s}.nss_two_body_orbit AS o JOIN {s}.gaia_source AS g ON o.source_id = g.source_id "
    "WHERE o.nss_solution_type LIKE 'SB2%' AND o.period >= " + repr(P_MIN) +
    " AND o.period <= " + repr(P_MAX))
MASS_CONST = 1.036149e-7

ROW_KEYS = ["source_id", "chunk", "G", "ra", "dec", "P", "e", "omega", "sol_type", "K1", "K2",
            "m1sin3i", "m1", "s3", "crowd", "gaia_eb", "gaia_ecl_sol", "gaia_class",
            "gaia_class_ecl", "n_epochs", "span_d"]
for _r, _ in REFS:
    ROW_KEYS += ["%s_label" % _r, "%s_null_label" % _r, "%s_n_dips" % _r, "%s_n_in" % _r,
                 "%s_n_events" % _r, "%s_depth" % _r, "%s_model" % _r]
ROW_KEYS += ["vsx_ecl", "simbad_eb", "tessebs_viz", "t10k_viz", "status", "error"]
LOOKUP_KEYS = ("vsx_ecl", "simbad_eb", "tessebs_viz", "t10k_viz")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ================================================================ pure helpers
def fnum(v, default=float("nan")):
    try:
        if v is None:
            return default
        s = str(v).strip().strip('"')
        if s in ("", "null", "NULL", "NaN", "nan", "None", "--"):
            return default
        x = float(s)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def parse_bool(v):
    s = str(v if v is not None else "").strip().lower()
    if s in ("true", "1", "t", "yes"):
        return True
    if s in ("false", "0", "f", "no"):
        return False
    return None


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, float):
        return "" if not math.isfinite(v) else repr(v)
    return str(v)


def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        raise ValueError("empty")
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def robust_sd(xs):
    m = median(xs)
    return 1.4826 * median([abs(x - m) for x in xs])


def true_to_phase(nu, e):
    """True anomaly (rad) -> fraction of the period after periastron, in [0, 1)."""
    E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0), math.sqrt(1.0 + e) * math.cos(nu / 2.0))
    M = E - e * math.sin(E)
    return (M / (2.0 * math.pi)) % 1.0


def conjunction_phases(e, omega_deg):
    e = e if (e is not None and math.isfinite(e)) else 0.0
    w = math.radians(omega_deg if (omega_deg is not None and math.isfinite(omega_deg)) else 0.0)
    return true_to_phase(math.pi / 2.0 - w, e), true_to_phase(3.0 * math.pi / 2.0 - w, e)


def dphase(a, b):
    return (a - b + 0.5) % 1.0 - 0.5


def m1sin3i(k1, k2, period, ecc):
    e = ecc if (ecc is not None and math.isfinite(ecc)) else 0.0
    return MASS_CONST * (1.0 - e * e) ** 1.5 * (k1 + k2) ** 2 * k2 * period


def solve(a, b):
    """Gaussian elimination with partial pivoting; None if singular."""
    n = len(b)
    m = [list(a[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[p][c]) < 1e-12:
            return None
        m[c], m[p] = m[p], m[c]
        for r in range(n):
            if r != c and m[r][c] != 0.0:
                f = m[r][c] / m[c][c]
                for k in range(c, n + 1):
                    m[r][k] -= f * m[c][k]
    return [m[i][n] / m[i][i] for i in range(n)]


def basis(ph, nh=NHARM):
    out = [1.0]
    for k in range(1, nh + 1):
        a = 2.0 * math.pi * k * ph
        out += [math.cos(a), math.sin(a)]
    return out


def fit_fourier(phs, ys, nh=NHARM):
    nb = 1 + 2 * nh
    if len(phs) < MIN_FIT:
        return None
    ata = [[0.0] * nb for _ in range(nb)]
    aty = [0.0] * nb
    for p, y in zip(phs, ys):
        b = basis(p, nh)
        for i in range(nb):
            aty[i] += b[i] * y
            for j in range(nb):
                ata[i][j] += b[i] * b[j]
    return solve(ata, aty)


def eval_fourier(c, ph, nh=NHARM):
    return sum(ci * bi for ci, bi in zip(c, basis(ph, nh)))


def classify(times, mags, P, t_peri, e, omega, shift=0.0):
    """The frozen g8 rule for one star. times in Gaia time (BJD - 2455197.5), mags in G."""
    n = len(times)
    res = {"n": n, "label": "FEW_EPOCHS", "n_dips": 0, "n_in": 0, "n_out": 0, "n_events": 0,
           "depth": float("nan"), "model": "", "sd": float("nan"), "thr": float("nan"),
           "dips": []}
    if n < MIN_EPOCHS or not (P > 0):
        return res
    c1, c2 = conjunction_phases(e, omega)
    conj = ((c1 + shift) % 1.0, (c2 + shift) % 1.0)
    ph = [((t - t_peri) / P) % 1.0 for t in times]
    near = []
    for p in ph:
        d1, d2 = dphase(p, conj[0]), dphase(p, conj[1])
        near.append((d1, 0) if abs(d1) <= abs(d2) else (d2, 1))
    fit_idx = [i for i in range(n) if abs(near[i][0]) > FIT_EXCLUDE]
    model = None
    if len(fit_idx) >= MIN_FIT:
        c = fit_fourier([ph[i] for i in fit_idx], [mags[i] for i in fit_idx])
        if c is not None:
            r0 = [mags[i] - eval_fourier(c, ph[i]) for i in fit_idx]
            s0 = robust_sd(r0)
            if s0 > 0:
                keep = [i for i, r in zip(fit_idx, r0) if abs(r) <= CLIP_SIGMA * s0]
                if len(keep) >= MIN_FIT:
                    c2_ = fit_fourier([ph[i] for i in keep], [mags[i] for i in keep])
                    if c2_ is not None:
                        c = c2_
            model = [eval_fourier(c, p) for p in ph]
            res["model"] = "fourier%d" % NHARM
    if model is None:
        base = [mags[i] for i in fit_idx] if len(fit_idx) >= 5 else list(mags)
        m0 = median(base)
        model = [m0] * n
        res["model"] = "median"
    resid = [mags[i] - model[i] for i in range(n)]
    sd_idx = fit_idx if len(fit_idx) >= 5 else list(range(n))
    sd = robust_sd([resid[i] for i in sd_idx])
    thr = max(DIP_MIN_MAG, DIP_MIN_SIGMA * sd)

    def event(i):
        d, w = near[i]
        return (w, int(round((times[i] - t_peri) / P - conj[w])))

    dips = [i for i in range(n) if resid[i] >= thr]
    in_d = [i for i in dips if abs(near[i][0]) <= WINDOW]
    out_d = [i for i in dips if abs(near[i][0]) > WINDOW]
    events = {event(i) for i in in_d}
    ecl = len(in_d) >= 2 and len(events) >= 2 and len(in_d) >= 2 * len(out_d)
    top = sorted(range(n), key=lambda i: -resid[i])[:3]
    shallow = (sd > 0 and len(top) == 3
               and all(abs(near[i][0]) <= SHALLOW_WINDOW and resid[i] >= SHALLOW_SIGMA * sd
                       for i in top)
               and len({event(i) for i in top}) >= 2)
    res.update({"label": "ECL_GAIA" if ecl else ("ECL_GAIA_SHALLOW" if shallow else "NONE"),
                "n_dips": len(dips), "n_in": len(in_d), "n_out": len(out_d),
                "n_events": len(events), "sd": sd, "thr": thr,
                "depth": max([resid[i] for i in in_d]) if in_d else float("nan"),
                "conj": list(conj),
                "dips": [{"t": times[i], "resid": resid[i], "dphase": near[i][0],
                          "conj": near[i][1]} for i in dips]})
    return res


def hash32(sid):
    return (int(sid) * 2654435761) % 4294967296


def chunk_of(sid, k):
    return (hash32(sid) >> 16) % k


def wilson(k, n, z=1.959964):
    if n <= 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def auc_greater(xs, ys):
    """AUC = P(x > y) (ties 1/2) and the one-sided normal-approximation Mann-Whitney p."""
    nx, ny = len(xs), len(ys)
    if nx == 0 or ny == 0:
        return float("nan"), float("nan")
    allv = sorted([(v, 0) for v in xs] + [(v, 1) for v in ys])
    rank_sum_x, i = 0.0, 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        rank_sum_x += avg * sum(1 for k in range(i, j + 1) if allv[k][1] == 0)
        i = j + 1
    u = rank_sum_x - nx * (nx + 1) / 2.0
    auc = u / (nx * ny)
    mu = nx * ny / 2.0
    sig = math.sqrt(nx * ny * (nx + ny + 1) / 12.0)
    z = (u - mu) / sig if sig > 0 else 0.0
    return auc, 0.5 * math.erfc(z / math.sqrt(2.0))


# ================================================================ epoch parsing
def _arr(s):
    s = str(s or "").strip().strip("[](){}")
    return [x.strip() for x in s.split(",")] if s else []


def parse_epoch_csv(text):
    """-> list of (time, mag, rejected) for the G band. Accepts one row per epoch (with or without
    a 'band' column) or array columns (g_transit_time / g_transit_mag / variability_flag_g_reject)."""
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return []
    keys = {k.strip().lower(): k for k in rows[0].keys() if k is not None}
    out = []
    if "g_transit_time" in keys and "g_transit_mag" in keys:
        for r in rows:
            ts, ms = _arr(r[keys["g_transit_time"]]), _arr(r[keys["g_transit_mag"]])
            fl = _arr(r[keys["variability_flag_g_reject"]]) if "variability_flag_g_reject" in keys else []
            for j, (t, m) in enumerate(zip(ts, ms)):
                tt, mm = fnum(t), fnum(m)
                if math.isfinite(tt) and math.isfinite(mm):
                    out.append((tt, mm, parse_bool(fl[j]) is True if j < len(fl) else False))
        return out
    tk = next((keys[k] for k in ("time", "obs_time", "g_time", "epoch") if k in keys), None)
    mk = next((keys[k] for k in ("mag", "g_mag", "magnitude") if k in keys), None)
    if tk is None or mk is None:
        return []
    bk = keys.get("band")
    flag_cols = [keys[k] for k in ("rejected_by_photometry", "rejected_by_variability",
                                   "variability_flag_g_reject", "rp", "rv") if k in keys]
    for r in rows:
        if bk is not None and str(r.get(bk, "")).strip().upper() not in ("G", "G_FOV", "FOV_G"):
            continue
        tt, mm = fnum(r.get(tk)), fnum(r.get(mk))
        if not (math.isfinite(tt) and math.isfinite(mm)):
            continue
        rej = any(parse_bool(r.get(c)) is True for c in flag_cols)
        out.append((tt, mm, rej))
    return out


def decode_payload(raw):
    """DataLink reply bytes -> concatenated CSV texts (handles gzip and zip)."""
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    if raw[:2] == b"PK":
        texts = []
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for name in z.namelist():
                b = z.read(name)
                if b[:2] == b"\x1f\x8b":
                    b = gzip.decompress(b)
                texts.append(b.decode("utf-8", "replace"))
        return texts
    return [raw.decode("utf-8", "replace")]


def usable(epochs):
    ok = [(t, m) for t, m, rej in epochs if not rej]
    ok.sort()
    return [t for t, _ in ok], [m for _, m in ok]


# ================================================================ grading (pure)
def blind_of(rec):
    G = fnum(rec.get("G"))
    cr = fnum(rec.get("crowd"))
    if math.isfinite(G) and G > G_FAINT:
        return True
    if math.isfinite(cr):
        return cr >= CROWD_RATIO
    return None if (math.isfinite(G) and G <= CROWD_G_MAX) else None


def known_gaia(rec):
    vals = [parse_bool(rec.get("gaia_eb")), parse_bool(rec.get("gaia_ecl_sol")),
            parse_bool(rec.get("gaia_class_ecl"))]
    if any(v is True for v in vals):
        return True
    if any(v is None for v in vals):
        return None
    return False


def vet_status(rec):
    """KNOWN / NEW / UNVETTED for a candidate."""
    kg = known_gaia(rec)
    lk = [parse_bool(rec.get(k)) for k in LOOKUP_KEYS]
    if kg is True or any(v is True for v in lk):
        return "KNOWN"
    if kg is None or any(v is None for v in lk):
        return "UNVETTED"
    return "NEW"


def t0_gate(recs, r):
    ctrl = [x for x in recs if parse_bool(x.get("gaia_eb")) is True
            and int(fnum(x.get("%s_n_dips" % r), 0)) >= 2]
    nd = sum(int(fnum(x.get("%s_n_dips" % r), 0)) for x in ctrl)
    ni = sum(int(fnum(x.get("%s_n_in" % r), 0)) for x in ctrl)
    share = ni / nd if nd else float("nan")
    if len(ctrl) < T0_MIN_CONTROLS:
        lab = "UNTESTABLE"
    else:
        lab = "TIME_OK" if share >= T0_MIN_SHARE else "TIME_BAD"
    return {"n_controls": len(ctrl), "n_dips": nd, "n_in": ni, "share": share,
            "chance_share": 4 * WINDOW, "label": lab}


def grade_all(recs):
    tested = [x for x in recs if x.get("status") == "OK"]
    gates = {r: t0_gate(tested, r) for r, _ in REFS}
    ref = next((r for r, _ in REFS if gates[r]["label"] == "TIME_OK"), REFS[0][0])
    interpreted = gates[ref]["label"] == "TIME_OK"
    L = "%s_label" % ref
    NL = "%s_null_label" % ref
    ok = [x for x in tested if x.get(L) not in ("", None, "FEW_EPOCHS")]
    # R1 recall on Gaia's own eclipsing binaries
    geb = [x for x in ok if parse_bool(x.get("gaia_eb")) is True]
    rk = sum(1 for x in geb if x.get(L) in ("ECL_GAIA", "ECL_GAIA_SHALLOW"))
    r_share = rk / len(geb) if geb else float("nan")
    r1 = ("UNTESTABLE" if len(geb) < T0_MIN_CONTROLS else
          "RECALL_OK" if r_share >= R1_MIN else "RECALL_LOW")
    # N1 null
    n_real = sum(1 for x in ok if x.get(L) == "ECL_GAIA")
    n_null = sum(1 for x in ok if x.get(NL) == "ECL_GAIA")
    excess = n_real / max(1, n_null)
    n1 = "UNTESTABLE" if n_real == 0 else ("NULL_OK" if excess >= N1_MIN_EXCESS else "NULL_FAIL")
    # B1 bright precision
    bright = [x for x in ok if x.get(L) == "ECL_GAIA" and fnum(x.get("G")) < G_BRIGHT]
    bdef = [x for x in bright if vet_status(x) in ("KNOWN", "NEW")]
    bk = sum(1 for x in bdef if vet_status(x) == "KNOWN")
    b_share = bk / len(bdef) if bdef else float("nan")
    b1 = ("UNTESTABLE" if len(bdef) < B1_MIN_N else
          "PRECISION_OK" if b_share >= B1_MIN_SHARE else "PRECISION_LOW")
    # M1 edge-on check with Gaia's masses
    s3c = [fnum(x.get("s3")) for x in ok if x.get(L) == "ECL_GAIA"]
    s3n = [fnum(x.get("s3")) for x in ok if x.get(L) == "NONE"]
    s3c = [v for v in s3c if math.isfinite(v)]
    s3n = [v for v in s3n if math.isfinite(v)]
    auc, p = auc_greater(s3c, s3n)
    if len(s3c) < M1_MIN_N or len(s3n) < M1_MIN_N:
        m1 = "UNTESTABLE"
    elif auc >= 0.6 and p <= 0.01:
        m1 = "EDGE_ON_CONFIRMED"
    elif auc < 0.55:
        m1 = "NOT_CONFIRMED"
    else:
        m1 = "WEAK"
    # MAIN: new TESS-blind eclipsing SB2s
    cand = [x for x in ok if x.get(L) == "ECL_GAIA" and blind_of(x) is True]
    new = [x for x in cand if vet_status(x) == "NEW"]
    unv = [x for x in cand if vet_status(x) == "UNVETTED"]
    main_label = next(lab for lim, lab in MAIN_BINS if len(new) >= lim)
    shallow_new = [x for x in ok if x.get(L) == "ECL_GAIA_SHALLOW" and blind_of(x) is True
                   and vet_status(x) == "NEW"]
    return {
        "ref": ref, "ref_value": dict(REFS)[ref], "interpreted": interpreted,
        "T0": gates,
        "R1": {"n_gaia_eb": len(geb), "n_flagged": rk, "share": r_share,
               "ci95": wilson(rk, len(geb)), "label": r1},
        "N1": {"n_real": n_real, "n_null": n_null, "excess": excess, "n_stars": len(ok),
               "null_rate": n_null / len(ok) if ok else float("nan"), "label": n1},
        "B1": {"n_bright": len(bright), "n_definite": len(bdef), "n_known": bk,
               "share_known": b_share, "label": b1},
        "M1": {"n_cand": len(s3c), "n_none": len(s3n), "auc": auc, "p_one_sided": p,
               "median_cand": median(s3c) if s3c else float("nan"),
               "median_none": median(s3n) if s3n else float("nan"), "label": m1},
        "MAIN": {"n_blind_ecl": len(cand), "n_new": len(new), "n_unvetted": len(unv),
                 "n_known": len(cand) - len(new) - len(unv), "label": main_label,
                 "n_shallow_new": len(shallow_new),
                 "new": [x.get("source_id") for x in new]},
        "counts": {"n_rows": len(recs), "n_tested": len(tested), "n_classified": len(ok),
                   "n_blind": sum(1 for x in ok if blind_of(x) is True)},
    }


# ================================================================ network
def http_get(url, timeout=HTTP_TIMEOUT, tries=3, data=None, accept_404=False):
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA},
                                         method="POST" if data is not None else "GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.geturl()
        except urllib.error.HTTPError as exc:
            if accept_404 and exc.code == 404:
                return b"", url
            last = exc
        except Exception as exc:
            last = exc
        log("HTTP retry", url[:110], a + 1, repr(last)[:160])
        time.sleep(5 * (a + 1))
    raise RuntimeError("HTTP failed %s: %r" % (url[:110], last))


def _text(raw):
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def tap_sync(query, base=TAP_BASE):
    body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                   "QUERY": query}).encode()
    raw, _ = http_get(base + "/sync", timeout=600, data=body)
    return list(csv.DictReader(io.StringIO(_text(raw))))


def tap_async(query, base=TAP_BASE, poll=10, max_wait=3600):
    body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                   "PHASE": "RUN", "QUERY": query}).encode()
    raw, job = http_get(base + "/async", data=body, tries=2)
    if job.rstrip("/").endswith("/async"):
        m = re.search(r"<uws:jobId>\s*([^<\s]+)\s*</uws:jobId>", _text(raw))
        if not m:
            raise RuntimeError("TAP async: no job URL")
        job = base + "/async/" + m.group(1)
    t0 = time.time()
    kicked = False
    while True:
        ph = _text(http_get(job + "/phase")[0]).strip().upper()
        if ph == "COMPLETED":
            break
        if ph in ("ERROR", "ABORTED"):
            raise RuntimeError("TAP async job %s" % ph)
        if ph == "PENDING" and not kicked:
            http_get(job + "/phase", data=b"PHASE=RUN", tries=2)
            kicked = True
        if time.time() - t0 > max_wait:
            raise RuntimeError("TAP async timeout")
        time.sleep(poll)
    raw, _ = http_get(job + "/results/result", timeout=900)
    return list(csv.DictReader(io.StringIO(_text(raw))))


def tap_ids(query_fmt, ids, schema, chunk=150):
    out = []
    for i in range(0, len(ids), chunk):
        out += tap_sync(query_fmt.format(s=schema, ids=",".join(ids[i:i + chunk])))
    return out


def discover(schema):
    tabs = ("nss_two_body_orbit", "gaia_source", "nss_masses", "binary_masses",
            "vari_eclipsing_binary", "vari_classifier_result")
    q = ("SELECT table_name, column_name FROM tap_schema.columns WHERE table_name IN (%s)"
         % ",".join("'%s.%s'" % (schema, t) for t in tabs))
    cols = {}
    for r in tap_sync(q):
        t = str(r.get("table_name", "")).split(".")[-1].strip().lower()
        cols.setdefault(t, set()).add(str(r.get("column_name", "")).strip().lower())
    return cols


def schema_gate(cols):
    nss, gs = cols.get("nss_two_body_orbit", set()), cols.get("gaia_source", set())
    return "OK" if all(c in nss for c in REQ_ORB) and all(c in gs for c in REQ_GS) else "G0"


def masses_table(cols):
    for t in ("nss_masses", "binary_masses"):
        if {"source_id", "m1"} <= cols.get(t, set()):
            return t
    return None


def fetch_epochs(sid, template, cache_dir=None):
    path = os.path.join(cache_dir, "%s.csv" % sid) if cache_dir else None
    if path and os.path.exists(path):
        with open(path, newline="") as fh:
            return [(float(r["t"]), float(r["mag"]), r["rej"] == "1") for r in csv.DictReader(fh)]
    raw, _ = http_get(template.format(sid=sid), accept_404=True)
    ep = []
    for text in decode_payload(raw) if raw else []:
        ep += parse_epoch_csv(text)
    if path:
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["t", "mag", "rej"])
            for t, m, rej in ep:
                w.writerow([repr(t), repr(m), "1" if rej else "0"])
    return ep


def choose_template(templates):
    tried = []
    for tpl in templates:
        try:
            ep = fetch_epochs(CONTROL_SID, tpl)
            t, _ = usable(ep)
            span = (t[-1] - t[0]) if t else 0.0
            tried.append({"template": tpl, "n": len(t), "span": span})
            if len(t) >= CONTROL_MIN_EPOCHS and span >= CONTROL_MIN_SPAN_D:
                return tpl, tried
        except Exception as exc:
            tried.append({"template": tpl, "error": repr(exc)[:200]})
    return None, tried


def vet_lookups(rec):
    """VSX, SIMBAD (Harvard mirror) and VizieR TESS EB / TESS Ten Thousand cones. None = no answer."""
    import sb2_screen_dr4 as g5          # repository module; imported only on release day
    s0 = g5.s0
    ra, dec = fnum(rec.get("ra")), fnum(rec.get("dec"))
    try:
        v = s0.get_json(s0.VSX_URL % (ra, dec, s0.VSX_RADIUS_DEG))
        objs = s0.vsx_objects(v) if v is not None else None
        rec["vsx_ecl"] = (any(s0.is_eclipsing_type(o.get("VariabilityType")) for o in objs)
                          if objs is not None else None)
    except Exception:
        rec["vsx_ecl"] = None
    try:
        eb, _ = s0.simbad_flags(g5.get_text(s0.SIMBAD % (ra, dec, s0.SIMBAD_RADIUS_ARCSEC)))
        rec["simbad_eb"] = eb
    except Exception:
        rec["simbad_eb"] = None
    ctrl = vet_lookups.ctrl
    for key, _ in g5.VIZ_CATS:
        rec[key] = g5.viz_lookup(ctrl.get(key), ra, dec, "", None) if ctrl.get(key) else None
    return rec


vet_lookups.ctrl = {}


def read_rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(path, recs):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ROW_KEYS, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            w.writerow({k: fmt(r.get(k)) for k in ROW_KEYS})


def run_chunk(a):
    os.makedirs(a.out_dir, exist_ok=True)
    t_start = time.time()
    meta = {"version": VERSION, "schema": a.schema, "chunk": a.chunk, "n_chunks": a.n_chunks,
            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    out_sum = os.path.join(a.out_dir, "g8_chunk_%d_summary.json" % a.chunk)

    def finish(code, **kw):
        meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        meta["exit_code"] = code
        kw["meta"] = meta
        with open(out_sum, "w") as fh:
            json.dump(clean(kw), fh, indent=1)
        return code

    ok, bad = self_test()
    if not ok:
        return finish(3, error="self-test failed %s" % bad)
    try:
        cols = discover(a.schema)
    except Exception as exc:
        return finish(2, error="TAP_SCHEMA unavailable: %r" % exc)
    meta["columns"] = {k: sorted(v) for k, v in cols.items()}
    if schema_gate(cols) == "G0":
        return finish(4, error="schema gate G0: required orbit columns missing")
    tpl = a.datalink_template or None
    tpl, tried = (tpl, []) if tpl else choose_template(DATALINK_TEMPLATES)
    meta["datalink_tried"] = tried
    if tpl is None:
        return finish(2, error="no DataLink template returned DR4 epochs for the control star")
    meta["datalink_template"] = tpl
    try:
        rows = tap_async(ORBIT_QUERY.format(s=a.schema))
    except Exception as exc:
        return finish(2, error="orbit query failed: %r" % exc)
    seen, sample = set(), []
    for r in rows:
        sid = str(r.get("source_id", "")).strip()
        P, k1, k2 = fnum(r.get("period")), fnum(r.get("semi_amplitude_primary")), \
            fnum(r.get("semi_amplitude_secondary"))
        if not sid.isdigit() or sid in seen or not (P_MIN <= P <= P_MAX and k1 > 0 and k2 > 0):
            continue
        seen.add(sid)
        if chunk_of(sid, a.n_chunks) == a.chunk:
            sample.append(r)
    sample.sort(key=lambda r: hash32(r["source_id"]))
    meta.update({"n_orbit_rows": len(rows), "n_sb2_unique": len(seen), "n_chunk": len(sample)})
    log("orbits", len(rows), "unique", len(seen), "chunk", len(sample))
    ids = [r["source_id"] for r in sample]
    flags = {"gaia_eb": set(), "gaia_ecl_sol": set(), "gaia_class": {}}
    flags_ok = {"gaia_eb": True, "gaia_ecl_sol": True, "gaia_class": True}
    try:
        flags["gaia_eb"] = {r["source_id"] for r in tap_ids(
            "SELECT source_id FROM {s}.vari_eclipsing_binary WHERE source_id IN ({ids})", ids, a.schema)}
    except Exception as exc:
        flags_ok["gaia_eb"] = False
        meta["gaia_eb_error"] = repr(exc)[:200]
    try:
        flags["gaia_ecl_sol"] = {r["source_id"] for r in tap_ids(
            "SELECT source_id FROM {s}.nss_two_body_orbit WHERE source_id IN ({ids}) "
            "AND nss_solution_type LIKE '%clipsing%'", ids, a.schema)}
    except Exception as exc:
        flags_ok["gaia_ecl_sol"] = False
        meta["gaia_ecl_sol_error"] = repr(exc)[:200]
    try:
        for r in tap_ids("SELECT source_id, best_class_name FROM {s}.vari_classifier_result "
                         "WHERE source_id IN ({ids})", ids, a.schema):
            flags["gaia_class"][r["source_id"]] = r.get("best_class_name", "")
    except Exception as exc:
        flags_ok["gaia_class"] = False
        meta["gaia_class_error"] = repr(exc)[:200]
    m1 = {}
    mt = masses_table(cols)
    meta["masses_table"] = mt
    if mt:
        try:
            for r in tap_ids("SELECT source_id, m1 FROM {s}.%s WHERE source_id IN ({ids})" % mt,
                             ids, a.schema):
                v = fnum(r.get("m1"))
                if math.isfinite(v) and v > 0 and r["source_id"] not in m1:
                    m1[r["source_id"]] = v
        except Exception as exc:
            meta["masses_error"] = repr(exc)[:200]
    crowd, crowd_ok = {}, True
    bright_ids = [r["source_id"] for r in sample if fnum(r.get("phot_g_mean_mag"), 99) <= CROWD_G_MAX]
    try:
        q = ("SELECT t.source_id, SUM(POWER(10.0, -0.4 * (n.phot_g_mean_mag - t.phot_g_mean_mag))) "
             "AS flux_ratio FROM {s}.gaia_source AS t JOIN {s}.gaia_source AS n ON 1 = CONTAINS("
             "POINT('ICRS', n.ra, n.dec), CIRCLE('ICRS', t.ra, t.dec, " + repr(CROWD_RADIUS_DEG) +
             ")) WHERE t.source_id IN ({ids}) AND n.source_id <> t.source_id AND "
             "n.phot_g_mean_mag IS NOT NULL GROUP BY t.source_id")
        for r in tap_ids(q, bright_ids, a.schema, chunk=100):
            crowd[r["source_id"]] = fnum(r.get("flux_ratio"), 0.0)
    except Exception as exc:
        crowd_ok = False
        meta["crowd_error"] = repr(exc)[:200]
    if a.cache_dir:
        os.makedirs(a.cache_dir, exist_ok=True)
    recs = []
    deadline = t_start + 60.0 * a.deadline_minutes
    for n, r in enumerate(sample):
        if time.time() > deadline:
            meta["stopped_at_deadline"] = n
            break
        sid = r["source_id"]
        P = fnum(r.get("period"))
        e = fnum(r.get("eccentricity"))
        om = fnum(r.get("arg_periastron"))
        k1, k2 = fnum(r.get("semi_amplitude_primary")), fnum(r.get("semi_amplitude_secondary"))
        G = fnum(r.get("phot_g_mean_mag"))
        ms = m1sin3i(k1, k2, P, e)
        cls = flags["gaia_class"].get(sid, "")
        rec = {"source_id": sid, "chunk": a.chunk, "G": G, "ra": fnum(r.get("ra")),
               "dec": fnum(r.get("dec")), "P": P, "e": e, "omega": om,
               "sol_type": r.get("nss_solution_type", ""), "K1": k1, "K2": k2, "m1sin3i": ms,
               "m1": m1.get(sid, float("nan")),
               "s3": ms / m1[sid] if sid in m1 else float("nan"),
               "crowd": (crowd.get(sid, 0.0) if crowd_ok else None) if G <= CROWD_G_MAX else None,
               "gaia_eb": (sid in flags["gaia_eb"]) if flags_ok["gaia_eb"] else None,
               "gaia_ecl_sol": (sid in flags["gaia_ecl_sol"]) if flags_ok["gaia_ecl_sol"] else None,
               "gaia_class": cls,
               "gaia_class_ecl": (str(cls).upper().startswith("ECL")) if flags_ok["gaia_class"] else None}
        try:
            t, m = usable(fetch_epochs(sid, tpl, a.cache_dir))
            rec["n_epochs"] = len(t)
            rec["span_d"] = (t[-1] - t[0]) if t else 0.0
            for rname, ref in REFS:
                tp = ref + fnum(r.get("t_periastron"))
                c = classify(t, m, P, tp, e, om)
                cn = classify(t, m, P, tp, e, om, shift=NULL_SHIFT)
                rec.update({"%s_label" % rname: c["label"], "%s_null_label" % rname: cn["label"],
                            "%s_n_dips" % rname: c["n_dips"], "%s_n_in" % rname: c["n_in"],
                            "%s_n_events" % rname: c["n_events"], "%s_depth" % rname: c["depth"],
                            "%s_model" % rname: c["model"]})
            rec["status"] = "OK"
        except Exception as exc:
            rec["status"] = "ERROR"
            rec["error"] = repr(exc)[:300]
        recs.append(rec)
        if (n + 1) % 200 == 0:
            log("[%d/%d]" % (n + 1, len(sample)))
            write_rows(os.path.join(a.out_dir, "g8_chunk_%d.csv" % a.chunk), recs)
        time.sleep(PAUSE)
    # vetting lookups for every candidate under either reference
    cands = [x for x in recs if any(x.get("%s_label" % rn) in ("ECL_GAIA", "ECL_GAIA_SHALLOW")
                                    for rn, _ in REFS)]
    meta["n_candidates_any_ref"] = len(cands)
    try:
        import sb2_screen_dr4 as g5
        vet_lookups.ctrl = {k: g5.viz_setup(cat) for k, cat in g5.VIZ_CATS}
        meta["viz_controls"] = vet_lookups.ctrl
        for x in cands:
            vet_lookups(x)
            time.sleep(PAUSE)
    except Exception as exc:
        meta["vet_error"] = repr(exc)[:200]
    path = os.path.join(a.out_dir, "g8_chunk_%d.csv" % a.chunk)
    write_rows(path, recs)
    if a.results_dir:
        os.makedirs(a.results_dir, exist_ok=True)
        write_rows(os.path.join(a.results_dir, "g8_chunk_%d.csv" % a.chunk), recs)
    n_ok = sum(1 for x in recs if x.get("status") == "OK")
    meta["n_processed"] = len(recs)
    meta["n_ok"] = n_ok
    return finish(0 if n_ok >= 1 else 2, chunk_grades=grade_all(recs))


def run_combine(a):
    os.makedirs(a.out_dir, exist_ok=True)
    recs, files = [], []
    for name in sorted(os.listdir(a.results_dir)):
        if re.fullmatch(r"g8_chunk_\d+\.csv", name):
            files.append(name)
            recs += read_rows(os.path.join(a.results_dir, name))
    g = grade_all(recs)
    g["files"] = files
    g["version"] = VERSION
    with open(os.path.join(a.out_dir, "g8_summary.json"), "w") as fh:
        json.dump(clean(g), fh, indent=1)
    ref = g["ref"]
    L = "%s_label" % ref
    cand = [x for x in recs if x.get(L) in ("ECL_GAIA", "ECL_GAIA_SHALLOW")]
    for x in cand:
        x["blind"] = blind_of(x)
        x["vet"] = vet_status(x)
    keys = ROW_KEYS + ["blind", "vet"]
    with open(os.path.join(a.out_dir, "g8_candidates.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for x in cand:
            w.writerow({k: fmt(x.get(k)) if not isinstance(x.get(k), str) else x.get(k) for k in keys})
    print(json.dumps(clean({k: g[k].get("label") if isinstance(g[k], dict) and "label" in g[k] else
                            g[k] for k in ("ref", "interpreted", "R1", "N1", "B1", "M1", "MAIN")})))
    return 0


def clean(o):
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, set):
        return sorted(clean(v) for v in o)
    return o


# ================================================================ DR3 rehearsal (not blind)
def rehearse_dr3(a):
    """Run the rule on the DR3 epochs saved by gaia_conj_dips (0.1.0), gaia_conj_dips_acv (0.1.0) and
    gaia_conj_dips_acv2 (0.1.0) in the repository at REPO_DIR. Reported, not graded."""
    sys.path.insert(0, a.rehearse_dr3)
    import gaia_conj_dips as m0
    import gaia_conj_dips_acv as m1
    import gaia_conj_dips_acv2 as m2
    truth = {}
    tpath = os.path.join(a.rehearse_dr3, "data", "ijspeert2024-check", "ijspeert_check.csv")
    if os.path.exists(tpath):
        for r in read_rows(tpath):
            sid = str(r.get("gaia_dr3", "")).strip()
            if sid:
                v = str(r.get("in_obaf_eb1", "")).strip().lower()
                truth[sid] = "EB" if v == "yes" else ("NOT_EB" if v == "no" else "")
    stars = []
    for sid, o in m0.ORBITS.items():
        ep = [(x["t"], x["mag"], x["rej"]) for x in m0.load_epochs(sid)]
        stars.append((sid, o["name"], o["P"], o["Tp"], o["e"], o["omega"], ep, "gaia_conj_dips"))
    for mod, tag in ((m1, "gaia_conj_dips_acv"), (m2, "gaia_conj_dips_acv2")):
        for sid, (name, P, _pe, Tp, _te, e, om) in mod.ORBITS.items():
            ep = [(t, mg, bool(rp) or bool(rv)) for t, mg, rp, rv in mod.load_epochs(sid)
                  if t is not None and mg is not None]
            stars.append((sid, name, P, Tp, e, om, ep, tag))
    out = []
    for sid, name, P, Tp, e, om, ep, tag in stars:
        t, m = usable(ep)
        tp = 2191.5 + Tp
        c = classify(t, m, P, tp, e, om)
        cn = classify(t, m, P, tp, e, om, shift=NULL_SHIFT)
        out.append({"source_id": sid, "name": name, "set": tag, "P": P, "n": len(t),
                    "truth": truth.get(sid, ""), "label": c["label"], "null_label": cn["label"],
                    "n_dips": c["n_dips"], "n_in": c["n_in"], "n_out": c["n_out"],
                    "n_events": c["n_events"], "model": c["model"], "sd": c["sd"],
                    "thr": c["thr"], "depth": c["depth"], "dips": c["dips"]})
    flagged = {"ECL_GAIA", "ECL_GAIA_SHALLOW"}
    eb = [x for x in out if x["truth"] == "EB"]
    summary = {
        "version": VERSION, "mode": "rehearse-dr3 (not blind; reported, not graded)",
        "n_stars": len(out),
        "labels": {lab: sum(1 for x in out if x["label"] == lab)
                   for lab in ("ECL_GAIA", "ECL_GAIA_SHALLOW", "NONE", "FEW_EPOCHS")},
        "null_labels": {lab: sum(1 for x in out if x["null_label"] == lab)
                        for lab in ("ECL_GAIA", "ECL_GAIA_SHALLOW", "NONE", "FEW_EPOCHS")},
        "known_eb": {"n": len(eb), "n_ecl": sum(1 for x in eb if x["label"] == "ECL_GAIA"),
                     "n_flagged": sum(1 for x in eb if x["label"] in flagged),
                     "names_flagged": [x["name"] for x in eb if x["label"] in flagged],
                     "names_missed": [x["name"] for x in eb if x["label"] not in flagged]},
        "flagged_not_known_eb": [x["name"] for x in out if x["label"] in flagged
                                 and x["truth"] != "EB"],
    }
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "g8_rehearsal_dr3.json"), "w") as fh:
        json.dump(clean({"summary": summary, "stars": out}), fh, indent=1)
    print(json.dumps(clean(summary), indent=1))
    for x in out:
        print(x["name"], x["truth"] or "-", x["label"], "null", x["null_label"], "dips",
              x["n_dips"], "in", x["n_in"], "ev", x["n_events"], "model", x["model"])
    return 0


# ================================================================ self-test
def synth(seed, P=3.0, n_pairs=100, span=2000.0, noise=0.004, depth1=0.0, depth2=0.0,
          half_width=0.025, ell=0.0, shallow=False):
    """Gaia-like sampling (pairs 106 min apart). Circular orbit, conjunctions at 0.25 / 0.75."""
    rng = random.Random(seed)
    times = []
    for _ in range(n_pairs):
        t = rng.uniform(0.0, span)
        times += [t, t + 0.0740]
    times.sort()
    mags = []
    for t in times:
        ph = (t / P) % 1.0
        m = 12.0 + rng.gauss(0.0, noise) + ell * math.cos(4.0 * math.pi * (ph - 0.25))
        if abs(dphase(ph, 0.25)) <= half_width:
            m += depth1
        if abs(dphase(ph, 0.75)) <= half_width:
            m += depth2
        mags.append(m)
    return times, mags


def self_test():
    checks = []
    t, m = synth(1, depth1=0.30, depth2=0.15)
    c = classify(t, m, 3.0, 0.0, None, None)
    checks.append(c["label"] == "ECL_GAIA" and c["n_events"] >= 2)
    cn = classify(t, m, 3.0, 0.0, None, None, shift=NULL_SHIFT)
    checks.append(cn["label"] == "NONE")
    t, m = synth(2, ell=0.05, noise=0.003)
    checks.append(classify(t, m, 3.0, 0.0, None, None)["label"] == "NONE")
    t, m = synth(3)
    checks.append(classify(t, m, 3.0, 0.0, None, None)["label"] == "NONE")
    checks.append(classify(t[:15], m[:15], 3.0, 0.0, None, None)["label"] == "FEW_EPOCHS")
    t, m = synth(4, depth1=0.015, depth2=0.015, half_width=0.015, noise=0.002)
    checks.append(classify(t, m, 3.0, 0.0, None, None)["label"] == "ECL_GAIA_SHALLOW")
    c1, c2 = conjunction_phases(None, None)
    checks.append(abs(c1 - 0.25) < 1e-12 and abs(c2 - 0.75) < 1e-12)
    checks.append(abs(eval_fourier(fit_fourier([i / 40.0 for i in range(40)],
                                               [1.0 + 0.3 * math.cos(2 * math.pi * i / 40.0)
                                                for i in range(40)]), 0.0) - 1.3) < 1e-9)
    checks.append(chunk_of("66729880383767168", 8) == chunk_of("66729880383767168", 8))
    rows = parse_epoch_csv("source_id,band,time,mag,rejected_by_photometry,rejected_by_variability\n"
                           "1,G,1700.5,10.1,false,false\n1,BP,1700.5,10.4,false,false\n"
                           "1,G,1701.5,10.3,false,true\n")
    checks.append(rows == [(1700.5, 10.1, False), (1701.5, 10.3, True)])
    rows = parse_epoch_csv('source_id,g_transit_time,g_transit_mag,variability_flag_g_reject\n'
                           '1,"(1.0, 2.0, 3.0)","(10.0, 10.5, )","(false, true, false)"\n')
    checks.append(rows == [(1.0, 10.0, False), (2.0, 10.5, True)])
    ok = all(checks)
    return ok, [i for i, x in enumerate(checks) if not x]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--rehearse-dr3", default="")
    ap.add_argument("--combine", action="store_true")
    ap.add_argument("--chunk", type=int, default=0)
    ap.add_argument("--n-chunks", type=int, default=8)
    ap.add_argument("--schema", default="gaiadr4")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--cache-dir", default="")
    ap.add_argument("--results-dir", default="")
    ap.add_argument("--datalink-template", default="")
    ap.add_argument("--deadline-minutes", type=float, default=300.0)
    a = ap.parse_args(argv)
    if a.self_test:
        ok, bad = self_test()
        print("SELF_TEST", "PASS" if ok else "FAIL", bad)
        return 0 if ok else 3
    if a.rehearse_dr3:
        return rehearse_dr3(a)
    if a.combine:
        return run_combine(a)
    return run_chunk(a)


if __name__ == "__main__":
    sys.exit(main())
