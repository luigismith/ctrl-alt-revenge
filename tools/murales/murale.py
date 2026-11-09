# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Le vignette dei murales di Totò: dalla base dipinta (ChatGPT) alla pixel art dei filmati.

  python -I tools/murales/murale.py CONFIG.json [--uscita DIR] [--anteprime DIR]

Ogni vignetta ha un file di configurazione, privato, accanto alla sua base nella cartella condivisa
(ctrlaltrevenge-lab-condiviso/murales/<capitolo>/<id>.json): le basi e i loro prompt non vanno nel repo.
Le immagini del gioco escono in game/assets/murales/<capitolo>/<id>/.

Il formato (deciso il 7 novembre 2026):
  - la vignetta è 512x288, in 16:9 come lo schermo (480x270) ma con 32x18 px di margine: la telecamera
    ci scorre sopra piano mentre scorrono le battute; per i dettagli il lettore delle scene usa lo zoom
    intero (2x), così i pixel restano quadrati;
  - per le panoramiche la vignetta può essere larga (fino a 960x288): si dice in "misura";
  - pixel della stessa misura degli sfondi, 48 colori per vignetta, niente retinatura; il contorno scuro e il
    rosa dei neon sono quelli dei primi piani.

I passi:
  1. ritaglio della base al rapporto della vignetta ("ritaglio": [x0, y0, x1, y1] in pixel della base,
     altrimenti al centro);
  2. riduzione con tools/ambienti/pixelizza.py (media d'area, k-medie in OKLab, pulizia dei pixel soli);
  3. l'inchiostro: i colori più scuri della tavolozza diventano il viola-nero dei contorni dei murales;
  4. le luci (murale_emis.png): i neon rosa, le lampade e gli schermi, da sommare per farli pulsare;
  5. le scritte, fatte con tools/env/pixfont.py e mai dall'AI: tag a spray con colature, insegne, cartelli;
  6. l'ordine dello spray (murale_rivela.png): in grigio, quando compare ogni pixel se la vignetta si dipinge
     davanti a noi (0 = subito, 255 = per ultimo), per un passaggio morbido dal gioco al murale;
  7. murale.json: misure, livelli, scorrimento consigliato, fonte per i crediti.

La configurazione:
  {
    "id": "p01_notte", "capitolo": "prologo",
    "base": "p01_notte_v1.png",                    relativo al file di configurazione
    "misura": [512, 288], "colori": 48, "ritaglio": null,
    "scorri": {"da": [0, 9], "a": [32, 9]},        il riquadro 480x270 all'inizio e alla fine
    "camera": {...},                               facoltativo: la regia consigliata, copiata così com'è nel json
    "inchiostro": "#1e1028",                       facoltativo: il colore dei contorni
    "luci": {"soglia": 0.80, "rosa": true, "rosa_tinta": [330, 18], "zone": [[x, y, w, h], ...]},
    "scritte": [{"testo": "REVENGE", "x": 40, "y": 30, "font": "5x7", "scala": 2, "colore": "#e8463a",
                 "contorno": "#1e1028", "colature": 3, "luce": false, "pendenza": 0.2},   pendenza: px in giù
                                                   per px a destra, per i cartelloni in prospettiva (facoltativa)
                {"testo": "RIGA 1", "x": 24, "y": 176, "strato": "registro_1"}],   con "strato": a parte, la fa
                                                   comparire il motore (scritta_<strato>.png, elencata nel json)
    "pupilla": {"centro": [x, y], "raggio": r},    facoltativo: dove il motore mette il logo ARIA+ nell'occhio
    "ritinta": [{"da": [180, 250], "a": 300, "croma": 0.6}],
    "figure": [{"nome": "toto", "base": "mp02_toto_v1.png", "altezza": 120, "x": 300, "y": 150,
                "colori": 24, "profondita": 1.0, "visibile": true,
                "finestra": [x0, y0, x1, y1]}],            facoltativo: la figura si vede solo dentro quel riquadro
                                                   della vignetta (un vano, una finestra); "taglia_y" taglia solo sotto
                "tavolozza_da": "sprite.png", "tavolozza_dist": 0.14,   facoltativi: la figura prende i colori
                                                   di quel PNG (lo sprite del gioco su trasparente), perché sfumi
                                                   nello sprite senza cambiare tinta
                "volto": {"blink": [[x, y, w, h, "#colore"], ...], "talk": [...]}}],   facoltativo, per i primi
                                                   piani che parlano: palpebre chiuse e bocca aperta, pennellate nostre
                                                   in pixel della figura col contorno -> figura_<nome>_blink.png, _talk
    "davanti": [{"nome": "alberi", "dopo": "perdoni", "righe": [y0, y1], "finestre": [[x0, x1], ...]}],
                                                   facoltativo: alberi o pali della vignetta che stanno davanti a
                                                   una figura che scorre; escono come figura ferma subito dopo "dopo"
    "fonte": "ChatGPT (OpenAI), da nostri render e schizzi; ridotto in pixel art dai nostri script"
  }
Le figure (dipinte su verde #00FF00) escono come strati a parte, figura_<nome>.png, con la posizione nel json:
il motore le anima e le fa scorrere in parallasse; nelle anteprime e nella rivelazione sono già al loro posto.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "ambienti"))
sys.path.insert(0, str(ROOT / "tools" / "env"))
import pixelizza as px  # noqa: E402
import pixfont as PF  # noqa: E402

SCHERMO = (480, 270)
INCHIOSTRO = (0x1E, 0x10, 0x28)     # il contorno dei murales (viola quasi nero)
INK_L = 0.20                         # sotto questa luminosità OKLab un colore è inchiostro
ROSA_NEON = (0xFF, 0x3D, 0xA8)
OUT = ROOT / "game" / "assets" / "murales"
PREVIEW = ROOT / "tools" / "out" / "murales"


