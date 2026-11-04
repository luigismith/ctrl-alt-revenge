# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Utility comuni per la pixel art generata da script.

Le immagini sono array numpy uint8 di forma (h, w, 4), RGBA con alfa non premoltiplicato.
Tutto è deterministico: niente casualità senza seme, niente antialiasing.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

Color = tuple[int, int, int, int]


def hexc(s: str, a: int = 255) -> Color:
    """'#rrggbb' -> (r, g, b, a)."""
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def with_alpha(c: Color, a: int) -> Color:
    return (c[0], c[1], c[2], a)


def new(w: int, h: int, color: Color = (0, 0, 0, 0)) -> np.ndarray:
    img = np.zeros((h, w, 4), np.uint8)
    img[:, :] = color
    return img


def paint(img: np.ndarray, mask: np.ndarray, color: Color) -> None:
    """Colora (sostituendo) i pixel della maschera."""
    img[mask] = color


def over(dst: np.ndarray, src: np.ndarray, x: int = 0, y: int = 0) -> None:
    """Compone src sopra dst in (x, y) con l'operatore 'over' (alfa dritto), con ritaglio."""
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float64) / 255.0
    d = dst[y0:y1, x0:x1].astype(np.float64) / 255.0
    sa, da = s[..., 3:4], d[..., 3:4]
    oa = sa + da * (1.0 - sa)
    rgb = np.where(oa > 0, (s[..., :3] * sa + d[..., :3] * da * (1.0 - sa)) / np.maximum(oa, 1e-9), 0.0)
    out = np.concatenate([rgb, oa], axis=-1)
    dst[y0:y1, x0:x1] = np.clip(np.rint(out * 255.0), 0, 255).astype(np.uint8)


def poly_mask(w: int, h: int, polys, ox: float = 0.0, oy: float = 0.0,
              combined: bool = False) -> np.ndarray:
    """Rasterizza poligoni (liste di (x, y)) campionando il centro dei pixel, regola nonzero.

    Senza antialiasing: un pixel è pieno se il suo centro sta dentro i poligoni.
    Normalmente è l'unione dei poligoni presi uno per uno (il verso non conta); con
    combined=True il numero di avvolgimento si somma su tutti i contorni, come nei font,
    così i contorni in verso opposto fanno da buchi. (ox, oy) sposta tutti i poligoni.
    """
    ys, xs = np.mgrid[0:h, 0:w]
    px = xs + 0.5 - ox
    py = ys + 0.5 - oy
    out = np.zeros((h, w), bool)
    wn = np.zeros((h, w), np.int32)
    for poly in polys:
        if not combined:
            wn = np.zeros((h, w), np.int32)
        n = len(poly)
        for i in range(n):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % n]
            if y0 == y1:
                continue
            # attraversamento del semiasse orizzontale verso +x
            up = (y0 <= py) & (py < y1)
            down = (y1 <= py) & (py < y0)
            t = (py - y0) / (y1 - y0)
            xi = x0 + t * (x1 - x0)
            hit = px < xi
            wn += np.where(up & hit, 1, 0)
            wn -= np.where(down & hit, 1, 0)
        if not combined:
            out |= wn != 0
    if combined:
        out = wn != 0
    return out


def rect_poly(x0: float, y0: float, x1: float, y1: float):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def ellipse_mask(w: int, h: int, cx: float, cy: float, rx: float, ry: float) -> np.ndarray:
    """Ellisse piena campionata sui centri dei pixel."""
    ys, xs = np.mgrid[0:h, 0:w]
    if rx <= 0 or ry <= 0:
        return np.zeros((h, w), bool)
    return ((xs + 0.5 - cx) / rx) ** 2 + ((ys + 0.5 - cy) / ry) ** 2 <= 1.0


def disc_mask(w: int, h: int, cx: float, cy: float, r: float) -> np.ndarray:
    return ellipse_mask(w, h, cx, cy, r, r)


CROSS = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
SQUARE = np.ones((3, 3), bool)


def dilate(mask: np.ndarray, r: int = 1, square: bool = True) -> np.ndarray:
    """Dilatazione di r pixel (quadrata = 8-connessa, altrimenti a croce = 4-connessa)."""
    if r <= 0:
        return mask.copy()
    st = SQUARE if square else CROSS
    return ndimage.binary_dilation(mask, structure=st, iterations=r)


def shift(mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
    """Sposta una maschera di (dx, dy) riempiendo con False."""
    h, w = mask.shape
    out = np.zeros_like(mask)
    xs0, xs1 = max(0, -dx), min(w, w - dx)
    ys0, ys1 = max(0, -dy), min(h, h - dy)
    if xs1 > xs0 and ys1 > ys0:
        out[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx] = mask[ys0:ys1, xs0:xs1]
    return out


BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float64) / 16.0


def bayer(w: int, h: int, ox: int = 0, oy: int = 0) -> np.ndarray:
    """Soglie di Bayer 4x4 in [0, 1) per retinature ordinate."""
    ys, xs = np.mgrid[0:h, 0:w]
    return BAYER4[(ys + oy) % 4, (xs + ox) % 4]


def dissolve(mask: np.ndarray, keep: float, ox: int = 0, oy: int = 0) -> np.ndarray:
    """Tiene circa la frazione 'keep' dei pixel con una retinatura ordinata (stile 16 bit)."""
    h, w = mask.shape
    return mask & (bayer(w, h, ox, oy) < keep)


def upscale(img: np.ndarray, k: int) -> np.ndarray:
    return np.repeat(np.repeat(img, k, axis=0), k, axis=1)


def save(img: np.ndarray, path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGBA").save(path, optimize=True)


def load(path: Path | str) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA")).copy()


def strip(frames: list[np.ndarray]) -> np.ndarray:
    """Affianca i fotogrammi (tutti della stessa misura) in una striscia orizzontale."""
    return np.concatenate(frames, axis=1)


def bbox(mask: np.ndarray):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def crop_alpha(img: np.ndarray, pad: int = 0) -> tuple[np.ndarray, tuple[int, int]]:
    """Ritaglia ai pixel non trasparenti (più un margine). Restituisce anche l'origine del ritaglio."""
    b = bbox(img[..., 3] > 0)
    if b is None:
        return img[:1, :1].copy(), (0, 0)
    x0, y0, x1, y1 = b
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(img.shape[1], x1 + pad), min(img.shape[0], y1 + pad)
    return img[y0:y1, x0:x1].copy(), (x0, y0)
