# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - pipeline degli sfondi: render del G-buffer delle scene con Blender.

  python -I tools/env/render_scenes.py street near fg

Per ogni scena scrive in tools/env/out/raw/: <scena>_job.json, i PNG delle passate, <scena>_meta.json,
<scena>_paint.json (operazioni di pittura 2D) e il log di Blender.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envlib as E  # noqa: E402
import layout as LY  # noqa: E402

SCRIPT = os.path.join(E.ROOT, "tools", "blender", "env_gbuffer.py")


def render(name, raw_dir=None, timeout=1200):
    raw_dir = raw_dir or os.path.join(E.OUT, "raw")
    S, view = LY.jobs_for(name)
    job = dict(tag=name, out_dir=raw_dir, view=view, objects=S.objects, kit_dirs=E.KIT_DIRS,
               p0=[-40.0, -40.0, -20.0], span=200.0)
    t = E.run_blender(SCRIPT, job, os.path.join(raw_dir, "%s_job.json" % name), timeout=timeout,
                      log=os.path.join(raw_dir, "%s_blender.log" % name))
    with open(os.path.join(raw_dir, "%s_paint.json" % name), "w", encoding="utf-8") as fh:
        json.dump(dict(scene=name, view=view, ops=S.paint), fh, indent=0, ensure_ascii=False)
    print("[render] %s: %d oggetti, %d operazioni di pittura, %.1f s" % (name, len(S.objects), len(S.paint), t))


if __name__ == "__main__":
    for nm in sys.argv[1:] or ["street", "near", "fg"]:
        render(nm)
