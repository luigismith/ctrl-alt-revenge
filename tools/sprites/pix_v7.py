# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - pipeline v7: aggiunte al post-processo (pixelize.py), dalla prova spike-sprite-v7.

(c) pixelatura: normali a capsula (volumi delle ossa al posto delle sfaccettature), filtro di moda sulle bande,
    linee interne pixel-perfect (niente angoli a L), contorno selettivo (selout) sul lato in luce,
    riduzione della tavolozza dentro le rampe di ogni materiale.
(d) timbri: occhio cyan, sopracciglio, bocca disegnati a pixel e posati sui punti del viso proiettati dalle ossa,
    con tre espressioni (normale, sforzo, dolore); solo sopra i pixel della testa (rispetta chi sta davanti).
(b) scie (smear): nastro che si assottiglia lungo i sotto-istanti del pugno o del piede, dietro lo sprite.
"""
import math

import numpy as np
from scipy import ndimage

N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

# parte -> (osso da, osso a, punto: testa o coda) per l'asse della capsula
CAPSULE = {1: ("pelvis", "spine_03", 0.165), 3: ("upperarm_l", "lowerarm_l", 0.06), 4: ("lowerarm_l", "hand_l", 0.05),
           6: ("upperarm_r", "lowerarm_r", 0.06), 7: ("lowerarm_r", "hand_r", 0.05), 9: ("thigh_l", "calf_l", 0.08),
           10: ("calf_l", "foot_l", 0.06), 12: ("thigh_r", "calf_r", 0.08), 13: ("calf_r", "foot_r", 0.06)}


def shifted(arr, dy, dx, fill):
    H, W = arr.shape[:2]
    out = np.full_like(arr, fill)
    ys = slice(max(dy, 0), H + min(dy, 0))
    yd = slice(max(-dy, 0), H + min(-dy, 0))
    xs = slice(max(dx, 0), W + min(dx, 0))
    xd = slice(max(-dx, 0), W + min(-dx, 0))
    out[yd, xd] = arr[ys, xs]
    return out


# ============================================================== (c) normali a capsula
def capsule_normals(lo, fd, p1, W1, alpha_w):
    """mescola alla normale del render quella di una capsula attorno all'osso della parte (spazio telecamera).
    lo["d"] = profondità lungo la vista; i punti delle ossa in fd sono (u, v, profondità) a 1x."""
    if alpha_w <= 0 or fd is None:
        return lo["n"]
    h, w = lo["alpha"].shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    P = np.stack([(xx + 0.5 - W1 / 2) * p1, (W1 / 2 - yy - 0.5) * p1, -lo["d"]], -1)
    n = lo["n"].copy()
    B = fd["bones"]

    def cam(pt):
        return np.array([(pt[0] - W1 / 2) * p1, (W1 / 2 - pt[1]) * p1, -pt[2]], np.float32)
    for part, (ba, bb, _r) in CAPSULE.items():
        m = lo["alpha"] & (lo["part"] == part)
        if not m.any():
            continue
        a = cam(B[ba][0:3])
        b = cam(B[bb][0:3]) if bb != "spine_03" else cam(B[bb][3:6])
        ab = b - a
        L2 = float((ab * ab).sum()) or 1e-6
        q = P[m]
        t = np.clip(((q - a) * ab).sum(-1) / L2, 0.0, 1.0)
        c = a + t[:, None] * ab
        nc = q - c
        nrm = np.linalg.norm(nc, axis=-1, keepdims=True)
        nc = nc / np.maximum(nrm, 1e-6)
        # dove la profondità non c'è (bordo) resta la normale del render
        mix = (1 - alpha_w) * n[m] + alpha_w * nc
        mix /= np.maximum(np.linalg.norm(mix, axis=-1, keepdims=True), 1e-6)
        n[m] = mix
    return n


# ============================================================== (c) bande: filtro di moda
def band_mode(ids, band, alpha, iters=1):
    """ogni pixel prende la banda più frequente fra gli 8 vicini dello stesso materiale se è maggioranza (>=5 su
    vicinato pieno): bordi delle bande meno seghettati, niente pixel isolati di banda."""
    h, w = ids.shape
    for _ in range(iters):
        new = band.copy()
        valid = alpha & (band >= 0)
        nb_ids = np.stack([shifted(ids, dy, dx, -1) for dy, dx in N8], 0)
        nb_b = np.stack([shifted(band, dy, dx, -9) for dy, dx in N8], 0)
        same = nb_ids == ids[None]
        for bv in np.unique(band[valid]):
            votes = ((nb_b == bv) & same).sum(0)
            cnt_same = same.sum(0)
            take = valid & (band != bv) & (votes >= 5) & (votes * 2 > cnt_same)
            new[take] = bv
        band = new
    return band


# ============================================================== (c) linee pixel-perfect
def pixel_perfect(mask):
    """toglie gli angoli a L delle linee di 1 px: un pixel con esattamente due vicini (8-connessi), uno
    orizzontale e uno verticale, si toglie (i due restano collegati in diagonale). In ordine di scansione,
    così il risultato non cambia se tutta la figura si sposta di un pixel (niente sfarfallio nel respiro)."""
    m = mask.copy()
    H, W = m.shape
    ys, xs = np.nonzero(m)
    for y, x in sorted(zip(ys.tolist(), xs.tolist())):
        if not m[y, x]:
            continue
        nb = [(dy, dx) for dy, dx in N8 if 0 <= y + dy < H and 0 <= x + dx < W and m[y + dy, x + dx]]
        if len(nb) != 2:
            continue
        (a0, a1), (b0, b1) = nb
        horiz = [d for d in nb if d[0] == 0]
        vert = [d for d in nb if d[1] == 0]
        if len(horiz) == 1 and len(vert) == 1:
            m[y, x] = False
    return m


# ============================================================== (c) contorno selettivo
def selout_colors(big, A, Rp, outline_mask, pal, out_rgb, light_dirs=((-1, 0), (0, 1), (-1, 1))):
    """i pixel del contorno sul lato della luce chiave (sopra e a destra) prendono il colore "linea" del materiale
    che toccano; sotto e a sinistra resta il contorno scuro comune (stacco dal fondo notturno)."""
    H, W = A.shape
    ys, xs = np.nonzero(outline_mask)
    for y, x in zip(ys, xs):
        lit = False
        for dy, dx in light_dirs:
            # il pixel di sprite che il contorno tocca sta in basso o a sinistra del contorno -> contorno in alto/destra
            yy, xx = y - dy, x - dx
            if 0 <= yy < H and 0 <= xx < W and A[yy, xx]:
                lit = True
                break
        if not lit:
            continue
        votes = {}
        for dy, dx in N4:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and A[yy, xx] and Rp[yy, xx]:
                votes[Rp[yy, xx]] = votes.get(Rp[yy, xx], 0) + 1
        if not votes:
            continue
        rn = max(votes, key=votes.get)
        if rn in ("GLOW",):
            continue
        r = pal[rn]
        c = r[0]
        big[y, x, :3] = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


# ============================================================== (c) tavolozza per materiale
def reduce_by_ramp(images, max_colors, pal, protect=()):
    """come reduce_palette ma fonde solo toni vicini della STESSA rampa (il meno usato va nel vicino), così i
    materiali non si mescolano. I colori fuori dalle rampe (contorno, riflesso, bagliore) sono protetti."""
    def key(c):
        c = c.lstrip("#")
        return int(c[0:2], 16) * 65536 + int(c[2:4], 16) * 256 + int(c[4:6], 16)
    owner = {}
    for rn, ramp in pal.items():
        if rn in ("OUT", "RIM", "GLOW"):
            continue
        for i, c in enumerate(ramp):
            owner.setdefault(key(c), (rn, i))
    prot = {key(c) for c in protect}
    counts = {}
    for im in images:
        a = im[..., 3] > 0
        px = im[a][:, :3].astype(np.int64) @ np.array([65536, 256, 1])
        k, n = np.unique(px, return_counts=True)
        for kk, nn in zip(k.tolist(), n.tolist()):
            counts[kk] = counts.get(kk, 0) + nn
    remap = {k: k for k in counts}
    live = dict(counts)

    def lab(k):
        rgb = np.array([[(k >> 16) & 255, (k >> 8) & 255, k & 255]], np.float64) / 255.0
        c = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
        M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
        xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
        f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
        return np.array([116 * f[0, 1] - 16, 500 * (f[0, 0] - f[0, 1]), 200 * (f[0, 1] - f[0, 2])])
    while len(live) > max_colors:
        best = None
        by_ramp = {}
        for k in live:
            if k in owner and k not in prot:
                by_ramp.setdefault(owner[k][0], []).append(k)
        for rn, ks in by_ramp.items():
            ks = sorted(ks, key=lambda k: owner[k][1])
            for a_, b_ in zip(ks, ks[1:]):
                d = float(np.linalg.norm(lab(a_) - lab(b_)))
                small = min(live[a_], live[b_])
                cost = d * math.sqrt(small)
                if best is None or cost < best[0]:
                    best = (cost, a_, b_)
        if best is None:
            break
        _, a_, b_ = best
        keep, drop = (a_, b_) if live[a_] >= live[b_] else (b_, a_)
        live[keep] += live.pop(drop)
        for k, v in remap.items():
            if v == drop:
                remap[k] = keep
    return remap, sorted(live.keys(), key=lambda k: -live[k])


# ============================================================== (d) timbri del viso
# griglie disegnate a pixel, rivolte a destra. Origine = primo pixel dell'occhio vicino (cyan).
# B sopracciglio, C cyan, W cyan chiarissimo, g bagliore cyan scuro, k occhio chiuso, M bocca, T denti, s pelle in ombra
FACE = {
    "neutral": {"eye": ["BBBB", ".CW."], "eye_o": (-2, -1), "mouth": ["MMM"], "mouth_o": (-1, 0)},
    "effort": {"eye": ["BBBB", ".CW."], "eye_o": (-2, -1), "mouth": ["MMM", "MTM"], "mouth_o": (-1, 0)},
    "pain": {"eye": ["..BB", "BkkC"], "eye_o": (-2, -1), "mouth": ["MM", "MM"], "mouth_o": (0, 0)},
}
FACE_MATS = ("SKIN", "SKIN_DARK", "EYE_GLOW", "EYE_DARK", "BROW", "NOSE_SHADOW", "MOUTH", "EYE_SOCKET", "BEARD",
             "BEARD_EDGE", "HAIR")


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def face_stamp(sprite, ids, part, depth, fd, ID, pal, expr="neutral", eye="cyan"):
    """posa occhio, sopracciglio e bocca sui punti proiettati (sprite = fotogramma intero, coordinate del render).
    Prima toglie i dettagli del viso venuti dal render (diventano pelle o barba), poi disegna il timbro."""
    h, w = ids.shape
    head = (part == 2) & (sprite[..., 3] > 0)
    feat = np.isin(ids, [ID[k] for k in ("EYE_GLOW", "EYE_DARK", "BROW", "EYE_SOCKET", "MOUTH") if k in ID]) & head
    skin_ids = [ID[k] for k in ("SKIN", "SKIN_DARK") if k in ID]
    beard_ids = [ID[k] for k in ("BEARD", "BEARD_EDGE") if k in ID]
    ys, xs = np.nonzero(feat)
    for y, x in zip(ys, xs):
        # colore del vicino più comune fra pelle e barba
        votes = {}
        for dy, dx in N8:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and not feat[yy, xx] and head[yy, xx] and \
                    (ids[yy, xx] in skin_ids or ids[yy, xx] in beard_ids):
                k = tuple(sprite[yy, xx, :3])
                votes[k] = votes.get(k, 0) + 1
        if votes:
            sprite[y, x, :3] = max(votes, key=votes.get)
            ids[y, x] = ID["SKIN"]
    st = FACE.get(expr, FACE["neutral"])
    brow_ramp = "HAIR" if "HAIR" in pal else ("BEARD" if "BEARD" in pal else "SKIN")
    if eye == "dark":
        # occhio senza bagliore (nemici): pupilla scura e bianco dell'occhio
        cw, cc = _hex(pal["OUT"][0]), _hex(pal["SKIN"][5] if len(pal["SKIN"]) > 5 else pal["SKIN"][4])
    else:
        cc, cw = _hex(pal["GLOW"][2]), _hex(pal["GLOW"][3])
    col = {"B": _hex(pal[brow_ramp][0]), "C": cc, "W": cw,
           "g": _hex(pal["GLOW"][1]) if "GLOW" in pal else _hex(pal["SKIN"][1]), "k": _hex(pal["SKIN"][0]),
           "M": _hex(pal["MOUTH"][0]), "T": _hex(pal[brow_ramp][4]), "s": _hex(pal["SKIN"][1])}
    allowed = np.isin(ids, [ID[k] for k in FACE_MATS if k in ID]) & head
    pts = fd["points"]

    def visible(pt, tol=0.035):
        u, v, d = pt
        x, y = int(math.floor(u)), int(math.floor(v))
        if not (0 <= x < w and 0 <= y < h) or not head[y, x]:
            return False
        return d <= depth[y, x] + tol

    def put(grid, ox, oy, idmap):
        for r, row in enumerate(grid):
            for c, ch in enumerate(row):
                if ch == ".":
                    continue
                x, y = ox + c, oy + r
                if 0 <= x < w and 0 <= y < h and allowed[y, x]:
                    sprite[y, x, :3] = col[ch]
                    ids[y, x] = idmap.get(ch, ids[y, x])
    if visible(pts["eye_r"]):
        ex, ey = int(math.floor(pts["eye_r"][0])), int(math.floor(pts["eye_r"][1]))
        ox, oy = st["eye_o"]
        put(st["eye"], ex + ox + 1, ey + oy + 1, {"B": ID["BROW"], "C": ID["EYE_GLOW"], "W": ID["EYE_GLOW"],
                                                  "k": ID["EYE_DARK"]})
        # bagliore: 1 px cyan scuro sulla pelle sotto l'occhio, se è pelle
        gy, gx = ey + 1, ex
        if 0 <= gy < h and 0 <= gx < w and allowed[gy, gx] and ids[gy, gx] in skin_ids and expr != "pain" \
                and eye != "dark":
            sprite[gy, gx, :3] = col["g"]
    if visible(pts["eye_l"], tol=0.05):
        x, y = int(math.floor(pts["eye_l"][0])), int(math.floor(pts["eye_l"][1]))
        if 0 <= x < w and 0 <= y < h and allowed[y, x]:
            sprite[y, x, :3] = col["B"]
            ids[y, x] = ID["EYE_DARK"]
    # riflesso sulla punta del naso (pelle chiara) e ombra sotto
    nx, ny = int(math.floor(pts["nose"][0])), int(math.floor(pts["nose"][1]))
    if 0 <= ny < h - 1 and 0 <= nx < w and allowed[ny, nx] and ids[ny, nx] in skin_ids:
        sprite[ny, nx, :3] = _hex(pal["SKIN"][4])
        if allowed[ny + 1, nx] and ids[ny + 1, nx] in skin_ids:
            sprite[ny + 1, nx, :3] = _hex(pal["SKIN"][1])
    mx, my = int(math.floor(pts["mouth"][0])), int(math.floor(pts["mouth"][1]))
    if 0 <= my < h and 0 <= mx < w and head[my, mx]:
        ox, oy = st["mouth_o"]
        put(st["mouth"], mx + ox, my + oy, {"M": ID["MOUTH"], "T": ID["MOUTH"]})
    return sprite, ids


# ============================================================== (b) scie
SMEAR_RAMP = {"fist_l": ("GLOW", 1, 3), "fist_r": ("WRAP", 3, 4), "toe_l": ("PANTS", 3, 4), "toe_r": ("PANTS", 3, 4),
              "heel_l": ("BOOTS", 3, 4), "heel_r": ("BOOTS", 3, 4)}


def _catmull(pts, sub=4):
    """punti della scia interpolati con Catmull-Rom: archi lisci invece di spezzate."""
    if len(pts) < 3:
        return pts
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(sub):
            t = k / sub
            t2, t3 = t * t, t * t * t
            q = [0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                        (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)]
            out.append(q)
    out.append(list(pts[-1][:2]))
    return out
SMEAR_W = {"fist_l": 7.0, "fist_r": 6.0, "toe_l": 8.0, "toe_r": 8.0}


def draw_smear(sprite, trail, pal, names, width=None, ramps=None):
    """scia a mezzaluna dietro lo sprite lungo i sotto-istanti del pugno o del piede: sottile dove il colpo
    è partito, larga vicino all'arto; bordo di un tono, anima più chiara. Solo sui pixel vuoti.
    ramps: {punto: [rampa, indice bordo, indice anima]} per cambiare i colori di SMEAR_RAMP (pixel_cfg)."""
    h, w = sprite.shape[:2]
    occupied = sprite[..., 3] > 0
    for nm in names:
        pts = [s_[nm] for s_ in trail if nm in s_]
        if len(pts) < 2:
            continue
        pts = _catmull(pts)
        rn, io, ii = (ramps or {}).get(nm) or SMEAR_RAMP.get(nm, ("HOOD", 4, 5))
        ramp = pal.get(rn) or pal["HOOD"]
        c_out, c_in = _hex(ramp[io]), _hex(ramp[ii])
        W_ = width or SMEAR_W.get(nm, 6.0)
        cover = np.zeros((h, w), bool)
        inner = np.zeros((h, w), bool)
        n = len(pts)
        for i in range(n - 1):
            (u0, v0), (u1, v1) = pts[i][:2], pts[i + 1][:2]
            steps = max(2, int(math.hypot(u1 - u0, v1 - v0) * 2))
            for st in range(steps + 1):
                t = st / steps
                k = (i + t) / (n - 1)
                if k > (0.98 if nm.startswith(("toe", "heel")) else 0.95):
                    continue
                u, v = u0 + (u1 - u0) * t, v0 + (v1 - v0) * t
                if nm.startswith(("toe", "heel")):
                    r = max(0.6, (W_ / 2) * (math.sin(math.pi * min(k, 0.98)) ** 0.5))   # mezzaluna (calci)
                else:
                    r = max(0.6, (W_ / 2) * (k ** 0.8))                                  # cuneo (pugni)
                x0, x1 = int(math.floor(u - r)), int(math.ceil(u + r))
                y0, y1 = int(math.floor(v - r)), int(math.ceil(v + r))
                for y in range(max(0, y0), min(h, y1 + 1)):
                    for x in range(max(0, x0), min(w, x1 + 1)):
                        dd = math.hypot(x + 0.5 - u, y + 0.5 - v)
                        if dd <= r:
                            cover[y, x] = True
                            if dd <= r * 0.5 and k > 0.3:
                                inner[y, x] = True
        m = cover & ~occupied
        sprite[m] = (*c_out, 255)
        sprite[m & inner] = (*c_in, 255)
    return sprite


# ============================================================== normal map (luci dinamiche nel gioco)
def normal_image(sprite, lo):
    """normal map dello sprite a 1x: RGB = 0,5 + 0,5 * normale (x destra, y su, z verso chi guarda: convenzione
    "OpenGL", Y+, quella delle CanvasTexture di Godot 4), A = alfa dello sprite. Dentro la sagoma la normale di
    ombreggiatura (render + capsule); sul contorno la direzione verso l'esterno, mezza inclinata (luce di taglio);
    scie e pixel aggiunti: piatta."""
    h, w = sprite.shape[:2]
    a = sprite[..., 3] > 0
    n = np.zeros((h, w, 3), np.float32)
    n[..., 2] = 1.0
    inside = lo["alpha"] & a
    n[inside] = lo["n"][inside]
    edge = a & ~lo["alpha"]
    if edge.any():
        from scipy import ndimage as _nd
        _, (iy, ix) = _nd.distance_transform_edt(~lo["alpha"], return_indices=True)
        yy, xx = np.nonzero(edge)
        dx = (xx - ix[yy, xx]).astype(np.float32)
        dy = -(yy - iy[yy, xx]).astype(np.float32)
        ln = np.maximum(np.hypot(dx, dy), 1e-6)
        v = np.stack([dx / ln * 0.85, dy / ln * 0.85, np.full_like(dx, 0.53)], -1)
        n[yy, xx] = v
    n[..., 2] = np.maximum(n[..., 2], 0.15)          # niente normali rivolte all'indietro (pieghe interne)
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = np.clip(np.rint((n * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)
    out[..., 3] = np.where(a, 255, 0).astype(np.uint8)
    return out
