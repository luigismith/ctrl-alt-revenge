# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - GIG di spalle per la schermata del titolo («Il tetto», Luigi, 7 novembre 2026).

  python -I tools/sprites/titolo_gig.py [--yaw 300] [--pitch 4] [--alto 190] [--quadro 240] [--prova]

GIG fermo (primo fotogramma di Idle_Loop, testa dritta), visto da dietro e un po' dal suo lato destro: si vedono
la schiena con la camicia ocra, il codino, il braccio cyber sul bordo sinistro della sagoma e, di taglio, l'occhio
aziendale. Si usa il passo dei primi piani di char_build.py (stessa pipeline di pixel degli sprite), ma con la figura
intera: il centro dell'inquadratura scende dalla testa al busto e la densità si calcola perché GIG sia alto
--alto pixel.

Escono in tools/sprites/out/titolo/:
  gig_titolo.png          i pixel, sulla tavolozza finale dello sprite di GIG;
  gig_titolo_normali.png  la normal map, per la luce del Wind Day nel gioco;
  gig_titolo_cyan.png     la maschera del cyan (braccio e occhio), per farlo pulsare;
  gig_titolo_4x.png       la tavola di controllo.
Il render a colori ad alta risoluzione va nella cartella privata condivisa (ambienti-ai/titolo/), mai nel repo.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chars as B  # noqa: E402
import charlib as C  # noqa: E402
import pixelize as PX  # noqa: E402

OUT = os.path.join(C.OUT, "titolo")
RIM = "#d8603a"                              # il riflesso della città sotto la polvere


def cyan_mask(im: np.ndarray) -> np.ndarray:
    rgb = im[..., :3].astype(int)
    return (im[..., 3] > 0) & (rgb[..., 2] - rgb[..., 0] >= 0.3 * 255) & (rgb[..., 1] - rgb[..., 0] >= 0.2 * 255)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--yaw", type=float, default=300.0, help="270 = di spalle; di più = si vede il suo lato destro")
    ap.add_argument("--pitch", type=float, default=4.0)
    ap.add_argument("--alto", type=int, default=190, help="altezza di GIG in pixel")
    ap.add_argument("--quadro", type=int, default=240, help="lato del quadro in pixel")
    ap.add_argument("--dz", type=float, default=-0.78, help="metri dal centro della testa al centro del quadro")
    ap.add_argument("--beauty", type=int, default=1920, help="lato del render a colori (0 = niente)")
    ap.add_argument("--azione", default="Idle_Loop", help="la clip della posa (UAL)")
    ap.add_argument("--fotogramma", type=int, default=1)
    ap.add_argument("--uscita", default=OUT)
    ap.add_argument("--prova", action="store_true", help="niente render a colori: solo i pixel")
    args = ap.parse_args()

    cid = "gig"
    cfg = C.char_cfg(cid)
    # la testa (cima-mento) di GIG è circa 1/7,3 della figura: da lì la densità
    face_px = args.alto / 7.3
    sp = dict(B.CLOSEUP_DEFAULT)
    sp.update(name="gig_titolo", action=args.azione, frame=args.fotogramma, yaw_deg=args.yaw, pitch_deg=args.pitch, face_px=face_px, frame_px=args.quadro,
              dz=args.dz, faces="right", variants=[], beauty=not args.prova and args.beauty > 0,
              beauty_px=args.beauty)
    raw = os.path.join(C.OUT, "raw_closeup", sp["name"])
    job = C.base_job(cid, cfg, "closeup", raw)
    job["closeup"] = sp
    job["beauty_png"] = os.path.join(raw, "closeup", "beauty_full.png") if sp["beauty"] else None
    C.run_blender("char_build.py", job, timeout=1200, tag="titolo-gig")
    d = os.path.join(raw, "closeup")
    meta = C.load_json(os.path.join(d, "meta.json"))
    fdata = C.load_json(os.path.join(d, "frames.json"))
    pcfg = B.closeup_pixel_cfg(cfg, meta, sp)
    # sul tetto la luce viene dalla città, davanti a GIG e a destra: il riflesso sul bordo è quello rosso-arancio
    # del Wind Day (non il magenta dei neon degli sprite) e sta sul bordo destro della sagoma
    pcfg.update(rim=RIM, rim_dir=[0.85, 0.35, -0.4], key=[0.55, 0.65, 0.25])
    sh = PX.Shader(pcfg, cfg["palette"], meta["ids"])
    spr, _ = PX.pixelize_sequence(d, fdata[:1], meta["ss"], sh, pcfg, loop=False)
    normals = getattr(PX.pixelize_sequence, "normals", [None])[0]
    dbg = os.path.join(B.final_dir(cid), cid + ".debug.json")
    pal = [PX.hx(c) for c in C.load_json(dbg)["palette"]] if os.path.exists(dbg) else None
    if pal is not None:
        pal.append(PX.hx(RIM))
    img = B.snap_to_palette(spr[0], pal) if pal is not None else spr[0]
    rgb = img[..., :3]
    magenta = (img[..., 3] > 0) & np.all(rgb == PX.hx("#e0559b"), -1)  # il riflesso degli sprite, se resta
    rgb[magenta] = PX.hx(RIM)
    # ritaglio: tutta la sagoma, con 2 px d'aria
    ys, xs = np.nonzero(img[..., 3] > 0)
    y0, y1, x0, x1 = max(0, ys.min() - 2), ys.max() + 3, max(0, xs.min() - 2), xs.max() + 3
    img = img[y0:y1, x0:x1]
    out = args.uscita
    os.makedirs(out, exist_ok=True)
    Image.fromarray(img, "RGBA").save(os.path.join(out, "gig_titolo.png"))
    if normals is not None:
        Image.fromarray(np.asarray(normals)[y0:y1, x0:x1]).save(os.path.join(out, "gig_titolo_normali.png"))
    cm = cyan_mask(img)
    Image.fromarray((cm * 255).astype(np.uint8)).save(os.path.join(out, "gig_titolo_cyan.png"))
    tiles = [("pixel", img)]
    if normals is not None:
        tiles.append(("normali", np.asarray(normals)[y0:y1, x0:x1]))
    B.closeup_sheet(tiles, "GIG per il titolo", f"yaw {args.yaw}, {img.shape[1]}x{img.shape[0]} px, cyan {int(cm.sum())} px",
                    os.path.join(out, "gig_titolo_4x.png"), scale=3)
    if job["beauty_png"] and os.path.exists(job["beauty_png"]):
        bd = B.condiviso_dir("ambienti-ai", "titolo")
        os.makedirs(bd, exist_ok=True)
        shutil.copyfile(job["beauty_png"], os.path.join(bd, "gig_titolo_render.png"))
    C.say(f"GIG per il titolo: {img.shape[1]}x{img.shape[0]} px, cyan {int(cm.sum())} px -> {out}")


if __name__ == "__main__":
    main()
