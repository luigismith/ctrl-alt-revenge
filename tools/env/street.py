# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - "Sotto la Linea": dal G-buffer della scena 'street' ai piani backdrop e floor.

  python -I tools/env/street.py

Scrive in tools/env/out/layers/: backdrop.png, backdrop_emis.png, floor.png, floor_emis.png (+ anteprime
x3) e street_split.json (righe di partenza dei due piani sullo schermo).
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envlib as E  # noqa: E402
import paint as P  # noqa: E402

CFG = dict(amb=0.62, key=0.7, spill=1.0, spill_sigma=(2.5, 10.0), wet=0.2, wet_comp=0.5, dither=0.0,
           inner=True, depth_thr=0.3, outline=True, cel=P.CEL_3TONI)


def build(out_dir=None):
    out_dir = out_dir or os.path.join(E.OUT, "layers")
    cv = P.load("street")
    P.patterns(cv, seed=7)
    P.run_ops(cv)
    rgb_lit, S = P.shade(cv, CFG)
    q = P.quantize(cv, rgb_lit, CFG)
    # pavimento: suolo davanti al filo delle facciate (Y < 0.6), più il cordolo
    Y = cv.pos[..., 1]
    Z = cv.pos[..., 2]
    # tutto ciò che sta davanti al filo delle facciate ed è basso (suolo, cordolo, tombini, caditoie, bordi
    # delle pozzanghere) va nel pavimento; il resto (anche la parte alta di pali e sacchi) nel fondale
    ground = cv.A & (Y < 0.55) & (Z < 0.3) & ~cv.is_em
    # il contorno esterno va solo verso il vuoto (parallasse), mai sul bordo fra pavimento e fondale
    res, alpha = P.outlines(cv, q, CFG)
    floor_m = ground & alpha
    back_m = alpha & ~ground
    em = P.emissive_mask(cv, res, alpha, cel=bool(CFG.get("cel")))
    # il pavimento prende anche gli aloni sul suolo; il fondale tutto il resto
    em_floor = em.copy()
    em_floor[~floor_m] = 0
    em_back = em.copy()
    em_back[floor_m] = 0
    rgba = P.to_rgba(res, alpha)
    floor = rgba.copy()
    floor[~floor_m] = 0
    back = rgba.copy()
    back[~back_m] = 0
    rows_f = np.nonzero(floor[..., 3].any(1))[0]
    fy0 = int(rows_f.min())
    rows_b = np.nonzero(back[..., 3].any(1))[0]
    by1 = int(rows_b.max()) + 1
    E.save_rgba(os.path.join(out_dir, "floor.png"), floor[fy0:], 3)
    E.save_rgba(os.path.join(out_dir, "floor_emis.png"), em_floor[fy0:], 0)
    E.save_rgba(os.path.join(out_dir, "backdrop.png"), back[:by1], 3)
    E.save_rgba(os.path.join(out_dir, "backdrop_emis.png"), em_back[:by1], 0)
    # anteprima unita (fondale + pavimento) a 1x, per i controlli
    E.save_rgba(os.path.join(out_dir, "street_full.png"), rgba, 0)
    E.save_rgba(os.path.join(out_dir, "street_full_emis.png"), em, 0)
    info = dict(floor_y=fy0 + int(cv.y0), backdrop_y=int(cv.y0), backdrop_h=by1, floor_h=E.SCREEN_H - fy0,
                colours=int(len(np.unique(rgba[rgba[..., 3] > 0][:, :3], axis=0))))
    json.dump(info, open(os.path.join(out_dir, "street_split.json"), "w"), indent=1)
    print("[street]", info)
    return info


if __name__ == "__main__":
    build()
