# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Mockup di verifica (1x e 3x) in tools/fxui/out/check/: HUD, titolo, scritte, effetti in scena.

  python -I tools/fxui/make_mockups.py

Usa solo gli asset generati in tools/fxui/out/assets/ e i font CAR Pixel (stesso disegno
del TTF). Il ritratto è un segnaposto disegnato qui. Per la scala dei personaggi, se ci
sono, usa i fotogrammi della prova "spike-3d2pixel" del laboratorio (solo per queste
immagini di controllo, che non vanno nel repo).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bitfont  # noqa: E402
import palette as P  # noqa: E402
import pix  # noqa: E402

ASSETS = HERE / "out" / "assets"
CHECK = HERE / "out" / "check"
LAB = Path(os.environ.get("USERPROFILE", "")) / "ctrlaltrevenge-lab"
SPIKE = LAB / "ricerca-2026-11-03" / "prove" / "spike-3d2pixel" / "out" / "frames"


def ui() -> dict:
    return json.loads((ASSETS / "ui" / "ui.json").read_text(encoding="utf-8"))


def fx() -> dict:
    return json.loads((ASSETS / "fx" / "fx.json").read_text(encoding="utf-8"))


def ui_img(key: str) -> np.ndarray:
    return pix.load(ASSETS / "ui" / ui()[key]["image"])


def fx_frame(name: str, k: int) -> tuple[np.ndarray, tuple[int, int]]:
    d = fx()[name]
    fw, fh = d["frame"]
    strip = pix.load(ASSETS / "fx" / d["image"])
    return strip[:, k * fw:(k + 1) * fw], tuple(d["anchor"])


def put_fx(img, name, k, x, y, flip=False):
    fr, (ax, ay) = fx_frame(name, k)
    if flip:
        fr = fr[:, ::-1]
        ax = fr.shape[1] - ax
    pix.over(img, fr, x - ax, y - ay)


def text(img, x, y, s, face=bitfont.BOLD, color=P.CREAM, right=False, center=False):
    w = face.width(s)
    if right:
        x -= w
    if center:
        x -= w // 2
    bitfont.draw(img, x, y, s, face, color, shadow=P.INK)


# ------------------------------------------------------------------------------------
# fondali segnaposto
# ------------------------------------------------------------------------------------

def backdrop(seed: int = 7, floor: bool = True) -> np.ndarray:
    """Notte: cielo blu-viola, palazzi con finestre rosse e arancio, asfalto viola."""
    rng = np.random.default_rng(seed)
    c = pix.new(384, 216, P.BG)
    for y in range(216):
        t = y / 215
        c[y, :] = (int(12 + 22 * t), int(10 + 10 * t), int(30 + 34 * t), 255)
    x = -6
    while x < 390:
        w = int(rng.integers(22, 46))
        h = int(rng.integers(70, 140))
        top = 150 - h
        c[max(0, top):150, max(0, x):max(0, x + w)] = (26, 21, 52, 255)
        for wy in range(top + 5, 146, 7):
            for wx in range(x + 3, x + w - 3, 6):
                if 0 <= wx < 382 and rng.random() < 0.25:
                    col = (226, 74, 58, 255) if rng.random() < 0.6 else (236, 160, 66, 255)
                    c[wy:wy + 2, wx:wx + 3] = col
        x += w + int(rng.integers(0, 6))
    if floor:
        for y in range(150, 216):
            t = (y - 150) / 66
            c[y, :] = (int(46 - 14 * t), int(32 - 10 * t), int(66 - 18 * t), 255)
        # riflessi bagnati dei neon
        for _ in range(9):
            rx = int(rng.integers(0, 370))
            ry = int(rng.integers(160, 210))
            c[ry, rx:rx + int(rng.integers(6, 18))] = (120, 50, 70, 255)
    # trave della ferrovia in primo piano
    c[0:12, :] = (18, 14, 30, 255)
    c[12, :] = (40, 32, 62, 255)
    return c


def sprite(kind: str, anim: str, k: int) -> np.ndarray | None:
    p = SPIKE / kind / anim / f"{anim}_{k:02d}.png"
    if not p.exists():
        return None
    return pix.load(p)


def put_sprite(img, spr, x, y, flip=False):
    """Disegna lo sprite con i piedi (ultima riga opaca, centro) in (x, y)."""
    if spr is None:
        return
    if flip:
        spr = spr[:, ::-1]
    a = spr[..., 3] > 0
    ys, xs = np.nonzero(a)
    fy = ys.max()
    fx_ = int(np.median(xs[ys >= fy - 2]))
    pix.over(img, spr, x - fx_, y - fy)


