# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""La fuga per i Tamburi e il garage della madre di GIG, il secondo tratto del prologo.

Scavalcato il muro del cimitero la fuga va verso sud, e lo sfondo guarda a est (decisione 65): le
palazzine dei Tamburi sotto la pioggia e, lontano, il Mar Piccolo con le gru dell'Arsenale. Il campo
di gioco è una strada coi lavori in corso: le macerie, il bidone della differenziata, la tettoia del
fruttivendolo con le cassette, lo scavo pieno d'acqua, il ponteggio fasciato dal telo, i bancali di
cemento, un pilastro di tufo e una pila di cordoli nuovi. Poi il garage, in sezione: sulla parete di
fondo il pannello degli attrezzi, la macchina da cucire e il manichino della sarta, i bracci appesi;
sopra, il tetto col lucernario, i serbatoi, l'antenna e i panni stesi.

Come si appoggiano le cose (vedi il README):
- il pavimento si disegna prima, e quello che ci sta sopra dopo, con la base sulla riga dove GIG posa
  i piedi, dentro la fascia dell'asfalto;
- un oggetto su un blocco ha la sua faccia di sopra sulla riga del blocco su tutta la larghezza, e la
  base sul pavimento; se il disegno non ha le proporzioni del blocco, si deforma poco e lo si dice;
