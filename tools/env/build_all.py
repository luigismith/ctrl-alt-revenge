# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - rigenera tutti gli sfondi e gli oggetti di scena di "Sotto la Linea".

  python -I tools/env/build_all.py            # render 3D, pittura, Warped City, oggetti, layers.json, verifiche
  python -I tools/env/build_all.py --install  # ... e poi copia i file finiti in game/assets (install.py)

Serve il laboratorio in %USERPROFILE%/ctrlaltrevenge-lab (Blender 4.5 portable, kit CC0, Warped City).
Tutto il lavoro sta in tools/env/out/ (ignorata da git). Nessun passo usa numeri casuali senza seme.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble  # noqa: E402
import compose  # noqa: E402
import envlib as E  # noqa: E402
import near_fg  # noqa: E402
import props  # noqa: E402
import render_scenes  # noqa: E402
import street  # noqa: E402
import taranto  # noqa: E402
import warped  # noqa: E402


def main(install=False):
    t0 = time.time()
    for sc in ("street", "near", "fg"):
        render_scenes.render(sc)
    street.build()
    near_fg.build_near()
    near_fg.build_fg()
    warped.build()
    taranto.build()  # il cielo e il piano lontano di Taranto sostituiscono quelli di Warped City
    os.makedirs(props.RAW, exist_ok=True)
    props.build_bin()
    props.build_apple()
    props.build_cable()
    assemble.write()
    d = os.path.join(E.OUT, "layers")
    out = os.path.join(E.OUT, "verify")
    meta, layers = compose.load_layers(d)
    compose.mockups(layers, out, compose.DEFAULT_SHOTS)
    compose.sheet(layers, os.path.join(out, "layers_sheet.png"))
    path, rep = compose.pan(layers, out, step=4)
    print("[build_all] pan:", path, rep["layer_steps"])
    print("[build_all] verifiche:", compose.checks(layers, meta))
    if install:
        import install as I
        I.install()
    print("[build_all] fatto in %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main("--install" in sys.argv)
