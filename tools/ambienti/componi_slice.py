# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""«Sotto la Linea»: il fondale della strada dei Tamburi (backdrop) dalle basi ridipinte con ChatGPT.

Le basi nascono dalla composizione frontale del gioco (backdrop sopra floor, ingrandita 3x, con i varchi
in magenta), tagliata in quattro pezzi ai confini dei negozi: ChatGPT ridipinge ogni pezzo tenendo le
posizioni, con le insegne vuote. Qui ogni base si riporta alla scala del gioco, si allinea il piede delle
facciate alla riga del marciapiede, si riduce in pixel art con una palette sola per tutta la strada e si
scrivono le insegne con i caratteri di pixfont (accenti giusti, niente testo inventato dall'AI). Dalle
vetrine accese, dalle insegne e dai lumini nasce la mappa emissiva.

Escono backdrop.png e backdrop_emis.png (2400×187), più un'anteprima. Dove una base manca, resta il
backdrop di prima.

Uso:

    python -I tools/ambienti/componi_slice.py [--basi CARTELLA] [--uscita CARTELLA]

Il codice è MIT, come il resto del gioco; le basi non stanno nel repo.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "env"))
from piani import ROOT  # noqa: E402
import pixelizza as px  # noqa: E402
import pixfont as PF  # noqa: E402

GAME = ROOT / "game/assets/env/sotto_la_linea"
BASI = ROOT.parent / "ctrlaltrevenge-lab-condiviso/ambienti-ai/sotto-la-linea/strada"
OUT = ROOT / "tools/out/ambienti/sotto_la_linea"

W, H = 2400, 187          # il backdrop
CUT = 180                 # sotto questa riga il backdrop è trasparente: c'è floor.png
FOOT = 178                # il piede delle facciate nel gioco
K = 3                     # la scala delle basi rispetto al gioco

# I pezzi: file, x di inizio e fine sullo schermo (come i ritagli in_P*.png), da dove si comincia a
# usarlo (per le sovrapposizioni), la riga del piede delle facciate nella base, a scala 270, e quanto
# pareggiarne i colori su quelli di P1 e P2 (ChatGPT fa ogni pezzo un po' più caldo o più freddo).
PEZZI = [
    ("s01_P1_v1.png", 0, 752, 0, 185, 0.0),
    ("s02_P2_v1.png", 750, 1425, 752, 185, 0.0),
    ("s03_P3_v1.png", 1425, 1965, 1425, 185, 0.8),
    ("s04_P4_v1.png", 1920, 2400, 1965, 185, 0.6),
]

# Dove ChatGPT ha dipinto qualcosa di semitrasparente sul magenta (i coni di luce delle lampade
# dell'arena): lì ogni pixel che tira al magenta, o col rosso quasi pieno (luce sopra il magenta), torna
# magenta, cioè trasparente. La luce la fa il gioco.
# (x0, y0, x1, y1) sullo schermo.
TO_KEY = [(2060, 40, 2330, 63)]


def base_hi(path: Path, x0: int, x1: int, foot: float) -> np.ndarray:
    """La base alla scala K del gioco, col piede delle facciate a FOOT: (H*K, (x1-x0)*K, 3)."""
    im = Image.open(path).convert("RGB")
    w = (x1 - x0) * K
    h = round(270 * K * FOOT / foot)
    a = np.asarray(im.resize((w, h), Image.BOX))
    return a[:H * K]


def _lab_mask(b: np.ndarray):
    rgb = b.astype(np.float64) / 255.0
    lab = px.to_oklab(rgb)
    m = px.magentaness(rgb) < 0.5
    m[FOOT * K:] = False
    return lab, m


