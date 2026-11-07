# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - cielo e piano lontano di "Sotto la Linea": Taranto, la notte del Wind Day.

Il capitolo 2 è la sera del 17 aprile 2087, fra le 20:40 e le 21:40, in un Wind Day: il maestrale alza la
polvere rossa dei parchi minerali, il cielo è un soffitto basso di polvere color ruggine acceso da sotto
dall'arancio della città, senza stelle né luna (la luna piena sta sopra la polvere). Dal parcheggio della
partenza, fra i palazzi, si vede l'area a caldo a ovest-nord-ovest: le cupole sui parchi minerali, la
galleria dei nastri, le collinette e, a sinistra, la torre rossa di SIDERA, che buca la polvere.

Le basi sono due immagini di ChatGPT, ridipinte di notte dalla nostra base del prologo (c01); gli originali e
i prompt stanno nella cartella privata condivisa (ambienti-ai/sotto-la-linea), non nel repo:
- l01_lontano_notte_v1.png: il cielo, ridotto in pixel art e stirato in larghezza (si vede solo dalle finestre
  fra i palazzi, righe 8-91 dello schermo);
- l01_skyline_magenta_v1.png: lo stesso skyline su fondo magenta; se ne ritagliano torre, collinette con la
  galleria e cupole, rimontati in modo che la torre cada nella finestra della partenza e le cupole in quella
  dell'arena. La cima della torre si scioglie nella polvere con un retino.

Il piano mid (i palazzi) per ora resta quello di warped.py.

  python -I tools/env/taranto.py [--basi CARTELLA] [--uscita CARTELLA]
Scrive sky.png, far.png, far_emis.png (+ _x3) e taranto_info.json.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ambienti"))
import envlib as E  # noqa: E402
import pixelizza as px  # noqa: E402

BASI = os.path.join(os.path.dirname(E.ROOT), "ctrlaltrevenge-lab-condiviso", "ambienti-ai", "sotto-la-linea")
SKY_BASE = "l01_lontano_notte_v1.png"
SKYLINE_BASE = "l01_skyline_magenta_v1.png"

FAR_Y = E.px(26)                       # 33: come prima
FAR_W = int(E.SCREEN_W + (E.LEVEL_W - E.SCREEN_W) * 0.125)   # 720
FAR_H = int(E.OY) - FAR_Y              # 155
GROUND = 57                            # riga del piano lontano dove poggiano torre e cupole (schermo 90)
SKYLINE_SCALE = 0.105                  # collinette, galleria e cupole lontane
TOWER_SCALE = 0.125                    # la torre: alta ~82 px, gli schermi a ~12 px dalla cima del piano
NEAR_DOMES_SCALE = 0.17                # le cupole della finestra dell'arena
FADE = 14                              # righe del retino in cima al piano lontano
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16 + 1 / 32

# Dal foglio magenta (1926x817), in pixel del foglio: i pezzi da rimontare.
CUT = {
    "torre": (120, 380),
    "collina": (380, 930),           # collinette, tetti lontani e galleria dei nastri
    "cupole": (930, 1926),
}
SHEET_GROUND = 706                     # riga del foglio dove poggia tutto (sotto c'è la foschia)


# --- Cielo -----------------------------------------------------------------------------------------
def build_sky(basi):
    """Il soffitto di polvere: dalla notte di ChatGPT, la parte a destra della torre, sopra le cupole. I fumi
    delle giunture delle cupole (in basso a destra) si coprono con la media della riga presa a sinistra."""
    im = Image.open(os.path.join(basi, SKY_BASE)).convert("RGB")
    a = np.asarray(im, np.float32)
    W, H = im.size
    x0, x1, y1 = int(W * 0.20), W, int(H * 0.53)
    crop = a[:y1, x0:x1].copy()
    # i fumi stanno a destra di ~62% della larghezza, sotto ~35% dell'altezza: righe uniformi
    sx, sy = int(W * 0.62) - x0, int(H * 0.33)
    clean = crop[sy:, :sx]
    crop[sy:, sx:] = np.median(clean, axis=1, keepdims=True)
    # la parte bassa resta più calda vicino all'orizzonte: la si porta in 95 righe, poi l'ultima si ripete
    rows = 96
    small = Image.fromarray(crop.clip(0, 255).astype(np.uint8)).resize((E.SCREEN_W, rows), Image.BOX)
    out, _ = px.pixelize(small, (E.SCREEN_W, rows), 14, denoise=0, clean_passes=2)
    sky = np.concatenate([out, np.repeat(out[-1:], E.SCREEN_H - rows, 0)], 0)
    return sky


