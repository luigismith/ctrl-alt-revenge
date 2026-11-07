# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Il logo del titolo, rifatto il 7 novembre 2026 (Luigi: «rifai anche la scritta»).

  python -I tools/fxui/logo.py --prove DIR          tutte le varianti, a 1x e a 4x
  python -I tools/fxui/logo.py --variante A --uscita DIR   title_logo.png e title_subtitle.png

Tutto procedurale, niente AI: le lettere sono quelle di bigfont.py, inclinate e più strette, con il
trattamento dei pezzi di street art dei murales di Totò (riempimento a fasce calde, contorno doppio
inchiostro-crema-inchiostro, blocco in rilievo, colature) e, sopra, i tasti CTRL e ALT di una tastiera
beige degli anni '90.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bigfont  # noqa: E402
import palette as P  # noqa: E402
import pix  # noqa: E402

INK = P.INK
PLUM = pix.hexc("#2a1426")      # il blocco in rilievo
PLUM_LO = pix.hexc("#1a0c18")
CREAM_LINE = pix.hexc("#f3e2b8")
WHITE = pix.hexc("#fffbea")
# tasti beige, come le tastiere dei PC degli anni '90
KEY_TOP = pix.hexc("#efe4c6")
KEY_FACE = pix.hexc("#ddcda4")
KEY_SIDE = pix.hexc("#a8916a")
KEY_SIDE_LO = pix.hexc("#7a6446")
KEY_INK = pix.hexc("#2b1a24")
CYAN = P.CYAN
CYAN_HI = P.CYAN_HI


@dataclass
class Variante:
    nome: str
    fill: list                      # colori delle fasce, dall'alto
    bands: list                     # inizio di ogni fascia (frazione di H)
    tasti: bool = True              # CTRL e ALT come tasti; altrimenti scritti come REVENGE, più piccoli
    ciano: bool = False             # il tocco di GIG: legende dei tasti accese e una riga «hackerata»
    colature: bool = True
    shear: float = 0.22
    H: int = 31
    note: str = ""
    extra: dict = field(default_factory=dict)


FUOCO = [pix.hexc("#fff3c4"), P.GOLD_HI, P.GOLD, P.ORANGE, pix.hexc("#d0581e")]
CREMA = [P.CREAM_HI, P.CREAM, P.CREAM_LO, P.CREAM_LO2]

VARIANTI = {
    "A": Variante("tasti e fuoco", FUOCO, [0.0, 0.16, 0.38, 0.62, 0.84],
                  note="tasti beige, REVENGE! inclinato a fasce di fuoco, colature"),
    "B": Variante("tasti e fuoco, col ciano", FUOCO, [0.0, 0.16, 0.38, 0.62, 0.84], ciano=True,
                  note="come A, ma le legende dei tasti e il sottotitolo si accendono del ciano di GIG"),
    "C": Variante("murale", CREMA, [0.0, 0.2, 0.55, 0.82], tasti=False,
                  note="tutto a spray, crema, CTRL+ALT piccolo sopra"),
}
SCELTA = "A"   # la variante del gioco (make_ui.py)


def shear_mask(mask: np.ndarray, k: float, base: int) -> np.ndarray:
    """Corsivo: la riga y si sposta a destra di (base - y) * k; la riga base resta ferma."""
    h, w = mask.shape
    extra = int(np.ceil(base * k)) + 2
    out = np.zeros((h, w + extra), bool)
    for y in range(h):
        dx = int(round(max(0, base - y) * k))
        out[y, dx:dx + w] = mask[y]
    return out


def word_mask(text: str, m: bigfont.M, gap: int, k: float) -> np.ndarray:
    mk, _ = bigfont.text_mask(text, m, gap)
    return shear_mask(mk, k, m.H)


def colature(F: np.ndarray, base: int, rng: np.random.Generator, n_per: int = 1) -> np.ndarray:
    """Colature dal fondo dei tratti: gocce larghe 2 px con la goccia tonda in fondo."""
    h, w = F.shape
    D = np.zeros_like(F)
    bottom = F[base - 1] & ~F[base] if base < h else F[base - 1]
    cols = np.nonzero(bottom)[0]
    if len(cols) == 0:
        return D
    # tratti contigui sul fondo
    runs, start = [], cols[0]
    for a, b in zip(cols[:-1], cols[1:]):
        if b != a + 1:
            runs.append((start, a))
            start = b
    runs.append((start, cols[-1]))
    for i, (a, b) in enumerate(runs):
        if b - a < 3 or rng.random() < 0.45:
            continue
        x = int(rng.integers(a + 1, b - 1))
        L = int(rng.integers(3, 9))
        D[base:base + L, x:x + 2] = True
        yb = base + L
        D[yb:yb + 2, x - 1:x + 3] = True
        D[yb + 2, x:x + 2] = True
    return D & ~F


