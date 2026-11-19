# SPDX-License-Identifier: Apache-2.0
"""dr4_fetch.py -- fetch Gaia DR4 counterparts and orbits for DR3 targets (stdlib only).

Part of gaia-orbit-transits by MV2 of Munim, Inc. (made with AI agents). Apache-2.0.
Used by calib_dr4_run.py (LEAD 1, findings/2026-11-18-calib-dr4-prereg.md) and later
by the DR4 SB1-reality test. Written 2026-11-18, two weeks before Gaia DR4.

Table names come from ESA's DR4 contents page (cosmos.esa.int/web/gaia/dr4, read
2026-11-18): gaiadr4.dr3_neighbourhood (07.03, TAP, 2,448,832,159 rows) and
gaiadr4.nss_two_body_orbit (10.08, TAP, 5,901,111 rows), plus the bright-source
gaiadr4.nss_two_body_orbit_supp.

0.2.0 (2026-11-19, calib-dr4 amendment 2): the DR3 rehearsal (gaia-calibdr4-reh-v1) showed
that ESA's gaiadr3.dr2_neighbourhood has NO 'source_id' column: its columns are
dr2_source_id, dr3_source_id, angular_distance, magnitude_difference,
proper_motion_propagation. The new-release identifier is '<release>_source_id'. The
new-release id column of a neighbourhood table is therefore resolved from TAP_SCHEMA, from a
fixed ordered list (XMATCH_NEW_ID_CANDIDATES): DR4 'dr4_source_id' then 'source_id'; DR3
'dr3_source_id' then 'source_id'. If neither exists the run stops (SchemaError, exit 4) with
the real column list. Every other table and column is still CHECKED at run time against
TAP_SCHEMA. No silent fallback beyond that fixed list.

The same code runs a DR3 "rehearsal" (schema 'dr3'): identity cross-match, DR3 orbits.
"""
import csv
import io
import math
import time
import urllib.parse
import urllib.request

VERSION = "0.2.0"
TAP_SYNC = "https://gea.esac.esa.int/tap-server/tap/sync"
CHUNK = 150
MATCH_RADIUS_MAS = 1000.0
AMBIG_DMAG = 1.0
JD_J2016 = 2457389.0
BTJD0 = 2457000.0

# Ordered candidates for the NEW-release identifier column of the neighbourhood table.
XMATCH_NEW_ID_CANDIDATES = {
    "dr4": ("dr4_source_id", "source_id"),
    "dr3": ("dr3_source_id", "source_id"),
}

SCHEMAS = {
    "dr4": {
        "release": "gaiadr4",
        "xmatch": "gaiadr4.dr3_neighbourhood",
        "xmatch_new_id": XMATCH_NEW_ID_CANDIDATES["dr4"][0],   # resolved at run time
        "xmatch_old_id": "dr3_source_id",
        "nss": "gaiadr4.nss_two_body_orbit",
        "nss_supp": "gaiadr4.nss_two_body_orbit_supp",
        "gaia_source": "gaiadr4.gaia_source",
    },
    "dr3": {
        "release": "gaiadr3",
        "xmatch": "gaiadr3.dr2_neighbourhood",
        "xmatch_new_id": XMATCH_NEW_ID_CANDIDATES["dr3"][0],   # resolved at run time
        "xmatch_old_id": "dr2_source_id",
        "nss": "gaiadr3.nss_two_body_orbit",
        "nss_supp": None,
        "gaia_source": "gaiadr3.gaia_source",
    },
}
_RESOLVED = {}      # schema -> new-id column confirmed in TAP_SCHEMA during this process

XMATCH_COLS = ("angular_distance", "magnitude_difference")
NSS_REQUIRED = ("source_id", "nss_solution_type", "period", "period_error",
                "t_periastron", "t_periastron_error", "eccentricity", "eccentricity_error",
                "a_thiele_innes", "a_thiele_innes_error", "b_thiele_innes",
                "b_thiele_innes_error", "f_thiele_innes", "f_thiele_innes_error",
                "g_thiele_innes", "g_thiele_innes_error", "corr_vec")
NSS_OPTIONAL = ("c_thiele_innes", "c_thiele_innes_error", "h_thiele_innes",
                "h_thiele_innes_error", "center_of_mass_velocity",
                "center_of_mass_velocity_error", "significance", "goodness_of_fit",
                "bit_index", "parallax", "parallax_error")

# Solution types that carry an astrometric (Thiele-Innes) orbit, in order of preference
# when one source has several. Matched case-insensitively by prefix.
ASTRO_PREF = ("astrospectrosb1", "orbitaltargetedsearchvalidated", "orbital",
              "orbitaltargetedsearch", "orbitalalternativevalidated",
              "orbitalalternative")
