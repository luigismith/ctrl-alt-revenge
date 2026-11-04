# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - scrive layers.json (formato della specifica §6) per i piani in tools/env/out/layers.

  python -I tools/env/assemble.py [cartella dei piani]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envlib as E  # noqa: E402


def write(d=None):
    d = d or os.path.join(E.OUT, "layers")
    st = json.load(open(os.path.join(d, "street_split.json")))
    nr = json.load(open(os.path.join(d, "near_info.json")))
    fg = json.load(open(os.path.join(d, "fg_info.json")))
    wc = json.load(open(os.path.join(d, "warped_info.json")))
    layers = [
        dict(name="sky", image="sky.png", scroll=0.0, y=wc["sky"]["y"], repeat_x=0, z=-100),
        dict(name="far", image="far.png", scroll=0.125, y=wc["far"]["y"], repeat_x=0, z=-90, emissive="far_emis.png"),
        dict(name="mid", image="mid.png", scroll=0.25, y=wc["mid"]["y"], repeat_x=0, z=-80, emissive="mid_emis.png"),
        dict(name="near", image="near.png", scroll=0.5, y=nr["y"], repeat_x=0, z=-70, emissive="near_emis.png"),
        dict(name="backdrop", image="backdrop.png", scroll=1.0, y=st["backdrop_y"], repeat_x=0, z=-20,
             emissive="backdrop_emis.png"),
        dict(name="floor", image="floor.png", scroll=1.0, y=st["floor_y"], repeat_x=0, z=-10,
             emissive="floor_emis.png"),
        dict(name="fg", image="fg.png", scroll=1.25, y=fg["y"], repeat_x=0, z=100, emissive="fg_emis.png"),
    ]
    meta = {"format": 1, "level_width": E.LEVEL_W, "floor_band": list(E.BAND), "layers": layers}
    with open(os.path.join(d, "layers.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("[assemble] layers.json:", [(l["name"], l["y"]) for l in layers])
    return meta


if __name__ == "__main__":
    write(sys.argv[1] if len(sys.argv) > 1 else None)
