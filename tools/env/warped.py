# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - cielo e piani lontani di "Sotto la Linea" dal pack CC0 Warped City (ansimuz).

Usa solo quattro PNG di ENVIRONMENT/background dello zip OpenGameArt (warped_city_files.zip):
skyline-a, skyline-b (cielo), buildings-bg (skyline lontano), near-buildings-bg (palazzi del piano mid).
Ogni colore della sorgente viene sostituito con una tabella esplicita verso la palette della locandina
(teal -> blu-viola, magenta -> rosso neon, finestre -> arancio caldo). Il piano lontano riceve l'unico
punto cyan del livello: una torre con antenna disegnata qui (codice), come nella locandina.

  python -I tools/env/warped.py <cartella ENVIRONMENT/background>   (predefinita: quella del laboratorio)
Scrive in tools/env/out/layers/: sky.png, far.png, far_emis.png, mid.png, mid_emis.png (+ x3).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envlib as E  # noqa: E402
from materials import RAMPS  # noqa: E402

WC_DIR = os.path.join(E.LAB, "sources", "chars", "oga-warped-city", "ex_all", "warped city files", "ENVIRONMENT",
                      "background")
SHA256 = {
    "skyline-a.png": "396a8ed4cc3027f38737319ebf78dd55452e0f6d56a28179dd6bd268e9870344",
    "skyline-b.png": "96deb29230a929a7464791195ea81c637736353e99f48ba309552ee06536a695",
    "buildings-bg.png": "2bcf93444924a333a340920ad773421137bc2d59d629017d5eb886239e70e7df",
    "near-buildings-bg.png": "70eca49ce42f7c57135ade657d669ee9c7850f1bd02ba3eeece5f3f33c731205",
}
# sorgente -> destinazione (None = trasparente)
MAP_SKY = {
    "#00003c": "#0a0b24", "#010350": "#0f1131", "#040c5a": "#15183f", "#031b70": "#15183f",
    "#21004b": "#1c1f4e", "#540052": "#262760", "#880c4f": "#322f6c", "#ec1e44": "#561a36",
    "#fc583a": "#722240", "#f07c36": "#834028", "#de9a41": "#a3542f", "#0b347f": "#4e5b84",
    "#177daa": "#a3b2c8",
}
MAP_FAR = {
    "#00003c": "#15183f", "#040c5a": "#1c1f4e", "#031b70": "#1c1f4e", "#0b347f": "#262760",
    "#21004b": "#22204c", "#540052": "#3e142c", "#9b0c8e": "#a8182e", "#177daa": "#c04a14",
}
MAP_MID = {
    "#050912": "#121327", "#031325": "#171a32", "#072b3a": "#212743", "#21004b": "#2b1f3e",
    "#0b347f": "#2d3557", "#320d4e": "#3a2a4f", "#177daa": "#b8663a", "#9b0c8e": "#e02a3a",
    "#031b70": "#212743", "#540052": "#561a36", "#fc583a": "#ff5a5a",
}
EMISSIVE_SRC = {"#177daa", "#9b0c8e", "#fc583a", "#ec1e44"}


def load(name, wc_dir):
    p = os.path.join(wc_dir, name)
    import hashlib
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    if h != SHA256[name]:
        raise SystemExit("hash diverso per %s: %s" % (name, h))
    return np.asarray(Image.open(p).convert("RGBA"))


def remap(a, table, emis_keep=False):
    out = np.zeros_like(a)
    emis = np.zeros_like(a)
    for src, dst in table.items():
        s = np.array(E.hx(src), np.uint8)
        m = (a[..., :3] == s).all(-1) & (a[..., 3] > 0)
        if dst is None:
            continue
        out[m, :3] = E.hx(dst)
        out[m, 3] = 255
        if src in EMISSIVE_SRC:
            emis[m, :3] = E.hx(dst)
            emis[m, 3] = 255
    left = (a[..., 3] > 0) & (out[..., 3] == 0)
    if left.any():
        raise SystemExit("colori non mappati: %s" % np.unique(a[left][:, :3], axis=0))
    return out, emis


def landmark_tower(h=118, w=40):
    """Torre-antenna lontana con la cabina cyan (l'unico cyan del livello) e la luce rossa in cima."""
    img = np.zeros((h, w, 4), np.uint8)
    em = np.zeros_like(img)
    body = E.hx("#1c1f4e")
    edge = E.hx("#2d3557")
    dark = E.hx("#15183f")
    cyan = [E.hx(c) for c in RAMPS["cyan"]]
    cx = w // 2

    def put(y, x, c, emis=False):
        if 0 <= y < h and 0 <= x < w:
            img[y, x, :3] = c
            img[y, x, 3] = 255
            if emis:
                em[y, x, :3] = c
                em[y, x, 3] = 255

    for y in range(h):
        if y < 10:
            half = 0                      # antenna
        elif y < 14:
            half = 2                      # testa
        elif y < 23:
            half = 8                      # cabina panoramica
        elif y < 26:
            half = 4                      # collo
        else:
            half = int(2 + (y - 26) / (h - 26) * 6)    # fusto che si allarga in basso
        for x in range(cx - half, cx + half + 1):
            put(y, x, edge if x == cx - half else body)
        if half > 0:
            put(y, cx + half, dark)
    # cabina: due fasce di finestre cyan e una luce sotto
    for x in range(cx - 7, cx + 8):
        if (x - cx) % 2 == 0:
            put(16, x, cyan[3] if abs(x - cx) < 5 else cyan[2], True)
            put(19, x, cyan[2], True)
        put(22, x, cyan[1], True)
    # luci di posizione lungo il fusto
    for y in range(30, h, 7):
        put(y, cx, cyan[1], True)
    # luce rossa in cima
    put(0, cx, E.hx("#ff5a5a"), True)
    put(1, cx, E.hx("#e02a3a"), True)
    return img, em


