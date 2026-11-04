# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Lettering a blocchi per logo e scritte grandi, nello stile della locandina.

Ogni lettera è una piccola costruzione geometrica (rettangoli, parallelogrammi, smussi)
in funzione dell'altezza delle maiuscole H e dello spessore delle aste S, rasterizzata
direttamente alla risoluzione del gioco: niente ingrandimenti, quindi pixel tutti uguali.
Proporzioni misurate sulla locandina: asta circa 0,21 H, lettere larghe 0,7-0,8 H.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

import pix


@dataclass
class M:
    """Misure di una dimensione del lettering."""
    H: int          # altezza delle maiuscole
    S: int          # spessore delle aste verticali
    T: int          # spessore delle barre orizzontali
    C: int          # smusso degli angoli

    @property
    def ym(self) -> int:
        """Inizio della barra centrale."""
        return (self.H - self.T) // 2

    def w(self, k: float, center: bool = False) -> int:
        """Larghezza k*H; con center=True ha la stessa parità di S (asta centrata intera)."""
        w = int(round(k * self.H))
        if center and (w - self.S) % 2:
            w += 1
        return w


def metrics(H: int, S: int | None = None, T: int | None = None) -> M:
    if S is None:
        S = max(2, int(round(0.21 * H)))
    if T is None:
        # come sulla locandina, le barre orizzontali sono un poco più sottili delle aste
        # (dalla misura 6 in su): le controforme restano leggibili anche col bordo dentro
        T = S - 1 if S >= 6 else S
    C = max(1, int(round(S * 0.5)))
    return M(H, S, T, C)


def R(x0, y0, x1, y1):
    return pix.rect_poly(x0, y0, x1, y1)


def diag(xa: float, ya: float, xb: float, yb: float, wd: float):
    """Parallelogramma con lati orizzontali a ya e yb, largo wd in orizzontale."""
    return [(xa - wd / 2, ya), (xa + wd / 2, ya), (xb + wd / 2, yb), (xb - wd / 2, yb)]


def tri(*pts):
    return list(pts)


def cut(x: float, y: float, sx: int, sy: int, c: int):
    """Triangolo da togliere all'angolo (x, y): lati di c verso (sx, sy)."""
    return [(x, y), (x + sx * c, y), (x, y + sy * c)]


def diag_width(m: M, dx: float, dy: float) -> float:
    """Larghezza orizzontale che dà a un tratto obliquo lo stesso peso di un'asta."""
    return m.S * math.sqrt(1.0 + (dx / dy) ** 2) if dy else m.S


# ------------------------------------------------------------------------------------
# glifi: ognuno restituisce (larghezza, poligoni pieni, poligoni da togliere)
# ------------------------------------------------------------------------------------

def g_A(m):
    W = m.w(0.78)
    ya = (m.H - m.T) // 2 + m.T // 2
    fill = [R(0, 0, W, m.H)]
    sub = [R(m.S, m.T, W - m.S, ya), R(m.S, ya + m.T, W - m.S, m.H),
           cut(0, 0, 1, 1, m.C + 1), cut(W, 0, -1, 1, m.C + 1)]
    return W, fill, sub


def g_B(m):
    W = m.w(0.74)
    yc = m.ym + m.T // 2
    fill = [R(0, 0, W, m.H)]
    sub = [R(m.S, m.T, W - m.S, m.ym), R(m.S, m.ym + m.T, W - m.S, m.H - m.T),
           cut(W, 0, -1, 1, m.C), cut(W, m.H, -1, -1, m.C),
           tri((W, yc - m.C), (W - m.C, yc), (W, yc + m.C))]
    return W, fill, sub


def g_C(m):
    W = m.w(0.72)
    fill = [R(0, 0, W, m.H)]
    sub = [R(m.S, m.T, W, m.H - m.T), cut(0, 0, 1, 1, m.C + 1), cut(0, m.H, 1, -1, m.C + 1)]
    return W, fill, sub


def g_D(m):
    W = m.w(0.76)
    fill = [R(0, 0, W, m.H)]
    sub = [R(m.S, m.T, W - m.S, m.H - m.T), cut(W, 0, -1, 1, m.C + 1), cut(W, m.H, -1, -1, m.C + 1)]
    return W, fill, sub


