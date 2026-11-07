#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""La pagina per scegliere le voci a orecchio: anteprime trattate delle prese migliori e dati.json.

Uso (Python isolato, dopo «scegli» di voci.py per ogni proposta di voce da confrontare):
  python -I -X utf8 tools/voci/scelta.py [--capitolo prologo] [--battute <file>] [--voci <file>] [--lab <cartella>]

Scrive in <lab>\\voci\\scelta\\: audio\\<voce>\\<scena>__<id>__<seme>.ogg e dati.json. La pagina è scelta/index.html,
il server è scelta_server.py; le scelte di Luigi finiscono in scelte_luigi.json. Audio e dati restano nel laboratorio.
I punti da ascoltare meglio («fuoco») e i titoli delle voci stanno nel blocco «pagina» di voci.json, che è privato.
"""
import argparse
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voci as V  # noqa: E402

PER_VOCE = 3
# Il fuoco di una battuta (voci.json, pagina.fuoco["<scena>/<id>"]): indice della prima parola da ascoltare
# (negativo = dalla fine), quante parole, etichetta e nota; con "fruscio": true misura anche la g dolce.


def fruscio_ms(y, sr, t0):
    import librosa
    if sr != 16000:
        y = librosa.resample(y, orig_sr=sr, target_sr=16000)
        sr = 16000
    t0 = max(0.0, t0 - 0.05)
    seg = y[int(t0 * sr): int((t0 + 0.30) * sr)]
    if seg.size < 512:
        return None
    S = np.abs(librosa.stft(seg, n_fft=256, hop_length=40)) ** 2
    f = librosa.fft_frequencies(sr=sr, n_fft=256)
    hi = S[f > 2500].sum(0)
    lo = S[(f > 100) & (f < 1000)].sum(0)
    tot = S.sum(0)
    act = tot > tot.max() * 0.01
    return round(float(((hi / (lo + 1e-9) > 1.0) & act).sum() * 40 / sr * 1000))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capitolo", default="prologo")
    ap.add_argument("--battute", help="di default docs/lore/battute/<capitolo>.json")
    ap.add_argument("--voci", default=os.path.join(V.REPO, "docs", "lore", "voci", "voci.json"))
    ap.add_argument("--lab", default=V.TTS, help="la cartella tts del laboratorio")
    a = ap.parse_args()
    a.battute = a.battute or os.path.join(V.REPO, "docs", "lore", "battute", a.capitolo + ".json")
    a.voce, a.solo, a.uscita = None, None, None
    cfg, lines = V.load(a.voci), V.load(a.battute)
    pag = cfg.get("pagina", {})
    FUOCO, TITOLI = pag.get("fuoco", {}), pag.get("titoli", {})
    voci_dir = os.path.join(a.lab, "voci")
    out = os.path.join(voci_dir, "scelta")
    tere_prop = list(cfg["voci"]["tere"]["proposte"])
    radici = {"messo": {cfg["voci"]["messo"]["voce"]: os.path.join(voci_dir, a.capitolo)}, "tere": {}}
    for p in tere_prop:
        r = os.path.join(voci_dir, a.capitolo) if p == cfg["voci"]["tere"]["voce"] else os.path.join(voci_dir, "alternative", "tere_" + p)
        if os.path.exists(os.path.join(r, "_scelte.json")):
            radici["tere"][p] = r
    asr = V.Asr(os.path.join(a.lab, "modelli", cfg["modelli"]["controllo"]["cartella"]))
    who = cfg["chi_ha_la_voce"][a.capitolo]
    scelte_cache = {}
    scene = []
    for scena, battute in lines["scene"].items():
        if scena not in who:
            continue
        righe = []
        for lid, text in battute.items():
            key = "%s/%s" % (scena, lid)
            vkey = who[scena].get(lid)
            if not vkey:
                spk = lid.rsplit("_", 1)[0].upper()
                righe.append({"key": key, "chi": spk, "testo": text, "voce": False})
                continue
            base, bcfg, own = V.resolve(cfg, vkey)
            tr = own.get("trattamento") or bcfg["trattamento"]
            riga = {"key": key, "chi": "MESSO" if base == "messo" else "TERE", "base": base, "testo": text, "voce": True,
                    "trattamento": tr, "fuoco": FUOCO.get(key), "prese": {}, "attuale": {}}
            if own.get("dove"):
                riga["dove"] = own["dove"]
            for nome, root in radici[base].items():
                if root not in scelte_cache:
                    scelte_cache[root] = V.load(os.path.join(root, "_scelte.json"))
                sc = scelte_cache[root].get(key)
                if not sc:
                    continue
                cands = sc["candidate"]
                fz = FUOCO.get(key)
                riga["attuale"][nome] = sc["scelta"]["seme"]
                lista = []
                for c in cands:
                    src = os.path.join(root, c["presa"])
                    rel = "audio/%s/%s__%s__%d.ogg" % (nome, scena, lid, c["seme"])
                    dst = os.path.join(out, rel.replace("/", os.sep))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    tmp = dst[:-4] + ".wav"
                    V.ffmpeg(["-i", src, "-af", cfg["trattamenti"][tr] + ",aresample=24000", "-ac", "1", "-c:a", "pcm_s16le", tmp])
                    w, sr = sf.read(tmp, dtype="float32")
                    w = V.trim(w, sr)
                    sf.write(tmp, w, sr, subtype="PCM_16")
                    item = {"seme": c["seme"], "cer": c["cer"], "durata_s": round(w.size / sr, 2), "sentito": c["sentito"], "file": rel}
                    if fz:
                        ch = [x for x in asr.run(tmp, words=True).get("chunks", []) if x["text"].strip()]
                        if ch:
                            i0 = fz["da"] if fz["da"] >= 0 else len(ch) + fz["da"]
                            sel = ch[max(0, i0): max(0, i0) + fz["quante"]]
                            if sel:
                                t0 = sel[0]["timestamp"][0]
                                t1 = sel[-1]["timestamp"][1] or (w.size / sr)
                                item["clip"] = [round(max(0.0, t0 - 0.08), 2), round(min(w.size / sr, t1 + 0.15), 2)]
                                if fz.get("fruscio"):
                                    item["fruscio_ms"] = fruscio_ms(w, sr, t0)
                    V.ffmpeg(["-i", tmp, "-c:a", "libvorbis", "-q:a", "6", dst])
                    os.remove(tmp)
                    lista.append(item)
                # Le migliori per voce: la scelta attuale prima, poi l'ordine di «scegli».
                # Dove si misura il fruscio della g dolce, fra quelle senza errori conta il fruscio più lungo.
                if fz and fz.get("fruscio"):
                    mn = min(x["cer"] for x in lista)
                    ok = [x for x in lista if x["cer"] <= mn + 0.02]
                    ok.sort(key=lambda x: -(x.get("fruscio_ms") or 0))
                    att = [x for x in lista if x["seme"] == sc["scelta"]["seme"]]
                    lista = (att + [x for x in ok if x not in att])[:PER_VOCE]
                else:
                    lista = lista[:PER_VOCE]
                tolti = []
                for f in os.listdir(os.path.dirname(dst)):
                    if f.startswith("%s__%s__" % (scena, lid)) and f not in [os.path.basename(x["file"]) for x in lista]:
                        tolti.append(f)
                for f in tolti:
                    os.remove(os.path.join(os.path.dirname(dst), f))
                riga["prese"][nome] = lista
                print("%-22s %-10s %s" % (key, nome, " ".join(str(x["seme"]) for x in lista)), flush=True)
            righe.append(riga)
        scene.append({"scena": scena, "righe": righe})
    demo = {}
    for p in tere_prop:
        f = "demo_voci_%s.mp4" % a.capitolo if p == cfg["voci"]["tere"]["voce"] else "demo_voci_%s_tere-%s.mp4" % (a.capitolo, p)
        if os.path.exists(os.path.join(voci_dir, "demo", f)):
            demo[p] = "../demo/" + f
    dati = {
        "capitolo": a.capitolo,
        "generato": __import__("time").strftime("%Y-%m-%d %H:%M"),
        "voce_tere_attuale": cfg["voci"]["tere"]["voce"],
        "voci_tere": [{"nome": p, "titolo": TITOLI.get(p, p), "descrizione": cfg["voci"]["tere"]["proposte"][p]["instruct"],
                       "demo": demo.get(p), "pronta": p in radici["tere"]} for p in tere_prop],
        "voce_messo": {"nome": cfg["voci"]["messo"]["voce"], "titolo": TITOLI.get(cfg["voci"]["messo"]["voce"]),
                       "descrizione": cfg["voci"]["messo"]["riferimento"]["instruct"]},
        "scene": scene,
        "pagina": {k: v for k, v in pag.items() if k not in ("fuoco", "titoli")},
    }
    V.save(dati, os.path.join(out, "dati.json"))
    print(os.path.join(out, "dati.json"))


if __name__ == "__main__":
    main()
