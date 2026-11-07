# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - rigenera gli oggetti di scena 3D di "Sotto la Linea": il bidone (bin) e la mela (apple).

  python -I tools/env/build_all.py            # render 3D e pixel, in tools/env/out/props/
  python -I tools/env/build_all.py --install  # ... e poi li copia in game/assets/props (install.py)

Serve il laboratorio in %USERPROFILE%/ctrlaltrevenge-lab (Blender 4.5 portable).
Tutto il lavoro sta in tools/env/out/ (ignorata da git). Nessun passo usa numeri casuali senza seme.

Gli sfondi, il pavimento e il cavo scoperto non si fanno più qui (7 novembre 2026): li fanno
tools/ambienti/componi_slice.py, patina_floor.py e cavo_rivolo.py, e tools/env/taranto.py per cielo, far e mid.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import props  # noqa: E402


def main(install=False):
    t0 = time.time()
    os.makedirs(props.RAW, exist_ok=True)
    props.build_bin()
    props.build_apple()
    if install:
        import install as I
        I.install()
    print("[build_all] fatto in %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main("--install" in sys.argv)