# --- Piano lontano -----------------------------------------------------------------------------------
def build_far(basi):
    """Il piano lontano, alla larghezza della parallasse (720). I pezzi hanno scale diverse: la torre è
    grande perché è alta 400 m e deve bucare la polvere, con gli schermi a metà della finestra della
    partenza; le cupole della finestra dell'arena sono più vicine, così se ne vede la parte alta sopra la
    ringhiera; il resto (collinette, galleria, cupole lontane) è piccolo."""
    im = Image.open(os.path.join(basi, SKYLINE_BASE)).convert("RGB")
    W, H = im.size
    _, pal = px.pixelize(im, (round(W * SKYLINE_SCALE), round(H * SKYLINE_SCALE)), 26, key_magenta=True)
    sheets = {}

    def piece(name, scale, flip=False):
        if scale not in sheets:
            sheets[scale], _ = px.pixelize(im, (round(W * scale), round(H * scale)), 26, key_magenta=True,
                                           palette=pal)
        sh = sheets[scale]
        a, b = CUT[name]
        p = sh[:round(SHEET_GROUND * scale), round(a * scale):round(b * scale)]
        return p[:, ::-1] if flip else p

    far = np.zeros((FAR_H, FAR_W, 4), np.uint8)
    # la foschia in fondo al foglio: una striscia continua che si ripete, presa sotto la collina
    piece("collina", SKYLINE_SCALE)
    sh = sheets[SKYLINE_SCALE]
    g = round(SHEET_GROUND * SKYLINE_SCALE)
    a, b = CUT["collina"]
    haze = sh[g:, round(a * SKYLINE_SCALE):round(b * SKYLINE_SCALE)]
    for x in range(0, FAR_W, haze.shape[1]):
        n = min(haze.shape[1], FAR_W - x)
        far[GROUND:GROUND + haze.shape[0], x:x + n] = haze[:, :n]
    far[GROUND + haze.shape[0]:] = far[GROUND + haze.shape[0] - 1]
    far[GROUND + haze.shape[0]:, :, 3] = 255

    def put(p, x):
        _paste(far, p, x, GROUND - p.shape[0])
        return x + p.shape[1]

    S0 = SKYLINE_SCALE
    # il fusto della torre è dello stesso rosso del cielo: lo si scurisce verso il prugna (controluce), le luci no
    torre = piece("torre", TOWER_SCALE).copy()
    dark = (torre[..., 3] > 0) & ~_lit(torre)
    t = torre[..., :3].astype(np.float32)
    t[dark] = t[dark] * np.array([0.62, 0.55, 0.72], np.float32) + np.array([6, 2, 14], np.float32)
    torre[..., :3] = t.clip(0, 255).astype(np.uint8)
    # da sinistra: collinette e cupole lontane, la torre con il centro a x 190 (finestra della partenza),
    # collinette e galleria, poi le cupole vicine della finestra dell'arena (x 390-650), e in fondo ancora
    # collinette e cupole lontane
    x0 = 190 - torre.shape[1] // 2
    xl = x0 - piece("collina", S0).shape[1]
    put(piece("collina", S0, True), xl)
    put(piece("cupole", S0, True), xl - piece("cupole", S0).shape[1])
    x = put(piece("collina", S0), x0 + torre.shape[1])
    x = put(piece("collina", S0, True), x)
    xd = max(x, 380)
    x = put(piece("cupole", NEAR_DOMES_SCALE), xd)
    steam(far, [xd + round((x - xd) * f) for f in (0.22, 0.47, 0.66, 0.9)])
    x = put(piece("collina", S0), x)
    while x < FAR_W:
        x = put(piece("cupole", S0, True), x)
        x = put(piece("collina", S0), x)
    put(torre, x0)
    # la cima della torre entra nella polvere: un retino che la svuota verso l'alto
    for r in range(FADE):
        keep = (r + 0.5) / FADE
        thr = BAYER4[r % 4][np.arange(FAR_W) % 4]
        far[r, thr > keep, 3] = 0
    far[far[..., 3] == 0, :3] = 0
    return far, x0 + torre.shape[1] // 2


