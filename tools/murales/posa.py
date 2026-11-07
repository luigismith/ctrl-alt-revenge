# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""I personaggi in posa per le vignette dei murales: il nostro render 3D, da dare a ChatGPT come riferimento.

  python -I tools/murales/posa.py --chi gig --azione Idle_Loop [--fotogramma 1] [--yaw 55] [--pitch 4]
                                  [--inquadra figura|busto|volto] [--lato 1536] [--capitolo prologo] [--nome NOME]

Nei murales i personaggi li ridipinge ChatGPT, come per i primi piani: gli si dà il nostro render, mai una foto,
e lui lo porta nello stile di Totò. Il render è quello a colori della pipeline dei primi piani (char_build.py),
con la clip e il fotogramma della posa scelti fra le animazioni UAL del personaggio.

L'uscita va solo nella cartella privata condivisa (ctrlaltrevenge-lab-condiviso/murales/<capitolo>/pose/),
mai nel repo.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "sprites"))
import build_chars as B  # noqa: E402
import charlib as C  # noqa: E402

# quanto è alta la testa nel quadro, e dove sta il centro rispetto alla testa (metri, in giù)
INQUADRATURE = {
    "figura": dict(teste=7.3, dz=-0.78),     # tutta la figura (come GIG del titolo)
    "busto": dict(teste=3.2, dz=-0.30),      # dalla vita in su
    "volto": dict(teste=1.6, dz=0.0),        # come i primi piani
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--chi", required=True, help="esattore, gig, gig_spento, messo, rider, thug_bruiser, thug_punk")
    ap.add_argument("--azione", default="Idle_Loop", help="la clip della posa (UAL)")
    ap.add_argument("--fotogramma", type=int, default=1)
    ap.add_argument("--yaw", type=float, default=55.0, help="0 = di lato verso destra, 90 = di fronte, 270 = di spalle")
    ap.add_argument("--pitch", type=float, default=4.0, help="gradi: positivo = la camera sta più in alto")
    ap.add_argument("--inquadra", choices=sorted(INQUADRATURE), default="figura")
    ap.add_argument("--lato", type=int, default=1536, help="lato del render in pixel")
    ap.add_argument("--capitolo", default="prologo")
    ap.add_argument("--nome", help="nome del file (predefinito: <chi>_<azione>_<fotogramma>_y<yaw>)")
    args = ap.parse_args()

    q = INQUADRATURE[args.inquadra]
    cfg = C.char_cfg(args.chi)
    nome = args.nome or f"{args.chi}_{args.azione}_{args.fotogramma}_y{int(args.yaw)}"
    quadro = 240
    sp = dict(B.CLOSEUP_DEFAULT)
    sp.update(name=f"murale_{nome}", action=args.azione, frame=args.fotogramma, yaw_deg=args.yaw,
              pitch_deg=args.pitch, face_px=quadro / q["teste"] * 0.9, frame_px=quadro, dz=q["dz"], faces="right",
              variants=[], beauty=True, beauty_px=args.lato)
    raw = os.path.join(C.OUT, "raw_closeup", sp["name"])
    job = C.base_job(args.chi, cfg, "closeup", raw)
    job["closeup"] = sp
    job["beauty_png"] = os.path.join(raw, "closeup", "beauty_full.png")
    C.run_blender("char_build.py", job, timeout=1200, tag=f"posa-{args.chi}")
    if not os.path.exists(job["beauty_png"]):
        sys.exit(f"il render non è uscito: {job['beauty_png']}")
    dest = B.condiviso_dir("murales", args.capitolo, "pose")
    os.makedirs(dest, exist_ok=True)
    out = os.path.join(dest, nome + ".png")
    shutil.copyfile(job["beauty_png"], out)
    C.say(f"posa {nome} -> {out}")


if __name__ == "__main__":
    main()