# Solution types known to be non-astrometric (spectroscopic / eclipsing only).
NON_ASTRO = ("sb1", "sb2", "sb1c", "sb2c", "eclipsingbinary", "eclipsingspectro",
             "firstdegreetrendsb1", "seconddegreetrendsb1", "acceleration7",
             "acceleration9")


class TapError(RuntimeError):
    """The archive did not answer with a table (down, HTML page, or query error)."""


class SchemaError(RuntimeError):
    """A required table or column is missing; .found holds what the archive has."""

    def __init__(self, msg, found=None):
        super().__init__(msg)
        self.found = found or {}


# ------------------------------------------------------------------ pure helpers
def fnum(x, default=float("nan")):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def chunks(seq, n=CHUNK):
    seq = list(seq)
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def _ids(ids):
    out = []
    for i in ids:
        s = str(i).strip()
        if not s.isdigit():
            raise ValueError(f"not a source_id: {i!r}")
        out.append(s)
    return ",".join(out)


def resolve_new_id(schema, have):
    """The new-release id column of the neighbourhood table: the first name of
    XMATCH_NEW_ID_CANDIDATES[schema] present in `have` (column names), else None."""
    names = {str(c).strip().lower() for c in have}
    for c in XMATCH_NEW_ID_CANDIDATES[schema]:
        if c in names:
            return c
    return None


def set_xmatch_new_id(schema, col):
    """Record the resolved column so every query of this process uses it."""
    if col not in XMATCH_NEW_ID_CANDIDATES[schema]:
        raise ValueError(f"{col!r} is not a registered new-id column for {schema}")
    SCHEMAS[schema]["xmatch_new_id"] = col
    _RESOLVED[schema] = col


def reset_xmatch_new_id():
    """Back to the defaults (tests)."""
    _RESOLVED.clear()
    for schema, cands in XMATCH_NEW_ID_CANDIDATES.items():
        SCHEMAS[schema]["xmatch_new_id"] = cands[0]


def missing_new_id_label(schema):
    return "%s.(%s)" % (SCHEMAS[schema]["xmatch"], " | ".join(XMATCH_NEW_ID_CANDIDATES[schema]))


def adql_columns(table):
    """TAP_SCHEMA query for a table's columns (Gaia stores 'schema.table')."""
    t = table.replace("'", "")
    return ("SELECT column_name, unit, description FROM tap_schema.columns "
            f"WHERE table_name = '{t}'")


def adql_xmatch(schema, old_ids, new_col=None):
    s = SCHEMAS[schema]
    new_col = new_col or s["xmatch_new_id"]
    if new_col not in XMATCH_NEW_ID_CANDIDATES[schema]:
        raise ValueError(f"{new_col!r} is not a registered new-id column for {schema}")
    cols = ", ".join([f"x.{new_col} AS new_id", f"x.{s['xmatch_old_id']} AS old_id"]
                     + [f"x.{c}" for c in XMATCH_COLS])
    return (f"SELECT {cols} FROM {s['xmatch']} AS x "
            f"WHERE x.{s['xmatch_old_id']} IN ({_ids(old_ids)})")


def adql_nss(table, ids, columns):
    cols = ", ".join(f"n.{c}" for c in columns)
    return f"SELECT {cols} FROM {table} AS n WHERE n.source_id IN ({_ids(ids)})"


def adql_ref_epoch(gaia_source, sid):
    return f"SELECT TOP 1 source_id, ref_epoch FROM {gaia_source} WHERE source_id = {_ids([sid])}"


def parse_csv(text):
    """CSV text from TAP -> list of dicts. Raises TapError on HTML / VOTable errors."""
    head = text.lstrip()[:200].lower()
    if head.startswith("<") or "<html" in head:
        raise TapError("archive returned a non-CSV answer: " + text.strip()[:300])
    return list(csv.DictReader(io.StringIO(text)))


def angular_mas(value, unit):
    """angular_distance converted to mas from its TAP_SCHEMA unit."""
    v = fnum(value)
    u = (unit or "mas").strip().lower()
    if u in ("mas", "milliarcsec"):
        return v
    if u in ("arcsec", "asec", "\""):
        return v * 1000.0
    if u in ("deg", "degree", "degrees"):
        return v * 3.6e6
    raise ValueError(f"unknown angular unit {unit!r}")


