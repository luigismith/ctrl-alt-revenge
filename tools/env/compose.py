# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - verifica degli sfondi: composizione dei piani come farà il gioco.

Legge layers.json (formato della specifica §6) e compone l'inquadratura 384x216 per una posizione
intera della telecamera: ogni piano sta in x = floor(-scroll * cam + 0.5) (+ ripetizione), y fisso;
la maschera emissiva si somma (modo additivo). Strumenti:
  mockup   inquadrature con i personaggi della prova v6.1 nella fascia calpestabile (1x e 3x)
  pan      GIF dello scorrimento da 0 a 1536 a passo costante (e striscia di controllo)
  checks   giunzioni dei piani ripetuti, spostamenti interi dei piani (niente tremolio), colori
  sheet    tavola dei piani
  python -I tools/env/compose.py all <cartella con layers.json> <cartella di uscita>
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envlib as E  # noqa: E402

LAB_CHARS = os.path.join(E.LAB, "ricerca-2026-11-03", "prove", "spike2-chars", "out", "v61", "frames", "v61")
LINEUP = os.path.join(E.LAB, "ricerca-2026-11-03", "prove", "spike-anim", "deliverables", "lineup_bodies_final_1x.png")
PROPS_DIR = os.path.join(E.OUT, "props")


def load_layers(d):
    meta = json.load(open(os.path.join(d, "layers.json"), encoding="utf-8"))
    layers = []
    for L in sorted(meta["layers"], key=lambda l: l["z"]):
        im = np.asarray(Image.open(os.path.join(d, L["image"])).convert("RGBA"))
        em = None
        if L.get("emissive"):
            em = np.asarray(Image.open(os.path.join(d, L["emissive"])).convert("RGBA"))
        layers.append(dict(L, img=im, em=em))
    return meta, layers


def layer_x(L, cam):
    return int(np.floor(-L["scroll"] * cam + 0.5))


def blit(dst, src, x, y, add=False):
    H, W = dst.shape[:2]
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    m = s[..., 3] > 0
    d = dst[y0:y1, x0:x1]
    if add:
        d[..., :3][m] = np.clip(d[..., :3][m].astype(np.int32) + s[..., :3][m], 0, 255)
    else:
        d[m] = s[m]


def draw_layer(dst, L, cam, add=False, src=None):
    src = L["img"] if src is None else src
    x = layer_x(L, cam)
    rep = L.get("repeat_x", 0)
    if rep:
        x = x % rep - rep
        while x < dst.shape[1]:
            blit(dst, src, x, L["y"], add)
            x += rep
    else:
        blit(dst, src, x, L["y"], add)


def frame(layers, cam, actors=(), emissive=True, upto_z=None):
    img = np.zeros((E.SCREEN_H, E.SCREEN_W, 4), np.uint8)
    img[..., 3] = 255
    for L in layers:
        if L["z"] > 0:
            continue
        draw_layer(img, L, cam)
        if emissive and L["em"] is not None:
            draw_layer(img, L, cam, add=True, src=L["em"])
    for a in sorted(actors, key=lambda a: a["y"]):
        draw_actor(img, a, cam)
    for L in layers:
        if L["z"] <= 0:
            continue
        draw_layer(img, L, cam)
        if emissive and L["em"] is not None:
            draw_layer(img, L, cam, add=True, src=L["em"])
    return img


# ------------------------------------------------------------------ personaggi della prova
_SPR = {}


