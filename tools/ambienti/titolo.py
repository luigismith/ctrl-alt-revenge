# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - la schermata del titolo «Il tetto» (Luigi, 7 novembre 2026), divisa in piani.

  python -I tools/ambienti/titolo.py [--base titolo_tetto_v1.png] [--uscita DIR] [--anteprime DIR]

GIG, di spalle, guarda la città dal terrazzo di una palazzina dei Tamburi: la sera del Wind Day (17 aprile
2087, ore 21), sotto la nube di polvere rossa, con la torre SIDERA, la Linea sui piloni e le cupole. La base è
dipinta da ChatGPT (registro nella cartella privata, `ambienti-ai/titolo/`); qui diventa pixel art a 480×270 e
si divide in piani che il gioco anima:

  base.png        il fondale, opaco;
  base_emis.png   le luci (finestre, maxischermo, cartellone, luci della torre), da sommare;
  torre_emis.png  solo le luci d'ostacolo della torre, per farle lampeggiare;
  gig.png         GIG di spalle, già illuminato dalla città (dal render 3D, tools/sprites/titolo_gig.py),
                  con gig_normali.png per la luce del Wind Day e gig_cyan.png per far pulsare braccio e occhio;
  panni.png       i panni sullo stendino, rossi di polvere, in FOTOGRAMMI fotogrammi affiancati (procedurali);
  titolo.json     dove sta ogni cosa: GIG, panni, logo, menu, luci.

Le correzioni alla base, prima della riduzione:
- la cima della torre si perde nella nube (la polvere arriva a 200-250 m, la torre ne fa 400: cronologia) e le
  sue luci rosse restano come aloni;
- il cartellone chiaro a sinistra vira al bianco-menta di ARIA+ (il ciano è solo di GIG);
- sul maxischermo c'è lo slogan di SIDERA, scritto con pixfont.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "env"))
from piani import ROOT  # noqa: E402
import pixelizza as px  # noqa: E402
import pixfont as PF  # noqa: E402

W, H = 480, 270
BASE = ROOT.parent / "ctrlaltrevenge-lab-condiviso/ambienti-ai/titolo/titolo_tetto_v1.png"
GIG = ROOT / "tools/sprites/out/titolo"
OUT = ROOT / "game/assets/ui/titolo"
PREVIEW = ROOT / "tools/out/ambienti/titolo"
COLORI = 64

# Nella base (1672×941): la torre, il cartellone, il maxischermo.
TORRE = (1048, 1190)          # colonne della torre e dei suoi bracci
TORRE_NUBE = (130, 300)       # sopra 300 la torre comincia a sparire, a 130 non c'è quasi più
CARTELLONE = (436, 505, 528, 556)
MAXI = (1218, 548, 1342, 655)

# Nel gioco (480×270).
GIG_FEET = (78, 264)          # il centro dei piedi di GIG
LOGO_CX, LOGO_Y = 182, 6      # il logo sopra GIG, a sinistra della torre
MENU_CX, MENU_Y, MENU_STEP = 352, 204, 13
FOTOGRAMMI, FPS = 8, 8
MINT = (150, 215, 180)


# --- La base ---------------------------------------------------------------------------------

