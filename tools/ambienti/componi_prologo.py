# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Il prologo, dal cimitero di San Brunone al garage per i Tamburi: i piani del gioco dalle basi
dipinte con l'AI e dalla mappa.

Le basi sono fogli di Gemini su fondo magenta e di ChatGPT su fondo trasparente (vedi il README):
qui ogni oggetto si ritaglia, si porta alla scala del gioco e si appoggia sui blocchi di
game/data/platform/prologo.txt, così quello che si vede coincide con quello su cui si salta. Per
ogni oggetto si dice quale parte del disegno (l'"àncora", in pixel del foglio) va sul blocco: per
esempio il cornicione di una tomba va sulla riga dove GIG appoggia i piedi. Il cimitero sta qui, la
fuga e il garage in fuga.py, gli strumenti comuni in piani.py.

Escono in game/assets/env/prologo/:
- cielo.png, medio.png, vicino.png: i piani dello sfondo del cimitero, con la parallasse (cielo con
  torre e cupole, cappelle e muro di cinta, lapidi e angeli);
- scena.png: il campo di gioco del cimitero dietro GIG (terreno e oggetti sui blocchi), alla scala
  del mondo, fino alla faccia destra del muro di cinta;
- davanti.png: il primo piano del cimitero davanti a GIG, in controluce;
- gli stessi col nome che finisce in "_fuga", per la fuga e il garage;
- layers.json: posizioni, velocità e tratti dei piani. Mentre GIG scavalca il muro di cinta, i piani
  del cimitero sfumano uno dopo l'altro, dal più lontano al più vicino, sopra quelli della fuga.

Uso:

    python -I tools/ambienti/componi_prologo.py [--basi CARTELLA] [--uscita CARTELLA] [--anteprima CARTELLA]

Con --anteprima escono anche alcune schermate di prova con GIG, composte come nel gioco; con --uscita
i piani si scrivono in un'altra cartella invece che nel gioco.
Il codice è MIT, come il resto del gioco; le basi non stanno nel repo.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from piani import (FLOOR, FRONT_BOTTOM, FRONT_LOW_TOP, ROOT, SCROLL, T, VIEW_H, VIEW_W, Canvas, Sheet,  # noqa: E402
                   alpha_sheet, backlit, cells, contact_sheet, floor_runs, front_x, ground_shadow, haze, layer_width,
                   put_tufts, settle, tuft_stamps,
                   pits, read_map, resample, screenshot, shade)
import pixelizza as px  # noqa: E402  (dopo piani, che mette questa cartella nel percorso)
from ritaglia_kit import cut_kit  # noqa: E402
import fuga  # noqa: E402

MAP = ROOT / "game/data/platform/prologo.txt"
OUT = ROOT / "game/assets/env/prologo"

## Il cimitero finisce col muro di cinta (colonne 166-168): la sua scena arriva alla faccia destra del
## muro, dove comincia quella della fuga.
CEM_SCENE_END = fuga.SCENE_X
## Mentre GIG scavalca il muro i piani del cimitero sfumano, dal più lontano al più vicino: ognuno
## sparisce del tutto a questa x della telecamera, dopo una dissolvenza di FADE px. Sotto ci sono già
## i piani della fuga, che si vedono da fuga.CAM_FROM.
CEM_LAYER_END = {"cielo": 3160, "medio": 3210, "vicino": 3260, "davanti": 3260}
FADE = 100
assert fuga.CAM_FROM <= CEM_LAYER_END["cielo"] - FADE


# --- I piani dello sfondo ---------------------------------------------------------------------

def ground_strip(basi: Path, scale: float, width: int, depth: int, k_haze: float = 0.0) -> np.ndarray:
    """Il viale in sezione (lo stesso del campo di gioco) alla scala di un piano lontano, ripetuto
    per `width` px, con la terra scura che continua sotto fino a `depth` px: quando la telecamera sale,
    i piani scendono meno del campo di gioco e sotto le loro cose deve esserci terreno."""
    sh = Sheet(basi / "c06_gioco_terreno_muro.jpg")
    sh.clean_top(0)
    (tb, _) = sh.objects[0]
    crop = (tb[0] + 14, 106, tb[2] - 14, tb[3])
    rgb, a = sh.piece(crop, 0)
    w = round((crop[2] - crop[0]) * scale)
    h = round((crop[3] - crop[1]) * scale)
    col, al = resample(rgb, a, w, h)
    out = np.zeros((depth, width, 4), np.uint8)
    earth = np.array([0.22, 0.12, 0.10])
    tile = np.zeros((h, w, 3))
    tile[:] = earth
    tile[al > 0] = col[al > 0]
    for x in range(0, width, w):
        n = min(w, width - x)
        hh = min(h, depth)
        out[:hh, x:x + n, :3] = (haze(k_haze)(tile[:hh, :n], None) * 255).astype(np.uint8)
    out[h:, :, :3] = (haze(k_haze)(earth[None, None, :], None) * 255).astype(np.uint8)
    out[..., 3] = 255
    return out


def cem_width(name: str) -> int:
    """La larghezza di un piano del cimitero: fino a dove sparisce."""
    return layer_width(SCROLL[name][0], CEM_LAYER_END[name])


def build_far(basi: Path) -> tuple[np.ndarray, int]:
    """Cielo, torre di SIDERA e cupole sopra gli altiforni: un'immagine sola, quasi ferma."""
    w = cem_width("cielo")
    # v3: la torre rossa (decisione 7) e gli schermi bianchi, non più menta; la v2 resta se manca la v3
    nome = "c01_lontano_v3_torre_rossa.png"
    base = Image.open(basi / (nome if (basi / nome).exists() else "c01_lontano_v2.jpg")).convert("RGB")
    h = round(base.height * w / base.width)
    out, _ = px.pixelize(base, (w, h), 28)
    # gli schermi della torre: anche nella v3 tirano al menta; li porto a un bianco caldo
    rgb = out[..., :3].astype(int)
    menta = (rgb[..., 1] > rgb[..., 0] + 6) & (rgb[..., 1] > 180)
    out[menta, :3] = (250, 244, 230)
    return out, h


def build_mid(basi: Path) -> np.ndarray:
    """Le cappelle col muro di cinta, tre file di Gemini una dopo l'altra. Hanno una palette sola: con
    una per fila, alle giunte il muro cambiava colore. La terza fila comincia dopo il pino che il
    bordo dell'immagine di Gemini taglia a metà, e sopra ogni giunta il cipresso più alto della prima
    fila la nasconde."""
    w = cem_width("medio")
    names = ("c02_medio_v1.jpg", "c03_medio_v2.jpg", "c10_medio_v3.jpg")
    first_x = {"c10_medio_v3.jpg": 69}
    labs = []
    for name in names:
        out, _ = px.pixelize(Image.open(basi / name), (396, 168), 256, key_magenta=True, clean_passes=0)
        labs.append(px.to_oklab(out[..., :3].astype(np.float64) / 255)[out[..., 3] > 0])
    pal = px.kmeans_palette(np.concatenate(labs), 32, seed=1)
    rows = [px.pixelize(Image.open(basi / name), (396, 168), 32, key_magenta=True, palette=pal)[0][:, first_x.get(name, 0):]
            for name in names]
    canvas = np.zeros((168 + 40, w, 4), np.uint8)
    canvas[164:] = ground_strip(basi, 0.08, w, 168 + 40 - 164, 0.1)
    x, i, joints = 0, 0, []
    while x < w:
        r = rows[i % len(rows)]
        n = min(r.shape[1], w - x)
        m = r[:, :n, 3] > 0
        canvas[:168, x:x + n][m] = r[:, :n][m]
        if x > 0:
            joints.append(x)
        x += r.shape[1] - 2
        i += 1
    # Il cipresso (colonne 7-25 della prima fila, con la cima a y 24): sopra il muro tutto quello che è
    # pieno, davanti al muro solo i pixel scuri e verdi, cioè l'albero e non il muro rosa.
    tree_rgba = rows[0][:, 7:26]
    lab = px.to_oklab(tree_rgba[..., :3].astype(np.float64) / 255)
    tree = (tree_rgba[..., 3] > 0) & ((np.arange(168)[:, None] < 70) | ((lab[..., 0] < 0.45) & (lab[..., 1] < 0.02)))
    tree[146:] = False
    tree = ndimage.binary_fill_holes(tree)
    for j in joints:
        x0 = j - tree_rgba.shape[1] // 2
        part = canvas[:168, x0:x0 + tree_rgba.shape[1]]
        m = tree[:, :part.shape[1]]
        part[m] = tree_rgba[:, :part.shape[1]][m]
    return canvas


def build_near(basi: Path, rng: np.random.Generator) -> tuple[np.ndarray, int]:
    """Lapidi, croci, angeli, lampioni e fontanelle fra le tombe, su una fila: oggetti del kit
    messi a caso (con un seme fisso), alla scala del piano."""
    items = cut_kit(Image.open(basi / "c04_vicino_kit.jpg"), 0.21, 40)
    spr = [Image.fromarray(it["rgba"], "RGBA") for it in items]
    # Lapidi e croci spesso, angeli e lampioni ogni tanto, fontanelle della bonifica poche volte.
    kinds = {
        "lapide": [3, 4, 5, 6, 7], "croce": [10], "angelo": [8, 9], "vaso": [11, 12],
        "lumini": [13], "fontanella": [14], "lampione": [16], "siepe": [17],
    }
    weights = {"lapide": 10, "croce": 3, "angelo": 1.5, "vaso": 2, "lumini": 2, "fontanella": 0.8,
               "lampione": 0.8, "siepe": 2.5}
    names = list(weights)
    p = np.array([weights[n] for n in names])
    p = p / p.sum()
    w = cem_width("vicino")
    base_y = 144
    H = base_y + 120
    canvas = Image.new("RGBA", (w, H), (0, 0, 0, 0))
    # Sotto la fila, un altro viale più lontano: quando la telecamera sale lo si vede scoprirsi.
    strip = ground_strip(basi, 0.15, w, H - base_y + 4)
    canvas.alpha_composite(Image.fromarray(strip, "RGBA"), (0, base_y - 4))
    x = int(rng.integers(0, 20))
    last = ""
    while x < w:
        k = str(rng.choice(names, p=p))
        if k == last and k in ("angelo", "lampione", "fontanella"):
            continue
        last = k
        s = spr[int(rng.choice(kinds[k]))]
        y = base_y - s.height + int(rng.integers(0, 3))
        canvas.alpha_composite(s, (x, y))
        x += s.width + int(rng.integers(2, 22))
    out = np.asarray(canvas).copy()
    # Un velo di foschia: le tombe di dietro stanno più lontano del campo di gioco.
    rgb = out[..., :3].astype(np.float64) / 255
    rgb = haze(0.12)(rgb, None)
    out[..., :3] = (rgb * 255 + 0.5).astype(np.uint8)
    return out, base_y


def build_front(kit: Path, rng: np.random.Generator) -> tuple[np.ndarray, int]:
    """Il primo piano, davanti a GIG, dal foglio di ChatGPT: siepi, erba col finocchio selvatico,
    lumini, ringhiere e vasi bassi lungo il bordo di sotto, e pochi cipressi o colonne alti dove non
    si salta. Sono in controluce: scuri, con un filo di luce calda a sinistra (il sole velato sta in
    alto a sinistra); i lumini restano accesi. Restituisce l'immagine e la sua altezza."""
    sh = alpha_sheet(kit)
    # Gli oggetti del foglio: 0 cipresso grande, 1 cipresso sottile, 2 siepe, 3 erba e finocchio,
    # 4 ringhiera, 5 davanzale coi lumini, 6 colonna spezzata con l'edera, 7 vaso di ghisa.
    def sprite(i: int, scale: float):
        (b, _) = sh.objects[i]
        rgb, a = sh.piece(b, i)
        return resample(rgb, a, round((b[2] - b[0]) * scale), round((b[3] - b[1]) * scale))

    w = cem_width("davanti")
    H = 300
    cv = Canvas(w, H)

    def place(i: int, scale: float, x: int) -> int:
        col, al = sprite(i, scale)
        h, ww = al.shape
        cv.paste(col, al, x, H - h)
        return ww

    # Le cose alte, nei punti dove si cammina e basta: la ringhiera a sinistra della partenza, la
    # colonna prima della tomba monumentale, un cipresso davanti alla galleria. Poche e strette,
    # perché GIG non sparisca dietro: passano in un attimo. Niente vicino alla partenza e alla tomba
    # di Mimmo, alle tombe dove si salta, alle fosse, al ponteggio e all'arena.
    tall = [(60, 4, 0.36), (1410, 6, 0.3), (2290, 0, 0.4)]
    taken = []
    for wx, i, s in tall:
        ww = round((sh.objects[i][0][2] - sh.objects[i][0][0]) * s)
        x = front_x(wx) - ww // 2
        place(i, s, x)
        taken.append((x - 24, x + ww + 24))
    # Le cose basse, a caso (con il seme fisso), alte al massimo fino a FRONT_LOW_TOP.
    low = {2: 0.30, 3: 0.15, 5: 0.24, 4: 0.20, 7: 0.14}
    weights = {2: 3.0, 3: 4.0, 5: 2.0, 4: 1.5, 7: 1.0}
    ids = list(low)
    p = np.array([weights[i] for i in ids])
    p = p / p.sum()
    max_h = FRONT_BOTTOM - FRONT_LOW_TOP
    # Fuori dalle fosse (con un margine: lontano dal centro dello schermo il primo piano scivola).
    avoid = [(front_x(840), front_x(1380)), (front_x(2800), w)]
    x = front_x(-40)
    while x < w:
        i = int(rng.choice(ids, p=p))
        b = sh.objects[i][0]
        s = min(low[i], max_h / (b[3] - b[1]))
        ww = round((b[2] - b[0]) * s)
        if any(x < t1 and x + ww > t0 for t0, t1 in taken + avoid):
            x += 16
            continue
        place(i, s, x)
        x += ww + int(rng.integers(30, 190))
    # Controluce: tutto scuro e un poco freddo, i lumini accesi, un filo di luce calda a sinistra.
    backlit(cv, lamp=lambda rgb: (rgb.mean(-1) > 0.72) & (rgb[..., 0] > 0.8) & (rgb[..., 2] < 0.8))
    return cv.finish(18), H


# --- Il campo di gioco ------------------------------------------------------------------------

def build_scene(basi: Path, rows: list[str]) -> np.ndarray:
    """Il campo di gioco del cimitero, dal bordo sinistro del livello alla faccia destra del muro di
    cinta (più una colonna, per il contorno del muro): di là comincia la scena della fuga.

    Tre strati, in quest'ordine: quello che sta dietro il viale (il muro dei loculi della galleria, i
    cumuli, il ponteggio crollato), il viale con le fosse, e le cose del piano di GIG, con la base
    sulla riga dei piedi dentro la ghiaia e l'ombra di contatto sotto."""
    W = CEM_SCENE_END + 1
    H = len(rows) * T + 60
    cv = Canvas(W, H)
    tombe = Sheet(basi / "c05_gioco_tombe.jpg")
    terra = Sheet(basi / "c06_gioco_terreno_muro.jpg")
    gall = Sheet(basi / "c07_gioco_galleria.jpg")
    pont = Sheet(basi / "c08_gioco_ponteggio.jpg")

    # --- 1. Dietro il viale.
    # Il muro dei loculi della galleria (colonne 92-124), in ombra: si ripete un pezzo di cinque file
    # di lastre (il passo del foglio è 86 px) preso dentro la cornice, così le giunte non si vedono.
    # Comincia e finisce dietro le colonne d'angolo.
    g0, g1 = 92 * T, 125 * T
    tile = (826, 31, 1256, 376)
    tw = round((tile[2] - tile[0]) * 0.5)
    x = g0 + 12
    while x < g1 - 12:
        w = min(tw, g1 - 12 - x)
        crop = (tile[0], tile[1], tile[0] + round(w / 0.5), tile[3])
        cv.put(gall, crop, crop, (x, 14 * T, x + w, FLOOR + 4), obj=1, tint=shade(0.42, 0.03))
        x += w
    # Le fosse: due cumuli di terra con la pala, fra una fossa e l'altra, con la base sul bordo della
    # ghiaia, così si vedono anche le tavole ai loro piedi.
    db = tombe.objects[5][0]
    s = 0.15
    dw, dh = round((db[2] - db[0]) * s), round((db[3] - db[1]) * s)
    for x in (51 * T + 30, 64 * T + 26):
        cv.put(tombe, db, db, (x, FLOOR - 4 - dh, x + dw, FLOOR - 4), obj=5, tint=shade(0.85))
    # Il ponteggio crollato (colonne 130-136, righe 6-19) col cunicolo sotto (righe 20-22). Il mucchio
    # di macerie del disegno è più basso del cunicolo: si allunga di una fila di mattoni (la fascia
    # 690-731 del foglio) finché tocca la ghiaia.
    tall = pont.heightened([(690, 731)])
    cv.put(tall, tall.objects[0][0], (543, 38, 843, 650), (130 * T - 2, 6 * T, 137 * T + 2, 20 * T), obj=0,
           outline=True, despill_all=True)
    # Il cunicolo: buio dentro, una tavola caduta sopra.
    x0, x1 = 130 * T, 137 * T
    for y in range(20 * T, FLOOR + 4):
        k = (y - 20 * T) / (FLOOR + 4 - 20 * T)
        cv.rgb[y, x0:x1] = np.array([0.07, 0.05, 0.06]) + k * np.array([0.13, 0.08, 0.07])
    cv.a[20 * T:FLOOR + 4, x0:x1] = 1
    cv.ring[20 * T:FLOOR, x0:x1] = False
    (pb, _) = gall.objects[2]
    cv.put(gall, pb, (pb[0], pb[1], pb[2], pb[1] + 54), (x0 - 10, 20 * T - 6, x1 + 10, 20 * T + 4), obj=2, outline=True)

    # --- 2. Il terreno: il viale in sezione, ripetuto sotto il pavimento, con i bordi delle fosse.
    terra.clean_top(0)
    (tb, _) = terra.objects[0]
    tsc = 0.25
    feet = 137  # nel foglio: metà della fascia di ghiaia
    inner0, inner1 = tb[0] + 14, tb[2] - 14  # senza il contorno dei due capi
    strip_h = round((tb[3] - feet) * tsc)
    for run0, run1 in floor_runs(rows, FLOOR // T, CEM_SCENE_END // T):
        x = run0
        k = 0
        while x < run1:
            ox = (k * 97) % 60
            w = min(round((inner1 - inner0 - ox) * tsc), run1 - x)
            crop = (inner0 + ox, tb[1], inner0 + ox + round(w / tsc), tb[3])
            _, _, aw, _ = cv.put(terra, crop, (crop[0], feet, crop[2], tb[3]), (x, FLOOR, x + w, FLOOR + strip_h),
                                 obj=0)
            x += max(1, aw)
            k += 1
        # Il bordo del viale: la prima riga della ghiaia un po' più scura, perché si legga. Le cose
        # del piano di GIG non ci sono ancora, quindi si scurisce solo la ghiaia.
        for xx in range(run0, run1):
            nz = np.nonzero(cv.a[FLOOR - 14:FLOOR + 4, xx])[0]
            if len(nz):
                cv.rgb[FLOOR - 14 + nz[0], xx] *= 0.72
        # Sotto la striscia, la terra continua scura fino in fondo.
        yb = FLOOR + strip_h - 1
        cv.rgb[yb:H, run0:run1] = np.array([0.22, 0.12, 0.10])
        cv.a[yb:H, run0:run1] = 1
        # Le pareti delle fosse: dove il pavimento finisce, la terra tagliata in ombra. Dove finisce
        # la scena il viale continua in quella della fuga.
        for edge, d in ((run0, 1), (run1 - 1, -1)):
            if edge <= 0 or edge >= CEM_SCENE_END - 1:
                continue
            for i in range(3):
                xx = edge + d * i
                cv.rgb[FLOOR - 2:H, xx] *= 0.45 + 0.15 * i
    # Dentro le fosse: la parete di fondo, dal bordo della ghiaia, terra che scende nel buio.
    for f0, f1 in pits(rows, FLOOR // T, CEM_SCENE_END // T):
        top = FLOOR - 6
        for y in range(top, H):
            k = max(0.0, 1.0 - (y - top) / 36.0)
            cv.rgb[y, f0:f1] = np.array([0.10, 0.06, 0.07]) + k * np.array([0.20, 0.11, 0.08])
        cv.rgb[top, f0:f1] *= 0.7
        cv.a[top:H, f0:f1] = 1
        # Qualche sasso e una radice sulla parete.
        rr = np.random.default_rng(f0)
        for _ in range((f1 - f0) // 10):
            xx, yy = int(rr.integers(f0 + 3, f1 - 3)), int(rr.integers(FLOOR, FLOOR + 22))
            cv.rgb[yy:yy + 2, xx:xx + 3] = np.array([0.36, 0.24, 0.20])

    # --- 3. Il piano di GIG: sopra il viale, con l'ultima riga (contorno compreso) a y 460-461.
    # Ogni cosa posata sul viale ha l'ombra di contatto sotto e attorno; alla fine, sopra tutto, le
    # sue ultime righe si scuriscono e qualche ciuffo della ghiaia le passa davanti (`stand`).
    # I ciuffi si prendono dal primo tratto del viale, dove dietro non c'è niente.
    stamps = tuft_stamps(cv, FLOOR - 20, FLOOR + 12, 0, 46 * T)
    feet: list[tuple[int, int, int]] = []

    def stand(x0: int, x1: int, bottom: int = FLOOR) -> None:
        ground_shadow(cv, x0, x1)
        feet.append((x0, x1, bottom))

    # Il pilastro dei loculi a sinistra (colonne 0-1, righe 4-22): uno solo, allungato di sei passi di
    # lastre e lampade (la fascia 206-324 del foglio), e 4 px oltre il bordo, perché il fusto arrivi a 0.
    lp = terra.heightened([(206, 324)] * 6)
    io, b = next((i, bb) for i, (bb, _) in enumerate(lp.objects) if bb[0] == 1192)
    stand(0, 2 * T)
    cv.put(lp, b, b, (-4, 4 * T, 2 * T, FLOOR), obj=io, outline=True, ink=True)

    # La galleria a colonnato: le colonne, le tavole davanti, sopra la trabeazione che è il tetto
    # (righe 12-13). Agli estremi le colonne d'angolo del foglio, che non hanno dietro il fondo scuro
    # del colonnato; il loro capitello sta sotto la fine del fregio.
    col_a, col_b, col_d = (48, 112, 115, 374), (255, 112, 322, 374), (671, 112, 738, 374)
    cw = round(67 * 0.5)
    first, last = g0 + 7, g1 - 7 - cw
    for i in range(5):
        cx = first + round(i * (last - first) / 4)
        c = col_a if i == 0 else col_d if i == 4 else col_b
        stand(cx + 2, cx + cw - 2, FLOOR + 1)
        cv.put(gall, c, c, (cx, 14 * T, cx + cw, FLOOR + 1), obj=0)
    # Le tavole del restauro, righe 18 (colonne 98-104) e 15 (colonne 108-114), sulle mensole fissate
    # al muro, davanti alle colonne: quello su cui si sale si vede tutto.
    for (c0, r) in ((98, 18), (108, 15)):
        cv.put(gall, pb, (pb[0], pb[1] + 4, pb[2], pb[1] + 58), (c0 * T, r * T - 1, (c0 + 7) * T, r * T + 8), obj=2,
               outline=True, ink=True)
    # La trabeazione: i due capi e il pezzo di mezzo ripetuto (senza `ink`, che segnerebbe le giunte).
    left, right = (34, 28, 62, 112), (734, 28, 762, 112)
    mid_crop = (62, 28, 734, 112)
    ends_w = round(28 * 0.5)
    cv.put(gall, left, left, (g0, 12 * T, g0 + ends_w, 14 * T), obj=0, outline=True)
    cv.put(gall, right, right, (g1 - ends_w, 12 * T, g1, 14 * T), obj=0, outline=True)
    x = g0 + ends_w
    mw = round((mid_crop[2] - mid_crop[0]) * 0.5)
    while x < g1 - ends_w:
        w = min(mw, g1 - ends_w - x)
        crop = (mid_crop[0], mid_crop[1], mid_crop[0] + round(w / 0.5), mid_crop[3])
        cv.put(gall, crop, crop, (x, 12 * T, x + w, 14 * T), obj=0, outline=True)
        x += w

    # Le tombe sui loro blocchi. Àncora: dalla metà della faccia di sopra alla base. La tomba di
    # Mimmo (colonne 4-8, righe 21-22), con la lapide e il bicchierino a destra; la tomba vecchia con
    # la croce (colonne 20-23), la tomba quadrata con la corona (29-31, righe 20-22), la lastra sul
    # gradino (37-39, riga 22). Nel foglio il plinto ha il fianco sinistro in prospettiva, più profondo
    # della ghiaia: lo si porta a terra dalla riga dove comincia lo smusso (`square_base`).
    for obj, anchor, block, bevel in ((0, (80, 155, 453, 295), (4, 21, 8, 22), 249),
                                      (1, (493, 141, 849, 295), (20, 21, 23, 22), 249),
                                      (2, (889, 150, 1044, 295), (29, 20, 31, 22), 264),
                                      (3, (1078, 214, 1333, 295), (37, 22, 39, 22), 252)):
        tombe.square_base(obj, bevel)
        target = cells(*block)
        stand(target[0], target[2])
        cv.put(tombe, tombe.objects[obj][0], anchor, target, obj=obj, outline=True, ink=True)
    # La tomba monumentale (colonne 74-88, righe 16-22), dal suo foglio: il cornicione va sulla riga
    # dove si cammina, i gradini sul pavimento. È alta sette blocchi, perché GIG appeso al cornicione
    # (la sporgenza con una mano) abbia i piedi sopra la ghiaia. La facciata ha due campate in più, una
    # per lato (dalla seconda alla terza colonna e dalla sesta alla settima), e tre fasce in più in
    # altezza, senza righe orizzontali: fra la targa e la porta (380-404) e fra la maniglia e le basi
    # delle colonne (556-588, due volte). Così entra nel blocco allungata solo di un decimo. Il plinto
    # (colonne 78-83, righe 14-15) va a parte, sul suo blocco.
    mon = Sheet(basi / "c09_tomba_monumentale.jpg")
    tall_mon = mon.widened([(268, 398), (1010, 1139)]).heightened([(380, 404), (556, 588), (556, 588)])
    base_y = 745 + 24 + 32 + 32
    stand(74 * T - 5, 89 * T + 5)
    cv.put(tall_mon, (26, 170, 1641, base_y), (54, 170, 1613, base_y), cells(74, 16, 88, 22), outline=True, ink=True)
    cv.put(mon, (476, 26, 932, 170), (476, 26, 932, 170), cells(78, 14, 83, 15), outline=True, ink=True)

    # Il cancello laterale col Redentore, dove si combatte, e il muro di cinta (colonne 166-168). Nel
    # foglio il pilastro è intero (x 462-594), poi ci sono il vuoto dei cardini e la cancellata
    # (594-912). Lo stesso pilastro sta a sinistra della cancellata e sul blocco del muro, specchiato
    # coi cardini verso la cancellata, tutti alla stessa scala: il cappello (y 440 del foglio) sulla
    # cima del muro (340), la base (fino a 737) sulla riga dei piedi. La cancellata entra di 3 px
    # sotto il pilastro del muro.
    gb = terra.objects[2][0]
    pil_crop, pil_anchor = (462, gb[1], 594, gb[3]), (462, 440, 594, 737)
    sx = 3 * T / (594 - 462)
    gate_w = round((912 - 594) * sx)
    gx1 = 166 * T + 3
    gx0 = gx1 - gate_w
    lx1 = gx0 + 3
    lx0 = lx1 - 3 * T
    rb = terra.objects[3][0]
    rs = 0.4
    rw, rh = round((rb[2] - rb[0]) * rs), round((rb[3] - rb[1]) * rs)
    rx = lx0 - rw - 24
    stand(rx + 18, rx + rw - 18, FLOOR + 2)
    cv.put(terra, rb, rb, (rx, FLOOR - rh + 2, rx + rw, FLOOR + 2), obj=3, outline=True, ink=True)
    stand(gx0, gx1, FLOOR + 2)
    cv.put(terra, (594, gb[1], 912, gb[3]), (594, 440, 912, 737), (gx0, 17 * T, gx1, FLOOR + 2), obj=2,
           tint=shade(0.8), despill_all=True)
    stand(lx0, lx1, FLOOR + 2)
    cv.put(terra, pil_crop, pil_anchor, (lx0, 17 * T, lx1, FLOOR + 2), obj=2, outline=True, ink=True)
    stand(166 * T, 169 * T, FLOOR + 2)
    cv.put(terra, pil_crop, pil_anchor, (166 * T, 17 * T, 169 * T, FLOOR + 2), obj=2, outline=True, ink=True, flip=True)

    # Sopra tutto: le basi più scure verso terra e i ciuffi davanti.
    rng = np.random.default_rng(11)
    for x0, x1, bottom in feet:
        settle(cv, x0, x1, bottom)
        put_tufts(cv, stamps, x0, x1, rng)
    return cv.finish(48)


# --- Tutto il prologo -------------------------------------------------------------------------

def build_all(basi: Path, rows: list[str]) -> tuple[list[dict], list[dict], dict[str, np.ndarray]]:
    """I piani del cimitero e della fuga, come voci di layers.json con l'immagine in "im", le scene del
    campo di gioco e le loro immagini."""
    level_w = len(rows[0]) * T
    cam_ref_y = len(rows) * T - VIEW_H
    cam_to = level_w - VIEW_W
    floor_screen = FLOOR - cam_ref_y

    far, far_h = build_far(basi)
    mid = build_mid(basi)
    near, near_base = build_near(basi, np.random.default_rng(2087))
    front, front_h = build_front(basi / "p01_primo_piano_kit.png", np.random.default_rng(1871))
    f_far, f_far_h = fuga.build_far(basi, cam_to)
    f_mid, f_mid_base = fuga.build_mid(basi, cam_to)
    f_near, f_near_base = fuga.build_near(basi, cam_to, np.random.default_rng(2087))
    f_front, f_front_h = fuga.build_front(basi, cam_to, np.random.default_rng(1871))

    # Dove stanno sullo schermo con GIG a terra. Nel cimitero le cupole spuntano sopra il muro delle
    # cappelle, le cappelle finiscono dietro le tombe vicine, le tombe vicine dietro il viale; nella
    # fuga le palazzine e il marciapiede di là posano sulla strada. Il primo piano sta davanti a
    # tutto, anche agli attori dell'arena (z fino a 100 + 2 y).
    cem = [("cielo", far, -round(far_h * 0.27), -100), ("medio", mid, floor_screen - 6 - 168, -90),
           ("vicino", near, floor_screen - 5 - near_base, -80), ("davanti", front, FRONT_BOTTOM - front_h, 1000)]
    esc = [("cielo", f_far, -round(f_far_h * 0.27)), ("medio", f_mid, floor_screen - 6 - f_mid_base),
           ("vicino", f_near, floor_screen - 5 - f_near_base), ("davanti", f_front, FRONT_BOTTOM - f_front_h)]
    layers = []
    for name, im, y, z in cem:
        layers.append({"name": name, "image": f"{name}.png", "scroll": SCROLL[name][0], "scroll_y": SCROLL[name][1],
                       "y": y, "z": z, "x_to": CEM_LAYER_END[name], "fade_out": FADE, "im": im})
    for name, im, y in esc:
        layers.append({"name": f"{name}_fuga", "image": f"{name}_fuga.png", "scroll": SCROLL[name][0],
                       "scroll_y": SCROLL[name][1], "y": y, "z": fuga.Z[name], "x_from": fuga.CAM_FROM,
                       "origin_x": fuga.CAM_FROM, "im": im})
    scenes = [{"image": "scena.png", "x": 0, "y": 0}, {"image": "scena_fuga.png", "x": fuga.SCENE_X, "y": 0}]
    images = {"scena.png": build_scene(basi, rows),
              "scena_fuga.png": fuga.build_scene(basi, rows, np.random.default_rng(64))}
    return layers, scenes, images


# --- Anteprima --------------------------------------------------------------------------------

## GIG nelle schermate di prova (x, y dei piedi): nel cimitero (la partenza, le tombe, le fosse, la
## tomba monumentale, la galleria, il ponteggio crollato, l'arena), sul muro di cinta mentre i piani
## cambiano, poi nella fuga e nel garage fino al tetto.
SHOTS = [(230, 460), (330, 460), (900, 460), (1500, 320), (2000, 460), (2600, 460), (2900, 460), (3100, 460),
         (3250, 460), (3350, 340), (3420, 460), (3520, 460), (3690, 420), (4200, 360), (4790, 460), (5340, 340),
         (6160, 420), (6400, 360), (6600, 180), (6700, 180)]


def preview(layers: list[dict], scenes: list[dict], images: dict[str, np.ndarray], rows: list[str],
            dest: Path) -> None:
    """Le schermate di prova, a gruppi di otto, con la telecamera come nel gioco."""
    level_w = len(rows[0]) * T
    cam_ref_y = len(rows) * T - VIEW_H
    shown = [dict(l, im=Image.fromarray(l["im"], "RGBA")) for l in layers]
    parts = [(Image.fromarray(images[s["image"]], "RGBA"), s["x"], s["y"]) for s in scenes]
    tiles = []
    for gx, gy in SHOTS:
        cx = min(max(gx + 45 - 240, 0), level_w - VIEW_W)
        cy = min(max(gy - 188, -80), cam_ref_y)
        tiles.append(screenshot(shown, parts, cam_ref_y, cx, cy, (gx, gy)))
    dest.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(tiles), 8):
        contact_sheet(tiles[i:i + 8], dest / f"schermate_{i // 8 + 1}.png")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--basi", default=str(ROOT / "tools/out/ambienti/basi"))
    ap.add_argument("--uscita", default=str(OUT))
    ap.add_argument("--anteprima", default="")
    a = ap.parse_args()
    basi, out = Path(a.basi), Path(a.uscita)
    rows = read_map(MAP)
    layers, scenes, images = build_all(basi, rows)
    out.mkdir(parents=True, exist_ok=True)
    for l in layers:
        Image.fromarray(l["im"], "RGBA").save(out / l["image"])
    for name, im in images.items():
        Image.fromarray(im, "RGBA").save(out / name)
    data = {
        "format": 1,
        "level_width": len(rows[0]) * T,
        "cam_ref_y": len(rows) * T - VIEW_H,  # la telecamera con GIG a terra, contro il fondo della mappa
        "layers": [{k: v for k, v in l.items() if k != "im"} for l in layers],
        "scenes": scenes,
    }
    (out / "layers.json").write_text(json.dumps(data, indent=2) + "\n", "utf-8")
    print("piani in", out)
    if a.anteprima:
        preview(layers, scenes, images, rows, Path(a.anteprima))
        print("anteprima in", a.anteprima)


if __name__ == "__main__":
    main()
