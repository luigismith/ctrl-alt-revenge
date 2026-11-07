# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - il cavo di «Sotto la Linea»: il rivolo dal pluviale, elettrificato (scelta di Luigi,
7 novembre 2026). Prende il posto della pozzanghera di tools/env/props.py.

  python -I tools/ambienti/cavo_rivolo.py [--uscita DIR]

Scrive cable.png e cable.json (formato sprite della specifica §4) in tools/out/ambienti/sotto_la_linea/.
È tutto procedurale, senza basi AI: è un oggetto animato.

La scena, in coordinate del mondo:
  - il pluviale di P3 (x 1645-1658) è spaccato sotto la fascetta, a y 153: il moncone e il muro bagnato
    sono nel backdrop (componi_slice.py, pluviale()), l'acqua che cade e il pezzo per terra sono qui;
  - l'acqua scende in diagonale verso sinistra, si allarga in una pozza sul marciapiede, scavalca il
    cordolo (y 217-222) e finisce nella caditoia (x 1556-1572), allargandosi sulla strada fino a y 263.
    Fra x 1538 e 1588, la zona del danno di prop_cable.gd, è bagnata tutta la fascia (188-260);
  - il cavo strappato scende da sotto la Linea (sparisce dietro la fg), passa a destra della scritta
    MALEDICONO, tocca terra e finisce con il capo spellato nell'acqua, vicino alla caditoia;
  - nei fotogrammi 0 e 3 (quelli che level.gd usa per il lampo della luce «cable») l'arco: bianco con
    l'alone viola, e l'acqua che si accende. Le scintille arancio ricadono nei due fotogrammi dopo.
    Il ciano no: è di GIG;
  - l'acqua riflette il muro in alto e la polvere rossa del cielo in basso, con i riflessi rossi della
    scritta che tremano; il cavo ondeggia appena, per il vento del Wind Day.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools/out/ambienti/sotto_la_linea"
X0, X1, Y0, Y1 = 1494, 1666, 18, 268          # il fotogramma, nel mondo
W, H = X1 - X0, Y1 - Y0
AX, AY = 1563, 188                            # l'ancora (prop_cable.gd: px al centro, py = band_top)
NF = 6
FLASH = (0, 3)
HIT = [[-28, -8, 56, 8]]
YY, XX = np.mgrid[Y0:Y1, X0:X1]

CORE, HALO, HALO2 = (255, 255, 255), (190, 140, 255), (118, 74, 200)
SPARK, SPARK2 = (255, 214, 120), (255, 128, 40)
CABLE, CABLE_HI, COPPER = (14, 12, 18), (78, 70, 104), (220, 136, 72)
RIM = (82, 72, 116)
# l'acqua: in alto riflette il muro, in basso la polvere rossa del cielo (le righe vicine riflettono più in alto)
TONI = [(40, 32, 58), (26, 20, 40), (21, 15, 32), (38, 18, 34)]


def L(x, y):
    """Dal mondo al fotogramma."""
    return int(round(x - X0)), int(round(y - Y0))


def put(img, x, y, col, a=255):
    if 0 <= x < W and 0 <= y < H:
        img[y, x, :3] = col
        img[y, x, 3] = a


def blob(cx, cy, rx, ry, seed, amp=0.1):
    a = np.arctan2((YY - cy) / ry, (XX - cx) / rx)
    r = np.hypot((XX - cx) / rx, (YY - cy) / ry)
    rnd = np.random.default_rng(seed)
    edge = 1.0 + sum(amp / k * 2 * np.sin(k * a + rnd.uniform(0, 6.3)) for k in (2, 3, 5, 9))
    return r < edge


def trap(ya, yb, xa0, xa1, xb0, xb1):
    """Un trapezio fra le righe ya e yb: l'acqua che si stringe verso il cordolo."""
    t = (YY - ya) / max(1, yb - ya)
    return (YY >= ya) & (YY <= yb) & (XX >= xa0 + (xb0 - xa0) * t) & (XX <= xa1 + (xb1 - xa1) * t)


