# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Gli strumenti comuni per comporre i piani di un livello dalle basi dipinte con l'AI.

Le basi sono fogli di Gemini su fondo magenta e di ChatGPT su fondo trasparente (vedi il README):
ogni oggetto si ritaglia, si porta alla scala del gioco e si appoggia sui blocchi della mappa, così
quello che si vede coincide con quello su cui si salta. Per ogni oggetto si dice quale parte del
disegno (l'"àncora", in pixel del foglio) va su quale riquadro del piano.

Il codice è MIT, come il resto del gioco.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pixelizza as px  # noqa: E402
from ritaglia_kit import find_objects  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

T = 20
VIEW_W, VIEW_H = 480, 270
FLOOR = 460

## Parallasse: quanto si muove ogni piano rispetto alla telecamera, in orizzontale e in verticale.
## Il primo piano ("davanti") sta fra GIG e chi guarda: va più veloce del campo di gioco.
SCROLL = {"cielo": (0.04, 0.02), "medio": (0.3, 0.12), "vicino": (0.6, 0.3), "davanti": (1.4, 1.35)}
## Il primo piano sale da sotto il bordo dello schermo: con GIG a terra il suo fondo sta a questa y.
FRONT_BOTTOM = 285
## Le cose basse del primo piano non salgono oltre questa y dello schermo, sotto il pavimento (230):
## così non coprono mai i piedi di GIG.
FRONT_LOW_TOP = 232


# --- La mappa ---------------------------------------------------------------------------------

def read_map(path: Path) -> list[str]:
    rows = [ln.rstrip("\n") for ln in path.read_text("utf-8").splitlines() if not ln.startswith(";")]
    return [r for r in rows if r]


def solid(rows: list[str], cx: int, cy: int) -> bool:
    return 0 <= cy < len(rows) and 0 <= cx < len(rows[cy]) and rows[cy][cx] == "#"


def floor_runs(rows: list[str], r: int, cmax: int, cmin: int = 0) -> list[tuple[int, int]]:
    """Tratti di pavimento pieno sulla riga r fra le colonne cmin e cmax, in pixel (x0, x1)."""
    runs, start = [], None
    for c in range(cmin, cmax + 1):
        on = c < cmax and solid(rows, c, r)
        if on and start is None:
            start = c
        elif not on and start is not None:
            runs.append((start * T, c * T))
            start = None
    return runs


def pits(rows: list[str], r: int, cmax: int, cmin: int = 0) -> list[tuple[int, int]]:
    runs = floor_runs(rows, r, cmax, cmin)
    return [(a[1], b[0]) for a, b in zip(runs, runs[1:])]


def cells(c0: int, r0: int, c1: int, r1: int) -> tuple[int, int, int, int]:
    """Il riquadro in pixel delle celle da (c0, r0) a (c1, r1), estremi compresi."""
    return (c0 * T, r0 * T, (c1 + 1) * T, (r1 + 1) * T)


def layer_width(scroll: float, cam_to: int, cam_from: int = 0) -> int:
    """Quanto dev'essere largo un piano che parte con la telecamera in cam_from e arriva a cam_to."""
    return int(VIEW_W + (cam_to - cam_from) * scroll) + 2


def front_x(world_x: float, origin: int = 0) -> int:
    """Dove va nel primo piano (che parte con la telecamera in `origin`) una cosa che deve passare
    davanti al punto `world_x` del campo di gioco quando quel punto è a metà schermo."""
    return round(VIEW_W / 2 + (world_x - origin - VIEW_W / 2) * SCROLL["davanti"][0])


# --- I fogli ----------------------------------------------------------------------------------

class Sheet:
    """Un foglio su fondo magenta: colore e trasparenza alla risoluzione piena, e i suoi oggetti."""

    def __init__(self, path: Path | None = None, *, rgb: np.ndarray | None = None, alpha: np.ndarray | None = None,
                 join: int = 6):
        if path is not None:
            src = Image.open(path).convert("RGB").filter(ImageFilter.MedianFilter(3))
            self.rgb = np.asarray(src, np.float64) / 255.0
            self.alpha = px.magenta_alpha(self.rgb)
        else:
            self.rgb, self.alpha = rgb, alpha
        # `join`: quanto si dilata la sagoma per tenere insieme le parti staccate di un oggetto
        # (più piccolo se due oggetti vicini finirebbero insieme).
        self.objects = find_objects(self.alpha, join=join)

    def widened(self, repeats: list[tuple[int, int]]) -> "Sheet":
        """Un foglio nuovo in cui ogni tratto verticale (x0, x1) si ripete subito dopo sé stesso, per
        esempio una campata da una colonna all'altra: serve quando il disegno è più stretto del suo
        blocco e non lo si vuole schiacciare."""
        rgb, alpha, x = [], [], 0
        for x0, x1 in sorted(repeats):
            rgb += [self.rgb[:, x:x1], self.rgb[:, x0:x1]]
            alpha += [self.alpha[:, x:x1], self.alpha[:, x0:x1]]
            x = x1
        rgb.append(self.rgb[:, x:])
        alpha.append(self.alpha[:, x:])
        return Sheet(rgb=np.concatenate(rgb, 1), alpha=np.concatenate(alpha, 1))

    def heightened(self, repeats: list[tuple[int, int]]) -> "Sheet":
        """Come widened(), in verticale: ogni fascia (y0, y1) si ripete subito sotto sé stessa."""
        t = Sheet(rgb=self.rgb.transpose(1, 0, 2), alpha=self.alpha.T).widened(repeats)
        return Sheet(rgb=t.rgb.transpose(1, 0, 2), alpha=t.alpha.T)

    def square_base(self, obj: int, y_from: int, skip: int = 6, sample: int = 10, dark: float = 0.68) -> None:
        """Il fianco della base disegnato in prospettiva (il plinto di una tomba visto un poco di lato)
        va più in profondità della ghiaia: sotto il suo spigolo resta un triangolo vuoto e da quel lato
        l'oggetto sembra sollevato. Dalla riga y_from in giù ogni colonna che non arriva al fondo
        scende fino a terra, col colore che il fianco ha appena sopra lo spigolo (saltando `skip` px di
        contorno e prendendo la mediana di `sample` px), sempre più in ombra verso terra, fino a `dark`."""
        (x0, y0, x1, y1), m = self.objects[obj]
        full = np.zeros(self.alpha.shape, bool)
        full[y0:y1, x0:x1] = m
        for x in range(x0, x1):
            col = np.nonzero(full[y_from:y1, x])[0]
            if not len(col) or y_from + col[-1] >= y1 - 2:
                continue
            yd = y_from + col[-1]
            src = np.median(self.rgb[max(y0, yd - skip - sample):yd - skip + 1, x], axis=0)
            k = np.linspace(0.92, dark, y1 - (yd - skip))[:, None]
            self.rgb[yd - skip:y1, x] = src * k
            self.alpha[yd - skip:y1, x] = 1
            full[yd - skip:y1, x] = True
        self.objects[obj] = ((x0, y0, x1, y1), full[y0:y1, x0:x1])

    def clean_top(self, obj: int, dark: float = 0.42, reach: int = 60) -> None:
        """Toglie dalla cima dell'oggetto la frangia sporca di magenta e il contorno scuro del
        foglio: in ogni colonna, tutto quello che sta sopra la prima riga scura (entro `reach` px)."""
        (x0, y0, x1, y1), m = self.objects[obj]
        L = self.rgb[..., :3].mean(-1)
        for x in range(x0, x1):
            col = np.nonzero(self.alpha[y0:y0 + reach, x])[0]
            if not len(col):
                continue
            dk = np.nonzero((L[y0:y0 + reach, x] < dark) & (self.alpha[y0:y0 + reach, x] > 0))[0]
            if len(dk):
                self.alpha[y0:y0 + dk[0] + 2, x] = 0

    def piece(self, crop: tuple[int, int, int, int], obj: int | None = None):
        """Colore e alfa di un riquadro del foglio; con `obj`, solo i pixel di quell'oggetto."""
        x0, y0, x1, y1 = crop
        a = self.alpha[y0:y1, x0:x1].astype(np.float64)
        if obj is not None:
            (bx0, by0, bx1, by1), m = self.objects[obj]
            full = np.zeros(self.alpha.shape, bool)
            full[by0:by1, bx0:bx1] = m
            a = a * full[y0:y1, x0:x1]
        return self.rgb[y0:y1, x0:x1], a


def alpha_sheet(path: Path) -> Sheet:
    """Un foglio PNG con la trasparenza già fatta (per esempio da ChatGPT). I bordi sfumati hanno
    colori sporchi: conta come pieno solo quello che è opaco almeno a metà."""
    im = np.asarray(Image.open(path).convert("RGBA"))
    rgb = np.asarray(Image.fromarray(im[..., :3]).filter(ImageFilter.MedianFilter(3)), np.float64) / 255.0
    return Sheet(rgb=rgb, alpha=(im[..., 3] >= 128).astype(np.uint8))


def plain_sheet(path: Path) -> Sheet:
    """Un'immagine piena, senza fondo da togliere (per esempio una parete vista di fronte)."""
    src = Image.open(path).convert("RGB").filter(ImageFilter.MedianFilter(3))
    rgb = np.asarray(src, np.float64) / 255.0
    s = Sheet.__new__(Sheet)
    s.rgb, s.alpha, s.objects = rgb, np.ones(rgb.shape[:2], np.uint8), []
    return s


def unmagenta(col: np.ndarray) -> np.ndarray:
    """Le reti, le grate e i vetri lasciano passare il magenta del fondo: lo si toglie dappertutto,
    non solo sui bordi."""
    m = px.magentaness(col)
    out = col.copy()
    for ch in (0, 2):
        out[..., ch] = np.where(m > 0.03, col[..., ch] - (m - 0.01), col[..., ch])
    return out.clip(0, 1)


def resample(rgb: np.ndarray, a: np.ndarray, w: int, h: int):
    """Riduce colore e alfa a w x h con la media d'area, pesando il colore con l'alfa."""
    w, h = max(1, w), max(1, h)
    a_img = Image.fromarray((a * 255).astype(np.uint8)).resize((w, h), Image.BOX)
    ah = np.asarray(a_img, np.float64) / 255.0
    prem = Image.fromarray((rgb * a[..., None] * 255).astype(np.uint8)).resize((w, h), Image.BOX)
    col = np.where(ah[..., None] > 0, np.asarray(prem, np.float64) / 255.0 / np.maximum(ah[..., None], 1e-3), 0.0)
    alpha = (ah >= 0.5).astype(np.uint8)
    return px.despill(col.clip(0, 1), alpha), alpha


class Canvas:
    """Un piano in costruzione: colore (0-1), alfa (0/1) e, per pixel, se va contornato."""

    def __init__(self, w: int, h: int):
        self.rgb = np.zeros((h, w, 3))
        self.a = np.zeros((h, w), np.uint8)
        self.ring = np.zeros((h, w), bool)

    def paste(self, rgb: np.ndarray, a: np.ndarray, x: int, y: int, outline: bool = False, ink: bool = False):
        """Con `outline` il pezzo ha il contorno scuro dove sotto non c'è niente; con `ink` anche dove
        sotto c'è già qualcosa (un muro, il pavimento): lì il contorno si dipinge subito."""
        h, w = a.shape
        X0, Y0 = max(0, x), max(0, y)
        X1, Y1 = min(self.a.shape[1], x + w), min(self.a.shape[0], y + h)
        if X0 >= X1 or Y0 >= Y1:
            return
        sa = a[Y0 - y:Y1 - y, X0 - x:X1 - x] > 0
        self.rgb[Y0:Y1, X0:X1][sa] = rgb[Y0 - y:Y1 - y, X0 - x:X1 - x][sa]
        self.a[Y0:Y1, X0:X1][sa] = 1
        # Quello che si posa sopra copre anche il contorno di chi sta sotto.
        self.ring[Y0:Y1, X0:X1][sa] = False
        if outline:
            pad = np.pad(a > 0, 1)
            ring = (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]) & ~(a > 0)
            # Il contorno anche appena fuori dal pezzo.
            gx0, gy0 = x - 1, y - 1
            GX0, GY0 = max(0, gx0), max(0, gy0)
            GX1, GY1 = min(self.a.shape[1], gx0 + w + 2), min(self.a.shape[0], gy0 + h + 2)
            r = np.zeros((h + 2, w + 2), bool)
            r[1:-1, 1:-1] = ring
            edge = np.zeros((h + 2, w + 2), bool)
            edge[0, 1:-1] = a[0] > 0
            edge[-1, 1:-1] = a[-1] > 0
            edge[1:-1, 0] = a[:, 0] > 0
            edge[1:-1, -1] = a[:, -1] > 0
            r |= edge
            sub = r[GY0 - gy0:GY1 - gy0, GX0 - gx0:GX1 - gx0]
            self.ring[GY0:GY1, GX0:GX1] |= sub
            if ink:
                on = sub & (self.a[GY0:GY1, GX0:GX1] > 0)
                self.rgb[GY0:GY1, GX0:GX1][on] = np.array(px.OUTLINE[:3]) / 255.0

    def put(self, sheet: Sheet, crop, anchor, target, obj: int | None = None, outline: bool = False,
            tint=None, despill_all: bool = False, drop_dark_top: bool = False, flip: bool = False,
            ink: bool = False) -> tuple[int, int, int, int]:
        """Mette un pezzo del foglio sul piano: la parte `anchor` del foglio (x0, y0, x1, y1) finisce
        esattamente sul riquadro `target` del piano; il resto di `crop` segue con la stessa scala.
        Con `flip` il pezzo si specchia (l'àncora resta sul suo riquadro)."""
        ax0, ay0, ax1, ay1 = anchor
        tx0, ty0, tx1, ty1 = target
        sx = (tx1 - tx0) / (ax1 - ax0)
        sy = (ty1 - ty0) / (ay1 - ay0)
        cx0, cy0, cx1, cy1 = crop
        rgb, a = sheet.piece(crop, obj)
        w, h = round((cx1 - cx0) * sx), round((cy1 - cy0) * sy)
        col, al = resample(rgb, a, w, h)
        if despill_all:
            col = unmagenta(col)
        if drop_dark_top:
            # Il contorno scuro del foglio in cima a una striscia da ripetere: via il primo pixel
            # di ogni colonna, se è scuro.
            for xx in range(al.shape[1]):
                for _ in range(3):
                    nz = np.nonzero(al[:, xx])[0]
                    if len(nz) < 4:
                        break
                    top, below = col[nz[0], xx].mean(), col[nz[3], xx].mean()
                    if top >= 0.3 and top >= 0.8 * below:
                        break
                    al[nz[0], xx] = 0
        if tint is not None:
            col = tint(col, al)
        if flip:
            col, al = col[:, ::-1], al[:, ::-1]
            x = tx1 - round((cx1 - ax0) * sx)
        else:
            x = tx0 + round((cx0 - ax0) * sx)
        y = ty0 + round((cy0 - ay0) * sy)
        self.paste(col, al, x, y, outline, ink)
        return x, y, w, h

    def finish(self, colors: int, seed: int = 1, outline_color=px.OUTLINE) -> np.ndarray:
        """Palette comune del piano, pulizia e contorni: l'immagine RGBA finale."""
        lab = px.to_oklab(self.rgb)
        pal = px.kmeans_palette(lab.reshape(-1, 3), colors, seed=seed, weights=self.a.reshape(-1).astype(np.float64))
        idx = px.map_to_palette(lab, pal)
        idx = px.majority_clean(idx, self.a, 1)
        pal_rgb = (px.from_oklab(pal) * 255 + 0.5).clip(0, 255).astype(np.uint8)
        out = np.zeros((*idx.shape, 4), np.uint8)
        out[..., :3] = pal_rgb[idx]
        out[..., 3] = self.a * 255
        ring = self.ring & (self.a == 0)
        out[ring] = (*outline_color, 255)
        return out


