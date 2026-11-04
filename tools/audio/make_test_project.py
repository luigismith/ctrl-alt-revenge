#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Crea il progetto Godot di prova dell'audio in tools/audio/out/test_project/.

Non si esegue mai Godot su game/ (lo usa chi scrive il codice): questo progetto ha le stesse
impostazioni di game/project.godot, ma solo gli autoload Sfx e Music, i WAV degli effetti,
il layout dei bus e le prove di tools/audio/godot_tests/.
Accanto al progetto (test_project/tools/run_godot.sh) c'è una copia identica di
tools/run_godot.sh: lo script usa <sua cartella>/../game, quindi gira sul progetto di prova.

  python -I tools/audio/make_test_project.py                   # script da tools/audio/out/godot_src
  python -I tools/audio/make_test_project.py --src game/src/audio --sfx game/assets/sfx
poi:
  tools/audio/out/test_project/tools/run_godot.sh 180 --headless --import
  REQUIRE_DONE=1 tools/audio/out/test_project/tools/run_godot.sh 180 --headless -s res://tests/test_audio.gd
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "test_project"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=HERE / "out" / "godot_src",
                    help="cartella con sfx.gd e music_director.gd")
    ap.add_argument("--bus-layout", type=Path, help="default_bus_layout.tres (predefinito: in --src o in game/)")
    ap.add_argument("--sfx", type=Path, default=HERE / "out" / "sfx", help="cartella con i WAV, i .import e mix.json")
    ap.add_argument("--clean", action="store_true", help="cancella anche la cache .godot del progetto di prova")
    a = ap.parse_args()

    game = OUT / "game"
    if a.clean and OUT.exists():
        shutil.rmtree(OUT)
    for d in ("tools", "game/src/audio", "game/src/test", "game/scenes", "game/tests", "game/assets/sfx"):
        (OUT / d).mkdir(parents=True, exist_ok=True)

    shutil.copyfile(ROOT / "tools" / "run_godot.sh", OUT / "tools" / "run_godot.sh")
    shutil.copyfile(ROOT / "game" / "icon.svg", OUT / "game" / "icon.svg")

    proj = (ROOT / "game" / "project.godot").read_text(encoding="utf-8")
    proj = re.sub(r'config/name="[^"]*"', 'config/name="CAR prova audio"', proj)
    proj = re.sub(r'run/main_scene="[^"]*"', 'run/main_scene="res://scenes/audio_test.tscn"', proj)
    proj = re.sub(r"\[autoload\]\n(.*?)\n\n", '[autoload]\n\nSfx="*res://src/audio/sfx.gd"\n'
                  'Music="*res://src/audio/music_director.gd"\n\n', proj, flags=re.S)
    (game / "project.godot").write_text(proj, encoding="utf-8", newline="\n")

    for name in ("sfx.gd", "music_director.gd"):
        shutil.copyfile(a.src / name, game / "src" / "audio" / name)
    bus = a.bus_layout or (a.src / "default_bus_layout.tres")
    if not bus.exists():
        bus = ROOT / "game" / "default_bus_layout.tres"
    shutil.copyfile(bus, game / "default_bus_layout.tres")

    n = 0
    for p in sorted(a.sfx.iterdir()):
        if p.suffix == ".wav" or p.name == "mix.json":
            shutil.copyfile(p, game / "assets" / "sfx" / p.name)
            n += 1
        elif p.name.endswith(".wav.import"):
            dst = game / "assets" / "sfx" / p.name
            # un .import già completato da Godot nel progetto di prova resta com'è
            if not dst.exists() or "uid=" not in dst.read_text(encoding="utf-8"):
                shutil.copyfile(p, dst)

    tests = HERE / "godot_tests"
    shutil.copyfile(tests / "test_audio.gd", game / "tests" / "test_audio.gd")
    shutil.copyfile(tests / "audio_test.gd", game / "src" / "test" / "audio_test.gd")
    shutil.copyfile(tests / "audio_test.tscn", game / "scenes" / "audio_test.tscn")
    print(f"progetto di prova pronto in {OUT} ({n} file audio)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