def shapes():
    pool = (blob(1563, 199, 45, 15, 11) | trap(205, 216, 1532, 1594, 1541, 1590)) & (YY >= 184) & (YY <= 216)
    road = (blob(1566, 243, 47, 20, 12) | trap(223, 232, 1541, 1590, 1534, 1597)) & (YY >= 223)
    d = np.array([1600 - 1651, 197 - 181.0])
    t = np.clip(((XX - 1651) * d[0] + (YY - 181) * d[1]) / (d @ d), 0, 1)
    dist = np.hypot(XX - (1651 + t * d[0]), YY - (181 + t * d[1]))
    stream = (dist < 1.5 + 2.2 * t) & (YY >= 180)
    return pool, road, stream, t


def tono(mask, img, f):
    """Riempie una pozza: le fasce di colore, il bordo chiaro dietro e i riflessi rossi che tremano."""
    rows = np.where(mask.any(1))[0]
    top, bot = rows.min(), rows.max()
    v = (YY - Y0 - top) / max(1, bot - top)
    band = np.clip((v * 4 + ((XX + YY) % 2) * 0.35).astype(int), 0, 3)
    col = np.array(TONI, np.uint8)[band]
    img[mask, :3] = col[mask]
    img[mask, 3] = 255
    for y in range(top, bot + 1, 3):                                    # i riflessi della scritta rossa
        yw = y + Y0
        if (yw * 7) % 5 == 0:
            continue
        sh = int(round(math.sin(yw * 0.9 + f * 1.05) * 1.5))
        for k in range(3):
            x = 1532 + ((yw * 37 + k * 23) % 56) + sh
            for xw in range(x, x + 3 + (yw + k * 5) % 6):
                lx, _ = L(xw, 0)
                if 0 <= lx < W and mask[y, lx]:
                    img[y, lx, :3] = (96, 34, 44) if v[y, lx] > 0.4 else (74, 56, 92)
    up = mask & ~np.roll(mask, 1, 0)                                    # il bordo lontano prende la luce
    brk = ((XX // 5 + f // 3) % 4) != 0
    img[up & brk, :3] = RIM


def cable_points(f):
    """Il cavo: scende da sotto la Linea, tocca terra sul marciapiede, scavalca il cordolo e finisce
    con il capo spellato nell'acqua. Il vento lo fa ondeggiare di un pixel."""
    sway = math.sin(f / NF * 2 * math.pi) * 1.3
    p0, c, p1 = (1628, 18), (1606, 160), (1594, 207)
    pts = []
    for u in np.linspace(0, 1, 240):
        x = (1 - u) ** 2 * p0[0] + 2 * u * (1 - u) * c[0] + u * u * p1[0] + sway * math.sin(u * math.pi) ** 2
        y = (1 - u) ** 2 * p0[1] + 2 * u * (1 - u) * c[1] + u * u * p1[1]
        pts.append((x, y, False))
    for a, b in (((1594, 207), (1580, 214)), ((1580, 214), (1574, 222)), ((1574, 222), (1568, 231))):
        for u in np.linspace(0, 1, 16):
            pts.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, True))
    return pts, (1567, 232)


def bolt(img, p, q, rnd, depth=0):
    """Un arco a zig-zag da p a q: l'anima bianca di un pixel, l'alone viola intorno."""
    pts = [np.array(p, float), np.array(q, float)]
    for _ in range(4):
        new = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            n = np.array([a[1] - b[1], b[0] - a[0]])
            new += [(a + b) / 2 + n * rnd.uniform(-0.3, 0.3), b]
        pts = new
    path = []
    for a, b in zip(pts, pts[1:]):
        for s in np.linspace(0, 1, int(max(abs(b - a))) + 2):
            path.append(L(*(a + (b - a) * s)))
    for x, y in path:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            put(img, x + dx, y + dy, HALO)
    for x, y in path:
        put(img, x, y, CORE)
    if depth == 0:
        k = int(rnd.integers(4, len(pts) - 4))
        bolt(img, pts[k], pts[k] + rnd.uniform(-8, 8, 2) + (0, 3), rnd, 1)