def over(dst: np.ndarray, src: np.ndarray, x: int, y: int) -> None:
    """Incolla src (RGBA, alfa 0/255) su dst, tagliando ai bordi."""
    H, W = dst.shape[:2]
    h, w = src.shape[:2]
    sx0, sy0 = max(0, -x), max(0, -y)
    dx0, dy0 = max(0, x), max(0, y)
    dx1, dy1 = min(W, x + w), min(H, y + h)
    if dx1 <= dx0 or dy1 <= dy0:
        return
    s = src[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0]
    m = s[..., 3] > 0
    dst[dy0:dy1, dx0:dx1][m] = s[m]


def hexrgb(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def ritaglia(img: Image.Image, misura: tuple[int, int], box) -> Image.Image:
    if box:
        return img.crop(tuple(box))
    W, H = img.size
    r = misura[0] / misura[1]
    if W / H > r:
        w = int(round(H * r))
        x0 = (W - w) // 2
        return img.crop((x0, 0, x0 + w, H))
    h = int(round(W / r))
    y0 = (H - h) // 2
    return img.crop((0, y0, W, y0 + h))


def inchiostro(rgba: np.ndarray, pal_lab: np.ndarray, ink=INCHIOSTRO) -> np.ndarray:
    """I colori della tavolozza più scuri di INK_L diventano un solo inchiostro, quello dei murales (nelle
    vignette tutte calde si può scaldare: "inchiostro" nella configurazione)."""
    pal_rgb = (px.from_oklab(pal_lab) * 255 + 0.5).clip(0, 255).astype(np.uint8)
    dark = [tuple(c) for c, lab in zip(pal_rgb, pal_lab) if lab[0] < INK_L]
    out = rgba.copy()
    for c in dark:
        m = np.all(out[..., :3] == c, -1)
        out[m, :3] = ink
    return out


def luci(rgba: np.ndarray, cfg: dict) -> np.ndarray:
    """Le parti che si accendono: neon rosa, colori molto chiari e saturi, zone date a mano."""
    rgb = rgba[..., :3].astype(np.float64) / 255
    lab = px.to_oklab(rgb)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    chroma = np.hypot(a, b)
    on = (L > cfg.get("soglia", 0.80)) & (chroma > 0.06)
    if cfg.get("rosa", True):
        # il rosa dei neon: tinta OKLab fra 330 e 18 gradi (i rossi della nube stanno sopra i 25)
        h0, h1 = cfg.get("rosa_tinta", [330, 18])
        hue = np.degrees(np.arctan2(b, a)) % 360
        on |= (chroma > 0.16) & ((hue > h0) | (hue < h1)) & (L > 0.48)
    for x, y, w, h in cfg.get("zone", []):
        z = np.zeros_like(on)
        z[y:y + h, x:x + w] = True
        on |= z & (L > 0.45)
    emis = np.zeros_like(rgba)
    emis[on, :3] = (rgba[on, :3] * 0.6).astype(np.uint8)
    emis[on, 3] = 255
    return emis


# segni che al 5x7 di pixfont mancano (la barra e la virgola delle date e dei registri): li aggiungiamo qui
FONT5x7 = dict(PF.FONT5x7, **{"/": ["..#", "..#", ".#.", ".#.", ".#.", "#..", "#.."],
                              ",": ["..", "..", "..", "..", "..", ".#", "#."]})
ACCENTI = {"À": ("A", -1), "È": ("E", -1), "É": ("E", 1), "Ì": ("I", -1), "Ò": ("O", -1), "Ù": ("U", -1)}


def accenti_alti(testo: str, font: dict) -> tuple[np.ndarray, int]:
    """Il testo a scala 1 con le maiuscole accentate alte come le altre e l'accento sopra la riga (nel 5x7 di
    pixfont l'accento sta dentro la cella e schiaccia la lettera: la Ì sembra una i). Rende anche quante righe
    sono state aggiunte in alto."""
    if font is not FONT5x7 or not any(c in ACCENTI for c in testo):
        return PF.render(testo, font, 1, 1), 0
    base = "".join(ACCENTI.get(c, (c, 0))[0] for c in testo)
    m = PF.render(base, font, 1, 1)
    top = np.zeros((3, m.shape[1]), bool)
    x = 0
    for c, b in zip(testo, base):
        gw = PF.glyph(b, font).shape[1]
        if c in ACCENTI:
            cx, verso = x + gw // 2, ACCENTI[c][1]
            top[0, cx + verso] = top[1, cx] = True     # grave: da in alto a sinistra; acuto: da destra
        x += gw + 1
    return np.vstack([top, m]), 3


def scritta(img: np.ndarray, emis: np.ndarray, s: dict, rng: np.random.Generator) -> None:
    """Una scritta di pixfont: contorno di 1 px, colature a spray dal fondo delle lettere."""
    font = PF.FONT3x5 if s.get("font") == "3x5" else FONT5x7
    scala = int(s.get("scala", 1))
    m, su = accenti_alti(s["testo"], font)
    m = np.kron(m, np.ones((scala, scala), bool)) if scala > 1 else m
    h, w = m.shape
    s = dict(s, y=int(s["y"]) - su * scala, x=int(s["cx"]) - w // 2 if "cx" in s else s["x"])
    pad = 1 + 10
    F = np.zeros((h + 2 * pad, w + 2 * pad), bool)
    F[pad:pad + h, pad:pad + w] = m
    n = int(s.get("colature", 0))
    if n:
        bottom = np.nonzero(F[pad + h - 1] & ~F[pad + h])[0]
        for x in rng.choice(bottom, size=min(n, len(bottom)), replace=False) if len(bottom) else []:
            L = int(rng.integers(2, 8))
            F[pad + h:pad + h + L, x] = True
            F[pad + h + L, x] = True
    p = float(s.get("pendenza", 0))
    lo = 0
    if p:
        # un cartellone in prospettiva: ogni colonna scende di p px per px verso destra, a gradini di pixel
        dy = np.round(p * (np.arange(F.shape[1]) - pad)).astype(int)
        lo = min(0, int(dy.min()))
        G = np.zeros((F.shape[0] + int(dy.max()) - lo, F.shape[1]), bool)
        for x in range(F.shape[1]):
            G[dy[x] - lo:dy[x] - lo + F.shape[0], x] = F[:, x]
        F = G
    O = ndimage.binary_dilation(F, np.ones((3, 3), bool)) & ~F
    x0, y0 = int(s["x"]) - pad, int(s["y"]) - pad + lo   # lo: il gradino in su della pendenza
    H, W = img.shape[:2]
    for mask, col in ((O, s.get("contorno", "#1e1028")), (F, s.get("colore", "#f3e2b8"))):
        if col is None:
            continue
        ys, xs = np.nonzero(mask)
        ys, xs = ys + y0, xs + x0
        ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
        img[ys[ok], xs[ok], :3] = hexrgb(col)
        if s.get("luce") and mask is F:
            emis[ys[ok], xs[ok], :3] = (np.array(hexrgb(col)) * 0.6).astype(np.uint8)
            emis[ys[ok], xs[ok], 3] = 255


def chiave_verde(rgb: np.ndarray) -> np.ndarray:
    """Quanto un pixel è fondo verde (0-1): verde puro e saturo, con un margine morbido per i bordi."""
    f = rgb.astype(np.float64)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    dom = g - np.maximum(r, b)
    return np.clip((dom - 60) / 60, 0, 1) * (g > 110)


def ritinta(im: Image.Image, regole: list) -> Image.Image:
    """Sposta le tinte che non vanno (per esempio il cyan, vietato nel prologo) prima della riduzione.
    Ogni regola: {"da": [h0, h1] gradi OKLab, "a": h, "croma": fattore, "chiaro": delta L,
    "zona": [x0, y0, x1, y1] in pixel della base, prima del ritaglio (facoltativa),
    "scuro": L, con la zona: tocca solo la macchia più grande della zona più scura di L (facoltativo), "chiudi": px,
    "luce_min": L, tocca solo i pixel più chiari di L (facoltativo)}."""
    lab = px.to_oklab(np.asarray(im).astype(np.float64) / 255)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    h = np.degrees(np.arctan2(b, a)) % 360
    c = np.hypot(a, b)
    for r in regole:
        h0, h1 = r["da"]
        m = ((h >= h0) & (h <= h1)) if h0 <= h1 else ((h >= h0) | (h <= h1))
        m &= c > float(r.get("croma_min", 0.02))
        if r.get("luce_min"):
            m &= L > float(r["luce_min"])   # solo i toni chiari (il bianco del purificatore, non il muro dietro)
        if r.get("zona"):
            x0, y0, x1, y1 = r["zona"]
            z = np.zeros_like(m)
            z[y0:y1, x0:x1] = True
            m &= z
        if r.get("scuro") and r.get("zona"):
            # solo la macchia scura più grande della zona (per esempio una manica su uno sfondo chiaro),
            # chiusa e riempita perché prenda anche i suoi riflessi
            k = z & (L < float(r["scuro"]))
            k = ndimage.binary_opening(k, iterations=2)
            lbl, n = ndimage.label(k)
            if n:
                k = lbl == 1 + int(np.argmax(ndimage.sum(k, lbl, range(1, n + 1))))
                k = ndimage.binary_fill_holes(ndimage.binary_closing(k, iterations=int(r.get("chiudi", 12)))) & z
                m &= k
        nh = np.radians(float(r["a"]))
        nc = c * float(r.get("croma", 1.0))
        a = np.where(m, nc * np.cos(nh), a)
        b = np.where(m, nc * np.sin(nh), b)
        L = np.where(m, np.clip(L + float(r.get("chiaro", 0.0)), 0, 1), L)
    rgb = px.from_oklab(np.stack([L, a, b], -1))
    return Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8))