- quello che sta sul fondo (le transenne, l'Ape, i mobili dipinti della parete) è più scuro e senza
  contorno, le cose su cui si salta hanno il contorno, anche sopra il muro e l'asfalto.

Basi (in tools/out/ambienti/basi, fuori dal repo; i prompt stanno nella cartella privata):
e01 il cielo, e02 ed e03 le palazzine, e04 le cose della strada di là, e05 gli oggetti della
strada, e06 il ponteggio col telo, e07 la parete del garage, e08 gli oggetti del garage e del
tetto, p02 il primo piano.

Il codice è MIT, come il resto del gioco.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from piani import (FLOOR, FRONT_BOTTOM, FRONT_LOW_TOP, SCROLL, T, Canvas, Sheet, alpha_sheet, backlit, floor_runs,
                   front_x, ground_shadow, haze, layer_width, pits, resample, shade, unmagenta)
import pixelizza as px  # dopo piani, che mette questa cartella nel percorso

## Da questa x della telecamera si vedono i piani della fuga: stanno sotto quelli del cimitero, che
## sfumano mentre GIG scavalca il muro.
CAM_FROM = 3060
## La scena della fuga parte dalla faccia destra del muro del cimitero.
SCENE_X = 3380
## I piani della fuga stanno sotto quelli del cimitero (z -100, -90, -80, 1000).
Z = {"cielo": -105, "medio": -104, "vicino": -103, "davanti": 1001}

ASPHALT = np.array([0.15, 0.16, 0.19])
EARTH = np.array([0.24, 0.12, 0.10])
RAIN = (0.56, 0.60, 0.68)
STEEL = np.array([0.42, 0.44, 0.47])
STEEL_HI = np.array([0.66, 0.68, 0.70])
STEEL_LO = np.array([0.20, 0.21, 0.24])

## Il garage, in celle della mappa: il muro con la porta (300-301), l'interno (302-338), il muro di
## destra (339-340); il tetto alla riga 9, col lucernario alle colonne 318-321.
GARAGE_DOOR = 300
GARAGE_IN = (302, 339)
SKYLIGHT = (318, 322)
ROOF_ROW = 9
## Il ponteggio: il blocco alto (colonne 236-242) col passaggio sotto il tubo (righe 20-22).
SCAFFOLD = (236, 243)
TUBE_ROW = 20


def street_sheet(basi: Path) -> Sheet:
    """Il foglio degli oggetti della strada (e05). Dalla strada in sezione si toglie la bocca dello
    scarico: ripetuta ogni 300 px, si noterebbe."""
    sh = Sheet(basi / "e05_gioco_strada.jpg")
    sh.rgb[650:750, 372:458] = sh.rgb[650:750, 492:578]
    return sh


# --- I piani dello sfondo ---------------------------------------------------------------------

def build_far(basi: Path, cam_to: int) -> tuple[np.ndarray, int]:
    """Il cielo di pioggia sopra i tetti dei Tamburi, il Mar Piccolo e le gru dell'Arsenale."""
    w = layer_width(SCROLL["cielo"][0], cam_to, CAM_FROM)
    base = Image.open(basi / "e01_lontano.jpg")
    h = round(base.height * w / base.width)
    out, _ = px.pixelize(base, (w, h), 28)
    return out, h


MID_K = 0.3


def build_mid(basi: Path, cam_to: int) -> tuple[np.ndarray, int]:
    """Le palazzine di là dalla strada: le due file di Gemini, poi le stesse specchiate (la luce
    della pioggia è piatta, senza ombre, e lo specchio non si nota). Sotto, l'asfalto bagnato.
    Restituisce l'immagine e la y del piede delle palazzine."""
    w = layer_width(SCROLL["medio"][0], cam_to, CAM_FROM)
    rows = []
    for name in ("e02_medio_v1.jpg", "e03_medio_v2.jpg"):
        im = Image.open(basi / name)
        out, _ = px.pixelize(im, (round(im.width * MID_K), round(im.height * MID_K)), 28, key_magenta=True)
        rows.append(out)
    seq = [rows[0], rows[1], rows[0][:, ::-1], rows[1][:, ::-1]]
    rh = max(r.shape[0] for r in rows)
    canvas = np.zeros((rh + 60, w, 4), np.uint8)
    canvas[rh - 6:, :, :3] = (ASPHALT * 255).astype(np.uint8)
    canvas[rh - 6:, :, 3] = 255
    x, i = 0, 0
    while x < w:
        r = seq[i % len(seq)]
        n = min(r.shape[1], w - x)
        m = r[:, :n, 3] > 0
        canvas[rh - r.shape[0]:rh, x:x + n][m] = r[:, :n][m]
        x += r.shape[1] - 2
        i += 1
    return canvas, rh


NEAR_K = 0.28


def build_near(basi: Path, cam_to: int, rng: np.random.Generator) -> tuple[np.ndarray, int]:
    """Il marciapiede di là: auto parcheggiate, l'Ape, lo scooter col telo, lampioni, cassonetti, la
    pensilina, panchine, fioriere e paletti, a caso con un seme fisso. Restituisce l'immagine e la y
    dove posano le cose."""
    sh = Sheet(basi / "e04_vicino_kit.jpg", join=2)
    # Gli oggetti del foglio: 0 e 1 utilitarie, 2 Ape, 3 scooter, 4 lampione, 5 cassonetto e
    # bidoni, 6 pensilina, 7 muretto col cancelletto, 8 cartello, 9 fioriera, 10 panchina,
    # 11-13 paletti.
    kinds = {"auto": [0, 1], "ape": [2], "scooter": [3], "lampione": [4], "cassonetti": [5], "pensilina": [6],
             "muretto": [7], "cartello": [8], "fioriera": [9], "panchina": [10], "paletti": [11]}
    weights = {"auto": 4.0, "ape": 1.0, "scooter": 1.5, "lampione": 2.0, "cassonetti": 1.2, "pensilina": 0.6,
               "muretto": 0.8, "cartello": 0.4, "fioriera": 1.2, "panchina": 1.0, "paletti": 1.0}
    names = list(weights)
    p = np.array([weights[n] for n in names])
    p = p / p.sum()

    def sprite(i: int):
        (b, _) = sh.objects[i]
        rgb, a = sh.piece(b, i)
        col, al = resample(rgb, a, round((b[2] - b[0]) * NEAR_K), round((b[3] - b[1]) * NEAR_K))
        # Dai vetri delle auto si vede il fondo magenta del foglio: diventano grigi, col cielo riflesso.
        return unmagenta(col), al

    spr = {i: sprite(i) for i in range(len(sh.objects))}
    w = layer_width(SCROLL["vicino"][0], cam_to, CAM_FROM)
    base_y = 100
    H = base_y + 60
    cv = Canvas(w, H)
    # Sotto, la strada di là in sezione (asfalto, cordolo, terra): si scopre quando la telecamera sale.
    strada = street_sheet(basi)
    (sb, _) = strada.objects[9]
    crop = (sb[0] + 14, sb[1], sb[2] - 14, sb[3])
    k = 0.15
    tw = round((crop[2] - crop[0]) * k)
    for x in range(0, w, tw):
        cv.put(strada, crop, (crop[0], 584, crop[2], sb[3]), (x, base_y, x + tw, base_y + round((sb[3] - 584) * k)), obj=9)
    yb = base_y + round((sb[3] - 584) * k) - 1
    cv.rgb[yb:] = EARTH * 0.8
    cv.a[yb:] = 1
    x = int(rng.integers(0, 16))
    last = ""
    while x < w:
        kind = str(rng.choice(names, p=p))
        if kind == last and kind in ("pensilina", "ape", "cartello", "muretto"):
            continue
        last = kind
        group = [11, 12, 13] if kind == "paletti" else [int(rng.choice(kinds[kind]))]
        for i in group:
            col, al = spr[i]
            hh, ww = al.shape
            cv.paste(col, al, x, base_y - hh + 2)
            x += ww + (5 if kind == "paletti" else 0)
        x += int(rng.integers(4, 26))
    # Un velo di pioggia: la strada di là è più lontana del campo di gioco.
    cv.rgb = haze(0.14, RAIN)(cv.rgb, None)
    return cv.finish(28), base_y


def build_front(basi: Path, cam_to: int, rng: np.random.Generator) -> tuple[np.ndarray, int]:
    """Il primo piano della strada, dal foglio di ChatGPT: i panni stesi fradici e i cavi in alto,
    dove si cammina e basta (quando la telecamera sale, scendono), fioriere con l'oleandro, paletti ed
    erbacce coi capperi in basso, un lampione e un divieto di sosta alti. Sono più scuri del campo di
    gioco, con un filo di luce grigia sui bordi di sopra: la luce della pioggia viene dall'alto.
    Restituisce l'immagine e la sua altezza."""
    sh = alpha_sheet(basi / "p02_primo_piano_strada.png")
    # Gli oggetti del foglio: 0 panni lunghi, 1 panni dei bambini, 2 cavi con la scatola, 3 fioriera
    # con l'oleandro, 4 piede del lampione, 5 paletto, 6 divieto di sosta, 7 erbacce e capperi.

    def sprite(i: int, scale: float):
        (b, _) = sh.objects[i]
        rgb, a = sh.piece(b, i)
        return resample(rgb, a, round((b[2] - b[0]) * scale), round((b[3] - b[1]) * scale))

    def fx(world_x: float) -> int:
        return front_x(world_x, CAM_FROM)

    w = layer_width(SCROLL["davanti"][0], cam_to, CAM_FROM)
    H = 300
    cv = Canvas(w, H)
    taken = []
    # In alto, appesi: dove GIG corre a terra senza saltare.
    for wx, i, s in ((3540, 1, 0.26), (4630, 2, 0.22), (5830, 0, 0.24)):
        col, al = sprite(i, s)
        cv.paste(col, al, fx(wx) - al.shape[1] // 2, 4)
    # Le cose alte, dove si cammina e basta: passano in un attimo.
    for wx, i, s in ((3620, 4, 0.33), (5930, 6, 0.30)):
        col, al = sprite(i, s)
        hh, ww = al.shape
        x = fx(wx) - ww // 2
        cv.paste(col, al, x, H - hh)
        taken.append((x - 24, x + ww + 24))
    # Le cose basse, a caso (col seme fisso), alte al massimo fino a FRONT_LOW_TOP; niente davanti
    # allo scavo (ne coprirebbero il buco) e nel garage.
    low = {3: 0.17, 5: 0.28, 7: 0.21}
    weights = {3: 3.0, 5: 2.0, 7: 3.0}
    ids = list(low)
    p = np.array([weights[i] for i in ids])
    p = p / p.sum()
    max_h = FRONT_BOTTOM - FRONT_LOW_TOP
    avoid = [(fx(4330), fx(4660)), (fx(5960), w)]
    x = fx(3380)
    while x < w:
        i = int(rng.choice(ids, p=p))
        b = sh.objects[i][0]
        s = min(low[i], max_h / (b[3] - b[1]))
        ww = round((b[2] - b[0]) * s)
        if any(x < t1 and x + ww > t0 for t0, t1 in taken + avoid):
            x += 16
            continue
        col, al = sprite(i, s)
        cv.paste(col, al, x, H - al.shape[0])
        x += ww + int(rng.integers(40, 200))
    backlit(cv, rim=(0.08, 0.09, 0.11), dark_k=0.42, dark_add=(0.012, 0.014, 0.03), rim_left=False)
    return cv.finish(18), H


# --- Il campo di gioco ------------------------------------------------------------------------

def top_profile(sheet: Sheet, obj: int) -> np.ndarray:
    """Per ogni colonna dell'oggetto, la prima riga piena (in px del foglio)."""
    (b, m) = sheet.objects[obj]
    first = np.argmax(m, axis=0).astype(float)
    first[~m.any(axis=0)] = np.nan
    return first + b[1]


def flat_top(sheet: Sheet, obj: int, tol: int = 14) -> tuple[int, int, int]:
    """La parte piatta in cima a un oggetto (un cumulo, un bancale): le colonne la cui cima sta entro
    `tol` px dalla cima tipica del terzo centrale. Restituisce (x0, x1, y) in px del foglio."""
    (b, _) = sheet.objects[obj]
    top = top_profile(sheet, obj)
    n = len(top)
    y = float(np.nanmedian(top[n // 3: 2 * n // 3]))
    flat = np.nonzero(np.abs(top - y) <= tol)[0]
    return b[0] + int(flat.min()), b[0] + int(flat.max()) + 1, round(y)


def smooth_noise(w: int, h: int, cell: int, rng: np.random.Generator) -> np.ndarray:
    gw, gh = w // cell + 3, h // cell + 3
    g = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8))
    big = g.resize((gw * cell, gh * cell), Image.BICUBIC)
    return np.asarray(big, np.float64)[:h, :w] / 255.0


## La parete del garage: la scala del dipinto e dove va il suo primo pezzo (il pannello degli attrezzi
## sopra il banco, colonne 306-309; il manichino finisce dove comincia lo scaffale, colonna 316).
WALL_K = 0.34
WALL_A_X = 6094


def garage_wall(basi: Path, rng: np.random.Generator) -> tuple[np.ndarray, int, int, np.ndarray]:
    """La parete di fondo del garage, dalla colonna 302 alla 338 e dal soffitto al pavimento.

    Il dipinto di Gemini è più piccolo della stanza, se le cose devono avere la misura giusta accanto
    a GIG (il manichino alto come una persona): se ne prendono due pezzi alla scala 0.34, e il resto
    della parete si dipinge qui coi suoi colori (intonaco, macchie d'umido, scaglie, la polvere rossa
    in basso). Dal primo pezzo si tolgono la mensola delle stoffe, che starebbe fra il banco e lo
    scaffale e sembrerebbe una piattaforma, e il quadro della Madonna, che va più a destra, dove lo
    scaffale non lo taglia. La porta del dipinto non si usa: il fascio del lucernario cade sul muro.
    Tutta la parete è più scura e meno satura delle cose su cui si salta.
    Restituisce il colore (0-1), la x e la y del mondo dove va, e il colore della luce del lucernario."""
    x0, x1 = GARAGE_IN[0] * T, GARAGE_IN[1] * T
    y0 = (ROOF_ROW + 1) * T
    W, H = x1 - x0, FLOOR + 4 - y0
    floor_y = FLOOR - y0
    src = np.asarray(Image.open(basi / "e07_garage_interno.jpg").convert("RGB"), np.float64) / 255.0
    src = src.copy()
    # Il marchio di fabbrica sul basamento della macchina da cucire: coperto col nero della ghisa.
    iron = np.median(src[560:600, 340:500].reshape(-1, 3), 0)
    src[518:552, 372:480] = np.minimum(src[518:552, 372:480], iron + 0.02)
    K = WALL_K
    TOP, BOTTOM = 45, 632  # il soffitto e il pavimento del dipinto

    # L'intonaco: il colore di un tratto liscio del dipinto, macchie d'umido più scure, scaglie di
    # vernice più chiare e la polvere rossa che sale dal pavimento.
    base = np.median(src[60:170, 600:700].reshape(-1, 3), 0)
    wall = np.ones((H, W, 3)) * base
    damp = np.clip((smooth_noise(W, H, 26, rng) - 0.55) * 4, 0, 1)
    wall *= (1 - 0.24 * damp)[..., None]
    peel = smooth_noise(W, H, 7, rng) > 0.8
    wall[peel] = wall[peel] * 1.12 + 0.02
    dust = np.clip((np.arange(H)[:, None, None] - (floor_y - 46)) / 46.0, 0, 1)
    wall = wall * (1 - 0.4 * dust) + np.array([0.32, 0.16, 0.12]) * 0.4 * dust
    # La lampada da lavoro (a x 140, y 140 del dipinto) scalda la parete intorno.
    lamp_x, lamp_y = WALL_A_X - x0 + 140 * K, floor_y - (BOTTOM - 140) * K
    gx, gy = np.meshgrid(np.arange(W), np.arange(H))
    glow = np.clip(1 - np.hypot(gx - lamp_x, (gy - lamp_y) * 1.3) / 120.0, 0, 1) ** 1.6
    warm = np.median(src[150:220, 40:120].reshape(-1, 3), 0)
    wall = wall * (1 - 0.75 * glow[..., None]) + warm * 0.75 * glow[..., None]

    def chunk(sx0: int, sx1: int, wx: int, soft: tuple[int, int, int], holes=()) -> None:
        """Le colonne sx0-sx1 del dipinto, col loro pavimento sul pavimento, dalla x del mondo wx.
        `soft`: sfumatura a sinistra, a destra e in cima (px); `holes`: riquadri del dipinto da
        lasciare fuori (sfumati), dove resta l'intonaco."""
        w = round((sx1 - sx0) * K)
        h = round((BOTTOM - TOP) * K)
        im = Image.fromarray((src[TOP:BOTTOM, sx0:sx1] * 255).astype(np.uint8)).resize((w, h), Image.BOX)
        c = np.asarray(im, np.float64) / 255.0
        a = np.ones((h, w))
        ls, rs, ts = soft
        for i in range(ls):
            a[:, i] = np.minimum(a[:, i], (i + 1) / (ls + 1))
        for i in range(rs):
            a[:, w - 1 - i] = np.minimum(a[:, w - 1 - i], (i + 1) / (rs + 1))
        for i in range(ts):
            a[i, :] = np.minimum(a[i, :], (i + 1) / (ts + 1))
        yy, xx = np.mgrid[0:h, 0:w]
        for hx0, hy0, hx1, hy1 in holes:
            X0, X1 = (hx0 - sx0) * K, (hx1 - sx0) * K
            Y0, Y1 = (hy0 - TOP) * K, (hy1 - TOP) * K
            d = np.minimum.reduce([xx - X0, X1 - xx, yy - Y0, Y1 - yy])
            a = np.minimum(a, np.clip(1 - d / 4, 0, 1))
        cx, cy = wx - x0, floor_y - h
        X0, X1 = max(0, cx), min(W, cx + w)
        sub = a[:, X0 - cx:X1 - cx, None]
        wall[cy:cy + h, X0:X1] = wall[cy:cy + h, X0:X1] * (1 - sub) + c[:, X0 - cx:X1 - cx] * sub

    # Il primo pezzo: la lampada e il pannello degli attrezzi sopra il banco, la macchina da cucire e
    # il manichino con la veste bianca; il secondo, i bracci appesi, il tavolo col monitor e gli
    # scatoloni, contro il muro di destra.
    chunk(0, 720, WALL_A_X, (20, 8, 14), holes=[(326, 192, 606, 312), (618, 176, 716, 312)])
    chunk(1000, 1584, x1 - round(584 * K), (12, 0, 14))
    # Il quadro della Madonna col lumino, più a destra, sopra la fine dello scaffale.
    mx0, my0, mx1, my1 = 622, 182, 712, 308
    mw, mh = round((mx1 - mx0) * K), round((my1 - my0) * K)
    pic = np.asarray(Image.fromarray((src[my0:my1, mx0:mx1] * 255).astype(np.uint8)).resize((mw, mh), Image.BOX),
                     np.float64) / 255.0
    px0, py0 = 6496 - x0, 76
    wall[py0:py0 + mh, px0:px0 + mw] = pic
    # Più scura e meno satura: è il fondo.
    grey = wall.mean(-1, keepdims=True)
    wall = (wall * 0.8 + grey * 0.2) * 0.8
    # Il fascio del lucernario, dal soffitto al pavimento, inclinato come la pioggia, con qualche
    # raggio più chiaro.
    lit = np.median(src[90:200, 860:960].reshape(-1, 3), 0)
    s0, s1 = SKYLIGHT[0] * T - x0, SKYLIGHT[1] * T - x0

    def edges(y: float) -> tuple[float, float]:
        t = y / floor_y
        return s0 - 39 * t, s1 - 6.5 * t

    for y in range(floor_y + 3):
        l, r = edges(y)
        k = 0.62 - 0.27 * min(1.0, y / floor_y)
        xs = np.arange(max(0, int(l) - 4), min(W, int(r) + 5))
        a = (np.clip(np.minimum(xs - l, r - xs) / 4 + 0.5, 0, 1) * k)[:, None]
        wall[y, xs] = wall[y, xs] * (1 - a) + lit * a
    for _ in range(9):
        u = 0.1 + 0.8 * rng.random()
        for y in range(floor_y):
            l, r = edges(y)
            if rng.random() < 0.85:
                xr = round(l + u * (r - l))
                wall[y, xr] = np.minimum(wall[y, xr] + 0.05, 1.0)
    # Il filo della lampada fino al soffitto.
    cord_x = round(WALL_A_X - x0 + 138 * K)
    top_chunk = floor_y - round((BOTTOM - TOP) * K)
    wall[0:top_chunk + 6, cord_x] = np.array([0.07, 0.07, 0.08])
    return wall.clip(0, 1), x0, y0, lit


def tuff_texture(ogg: Sheet, height: int) -> tuple[Sheet, tuple[int, int, int, int], float]:
    """Il muro di tufo in sezione (e08, oggetto 4), allungato ripetendo la sua fascia di blocchi finché,
    largo due celle, arriva almeno a `height` px. Restituisce il foglio, il riquadro del muro e la scala."""
    (tb, _) = ogg.objects[4]
    s = 2 * T / (tb[2] - tb[0])
    band = (tb[1] + 4, tb[1] + 194)
    n = max(0, int(np.ceil((height / s - (tb[3] - tb[1])) / (band[1] - band[0]))))
    tall = ogg.heightened([band] * n) if n else ogg
    return tall, (tb[0], tb[1], tb[2], tb[3] + n * (band[1] - band[0])), s


def build_scene(basi: Path, rows: list[str], rng: np.random.Generator) -> np.ndarray:
    """Il campo di gioco della fuga, alla scala del mondo, dalla faccia destra del muro del cimitero
    alla fine del livello."""
    cols = len(rows[0])
    W, H = cols * T - SCENE_X, len(rows) * T + 60
    cv = Canvas(W, H)
    O = SCENE_X

    def box(x0, y0, x1, y1):
        return (x0 - O, y0, x1 - O, y1)

    def fill(x0, y0, x1, y1, color):
        cv.rgb[y0:y1, x0 - O:x1 - O] = color
        cv.a[y0:y1, x0 - O:x1 - O] = 1

    strada = street_sheet(basi)
    telo = Sheet(basi / "e06_ponteggio_telo.jpg")
    ogg = Sheet(basi / "e08_garage_oggetti.jpg")
    vicino = Sheet(basi / "e04_vicino_kit.jpg", join=2)
    # e05: 0 Ape, 1 new jersey, 2 tettoia, 3 cassette, 4 e 5 transenne, 6 macerie, 7 cancello,
    # 8 bancale, 9 la strada in sezione. e08: 0 banco, 1 scaffale, 2 tetto in sezione, 3 lucernario,
    # 4 muro di tufo in sezione, 5 serbatoi, 6 antenna, 7 panni sul tetto, 8 pavimento del garage.
    c_from = SCENE_X // T
    pit = pits(rows, FLOOR // T, GARAGE_DOOR, c_from)[0]
    sx0, sx1 = SCAFFOLD[0] * T, SCAFFOLD[1] * T
    tube_y = TUBE_ROW * T
    roof_y = ROOF_ROW * T

    # --- 1. Il fondo: la parete del garage, il garage chiuso del vicino, il buio sotto il ponteggio
    # e nel vano della porta.
    wall, wx0, wy0, lit = garage_wall(basi, rng)
    wh, ww = wall.shape[:2]
    cv.rgb[wy0:wy0 + wh, wx0 - O:wx0 - O + ww] = wall
    cv.a[wy0:wy0 + wh, wx0 - O:wx0 - O + ww] = 1
    n0, n1 = (GARAGE_IN[1] + 2) * T, (cols - 2) * T
    dark = np.median(wall[20:120, 300:360].reshape(-1, 3), 0) * 0.3
    fill(n0, wy0, n1, FLOOR + 4, dark)
    for bx, by, bw, bh in ((16, 34, 46, 34), (64, 26, 38, 26), (22, 56, 32, 22), (150, 40, 60, 40)):
        fill(n0 + bx, FLOOR - by, n0 + bx + bw, FLOOR - by + bh, dark * 1.7)
        fill(n0 + bx, FLOOR - by, n0 + bx + bw, FLOOR - by + 1, dark * 2.4)
    for y in range(tube_y + 2, FLOOR):
        k = (y - tube_y) / (FLOOR - tube_y)
        fill(sx0 - 2, y, sx1 + 2, y + 1, np.array([0.05, 0.05, 0.08]) + k * np.array([0.08, 0.08, 0.10]))
    door0, door1 = GARAGE_DOOR * T, (GARAGE_DOOR + 2) * T
    fill(door0, 18 * T, door1, FLOOR, np.array([0.10, 0.10, 0.13]))

    # --- 2. Il pavimento: la strada in sezione fino alla porta del garage, con lo scavo; dentro, il
    # cemento con le macchie d'olio.
    (sb, _) = strada.objects[9]
    inner0, inner1 = sb[0] + 14, sb[2] - 14
    feet, tsc = 584, 0.25
    strip_h = round((sb[3] - feet) * tsc)
    for run0, run1 in floor_runs(rows, FLOOR // T, GARAGE_DOOR, c_from):
        x, k = run0, 0
        while x < run1:
            ox = (k * 97) % 60
            w = min(round((inner1 - inner0 - ox) * tsc), run1 - x)
            crop = (inner0 + ox, sb[1], inner0 + ox + round(w / tsc), sb[3])
            _, _, aw, _ = cv.put(strada, crop, (crop[0], feet, crop[2], sb[3]), box(x, FLOOR, x + w, FLOOR + strip_h), obj=9)
            x += max(1, aw)
            k += 1
        fill(run0, FLOOR + strip_h - 1, run1, H, EARTH)
        for edge, dd in ((run0, 1), (run1 - 1, -1)):
            if edge <= SCENE_X or edge >= GARAGE_DOOR * T - 1:
                continue
            for i in range(3):
                cv.rgb[FLOOR - 8:H, edge + dd * i - O] *= 0.45 + 0.15 * i
    (gb, _) = ogg.objects[8]
    g0, g1 = gb[0] + 10, gb[2] - 10
    gfeet, gk = 615, 0.15
    gh = round((gb[3] - gfeet) * gk)
    x, k = GARAGE_DOOR * T, 0
    while x < cols * T:
        ox = (k * 71) % 90
        w = min(round((g1 - g0 - ox) * gk), cols * T - x)
        crop = (g0 + ox, gb[1], g0 + ox + round(w / gk), gb[3])
        _, _, aw, _ = cv.put(ogg, crop, (crop[0], gfeet, crop[2], gb[3]), box(x, FLOOR, x + w, FLOOR + gh), obj=8)
        x += max(1, aw)
        k += 1
    fill(GARAGE_DOOR * T, FLOOR + gh - 1, cols * T, H, EARTH)
    # Lo scavo: la parete di terra in fondo, due tubi tagliati che spuntano dai lati e l'acqua piovana
    # sul fondo. Niente che attraversi il buco: sembrerebbe un appoggio.
    f0, f1 = pit
    fill(f0, FLOOR - 8, f1, FLOOR - 6, np.array([0.30, 0.30, 0.32]))
    for y in range(FLOOR - 6, H):
        k = max(0.0, 1.0 - (y - (FLOOR - 6)) / 34.0)
        fill(f0, y, f1, y + 1, np.array([0.10, 0.06, 0.07]) + k * np.array([0.20, 0.11, 0.08]))
    for a0, a1, cap in ((f0, f0 + 9, f0 + 8), (f1 - 9, f1, f1 - 9)):
        fill(a0, FLOOR + 16, a1, FLOOR + 23, np.array([0.30, 0.31, 0.34]))
        fill(a0, FLOOR + 16, a1, FLOOR + 17, np.array([0.52, 0.54, 0.56]))
        fill(a0, FLOOR + 22, a1, FLOOR + 23, np.array([0.14, 0.14, 0.16]))
        fill(cap, FLOOR + 17, cap + 1, FLOOR + 22, np.array([0.05, 0.05, 0.06]))
    fill(f0, H - 14, f1, H, np.array([0.13, 0.16, 0.22]))
    fill(f0, H - 14, f1, H - 13, np.array([0.50, 0.58, 0.66]))
    rr = np.random.default_rng(f0)
    for _ in range((f1 - f0) // 10):
        xx, yy = int(rr.integers(f0 + 3, f1 - 3)), int(rr.integers(FLOOR, FLOOR + 20))
        fill(xx, yy, xx + 3, yy + 2, np.array([0.36, 0.24, 0.20]))
    # L'ombra del ponteggio sulla strada e la luce del lucernario sul pavimento del garage.
    cv.rgb[FLOOR - 8:FLOOR + 4, sx0 - 2 - O:sx1 + 2 - O] *= 0.5
    l0, l1 = SKYLIGHT[0] * T, SKYLIGHT[1] * T
    patch = cv.rgb[FLOOR - 6:FLOOR + 4, l0 - 36 - O:l1 - 6 - O]
    cv.rgb[FLOOR - 6:FLOOR + 4, l0 - 36 - O:l1 - 6 - O] = patch * 0.6 + lit * 0.4

    # --- 3. Sul fondo della strada, più scure e senza contorno: le transenne ai lati dello scavo e
    # l'Ape parcheggiata davanti al garage, coi piedi un poco più in là di quelli di GIG.
    for i, xa in ((4, f0 - 72), (5, f1 + 8)):
        (b, _) = strada.objects[i]
        bw, bh = round((b[2] - b[0]) * 0.4), round((b[3] - b[1]) * 0.4)
        cv.put(strada, b, b, box(xa, FLOOR - 3 - bh, xa + bw, FLOOR - 3), obj=i, tint=shade(0.78, 0.01))
    (b, _) = strada.objects[0]
    bw, bh = round((b[2] - b[0]) * 0.42), round((b[3] - b[1]) * 0.42)
    cv.put(strada, b, b, box(5640, FLOOR - 4 - bh, 5640 + bw, FLOOR - 4), obj=0, tint=shade(0.72, 0.015))

    # --- 4. Il ponteggio: il telo fino al tubo, dai pali esterni ai bordi del blocco; sotto, il buio
    # fra i pali, il tubo, i pali e le basette sulla riga dei piedi.
    sxs = (sx1 - sx0 + 8) / (720 - 48)
    tarp_top = tube_y - round((968 - 26) * sxs)

    def wet(col, _a):
        """Lo sporco rosso in fondo al telo, visto piccolo, sembra sangue: diventa fango grigio. Il
        telo è bagnato dalla pioggia: più scuro e meno acceso del verde della base."""
        red = np.clip((col[..., 0] - np.maximum(col[..., 1], col[..., 2]) - 0.06) * 5, 0, 1)[..., None]
        grey = col.mean(-1, keepdims=True) * np.array([1.0, 0.97, 0.9])
        col = col * (1 - red) + grey * red
        return ((col * 0.72 + col.mean(-1, keepdims=True) * 0.28) * 0.86).clip(0, 1)

    cv.put(telo, (32, 26, 736, 968), (48, 26, 720, 968), box(sx0 - 4, tarp_top, sx1 + 4, tube_y), obj=0,
           outline=True, ink=True, tint=wet, despill_all=True)
    fill(sx0 - 5, tube_y - 1, sx1 + 5, tube_y + 3, STEEL)
    fill(sx0 - 5, tube_y - 1, sx1 + 5, tube_y, STEEL_HI)
    fill(sx0 - 5, tube_y + 2, sx1 + 5, tube_y + 3, STEEL_LO)
    for xp, c in ((sx0 - 4, STEEL), (sx1 + 1, STEEL), (sx0 + 44, STEEL_LO), (sx1 - 47, STEEL_LO)):
        fill(xp, tube_y + 3, xp + 3, FLOOR, c)
        if c is STEEL:
            fill(xp, tube_y + 3, xp + 1, FLOOR, STEEL_HI)
        fill(xp - 3, FLOOR - 2, xp + 6, FLOOR + 1, STEEL_LO)
    for _ in range(14):
        xx = int(rng.integers(sx0 - 2, sx1 + 2))
        yy = tube_y + 4 + int(rng.integers(0, 10))
        fill(xx, yy, xx + 1, yy + 2, np.array([0.62, 0.72, 0.80]))

    # --- 5. Le cose su cui si sale: la faccia di sopra del disegno sulla riga dove GIG posa i piedi,
    # la base sul pavimento, con l'ombra di contatto sotto. Dove il disegno ha dei vuoti (fra le
    # stecche delle cassette, sotto il banco) si vedeva il magenta del foglio: lì `despill_all`.

    def shadow(x0: float, x1: float) -> None:
        ground_shadow(cv, round(x0) - O, round(x1) - O)

    # Le macerie coi sacchi (colonne 182-186, righe 21-22): la parte piatta in cima su quasi tutto il
    # blocco, un poco allargata (x 0.45, y 0.37); i fianchi scendono fuori dal blocco.
    (b, _) = strada.objects[6]
    fx0, fx1, fy = flat_top(strada, 6)
    mid = (182 * T + 187 * T) / 2
    hw = (fx1 - fx0) * 0.45 / 2
    tx0, tx1 = round(mid - hw), round(mid + hw)
    k = (tx1 - tx0) / (fx1 - fx0)
    shadow(tx0 + (b[0] - fx0) * k + 6, tx0 + (b[2] - fx0) * k - 6)
    cv.put(strada, b, (fx0, fy, fx1, 505), box(tx0, 21 * T, tx1, FLOOR), obj=6,
           outline=True, ink=True)
    # Il bidone verde della differenziata (colonne 196-197, righe 20-22): il coperchio sulla riga 20.
    shadow(196 * T, 198 * T)
    cv.put(vicino, (544, 370, 646, 516), (548, 383, 642, 510), box(196 * T - 2, 20 * T, 198 * T + 2, FLOOR), obj=5,
           outline=True, ink=True)
    # La tettoia del fruttivendolo (riga 18, colonne 206-213): il tetto ondulato, visto un poco
    # dall'alto, ha la riga dei piedi a metà; i pali davanti posano sulla strada.
    (b, _) = strada.objects[2]
    shadow(206 * T, 214 * T)
    cv.put(strada, b, (740, 49, 1080, 250), box(206 * T, 18 * T, 214 * T, FLOOR), obj=2, outline=True, ink=True,
           despill_all=True)
    # Le cassette sotto la tettoia (colonne 208-210, righe 21-22): due pile di due.
    (b, _) = strada.objects[3]
    for crop, top, tx in (((1136, 138, 1204, 252), 140, 208 * T), ((1272, 145, 1349, 252), 147, 208 * T + 30)):
        cv.put(strada, crop, (crop[0], top, crop[2], 250), box(tx, 21 * T, tx + 30, FLOOR), obj=3, outline=True,
               ink=True, despill_all=True)
    # I due bancali coi sacchi di cemento sotto il telo di plastica (colonne 252-256, righe 21-22).
    (b, _) = strada.objects[8]
    fx0, fx1, fy = flat_top(strada, 8, tol=18)
    shadow(252 * T, 257 * T)
    for i, (tx0, tx1) in enumerate(((252 * T, 252 * T + 50), (252 * T + 50, 257 * T))):
        cv.put(strada, b, (fx0, fy, fx1, 515), box(tx0, 21 * T, tx1, FLOOR), obj=8, outline=True, ink=True,
               flip=i == 1, despill_all=True)
    # Il pilastro di tufo (colonne 266-267, righe 17-22), col suo cappello di cemento; e i muri del
    # garage, di tufo come quelli veri dei Tamburi. I muri che arrivano al pavimento hanno in basso
    # l'intonaco rovinato; quello sopra la porta no.
    tuff, tb_t, s_t = tuff_texture(ogg, FLOOR + 2)

    def tuff_wall(x: int, ya: int, yb: int, foot: bool = True) -> None:
        h_src = round((yb - ya) / s_t)
        y_src = tb_t[3] - h_src if foot else tb_t[1]
        crop = (tb_t[0], y_src, tb_t[2], y_src + h_src)
        cv.put(tuff, crop, crop, box(x, ya, x + 2 * T, yb), outline=True, ink=True)

    shadow(266 * T, 268 * T)
    tuff_wall(266 * T, 17 * T + 4, FLOOR + 1)
    concrete = np.array([0.50, 0.50, 0.49])
    fill(266 * T - 2, 17 * T, 268 * T + 2, 17 * T + 5, concrete)
    fill(266 * T - 2, 17 * T, 268 * T + 2, 17 * T + 1, concrete * 1.4)
    fill(266 * T - 2, 17 * T + 4, 268 * T + 2, 17 * T + 5, concrete * 0.56)
    cv.ring[17 * T - 1, 266 * T - 3 - O:268 * T + 3 - O] = True
    cv.ring[17 * T:17 * T + 5, 266 * T - 3 - O] = True
    cv.ring[17 * T:17 * T + 5, 268 * T + 2 - O] = True
    # La pila di cordoli nuovi (colonne 276-280, riga 22): due file di tre.
    shadow(276 * T, 281 * T)
    cv.put(strada, (157, 610, 550, 648), (157, 610, 550, 648), box(276 * T, 22 * T, 281 * T, 22 * T + 10), obj=9,
           outline=True, ink=True)
    cv.put(strada, (556, 610, 952, 648), (556, 610, 952, 648), box(276 * T, 22 * T + 10, 281 * T, FLOOR + 1), obj=9,
           outline=True, ink=True)

    # --- 6. Il garage: i muri, l'architrave e il rullo della saracinesca alzata, il tetto col
    # lucernario e, sopra, le cose del tetto; dentro, il banco e lo scaffale.
    tuff_wall(GARAGE_DOOR * T, (ROOF_ROW + 1) * T - 4, 18 * T - 4, foot=False)
    tuff_wall(GARAGE_IN[1] * T, (ROOF_ROW + 1) * T - 4, FLOOR + 1)
    tuff_wall((cols - 2) * T, 0, FLOOR + 1)
    fill(door0, 18 * T - 5, door1, 18 * T + 1, np.array([0.44, 0.44, 0.45]))
    fill(door0, 18 * T - 5, door1, 18 * T - 4, np.array([0.62, 0.62, 0.62]))
    fill(door1 - 2, 18 * T + 1, door1 + 12, 18 * T + 8, np.array([0.22, 0.23, 0.26]))
    fill(door1 - 2, 18 * T + 1, door1 + 12, 18 * T + 2, np.array([0.36, 0.37, 0.40]))
    # Il tetto in sezione (riga 9), dal muro della porta in fondo, aperto sul lucernario: la riga
    # dei piedi a metà della guaina nera, come per la strada.
    (rb, _) = ogg.objects[2]
    r_in0, r_in1 = rb[0] + 14, rb[2] - 14
    rfeet, rk = 342, 0.25
    rh_below = round((rb[3] - rfeet) * rk)
    for r0, r1 in ((GARAGE_DOOR * T, l0), (l1, cols * T)):
        x, k = r0, 0
        while x < r1:
            ox = (k * 53) % 40
            w = min(round((r_in1 - r_in0 - ox) * rk), r1 - x)
            crop = (r_in0 + ox, rb[1], r_in0 + ox + round(w / rk), rb[3])
            _, _, aw, _ = cv.put(ogg, crop, (crop[0], rfeet, crop[2], rb[3]), box(x, roof_y, x + w, roof_y + rh_below), obj=2)
            x += max(1, aw)
            k += 1
        for i in range(3):
            for xx in (r0 + i, r1 - 1 - i):
                if GARAGE_DOOR * T < xx < cols * T - 1:
                    cv.rgb[roof_y - 11:roof_y + rh_below, xx - O] *= 0.55 + 0.15 * i
    # Il lucernario: i due cordoli e il vetro armato aperto, appoggiato a sinistra.
    curb = np.array([0.46, 0.46, 0.47])
    for cx in (l0 - 7, l1):
        fill(cx, roof_y - 12, cx + 7, roof_y + 2, curb)
        fill(cx, roof_y - 12, cx + 7, roof_y - 11, curb * 1.35)
        cv.ring[roof_y - 13, cx - 1 - O:cx + 8 - O] = True
        cv.ring[roof_y - 12:roof_y, cx - 1 - O] = True
        cv.ring[roof_y - 12:roof_y, cx + 7 - O] = True
    # Il vetro, visto un poco dall'alto: un telaio di ferro largo quanto il cordolo, inclinato
    # all'indietro, col vetro armato dentro (la rete di fili) e un riflesso; sotto, l'asta che lo tiene.
    hx, hy = l0 - 7, roof_y - 12

    def shape(draw) -> np.ndarray:
        im = Image.new("L", (64, 72), 0)
        draw(ImageDraw.Draw(im), lambda x, y: (x - (hx - 48), y - (hy - 66)))
        return np.asarray(im) > 0

    frame = shape(lambda d, p: d.polygon([p(hx - 16, hy), p(hx + 2, hy), p(hx - 20, hy - 58), p(hx - 38, hy - 58)], fill=255))
    glass = shape(lambda d, p: d.polygon([p(hx - 13, hy - 3), p(hx - 1, hy - 3), p(hx - 21, hy - 55), p(hx - 33, hy - 55)],
                                          fill=255))
    wires = shape(lambda d, p: [d.line([p(hx - 13 + i, hy - 3), p(hx - 33 + i, hy - 55)], fill=255) for i in range(3, 12, 4)]
                  + [d.line([p(hx - 40, y), p(hx + 4, y)], fill=255) for y in range(hy - 9, hy - 54, -7)])
    shine = shape(lambda d, p: d.line([p(hx - 6, hy - 8), p(hx - 21, hy - 46)], fill=255))
    rod = shape(lambda d, p: d.line([p(hx - 18, hy), p(hx - 24, hy - 26)], fill=255))
    gx0, gy0 = hx - 48 - O, hy - 66
    sub_rgb = cv.rgb[gy0:gy0 + 72, gx0:gx0 + 64]
    sub_a = cv.a[gy0:gy0 + 72, gx0:gx0 + 64]
    sub_rgb[rod & ~frame] = np.array([0.25, 0.26, 0.28])
    sub_rgb[frame] = np.array([0.59, 0.59, 0.57])
    sub_rgb[glass] = np.array([0.47, 0.57, 0.63])
    sub_rgb[glass & wires] = np.array([0.40, 0.48, 0.54])
    sub_rgb[glass & shine] = np.array([0.80, 0.87, 0.90])
    sub_a[frame | rod] = 1
    on = frame | rod
    pad = np.pad(on, 1)
    around = (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]) & ~on
    cv.ring[gy0:gy0 + 72, gx0:gx0 + 64] |= around
    # Sul tetto, un poco più in là di GIG: i serbatoi neri, l'antenna con la parabola e i panni.
    for i, xa, s in ((5, GARAGE_DOOR * T + 46, 0.38), (6, 311 * T + 4, 0.38), (7, 324 * T + 6, 0.44)):
        (b, _) = ogg.objects[i]
        bw, bh = round((b[2] - b[0]) * s), round((b[3] - b[1]) * s)
        cv.put(ogg, b, b, box(xa, roof_y - 6 - bh, xa + bw, roof_y - 6), obj=i, outline=True, tint=shade(0.82, 0.01))
    # Il banco di GIG (colonne 306-309, righe 21-22): il piano, visto un poco dall'alto, con la riga
    # dei piedi a metà. Lo scaffale (riga 18, colonne 316-323): la tavola sulla riga 18.
    (b, _) = ogg.objects[0]
    shadow(306 * T - 2, 310 * T + 2)
    cv.put(ogg, b, (50, 80, 360, 212), box(306 * T - 2, 21 * T, 310 * T + 2, FLOOR), obj=0, outline=True, ink=True,
           despill_all=True)
    (b, _) = ogg.objects[1]
    sh_h = round((b[3] - b[1]) * 8 * T / (b[2] - b[0]))
    cv.put(ogg, b, b, box(316 * T, 18 * T, 324 * T, 18 * T + sh_h), obj=1, outline=True, ink=True,
           despill_all=True)
    return cv.finish(64)
