# -*- coding: utf-8 -*-
"""I controlli a ogni push: la coda, l'inbox e il sito.

  python strumenti/controlli.py               # controlla e basta (esce con 1 se qualcosa non va)
  python strumenti/controlli.py --apri-veto   # in più apre la issue di veto ai contenuti «pronto» che non ce l'hanno

Le parole vietate non compaiono mai nei messaggi: solo file, campo e riga.
"""
import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import coda  # noqa: E402
from comune import RADICE, gh_disponibile  # noqa: E402

MAX_MB_INBOX = 50


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--apri-veto", action="store_true")
    arg = a.parse_args()
    errori = []

    vietate = coda.parole_vietate()
    contenuti = coda.tutti()
    ids = [str(c.get("id")) for c in contenuti]
    if len(ids) != len(set(ids)):
        errori.append("due contenuti con lo stesso id")
    for c in contenuti:
        e = coda.valida(c, vietate)
        # una bozza può essere incompleta, ma non può contenere spoiler
        if c.get("stato") == "bozza":
            e = [x for x in e if "lista nera" in x or "lista degli spoiler" in x]
        errori += e

    for f in (RADICE / "inbox").rglob("*"):
        if f.is_file() and f.stat().st_size > MAX_MB_INBOX * 1e6:
            errori.append(f"inbox: {f.relative_to(RADICE)} supera {MAX_MB_INBOX} MB (comprimerlo prima)")
    for cartella in (RADICE / "inbox").iterdir() if (RADICE / "inbox").exists() else []:
        if cartella.is_dir() and not (cartella / "nota.md").exists():
            errori.append(f"inbox: {cartella.name} non ha la nota.md")

    for pagina in ("docs/index.html", "docs/en/index.html"):
        p = RADICE / pagina
        if not p.exists():
            errori.append(f"sito: manca {pagina}")
        elif re.search(r"\{\{[\w.]+\}\}", p.read_text(encoding="utf-8")):
            errori.append(f"sito: {pagina} ha segnaposto non riempiti")

    if arg.apri_veto and gh_disponibile():
        for c in contenuti:
            if c.get("stato") == "pronto" and not c.get("issue") and not coda.valida(c, vietate):
                coda.apri_veto(c)

    if errori:
        print("[controlli] NON superati:")
        for e in errori:
            print(f"  - {e}")
        sys.exit(1)
    print(f"[controlli] ok: {len(contenuti)} contenuti in coda, sito in ordine")


if __name__ == "__main__":
    main()
