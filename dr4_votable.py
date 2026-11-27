# SPDX-License-Identifier: Apache-2.0
"""dr4_votable 0.1.0 - read VOTABLE replies (TABLEDATA, BINARY, BINARY2) with the standard library only,
and turn them into the CSV text the frozen DR4-day scripts already parse.

gaia-orbit-transits, MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0.

Why: on 27 Nov 2026 the AIP Gaia TAP mirror answered every query with a VOTABLE even when CSV was
requested (job sb2-phase-grade-v1 failed on it), and the Gaia DR4 pre-release sample of DataLink epoch
products is a BINARY2 VOTable with array columns. The DR4-day scripts (sb2_ecl_dr4 0.1.0 and friends)
were frozen before DR4 and parse CSV only. install(module) wraps such a module's decode_payload() so a
VOTABLE reply is converted to CSV (array cells written as "[v1,v2,...]", which their parsers already
split) before the frozen parser sees it. The detection rule itself is untouched.

Usage on DR4 day:
    import sb2_ecl_dr4, dr4_votable
    dr4_votable.install(sb2_ecl_dr4)      # no-op for CSV replies
"""
import base64
import csv
import io
import struct
import xml.etree.ElementTree as ET

VERSION = "0.1.0"

# datatype -> (struct code, bytes per element)
_NUM = {"unsignedByte": ("B", 1), "short": ("h", 2), "int": ("i", 4), "long": ("q", 8),
        "float": ("f", 4), "double": ("d", 8), "floatComplex": ("f", 8), "doubleComplex": ("d", 16)}
_INTS = ("unsignedByte", "short", "int", "long")
_FLOATS = ("float", "double")
_TRUE = {b"T": True, b"t": True, b"1": True, b"F": False, b"f": False, b"0": False}


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _shape(arraysize):
    """arraysize attribute -> (fixed element count, variable?, scalar?)."""
    if arraysize is None or str(arraysize).strip() == "":
        return 1, False, True
    dims = str(arraysize).strip().split("x")
    last = dims[-1]
    fixed = 1
    for d in dims[:-1]:
        fixed *= int(d)
    if last.endswith("*"):
        return fixed, True, False
    return fixed * int(last), False, False


def _field_info(el):
    mult, var, scalar = _shape(el.get("arraysize"))
    return {"name": el.get("name") or el.get("ID") or "", "datatype": el.get("datatype") or "char",
            "mult": mult, "var": var, "scalar": scalar}


