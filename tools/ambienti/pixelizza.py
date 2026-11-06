# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Dalle basi dipinte (generate con l'AI) alla pixel art del gioco.

Le basi arrivano grandi, con le sfumature e il rumore del JPEG. Qui diventano pixel art alla
scala del gioco (60 px per metro, schermo 480x270) in quattro passi:

1. riduzione per media d'area alla misura finale, dopo una mediana leggera che toglie il rumore;
2. palette: k-means nello spazio OKLab, con un numero di colori deciso per piano (i piani
   lontani ne hanno pochi, gli oggetti di scena di più); nessuna retinatura, come gli sfondi
   dello slice;
3. pulizia: un pixel isolato prende il colore che lo circonda (filtro di maggioranza);
4. per gli oggetti di scena: trasparenza dal fondo magenta e, se serve, il contorno di 1 px
   (`#140e1e`, lo stesso dei personaggi).

Uso da riga di comando, per provare:

    python -I tools/ambienti/pixelizza.py base.jpg uscita.png --size 792x336 --colori 28

Il codice è MIT, come il resto del gioco. Le basi AI non stanno nel repo: vedi il README.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

OUTLINE = (0x14, 0x0E, 0x1E)


# --- Colore: sRGB <-> OKLab -------------------------------------------------------------------

def _srgb_to_lin(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lin_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]])
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]])


def to_oklab(rgb01: np.ndarray) -> np.ndarray:
    lms = _srgb_to_lin(rgb01) @ _M1.T
    return np.cbrt(lms) @ _M2.T


def from_oklab(lab: np.ndarray) -> np.ndarray:
    lms = lab @ np.linalg.inv(_M2).T
    return _lin_to_srgb((lms ** 3) @ np.linalg.inv(_M1).T)


# --- Palette ----------------------------------------------------------------------------------

def kmeans_palette(lab: np.ndarray, k: int, seed: int = 1, iters: int = 24,
                   weights: np.ndarray | None = None) -> np.ndarray:
    """Palette di `k` colori (in OKLab) dai pixel `lab` (N x 3), con k-means++ deterministico.
    `weights` (N) pesa i pixel: per esempio 0 per i trasparenti."""
    rng = np.random.default_rng(seed)
    pts = lab
    w = np.ones(len(pts)) if weights is None else weights.astype(np.float64)
    keep = w > 0
    pts, w = pts[keep], w[keep]
    if len(pts) > 60000:
        idx = rng.choice(len(pts), 60000, replace=False, p=w / w.sum())
        pts, w = pts[idx], np.ones(60000)
    k = min(k, len(pts))
    centers = [pts[rng.choice(len(pts), p=w / w.sum())]]
    d2 = np.sum((pts - centers[0]) ** 2, axis=1)
    for _ in range(1, k):
        p = d2 * w
        centers.append(pts[rng.choice(len(pts), p=p / p.sum())] if p.sum() > 0 else pts[rng.integers(len(pts))])
        d2 = np.minimum(d2, np.sum((pts - centers[-1]) ** 2, axis=1))
    c = np.array(centers)
    for _ in range(iters):
        lab_idx = np.argmin(((pts[:, None, :] - c[None, :, :]) ** 2).sum(-1), axis=1)
        for j in range(k):
            m = lab_idx == j
            if m.any():
                c[j] = np.average(pts[m], axis=0, weights=w[m])
    return c


def map_to_palette(lab: np.ndarray, pal: np.ndarray) -> np.ndarray:
    """Indice del colore più vicino (in OKLab) per ogni pixel; `lab` è H x W x 3."""
    flat = lab.reshape(-1, 3)
    out = np.empty(len(flat), np.int32)
    for s in range(0, len(flat), 200000):
        blk = flat[s:s + 200000]
        out[s:s + 200000] = np.argmin(((blk[:, None, :] - pal[None, :, :]) ** 2).sum(-1), axis=1)
    return out.reshape(lab.shape[:2])


# --- Pulizia ----------------------------------------------------------------------------------

def majority_clean(idx: np.ndarray, alpha: np.ndarray | None = None, passes: int = 1) -> np.ndarray:
    """Un pixel diverso da tutti gli 8 vicini prende il colore più frequente fra loro."""
    idx = idx.copy()
    h, w = idx.shape
    for _ in range(passes):
        pad = np.pad(idx, 1, mode="edge")
        nb = np.stack([pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
                       for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx])
        same = (nb == idx[None]).sum(0)
        lonely = same == 0
        if alpha is not None:
            lonely &= alpha > 0
        if not lonely.any():
            break
        ys, xs = np.nonzero(lonely)
        for y, x in zip(ys, xs):
            vals, counts = np.unique(nb[:, y, x], return_counts=True)
            idx[y, x] = vals[np.argmax(counts)]
    return idx


# --- Trasparenza e contorno -------------------------------------------------------------------

def magentaness(rgb01: np.ndarray) -> np.ndarray:
    """Quanto un colore tira al magenta del fondo: rosso e blu insieme sopra il verde (0-1)."""
    return np.clip(np.minimum(rgb01[..., 0], rgb01[..., 2]) - rgb01[..., 1], 0.0, 1.0)