def placeholder_portrait() -> np.ndarray:
    """Ritratto segnaposto 32x32: busto con codino e barba grigi, camicia ocra, occhio cyan."""
    im = pix.new(32, 32)
    skin, skin_d = pix.hexc("#c9906a"), pix.hexc("#9a6448")
    hair, hair_d = pix.hexc("#b4b2b8"), pix.hexc("#7d7b86")
    shirt, shirt_d = pix.hexc("#c27c25"), pix.hexc("#8a5214")
    hood = pix.hexc("#6c6a74")
    pix.paint(im, pix.ellipse_mask(32, 32, 16, 34, 15, 9), shirt)
    pix.paint(im, pix.ellipse_mask(32, 32, 16, 36, 15, 9) & (np.arange(32)[:, None] > 29), shirt_d)
    pix.paint(im, pix.ellipse_mask(32, 32, 16, 26, 8, 4), hood)
    pix.paint(im, pix.ellipse_mask(32, 32, 16, 15, 7, 9), skin)
    pix.paint(im, pix.ellipse_mask(32, 32, 19, 16, 3, 8) & pix.ellipse_mask(32, 32, 16, 15, 7, 9), skin_d)
    pix.paint(im, pix.ellipse_mask(32, 32, 16, 21, 6, 4) & (np.arange(32)[:, None] >= 18), hair)
    pix.paint(im, pix.ellipse_mask(32, 32, 16, 8, 7, 4), hair)
    pix.paint(im, pix.ellipse_mask(32, 32, 12, 4, 2.5, 2.5), hair_d)
    im[14, 12:14] = pix.hexc("#2a1c22")
    im[14, 18:20] = P.CYAN
    im[13, 18:20] = P.CYAN_WHITE
    return im


# ------------------------------------------------------------------------------------
# HUD
# ------------------------------------------------------------------------------------

def draw_bar(img, x, y, w, h, ratio, ghost, enemy=False):
    sfx = "_enemy" if enemy else ""
    back = ui_img("bar_back" + sfx)
    gh = ui_img("bar_ghost" + sfx)
    fill = ui_img("bar_fill" + sfx)
    frame = ui_img("bar_frame" + sfx)
    pix.over(img, back[:, :w], x, y)
    gw, fw = int(round(w * ghost)), int(round(w * ratio))
    if gw > 0:
        pix.over(img, gh[:, :gw], x, y)
    if fw > 0:
        pix.over(img, fill[:, :fw], x, y)
    pix.over(img, frame, x - 2, y - 2)


