# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - la patina rossa del minerale sul pavimento di «Sotto la Linea» (Luigi, 7 novembre
2026: una velatura leggera sui bordi e nelle crepe).

  python -I tools/ambienti/patina_floor.py [--sorgente floor.png] [--uscita DIR]

Il minerale si posa nelle fughe delle lastre, nelle crepe dell'asfalto, al piede delle facciate e nel
canale di scolo; altrove c'è appena un velo a chiazze. Le pozze restano pulite: wind_day.gd ricava la
maschera delle pozze da floor.png (pixel opachi con g >= r + 4 e b > g + 6), quindi lo script controlla
che la maschera venga identica, pixel per pixel, e che l'alfa non cambi.

La patina si dà una volta sola: il PNG porta la nota «car-patina» e lo script rifiuta un floor che ce l'ha già.
Il floor pulito lo prende da git (commit b11dd34), dove il pavimento non ha ancora la patina; con --sorgente
si può dare un altro PNG.

Il retino non è ordinato: la soglia di ogni pixel viene da un rumore a grani (Luigi, 7 novembre 2026:
«retino più morbido»), così il minerale sembra polvere posata e non una grata.
"""
from __future__ import annotations

import argparse
import io
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from PIL.PngImagePlugin import PngInfo

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / "game/assets/env/sotto_la_linea"
OUT = ROOT / "tools/out/ambienti/sotto_la_linea"
FY = 162                                     # il floor sta a y 162 nel mondo
SIDE = (180 - FY, 216 - FY)                  # il marciapiede
FOOT = (180 - FY, 184 - FY)                  # il piede delle facciate
GUTTER = (222 - FY, 227 - FY)                # il canale di scolo
PULITO = "b11dd34"                           # l'ultimo commit con il floor senza patina
LIVELLI = 8                                  # i gradini della velatura


def pozze(a: np.ndarray) -> np.ndarray:
    r, g, b, al = (a[..., k].astype(int) for k in range(4))
    return (al > 127) & (g >= r + 4) & (b > g + 6)


def noise(h: int, w: int, seed: int, scale: int) -> np.ndarray:
    rnd = np.random.default_rng(seed)
    small = rnd.random((h // scale + 2, w // scale + 2))
    im = Image.fromarray((small * 255).astype(np.uint8)).resize((w + 2 * scale, h + 2 * scale), Image.BICUBIC)
    return np.asarray(im, float)[scale:scale + h, scale:scale + w] / 255.0


def patina(a: np.ndarray) -> np.ndarray:
    h, w = a.shape[:2]
    rgb = a[..., :3].astype(float)
    lum = rgb @ [0.3, 0.59, 0.11]
    mean = np.asarray(Image.fromarray(lum.astype(np.uint8)).filter(ImageFilter.BoxBlur(3)), float)
    yy = np.arange(h)[:, None] + np.zeros((1, w))
    opaque = a[..., 3] > 127
    water = pozze(a)
    near_water = np.asarray(Image.fromarray(water.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(5))) > 0
    crack = np.clip((mean - lum - 2) / 4, 0, 1)                      # fughe e crepe: più scure dell'intorno
    n = noise(h, w, 5, 9) * 0.6 + noise(h, w, 6, 3) * 0.4             # le chiazze del vento
    wgt = crack * 0.85
    wgt += ((yy >= FOOT[0]) & (yy < FOOT[1])) * (0.34 - (yy - FOOT[0]) * 0.07)
    wgt += ((yy >= GUTTER[0]) & (yy < GUTTER[1])) * 0.32
    wgt += 0.12
    wgt *= 0.35 + 0.9 * n
    wgt[(yy < SIDE[0]) | ~opaque | near_water] = 0                   # niente sopra il marciapiede, niente nelle pozze
    rnd = np.random.default_rng(7)
    grani = rnd.random((h, w)) * 0.55 + noise(h, w, 8, 2) * 0.45      # soglia a grani: niente schema che si ripete
    lv = np.floor(np.clip(wgt, 0, 0.7) * LIVELLI + grani) / LIVELLI
    ore = np.stack([lum * 1.7 + 30, lum * 0.72 + 6, lum * 0.55 + 4], -1)  # il minerale, con la luce del punto
    out = a.copy()
    out[..., :3] = np.clip(rgb * (1 - lv[..., None]) + ore * lv[..., None], 0, 255).astype(np.uint8)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sorgente", help="un floor pulito; senza, quello del commit " + PULITO)
    ap.add_argument("--uscita", default=str(OUT))
    args = ap.parse_args()
    if args.sorgente:
        src = Image.open(args.sorgente)
    else:
        rel = (GAME / "floor.png").relative_to(ROOT).as_posix()
        raw = subprocess.run(["git", "-C", str(ROOT), "show", f"{PULITO}:{rel}"], capture_output=True, check=True)
        src = Image.open(io.BytesIO(raw.stdout))
    if "car-patina" in src.info:
        raise SystemExit(f"{args.sorgente} ha già la patina: serve il floor di prima")
    a = np.asarray(src.convert("RGBA"))
    b = patina(a)
    bad = pozze(b) != pozze(a)
    b[bad] = a[bad]                                                  # per sicurezza: nessun pixel cambia maschera
    assert (pozze(b) == pozze(a)).all() and (b[..., 3] == a[..., 3]).all()
    out = Path(args.uscita)
    out.mkdir(parents=True, exist_ok=True)
    info = PngInfo()
    info.add_text("car-patina", "1")
    Image.fromarray(b, "RGBA").save(out / "floor.png", pnginfo=info)
    changed = (b[..., :3] != a[..., :3]).any(-1).mean()
    print(f"floor: pixel toccati {changed:.0%}, maschera delle pozze identica ({pozze(a).sum()} px), "
          f"ripristinati {int(bad.sum())}")


if __name__ == "__main__":
    main()