def magenta_alpha(rgb01: np.ndarray, tol: float = 0.18) -> np.ndarray:
    """Alfa (0/1) da un fondo magenta: trasparente quello che è vicino a #ff00ff in OKLab, e
    anche i bordi sfumati che ne hanno preso molto (il magenta "sporco" dei JPEG)."""
    lab = to_oklab(rgb01)
    key = to_oklab(np.array([1.0, 0.0, 1.0]))
    d = np.sqrt(((lab - key) ** 2).sum(-1))
    return ((d > tol) & (magentaness(rgb01) < 0.42)).astype(np.uint8)


def despill(rgb01: np.ndarray, alpha: np.ndarray, reach: int = 2) -> np.ndarray:
    """Toglie la tinta magenta rimasta sui bordi: entro `reach` px dal trasparente, rosso e blu
    scendono di quanto superano il verde. Fuori dall'immagine conta come trasparente: un pezzo
    tagliato sul bordo di un oggetto (una striscia di viale, una cornice) ha il magenta proprio lì."""
    h, w = alpha.shape
    hole = np.pad(alpha == 0, reach, constant_values=True)
    near = np.zeros((h, w), bool)
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            near |= hole[reach + dy:reach + dy + h, reach + dx:reach + dx + w]
    out = rgb01.copy()
    m = magentaness(rgb01)
    fix = near & (alpha > 0) & (m > 0.04)
    for ch in (0, 2):
        out[..., ch] = np.where(fix, rgb01[..., ch] - (m - 0.02), rgb01[..., ch])
    return out.clip(0.0, 1.0)


def add_outline(rgba: np.ndarray, color=OUTLINE) -> np.ndarray:
    """Contorno di 1 px fuori dalla sagoma (4-vicini), come gli sprite dei personaggi."""
    a = rgba[..., 3] > 0
    pad = np.pad(a, 1)
    ring = (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]) & ~a
    out = rgba.copy()
    out[ring] = (*color, 255)
    return out


# --- Il passaggio intero ----------------------------------------------------------------------

def pixelize(img: Image.Image, size: tuple[int, int], colors: int, *, key_magenta: bool = False,
             outline: bool = False, seed: int = 1, clean_passes: int = 1,
             palette: np.ndarray | None = None, denoise: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Restituisce l'immagine RGBA (H x W x 4, uint8) e la palette usata (in OKLab)."""
    src = img.convert("RGB")
    if denoise:
        src = src.filter(ImageFilter.MedianFilter(denoise))
    rgb_hi = np.asarray(src, np.float64) / 255.0
    alpha = None
    if key_magenta:
        a_hi = magenta_alpha(rgb_hi)
        a_img = Image.fromarray((a_hi * 255).astype(np.uint8)).resize(size, Image.BOX)
        alpha = (np.asarray(a_img) >= 128).astype(np.uint8)
        # Il colore dei bordi non deve sporcarsi del magenta: si riduce pesando con l'alfa.
        prem = rgb_hi * a_hi[..., None]
        pr = np.asarray(Image.fromarray((prem * 255).astype(np.uint8)).resize(size, Image.BOX), np.float64)
        ah = np.asarray(a_img, np.float64)[..., None] / 255.0
        rgb = np.where(ah > 0, pr / 255.0 / np.maximum(ah, 1e-3), 0.0).clip(0, 1)
        rgb = despill(rgb, alpha)
    else:
        rgb = np.asarray(src.resize(size, Image.BOX), np.float64) / 255.0
    lab = to_oklab(rgb)
    if palette is None:
        wts = None if alpha is None else alpha.reshape(-1).astype(np.float64)
        palette = kmeans_palette(lab.reshape(-1, 3), colors, seed=seed, weights=wts)
    idx = map_to_palette(lab, palette)
    if clean_passes:
        idx = majority_clean(idx, alpha, clean_passes)
    pal_rgb = (from_oklab(palette) * 255 + 0.5).clip(0, 255).astype(np.uint8)
    out = np.zeros((*idx.shape, 4), np.uint8)
    out[..., :3] = pal_rgb[idx]
    out[..., 3] = 255 if alpha is None else alpha * 255
    if outline:
        out = add_outline(out)
    return out, palette


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--size", required=True, help="LxA, per esempio 792x336")
    ap.add_argument("--colori", type=int, default=28)
    ap.add_argument("--magenta", action="store_true", help="fondo magenta trasparente")
    ap.add_argument("--contorno", action="store_true")
    ap.add_argument("--anteprima", type=int, default=0, help="salva anche una copia ingrandita xN")
    a = ap.parse_args()
    w, h = (int(v) for v in a.size.lower().split("x"))
    out, _ = pixelize(Image.open(a.src), (w, h), a.colori, key_magenta=a.magenta, outline=a.contorno)
    im = Image.fromarray(out, "RGBA")
    im.save(a.dst)
    if a.anteprima:
        p = Path(a.dst)
        im.resize((w * a.anteprima, h * a.anteprima), Image.NEAREST).save(p.with_name(p.stem + f"_x{a.anteprima}.png"))


if __name__ == "__main__":
    main()