## L'ombra di contatto riga per riga, dalla riga dei piedi (0): sopra è il pavimento dietro la base,
## sotto quello davanti.
_SHADOW_ROWS = {-6: 0.25, -5: 0.4, -4: 0.55, -3: 0.7, -2: 0.85, -1: 1.0, 0: 1.0, 1: 0.95, 2: 0.8, 3: 0.6, 4: 0.4,
                5: 0.2}


def ground_shadow(cv: Canvas, x0: int, x1: int, base: int = FLOOR, k: float = 0.6, left: int = 4,
                  right: int = 9) -> None:
    """L'ombra di contatto, da fare prima di posare un oggetto sul pavimento: scurisce il pavimento
    sotto la sua base (x0-x1, in px del piano) e attorno, più forte sulla riga dei piedi. Sfuma verso
    il basso e verso i lati, ed è più lunga a destra, perché la luce viene dall'alto a sinistra.
    Dev'essere netta: la palette del piano si mangia le differenze piccole."""
    H, W = cv.a.shape
    for xx in range(max(0, x0 - left), min(W, x1 + right)):
        if xx < x0:
            hk = (xx - (x0 - left) + 1) / (left + 1)
        elif xx >= x1:
            hk = (x1 + right - xx) / (right + 1)
        else:
            hk = 1.0
        for dy, vk in _SHADOW_ROWS.items():
            if 0 <= base + dy < H:
                cv.rgb[base + dy, xx] *= 1.0 - k * hk * vk


