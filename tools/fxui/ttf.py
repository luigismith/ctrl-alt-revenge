# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Scrive un font TrueType (contorni 'glyf') a partire da glifi bitmap, senza librerie esterne.

Ogni pixel diventa un quadrato di 'unit' unità; i pixel adiacenti si fondono in contorni
rettilinei (esterni in senso orario, buchi in senso antiorario, come vuole TrueType).
Con unitsPerEm = 12 * unit, alla dimensione 12 px un pixel del font è un pixel dello schermo.
Il file è deterministico: date fisse, tabelle in ordine, nessun dato variabile.
"""
from __future__ import annotations

import struct
from datetime import datetime, timezone

# ------------------------------------------------------------------------------------
# contorni
# ------------------------------------------------------------------------------------


def _pixels(top: int, rows: list[str]) -> set[tuple[int, int]]:
    """Pixel pieni come (x, y) con y verso l'alto: la riga ad altezza h occupa [h-1, h]."""
    out = set()
    for r, row in enumerate(rows):
        h = top - r
        for c, v in enumerate(row):
            if v == "#":
                out.add((c, h - 1))
    return out


def trace(pixels: set[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    """Traccia i bordi dell'unione dei pixel. Interno sempre a destra del verso di percorrenza."""
    edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for (x, y) in pixels:
        for e in (((x, y), (x, y + 1)), ((x, y + 1), (x + 1, y + 1)),
                  ((x + 1, y + 1), (x + 1, y)), ((x + 1, y), (x, y))):
            rev = (e[1], e[0])
            if rev in edges:
                edges.remove(rev)
            else:
                edges.add(e)
    out: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for a, b in edges:
        out.setdefault(a, []).append(b)
    contours = []
    while out:
        start = min(out)
        b = sorted(out[start])[0]
        out[start].remove(b)
        if not out[start]:
            del out[start]
        pts = [start]
        prev, cur = start, b
        while cur != start:
            pts.append(cur)
            cand = out[cur]
            din = (cur[0] - prev[0], cur[1] - prev[1])
            right = (din[1], -din[0])
            left = (-din[1], din[0])
            # nei punti di sella (pixel che si toccano solo in diagonale) si gira a destra:
            # i due pixel restano contorni separati
            prefs = {right: 0, din: 1, left: 2}
            nxt = min(cand, key=lambda c: prefs.get((c[0] - cur[0], c[1] - cur[1]), 3))
            cand.remove(nxt)
            if not cand:
                del out[cur]
            prev, cur = cur, nxt
        contours.append(_simplify(pts))
    return contours


def _simplify(pts: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Toglie i punti allineati."""
    n = len(pts)
    keep = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        d1 = (p1[0] - p0[0], p1[1] - p0[1])
        d2 = (p2[0] - p1[0], p2[1] - p1[1])
        if d1[0] * d2[1] - d1[1] * d2[0] != 0:
            keep.append(p1)
    return keep


# ------------------------------------------------------------------------------------
# tabelle
# ------------------------------------------------------------------------------------


def _checksum(data: bytes) -> int:
    data = data + b"\0" * ((4 - len(data) % 4) % 4)
    s = 0
    for (v,) in struct.iter_unpack(">I", data):
        s = (s + v) & 0xFFFFFFFF
    return s


def _encode_glyph(contours: list[list[tuple[int, int]]]) -> tuple[bytes, tuple[int, int, int, int], int]:
    if not contours:
        return b"", (0, 0, 0, 0), 0
    pts, ends = [], []
    for c in contours:
        pts.extend(c)
        ends.append(len(pts) - 1)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bb = (min(xs), min(ys), max(xs), max(ys))
    out = struct.pack(">hhhhh", len(contours), *bb)
    out += b"".join(struct.pack(">H", e) for e in ends)
    out += struct.pack(">H", 0)  # niente istruzioni
    flags, xb, yb = bytearray(), bytearray(), bytearray()
    px = py = 0
    for (x, y) in pts:
        dx, dy = x - px, y - py
        px, py = x, y
        f = 0x01  # punto sulla curva
        if dx == 0:
            f |= 0x10
        elif -255 <= dx <= 255:
            f |= 0x02 | (0x10 if dx > 0 else 0)
            xb += struct.pack(">B", abs(dx))
        else:
            xb += struct.pack(">h", dx)
        if dy == 0:
            f |= 0x20
        elif -255 <= dy <= 255:
            f |= 0x04 | (0x20 if dy > 0 else 0)
            yb += struct.pack(">B", abs(dy))
        else:
            yb += struct.pack(">h", dy)
        flags.append(f)
    out += bytes(flags) + bytes(xb) + bytes(yb)
    return out, bb, len(pts)


def _name_table(names: dict[int, str]) -> bytes:
    recs = []
    data = b""
    for nid in sorted(names):
        s = names[nid].encode("utf-16-be")
        recs.append(struct.pack(">HHHHHH", 3, 1, 0x409, nid, len(s), len(data)))
        data += s
    header = struct.pack(">HHH", 0, len(recs), 6 + 12 * len(recs))
    return header + b"".join(recs) + data


def _cmap_table(code_to_gid: dict[int, int]) -> bytes:
    codes = sorted(c for c in code_to_gid if c <= 0xFFFF)
    segs = []
    for c in codes:
        g = code_to_gid[c]
        if segs and c == segs[-1][1] + 1 and g == segs[-1][2] + (c - segs[-1][0]):
            segs[-1][1] = c
        else:
            segs.append([c, c, g])
    segs.append([0xFFFF, 0xFFFF, 0])
    n = len(segs)
    ends = [s[1] for s in segs]
    starts = [s[0] for s in segs]
    deltas = [((s[2] - s[0]) & 0xFFFF) if s[0] != 0xFFFF else 1 for s in segs]
    sr = 2
    es = 0
    while sr * 2 <= 2 * n:
        sr *= 2
        es += 1
    sub = struct.pack(">HHH", 4, 0, 0)  # lunghezza riempita dopo
    sub += struct.pack(">HHHH", 2 * n, sr, es, 2 * n - sr)
    sub += b"".join(struct.pack(">H", e) for e in ends) + struct.pack(">H", 0)
    sub += b"".join(struct.pack(">H", s) for s in starts)
    sub += b"".join(struct.pack(">H", d) for d in deltas)
    sub += b"".join(struct.pack(">H", 0) for _ in segs)
    sub = sub[:2] + struct.pack(">H", len(sub)) + sub[4:]
    head = struct.pack(">HH", 0, 2)
    off = 4 + 8 * 2
    head += struct.pack(">HHI", 0, 3, off) + struct.pack(">HHI", 3, 1, off)
    return head + sub


def _longdatetime(dt: datetime) -> int:
    epoch = datetime(1904, 1, 1, tzinfo=timezone.utc)
    return int((dt - epoch).total_seconds())


def build(glyphs: dict[str, tuple[int, list[str]]], advances: dict[str, int], *,
          family: str, style: str, unit: int, ascent: int, descent: int, em_px: int,
          version: str, copyright_text: str, license_text: str, vendor: str = "CAR ",
          bold: bool = False, x_height: int = 5, cap_height: int = 7) -> bytes:
    """Costruisce il TTF. 'advances' sovrascrive l'avanzamento in px (altrimenti larghezza + 1)."""
    upm = em_px * unit
    chars = sorted((c for c in glyphs if c != " "), key=ord)
    order = [".notdef", " "] + chars
    code_to_gid = {ord(" "): 1}
    for i, c in enumerate(chars):
        code_to_gid[ord(c)] = i + 2

    glyf = b""
    loca = []
    metrics = []
    max_pts = max_ctr = 0
    bbs = []
    for name in order:
        if name == ".notdef":
            # rettangolo vuoto 5x7
            rows = ["#####", "#...#", "#...#", "#...#", "#...#", "#...#", "#####"]
            ctr = trace(_pixels(7, rows))
            adv = 6
        elif name == " ":
            ctr = []
            adv = advances.get(" ", 4)
        else:
            top, rows = glyphs[name]
            ctr = trace(_pixels(top, rows))
            adv = advances.get(name, len(rows[0]) + 1)
        ctr = [[(x * unit, y * unit) for (x, y) in c] for c in ctr]
        data, bb, npts = _encode_glyph(ctr)
        max_pts = max(max_pts, npts)
        max_ctr = max(max_ctr, len(ctr))
        loca.append(len(glyf))
        glyf += data + b"\0" * ((4 - len(data) % 4) % 4)
        lsb = bb[0] if ctr else 0
        metrics.append((adv * unit, lsb, bb if ctr else None))
        if ctr:
            bbs.append(bb)
    loca.append(len(glyf))

    x_min = min(b[0] for b in bbs)
    y_min = min(b[1] for b in bbs)
    x_max = max(b[2] for b in bbs)
    y_max = max(b[3] for b in bbs)
    assert y_max <= ascent * unit and y_min >= -descent * unit, (y_min, y_max)

    when = _longdatetime(datetime(2026, 11, 3, tzinfo=timezone.utc))
    head = struct.pack(">HHIIIHHqqhhhhHHhhh", 1, 0, 0x00010000, 0, 0x5F0F3CF5, 0x000B, upm,
                       when, when, x_min, y_min, x_max, y_max, 1 if bold else 0, em_px, 2, 1, 0)

    adv_max = max(m[0] for m in metrics)
    lsbs = [m[1] for m in metrics if m[2]]
    rsbs = [m[0] - (m[1] + (m[2][2] - m[2][0])) for m in metrics if m[2]]
    extents = [m[1] + (m[2][2] - m[2][0]) for m in metrics if m[2]]
    hhea = struct.pack(">IhhhHhhhhhhhhhhhH", 0x00010000, ascent * unit, -descent * unit, 0,
                       adv_max, min(lsbs), min(rsbs), max(extents), 1, 0, 0, 0, 0, 0, 0, 0,
                       len(order))
    # 'prep' minimo (controllo dei dropout, come nei TTF non hintati comuni). Serve anche a un
    # altro scopo: FreeType applica di suo l'auto-hinter ai TTF senza alcuna istruzione, e
    # l'auto-hinter sposta di un pixel gli accenti isolati. Con un 'prep' usa l'interprete
    # TrueType, che su contorni già allineati alla griglia non cambia nulla.
    prep = bytes([0xB8, 0x01, 0xFF, 0x85, 0xB0, 0x01, 0x8D])  # PUSHW 511 SCANCTRL PUSHB 1 SCANTYPE
    maxp = struct.pack(">IHHHHHHHHHHHHHH", 0x00010000, len(order), max_pts, max_ctr, 0, 0, 2,
                       0, 0, 0, 0, 4, 0, 0, 0)
    hmtx = b"".join(struct.pack(">Hh", m[0], m[1]) for m in metrics)
    loca_b = b"".join(struct.pack(">I", o) for o in loca)

    nonzero = [m[0] for m in metrics if m[0] > 0]
    avg = round(sum(nonzero) / len(nonzero))
    first = min(code_to_gid)
    last = min(max(code_to_gid), 0xFFFF)
    fs_sel = (0x20 if bold else 0x40) | 0x80
    u1 = (1 << 0) | (1 << 1) | (1 << 31)
    u2 = (1 << (45 - 32)) | (1 << (46 - 32))
    os2 = struct.pack(">HhHHH", 4, avg, 700 if bold else 400, 5, 0)
    os2 += struct.pack(">hhhhhhhhhhh", 5 * unit, 5 * unit, 0, 2 * unit, 5 * unit, 5 * unit, 0,
                       4 * unit, unit, 4 * unit, 0)
    os2 += bytes(10)  # PANOSE
    os2 += struct.pack(">IIII", u1, u2, 0, 0)
    os2 += vendor.encode("ascii")[:4].ljust(4)
    os2 += struct.pack(">HHH", fs_sel, first, last)
    os2 += struct.pack(">hhhHH", ascent * unit, -descent * unit, 0, ascent * unit, descent * unit)
    os2 += struct.pack(">II", 1, 0)
    os2 += struct.pack(">hhHHH", x_height * unit, cap_height * unit, 0, 32, 0)
    assert len(os2) == 96

    ps_name = (family + "-" + style).replace(" ", "")
    names = {
        0: copyright_text,
        1: family,
        2: style,
        3: f"{family} {style} {version}",
        4: f"{family} {style}" if style != "Regular" else family,
        5: f"Version {version}",
        6: ps_name,
        13: license_text,
    }
    name = _name_table(names)
    post = struct.pack(">IIhhIIIII", 0x00030000, 0, -unit, unit, 0, 0, 0, 0, 0)
    cmap = _cmap_table(code_to_gid)
    gasp = struct.pack(">HHHH", 1, 1, 0xFFFF, 0x0000)

    tables = {
        b"OS/2": os2, b"cmap": cmap, b"gasp": gasp, b"glyf": glyf, b"head": head,
        b"hhea": hhea, b"hmtx": hmtx, b"loca": loca_b, b"maxp": maxp, b"name": name,
        b"post": post, b"prep": prep,
    }
    tags = sorted(tables)
    n = len(tags)
    sr = 1
    es = 0
    while sr * 2 <= n:
        sr *= 2
        es += 1
    sr *= 16
    out = struct.pack(">IHHHH", 0x00010000, n, sr, es, n * 16 - sr)
    offset = 12 + 16 * n
    dir_entries = b""
    body = b""
    head_off = None
    for t in tags:
        data = tables[t]
        if t == b"head":
            head_off = offset
        dir_entries += struct.pack(">4sIII", t, _checksum(data), offset, len(data))
        padded = data + b"\0" * ((4 - len(data) % 4) % 4)
        body += padded
        offset += len(padded)
    font = bytearray(out + dir_entries + body)
    adj = (0xB1B0AFBA - _checksum(bytes(font))) & 0xFFFFFFFF
    font[head_off + 8:head_off + 12] = struct.pack(">I", adj)
    return bytes(font)


# ------------------------------------------------------------------------------------
# lettura (per la verifica di andata e ritorno, senza FreeType)
# ------------------------------------------------------------------------------------


def read(data: bytes) -> dict:
    """Legge cmap (formato 4), hmtx, loca e glyf di un TTF scritto da build().

    Restituisce {"upm", "cmap": {codice: gid}, "advance": [..], "glyphs": [contorni]},
    con i contorni come liste di punti (x, y) in unità del font.
    """
    n = struct.unpack(">H", data[4:6])[0]
    tables = {}
    for i in range(n):
        tag, cs, off, ln = struct.unpack(">4sIII", data[12 + 16 * i:28 + 16 * i])
        d = data[off:off + ln]
        tables[tag] = d
        if tag == b"head":
            d = d[:8] + b"\0\0\0\0" + d[12:]  # la somma di 'head' si calcola con l'aggiustamento a 0
        assert _checksum(d) == cs, f"somma di controllo errata per {tag!r}"
    assert _checksum(data) == 0xB1B0AFBA, "checkSumAdjustment errato"
    head = tables[b"head"]
    upm = struct.unpack(">H", head[18:20])[0]
    loc_fmt = struct.unpack(">h", head[50:52])[0]
    num_glyphs = struct.unpack(">H", tables[b"maxp"][4:6])[0]
    n_hm = struct.unpack(">H", tables[b"hhea"][34:36])[0]
    hmtx = tables[b"hmtx"]
    advance = [struct.unpack(">H", hmtx[4 * min(i, n_hm - 1):4 * min(i, n_hm - 1) + 2])[0]
               for i in range(num_glyphs)]
    loca_b = tables[b"loca"]
    if loc_fmt == 1:
        loca = [struct.unpack(">I", loca_b[4 * i:4 * i + 4])[0] for i in range(num_glyphs + 1)]
    else:
        loca = [2 * struct.unpack(">H", loca_b[2 * i:2 * i + 2])[0] for i in range(num_glyphs + 1)]
    glyf = tables[b"glyf"]
    glyphs = []
    for g in range(num_glyphs):
        a, b = loca[g], loca[g + 1]
        if a == b:
            glyphs.append([])
            continue
        gd = glyf[a:b]
        nc = struct.unpack(">h", gd[0:2])[0]
        assert nc >= 0, "glifi composti non previsti"
        ends = [struct.unpack(">H", gd[10 + 2 * i:12 + 2 * i])[0] for i in range(nc)]
        p = 10 + 2 * nc
        ilen = struct.unpack(">H", gd[p:p + 2])[0]
        p += 2 + ilen
        npts = ends[-1] + 1
        flags = []
        while len(flags) < npts:
            f = gd[p]
            p += 1
            flags.append(f)
            if f & 0x08:
                rep = gd[p]
                p += 1
                flags.extend([f] * rep)
        coords = []
        for short, same in ((0x02, 0x10), (0x04, 0x20)):
            vals, v = [], 0
            for f in flags:
                if f & short:
                    d = gd[p]
                    p += 1
                    v += d if f & same else -d
                elif not f & same:
                    v += struct.unpack(">h", gd[p:p + 2])[0]
                    p += 2
                vals.append(v)
            coords.append(vals)
        pts = list(zip(*coords))
        assert all(f & 0x01 for f in flags), "punti fuori curva non previsti"
        ctrs, s = [], 0
        for e in ends:
            ctrs.append(pts[s:e + 1])
            s = e + 1
        glyphs.append(ctrs)
    cm = tables[b"cmap"]
    cmap = {}
    nsub = struct.unpack(">H", cm[2:4])[0]
    for i in range(nsub):
        pid, eid, off = struct.unpack(">HHI", cm[4 + 8 * i:12 + 8 * i])
        if (pid, eid) != (3, 1):
            continue
        sub = cm[off:]
        assert struct.unpack(">H", sub[0:2])[0] == 4
        seg2 = struct.unpack(">H", sub[6:8])[0]
        segn = seg2 // 2
        ends_ = struct.unpack(f">{segn}H", sub[14:14 + seg2])
        starts = struct.unpack(f">{segn}H", sub[16 + seg2:16 + 2 * seg2])
        deltas = struct.unpack(f">{segn}h", sub[16 + 2 * seg2:16 + 3 * seg2])
        roffs = struct.unpack(f">{segn}H", sub[16 + 3 * seg2:16 + 4 * seg2])
        for s0, e0, dl, ro in zip(starts, ends_, deltas, roffs):
            assert ro == 0
            for c in range(s0, e0 + 1):
                if c != 0xFFFF:
                    cmap[c] = (c + dl) & 0xFFFF
    return {"upm": upm, "cmap": cmap, "advance": advance, "glyphs": glyphs}