def stats(pieces: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Media e deviazione dei colori (OKLab) delle facciate dei pezzi di riferimento."""
    v = np.concatenate([lab[m] for lab, m in map(_lab_mask, pieces)])
    return v.mean(0), v.std(0)


def match(b: np.ndarray, ref: tuple[np.ndarray, np.ndarray], k: float) -> np.ndarray:
    """Porta media e contrasto dei colori del pezzo verso quelli di riferimento, con forza k."""
    lab, m = _lab_mask(b)
    keep = px.magentaness(b.astype(np.float64) / 255.0) >= 0.5
    v = lab[~keep]
    mu, sd = lab[m].mean(0), lab[m].std(0)
    new = (v - mu) / np.maximum(sd, 1e-4) * ref[1] + ref[0]
    lab[~keep] = v * (1 - k) + new * k
    out = (px.from_oklab(lab) * 255 + 0.5).clip(0, 255).astype(np.uint8)
    out[keep] = b[keep]
    return out


def compose(basi: Path) -> tuple[np.ndarray, np.ndarray]:
    """Il backdrop nuovo e una maschera dei tratti rifatti."""
    old = np.asarray(Image.open(GAME / "backdrop.png").convert("RGBA"))
    hi = np.zeros((H * K, W * K, 3), np.uint8)
    hi[...] = (255, 0, 255)
    done = np.zeros(W, bool)
    ref = stats([base_hi(basi / n, x0, x1, f) for n, x0, x1, _u, f, k in PEZZI if k == 0 and (basi / n).exists()])
    for name, x0, x1, use0, foot, k in PEZZI:
        p = basi / name
        if not p.exists():
            print("manca", name, "- resta il backdrop di prima")
            continue
        b = base_hi(p, x0, x1, foot)
        if k:
            b = match(b, ref, k)
        s = use0 - x0
        hi[:, use0 * K:x1 * K] = b[:, s * K:]
        done[use0:x1] = True
    for x0, y0, x1, y1 in TO_KEY:
        r = hi[y0 * K:y1 * K, x0 * K:x1 * K]
        r[(px.magentaness(r.astype(np.float64) / 255.0) > 0.06) | (r[..., 0] > 225)] = (255, 0, 255)
    rgba, _ = px.pixelize(Image.fromarray(hi), (W, H), 72, key_magenta=True, seed=3, denoise=3)
    # Sotto CUT c'è floor.png, ma non dappertutto: dove il pavimento è trasparente (soglie, gradini,
    # piedi dei pilastri del backdrop vecchio) il backdrop resta pieno, se no si vede il piano dietro.
    floor = np.asarray(Image.open(GAME / "floor.png").convert("RGBA"))[CUT - 162:H - 162, :, 3]
    rgba[CUT:, :, 3] = np.where(floor > 0, 0, 255)
    out = old.copy()
    out[:, done] = rgba[:, done]
    return out, done


# ---------------------------------------------------------------------------------------------
# Il piano near (1440×210, parallasse 0,5): la seconda fila di palazzine dietro la strada. Si vede solo
# da tre finestre del backdrop: il varco del lotto (la torre di SIDERA sta nel far, e lì il near resta
# basso), il cielo sopra la recinzione della bonifica (il cartellone MANODOPERA) e l'arena (il maxischermo
# di Pasqua; a sinistra resta vuoto, perché dietro si vedono le cupole). Le basi nascono da tre schizzi
# nostri (near/in_n1..3.png, a 3x), ridipinti da ChatGPT; fuori dai pezzi il near è trasparente.

NW, NH = 1440, 210
NEAR_ROWS = 150           # ogni pezzo è alto 150 righe; sotto si allunga la sua ultima riga (non si vede)
NEAR_BASI = BASI.parent / "near"
# (base, x0, x1, dy): n2 e n3 scendono, perché la trave della fg copre le righe 0-33 e il cartellone e il
# maxischermo devono stare sotto; i loro tetti finiscono dietro la strada. Il maxischermo scende meno:
# nell'arena, sotto la riga 65, c'è la cima della recinzione.
NEAR_DY, NEAR_DY_M = 18, 12
NEAR_PEZZI = [("n01_N1_v1.png", 0, 330, 0), ("n02_N2_v1.png", 330, 770, NEAR_DY),
              ("n03_N3_v1.png", 1040, 1440, NEAR_DY_M)]
NEAR_FOG, NEAR_FOG_K = np.array([46, 34, 70.0]), 0.22    # più lontano della strada: un velo prugna


def compose_near(basi: Path) -> np.ndarray:
    hi = np.zeros((NH * K, NW * K, 3), np.uint8)
    hi[...] = (255, 0, 255)
    for name, x0, x1, dy in NEAR_PEZZI:
        p = basi / name
        if not p.exists():
            print("manca", name, "- lì il near resta vuoto")
            continue
        b = np.asarray(Image.open(p).convert("RGB").resize(((x1 - x0) * K, NEAR_ROWS * K), Image.BOX))
        y0, y1 = dy * K, (dy + NEAR_ROWS) * K
        hi[y0:y1, x0 * K:x1 * K] = b
        hi[y1:, x0 * K:x1 * K] = b[-1]
    rgba, _ = px.pixelize(Image.fromarray(hi), (NW, NH), 48, key_magenta=True, seed=5, denoise=3)
    rgb = rgba[..., :3].astype(np.float64)
    lit = emissiva(rgba)[..., 3] > 0
    fog = rgb * (1 - NEAR_FOG_K) + NEAR_FOG * NEAR_FOG_K
    rgb[~lit] = fog[~lit]
    rgba[..., :3] = rgb.clip(0, 255).astype(np.uint8)
    rgba[rgba[..., 3] == 0, :3] = 0
    return rgba


# ---------------------------------------------------------------------------------------------
# Le insegne. Le scrive il codice, mai l'AI: le coordinate sono quelle dei pannelli vuoti delle basi.
# Il 17 aprile 2087 è il Giovedì Santo e Pasqua cade il 20: «FINE LAVORI: PASQUA 2087» è fra tre giorni.

F5, F3 = PF.FONT5x7, PF.FONT3x5
MINT = (150, 215, 180)        # il marchio ARIA+, poco e verso il verde (il ciano è di GIG)


def _mask(text: str, font, scale: int = 1, sy: int = 1, spacing: int = 1) -> np.ndarray:
    m = PF.render(text, font, scale, spacing)
    return np.repeat(m, sy, axis=0) if sy > 1 else m


def _put(img: np.ndarray, m: np.ndarray, x: int, y: int, col) -> None:
    h, w = m.shape
    img[y:y + h, x:x + w, :len(col)][m] = col
    if img.shape[2] == 4 and len(col) == 3:
        img[y:y + h, x:x + w, 3][m] = 255


def _outline(m: np.ndarray) -> np.ndarray:
    p = np.pad(m, 1)
    o = np.zeros_like(p)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            o |= np.roll(np.roll(p, dy, 0), dx, 1)
    return o & ~p


class Insegne:
    """Disegna sul backdrop (RGBA) e sulla mappa emissiva (RGBA) insieme."""

    def __init__(self, img: np.ndarray, emis: np.ndarray):
        self.img, self.emis = img, emis

    def rect(self, x0, y0, x1, y1, col, border=None, glow=None, grime=0.0):
        self.img[y0:y1, x0:x1, :3] = col
        self.img[y0:y1, x0:x1, 3] = 255
        if grime:
            # carta e lamiera di notte: macchie, sporco dal basso e qualche puntino di ruggine
            r = np.random.default_rng(x0 * 7 + y0)
            n = r.uniform(1 - grime, 1, (y1 - y0, x1 - x0))
            n *= np.linspace(1, 1 - grime, y1 - y0)[:, None]
            reg = self.img[y0:y1, x0:x1, :3].astype(np.float64) * n[..., None]
            spot = r.random((y1 - y0, x1 - x0)) < grime * 0.25
            reg[spot] = reg[spot] * 0.6 + np.array([120, 60, 36]) * 0.4
            self.img[y0:y1, x0:x1, :3] = reg.astype(np.uint8)
        if border is not None:
            for sl in ((slice(y0, y0 + 1), slice(x0, x1)), (slice(y1 - 1, y1), slice(x0, x1)),
                       (slice(y0, y1), slice(x0, x0 + 1)), (slice(y0, y1), slice(x1 - 1, x1))):
                self.img[sl[0], sl[1], :3] = border
        if glow is not None:
            self.emis[y0:y1, x0:x1] = (*glow, 255)

    def text(self, s, x, y, col, font=F5, scale=1, sy=1, center=False, outline=None, glow=None,
             spacing=1, spray=False):
        m = _mask(s, font, scale, sy, spacing)
        if spray:
            # a mano: corsivo (le righe alte spostate di un pixel), qualche buco, le colature
            h = m.shape[0]
            m = np.pad(m, ((0, 0), (0, 2)))
            for yy in range(h):
                m[yy] = np.roll(m[yy], 2 - (yy * 3) // h)
            r = np.random.default_rng(len(s) * 31 + x)
            m &= r.random(m.shape) > 0.07
        if center:
            x -= m.shape[1] // 2
        if outline is not None:
            o = _outline(m)
            _put(self.img, o, x - 1, y - 1, outline)
        _put(self.img, m, x, y, col)
        if spray:
            r = np.random.default_rng(x + y)
            for xx in r.choice(np.nonzero(m[-1])[0], 3, replace=False):
                self.img[y + m.shape[0]:y + m.shape[0] + int(r.integers(2, 6)), x + xx, :3] =                     (np.array(col) * 0.8).astype(np.uint8)
        if glow is not None:
            _put(self.emis, m, x, y, glow)
        return m.shape[1]

    def lines(self, rows, x, y, font=F3, gap=1):
        """rows: (testo, colore); centrate su x."""
        for s, col in rows:
            self.text(s, x, y, col, font, center=True)
            y += len(font["A"]) + gap

    def rust(self, x0, y0, x1, y, col, seed):
        """Una riga illeggibile: tratti corti, come lettere consumate."""
        r = np.random.default_rng(seed)
        x = x0
        while x < x1 - 1:
            n = int(r.integers(1, 4))
            self.img[y, x:min(x + n, x1), :3] = col
            x += n + int(r.integers(1, 3))


def insegne(img: np.ndarray, emis: np.ndarray) -> None:
    d = Insegne(img, emis)
    DARK, RED, CREAM = (40, 26, 34), (150, 32, 28), (226, 208, 182)

    # T1, l'angolo dell'edicola: la targa di ferro corroso.
    d.rect(8, 133, 52, 149, (74, 48, 38), border=(44, 28, 26))
    for i in range(6):
        d.img[134 + (i * 5) % 14, 9 + i * 7:12 + i * 7, :3] = (120, 62, 36)   # colature di ruggine
    d.rust(11, 136, 49, 136, (128, 96, 76), 1)
    d.text("MALEDICONO", 30, 140, (170, 128, 98), F3, center=True)
    d.rust(11, 146, 49, 146, (128, 96, 76), 2)

    # Il cartello del Wind Day sulla lamiera, coperto dall'adesivo di ARIA+.
    d.rect(82, 97, 134, 125, (176, 164, 150), border=(110, 98, 92), grime=0.25)
    d.text("WIND DAY", 108, 99, RED, F3, center=True)
    for yy, s in ((105, 3), (121, 4)):
        d.rust(86, yy, 130, yy, (130, 124, 116), s)
    d.rect(76, 107, 141, 120, (200, 204, 190), border=MINT, grime=0.12)
    d.lines([("AVVISO SUPERATO", (60, 120, 92)), ("ARIA CERTIFICATA", DARK)], 108, 108)

    # Il pannello del lotto.
    d.rect(148, 106, 209, 131, (180, 164, 154), border=(100, 86, 84), grime=0.22)
    d.rect(149, 107, 208, 109, MINT)
    d.lines([("CANTIERE ARIA+", DARK), ("VIETATO", RED), ("L'ACCESSO", RED)], 178, 111)

    # Il panificio: lettere dipinte sulla tavola chiara.
    d.text("PANIFICIO", 379, 55, (118, 34, 26), F5, scale=2, center=True)

    # Il portone 17.
    d.rect(549, 85, 559, 92, (190, 170, 120), border=(90, 70, 50))
    d.text("17", 554, 86, DARK, F3, center=True)

    # La tabaccheria: la T bianca sul blu, accesa; la tavola con le due righe.
    d.text("T", 567, 50, (238, 238, 232), F5, scale=3, center=True, glow=(150, 150, 160))
    d.text("TABACCHI · LOTTO", 657, 54, (30, 36, 70), F5, center=True)
    d.text("RICARICHE ARIA+ · MANODOPERA", 657, 64, (118, 34, 26), F3, center=True)

    # Lo striscione sulla recinzione del cantiere.
    d.lines([("BONIFICA ARIA+", DARK), ("LAVORI IN CORSO", DARK), ("FINE LAVORI:", DARK),
             ("PASQUA 2087", RED)], 799, 99, gap=2)
    # REVENGE, nello stile di Totò, sulla lamiera vuota.
    d.text("REVENGE", 850, 149, (238, 168, 58), F5, sy=2, outline=(48, 20, 36), spray=True)

    # Il kebab: la tavola è accesa da dietro.
    d.emis[43:63, 936:1103] = (90, 52, 22, 255)
    w = d.text("KEBAB", 946, 46, (124, 28, 20), F5, scale=2)
    d.text("· PANZEROTTI", 946 + w + 8, 50, (124, 28, 20), F5)

    # Il cancello: VENDESI e la scritta a spray.
    d.rect(1180, 112, 1214, 121, (184, 174, 160), border=(130, 40, 34), grime=0.2)
    d.text("VENDESI", 1197, 114, (176, 34, 30), F3, center=True)
    d.text("ARIA VERA", 1148, 146, (196, 190, 160), F5, sy=2, outline=(40, 30, 40), spray=True)

    # La farmacia: lettere verdi accese, come la croce.
    d.text("FARMACIA", 1312, 49, (120, 236, 120), F5, scale=2, center=True, glow=(40, 150, 40))
    cr = img[38:72, 1400:1428, :3].astype(int)                                  # la croce della base
    verde = (cr[..., 1] > 120) & (cr[..., 1] > cr[..., 0] + 40)
    emis[38:72, 1400:1428][verde] = (40, 150, 40, 255)

    # La serranda di P3: la scritta e l'avviso.
    d.text("MALEDICONO", 1530, 112, (196, 58, 48), F5, sy=2, outline=(36, 22, 34), spray=True)
    d.rect(1556, 141, 1598, 151, (176, 166, 156), border=(150, 34, 30), grime=0.2)
    d.text("AFFITTASI", 1577, 144, (176, 34, 30), F3, center=True)
    # I manifesti funebri: bianchi, il bordo nero, la croce, niente nomi.
    for x0, y0, x1, y1 in ((1621, 123, 1636, 144), (1627, 146, 1641, 164)):
        d.rect(x0, y0, x1, y1, (176, 172, 168), border=(24, 22, 26), grime=0.2)
        cx = (x0 + x1) // 2
        d.img[y0 + 2:y0 + 5, cx, :3] = (24, 22, 26)
        d.img[y0 + 3, cx - 1:cx + 2, :3] = (24, 22, 26)
        for k, yy in enumerate(range(y0 + 7, y1 - 2, 2)):
            d.rust(x0 + 2, yy, x1 - 2, yy, (110, 108, 110), 10 + k + x0)

    # L'osteria: la tavola e la lavagna (allargata, perché PANZEROTTI ci stia).
    d.text("OSTERIA", 1747, 89, (222, 184, 112), F5, scale=2, center=True)
    d.rect(1808, 119, 1850, 152, (34, 40, 38), border=(120, 80, 46))
    d.lines([("COZZE", (206, 206, 196)), ("PANZEROTTI", (206, 206, 196)), ("VINO", (206, 206, 196))],
            1829, 124, gap=4)

    # Il MiniBar: il neon sulla tavola, BAR sulla bandiera accesa, la TV.
    d.text("MINIBAR", 1898, 88, (255, 214, 130), F5, sy=2, center=True, glow=(200, 120, 50))
    for i, ch in enumerate("BAR"):
        d.text(ch, 1951, 90 + i * 7, (110, 30, 20), F3, center=True)
    d.emis[83:118, 1945:1958] = (110, 60, 20, 255)
    d.emis[123:139, 1875:1896] = (70, 76, 64, 255)


# ---------------------------------------------------------------------------------------------
# Il piano fg (2880×33, parallasse 1,25): il ventre della galleria della Linea, sopra la strada. La base
# di ChatGPT (fg/f01_FG_v1.png, dal nostro schizzo fg/in_fg.png) ha la striscia più alta del previsto,
# quindi non si schiaccia: si taglia nei suoi pannelli di traliccio (da montante a montante) e si
# ricompone a 6x, con ogni pannello largo 48,5 px (6 pannelli = 291, il passo delle lampade del gioco).
# Ogni 6 pannelli: quello con la lampada (a x 65 + 291k, dove stanno le luci di sotto_la_linea.json),
# tre pannelli lisci e, una campata sì e una no, la targa «LINEA 3», larga due pannelli.

FW, FH, FK = 2880, 33, 6
FG_BASE = BASI.parent / "fg" / "f01_FG_v1.png"
FG_ROWS = (240, 411)                                  # la striscia dentro la base
FG_LAMPADA = (1079, 1348)                             # pannelli della base, in colonne
FG_TARGA = (1622, 2163)
FG_LISCI = [(264, 537), (537, 811), (811, 1079), (1348, 1622)]
FG_CELLA, FG_LAMP_DX = 291, 248                       # a 6x: un pannello, e la lampada dentro il suo


def compose_fg(base: Path) -> tuple[np.ndarray, list[int]]:
    b = Image.open(base).convert("RGB").crop((0, FG_ROWS[0], 2170, FG_ROWS[1]))
    hh = FH * FK

    def cella(x0, x1, n=1):
        return np.asarray(b.crop((x0, 0, x1, b.height)).resize((FG_CELLA * n, hh), Image.LANCZOS))
    lamp, targa = cella(*FG_LAMPADA), cella(*FG_TARGA, 2)
    lisci = [cella(*c) for c in FG_LISCI]
    hi = np.zeros((hh, FW * FK, 3), np.uint8)
    hi[...] = (255, 0, 255)
    r = np.random.default_rng(3)
    prev, targhe = -1, []
    x0 = 65 * FK - FG_LAMP_DX - FG_CELLA                # la prima cella, a sinistra dello schermo
    j = -1
    while x0 < FW * FK:
        m = j % 6
        if m == 0:
            t = lamp
        elif m == 3 and (j // 6) % 2 == 0:            # la targa una campata sì e una no
            t = targa
            targhe.append(x0)
        elif m == 4 and (j // 6) % 2 == 0:
            j, x0 = j + 1, x0 + FG_CELLA
            continue
        else:
            k = int(r.integers(len(lisci) - (prev >= 0)))
            k += prev >= 0 and k >= prev                # mai due pannelli uguali di fila
            prev, t = k, lisci[k]
        a, z = max(0, x0), min(FW * FK, x0 + t.shape[1])
        hi[:, a:z] = t[:, a - x0:z - x0]
        j, x0 = j + 1, x0 + FG_CELLA
    rgba, _ = px.pixelize(Image.fromarray(hi), (FW, FH), 40, key_magenta=True, seed=7, denoise=3)
    # È il piano più vicino e sta in controluce: più scuro, e la ruggine meno accesa (resta nelle
    # scanalature). Le lenti delle lampade non si toccano.
    rgb = rgba[..., :3].astype(np.float64)
    lum = rgb.mean(-1, keepdims=True)
    k = (lum[..., 0] < 150)[..., None]
    dark = (lum + (rgb - lum) * 0.6) * 0.7 + np.array([22, 20, 30.0]) * 0.3
    rgba[..., :3] = np.where(k, dark, rgb).clip(0, 255).astype(np.uint8)
    rgba[rgba[..., 3] == 0, :3] = 0
    return rgba, [x // FK for x in targhe]


def insegne_fg(img: np.ndarray, emis: np.ndarray, targhe: list[int]) -> None:
    d = Insegne(img, emis)
    for x in targhe:                                   # la targa sta a 4-52 px dall'inizio della cella
        d.text("LINEA 3", x + 28, 19, (44, 40, 48), F3, center=True)
    lum = img[..., :3].astype(int).sum(-1)
    for x in range(65, FW, 291):                       # le lenti calde delle lampade
        sl = img[24:FH, x - 12:x + 12]
        on = (lum[24:FH, x - 12:x + 12] > 520) & (sl[..., 3] > 0)
        emis[24:FH, x - 12:x + 12][on] = (255, 200, 130, 255)


def insegne_near(img: np.ndarray, emis: np.ndarray) -> None:
    """Il cartellone di SIDERA (lo slogan del 2.0, da docs/mondo.md) e il maxischermo di Pasqua."""
    d = Insegne(img, emis)
    # Il cartellone: carta chiara accesa dai due fari; il braccio a sinistra è della base.
    a = img[17 + NEAR_DY:59 + NEAR_DY, 473:651]
    on = a[..., :3].astype(int).sum(-1) > 380
    emis[17 + NEAR_DY:59 + NEAR_DY, 473:651][on] = (70, 64, 56, 255)
    d.text("MANODOPERA 2.0", 599, 24 + NEAR_DY, (40, 34, 44), F5, center=True)
    d.lines([("FISIOTERAPIA NOTTURNA", (60, 56, 62)), ("MENTRE DORMI", (60, 56, 62))], 599, 35 + NEAR_DY)
    d.text("SIDERA", 599, 50 + NEAR_DY, (170, 30, 30), F3, center=True)
    # Il maxischermo: la base lo fa azzurrino, ma il ciano è di GIG; si porta al bianco-menta.
    x0, y0, x1, y1 = 1229, 20 + NEAR_DY_M, 1394, 55 + NEAR_DY_M
    s = img[y0:y1, x0:x1, :3].astype(np.float64)
    lum = s @ np.array([0.299, 0.587, 0.114])
    t = np.clip((lum - 150) / 60, 0, 1)[..., None]
    img[y0:y1, x0:x1, :3] = (s * (1 - t) + np.array([232, 242, 228]) * t).astype(np.uint8)
    emis[y0:y1, x0:x1][t[..., 0] > 0.5] = (120, 132, 118, 255)
    cx = (x0 + x1) // 2
    d.text("DOMENICA DI PASQUA", cx, 24 + NEAR_DY_M, (40, 96, 70), F5, center=True)
    d.text("TARANTO È PURA", cx, 33 + NEAR_DY_M, (40, 96, 70), F5, center=True)
    d.text("FESTA ARIA+", cx, 42 + NEAR_DY_M, (70, 150, 110), F5, center=True)


def emissiva(img: np.ndarray) -> np.ndarray:
    """Le luci che ci sono già nella base (vetrine, lampade, lumini): i pixel caldi e chiari."""
    rgb = img[..., :3].astype(np.float64)
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    warm = (rgb[..., 0] >= rgb[..., 1]) & (rgb[..., 1] >= rgb[..., 2] - 4)
    t = np.clip((lum - 150) / 70, 0, 1) * warm * (img[..., 3] > 0)
    e = np.zeros_like(img)
    e[..., :3] = (rgb * 0.5 * t[..., None]).astype(np.uint8)
    e[..., 3] = np.where(t > 0, 255, 0)
    return e


def gruppi_neon(emis: np.ndarray) -> list[tuple[int, int]]:
    """Le colonne che il gioco fa sfarfallare (la stessa regola di backdrop.gd, _neon_groups)."""
    h, w = emis.shape[:2]
    step = max(1, h // 54)
    c = emis[::step].astype(np.float64) / 255
    lum = c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722
    used = ((c[..., 3] > 0.2) & (lum > 0.08)).any(0)
    runs, start, gap = [], -1, 0
    for x in range(w + 1):
        on = x < w and used[x]
        if on:
            start = x if start < 0 else start
            gap = 0
        elif start >= 0:
            gap += 1
            if gap >= 5 or x == w:
                runs.append((start, x - gap + 1))
                start, gap = -1, 0
    small = [r for r in runs if 5 <= r[1] - r[0] <= 113]
    return [small[int((2 * g + 1) * len(small) / 6.0)] for g in range(min(3, len(small)))]


def pluviale(img: np.ndarray) -> None:
    """Il pluviale di P3 (x 1645-1658) è spaccato sotto la fascetta (y 152): il tratto di sotto manca,
    il muro dietro è bagnato. L'acqua che cade, il pezzo per terra e il rivolo sono del prop «cable»
    (tools/ambienti/cavo_rivolo.py), che scende fino al tombino."""
    rnd = np.random.default_rng(31)
    x0, x1, yb, yf = 1645, 1658, 153, 181
    for y in range(yb, yf):
        for x in range(x0, x1 + 1):
            src = 1644 - (x - x0) % 3 if x <= 1652 else min(1666, x + 9)   # intonaco a sinistra, mattoni a destra
            img[y, x] = img[y, src]
    for x in range(x0, x1 + 1):                                             # il bordo rotto, frastagliato
        for y in range(yb, yb + int(rnd.integers(0, 4))):
            img[y, x, :3] = (img[y - 3, x, :3] * 0.8).astype(np.uint8)
        img[yb + int(rnd.integers(0, 3)), x, :3] = (22, 16, 22)
    yy, xx = np.mgrid[yb:yf, x0 - 3:x1 + 3]                                # la scia d'acqua sul muro
    wet = np.abs(xx - 1650 + np.sin(yy * 0.4) * 1.5) < 4 + (yy - yb) * 0.12
    reg = img[yb:yf, x0 - 3:x1 + 3, :3].astype(np.float64)
    reg[wet] *= 0.68
    img[yb:yf, x0 - 3:x1 + 3, :3] = reg.astype(np.uint8)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--basi", default=str(BASI))
    ap.add_argument("--uscita", default=str(OUT))
    a = ap.parse_args()
    out = Path(a.uscita)
    out.mkdir(parents=True, exist_ok=True)
    back, done = compose(Path(a.basi))
    old_e = np.asarray(Image.open(GAME / "backdrop_emis.png").convert("RGBA"))
    emis = old_e.copy()
    emis[:, done] = emissiva(back)[:, done]
    insegne(back, emis)
    pluviale(back)
    emis[153:181, 1642:1661] = 0
    emis[CUT:, :, 3] = np.where(back[CUT:, :, 3] > 0, emis[CUT:, :, 3], 0)
    Image.fromarray(back, "RGBA").save(out / "backdrop.png")
    Image.fromarray(emis, "RGBA").save(out / "backdrop_emis.png")
    print("neon che sfarfallano (colonne):", gruppi_neon(emis))
    # anteprima: sopra il floor del gioco, su fondo scuro, con l'emissiva in additivo, 2x
    floor = Image.open(GAME / "floor.png").convert("RGBA")
    pv = Image.new("RGBA", (W, 270), (40, 36, 56, 255))
    pv.alpha_composite(floor, (0, 162))
    pv.alpha_composite(Image.fromarray(back, "RGBA"), (0, 0))
    e = np.zeros((270, W, 3), np.int32)
    e[:H] = emis[..., :3].astype(np.int32) * (emis[..., 3:] > 0)
    pv = Image.fromarray(np.clip(np.asarray(pv.convert("RGB"), np.int32) + e, 0, 255).astype(np.uint8))
    for i in range(0, W, 800):
        pv.crop((i, 0, i + 800, 270)).convert("RGB").resize((1600, 540), Image.NEAREST).save(
            out / f"anteprima_{i:04d}.png")
    print("backdrop in", out)

    near = compose_near(NEAR_BASI)
    ne = emissiva(near)
    ne[..., :3] = (ne[..., :3] * 0.7).astype(np.uint8)      # più lontano: le finestre accese più deboli
    insegne_near(near, ne)
    Image.fromarray(near, "RGBA").save(out / "near.png")
    Image.fromarray(ne, "RGBA").save(out / "near_emis.png")
    print("near: neon che sfarfallano (colonne):", gruppi_neon(ne))

    if FG_BASE.exists():
        fg, targhe = compose_fg(FG_BASE)
        fe = np.zeros_like(fg)
        insegne_fg(fg, fe, targhe)
        Image.fromarray(fg, "RGBA").save(out / "fg.png")
        Image.fromarray(fe, "RGBA").save(out / "fg_emis.png")
        print("fg: targhe a x", targhe)
    else:
        print("manca", FG_BASE, "- la fg resta quella del gioco")


if __name__ == "__main__":
    main()
