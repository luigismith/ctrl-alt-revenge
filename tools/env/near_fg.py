# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - piani 'near' (palazzi del secondo isolato, parallasse 0,5) e 'fg' (impalcato della
ferrovia visto dal basso, parallasse 1,25) dal G-buffer delle scene omonime.

  python -I tools/env/near_fg.py [near] [fg]
"""
import json
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envlib as E  # noqa: E402
import paint as P  # noqa: E402
from materials import RAMPS  # noqa: E402

# le sfocature (spill_sigma) sono in px: a 60 px/m (17,5 nel piano near) valgono 1,25 volte quelle di progetto
NEAR_CFG = dict(amb=0.72, key=0.6, spill=0.9, spill_sigma=(1.5 * E.S, 6.0 * E.S), wet=0, dither=0.0, inner=True,
                depth_thr=1.2, outline=True, fog=0.12, fogcol="#1c1f4e", cel=P.CEL_3TONI)
FG_MAX_Y = E.px(26)    # 33
FG_CFG = dict(amb=0.45, key=0.35, spill=1.2, spill_sigma=(2.0 * E.S, 8.0 * E.S), wet=0, dither=0.0, inner=True,
              depth_thr=0.25, outline=True, cel=P.CEL_3TONI)


def windows_near(cv: P.Canvas):
    """Finestre dei palazzi lontani: tende, persiane, tapparelle, sagome; scelte per oggetto (seme fisso)."""
    for oid in np.unique(cv.oid[cv.A & np.isin(cv.cls, [E.CLS["WINDOW_LIT"], E.CLS["GLASS"]])]):
        m = cv.oid == oid
        ys, xs = np.nonzero(m)
        if len(ys) < 6:
            continue
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        r = random.Random(int(oid) * 7919)
        lit = cv.is_em[ys[0], xs[0]]
        sub = (slice(y0, y1), slice(x0, x1))
        mm = m[sub]
        h, w = y1 - y0, x1 - x0
        yy, xx = np.mgrid[0:h, 0:w]
        if lit:
            base = cv.emi[ys[0], xs[0]].copy()
            style = r.choice(["curtain", "blind", "figure", "plain", "half"])
            col = np.zeros((h, w, 3), np.float32)
            col[:] = base
            dark = base * np.array([0.55, 0.42, 0.42])
            if style == "curtain":
                col[(xx < 2) | (xx >= w - 2)] = dark
            elif style == "blind":
                col[yy % 2 == 0] = dark
            elif style == "figure":
                cx = r.randint(2, max(2, w - 3))
                col[((yy - h // 3) ** 2 + (xx - cx) ** 2 <= 2) | ((yy > h // 3 + 1) & (np.abs(xx - cx) <= 1))] = dark * 0.7
            elif style == "half":
                col[yy < h // 2] = dark
            col[0, :] = dark * 0.8
            cv.col[sub][mm] = col[mm]
            cv.emi[sub][mm] = col[mm]
        else:
            style = r.choice(["shutter", "shutter", "glass", "blind_dark"])
            base = cv.col[ys[0], xs[0]].copy()
            col = np.zeros((h, w, 3), np.float32)
            if style == "shutter":
                # persiane chiuse: listelli orizzontali, colore del legno verniciato (scuro)
                pc = np.array(P.rgb(r.choice(["#2a3a3a", "#3a2a2a", "#2c2836"])), np.float32)
                col[:] = pc
                col[yy % 2 == 0] = pc * 0.7
                col[:, w // 2] = pc * 0.6
            elif style == "blind_dark":
                col[:] = base
                col[yy % 2 == 0] = base * 0.75
            else:
                col[:] = base
                d = (xx + yy) % 7 == 0
                col[d] = base * 1.5
            cv.col[sub][mm] = col[mm]
            cv.final[sub][mm] = False


def fog(rgb01, cv, cfg):
    k = cfg.get("fog", 0)
    if k <= 0:
        return rgb01
    fc = P.rgb(cfg["fogcol"])
    out = rgb01 * (1 - k) + fc[None, None] * k
    return np.where(cv.is_em[..., None], rgb01 * (1 - k * 0.3) + fc * k * 0.3, out)


def build_near(out_dir=None):
    out_dir = out_dir or os.path.join(E.OUT, "layers")
    cv = P.load("near")
    P.patterns(cv, seed=17)
    windows_near(cv)
    P.run_ops(cv)
    rgb_lit, S = P.shade(cv, NEAR_CFG)
    rgb_lit = fog(rgb_lit, cv, NEAR_CFG)
    cfg = dict(NEAR_CFG, extra_ramps=["night"])
    q = P.quantize(cv, rgb_lit, cfg)
    res, alpha = P.outlines(cv, q, cfg)
    em = P.emissive_mask(cv, res, alpha, strength=0.45, cel=bool(NEAR_CFG.get("cel")))
    rgba = P.to_rgba(res, alpha)
    rows = np.nonzero(rgba[..., 3].any(1))[0]
    y0 = int(rows.min())
    E.save_rgba(os.path.join(out_dir, "near.png"), rgba[y0:], 3)
    E.save_rgba(os.path.join(out_dir, "near_emis.png"), em[y0:], 0)
    info = dict(y=y0 + int(cv.y0), w=rgba.shape[1], h=rgba.shape[0] - y0)
    json.dump(info, open(os.path.join(out_dir, "near_info.json"), "w"), indent=1)
    print("[near]", info)
    return info


def build_fg(out_dir=None):
    out_dir = out_dir or os.path.join(E.OUT, "layers")
    cv = P.load("fg")
    P.patterns(cv, seed=27)
    P.run_ops(cv)
    rgb_lit, S = P.shade(cv, FG_CFG)
    q = P.quantize(cv, rgb_lit, FG_CFG)
    res, alpha = P.outlines(cv, q, FG_CFG)
    em = P.emissive_mask(cv, res, alpha, strength=0.6, cel=bool(FG_CFG.get("cel")))
    rgba = P.to_rgba(res, alpha)
    rows = np.nonzero(rgba[..., 3].any(1))[0]
    # il primo piano resta sopra FG_MAX_Y: sotto cominciano le insegne del fondale, che devono leggersi
    # con la telecamera ferma in partenza e nelle ondate (y 34-56)
    y1 = min(int(rows.max()) + 1, FG_MAX_Y)
    E.save_rgba(os.path.join(out_dir, "fg.png"), rgba[:y1], 3)
    E.save_rgba(os.path.join(out_dir, "fg_emis.png"), em[:y1], 0)
    info = dict(y=int(cv.y0), w=rgba.shape[1], h=y1)
    json.dump(info, open(os.path.join(out_dir, "fg_info.json"), "w"), indent=1)
    print("[fg]", info)
    return info


if __name__ == "__main__":
    which = sys.argv[1:] or ["near", "fg"]
    if "near" in which:
        build_near()
    if "fg" in which:
        build_fg()