def settle(cv: Canvas, x0: int, x1: int, bottom: int = FLOOR, ks=(0.7, 0.79, 0.87, 0.94)) -> None:
    """Dopo aver posato un oggetto sul pavimento: le sue ultime righe sopra `bottom` un poco più scure,
    dove arriva meno luce, così la base non sembra staccata da terra."""
    for i, k in enumerate(ks):
        cv.rgb[bottom - 1 - i, max(0, x0):x1] *= k


def tuft_stamps(cv: Canvas, y0: int, y1: int, x0: int, x1: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """I ciuffi d'erba già dipinti nel pavimento (nel riquadro x0-x1, y0-y1 del piano, dove c'è solo il
    pavimento): ognuno è un timbro, colore e maschera, da ripetere davanti alla base degli oggetti."""
    from scipy import ndimage
    rgb, a = cv.rgb[y0:y1, x0:x1], cv.a[y0:y1, x0:x1] > 0
    green = a & (rgb[..., 1] > rgb[..., 0] + 0.03) & (rgb[..., 1] > rgb[..., 2] + 0.03)
    lab, _ = ndimage.label(green, structure=np.ones((3, 3)))
    stamps = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if 3 <= h <= 8 and 4 <= w <= 11:
            stamps.append((rgb[sl].copy(), lab[sl] == i))
    return stamps


def put_tufts(cv: Canvas, stamps, x0: int, x1: int, rng: np.random.Generator, base: int = FLOOR,
              every: int = 28) -> None:
    """Qualche ciuffo davanti alla base di un oggetto (x0-x1): uno per angolo, che li nasconde, e altri
    ogni `every` px. Nascono nel pavimento davanti, poco sotto la riga dei piedi, e coprono le ultime
    righe della base: è il terreno che passa davanti, e l'oggetto ci sta dentro."""
    if not stamps:
        return
    xs = [x0 - 3, x1 - 5] + [int(v) for v in rng.integers(x0 + 6, max(x0 + 7, x1 - 10), max(0, (x1 - x0) // every - 1))]
    for x in xs:
        rgb, m = stamps[int(rng.integers(len(stamps)))]
        if rng.random() < 0.5:
            rgb, m = rgb[:, ::-1], m[:, ::-1]
        h, w = m.shape
        yb = base + int(rng.integers(2, 4))
        X0, X1 = max(0, x), min(cv.a.shape[1], x + w)
        if X1 <= X0:
            continue
        sub = m[:, X0 - x:X1 - x]
        cv.rgb[yb - h:yb, X0:X1][sub] = rgb[:, X0 - x:X1 - x][sub]
        cv.a[yb - h:yb, X0:X1][sub] = 1
        cv.ring[yb - h:yb, X0:X1][sub] = False


def shade(k: float, blue: float = 0.0):
    """Tinta per le cose in ombra: scurisce di k e tira un poco al blu."""
    def f(col, _a):
        c = col * k
        c[..., 2] = c[..., 2] + blue
        return c.clip(0, 1)
    return f


def haze(amount: float, color=(0.80, 0.66, 0.62)):
    """Foschia: avvicina i colori a quello dell'orizzonte, per i piani lontani."""
    hc = np.array(color)
    def f(col, _a):
        return (col * (1 - amount) + hc * amount).clip(0, 1)
    return f


def blit(screen: Image.Image, im: Image.Image, x: int, y: int, alpha: float = 1.0) -> None:
    """Compone `im` sullo schermo in (x, y), anche se esce dai bordi, con un'opacità in più."""
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(screen.width, x + im.width), min(screen.height, y + im.height)
    if x0 >= x1 or y0 >= y1 or alpha <= 0:
        return
    part = im.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    if alpha < 1:
        a = np.asarray(part.getchannel("A"), np.float64) * alpha
        part.putalpha(Image.fromarray(a.astype(np.uint8)))
    screen.alpha_composite(part, (x0, y0))


def layer_alpha(layer: dict, cam_x: int) -> float:
    """Quanto si vede un piano con la telecamera in cam_x: lo stesso conto di Backdrop.alpha()."""
    x_from, x_to = layer.get("x_from", -(1 << 30)), layer.get("x_to", 1 << 30)
    if cam_x < x_from or cam_x > x_to:
        return 0.0
    a = 1.0
    if layer.get("fade_in", 0) > 0:
        a = min(a, (cam_x - x_from) / layer["fade_in"])
    if layer.get("fade_out", 0) > 0:
        a = min(a, (x_to - cam_x) / layer["fade_out"])
    return max(0.0, min(1.0, a))


GIG_SPRITE = ROOT / "game/assets/sprites/gig/gig.png"


def screenshot(layers: list[dict], scenes: list[tuple[Image.Image, int, int]], cam_ref_y: int, cam_x: int, cam_y: int,
               gig: tuple[int, int] | None = None) -> Image.Image:
    """Una schermata composta come nel gioco: i piani (le voci di layers.json, con l'immagine in
    "im"), le scene del campo di gioco e GIG coi piedi in `gig` (x, y del mondo)."""
    screen = Image.new("RGBA", (VIEW_W, VIEW_H), (40, 36, 48, 255))
    cam_dy = cam_y - cam_ref_y

    def draw(ls):
        for l in sorted(ls, key=lambda l: l["z"]):
            x = -round((cam_x - l.get("origin_x", 0)) * l["scroll"])
            blit(screen, l["im"], x, l["y"] - round(cam_dy * l["scroll_y"]), layer_alpha(l, cam_x))

    draw([l for l in layers if l["z"] < 0])
    for im, sx, sy in scenes:
        blit(screen, im, sx - cam_x, sy - cam_y)
    if gig is not None:
        sprite = Image.open(GIG_SPRITE).convert("RGBA").crop((203, 380, 263, 494))
        blit(screen, sprite, gig[0] - 24 - cam_x, gig[1] - 111 - cam_y)
    draw([l for l in layers if l["z"] >= 0])
    return screen


def contact_sheet(tiles: list[Image.Image], dest: Path, cols: int = 2, zoom: int = 2) -> None:
    """Le schermate una accanto all'altra, ingrandite senza sfumare."""
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGBA", (VIEW_W * cols, VIEW_H * rows), (0, 0, 0, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * VIEW_W, (i // cols) * VIEW_H))
    sheet.resize((sheet.width * zoom, sheet.height * zoom), Image.NEAREST).save(dest)


def backlit(cv: Canvas, rim=(0.13, 0.065, 0.04), dark_k: float = 0.30, dark_add=(0.012, 0.008, 0.035),
            lamp=None, rim_left: bool = True) -> None:
    """Il controluce del primo piano: tutto scuro, un filo di luce sui bordi di sopra (e, se c'è, di
    sinistra); `lamp(rgb)` dice quali pixel restano accesi (i lumini, le lampade)."""
    on = cv.a > 0
    lit = lamp(cv.rgb) if lamp is not None else np.zeros_like(on)
    dark = cv.rgb * dark_k + np.array(dark_add)
    out_rgb = np.where(lit[..., None], cv.rgb * 0.95, dark)
    open_side = np.zeros_like(on)
    if rim_left:
        open_side[:, 1:] = ~on[:, :-1]
        open_side[:, 0] = True
    up_open = np.zeros_like(on)
    up_open[1:] = ~on[:-1]
    edge = on & (open_side | up_open) & ~lit
    out_rgb[edge] = dark[edge] + np.array(rim)
    cv.rgb = out_rgb.clip(0, 1)
