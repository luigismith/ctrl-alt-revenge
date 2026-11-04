# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Verifica in Godot 4.7.2 di font e interfaccia, in un progetto temporaneo.

  python -I tools/fxui/godot_check.py fonts   # font: confronto pixel per pixel a 1x
  python -I tools/fxui/godot_check.py hud     # HUD costruito con nodi Godot e gli asset veri

Il progetto sta in tools/fxui/out/godot_check/ con le stesse impostazioni di
game/project.godot (senza autoload) e gli asset nelle stesse cartelle res://assets/...
di game/, così i file .import prodotti qui valgono anche là.
Godot si lancia sempre con tools/run_godot.sh (timeout, log, controllo degli errori).
La finestra si apre per pochi secondi: il rendering serve davvero.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import bitfont  # noqa: E402
import pix  # noqa: E402

PROJ = HERE / "out" / "godot_check"


def find_bash() -> str:
    """Git Bash: dalla variabile CAR_BASH, accanto a git.exe oppure dal PATH."""
    env = os.environ.get("CAR_BASH", "")
    if env and Path(env).is_file():
        return env
    git = shutil.which("git")
    if git:
        # .../Git/cmd/git.exe oppure .../Git/mingw64/bin/git.exe -> .../Git/usr/bin/bash.exe
        for up in Path(git).resolve().parents:
            cand = up / "usr" / "bin" / "bash.exe"
            if cand.is_file():
                return str(cand)
    found = shutil.which("bash")
    if found and "system32" not in found.lower():   # niente bash di WSL
        return found
    raise SystemExit("Git Bash non trovato: impostare CAR_BASH con il percorso di bash.exe")

FONT_IMPORT = """[remap]

importer="font_data_dynamic"
type="FontFile"

[params]

Rendering=null
antialiasing=0
generate_mipmaps=false
disable_embedded_bitmaps=true
multichannel_signed_distance_field=false
msdf_pixel_range=8
msdf_size=48
allow_system_fallback=false
force_autohinter=false
hinting=0
subpixel_positioning=0
keep_rounding_remainders=true
oversampling=0.0
Fallbacks=null
fallbacks=[]
Compress=null
compress=true
preload=[]
language_support={}
script_support={}
opentype_features={}
"""


def _win(p: Path) -> str:
    return str(p).replace("\\", "/")


def run_godot(secs: int, *args: str) -> None:
    # il progetto temporaneo si passa con GODOT_PROJECT: run_godot.sh mette un solo --path
    cmd = [find_bash(), _win(ROOT / "tools" / "run_godot.sh"), str(secs), *args]
    env = dict(os.environ)
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    env["GODOT_PROJECT"] = _win(PROJ)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip())
        raise SystemExit(f"run_godot.sh fallito ({r.returncode}): {' '.join(args)}")


def make_project(main_scene: str) -> None:
    """Ricrea il progetto (la cache .godot si butta: l'import è veloce e così è pulito)."""
    if PROJ.exists():
        shutil.rmtree(PROJ)
    PROJ.mkdir(parents=True)
    src = (ROOT / "game" / "project.godot").read_text(encoding="utf-8")
    out, skip = [], False
    for line in src.splitlines():
        if line.startswith("["):
            skip = line.strip() == "[autoload]"
        if skip:
            continue
        if line.startswith("config/name="):
            line = 'config/name="fxui_check"'
        if line.startswith("config/icon="):
            continue
        if line.startswith("run/main_scene="):
            line = f'run/main_scene="{main_scene}"'
        out.append(line)
    (PROJ / "project.godot").write_text("\n".join(out) + "\n", encoding="utf-8")
    for gd in (HERE / "godot").glob("*.gd"):
        shutil.copy(gd, PROJ / gd.name)
        name = gd.stem
        (PROJ / f"{name}.tscn").write_text(
            "[gd_scene format=3]\n\n"
            f'[ext_resource type="Script" path="res://{gd.name}" id="1_s"]\n\n'
            f'[node name="{name}" type="Node2D"]\nscript = ExtResource("1_s")\n',
            encoding="utf-8")


def add_fonts(font_dir: Path) -> None:
    dst = PROJ / "assets" / "fonts"
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(font_dir.glob("*.ttf")):
        (dst / (f.name + ".import")).write_text(FONT_IMPORT, encoding="utf-8")
        shutil.copy(f, dst / f.name)


