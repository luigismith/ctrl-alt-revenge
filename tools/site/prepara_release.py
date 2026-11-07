# SPDX-License-Identifier: MIT
"""Raccoglie in una cartella gli allegati della release "musica-demo", quelli che il sito scarica
(.github/workflows/sito.yml) e che non stanno nel repo:

- music.json e gli OGG che nomina, dalla musica del laboratorio (<laboratorio>/music);
- battute-<capitolo>.json, dalla cartella privata della storia (docs/lore/battute/<capitolo>.json);
- voci-<capitolo>.zip, dalle voci del laboratorio (<laboratorio>/tts/voci/<capitolo>/): solo
  manifest.json e gli OGG, senza i file di lavoro che iniziano con "_".

Non carica niente: stampa i file e il comando per caricarli. La cartella di uscita non deve stare nel
repo (la musica e le battute non ci vanno mai).

    python -I tools/site/prepara_release.py <cartella di uscita> [--capitoli prologo]
"""
import argparse
import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--capitoli", default="prologo", help="capitoli della demo, separati da virgole")
    ap.add_argument("--lab", default=os.environ.get("CAR_LAB") or os.path.join(os.path.expanduser("~"), "ctrlaltrevenge-lab"))
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    if os.path.commonpath([out, ROOT]) == ROOT:
        print("La cartella di uscita sta nel repo: sceglierne una fuori.", file=sys.stderr)
        return 1
    os.makedirs(out, exist_ok=True)
    files = []

    music = os.path.join(a.lab, "music")
    man = os.path.join(music, "music.json")
    if os.path.isfile(man):
        with open(man, encoding="utf-8") as f:
            tracks = json.load(f).get("tracks", [])
        names = {"music.json"}
        for t in tracks:
            names.add(t["file"])
            names.update(l["file"] for l in t.get("layers", []))
        for n in sorted(names):
            src = os.path.join(music, n)
            if not os.path.isfile(src):
                print("Manca %s, che music.json nomina." % src, file=sys.stderr)
                return 1
            shutil.copy2(src, os.path.join(out, n))
            files.append((n, src))
    else:
        print("Avviso: nessuna musica in %s." % music)

    for cap in [c.strip() for c in a.capitoli.split(",") if c.strip()]:
        src = os.path.join(ROOT, "docs", "lore", "battute", cap + ".json")
        if os.path.isfile(src):
            n = "battute-%s.json" % cap
            shutil.copy2(src, os.path.join(out, n))
            files.append((n, src))
        else:
            print("Avviso: mancano le battute %s." % src)
        voci = os.path.join(a.lab, "tts", "voci", cap)
        if os.path.isfile(os.path.join(voci, "manifest.json")):
            n = "voci-%s.zip" % cap
            with zipfile.ZipFile(os.path.join(out, n), "w", zipfile.ZIP_STORED) as z:
                for d, dirs, fs in os.walk(voci):
                    dirs[:] = sorted(x for x in dirs if not x.startswith("_"))
                    for fn in sorted(fs):
                        if fn.startswith("_") or not (fn == "manifest.json" or fn.endswith(".ogg")):
                            continue
                        p = os.path.join(d, fn)
                        z.write(p, os.path.relpath(p, voci).replace(os.sep, "/"))
            files.append((n, voci))
        else:
            print("Avviso: nessuna voce in %s." % voci)

    print("Allegati per la release musica-demo, in %s:" % out)
    for n, src in files:
        print("  %-28s %9d byte  da %s" % (n, os.path.getsize(os.path.join(out, n)), src))
    print("Per caricarli (sostituisce quelli con lo stesso nome):")
    print('  gh release upload musica-demo --clobber "%s"/*' % out.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
