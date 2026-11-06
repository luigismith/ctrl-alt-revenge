# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Ritaglia un foglio di oggetti su fondo magenta (un "kit") e li porta in pixel art.

Le basi dei kit arrivano da Gemini: tanti oggetti separati su un magenta piatto (#ff00ff).
Qui ogni oggetto diventa uno sprite a sé:

1. trasparenza dal magenta, sull'immagine grande (vedi `pixelizza.magenta_alpha`);
2. oggetti = componenti connesse della sagoma, dopo una piccola dilatazione che tiene insieme
   le parti staccate (i fiori e il loro vaso, un gruppo di lumini); le briciole si scartano;
3. tutti alla stessa scala (`--scala`, frazione della misura del foglio), così restano in
   proporzione fra loro come nel foglio;
4. una palette sola per tutto il kit (k-means in OKLab sui pixel di tutti gli oggetti), perché
   gli oggetti dello stesso piano devono avere gli stessi colori.

Uso:

    python -I tools/ambienti/ritaglia_kit.py kit.jpg cartella_uscita --scala 0.28 --colori 32

Nella cartella escono `NN.png` (numerati da sinistra a destra, riga per riga), `kit.json` con
misure e posizione di ogni oggetto nel foglio e `foglio.png`, un'anteprima ingrandita.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

# Con python -I la cartella dello script non è nel percorso: la si aggiunge per pixelizza.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pixelizza as px  # noqa: E402


def find_objects(alpha: np.ndarray, join: int = 6, min_area: int = 400) -> list[tuple[tuple[int, int, int, int], np.ndarray]]:
    """Gli oggetti della sagoma `alpha` (0/1), in ordine di lettura: per ognuno il riquadro
    (x0, y0, x1, y1) e la sua maschera dentro il riquadro (senza i pezzi dei vicini)."""
    grown = ndimage.binary_dilation(alpha > 0, iterations=join)
    lab, n = ndimage.label(grown)
    found = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if sl is None:
            continue
        ys, xs = sl
        part = (lab[sl] == i) & (alpha[sl] > 0)
        if part.sum() < min_area:
            continue
        # Il riquadro vero, senza il bordo aggiunto dalla dilatazione.
        yy, xx = np.nonzero(part)
        box = (xs.start + xx.min(), ys.start + yy.min(), xs.start + xx.max() + 1, ys.start + yy.max() + 1)
        found.append((box, part[yy.min():yy.max() + 1, xx.min():xx.max() + 1]))
    if not found:
        return found
    # Righe: oggetti la cui base sta entro un terzo dell'altezza media l'uno dall'altro.
    hmean = float(np.mean([b[3] - b[1] for b, _ in found]))
    found.sort(key=lambda f: f[0][3])
    rows: list[list] = []
    for f in found:
        if rows and abs(f[0][3] - rows[-1][-1][0][3]) < hmean / 3:
            rows[-1].append(f)
        else:
            rows.append([f])
    out = []
    for r in rows:
        out.extend(sorted(r, key=lambda f: f[0][0]))
    return out


def cut_kit(img: Image.Image, scale: float, colors: int, *, join: int = 6, min_area: int = 400,
            outline: bool = False, seed: int = 1) -> list[dict]:
    """Gli oggetti del foglio come sprite RGBA alla scala data, con una palette comune."""
    src = img.convert("RGB").filter(ImageFilter.MedianFilter(3))
    rgb_hi = np.asarray(src, np.float64) / 255.0
    a_hi = px.magenta_alpha(rgb_hi)
    # Il viola dei bordi si toglie sul foglio grande, prima della riduzione: dopo, la media l'avrebbe
    # già portato dentro la sagoma.
    rgb_hi = px.despill(rgb_hi, a_hi, 3)
    found = find_objects(a_hi, join=join, min_area=min_area)
    # Per ogni oggetto: riduzione con il colore pesato dall'alfa (niente alone magenta).
    items = []
    for (x0, y0, x1, y1), mask in found:
        w = max(1, round((x1 - x0) * scale))
        h = max(1, round((y1 - y0) * scale))
        a = mask.astype(np.float64)
        rgb = rgb_hi[y0:y1, x0:x1]
        a_img = Image.fromarray((a * 255).astype(np.uint8)).resize((w, h), Image.BOX)
        alpha = (np.asarray(a_img) >= 128).astype(np.uint8)
        prem = Image.fromarray((rgb * a[..., None] * 255).astype(np.uint8)).resize((w, h), Image.BOX)
        ah = np.asarray(a_img, np.float64)[..., None] / 255.0
        col = np.where(ah > 0, np.asarray(prem, np.float64) / 255.0 / np.maximum(ah, 1e-3), 0.0).clip(0, 1)
        col = px.despill(col, alpha)
        items.append({"box": [int(x0), int(y0), int(x1), int(y1)], "rgb": col, "alpha": alpha})
    # Una palette per tutto il kit.
    lab_all = np.concatenate([px.to_oklab(it["rgb"]).reshape(-1, 3) for it in items])
    w_all = np.concatenate([it["alpha"].reshape(-1).astype(np.float64) for it in items])
    pal = px.kmeans_palette(lab_all, colors, seed=seed, weights=w_all)
    pal_rgb = (px.from_oklab(pal) * 255 + 0.5).clip(0, 255).astype(np.uint8)
    for it in items:
        idx = px.map_to_palette(px.to_oklab(it["rgb"]), pal)
        idx = px.majority_clean(idx, it["alpha"], 1)
        out = np.zeros((*idx.shape, 4), np.uint8)
        out[..., :3] = pal_rgb[idx]
        out[..., 3] = it["alpha"] * 255
        if outline:
            out = px.add_outline(np.pad(out, ((1, 1), (1, 1), (0, 0))))
        it["rgba"] = out
    return items


def contact_sheet(items: list[dict], zoom: int = 3, bg=(40, 38, 48)) -> Image.Image:
    """Tutti gli sprite in fila, ingranditi, con il loro numero."""
    pad = 6
    tiles = [Image.fromarray(it["rgba"], "RGBA") for it in items]
    row_w = 0
    rows: list[list[int]] = [[]]
    for i, t in enumerate(tiles):
        if row_w + t.width + pad > 420 and rows[-1]:
            rows.append([])
            row_w = 0
        rows[-1].append(i)
        row_w += t.width + pad
    heights = [max(tiles[i].height for i in r) + 12 for r in rows]
    W = max(sum(tiles[i].width + pad for i in r) for r in rows) + pad
    H = sum(heights) + pad
    sheet = Image.new("RGBA", (W, H), (*bg, 255))
    d = ImageDraw.Draw(sheet)
    y = pad
    for r, hh in zip(rows, heights):
        x = pad
        for i in r:
            t = tiles[i]
            sheet.alpha_composite(t, (x, y + hh - 12 - t.height))
            d.text((x, y + hh - 11), f"{i:02d}", fill=(255, 230, 120, 255))
            x += t.width + pad
        y += hh
    return sheet.resize((W * zoom, H * zoom), Image.NEAREST)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--scala", type=float, required=True, help="frazione della misura del foglio, per esempio 0.28")
    ap.add_argument("--colori", type=int, default=32)
    ap.add_argument("--unisci", type=int, default=6, help="dilatazione in px che tiene insieme le parti staccate")
    ap.add_argument("--minimo", type=int, default=400, help="area minima di un oggetto, in px del foglio")
    ap.add_argument("--contorno", action="store_true")
    a = ap.parse_args()
    out = Path(a.dst)
    out.mkdir(parents=True, exist_ok=True)
    items = cut_kit(Image.open(a.src), a.scala, a.colori, join=a.unisci, min_area=a.minimo, outline=a.contorno)
    meta = []
    for i, it in enumerate(items):
        Image.fromarray(it["rgba"], "RGBA").save(out / f"{i:02d}.png")
        h, w = it["rgba"].shape[:2]
        meta.append({"id": i, "file": f"{i:02d}.png", "size": [w, h], "box_in_sheet": it["box"]})
    (out / "kit.json").write_text(json.dumps({"source": Path(a.src).name, "scale": a.scala, "objects": meta}, indent=1), "utf-8")
    contact_sheet(items).save(out / "foglio.png")
    print(f"{len(items)} oggetti in {out}")


if __name__ == "__main__":
    main()
