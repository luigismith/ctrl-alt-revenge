"""Primi piani 96x96 dalle basi in stile murales fatte con ChatGPT (decisione 68 della storia).

Il volto nasce dal nostro render 3D, ridipinto da ChatGPT nello stile dei murales di Totò; la base originale sta
nella cartella privata condivisa (primi-piani/ai/chatgpt), mai nel repo. Qui la riduciamo in pixel art:
  1. scontorno del fondo verde pieno, senza alone verde ai bordi;
  2. allineamento della sagoma a quella del render 3D dello stesso primo piano (scala e spostamento col miglior
     IoU), così inquadratura e lato del volto restano quelli dei primi piani del gioco;
  3. riduzione a 96x96 (media per area, alfa binaria) e tavolozza piccola con le k-medie in Lab;
  4. aggancio della tavolozza ai colori del personaggio (pelle, lenti...: quelli degli sprite);
  5. contorno esterno #140e1e, come gli altri primi piani.
Niente di animato viene dall'AI: le palpebre chiuse ("blink") e la bocca aperta ("talk") le disegna questo script
sui pixel della base, come build_chars.py coi primi piani dal 3D, così lo scambio delle immagini non sfarfalla.

La configurazione sta nel JSON del personaggio (tools/sprites/chars/<id>.json), nella voce "closeups" del primo
piano, alla chiave "ai":
  base     file della base, relativo a primi-piani/ai nella cartella condivisa
  render   render 3D di riferimento per l'allineamento, relativo a primi-piani (di solito <nome>.png)
  colors   colori della tavolozza (prima del contorno)
  canon    colori del personaggio a cui agganciare la tavolozza
  eyes     per ogni occhio che si chiude, il riquadro [x, y, w, h] a 96 px dove cercarlo
  mouth    il riquadro [x, y, w, h] della bocca chiusa (la riga scura delle labbra)
  open_px  quanto si apre la bocca al centro, in pixel

Uso (Python del laboratorio):
  python -I tools/sprites/closeup_ai.py gig_spento messo      primi piani "ai" di questi personaggi
  python -I tools/sprites/closeup_ai.py messo --zoom DIR       solo la base ingrandita 8x con la griglia, per
                                                               scegliere i riquadri di occhi e bocca
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charlib as C  # noqa: E402
import review as RV  # noqa: E402

N = 96
OUTLINE = np.array([0x14, 0x0E, 0x1E], np.uint8)
CHROMA_W = 1.6
CLOSEUP_DIR = os.path.join(C.ASSETS, "ui", "closeups")
BG_SCENE = (18, 15, 36)
FONTE = "ChatGPT (OpenAI), dal nostro render 3D; ridotto in pixel art dai nostri script"


def condiviso_dir(*parts):
    """cartella privata condivisa fra i PC (mai nel repo): CAR_CONDIVISO o ctrlaltrevenge-lab-condiviso accanto
    al repo."""
    base = os.environ.get("CAR_CONDIVISO") or os.path.join(os.path.dirname(C.REPO), "ctrlaltrevenge-lab-condiviso")
    return os.path.join(base, *parts)


def hx(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.uint8)


def tohex(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c[:3])


# ------------------------------------------------------------------ colore
def srgb_to_lab(rgb):
    c = rgb.astype(np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[..., 1] - 16
    # a* e b* pesano di più: le zone piccole ma sature (lenti, luce rosa, occhio grigio sulla pelle) non si
    # perdono nella tavolozza
    a = 500 * (f[..., 0] - f[..., 1]) * CHROMA_W
    b = 200 * (f[..., 1] - f[..., 2]) * CHROMA_W
    return np.stack([L, a, b], -1)


def kmeans(x, k, iters=30, seed=7):
    """k-medie con partenza k-means++ a seme fisso: la stessa base dà sempre la stessa tavolozza."""
    rng = np.random.default_rng(seed)
    cent = [x[rng.integers(len(x))]]
    for _ in range(1, k):
        d = np.min(((x[:, None, :] - np.array(cent)[None]) ** 2).sum(-1), 1)
        cent.append(x[rng.choice(len(x), p=d / d.sum())])
    cent = np.array(cent)
    for _ in range(iters):
        lab = np.argmin(((x[:, None, :] - cent[None]) ** 2).sum(-1), 1)
        new = np.array([x[lab == i].mean(0) if (lab == i).any() else cent[i] for i in range(k)])
        if np.allclose(new, cent):
            break
        cent = new
    return cent


# ------------------------------------------------------------------ scontorno e allineamento
def key_green(rgb):
    """(maschera della figura, colori senza verde): il fondo è il verde pieno collegato ai bordi; il fondo prende
    il colore del pixel di figura più vicino, così le riduzioni non mescolano il verde ai bordi."""
    r, g, b = [rgb[..., i].astype(np.int32) for i in range(3)]
    bg = ((g - np.maximum(r, b)) > 70) & (g > 110)
    lab, _ = ndimage.label(bg)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fig = ~np.isin(lab, list(border))
    out = rgb.astype(np.int32)
    gmax = np.maximum(out[..., 0], out[..., 2]) + 6
    out[..., 1] = np.where(fig, np.minimum(out[..., 1], gmax), out[..., 1])
    iy, ix = ndimage.distance_transform_edt(~fig, return_distances=False, return_indices=True)
    return fig, out[iy, ix].clip(0, 255).astype(np.uint8)


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


def best_fit(ai_mask, ref_mask, M=N, scales=np.linspace(0.84, 1.16, 33), maxshift=14):
    """scala (attorno al centro) e spostamento in pixel della griglia M che portano la sagoma AI su quella del
    render. -> (IoU senza correzione, (IoU, scala, dx, dy))"""
    ref = np.array(Image.fromarray(ref_mask.astype(np.uint8) * 255).resize((M, M), Image.BOX)) > 127
    src = Image.fromarray(ai_mask.astype(np.uint8) * 255)

    def placed(s):
        sz = max(8, int(round(M * s)))
        a = np.array(src.resize((sz, sz), Image.BOX)) > 127
        big = np.zeros((M + 2 * sz, M + 2 * sz), bool)
        off = int(round(M / 2 * (1 - s))) + sz
        big[off:off + sz, off:off + sz] = a
        return big, sz

    big, sz = placed(1.0)
    iou0 = iou(big[sz:sz + M, sz:sz + M], ref)
    best = (iou0, 1.0, 0, 0)
    for s in scales:
        big, sz = placed(s)
        for dy in range(-maxshift, maxshift + 1):
            for dx in range(-maxshift, maxshift + 1):
                v = iou(big[sz - dy:sz - dy + M, sz - dx:sz - dx + M], ref)
                if v > best[0] + 1e-9:
                    best = (v, float(s), dx, dy)
    return iou0, best


def place_full(rgba, F, s, dx, dy, M=N):
    """l'immagine RGBA scalata di s e spostata di (dx, dy) pixel della griglia M, in una tela FxF."""
    sz = int(round(F * s))
    rgb = Image.fromarray(np.ascontiguousarray(rgba[..., :3])).resize((sz, sz), Image.LANCZOS)
    al = Image.fromarray(np.ascontiguousarray(rgba[..., 3])).resize((sz, sz), Image.LANCZOS)
    im = Image.merge("RGBA", (*rgb.split(), al))
    ox = int(round(F / 2 * (1 - s) + dx * F / M))
    oy = int(round(F / 2 * (1 - s) + dy * F / M))
    mg = sz + F
    canvas = Image.new("RGBA", (F + 2 * mg, F + 2 * mg), (0, 0, 0, 0))
    canvas.alpha_composite(im, (ox + mg, oy + mg))
    return np.array(canvas.crop((mg, mg, mg + F, mg + F)))


