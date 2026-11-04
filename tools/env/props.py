# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - oggetti di scena di "Sotto la Linea" nel formato sprite della specifica §4.

  python -I tools/env/props.py
Scrive in tools/env/out/props/: bin.png/.json, apple.png/.json, cable.png/.json e le tavole di controllo.

  bin    bidone dell'immondizia: idle (intero), hit (colpito, 2 fotogrammi), break (rotto, 4 fotogrammi,
         l'ultimo 'hold'). Render 3D -> pixel con la stessa vista, luce e palette degli sfondi.
  apple  mela (+30 di vita): idle (2 fotogrammi, il secondo con il luccichio).
  cable  cavo dell'alta tensione strappato in una pozzanghera, scintille animate (6 fotogrammi, loop).
         Si appoggia al pavimento: è dipinto sopra i pixel del piano floor fra x 1222 e 1282, così si
         fonde col suolo; l'ancora è dove il cavo che scende dal palo tocca terra (x 1250, y 150).
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envlib as E  # noqa: E402
import paint as P  # noqa: E402
from materials import M_APPLE, M_BIN, M_BIN_LID, M_LEAF, M_METAL, M_PAPER, M_RUST, M_TRASH, RAMPS  # noqa: E402

C = E.CLS
SCRIPT = os.path.join(E.ROOT, "tools", "blender", "env_gbuffer.py")
OUT = os.path.join(E.OUT, "props")
RAW = os.path.join(E.OUT, "raw_props")
BIN_COL = "#3a4a52"       # lamiera zincata scura (verde-grigio)
CFG = dict(amb=0.7, key=0.8, spill=0.0, spill_sigma=(2.0, 6.0), wet=0, dither=0.0, inner=True, depth_thr=0.06,
           outline=True)


# ------------------------------------------------------------------ geometria con rotazioni libere
def rot(rx=0.0, ry=0.0, rz=0.0):
    ax, ay, az = (math.radians(a) for a in (rx, ry, rz))
    Rx = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    Ry = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    Rz = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def cyl_mesh(r0, r1, h, n=14, z0=0.0, dent=None):
    verts, faces = [], []
    for ring, (rr, zz) in enumerate(((r0, z0), (r1, z0 + h))):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            d = 1.0
            if dent is not None:
                ang0, depth, width = dent
                da = math.atan2(math.sin(a - ang0), math.cos(a - ang0))
                d = 1.0 - depth * math.exp(-(da / width) ** 2) * (0.6 if ring == 1 else 1.0)
            verts.append((rr * d * math.cos(a), rr * d * math.sin(a), zz))
    for k in range(n):
        faces.append((k, (k + 1) % n, n + (k + 1) % n, n + k))
    faces.append(tuple(reversed(range(n))))
    faces.append(tuple(range(n, 2 * n)))
    return verts, faces


def box_mesh(sx, sy, sz):
    v = [(x, y, z) for z in (0, sz) for y in (-sy / 2, sy / 2) for x in (-sx / 2, sx / 2)]
    f = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    return v, f


def place(verts, R, t):
    V = np.array(verts, np.float64) @ np.array(R).T + np.array(t)
    return [list(map(float, p)) for p in V]


def obj(verts, faces, cls, mat, col, R=None, t=(0, 0, 0), smooth=False):
    R = np.eye(3) if R is None else R
    return dict(type="mesh", verts=place(verts, R, t), faces=[list(f) for f in faces], cls=C[cls], mat=mat,
                alb=E.f3(col), smooth=smooth)


# ------------------------------------------------------------------ bidone
BIN_R, BIN_H = 0.25, 0.7