def _read_value(buf, pos, f):
    dt = f["datatype"]
    if f["var"]:
        (n,) = struct.unpack_from(">i", buf, pos)
        pos += 4
        n *= f["mult"]
    else:
        n = f["mult"]
    if dt == "char":
        return buf[pos:pos + n].decode("utf-8", "replace").rstrip("\x00"), pos + n
    if dt == "unicodeChar":
        return buf[pos:pos + 2 * n].decode("utf-16-be", "replace").rstrip("\x00"), pos + 2 * n
    if dt == "bit":
        nb = (n + 7) // 8
        bits = [bool(buf[pos + i // 8] & (0x80 >> (i % 8))) for i in range(n)]
        return (bits[0] if f["scalar"] else bits), pos + nb
    if dt == "boolean":
        vals = [_TRUE.get(buf[pos + i:pos + i + 1]) for i in range(n)]
        return (vals[0] if f["scalar"] else vals), pos + n
    if dt not in _NUM:
        raise ValueError("unsupported VOTABLE datatype %r" % dt)
    code, size = _NUM[dt]
    if dt.endswith("Complex"):
        flat = struct.unpack_from(">%d%s" % (2 * n, code), buf, pos)
        vals = [complex(flat[2 * i], flat[2 * i + 1]) for i in range(n)]
    else:
        vals = list(struct.unpack_from(">%d%s" % (n, code), buf, pos))
    return (vals[0] if f["scalar"] else vals), pos + size * n


def _decode_binary(fields, raw, binary2):
    nmask = (len(fields) + 7) // 8 if binary2 else 0
    rows, pos = [], 0
    while pos < len(raw):
        mask = raw[pos:pos + nmask]
        pos += nmask
        row = []
        for j, f in enumerate(fields):
            v, pos = _read_value(raw, pos, f)
            if binary2 and mask[j // 8] & (0x80 >> (j % 8)):
                v = None  # BINARY2 null flag: bytes are present but the value is null
            row.append(v)
        rows.append(row)
    return rows


def _scalar_text(dt, s):
    s = s.strip()
    if s == "":
        return None
    if dt in _INTS:
        try:
            return int(s)
        except ValueError:
            return float(s)
    if dt in _FLOATS:
        return float(s)
    if dt == "boolean":
        return s[:1] in ("T", "t", "1")
    return s


def _decode_tabledata(fields, tabledata):
    rows = []
    for tr in tabledata:
        if _local(tr.tag) != "TR":
            continue
        tds = [td.text or "" for td in tr if _local(td.tag) == "TD"]
        row = []
        for f, s in zip(fields, tds):
            if f["datatype"] in ("char", "unicodeChar"):
                row.append(s.strip() if s.strip() != "" else None)
            elif f["scalar"]:
                row.append(_scalar_text(f["datatype"], s))
            else:
                row.append([_scalar_text(f["datatype"], t) for t in s.split()])
        rows.append(row)
    return rows


def parse_votable(text):
    """VOTABLE text or bytes -> (column names, rows as lists). Raises RuntimeError on QUERY_STATUS=ERROR."""
    blob = text.encode("utf-8") if isinstance(text, str) else text
    root = ET.fromstring(blob)
    for el in root.iter():
        if _local(el.tag) == "INFO" and el.get("name") == "QUERY_STATUS" and el.get("value") == "ERROR":
            raise RuntimeError("TAP/DataLink error: %s" % ((el.text or "").strip() or "ERROR"))
    for table in root.iter():
        if _local(table.tag) != "TABLE":
            continue
        fields = [_field_info(el) for el in table if _local(el.tag) == "FIELD"]
        data = next((el for el in table if _local(el.tag) == "DATA"), None)
        if data is None:
            continue
        names = [f["name"] for f in fields]
        for part in data:
            kind = _local(part.tag)
            if kind == "TABLEDATA":
                return names, _decode_tabledata(fields, part)
            if kind in ("BINARY", "BINARY2"):
                stream = next((el for el in part if _local(el.tag) == "STREAM"), None)
                if stream is None or stream.get("href"):
                    raise NotImplementedError("VOTABLE STREAM by href is not supported")
                if (stream.get("encoding") or "base64") != "base64":
                    raise NotImplementedError("VOTABLE STREAM encoding %r" % stream.get("encoding"))
                raw = base64.b64decode("".join((stream.text or "").split()))
                return names, _decode_binary(fields, raw, kind == "BINARY2")
            if kind == "FITS":
                raise NotImplementedError("VOTABLE FITS serialization is not supported")
        return names, []
    return [], []


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(_cell(x) for x in v) + "]"
    return str(v)


def votable_to_csv(text):
    names, rows = parse_votable(text)
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(names)
    for r in rows:
        w.writerow([_cell(v) for v in r])
    return out.getvalue()


def looks_like_votable(text):
    head = text[:3000] if isinstance(text, str) else text[:3000].decode("utf-8", "replace")
    return head.lstrip().startswith("<") and "<VOTABLE" in head.upper()


def install(module, attr="decode_payload"):
    """Wrap module.<attr>(raw) -> list of texts so VOTABLE texts become CSV. Returns the original."""
    orig = getattr(module, attr)
    if getattr(orig, "_dr4_votable", False):
        return getattr(orig, "__wrapped__")

    def wrapped(raw, *a, **kw):
        return [votable_to_csv(t) if looks_like_votable(t) else t for t in orig(raw, *a, **kw)]

    wrapped.__wrapped__ = orig
    wrapped._dr4_votable = True
    setattr(module, attr, wrapped)
    return orig