# ------------------------------------------------------------------ riduzione e tavolozza
def downscale(rgba, n=N):
    """media per area con alfa premoltiplicata; alfa binaria a metà copertura."""
    a = rgba[..., 3:4].astype(np.float64) / 255.0
    pre = np.concatenate([rgba[..., :3] * a, a * 255], -1)
    k = rgba.shape[0] // n
    pre = pre[:k * n, :k * n].reshape(n, k, n, k, 4).mean((1, 3))
    alpha = pre[..., 3] / 255.0
    rgb = np.where(alpha[..., None] > 0, pre[..., :3] / np.maximum(alpha[..., None], 1e-6), 0)
    return rgb.clip(0, 255), alpha >= 0.5


def clean_mask(m, min_px=6):
    """via le isole e i buchi più piccoli di min_px (spruzzi e colature staccate)."""
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= min_px])
    holes, hn = ndimage.label(~keep)
    hs = ndimage.sum(~keep, holes, range(1, hn + 1))
    border = set(np.unique(np.concatenate([holes[0], holes[-1], holes[:, 0], holes[:, -1]]))) - {0}
    fill = [i + 1 for i, s in enumerate(hs) if s < min_px and (i + 1) not in border]
    return keep | np.isin(holes, fill)


def edge_of(m):
    p = np.pad(m, 1)
    return m & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])