def bin_parts(tilt=0.0, lean_dir=0.0, lid_off=None, dent=None, squash=1.0, pos=(0.0, 0.0, 0.0), side=False):
    """Corpo, nervature, maniglie e coperchio. lid_off = (dx, dy, dz, rx, ry) del coperchio staccato."""
    out = []
    if side:
        R = rot(0, 90, lean_dir)          # sdraiato su un fianco, lungo X
        base = (pos[0], pos[1], pos[2] + BIN_R * 0.92)
    else:
        R = rot(tilt * math.sin(math.radians(lean_dir)), -tilt * math.cos(math.radians(lean_dir)), 0)
        base = pos
    v, f = cyl_mesh(BIN_R * 0.92, BIN_R, BIN_H * squash, n=16, dent=dent)
    out.append(obj(v, f, "METAL", M_BIN, BIN_COL, R, base))
    for zr in (0.22, 0.5):
        v, f = cyl_mesh(BIN_R * 1.03, BIN_R * 1.03, 0.035, n=16, z0=zr * BIN_H * squash, dent=dent)
        out.append(obj(v, f, "METAL", M_METAL, "#465a64", R, base))
    for s in (-1, 1):
        v, f = box_mesh(0.05, 0.12, 0.04)
        out.append(obj(v, f, "METAL", M_METAL, "#2a343c", R, np.array(base) + R @ np.array([s * (BIN_R + 0.02), 0, BIN_H * squash * 0.8])))
    # coperchio
    lv1, lf1 = cyl_mesh(BIN_R * 1.06, BIN_R * 1.06, 0.05, n=16)
    lv2, lf2 = cyl_mesh(BIN_R * 1.0, BIN_R * 0.35, 0.07, n=16, z0=0.05)
    lv3, lf3 = box_mesh(0.14, 0.04, 0.05)
    if lid_off is None:
        Rl = R
        tl = np.array(base) + R @ np.array([0, 0, BIN_H * squash])
    else:
        dx, dy, dz, rx, ry = lid_off
        Rl = rot(rx, ry, 0)
        tl = np.array([dx, dy, dz])
    out.append(obj(lv1, lf1, "METAL", M_BIN_LID, "#4a5c66", Rl, tl))
    out.append(obj(lv2, lf2, "METAL", M_BIN_LID, "#4a5c66", Rl, tl))
    out.append(obj(lv3, lf3, "METAL", M_METAL, "#2a343c", Rl, tl + Rl @ np.array([0, 0, 0.12])))
    return out


def trash_pieces(seed, spread=1.0, n=7, origin=(0.0, 0.0)):
    r = random.Random(seed)
    out = []
    for i in range(n):
        kind = r.random()
        x = origin[0] + r.uniform(-0.15, 0.55) * spread
        y = origin[1] + r.uniform(-0.35, 0.2) * spread
        if kind < 0.35:
            v, f = cyl_mesh(0.035, 0.035, 0.11, n=8)
            out.append(obj(v, f, "METAL", M_RUST, r.choice(["#b8303f", "#3b5fa0", "#c8c0d8"]), rot(0, 90, r.uniform(0, 180)),
                           (x, y, 0.035)))
        elif kind < 0.7:
            v, f = box_mesh(r.uniform(0.12, 0.2), r.uniform(0.08, 0.14), 0.012)
            out.append(obj(v, f, "PAPER", M_PAPER, r.choice(["#aaa1b4", "#857d90", "#cdc4d4"]), rot(0, 0, r.uniform(0, 90)),
                           (x, y, 0.0)))
        else:
            v, f = cyl_mesh(0.11, 0.06, 0.13, n=8)
            out.append(obj(v, f, "TRASH", M_TRASH, "#1a1724", rot(0, 0, 0), (x, y, 0.0)))
    return out


