#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Il confronto del filtro TV nella pagina delle voci: ogni battuta finale a ogni livello, più quella senza filtro.

Uso (Python isolato, dopo «finali» di voci.py):
  python -I -X utf8 tools/voci/scelta_tv.py [--capitolo prologo] [--battute <file>] [--voci <file>] [--lab <cartella>]

Parte dai .wav senza filtro di voci\\<capitolo>\\_finali e scrive in voci\\scelta\\: audio\\tv\\<livello>\\<scena>__<id>.ogg
e tv.json. Usa la stessa funzione di voci.py, quindi si sente quello che finirà nel gioco. Audio e dati restano nel
laboratorio. I nomi delle scene nella pagina vengono da pagina.scene di voci.json.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voci as V  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capitolo", default="prologo")
    ap.add_argument("--battute", help="di default docs/lore/battute/<capitolo>.json")
    ap.add_argument("--voci", default=os.path.join(V.REPO, "docs", "lore", "voci", "voci.json"))
    ap.add_argument("--lab", default=V.TTS, help="la cartella tts del laboratorio")
    a = ap.parse_args()
    a.battute = a.battute or os.path.join(V.REPO, "docs", "lore", "battute", a.capitolo + ".json")
    a.voce, a.solo, a.uscita, a.tv = None, None, None, None
    cfg, lines = V.load(a.voci), V.load(a.battute)
    root = V.out_root(a)
    man = V.load(os.path.join(root, "manifest.json"))
    out = os.path.join(a.lab, "voci", "scelta")
    tv = cfg["tv"]
    # La proposta di Claude per prima, poi le altre, poi «senza» come riferimento.
    ordine = [tv["livello"]] + [k for k in tv["livelli"] if k != tv["livello"]] + ["senza"]
    livelli = []
    for k in ordine:
        p = tv["livelli"].get(k, {})
        livelli.append({"nome": k, "titolo": p.get("titolo", "Senza filtro"),
                        "descrizione": p.get("descrizione", "Le voci come escono dal trattamento, per confronto."),
                        "proposta": k == tv["livello"], "riferimento": k == "senza"})
    who = cfg["chi_ha_la_voce"][a.capitolo]
    scene = []
    for scena, battute in lines["scene"].items():
        if scena not in who:
            continue
        righe = []
        for lid, text in battute.items():
            key = "%s/%s" % (scena, lid)
            b = man["battute"].get(key)
            if not b:
                continue
            wav = os.path.join(root, "_finali", scena, lid + ".wav")
            files = {}
            for k in ordine:
                rel = "audio/tv/%s/%s__%s.ogg" % (k, scena, lid)
                dst = os.path.join(out, rel.replace("/", os.sep))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                V.codifica(a, cfg, b["trattamento"], wav, dst, livello=k)
                files[k] = rel
            righe.append({"key": key, "chi": b["chi"].upper(),
                          "testo": text, "trattamento": b["trattamento"], "file": files})
            print("%-22s %s" % (key, " ".join(ordine)), flush=True)
        scene.append({"scena": scena, "righe": righe})
    V.save({"capitolo": a.capitolo, "nomi_scena": cfg.get("pagina", {}).get("scene", {}), "generato": time.strftime("%Y-%m-%d %H:%M"), "livello_attuale": tv["livello"],
            "ronzio_hz": tv.get("ronzio_hz"), "campionamento_hz": tv.get("campionamento_hz"),
            "livelli": livelli, "scene": scene}, os.path.join(out, "tv.json"))
    print(os.path.join(out, "tv.json"))


if __name__ == "__main__":
    main()
