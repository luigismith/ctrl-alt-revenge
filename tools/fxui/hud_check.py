# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Verifica dell'HUD in Godot: confronto pixel per pixel con il mockup Python.

Si lancia con  python -I tools/fxui/godot_check.py hud  (dopo make_ui, make_fx, make_mockups).
"""
from __future__ import annotations

import shutil

import numpy as np

import godot_check as gc
import pix

HERE = gc.HERE


def run() -> int:
    gc.make_project("res://hud_check.tscn")
    gc.add_fonts(HERE / "out" / "fonts")
    gc.add_tree(HERE / "out" / "assets" / "ui", "assets/ui")
    gc.add_tree(HERE / "out" / "assets" / "fx", "assets/fx")
    shutil.copy(HERE / "out" / "check" / "portrait_placeholder.png", gc.PROJ / "portrait_placeholder.png")
    png = HERE / "out" / "check" / "godot_hud_1x.png"
    got = gc.capture("hud_check", png)
    ref = pix.load(HERE / "out" / "check" / "hud_plain_1x.png")
    diff = (got[..., :3].astype(int) != ref[..., :3].astype(int)).any(-1)
    n = int(diff.sum())
    print(f"HUD Godot contro mockup Python: pixel diversi {n} su {diff.size}")
    if n:
        vis = got.copy()
        vis[diff] = (255, 0, 255, 255)
        pix.save(pix.upscale(vis, 3), HERE / "out" / "check" / "godot_hud_diff_3x.png")
    pix.save(pix.upscale(got, 3), HERE / "out" / "check" / "godot_hud_3x.png")
    # effetti: solo per guardarli disegnati da Godot
    png_fx = HERE / "out" / "check" / "godot_fx_1x.png"
    gc.run_godot(60, "res://hud_check.tscn", "--", f"out={gc._win(png_fx)}", "mode=fx")
    fx_img = pix.load(png_fx)
    pix.save(pix.upscale(fx_img, 3), HERE / "out" / "check" / "godot_fx_3x.png")
    return 0 if n == 0 else 1