def figura(cp: Path, fc: dict, ink, seed: int, pal_sfondo: np.ndarray | None = None) -> tuple[np.ndarray, dict]:
    """Una figura dipinta su fondo verde: si ritaglia, si riduce all'altezza data (pixel quadrati, media d'area),
    si porta su una sua tavolozza e prende il contorno d'inchiostro. Esce come strato a parte, per animarla."""
    im = Image.open(cp.parent / fc["base"]).convert("RGB")
    if fc.get("ritaglio"):
        im = im.crop(tuple(fc["ritaglio"]))
    if fc.get("specchia"):                                   # mai per GIG: braccio e occhio cyber hanno il loro lato
        im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if fc.get("liscia"):
        # "liscia": filtro mediano sulla base (lato in pixel della base), prima della riduzione: toglie le righe di
        # pioggia e le sbavature dipinte sulla figura, che ridotte diventano rumore, e lascia le campiture piatte
        from PIL import ImageFilter
        im = im.filter(ImageFilter.MedianFilter(int(fc["liscia"]) | 1))
    rgb = np.asarray(im)
    key = chiave_verde(rgb)
    alpha = 1.0 - ndimage.binary_opening(key > 0.5, iterations=2) * 1.0
    alpha = ndimage.binary_opening(alpha > 0.5, iterations=2)
    lab_lbl, n = ndimage.label(alpha)
    if n > 1:                                           # via le macchioline staccate
        sizes = ndimage.sum(alpha, lab_lbl, range(1, n + 1))
        keep = np.isin(lab_lbl, 1 + np.nonzero(sizes >= sizes.max() * float(fc.get("isole", 0.02)))[0])
        alpha = keep
    ys, xs = np.nonzero(alpha)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgb, alpha = rgb[y0:y1, x0:x1].copy(), alpha[y0:y1, x0:x1]
    # il verde che sborda sui contorni: lo si toglie portando G sotto il massimo di R e B
    # vicino al bordo (entro "bordo_verde" px della base) il verde si toglie del tutto, più dentro solo se è forte:
    # così i capelli grigi e la pelle restano puliti e i colori verdi della figura (pantaloni oliva) restano
    vicino = ndimage.distance_transform_edt(alpha) <= float(fc.get("bordo_verde", 24))
    mx = np.maximum(rgb[..., 0], rgb[..., 2]).astype(int)
    spill = (rgb[..., 1].astype(int) > mx + 20) | (vicino & (rgb[..., 1].astype(int) > mx))
    rgb[spill, 1] = mx[spill]
    h = int(fc["altezza"])
    w = max(1, int(round(rgb.shape[1] * h / rgb.shape[0])))
    # i colori: media dei soli pixel della figura (il fondo non deve sporcare i bordi)
    a = Image.fromarray((alpha * 255).astype(np.uint8)).resize((w, h), Image.BOX)
    pre = Image.fromarray((rgb * alpha[..., None]).astype(np.uint8)).resize((w, h), Image.BOX)
    am = np.asarray(a).astype(np.float64) / 255
    col = np.asarray(pre).astype(np.float64) / np.maximum(am[..., None], 1e-3)
    on = am > float(fc.get("soglia_alfa", 0.5))
    fill = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
    if fc.get("nitido"):
        # "nitido": la maschera di contrasto sulla figura già ridotta, prima della tavolozza: i passaggi fra i toni
        # che la media d'area impasta (pieghe, barba, metallo) tornano netti
        from PIL import ImageFilter
        fill = fill.filter(ImageFilter.UnsharpMask(radius=1, percent=int(fc["nitido"]), threshold=2))
    out, _ = px.pixelize(fill, (w, h), int(fc.get("colori", 24)), seed=seed, denoise=0, clean_passes=1)
    out[..., 3] = on * 255
    out[~on] = 0
    if fc.get("dettagli_scuri"):
        # i dettagli scuri piccoli (fori degli occhi, grani del rosario, pieghe) la media d'area li spegne:
        # dove la base è scura per più di questa frazione del pixel, il pixel diventa inchiostro
        Lb = px.to_oklab(rgb.astype(np.float64) / 255)[..., 0]
        scuro = Image.fromarray(((Lb < INK_L + 0.08) & alpha).astype(np.uint8) * 255).resize((w, h), Image.BOX)
        out[(np.asarray(scuro) / 255 > float(fc["dettagli_scuri"])) & on, :3] = ink
    if fc.get("grana"):
        # la nebbiolina dello spray: una frazione dei pixel prende il colore di un vicino a 1-2 px, così i passaggi
        # fra i toni diventano puntinati come nello sfondo invece che netti come in un render ridotto
        rg = np.random.default_rng(seed + 11)
        yy, xx = np.mgrid[0:h, 0:w]
        sy = np.clip(yy + rg.integers(-2, 3, (h, w)), 0, h - 1)
        sx = np.clip(xx + rg.integers(-2, 3, (h, w)), 0, w - 1)
        m = on & on[sy, sx] & (rg.random((h, w)) < float(fc["grana"]))
        out[m, :3] = out[sy, sx, :3][m]
    if fc.get("tinta"):
        # la luce della vignetta sulla figura (il caldo rosato della foschia): la lega allo sfondo
        tc = fc["tinta"]
        t = np.array(hexrgb(tc["colore"]), float)
        k = float(tc.get("forza", 0.15))
        chiaro = on & (out[..., :3].astype(int).sum(axis=2) > 3 * 60)
        out[chiaro, :3] = (out[chiaro, :3] * (1 - k) + t * k).astype(np.uint8)
    if fc.get("rim"):
        # il filo di neon rosa dei murales sui bordi dalla parte della luce ("lati": sx, dx, alto), come lo
        # hanno le forme dello sfondo: senza, la figura sembra un render incollato sopra
        rc = fc["rim"]
        rosa = np.array(hexrgb(rc.get("colore", "#ff3da8")), float)
        k = float(rc.get("forza", 0.75))
        bordo = np.zeros_like(on)
        for lato in rc.get("lati", ["sx", "alto"]):
            dy, dx = {"sx": (0, -1), "dx": (0, 1), "alto": (-1, 0)}[lato]
            op = np.pad(on, 1)
            fuori = ~op[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            bordo |= on & fuori
        out[bordo, :3] = (out[bordo, :3] * (1 - k) + rosa * k).astype(np.uint8)
    if pal_sfondo is not None:
        # "tavolozza_sfondo": la figura prende i colori dello sfondo (il più vicino in OKLab), come se fosse
        # dipinta con le stesse bombolette
        pl = px.to_oklab(pal_sfondo.astype(np.float64) / 255)
        fl = px.to_oklab(out[..., :3].astype(np.float64) / 255)
        d = ((fl[on][:, None, :] - pl[None, :, :]) ** 2).sum(axis=2)
        # se lo sfondo non ha un colore abbastanza vicino (i grigi dei capelli e del metallo), resta il suo
        vic = d.min(axis=1) <= float(fc.get("tavolozza_dist", 0.05)) ** 2
        sel = np.argwhere(on)[vic]
        out[sel[:, 0], sel[:, 1], :3] = pal_sfondo[d.argmin(axis=1)[vic]]
    if fc.get("contorno", True):
        n = int(fc.get("contorno_px", 1))
        pad = np.zeros((h + 2 * n, w + 2 * n, 4), np.uint8)
        pad[n:-n, n:-n] = out
        on_p = np.pad(on, n)
        ring_p = ndimage.binary_dilation(on_p, np.ones((3, 3), bool), iterations=n) & ~on_p
        pad[ring_p, :3] = ink
        pad[ring_p, 3] = 255
        out = pad
    # i pixel scurissimi della figura diventano lo stesso inchiostro della vignetta
    lab = px.to_oklab(out[..., :3].astype(np.float64) / 255)
    out[(lab[..., 0] < INK_L) & (out[..., 3] > 0), :3] = ink
    if fc.get("toppa"):
        # un pezzo ridisegnato a mano in pixel art (la testa di spalle, che ridotta diventa una macchia):
        # {"file": png accanto alla base, "x", "y"} in pixel della figura; sostituisce tutto il suo riquadro
        tp = fc["toppa"]
        pt = np.asarray(Image.open(cp.parent / tp["file"]).convert("RGBA"))
        ty, tx = int(tp["y"]), int(tp["x"])
        out[ty:ty + pt.shape[0], tx:tx + pt.shape[1]] = pt[:out.shape[0] - ty, :out.shape[1] - tx]
    if "taglia_y" in fc:
        # la figura passa dietro qualcosa (un muro): sotto questa riga della vignetta non si vede
        r = max(0, int(fc["taglia_y"]) - int(fc["y"]))
        out[r:] = 0
        out[r:r + 1, :, :3] = ink
        out[r:r + 1, :, 3] = out[r - 1:r, :, 3] if r else 0
    if fc.get("finestra"):
        # la figura sta dentro un vano (una finestra): fuori da [x0, y0, x1, y1] della vignetta non si vede
        fx0, fy0, fx1, fy1 = (int(v) for v in fc["finestra"])
        ox, oy = int(fc["x"]), int(fc["y"])
        vis = np.zeros(out.shape[:2], bool)
        vis[max(0, fy0 - oy):max(0, fy1 - oy), max(0, fx0 - ox):max(0, fx1 - ox)] = True
        out[~vis] = 0
    dx0 = dy0 = 0
    if fc.get("scia"):
        out, dx0, dy0 = scia(out, fc["scia"], ink, seed)
    sp = int(fc.get("contorno_px", 1)) - 1 if fc.get("contorno", True) else 0   # il contorno spesso sporge
    info = {"nome": fc["nome"], "file": f"figura_{fc['nome']}.png", "x": int(fc["x"]) - sp - dx0,
            "y": int(fc["y"]) - sp - dy0,
            "misura": [int(out.shape[1]), int(out.shape[0])]}
    for k in ("profondita", "nota", "visibile"):
        if k in fc:
            info[k] = fc[k]
    return out, info


def davanti(img: np.ndarray, dc: dict) -> tuple[np.ndarray, dict]:
    """Un pezzo della vignetta che sta davanti a una figura che scorre (il tronco del pino davanti ai perdoni di
    MP06): per ogni riga fra "righe" [y0, y1] e in ogni finestra [x0, x1] si prende dal primo all'ultimo pixel
    che non è fondo chiaro (scuro, verde o rosso bruno). Esce come figura ferma con la vignetta (profondità 1)."""
    rgb = img[..., :3].astype(np.int32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lum = (r * 3 + g * 6 + b) // 10
    pieno = (lum < int(dc.get("soglia", 110))) | ((g > r) & (g >= b)) | ((r > g + 20) & (r > b + 20) & (lum < 140))
    m = np.zeros(lum.shape, bool)
    y0, y1 = dc["righe"]
    for x0, x1 in dc["finestre"]:
        for y in range(y0, y1 + 1):
            xs = np.flatnonzero(pieno[y, x0:x1 + 1])
            if len(xs):
                m[y, x0 + xs[0]:x0 + xs[-1] + 1] = True
    ys, xs = np.nonzero(m)
    bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    f = np.zeros((by1 - by0, bx1 - bx0, 4), np.uint8)
    f[..., :3] = img[by0:by1, bx0:bx1, :3]
    f[..., 3] = np.where(m[by0:by1, bx0:bx1], 255, 0)
    info = {"nome": dc["nome"], "file": f"figura_{dc['nome']}.png", "x": int(bx0), "y": int(by0),
            "misura": [int(bx1 - bx0), int(by1 - by0)], "profondita": 1.0,
            "nota": dc.get("nota", "pezzo della vignetta che copre la figura di prima")}
    return f, info


def volto(f: np.ndarray, vc: dict) -> dict:
    """Le varianti animate di un volto dipinto: occhi chiusi ("blink") e bocca aperta ("talk"). Le disegniamo noi,
    a mano, sui pixel della figura già ridotta: ogni variante è una lista di pennellate [x, y, w, h, "#colore"] in
    pixel della figura (col contorno), date nell'ordine. Sui volti dei murales la ricerca automatica degli occhi dei
    primi piani del gioco (closeup_ai.py) non funziona: l'occhio è una fessura chiara sotto l'ombra del sopracciglio.
    -> {"blink": rgba, "talk": rgba, "info": {"blink": riquadro, "talk": riquadro}}"""
    res, info = {}, {}
    for k in ("blink", "talk"):
        if not vc.get(k):
            continue
        comp = f.copy()
        xs, ys = [], []
        for x, y, w, h, col in vc[k]:
            tocca = comp[y:y + h, x:x + w, 3] > 0                 # solo sulla figura, mai sul trasparente
            comp[y:y + h, x:x + w, :3][tocca] = hexrgb(col)
            xs += [x, x + w]
            ys += [y, y + h]
        res[k] = comp
        info[k] = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
    res["info"] = info
    return res


def scia(out: np.ndarray, sc: dict, ink, seed: int) -> tuple[np.ndarray, int, int]:
    """La scia di un getto (il braccio cyber di GIG in MP13): una linea che parte dall'ugello e si sfalda in
    trattini e poi in gocce sparse, dal colore chiaro dell'anima a quello scuro della coda. Al posto di un cono
    pieno, che ridotto in pixel sembra una lama. "punti": la spezzata in pixel della figura (col contorno),
    anche fuori dal suo riquadro: la figura si allarga e la sua x, y nel json si sposta di conseguenza."""
    P = np.array(sc["punti"], float)
    cols = [np.array(hexrgb(c)) for c in sc.get("colori", ["#f2fffc", "#7ef4ff", "#2cc4d8", "#1a7a8c"])]
    rg = np.random.default_rng(seed + int(sc.get("seme", 3)))
    # la spezzata, ricampionata a passi di mezzo pixel
    seg = np.diff(P, axis=0)
    lun = np.hypot(seg[:, 0], seg[:, 1])
    tot = lun.sum()
    ts = np.arange(0, tot, 0.5)
    cum = np.concatenate([[0], np.cumsum(lun)])
    idx = np.clip(np.searchsorted(cum, ts, side="right") - 1, 0, len(seg) - 1)
    pts = P[idx] + seg[idx] * ((ts - cum[idx]) / np.maximum(lun[idx], 1e-6))[:, None]
    u = ts / tot                                              # 0 all'ugello, 1 in fondo
    pieno, tratti = float(sc.get("pieno", 0.18)), float(sc.get("tratti", 0.55))
    larg = float(sc.get("larghezza", 2.0))
    disegno = []
    for (x, y), t in zip(pts, u):
        if t > pieno:
            fase = (t - pieno) / (1 - pieno)
            if t < tratti:
                if (t * tot / float(sc.get("passo", 5.0))) % 1.0 > 0.62:       # i buchi fra i trattini
                    continue
            elif rg.random() > float(sc.get("gocce", 0.4)) * (1.0 - fase) + 0.04:   # le gocce, sempre più rade
                continue
            if t >= tratti:                                                   # le gocce si allargano un poco
                x += rg.normal(0, 1.0 + 2.5 * fase)
                y += rg.normal(0, 0.6)
        k = min(len(cols) - 1, int(t * len(cols)))
        w = larg if t < pieno else (1.0 if t >= tratti else max(1.0, larg - 0.5))
        disegno.append((x, y, w, k, t))
    xs = [d[0] for d in disegno]
    ys = [d[1] for d in disegno]
    m = 2
    dx0 = max(0, int(np.ceil(-min(xs))) + m)
    dy0 = max(0, int(np.ceil(-min(ys))) + m)
    H = max(out.shape[0] + dy0, int(max(ys)) + dy0 + m)
    W = max(out.shape[1] + dx0, int(max(xs)) + dx0 + m)
    big = np.zeros((H, W, 4), np.uint8)
    big[dy0:dy0 + out.shape[0], dx0:dx0 + out.shape[1]] = out
    sotto = big[..., 3] > 0                                       # la scia passa dietro la figura
    for x, y, w, k, t in disegno:
        xi, yi = int(round(x)) + dx0, int(round(y)) + dy0
        r = int(w) - 1
        for yy in range(yi - r, yi + r + 1):
            for xx in range(xi - r, xi + r + 1):
                if 0 <= yy < H and 0 <= xx < W and not sotto[yy, xx]:
                    big[yy, xx, :3] = cols[k] if not (t < pieno and r and (yy, xx) != (yi, xi)) else cols[min(k + 1, len(cols) - 1)]
                    big[yy, xx, 3] = 255
    return big, dx0, dy0


def accorda(im: Image.Image, cartella: Path, rf: dict) -> Image.Image:
    """"riferimento": i colori della base portati verso quelli di un'immagine del gioco (la cattura dello stesso
    posto), con media e deviazione di L, a, b in OKLab: per i murales che si dissolvono nel livello o ne escono
    (MP06 al cimitero), che altrimenti staccano. {"file": png accanto al json, "zona": [x0, y0, x1, y1] del
    riferimento da misurare (facoltativa, per lasciare fuori HUD e personaggi), "forza": 0-1, "croma": 0-1}."""
    ref = Image.open(cartella / rf["file"]).convert("RGB")
    if rf.get("zona"):
        ref = ref.crop(tuple(rf["zona"]))
    rl = px.to_oklab(np.asarray(ref).astype(np.float64) / 255).reshape(-1, 3)
    bl = px.to_oklab(np.asarray(im).astype(np.float64) / 255)
    k = float(rf.get("forza", 1.0))
    out = bl.copy()
    for c in range(3):
        m0, s0 = bl[..., c].mean(), bl[..., c].std() + 1e-6
        m1, s1 = rl[:, c].mean(), rl[:, c].std() + 1e-6
        if c and "croma" in rf:                                   # la croma del riferimento, scalata a mano
            s1 *= float(rf["croma"])
        out[..., c] = (bl[..., c] - m0) * s1 / s0 + m1
    if rf.get("locale"):
        # "locale": sigma in pixel del riferimento. Il riferimento è la stessa inquadratura: le macchie di colore
        # (cielo, muri, cipressi) si portano una per una sulle sue, il dettaglio resta quello del murale.
        # "fuori": [[x0, y0, x1, y1], ...] del riferimento da non misurare (HUD, cartelli, GIG)
        rw, rh = Image.open(cartella / rf["file"]).size
        rf_full = px.to_oklab(np.asarray(Image.open(cartella / rf["file"]).convert("RGB")).astype(np.float64) / 255)
        ok = np.ones((rh, rw))
        for x0, y0, x1, y1 in rf.get("fuori", []):
            ok[y0:y1, x0:x1] = 0
        sg = float(rf["locale"])
        small = np.asarray(Image.fromarray((np.clip(px.from_oklab(out), 0, 1) * 255).astype(np.uint8)).resize(
            (rw, rh), Image.BOX)).astype(np.float64) / 255
        sl = px.to_oklab(small)
        den = ndimage.gaussian_filter(ok, sg) + 1e-6
        diff = np.stack([ndimage.gaussian_filter(rf_full[..., c] * ok, sg) / den
                         - ndimage.gaussian_filter(sl[..., c] * ok, sg) / den for c in range(3)], -1)
        H, W = out.shape[:2]
        up = np.stack([np.asarray(Image.fromarray(diff[..., c].astype(np.float32)).resize((W, H), Image.BILINEAR))
                       for c in range(3)], -1)
        out = out + up * float(rf.get("forza_locale", 1.0))
    out = bl * (1 - k) + out * k
    rgb = np.clip(px.from_oklab(out), 0, 1)
    return Image.fromarray((rgb * 255 + 0.5).astype(np.uint8))


def riduci(base: Image.Image, misura, colori: int, seed: int, rc: dict) -> tuple[np.ndarray, np.ndarray]:
    """La base ridotta alla vignetta. Senza "riduzione" è quella di sempre (mediana 3, media d'area, una pulizia dei
    pixel soli). Con "riduzione": {"mediana": n, "metodo": "box" | "lanczos", "nitido": percento, "pulizia": passi}
    si tiene più dettaglio: niente mediana, un ricampionamento più netto, la maschera di contrasto sulla vignetta già
    ridotta e i pixel soli lasciati dove sono (gli occhi, le lampadine, i bulloni)."""
    if not rc:
        return px.pixelize(base, misura, colori, seed=seed, denoise=3, clean_passes=1)
    from PIL import ImageFilter
    im = base.convert("RGB")
    if rc.get("mediana"):
        im = im.filter(ImageFilter.MedianFilter(int(rc["mediana"]) | 1))
    im = im.resize(tuple(misura), Image.LANCZOS if rc.get("metodo") == "lanczos" else Image.BOX)
    if rc.get("nitido"):
        im = im.filter(ImageFilter.UnsharpMask(radius=float(rc.get("raggio", 1.0)), percent=int(rc["nitido"]),
                                               threshold=int(rc.get("soglia", 2))))
    return px.pixelize(im, misura, colori, seed=seed, denoise=0, clean_passes=int(rc.get("pulizia", 0)))


def rivela(img: np.ndarray, seed: int, ink=INCHIOSTRO) -> np.ndarray:
    """L'ordine dello spray: macchie larghe che si allargano, con il bordo sfrangiato del nebulizzato, da sinistra
    verso destra. I contorni (l'inchiostro) compaiono un poco dopo i colori, come quando si ripassano alla fine."""
    H, W = img.shape[:2]
    rng = np.random.default_rng(seed)
    big = ndimage.gaussian_filter(rng.random((H, W)), 22, mode="wrap")
    mid = ndimage.gaussian_filter(rng.random((H, W)), 6, mode="wrap")
    fine = rng.random((H, W))
    # da sinistra verso destra, come chi dipinge un muro camminando
    sweep = np.linspace(0, 1, W)[None, :].repeat(H, 0)
    v = 0.45 * sweep + 0.30 * (big - big.min()) / (np.ptp(big) or 1) + 0.15 * (mid - mid.min()) / (np.ptp(mid) or 1) \
        + 0.10 * fine
    v = (v - v.min()) / (np.ptp(v) or 1)
    dark = np.all(img[..., :3] == ink, -1)
    v = np.where(dark, 0.18 + 0.82 * v, 0.88 * v)
    return (v * 255).astype(np.uint8)


MURO = (0xB8, 0xA8, 0x94)            # l'intonaco su cui si dipinge, solo per l'anteprima


def anteprima_rivela(img: np.ndarray, riv: np.ndarray, prev: Path, vid: str, passi: int = 28) -> None:
    """La rivelazione: una GIF corta (1x) e la tavola di 4 fotogrammi (25, 50, 75, 100%)."""
    def fotogramma(t: float) -> np.ndarray:
        f = np.empty_like(img[..., :3])
        f[:] = MURO
        on = riv.astype(np.float64) <= t * 255
        f[on] = img[on, :3]
        return f
    frames = [Image.fromarray(fotogramma(i / (passi - 1))) for i in range(passi)]
    frames = [frames[0]] * 4 + frames + [frames[-1]] * 14
    frames[0].save(prev / f"{vid}_rivela.gif", save_all=True, append_images=frames[1:], duration=70, loop=0,
                   optimize=False)
    H, W = img.shape[:2]
    tav = Image.new("RGB", (W * 2 + 4, H * 2 + 4), (20, 14, 30))
    for i, t in enumerate((0.25, 0.5, 0.75, 1.0)):
        tav.paste(Image.fromarray(fotogramma(t)), ((i % 2) * (W + 4), (i // 2) * (H + 4)))
    tav.save(prev / f"{vid}_rivela_4.png")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("config")
    ap.add_argument("--uscita", help="cartella delle immagini (predefinita: game/assets/murales/<capitolo>/<id>)")
    ap.add_argument("--anteprime", default=str(PREVIEW))
    args = ap.parse_args()
    cp = Path(args.config)
    cfg = json.loads(cp.read_text(encoding="utf-8"))
    vid, cap = cfg["id"], cfg.get("capitolo", "prologo")
    misura = tuple(cfg.get("misura", [512, 288]))
    out = Path(args.uscita) if args.uscita else OUT / cap / vid
    prev = Path(args.anteprime)
    out.mkdir(parents=True, exist_ok=True)
    prev.mkdir(parents=True, exist_ok=True)
    seed = int(cfg.get("seme", 7))
    rng = np.random.default_rng(seed)

    base = Image.open(cp.parent / cfg["base"]).convert("RGB")
    if cfg.get("ritinta"):
        base = ritinta(base, cfg["ritinta"])
    base = ritaglia(base, misura, cfg.get("ritaglio"))
    if cfg.get("riferimento"):
        base = accorda(base, cp.parent, cfg["riferimento"])
    img, pal = riduci(base, misura, int(cfg.get("colori", 48)), seed, cfg.get("riduzione", {}))
    ink = hexrgb(cfg["inchiostro"]) if "inchiostro" in cfg else INCHIOSTRO
    img = inchiostro(img, pal, ink)
    emis = luci(img, cfg.get("luci", {}))
    if cfg.get("schermi"):
        # i maxischermi della torre di SIDERA, come nel cielo del prologo: [[x, y, w, h], ...]
        import schermi_torre
        schermi_torre.disegna(img, [tuple(b) for b in cfg["schermi"]], emis)
    strati = []
    for s in cfg.get("scritte", []):
        if s.get("strato"):
            # una scritta che il motore fa comparire da sola (il registro che scorre): strato trasparente a parte
            st, se = np.zeros_like(img), np.zeros_like(emis)
            scritta(st, se, s, rng)
            st[..., 3] = np.where(st[..., :3].any(axis=2), 255, 0)
            strati.append((st, {"nome": s["strato"], "file": f"scritta_{s['strato']}.png", "testo": s["testo"]}))
        else:
            scritta(img, emis, s, rng)
    figs = []
    comp = img.copy()
    for st, _ in strati:
        over(comp, st, 0, 0)
    for fc in cfg.get("figure", []):
        pal_bg = np.unique(img[..., :3][img[..., 3] > 0], axis=0) if fc.get("tavolozza_sfondo") else None
        if fc.get("tavolozza_da"):
            # "tavolozza_da": i colori di un PNG (lo sprite del gioco su trasparente), perché la figura sfumi nello
            # sprite senza cambiare tinta; vale come tavolozza_sfondo, con la sua soglia tavolozza_dist
            tp = np.asarray(Image.open(cp.parent / fc["tavolozza_da"]).convert("RGBA"))
            pal_bg = np.unique(tp[..., :3][tp[..., 3] > 0], axis=0)
        f, info = figura(cp, fc, ink, seed, pal_bg)
        if fc.get("volto"):
            vv = volto(f, fc["volto"])
            for k in ("blink", "talk"):
                if k in vv:
                    Image.fromarray(vv[k]).save(out / f"figura_{fc['nome']}_{k}.png")
                    info[k] = f"figura_{fc['nome']}_{k}.png"
            info["volto"] = vv["info"]
        figs.append((f, info))
        if info.get("visibile", True):
            over(comp, f, info["x"], info["y"])
    for dc in cfg.get("davanti", []):
        f, info = davanti(img, dc)
        nomi = [i["nome"] for _, i in figs]
        figs.insert(nomi.index(dc["dopo"]) + 1 if dc.get("dopo") in nomi else len(figs), (f, info))
        over(comp, f, info["x"], info["y"])
    riv = rivela(comp, seed, ink)

    Image.fromarray(img).save(out / "murale.png")
    for f, info in figs + strati:
        Image.fromarray(f).save(out / info["file"])
    Image.fromarray(emis).save(out / "murale_emis.png")
    Image.fromarray(riv).save(out / "murale_rivela.png")
    W, H = misura
    sc = cfg.get("scorri", {"da": [0, (H - SCHERMO[1]) // 2], "a": [W - SCHERMO[0], (H - SCHERMO[1]) // 2]})
    info = {
        "nota": "vignetta dei murales di Totò (tools/murales/murale.py): murale.png opaco, murale_emis.png da "
                "sommare (luci che pulsano), murale_rivela.png = ordine dello spray (0 subito, 255 per ultimo)",
        "id": vid, "capitolo": cap, "misura": [W, H], "schermo": list(SCHERMO),
        "scorri": sc, **({"camera": cfg["camera"]} if "camera" in cfg else {}),
        **({"pupilla": cfg["pupilla"]} if "pupilla" in cfg else {}),
        **({"scritte": [i for _, i in strati]} if strati else {}),
        **({"figure": [i for _, i in figs]} if figs else {}), "colori": int(len(np.unique(img[..., :3].reshape(-1, 3), axis=0))),
        "fonte": cfg.get("fonte", "ChatGPT (OpenAI), da nostri render e schizzi; ridotto in pixel art dai nostri "
                                  "script"),
    }
    (out / "murale.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")

    # anteprima: la vignetta a 2x, con il riquadro dello schermo all'inizio e alla fine dello scorrimento
    pv = Image.fromarray(np.clip(comp[..., :3].astype(np.int32) + emis[..., :3].astype(np.int32) // 2, 0, 255)
                         .astype(np.uint8)).resize((W * 2, H * 2), Image.NEAREST)
    from PIL import ImageDraw
    d = ImageDraw.Draw(pv)
    for (x, y), col in ((sc["da"], (255, 255, 255)), (sc["a"], (255, 214, 92))):
        d.rectangle([x * 2, y * 2, (x + SCHERMO[0]) * 2 - 1, (y + SCHERMO[1]) * 2 - 1], outline=col)
    pv.save(prev / f"{vid}_2x.png")
    anteprima_rivela(comp, riv, prev, vid)
    Image.fromarray(comp[..., :3]).save(prev / f"{vid}_1x.png")
    print(f"{vid}: {W}x{H}, {info['colori']} colori, luci {int((emis[..., 3] > 0).sum())} px -> {out}")


if __name__ == "__main__":
    main()