def frame(f, pool, road, stream, t, rnd):
    img = np.zeros((H, W, 4), np.uint8)
    flash = f in FLASH
    after = (f - 1) in FLASH
    wet = pool | road | stream
    tono(pool, img, f)
    tono(road, img, f)
    # il rivolo: più chiaro, con i trattini che scendono verso la pozza
    sc = stream & ~pool
    img[sc, :3] = (46, 40, 70)
    img[sc & ~np.roll(sc, 1, 0), :3] = RIM
    img[sc, 3] = 255
    flow = stream & (((t * 40 - f * 1.5).astype(int) % 5) == 0) & ((XX + YY) % 2 == 0)
    img[flow, :3] = (132, 124, 176)
    for k in range(3):                                                  # la corrente nella pozza, verso il cordolo
        s = (f * 4 + k * 13) % 40
        for dx in range(3):
            lx, ly = L(1592 - s + dx, 196 + k * 5 + s // 8)
            if 0 <= lx < W and 0 <= ly < H and pool[ly, lx]:
                put(img, lx, ly, (104, 96, 146))
    # la cascatella sul cordolo, con la schiuma nel canale
    for x in range(1543, 1590):
        for y in range(217, 222):
            on = (x * 3 + y * 2 - f * 2) % 7 < 2
            put(img, *L(x, y), (124, 116, 168) if on else (34, 30, 54))
        if (x * 5 + f) % 4:
            put(img, *L(x, 222), (176, 172, 204))
    for x in range(1556, 1573):                                         # la caditoia
        for y in range(224, 229):
            bar = (x - 1556) % 3 == 0 or y in (224, 228)
            put(img, *L(x, y), (70, 66, 84) if bar else (6, 4, 12))
    # l'acqua che cade dal pluviale rotto (il moncone è nel backdrop, a y 153)
    for y in range(155, 181):
        for x in (1649, 1650, 1651):
            if x == 1650:
                put(img, *L(x, y), (168, 162, 202), a=235)
            elif ((y + f * 3 + x) // 2) % 3:
                put(img, *L(x, y), (96, 90, 136), a=220)
    for _ in range(6):                                                  # gli schizzi
        ang = rnd.uniform(math.pi * 1.05, math.pi * 1.95)
        r = rnd.uniform(2, 6)
        put(img, *L(1650 + math.cos(ang) * r, 180 + math.sin(ang) * r * 0.5), (184, 180, 212))
    # il pezzo di pluviale caduto sul marciapiede, a destra della pozza
    for x in range(1612, 1631):
        put(img, *L(x, 191), (150, 92, 72))
        put(img, *L(x, 192), (118, 66, 54))
        put(img, *L(x, 193), (70, 40, 40))
    for y in range(190, 195):
        put(img, *L(1611, y), (34, 22, 26))
    put(img, *L(1631, 191), (200, 120, 70))
    # il cavo, due pixel, con il filo di luce a sinistra (sopra, dove sta per terra)
    pts, end = cable_points(f)
    for i, (x, y, ground) in enumerate(pts):
        lx, ly = L(x, y)
        if ground and 0 <= ly < H and 0 <= lx < W and wet[ly, lx] and i % 4 == 0:
            continue                                                    # a tratti sott'acqua
        put(img, lx, ly, CABLE)
        put(img, lx + 1, ly, CABLE)
        if not ground and i % 9:
            put(img, lx - 1, ly, CABLE_HI)
        elif ground and i % 3:
            put(img, lx, ly - 1, CABLE_HI)
    ex, ey = L(*end)
    for dx, dy in ((-1, 1), (-2, 1), (-3, 2), (-2, 2), (-4, 3), (-1, 2)):  # i fili di rame
        put(img, ex + dx, ey + dy, COPPER)
    # l'acqua che si accende: piena nel lampo, un riverbero nel fotogramma dopo
    if flash or after:
        d = np.hypot((XX - end[0]) * 0.7, (YY - end[1]) * 1.5) + ((XX + YY) % 2) * 3
        lv = [(8, (236, 228, 255)), (16, (164, 136, 236)), (28, (92, 70, 158))] if flash else \
             [(7, (120, 92, 196)), (14, (64, 48, 112))]
        for r, col in reversed(lv):
            img[wet & (d < r), :3] = col
        if flash:
            hi = wet & (d < 24) & (((YY + f) % 3) == 0) & (((XX * 3 + YY) % 11) < 4)
            img[hi, :3] = (250, 246, 255)
    if flash:
        targets = [(1541, 240), (1590, 229), (1558, 255), (1552, 205)] if f == 0 else \
                  [(1546, 226), (1586, 249), (1574, 208), (1563, 258)]
        for q in targets:
            bolt(img, (end[0] - 2, end[1] + 1), q, rnd)
        for _ in range(5):                                              # le scintille alla partenza
            put(img, ex + int(rnd.integers(-4, 5)), ey - int(rnd.integers(1, 5)), SPARK)
    else:
        put(img, ex - 2, ey + 2, (255, 150, 70))                        # la brace sul capo
        for _ in range(3):                                              # i guizzi viola sull'acqua
            x, y = ex + int(rnd.integers(-9, 10)), ey + int(rnd.integers(-1, 5))
            if 0 <= y < H and 0 <= x < W and wet[y, x]:
                put(img, x, y, HALO2)
                put(img, x + 1, y, HALO)
    # le scintille arancio ricadono nei due fotogrammi dopo il lampo
    for start in FLASH:
        age = (f - start) % NF
        if not 1 <= age <= 2:
            continue
        sr = np.random.default_rng(100 + start)
        for _ in range(11):
            vx, vy = sr.uniform(-2.6, 2.6), sr.uniform(-4.4, -1.8)
            tt = age * 2.6
            x, y = end[0] + vx * tt, end[1] + vy * tt + 0.42 * tt * tt
            if y > end[1] + 4:
                continue
            put(img, *L(x, y), SPARK)
            put(img, *L(x - vx * 0.6, y - (vy + 0.84 * tt) * 0.6), SPARK2)
    return img


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--uscita", default=str(OUT))
    out = Path(ap.parse_args().uscita)
    out.mkdir(parents=True, exist_ok=True)
    pool, road, stream, t = shapes()
    zona = (pool | road | ((YY >= 217) & (YY <= 222)))[188 - Y0:261 - Y0, 1538 - X0:1589 - X0]
    print(f"zona del danno bagnata: {zona.mean():.0%}")
    rnd = np.random.default_rng(7)
    frames = [frame(f, pool, road, stream, t, rnd) for f in range(NF)]
    sheet = np.zeros((H + 2, (W + 1) * NF + 1, 4), np.uint8)
    fr = []
    for k, im in enumerate(frames):
        x = 1 + k * (W + 1)
        sheet[1:1 + H, x:x + W] = im
        fr.append(dict(rect=[x, 1, W, H], anchor=[AX - X0, AY - Y0], ticks=3 if k in FLASH else 4, hurt=[],
                       hit=HIT, events=["sfx:zap"] if k == 0 else [], tags=["active"], dx=0))
    Image.fromarray(sheet, "RGBA").save(out / "cable.png")
    meta = {"id": "cable", "format": 1, "image": "cable.png", "pixels_per_meter": 60,
            "animations": {"idle": dict(loop=True, frames=fr)}}
    (out / "cable.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("cable:", sheet.shape[1], "x", sheet.shape[0], "- ancora", AX - X0, AY - Y0)


if __name__ == "__main__":
    main()