def steam(far, xs, height=14):
    """Il vapore di bonifica che esce dalle giunture delle cupole (decisione 6): fili chiari a retino, larghi
    1-2 px, che salgono piegando a sinistra col maestrale e si diradano verso l'alto."""
    col = np.array(E.hx("#c09284"), np.uint8)
    hi = np.array(E.hx("#dcb4a2"), np.uint8)
    for i, x0 in enumerate(xs):
        top = np.nonzero(far[:, x0, 3] > 0)[0]
        if not len(top):
            continue
        y0 = top[0]
        for k in range(height):
            y = y0 - 1 - k
            x = x0 - (k + i) // 4
            dens = 1 - k / height
            for dx in (0, 1) if k < height // 2 else (0,):
                if 0 <= y and 0 <= x + dx < far.shape[1] and BAYER4[y % 4][(x + dx) % 4] < dens * 0.9:
                    far[y, x + dx, :3] = hi if dx == 0 and k < 4 else col
                    far[y, x + dx, 3] = 255


def emissive(far, tower_cx):
    """Le luci: segnali rossi, schermi bianchi, finestre e fari arancio. Si prendono i pixel accesi e saturi
    o molto chiari. Sopra la torre, dove la cima sparisce, la polvere è accesa dalla terrazza (ARIA+ Alta
    Quota): un alone rosso-arancio a retino, più fitto in basso."""
    lit = _lit(far)
    em = np.zeros_like(far)
    em[lit] = far[lit]
    em[lit, 3] = 255
    glow = np.array(E.hx("#a8401c"), np.float32)
    for r in range(FADE + 4):
        for dx in range(-14, 15):
            x = tower_cx + dx
            d = ((dx / 14) ** 2 + ((r - FADE * 0.6) / (FADE * 0.9)) ** 2) ** 0.5
            k = max(0.0, 1 - d)
            if k > 0 and em[r, x, 3] == 0 and BAYER4[r % 4][x % 4] < k * 0.8:
                em[r, x, :3] = (glow * (0.35 + 0.4 * k)).astype(np.uint8)
                em[r, x, 3] = 255
    return em


def _lit(a):
    """I pixel accesi: chiari e saturi (segnali, fari, finestre) o quasi bianchi (schermi)."""
    rgb = a[..., :3].astype(np.float32) / 255
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-3)
    return (a[..., 3] > 0) & (((mx > 0.62) & (sat > 0.45)) | (mn > 0.72))


def _paste(dst, src, x, y):
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    m = s[..., 3] > 0
    dst[y0:y1, x0:x1][m] = s[m]


def dim(a, k):
    out = a.copy()
    out[..., :3] = (out[..., :3].astype(np.float32) * k).astype(np.uint8)
    return out


def build(basi=BASI, out_dir=None):
    out_dir = out_dir or os.path.join(E.OUT, "layers")
    os.makedirs(out_dir, exist_ok=True)
    sky = build_sky(basi)
    far, tower_cx = build_far(basi)
    E.save_rgba(os.path.join(out_dir, "sky.png"), sky, 3)
    E.save_rgba(os.path.join(out_dir, "far.png"), far, 3)
    E.save_rgba(os.path.join(out_dir, "far_emis.png"), dim(emissive(far, tower_cx), 0.6), 0)
    info = dict(sky=dict(y=0, w=sky.shape[1], h=sky.shape[0]), far=dict(y=FAR_Y, w=far.shape[1], h=far.shape[0]))
    json.dump(info, open(os.path.join(out_dir, "taranto_info.json"), "w"), indent=1)
    print("[taranto]", info)
    return info


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--basi", default=BASI)
    ap.add_argument("--uscita", default=None)
    a = ap.parse_args()
    build(a.basi, a.uscita)