BIN_FRAMES = [
    # nome animazione, indice, oggetti, ticks, extra
    ("idle", dict()),
    ("hit0", dict(tilt=7, lean_dir=0, dent=(math.radians(200), 0.18, 0.6), lid_off=(0.02, 0.0, BIN_H + 0.05, 6, -8))),
    ("hit1", dict(tilt=-3, lean_dir=0, dent=(math.radians(200), 0.18, 0.6))),
    ("break0", dict(tilt=18, lean_dir=0, dent=(math.radians(200), 0.3, 0.7),
                    lid_off=(0.25, -0.05, BIN_H + 0.32, 30, -40))),
    ("break1", dict(tilt=55, lean_dir=0, dent=(math.radians(200), 0.35, 0.8),
                    lid_off=(0.55, -0.1, 0.35, 70, -80), trash=(1, 0.5))),
    ("break2", dict(side=True, lean_dir=-10, dent=(math.radians(200), 0.4, 0.8), pos=(0.12, 0.0, 0.0),
                    lid_off=(0.78, -0.2, 0.0, 6, 8), trash=(2, 1.0))),
    ("break3", dict(side=True, lean_dir=-10, dent=(math.radians(200), 0.45, 0.9), squash=0.9, pos=(0.12, 0.0, 0.0),
                    lid_off=(0.82, -0.22, 0.0, 4, 6), trash=(3, 1.2))),
]


def bin_frame_objects(spec):
    sp = dict(spec)
    trash = sp.pop("trash", None)
    objs = bin_parts(**sp)
    if trash:
        objs += trash_pieces(100 + trash[0], spread=trash[1], n=4 + 2 * trash[0], origin=(0.3, -0.1))
    return objs


# ------------------------------------------------------------------ mela
def apple_objects():
    out = []
    n, rings = 14, 9
    verts, faces = [], []
    R0 = 0.12
    for j in range(rings + 1):
        t = j / rings
        phi = math.pi * t
        rr = R0 * math.sin(phi) * (1.0 + 0.08 * math.sin(phi * 2))
        z = R0 * (1 - math.cos(phi)) * 0.92
        if j in (0, rings):
            rr *= 0.35
        for k in range(n):
            a = 2 * math.pi * k / n
            verts.append((rr * math.cos(a), rr * math.sin(a), z))
    for j in range(rings):
        for k in range(n):
            a, b = j * n + k, j * n + (k + 1) % n
            faces.append((a, b, b + n, a + n))
    faces.append(tuple(reversed(range(n))))
    faces.append(tuple(range(rings * n, rings * n + n)))
    out.append(dict(type="mesh", verts=[list(v) for v in verts], faces=[list(f) for f in faces], cls=C["METAL"],
                    mat=M_APPLE, alb=E.f3("#c42030"), smooth=True))
    v, f = cyl_mesh(0.012, 0.009, 0.07, n=6, z0=0.2)
    out.append(obj(v, f, "WOOD", M_LEAF, "#3b2228", rot(0, 14, 0), (0, 0, 0)))
    leaf = [(0, 0, 0), (0.07, 0.015, 0.02), (0.11, 0.0, 0.045), (0.065, -0.015, 0.05)]
    out.append(dict(type="mesh", verts=[list(map(float, p)) for p in (np.array(leaf) + [0.01, -0.02, 0.24])],
                    faces=[[0, 1, 2, 3]], cls=C["PLANT"], mat=M_LEAF, alb=E.f3("#2e6a3a")))
    return out


# ------------------------------------------------------------------ render e pixel
def render_frame(tag, objects, x0, x1, y0, y1):
    view = dict(yaw=E.YAW, pitch=E.PITCH, ppm=E.PPM, ss=E.SS, x0=x0, x1=x1, y0=y0, y1=y1, oy=0.0)
    job = dict(tag=tag, out_dir=RAW, view=view, objects=objects, kit_dirs={}, p0=[-5.0, -5.0, -5.0], span=20.0)
    E.run_blender(SCRIPT, job, os.path.join(RAW, tag + "_job.json"), timeout=300, log=os.path.join(RAW, tag + ".log"))
    with open(os.path.join(RAW, tag + "_paint.json"), "w") as fh:
        json.dump(dict(ops=[]), fh)


def pixel_frame(tag, extra_pass=None):
    cv = P.load(tag, RAW)
    P.patterns(cv, seed=5)
    if extra_pass:
        extra_pass(cv)
    lit, S = P.shade(cv, CFG)
    q = P.quantize(cv, lit, CFG)
    res, alpha = P.outlines(cv, q, CFG)
    return P.to_rgba(res, alpha), cv


def apple_highlight(cv):
    pass


