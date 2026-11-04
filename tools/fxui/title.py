# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Scritte grandi in stile locandina: riempimento a fasce, bordo, estrusione, ombra."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import bigfont
import palette as P
import pix


@dataclass
class Style:
    fill: list = field(default_factory=lambda: [P.CREAM_HI, P.CREAM, P.CREAM_LO])
    bands: list = field(default_factory=lambda: [0.0, 0.2, 0.68])   # inizio di ogni fascia (frazione di H)
    top_light: object = P.CREAM_HI      # 1 px chiaro sul bordo superiore di ogni tratto (None = no)
    bottom_dark: object = None          # 1 px scuro sul bordo inferiore di ogni tratto
    outline: object = P.RED_DARK
    outline_w: int = 2
    outline_outer: object = None        # colore dell'ultimo px esterno del bordo (None = come outline)
    extrude: object = P.RED_DEEP
    extrude_n: int = 2                  # px di estrusione verso il basso a destra
    extrude_dir: tuple = (0, 1)         # passo dell'estrusione
    shadow: object = P.INK
    shadow_d: tuple = (2, 2)


LOGO = Style()
BANNER = Style(outline_w=1, extrude_n=1, shadow_d=(1, 1), bands=[0.0, 0.22, 0.7])
SUBTITLE = Style(fill=[P.ORANGE_HI, P.ORANGE, P.ORANGE_LO], bands=[0.0, 0.25, 0.75],
                 top_light=None, outline=P.INK, outline_w=1, extrude=None, extrude_n=0,
                 shadow=None)


def render(lines: list[str], m: bigfont.M, style: Style, gap: int | None = None,
           line_gap: int | None = None, align: str = "center", space: int | None = None,
           fills: dict | None = None) -> np.ndarray:
    """Disegna una o più righe. Restituisce l'immagine RGBA ritagliata ai pixel visibili.

    fills: {indice del carattere nella prima riga: [colori delle fasce]} per colorare a parte
    singoli caratteri (es. il numero del livello).
    """
    if gap is None:
        gap = 2 * style.outline_w + 1
    if line_gap is None:
        line_gap = 2 * style.outline_w + style.extrude_n + 3
    pad = style.outline_w + style.extrude_n + max(style.shadow_d) + 2
    rows = []
    for li, t in enumerate(lines):
        mk, _ = bigfont.text_mask(t, m, gap, space)
        # mappa carattere -> colonne, per i colori dei singoli caratteri
        owner = np.full(mk.shape[1], -1, np.int32)
        x = 0
        for ci, ch in enumerate(t):
            w = (space if space is not None else max(3, int(round(m.H * 0.32)))) if ch == " " \
                else bigfont.glyph_mask(ch, m).shape[1]
            owner[x:x + w] = ci if li == 0 else -1
            x += w + gap
        rows.append((mk, owner))
    W = max(mk.shape[1] for mk, _ in rows) + 2 * pad
    row_h = m.H
    H = len(lines) * row_h + (len(lines) - 1) * line_gap + 2 * pad + max(2, m.T)
    F = np.zeros((H, W), bool)
    band_idx = np.full((H, W), -1, np.int32)
    char_idx = np.full((H, W), -1, np.int32)
    y = pad
    for mk, owner in rows:
        if align == "center":
            x = pad + (W - 2 * pad - mk.shape[1]) // 2
        else:
            x = pad
        hh, ww = mk.shape
        F[y:y + hh, x:x + ww] |= mk
        char_idx[y:y + hh, x:x + ww][mk] = np.broadcast_to(owner, mk.shape)[mk]
        # fasce del riempimento, relative alla riga
        for r in range(hh):
            frac = r / m.H
            b = 0
            for i, start in enumerate(style.bands):
                if frac >= start:
                    b = i
            row = band_idx[y + r, x:x + ww]
            row[mk[r]] = b
        y += row_h + line_gap
    O = pix.dilate(F, style.outline_w, square=True)
    body = O.copy()
    E = np.zeros_like(F)
    for i in range(1, style.extrude_n + 1):
        E |= pix.shift(O, style.extrude_dir[0] * i, style.extrude_dir[1] * i)
    E &= ~O
    body |= E
    img = pix.new(W, H)
    if style.shadow is not None:
        SH = pix.shift(body, *style.shadow_d) & ~body
        pix.paint(img, SH, style.shadow)
    if style.extrude is not None:
        pix.paint(img, E, style.extrude)
    pix.paint(img, O & ~F, style.outline)
    if style.outline_outer is not None and style.outline_w > 1:
        inner = pix.dilate(F, style.outline_w - 1, square=True)
        pix.paint(img, O & ~inner, style.outline_outer)
    special = np.zeros_like(F)
    if fills:
        for ci in fills:
            special |= char_idx == ci
    for i, c in enumerate(style.fill):
        pix.paint(img, F & (band_idx == i) & ~special, c)
    if fills:
        for ci, cols in fills.items():
            for i, c in enumerate(cols):
                pix.paint(img, F & (band_idx == i) & (char_idx == ci), c)
    if style.top_light is not None:
        top = F & ~pix.shift(F, 0, 1) & ~special
        pix.paint(img, top, style.top_light)
    if style.bottom_dark is not None:
        bot = F & ~pix.shift(F, 0, -1)
        pix.paint(img, bot, style.bottom_dark)
    out, _ = pix.crop_alpha(img)
    return out
