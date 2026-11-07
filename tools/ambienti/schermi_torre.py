# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Gli schermi della torre di SIDERA nel cielo del prologo (e nel murale MP06 che lo ripete): due maxischermi
del 2087, uno con la pubblicità di ARIA+ (bianco e menta, mai cyan: decisione 7) e uno con il nome di SIDERA.

  python -I tools/ambienti/schermi_torre.py game/assets/env/prologo/cielo.png [altri png...]

Trova da solo i due rettangoli chiari degli schermi (bianco caldo, li lascia così componi_prologo.py) e ci
disegna sopra il contenuto con pixfont. Lo usano anche componi_prologo.py (build_far) e murale.py ("schermi").
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "env"))
import pixfont as PF  # noqa: E402

CORNICE = (0x26, 0x08, 0x1A)
ARIA_FONDO, ARIA_TESTO, MENTA = (0xF4, 0xF1, 0xE6), (0x3A, 0x1C, 0x34), (0x6C, 0xD8, 0x9A)
SIDERA_FONDO, SIDERA_TESTO, SIDERA_RIGA = (0x2E, 0x14, 0x2C), (0xF6, 0xE8, 0xD0), (0xE0, 0x46, 0x3C)


def trova(img: np.ndarray, min_w: int = 18, min_h: int = 14, y_max: int | None = None) -> list[tuple[int, int, int, int]]:
    """I rettangoli chiari abbastanza grandi (x, y, w, h), da sinistra a destra."""
    rgb = img[..., :3].astype(int)
    chiaro = (rgb.sum(axis=2) > 600) & ((img[..., 3] > 0) if img.shape[2] == 4 else True)
    if y_max is not None:
        chiaro[y_max:] = False
    lbl, _ = ndimage.label(chiaro)
    boxes = []
    for s in ndimage.find_objects(lbl):
        h, w = s[0].stop - s[0].start, s[1].stop - s[1].start
        if w >= min_w and h >= min_h and w < 3 * h:
            boxes.append((s[1].start, s[0].start, w, h))
    return sorted(boxes)


def _testo(img: np.ndarray, t: str, cx: int, y: int, col, font=PF.FONT3x5) -> int:
    m = PF.render(t, font, 1, 1)
    h, w = m.shape
    x = cx - w // 2
    ys, xs = np.nonzero(m)
    img[ys + y, xs + x, :3] = col
    return x + w


def disegna(img: np.ndarray, boxes: list[tuple[int, int, int, int]], emis: np.ndarray | None = None) -> None:
    """Il primo schermo (a sinistra) è ARIA+, il secondo SIDERA. Se c'è emis, ci mette la loro luce."""
    for i, (x, y, w, h) in enumerate(boxes[:2]):
        aria = i == 0
        fondo = ARIA_FONDO if aria else SIDERA_FONDO
        img[y:y + h, x:x + w, :3] = CORNICE
        img[y + 1:y + h - 1, x + 1:x + w - 1, :3] = fondo
        cx = x + w // 2
        if aria:
            # ARIA+ con la croce menta, e sotto una riga menta (la "boccata" della pubblicità)
            ty = y + h // 2 - 5
            fine = _testo(img, "ARIA", cx - 2, ty, ARIA_TESTO)
            px, py = fine + 1, ty + 1
            img[py + 1, px:px + 3, :3] = MENTA
            img[py:py + 3, px + 1, :3] = MENTA
            img[ty + 8, x + 4:x + w - 4, :3] = MENTA
        else:
            ty = y + h // 2 - 5
            _testo(img, "SIDERA", cx, ty, SIDERA_TESTO)
            img[ty + 8, x + 4:x + w - 4, :3] = SIDERA_RIGA
        if emis is not None:
            dentro = img[y + 1:y + h - 1, x + 1:x + w - 1, :3].astype(int)
            e = (dentro * (0.35 if aria else 0.5)).astype(np.uint8)
            if not aria:
                e[dentro.sum(axis=2) < 200] = 0
            emis[y + 1:y + h - 1, x + 1:x + w - 1, :3] = e
            emis[y + 1:y + h - 1, x + 1:x + w - 1, 3] = 255


def main() -> None:
    for f in sys.argv[1:]:
        a = np.asarray(Image.open(f).convert("RGBA")).copy()
        boxes = trova(a)
        if len(boxes) < 2:
            sys.exit(f"{f}: schermi non trovati ({boxes})")
        disegna(a, boxes)
        Image.fromarray(a).save(f)
        print(f"{f}: schermi {boxes[:2]}")


if __name__ == "__main__":
    main()
