# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Tavole di controllo: miniature per scegliere le pose, tavole 4x per animazione (con ancora e box),
GIF a velocità reale (i tick a 60 Hz diventano millisecondi), scena di prova 384x216 con i personaggi."""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BG = (28, 24, 40)


def font(size):
    for f in ("C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def explore_sheets(explore_dir, out_dir, cols=12, scale=1):
    """una tavola per clip con tutte le miniature numerate (esplorazione delle pose)."""
    os.makedirs(out_dir, exist_ok=True)
    idx = json.load(open(os.path.join(explore_dir, "index.json")))
    for clip, frames in idx["clips"].items():
        d = os.path.join(explore_dir, clip.replace("|", "_"))
        ims = [Image.open(os.path.join(d, f"f{f:03d}.png")).convert("RGB") for f in frames]
        if not ims:
            continue
        # ritaglio comune attorno al personaggio
        arrs = [np.asarray(im) for im in ims]
        bg = arrs[0][0, 0].astype(int)
        mask = np.zeros(arrs[0].shape[:2], bool)
        for a in arrs:
            mask |= (np.abs(a.astype(int) - bg).sum(-1) > 12)
        ys, xs = np.nonzero(mask)
        x0, x1 = max(xs.min() - 4, 0), min(xs.max() + 5, arrs[0].shape[1])
        y0, y1 = max(ys.min() - 4, 0), min(ys.max() + 5, arrs[0].shape[0])
        cw, ch = (x1 - x0) * scale, (y1 - y0) * scale
        n = len(ims)
        c = min(cols, n)
        r = (n + c - 1) // c
        sheet = Image.new("RGB", (c * (cw + 4) + 4, r * (ch + 18) + 24), (40, 40, 52))
        dr = ImageDraw.Draw(sheet)
        dr.text((4, 4), clip, fill=(230, 230, 240), font=font(14))
        for i, (im, f) in enumerate(zip(ims, frames)):
            x = 4 + (i % c) * (cw + 4)
            y = 22 + (i // c) * (ch + 18)
            sheet.paste(im.crop((x0, y0, x1, y1)).resize((cw, ch), Image.NEAREST), (x, y))
            dr.text((x + 2, y + ch + 1), str(f), fill=(250, 220, 120), font=font(12))
        sheet.save(os.path.join(out_dir, f"explore_{clip.replace('|', '_')}.png"))


def union_box(sprites, margin=2):
    x0 = y0 = 10 ** 9
    x1 = y1 = -1
    for im in sprites:
        ys, xs = np.nonzero(im[..., 3])
        if len(xs):
            x0, x1 = min(x0, xs.min()), max(x1, xs.max())
            y0, y1 = min(y0, ys.min()), max(y1, ys.max())
    if x1 < 0:
        return 0, 0, 8, 8
    return max(x0 - margin, 0), max(y0 - margin, 0), x1 + margin + 1, y1 + margin + 1


def contact_sheet(frames, labels, title, path, scale=4, anchors=None, boxes=None, bg=(58, 58, 74), sub=""):
    """frames: immagini RGBA di uguale dimensione (fotogrammi completi); anchors: [(x, y)]; boxes: [(hurt, hit)]
    con box [x, y, w, h] relativi all'ancora."""
    x0, y0, x1, y1 = union_box(frames + ([] if anchors is None else []))
    if anchors:
        xs = [a[0] for a in anchors]
        ys = [a[1] for a in anchors]
        x0, y0 = min(x0, min(xs) - 2), min(y0, min(ys) - 2)
        x1, y1 = max(x1, max(xs) + 3), max(y1, max(ys) + 3)
    cw, ch = (x1 - x0) * scale, (y1 - y0) * scale
    gap, top, lab_h = 10, 52, 30
    W = gap + len(frames) * (cw + gap)
    H = top + ch + lab_h
    sheet = Image.new("RGB", (max(W, 400), H), bg)
    dr = ImageDraw.Draw(sheet)
    dr.text((gap, 6), title, fill=(235, 235, 245), font=font(18 if scale > 2 else 12))
    if sub:
        dr.text((gap, 30), sub, fill=(170, 170, 190), font=font(12 if scale > 2 else 9))
    for i, (sp, lb) in enumerate(zip(frames, labels)):
        im = Image.fromarray(sp[y0:y1, x0:x1], "RGBA").resize((cw, ch), Image.NEAREST)
        x = gap + i * (cw + gap)
        dr.rectangle([x - 1, top - 1, x + cw, top + ch], outline=(80, 80, 100))
        sheet.paste(im, (x, top), im)
        if anchors:
            ax, ay = anchors[i]
            px, py = x + (ax - x0) * scale, top + (ay - y0) * scale
            dr.line([px - 5, py, px + 5, py], fill=(255, 230, 0))
            dr.line([px, py - 5, px, py + 5], fill=(255, 230, 0))
            if boxes:
                hurt, hit = boxes[i]
                for bx, col in [(b, (60, 200, 255)) for b in hurt] + [(b, (255, 60, 60)) for b in hit]:
                    rx, ry, rw, rh = bx
                    dr.rectangle([px + rx * scale, py + ry * scale, px + (rx + rw) * scale - 1,
                                  py + (ry + rh) * scale - 1], outline=col)
        dr.text((x + 2, top + ch + 4), lb, fill=(220, 220, 230), font=font(12 if scale > 2 else 9))
    sheet.save(path)


def save_gif(frames, ticks, path, scale=3, bg=BG, anchors=None):
    """GIF a velocità reale: un fotogramma dura ticks/60 s (la GIF arrotonda ai centesimi)."""
    x0, y0, x1, y1 = union_box(frames, margin=4)
    if anchors:
        x0 = min(x0, min(a[0] for a in anchors) - 4)
        x1 = max(x1, max(a[0] for a in anchors) + 4)
        y1 = max(y1, max(a[1] for a in anchors) + 3)
    out = []
    durs = []
    acc = 0.0
    for sp, t in zip(frames, ticks):
        im = Image.new("RGBA", (x1 - x0, y1 - y0), (*bg, 255))
        im.alpha_composite(Image.fromarray(sp[y0:y1, x0:x1], "RGBA"))
        im = im.resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.NEAREST).convert("RGB")
        out.append(im.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
        # durate arrotondate senza accumulare errore
        acc += t * 1000.0 / 60.0
        d = int(round(acc / 10.0)) * 10 - sum(durs)
        durs.append(max(d, 20))
    out[0].save(path, save_all=True, append_images=out[1:], duration=durs, loop=0, disposal=1)