def palette(rgb, m, k):
    """(centri Lab, colori RGB): per ogni centro il colore medio dei suoi pixel; i quasi neri diventano il
    contorno #140e1e."""
    lab = srgb_to_lab(rgb[m])
    cent = kmeans(lab, k)
    idx = np.argmin(((lab[:, None, :] - cent[None]) ** 2).sum(-1), 1)
    pr = np.array([rgb[m][idx == i].mean(0) if (idx == i).any() else (0, 0, 0) for i in range(k)])
    pr = pr.round().clip(0, 255).astype(np.uint8)
    pr[cent[:, 0] < 14] = OUTLINE
    return cent, pr


def snap_canon(pal_rgb, canon, max_de=40.0, radius=25.0):
    """per ogni colore del personaggio, il colore della tavolozza più vicino (entro max_de) diventa quello e i
    vicini (entro radius) lo seguono in proporzione. Il contorno non si tocca. -> (tavolozza, agganci)"""
    pal = pal_rgb.astype(np.float64)
    lab = srgb_to_lab(pal_rgb)
    fixed = np.all(pal_rgb == OUTLINE, axis=1)
    shift = np.zeros_like(pal)
    wsum = np.zeros(len(pal))
    agganci = []
    for h in canon:
        c = hx(h).astype(np.float64)
        d = np.linalg.norm(lab - srgb_to_lab(hx(h)[None])[0], axis=1)
        d[fixed] = np.inf
        j = int(np.argmin(d))
        if d[j] > max_de:
            agganci.append(f"{h}: nessuno (il più vicino è a {d[j]:.0f})")
            continue
        agganci.append(f"{h} <- {tohex(pal_rgb[j])} ({d[j]:.0f})")
        w = np.clip(1 - np.linalg.norm(lab - lab[j], axis=1) / radius, 0, 1)
        w[fixed] = 0
        shift += w[:, None] * (c - pal[j])
        wsum += w
    out = pal + shift / np.maximum(wsum, 1)[:, None]
    return out.round().clip(0, 255).astype(np.uint8), agganci


def quantize(rgb, m, pal_lab, pal_rgb):
    out = np.zeros((N, N, 4), np.uint8)
    lab = srgb_to_lab(rgb[m])
    out[m, :3] = pal_rgb[np.argmin(((lab[:, None, :] - pal_lab[None]) ** 2).sum(-1), 1)]
    out[m, 3] = 255
    out[edge_of(m), :3] = OUTLINE
    return out


def cyan_count(img):
    """stessa prova di build_chars.py e dello shader del gioco."""
    rgb = img[..., :3].astype(int)
    return int(((img[..., 3] > 0) & (rgb[..., 2] - rgb[..., 0] >= 0.4 * 255)
                & (rgb[..., 1] - rgb[..., 0] >= 0.3 * 255)).sum())


def luma(c):
    c = np.asarray(c, np.float64)
    return 0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2]


