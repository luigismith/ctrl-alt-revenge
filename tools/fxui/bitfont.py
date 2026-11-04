# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Disegno di testo con i font bitmap di font_glyphs (stesso risultato del TTF a 1x)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import font_glyphs as fg
import pix


@dataclass
class Face:
    name: str
    table: dict
    advances: dict = field(default_factory=dict)
    ascent: int = fg.ASCENT
    descent: int = fg.DESCENT

    @property
    def line_height(self) -> int:
        return self.ascent + self.descent

    def glyph(self, ch: str):
        if ch in self.table:
            return self.table[ch]
        return self.table["?"]

    def advance(self, ch: str) -> int:
        if ch in self.advances:
            return self.advances[ch]
        top, rows = self.glyph(ch)
        return len(rows[0]) + 1

    def width(self, text: str) -> int:
        """Larghezza in px dell'inchiostro (senza lo spazio dopo l'ultimo glifo)."""
        if not text:
            return 0
        w = sum(self.advance(c) for c in text)
        last = text[-1]
        if last not in self.advances:
            w -= 1
        return w

    def mask(self, text: str) -> np.ndarray:
        """Maschera del testo: altezza = ascent + descent, linea di base alla riga 'ascent'."""
        w = max(1, sum(self.advance(c) for c in text))
        m = np.zeros((self.line_height, w), bool)
        x = 0
        for ch in text:
            top, rows = self.glyph(ch)
            if ch != " ":
                for r, row in enumerate(rows):
                    y = self.ascent - (top - r)
                    for c, v in enumerate(row):
                        if v == "#":
                            m[y, x + c] = True
            x += self.advance(ch)
        return m


REGULAR = Face("CAR Pixel", fg.REGULAR, fg.ADVANCE_REG)
BOLD = Face("CAR Pixel Bold", fg.BOLD, fg.ADVANCE_BOLD)


def draw(img: np.ndarray, x: int, y: int, text: str, face: Face, color, shadow=None,
         outline=None, shadow_offset=(1, 1)) -> None:
    """Scrive 'text' con l'angolo in alto a sinistra della riga in (x, y).

    shadow: colore dell'ombra spostata di shadow_offset; outline: contorno di 1 px (8 direzioni).
    """
    m = face.mask(text)
    pad = 2
    H, W = m.shape
    big = np.zeros((H + 2 * pad, W + 2 * pad), bool)
    big[pad:pad + H, pad:pad + W] = m
    layer = pix.new(W + 2 * pad, H + 2 * pad)
    if outline is not None:
        pix.paint(layer, pix.dilate(big, 1, square=True), outline)
    if shadow is not None:
        sh = pix.shift(big, *shadow_offset)
        if outline is not None:
            sh = pix.shift(pix.dilate(big, 1, square=True), *shadow_offset)
        under = pix.new(W + 2 * pad, H + 2 * pad)
        pix.paint(under, sh, shadow)
        pix.over(under, layer)
        layer = under
    pix.paint(layer, big, color)
    pix.over(img, layer, x - pad, y - pad)
