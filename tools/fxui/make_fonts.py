# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Costruisce i font "CAR Pixel" (regolare e grassetto) in TTF e li verifica.

  python -I tools/fxui/make_fonts.py            # scrive in tools/fxui/out/fonts/

Verifica: il TTF viene riletto (senza FreeType) e i suoi contorni, rasterizzati, devono
rifare pixel per pixel il bitmap, avanzamenti compresi; poi FreeType (tramite Pillow) deve
caricarlo e disegnare ogni glifo quasi uguale a 10x.
Il controllo a 1x si fa in Godot (godot_check.py): Pillow non permette di spegnere
l'hinting e FreeType, sui TTF senza istruzioni, applica l'auto-hinter, che sposta di un
pixel gli accenti isolati del regolare. È il motivo per cui in Godot l'hinting va su "Nessuno".
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bitfont  # noqa: E402
import font_glyphs as fg  # noqa: E402
import ttf  # noqa: E402

OUT = HERE / "out" / "fonts"
UNIT = 100        # unità per pixel del font
EM_PX = 12        # unitsPerEm = 1200: a 12 px un pixel del font = un pixel dello schermo
VERSION = "1.000"
COPYRIGHT = "Copyright (c) 2026 Luigi Massari. CTRL+ALT REVENGE."
LICENSE = ("Asset originale del gioco CTRL+ALT REVENGE: tutti i diritti riservati "
           "(LicenseRef-CAR-Assets, vedi LICENSES/LicenseRef-CAR-Assets.txt).")

FONTS = {
    "car_pixel_regular.ttf": (bitfont.REGULAR, "Regular", False),
    "car_pixel_bold.ttf": (bitfont.BOLD, "Bold", True),
}

PHRASES = [
    "CTRL+ALT REVENGE! TARANTO · 2087",
    "GIG ×3  PUNK  BRUTO  004200  999999  VAI ▶",
    "Città, più, perché, così, però, è l’arena. È COSÌ!",
    "ÀÈÉÌÒÙ àèéìòù ÁÍÓÚ áíóú",
    "0123456789 abcdefghijklmnopqrstuvwxyz",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
    "« » · ° © ‘’ “” … – — ▶◀▲▼♥",
]


def freetype_mask(path: Path, text: str, size: int, width: int) -> np.ndarray:
    """Testo disegnato da FreeType senza antialiasing; linea di base alla riga 'ascent'."""
    font = ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.BASIC)
    k = size // EM_PX
    img = Image.new("L", (width * k + 8, (fg.ASCENT + fg.DESCENT) * k + 8), 0)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    d.text((0, fg.ASCENT * k), text, font=font, fill=255, anchor="ls")
    a = np.asarray(img) > 127
    return a[:(fg.ASCENT + fg.DESCENT) * k, :width * k]


def verify_roundtrip(path: Path, face: bitfont.Face) -> list[str]:
    """Rilegge il TTF (senza FreeType) e ne rasterizza i contorni: devono rifare il bitmap."""
    import pix
    info = ttf.read(path.read_bytes())
    errors = []
    if info["upm"] != UNIT * EM_PX:
        errors.append(f"unitsPerEm {info['upm']}")
    for ch in sorted(face.table, key=ord):
        gid = info["cmap"].get(ord(ch))
        if gid is None:
            errors.append(f"U+{ord(ch):04X} assente dalla cmap")
            continue
        if info["advance"][gid] != face.advance(ch) * UNIT:
            errors.append(f"U+{ord(ch):04X}: avanzamento {info['advance'][gid]}")
        ref = face.mask(ch)
        polys = [[(x / UNIT, fg.ASCENT - y / UNIT) for (x, y) in c] for c in info["glyphs"][gid]]
        got = (pix.poly_mask(ref.shape[1], ref.shape[0], polys, combined=True)
               if polys else np.zeros_like(ref))
        if not np.array_equal(ref, got):
            errors.append(f"U+{ord(ch):04X}: contorni diversi dal bitmap")
    return errors


def verify_freetype(path: Path, face: bitfont.Face, k: int = 10) -> list[str]:
    """FreeType (Pillow) deve caricare il font e disegnare ogni glifo quasi come il bitmap.

    Tolleranza: l'auto-hinter di FreeType, attivo in Pillow, può spostare di un pixel del
    dispositivo un bordo; si chiede una sovrapposizione (IoU) di almeno 0,9 a 10x.
    """
    errors = []
    for ch in sorted(face.table, key=ord):
        if ch == " ":
            continue
        ref = np.repeat(np.repeat(face.mask(ch), k, 0), k, 1)
        got = freetype_mask(path, ch, EM_PX * k, ref.shape[1] // k)
        iou = (ref & got).sum() / max(1, (ref | got).sum())
        if iou < 0.9:
            errors.append(f"U+{ord(ch):04X}: FreeType IoU {iou:.2f}")
    for text in PHRASES:
        ref = np.repeat(np.repeat(face.mask(text), k, 0), k, 1)
        got = freetype_mask(path, text, EM_PX * k, ref.shape[1] // k)
        iou = (ref & got).sum() / max(1, (ref | got).sum())
        if iou < 0.95:
            errors.append(f"frase {text[:20]!r}: FreeType IoU {iou:.2f}")
    return errors


def verify(path: Path, face: bitfont.Face) -> list[str]:
    return verify_roundtrip(path, face) + verify_freetype(path, face)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fg.check(fg.REGULAR, "regolare")
    fg.check(fg.BOLD, "grassetto")
    ok = True
    for fname, (face, style, bold) in FONTS.items():
        data = ttf.build(face.table, face.advances, family="CAR Pixel", style=style,
                         unit=UNIT, ascent=fg.ASCENT, descent=fg.DESCENT, em_px=EM_PX,
                         version=VERSION, copyright_text=COPYRIGHT, license_text=LICENSE,
                         bold=bold, x_height=fg.XH, cap_height=fg.CAP)
        path = OUT / fname
        path.write_bytes(data)
        errs = verify(path, face)
        n = len([c for c in face.table if c != " "]) + 1
        print(f"{fname}: {len(data)} byte, {n} glifi, errori: {len(errs)}")
        for e in errs[:20]:
            print("  ", e)
        ok &= not errs
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
