#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Lo zip delle voci di un capitolo, per gli allegati della release: manifest.json e <scena>/*.ogg, senza le cartelle di lavoro.

Uso:  python -I tools/voci/zip_voci.py [capitolo]      scrive <laboratorio>\\tts\\voci\\voci-<capitolo>.zip

Il laboratorio è %CAR_LAB%, altrimenti %USERPROFILE%\\ctrlaltrevenge-lab. Lo zip non va nel repo: è un allegato della release.
"""
import json
import os
import sys
import zipfile

LAB = os.path.join(os.environ.get("CAR_LAB") or os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"),
                                                             "ctrlaltrevenge-lab"), "tts")


def main():
    cap = sys.argv[1] if len(sys.argv) > 1 else "prologo"
    root = os.path.join(LAB, "voci", cap)
    man = json.load(open(os.path.join(root, "manifest.json"), encoding="utf-8"))
    files = ["manifest.json"] + [b["file"] for b in man["battute"].values()]
    out = os.path.join(LAB, "voci", "voci-%s.zip" % cap)
    tmp = out + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:  # gli .ogg sono già compressi
        for f in files:
            z.write(os.path.join(root, f.replace("/", os.sep)), f)
    os.replace(tmp, out)
    print(out, len(files), "file,", round(os.path.getsize(out) / 1024), "KB, filtro TV:", man.get("tv"))


if __name__ == "__main__":
    main()