def draw_hud(img, score=4200, lives=3, gig=0.70, gig_ghost=0.82, enemy="PUNK", en=0.40, en_ghost=0.55,
             arrow_frame=0):
    L = ui()["hud_layout"]
    x, y = L["portrait_frame"]
    pix.over(img, ui_img("portrait_back"), x, y)
    px_, py_ = L["portrait"]
    pix.over(img, placeholder_portrait(), px_, py_)
    pix.over(img, ui_img("portrait_frame"), x, y)
    text(img, *L["gig_name"], "GIG")
    lx, ly = L["gig_lives_right"]
    text(img, lx, ly, "×%d" % lives, color=P.GOLD_HI, right=True)
    bx, by, bw, bh = L["gig_bar"]
    draw_bar(img, bx, by, bw, bh, gig, gig_ghost)
    if enemy:
        text(img, *L["enemy_name"], enemy)
        ex, ey, ew, eh = L["enemy_bar"]
        draw_bar(img, ex, ey, ew, eh, en, en_ghost, enemy=True)
    sx, sy = L["score_right"]
    text(img, sx, sy, "%06d" % score, color=P.GOLD_HI, right=True)
    if arrow_frame is not None:
        d = ui()["go_arrow"]
        fw, fh = d["frame"]
        strip = ui_img("go_arrow")
        ax, ay = L["go_arrow_right_center_y"]
        pix.over(img, strip[:, arrow_frame * fw:(arrow_frame + 1) * fw], ax - fw, ay - fh // 2)


def hud_mockup() -> np.ndarray:
    img = backdrop()
    # scena: GIG colpisce il punk (scala dei personaggi ed effetti in contesto)
    gig = sprite("v5", "Punch_Cross", 2)
    thug = sprite("thug_v5", "Hit_Chest", 1)
    put_fx(img, "ombra", 1, 150, 186)
    put_fx(img, "ombra", 1, 205, 188)
    put_sprite(img, gig, 150, 186)
    put_sprite(img, thug, 205, 188, flip=True)
    put_fx(img, "hit_spark_light", 1, 191, 128)
    put_fx(img, "dust_skid", 2, 212, 188, flip=True)
    put_fx(img, "ombra", 0, 300, 196)
    put_sprite(img, sprite("thug_v5", "Guard_Idle", 0), 300, 196, flip=True)
    put_fx(img, "glint", 3, 282, 132)
    # pioggia leggera
    rng = np.random.default_rng(3)
    for _ in range(26):
        k = int(rng.integers(0, 4))
        put_fx(img, "rain_streak", k, int(rng.integers(0, 384)), int(rng.integers(20, 200)))
    for (sx, sy, k) in ((60, 175, 1), (250, 202, 2), (340, 170, 0)):
        put_fx(img, "rain_splash", k, sx, sy)
    draw_hud(img)
    return img


# ------------------------------------------------------------------------------------
# titolo e scritte
# ------------------------------------------------------------------------------------

def title_mockup() -> np.ndarray:
    img = backdrop(11)
    logo = ui_img("logo")
    sub = ui_img("subtitle")
    lx = (384 - logo.shape[1]) // 2
    pix.over(img, logo, lx, 14)
    pix.over(img, sub, (384 - sub.shape[1]) // 2, 14 + logo.shape[0] + 3)
    put_fx(img, "ombra", 1, 70, 204)
    put_sprite(img, sprite("v5", "Guard_Idle", 0), 70, 204)
    text(img, 192, 168, "PREMI INVIO", color=P.GOLD_HI, center=True)
    text(img, 380, 203, "© 2026 Luigi Massari", face=bitfont.REGULAR, color=P.CREAM_LO2, right=True)
    return img


def messages_mockup() -> np.ndarray:
    screens = []
    for key, extra in (("stage_card_1", None), ("msg_zone_clear", "go"), ("msg_pause", "menu"),
                       ("msg_continue", "count"), ("msg_game_over", None), ("msg_demo_end", "end")):
        img = backdrop(5)
        im = ui_img(key)
        y = 70 if key != "msg_pause" else 52
        pix.over(img, im, (384 - im.shape[1]) // 2, y)
        if extra == "go":
            d = ui()["go_arrow"]
            fw, fh = d["frame"]
            pix.over(img, ui_img("go_arrow")[:, :fw], 381 - fw, 64 - fh // 2 + 60)
        if extra == "menu":
            for i, s in enumerate(("RIPRENDI", "COMANDI", "ESCI AL TITOLO")):
                col = P.GOLD_HI if i == 0 else P.CREAM
                text(img, 150, 100 + 14 * i, s, color=col)
            text(img, 140, 100, "▶", color=P.GOLD_HI)
        if extra == "count":
            text(img, 192, 110, "9", color=P.GOLD_HI, center=True)
            text(img, 192, 150, "Premi ATTACCO per continuare", face=bitfont.REGULAR, center=True)
        if extra == "end":
            text(img, 192, 112, "PUNTEGGIO   004200", center=True)
            text(img, 192, 140, "Grazie per aver giocato!", face=bitfont.REGULAR, center=True)
        draw_hud(img, arrow_frame=None, enemy="BRUTO", en=0.85, en_ghost=0.85)
        screens.append(img)
    grid = pix.new(384 * 3 + 8, 216 * 2 + 4, P.INK)
    for i, s in enumerate(screens):
        r, c = divmod(i, 3)
        pix.over(grid, s, c * 388, r * 220)
    return grid


def main() -> int:
    CHECK.mkdir(parents=True, exist_ok=True)
    hud = hud_mockup()
    pix.save(hud, CHECK / "hud_mockup_1x.png")
    pix.save(pix.upscale(hud, 3), CHECK / "hud_mockup_3x.png")
    # HUD da solo su fondo scuro uniforme (come chiede la verifica)
    plain = pix.new(384, 216, P.BG)
    draw_hud(plain)
    pix.save(plain, CHECK / "hud_plain_1x.png")
    pix.save(placeholder_portrait(), CHECK / "portrait_placeholder.png")
    pix.save(pix.upscale(plain, 3), CHECK / "hud_plain_3x.png")
    t = title_mockup()
    pix.save(t, CHECK / "title_mockup_1x.png")
    pix.save(pix.upscale(t, 3), CHECK / "title_mockup_3x.png")
    m = messages_mockup()
    pix.save(m, CHECK / "messages_1x.png")
    print("mockup in", CHECK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
