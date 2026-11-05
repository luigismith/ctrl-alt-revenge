# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - pipeline degli sfondi: dal G-buffer 1x alla pixel art ("shader differito" in Python).

Passi, nell'ordine:
  1. motivi delle superfici per materiale (intonaco, mattoni, serrande, asfalto...), ancorati al mondo;
  2. operazioni di pittura del layout (insegne al neon con caratteri pixel, manifesti, graffiti, targhe,
     interni delle vetrine, reti metalliche con test di profondità, pozzanghere, crepe, rifiuti);
  3. luce: luce chiave a bande nella stessa direzione dei personaggi (spazio telecamera) + ambiente
     notturno + luce colorata dei neon (sfocatura dell'emissivo) + riflessi sull'asfalto bagnato;
  4. palette: colore più vicino in OKLab fra le rampe ammesse per quel materiale, retinatura ordinata
     4x4 solo sulle superfici grandi;
  5. contorni: 1 px esterno (#140e1e come i personaggi) e linee interne dove la profondità salta;
  6. maschera emissiva per Godot (aloni additivi dei neon, delle lampade e delle vetrine).
Cel shading (dal 4 novembre 2026, piani con la chiave "cel" nella configurazione: street, near, fg): la luce chiave
ha toni con soglie uguali per tutti i materiali, la luce dei neon e i riflessi sul bagnato vanno a zone con il bordo
netto, gli aloni sono anelli netti e la retinatura è spenta. Gli oggetti di scena (props.py) restano come prima.
Tutto è deterministico: rumori e scelte da semi fissi.
Misure in pixel: dal 5 novembre 2026 la vista ha 60 px/m (prima 48). I passi dei motivi che rappresentano misure vere
(corsi dei mattoni, assi, casseforme, maglie della rete...) e le sfocature crescono del 25% con E.px(); le linee di
1 px, i caratteri pixel (pixfont) e i piccoli dettagli disegnati a mano restano della loro misura in pixel.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envlib as E  # noqa: E402
import pixfont as PF  # noqa: E402
from materials import MATERIALS, RAMPS  # noqa: E402

C = E.CLS
AMB = np.array([0.36, 0.36, 0.56], np.float32)      # ambiente notturno blu-viola (lineare)
KEYC = np.array([0.62, 0.66, 0.92], np.float32)     # luce chiave fredda (cielo/luna)
# cel shading a 3 toni (prova del 4 novembre 2026): soglie su n·L della luce chiave, sull'intensità della luce dei neon
# e su quella dei riflessi sul bagnato
CEL_3TONI = dict(key_thr=(0.4, 0.7), spill_thr=(0.15, 0.6), wet_thr=(0.006, 0.03), wet_lane=0.6)


# ------------------------------------------------------------------ rumore e utilità
def vnoise(shape, cell, seed, ox=0, oy=0):
    """Rumore a valori, interpolazione bilineare, ancorato alle coordinate (ox, oy)."""
    h, w = shape
    rng = np.random.default_rng(seed)
    gh, gw = (h + oy % cell) // cell + 3, (w + ox % cell) // cell + 3
    g = rng.random((gh, gw)).astype(np.float32)
    yy = (np.arange(h) + oy % cell) / cell
    xx = (np.arange(w) + ox % cell) / cell
    y0 = np.floor(yy).astype(int)
    x0 = np.floor(xx).astype(int)
    fy = (yy - y0)[:, None]
    fx = (xx - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def hash2(x, y, seed=0):
    """Hash intero deterministico per coordinate intere (array)."""
    h = (np.asarray(x, np.int64) * 374761393 + np.asarray(y, np.int64) * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def lin(c):
    return E.srgb_to_lin(c)


def rgb(hexc):
    return np.array(E.hx(hexc), np.float32) / 255.0


class Canvas:
    """Buffer 1x della scena con tutto ciò che serve ai passi di pittura e luce."""

    def __init__(self, meta, D, ops):
        self.meta, self.D, self.ops = meta, D, ops
        v = meta["view"]
        self.view = v
        self.x0, self.y0 = v["x0"], v["y0"]
        self.ppm = v["ppm"]
        self.kx = v["ppm"] * math.cos(math.radians(v["yaw"]))
        self.kyx = v["ppm"] * math.sin(math.radians(v["yaw"]))
        self.kyy = v["ppm"] * math.sin(math.radians(v["pitch"])) / math.cos(math.radians(v["yaw"]))
        self.kz = v["ppm"] * math.cos(math.radians(v["pitch"]))
        self.oy = v["oy"]
        self.A = D["a"].copy()
        self.H, self.W = self.A.shape
        self.col = D["alb"].copy()                      # sRGB 0..1, prima della luce
        self.mat = D["mat"].copy()
        self.cls = D["cls"].copy()
        self.oid = D["oid"].copy()
        self.n = D["n"].copy()
        self.pos = D["pos"].copy()
        self.depth = D["depth"].copy()
        self.emi = D["emi"].copy()                      # sRGB 0..1
        self.is_em = (self.emi.max(-1) > 0.02) & self.A
        self.final = np.zeros((self.H, self.W), bool)   # pixel già definitivi (niente luce né palette)
        self.ramp_override = {}                         # (y, x) -> nome rampa forzata (non usato in blocco)
        self.force_ramp = np.full((self.H, self.W), -1, np.int32)
        self.noline = np.zeros((self.H, self.W), bool)  # niente linee di contorno interne
        self.glow = np.zeros((self.H, self.W, 3), np.float32)   # contributo alla maschera emissiva (lineare)
        self.halo_fill = np.zeros((self.H, self.W), bool)       # alone pieno (cel): dentro la cornice delle insegne
        self.cone = np.zeros((self.H, self.W), np.int32)        # coni delle lampade a muro (cel): 0, 1 lontano, 2 vicino
        self.neon = self.A & np.isin(self.cls, [E.CLS["NEON"], E.CLS["LAMP"]]) & self.is_em
        self.wet = np.zeros((self.H, self.W), np.float32)       # 0..1 bagnato (riflessi)
        yy, xx = np.mgrid[0:self.H, 0:self.W]
        self.yy, self.xx = yy + self.y0, xx + self.x0     # coordinate schermo/mondo in px
        self.bay = E.BAYER4[self.yy % 4, self.xx % 4]

    # ---------------- conversioni mondo <-> canvas
    def sx(self, X, Y):
        return self.kx * X + self.kyx * Y - self.x0

    def sy(self, Y, Z):
        if self.view["pitch"] >= 0:
            return self.oy - self.kyy * Y - self.kz * Z - self.y0
        return self.oy + self.kyy * Y - self.kz * Z - self.y0

    def front_rect(self, X0, X1, Z0, Z1, Yf):
        """Rettangolo sullo schermo (indici canvas) di un rettangolo su una faccia frontale (normale -Y)."""
        xa, xb = self.sx(X0, Yf), self.sx(X1, Yf)
        ya, yb = self.sy(Yf, Z1), self.sy(Yf, Z0)
        return int(round(xa)), int(round(xb)), int(round(ya)), int(round(yb))

    def face_y_of(self, oid, rect=None):
        m = self.oid == oid
        if rect is not None:
            x0, x1, y0, y1 = rect
            mm = np.zeros_like(m)
            mm[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = True
            m &= mm
        if not m.any():
            return None
        ys = self.pos[..., 1][m]
        return float(np.median(ys))

    def ground_XY(self, z):
        """Per ogni pixel: (X, Y) del punto del suolo a quota z che cade lì."""
        if self.view["pitch"] >= 0:
            Y = (self.oy - self.kz * z - (self.yy + 0.5)) / self.kyy
        else:
            Y = ((self.yy + 0.5) - self.oy + self.kz * z) / self.kyy
        X = ((self.xx + 0.5) - self.kyx * Y) / self.kx
        return X, Y

    def paste(self, x0, y0, bitmap_rgb, mask, where=None, emissive=None, final=True, mat=None, cls=None, neon=False):
        """Copia una bitmap (h, w, 3 sRGB) con maschera nel canvas in (x0, y0), limitata a 'where'."""
        h, w = mask.shape
        X0, Y0 = max(x0, 0), max(y0, 0)
        X1, Y1 = min(x0 + w, self.W), min(y0 + h, self.H)
        if X1 <= X0 or Y1 <= Y0:
            return np.zeros((self.H, self.W), bool)
        sub = mask[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0].copy()
        if where is not None:
            sub &= where[Y0:Y1, X0:X1]
        tgt = (slice(Y0, Y1), slice(X0, X1))
        cb = bitmap_rgb[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
        self.col[tgt][sub] = cb[sub]
        if final:
            self.final[tgt][sub] = True
        if emissive is not None:
            em = emissive[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
            e = em[sub]
            self.emi[tgt][sub] = e
            self.is_em[tgt][sub] = e.max(-1) > 0.02
            if neon:
                self.neon[tgt][sub] = e.max(-1) > 0.02
        if mat is not None:
            self.mat[tgt][sub] = mat
        if cls is not None:
            self.cls[tgt][sub] = cls
        full = np.zeros((self.H, self.W), bool)
        full[tgt] = sub
        return full


# ------------------------------------------------------------------ 1. motivi delle superfici
def patterns(cv: Canvas, seed=7):
    A = cv.A
    M = cv.mat
    xx, yy = cv.xx, cv.yy
    big = vnoise((cv.H, cv.W), E.px(23), seed + 1, cv.x0, cv.y0)
    mid = vnoise((cv.H, cv.W), E.px(7), seed + 2, cv.x0, cv.y0)
    fine = hash2(xx, yy, seed + 3)
    pos = cv.pos
    Z = pos[..., 2]
    nyc = cv.n[..., 1]
    mname = np.vectorize(lambda m: MATERIALS.get(int(m), {}).get("pattern") or "", otypes=[object])(M)

    def has(p):
        return A & (mname == p) & ~cv.is_em

    col = cv.col
    # intonaco: macchie a due toni con bordo retinato, sporco alla base, qualche crepa
    m = has("plaster")
    if m.any():
        t = big + (cv.bay - 0.5) * 0.18
        f = np.where(t > 0.58, 1.07, np.where(t < 0.36, 0.92, 1.0))
        g = np.clip((0.55 - Z) / 0.55, 0, 1) * (0.75 + 0.5 * mid)
        f = f * np.where(g > 0.45 + cv.bay * 0.3, 0.8, 1.0)
        col[m] *= f[m][:, None]
    # mattoni: corsi di 5 px, mattoni di 10 px sfalsati, giunti scuri, toni per mattone
    m = has("brick")
    if m.any():
        bh, bw = E.px(4), E.px(8)
        row = (yy // bh)
        off = (row % 2) * (bw // 2)
        bx = (xx + off) // bw
        mortar = (yy % bh == 0) | ((xx + off) % bw == 0)
        tone = 0.86 + 0.26 * hash2(bx, row, seed + 5)
        f = np.where(mortar, 0.62, tone)
        f *= np.where(big > 0.66, 0.9, 1.0)
        col[m] *= f[m][:, None]
    # pietra: blocchi 18 x 9 px
    m = has("stone")
    if m.any():
        sh, sw = E.px(7), E.px(14)
        row = yy // sh
        off = (row % 2) * (sw // 2)
        joint = (yy % sh == 0) | ((xx + off) % sw == 0)
        tone = 0.9 + 0.18 * hash2((xx + off) // sw, row, seed + 6)
        col[m] *= np.where(joint, 0.7, tone)[m][:, None]
    # cemento (muri bassi, piloni): casseforme orizzontali ogni 28 px, colature
    for p, step in (("concrete", E.px(22)), ("pillar", E.px(18))):
        m = has(p)
        if m.any():
            joint = (yy % step == 0)
            stain = (mid > 0.62) & (fine > 0.35)
            f = np.where(joint, 0.78, 1.0) * np.where(stain, 0.9, 1.0) * np.where(big > 0.6, 1.06, 1.0)
            dl = E.px(40)
            drip = (hash2(xx, 0, seed + 8) > 0.93) & (((yy + (hash2(xx, 1, seed) * dl).astype(int)) % dl) < E.px(22))
            f = np.where(drip, f * 0.82, f)
            col[m] *= f[m][:, None]
    # serrande: costole orizzontali di 4 px (una riga scura, una chiara, due di lamiera)
    m = has("shutter")
    if m.any():
        rp = E.px(3)
        rib = np.where(yy % rp == 0, 0.7, np.where(yy % rp == 1, 1.12, 1.0))
        rust = (mid > 0.7) & (fine > 0.5)
        f = rib * np.where(rust, 0.86, 1.0)
        col[m] *= f[m][:, None]
    # legno (porte, palizzate): venature verticali, assi ogni 6 px (porte) e 11 px (palizzate)
    for p, step in (("wood", E.px(5)), ("hoarding", E.px(9))):
        m = has(p)
        if m.any():
            seam = (xx % step == 0)
            grain = 0.92 + 0.12 * hash2(xx, yy // E.px(6), seed + 9)
            col[m] *= np.where(seam, 0.66, grain)[m][:, None]
    # asfalto e marciapiede: granelli chiari radi, toni larghi, rattoppi più scuri
    for p, k in (("asphalt", 1.0), ("sidewalk", 1.0), ("dirt", 1.25)):
        m = has(p)
        if m.any():
            speck = fine > (0.965 if p != "dirt" else 0.93)
            darks = fine < (0.03 if p != "dirt" else 0.07)
            f = np.where(big > 0.62, 1.05, np.where(big < 0.32, 0.93, 1.0))
            f = np.where(speck, 1.22 * k, np.where(darks, 0.8, f))
            col[m] *= f[m][:, None]
    # lastre del piazzale (arena): giunti lungo X ogni 2,4 m e lungo Y ogni 1,5 m, macchie d'olio
    m = has("slab")
    if m.any():
        X = pos[..., 0]
        Yw = pos[..., 1]
        jx = np.abs(((X + 0.05) % 2.4) - 0.05) < 0.04
        jy = np.abs(((Yw + 0.05) % 1.5) - 0.05) < 0.07
        oil = (big > 0.7) & (mid > 0.45)
        f = np.where(jx | jy, 0.7, np.where(oil, 0.8, np.where(fine > 0.97, 1.2, 1.0)))
        f *= np.where(big < 0.3, 0.94, 1.0)
        col[m] *= f[m][:, None]
        cv.wet[m & oil] = np.maximum(cv.wet[m & oil], 0.35)
    # marciapiede: lastre di cemento 1 x 0,5 m con giunti scuri e qualche lastra rotta o diversa
    m = has("sidewalk") & (pos[..., 2] > -0.02)
    if m.any():
        X = pos[..., 0]
        Yw = pos[..., 1]
        jx = np.abs(((X + 0.02) % 1.0) - 0.02) < 0.03
        jy = np.abs(((Yw + 0.02) % 0.5) - 0.02) < 0.05
        tile = hash2(np.floor(X).astype(int), np.floor(Yw * 2).astype(int), seed + 11)
        f = np.where(jx | jy, 0.78, np.where(tile > 0.9, 0.9, np.where(tile < 0.08, 1.07, 1.0)))
        col[m] *= f[m][:, None]
    # cordolo in pietra: giunti ogni ~1 m (lungo X) e bordo superiore più chiaro
    m = has("kerb")
    if m.any():
        X = pos[..., 0]
        joint = (np.abs(((X * 1.0) % 1.2)) < 0.05)
        top = nyc > 0.6
        f = np.where(joint, 0.7, np.where(top, 1.08, 0.95))
        col[m] *= f[m][:, None]
    # tende: bordo di 1 px più chiaro in basso alla mantovana (fatto dalla luce); qui solo trama
    m = has("awning")
    if m.any():
        col[m] *= np.where((xx % E.px(6)) < E.px(6) // 2, 1.0, 0.94)[m][:, None]
    # erbacce: due toni a ciuffi
    m = has("plant")
    if m.any():
        col[m] *= np.where(fine > 0.5, 1.15, 0.85)[m][:, None]
    # rivetti (travi d'acciaio): file di punti
    m = has("rivets")
    if m.any():
        dots = ((xx % E.px(6)) == 0) & ((yy % E.px(4)) == 1)
        col[m] *= np.where(dots, 1.35, 1.0)[m][:, None]
    m = has("cabinet")
    if m.any():
        col[m] *= np.where((yy % E.px(3)) == 0, 0.75, 1.0)[m][:, None]
    m = has("rust")
    if m.any():
        col[m] *= np.where(mid > 0.6, 0.85, np.where(fine > 0.9, 1.2, 1.0))[m][:, None]
    m = has("bin_ribs")
    if m.any():
        col[m] *= np.where((yy % E.px(5)) == 0, 0.78, 1.0)[m][:, None]


# ------------------------------------------------------------------ 2. operazioni di pittura
def neon_bitmap(mask, ramp, ring=1, core_idx=5, tube_idx=3, halo_idx=1):
    """Lettere al neon: tratto chiaro (nucleo), anello del tubo, alone scuro retinato.
    Ritorna (rgb, alfa, emissivo) con un bordo di 'ring+1' px attorno alla maschera."""
    pad = ring + 2
    m = np.pad(mask, pad)
    r = RAMPS[ramp]
    tube = ndi.binary_dilation(m, structure=np.ones((3, 3), bool), iterations=ring) & ~m
    halo = ndi.binary_dilation(m | tube, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)) & ~m & ~tube
    hh, ww = m.shape
    yy, xx = np.mgrid[0:hh, 0:ww]
    halo &= ((xx + yy) % 2 == 0)
    rgbm = np.zeros((hh, ww, 3), np.float32)
    rgbm[m] = rgb(r[core_idx])
    rgbm[tube] = rgb(r[tube_idx])
    rgbm[halo] = rgb(r[halo_idx])
    alpha = m | tube | halo
    em = np.zeros_like(rgbm)
    em[m] = rgb(r[core_idx])
    em[tube] = rgb(r[tube_idx]) * 0.9
    return rgbm, alpha, em, pad


def op_neon_text(cv: Canvas, o):
    x0, x1, y0, y1 = cv.front_rect(o["X0"], o["X1"], o["z0"], o["z1"], o["Yf"])
    w, h = x1 - x0, y1 - y0
    font = o.get("font", "med")
    if font == "big":
        mask = PF.render(o["text"], PF.FONT5x7, scale=2, spacing=2)
    elif font == "near":
        mask = PF.render(o["text"], PF.FONT3x5, scale=1, spacing=1)
    else:
        mask = PF.render(o["text"], PF.FONT5x7, scale=1, spacing=2)
    sub = None
    if o.get("sub"):
        sub = PF.render(o["sub"], PF.FONT3x5, scale=1, spacing=1)
    ring = 1 if font != "near" else 0
    rgbm, al, em, pad = neon_bitmap(mask, o["ramp"], ring=ring)
    where = cv.oid == o["oid"]
    total_w = al.shape[1] + (sub.shape[1] + 6 if sub is not None else 0)
    cross_w = 0
    if o.get("cross"):
        cross_w = 16
        total_w += cross_w
    ox = x0 + (w - total_w) // 2
    oy = y0 + (h - al.shape[0]) // 2
    if o.get("cross"):
        cm = np.zeros((11, 11), bool)
        cm[4:7, :] = True
        cm[:, 4:7] = True
        crgb, cal, cem, cpad = neon_bitmap(cm, "neon_green", ring=1, core_idx=5, tube_idx=4)
        cv.paste(ox, y0 + (h - cal.shape[0]) // 2, crgb, cal, where, cem, neon=True)
        ox += cross_w
    cv.paste(ox, oy, rgbm, al, where, em, neon=True)
    if sub is not None:
        srgb, sal, sem, spad = neon_bitmap(sub, "warm", ring=0, core_idx=6, tube_idx=4)
        cv.paste(ox + al.shape[1] + 2, oy + al.shape[0] - sal.shape[0] - 2, srgb, sal, where, sem, neon=True)
    if o.get("frame"):
        # tubo di cornice a 2 px dal bordo del pannello
        fm = np.zeros((h, w), bool)
        fm[2, 2:w - 2] = fm[h - 3, 2:w - 2] = True
        fm[2:h - 2, 2] = fm[2:h - 2, w - 3] = True
        r = RAMPS[o["ramp"]]
        fr = np.zeros((h, w, 3), np.float32)
        fr[fm] = rgb(r[4])
        fe = fr * 0.8
        cv.paste(x0, y0, fr, fm, where, fe, neon=True)
        # dentro la cornice l'alone del cel è pieno: senza, fra le lettere e i lati corti della cassetta restano due
        # dischi scuri, dove gli aloni sommati non arrivano alla soglia
        inner = np.zeros((cv.H, cv.W), bool)
        inner[max(y0 + 3, 0):max(y1 - 3, 0), max(x0 + 3, 0):max(x1 - 3, 0)] = True
        cv.halo_fill |= inner & where


def op_neon_vertical(cv: Canvas, o):
    """Lettere impilate sulla faccia +X di un'insegna a bandiera (faccia di sbieco: si campiona per pixel)."""
    Xf, Y0, Y1, z0, z1 = o["Xf"], o["Y0"], o["Y1"], o["z0"], o["z1"]
    tw = int(round((Y1 - Y0) * cv.kyx))
    th = int(round((z1 - z0) * cv.kz))
    letters = [PF.render(ch, PF.FONT5x7, scale=1 if o.get("small") else 2) for ch in o["text"]]
    tex_mask = np.zeros((th, tw), bool)
    gap = 2
    tot = sum(l.shape[0] for l in letters) + gap * (len(letters) - 1)
    if tot > th - 4:
        gap = 1
        letters = [l[1:] if l.shape[0] > 13 else l for l in letters]
        tot = sum(l.shape[0] for l in letters) + gap * (len(letters) - 1)
    if tot > th - 2 or letters[0].shape[1] > tw - 2:
        letters = [PF.render(ch, PF.FONT5x7, scale=1) for ch in o["text"]]
        gap = 2
        tot = sum(l.shape[0] for l in letters) + gap * (len(letters) - 1)
    yy0 = (th - tot) // 2
    for l in letters:
        xx0 = (tw - l.shape[1]) // 2
        tex_mask[yy0:yy0 + l.shape[0], max(xx0, 0):max(xx0, 0) + l.shape[1]] = l[:, :tw]
        yy0 += l.shape[0] + gap
    rgbm, al, em, pad = neon_bitmap(tex_mask, o["ramp"], ring=1)
    # bordo del tubo intorno alla faccia
    where = cv.oid == o["oid"]
    ys, xs = np.nonzero(where)
    if not len(ys):
        return
    for y, x in zip(ys, xs):
        Y = ((x + cv.x0 + 0.5) - cv.kx * Xf) / cv.kyx
        Z = (cv.oy - cv.kyy * Y - (y + cv.y0 + 0.5)) / cv.kz
        if Y < Y0 - 0.01 or Y > Y1 + 0.01 or Z < z0 - 0.01 or Z > z1 + 0.01:
            continue
        u = int((Y - Y0) / (Y1 - Y0) * tw) + pad
        v = int((z1 - Z) / (z1 - z0) * th) + pad
        if 0 <= v < al.shape[0] and 0 <= u < al.shape[1]:
            if al[v, u]:
                cv.col[y, x] = rgbm[v, u]
                cv.final[y, x] = True
                if em[v, u].max() > 0.02:
                    cv.emi[y, x] = em[v, u]
                    cv.is_em[y, x] = True
                    cv.neon[y, x] = True
            edge = (u - pad <= 0) or (u - pad >= tw - 1) or (v - pad <= 0) or (v - pad >= th - 1)
            if edge:
                cv.col[y, x] = rgb(RAMPS[o["ramp"]][3])
                cv.emi[y, x] = rgb(RAMPS[o["ramp"]][3]) * 0.8
                cv.is_em[y, x] = True
                cv.neon[y, x] = True
                cv.final[y, x] = True


def op_cross_blade(cv: Canvas, o):
    """Croce della farmacia sulla faccia +X dell'insegna a bandiera: verde, come in Italia."""
    Xf, Y0, Y1, z0, z1 = o["Xf"], o["Y0"], o["Y1"], o["z0"], o["z1"]
    where = cv.oid == o["oid"]
    ys, xs = np.nonzero(where)
    r = RAMPS["neon_green"]
    for y, x in zip(ys, xs):
        Y = ((x + cv.x0 + 0.5) - cv.kx * Xf) / cv.kyx
        Z = (cv.oy - cv.kyy * Y - (y + cv.y0 + 0.5)) / cv.kz
        u = (Y - Y0) / (Y1 - Y0)
        v = (z1 - Z) / (z1 - z0)
        if not (0 <= u <= 1 and 0 <= v <= 1):
            continue
        inner = (abs(u - 0.5) < 0.16 and abs(v - 0.5) < 0.38) or (abs(v - 0.5) < 0.12 and abs(u - 0.5) < 0.42)
        if inner:
            core = (abs(u - 0.5) < 0.06 and abs(v - 0.5) < 0.3) or (abs(v - 0.5) < 0.04 and abs(u - 0.5) < 0.34)
            c = rgb(r[5] if core else r[3])
            cv.col[y, x] = c
            cv.emi[y, x] = c
            cv.is_em[y, x] = True
            cv.neon[y, x] = True
            cv.final[y, x] = True


def op_plate(cv: Canvas, o):
    """Targa / cartello con testo piccolo (3x5) o simbolo."""
    where = cv.oid == o["oid"] if o.get("oid") else np.ones((cv.H, cv.W), bool)
    Yf = o.get("face_Y")
    if Yf is None:
        Yf = cv.face_y_of(o["oid"]) if o.get("oid") else 0.0
    x0, x1, y0, y1 = cv.front_rect(o["X0"], o["X1"], o["z0"], o["z1"], Yf)
    w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    bg = rgb(o["bg"])
    fg = rgb(o["col"])
    img = np.zeros((h, w, 3), np.float32)
    img[:] = bg
    msk = np.ones((h, w), bool)
    text = o["text"]
    if text in PF.SYMBOLS:
        t = PF.glyph(text, PF.FONT5x7)
    elif o.get("lines", 1) > 1:
        words = text.split(" ")
        half = (len(words) + 1) // 2
        t = PF.render_lines([" ".join(words[:half]), " ".join(words[half:])], PF.FONT3x5, 1, 1)
    else:
        t = PF.render(text, PF.FONT3x5 if text not in ("★★",) else PF.FONT3x5, 1, 1)
    th, tw = t.shape
    if tw > w - 2 or th > h - 2:
        # testo troppo grande: righe illeggibili (come da lontano)
        t = np.zeros((h, w), bool)
        t[1::2, 1:w - 1] = (np.arange(1, w - 1) % 3 != 0)
        t[::2] = False
        th, tw = t.shape
    ox, oy = (w - tw) // 2, (h - th) // 2
    sub = img[max(oy, 0):max(oy, 0) + th, max(ox, 0):max(ox, 0) + tw]
    sub[t[:sub.shape[0], :sub.shape[1]]] = fg
    # bordo scuro
    img[0, :] = img[-1, :] = bg * 0.6
    img[:, 0] = img[:, -1] = bg * 0.6
    cv.paste(x0, y0, img, msk, where, None, final=False)


def poster_bitmap(w, h, rng):
    """Manifesto: carta di un colore, una fascia di 'titolo', righe di testo finto, a volte una figura."""
    pal = ["#cdc4d4", "#aaa1b4", "#d8b040", "#b8303f", "#3b5fa0", "#e06a2a", "#7a3a9a", "#857d90"]
    base = rgb(rng.choice(pal))
    ink = rgb(rng.choice(["#140e1e", "#29252f", "#b8303f", "#3b5fa0"]))
    img = np.zeros((h, w, 3), np.float32)
    img[:] = base
    kind = rng.random()
    if kind < 0.35 and h >= 8:
        # titolo in alto + figura (cerchio/volto) + righe
        img[1:3, 1:w - 1] = ink
        cy, cx, r = h // 2, w // 2, max(2, min(w, h) // 4)
        yy, xx = np.mgrid[0:h, 0:w]
        img[((yy - cy) ** 2 + (xx - cx) ** 2) <= r * r] = rgb(rng.choice(["#29252f", "#3b5fa0", "#b8303f"]))
        for yl in range(h - 3, h - 1):
            img[yl, 1:w - 1:2] = ink
    elif kind < 0.7:
        for yl in range(1, h - 1, 2):
            n = rng.randint(max(1, w // 3), max(2, w - 2))
            img[yl, 1:1 + n] = ink
    else:
        # grande lettera / numero
        t = PF.render(rng.choice(["3", "X", "!", "€", "1", "A"]), PF.FONT3x5, 1)
        th, tw = t.shape
        if th <= h and tw <= w:
            sub = img[(h - th) // 2:(h - th) // 2 + th, (w - tw) // 2:(w - tw) // 2 + tw]
            sub[t] = ink
    # strappi: angoli mancanti e righe di colla
    msk = np.ones((h, w), bool)
    if rng.random() < 0.5:
        k = rng.randint(1, max(1, min(w, h) // 2))
        for i in range(k):
            msk[h - 1 - i, w - 1 - (k - i):] = False
    if rng.random() < 0.3:
        msk[0, :rng.randint(1, w)] = False
    return img, msk


def op_posters(cv: Canvas, o):
    where = cv.oid == o["oid"]
    Yf = o.get("face_Y")
    if Yf is None:
        Yf = cv.face_y_of(o["oid"])
        if Yf is None:
            return
    x0, x1, y0, y1 = cv.front_rect(o["X0"], o["X1"], o["z0"], o["z1"], Yf)
    rng = random.Random(o["seed"])
    W_, H_ = x1 - x0, y1 - y0
    if W_ < 4 or H_ < 4:
        return
    n = o.get("n", 4)
    placed = 0
    tries = 0
    # le estrazioni si fanno in px di progetto (48 px/m) e poi si portano a 60 px/m: così i manifesti restano dove
    # erano, con gli stessi colori, solo più grandi in pixel
    Wd, Hd = int(round(W_ / E.S)), int(round(H_ / E.S))
    while placed < n and tries < n * 8:
        tries += 1
        pwd = rng.randint(7, 13) if not o.get("dense") else rng.randint(8, 15)
        phd = rng.randint(10, 17)
        pwd, phd = min(pwd, Wd), min(phd, Hd)
        pw, ph = min(E.px(pwd), W_), min(E.px(phd), H_)
        px = x0 + min(E.px(rng.randint(0, max(Wd - pwd, 0))), W_ - pw)
        py = y0 + min(E.px(rng.randint(0, max(Hd - phd, 0))), H_ - ph)
        state = rng.getstate()
        r2 = random.Random()
        r2.setstate(state)
        img, msk = poster_bitmap(pw, ph, r2)
        poster_bitmap(pwd, phd, rng)        # fa avanzare il seme come prima
        cv.paste(px, py, img, msk, where, None, final=False, mat=25)
        placed += 1


GRAFF_COLS = [("#c8c0d8", "#3b5fa0"), ("#e06a2a", "#140e1e"), ("#d8b040", "#7a3a9a"), ("#b8303f", "#c8c0d8"),
              ("#7a3a9a", "#d8b040")]


def op_graffiti(cv: Canvas, o):
    """Scritta a bolle (lettere 5x7 ingrandite e arrotondate) con contorno, più 'tag' a scarabocchio."""
    where = cv.oid == o["oid"]
    Yf = o.get("face_Y")
    if Yf is None:
        Yf = cv.face_y_of(o["oid"])
        if Yf is None:
            return
    x0, x1, y0, y1 = cv.front_rect(o["X0"], o["X1"], o["z0"], o["z1"], Yf)
    rng = random.Random(o["seed"])
    W_, H_ = x1 - x0, y1 - y0
    word = o.get("word", "GIG")
    fillc, linec = GRAFF_COLS[o["seed"] % len(GRAFF_COLS)]
    m = PF.render(word, PF.FONT5x7, scale=1, spacing=1)
    # ingrandisci di 2 con dilatazione: lettere a bolla
    scale = 2 if (m.shape[1] * 2 + 4 <= W_ and m.shape[0] * 2 + 4 <= H_) else 1
    if scale == 2:
        m = np.kron(m, np.ones((2, 2), bool))
    m = np.pad(m, 2)
    fat = ndi.binary_dilation(m, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool))
    line = ndi.binary_dilation(fat, structure=np.ones((3, 3), bool)) & ~fat
    h, w = fat.shape
    # leggera inclinazione: sposta le colonne
    shear = np.zeros((h + 4, w), bool)
    sl = np.zeros((h + 4, w), bool)
    for c in range(w):
        s = int(round(2 * math.sin(c / max(w, 1) * math.pi * 1.3 + o["seed"])) + 2)
        shear[s:s + h, c] = fat[:, c]
        sl[s:s + h, c] = line[:, c]
    img = np.zeros(shear.shape + (3,), np.float32)
    img[shear] = rgb(fillc)
    img[sl] = rgb(linec)
    # luce sul riempimento: metà alta più chiara
    hh = shear.shape[0]
    hi = np.zeros_like(shear)
    hi[:hh // 2] = True
    img[shear & hi] = np.clip(rgb(fillc) * 1.12, 0, 1)
    msk = shear | sl
    px = x0 + max(0, (W_ - w) // 2) + E.px(rng.randint(-3, 3))
    py = y0 + max(0, (H_ - hh) // 2)
    cv.paste(px, py, img, msk, where, None, final=False, mat=25)
    # tag a scarabocchio accanto (posizioni estratte in px di progetto, come prima, poi portate a 60 px/m)
    Wd, Hd = int(round(W_ / E.S)), int(round(H_ / E.S))
    for k in range(rng.randint(1, 3)):
        tx = x0 + E.px(rng.randint(0, max(1, Wd - 14)))
        ty = y0 + E.px(rng.randint(0, max(1, Hd - 6)))
        tc = rgb(rng.choice(["#c8c0d8", "#140e1e", "#b8303f", "#d8b040"]))
        L = rng.randint(8, 14)
        pts = []
        yv = ty + 3
        for i in range(L):
            yv += rng.choice([-1, 0, 1])
            yv = min(max(yv, ty), ty + 5)
            pts.append((tx + i, yv))
        for (px_, py_) in pts:
            if 0 <= px_ < cv.W and 0 <= py_ < cv.H and where[py_, px_]:
                cv.col[py_, px_] = tc
                cv.mat[py_, px_] = 25


def op_tabacchi_t(cv: Canvas, o):
    where = cv.oid == o["oid"]
    x0, x1, y0, y1 = cv.front_rect(o["X0"], o["X1"], o["z0"], o["z1"], o["Yf"])
    w, h = x1 - x0, y1 - y0
    img = np.zeros((h, w, 3), np.float32)
    img[:] = rgb("#1c2a6a")
    msk = np.ones((h, w), bool)
    # T bianca illuminata
    tm = np.zeros((h, w), bool)
    tm[3:5, 2:w - 2] = True
    tm[3:h - 3, w // 2 - 1:w // 2 + 1] = True
    img[tm] = rgb("#f4eef8")
    img[0, :] = img[-1, :] = img[:, 0] = img[:, -1] = rgb("#0f1640")
    em = np.zeros_like(img)
    em[tm] = rgb("#c9c0d6") * 0.9
    em[~tm] = rgb("#1c2a6a") * 0.6
    cv.paste(x0, y0, img, msk, where, em)


def op_interior(cv: Canvas, o):
    """Interni delle vetrine accese: parete di fondo calda, fascia luminosa in alto, scaffali con bottiglie
    in controluce, banco scuro, sagome; riflessi diagonali sul vetro. Toni medi: la vetrina non deve
    essere la cosa più chiara dello schermo (quello spetta ai neon)."""
    where = cv.oid == o["oid"]
    if not where.any():
        return
    Yf = cv.face_y_of(o["oid"])
    x0, x1, y0, y1 = cv.front_rect(o["X0"], o["X1"], o["z0"], o["z1"], Yf)
    w, h = x1 - x0, y1 - y0
    if w < 4 or h < 4:
        return
    style = o["style"]
    rng = random.Random(len(style) * 1000 + x0)
    W_ = RAMPS["warm"]
    back = rgb(W_[3])
    back_lo = rgb(W_[2])
    top = rgb(W_[4])
    lamp = rgb(W_[6])
    sil = rgb(W_[1])
    sil2 = rgb(W_[0])
    img = np.zeros((h, w, 3), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    img[:] = back
    img[yy > h * 0.55] = back_lo
    img[yy < 3] = top
    for lx in range(3, w - 3, max(E.px(8), w // 4)):
        img[1, lx:lx + E.px(3)] = lamp
    msk = np.ones((h, w), bool)
    if style in ("bar", "tabacchi", "farmacia", "kebab", "osteria"):
        for k, fy in enumerate((0.2, 0.38)):
            sy = int(h * fy)
            img[sy + 3, 1:w - 1] = sil
            for xi in range(2, w - 2, 2):
                if rng.random() < 0.75:
                    hgt = rng.randint(3, 4)          # bottiglie: 2-3 px a 48 px/m, 3-4 a 60
                    if style == "farmacia":
                        c = rgb(rng.choice([W_[5], W_[2], "#cdc4d4"]))
                    elif style == "tabacchi":
                        c = rgb(rng.choice([W_[1], W_[2], "#b8303f", "#3b5fa0"]))
                    else:
                        c = rgb(rng.choice([W_[1], W_[0], W_[2], "#561a36"]))
                    img[sy + 3 - hgt:sy + 3, xi] = c
                    if style in ("bar", "osteria") and hgt == 4:
                        img[sy + 3 - hgt - 1, xi] = sil2
        cy = int(h * 0.62)
        img[cy:, :] = sil
        img[cy, :] = rgb(W_[3])
        img[cy + 1, :] = rgb(W_[2])
        if style == "bar":
            mx = int(w * 0.62)
            img[cy - 6:cy, mx:mx + 9] = rgb("#3e4a60")       # macchina del caffè
            img[cy - 6, mx:mx + 9] = rgb("#7686a0")
            img[cy - 4, mx + 2] = rgb("#e02a3a")
            img[cy - 4, mx + 6] = rgb("#e02a3a")
        if style == "kebab":
            kx = int(w * 0.72)
            img[int(h * 0.22):cy, kx - 3:kx + 4] = rgb("#86482a")      # spiedo
            img[int(h * 0.22):cy, kx - 1:kx + 1] = rgb("#b8663a")
            img[int(h * 0.22) - 1, kx - 2:kx + 3] = rgb("#3e4a60")
            my = int(h * 0.08)                                          # menu luminoso
            img[my:my + 8, 2:17] = rgb("#29252f")
            img[my + 1:my + 7:2, 3:16:2] = rgb("#e08c4c")
        if style in ("bar", "osteria", "kebab", "tabacchi"):
            sx_ = int(w * (0.3 if style != "kebab" else 0.42))
            head = (yy - int(h * 0.44)) ** 2 + (xx - sx_) ** 2 <= 8
            body = (yy > int(h * 0.49)) & (np.abs(xx - sx_) <= 4) & (yy < cy + 1)
            img[head | body] = sil2
        if style == "tabacchi":
            for bx in range(3, w - 9, 12):                              # gratta e vinci sul banco
                img[cy + 3:cy + 9, bx:bx + 9] = rgb("#d8b040")
                img[cy + 4, bx + 1:bx + 8] = rgb("#b8303f")
                img[cy + 7, bx + 1:bx + 8] = rgb("#3b5fa0")
        if style == "farmacia":
            img[cy + 3:cy + 6, 3:w - 3] = rgb(W_[4])
            img[cy + 4, 4:w - 4:3] = rgb("#e02a3a")
    elif style == "door":
        img[:] = back
        img[yy > h * 0.6] = back_lo
        img[yy < 3] = top
        img[:, 2] = sil
        img[:, w - 3] = sil
        img[int(h * 0.5), 3:w - 3] = rgb(W_[2])
    diag = (((xx + yy) % E.px(13)) == 0) | (((xx + yy) % E.px(13)) == 1)
    diag &= (yy < h * 0.55) & ((xx * 3 + yy) % 7 != 0)
    img[diag] = np.clip(img[diag] * 1.25 + 0.05, 0, 1)
    img[0, :] = sil
    em = img * 0.92
    cv.paste(x0, y0, img, msk, where, em)


def op_window_neon(cv: Canvas, o):
    """Piccola scritta al neon appesa dietro il vetro (APERTO, 24H, VINO...)."""
    where = cv.oid == o["oid"]
    if not where.any():
        return
    Yf = cv.face_y_of(o["oid"])
    x0, x1, y0, y1 = cv.front_rect(o["X0"], o["X1"], o["z0"], o["z1"], Yf)
    mask = PF.render(o["text"], PF.FONT3x5, 1, 1)
    rgbm, al, em, pad = neon_bitmap(mask, o["ramp"], ring=1, core_idx=5, tube_idx=3, halo_idx=2)
    ox = x0 + int((x1 - x0 - al.shape[1]) * o.get("fx", 0.5))
    oy = y0 + int((y1 - y0 - al.shape[0]) * o.get("fy", 0.3))
    cv.paste(ox, oy, rgbm, al, where, em, neon=True)


def op_door_panels(cv: Canvas, o):
    """Porte in legno: specchiature e maniglia."""
    where = cv.oid == o["oid"]
    if not where.any():
        return
    Yf = cv.face_y_of(o["oid"])
    x0, x1, y0, y1 = cv.front_rect(o["X0"], o["X1"], o["z0"], o["z1"], Yf)
    w, h = x1 - x0, y1 - y0
    img = np.zeros((h, w, 3), np.float32)
    msk = np.zeros((h, w), bool)
    base = cv.col[min(max(y0 + h // 2, 0), cv.H - 1), min(max(x0 + w // 2, 0), cv.W - 1)].copy()
    # due ante con specchiature (riquadri incisi)
    for (ax0, ax1) in ((2, w // 2 - 1), (w // 2 + 1, w - 2)):
        for (py0, py1) in ((int(h * 0.08), int(h * 0.45)), (int(h * 0.52), int(h * 0.92))):
            msk[py0, ax0:ax1] = msk[py1, ax0:ax1] = True
            msk[py0:py1, ax0] = msk[py0:py1, ax1 - 1] = True
            img[py0, ax0:ax1] = base * 0.6
            img[py0:py1, ax0] = base * 0.6
            img[py1, ax0:ax1] = base * 1.25
            img[py0:py1, ax1 - 1] = base * 1.25
    msk[:, w // 2] = True
    img[:, w // 2] = base * 0.5
    hy = int(h * 0.5)
    for hx in (w // 2 - 2, w // 2 + 2):
        msk[hy, hx] = True
        img[hy, hx] = rgb("#d8b040")
    cv.paste(x0, y0, img, msk, where, None, final=False)


def op_fence(cv: Canvas, o):
    """Rete a maglie romboidali (o cancello a sbarre) su un piano verticale, con test di profondità:
    dove la rete è davanti, i fili coprono e i buchi lasciano vedere ciò che c'è dietro (o il vuoto)."""
    Y = o["Y"]
    x0, x1, y0, y1 = cv.front_rect(o["X0"], o["X1"], o["z0"], o["z1"], Y)
    x0, x1 = max(x0, 0), min(x1, cv.W)
    y0, y1 = max(y0, 0), min(y1, cv.H)
    if x1 <= x0 or y1 <= y0:
        return
    f = np.array(cv.meta["f"], np.float32)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    Xw = ((xx + cv.x0 + 0.5) - cv.kyx * Y) / cv.kx
    Zw = (cv.oy - cv.kyy * Y - (yy + cv.y0 + 0.5)) / cv.kz
    dpanel = Xw * f[0] + Y * f[1] + Zw * f[2]
    behind = ~cv.A[y0:y1, x0:x1] | (cv.depth[y0:y1, x0:x1] > dpanel + 0.02)
    gx, gy = xx + cv.x0, yy + cv.y0
    if o.get("style") == "bars":
        wire = (gx % E.px(4) == 0)
        col = rgb("#3a4256")
    else:
        sag = 0
        wire = ((gx + gy) % E.px(4) == 0) | ((gx - gy) % E.px(4) == 0)
        # qualche buco nella rete e un lembo piegato
        rng = np.random.default_rng(o.get("seed", 0))
        holes = vnoise((y1 - y0, x1 - x0), E.px(9), o.get("seed", 0) + 5, x0, y0) > 0.8
        wire &= ~holes
        col = rgb("#414a60")
    m = behind & wire
    sub = (slice(y0, y1), slice(x0, x1))
    cv.col[sub][m] = col
    cv.A[sub][m] = True
    cv.mat[sub][m] = 7
    cv.cls[sub][m] = C["FENCE"]
    cv.oid[sub][m] = 60000
    cv.n[sub][m] = np.array([-0.5, -0.18, 0.84], np.float32)
    cv.depth[sub][m] = dpanel[m]
    cv.pos[sub][m] = np.stack([Xw[m], np.full(m.sum(), Y, np.float32), Zw[m]], -1)
    cv.is_em[sub][m] = False
    cv.emi[sub][m] = 0
    cv.noline[sub][m] = True


def op_barbed(cv: Canvas, o):
    """Filo spinato sopra la rete: due fili attorcigliati con le punte; solo dove il filo è davanti."""
    Y = o["Y"]
    x0, x1, ya, yb = cv.front_rect(o["X0"], o["X1"], o["z"], o["z"] + 0.12, Y)
    f = np.array(cv.meta["f"], np.float32)

    def put(yy, x, c):
        if not (0 <= yy < cv.H and 0 <= x < cv.W):
            return
        Xw = ((x + cv.x0 + 0.5) - cv.kyx * Y) / cv.kx
        Zw = (cv.oy - cv.kyy * Y - (yy + cv.y0 + 0.5)) / cv.kz
        d = Xw * f[0] + Y * f[1] + Zw * f[2]
        if cv.A[yy, x] and cv.depth[yy, x] < d - 0.02:
            return
        cv.col[yy, x] = rgb(c)
        cv.A[yy, x] = True
        cv.mat[yy, x] = 7
        cv.cls[yy, x] = C["CABLE"]
        cv.oid[yy, x] = 60001
        cv.noline[yy, x] = True
        cv.pos[yy, x] = (Xw, Y, Zw)
        cv.depth[yy, x] = d
        cv.n[yy, x] = (-0.5, -0.18, 0.84)
        cv.is_em[yy, x] = False

    tw = E.px(3)      # passo dell'attorcigliatura; le punte ogni due passi
    for x in range(max(x0, 0), min(x1, cv.W)):
        y = ya + (2 if (x // tw) % 2 else 1)
        put(y, x, "#4a5266")
        if (x % tw) == 1:
            put(y + 1, x, "#4a5266")
        if x % (2 * tw) == 0:
            put(ya, x, "#5a6278")


def op_rivets(cv: Canvas, o):
    pass   # già nel motivo "rivets" del materiale acciaio


def ground_op_mask(cv, o, z):
    X, Y = cv.ground_XY(z)
    return X, Y


def op_puddle(cv: Canvas, o):
    """Pozzanghera: ellisse irregolare sul suolo, superficie scura che riflette (il riflesso si fa nella luce)."""
    z = o.get("z", 0.0)
    X, Y = cv.ground_XY(z)
    rng = np.random.default_rng(o["seed"])
    ph = rng.random(3) * 6.28
    dx = (X - o["X"]) / o["rx"]
    dy = (Y - o["Y"]) / o["ry"]
    ang = np.arctan2(dy, dx)
    rr = 1 + 0.16 * np.sin(2 * ang + ph[0]) + 0.1 * np.sin(3 * ang + ph[1]) + 0.07 * np.sin(5 * ang + ph[2])
    d = np.sqrt(dx * dx + dy * dy) / rr
    ground = cv.A & np.isin(cv.cls, E.GROUND + [C["SIDEWALK"]]) & ~cv.is_em & (np.abs(cv.pos[..., 2] - z) < 0.06)
    m = ground & (d < 1.0)
    edge = ground & (d >= 1.0) & (d < 1.12)
    cv.mat[m] = 39
    cv.cls[m] = C["PUDDLE"]
    cv.col[m] = rgb("#0d0a16")
    cv.wet[m] = 1.0
    cv.col[edge] *= 0.78
    cv.wet[edge] = np.maximum(cv.wet[edge], 0.6)


def op_patch(cv: Canvas, o):
    z = o.get("z", 0.0)
    X, Y = cv.ground_XY(z)
    dx = (X - o["X"]) / o["rx"]
    dy = (Y - o["Y"]) / o["ry"]
    rng = np.random.default_rng(o["seed"])
    k = rng.uniform(0.85, 1.12)
    box = (np.abs(dx) < 1) & (np.abs(dy) < 1)
    ground = cv.A & (cv.mat == 11) & (np.abs(cv.pos[..., 2] - z) < 0.06)
    m = ground & box
    cv.col[m] *= k
    edge = ground & ~box & (np.abs(dx) < 1.05) & (np.abs(dy) < 1.18)
    cv.col[edge] *= 0.8


def op_crack(cv: Canvas, o):
    rng = random.Random(o["seed"])
    Xc, Yc = o["X"], o["Y"]
    ang = rng.uniform(-0.6, 0.6)
    pts = [(Xc, Yc)]
    L = o["length"]
    n = 10
    for i in range(n):
        ang += rng.uniform(-0.5, 0.5)
        Xc += math.cos(ang) * L / n
        Yc += math.sin(ang) * L / n * 0.5
        pts.append((Xc, Yc))
        if rng.random() < 0.15:
            b = rng.uniform(-1.2, 1.2)
            pts.append((Xc + math.cos(ang + b) * 0.15, Yc + math.sin(ang + b) * 0.08))
            pts.append((Xc, Yc))
    for (Xa, Ya), (Xb, Yb) in zip(pts[:-1], pts[1:]):
        for t in np.linspace(0, 1, 8):
            Xp, Yp = Xa + (Xb - Xa) * t, Ya + (Yb - Ya) * t
            z = 0.0 if Yp > E.BAND[0] else 0.0
            for zz in (0.0, -0.12):
                x = int(cv.sx(Xp, Yp))
                y = int(cv.sy(Yp, zz))
                if 0 <= x < cv.W and 0 <= y < cv.H and cv.A[y, x] and cv.mat[y, x] in (11, 12, 6, 26) \
                        and abs(cv.pos[y, x, 2] - zz) < 0.05:
                    cv.col[y, x] *= 0.62


def op_litter(cv: Canvas, o):
    rng = random.Random(o["seed"])
    for zz in (0.0, -0.12):
        x = int(cv.sx(o["X"], o["Y"]))
        y = int(cv.sy(o["Y"], zz))
        if not (2 <= x < cv.W - 3 and 1 <= y < cv.H - 2):
            continue
        if not (cv.A[y, x] and cv.mat[y, x] in (11, 12, 6, 14) and abs(cv.pos[y, x, 2] - zz) < 0.05):
            continue
        kind = rng.random()
        if kind < 0.4:      # carta
            c = rgb(rng.choice(["#aaa1b4", "#857d90", "#cdc4d4"]))
            for (dx, dy) in ((0, 0), (1, 0), (2, 0), (1, -1)):
                cv.col[y + dy, x + dx] = c * (0.8 if dy else 1.0)
        elif kind < 0.7:    # lattina
            cv.col[y, x] = rgb("#b8303f")
            cv.col[y, x + 1] = rgb("#aaa1b4")
        elif kind < 0.85:   # mozziconi
            cv.col[y, x] = rgb("#cdc4d4")
            cv.col[y, x + 3] = rgb("#aaa1b4")
        else:               # macchia d'olio
            for dx in range(-2, 3):
                cv.col[y, x + dx] *= 0.7
                cv.wet[y, x + dx] = 0.5


def op_lane(cv: Canvas, o):
    X, Y = cv.ground_XY(o["z"])
    on = (np.abs(Y - o["Y"]) < 0.06) & (X > o["X0"]) & (X < o["X1"])
    per = o["dash"] + o["gap"]
    on &= ((X - o["X0"]) % per) < o["dash"]
    m = on & cv.A & (np.abs(cv.pos[..., 2] - o["z"]) < 0.05) & np.isin(cv.mat, [11, 6, 39])
    worn = hash2(cv.xx, cv.yy, 77) > 0.72
    cv.col[m & ~worn] = rgb(o["col"]) * 0.75


def op_grate(cv: Canvas, o):
    X, Y = cv.ground_XY(o["z"])
    m = (X > o["X0"]) & (X < o["X1"]) & (Y > o["Y0"]) & (Y < o["Y1"]) & cv.A & (cv.mat == 7)
    bars = (cv.xx % 2 == 0)
    cv.col[m & bars] = rgb("#2e3649")
    cv.col[m & ~bars] = rgb("#07060c")
    cv.noline[m] = True


def op_awning_text(cv: Canvas, o):
    """Scritta sulla mantovana della tenda (testo chiaro 3x5)."""
    t = PF.render(o["text"], PF.FONT3x5, 1, 1)
    # mantovana: pixel AWNING con normale verso la telecamera nella fascia bassa della tenda
    xa = int(cv.sx(o["X0"], 0.0))
    xb = int(cv.sx(o["X1"], 0.0))
    m = cv.A & (cv.cls == C["AWNING"]) & (cv.n[..., 1] < 0.3)
    m[:, :max(xa - E.px(30), 0)] = False
    m[:, xb + E.px(40):] = False
    ys, xs = np.nonzero(m)
    if not len(ys):
        return
    cy = int(np.median(ys))
    cx = int((xs.min() + xs.max()) / 2)
    th, tw = t.shape
    for yy in range(th):
        for xx in range(tw):
            if t[yy, xx]:
                y, x = cy - th // 2 + yy, cx - tw // 2 + xx
                if 0 <= y < cv.H and 0 <= x < cv.W and m[y, x]:
                    cv.col[y, x] = rgb("#cdc4d4")


def op_menu_board(cv: Canvas, o):
    """Lavagna dell'osteria: piccola, con righe di gesso."""
    pass


def op_lamp_cone(cv: Canvas, o):
    """Cono di luce di una lampada a muro, per i piani a toni (cel): sulla facciata sotto la lampada due bande a bordo
    netto, la vicina più stretta e corta, la lontana più larga e lunga, che si allargano verso il basso e finiscono
    tonde. Segna cv.cone (1 lontana, 2 vicina): nel cono quantize alza il colore di altrettanti toni della sua rampa."""
    Yf = o["Yf"]
    xc = cv.sx(o["X"], Yf)
    yt = cv.sy(Yf, o["z"])
    hw = 0.5 * o.get("w", 0.14) * cv.kx
    dy = (cv.yy - cv.y0 + 0.5) - yt
    dx = np.abs((cv.xx - cv.x0 + 0.5) - xc)
    wall = cv.A & ~cv.is_em & (np.abs(cv.pos[..., 1] - Yf) < 0.25) & (cv.pos[..., 2] > 0.02)
    for band, (ang, length) in ((1, (o.get("ang_far", 34.0), o.get("len_far", 1.5))),
                                (2, (o.get("ang_near", 22.0), o.get("len_near", 0.8)))):
        L = length * cv.kz
        side = np.maximum(dx - hw, 0.0)
        inside = (dy >= 0) & (side <= dy * math.tan(math.radians(ang))) & (dy * dy + side * side <= L * L) & wall
        cv.cone = np.where(inside, np.maximum(cv.cone, band), cv.cone)


OPS = dict(neon_text=op_neon_text, neon_vertical=op_neon_vertical, cross_blade=op_cross_blade, plate=op_plate,
           posters=op_posters, graffiti=op_graffiti, tabacchi_t=op_tabacchi_t, interior=op_interior,
           door_panels=op_door_panels, window_neon=op_window_neon, fence=op_fence, barbed=op_barbed, rivets=op_rivets, puddle=op_puddle,
           patch=op_patch, crack=op_crack, litter=op_litter, lane=op_lane, grate=op_grate,
           awning_text=op_awning_text, menu_board=op_menu_board, lamp_cone=op_lamp_cone)


def run_ops(cv: Canvas):
    # ordine: suolo e superfici, poi decorazioni, poi insegne (sopra a tutto), poi reti (test di profondità)
    order = ["patch", "crack", "lane", "grate", "puddle", "litter", "posters", "graffiti", "door_panels",
             "interior", "window_neon", "plate", "tabacchi_t", "awning_text", "neon_text", "neon_vertical", "cross_blade",
             "menu_board", "rivets", "fence", "barbed", "lamp_cone"]
    for kind in order:
        for o in cv.ops:
            if o["kind"] == kind:
                OPS[kind](cv, o)


# ------------------------------------------------------------------ 3-4. luce e palette
def blur(img, sigma):
    if sigma <= 0:
        return img.copy()
    return np.stack([ndi.gaussian_filter(img[..., c], sigma, mode="constant") for c in range(img.shape[-1])], -1)


def shade(cv: Canvas, layer_cfg):
    if layer_cfg.get("cel"):
        return shade_cel(cv, layer_cfg)
    A = cv.A
    nL = (cv.n * E.KEY_CAM).sum(-1)
    light = np.zeros((cv.H, cv.W, 3), np.float32)
    band = np.zeros((cv.H, cv.W), np.float32)
    for mid, m in MATERIALS.items():
        sel = A & (cv.mat == mid)
        if not sel.any():
            continue
        thr = m["bands"]
        b = np.zeros(sel.sum(), np.float32)
        for t in thr:
            b += (nL[sel] > t)
        band[sel] = b / max(len(thr), 1)
    amb = layer_cfg.get("amb", 0.62)
    key = layer_cfg.get("key", 0.62)
    light = AMB[None, None] * amb + KEYC[None, None] * (key * band)[..., None]
    # neon: sfocatura dell'emissivo in due misure (alone stretto e luce diffusa)
    E_lin = np.where(cv.is_em[..., None], lin(cv.emi), 0)
    s1, s2 = layer_cfg.get("spill_sigma", (3.0, 11.0))
    S = blur(E_lin, s1) * 3.0 + blur(E_lin, s2) * 1.8
    spill_k = np.vectorize(lambda m: MATERIALS.get(int(m), {}).get("spill", 1.0), otypes=[np.float32])(cv.mat)
    light = light + S * (spill_k * layer_cfg.get("spill", 1.0))[..., None]
    out = lin(cv.col) * light
    # suolo bagnato: riflessi verticali delle luci della facciata (specchio compresso) + pozzanghere
    if layer_cfg.get("wet", 0) > 0:
        out = out + wet_reflections(cv, E_lin, layer_cfg)
    # emissivi: il loro colore pieno
    out = np.where(cv.is_em[..., None], lin(cv.emi), out)
    out = np.where(cv.final[..., None] & ~cv.is_em[..., None], lin(cv.col) * np.maximum(light, 0.55), out)
    return E.lin_to_srgb(np.clip(out, 0, 1)), S


def wet_reflections(cv: Canvas, E_lin, cfg):
    """Riflessi sull'asfalto bagnato (stile pixel art, non fisico): le luci della facciata si specchiano sotto
    la sua base, compresse in verticale, allungate verso chi guarda e spezzate in strisce verticali.
    Deboli sul marciapiede, più forti in strada, pieni nelle pozzanghere."""
    H, W = cv.H, cv.W
    ground = cv.A & (cv.n[..., 1] > 0.5) & (cv.pos[..., 1] < 0.65) & (cv.pos[..., 2] < 0.05) & ~cv.is_em
    refl = np.zeros((H, W, 3), np.float32)
    src = ndi.uniform_filter1d(E_lin, 3, axis=1)
    comp = cfg.get("wet_comp", 0.5)
    y_base = int(round(E.OY - E.KYY * 0.6 - cv.y0))
    for y in range(H):
        if not ground[y].any():
            continue
        dy = y - y_base
        if dy <= 0:
            continue
        ys = y_base - int(dy / comp)
        if ys < 0:
            continue
        refl[y] = src[ys]
    refl = ndi.uniform_filter1d(refl, E.px(7), axis=0, origin=-(E.px(7) // 2))
    col_ph = (hash2(cv.xx, 0, 5) * E.px(9)).astype(int)
    col_len = E.px(2) + (hash2(cv.xx, 1, 6) * E.px(4)).astype(int)
    streak = ((cv.yy + col_ph) % (col_len + E.px(3))) < col_len
    streak &= (cv.xx % 2 == 0) | (hash2(cv.xx, 2, 7) > 0.6)
    road = cv.pos[..., 2] < -0.05
    k = np.where(road, cfg.get("wet", 0.2), cfg.get("wet", 0.2) * 0.6) * np.where(streak, 1.0, 0.25)
    pud = cv.mat == 39
    k = np.where(pud, 0.75, k)
    k = np.where(cv.wet > 0, np.maximum(k, cv.wet * 0.5 * np.where(streak, 1.0, 0.5)), k)
    fade = np.clip(1.0 - (cv.yy - y_base - cv.y0) / float(E.px(110)), 0.3, 1.0)
    out = refl * (k * fade)[..., None]
    out[~ground] = 0
    return out


# ------------------------------------------------------------------ 3-4 bis. cel shading (piani con "cel")
def zone_levels(I, valid, thr, how="media"):
    """Zone di I con il bordo netto: 0 sotto la prima soglia, poi 1, 2...; in ogni zona vale la media (o la
    mediana) di I sui pixel validi della zona; una zona vuota vale la sua soglia."""
    z = np.zeros(I.shape, np.int32)
    for t in thr:
        z += I > t
    lev = [0.0]
    for k in range(1, len(thr) + 1):
        m = valid & (z == k)
        if not m.any():
            lev.append(float(thr[k - 1]))
        else:
            lev.append(float(np.mean(I[m]) if how == "media" else np.median(I[m])))
    return np.asarray(lev, np.float32)[z]


def key_bands_cel(cv: Canvas, nL, key_thr):
    """Luce chiave a toni: il tono viene da soglie su n·L uguali per tutti i materiali (key_thr); il livello di ogni
    tono, per materiale, è la banda che le soglie del materiale danno alla mediana di n·L dei pixel di quel tono.
    Così una faccia piatta resta com'era e cambiano solo le superfici curve e i materiali con più toni."""
    idx = np.zeros(nL.shape, np.int32)
    for t in key_thr:
        idx += nL > t
    band = np.zeros(nL.shape, np.float32)
    for mid, m in MATERIALS.items():
        sel = cv.A & (cv.mat == mid)
        if not sel.any():
            continue
        thr = m["bands"]
        for k in range(len(key_thr) + 1):
            s = sel & (idx == k)
            if s.any():
                med = float(np.median(nL[s]))
                band[s] = sum(med > t for t in thr) / max(len(thr), 1)
    return band


def shade_cel(cv: Canvas, layer_cfg):
    """Come shade, ma a toni: luce chiave a toni (key_bands_cel), luce dei neon e riflessi sul bagnato a zone con il
    bordo netto (soglie cel.spill_thr e cel.wet_thr sull'intensità, livello = media della zona, tinta invariata)."""
    cel = layer_cfg["cel"]
    A = cv.A
    nL = (cv.n * E.KEY_CAM).sum(-1)
    band = key_bands_cel(cv, nL, cel["key_thr"])
    amb = layer_cfg.get("amb", 0.62)
    key = layer_cfg.get("key", 0.62)
    light = AMB[None, None] * amb + KEYC[None, None] * (key * band)[..., None]
    # neon: la stessa sfocatura dell'emissivo della luce sfumata, poi l'intensità a zone
    E_lin = np.where(cv.is_em[..., None], lin(cv.emi), 0)
    s1, s2 = layer_cfg.get("spill_sigma", (3.0, 11.0))
    S = blur(E_lin, s1) * 3.0 + blur(E_lin, s2) * 1.8
    spill_k = np.vectorize(lambda m: MATERIALS.get(int(m), {}).get("spill", 1.0), otypes=[np.float32])(cv.mat)
    Se = S * (spill_k * layer_cfg.get("spill", 1.0))[..., None]
    I = Se.max(-1)
    hue = Se / np.maximum(I, 1e-6)[..., None]
    how = cel.get("zone", "media")
    Iq = zone_levels(I, A & ~cv.is_em, cel["spill_thr"], how)
    light = light + hue * Iq[..., None]
    out = lin(cv.col) * light
    if layer_cfg.get("wet", 0) > 0:
        R = wet_reflections(cv, E_lin, layer_cfg)
        IR = R.max(-1)
        hR = R / np.maximum(IR, 1e-6)[..., None]
        IRq = zone_levels(IR, A & ~cv.is_em & (IR > 0), cel["wet_thr"], how)
        # nella corsia dove si cammina i riflessi sono più scuri: le strisce arancio delle insegne non devono
        # confondersi con gli stivali dei personaggi
        lane = (cv.yy >= E.BAND[0]) & (cv.yy <= E.BAND[1])
        IRq = np.where(lane, IRq * cel.get("wet_lane", 1.0), IRq)
        out = out + hR * IRq[..., None]
    out = np.where(cv.is_em[..., None], lin(cv.emi), out)
    out = np.where(cv.final[..., None] & ~cv.is_em[..., None], lin(cv.col) * np.maximum(light, 0.55), out)
    return E.lin_to_srgb(np.clip(out, 0, 1)), S


def quantize(cv: Canvas, rgb01, layer_cfg):
    """Colore più vicino nella rampa del materiale (+ rampe dei neon per i pixel illuminati)."""
    out = np.zeros_like(rgb01)
    A = cv.A
    dith = layer_cfg.get("dither", 0.03)
    lab_cache = {}
    for mid in np.unique(cv.mat[A]):
        m = MATERIALS.get(int(mid))
        sel = A & (cv.mat == mid) & ~cv.is_em
        if not sel.any():
            continue
        names = [m["ramp"]] + list(m.get("tint") or []) if m else ["wall_grey"]
        names = names + ["paper", "graffiti", "white"] if mid == 25 else names
        if layer_cfg.get("extra_ramps"):
            names = names + list(layer_cfg["extra_ramps"])
        pal, seg_end = [], []
        for nm in names:
            pal += RAMPS[nm]
            seg_end += [len(pal) - 1] * len(RAMPS[nm])
        c = rgb01[sel].copy()
        if m and m.get("dither") and dith > 0:
            c = np.clip(c * (1 + dith * (cv.bay[sel] - 0.47) * 2)[:, None], 0, 1)
        idx = E.nearest(c, pal, weights=(1.0, 1.3, 1.3))
        if layer_cfg.get("cel") and cv.cone.any():
            # coni delle lampade a muro (op_lamp_cone): il colore sale di 1 tono (banda lontana) o di 2 (banda
            # vicina) dentro la sua rampa; così il motivo della superficie resta pulito, senza puntini
            idx = np.minimum(idx + cv.cone[sel], np.asarray(seg_end)[idx])
        palv = np.array([E.hx(p) for p in pal], np.float32) / 255.0
        out[sel] = palv[idx]
    # emissivi: rampe dei neon, delle luci calde e del cyan
    sel = A & cv.is_em
    if sel.any():
        pal = RAMPS["neon_red"] + RAMPS["neon_orange"] + RAMPS["warm"] + RAMPS["white"] + ["#1c2a6a", "#0f1640"]
        if layer_cfg.get("cyan"):
            pal += RAMPS["cyan"]
        idx = E.nearest(rgb01[sel], pal, weights=(0.8, 1.5, 1.5))
        palv = np.array([E.hx(p) for p in pal], np.float32) / 255.0
        out[sel] = palv[idx]
    return out


# ------------------------------------------------------------------ 5. contorni
def outlines(cv: Canvas, rgb01, layer_cfg):
    A = cv.A
    outc = rgb(E.OUTLINE)
    res = rgb01.copy()
    alpha = A.copy()
    if layer_cfg.get("inner", True):
        thr = layer_cfg.get("depth_thr", 0.35)
        dep = np.where(A, cv.depth, 1e9)
        line = np.zeros_like(A)
        thin = np.isin(cv.cls, E.THIN) | cv.is_em | cv.noline | (cv.mat == 25)
        for dn, on, tn in zip(E.nb4(dep, 1e9), E.nb4(cv.oid, -2), E.nb4(thin, True)):
            line |= A & (dep - dn > thr) & (on != cv.oid) & ~tn
        line &= ~cv.is_em & ~cv.noline
        # linea interna: il colore più scuro della rampa del materiale (più morbido del nero)
        for mid in np.unique(cv.mat[line]):
            m = MATERIALS.get(int(mid))
            c = rgb(RAMPS[m["ramp"]][0]) if m else outc
            res[line & (cv.mat == mid)] = c
    if layer_cfg.get("outline", True):
        sil = np.zeros_like(A)
        for an in E.nb4(A, False):
            sil |= ~A & an
        if layer_cfg.get("outline_mask") is not None:
            sil &= layer_cfg["outline_mask"]
        res[sil] = outc
        alpha = alpha | sil
    return res, alpha


# ------------------------------------------------------------------ 6. maschera emissiva
def emissive_mask(cv: Canvas, rgb01, alpha, strength=0.55, cel=False):
    """Aloni additivi per Godot: attorno a neon e lampade un alone a due livelli retinato e il nucleo a metà
    intensità; le vetrine accese danno solo un alone debole (il loro interno resta com'è). Con cel i due anelli
    hanno il bordo netto (niente soglia retinata con la matrice di Bayer)."""
    neon = cv.neon & cv.is_em
    E_n = np.where(neon[..., None], lin(cv.emi), 0)
    E_w = np.where((cv.is_em & ~neon)[..., None], lin(cv.emi), 0) * 0.35
    s1, s2 = 1.6 * E.S, 4.5 * E.S      # misure di progetto (48 px/m) portate a 60 px/m
    near = blur(E_n, s1) * 2.4 + blur(E_w, s1) * 1.2
    far = blur(E_n, s2) * 2.0 + blur(E_w, s2) * 1.0
    I1 = near.max(-1)
    I2 = far.max(-1)
    hue1 = near / np.maximum(I1, 1e-6)[..., None]
    hue2 = far / np.maximum(I2, 1e-6)[..., None]
    dith = 0.0 if cel else 1.0
    lv1 = (I1 + (cv.bay - 0.5) * 0.12 * dith) > 0.22
    lv2 = (I2 + (cv.bay - 0.5) * 0.1 * dith) > 0.12
    if cel:
        lv2 |= cv.halo_fill & (I2 > 0.01)
    em = np.zeros((cv.H, cv.W, 3), np.float32)
    em[lv2] = hue2[lv2] * 0.16
    em[lv1] = hue1[lv1] * 0.3
    em[cv.is_em & ~neon] = 0
    em[neon] = np.maximum(em[neon], E.lin_to_srgb(lin(cv.emi[neon]) * 0.45))
    em = np.clip(em * strength / 0.55, 0, 1)
    out = np.zeros((cv.H, cv.W, 4), np.uint8)
    out[..., :3] = (em * 255 + 0.5).astype(np.uint8)
    out[..., 3] = np.where(em.max(-1) > 0.01, 255, 0)
    return out


def to_rgba(rgb01, alpha):
    out = np.zeros(rgb01.shape[:2] + (4,), np.uint8)
    out[..., :3] = (np.clip(rgb01, 0, 1) * 255 + 0.5).astype(np.uint8)
    out[..., 3] = np.where(alpha, 255, 0)
    return out


def load(scene, raw_dir=None):
    raw_dir = raw_dir or os.path.join(E.OUT, "raw")
    meta, D = E.gbuffer_1x(raw_dir, scene)
    ops = json.load(open(os.path.join(raw_dir, "%s_paint.json" % scene), encoding="utf-8"))["ops"]
    return Canvas(meta, D, ops)