def ritocca(hi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Torre nella nube e cartellone di ARIA+, sulla base grande. Restituisce la base e gli aloni."""
    a = hi.astype(np.float64)
    h, w = a.shape[:2]
    x0, x1 = TORRE
    y_lo, y_hi = TORRE_NUBE
    # il colore della nube riga per riga, dai due lati della torre
    side = np.concatenate([a[:y_hi, x0 - 50:x0 - 10], a[:y_hi, x1 + 10:x1 + 50]], axis=1)
    sky = np.median(side, axis=1)
    sky = np.asarray(Image.fromarray(sky[:, None, :].astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)),
                     np.float64)[:, 0]
    reg = a[:y_hi, x0:x1]
    red = (reg[..., 0] > 170) & (reg[..., 1] < 120) & (reg[..., 0] - reg[..., 1] > 90)
    yy = np.arange(y_hi)[:, None]
    f = np.clip((y_hi - yy) / (y_hi - y_lo), 0, 1) ** 0.8 * 0.93
    xs = np.arange(x1 - x0)
    feather = np.clip(np.minimum(xs, x1 - x0 - 1 - xs) / 12, 0, 1)[None, :]
    f = f * feather
    a[:y_hi, x0:x1] = reg * (1 - f[..., None]) + sky[:, None, :] * f[..., None]
    # gli aloni delle luci rosse che si perdono nella polvere
    glow = np.zeros((h, w), np.float64)
    glow[:y_hi, x0:x1] = red * np.maximum(f, 0.35)
    glow = np.asarray(Image.fromarray((glow * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)),
                      np.float64) / 255
    glow = np.clip(glow * 2.6, 0, 1)
    a += glow[..., None] * np.array([110.0, 18.0, 12.0])
    # il cartellone: il bianco della base va al bianco-menta
    cx0, cy0, cx1, cy1 = CARTELLONE
    c = a[cy0:cy1, cx0:cx1]
    lum = c @ np.array([0.299, 0.587, 0.114])
    t = np.clip((lum - 150) / 70, 0, 1)[..., None]
    mint = np.array([205.0, 238.0, 214.0]) * (lum[..., None] / 235)
    a[cy0:cy1, cx0:cx1] = c * (1 - t) + mint * t
    return np.clip(a, 0, 255).astype(np.uint8), glow


def scala(xy, hi_shape) -> tuple[int, int]:
    return int(round(xy[0] * W / hi_shape[1])), int(round(xy[1] * H / hi_shape[0]))


def luci(img: np.ndarray) -> np.ndarray:
    """La mappa emissiva: luci calde e chiare, rossi accesi della torre e il bianco-menta del cartellone."""
    rgb = img[..., :3].astype(np.float64)
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    warm = (rgb[..., 0] >= rgb[..., 1]) & (rgb[..., 1] >= rgb[..., 2] - 4)
    t = np.clip((lum - 140) / 70, 0, 1) * warm
    red = np.clip((rgb[..., 0] - 175) / 50, 0, 1) * (rgb[..., 1] < 95) * (rgb[..., 0] - rgb[..., 1] > 120)
    mint = (rgb[..., 1] > rgb[..., 0] + 8) & (lum > 170)
    t = np.maximum(np.maximum(t, red), mint * 1.0)
    e = np.zeros((*img.shape[:2], 4), np.uint8)
    e[..., :3] = (rgb * 0.5 * t[..., None]).astype(np.uint8)
    e[..., 3] = np.where(t > 0, 255, 0)
    return e


def maxischermo(img: np.ndarray, emis: np.ndarray, rect: tuple[int, int, int, int]) -> None:
    """Lo slogan di SIDERA sul maxischermo (docs/mondo.md), in due righe da 3×5."""
    x0, y0, x1, y1 = rect
    cx = (x0 + x1) // 2
    rows = ["TARANTO", "È PURA"]
    hh = len(PF.FONT3x5["A"])
    y = (y0 + y1) // 2 - (2 * hh + 4) // 2
    for s in rows:
        m = PF.render(s, PF.FONT3x5, 1, 1)
        if s.startswith("È"):
            # il 3×5 non ha posto per l'accento: due pixel in diagonale sopra la E, nell'interlinea
            m = np.pad(m, ((2, 0), (0, 0)))
            m[0, 0] = m[1, 1] = True
            y -= 2
        x = cx - m.shape[1] // 2
        img[y:y + m.shape[0], x:x + m.shape[1], :3][m] = (255, 232, 170)
        emis[y:y + m.shape[0], x:x + m.shape[1]][m] = (150, 130, 90, 255)
        y += m.shape[0] + 3


# --- GIG ------------------------------------------------------------------------------------

def _n(v):
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v)


def gig_notte(spr: np.ndarray, nrm: np.ndarray, cyan: np.ndarray) -> np.ndarray:
    """GIG di spalle alla città: la schiena in ombra, la luce rossa della nube dall'alto, il bordo destro
    acceso dalla città. Il cyan del braccio e dell'occhio resta com'è: è luce sua."""
    a = spr[..., 3] > 0
    alb = spr[..., :3].astype(np.float64) / 255
    n = nrm[..., :3].astype(np.float64) / 127.5 - 1      # x a destra, y in alto, z verso di noi
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    amb = np.array([0.50, 0.36, 0.40])
    sky_d, sky_c = _n([0.15, 1.0, 0.25]), np.array([0.85, 0.42, 0.30])
    rim_d, rim_c = _n([0.85, 0.2, 0.0]), np.array([1.0, 0.55, 0.28])
    sky = np.clip(n @ sky_d, 0, 1)[..., None] * sky_c * 0.75
    rim = (np.clip(n @ rim_d, 0, 1) ** 2 * (1 - np.clip(n[..., 2], 0, 1)) ** 1.5)[..., None] * rim_c * 2.2
    col = alb * (amb + sky) + rim * (0.35 + 0.65 * alb)
    col = np.clip(col, 0, 1)
    out = spr.copy()
    out[..., :3] = (col * 255).astype(np.uint8)
    out[cyan] = spr[cyan]
    # pochi colori, come uno sprite: k-means sui pixel opachi non cyan
    sel = a & ~cyan
    lab = px.to_oklab(out[..., :3].astype(np.float64) / 255)
    pal = px.kmeans_palette(lab[sel], 22, seed=2)
    idx = px.map_to_palette(lab, pal)
    q = (px.from_oklab(pal) * 255 + 0.5).clip(0, 255).astype(np.uint8)[idx]
    out[..., :3][sel] = q[sel]
    return out


# --- I panni --------------------------------------------------------------------------------

def stendino(hi: np.ndarray, x0: int, x1: int) -> dict[int, int]:
    """La riga del filo nel gioco, colonna per colonna: sulla base grande è la riga più scura fra y 400 e 520
    (fra il muro e il palo), poi una parabola che la liscia."""
    lum = hi[..., :3].astype(np.float64) @ np.array([0.299, 0.587, 0.114])
    hx = np.arange(int(x0 * hi.shape[1] / W), int(x1 * hi.shape[1] / W), 4)
    hy = np.array([400 + np.argmin(lum[400:520, x]) for x in hx], np.float64)
    c = np.polyfit(hx * W / hi.shape[1], hy * H / hi.shape[0], 2)
    return {x: int(round(np.polyval(c, x))) for x in range(x0, x1)}


SS = 4                                       # i panni si disegnano a 4x e poi si riducono
ORLO = (52, 22, 32)                          # il contorno dei panni, prugna scuro
PANNI = [
    # nome, x sinistra, larghezza, altezza, ampiezza del vento, rampa (luce -> ombra); stoffa controluce
    ("lenzuolo", 123, 30, 30, 4.0, [(238, 178, 146), (206, 136, 112), (160, 92, 84), (112, 58, 62)]),
    ("camicia", 157, 16, 18, 3.0, [(184, 134, 140), (148, 100, 114), (110, 68, 88), (76, 44, 64)]),
    ("asciugamano", 177, 12, 22, 3.0, [(240, 170, 90), (206, 124, 62), (156, 82, 50), (106, 52, 44)]),
    ("calzino", 193, 4, 9, 1.5, [(196, 160, 136), (160, 122, 106), (118, 84, 80), (82, 54, 58)]),
    ("calzino", 199, 4, 8, 1.5, [(196, 160, 136), (160, 122, 106), (118, 84, 80), (82, 54, 58)]),
]


def panno(kind: str, w: int, h: int, amp: float, ramp, t: float, seed: int) -> np.ndarray:
    """Un panno appeso per l'orlo alto e gonfiato dal maestrale verso destra (il vento viene dal tramonto).
    t in [0, 1) è la fase del ciclo. Si disegna a SS x, si riduce, si porta a 4 toni e prende il contorno."""
    pad = int(np.ceil(amp)) + 2
    gw, gh = (w + pad) * SS, (h + 1) * SS
    Y, X = np.mgrid[0:gh, 0:gw].astype(np.float64)
    v = Y / (h * SS)
    ph = 2 * np.pi * t + seed * 1.7
    dx = amp * v ** 1.3 * (0.75 + 0.35 * np.sin(ph - v * 2.6)) * SS
    u = (X - dx) / (w * SS)
    lift = 0.06 + 0.06 * np.sin(ph + 1.3)                       # il vento solleva l'orlo basso
    hem = 1 - lift - 0.05 * (0.5 + 0.5 * np.sin(u * 6.5 + ph * 1.5))
    inside = (u >= 0) & (u <= 1) & (v >= 0) & (v <= hem)
    if kind == "camicia":
        body = (u >= 0.2) & (u <= 0.8)
        sleeve = (v <= 0.42) & (np.abs(u - 0.5) <= 0.5 - 0.25 * v)
        inside &= body | sleeve
        inside &= ~((v < 0.1) & (np.abs(u - 0.5) < 0.1))       # il collo
    if kind == "calzino":
        inside &= ~((v > 0.7) & (u > 0.55 + 0.5 * (v - 0.7)))     # la punta del piede
        inside |= (v > 0.7) & (v <= hem) & (u >= 0) & (u <= 1.4 - (v - 0.7))
    fold = np.sin(u * (10 if kind == "lenzuolo" else 6) + ph * 1.2 - v * 1.8 + seed)
    light = 0.5 + 0.28 * fold + 0.22 * v                         # la città accende la stoffa da sotto
    if kind == "asciugamano":
        light -= 0.35 * ((np.abs(v - 0.18) < 0.04) | (np.abs(v - 0.78) < 0.04))
    k = np.clip(3 - np.floor(np.clip(light, 0, 0.999) * 4), 0, 3)
    a_lo = np.asarray(Image.fromarray((inside * 255).astype(np.uint8)).resize((w + pad, h + 1), Image.BOX)) >= 128
    k_lo = np.asarray(Image.fromarray((k * 60).astype(np.uint8)).resize((w + pad, h + 1), Image.BOX), np.float64)
    k_lo = np.clip(np.round(k_lo / 60), 0, 3).astype(int)
    out = np.zeros((h + 3, w + pad + 2, 4), np.uint8)
    rgb = np.array(ramp, np.uint8)[k_lo]
    out[1:-1, 1:-1, :3][a_lo] = rgb[a_lo]
    out[1:-1, 1:-1, 3][a_lo] = 255
    out = px.add_outline(out, ORLO)
    return out


def panni(line: dict[int, int]) -> tuple[np.ndarray, dict]:
    """Il foglio dei fotogrammi: ogni fotogramma copre la stessa zona dello schermo (x, y, w, h)."""
    xs0 = min(p[1] for p in PANNI) - 2
    xs1 = max(p[1] + p[2] for p in PANNI) + 8
    ytop = min(line[x] for x in range(xs0, xs1)) - 2
    ybot = max(line[p[1]] + p[3] for p in PANNI) + 6
    fw, fh = xs1 - xs0, ybot - ytop
    sheet = np.zeros((fh, fw * FOTOGRAMMI, 4), np.uint8)
    for f in range(FOTOGRAMMI):
        t = f / FOTOGRAMMI
        for i, (kind, x, w, h, amp, ramp) in enumerate(PANNI):
            p = panno(kind, w, h, amp, ramp, (t + i * 0.19) % 1, i)
            for c in range(p.shape[1]):
                gx = x - 1 + c
                y0 = line.get(min(max(gx, x), x + w - 1), line[x]) - ytop - 1   # l'orlo alto segue il filo
                col = p[:, c]
                m = col[:, 3] > 0
                dst = sheet[y0:y0 + len(col), f * fw + gx - xs0]
                dst[m[:len(dst)]] = col[:len(dst)][m[:len(dst)]]
            for pg in (x, x + w - 1):                                       # le mollette, sul filo
                sheet[line[pg] - ytop - 1:line[pg] - ytop + 1, f * fw + pg - xs0] = (84, 52, 40, 255)
    return sheet, {"x": xs0, "y": ytop, "w": fw, "h": fh, "fotogrammi": FOTOGRAMMI, "fps": FPS}


# --- Anteprima ------------------------------------------------------------------------------

def menu_mock(img: Image.Image, items, cx, y, step, sel=0) -> None:
    a = np.asarray(img).copy()
    for i, s in enumerate(items):
        m = PF.render(s, PF.FONT5x7, 1, 1)
        x = cx - m.shape[1] // 2
        yy = y + i * step
        col = (255, 214, 92) if i == sel else (242, 226, 190)
        sh = np.zeros_like(a[..., 0], bool)
        sh[yy + 1:yy + 1 + m.shape[0], x + 1:x + 1 + m.shape[1]] = m
        a[sh] = (20, 8, 14, 255)
        a[yy:yy + m.shape[0], x:x + m.shape[1]][m] = (*col, 255)
        if i == sel:
            mk = PF.render(">", PF.FONT5x7, 1, 1)
            a[yy:yy + mk.shape[0], x - 10:x - 10 + mk.shape[1]][mk] = (*col, 255)
    img.paste(Image.fromarray(a))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=str(BASE))
    ap.add_argument("--uscita", default=str(OUT))
    ap.add_argument("--anteprime", default=str(PREVIEW))
    ap.add_argument("--logo", default=str(ROOT / "game/assets/ui/title_logo.png"), help="per provare un logo nuovo")
    ap.add_argument("--sottotitolo", default=str(ROOT / "game/assets/ui/title_subtitle.png"))
    args = ap.parse_args()
    out, prev = Path(args.uscita), Path(args.anteprime)
    out.mkdir(parents=True, exist_ok=True)
    prev.mkdir(parents=True, exist_ok=True)

    hi = np.asarray(Image.open(args.base).convert("RGB"))
    hi2, glow = ritocca(hi)
    base, _pal = px.pixelize(Image.fromarray(hi2), (W, H), COLORI, seed=3, denoise=5, clean_passes=2)
    emis = luci(base)
    mx = (*scala(MAXI[:2], hi.shape), *scala(MAXI[2:], hi.shape))
    maxischermo(base, emis, mx)
    # le luci della torre, a parte: gli aloni ridotti alla misura del gioco
    g = np.asarray(Image.fromarray((glow * 255).astype(np.uint8)).resize((W, H), Image.BOX), np.float64) / 255
    torre = np.zeros((H, W, 4), np.uint8)
    on = g > 0.08
    torre[on] = (np.array([200, 40, 30, 255]) * np.clip(g[on] * 1.4, 0, 1)[:, None]).astype(np.uint8)
    torre[on, 3] = 255
    Image.fromarray(base).save(out / "base.png")
    Image.fromarray(emis).save(out / "base_emis.png")
    Image.fromarray(torre).save(out / "torre_emis.png")

    # GIG
    spr = np.asarray(Image.open(GIG / "gig_titolo.png").convert("RGBA"))
    nrm = np.asarray(Image.open(GIG / "gig_titolo_normali.png").convert("RGBA"))
    cyan = np.asarray(Image.open(GIG / "gig_titolo_cyan.png").convert("L")) > 127
    gig = gig_notte(spr, nrm, cyan)
    Image.fromarray(gig).save(out / "gig.png")
    Image.fromarray(nrm).save(out / "gig_normali.png")
    Image.fromarray((cyan * 255).astype(np.uint8)).save(out / "gig_cyan.png")
    gx, gy = GIG_FEET[0] - gig.shape[1] // 2, GIG_FEET[1] - gig.shape[0]

    # i panni
    line = stendino(hi, 70, 214)
    sheet, pinfo = panni(line)
    Image.fromarray(sheet).save(out / "panni.png")

    logo = Image.open(args.logo).convert("RGBA")
    sub = Image.open(args.sottotitolo).convert("RGBA")
    lx = LOGO_CX - logo.width // 2
    sy = LOGO_Y + logo.height + 3
    info = {
        "nota": "schermata del titolo «Il tetto»: piani e posizioni (tools/ambienti/titolo.py)",
        "schermo": [W, H],
        "base": "base.png", "emis": "base_emis.png", "torre_emis": "torre_emis.png",
        "gig": {"png": "gig.png", "normali": "gig_normali.png", "cyan": "gig_cyan.png", "pos": [gx, gy],
                "piedi": list(GIG_FEET)},
        "panni": {"png": "panni.png", **pinfo},
        "logo": {"pos": [lx, LOGO_Y]},
        "sottotitolo": {"cx": LOGO_CX, "y": sy},
        "menu": {"cx": MENU_CX, "y": MENU_Y, "passo": MENU_STEP},
        "maxischermo": list(mx),
        "stendino": [[x, line[x]] for x in sorted(line)[::8]],
    }
    (out / "titolo.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")

    # anteprima: tutti i piani, primo fotogramma dei panni, logo, sottotitolo, menu
    for f in (0, FOTOGRAMMI // 2):
        im = Image.fromarray(base).convert("RGBA")
        e = Image.fromarray(emis)
        glowim = Image.fromarray(np.clip(np.asarray(im, np.int32)[..., :3] + np.asarray(e, np.int32)[..., :3] * 0.6
                                         + np.asarray(Image.fromarray(torre), np.int32)[..., :3] * 0.5, 0, 255)
                                 .astype(np.uint8))
        im = glowim.convert("RGBA")
        fr = Image.fromarray(sheet[:, f * pinfo["w"]:(f + 1) * pinfo["w"]])
        im.alpha_composite(fr, (pinfo["x"], pinfo["y"]))
        im.alpha_composite(Image.fromarray(gig), (gx, gy))
        im.alpha_composite(logo, (lx, LOGO_Y))
        im.alpha_composite(sub, (LOGO_CX - sub.width // 2, sy))
        menu_mock(im, ["PROLOGO", "GIOCA", "STANZA DI PROVA", "CREDITI", "ESCI"], MENU_CX, MENU_Y, MENU_STEP)
        im.convert("RGB").save(prev / f"titolo_{f}.png")
        im.convert("RGB").resize((W * 2, H * 2), Image.NEAREST).save(prev / f"titolo_{f}_2x.png")
    print(f"titolo: base {COLORI} colori, maxischermo {mx}, GIG {gig.shape[1]}x{gig.shape[0]} a {gx},{gy}, "
          f"panni {pinfo} -> {out}")


if __name__ == "__main__":
    main()