def pack(frames, pad=1):
    """Impacchetta i fotogrammi (ritagliati al contenuto) in una riga: ritorna atlante e rettangoli."""
    crops = []
    for name, img, anchor in frames:
        al = img[..., 3] > 0
        ys, xs = np.nonzero(al)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        crops.append((name, img[y0:y1, x0:x1], (anchor[0] - x0, anchor[1] - y0)))
    W = sum(c[1].shape[1] for c in crops) + pad * (len(crops) + 1)
    H = max(c[1].shape[0] for c in crops) + 2 * pad
    atlas = np.zeros((H, W, 4), np.uint8)
    rects = {}
    x = pad
    for name, im, anc in crops:
        h, w = im.shape[:2]
        atlas[pad:pad + h, x:x + w] = im
        rects[name] = ([int(x), int(pad), int(w), int(h)], [int(anc[0]), int(anc[1])])
        x += w + pad
    return atlas, rects


def build_bin():
    x0, x1, y0, y1 = -40, 56, -64, 12
    frames = []
    for name, spec in BIN_FRAMES:
        tag = "bin_" + name
        render_frame(tag, bin_frame_objects(spec), x0, x1, y0, y1)
        img, cv = pixel_frame(tag)
        frames.append((name, img, (-x0, -y0)))
    atlas, rects = pack(frames)
    hurt = [[-12, -38, 24, 38]]

    def fr(name, ticks, hurt_=hurt, events=(), tags=()):
        rect, anc = rects[name]
        return dict(rect=rect, anchor=anc, ticks=ticks, hurt=hurt_, hit=[], events=list(events), tags=list(tags), dx=0)

    anims = {
        "idle": dict(loop=True, frames=[fr("idle", 60)]),
        "hit": dict(loop=False, frames=[fr("hit0", 4, events=["sfx:bin_hit"]), fr("hit1", 6), fr("idle", 4)]),
        "break": dict(loop=False, frames=[fr("break0", 4, [], ["sfx:bin_break"]), fr("break1", 5, []),
                                          fr("break2", 6, []), fr("break3", 1, [], (), ["hold"])]),
    }
    # bidone dell'immondizia (x 1050): 'break' finisce su un fotogramma 'hold' (rottame a terra);
    # la mela compare dove era il bidone
    meta = {"id": "bin", "format": 1, "image": "bin.png", "pixels_per_meter": int(E.PPM), "animations": anims}
    save(atlas, meta, "bin")
    return atlas, rects


def build_apple():
    x0, x1, y0, y1 = -20, 20, -28, 6
    render_frame("apple", apple_objects(), x0, x1, y0, y1)
    img, cv = pixel_frame("apple")
    # foglia disegnata in 2D (a 1 px la geometria si perde): due toni di verde sopra a destra
    al0 = img[..., 3] > 0
    ys0, xs0 = np.nonzero(al0)
    ty, tx = ys0.min(), int(np.median(xs0[ys0 == ys0.min()]))
    leaf = {(0, 1): "#5a9a4a", (0, 2): "#5a9a4a", (-1, 2): "#3d7a3e", (-1, 3): "#3d7a3e", (1, 1): "#3d7a3e",
            (-1, 1): "#140e1e", (0, 3): "#140e1e", (-2, 2): "#140e1e", (-2, 3): "#140e1e", (-1, 4): "#140e1e",
            (1, 2): "#140e1e", (0, 0): "#3b2228", (-1, 0): "#3b2228"}
    for (dy, dx), c in leaf.items():
        y, x = ty + dy, tx + dx
        if 0 <= y < img.shape[0] and 0 <= x < img.shape[1] and (c != "#140e1e" or img[y, x, 3] == 0):
            img[y, x] = (*E.hx(c), 255)
    # luccichio: secondo fotogramma con una scintilla bianca a croce in alto a sinistra
    img2 = img.copy()
    al = img[..., 3] > 0
    ys, xs = np.nonzero(al)
    cy, cx = ys.min() + 4, xs.min() + 3
    for (dy, dx) in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
        y, x = cy + dy, cx + dx
        if 0 <= y < img2.shape[0] and 0 <= x < img2.shape[1]:
            img2[y, x] = (*E.hx("#f4eef8"), 255)
    frames = [("idle0", img, (-x0, -y0)), ("idle1", img2, (-x0, -y0))]
    atlas, rects = pack(frames)
    hurt = [[-8, -14, 16, 14]]

    def fr(name, ticks):
        rect, anc = rects[name]
        return dict(rect=rect, anchor=anc, ticks=ticks, hurt=hurt, hit=[], events=[], tags=[], dx=0)

    # mela (+30 di vita): 'hurt' è l'area di raccolta
    meta = {"id": "apple", "format": 1, "image": "apple.png", "pixels_per_meter": int(E.PPM),
            "animations": {"idle": dict(loop=True, frames=[fr("idle0", 50), fr("idle1", 8)])}}
    save(atlas, meta, "apple")
    return atlas


