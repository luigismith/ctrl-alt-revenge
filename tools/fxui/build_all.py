# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Costruisce effetti, interfaccia e font, li verifica e (a richiesta) li installa nel gioco.

  python -I tools/fxui/build_all.py                 # genera tutto in tools/fxui/out/
  python -I tools/fxui/build_all.py --godot         # più le verifiche in Godot 4.7.2
  python -I tools/fxui/build_all.py --godot --install

--install copia in game/assets/fonts, game/assets/ui (non tocca ui/portraits/) e
game/assets/fx: ogni file arriva prima con un nome temporaneo e poi viene rinominato,
così Godot non importa file a metà; i .import dei font arrivano prima dei TTF.
Tutto è deterministico: due esecuzioni danno gli stessi byte (salvo gli uid dei .import,
che li genera Godot nel progetto di verifica).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "out"
GAME = ROOT / "game" / "assets"
PY = sys.executable

DOCS = HERE / "docs_assets"   # README e font.json da installare accanto agli asset


def step(*args: str) -> None:
    print(">>", " ".join(args))
    r = subprocess.run([PY, "-I", *args], cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(f"fallito: {' '.join(args)}")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def install_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".fxui-tmp")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def install() -> None:
    fonts_src = OUT / "fonts"
    imports = OUT / "godot_check" / "assets" / "fonts"
    # font: prima i .import (con le impostazioni giuste), poi i TTF, poi documenti
    for ttf in sorted(fonts_src.glob("*.ttf")):
        imp = imports / (ttf.name + ".import")
        if not imp.exists():
            raise SystemExit(f"manca {imp}: eseguire prima con --godot")
        install_file(imp, GAME / "fonts" / imp.name)
    for ttf in sorted(fonts_src.glob("*.ttf")):
        install_file(ttf, GAME / "fonts" / ttf.name)
    for name in ("README.md", "font.json"):
        install_file(DOCS / "fonts" / name, GAME / "fonts" / name)
    # interfaccia ed effetti: prima le immagini, per ultimo il JSON che le elenca
    for sub in ("ui", "fx"):
        src = OUT / "assets" / sub
        for png in sorted(src.glob("*.png")):
            install_file(png, GAME / sub / png.name)
        install_file(DOCS / sub / "README.md", GAME / sub / "README.md")
        js = "ui.json" if sub == "ui" else "fx.json"
        install_file(src / js, GAME / sub / js)
    print("installati in", GAME)
    for sub in ("fonts", "ui", "fx"):
        for f in sorted((GAME / sub).glob("*")):
            if f.is_file():
                print(f"  {sub}/{f.name:32s} {f.stat().st_size:7d}  {sha(f)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--godot", action="store_true", help="verifica font e HUD in Godot 4.7.2")
    ap.add_argument("--install", action="store_true", help="copia in game/assets/")
    a = ap.parse_args()
    step(str(HERE / "make_fonts.py"))
    step(str(HERE / "make_ui.py"))
    step(str(HERE / "make_fx.py"))
    step(str(HERE / "make_sheets.py"))
    step(str(HERE / "make_mockups.py"))
    if a.godot:
        step(str(HERE / "godot_check.py"), "fonts")
        step(str(HERE / "godot_check.py"), "hud")
    if a.install:
        install()
    return 0


if __name__ == "__main__":
    sys.exit(main())