# ------------------------------------------------------------------ occhi e bocca, disegnati da noi
def main_colour(img, mask):
    px = [tuple(int(v) for v in p[:3]) for p in img[mask]]
    if not px:
        return None
    vals, counts = np.unique(np.array(px), axis=0, return_counts=True)
    return vals[int(np.argmax(counts))]


def eye_region(img, box, skin_l):
    """i pixel dell'occhio nel riquadro: quelli più scuri della pelle in ombra (ciglia, iride, contorno), la
    componente più grande, più i chiari che chiude dentro (il bianco)."""
    x, y, w, h = box
    win = np.zeros(img.shape[:2], bool)
    win[y:y + h, x:x + w] = True
    dark = win & (img[..., 3] > 0) & (luma(img[..., :3]) < skin_l)
    lab, n = ndimage.label(dark)
    if n == 0:
        return dark
    sizes = ndimage.sum(dark, lab, range(1, n + 1))
    reg = ndimage.binary_fill_holes(lab == (int(np.argmax(sizes)) + 1)) & win
    # il riflesso e il bianco dell'occhio sul bordo: i chiari dentro il riquadro dell'occhio che lo toccano
    b = bbox_of(reg)
    if b:
        bx, by, bw, bh = b
        box_m = np.zeros_like(reg)
        box_m[by:by + bh, bx:bx + bw] = True
        rgb = img[..., :3].astype(np.int32)
        grey = (rgb[..., 0] - rgb[..., 2]) < 30  # la pelle tira al rosso, riflesso e bianco no
        light = box_m & (img[..., 3] > 0) & ((luma(img[..., :3]) > skin_l + 60) | grey)
        reg |= light & ndimage.binary_dilation(reg)
    return reg


def paint_blink(img, reg, lash):
    """occhio chiuso: i pixel dell'occhio prendono il colore della palpebra (la pelle subito sopra) e la riga più
    bassa di ogni colonna diventa la linea delle ciglia. -> (immagine, riquadro, colore della palpebra)"""
    out = img.copy()
    above = np.zeros_like(reg)
    for k in (1, 2, 3):
        above[:-k] |= reg[k:]
    above &= ~reg & (img[..., 3] > 0) & (luma(img[..., :3]) > luma(lash) + 40)
    lid = main_colour(img, above)
    ys, xs = np.nonzero(reg)
    out[reg, :3] = lid
    # la linea delle ciglia: il fondo dell'occhio colonna per colonna, lisciato (mediana su tre colonne),
    # così si legge come una palpebra e non come un bordo seghettato
    cols = np.unique(xs)
    bottom = np.array([ys[xs == x].max() for x in cols])
    smooth = ndimage.median_filter(bottom, size=3, mode="nearest")
    for i, x in enumerate(cols):
        y = int(smooth[i])
        out[y, x, :3] = lash
        reg[y, x] = True
    return out, bbox_of(reg), lid


def mouth_line(img, box):
    """la bocca chiusa: in ogni colonna del riquadro il pixel più scuro, se è più scuro dei vicini sopra e sotto.
    -> ({x: y}, colore scuro)"""
    x0, y0, w, h = box
    line = {}
    L = luma(img[..., :3])
    for x in range(x0, x0 + w):
        col = [(L[y, x], y) for y in range(y0, y0 + h) if img[y, x, 3] > 0]
        if col:
            line[x] = min(col)[1]
    ys = [img[y, x, :3] for x, y in line.items()]
    dark = min(ys, key=lambda c: luma(c))
    return line, dark


def paint_talk(img, line, dark, open_px):
    """bocca aperta: sotto la riga della bocca chiusa un ovale scuro, alto open_px al centro e niente agli
    angoli. -> (immagine, maschera della bocca aperta)"""
    out = img.copy()
    opened = np.zeros(img.shape[:2], bool)
    xa, xb = min(line), max(line)
    span = xb - xa + 1
    for x, y0 in line.items():
        opened[y0, x] = img[y0, x, 3] > 0
        t = (x - xa + 0.5) / span
        k = int(round(open_px * (1.0 - abs(2.0 * t - 1.0) ** 2)))
        for y in range(y0 + 1, min(img.shape[0], y0 + 1 + k)):
            if img[y, x, 3] > 0:
                out[y, x, :3] = dark
                opened[y, x] = True
    return out, opened


