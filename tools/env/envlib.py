# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - pipeline degli sfondi: funzioni comuni.

Contiene le costanti della vista (le stesse dei personaggi, tools/sprites/camera.json), la proiezione
mondo -> schermo, l'avvio di Blender, la lettura del G-buffer scritto da tools/blender/env_gbuffer.py
(decodifica, inclinazione 1:8 e riduzione a 1x per voto di maggioranza), la palette e gli strumenti
sul colore (OKLab).

Sistema di riferimento della scena (metri): X lungo la strada, Y profondità (lontano dalla telecamera),
Z in alto. Sullo schermo (px, 1x):
    x = KX * X + KYX * Y
    y = OY - KYY * Y - KZ * Z
con OY = 188: il bordo posteriore della fascia calpestabile (Y = 0, Z = 0) cade su y = 188.

Scala: dal 5 novembre 2026 lo schermo è 480x270 e la vista ha 60 px/m (prima 384x216 e 48 px/m), tutto più grande
del 25%. Le posizioni di progetto del layout restano scritte in px a 48 px/m (DESIGN_PPM) e si convertono qui:
design_X() le porta in metri, px() porta una misura in pixel di progetto ai pixel di oggi con floor(p * 1,25 + 0,5),
la stessa regola dei dati del livello nel codice del gioco.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image

# ------------------------------------------------------------------ vista (= tools/sprites/camera.json)
YAW = 30.0
PITCH = 12.0
PPM = 60.0
DESIGN_PPM = 48.0                                            # scala dei numeri di progetto in px (layout, props)
S = PPM / DESIGN_PPM                                         # 1,25
SS = 4
KEY_CAM = np.array([0.3811, 0.702, 0.6017], np.float32)     # direzione verso la luce chiave, spazio telecamera
KEY_CAM /= np.linalg.norm(KEY_CAM)
OUTLINE = "#140e1e"                                          # contorno dei personaggi
K_SHEAR = math.tan(math.radians(YAW)) * math.sin(math.radians(PITCH))
KX = PPM * math.cos(math.radians(YAW))                       # 51.96 px per metro lungo la strada
KYX = PPM * math.sin(math.radians(YAW))                      # 30.0 px a destra per metro di profondità
KYY = PPM * math.sin(math.radians(PITCH)) / math.cos(math.radians(YAW))   # 14.40 px in su per metro di profondità
KZ = PPM * math.cos(math.radians(PITCH))                     # 58.69 px per metro di altezza


def px(p):
    """Misura in pixel di progetto (48 px/m) -> pixel di oggi (60 px/m): floor(p * 1,25 + 0,5)."""
    return int(math.floor(p * S + 0.5))


OY = float(px(150))                                          # 188
LEVEL_W = px(1920)                                           # 2400
SCREEN_W, SCREEN_H = px(384), px(216)                        # 480 x 270
BAND = (px(150), px(208))                                    # (188, 260)

LAB = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "ctrlaltrevenge-lab")
# Blender 4.5.15 del laboratorio: la cartella portatile su Windows, l'app sul Mac.
BLENDER = (os.path.join(LAB, "tools", "blender-4.5.15", "Blender.app", "Contents", "MacOS", "Blender")
           if sys.platform == "darwin" else os.path.join(LAB, "tools", "blender-4.5.15", "blender.exe"))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "tools", "env", "out")
SRC_ENV = os.path.join(LAB, "sources", "env")
KIT_DIRS = {
    "cp": os.path.join(SRC_ENV, "q-cyberpunk-gdevelop"),
    "dt": os.path.join(SRC_ENV, "q-downtown", "ex", "Exports", "glTF (Godot)"),
    "kr": os.path.join(SRC_ENV, "kenney-city-kit-roads", "ex", "Models", "GLB format"),
    "ki": os.path.join(SRC_ENV, "kenney-city-kit-industrial", "ex", "Models", "GLB format"),
    "kc": os.path.join(SRC_ENV, "kenney-city-kit-commercial", "ex", "Models", "GLB format"),
}