def sprite(key):
    if key in _SPR:
        return _SPR[key]
    if key.startswith("gig:"):
        anim, idx = key[4:].split("/")
        im = np.asarray(Image.open(os.path.join(LAB_CHARS, anim, "%s_%02d.png" % (anim, int(idx)))).convert("RGBA"))
        anchor = (63, 119)
    elif key.startswith("prop:"):
        name, anim, idx = key[5:].split("/")
        meta = json.load(open(os.path.join(PROPS_DIR, name + ".json"), encoding="utf-8"))
        atlas = np.asarray(Image.open(os.path.join(PROPS_DIR, meta["image"])).convert("RGBA"))
        fr = meta["animations"][anim]["frames"][int(idx)]
        x, y, w, h = fr["rect"]
        im = atlas[y:y + h, x:x + w]
        anchor = tuple(fr["anchor"])
    else:
        a = np.asarray(Image.open(LINEUP).convert("RGBA")).copy()
        bg = a[0, 0, :3].copy()
        a[(a[..., :3] == bg).all(-1), 3] = 0
        cols = dict(punk=(82, 110), bruiser=(121, 154), punk_jab=(470, 522), bruiser_jab=(531, 586),
                    punk_walk=(254, 282))[key]
        im = a[:, cols[0] - 2:cols[1] + 2]
        al = im[..., 3] > 0
        ys, xs = np.nonzero(al)
        fy = ys.max()
        feet = np.nonzero(al[fy - 2:fy + 1].any(0))[0]
        anchor = (int(feet.mean()), int(fy))
    _SPR[key] = (im, anchor)
    return _SPR[key]


def draw_actor(img, a, cam):
    im, (ax, ay) = sprite(a["spr"])
    if a.get("flip"):
        im = im[:, ::-1]
        ax = im.shape[1] - 1 - ax
    sx = int(a["x"] - cam)
    sy = int(a["y"])
    if a.get("noshadow"):
        blit(img, im, sx - ax, sy - ay)
        return
    # ombra: ellisse scura semitrasparente (il codice userà l'effetto 'ombra')
    rx, ry = 13, 3
    yy, xx = np.mgrid[-ry:ry + 1, -rx:rx + 1]
    m = (xx / rx) ** 2 + (yy / ry) ** 2 <= 1
    for dy in range(-ry, ry + 1):
        for dx in range(-rx, rx + 1):
            if m[dy + ry, dx + rx]:
                y, x = sy + dy, sx + dx
                if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
                    img[y, x, :3] = (img[y, x, :3] * 0.45).astype(np.uint8)
    blit(img, im, sx - ax, sy - ay)


# ------------------------------------------------------------------ uscite
def save_png(path, img, scale=1):
    im = Image.fromarray(img[..., :3])
    if scale > 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(path)


def mockups(layers, out_dir, shots):
    os.makedirs(out_dir, exist_ok=True)
    for name, cam, actors in shots:
        f = frame(layers, cam, actors)
        save_png(os.path.join(out_dir, "mock_%s_1x.png" % name), f, 1)
        save_png(os.path.join(out_dir, "mock_%s_3x.png" % name), f, 3)


