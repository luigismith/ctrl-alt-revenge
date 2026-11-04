# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Genera gli effetti visivi (strisce PNG + fx.json) in tools/fxui/out/assets/fx/.

  python -I tools/fxui/make_fx.py

Ogni effetto è una striscia orizzontale di fotogrammi della stessa misura; fx.json usa il
formato del §7 della specifica: image, frame [w, h], count, ticks (a 60 Hz), anchor [x, y]
(il punto del fotogramma che va sulla posizione dell'effetto). Campi in più, facoltativi:
loop, mode ("anim" o "variants": fotogrammi da scegliere, non da animare), flip, note.
Disegno procedurale con semi fissi: nessuna casualità non riproducibile, nessun
antialiasing; le dissolvenze sono retinature ordinate, come sulle console a 16 bit.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import palette as P  # noqa: E402
import pix  # noqa: E402

OUT = HERE / "out" / "assets" / "fx"


# ------------------------------------------------------------------------------------
# primitive
# ------------------------------------------------------------------------------------

def star_poly(cx, cy, tips, valley, rot=0.0, sx=1.0, sy=1.0):
    """Stella: 'tips' = lunghezze delle punte (una per punta), 'valley' = raggio delle gole."""
    n = len(tips)
    pts = []
    for k in range(n):
        a = rot + 2 * math.pi * k / n
        b = a + math.pi / n
        pts.append((cx + sx * tips[k] * math.cos(a), cy + sy * tips[k] * math.sin(a)))
        pts.append((cx + sx * valley * math.cos(b), cy + sy * valley * math.sin(b)))
    return pts


def star_mask(w, h, cx, cy, tips, valley, rot=0.0, scale=1.0, sx=1.0, sy=1.0):
    poly = star_poly(cx, cy, [t * scale for t in tips], valley * scale, rot, sx, sy)
    return pix.poly_mask(w, h, [poly])


def ring_mask(w, h, cx, cy, r_out, r_in, sy=1.0):
    return pix.ellipse_mask(w, h, cx, cy, r_out, r_out * sy) & ~pix.ellipse_mask(w, h, cx, cy, r_in, r_in * sy)


def line_pts(x0, y0, x1, y1):
    """Bresenham tra punti interi."""
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    out = []
    while True:
        out.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return out


def draw_line(mask, x0, y0, x1, y1):
    h, w = mask.shape
    for (x, y) in line_pts(x0, y0, x1, y1):
        if 0 <= x < w and 0 <= y < h:
            mask[y, x] = True


def ray_mask(w, h, cx, cy, ang, length, base_half=1.6, start=0.0):
    """Raggio affusolato dal centro verso l'esterno: triangolo sottile più la linea dell'asse
    (così la punta resta continua anche dove il triangolo è più stretto di un pixel)."""
    ca, sa = math.cos(ang), math.sin(ang)
    px, py = -sa, ca
    x0, y0 = cx + start * ca, cy + start * sa
    tri = [(x0 + px * base_half, y0 + py * base_half), (x0 - px * base_half, y0 - py * base_half),
           (cx + length * ca, cy + length * sa)]
    m = pix.poly_mask(w, h, [tri])
    draw_line(m, x0, y0, cx + (length - 0.5) * ca, cy + (length - 0.5) * sa)
    return m


def radial(w, h, cx, cy):
    ys, xs = np.mgrid[0:h, 0:w]
    return np.hypot(xs + 0.5 - cx, ys + 0.5 - cy)


def layered(w, h, layers):
    """layers: lista (maschera, colore) dal fondo verso l'alto."""
    img = pix.new(w, h)
    for m, c in layers:
        pix.paint(img, m, c)
    return img


# ------------------------------------------------------------------------------------
# scintille d'impatto (stile Streets of Rage 2)
# ------------------------------------------------------------------------------------

def _spikes(rng, n, long_, short_, jitter):
    """Punte alternate lunghe/corte con un po' di irregolarità."""
    t = []
    for k in range(n):
        base = long_ if k % 2 == 0 else short_
        t.append(base * (1.0 + rng.uniform(-jitter, jitter)))
    return t


def hit_spark_light():
    W = H = 24
    cx = cy = 12.0
    rng = np.random.default_rng(11)
    tips = _spikes(rng, 8, 11.5, 7.0, 0.12)
    rot = math.radians(4)
    frames = []
    # 0: lampo piccolo e pieno
    m_out = star_mask(W, H, cx, cy, tips, 2.6, rot, 0.52)
    m_mid = star_mask(W, H, cx, cy, tips, 2.2, rot, 0.36)
    m_core = pix.disc_mask(W, H, cx, cy, 2.3)
    frames.append(layered(W, H, [(m_out, P.SPARK_YEL), (m_mid, P.SPARK_PALE), (m_core, P.WHITE)]))
    # 1: stella piena: bianco, giallo, arancio, punte rosse
    m_out = star_mask(W, H, cx, cy, tips, 3.8, rot)
    m_mid = star_mask(W, H, cx, cy, tips, 3.4, rot, 0.74)
    m_in = star_mask(W, H, cx, cy, tips, 3.0, rot, 0.48)
    m_core = pix.disc_mask(W, H, cx, cy, 3.4)
    edge = m_out & ~pix.dilate(m_out, 1, square=False) | (m_out & (radial(W, H, cx, cy) > 9.5))
    frames.append(layered(W, H, [(m_out, P.SPARK_ORA), (edge, P.SPARK_RED), (m_mid, P.SPARK_YEL),
                                 (m_in, P.SPARK_PALE), (m_core, P.WHITE)]))
    # 2: più grande, ruotata, il centro si svuota
    rot2 = rot + math.radians(9)
    m_out = star_mask(W, H, cx, cy, tips, 4.2, rot2, 1.06)
    m_mid = star_mask(W, H, cx, cy, tips, 3.6, rot2, 0.80)
    hole = pix.disc_mask(W, H, cx, cy, 3.2)
    r = radial(W, H, cx, cy)
    frames.append(layered(W, H, [(m_out & ~hole, P.SPARK_RED), (m_mid & ~hole, P.SPARK_ORA),
                                 (m_mid & ~hole & (r < 6.5), P.SPARK_YEL)]))
    # 3: restano le punte, che si sfaldano
    m_out = star_mask(W, H, cx, cy, tips, 4.2, rot2, 1.12)
    tipsonly = m_out & (r > 6.3)
    frames.append(layered(W, H, [(pix.dissolve(tipsonly, 0.8), P.SPARK_RED),
                                 (pix.dissolve(tipsonly & (r < 9.5), 0.8), P.SPARK_ORA),
                                 (pix.dissolve(tipsonly & (r < 7.6), 0.8), P.SPARK_YEL)]))
    return frames, (W, H), (12, 12), 2


def hit_spark_heavy():
    W = H = 40
    cx = cy = 20.0
    rng = np.random.default_rng(23)
    tips = _spikes(rng, 10, 18.5, 11.0, 0.14)
    rot = math.radians(-6)
    r = radial(W, H, cx, cy)
    frames = []
    # 0: lampo bianco con croce
    core = pix.disc_mask(W, H, cx, cy, 4.6)
    cross = np.zeros((H, W), bool)
    for k in range(4):
        cross |= ray_mask(W, H, cx, cy, k * math.pi / 2, 13.5, 2.2)
        cross |= ray_mask(W, H, cx, cy, k * math.pi / 2 + math.pi / 4, 8.0, 1.6)
    halo = pix.dilate(core | cross, 1, square=False)
    frames.append(layered(W, H, [(halo, P.SPARK_YEL), (cross, P.SPARK_PALE), (core, P.WHITE)]))
    # 1: stella grande a strati
    m_out = star_mask(W, H, cx, cy, tips, 6.0, rot)
    m_mid = star_mask(W, H, cx, cy, tips, 5.2, rot, 0.74)
    m_in = star_mask(W, H, cx, cy, tips, 4.6, rot, 0.50)
    m_core = pix.disc_mask(W, H, cx, cy, 5.2)
    edge = m_out & (r > 15.5)
    frames.append(layered(W, H, [(m_out, P.SPARK_ORA), (edge, P.SPARK_RED), (m_mid, P.SPARK_YEL),
                                 (m_in, P.SPARK_PALE), (m_core, P.WHITE)]))
    # 2: la stella si allarga e si svuota, parte l'anello d'urto
    rot2 = rot + math.radians(7)
    m_out = star_mask(W, H, cx, cy, tips, 6.4, rot2, 1.04)
    m_mid = star_mask(W, H, cx, cy, tips, 5.4, rot2, 0.78)
    hole = pix.disc_mask(W, H, cx, cy, 4.8)
    ring = ring_mask(W, H, cx, cy, 13.5, 12.2)
    frames.append(layered(W, H, [(m_out & ~hole, P.SPARK_RED), (m_mid & ~hole, P.SPARK_ORA),
                                 (m_mid & ~hole & (r < 10), P.SPARK_YEL), (ring, P.SPARK_PALE)]))
    # 3: punte staccate e anello più largo, arancio
    m_out = star_mask(W, H, cx, cy, tips, 6.4, rot2, 1.1)
    tipsonly = m_out & (r > 11.0)
    ring = ring_mask(W, H, cx, cy, 16.6, 15.4)
    frames.append(layered(W, H, [(pix.dissolve(tipsonly, 0.7), P.SPARK_RED),
                                 (pix.dissolve(tipsonly & (r < 15), 0.7), P.SPARK_ORA),
                                 (pix.dissolve(ring, 0.75), P.SPARK_YEL)]))
    # 4: scintille sparse
    sp = np.zeros((H, W), bool)
    for k in range(12):
        a = 2 * math.pi * k / 12 + 0.21 * (k % 3)
        rr = 17.0 + (k % 4) * 0.8
        x, y = int(cx + rr * math.cos(a)), int(cy + rr * math.sin(a))
        if 0 <= x < W and 0 <= y < H:
            sp[y, x] = True
            if k % 2 == 0 and 0 <= x + 1 < W:
                sp[y, x + 1] = True
    ring = ring_mask(W, H, cx, cy, 18.6, 17.6)
    frames.append(layered(W, H, [(pix.dissolve(ring, 0.35), P.SPARK_RED), (sp, P.SPARK_ORA)]))
    return frames, (W, H), (20, 20), 2


# ------------------------------------------------------------------------------------
# glint: scintilla a stella che annuncia il colpo caricato
# ------------------------------------------------------------------------------------

def glint():
    W = H = 25
    c = 12
    frames = []

    def sparkle(arm, diag, core, rot45=False, bright=True):
        img = pix.new(W, H)
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        ddirs = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
        if rot45:
            dirs, ddirs = ddirs, dirs
        cols = [P.WHITE, P.SPARK_PALE, P.SPARK_YEL, P.SPARK_ORA] if bright else \
            [P.SPARK_PALE, P.SPARK_YEL, P.SPARK_ORA, P.SPARK_RED]
        for (dx, dy) in dirs:
            for k in range(1, arm + 1):
                t = k / max(1, arm)
                ci = 0 if t <= 0.35 else 1 if t <= 0.65 else 2 if t <= 0.9 else 3
                img[c + dy * k, c + dx * k] = cols[ci]
        for (dx, dy) in ddirs:
            for k in range(1, diag + 1):
                t = k / max(1, diag)
                img[c + dy * k, c + dx * k] = cols[1] if t < 0.6 else cols[2]
        if core >= 1:
            for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                img[c + dy, c + dx] = cols[0]
        if core >= 2:
            for (dx, dy) in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                img[c + dy, c + dx] = cols[1]
            for (dx, dy) in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                img[c + dy, c + dx] = cols[0]
        img[c, c] = P.WHITE
        return img

    frames.append(sparkle(2, 0, 0))
    frames.append(sparkle(5, 1, 1))
    frames.append(sparkle(8, 2, 1))
    frames.append(sparkle(11, 3, 2))
    frames.append(sparkle(6, 2, 1, rot45=True))
    frames.append(sparkle(3, 0, 0, bright=False))
    return frames, (W, H), (12, 12), 2


# ------------------------------------------------------------------------------------
# scarica cyber (gancio di GIG)
# ------------------------------------------------------------------------------------

def _bolt(rng, cx, cy, ang, length, step=2.6, wiggle=0.55):
    pts = [(cx + 2.5 * math.cos(ang), cy + 2.5 * math.sin(ang))]
    a = ang
    dist = 2.5
    while dist < length:
        a = ang + rng.uniform(-wiggle, wiggle)
        x, y = pts[-1]
        pts.append((x + step * math.cos(a), y + step * math.sin(a)))
        dist += step
    return pts


def _bolts(W, H, cx, cy, seed, n, lmin, lmax, forward=0.35, fork=0.4):
    rng = np.random.default_rng(seed)
    core = np.zeros((H, W), bool)
    for k in range(n):
        base = 2 * math.pi * k / n + rng.uniform(-0.35, 0.35)
        # spinta in avanti (+x): il gancio colpisce verso destra
        base = math.atan2(math.sin(base), math.cos(base) + forward)
        L = rng.uniform(lmin, lmax)
        pts = _bolt(rng, cx, cy, base, L)
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            draw_line(core, x0, y0, x1, y1)
        if rng.random() < fork and len(pts) > 3:
            i = int(rng.integers(1, len(pts) - 2))
            fa = base + rng.choice([-0.8, 0.8])
            fpts = _bolt(rng, pts[i][0] - 2.5 * math.cos(fa), pts[i][1] - 2.5 * math.sin(fa), fa, L * 0.45)
            for (x0, y0), (x1, y1) in zip(fpts, fpts[1:]):
                draw_line(core, x0, y0, x1, y1)
    return core


def cyber_spark():
    W = H = 40
    cx = cy = 20.0
    r = radial(W, H, cx, cy)
    frames = []
    # 0: lampo e archi corti
    core = _bolts(W, H, cx, cy, 101, 5, 7, 10)
    flash = pix.disc_mask(W, H, cx, cy, 3.2)
    glow = pix.dilate(core | flash, 1, square=False)
    halo = pix.disc_mask(W, H, cx, cy, 5.4)
    frames.append(layered(W, H, [(halo, P.CYAN_MID), (glow, P.CYAN), (core, P.CYAN_WHITE), (flash, P.WHITE)]))
    # 1: archi lunghi
    core = _bolts(W, H, cx, cy, 202, 6, 13, 18)
    flash = pix.disc_mask(W, H, cx, cy, 3.6)
    glow = pix.dilate(core | flash, 1, square=False)
    outer = pix.dissolve(pix.dilate(glow, 1, square=False) & ~glow, 0.5)
    frames.append(layered(W, H, [(outer, P.CYAN_DEEP), (glow, P.CYAN), (core, P.CYAN_WHITE),
                                 (flash, P.WHITE), (pix.disc_mask(W, H, cx, cy, 1.6), P.WHITE)]))
    # 2: archi nuovi, il centro si stringe
    core = _bolts(W, H, cx, cy, 303, 6, 14, 19)
    flash = pix.disc_mask(W, H, cx, cy, 2.2)
    glow = pix.dilate(core | flash, 1, square=False)
    outer = pix.dissolve(pix.dilate(glow, 1, square=False) & ~glow, 0.4)
    frames.append(layered(W, H, [(outer, P.CYAN_DEEP), (glow, P.CYAN_MID), (core, P.CYAN_HI),
                                 (flash, P.CYAN_WHITE)]))
    # 3: archi spezzati e scintille
    core = _bolts(W, H, cx, cy, 404, 5, 13, 18)
    core = pix.dissolve(core, 0.6, 1, 2) & (r > 4)
    glow = pix.dissolve(pix.dilate(core, 1, square=False), 0.5)
    sp = np.zeros((H, W), bool)
    rng = np.random.default_rng(405)
    for _ in range(7):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(12, 18)
        x, y = int(cx + rr * math.cos(a)), int(cy + rr * math.sin(a))
        sp[y, x] = True
    frames.append(layered(W, H, [(glow, P.CYAN_DEEP), (core, P.CYAN), (sp, P.CYAN_HI)]))
    # 4: residui
    core = _bolts(W, H, cx, cy, 505, 4, 12, 17)
    core = pix.dissolve(core, 0.3, 2, 1) & (r > 7)
    sp = np.zeros((H, W), bool)
    for _ in range(5):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(15, 19)
        x, y = int(cx + rr * math.cos(a)), int(cy + rr * math.sin(a))
        sp[y, x] = True
    frames.append(layered(W, H, [(core, P.CYAN_DEEP), (sp, P.CYAN)]))
    return frames, (W, H), (20, 20), 2


# ------------------------------------------------------------------------------------
# polvere
# ------------------------------------------------------------------------------------

def cloud(img, cx, cy, rx, ry, keep=1.0, ground=None, seed=0):
    """Nuvola di polvere: grappolo di sbuffi tondi sovrapposti, bordo a bozzi.

    Luce dall'alto: bordo superiore chiaro, inferiore più scuro, interno pieno. Niente
    ombreggiatura da sfera (sembrerebbero sassi). 'keep' < 1 sfalda con una retinatura.
    """
    h, w = img.shape[:2]
    rng = np.random.default_rng(seed)
    m = pix.ellipse_mask(w, h, cx, cy + ry * 0.15, rx * 0.8, ry * 0.65)
    n = 4 + int(rx > 6)
    for i in range(n):
        a = math.pi * (i + 0.5) / n + rng.uniform(-0.25, 0.25)
        ox = -math.cos(a) * rx * 0.62
        oy = -math.sin(a) * ry * 0.45
        rr = ry * rng.uniform(0.5, 0.68)
        m |= pix.disc_mask(w, h, cx + ox, cy + oy, rr)
    if ground is not None:
        m &= (np.arange(h)[:, None] <= ground)
    top = m & ~pix.shift(m, 0, 1)
    top |= m & ~pix.shift(m, 0, 2) & pix.dissolve(np.ones_like(m), 0.5)
    bottom = m & ~pix.shift(m, 0, -1)
    if keep < 1.0:
        sel = pix.dissolve(np.ones((h, w), bool), keep, seed % 4, (seed // 4) % 4)
        m &= sel
        top &= sel
        bottom &= sel
    pix.paint(img, m, P.DUST)
    pix.paint(img, bottom, P.DUST_MID)
    pix.paint(img, top, P.DUST_HI)


def dust_land():
    W, H = 64, 24
    gx, gy = 32, 22          # ancora: punto a terra
    plan = [
        # (scostamento, semiasse x, semiasse y, alzata, conservazione) per fotogramma
        [(-6, 7.0, 3.0, 0, 1.0), (6, 7.0, 3.0, 0, 1.0)],
        [(-12, 7.5, 4.5, 0, 1.0), (12, 7.5, 4.5, 0, 1.0), (0, 5.0, 2.6, 0, 1.0)],
        [(-17, 8.0, 5.5, 1, 1.0), (17, 8.0, 5.5, 1, 1.0), (-6, 5.0, 3.2, 0, 0.9), (6, 5.0, 3.2, 0, 0.9)],
        [(-21, 8.0, 6.0, 2, 0.8), (21, 8.0, 6.0, 2, 0.8), (-9, 4.6, 3.2, 1, 0.6), (9, 4.6, 3.2, 1, 0.6)],
        [(-24, 7.4, 5.6, 3, 0.5), (24, 7.4, 5.6, 3, 0.5)],
        [(-27, 6.4, 5.0, 4, 0.22), (27, 6.4, 5.0, 4, 0.22)],
    ]
    frames = []
    for i, puffs in enumerate(plan):
        img = pix.new(W, H)
        for j, (dx, rx, ry, rise, keep) in enumerate(puffs):
            cloud(img, gx + dx, gy - ry * 0.75 - rise, rx, ry, keep, ground=gy, seed=40 + j * 7 + (dx < 0))
        frames.append(img)
    return frames, (W, H), (gx, gy), 3


def dust_skid():
    W, H = 32, 20
    fx, fy = 24, 18          # ancora: il piede (il pennacchio va verso -x)
    plan = [
        [(-2, 3.6, 2.2, 0, 1.0)],
        [(-5, 5.0, 3.2, 1, 1.0)],
        [(-9, 6.0, 4.0, 2, 1.0), (-1, 3.4, 2.2, 0, 0.9)],
        [(-13, 6.2, 4.4, 4, 0.65), (-5, 3.6, 2.6, 1, 0.55)],
        [(-16, 5.6, 4.0, 6, 0.28), (-8, 3.2, 2.4, 2, 0.25)],
    ]
    frames = []
    for i, puffs in enumerate(plan):
        img = pix.new(W, H)
        for j, (dx, rx, ry, rise, keep) in enumerate(puffs):
            cloud(img, fx + dx, fy - ry * 0.8 - rise, rx, ry, keep, ground=fy, seed=60 + j * 5)
        frames.append(img)
    return frames, (W, H), (fx, fy), 3


# ------------------------------------------------------------------------------------
# ombra, pioggia, KO
# ------------------------------------------------------------------------------------

def ombra():
    W, H = 48, 12
    cx, cy = 24.0, 6.0
    frames = []
    # fotogramma 0 = la più grande, che riempie il fotogramma: va bene anche a chi la stira
    for (rx, ry) in ((23, 5), (18, 4), (12, 3)):
        img = pix.new(W, H)
        outer = pix.ellipse_mask(W, H, cx, cy, rx, ry)
        inner = pix.ellipse_mask(W, H, cx, cy, rx * 0.72, ry * 0.62)
        # Alfa alte: l'asfalto di "Sotto la Linea" è già scuro, con 96/150 l'ombra in gioco
        # quasi non si vedeva (integrazione del 3/11/2026).
        pix.paint(img, outer, pix.with_alpha(P.SHADOW, 150))
        pix.paint(img, inner, pix.with_alpha(P.SHADOW, 205))
        frames.append(img)
    return frames, (W, H), (24, 6), 0


RAIN_SLANT = 4   # la pioggia scende di 4 px per ogni px verso sinistra (pendenza 0,25)


def _streak(img, x_head, y_head, length, alpha_head=210, alpha_tail=50):
    """Goccia sottile: testa in basso, coda in alto a destra (cade verso sinistra)."""
    for k in range(length):
        y = y_head - k
        x = x_head + (k + RAIN_SLANT // 2) // RAIN_SLANT
        t = k / max(1, length - 1)
        a = int(round(alpha_head + (alpha_tail - alpha_head) * t))
        col = P.RAIN_HI if k == 0 else P.RAIN if t < 0.6 else P.RAIN_LO
        if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
            img[y, x] = pix.with_alpha(col, a)


def rain_streak():
    W, H = 6, 16
    frames = []
    for length in (7, 10, 13, 16):
        img = pix.new(W, H)
        _streak(img, 1, H - 1, length)
        frames.append(img)
    return frames, (W, H), (1, 15), 0


def rain_sheet():
    """Tessera di pioggia ripetibile (128x128) da far scorrere: alternativa alle gocce singole."""
    W = H = 128
    rng = np.random.default_rng(77)
    img = pix.new(W, H)
    big = pix.new(W * 3, H * 3)
    for _ in range(26):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, H))
        length = int(rng.choice([7, 9, 11, 13, 15]))
        a = int(rng.integers(120, 200))
        for ox in (0, W, 2 * W):
            for oy in (0, H, 2 * H):
                _streak(big, x + ox, y + oy, length, alpha_head=a, alpha_tail=40)
    img[:] = big[H:2 * H, W:2 * W]
    # ricucitura: ciò che sborda da un lato rientra dall'altro
    for oy in (0, H, 2 * H):
        for ox in (0, W, 2 * W):
            if (ox, oy) == (W, H):
                continue
            tile = big[oy:oy + H, ox:ox + W]
            m = tile[..., 3] > img[..., 3]
            img[m] = tile[m]
    return [img], (W, H), (0, 0), 0


def rain_splash():
    W, H = 12, 8
    cx, gy = 6, 7
    frames = []
    hi = pix.with_alpha(P.RAIN_HI, 230)
    mid = pix.with_alpha(P.RAIN, 190)
    lo = pix.with_alpha(P.RAIN_LO, 130)
    # 0: piccolo schizzo verticale
    img = pix.new(W, H)
    img[gy, cx - 1:cx + 1] = mid
    img[gy - 1, cx - 1] = hi
    img[gy - 2, cx] = hi
    frames.append(img)
    # 1: corona
    img = pix.new(W, H)
    img[gy, cx - 2:cx + 2] = mid
    for (x, y) in ((cx - 3, gy - 1), (cx + 2, gy - 1), (cx - 3, gy - 2), (cx + 2, gy - 2),
                   (cx - 4, gy - 3), (cx + 3, gy - 3)):
        img[y, x] = hi
    frames.append(img)
    # 2: goccioline che volano via e anello a terra
    img = pix.new(W, H)
    ring = ring_mask(W, H, cx, gy + 0.5, 4.2, 2.6, sy=0.38)
    pix.paint(img, ring, lo)
    for (x, y) in ((cx - 5, gy - 4), (cx + 4, gy - 4), (cx - 1, gy - 5)):
        img[y, x] = mid
    frames.append(img)
    # 3: anello largo che svanisce
    img = pix.new(W, H)
    ring = ring_mask(W, H, cx, gy + 0.5, 5.6, 4.2, sy=0.34)
    pix.paint(img, pix.dissolve(ring, 0.5), lo)
    for (x, y) in ((cx - 6, gy - 2), (cx + 5, gy - 2)):
        img[y, x] = lo
    frames.append(img)
    return frames, (W, H), (cx, gy), 3


def ko_flash():
    W = H = 64
    cx = cy = 32.0
    r = radial(W, H, cx, cy)
    rng = np.random.default_rng(31)
    tips = _spikes(rng, 12, 28.0, 15.0, 0.12)
    frames = []
    # 0: lampo bianco con quattro raggi lunghi
    rays = np.zeros((H, W), bool)
    for k in range(4):
        rays |= ray_mask(W, H, cx, cy, k * math.pi / 2, 30.5, 3.0)
        rays |= ray_mask(W, H, cx, cy, k * math.pi / 2 + math.pi / 4, 17.0, 2.0)
    core = pix.disc_mask(W, H, cx, cy, 8.5)
    frames.append(layered(W, H, [(pix.dilate(rays | core, 1, square=False), P.SPARK_YEL),
                                 (rays, P.SPARK_PALE), (core, P.WHITE)]))
    # 1: stella enorme
    m_out = star_mask(W, H, cx, cy, tips, 9.0, 0.1)
    m_mid = star_mask(W, H, cx, cy, tips, 8.0, 0.1, 0.72)
    m_in = star_mask(W, H, cx, cy, tips, 7.0, 0.1, 0.48)
    core = pix.disc_mask(W, H, cx, cy, 9.5)
    frames.append(layered(W, H, [(m_out, P.SPARK_ORA), (m_out & (r > 23), P.SPARK_RED), (m_mid, P.SPARK_YEL),
                                 (m_in, P.SPARK_PALE), (core, P.WHITE)]))
    # 2: anello d'urto spesso, la stella si svuota
    ring = ring_mask(W, H, cx, cy, 23.5, 20.0)
    ring_in = ring_mask(W, H, cx, cy, 22.2, 20.6)
    m_mid = star_mask(W, H, cx, cy, tips, 8.0, 0.25, 0.7)
    hole = pix.disc_mask(W, H, cx, cy, 7.5)
    frames.append(layered(W, H, [(m_mid & ~hole, P.SPARK_ORA), (m_mid & ~hole & (r < 13), P.SPARK_YEL),
                                 (ring, P.SPARK_YEL), (ring_in, P.WHITE)]))
    # 3: anello più largo e raggi corti
    ring = ring_mask(W, H, cx, cy, 27.5, 25.5)
    streaks = np.zeros((H, W), bool)
    for k in range(10):
        a = 2 * math.pi * k / 10 + 0.15
        draw_line(streaks, cx + 13 * math.cos(a), cy + 13 * math.sin(a), cx + 20 * math.cos(a), cy + 20 * math.sin(a))
    frames.append(layered(W, H, [(ring, P.SPARK_ORA), (ring & (r < 26.5), P.SPARK_YEL), (streaks, P.SPARK_PALE)]))
    # 4: anello sottile che si sfalda, scintille
    ring = ring_mask(W, H, cx, cy, 30.5, 29.3)
    sp = np.zeros((H, W), bool)
    for k in range(14):
        a = 2 * math.pi * k / 14 + 0.3 * (k % 2)
        rr = 21 + (k % 3) * 2
        sp[int(cy + rr * math.sin(a)), int(cx + rr * math.cos(a))] = True
    frames.append(layered(W, H, [(pix.dissolve(ring, 0.6), P.SPARK_RED), (sp, P.SPARK_YEL)]))
    # 5: ultime scintille
    sp = np.zeros((H, W), bool)
    for k in range(10):
        a = 2 * math.pi * k / 10 + 0.5
        rr = 25 + (k % 3) * 2
        sp[int(cy + rr * math.sin(a)), int(cx + rr * math.cos(a))] = True
    frames.append(layered(W, H, [(sp, P.SPARK_ORA)]))
    return frames, (W, H), (32, 32), 3


# ------------------------------------------------------------------------------------
# principale
# ------------------------------------------------------------------------------------

EFFECTS = {
    "hit_spark_light": (hit_spark_light, {
        "loop": False, "mode": "anim",
        "note": "Colpo leggero (jab, ginocchiata): stella bianca, gialla e arancio. Simmetrica."}),
    "hit_spark_heavy": (hit_spark_heavy, {
        "loop": False, "mode": "anim",
        "note": "Colpo pesante (calcio finale, proiezione, haymaker): stella grande con anello d'urto."}),
    "dust_land": (dust_land, {
        "loop": False, "mode": "anim",
        "note": "Atterraggio e corpo che cade: due nuvole che si allargano ai lati. Ancora = punto a terra."}),
    "dust_skid": (dust_skid, {
        "loop": False, "mode": "anim", "flip": True,
        "note": ("Sbuffo dai piedi (frenata, spinta all'indietro). Disegnato per chi guarda a destra: "
                 "il pennacchio va verso -x. Specchiare per chi guarda a sinistra.")}),
    "glint": (glint, {
        "loop": False, "mode": "anim",
        "note": "Lampo a stella che annuncia l'haymaker del punk: 6 x 2 = 12 tick, dal tick 20 dell'avvio."}),
    "cyber_spark": (cyber_spark, {
        "loop": False, "mode": "anim", "flip": True,
        "note": ("Scarica cyan del gancio cyber. Gli archi vanno un po' più verso +x: specchiare "
                 "se il colpo va verso sinistra.")}),
    "ombra": (ombra, {
        "loop": False, "mode": "variants",
        "variants": ["grande", "media", "piccola"],
        "note": ("Non è un'animazione: fotogramma 0 = ombra grande (46x10, riempie il fotogramma: bruto, "
                 "corpi a terra; è anche quella da stirare se si vuole una larghezza qualsiasi), "
                 "1 = media (36x8: GIG e punk), 2 = piccola (24x6: oggetti, personaggi in alto nel "
                 "salto). Ellisse semitrasparente centrata sull'ancora, da disegnare in (x, y) prima "
                 "dello sprite; a 1x resta perfetta al pixel.")}),
    "rain_streak": (rain_streak, {
        "loop": False, "mode": "variants",
        "note": ("Quattro gocce di lunghezza diversa (7, 10, 13, 16 px), semitrasparenti. Non è "
                 "un'animazione: ogni goccia sceglie un fotogramma e si muove scendendo di 4 px per "
                 "ogni px verso sinistra (pendenza 0,25); l'ancora è la testa (il punto più basso).")}),
    "rain_sheet": (rain_sheet, {
        "loop": False, "mode": "variants", "tile": True,
        "note": ("Facoltativo: tessera di pioggia 128x128 ripetibile, da far scorrere (per esempio "
                 "6 px in basso e 1,5 px a sinistra per tick) al posto delle gocce singole.")}),
    "rain_splash": (rain_splash, {
        "loop": False, "mode": "anim",
        "note": "Schizzo a terra di una goccia. Ancora = punto d'impatto sul suolo."}),
    "ko_flash": (ko_flash, {
        "loop": False, "mode": "anim",
        "note": ("Facoltativo: lampo del KO finale dell'ondata (durante il congelamento di 26 tick). "
                 "6 x 3 = 18 tick.")}),
}


def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    fx = {}
    for name, (fn, extra) in EFFECTS.items():
        frames, (w, h), anchor, ticks = fn()
        for f in frames:
            assert f.shape[:2] == (h, w), (name, f.shape)
        pix.save(pix.strip(frames), OUT / f"{name}.png")
        d = {"image": f"{name}.png", "frame": [w, h], "count": len(frames), "ticks": ticks,
             "anchor": [int(anchor[0]), int(anchor[1])]}
        d.update(extra)
        fx[name] = d
    (OUT / "fx.json").write_text(json.dumps(fx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return fx


if __name__ == "__main__":
    fx = build()
    for k, v in fx.items():
        print(f"{k:16s} frame {v['frame']} x{v['count']} ticks {v['ticks']} anchor {v['anchor']}")