def fill_bands(img: np.ndarray, F: np.ndarray, y0: int, H: int, colors: list, bands: list,
               dither: bool = True) -> None:
    """Fasce orizzontali; sul confine fra due fasce una riga a scacchi (retinatura da 16 bit)."""
    h, w = F.shape
    ys = np.arange(h)[:, None] - y0
    frac = ys / H
    idx = np.zeros((h, 1), np.int32)
    for i, s in enumerate(bands):
        idx[frac >= s] = i
    idx = np.broadcast_to(idx, (h, w)).copy()
    if dither:
        chk = (np.add.outer(np.arange(h), np.arange(w)) % 2) == 0
        for i, s in enumerate(bands[1:], 1):
            yb = y0 + int(round(s * H))
            if 0 <= yb - 1 < h:
                row = idx[yb - 1]
                row[chk[yb - 1]] = i
    idx[ys[:, 0] >= H] = len(colors) - 1  # colature: l'ultimo colore
    for i, c in enumerate(colors):
        pix.paint(img, F & (idx == i), c)


def pezzo(lines: list[tuple[str, bigfont.M, float]], v: Variante, seed: int = 7,
          line_gap: int = 6, glitch: bool = False) -> np.ndarray:
    """Un «pezzo» di street art: righe di lettere inclinate, contorno doppio, rilievo, colature."""
    rng = np.random.default_rng(seed)
    masks = []
    for text, m, k in lines:
        gap = max(2, m.S // 3)
        mk = word_mask(text, m, gap, k)
        masks.append((mk, m))
    pad = 12
    W = max(mk.shape[1] for mk, _ in masks) + 2 * pad
    Ht = sum(m.H for _, m in masks) + line_gap * (len(masks) - 1) + 2 * pad + 14
    F = np.zeros((Ht, W), bool)
    layers = []  # (maschera della riga, y0, H)
    y = pad
    for mk, m in masks:
        x = pad + (W - 2 * pad - mk.shape[1]) // 2
        L = np.zeros_like(F)
        L[y:y + mk.shape[0], x:x + mk.shape[1]] = mk
        if v.colature:
            L |= colature(L, y + m.H, rng)
        F |= L
        layers.append((L, y, m.H))
        y += m.H + line_gap
    if glitch:
        # una fetta della riga grande spostata a destra, come un segnale disturbato
        L, y0, H = layers[-1]
        a, b = y0 + int(H * 0.46), y0 + int(H * 0.46) + 3
        sl = F[a:b].copy()
        F[a:b] = False
        F[a:b, 4:] = sl[:, :-4]
        for i, (L2, yy, hh) in enumerate(layers):
            s2 = L2[a:b].copy()
            L2[a:b] = False
            L2[a:b, 4:] = s2[:, :-4]
    O1 = pix.dilate(F, 1)                 # inchiostro
    # il filo crema e l'inchiostro di fuori girano solo attorno alla sagoma: nei buchi delle lettere
    # (A, R, E, G) resta l'inchiostro, così le controforme non si riempiono di righe
    S1 = ndimage.binary_fill_holes(pix.dilate(F, 2))
    O2 = pix.dilate(F, 2)
    holes = S1 & ~O2
    O2 |= holes
    O3 = pix.dilate(S1, 1)                # inchiostro di fuori
    E = np.zeros_like(F)
    for i in range(1, 5):                 # il blocco in rilievo, giù a destra
        E |= pix.shift(O3, i, i)
    E &= ~O3
    img = pix.new(W, Ht)
    pix.paint(img, pix.shift(O3 | E, 1, 1) & ~(O3 | E), INK)
    pix.paint(img, E, PLUM)
    # il bordo in basso del rilievo, più scuro
    pix.paint(img, E & ~pix.shift(E, -1, -1), PLUM_LO)
    pix.paint(img, O3 & ~O2, INK)
    pix.paint(img, O2 & ~O1, CREAM_LINE)
    pix.paint(img, holes | (O1 & ~F), INK)
    # nei buchi il filo crema non c'è: si toglie dove tocca un buco
    pix.paint(img, (O2 & ~O1) & pix.dilate(holes, 1) & ~pix.dilate(~S1, 1), INK)
    for L, y0, H in layers:
        fill_bands(img, L, y0, H, v.fill, v.bands)
    # luce: 1 px chiaro sul bordo in alto e sul bordo sinistro dei tratti
    top = F & ~pix.shift(F, 0, 1)
    pix.paint(img, top, WHITE)
    # i lampi di vernice fresca: piccole diagonali bianche sulle lettere grandi
    L, y0, H = layers[-1]
    ys, xs = np.nonzero(L[y0 + 3:y0 + H // 2])
    for _ in range(5):
        if len(xs) == 0:
            break
        j = int(rng.integers(len(xs)))
        cx, cy = xs[j], ys[j] + y0 + 3
        for t in range(3):
            if L[cy + t, cx - t] and L[cy + t, cx - t - 1]:
                img[cy + t, cx - t] = WHITE
    if glitch:
        a = layers[-1][1] + int(layers[-1][2] * 0.46)
        edge = (O3[a - 1] | O3[a]) if a > 0 else O3[a]
        img[a - 1, :][edge & (img[a - 1, :, 3] > 0)] = CYAN_HI
        b = a + 3
        img[b, :][O3[b] & (img[b, :, 3] > 0) & ~F[b]] = CYAN
    out, _ = pix.crop_alpha(img)
    return out


def tasto(legend: str, ciano: bool, h_leg: int = 11) -> np.ndarray:
    """Un tasto beige visto un po' dall'alto: faccia, fianchi, legenda."""
    m = bigfont.metrics(h_leg, 3)
    lm, lw = bigfont.text_mask(legend, m, 2)
    lm = lm[:m.H]
    face_w, face_h = lw + 12, m.H + 9
    skirt = 5
    W, Hh = face_w + 6, face_h + skirt + 4
    img = pix.new(W + 2, Hh + 2)
    # sagoma esterna: rettangolo con gli angoli smussati di 2
    body = np.zeros((Hh, W), bool)
    body[:, :] = True
    for (yy, xx) in [(0, 0), (0, W - 1), (Hh - 1, 0), (Hh - 1, W - 1)]:
        sy = 1 if yy == 0 else -1
        sx = 1 if xx == 0 else -1
        body[yy, xx] = body[yy, xx + sx] = body[yy + sy, xx] = False
    full = np.zeros((Hh + 2, W + 2), bool)
    full[1:Hh + 1, 1:W + 1] = body
    pix.paint(img, pix.dilate(full, 1) & ~full, INK)
    pix.paint(img, full, KEY_SIDE)
    # fianco in basso più scuro
    lo = np.zeros_like(full)
    lo[Hh - skirt + 1:Hh + 1, 1:W + 1] = True
    pix.paint(img, full & lo, KEY_SIDE_LO)
    # faccia superiore, rientrata
    fx0, fy0 = 4, 2
    face = np.zeros_like(full)
    face[fy0:fy0 + face_h, fx0:fx0 + face_w] = True
    for (yy, xx) in [(fy0, fx0), (fy0, fx0 + face_w - 1), (fy0 + face_h - 1, fx0), (fy0 + face_h - 1, fx0 + face_w - 1)]:
        face[yy, xx] = False
    pix.paint(img, face, KEY_FACE)
    pix.paint(img, face & ~pix.shift(face, 0, 2), KEY_TOP)
    pix.paint(img, face & ~pix.shift(face, 0, -1), KEY_SIDE)
    lx, ly = fx0 + (face_w - lw) // 2, fy0 + 4
    leg = np.zeros_like(full)
    leg[ly:ly + m.H, lx:lx + lw] = lm
    if ciano:
        pix.paint(img, pix.dilate(leg, 1, square=False) & face & ~leg, pix.hexc("#7fb9b4"))
        pix.paint(img, leg, P.CYAN_MID)
        pix.paint(img, leg & ~pix.shift(leg, 0, 1), CYAN_HI)
    else:
        pix.paint(img, leg, KEY_INK)
    return img


def piu() -> np.ndarray:
    m = bigfont.metrics(13, 4)
    mk = bigfont.glyph_mask("+", m)[:m.H]
    mk = np.pad(mk, ((2, 3), (2, 3)))
    img = pix.new(mk.shape[1], mk.shape[0])
    O = pix.dilate(mk, 1)
    pix.paint(img, pix.shift(O, 1, 1) & ~O, PLUM)
    pix.paint(img, O & ~mk, INK)
    pix.paint(img, mk, CREAM_LINE)
    pix.paint(img, mk & ~pix.shift(mk, 0, 1), WHITE)
    return img


def logo(v: Variante) -> np.ndarray:
    big = bigfont.metrics(v.H, 8, 7)
    if not v.tasti:
        small = bigfont.metrics(16, 4)
        return pezzo([("CTRL+ALT", small, v.shear * 0.6), ("REVENGE!", big, v.shear)], v, line_gap=6)
    rev = pezzo([("REVENGE!", big, v.shear)], v)
    k1, k2, pl = tasto("CTRL", v.ciano), tasto("ALT", v.ciano), piu()
    gap = 3
    row_w = k1.shape[1] + gap + pl.shape[1] + gap + k2.shape[1]
    row_h = max(k1.shape[0], k2.shape[0])
    W = max(rev.shape[1], row_w) + 4
    over = 4                                   # i tasti si appoggiano sul pezzo
    Ht = row_h + rev.shape[0] - over
    img = pix.new(W, Ht)
    pix.over(img, rev, (W - rev.shape[1]) // 2, row_h - over)
    # la fila dei tasti un po' a sinistra, come l'inclinazione della scritta
    x = (W - row_w) // 2 - 10
    pix.over(img, k1, x, row_h - k1.shape[0])
    x += k1.shape[1] + gap
    pix.over(img, pl, x, (row_h - pl.shape[0]) // 2 + 1)
    x += pl.shape[1] + gap
    pix.over(img, k2, x, row_h - k2.shape[0])
    out, _ = pix.crop_alpha(img)
    return out


def sottotitolo(v: Variante) -> np.ndarray:
    """TARANTO · 2087 in crema, spaziato, fra due trattini: un'etichetta, non un'altra scritta grande."""
    m = bigfont.metrics(10, 2)
    mk, w = bigfont.text_mask("TARANTO · 2087", m, 2, space=5)
    mk = mk[:m.H]
    dash = 10
    W = w + 2 * (dash + 5) + 4
    F = np.zeros((m.H + 4, W), bool)
    F[2:2 + m.H, dash + 7:dash + 7 + w] = mk
    yc = 2 + m.ym
    F[yc:yc + m.T, 2:2 + dash] = True
    F[yc:yc + m.T, W - 2 - dash:W - 2] = True
    img = pix.new(W + 1, m.H + 5)
    Fp = np.zeros(img.shape[:2], bool)
    Fp[:F.shape[0], :F.shape[1]] = F
    O = pix.dilate(Fp, 1)
    pix.paint(img, pix.shift(O, 1, 1) & ~O, PLUM)
    pix.paint(img, O & ~Fp, INK)
    pix.paint(img, Fp, (CYAN_HI if v.ciano else CREAM_LINE))
    out, _ = pix.crop_alpha(img)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--prove", help="cartella: tutte le varianti, a 1x e a 4x")
    ap.add_argument("--variante", default=SCELTA, choices=sorted(VARIANTI))
    ap.add_argument("--uscita", help="cartella: title_logo.png e title_subtitle.png della variante")
    args = ap.parse_args()
    if args.prove:
        d = Path(args.prove)
        for k, v in VARIANTI.items():
            lg, st = logo(v), sottotitolo(v)
            pix.save(lg, d / f"logo_{k}.png")
            pix.save(st, d / f"sottotitolo_{k}.png")
            bg = pix.new(lg.shape[1] + 8, lg.shape[0] + st.shape[0] + 14, pix.hexc("#3a1a1e"))
            pix.over(bg, lg, 4, 4)
            pix.over(bg, st, (bg.shape[1] - st.shape[1]) // 2, lg.shape[0] + 8)
            pix.save(pix.upscale(bg, 4), d / f"logo_{k}_4x.png")
            print(k, v.nome, lg.shape[1], "x", lg.shape[0], "| sottotitolo", st.shape[1], "x", st.shape[0])
    if args.uscita:
        v = VARIANTI[args.variante]
        pix.save(logo(v), Path(args.uscita) / "title_logo.png")
        pix.save(sottotitolo(v), Path(args.uscita) / "title_subtitle.png")


if __name__ == "__main__":
    main()