# ------------------------------------------------------------------ classi del G-buffer
CLS = dict(NONE=0, WALL=1, BRICK=2, CONCRETE=3, METAL=4, ASPHALT=5, ROOF=6, GLASS=7, WINDOW_LIT=8,
           NEON=9, SIGN=10, DARK=11, DECAL=12, PUDDLE=13, LAMP=14, WOOD=15, SHUTTER=16, FENCE=17,
           AWNING=18, SIDEWALK=19, TRIM=20, PIPE=21, BILLBOARD=22, WINDOW=23, ACCENT=24, CABLE=25,
           KERB=26, PLANT=27, TRASH=28, POLE=29, PAPER=30)
CLS_NAME = {v: k for k, v in CLS.items()}
THIN = [CLS[k] for k in ("NEON", "CABLE", "FENCE", "LAMP", "POLE")]
EMISSIVE = [CLS[k] for k in ("WINDOW_LIT", "NEON", "LAMP", "BILLBOARD")]
GROUND = [CLS[k] for k in ("ASPHALT", "SIDEWALK", "KERB", "PUDDLE", "DECAL")]


def to_screen(X, Y, Z=0.0):
    return KX * X + KYX * Y, OY - KYY * Y - KZ * Z


def x_to_X(x, Y=0.0):
    """x schermo (px del mondo) -> X lungo la strada, alla profondità Y."""
    return (x - KYX * Y) / KX


def design_X(xs, Y=0.0):
    """x di progetto (px del mondo a 48 px/m) -> X lungo la strada, alla profondità Y. Il punto resta dove era in
    metri: sullo schermo di oggi cade in xs * 1,25."""
    return x_to_X(xs * S, Y)


# ------------------------------------------------------------------ colore
def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def hexs(rgb):
    return "#%02x%02x%02x" % tuple(int(round(max(0, min(255, c)))) for c in rgb)


def f3(s):
    """'#rrggbb' -> [r, g, b] in 0..1 (sRGB)."""
    return [c / 255.0 for c in hx(s)]