# ------------------------------------------------------------------ cavo nella pozzanghera
CABLE_X0, CABLE_X1 = 1222, 1282
CABLE_ANCHOR = (1250, 150)
PUD_Y0, PUD_Y1 = 146, 212         # la pozza copre tutta la fascia calpestabile (y 150-208)


def build_cable(layers_dir=None, nframes=6):
    """Pozzanghera unica e irregolare che attraversa tutta la fascia (y 146-214) fra x 1222 e 1282, con il cavo
    dell'alta tensione che scende dal palo (ancora in x 1250, y 150), serpeggia nell'acqua e finisce col capo
    spezzato. Deve leggersi subito come un pericolo:
      - archi elettrici bianco-azzurri di 16-24 px che saltano dal capo spezzato;
      - un lampo in 2 fotogrammi su 6 che illumina l'acqua e l'asfalto intorno (luce già dipinta nei fotogrammi,
        perché l'oggetto si disegna sotto gli attori, sopra il pavimento);
      - riflessi azzurri sull'acqua e un bordo chiaro sul cavo, che così si stacca dal fondo scuro.
    Dipinta sopra i pixel del pavimento: fuori dalla pozza l'immagine è trasparente, salvo l'alone del lampo."""
    layers_dir = layers_dir or os.path.join(E.OUT, "layers")
    split = json.load(open(os.path.join(layers_dir, "street_split.json")))
    floor = np.asarray(Image.open(os.path.join(layers_dir, "floor.png")).convert("RGBA"))
    fy = split["floor_y"]
    # l'immagine è più larga della pozza (x 1222-1282): ci sta l'alone del lampo sull'asfalto
    X0, X1 = CABLE_X0 - 18, CABLE_X1 + 18
    Y0, Y1 = 140, 214
    base = floor[Y0 - fy:Y1 - fy, X0:X1].astype(np.float32)
    h, w = base.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]

    ytop, ybot = PUD_Y0 - Y0, PUD_Y1 - Y0
    # una pozza lunga che attraversa la strada: un nucleo arrotondato che copre in ogni riga della fascia la zona
    # del danno (x 1230-1270, vedi prop_cable.gd), così chi prende la scossa sta sempre dentro l'acqua che si
    # vede, più lobi sparsi sui lati e in cima e in fondo che rompono la sagoma
    from scipy import ndimage
    hx0, hx1 = 1230 - X0 - 4, 1270 - X0 + 4
    cy0, cy1 = ytop, ybot
    rad = 6.0
    qx = np.clip(xx, hx0 + rad, hx1 - rad)
    qy = np.clip(yy, cy0 + rad, cy1 - rad)
    shape = (xx - qx) ** 2 + (yy - qy) ** 2 < rad ** 2
    # lobi di misure diverse: piccoli sul marciapiede (in alto), più grandi verso la strada (in basso)
    for (side, fy_, lrx, lry, out) in ((-1, 0.18, 4.0, 3.0, 0.4), (1, 0.30, 5.5, 3.5, 0.5), (-1, 0.55, 7.0, 5.0, 0.6),
                                       (1, 0.72, 9.0, 4.5, 0.7), (-1, 0.86, 11.0, 5.0, 0.8), (1, 0.93, 6.0, 3.0, 0.5)):
        ly = cy0 + fy_ * (cy1 - cy0)
        lx = (hx0 if side < 0 else hx1) + side * lrx * out
        shape |= ((xx - lx) / lrx) ** 2 + ((yy - ly) / lry) ** 2 < 1.0
    # bordo mosso a bassa frequenza su tutto il contorno (niente lati dritti)
    ang = np.arctan2(yy - (cy0 + cy1) / 2.0, (xx - (hx0 + hx1) / 2.0) * 1.4)
    wob = 2.2 * np.sin(5 * ang + 0.8) + 1.4 * np.sin(9 * ang + 2.3)
    dist = ndimage.distance_transform_edt(~shape)
    shape |= dist < np.clip(wob, 0, None)
    inner = ndimage.distance_transform_edt(shape)
    shape &= ~((inner <= np.clip(-wob, 0, None)) & ~((xx >= hx0 + 3) & (xx <= hx1 - 3)))
    shape &= (yy >= ytop) & (yy <= ybot)
    shape = ndimage.binary_closing(shape, structure=np.ones((3, 3), bool))
    shape = ndimage.binary_opening(shape, structure=np.ones((3, 3), bool))
    # controllo: la zona del danno è tutta dentro la pozza nella fascia calpestabile
    hz = (xx >= 1230 - X0) & (xx <= 1270 - X0) & (yy >= 150 - Y0) & (yy <= 208 - Y0)
    assert (shape | ~hz).all(), "la pozza non copre tutta la zona del danno del cavo"
    core = ndi_erode(shape)
    edge = shape & ~core
    top_hi = shape & ~np.roll(shape, 1, 0)

    # acqua: blu-viola scura con riflessi orizzontali azzurri (la luce del cavo e del palo)
    W_ = dict(base="#131a33", deep="#0d0f22", sheen="#22325a", sheen2="#33507e", sheen3="#5a90c0",
              rim="#3a3a5e", lit="#3f6fa8", lit2="#7fc4f0")
    water = np.zeros((h, w, 3), np.uint8)
    water[:] = E.hx(W_["base"])
    water[core & ((yy + xx) % 2 == 0) & (yy > h * 0.55)] = E.hx(W_["deep"])
    rr = np.random.default_rng(1250)
    ph = rr.integers(0, 9, size=h)
    sheen = ((xx + ph[yy] * 3) % 11 < 4) & (yy % 3 == 1)
    water[sheen] = E.hx(W_["sheen"])
    water[sheen & ((xx + 2 * yy) % 9 < 2)] = E.hx(W_["sheen2"])

    # percorso del cavo: dal palo (in alto) fino al capo spezzato nella parte vicina della pozza
    ax = CABLE_ANCHOR[0] - X0
    ay0 = CABLE_ANCHOR[1] - Y0
    path = []
    for tt in np.linspace(0, 1, 260):
        y = ay0 - 1 + tt * 40
        x = ax + 6 * math.sin(tt * 6.0) * (0.25 + tt) - 9 * tt
        path.append((x, y))
    end = path[-1]
    ex, ey = int(round(end[0])), int(round(end[1]))
    CABLE = E.hx("#141221")
    CABLE_EDGE = E.hx("#8a90b8")
    COPPER = E.hx("#ff9a48")
    ARC_CORE = E.hx("#f6fbff")
    ARC_MID = E.hx("#a8e4ff")
    ARC_OUT = E.hx("#4aa8ff")

    def line_pts(p0, p1):
        (x0, y0), (x1, y1) = p0, p1
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        return [(int(round(x0 + (x1 - x0) * i / n)), int(round(y0 + (y1 - y0) * i / n))) for i in range(n + 1)]

    def arc(img, r, x0, y0, length, ang0, jag=1.1):
        """arco a zigzag: anima bianca di 1 px, alone azzurro di 1 px (più scuro dove c'è solo aria)."""
        x, y = float(x0), float(y0)
        ang = ang0
        knots = [(int(x0), int(y0))]
        for i in range(max(2, length // 3)):
            ang += r.uniform(-0.6, 0.6)
            x += math.cos(ang) * 3.0 + r.uniform(-jag, jag)
            y += math.sin(ang) * 3.0 + r.uniform(-jag, jag) * 0.7
            knots.append((int(round(x)), int(round(y))))
        pts = []
        for p0, p1 in zip(knots[:-1], knots[1:]):
            pts += line_pts(p0, p1)
        core = set(pts)
        for (xi, yi) in pts:
            for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                X, Y = xi + dx, yi + dy
                if 0 <= Y < h and 0 <= X < w and (X, Y) not in core:
                    img[Y, X, :3] = ARC_MID if img[Y, X, 3] else ARC_OUT
                    img[Y, X, 3] = 255
        for (xi, yi) in pts:
            if 0 <= yi < h and 0 <= xi < w:
                img[yi, xi, :3] = ARC_CORE
                img[yi, xi, 3] = 255
        return pts

    flash_frames = (0, 3)
    frames = []
    for k in range(nframes):
        flash = k in flash_frames
        img = np.zeros((h, w, 4), np.uint8)
        # alone del lampo sull'asfalto intorno alla pozza (luce azzurra a gradini, senza sfumature)
        if flash:
            d = np.sqrt(((xx - ex) / 1.7) ** 2 + ((yy - ey) * 1.25) ** 2)
            halo = (d < 24) & ~shape
            k1 = halo & (d < 14)
            lit = base[..., :3] * 0.62 + np.array(E.hx("#7fb8f0"), np.float32) * 0.38
            lit2 = base[..., :3] * 0.78 + np.array(E.hx("#5f8ad0"), np.float32) * 0.22
            img[halo, :3] = lit2[halo].astype(np.uint8)
            img[k1, :3] = lit[k1].astype(np.uint8)
            img[halo, 3] = 255
            # bordo dell'alone a scacchi: niente linea dritta fra asfalto illuminato e no
            fringe = halo & (d > 19) & ((xx + yy) % 2 == 0)
            img[fringe, 3] = 0
        img[shape, :3] = water[shape]
        img[shape, 3] = 255
        img[edge, :3] = E.hx(W_["rim"])
        img[top_hi & shape, :3] = E.hx(W_["sheen2"])
        if flash:
            # l'acqua si accende: riflessi chiari vicino al capo spezzato
            dl = np.sqrt(((xx - ex) / 1.4) ** 2 + ((yy - ey) * 1.2) ** 2)
            near = shape & (dl < 20)
            img[near & sheen, :3] = E.hx(W_["lit2"])
            img[near & ~sheen & ((xx + yy) % 2 == 0), :3] = E.hx(W_["lit"])
            img[shape & (dl >= 20) & sheen, :3] = E.hx(W_["sheen3"])
        else:
            # riflesso azzurro tenue e mobile
            refl = shape & sheen & (((xx + k * 2) % 7) < 2)
            img[refl, :3] = E.hx(W_["sheen3"])
        # cavo: 2 px scuri con il bordo chiaro di 1 px sopra (si stacca dall'acqua scura)
        for (x, y) in path:
            xi, yi = int(round(x)), int(round(y))
            for dx in (0, 1):
                if 0 <= yi < h and 0 <= xi + dx < w:
                    img[yi, xi + dx, :3] = CABLE
                    img[yi, xi + dx, 3] = 255
        for (x, y) in path:
            xi, yi = int(round(x)), int(round(y))
            if 0 <= yi - 1 < h and 0 <= xi < w and tuple(img[yi - 1, xi, :3]) != CABLE:
                img[yi - 1, xi, :3] = CABLE_EDGE
                img[yi - 1, xi, 3] = 255
        # increspature intorno al capo
        rad = 3 + (k % 3) * 3
        ring = (np.abs(np.sqrt((xx - ex) ** 2 + ((yy - ey) * 2.2) ** 2) - rad) < 0.6) & shape
        img[ring, :3] = E.hx(W_["sheen3"] if not flash else W_["lit2"])
        # capo spezzato: rame
        for dx in range(-1, 2):
            if 0 <= ey < h and 0 <= ex + dx < w:
                img[ey, ex + dx, :3] = COPPER
                img[ey, ex + dx, 3] = 255
        r = random.Random(1250 + 31 * k)
        if flash:
            # due o tre archi lunghi verso l'alto e di lato
            for i, a0 in enumerate((-math.pi * 0.62, -math.pi * 0.30, -math.pi * 0.85)[:3 if k == 0 else 2]):
                arc(img, r, ex, ey - 1, r.randint(16, 24), a0 + r.uniform(-0.15, 0.15))
            for (dy, dx) in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (-2, 0)):
                yi, xi = ey - 1 + dy, ex + dx
                if 0 <= yi < h and 0 <= xi < w:
                    img[yi, xi, :3] = ARC_CORE if abs(dy) + abs(dx) <= 1 else ARC_MID
                    img[yi, xi, 3] = 255
        else:
            # crepitio: archi corti e qualche scintilla
            for s_ in range(r.randint(2, 3)):
                arc(img, r, ex, ey - 1, r.randint(5, 9), r.uniform(-math.pi * 0.95, -math.pi * 0.05), jag=0.9)
            for s_ in range(r.randint(2, 4)):
                xi = ex + r.randint(-6, 6)
                yi = ey - r.randint(2, 9)
                if 0 <= yi < h and 0 <= xi < w:
                    img[yi, xi, :3] = ARC_MID
                    img[yi, xi, 3] = 255
        frames.append(img)
    pad = 1
    W = (w + pad) * nframes + pad
    atlas = np.zeros((h + 2 * pad, W, 4), np.uint8)
    rects = []
    for k, img in enumerate(frames):
        x = pad + k * (w + pad)
        atlas[pad:pad + h, x:x + w] = img
        rects.append([x, pad, w, h])
    anc = [CABLE_ANCHOR[0] - X0, CABLE_ANCHOR[1] - Y0]
    hit = [[-22, -6, 44, 6]]
    fr = []
    for k in range(nframes):
        ev = ["sfx:zap"] if k == 0 else []
        fr.append(dict(rect=rects[k], anchor=anc, ticks=3 if k in flash_frames else 4, hurt=[], hit=hit,
                       events=ev, tags=["active"], dx=0))
    # ostacolo: si disegna con l'ancora in (x 1250, y 150), sotto gli attori (sta sul suolo), e copre tutta la
    # fascia calpestabile fra x 1224 e 1280; 'hit' è a livello del suolo: il codice lo applica a tutta la
    # profondità della fascia (y 150-208) fra x 1230 e 1270 quando l'attore non è in aria
    meta = {"id": "cable", "format": 1, "image": "cable.png", "pixels_per_meter": int(E.PPM),
            "animations": {"idle": dict(loop=True, frames=fr)}}
    save(atlas, meta, "cable")
    return atlas


def ndi_erode(m):
    from scipy import ndimage
    return ndimage.binary_erosion(m, structure=np.ones((3, 3), bool))


def save(atlas, meta, name):
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(atlas, "RGBA").save(os.path.join(OUT, name + ".png"), optimize=True)
    with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    big = Image.new("RGBA", (atlas.shape[1], atlas.shape[0]), (40, 36, 56, 255))
    big.alpha_composite(Image.fromarray(atlas, "RGBA"))
    big.convert("RGB").resize((atlas.shape[1] * 4, atlas.shape[0] * 4), Image.NEAREST).save(
        os.path.join(OUT, name + "_x4.png"))
    print("[props]", name, atlas.shape[1::-1])


if __name__ == "__main__":
    which = sys.argv[1:] or ["bin", "apple", "cable"]
    os.makedirs(RAW, exist_ok=True)
    if "bin" in which:
        build_bin()
    if "apple" in which:
        build_apple()
    if "cable" in which:
        build_cable()