def pick_match(cands, radius_mas=MATCH_RADIUS_MAS, dmag=AMBIG_DMAG):
    """Choose the new-release counterpart of one old source.

    cands: dicts with new_id, ang_mas, dmag (|G_new - G_old| or nan).
    Returns (new_id or None, status). status: 'ok', 'none' (nothing within radius),
    'ambiguous' (a second candidate within radius whose magnitude is within `dmag` of
    the old source's, or with unknown magnitude difference).
    """
    near = sorted((c for c in cands if math.isfinite(fnum(c.get("ang_mas")))
                   and fnum(c.get("ang_mas")) <= radius_mas),
                  key=lambda c: fnum(c.get("ang_mas")))
    if not near:
        return None, "none"
    for other in near[1:]:
        dm = fnum(other.get("dmag"))
        if not math.isfinite(dm) or abs(dm) < dmag:
            return None, "ambiguous"
    return str(near[0]["new_id"]), "ok"


def resolve_matches(xrows, old_ids, unit="mas"):
    """Cross-match rows (new_id, old_id, angular_distance, magnitude_difference) ->
    {old_id: (new_id or None, status)}. A new source claimed by two of our old sources
    makes both 'ambiguous' (merge)."""
    by_old = {str(o): [] for o in old_ids}
    for r in xrows:
        o = str(r.get("old_id", "")).strip()
        if o in by_old:
            by_old[o].append({"new_id": str(r.get("new_id", "")).strip(),
                              "ang_mas": angular_mas(r.get("angular_distance"), unit),
                              "dmag": fnum(r.get("magnitude_difference"))})
    res = {o: pick_match(c) for o, c in by_old.items()}
    claimed = {}
    for o, (n, st) in res.items():
        if st == "ok":
            claimed.setdefault(n, []).append(o)
    for n, olds in claimed.items():
        if len(olds) > 1:
            for o in olds:
                res[o] = (None, "ambiguous")
    return res


def solution_kind(st):
    """'astro' (Thiele-Innes orbit), 'other' (known non-astrometric) or 'unknown'."""
    s = str(st or "").strip().strip('"').lower()
    if any(s.startswith(p) for p in ASTRO_PREF):
        return "astro"
    if s in NON_ASTRO:
        return "other"
    return "unknown"


def _pref_rank(st):
    s = str(st or "").strip().strip('"').lower()
    best = len(ASTRO_PREF)
    for i, p in enumerate(ASTRO_PREF):
        if s == p:
            return i
        if s.startswith(p):
            best = min(best, i)
    return best


def pick_solution(rows):
    """Among one source's NSS rows, the astrometric/combined solution to test.

    Preference: ASTRO_PREF order, then larger significance. Never chosen by period
    (that would bias towards CONFIRMED). Returns (row or None, n_astro, unknown_types).
    """
    astro = [r for r in rows if solution_kind(r.get("nss_solution_type")) == "astro"]
    unknown = sorted({str(r.get("nss_solution_type")) for r in rows
                      if solution_kind(r.get("nss_solution_type")) == "unknown"})
    if not astro:
        return None, 0, unknown
    astro.sort(key=lambda r: (_pref_rank(r.get("nss_solution_type")),
                              -fnum(r.get("significance"), 0.0)))
    return astro[0], len(astro), unknown


def t_ref_btjd(ref_epoch_yr):
    """BTJD of a Julian-year reference epoch (J2016.0 -> 389.0, J2017.5 -> 936.875)."""
    return (JD_J2016 + (float(ref_epoch_yr) - 2016.0) * 365.25) - BTJD0


def lim_at(P, m1, m2, r1, r2, e, f, rsun_au=0.00465047, year_d=365.25):
    """|cos i| below which the conjunction at true anomaly f eclipses (relative orbit,
    total mass m1 + m2, radii in R_sun). Same geometry as gaia_orbits.eclipse_geometry."""
    P, m1, m2, r1, r2 = (fnum(x) for x in (P, m1, m2, r1, r2))
    e = min(max(fnum(e, 0.0), 0.0), 0.97)
    if not all(math.isfinite(x) for x in (P, m1, m2, r1, r2)) or P <= 0 or m1 + m2 <= 0:
        return float("nan")
    a_au = ((m1 + m2) * (P / year_d) ** 2) ** (1.0 / 3.0)
    rc = a_au * (1.0 - e * e) / (1.0 + e * math.cos(f))
    return min((r1 + r2) * rsun_au / rc, 1.0)


def detect_event(clean, wins_by_key, P, n):
    """calib_window.detect_at (skip_wide=False) that also returns the event time and
    which conjunction matched. clean: [(t, snr, dur_h)]; wins_by_key: {'t1': [(c, sd)],
    't2': [...]}. Returns (snr, z, h, t, key) or None."""
    best = None
    wins = [(k, c, sd) for k in ("t1", "t2") for c, sd in wins_by_key.get(k, [])]
    for tt, snr, dh in clean:
        dh = dh if math.isfinite(fnum(dh)) else 4.0
        for k, c, sd in wins:
            if not (math.isfinite(fnum(sd)) and sd > 0 and math.isfinite(fnum(c))):
                continue
            hw = min(n * sd + dh / 48.0, P / 4.0)
            off = tt - c
            if abs(off) <= hw:
                cand = (snr, off / sd, hw / sd, tt, k)
                if best is None or cand[0] > best[0] or \
                        (cand[0] == best[0] and abs(cand[1]) < abs(best[1])):
                    best = cand
    return best