def bbox_of(m):
    ys, xs = np.nonzero(m)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]


# ------------------------------------------------------------------ tavole di controllo
def zoom_grid(img, path, k=8):
    """la base ingrandita k volte su fondo scuro, con la griglia ogni 8 pixel e le coordinate."""
    W = N * k
    sheet = Image.new("RGB", (W + 30, W + 30), BG_SCENE)
    t = Image.fromarray(img, "RGBA").resize((W, W), Image.NEAREST)
    sheet.paste(t, (30, 30), t)
    d = ImageDraw.Draw(sheet)
    for i in range(0, N + 1, 4):
        c = (90, 90, 120) if i % 8 else (200, 200, 90)
        if i % 8 == 0:
            d.text((30 + i * k + 2, 4), str(i), fill=c)
            d.text((2, 30 + i * k + 2), str(i), fill=c)
        d.line([(30 + i * k, 30), (30 + i * k, 30 + W)], fill=c if i % 8 == 0 else (60, 60, 80))
        d.line([(30, 30 + i * k), (30 + W, 30 + i * k)], fill=c if i % 8 == 0 else (60, 60, 80))
    sheet.save(path)


def closeup_sheet(tiles, title, sub, path, scale=4):
    n = N * scale
    gap, top, lab = 12, 52, 26
    sheet = Image.new("RGB", (gap + len(tiles) * (n + gap), top + n + lab), (58, 58, 74))
    dr = ImageDraw.Draw(sheet)
    dr.text((gap, 6), title, fill=(235, 235, 245), font=RV.font(18))
    dr.text((gap, 30), sub, fill=(170, 170, 190), font=RV.font(12))
    for i, (label, im) in enumerate(tiles):
        x = gap + i * (n + gap)
        bg = Image.new("RGB", (n, n), BG_SCENE)
        t = Image.fromarray(im, "RGBA").resize((n, n), Image.NEAREST)
        bg.paste(t, (0, 0), t)
        sheet.paste(bg, (x, top))
        dr.text((x, top + n + 6), label, fill=(220, 220, 235), font=RV.font(12))
    sheet.save(path)


# ------------------------------------------------------------------ principale
def reduce_base(ai):
    """la base AI ridotta a 96x96 sulla tavolozza agganciata ai colori del personaggio. -> (immagine, misure)"""
    ref = np.array(Image.open(condiviso_dir("primi-piani", ai["render"])).convert("RGBA"))
    ref_mask, F = ref[..., 3] > 127, ref.shape[0]
    src = np.array(Image.open(condiviso_dir("primi-piani", "ai", ai["base"])).convert("RGB"))
    fig, rgb = key_green(src)
    iou0, (iou1, s, dx, dy) = best_fit(fig, ref_mask)
    small_ai = np.array(Image.fromarray(fig.astype(np.uint8) * 255).resize((N, N), Image.BOX)) > 127
    small_ref = np.array(Image.fromarray(ref_mask.astype(np.uint8) * 255).resize((N, N), Image.BOX)) > 127
    mirrored = iou(small_ai, small_ref[:, ::-1]) > iou(small_ai, small_ref)
    placed = place_full(np.dstack([rgb, fig.astype(np.uint8) * 255]), F, s, dx, dy)
    col, m = downscale(placed)
    m = clean_mask(m)
    pal_lab, pal_rgb = palette(col, m, ai.get("colors", 20))
    pal_rgb, agganci = snap_canon(pal_rgb, ai.get("canon", []))
    base = quantize(col, m, pal_lab, pal_rgb)
    info = dict(iou_senza_correzione=round(iou0, 3), iou_allineato=round(iou1, 3), scala=round(s, 3), dx=dx,
                dy=dy, specchiata=bool(mirrored), agganci=agganci)
    return base, info