def paste(dst, src, x, y):
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    m = s[..., 3] > 0
    dst[y0:y1, x0:x1][m] = s[m]


def build(wc_dir=WC_DIR, out_dir=None):
    out_dir = out_dir or os.path.join(E.OUT, "layers")
    os.makedirs(out_dir, exist_ok=True)
    info = {}
    # ---------------- cielo: a | b | a, statico (fattore 0), 384 x 216
    sa, _ = remap(load("skyline-a.png", wc_dir), MAP_SKY)
    sb, _ = remap(load("skyline-b.png", wc_dir), MAP_SKY)
    # togli il pianeta ad anelli di skyline-b (in alto a sinistra): copia il cielo stellato di skyline-a
    sb = sb.copy()
    sb[:40, :60] = sa[:40, :60]
    strip = np.concatenate([sa, sb, sa], 1)
    SKY_OFF = 22
    sky = strip[SKY_OFF:SKY_OFF + E.SCREEN_H]
    E.save_rgba(os.path.join(out_dir, "sky.png"), sky, 3)
    info["sky"] = dict(y=0, w=sky.shape[1], h=sky.shape[0])
    # ---------------- lontano: buildings-bg x4 (diritto/specchiato), 576 px, più la torre cyan
    fb, fe = remap(load("buildings-bg.png", wc_dir), MAP_FAR)
    tiles = [fb, fb[:, ::-1], fb, fb[:, ::-1]]
    etiles = [fe, fe[:, ::-1], fe, fe[:, ::-1]]
    far = np.concatenate(tiles, 1)
    far_e = np.concatenate(etiles, 1)
    tw, te = landmark_tower()
    th = tw.shape[0]
    pad = th - far.shape[0] + 6
    far = np.concatenate([np.zeros((pad, far.shape[1], 4), np.uint8), far], 0)
    far_e = np.concatenate([np.zeros((pad, far_e.shape[1], 4), np.uint8), far_e], 0)
    paste(far, tw, 150 - tw.shape[1] // 2, far.shape[0] - th - 6)
    paste(far_e, te, 150 - tw.shape[1] // 2, far.shape[0] - th - 6)
    FAR_Y = 26
    E.save_rgba(os.path.join(out_dir, "far.png"), far, 3)
    E.save_rgba(os.path.join(out_dir, "far_emis.png"), dim(far_e, 0.6), 0)
    info["far"] = dict(y=FAR_Y, w=far.shape[1], h=far.shape[0])
    # ---------------- mid: near-buildings-bg + tre palazzi ripetuti specchiati, 768 px
    mb, me = remap(load("near-buildings-bg.png", wc_dir), MAP_MID)
    cols = np.nonzero(mb[..., 3].any(0))[0]
    # separa i palazzi (colonne vuote fra loro)
    runs, start = [], None
    for x in range(mb.shape[1]):
        on = mb[:, x, 3].any()
        if on and start is None:
            start = x
        if not on and start is not None:
            runs.append((start, x))
            start = None
    if start is not None:
        runs.append((start, mb.shape[1]))
    W = 768
    mid = np.zeros((mb.shape[0], W, 4), np.uint8)
    mid_e = np.zeros_like(mid)
    # posizioni fisse: varco libero fra x 90 e 260 (si vede la torre cyan nel lotto della partenza)
    place = [(0, 4, False), (3, 262, False), (2, 372, False), (1, 490, False), (4, 580, False), (0, 676, True)]
    for i, x, fl in place:
        a, b = runs[i]
        piece, pe = mb[:, a:b], me[:, a:b]
        if fl:
            piece, pe = piece[:, ::-1], pe[:, ::-1]
        paste(mid, piece, x, 0)
        paste(mid_e, pe, x, 0)
    MID_Y = 14
    E.save_rgba(os.path.join(out_dir, "mid.png"), mid, 3)
    E.save_rgba(os.path.join(out_dir, "mid_emis.png"), dim(mid_e, 0.5), 0)
    info["mid"] = dict(y=MID_Y, w=mid.shape[1], h=mid.shape[0])
    json.dump(info, open(os.path.join(out_dir, "warped_info.json"), "w"), indent=1)
    print("[warped]", info)
    return info


def dim(a, k):
    out = a.copy()
    out[..., :3] = (out[..., :3].astype(np.float32) * k).astype(np.uint8)
    return out


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else WC_DIR)