def pan(layers, out_dir, step=4, cam0=0, cam1=1536, scale=1, every=1):
    """GIF dello scorrimento (passo costante in px per fotogramma, telecamera intera) + controlli."""
    os.makedirs(out_dir, exist_ok=True)
    frames = []
    cams = list(range(cam0, cam1 + 1, step))
    gig = [("gig:Guard_Idle/%d" % (i % 4)) for i in range(4)]
    prev_x = None
    report = dict(step=step, frames=len(cams), layer_steps={})
    for i, cam in enumerate(cams):
        actors = [dict(spr=gig[(i // 6) % 4], x=cam + 150, y=184)]
        f = frame(layers, cam, actors)
        if i % every == 0:
            im = Image.fromarray(f[..., :3]).resize((E.SCREEN_W * scale, E.SCREEN_H * scale), Image.NEAREST)
            frames.append(im.convert("P", palette=Image.ADAPTIVE, colors=255))
        xs = {L["name"]: layer_x(L, cam) for L in layers}
        if prev_x is not None:
            for k, v in xs.items():
                report["layer_steps"].setdefault(k, set()).add(prev_x[k] - v)
        prev_x = xs
    report["layer_steps"] = {k: sorted(v) for k, v in report["layer_steps"].items()}
    path = os.path.join(out_dir, "pan_step%d.gif" % step)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=False)
    json.dump(report, open(os.path.join(out_dir, "pan_step%d.json" % step), "w"), indent=1)
    return path, report


def sheet(layers, out_path, scale=1):
    pad = 12
    W = max(L["img"].shape[1] for L in layers)
    H = sum(L["img"].shape[0] + pad + 10 for L in layers)
    canvas = Image.new("RGB", (W, H), (255, 0, 255))
    dr = ImageDraw.Draw(canvas)
    y = 0
    for L in layers:
        dr.rectangle([0, y, W, y + 10], fill=(20, 16, 30))
        dr.text((2, y - 1), "%s  scroll %.3f  y %d  %dx%d  repeat %d" % (L["name"], L["scroll"], L["y"],
                L["img"].shape[1], L["img"].shape[0], L.get("repeat_x", 0)), fill=(230, 230, 240))
        y += 11
        bgc = Image.new("RGBA", (L["img"].shape[1], L["img"].shape[0]), (255, 0, 255, 255))
        bgc.alpha_composite(Image.fromarray(L["img"]))
        canvas.paste(bgc.convert("RGB"), (0, y))
        y += L["img"].shape[0] + pad
    if scale > 1:
        canvas = canvas.resize((canvas.width * scale, canvas.height * scale), Image.NEAREST)
    canvas.save(out_path)


def checks(layers, meta):
    rep = {}
    for L in layers:
        im = L["img"]
        rep[L["name"]] = dict(size=list(im.shape[1::-1]), colours=int(len(np.unique(im[im[..., 3] > 0][:, :3], axis=0))),
                              opaque=float((im[..., 3] > 0).mean()))
        need = int(E.SCREEN_W + (E.LEVEL_W - E.SCREEN_W) * L["scroll"])
        rep[L["name"]]["covers_needed_px"] = need
        rep[L["name"]]["ok_width"] = bool(L.get("repeat_x", 0) > 0 or im.shape[1] >= need)
        if L.get("repeat_x"):
            p = L["repeat_x"]
            a = im[:, :p].astype(int)
            col_l, col_r = a[:, 0], a[:, p - 1]
            rep[L["name"]]["seam_diff"] = int(np.abs(col_l - col_r).sum())
    return rep


DEFAULT_SHOTS = [
    ("partenza", 0, [dict(spr="gig:Guard_Idle/0", x=150, y=184)]),
    ("ondata1", 620, [dict(spr="gig:Punch_Jab/2", x=760, y=172), dict(spr="punk_jab", x=812, y=174, flip=True)]),
    ("bidone", 900, [dict(spr="gig:Guard_Idle/1", x=990, y=196), dict(spr="prop:bin/idle/0", x=1050, y=178),
                     dict(spr="prop:apple/idle/1", x=1100, y=200)]),
    ("ostacolo", 1100, [dict(spr="prop:cable/idle/0", x=1250, y=150, noshadow=True),
                        dict(spr="gig:Guard_Idle/2", x=1196, y=182)]),
    ("arena", 1536, [dict(spr="gig:Guard_Idle/0", x=1650, y=190), dict(spr="punk", x=1780, y=168, flip=True),
                     dict(spr="bruiser", x=1840, y=200, flip=True)]),
]

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    d = sys.argv[2] if len(sys.argv) > 2 else os.path.join(E.OUT, "layers")
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(E.OUT, "verify")
    meta, layers = load_layers(d)
    if mode in ("mockup", "all"):
        mockups(layers, out, DEFAULT_SHOTS)
    if mode in ("sheet", "all"):
        sheet(layers, os.path.join(out, "layers_sheet.png"))
    if mode in ("pan", "all"):
        print(pan(layers, out, step=4))
    if mode in ("checks", "all"):
        print(json.dumps(checks(layers, meta), indent=1))
