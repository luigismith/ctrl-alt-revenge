# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - copia il bidone e la mela finiti da tools/env/out/props in game/assets/props.

Ogni file si copia prima con un nome temporaneo (.tmp, che Godot non importa) e poi si rinomina:
chi lavora al codice non vede mai un PNG a metà.
  python -I tools/env/install.py
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envlib as E  # noqa: E402

PROP_FILES = ["bin.png", "bin.json", "apple.png", "apple.json"]


def put(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".tmp"
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def install():
    src = os.path.join(E.OUT, "props")
    dst = os.path.join(E.ROOT, "game", "assets", "props")
    for f in PROP_FILES:
        put(os.path.join(src, f), os.path.join(dst, f))
    print("[install] %d file in %s" % (len(PROP_FILES), dst))


if __name__ == "__main__":
    install()