def add_tree(src: Path, rel: str) -> None:
    dst = PROJ / rel
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def capture(scene: str, png: Path, secs: int = 60) -> np.ndarray:
    if png.exists():
        png.unlink()
    run_godot(180, "--headless", "--import")
    run_godot(secs, f"res://{scene}.tscn", "--", f"out={_win(png)}")
    return pix.load(png)


# ------------------------------------------------------------------------------------
# font
# ------------------------------------------------------------------------------------

PHRASES = [
    "CTRL+ALT REVENGE! PICCHIA DURO A SCORRIMENTO",
    "GIG \u00d73  PUNK  BRUTO  004200  999999  VAI \u25b6",
    "Citt\u00e0, pi\u00f9, perch\u00e9, cos\u00ec, per\u00f2, \u00e8 l\u2019arena. \u00c8 COS\u00cc!",
    "\u00c0\u00c8\u00c9\u00cc\u00d2\u00d9 \u00e0\u00e8\u00e9\u00ec\u00f2\u00f9 \u00c1\u00cd\u00d3\u00da \u00e1\u00ed\u00f3\u00fa",
    "0123456789 abcdefghijklmnopqrstuvwxyz",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ !\"#$%&'()*+,-./:;<=>?@",
    "[\\]^_`{|}~ \u00ab \u00bb \u00b7 \u00b0 \u00a9 \u2018\u2019 \u201c\u201d \u2026 \u2013 \u2014 \u25b6\u25c0\u25b2\u25bc\u2665",
]


def expected_fonts() -> tuple[np.ndarray, np.ndarray]:
    """Maschera attesa del testo bianco e maschera della zona confrontata."""
    m = np.zeros((216, 384), bool)
    y = 2
    for face in (bitfont.REGULAR, bitfont.BOLD):
        for p in PHRASES:
            t = face.mask(p)
            h, w = t.shape
            w = min(w, 384 - 2)
            m[y:y + h, 2:2 + w] |= t[:, :w]
            y += 13
    region = np.zeros((216, 384), bool)
    region[:190, :] = True
    # il Label con l'ombra
    lab = bitfont.BOLD.mask("GIG \u00d73   PUNK   004200")
    m[192:192 + lab.shape[0], 2:2 + lab.shape[1]] |= lab
    region[190:216, :196] = True
    return m, region


def check_fonts() -> int:
    make_project("res://font_check.tscn")
    add_fonts(HERE / "out" / "fonts")
    png = HERE / "out" / "godot_font_check.png"
    img = capture("font_check", png)
    rgb = img[..., :3].astype(int)
    white = (rgb == 255).all(-1)
    exp, region = expected_fonts()
    diff = (white != exp) & region
    n = int(diff.sum())
    print(f"pixel bianchi attesi {int(exp.sum())}, trovati {int((white & region).sum())}, diversi {n}")
    # l'ombra del Label (rosso puro) deve stare esattamente a +1,+1 dal testo
    red = (rgb[..., 0] == 255) & (rgb[..., 1] == 0) & (rgb[..., 2] == 0)
    lab = np.zeros_like(exp)
    lm = bitfont.BOLD.mask("GIG \u00d73   PUNK   004200")
    lab[192:192 + lm.shape[0], 2:2 + lm.shape[1]] = lm
    exp_shadow = pix.shift(lab, 1, 1) & ~lab
    nsh = int(((red != exp_shadow) & region & (np.arange(216)[:, None] >= 190)).sum())
    print(f"ombra del Label: pixel diversi {nsh}")
    vis = img.copy()
    vis[diff] = (255, 0, 255, 255)
    pix.save(pix.upscale(vis, 3), HERE / "out" / "godot_font_check_diff_3x.png")
    return 0 if (n == 0 and nsh == 0) else 1


def main() -> int:
    what = sys.argv[1] if len(sys.argv) > 1 else "fonts"
    if what == "fonts":
        return check_fonts()
    if what == "hud":
        import hud_check
        return hud_check.run()
    raise SystemExit("uso: godot_check.py fonts|hud")


if __name__ == "__main__":
    sys.exit(main())
