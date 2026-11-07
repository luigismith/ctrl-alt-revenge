# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - oggetti di scena di "Sotto la Linea" nel formato sprite della specifica §4.

  python -I tools/env/props.py
Scrive in tools/env/out/props/: bin.png/.json, apple.png/.json e le tavole di controllo.

  bin    bidone dell'immondizia: idle (intero), hit (colpito, 2 fotogrammi), break (rotto, 4 fotogrammi,
         l'ultimo 'hold'). Render 3D -> pixel con la stessa vista, luce e palette degli sfondi.
  apple  mela (+30 di vita): idle (2 fotogrammi, il secondo con il luccichio).

Il cavo scoperto (cable) dal 7 novembre 2026 lo fa tools/ambienti/cavo_rivolo.py.

Scala: 60 px/m (fino al 5 novembre 2026 erano 48). Le misure in pixel scritte qui sono di progetto, a 48 px/m, e
passano per E.px() (floor(p * 1,25 + 0,5)), la stessa regola dei dati del livello; i rettangoli hurt/hit sono
convertiti sui bordi, simmetrici rispetto all'ancora.
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
px = E.px
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
    x0, x1, y0, y1 = px(-40), px(56), px(-64), px(12)
    frames = []
    for name, spec in BIN_FRAMES:
        tag = "bin_" + name
        render_frame(tag, bin_frame_objects(spec), x0, x1, y0, y1)
        img, cv = pixel_frame(tag)
        frames.append((name, img, (-x0, -y0)))
    atlas, rects = pack(frames)
    hurt = [[-px(12), -px(38), 2 * px(12), px(38)]]          # [-15, -48, 30, 48]

    def fr(name, ticks, hurt_=hurt, events=(), tags=()):
        rect, anc = rects[name]
        return dict(rect=rect, anchor=anc, ticks=ticks, hurt=hurt_, hit=[], events=list(events), tags=list(tags), dx=0)

    anims = {
        "idle": dict(loop=True, frames=[fr("idle", 60)]),
        "hit": dict(loop=False, frames=[fr("hit0", 4, events=["sfx:bin_hit"]), fr("hit1", 6), fr("idle", 4)]),
        "break": dict(loop=False, frames=[fr("break0", 4, [], ["sfx:bin_break"]), fr("break1", 5, []),
                                          fr("break2", 6, []), fr("break3", 1, [], (), ["hold"])]),
    }
    # bidone dell'immondizia (x 1313): 'break' finisce su un fotogramma 'hold' (rottame a terra);
    # la mela compare dove era il bidone
    meta = {"id": "bin", "format": 1, "image": "bin.png", "pixels_per_meter": int(E.PPM), "animations": anims}
    save(atlas, meta, "bin")
    return atlas, rects


def build_apple():
    x0, x1, y0, y1 = px(-20), px(20), px(-28), px(6)
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
    hurt = [[-px(8), -px(14), 2 * px(8), px(14)]]            # [-10, -18, 20, 18]

    def fr(name, ticks):
        rect, anc = rects[name]
        return dict(rect=rect, anchor=anc, ticks=ticks, hurt=hurt, hit=[], events=[], tags=[], dx=0)

    # mela (+30 di vita): 'hurt' è l'area di raccolta
    meta = {"id": "apple", "format": 1, "image": "apple.png", "pixels_per_meter": int(E.PPM),
            "animations": {"idle": dict(loop=True, frames=[fr("idle0", 50), fr("idle1", 8)])}}
    save(atlas, meta, "apple")
    return atlas


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
    which = sys.argv[1:] or ["bin", "apple"]
    os.makedirs(RAW, exist_ok=True)
    if "bin" in which:
        build_bin()
    if "apple" in which:
        build_apple()