def g_E(m):
    W = m.w(0.66)
    fill = [R(0, 0, m.S, m.H), R(0, 0, W, m.T), R(0, m.ym, W - max(1, m.S // 3), m.ym + m.T),
            R(0, m.H - m.T, W, m.H)]
    return W, fill, []


def g_F(m):
    W = m.w(0.64)
    fill = [R(0, 0, m.S, m.H), R(0, 0, W, m.T), R(0, m.ym, W - max(1, m.S // 3), m.ym + m.T)]
    return W, fill, []


def g_G(m):
    W = m.w(0.76)
    xb = W // 2 - (m.S // 4)
    fill = [R(0, 0, W, m.H)]
    sub = [R(m.S, m.T, W, m.H - m.T), cut(0, 0, 1, 1, m.C + 1), cut(0, m.H, 1, -1, m.C + 1)]
    add = [R(W - m.S, m.ym, W, m.H), R(xb, m.ym, W, m.ym + m.T)]
    return W, fill, sub, add, [cut(W, m.H, -1, -1, m.C)]


def g_H(m):
    W = m.w(0.76)
    return W, [R(0, 0, m.S, m.H), R(W - m.S, 0, W, m.H), R(0, m.ym, W, m.ym + m.T)], []


def g_I(m):
    return m.S, [R(0, 0, m.S, m.H)], []


def g_J(m):
    W = m.w(0.64)
    yh = m.H - m.T - max(2, m.H // 5)
    fill = [R(W - m.S, 0, W, m.H), R(0, m.H - m.T, W, m.H), R(0, yh, m.S, m.H)]
    return W, fill, [cut(0, m.H, 1, -1, m.C), cut(W, m.H, -1, -1, m.C + 1)]


def g_K(m):
    W = m.w(0.76)
    yc = m.H / 2
    wd = diag_width(m, W - m.S, m.H / 2) * 0.9
    fill = [R(0, 0, m.S, m.H),
            diag(m.S + wd / 2 - 1, yc + m.T / 2, W - wd / 2, 0, wd),
            diag(m.S + wd / 2 - 1, yc - m.T / 2, W - wd / 2, m.H, wd)]
    return W, fill, []


def g_L(m):
    W = m.w(0.62)
    return W, [R(0, 0, m.S, m.H), R(0, m.H - m.T, W, m.H)], []


def g_M(m):
    W = m.w(0.98, center=True)
    yv = int(round(m.H * 0.62))
    xc = W / 2
    wd = diag_width(m, xc - m.S, yv) * 0.92
    fill = [R(0, 0, m.S, m.H), R(W - m.S, 0, W, m.H),
            diag(wd / 2, 0, xc, yv, wd), diag(W - wd / 2, 0, xc, yv, wd)]
    return W, fill, []


def g_N(m):
    W = m.w(0.82)
    wd = diag_width(m, W - m.S, m.H) * 0.95
    fill = [R(0, 0, m.S, m.H), R(W - m.S, 0, W, m.H), diag(wd / 2, 0, W - wd / 2, m.H, wd)]
    return W, fill, []


def g_O(m):
    W = m.w(0.76)
    fill = [R(0, 0, W, m.H)]
    sub = [R(m.S, m.T, W - m.S, m.H - m.T)] + [cut(x, y, sx, sy, m.C + 1) for (x, y, sx, sy) in
                                                 ((0, 0, 1, 1), (W, 0, -1, 1), (0, m.H, 1, -1), (W, m.H, -1, -1))]
    return W, fill, sub


def _bowl_bottom(m):
    """Fine della pancia di P e R: un poco sotto la metà alle misure grandi."""
    return m.ym + m.T + (1 if m.H >= 20 else 0)


def g_P(m):
    W = m.w(0.72)
    yb = _bowl_bottom(m)
    fill = [R(0, 0, m.S, m.H), R(0, 0, W, yb)]
    sub = [R(m.S, m.T, W - m.S, yb - m.T), cut(W, 0, -1, 1, m.C + 1), cut(W, yb, -1, -1, m.C + 1)]
    return W, fill, sub


def g_Q(m):
    W, fill, sub = g_O(m)
    t = max(2, m.S // 2 + 1)
    tail = [diag(W - m.S - t / 2, m.H - m.T - t, W + t / 2, m.H + t // 2, m.S)]
    return W, fill, sub, tail, []


def g_R(m):
    W = m.w(0.76)
    yb = _bowl_bottom(m)
    wd = m.S + 1
    fill = [R(0, 0, m.S, m.H), R(0, 0, W, yb)]
    sub = [R(m.S, m.T, W - m.S, yb - m.T), cut(W, 0, -1, 1, m.C + 1), cut(W, yb, -1, -1, m.C + 1)]
    leg = [diag(W - m.S - wd / 2 + 1, yb - 1, W - wd / 2, m.H, wd)]
    return W, fill, sub, leg, []


def g_S(m):
    W = m.w(0.72)
    # code delle estremità (in alto a destra, in basso a sinistra): devono lasciare aperta
    # la controforma, altrimenti alle misure piccole la S diventa un 8
    hook = max(0, min(m.C, m.ym - m.T - 2))
    fill = [R(0, 0, W, m.T), R(0, 0, m.S, m.ym + m.T), R(0, m.ym, W, m.ym + m.T),
            R(W - m.S, m.ym, W, m.H), R(0, m.H - m.T, W, m.H),
            R(W - m.S, 0, W, m.T + hook), R(0, m.H - m.T - hook, m.S, m.H)]
    sub = [cut(0, 0, 1, 1, m.C + 1), cut(W, m.H, -1, -1, m.C + 1),
           cut(0, m.ym + m.T, 1, -1, m.C), cut(W, m.ym, -1, 1, m.C)]
    return W, fill, sub


def g_T(m):
    W = m.w(0.76, center=True)
    x0 = (W - m.S) // 2
    return W, [R(0, 0, W, m.T), R(x0, 0, x0 + m.S, m.H)], []


def g_U(m):
    W = m.w(0.76)
    fill = [R(0, 0, m.S, m.H), R(W - m.S, 0, W, m.H), R(0, m.H - m.T, W, m.H)]
    return W, fill, [cut(0, m.H, 1, -1, m.C + 1), cut(W, m.H, -1, -1, m.C + 1)]


def g_V(m):
    """Fianchi verticali in alto, poi due obliqui paralleli verso un fondo piatto."""
    W = m.w(0.80, center=True)
    yv = int(round(m.H * 0.42))
    xc = W / 2
    bw = m.S
    slope = (m.H - yv) / (xc - bw / 2)
    ya = yv + (xc - m.S) * slope
    poly = [(0, 0), (m.S, 0), (m.S, yv), (xc, ya), (W - m.S, yv), (W - m.S, 0), (W, 0), (W, yv),
            (xc + bw / 2, m.H), (xc - bw / 2, m.H), (0, yv)]
    return W, [poly], []


def g_W(m):
    W = m.w(1.02, center=True)
    yv = m.H - int(round(m.H * 0.62))
    xc = W / 2
    wd = diag_width(m, xc - m.S, m.H - yv) * 0.92
    fill = [R(0, 0, m.S, m.H), R(W - m.S, 0, W, m.H),
            diag(xc, yv, wd / 2, m.H, wd), diag(xc, yv, W - wd / 2, m.H, wd)]
    return W, fill, []


def g_X(m):
    W = m.w(0.80)
    wd = diag_width(m, W - m.S, m.H) * 0.95
    return W, [diag(wd / 2, 0, W - wd / 2, m.H, wd), diag(W - wd / 2, 0, wd / 2, m.H, wd)], []


def g_Y(m):
    W = m.w(0.80, center=True)
    yc = int(round(m.H * 0.5))
    xc = W / 2
    wd = diag_width(m, xc - m.S / 2, yc) * 0.92
    x0 = (W - m.S) // 2
    fill = [diag(wd / 2, 0, xc, yc + m.T / 2, wd), diag(W - wd / 2, 0, xc, yc + m.T / 2, wd),
            R(x0, yc, x0 + m.S, m.H)]
    return W, fill, []


def g_Z(m):
    W = m.w(0.72)
    wd = diag_width(m, W - m.S, m.H - 2 * m.T) * 0.95
    fill = [R(0, 0, W, m.T), R(0, m.H - m.T, W, m.H), diag(W - wd / 2, m.T, wd / 2, m.H - m.T, wd)]
    return W, fill, []


def g_0(m):
    W = m.w(0.70)
    fill = [R(0, 0, W, m.H)]
    sub = [R(m.S, m.T, W - m.S, m.H - m.T)] + [cut(x, y, sx, sy, m.C + 1) for (x, y, sx, sy) in
                                                 ((0, 0, 1, 1), (W, 0, -1, 1), (0, m.H, 1, -1), (W, m.H, -1, -1))]
    return W, fill, sub


def g_1(m):
    W = m.w(0.56)
    x0 = W - m.S - max(1, m.S // 2)
    fl = max(2, m.C + 1)
    fill = [R(x0, 0, x0 + m.S, m.H), [(x0, 0), (x0 + 1, 0), (x0 + 1, fl + m.T), (0, fl + m.T), (0, fl)],
            R(0, m.H - m.T, W, m.H)]
    return W, fill, []


def g_2(m):
    W = m.w(0.70)
    fill = [R(0, 0, W, m.T), R(W - m.S, 0, W, m.ym + m.T), R(0, m.ym, W, m.ym + m.T),
            R(0, m.ym, m.S, m.H), R(0, m.H - m.T, W, m.H), R(0, 0, m.S, m.T + m.C)]
    return W, fill, [cut(0, 0, 1, 1, m.C), cut(W, 0, -1, 1, m.C + 1), cut(W, m.ym + m.T, -1, -1, m.C)]


def g_3(m):
    W = m.w(0.70)
    fill = [R(0, 0, W, m.T), R(W - m.S, 0, W, m.H), R(m.S // 2, m.ym, W, m.ym + m.T),
            R(0, m.H - m.T, W, m.H)]
    return W, fill, [cut(W, 0, -1, 1, m.C + 1), cut(W, m.H, -1, -1, m.C + 1)]


def g_4(m):
    W = m.w(0.72)
    fill = [R(0, 0, m.S, m.ym + m.T), R(0, m.ym, W, m.ym + m.T), R(W - m.S, 0, W, m.H)]
    return W, fill, []


def g_5(m):
    W = m.w(0.70)
    fill = [R(0, 0, W, m.T), R(0, 0, m.S, m.ym + m.T), R(0, m.ym, W, m.ym + m.T),
            R(W - m.S, m.ym, W, m.H), R(0, m.H - m.T, W, m.H)]
    return W, fill, [cut(W, m.ym, -1, 1, m.C + 1), cut(W, m.H, -1, -1, m.C + 1), cut(0, m.H, 1, -1, m.C)]


def g_6(m):
    W = m.w(0.70)
    fill = [R(0, 0, W, m.T), R(0, 0, m.S, m.H), R(0, m.ym, W, m.ym + m.T),
            R(W - m.S, m.ym, W, m.H), R(0, m.H - m.T, W, m.H)]
    return W, fill, [cut(0, 0, 1, 1, m.C + 1), cut(0, m.H, 1, -1, m.C + 1), cut(W, m.H, -1, -1, m.C + 1),
                     cut(W, m.ym, -1, 1, m.C)]


def g_7(m):
    W = m.w(0.68)
    fill = [R(0, 0, W, m.T), R(W - m.S, 0, W, m.ym + m.T),
            diag(W - m.S / 2 - 0.5, m.ym + m.T, W / 2, m.H, m.S + 1)]
    return W, fill, []


def g_8(m):
    W, fill, sub = g_B(m)
    sub = sub[:2] + [cut(x, y, sx, sy, m.C + 1) for (x, y, sx, sy) in
                     ((0, 0, 1, 1), (W, 0, -1, 1), (0, m.H, 1, -1), (W, m.H, -1, -1))]
    return W, fill, sub


def g_9(m):
    W = m.w(0.70)
    fill = [R(0, 0, W, m.T), R(W - m.S, 0, W, m.H), R(0, m.ym, W, m.ym + m.T),
            R(0, 0, m.S, m.ym + m.T), R(0, m.H - m.T, W, m.H)]
    return W, fill, [cut(0, 0, 1, 1, m.C + 1), cut(W, 0, -1, 1, m.C + 1), cut(W, m.H, -1, -1, m.C + 1),
                     cut(0, m.ym + m.T, 1, -1, m.C)]


def g_excl(m):
    W = m.S
    gap = max(1, m.T // 2)
    return W, [R(0, 0, W, m.H - m.T - gap), R(0, m.H - m.T, W, m.H)], []


def g_quest(m):
    W = m.w(0.68)
    gap = max(1, m.T // 2)
    x0 = (W - m.S) // 2
    y2 = m.H - m.T - gap
    fill = [R(0, 0, W, m.T), R(W - m.S, 0, W, m.ym + m.T // 2 + 1), R(x0, m.ym, W, m.ym + m.T),
            R(x0, m.ym, x0 + m.S, y2), R(x0, m.H - m.T, x0 + m.S, m.H), R(0, 0, m.S, m.T + m.C)]
    return W, fill, [cut(0, 0, 1, 1, m.C), cut(W, 0, -1, 1, m.C + 1), cut(W, m.ym + m.T, -1, -1, m.C)]


def g_plus(m):
    W = m.w(0.70, center=True)
    hh = int(round(m.H * 0.72))
    if (hh - m.T) % 2:
        hh += 1
    y0 = (m.H - hh) // 2
    yc0 = y0 + (hh - m.T) // 2
    x0 = (W - m.S) // 2
    return W, [R(x0, y0, x0 + m.S, y0 + hh), R(0, yc0, W, yc0 + m.T)], []


def g_minus(m):
    W = m.w(0.5)
    return W, [R(0, m.ym, W, m.ym + m.T)], []


def g_dot(m):
    return m.S, [R(0, m.H - m.T, m.S, m.H)], []


def g_middot(m):
    s = max(2, m.S - (1 if m.S > 3 else 0))
    y0 = (m.H - s) // 2
    return s, [R(0, y0, s, y0 + s)], []


def g_colon(m):
    y0 = m.H // 2 - m.T - max(1, m.T // 2)
    return m.S, [R(0, y0, m.S, y0 + m.T), R(0, m.H - m.T, m.S, m.H)], []


def g_apos(m):
    return m.S, [R(0, 0, m.S, max(2, m.H // 3))], []


def g_comma(m):
    return m.S, [R(0, m.H - m.T, m.S, m.H), R(0, m.H, max(1, m.S // 2), m.H + max(1, m.T // 2))], []


GLYPHS = {
    "A": g_A, "B": g_B, "C": g_C, "D": g_D, "E": g_E, "F": g_F, "G": g_G, "H": g_H, "I": g_I,
    "J": g_J, "K": g_K, "L": g_L, "M": g_M, "N": g_N, "O": g_O, "P": g_P, "Q": g_Q, "R": g_R,
    "S": g_S, "T": g_T, "U": g_U, "V": g_V, "W": g_W, "X": g_X, "Y": g_Y, "Z": g_Z,
    "0": g_0, "1": g_1, "2": g_2, "3": g_3, "4": g_4, "5": g_5, "6": g_6, "7": g_7, "8": g_8,
    "9": g_9, "!": g_excl, "?": g_quest, "+": g_plus, "-": g_minus, ".": g_dot,
    "·": g_middot, ":": g_colon, "'": g_apos, ",": g_comma,
}


def glyph_mask(ch: str, m: M) -> np.ndarray:
    """Maschera di un glifo: righe da 0 (cima delle maiuscole) a H (più l'eventuale coda)."""
    res = GLYPHS[ch](m)
    if len(res) == 3:
        W, fill, sub = res
        add, sub2 = [], []
    else:
        W, fill, sub, add, sub2 = res
    h = m.H + max(2, m.T)  # spazio per code (Q, virgola)
    w = W + m.S
    mask = pix.poly_mask(w, h, fill)
    if sub:
        mask &= ~pix.poly_mask(w, h, sub)
    if add:
        mask |= pix.poly_mask(w, h, add)
    if sub2:
        mask &= ~pix.poly_mask(w, h, sub2)
    if ch == "Q":
        return mask  # la coda della Q sporge a destra
    return mask[:, :W]


def text_mask(text: str, m: M, gap: int, space: int | None = None) -> tuple[np.ndarray, int]:
    """Maschera di una riga di testo. Restituisce (maschera, larghezza)."""
    if space is None:
        space = max(3, int(round(m.H * 0.32)))
    parts = []
    for ch in text:
        if ch == " ":
            parts.append(np.zeros((m.H + max(2, m.T), space), bool))
        else:
            parts.append(glyph_mask(ch, m))
    total = sum(p.shape[1] for p in parts) + gap * (len(parts) - 1)
    out = np.zeros((m.H + max(2, m.T), total), bool)
    x = 0
    for i, p in enumerate(parts):
        out[:, x:x + p.shape[1]] |= p
        x += p.shape[1] + gap
    return out, total