def build(cid, zoom=None):
    cfg = C.char_cfg(cid)
    for sp in cfg.get("closeups") or []:
        ai = sp.get("ai")
        if not ai:
            continue
        name = sp["name"]
        base, info = reduce_base(ai)
        if info["specchiata"]:
            raise SystemExit(f"{name}: la base AI sembra specchiata rispetto al render, non la uso")
        if zoom:
            os.makedirs(zoom, exist_ok=True)
            zoom_grid(base, os.path.join(zoom, name + "_8x.png"))
            C.say(f"  {name}: base ingrandita in {zoom}")
            continue
        variants = sp.get("variants", ["blink", "talk"])
        res = dict(size=[N, N], faces=sp.get("faces", "right"))
        out = {"base": base}
        lash = OUTLINE
        notes = []
        if "blink" in variants and ai.get("eyes"):
            skin_l = min(luma(hx(c)) for c in ai.get("canon", [])[:2]) if ai.get("canon") else 110
            comp, rects, lid = base.copy(), [], None
            for box in ai["eyes"]:
                reg = eye_region(comp, box, ai.get("eye_luma", skin_l - 10))
                comp, r, lid = paint_blink(comp, reg, lash)
                rects.append(r)
            out["blink"] = comp
            res["eyes"] = rects
            res["lid"] = tohex(lid)
            notes.append(f"occhi chiusi {len(rects)}")
        if "talk" in variants and ai.get("mouth"):
            line, dark = mouth_line(base, ai["mouth"])
            dark = hx(ai["mouth_dark"]) if ai.get("mouth_dark") else dark
            comp, opened = paint_talk(base, line, dark, ai.get("open_px", 2))
            out["talk"] = comp
            res["mouth"] = bbox_of(opened)
            res["mouth_dark"] = tohex(dark)
            notes.append(f"bocca aperta {int((comp != base).any(-1).sum())} px")
        res["variants"] = [k for k in out if k != "base"]
        res["fonte"] = FONTE
        cy = sum(cyan_count(im) for im in out.values())
        colours = len(np.unique(base[base[..., 3] > 0][:, :3], axis=0))
        os.makedirs(CLOSEUP_DIR, exist_ok=True)
        for k, im in out.items():
            fn = name + ("" if k == "base" else "_" + k) + ".png"
            Image.fromarray(im, "RGBA").save(os.path.join(CLOSEUP_DIR, fn))
        C.save_json(os.path.join(CLOSEUP_DIR, name + ".json"), res)
        sub = (f"base {ai['base']}; IoU col render {info['iou_senza_correzione']} -> {info['iou_allineato']} "
               f"(scala {info['scala']}, {info['dx']:+d},{info['dy']:+d}); {colours} colori; "
               + ", ".join(notes) + f"; pixel cyan: {cy}")
        tiles = list(out.items())
        ov = base.copy()
        for r in res.get("eyes", []) + ([res["mouth"]] if "mouth" in res else []):
            x, y, w, h = r
            ov[y, x:x + w] = ov[y + h - 1, x:x + w] = (255, 230, 0, 255)
            ov[y:y + h, x] = ov[y:y + h, x + w - 1] = (255, 230, 0, 255)
        tiles.append(("rettangoli del JSON", ov))
        rvd = os.path.join(C.OUT, "review", "closeups")
        os.makedirs(rvd, exist_ok=True)
        closeup_sheet(tiles, f"primo piano {name} ({cid}), base ChatGPT", sub, os.path.join(rvd, name + "_4x.png"))
        C.say(f"  primo piano {name}: {sub}")
        C.say("    " + "; ".join(info["agganci"]))
        if cy and cid == "gig_spento":
            C.say(f"AVVISO: {name}: {cy} pixel cyan su GIG prima del riavvio")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chars", nargs="+")
    ap.add_argument("--zoom", help="solo la base ingrandita 8x con la griglia, in questa cartella")
    a = ap.parse_args()
    for c in a.chars:
        build(c, a.zoom)
