# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - copia gli sfondi e gli oggetti di scena finiti da tools/env/out in game/assets.

Ogni file si copia prima con un nome temporaneo (.tmp, che Godot non importa) e poi si rinomina:
chi lavora al codice non vede mai un PNG a metà.
  python -I tools/env/install.py
"""
import hashlib
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envlib as E  # noqa: E402
import warped  # noqa: E402

ENV_FILES = ["layers.json", "sky.png", "far.png", "far_emis.png", "mid.png", "mid_emis.png", "near.png",
             "near_emis.png", "backdrop.png", "backdrop_emis.png", "floor.png", "floor_emis.png", "fg.png",
             "fg_emis.png"]
PROP_FILES = ["bin.png", "bin.json", "apple.png", "apple.json", "cable.png", "cable.json"]
WC_ZIP = os.path.join(E.LAB, "sources", "chars", "oga-warped-city", "warped_city_files.zip")
WC_ZIP_SHA = "cf0e69a203206f529adbaf1f82d4c5f165ca9cdb49d3995ec88d135b37e40e3e"


def put(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".tmp"
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def install():
    layers = os.path.join(E.OUT, "layers")
    props = os.path.join(E.OUT, "props")
    env_dst = os.path.join(E.ROOT, "game", "assets", "env", "sotto_la_linea")
    prop_dst = os.path.join(E.ROOT, "game", "assets", "props")
    wc_dst = os.path.join(E.ROOT, "game", "assets", "third_party", "ansimuz-warped-city")
    for f in ENV_FILES:
        put(os.path.join(layers, f), os.path.join(env_dst, f))
    for f in PROP_FILES:
        put(os.path.join(props, f), os.path.join(prop_dst, f))
    # file CC0 usati di Warped City, così come sono nello zip (controllo dell'hash)
    if sha(WC_ZIP) != WC_ZIP_SHA:
        raise SystemExit("lo zip di Warped City non è quello registrato")
    for name, h in warped.SHA256.items():
        src = os.path.join(warped.WC_DIR, name)
        if sha(src) != h:
            raise SystemExit("hash diverso: " + name)
        put(src, os.path.join(wc_dst, name))
    put(os.path.join(E.ROOT, "tools", "env", "SOURCE_warped_city.md"), os.path.join(wc_dst, "SOURCE.md"))
    print("[install] %d file in %s, %d in %s, %d in %s" % (len(ENV_FILES), env_dst, len(PROP_FILES), prop_dst,
                                                            len(warped.SHA256), wc_dst))


if __name__ == "__main__":
    install()