# ------------------------------------------------------------------ network
def tap_query(adql, url=TAP_SYNC, tries=4, timeout=120):
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                   "QUERY": adql}).encode()
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data,
                                         headers={"User-Agent": "mv2-gaia-orbit-transits"})
            with urllib.request.urlopen(req, timeout=timeout) as fh:
                return parse_csv(fh.read().decode("utf-8", "replace"))
        except Exception as exc:          # network, HTTP or TapError
            last = exc
            time.sleep(10 * (k + 1))
    raise TapError(f"TAP failed after {tries} tries: {last}")


def table_columns(table, query=tap_query):
    """{column: {unit, description, via}} from TAP_SCHEMA; if TAP_SCHEMA lists nothing,
    the header of 'SELECT TOP 1 *' (no units; via='top1'). {} if the table is absent."""
    rows = query(adql_columns(table))
    if rows:
        return {str(r.get("column_name", "")).strip().lower():
                {"unit": r.get("unit", "") or "", "description": r.get("description", "") or "",
                 "via": "tap_schema"} for r in rows}
    try:
        rows = query(f"SELECT TOP 1 * FROM {table}")
    except TapError:
        return {}
    if not rows:
        return {}
    return {str(k).strip().lower(): {"unit": "", "description": "", "via": "top1"}
            for k in rows[0].keys()}


def ensure_xmatch_new_id(schema, query=tap_query):
    """Resolve (once per process) the new-id column of the schema's neighbourhood table
    from TAP_SCHEMA. Raises SchemaError with the real columns if no candidate exists."""
    if schema in _RESOLVED:
        return _RESOLVED[schema]
    table = SCHEMAS[schema]["xmatch"]
    have = table_columns(table, query)
    col = resolve_new_id(schema, have)
    if col is None:
        raise SchemaError("missing: " + missing_new_id_label(schema), {table: sorted(have)})
    set_xmatch_new_id(schema, col)
    return col


def check_schema(schema, query=tap_query):
    """Verify every table/column used. Returns {table: {column: meta}}; raises
    SchemaError listing what exists when anything required is missing. Resolves the
    neighbourhood table's new-id column (XMATCH_NEW_ID_CANDIDATES)."""
    s = SCHEMAS[schema]
    found, missing = {}, []
    need = {s["xmatch"]: (s["xmatch_old_id"],) + XMATCH_COLS,
            s["nss"]: NSS_REQUIRED,
            s["gaia_source"]: ("source_id", "ref_epoch")}
    for table, cols in need.items():
        have = table_columns(table, query)
        found[table] = have
        missing += [f"{table}.{c}" for c in cols if c not in have]
        if table == s["xmatch"]:
            col = resolve_new_id(schema, have)
            if col is None:
                missing.append(missing_new_id_label(schema))
            else:
                set_xmatch_new_id(schema, col)
    if s.get("nss_supp"):
        found[s["nss_supp"]] = table_columns(s["nss_supp"], query)
    if missing:
        raise SchemaError("missing: " + ", ".join(missing),
                          {t: sorted(c) for t, c in found.items()})
    return found


def fetch_matches(schema, old_ids, unit="mas", query=tap_query):
    if schema == "dr3":
        return {str(o): (str(o), "ok") for o in old_ids}, []
    ensure_xmatch_new_id(schema, query)
    rows = []
    for ch in chunks(old_ids):
        rows += query(adql_xmatch(schema, ch))
    return resolve_matches(rows, old_ids, unit), rows


def fetch_orbits(schema, new_ids, available, query=tap_query):
    """All NSS rows for the new ids from the main table (and _supp when present).
    available: {table: {col: meta}} from check_schema. Returns {id: [rows]}."""
    s = SCHEMAS[schema]
    out = {}
    tables = [s["nss"]] + ([s["nss_supp"]] if s.get("nss_supp")
                           and available.get(s["nss_supp"]) else [])
    for table in tables:
        have = available.get(table, {})
        cols = [c for c in NSS_REQUIRED + NSS_OPTIONAL if c in have]
        if "source_id" not in cols:
            continue
        for ch in chunks([i for i in new_ids if i]):
            for r in query(adql_nss(table, ch, cols)):
                r["_table"] = table
                out.setdefault(str(r.get("source_id", "")).strip(), []).append(r)
    return out