def srgb_to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def oklab(lin):
    M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                   [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
    M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                   [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)
    lms = np.cbrt(np.maximum(np.asarray(lin, np.float32) @ M1.T, 0))
    return lms @ M2.T


def nearest(rgb01, pal_hex, weights=(1.0, 1.0, 1.0)):
    """rgb01 (N,3) sRGB 0..1 -> indici nella palette (distanza OKLab pesata)."""
    pal = np.array([hx(c) for c in pal_hex], np.float32) / 255.0
    pl = oklab(srgb_to_lin(pal))
    lab = oklab(srgb_to_lin(np.asarray(rgb01, np.float32)))
    w = np.array(weights, np.float32)
    out = np.empty(len(lab), np.int64)
    for i0 in range(0, len(lab), 200000):
        d = (((lab[i0:i0 + 200000, None, :] - pl[None]) * w) ** 2).sum(-1)
        out[i0:i0 + 200000] = d.argmin(1)
    return out


BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16.0


# ------------------------------------------------------------------ Blender
def run_blender(script, job, job_path, timeout=900, log=None):
    os.makedirs(os.path.dirname(job_path), exist_ok=True)
    with open(job_path, "w", encoding="utf-8") as fh:
        json.dump(job, fh)
    cmd = [BLENDER, "-b", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1",
           "--python", script, "--", job_path]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    if log:
        with open(log, "w", encoding="utf-8") as fh:
            fh.write(p.stdout + "\n---- stderr ----\n" + p.stderr)
    if p.returncode != 0 or "Traceback" in p.stdout + p.stderr:
        tail = (p.stdout + p.stderr)[-3000:]
        raise RuntimeError("Blender non è riuscito (%d):\n%s" % (p.returncode, tail))
    return time.time() - t0


# ------------------------------------------------------------------ G-buffer
def load_gbuffer(raw_dir, tag):
    meta = json.load(open(os.path.join(raw_dir, "%s_meta.json" % tag), encoding="utf-8"))
    P = {}
    for p in meta["passes"]:
        P[p] = np.asarray(Image.open(os.path.join(raw_dir, "%s_%s.png" % (tag, p))).convert("RGBA"))
    a = P["alb"][..., 3] > 127
    alb = P["alb"][..., :3].astype(np.float32) / 255.0
    nx = P["nrm"][..., 0].astype(np.float32) / 255.0 * 2 - 1
    ny = P["nrm"][..., 1].astype(np.float32) / 255.0 * 2 - 1
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    n = np.stack([nx, ny, nz], -1)
    cls = P["nrm"][..., 2].astype(np.int32)
    oid = P["oid"][..., 0].astype(np.int32) * 256 + P["oid"][..., 1].astype(np.int32)
    mat = P["oid"][..., 2].astype(np.int32)
    emi = P["emi"][..., :3].astype(np.float32) / 255.0
    sp = meta["span"] / 65535.0
    p0 = meta["p0"]
    X = p0[0] + (P["pxy"][..., 0].astype(np.float32) * 256 + P["pxy"][..., 1]) * sp
    Y = p0[1] + (P["pxy"][..., 2].astype(np.float32) * 256 + P["pyz"][..., 0]) * sp
    Z = p0[2] + (P["pyz"][..., 1].astype(np.float32) * 256 + P["pyz"][..., 2]) * sp
    pos = np.stack([X, Y, Z], -1)
    cls[~a] = 0
    oid[~a] = 0
    return meta, dict(a=a, alb=alb, n=n, cls=cls, oid=oid, mat=mat, emi=emi, pos=pos)


def shear_hi(meta, G):
    """Inclinazione verticale per colonna (al supersampling): la strada diventa orizzontale."""
    v = meta["view"]
    ss, k = meta["ss"], meta["k"]
    x0, x1, y0, y1 = v["x0"], v["x1"], v["y0"], v["y1"]
    W = G["a"].shape[1]
    Hout = int(round((y1 - y0) * ss))
    c = np.arange(W)
    base = ss * k * x0 - ss * min(k * x0, k * x1)
    shift = np.floor(base + k * (c + 0.5) + 0.5).astype(np.int64)
    rows = np.arange(Hout)[:, None] + shift[None, :]
    H = G["a"].shape[0]
    valid = (rows >= 0) & (rows < H)
    rows = np.clip(rows, 0, H - 1)
    out = {}
    for key, arr in G.items():
        o = arr[rows, c[None, :]]
        if key == "a":
            o = o & valid
        out[key] = o
    out["cls"][~out["a"]] = 0
    out["oid"][~out["a"]] = 0
    return out


def downsample(G, ss=SS, cov_thr=0.5):
    """Riduzione a 1x: per ogni blocco ss x ss vince l'oggetto più presente; i dettagli sottili
    (neon, cavi, reti, lampade, pali) vincono se coprono almeno ss campioni."""
    a = G["a"]
    H, W = a.shape
    H, W = H - H % ss, W - W % ss
    h, w = H // ss, W // ss

    def blk(x):
        x = x[:H, :W]
        x = x.reshape(h, ss, w, ss, *x.shape[2:])
        x = np.moveaxis(x, 2, 1)
        return x.reshape(h, w, ss * ss, *x.shape[4:])

    ab, ob, cb = blk(a), blk(G["oid"]), blk(G["cls"])
    K = np.where(ab, ob, -1)
    out = dict(a=np.zeros((h, w), bool), oid=np.zeros((h, w), np.int32), cls=np.zeros((h, w), np.int32),
               mat=np.zeros((h, w), np.int32), alb=np.zeros((h, w, 3), np.float32), n=np.zeros((h, w, 3), np.float32),
               emi=np.zeros((h, w, 3), np.float32), pos=np.zeros((h, w, 3), np.float32), cov=np.zeros((h, w), np.float32))
    nb, eb, lb, pb, mb = blk(G["n"]), blk(G["emi"]), blk(G["alb"]), blk(G["pos"]), blk(G["mat"])
    step = max(1, 120000 // max(w, 1))
    for y0 in range(0, h, step):
        y1 = min(h, y0 + step)
        Kk = K[y0:y1]
        cnt = (Kk[..., :, None] == Kk[..., None, :]).sum(-1)
        cnt = np.where(Kk >= 0, cnt, 0)
        thin = np.isin(cb[y0:y1], THIN) & (Kk >= 0)
        cnt_thin = np.where(thin, cnt, 0)
        i_any = cnt.argmax(-1)
        i_thin = cnt_thin.argmax(-1)
        has_thin = np.take_along_axis(cnt_thin, i_thin[..., None], -1)[..., 0] >= ss
        best_i = np.where(has_thin, i_thin, i_any)
        best = np.take_along_axis(Kk, best_i[..., None], -1)[..., 0]
        cov = (Kk >= 0).mean(-1)
        al = ((cov >= cov_thr) | has_thin) & (best >= 0)
        sel = (Kk == best[..., None]) & (Kk >= 0)
        ws = np.maximum(sel.sum(-1), 1)
        out["a"][y0:y1] = al
        out["cov"][y0:y1] = cov
        out["oid"][y0:y1] = np.where(al, best, 0)
        out["cls"][y0:y1] = np.where(al, np.take_along_axis(cb[y0:y1], best_i[..., None], -1)[..., 0], 0)
        out["mat"][y0:y1] = np.where(al, np.take_along_axis(mb[y0:y1], best_i[..., None], -1)[..., 0], 0)
        out["alb"][y0:y1] = (lb[y0:y1] * sel[..., None]).sum(-2) / ws[..., None]
        nn = (nb[y0:y1] * sel[..., None]).sum(-2)
        out["n"][y0:y1] = nn / np.maximum(np.linalg.norm(nn, axis=-1, keepdims=True), 1e-6)
        out["emi"][y0:y1] = (eb[y0:y1] * sel[..., None]).sum(-2) / ws[..., None]
        out["pos"][y0:y1] = (pb[y0:y1] * sel[..., None]).sum(-2) / ws[..., None]
    return out


def gbuffer_1x(raw_dir, tag, cov_thr=0.5):
    meta, G = load_gbuffer(raw_dir, tag)
    G = shear_hi(meta, G)
    D = downsample(G, meta["ss"], cov_thr)
    v = meta["view"]
    f = np.array(meta["f"], np.float32)
    D["depth"] = np.where(D["a"], (D["pos"] * f).sum(-1), 1e9)
    D["x0"], D["y0"] = v["x0"], v["y0"]
    return meta, D


# ------------------------------------------------------------------ immagini
def save_rgba(path, arr, scale_preview=0, bg=(40, 36, 56)):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = Image.fromarray(np.ascontiguousarray(arr), "RGBA")
    im.save(path, optimize=True)
    if scale_preview:
        b = Image.new("RGBA", im.size, (*bg, 255))
        b.alpha_composite(im)
        b = b.convert("RGB").resize((im.width * scale_preview, im.height * scale_preview), Image.NEAREST)
        b.save(path.replace(".png", "_x%d.png" % scale_preview))
    return path


def nb4(arr, fill):
    up = np.concatenate([np.full_like(arr[:1], fill), arr[:-1]], 0)
    dn = np.concatenate([arr[1:], np.full_like(arr[:1], fill)], 0)
    lf = np.concatenate([np.full_like(arr[:, :1], fill), arr[:, :-1]], 1)
    rt = np.concatenate([arr[:, 1:], np.full_like(arr[:, :1], fill)], 1)
    return [up, dn, lf, rt]
