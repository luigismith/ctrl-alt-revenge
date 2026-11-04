# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Tavole di verifica degli effetti (4x) in tools/fxui/out/check/.

  python -I tools/fxui/make_sheets.py

Ogni effetto: i fotogrammi su fondo scuro (colore del progetto) e su un viola medio
(muro illuminato), con il riquadro del fotogramma e due tacche che segnano l'ancora.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bitfont  # noqa: E402
import palette as P  # noqa: E402
import pix  # noqa: E402

FX = HERE / "out" / "assets" / "fx"
CHECK = HERE / "out" / "check"
BG_LIGHT = pix.hexc("#4a4066")
BOX = pix.hexc("#3a3550")
TICK = pix.hexc("#ff40ff")


def sheet(name: str, d: dict, per_row: int = 6, k: int = 4):
    strip = pix.load(FX / d["image"])
    fw, fh = d["frame"]
    n = d["count"]
    ax, ay = d["anchor"]
    cols = min(per_row, n)
    rows = (n + cols - 1) // cols
    cell_w, cell_h = fw + 6, fh + 6
    label_h = 14
    W = cols * cell_w + 4
    H = label_h + 2 * rows * cell_h + 8
    img = pix.new(W, H, P.BG)
    info = f"{name}  {fw}x{fh} x{n}  ticks {d['ticks']}  ancora {ax},{ay}"
    bitfont.draw(img, 2, 1, info, bitfont.REGULAR, P.CREAM)
    for half, bg in enumerate((P.BG, BG_LIGHT)):
        for i in range(n):
            r, c = divmod(i, cols)
            x = 2 + c * cell_w + 2
            y = label_h + (half * rows + r) * cell_h + 2
            img[y - 1:y + fh + 1, x - 1:x + fw + 1] = BOX
            img[y:y + fh, x:x + fw] = bg
            pix.over(img, strip[:, i * fw:(i + 1) * fw], x, y)
            img[y - 2, x + ax] = TICK
            img[y + ay, x - 2] = TICK
    out = pix.upscale(img, k)
    pix.save(out, CHECK / f"fx_{name}_{k}x.png")
    return out


def main() -> int:
    fx = json.loads((FX / "fx.json").read_text(encoding="utf-8"))
    for name, d in fx.items():
        per_row = 3 if d["frame"][0] >= 64 else 4 if d["frame"][0] >= 40 else 6
        if name == "rain_sheet":
            per_row = 1
        sheet(name, d, per_row)
    print("tavole in", CHECK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
