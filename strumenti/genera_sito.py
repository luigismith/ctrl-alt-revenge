# -*- coding: utf-8 -*-
"""Genera il sito: docs/index.html (italiano) e docs/en/index.html (inglese).

Un solo modello (sito/modello.html) e i testi in sito/testi/<lingua>.json.
La sezione «Dal laboratorio» si costruisce da stato.json: solo le uscite
già pubblicate e verificate, mai la coda.

L'indirizzo del sito non è scritto qui: si ricava dal repository in cui
gira (GITHUB_REPOSITORY), così lo scambio dei nomi non rompe niente.
"""
import html
import json
import os
import pathlib
import re
import sys

RADICE = pathlib.Path(__file__).resolve().parent.parent
MODELLO = RADICE / "sito" / "modello.html"
TESTI = RADICE / "sito" / "testi"
DOCS = RADICE / "docs"
STATO = RADICE / "stato.json"

REPO = os.environ.get("GITHUB_REPOSITORY", "luigismith/ctrl-alt-revenge-nuovo")
PROPRIETARIO, NOME = REPO.split("/")
URL_SITO = f"https://{PROPRIETARIO}.github.io/{NOME}/"
URL_CODICE = f"https://github.com/{REPO}"

LINGUE = {
    # lingua: (cartella di uscita, prefisso per i file comuni, link all'altra lingua, altra lingua, sigla)
    "it": ("", "", "en/", "en", "EN"),
    "en": ("en/", "../", "../", "it", "IT"),
}

# Le chiavi che finiscono dentro un attributo HTML si proteggono; le altre
# possono contenere un po' di HTML nostro (<strong>, <i lang>).
ATTRIBUTI = re.compile(r"(^meta\.|\.alt$|_alt$|_label$|^ui\.)")


def appiattisci(d, prefisso=""):
    piatto = {}
    for k, v in d.items():
        chiave = f"{prefisso}{k}"
        if isinstance(v, dict):
            piatto.update(appiattisci(v, chiave + "."))
        else:
            piatto[chiave] = v
    return piatto


def leggi_uscite():
    """Le uscite pubblicate, dalla più recente. Lo stato lo scrivono i pubblicatori."""
    if not STATO.exists():
        return []
    stato = json.loads(STATO.read_text(encoding="utf-8"))
    uscite = [u for u in stato.get("uscite", []) if u.get("verificato") and u.get("permalink")]
    return sorted(uscite, key=lambda u: u["quando"], reverse=True)


def laboratorio(t, base, uscite):
    if not uscite:
        return (
            '    <div class="scatola-vuota">\n'
            f'      <p class="scatola-vuota__scritta">{t["lab.vuoto"]}</p>\n'
            '      <ul class="bacheca-vuota" aria-hidden="true"><li></li><li></li><li></li><li></li></ul>\n'
            "    </div>"
        )
    schede = []
    for u in uscite[:12]:
        dove = t["lab.apri_yt"] if u.get("rete") == "youtube" else t["lab.apri_ig"]
        testo = html.escape(u.get("titolo", ""))
        schede.append(
            '      <li class="uscita">'
            f'<a href="{html.escape(u["permalink"])}">'
            f'<img src="{base}{html.escape(u["anteprima"])}" alt="" loading="lazy" width="400" height="500">'
            f'<span class="uscita__data">{u["quando"][:10]}</span>'
            f'<span class="uscita__titolo">{testo}</span>'
            f'<span class="uscita__dove">{dove}</span></a></li>'
        )
    return '    <ul class="uscite">\n' + "\n".join(schede) + "\n    </ul>"


def genera():
    modello = MODELLO.read_text(encoding="utf-8")
    uscite = leggi_uscite()
    for lingua, (cartella, base, url_altra, altra_lang, altra_sigla) in LINGUE.items():
        testi = appiattisci(json.loads((TESTI / f"{lingua}.json").read_text(encoding="utf-8")))
        valori = {k: (html.escape(v, quote=True) if ATTRIBUTI.search(k) else v) for k, v in testi.items()}
        valori.update({
            "lang": lingua, "base": base, "url_altra": url_altra,
            "altra_lang": altra_lang, "altra_sigla": altra_sigla,
            "url_sito": URL_SITO, "url_pagina": URL_SITO + cartella, "url_codice": URL_CODICE,
            "LABORATORIO": laboratorio(testi, base, uscite),
        })
        pagina = re.sub(r"\{\{([\w.]+)\}\}", lambda m: valori[m.group(1)] if m.group(1) in valori else m.group(0), modello)
        rimasti = re.findall(r"\{\{[\w.]+\}\}", pagina)
        if rimasti:
            sys.exit(f"[errore] {lingua}: segnaposto senza testo: {sorted(set(rimasti))}")
        uscita = DOCS / cartella / "index.html"
        uscita.parent.mkdir(parents=True, exist_ok=True)
        uscita.write_text(pagina, encoding="utf-8", newline="\n")
        print(f"[ok] {uscita.relative_to(RADICE)}")
    # le pagine fisse (privacy, cancellazione dei dati, 404): solo gli indirizzi cambiano
    for modello_p in sorted((RADICE / "sito" / "pagine").rglob("*.html")):
        rel = modello_p.relative_to(RADICE / "sito" / "pagine")
        testo = modello_p.read_text(encoding="utf-8").replace("{{url_codice}}", URL_CODICE).replace("{{url_sito}}", URL_SITO)
        (DOCS / rel).parent.mkdir(parents=True, exist_ok=True)
        (DOCS / rel).write_text(testo, encoding="utf-8", newline="\n")
        print(f"[ok] docs/{rel.as_posix()}")


if __name__ == "__main__":
    genera()
